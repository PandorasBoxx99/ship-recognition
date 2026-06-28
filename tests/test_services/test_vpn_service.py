"""Tests for the VPN service (NordVPN REST-API + SOCKS5 proxy, no CLI)."""

from unittest.mock import MagicMock, patch

import pytest

from backend.services import vpn_service
from backend.services.vpn_service import (
    get_proxies,
    get_service_credentials,
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


# --- connection info (direct + VPN IP) ---


@patch("backend.services.vpn_service.get_direct_ip", return_value="185.169.0.170")
@patch("backend.services.vpn_service.settings")
def test_connection_info_vpn_disabled(mock_settings, mock_direct):
    mock_settings.VPN_ENABLED = False
    mock_settings.VPN_API_KEY = "tok"

    info = vpn_service.get_connection_info()

    assert info["vpn_enabled"] is False
    assert info["direct_ip"] == "185.169.0.170"
    assert info["vpn_ip"] is None
    assert info["protected"] is False
    assert info["available_countries"] == ["Netherlands", "Sweden", "United States"]


@patch("backend.services.vpn_service.get_exit_ip", return_value="213.232.87.234")
@patch("backend.services.vpn_service.get_proxies", return_value={"https": "socks5h://x"})
@patch("backend.services.vpn_service.get_socks5_upstream",
       return_value=("nl.socks.nordhold.net", 1080, "u", "p"))
@patch("backend.services.vpn_service.get_direct_ip", return_value="185.169.0.170")
@patch("backend.services.vpn_service.settings")
def test_connection_info_protected(mock_settings, mock_direct, mock_up, mock_proxies, mock_exit):
    mock_settings.VPN_ENABLED = True
    mock_settings.VPN_API_KEY = "tok"
    mock_settings.VPN_PROXY_COUNTRY = "Netherlands"
    mock_settings.VPN_DEFAULT_COUNTRY = "Germany"

    info = vpn_service.get_connection_info()

    assert info["vpn_ip"] == "213.232.87.234"
    assert info["server_host"] == "nl.socks.nordhold.net"
    assert info["proxy_country"] == "Netherlands"
    assert info["protected"] is True
