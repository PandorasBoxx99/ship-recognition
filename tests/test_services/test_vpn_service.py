"""Tests for the VPN service (NordVPN REST-API + SOCKS5 proxy, no CLI)."""

from unittest.mock import MagicMock, patch

import pytest

from backend.services import vpn_service
from backend.services.vpn_service import (
    get_proxies,
    get_service_credentials,
    get_vpn_status,
    resolve_proxy_country,
)


@pytest.fixture(autouse=True)
def _reset_creds_cache():
    """Service credentials are cached at module level — clear between tests."""
    vpn_service._cached_creds = None
    yield
    vpn_service._cached_creds = None


def _api_response(status_code, json_data):
    """Build a fake requests.Response with given status and JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_get_status_connected(mock_settings, mock_get):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "valid-token"
    mock_settings.VPN_DEFAULT_COUNTRY = "Germany"
    # 1st call: credential check (dict), 2nd call: server recommendations (list)
    mock_get.side_effect = [
        _api_response(200, {"username": "ronny"}),
        _api_response(200, [{"name": "de1024", "station": "1.2.3.4"}]),
    ]

    status = get_vpn_status()

    assert status["connected"] is True
    assert status["country"] == "Germany"
    assert status["ip"] == "1.2.3.4"
    assert status["server"] == "de1024"
    assert status["token_valid"] is True


@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_get_status_invalid_token(mock_settings, mock_get):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "bad-token"
    mock_get.return_value = _api_response(401, {})

    status = get_vpn_status()

    assert status["connected"] is False
    assert status["token_valid"] is False


@patch("backend.services.vpn_service.settings")
def test_get_status_no_token(mock_settings):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = ""

    status = get_vpn_status()

    assert status["connected"] is False
    assert "token" in status["error"].lower()


@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_get_status_api_unreachable(mock_settings, mock_get):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "valid-token"
    mock_get.side_effect = Exception("connection refused")

    status = get_vpn_status()

    assert status["connected"] is False
    assert "error" in status


@patch("backend.services.vpn_service.settings")
def test_disabled_vpn(mock_settings):
    mock_settings.VPN_ENABLED = False

    status = get_vpn_status()

    assert status["connected"] is False
    assert "deaktiviert" in status["error"].lower()


# --- SOCKS5 proxy routing ---


@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_get_service_credentials(mock_settings, mock_get):
    mock_settings.VPN_API_KEY = "valid-token"
    mock_get.return_value = _api_response(200, {"username": "svc-user", "password": "svc-pass"})

    creds = get_service_credentials()

    assert creds == ("svc-user", "svc-pass")


@patch("backend.services.vpn_service.requests.get")
@patch("backend.services.vpn_service.settings")
def test_get_proxies_builds_socks_url(mock_settings, mock_get):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "valid-token"
    mock_settings.VPN_PROXY_COUNTRY = "Netherlands"
    mock_settings.VPN_DEFAULT_COUNTRY = "Germany"
    mock_get.return_value = _api_response(200, {"username": "svc-user", "password": "svc-pass"})

    proxies = get_proxies()

    assert proxies is not None
    expected = "socks5h://svc-user:svc-pass@nl.socks.nordhold.net:1080"
    assert proxies["http"] == expected
    assert proxies["https"] == expected


@patch("backend.services.vpn_service.settings")
def test_get_proxies_disabled_returns_none(mock_settings):
    mock_settings.VPN_ENABLED = False

    assert get_proxies() is None


@patch("backend.services.vpn_service.settings")
def test_resolve_proxy_country_falls_back_to_supported(mock_settings):
    # Germany has no SOCKS5 proxy -> must fall back to a supported country
    mock_settings.VPN_PROXY_COUNTRY = "Germany"
    mock_settings.VPN_DEFAULT_COUNTRY = "Germany"

    country = resolve_proxy_country()

    assert country in vpn_service.SOCKS5_PROXIES
