"""Tests for scraper service."""

from unittest.mock import MagicMock, patch

from backend.services.scrape_service import analyze_website, find_images

MOCK_HTML = """
<html>
<head><title>Test Ship Site</title></head>
<body>
<a href="/category/tankers">Tankers</a>
<a href="/category/bulkers">Bulkers</a>
<img src="/images/ship1.jpg" alt="Ship One">
<img src="/images/ship2.png" alt="Ship Two">
<img src="/images/logo.svg" alt="Logo">
</body>
</html>
"""


@patch("backend.services.scrape_service._session")
def test_analyze_website(mock_session):
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML
    mock_resp.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_resp

    result = analyze_website("https://example.com/ships")
    assert result["success"] is True
    assert result["title"] == "Test Ship Site"
    assert isinstance(result["categories"], list)
    assert any("tankers" in c["url"].lower() for c in result["categories"])


@patch("backend.services.scrape_service._session")
def test_analyze_website_failure(mock_session):
    mock_session.get.side_effect = Exception("Connection error")

    result = analyze_website("https://unreachable.example.com")
    assert result["success"] is False
    assert "error" in result


@patch("backend.services.scrape_service._session")
def test_find_images(mock_session):
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML
    mock_session.get.return_value = mock_resp

    images = find_images("https://example.com/ships", limit=10)
    assert isinstance(images, list)
    # Should find .jpg and .png but not .svg
    assert len(images) == 2
    assert all("url" in img for img in images)


@patch("backend.services.scrape_service._session")
def test_find_images_limit(mock_session):
    mock_resp = MagicMock()
    mock_resp.text = MOCK_HTML
    mock_session.get.return_value = mock_resp

    images = find_images("https://example.com/ships", limit=1)
    assert len(images) == 1


@patch("backend.services.scrape_service._session")
def test_find_images_error(mock_session):
    mock_session.get.side_effect = Exception("Timeout")

    images = find_images("https://example.com/ships")
    assert images == []


VESSEL_FINDER_HTML = """
<html><body>
<a href="/ship-photos/12345">
    <div>
        <a href="/vessels/details/9876543">MV Test Ship</a>
    </div>
</a>
<a href="/ship-photos/67890">Photo 2</a>
</body></html>
"""


@patch("backend.services.scrape_service._session")
def test_find_vesselfinder_images(mock_session):
    mock_resp = MagicMock()
    mock_resp.text = VESSEL_FINDER_HTML
    mock_session.get.return_value = mock_resp

    images = find_images("https://www.vesselfinder.com/gallery", limit=10)
    assert isinstance(images, list)
    assert len(images) >= 1
    assert "photos.vesselfinder.com" in images[0]["url"]
