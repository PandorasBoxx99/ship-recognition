"""Tests for /api/urls endpoints."""


def test_get_urls(client):
    resp = client.get("/api/urls")
    assert resp.status_code == 200
    urls = resp.json()
    assert isinstance(urls, list)
    assert len(urls) >= 2
    assert urls[0]["name"] in ("ShipSpotting", "VesselFinder")


def test_add_url(client):
    resp = client.post("/api/urls", json={"url": "https://new-source.com/", "name": "NewSource"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "https://new-source.com/"
    assert data["name"] == "NewSource"
    assert "id" in data


def test_add_url_auto_name(client):
    resp = client.post("/api/urls", json={"url": "https://www.example-ships.com/gallery"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"]  # auto-generated name


def test_add_url_empty_fails(client):
    resp = client.post("/api/urls", json={"url": ""})
    assert resp.status_code == 400


def test_add_url_duplicate_fails(client):
    client.post("/api/urls", json={"url": "https://unique-test.com/", "name": "Test"})
    resp = client.post("/api/urls", json={"url": "https://unique-test.com/", "name": "Test2"})
    assert resp.status_code == 409


def test_delete_url(client):
    # Create then delete
    create_resp = client.post("/api/urls", json={"url": "https://to-delete.com/", "name": "Del"})
    url_id = create_resp.json()["id"]

    resp = client.delete(f"/api/urls/{url_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
