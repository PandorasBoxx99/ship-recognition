"""Tests for /api/stats endpoint (ship data from v2, pipeline metrics from queue)."""


def test_get_stats(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "total_jobs", "total_ships", "total_images",
        "pending", "failed", "classifications", "type_distribution",
    ):
        assert key in data
    # Seed data has 1 job and 1 pending item (queue/ingestion layer)
    assert data["total_jobs"] >= 1
    assert data["pending"] >= 1


def test_stats_type_distribution(client):
    resp = client.get("/api/stats")
    data = resp.json()
    dist = data["type_distribution"]
    assert isinstance(dist, list)
    if dist:
        assert "type" in dist[0]
        assert "count" in dist[0]
