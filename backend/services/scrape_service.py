"""Scraper service — website analysis, image discovery, and download."""

import json
import logging
import os
import random
import re
import threading
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
import structlog
from bs4 import BeautifulSoup

from backend.config import settings
from backend.database import SessionLocal
from backend.models.item import Item
from backend.models.job import Job

log = structlog.get_logger()

# ---- Dedicated file logger for scraping ----
_scrape_logger = logging.getLogger("scrape_file")
_scrape_logger.setLevel(logging.DEBUG)
_scrape_log_path = os.path.join(settings.LOG_DIR, "scrape.log")
os.makedirs(settings.LOG_DIR, exist_ok=True)
_fh = logging.FileHandler(_scrape_log_path, encoding="utf-8")
_fh.setFormatter(
    logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
_scrape_logger.addHandler(_fh)

# Abort a scrape job after this many consecutive download failures
MAX_CONSECUTIVE_FAILURES = 5


def scrape_log(level: str, job_id: int | None, msg: str, **kw):
    """Write to both structlog and the dedicated scrape.log file."""
    extra = " ".join(f"{k}={v}" for k, v in kw.items()) if kw else ""
    prefix = f"[Job {job_id}] " if job_id else ""
    line = f"{prefix}{msg}  {extra}".strip()
    getattr(_scrape_logger, level, _scrape_logger.info)(line)
    getattr(log, level, log.info)(msg, job_id=job_id, **kw)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

_session = requests.Session()
_session.headers.update(HEADERS)

# Global state for running jobs (matches original app.py pattern)
active_jobs: dict[int, threading.Thread] = {}


def analyze_website(url: str) -> dict:
    """Analyze a website and find categories/structure."""
    try:
        response = _session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        categories = []
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        patterns = [
            'a[href*="category"]',
            'a[href*="type"]',
            'a[href*="gallery"]',
            ".category a",
            ".nav-item a",
            "li.menu-item a",
        ]

        seen_urls: set[str] = set()
        for pattern in patterns:
            for link in soup.select(pattern):
                href = link.get("href", "")
                if href and href not in seen_urls:
                    full_url = urljoin(base_url, href)
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        categories.append(
                            {"name": link.get_text(strip=True) or href, "url": full_url}
                        )
                        seen_urls.add(href)

        title = soup.title.string if soup.title else url

        return {"success": True, "title": title, "categories": categories[:50], "url": url}
    except Exception as e:
        return {"success": False, "error": str(e)}


def find_images(url: str, limit: int = 100) -> list[dict]:
    """Find ship images on a page. Auto-selects scraper strategy per site."""

    # Sites that need headless browser (Cloudflare protected)
    if "marinetraffic.com" in url or "shipspotting.com" in url:
        try:
            from backend.services.browser_scraper import find_marinetraffic_images
            return find_marinetraffic_images(url, limit)
        except ImportError:
            log.warning("playwright_not_available", url=url)
            return []

    try:
        response = _session.get(url, timeout=30)
        soup = BeautifulSoup(response.text, "html.parser")
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        if "vesselfinder.com" in url:
            return _find_vesselfinder_images(soup, base_url, limit)

        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                full_url = urljoin(base_url, src)
                alt = img.get("alt", "")
                if any(ext in full_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    images.append({"url": full_url, "alt": alt, "source_page": url})
                    if len(images) >= limit:
                        break

        return images
    except Exception as e:
        log.error("find_images_error", url=url, error=str(e))
        return []


def _find_vesselfinder_images(soup: BeautifulSoup, base_url: str, limit: int) -> list[dict]:
    """VesselFinder-specific image finder with metadata extraction.

    Finds photos from gallery, then fetches vessel detail pages
    to extract: ship type, IMO, MMSI, flag, year built, dimensions.
    """
    images = []
    seen_vessels: dict[str, dict] = {}  # cache detail lookups by vessel URL

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if "/ship-photos/" in href and href.count("/") == 2:
            photo_url = urljoin(base_url, href)

            # Find ship name and detail link
            ship_name = ""
            vessel_url = ""
            parent = link.find_parent()
            if parent:
                name_el = parent.find("a", class_="ship-name")
                if not name_el:
                    name_el = parent.find("a", href=lambda h: h and "/vessels/details/" in h)
                if name_el:
                    ship_name = name_el.get_text(strip=True)
                    vessel_url = urljoin(base_url, name_el.get("href", ""))

            photo_id = href.split("/")[-1]
            image_url = f"https://photos.vesselfinder.com/2/{photo_id}.jpg"

            entry = {
                "url": image_url,
                "alt": ship_name,
                "source_page": photo_url,
                "photo_id": photo_id,
                "vessel_url": vessel_url,
            }

            # Fetch vessel metadata (cached per vessel URL)
            if vessel_url and vessel_url not in seen_vessels:
                try:
                    meta = _fetch_vesselfinder_details(vessel_url)
                    seen_vessels[vessel_url] = meta
                    time.sleep(0.5)  # rate limit
                except Exception as e:
                    log.warning("vessel_detail_error", url=vessel_url, error=str(e))
                    seen_vessels[vessel_url] = {}

            if vessel_url in seen_vessels:
                entry.update(seen_vessels[vessel_url])

            images.append(entry)

            if len(images) >= limit:
                break

    return images


def _fetch_vesselfinder_details(vessel_url: str) -> dict:
    """Fetch vessel detail page and extract metadata.

    Returns dict with: ship_type, imo, mmsi, flag, year_built, length, beam, gross_tonnage.
    """
    try:
        resp = _session.get(vessel_url, timeout=15)
        if resp.status_code != 200:
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        meta: dict[str, str] = {}

        # H2 often contains "Ship Type, IMO XXXXXXX"
        h2 = soup.find("h2")
        if h2:
            h2_text = h2.get_text(strip=True)
            # Parse "Oil Products Tanker, IMO 9417531"
            if "IMO" in h2_text:
                parts = h2_text.split(",")
                if len(parts) >= 2:
                    meta["ship_type"] = parts[0].strip()
                    imo_match = re.search(r"IMO\s*(\d+)", h2_text)
                    if imo_match:
                        meta["imo"] = imo_match.group(1)

        # Extract key-value pairs from detail table
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)

                if "IMO" in label and "MMSI" in label:
                    # "9417531 / 212874000"
                    parts = value.split("/")
                    if len(parts) >= 2:
                        meta["imo"] = parts[0].strip()
                        meta["mmsi"] = parts[1].strip()
                elif label == "IMO number":
                    meta["imo"] = value
                elif label == "MMSI":
                    meta["mmsi"] = value
                elif label == "Ship Type":
                    meta["ship_type"] = value
                elif label == "AIS Type":
                    meta.setdefault("ship_type", value)
                elif "Flag" in label:
                    meta["flag"] = value
                elif label == "Year of Build":
                    meta["year_built"] = value
                elif "Length Overall" in label:
                    meta["length"] = value
                elif "Beam" in label and "m" in label:
                    meta["beam"] = value
                elif "Gross Tonnage" in label:
                    meta["gross_tonnage"] = value
                elif "DWT" in label:
                    meta["dwt"] = value

        log.info("vessel_detail_scraped", url=vessel_url, meta=meta)
        return meta

    except Exception as e:
        log.error("vessel_detail_fetch_error", url=vessel_url, error=str(e))
        return {}


def download_image(url: str, save_path: str) -> bool:
    """Download a single image via HTTP."""
    try:
        response = _session.get(url, timeout=30, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        log.error("download_error", url=url, error=str(e))
        return False


def _download_with_browser(page, url: str, save_path: str) -> bool:
    """Download an image using Playwright browser (bypasses Cloudflare).

    Uses page.goto() to navigate to the image URL so Cloudflare cookies are sent.
    Captures the response body from the network response.
    """
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Navigate to image URL — browser sends cookies from its session
        resp = page.goto(url, timeout=30000, wait_until="load")
        if resp and resp.ok:
            body = resp.body()
            if body and len(body) > 1000:  # sanity check: real image > 1KB
                with open(save_path, "wb") as f:
                    f.write(body)
                log.info("browser_download_ok", url=url, size=len(body))
                return True
            else:
                log.error("browser_download_too_small", url=url, size=len(body) if body else 0)
                return False
        else:
            status = resp.status if resp else "no response"
            log.error("browser_download_error", url=url, status=status)
            return False
    except Exception as e:
        log.error("browser_download_error", url=url, error=str(e))
        return False


def _needs_browser(url: str) -> bool:
    """Check if the URL requires a browser-based download (Cloudflare-protected sites)."""
    return "marinetraffic.com" in url or "shipspotting.com" in url


def run_scraping_job(job_id: int) -> None:
    """Background task for scraping. Runs in its own thread with its own DB session.

    Supports resume: only processes items with status='pending', so already-downloaded
    or previously-failed items are skipped automatically.
    """
    db = SessionLocal()
    pw = None
    browser = None
    succeeded = 0
    failed = 0
    abort_reason = ""

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            scrape_log("error", job_id, "Job nicht gefunden in DB")
            return

        job.status = "running"
        job.started_at = job.started_at or datetime.now()
        job.error_message = None  # Clear previous error on resume
        db.commit()

        # Only fetch pending items (enables resume after pause/failure)
        items = (
            db.query(Item)
            .filter(Item.job_id == job_id, Item.status == "pending")
            .limit(job.limit_count or 1000)
            .all()
        )

        pending_count = len(items)
        already_done = (job.downloaded or 0)
        scrape_log("info", job_id,
                   f"START  url={job.url}  pending={pending_count}  "
                   f"already_done={already_done}  limit={job.limit_count}")

        if pending_count == 0:
            scrape_log("info", job_id, "Keine ausstehenden Items — Job abgeschlossen")
            job.status = "completed"
            job.completed_at = datetime.now()
            db.commit()
            return

        # Launch browser if needed for Cloudflare-protected downloads
        use_browser = _needs_browser(job.url)
        page = None
        if use_browser:
            try:
                from backend.services.browser_scraper import _launch_browser
                pw, browser, page = _launch_browser()
                page.goto(job.url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(5)
                scrape_log("info", job_id, "Browser-Session gestartet (Cloudflare-Bypass)")
            except Exception as e:
                abort_reason = f"Browser konnte nicht gestartet werden: {e}"
                scrape_log("error", job_id, abort_reason)
                job.status = "failed"
                job.error_message = abort_reason
                db.commit()
                return

        consecutive_failures = 0

        for idx, item in enumerate(items, 1):
            # Check if job was paused
            db.refresh(job)
            if job.status != "running":
                abort_reason = f"Job pausiert bei Item {idx}/{pending_count} (Item-ID {item.id})"
                scrape_log("warning", job_id, abort_reason)
                break

            delay = random.uniform(job.delay_min, job.delay_max)
            time.sleep(delay)

            if not item.image_url:
                scrape_log("warning", job_id, f"Item {item.id}: Keine image_url, uebersprungen")
                item.status = "failed"
                item.error_message = "Keine Bild-URL vorhanden"
                failed += 1
                job.downloaded = (job.downloaded or 0) + 1
                db.commit()
                continue

            # Build filename
            filename = f"{job_id}_{item.id}_{os.path.basename(urlparse(item.image_url).path)}"
            if not os.path.splitext(filename)[1]:
                meta = {}
                try:
                    meta = json.loads(item.metadata_ or "{}")
                except Exception:
                    pass
                photo_id = meta.get("photo_id", item.id)
                filename = f"{job_id}_{item.id}_{photo_id}.jpg"

            save_path = os.path.join(settings.DOWNLOAD_DIR, str(job_id), filename)

            # Download
            if use_browser and page:
                success = _download_with_browser(page, item.image_url, save_path)
            else:
                success = download_image(item.image_url, save_path)

            if success:
                item.status = "downloaded"
                item.local_path = save_path
                item.downloaded_at = datetime.now()
                item.error_message = None
                succeeded += 1
                consecutive_failures = 0

                # Sync to normalized Ship+Image entity
                try:
                    from backend.services.ship_sync_service import sync_item_to_ship
                    ship, _img = sync_item_to_ship(db, item)
                    scrape_log("info", job_id,
                               f"OK     [{idx}/{pending_count}]  {item.ship_name or 'Unbekannt'}  "
                               f"photo_id={meta.get('photo_id', '-')}  "
                               f"size={os.path.getsize(save_path)}B  "
                               f"ship_id={ship.id}")
                except Exception as sync_err:
                    scrape_log("warning", job_id,
                               f"OK     [{idx}/{pending_count}]  {item.ship_name or 'Unbekannt'}  "
                               f"photo_id={meta.get('photo_id', '-')}  "
                               f"size={os.path.getsize(save_path)}B  "
                               f"sync_error={sync_err}")
            else:
                item.status = "failed"
                item.error_message = "Download fehlgeschlagen"
                failed += 1
                consecutive_failures += 1
                scrape_log("error", job_id,
                           f"FEHLER [{idx}/{pending_count}]  {item.ship_name or 'Unbekannt'}  "
                           f"url={item.image_url}")

            job.downloaded = (job.downloaded or 0) + 1
            db.commit()

            # Abort if too many consecutive failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                abort_reason = (
                    f"Abgebrochen: {MAX_CONSECUTIVE_FAILURES} Downloads in Folge fehlgeschlagen. "
                    f"Moeglicherweise blockiert die Quelle. "
                    f"Fortschritt: {succeeded} OK, {failed} Fehler von {pending_count}."
                )
                scrape_log("error", job_id, abort_reason)
                job.status = "failed"
                job.error_message = abort_reason
                db.commit()
                return

        # Final status
        remaining = db.query(Item).filter(
            Item.job_id == job_id, Item.status == "pending"
        ).count()

        if remaining == 0 and job.status == "running":
            job.status = "completed"
            job.completed_at = datetime.now()
            summary = f"Abgeschlossen: {succeeded} heruntergeladen, {failed} fehlgeschlagen"
            scrape_log("info", job_id, f"FERTIG  {summary}")
        elif job.status == "running":
            # Paused externally or partial
            job.status = "paused"
            summary = f"Pausiert: {succeeded} OK, {failed} Fehler, {remaining} ausstehend"
            job.error_message = abort_reason or summary
            scrape_log("warning", job_id, summary)

        db.commit()

    except Exception as e:
        abort_reason = f"Unerwarteter Fehler: {e}"
        scrape_log("error", job_id, abort_reason)
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = abort_reason
                db.commit()
        except Exception:
            pass
    finally:
        scrape_log("info", job_id,
                   f"ENDE   succeeded={succeeded}  failed={failed}  "
                   f"abort_reason={abort_reason or 'keiner'}")
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if pw:
            try:
                pw.stop()
            except Exception:
                pass
        db.close()
        active_jobs.pop(job_id, None)


def start_scraping_job(job_id: int) -> None:
    """Launch the scraping job in a background thread."""
    scrape_log("info", job_id, "Thread wird gestartet")
    thread = threading.Thread(target=run_scraping_job, args=(job_id,), daemon=True)
    thread.start()
    active_jobs[job_id] = thread
