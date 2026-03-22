"""Scraper service — website analysis, image discovery, and download."""

import os
import random
import threading
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models.item import Item
from backend.models.job import Job

import structlog

log = structlog.get_logger()

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
    """Find ship images on a page."""
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
    """VesselFinder-specific image finder."""
    images = []

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if "/ship-photos/" in href and href.count("/") == 2:
            photo_url = urljoin(base_url, href)

            ship_name = ""
            parent = link.find_parent()
            if parent:
                name_link = parent.find("a", href=lambda h: h and "/vessels/details/" in h)
                if name_link:
                    ship_name = name_link.get_text(strip=True)

            photo_id = href.split("/")[-1]
            image_url = f"https://photos.vesselfinder.com/2/{photo_id}.jpg"

            images.append(
                {"url": image_url, "alt": ship_name, "source_page": photo_url, "photo_id": photo_id}
            )

            if len(images) >= limit:
                break

    return images


def download_image(url: str, save_path: str) -> bool:
    """Download a single image."""
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


def run_scraping_job(job_id: int) -> None:
    """Background task for scraping. Runs in its own thread with its own DB session."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.now().isoformat()
        db.commit()

        items = (
            db.query(Item)
            .filter(Item.job_id == job_id, Item.status == "pending")
            .limit(job.limit_count or 1000)
            .all()
        )

        for item in items:
            # Check if job was paused
            db.refresh(job)
            if job.status != "running":
                break

            delay = random.uniform(job.delay_min, job.delay_max)
            time.sleep(delay)

            if item.image_url:
                filename = f"{job_id}_{item.id}_{os.path.basename(urlparse(item.image_url).path)}"
                save_path = os.path.join(settings.DOWNLOAD_DIR, str(job_id), filename)

                success = download_image(item.image_url, save_path)

                if success:
                    item.status = "downloaded"
                    item.local_path = save_path
                    item.downloaded_at = datetime.now().isoformat()
                else:
                    item.status = "failed"

                job.downloaded = (job.downloaded or 0) + 1
                db.commit()

        job.status = "completed"
        job.completed_at = datetime.now().isoformat()
        db.commit()

    except Exception as e:
        log.error("scraping_job_failed", job_id=job_id, error=str(e))
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()
        active_jobs.pop(job_id, None)


def start_scraping_job(job_id: int) -> None:
    """Launch the scraping job in a background thread."""
    thread = threading.Thread(target=run_scraping_job, args=(job_id,), daemon=True)
    thread.start()
    active_jobs[job_id] = thread
