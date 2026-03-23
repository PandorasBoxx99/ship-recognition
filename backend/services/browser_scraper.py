"""Headless browser scraper for Cloudflare-protected sites (MarineTraffic, ShipSpotting).

Uses Playwright with anti-detection to bypass bot protection.
Falls back gracefully if Playwright is not installed.
"""

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
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("playwright_not_installed")
        return [{"error": "Playwright nicht installiert. Run: pip install playwright && playwright install chromium"}]

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

            if container:
                # Ship name + detail link
                ship_link = container.find("a", href=lambda h: h and "/ais/details/ships/" in h)
                if ship_link:
                    ship_name = ship_link.get_text(strip=True)
                    detail_url = ship_link.get("href", "")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = MARINETRAFFIC_BASE + detail_url

                # Extract location and photographer from text
                text_parts = container.get_text(" | ", strip=True).split(" | ")
                for part in text_parts:
                    part = part.strip()
                    # Skip known non-location parts
                    if part in (ship_name, "Rate") or "rating" in part.lower():
                        continue
                    if re.match(r"\d{4}-\d{2}-\d{2}", part):
                        continue  # date
                    if not location and len(part) > 2 and part != ship_name:
                        location = part
                    elif location and not photographer and len(part) > 2:
                        photographer = part

            images.append({
                "url": image_url,
                "alt": ship_name,
                "source_page": photos_url,
                "photo_id": photo_id,
                "detail_url": detail_url,
                "location": location,
                "photographer": photographer,
            })

            if len(images) >= limit:
                break

        log.info("marinetraffic_scraped", count=len(images))

        # Fetch detail pages for ship metadata
        seen_details: dict[str, dict] = {}
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
                time.sleep(1)
            except Exception as e:
                log.warning("mt_detail_error", url=durl, error=str(e))
                seen_details[durl] = {}

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

    return meta
