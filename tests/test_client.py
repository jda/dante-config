"""Integration tests for DanteClient with mocked transport."""

import struct
from unittest.mock import MagicMock, patch

import pytest

from dante_config.client import DanteClient
from dante_config.const import ArcCommand
from dante_config.exceptions import DanteConnectionError, DanteTimeoutError
from dante_config.transport import DanteUDPProtocol


def _make_arc_response(seq_id: int, payload: bytes) -> bytes:
    """Build a mock ARC response frame."""
    header = struct.pack(">BBBHH", 0x27, 0xFF, 0x00, 0, seq_id)
    frame = bytearray(header + payload)
    frame[3] = len(frame)
    return bytes(frame)


def _make_name_response(seq_id: int, name: str) -> bytes:
    """Build a mock device name response."""
    # Response format: 10 bytes header + name + null
    header = bytearray(10)
    header[0] = 0x27
    header[1] = 0xFF
    header[4:6] = struct.pack(">H", seq_id)
    header[6:8] = struct.pack(">H", ArcCommand.DEVICE_NAME)
    return bytes(header) + name.encode("ascii") + b"\x00"


def _make_channel_count_response(seq_id: int, tx: int, rx: int) -> bytes:
    """Build a mock channel count response."""
    response = bytearray(16)
    response[0] = 0x27
    response[1] = 0xFF
    response[4:6] = struct.pack(">H", seq_id)
    response[13] = tx
    response[15] = rx
    return bytes(response)


@pytest.fixture
def mock_protocol() -> DanteUDPProtocol:
    """Create a mock protocol."""
    proto = DanteUDPProtocol(8800)
    proto.transport = MagicMock()
    return proto


class TestDanteClientConnection:
    """Test client connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_creates_transports(self) -> None:
        with patch("dante_config.client.create_dante_transport") as mock_create:
            mock_transport = MagicMock()
            mock_proto = DanteUDPProtocol(8800)
            mock_create.return_value = (mock_transport, mock_proto)

            client = DanteClient("192.168.1.1")
            await client.connect()

            assert client.is_connected
            assert mock_create.call_count == 2  # ARC + Settings

    @pytest.mark.asyncio
    async def test_close_cleans_up(self) -> None:
        with patch("dante_config.client.create_dante_transport") as mock_create:
            mock_transport = MagicMock()
            mock_proto = MagicMock(spec=DanteUDPProtocol)
            mock_create.return_value = (mock_transport, mock_proto)

            client = DanteClient("192.168.1.1")
            await client.connect()
            await client.close()

            assert not client.is_connected

    @pytest.mark.asyncio
    async def test_command_without_connect_raises(self) -> None:
        client = DanteClient("192.168.1.1")
        with pytest.raises(DanteConnectionError):
            await client.get_device_name()


class TestDanteClientQueries:
    """Test client query methods with mocked responses."""

    @pytest.mark.asyncio
    async def test_get_device_name(self) -> None:
        client = DanteClient("192.168.1.1", mac_address="001122334455")

        mock_proto = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(frame, seq_id=None, timeout=2.0):
            return _make_name_response(seq_id, "TestDevice")

        mock_proto.send_and_receive = mock_send

        client._arc_protocol = mock_proto
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        name = await client.get_device_name()
        assert name == "TestDevice"

    @pytest.mark.asyncio
    async def test_get_channel_counts(self) -> None:
        client = DanteClient("192.168.1.1")
        mock_proto = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(frame, seq_id=None, timeout=2.0):
            return _make_channel_count_response(seq_id, 8, 4)

        mock_proto.send_and_receive = mock_send
        client._arc_protocol = mock_proto
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        tx, rx = await client.get_channel_counts()
        assert tx == 8
        assert rx == 4

    @pytest.mark.asyncio
    async def test_get_device_name_timeout(self) -> None:
        client = DanteClient("192.168.1.1")
        mock_proto = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(frame, seq_id=None, timeout=2.0):
            return None  # simulate timeout

        mock_proto.send_and_receive = mock_send
        client._arc_protocol = mock_proto
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        with pytest.raises(DanteTimeoutError):
            await client.get_device_name()


class TestDanteClientControl:
    """Test client control methods."""

    @pytest.mark.asyncio
    async def test_identify(self) -> None:
        client = DanteClient("192.168.1.1", mac_address="aabbccddeeff")
        mock_settings = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(frame, timeout=2.0):
            return b"\xff\xff\x00\x20"  # minimal response

        mock_settings.send_and_receive = mock_send
        client._arc_protocol = MagicMock(spec=DanteUDPProtocol)
        client._settings_protocol = mock_settings

        await client.identify()  # should not raise

    @pytest.mark.asyncio
    async def test_reboot_without_mac_raises(self) -> None:
        client = DanteClient("192.168.1.1")
        client._arc_protocol = MagicMock(spec=DanteUDPProtocol)
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        with pytest.raises(DanteConnectionError, match="MAC"):
            await client.reboot()

    @pytest.mark.asyncio
    async def test_add_subscription(self) -> None:
        client = DanteClient("192.168.1.1")
        mock_arc = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(frame, seq_id=None, timeout=2.0):
            return _make_arc_response(seq_id, b"\x00\x00")

        mock_arc.send_and_receive = mock_send
        client._arc_protocol = mock_arc
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        await client.add_subscription(1, "TX-01", "SenderDevice")
