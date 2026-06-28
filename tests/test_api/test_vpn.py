"""Tests for the /api/vpn endpoints (NordVPN SOCKS5)."""

from unittest.mock import patch


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


@patch("backend.routers.vpn.update_env_settings")
@patch("backend.services.vpn_service.get_connection_info")
def test_vpn_config_change_country(mock_info, mock_update, client):
    mock_info.return_value = {
        "vpn_enabled": True, "token_present": True, "direct_ip": "185.169.0.170",
        "vpn_ip": "185.236.42.49", "proxy_country": "Sweden",
        "server_host": "se.socks.nordhold.net",
        "available_countries": ["Netherlands", "Sweden", "United States"], "protected": True,
    }

    resp = client.put("/api/vpn/config", json={"proxy_country": "Sweden"})
    assert resp.status_code == 200
    mock_update.assert_called_once_with({"vpn_proxy_country": "Sweden"})
