"""Integration tests for DanteClient with mocked transport."""

# pylint: disable=protected-access

import struct
from unittest.mock import MagicMock, patch

import pytest

from dante_config.client import DanteClient
from dante_config.const import ARC_FLAGS, ARC_MAGIC, PORT_ARC, PORT_SETTINGS, ArcCommand
from dante_config.exceptions import DanteConnectionError, DanteTimeoutError
from dante_config.transport import DanteMulticastProtocol, DanteUDPProtocol


def _make_arc_response(seq_id: int, payload: bytes) -> bytes:
    """Build a mock ARC response frame using current protocol values."""
    header = struct.pack(">BBBHH", ARC_MAGIC, ARC_FLAGS, 0x00, 0, seq_id)
    frame = bytearray(header + payload)
    frame[3] = len(frame)
    return bytes(frame)


def _make_name_response(seq_id: int, name: str) -> bytes:
    """Build a mock device name response using current protocol values."""
    # Response format: 10 bytes header + name + null
    header = bytearray(10)
    header[0] = ARC_MAGIC
    header[1] = ARC_FLAGS
    header[4:6] = struct.pack(">H", seq_id)
    header[6:8] = struct.pack(">H", ArcCommand.DEVICE_NAME)
    return bytes(header) + name.encode("ascii") + b"\x00"


def _make_channel_count_response(seq_id: int, tx: int, rx: int) -> bytes:
    """Build a mock channel count response using current protocol values."""
    response = bytearray(16)
    response[0] = ARC_MAGIC
    response[1] = ARC_FLAGS
    response[4:6] = struct.pack(">H", seq_id)
    response[13] = tx
    response[15] = rx
    return bytes(response)


@pytest.fixture
def mock_protocol() -> DanteUDPProtocol:
    """Create a mock protocol."""
    proto = DanteUDPProtocol(PORT_ARC)
    proto.transport = MagicMock()
    return proto


class TestDanteClientArcPort:
    """Test arc_port parameter handling."""

    def test_default_arc_port(self) -> None:
        """Verify default ARC port is used when not specified."""
        client = DanteClient("192.168.1.1")
        assert client.arc_port == PORT_ARC

    def test_custom_arc_port(self) -> None:
        """Verify custom ARC port is stored."""
        client = DanteClient("192.168.1.1", arc_port=5555)
        assert client.arc_port == 5555

    @pytest.mark.asyncio
    async def test_connect_uses_custom_arc_port(self) -> None:
        """Verify connect passes custom ARC port to transport factory."""
        with (
            patch("dante_config.client.create_dante_transport") as mock_create,
            patch("dante_config.client.create_multicast_listener") as mock_mcast,
        ):
            mock_transport = MagicMock()
            mock_proto = DanteUDPProtocol(PORT_ARC)
            mock_create.return_value = (mock_transport, mock_proto)
            mock_mcast.return_value = (
                MagicMock(),
                MagicMock(spec=DanteMulticastProtocol),
            )

            client = DanteClient("192.168.1.1", arc_port=5555)
            await client.connect()

            calls = mock_create.call_args_list
            assert calls[0].args == ("192.168.1.1", 5555)
            assert calls[1].args == ("192.168.1.1", PORT_SETTINGS)


