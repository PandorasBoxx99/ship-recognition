"""Tests for /api/ships endpoints."""


def test_get_ships(client):
    resp = client.get("/api/ships")
    assert resp.status_code == 200
    data = resp.json()
    assert "ships" in data
    assert "types" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert isinstance(data["ships"], list)
    assert data["total"] >= 2  # 2 downloaded items in seed data


def test_get_ships_pagination(client):
    resp = client.get("/api/ships?page=1&per_page=1")
    data = resp.json()
    assert len(data["ships"]) <= 1
    assert data["per_page"] == 1


def test_get_ships_filter_by_type(client):
    resp = client.get("/api/ships?type=Container Ship")
    data = resp.json()
    for ship in data["ships"]:
        assert ship["ship_type"] == "Container Ship"


def test_get_ships_search(client):
    resp = client.get("/api/ships?search=Alpha")
    data = resp.json()
    assert data["total"] >= 1
    assert any("Alpha" in s.get("ship_name", "") for s in data["ships"])


def test_get_ship_detail(client):
    ships = client.get("/api/ships").json()["ships"]
    ship_id = ships[0]["id"]

    resp = client.get(f"/api/ships/{ship_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == ship_id
    assert "ship_name" in data
    assert "job_name" in data


def test_get_ship_not_found(client):
    resp = client.get("/api/ships/99999")
    assert resp.status_code == 404


def test_ships_stats(client):
    resp = client.get("/api/ships/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_downloaded" in data
    assert "total_classified" in data
    assert "by_type" in data
    assert isinstance(data["by_type"], list)
