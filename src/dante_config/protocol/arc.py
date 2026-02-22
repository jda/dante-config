"""ARC protocol frame builders and response parsers (port 8800)."""

from __future__ import annotations

import struct

from ..const import ArcCommand
from ..models import DanteChannel, DanteSubscription
from .common import build_arc_frame, get_label

# ---------------------------------------------------------------------------
# Frame Builders
# ---------------------------------------------------------------------------


def build_device_name_query(seq_id: int | None = None) -> tuple[bytes, int]:
    """Build a query for the device name (0x1002)."""
    return build_arc_frame(ArcCommand.DEVICE_NAME, b"\x00\x00", seq_id)


def build_channel_count_query(seq_id: int | None = None) -> tuple[bytes, int]:
    """Build a query for TX/RX channel counts (0x1000)."""
    return build_arc_frame(ArcCommand.CHANNEL_COUNT, b"\x00\x00", seq_id)


def build_device_info_query(seq_id: int | None = None) -> tuple[bytes, int]:
    """Build a query for device info (0x1003)."""
    return build_arc_frame(ArcCommand.DEVICE_INFO, b"\x00\x00", seq_id)


def build_tx_channels_query(
    page: int = 0, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a query for TX channels (0x2000) with pagination."""
    pagination = _build_pagination(page)
    return build_arc_frame(ArcCommand.TX_CHANNELS, pagination, seq_id)


def build_tx_friendly_names_query(
    page: int = 0, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a query for TX friendly names (0x2010) with pagination."""
    pagination = _build_pagination(page)
    return build_arc_frame(ArcCommand.TX_FRIENDLY_NAMES, pagination, seq_id)


def build_rx_channels_query(
    page: int = 0, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a query for RX channels (0x3000) with pagination."""
    pagination = _build_pagination(page)
    return build_arc_frame(ArcCommand.RX_CHANNELS, pagination, seq_id)


def build_set_device_name(name: str, seq_id: int | None = None) -> tuple[bytes, int]:
    """Build a command to set the device name (0x1001)."""
    name_bytes = b"\x00\x00" + name.encode("utf-8") + b"\x00"
    return build_arc_frame(ArcCommand.SET_DEVICE_NAME, name_bytes, seq_id)


def build_reset_device_name(seq_id: int | None = None) -> tuple[bytes, int]:
    """Build a command to reset the device name to factory default (0x1001)."""
    return build_arc_frame(ArcCommand.SET_DEVICE_NAME, b"\x00\x00", seq_id)


def build_set_tx_channel_name(
    channel_number: int, name: str, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a command to set a TX channel name (0x2013)."""
    name_bytes = name.encode("utf-8")
    args = (
        b"\x00\x00\x02\x01\x00\x00\x00"
        + struct.pack(">B", channel_number)
        + b"\x00\x18\x00\x00\x00\x00\x00\x00"
        + name_bytes
        + b"\x00"
    )
    return build_arc_frame(ArcCommand.SET_TX_CHANNEL_NAME, args, seq_id)


def build_reset_tx_channel_name(
    channel_number: int, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a command to reset a TX channel name (0x2013)."""
    args = (
        b"\x00\x00\x02\x01\x00\x00\x00"
        + struct.pack(">B", channel_number)
        + b"\x00\x18\x00\x00\x00\x00\x00\x00\x00"
    )
    return build_arc_frame(ArcCommand.SET_TX_CHANNEL_NAME, args, seq_id)


def build_set_rx_channel_name(
    channel_number: int, name: str, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a command to set an RX channel name (0x3001)."""
    name_bytes = name.encode("utf-8")
    args = (
        b"\x00\x00\x02\x01\x00"
        + struct.pack(">B", channel_number)
        + b"\x00\x14\x00\x00\x00\x00"
        + name_bytes
        + b"\x00"
    )
    return build_arc_frame(ArcCommand.SET_RX_CHANNEL_NAME, args, seq_id)


def build_reset_rx_channel_name(
    channel_number: int, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a command to reset an RX channel name (0x3001)."""
    args = (
        b"\x00\x00\x02\x01\x00"
        + struct.pack(">B", channel_number)
        + b"\x00\x14\x00\x00\x00\x00\x00"
    )
    return build_arc_frame(ArcCommand.SET_RX_CHANNEL_NAME, args, seq_id)


def build_add_subscription(
    rx_channel_number: int,
    tx_channel_name: str,
    tx_device_name: str,
    seq_id: int | None = None,
) -> tuple[bytes, int]:
    """Build a command to add a subscription (0x3010)."""
    tx_ch_bytes = tx_channel_name.encode("utf-8")
    tx_dev_bytes = tx_device_name.encode("utf-8")

    tx_ch_offset = 52  # 0x34 — fixed offset
    tx_dev_offset = tx_ch_offset + len(tx_ch_bytes) + 1  # +1 for null terminator

    args = (
        b"\x00\x00\x02\x01\x00"
        + struct.pack(">B", rx_channel_number)
        + b"\x00"
        + struct.pack(">B", tx_ch_offset)
        + b"\x00"
        + struct.pack(">B", tx_dev_offset)
        + b"\x00" * 32
        + tx_ch_bytes
        + b"\x00"
        + tx_dev_bytes
        + b"\x00"
    )
    return build_arc_frame(ArcCommand.ADD_SUBSCRIPTION, args, seq_id)


def build_remove_subscription(
    rx_channel_number: int, seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build a command to remove a subscription (0x3014)."""
    args = b"\x00\x00\x00\x01\x00\x00\x00" + struct.pack(">B", rx_channel_number)
    return build_arc_frame(ArcCommand.REMOVE_SUBSCRIPTION, args, seq_id)


def build_set_latency(latency_us: int, seq_id: int | None = None) -> tuple[bytes, int]:
    """Build a command to set the device latency (0x1101).

    latency_us: latency in microseconds.
    """
    lat = struct.pack(">I", latency_us)
    args = (
        b"\x00\x00\x05\x03\x82\x05\x00\x20\x02\x11\x00\x10\x83\x01"
        b"\x00\x24\x82\x19\x83\x01\x83\x02\x83\x06" + lat + lat
    )
    return build_arc_frame(ArcCommand.SET_LATENCY, args, seq_id)


# ---------------------------------------------------------------------------
# Response Parsers
# ---------------------------------------------------------------------------


def parse_device_name(response: bytes) -> str:
    """Parse device name from a 0x1002 response."""
    return response[10:-1].decode("ascii", errors="replace").rstrip("\x00")


def parse_channel_counts(response: bytes) -> tuple[int, int]:
    """Parse TX and RX channel counts from a 0x1000 response.

    Returns (tx_count, rx_count).
    """
    tx_count = response[13]
    rx_count = response[15]
    return tx_count, rx_count


def parse_tx_channels(
    response: bytes,
    tx_count: int,
    existing_friendly_names: dict[int, str] | None = None,
) -> tuple[dict[int, DanteChannel], int]:
    """Parse TX channels from a 0x2000 response.

    Returns (channels_dict, sample_rate).
    """
    hex_str = response.hex()
    channels: dict[int, DanteChannel] = {}
    sample_rate = 0
    first_group: str | None = None

    num_entries = min(tx_count, 32)
    for i in range(num_entries):
        offset = 24 + (i * 16)
        if offset + 16 > len(hex_str):
            break

        entry = hex_str[offset : offset + 16]
        fields = [entry[j : j + 4] for j in range(0, 16, 4)]

        channel_number = int(fields[0], 16)
        if channel_number == 0:
            break

        channel_group = fields[2]
        channel_offset = fields[3]

        if first_group is None:
            first_group = channel_group

        channel_disabled = channel_group != first_group
        if channel_disabled:
            break

        # Extract sample rate from first channel
        if i == 0:
            o1 = (int(channel_group, 16) * 2) + 2
            o2 = o1 + 6
            if o2 <= len(hex_str):
                sample_rate = int(hex_str[o1:o2], 16)

        channel_name = (
            get_label(hex_str, channel_offset) if channel_offset != "0000" else ""
        )

        friendly = None
        if existing_friendly_names:
            friendly = existing_friendly_names.get(channel_number)

        channels[channel_number] = DanteChannel(
            number=channel_number,
            name=channel_name,
            channel_type="tx",
            friendly_name=friendly,
            enabled=True,
        )

    return channels, sample_rate


def parse_tx_friendly_names(response: bytes) -> dict[int, str]:
    """Parse TX friendly names from a 0x2010 response.

    Returns {channel_number: friendly_name}.
    """
    hex_str = response.hex()
    names: dict[int, str] = {}

    for i in range(32):
        offset = 24 + (i * 12)
        if offset + 12 > len(hex_str):
            break

        entry = hex_str[offset : offset + 12]
        fields = [entry[j : j + 4] for j in range(0, 12, 4)]

        channel_number = int(fields[1], 16)
        if channel_number == 0:
            break

        channel_offset = fields[2]
        if channel_offset != "0000":
            name = get_label(hex_str, channel_offset)
            if name:
                names[channel_number] = name

    return names


def parse_rx_channels(
    response: bytes,
    device_name: str,
    rx_count: int,
) -> tuple[dict[int, DanteChannel], list[DanteSubscription], int]:
    """Parse RX channels from a 0x3000 response.

    Returns (channels_dict, subscriptions_list, sample_rate).
    """
    hex_str = response.hex()
    channels: dict[int, DanteChannel] = {}
    subscriptions: list[DanteSubscription] = []
    sample_rate = 0

    num_entries = min(rx_count, 16)
    for i in range(num_entries):
        offset = 24 + (i * 40)
        if offset + 40 > len(hex_str):
            break

        entry = hex_str[offset : offset + 40]
        # 8 fields of 4 hex chars each = 32 hex chars for the fixed part
        # But entry is 40 hex chars total, so we take first 32 as 8 fields
        fields = [entry[j : j + 4] for j in range(0, 32, 4)]

        channel_number = int(fields[0], 16)
        if channel_number == 0:
            break

        info_offset = fields[2]
        tx_channel_offset = fields[3]
        tx_device_offset = fields[4]
        rx_channel_offset = fields[5]
        rx_channel_status_code = int(fields[6], 16)
        subscription_status_code = int(fields[7], 16)

        # Extract sample rate from first channel with a subscription
        if i == 0 and tx_device_offset != "0000":
            o1 = (int(info_offset, 16) * 2) + 2
            o2 = o1 + 6
            if o2 <= len(hex_str):
                sample_rate = int(hex_str[o1:o2], 16)

        rx_channel_name = (
            get_label(hex_str, rx_channel_offset) if rx_channel_offset != "0000" else ""
        )

        channels[channel_number] = DanteChannel(
            number=channel_number,
            name=rx_channel_name,
            channel_type="rx",
            status_code=rx_channel_status_code,
        )

        # Build subscription if there is one
        if tx_device_offset != "0000":
            tx_dev_name = get_label(hex_str, tx_device_offset)
            if tx_dev_name == ".":
                tx_dev_name = device_name

            if tx_channel_offset == "0000":
                tx_ch_name = rx_channel_name
            else:
                tx_ch_name = get_label(hex_str, tx_channel_offset)

            subscriptions.append(
                DanteSubscription(
                    rx_channel_name=rx_channel_name,
                    rx_device_name=device_name,
                    tx_channel_name=tx_ch_name,
                    tx_device_name=tx_dev_name,
                    status_code=subscription_status_code,
                )
            )

    return channels, subscriptions, sample_rate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_pagination(page: int) -> bytes:
    """Build the 8-byte pagination argument for channel queries."""
    pagination_hex = f"0000000100{page:01x}10000"
    # Pad to 16 hex chars (8 bytes)
    pagination_hex = pagination_hex.ljust(16, "0")
    return bytes.fromhex(pagination_hex)
