"""Tests for VPN service."""

from unittest.mock import MagicMock, patch

from backend.services.vpn_service import get_vpn_status


@patch("backend.services.vpn_service.subprocess")
def test_get_status_connected(mock_sub):
    mock_result = MagicMock()
    mock_result.stdout = "Status: Connected\nCountry: Germany\nServer IP: 10.0.0.1\n"
    mock_sub.run.return_value = mock_result

    status = get_vpn_status()
    assert status["connected"] is True
    assert status["country"] == "Germany"
    assert status["ip"] == "10.0.0.1"


@patch("backend.services.vpn_service.subprocess")
def test_get_status_disconnected(mock_sub):
    mock_result = MagicMock()
    mock_result.stdout = "Status: Disconnected\n"
    mock_sub.run.return_value = mock_result

    status = get_vpn_status()
    assert status["connected"] is False
    assert status["country"] is None


@patch("backend.services.vpn_service.subprocess")
def test_get_status_german_output(mock_sub):
    mock_result = MagicMock()
    mock_result.stdout = "Status: Verbunden\nLand: Deutschland\nIP: 10.0.0.2\n"
    mock_sub.run.return_value = mock_result

    status = get_vpn_status()
    assert status["connected"] is True
    assert status["country"] == "Deutschland"


@patch("backend.services.vpn_service.subprocess")
def test_get_status_timeout(mock_sub):
    mock_sub.run.side_effect = Exception("Command timed out")

    status = get_vpn_status()
    assert status["connected"] is False
    assert "error" in status


@patch("backend.services.vpn_service.settings")
def test_disabled_vpn(mock_settings):
    mock_settings.VPN_ENABLED = False

    status = get_vpn_status()
    assert status["connected"] is False
    assert "disabled" in status["error"].lower()
