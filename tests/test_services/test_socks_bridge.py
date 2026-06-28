"""Tests for the local SOCKS5 bridge (no-auth entry -> authenticated upstream)."""

import socket

from backend.services.socks_bridge import Socks5Bridge


def test_bridge_start_returns_loopback_port():
    bridge = Socks5Bridge("nl.socks.nordhold.net", 1080, "user", "pass")
    try:
        port = bridge.start()
        assert isinstance(port, int)
        assert port > 0
        assert bridge.port == port
        # bound to loopback only
        assert bridge._server.getsockname()[0] == "127.0.0.1"
    finally:
        bridge.stop()


def test_bridge_accepts_noauth_handshake():
    # Upstream is never reached: we only exercise the local no-auth handshake.
    bridge = Socks5Bridge("invalid.upstream.local", 1080, "user", "pass")
    port = bridge.start()
    try:
        client = socket.create_connection(("127.0.0.1", port), timeout=5)
        client.settimeout(5)
        # SOCKS5 greeting: version 5, one method, "no authentication" (0x00)
        client.sendall(b"\x05\x01\x00")
        reply = client.recv(2)
        assert reply == b"\x05\x00"  # server must select no-auth
        client.close()
    finally:
        bridge.stop()
