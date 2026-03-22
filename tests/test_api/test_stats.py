"""Tests for /api/stats endpoint."""


def test_get_stats(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_jobs" in data
    assert "total_items" in data
    assert "downloaded" in data
    assert "pending" in data
    assert "failed" in data
    assert "classifications" in data
    assert "type_distribution" in data
    assert data["total_jobs"] >= 1
    assert data["total_items"] >= 3
    assert data["downloaded"] >= 2


def test_stats_type_distribution(client):
    resp = client.get("/api/stats")
    data = resp.json()
    dist = data["type_distribution"]
    assert isinstance(dist, list)
    if dist:
        assert "type" in dist[0]
        assert "count" in dist[0]
