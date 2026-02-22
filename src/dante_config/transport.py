"""Async UDP transport for Dante protocol communication."""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
from typing import Any

from .exceptions import DanteConnectionError

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 2.0


class DanteUDPProtocol(asyncio.DatagramProtocol):
    """asyncio DatagramProtocol for Dante UDP communication.

    ARC (port 8800): matches responses by seq_id via pending futures.
    Settings (port 8700): uses a single default waiter (serialized per device).
    """

    def __init__(self, port: int) -> None:
        self.port = port
        self.transport: asyncio.DatagramTransport | None = None
        self._pending: dict[int, asyncio.Future[bytes]] = {}
        self._default_waiter: asyncio.Future[bytes] | None = None
        self._closed = False

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        if len(data) < 8:
            return

        # ARC responses: match by seq_id (bytes 4-5)
        # Accept both 0x27 (legacy) and 0x28 (current) magic bytes
        if data[0] in (0x27, 0x28):
            seq_id = int.from_bytes(data[4:6], "big")
            future = self._pending.pop(seq_id, None)
            if future and not future.done():
                future.set_result(data)
                return

        # Settings responses or any unmatched: deliver to default waiter
        if self._default_waiter and not self._default_waiter.done():
            self._default_waiter.set_result(data)
            return

    def error_received(self, exc: Exception) -> None:
        _LOGGER.debug("UDP error on port %d: %s", self.port, exc)

    def connection_lost(self, exc: Exception | None) -> None:
        self._closed = True
        # Cancel all pending futures
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        if self._default_waiter and not self._default_waiter.done():
            self._default_waiter.cancel()

    async def send_and_receive(
        self,
        frame: bytes,
        seq_id: int | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> bytes | None:
        """Send a frame and wait for the matching response.

        For ARC frames, seq_id is used to match the response.
        For Settings frames, a single default waiter is used.
        """
        if self.transport is None or self._closed:
            raise DanteConnectionError("Transport not connected")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[bytes] = loop.create_future()

        if seq_id is not None:
            self._pending[seq_id] = future
        else:
            # Settings: serialize — wait for any prior waiter
            if self._default_waiter and not self._default_waiter.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self._default_waiter), timeout=timeout
                    )
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    pass
            self._default_waiter = future

        try:
            self.transport.sendto(frame)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout waiting for response on port %d", self.port)
            return None
        except asyncio.CancelledError:
            return None
        finally:
            if seq_id is not None:
                self._pending.pop(seq_id, None)

    def send_only(self, frame: bytes) -> None:
        """Send a frame without waiting for a response."""
        if self.transport is None or self._closed:
            raise DanteConnectionError("Transport not connected")
        self.transport.sendto(frame)

    def close(self) -> None:
        """Close the transport."""
        self._closed = True
        if self.transport:
            self.transport.close()
            self.transport = None


async def create_dante_transport(
    host: str,
    port: int,
    loop: asyncio.AbstractEventLoop | None = None,
) -> tuple[asyncio.DatagramTransport, DanteUDPProtocol]:
    """Create a connected UDP transport to a Dante device."""
    if loop is None:
        loop = asyncio.get_running_loop()

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DanteUDPProtocol(port),
        remote_addr=(host, port),
    )
    return transport, protocol


class DanteMulticastProtocol(asyncio.DatagramProtocol):
    """Receives multicast Settings responses and delivers to a delegate protocol."""

    def __init__(self, delegate: DanteUDPProtocol, expected_host: str) -> None:
        self.delegate = delegate
        self.expected_host = expected_host
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str | Any, int]) -> None:
        if len(data) < 4:
            return
        # Only accept responses from the device we're talking to
        if addr[0] != self.expected_host:
            return
        # Settings responses have 0xFFFF magic
        if data[0] == 0xFF and data[1] == 0xFF:
            if (
                self.delegate._default_waiter
                and not self.delegate._default_waiter.done()
            ):
                self.delegate._default_waiter.set_result(data)

    def error_received(self, exc: Exception) -> None:
        _LOGGER.debug("Multicast UDP error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        pass

    def close(self) -> None:
        if self.transport:
            self.transport.close()
            self.transport = None


async def create_multicast_listener(
    group: str,
    port: int,
    delegate: DanteUDPProtocol,
    expected_host: str,
    loop: asyncio.AbstractEventLoop | None = None,
) -> tuple[asyncio.DatagramTransport, DanteMulticastProtocol]:
    """Create a multicast listener that delivers to a delegate protocol."""
    if loop is None:
        loop = asyncio.get_running_loop()

    # Create a UDP socket bound to the multicast port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", port))

    # Join the multicast group
    mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton("0.0.0.0"))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.setblocking(False)

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DanteMulticastProtocol(delegate, expected_host),
        sock=sock,
    )
    return transport, protocol
