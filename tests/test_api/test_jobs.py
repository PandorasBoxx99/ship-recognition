"""Tests for /api/jobs and /api/analyze endpoints."""

from unittest.mock import patch


def test_get_jobs(client):
    resp = client.get("/api/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    job = jobs[0]
    assert "id" in job
    assert "url" in job
    assert "status" in job
    assert "total_items" in job


def test_get_job_detail(client):
    # Get list first to find an ID
    jobs = client.get("/api/jobs").json()
    job_id = jobs[0]["id"]

    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "job" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_get_job_not_found(client):
    resp = client.get("/api/jobs/99999")
    assert resp.status_code == 404


@patch("backend.routers.scrape.find_images", return_value=[
    {"url": "https://img.example.com/1.jpg", "alt": "Ship A", "source_page": "https://example.com"},
])
def test_create_job(mock_find, client):
    resp = client.post("/api/jobs", json={
        "url": "https://example.com/ships",
        "name": "New Test Job",
        "limit": 50,
        "delay_min": 2.0,
        "delay_max": 4.0,
        "vpn_required": False,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Test Job"
    assert data["total_items"] == 1
    assert data["status"] == "pending"


def test_create_job_no_url(client):
    resp = client.post("/api/jobs", json={"name": "No URL"})
    assert resp.status_code == 422  # Pydantic validation error


def test_pause_job(client):
    jobs = client.get("/api/jobs").json()
    job_id = jobs[0]["id"]

    resp = client.post(f"/api/jobs/{job_id}/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_delete_job(client):
    # Create a throwaway job first
    with patch("backend.routers.scrape.find_images", return_value=[]):
        create_resp = client.post("/api/jobs", json={
            "url": "https://delete-me.com",
            "vpn_required": False,
        })
    job_id = create_resp.json()["id"]

    resp = client.delete(f"/api/jobs/{job_id}/delete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Verify it's gone
    resp = client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 404


@patch("backend.routers.scrape.analyze_website", return_value={
    "success": True,
    "title": "Example Ships",
    "categories": [{"name": "Tankers", "url": "https://example.com/tankers"}],
    "url": "https://example.com",
})
def test_analyze(mock_analyze, client):
    resp = client.post("/api/analyze", json={"url": "https://example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "categories" in data
