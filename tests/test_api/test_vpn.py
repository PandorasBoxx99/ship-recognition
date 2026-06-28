"""Tests for the /api/vpn endpoints (NordVPN REST-API based, no CLI)."""

from unittest.mock import MagicMock, patch


def _api_response(status_code, json_data):
    """Build a fake requests.Response with given status and JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


CREDENTIALS_OK = {"username": "ronny"}
SERVERS_OK = [{"name": "de1024", "station": "1.2.3.4"}]


@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_vpn_status_connected(mock_settings, mock_get, client):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "valid-token"
    mock_settings.VPN_DEFAULT_COUNTRY = "Germany"
    mock_get.side_effect = [
        _api_response(200, CREDENTIALS_OK),
        _api_response(200, SERVERS_OK),
    ]

    resp = client.get("/api/vpn/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["country"] == "Germany"
    assert data["ip"] == "1.2.3.4"


@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_vpn_status_invalid_token(mock_settings, mock_get, client):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "bad-token"
    mock_get.return_value = _api_response(401, {})

    resp = client.get("/api/vpn/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False


@patch("backend.services.vpn_service.get_exit_ip", return_value="213.232.87.234")
@patch("backend.services.vpn_service.get_proxies", return_value={"https": "socks5h://x"})
@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_vpn_connect(mock_settings, mock_get, mock_proxies, mock_exit, client):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "valid-token"
    mock_get.side_effect = [
        _api_response(200, CREDENTIALS_OK),  # test_token
        _api_response(200, SERVERS_OK),       # recommendations
    ]

    resp = client.post("/api/vpn/connect", json={"country": "Netherlands"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["ip"] == "213.232.87.234"  # the verified SOCKS5 exit IP


def test_vpn_disconnect(client):
    resp = client.post("/api/vpn/disconnect")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False


@patch("backend.services.vpn_service.get_exit_ip", return_value="213.232.87.234")
@patch("backend.services.vpn_service.get_proxies", return_value={"https": "socks5h://x"})
@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_vpn_rotate(mock_settings, mock_get, mock_proxies, mock_exit, client):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "valid-token"
    mock_settings.VPN_DEFAULT_COUNTRY = "Germany"
    mock_get.side_effect = [
        _api_response(200, CREDENTIALS_OK),
        _api_response(200, SERVERS_OK),
    ]

    resp = client.post("/api/vpn/rotate")
    assert resp.status_code == 200


@patch("backend.services.vpn_service.settings")
def test_vpn_disabled(mock_settings, client):
    mock_settings.VPN_ENABLED = False

    resp = client.get("/api/vpn/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert "deaktiviert" in data.get("error", "").lower()


@patch("backend.services.vpn_service.get_connection_info")
def test_vpn_connection_endpoint(mock_info, client):
    mock_info.return_value = {
        "vpn_enabled": True, "token_present": True,
        "direct_ip": "185.169.0.170", "vpn_ip": "213.232.87.234",
        "proxy_country": "Netherlands", "server_host": "nl.socks.nordhold.net",
        "available_countries": ["Netherlands", "Sweden", "United States"],
        "protected": True,
    }

    resp = client.get("/api/vpn/connection")
    assert resp.status_code == 200
    data = resp.json()
    assert data["protected"] is True
    assert data["vpn_ip"] == "213.232.87.234"
    assert data["available_countries"] == ["Netherlands", "Sweden", "United States"]


def test_vpn_config_invalid_country(client):
    # Germany has no SOCKS5 proxy -> rejected before any .env write
    resp = client.put("/api/vpn/config", json={"proxy_country": "Germany"})
    assert resp.status_code == 400


@patch("backend.routers.vpn.update_env_settings")
@patch("backend.services.vpn_service.get_connection_info")
def test_vpn_config_toggle_off(mock_info, mock_update, client):
    mock_info.return_value = {
        "vpn_enabled": False, "token_present": True, "direct_ip": "185.169.0.170",
        "vpn_ip": None, "proxy_country": None, "server_host": None,
        "available_countries": ["Netherlands", "Sweden", "United States"], "protected": False,
    }

    resp = client.put("/api/vpn/config", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["vpn_enabled"] is False
    mock_update.assert_called_once_with({"vpn_enabled": False})
