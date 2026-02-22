"""High-level async API for controlling a single Dante device."""

from __future__ import annotations

import asyncio
import logging

from .const import (
    MULTICAST_GROUP_SETTINGS,
    PORT_ARC,
    PORT_SETTINGS,
    PORT_SETTINGS_MCAST,
)
from .exceptions import DanteConnectionError, DanteTimeoutError
from .models import DanteChannel, DanteDeviceInfo, DanteSubscription
from .protocol import arc, settings
from .transport import (
    DanteMulticastProtocol,
    DanteUDPProtocol,
    create_dante_transport,
    create_multicast_listener,
)

_LOGGER = logging.getLogger(__name__)


class DanteClient:
    """Async client for a single Dante device.

    Usage::

        client = DanteClient("192.168.1.100", mac_address="aabbccddeeff")
        await client.connect()
        info = await client.get_full_state()
        await client.close()
    """

    def __init__(
        self,
        host: str,
        mac_address: str | None = None,
        arc_port: int | None = None,
    ) -> None:
        self.host = host
        self.mac_address = mac_address or ""
        self.arc_port = arc_port if arc_port is not None else PORT_ARC
        self._arc_protocol: DanteUDPProtocol | None = None
        self._settings_protocol: DanteUDPProtocol | None = None
        self._mcast_protocol: DanteMulticastProtocol | None = None
        self._arc_transport: asyncio.DatagramTransport | None = None
        self._settings_transport: asyncio.DatagramTransport | None = None
        self._mcast_transport: asyncio.DatagramTransport | None = None

    async def connect(self) -> None:
        """Create UDP endpoints for ARC, Settings (8700), and multicast (8702)."""
        self._arc_transport, self._arc_protocol = await create_dante_transport(
            self.host, self.arc_port
        )
        (
            self._settings_transport,
            self._settings_protocol,
        ) = await create_dante_transport(self.host, PORT_SETTINGS)
        (
            self._mcast_transport,
            self._mcast_protocol,
        ) = await create_multicast_listener(
            MULTICAST_GROUP_SETTINGS,
            PORT_SETTINGS_MCAST,
            self._settings_protocol,
            self.host,
        )

    async def close(self) -> None:
        """Close all UDP endpoints."""
        if self._mcast_protocol:
            self._mcast_protocol.close()
            self._mcast_protocol = None
            self._mcast_transport = None
        if self._arc_protocol:
            self._arc_protocol.close()
            self._arc_protocol = None
            self._arc_transport = None
        if self._settings_protocol:
            self._settings_protocol.close()
            self._settings_protocol = None
            self._settings_transport = None

    @property
    def is_connected(self) -> bool:
        return self._arc_protocol is not None and self._settings_protocol is not None

    # -------------------------------------------------------------------
    # ARC helpers
    # -------------------------------------------------------------------

    async def _arc_command(
        self, frame: bytes, seq_id: int, timeout: float = 2.0
    ) -> bytes | None:
        if not self._arc_protocol:
            raise DanteConnectionError("Not connected")
        return await self._arc_protocol.send_and_receive(
            frame, seq_id=seq_id, timeout=timeout
        )

    async def _settings_command(
        self, frame: bytes, timeout: float = 2.0
    ) -> bytes | None:
        if not self._settings_protocol:
            raise DanteConnectionError("Not connected")
        return await self._settings_protocol.send_and_receive(frame, timeout=timeout)

    # -------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------

    async def get_device_name(self) -> str:
        """Query the device name."""
        frame, seq_id = arc.build_device_name_query()
        response = await self._arc_command(frame, seq_id)
        if response is None:
            raise DanteTimeoutError("Device name query timed out")
        return arc.parse_device_name(response)

    async def get_channel_counts(self) -> tuple[int, int]:
        """Query TX and RX channel counts. Returns (tx_count, rx_count)."""
        frame, seq_id = arc.build_channel_count_query()
        response = await self._arc_command(frame, seq_id)
        if response is None:
            raise DanteTimeoutError("Channel count query timed out")
        return arc.parse_channel_counts(response)

    async def get_tx_channels(
        self, tx_count: int | None = None
    ) -> tuple[dict[int, DanteChannel], int]:
        """Query all TX channels with pagination.

        Returns (channels_dict, sample_rate).
        """
        if tx_count is None:
            tx_count, _ = await self.get_channel_counts()

        all_channels: dict[int, DanteChannel] = {}
        sample_rate = 0

        # First pass: get friendly names
        all_friendly_names: dict[int, str] = {}
        for page in range(0, max(1, (tx_count + 15) // 16), 2):
            frame, seq_id = arc.build_tx_friendly_names_query(page)
            response = await self._arc_command(frame, seq_id)
            if response:
                names = arc.parse_tx_friendly_names(response)
                all_friendly_names.update(names)

        # Second pass: get channel details
        for page in range(0, max(1, (tx_count + 15) // 16), 2):
            frame, seq_id = arc.build_tx_channels_query(page)
            response = await self._arc_command(frame, seq_id)
            if response:
                channels, sr = arc.parse_tx_channels(
                    response, tx_count, all_friendly_names
                )
                all_channels.update(channels)
                if sr:
                    sample_rate = sr

        return all_channels, sample_rate

    async def get_rx_channels(
        self, device_name: str | None = None, rx_count: int | None = None
    ) -> tuple[dict[int, DanteChannel], list[DanteSubscription], int]:
        """Query all RX channels with pagination.

        Returns (channels_dict, subscriptions_list, sample_rate).
        """
        if device_name is None:
            device_name = await self.get_device_name()
        if rx_count is None:
            _, rx_count = await self.get_channel_counts()

        all_channels: dict[int, DanteChannel] = {}
        all_subscriptions: list[DanteSubscription] = []
        sample_rate = 0

        for page in range(0, max(1, (rx_count + 15) // 16)):
            frame, seq_id = arc.build_rx_channels_query(page)
            response = await self._arc_command(frame, seq_id)
            if response:
                channels, subs, sr = arc.parse_rx_channels(
                    response, device_name, rx_count
                )
                all_channels.update(channels)
                all_subscriptions.extend(subs)
                if sr:
                    sample_rate = sr

        return all_channels, all_subscriptions, sample_rate

    async def get_dante_model(self) -> tuple[str, str]:
        """Query the Dante model. Returns (model_id, model)."""
        frame = settings.build_dante_model_query()
        response = await self._settings_command(frame)
        if response is None:
            return "", ""
        return settings.parse_dante_model(response)

    async def get_manufacturer(self) -> tuple[str, str]:
        """Query the manufacturer. Returns (manufacturer, model)."""
        frame = settings.build_manufacturer_query()
        response = await self._settings_command(frame)
        if response is None:
            return "", ""
        return settings.parse_manufacturer(response)

    async def get_full_state(self) -> DanteDeviceInfo:
        """Query all device state and return a DanteDeviceInfo snapshot."""
        device_name = await self.get_device_name()
        tx_count, rx_count = await self.get_channel_counts()

        tx_channels, tx_sample_rate = await self.get_tx_channels(tx_count)
        rx_channels, subscriptions, rx_sample_rate = await self.get_rx_channels(
            device_name, rx_count
        )

        sample_rate = rx_sample_rate or tx_sample_rate

        model_id, dante_model = await self.get_dante_model()
        manufacturer, model = await self.get_manufacturer()

        return DanteDeviceInfo(
            name=device_name,
            ipv4=self.host,
            mac_address=self.mac_address,
            model_id=model_id,
            model=model,
            manufacturer=manufacturer,
            dante_model=dante_model,
            sample_rate=sample_rate,
            tx_count=tx_count,
            rx_count=rx_count,
            tx_channels=tx_channels,
            rx_channels=rx_channels,
            subscriptions=subscriptions,
        )

    # -------------------------------------------------------------------
    # Control Methods
    # -------------------------------------------------------------------

    async def identify(self) -> None:
        """Flash the device LED for identification."""
        frame = settings.build_identify(self.mac_address or None)
        await self._settings_command(frame)

    async def set_device_name(self, name: str) -> None:
        """Set the device name."""
        frame, seq_id = arc.build_set_device_name(name)
        await self._arc_command(frame, seq_id)

    async def reset_device_name(self) -> None:
        """Reset device name to factory default."""
        frame, seq_id = arc.build_reset_device_name()
        await self._arc_command(frame, seq_id)

    async def set_sample_rate(self, sample_rate: int) -> None:
        """Set the device sample rate (e.g. 48000, 96000)."""
        frame = settings.build_set_sample_rate(sample_rate)
        await self._settings_command(frame)

    async def set_encoding(self, encoding: int) -> None:
        """Set the audio encoding (use Encoding enum values)."""
        frame = settings.build_set_encoding(encoding)
        await self._settings_command(frame)

    async def set_latency(self, latency_us: int) -> None:
        """Set the device latency in microseconds."""
        frame, seq_id = arc.build_set_latency(latency_us)
        await self._arc_command(frame, seq_id)

    async def set_aes67(self, enabled: bool) -> None:
        """Enable or disable AES67 mode."""
        frame = settings.build_set_aes67(enabled, self.mac_address or None)
        await self._settings_command(frame)

    async def reboot(self) -> None:
        """Reboot the device. NOT YET WIRE-CONFIRMED."""
        if not self.mac_address:
            raise DanteConnectionError("MAC address required for reboot")
        frame = settings.build_reboot(self.mac_address)
        # Send without waiting for response — device will go offline
        if self._settings_protocol:
            self._settings_protocol.send_only(frame)

    async def add_subscription(
        self,
        rx_channel_number: int,
        tx_channel_name: str,
        tx_device_name: str,
    ) -> None:
        """Subscribe an RX channel to a TX channel on another device."""
        frame, seq_id = arc.build_add_subscription(
            rx_channel_number, tx_channel_name, tx_device_name
        )
        await self._arc_command(frame, seq_id)

    async def remove_subscription(self, rx_channel_number: int) -> None:
        """Remove a subscription from an RX channel."""
        frame, seq_id = arc.build_remove_subscription(rx_channel_number)
        await self._arc_command(frame, seq_id)

    async def set_tx_channel_name(self, channel_number: int, name: str) -> None:
        """Set a TX channel's name."""
        frame, seq_id = arc.build_set_tx_channel_name(channel_number, name)
        await self._arc_command(frame, seq_id)

    async def set_rx_channel_name(self, channel_number: int, name: str) -> None:
        """Set an RX channel's name."""
        frame, seq_id = arc.build_set_rx_channel_name(channel_number, name)
        await self._arc_command(frame, seq_id)

    async def reset_tx_channel_name(self, channel_number: int) -> None:
        """Reset a TX channel's name to default."""
        frame, seq_id = arc.build_reset_tx_channel_name(channel_number)
        await self._arc_command(frame, seq_id)

    async def reset_rx_channel_name(self, channel_number: int) -> None:
        """Reset an RX channel's name to default."""
        frame, seq_id = arc.build_reset_rx_channel_name(channel_number)
        await self._arc_command(frame, seq_id)
