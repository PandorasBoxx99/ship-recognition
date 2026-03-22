"""Tests for /api/vpn endpoints."""

from unittest.mock import MagicMock, patch


CONNECTED_OUTPUT = "Status: Connected\nCountry: Germany\nServer IP: 1.2.3.4\n"
DISCONNECTED_OUTPUT = "Status: Disconnected\n"


@patch("backend.services.vpn_service.subprocess")
def test_vpn_status_connected(mock_sub, client):
    mock_result = MagicMock()
    mock_result.stdout = CONNECTED_OUTPUT
    mock_sub.run.return_value = mock_result

    resp = client.get("/api/vpn/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["country"] == "Germany"
    assert data["ip"] == "1.2.3.4"


@patch("backend.services.vpn_service.subprocess")
def test_vpn_status_disconnected(mock_sub, client):
    mock_result = MagicMock()
    mock_result.stdout = DISCONNECTED_OUTPUT
    mock_sub.run.return_value = mock_result

    resp = client.get("/api/vpn/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False


@patch("backend.services.vpn_service.time.sleep")
@patch("backend.services.vpn_service.subprocess")
def test_vpn_connect(mock_sub, mock_sleep, client):
    mock_result = MagicMock()
    mock_result.stdout = CONNECTED_OUTPUT
    mock_sub.run.return_value = mock_result

    resp = client.post("/api/vpn/connect", json={"country": "Germany"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True


@patch("backend.services.vpn_service.subprocess")
def test_vpn_disconnect(mock_sub, client):
    mock_result = MagicMock()
    mock_result.stdout = DISCONNECTED_OUTPUT
    mock_sub.run.return_value = mock_result

    resp = client.post("/api/vpn/disconnect")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False


@patch("backend.services.vpn_service.time.sleep")
@patch("backend.services.vpn_service.subprocess")
def test_vpn_rotate(mock_sub, mock_sleep, client):
    mock_result = MagicMock()
    mock_result.stdout = CONNECTED_OUTPUT
    mock_sub.run.return_value = mock_result

    resp = client.post("/api/vpn/rotate")
    assert resp.status_code == 200


@patch("backend.services.vpn_service.settings")
def test_vpn_disabled(mock_settings, client):
    mock_settings.VPN_ENABLED = False

    resp = client.get("/api/vpn/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert "disabled" in data.get("error", "").lower()
