"""Tests for the VPN service (NordVPN REST-API based, no CLI)."""

from unittest.mock import MagicMock, patch

from backend.services.vpn_service import get_vpn_status


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
