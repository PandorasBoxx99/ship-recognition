"""Local no-auth SOCKS5 bridge that upstreams to an authenticated SOCKS5 proxy.

Chromium (and therefore Playwright) can use a SOCKS5 proxy, but NOT one that
requires username/password authentication. NordVPN's SOCKS5 proxies need auth.

This bridge listens on 127.0.0.1 WITHOUT authentication and forwards every
connection to the upstream NordVPN proxy WITH the service credentials. The
headless browser points at the local bridge, so its traffic (page navigation
and image downloads) is tunneled through NordVPN too.

Only loopback is bound, so the unauthenticated entry point is never exposed
to the network.
"""

import select
import socket
import struct
import threading

import socks
import structlog

log = structlog.get_logger()

_RELAY_BUF = 8192
_UPSTREAM_TIMEOUT = 30


class Socks5Bridge:
    """A loopback SOCKS5 server that relays to an authenticated upstream proxy."""

    def __init__(self, up_host: str, up_port: int, up_user: str, up_pass: str):
        self._up = (up_host, up_port, up_user, up_pass)
        self._server: socket.socket | None = None
        self._running = False
        self.port: int | None = None

    def start(self) -> int:
        """Bind to a free loopback port, begin accepting, and return the port."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(50)
        self.port = self._server.getsockname()[1]
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        log.info("socks_bridge_started", port=self.port, upstream=self._up[0])
        return self.port

    def stop(self) -> None:
        """Stop accepting and close the listening socket."""
        self._running = False
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None
        log.info("socks_bridge_stopped", port=self.port)

    def _accept_loop(self) -> None:
        while self._running and self._server:
            try:
                client, _ = self._server.accept()
            except OSError:
                break  # server socket closed by stop()
            threading.Thread(target=self._handle, args=(client,), daemon=True).start()

    def _handle(self, client: socket.socket) -> None:
        upstream = None
        try:
            # --- SOCKS5 greeting: accept "no authentication" ---
            client.recv(1)  # version byte
            n_methods = client.recv(1)[0]
            client.recv(n_methods)  # discard offered methods
            client.sendall(b"\x05\x00")

            # --- CONNECT request ---
            header = client.recv(4)
            if len(header) < 4:
                return
            _, cmd, _, atyp = header
            if cmd != 0x01:  # only CONNECT
                client.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                return
            if atyp == 0x01:  # IPv4
                host = socket.inet_ntoa(client.recv(4))
            elif atyp == 0x03:  # domain name (already ASCII/punycode)
                length = client.recv(1)[0]
                host = client.recv(length).decode("ascii", "ignore")
            elif atyp == 0x04:  # IPv6
                host = socket.inet_ntop(socket.AF_INET6, client.recv(16))
            else:
                client.sendall(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
                return
            port = struct.unpack(">H", client.recv(2))[0]

            # --- open authenticated upstream connection ---
            up_host, up_port, up_user, up_pass = self._up
            upstream = socks.socksocket()
            upstream.set_proxy(
                socks.SOCKS5, up_host, up_port,
                username=up_user, password=up_pass, rdns=True,
            )
            upstream.settimeout(_UPSTREAM_TIMEOUT)
            upstream.connect((host, port))

            # success reply (bound address is irrelevant for CONNECT)
            client.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            self._relay(client, upstream)
        except Exception as e:
            log.warning("socks_bridge_conn_error", error=str(e))
        finally:
            for sock in (upstream, client):
                if sock:
                    try:
                        sock.close()
                    except OSError:
                        pass

    @staticmethod
    def _relay(a: socket.socket, b: socket.socket) -> None:
        """Pump bytes between two sockets until either side closes."""
        pair = [a, b]
        while True:
            readable, _, _ = select.select(pair, [], [], 60)
            if not readable:
                break
            for src in readable:
                data = src.recv(_RELAY_BUF)
                if not data:
                    return
                (b if src is a else a).sendall(data)