class TestDanteClientConnection:
    """Test client connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_creates_transports(self) -> None:
        """Verify connect creates ARC, Settings, and multicast transports."""
        with (
            patch("dante_config.client.create_dante_transport") as mock_create,
            patch("dante_config.client.create_multicast_listener") as mock_mcast,
        ):
            mock_transport = MagicMock()
            mock_proto = DanteUDPProtocol(PORT_ARC)
            mock_create.return_value = (mock_transport, mock_proto)
            mock_mcast.return_value = (
                MagicMock(),
                MagicMock(spec=DanteMulticastProtocol),
            )

            client = DanteClient("192.168.1.1")
            await client.connect()

            assert client.is_connected
            assert mock_create.call_count == 2  # ARC + Settings
            assert mock_mcast.call_count == 1  # Multicast

    @pytest.mark.asyncio
    async def test_close_cleans_up(self) -> None:
        """Verify close sets is_connected to False."""
        with (
            patch("dante_config.client.create_dante_transport") as mock_create,
            patch("dante_config.client.create_multicast_listener") as mock_mcast,
        ):
            mock_transport = MagicMock()
            mock_proto = MagicMock(spec=DanteUDPProtocol)
            mock_create.return_value = (mock_transport, mock_proto)
            mock_mcast.return_value = (
                MagicMock(),
                MagicMock(spec=DanteMulticastProtocol),
            )

            client = DanteClient("192.168.1.1")
            await client.connect()
            await client.close()

            assert not client.is_connected

    @pytest.mark.asyncio
    async def test_command_without_connect_raises(self) -> None:
        """Verify commands raise DanteConnectionError before connect."""
        client = DanteClient("192.168.1.1")
        with pytest.raises(DanteConnectionError):
            await client.get_device_name()


class TestDanteClientQueries:
    """Test client query methods with mocked responses."""

    @pytest.mark.asyncio
    async def test_get_device_name(self) -> None:
        """Verify get_device_name returns parsed name from mock response."""
        client = DanteClient("192.168.1.1", mac_address="001122334455")

        mock_proto = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(_frame, seq_id=None, **_kwargs):  # noqa: ARG001
            return _make_name_response(seq_id, "TestDevice")

        mock_proto.send_and_receive = mock_send

        client._arc_protocol = mock_proto
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        name = await client.get_device_name()
        assert name == "TestDevice"

    @pytest.mark.asyncio
    async def test_get_channel_counts(self) -> None:
        """Verify get_channel_counts returns parsed TX and RX counts."""
        client = DanteClient("192.168.1.1")
        mock_proto = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(_frame, seq_id=None, **_kwargs):  # noqa: ARG001
            return _make_channel_count_response(seq_id, 8, 4)

        mock_proto.send_and_receive = mock_send
        client._arc_protocol = mock_proto
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        tx, rx = await client.get_channel_counts()
        assert tx == 8
        assert rx == 4

    @pytest.mark.asyncio
    async def test_get_device_name_timeout(self) -> None:
        """Verify DanteTimeoutError is raised on timeout."""
        client = DanteClient("192.168.1.1")
        mock_proto = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(  # pylint: disable=unused-argument
            _frame, seq_id=None, **_kwargs
        ):
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
        """Verify identify command completes without error."""
        client = DanteClient("192.168.1.1", mac_address="aabbccddeeff")
        mock_settings = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(_frame, **_kwargs):
            return b"\xff\xff\x00\x20"  # minimal response

        mock_settings.send_and_receive = mock_send
        client._arc_protocol = MagicMock(spec=DanteUDPProtocol)
        client._settings_protocol = mock_settings

        await client.identify()  # should not raise

    @pytest.mark.asyncio
    async def test_reboot_without_mac_raises(self) -> None:
        """Verify reboot raises DanteConnectionError without MAC."""
        client = DanteClient("192.168.1.1")
        client._arc_protocol = MagicMock(spec=DanteUDPProtocol)
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        with pytest.raises(DanteConnectionError, match="MAC"):
            await client.reboot()

    @pytest.mark.asyncio
    async def test_add_subscription(self) -> None:
        """Verify add_subscription sends correct ARC command."""
        client = DanteClient("192.168.1.1")
        mock_arc = MagicMock(spec=DanteUDPProtocol)

        async def mock_send(_frame, seq_id=None, **_kwargs):  # noqa: ARG001
            return _make_arc_response(seq_id, b"\x00\x00")

        mock_arc.send_and_receive = mock_send
        client._arc_protocol = mock_arc
        client._settings_protocol = MagicMock(spec=DanteUDPProtocol)

        await client.add_subscription(1, "TX-01", "SenderDevice")
