"""Unit tests for transport layer (DanteUDPProtocol, DanteMulticastProtocol)."""

from __future__ import annotations

import asyncio
import struct
from unittest.mock import MagicMock

import pytest

from dante_config.const import ARC_FLAGS, ARC_MAGIC, PORT_ARC
from dante_config.transport import DanteMulticastProtocol, DanteUDPProtocol

# ---------------------------------------------------------------------------
# DanteUDPProtocol — backward compatibility
# ---------------------------------------------------------------------------


class TestDanteUDPProtocolMagicBytes:
    """Verify both legacy (0x27) and current (0x28) magic bytes are accepted."""

    @pytest.mark.asyncio
    async def test_current_magic_delivers_response(self) -> None:
        proto = DanteUDPProtocol(PORT_ARC)
        proto.transport = MagicMock()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bytes] = loop.create_future()
        proto._pending[0x1234] = future

        # BBBBHH = magic, flags, reserved, length, seq_id, command
        frame = struct.pack(">BBBBHH", ARC_MAGIC, ARC_FLAGS, 0x00, 8, 0x1234, 0x1000)
        proto.datagram_received(frame, ("192.168.1.1", PORT_ARC))

        assert future.done()
        assert future.result() == frame

    @pytest.mark.asyncio
    async def test_legacy_magic_delivers_response(self) -> None:
        proto = DanteUDPProtocol(PORT_ARC)
        proto.transport = MagicMock()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bytes] = loop.create_future()
        proto._pending[0x5678] = future

        # Legacy magic 0x27 with old flags 0xFF
        frame = struct.pack(">BBBBHH", 0x27, 0xFF, 0x00, 8, 0x5678, 0x1000)
        proto.datagram_received(frame, ("192.168.1.1", PORT_ARC))

        assert future.done()
        assert future.result() == frame


class TestDeliverResponse:
    """Test the public deliver_response() method."""

    @pytest.mark.asyncio
    async def test_delivers_when_waiter_present(self) -> None:
        proto = DanteUDPProtocol(8700)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bytes] = loop.create_future()
        proto._default_waiter = future

        data = b"\xff\xff\x00\x20" + b"\x00" * 28
        assert proto.deliver_response(data) is True
        assert future.done()
        assert future.result() == data

    def test_returns_false_when_no_waiter(self) -> None:
        proto = DanteUDPProtocol(8700)
        data = b"\xff\xff\x00\x20" + b"\x00" * 28
        assert proto.deliver_response(data) is False


# ---------------------------------------------------------------------------
# DanteMulticastProtocol
# ---------------------------------------------------------------------------


class TestDanteMulticastProtocol:
    """Test multicast protocol filtering and delegation."""

    @staticmethod
    async def _make_protocol_pair() -> tuple[DanteMulticastProtocol, DanteUDPProtocol]:
        loop = asyncio.get_running_loop()
        delegate = DanteUDPProtocol(8700)
        delegate.transport = MagicMock()
        waiter: asyncio.Future[bytes] = loop.create_future()
        delegate._default_waiter = waiter
        mreq = b"\x00" * 8  # dummy mreq for tests
        mcast = DanteMulticastProtocol(delegate, "10.8.2.25", mreq)
        mcast.transport = MagicMock()
        return mcast, delegate

    @pytest.mark.asyncio
    async def test_valid_settings_response_delivered(self) -> None:
        mcast, delegate = await self._make_protocol_pair()
        data = b"\xff\xff\x00\x20" + b"\x00" * 28
        mcast.datagram_received(data, ("10.8.2.25", 8702))

        assert delegate._default_waiter is not None
        assert delegate._default_waiter.done()
        assert delegate._default_waiter.result() == data

    @pytest.mark.asyncio
    async def test_wrong_source_host_dropped(self) -> None:
        mcast, delegate = await self._make_protocol_pair()
        data = b"\xff\xff\x00\x20" + b"\x00" * 28
        mcast.datagram_received(data, ("10.8.2.99", 8702))

        assert delegate._default_waiter is not None
        assert not delegate._default_waiter.done()

    @pytest.mark.asyncio
    async def test_non_settings_magic_dropped(self) -> None:
        mcast, delegate = await self._make_protocol_pair()
        # ARC magic, not settings
        data = b"\x28\x09\x00\x0a" + b"\x00" * 6
        mcast.datagram_received(data, ("10.8.2.25", 8702))

        assert delegate._default_waiter is not None
        assert not delegate._default_waiter.done()

    @pytest.mark.asyncio
    async def test_short_datagram_dropped(self) -> None:
        mcast, delegate = await self._make_protocol_pair()
        mcast.datagram_received(b"\xff\xff", ("10.8.2.25", 8702))

        assert delegate._default_waiter is not None
        assert not delegate._default_waiter.done()

    @pytest.mark.asyncio
    async def test_no_waiter_does_not_crash(self) -> None:
        delegate = DanteUDPProtocol(8700)
        delegate.transport = MagicMock()
        # No waiter set
        mreq = b"\x00" * 8
        mcast = DanteMulticastProtocol(delegate, "10.8.2.25", mreq)
        mcast.transport = MagicMock()

        data = b"\xff\xff\x00\x20" + b"\x00" * 28
        mcast.datagram_received(data, ("10.8.2.25", 8702))  # should not raise
