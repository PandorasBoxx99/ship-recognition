"""Headless browser scraper for Cloudflare-protected sites (MarineTraffic, ShipSpotting).

Uses Playwright with anti-detection to bypass bot protection.
Falls back gracefully if Playwright is not installed.
"""

import importlib.util
import re
import time

import structlog

log = structlog.get_logger()

MARINETRAFFIC_BASE = "https://www.marinetraffic.com"


def _launch_browser():
    """Launch Playwright Chromium with anti-detection settings."""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
    )
    ctx = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        locale="de-DE",
    )
    page = ctx.new_page()
    page.add_init_script(
        'Object.defineProperty(navigator,"webdriver",{get:()=>undefined})'
    )
    return pw, browser, page


def find_marinetraffic_images(url: str, limit: int = 50) -> list[dict]:
    """Scrape MarineTraffic ship photos using headless browser.

    Returns list of dicts with: url, alt (ship name), source_page, ship_id,
    location, photographer, detail_url.
    """
    if importlib.util.find_spec("playwright") is None:
        log.error("playwright_not_installed")
        return [{"error": "Playwright nicht installiert. "
                 "Run: pip install playwright && playwright install chromium"}]

    photos_url = url
    if "/photos" not in url:
        photos_url = f"{MARINETRAFFIC_BASE}/en/photos/of/ships"

    pw = None
    browser = None
    try:
        pw, browser, page = _launch_browser()

        log.info("browser_loading", url=photos_url)
        page.goto(photos_url, timeout=45000, wait_until="domcontentloaded")

        # Wait for Cloudflare challenge to pass
        time.sleep(8)

        title = page.title()
        if "cloudflare" in title.lower() or "blocked" in title.lower():
            log.warning("cloudflare_still_blocking", title=title)
            time.sleep(10)
            title = page.title()

        if "cloudflare" in title.lower():
            return [{"error": "Cloudflare blockiert weiterhin. Versuche es spaeter erneut."}]

        log.info("browser_loaded", title=title)

        # Scroll down to load more images (lazy-loaded content)
        prev_height = 0
        scroll_attempts = 0
        max_scrolls = 10
        while scroll_attempts < max_scrolls:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break
            prev_height = new_height
            scroll_attempts += 1
            log.info("browser_scrolled", attempt=scroll_attempts, height=new_height)

        from bs4 import BeautifulSoup
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        images = []
        for img in soup.find_all("img", src=lambda s: s and "getPhoto" in s):
            src = img.get("src", "")
            photo_id_match = re.search(r"photo_id=(\d+)", src)
            if not photo_id_match:
                continue

            photo_id = photo_id_match.group(1)
            image_url = f"{MARINETRAFFIC_BASE}/getPhoto/?photo_id={photo_id}&photo_size=800"

            # Find container with metadata
            container = img.find_parent("div")
            if container:
                container = container.find_parent("div") or container

            ship_name = ""
            detail_url = ""
            location = ""
            photographer = ""
            photo_date = ""

            if container:
                # Ship name + detail link
                ship_link = container.find("a", href=lambda h: h and "/ais/details/ships/" in h)
                if ship_link:
                    ship_name = ship_link.get_text(strip=True)
                    detail_url = ship_link.get("href", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = MARINETRAFFIC_BASE + detail_url

                # Extract location, photographer, and date from text
                # On MarineTraffic listings, text order is typically:
                #   ship_name | photographer | date | location | ...
                text_parts = container.get_text(" | ", strip=True).split(" | ")
                non_meta_parts: list[str] = []
                for part in text_parts:
                    part = part.strip()
                    if not part or len(part) < 2:
                        continue
                    if part == ship_name or part == "Rate" or "rating" in part.lower():
                        continue
                    # Capture date (YYYY-MM-DD HH:MM or DD/MM/YYYY patterns)
                    if re.match(r"\d{4}-\d{2}-\d{2}", part):
                        photo_date = part
                        continue
                    if re.match(r"\d{2}/\d{2}/\d{4}", part):
                        photo_date = part
                        continue
                    non_meta_parts.append(part)

                # MarineTraffic: first part is photographer, second could be location
                if len(non_meta_parts) >= 1:
                    photographer = non_meta_parts[0]
                if len(non_meta_parts) >= 2:
                    location = non_meta_parts[1]

            images.append({
                "url": image_url,
                "alt": ship_name,
                "source_page": photos_url,
                "photo_id": photo_id,
                "detail_url": detail_url,
                "location": location,
                "photographer": photographer,
                "photo_date": photo_date,
            })

            if len(images) >= limit:
                break

        log.info("marinetraffic_scraped", count=len(images))

        # Fetch detail pages for ship metadata + find all photos per ship
        seen_details: dict[str, dict] = {}
        extra_images: list[dict] = []

        for img in images:
            durl = img.get("detail_url", "")
            if not durl or durl in seen_details:
                if durl in seen_details:
                    img.update(seen_details[durl])
                continue

            try:
                page.goto(durl, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)
                detail_html = page.content()
                meta = _parse_marinetraffic_detail(detail_html)
                seen_details[durl] = meta
                img.update(meta)
                log.info("mt_detail_scraped", ship=img.get("alt"), meta=meta)

                # Find ALL photos of this ship on the detail page
                detail_soup = BeautifulSoup(detail_html, "html.parser")
                existing_ids = {i.get("photo_id") for i in images + extra_images}
                for detail_img in detail_soup.find_all("img", src=lambda s: s and "getPhoto" in s):
                    pid_match = re.search(r"photo_id=(\d+)", detail_img.get("src", ""))
                    if pid_match and pid_match.group(1) not in existing_ids:
                        pid = pid_match.group(1)
                        extra_images.append({
                            "url": f"{MARINETRAFFIC_BASE}/getPhoto/?photo_id={pid}&photo_size=800",
                            "alt": img.get("alt", ""),
                            "source_page": durl,
                            "photo_id": pid,
                            "detail_url": durl,
                            "location": img.get("location", ""),
                            "photographer": "",
                            **meta,
                        })
                        existing_ids.add(pid)
                        log.info("mt_extra_photo", ship=img.get("alt"), photo_id=pid)

                time.sleep(1)
            except Exception as e:
                log.warning("mt_detail_error", url=durl, error=str(e))
                seen_details[durl] = {}

        # Merge extra images from ship detail pages
        images.extend(extra_images)
        log.info(
            "marinetraffic_total_with_extras",
            listing=len(images) - len(extra_images),
            extras=len(extra_images),
            total=len(images),
        )

        return images

    except Exception as e:
        log.error("browser_scrape_error", error=str(e))
        return [{"error": str(e)}]
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()


def _parse_marinetraffic_detail(html: str) -> dict:
    """Parse MarineTraffic vessel detail page for metadata."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    meta: dict[str, str] = {}

    # Ship type from breadcrumb or header
    for el in soup.find_all(["h1", "h2", "span", "div"]):
        text = el.get_text(strip=True)
        if "IMO:" in text:
            imo_match = re.search(r"IMO:\s*(\d+)", text)
            if imo_match:
                meta["imo"] = imo_match.group(1)
        if "MMSI:" in text:
            mmsi_match = re.search(r"MMSI:\s*(\d+)", text)
            if mmsi_match:
                meta["mmsi"] = mmsi_match.group(1)

    # Look for vessel info table
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True).lower()
            value = cells[1].get_text(strip=True)
            if not value:
                continue
            if "imo" in label:
                meta["imo"] = re.sub(r"\D", "", value)[:7]
            elif "mmsi" in label:
                meta["mmsi"] = re.sub(r"\D", "", value)[:9]
            elif "ship type" in label or "vessel type" in label:
                meta["ship_type"] = value
            elif "flag" in label:
                meta["flag"] = value
            elif "year" in label and "built" in label:
                meta["year_built"] = value
            elif "gross tonnage" in label:
                meta["gross_tonnage"] = value
            elif "length" in label:
                meta["length"] = value

    # Also check key-value spans
    for span in soup.find_all("span"):
        text = span.get_text(strip=True)
        if "Vessel Type:" in text or "Ship Type:" in text:
            value = text.split(":")[-1].strip()
            if value:
                meta["ship_type"] = value

    # Extract coordinates (lat/lon) from page content
    full_text = soup.get_text()
    lat_match = re.search(r"(?:lat|latitude)[:\s]*(-?\d+\.?\d*)", full_text, re.IGNORECASE)
    lon_match = re.search(r"(?:lon|longitude)[:\s]*(-?\d+\.?\d*)", full_text, re.IGNORECASE)
    if lat_match:
        meta["latitude"] = lat_match.group(1)
    if lon_match:
        meta["longitude"] = lon_match.group(1)

    # Try to extract coordinates from data attributes or meta tags
    for el in soup.find_all(attrs={"data-lat": True}):
        meta["latitude"] = el["data-lat"]
        if el.get("data-lon"):
            meta["longitude"] = el["data-lon"]
        break

    # Extract port/area name
    for el in soup.find_all(["a", "span", "div"]):
        text = el.get_text(strip=True)
        if "Port:" in text or "Area:" in text:
            val = text.split(":")[-1].strip()
            if val:
                meta["port"] = val
                break

    return meta
