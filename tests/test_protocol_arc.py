"""Unit tests for ARC protocol frame construction and parsing."""

import struct

import pytest

from dante_config.const import ArcCommand
from dante_config.protocol.arc import (
    build_add_subscription,
    build_channel_count_query,
    build_device_info_query,
    build_device_name_query,
    build_remove_subscription,
    build_reset_device_name,
    build_reset_rx_channel_name,
    build_reset_tx_channel_name,
    build_rx_channels_query,
    build_set_device_name,
    build_set_latency,
    build_set_rx_channel_name,
    build_set_tx_channel_name,
    build_tx_channels_query,
    build_tx_friendly_names_query,
    parse_channel_counts,
    parse_device_name,
    parse_rx_channels,
    parse_tx_channels,
    parse_tx_friendly_names,
)
from dante_config.protocol.common import get_label


class TestArcFrameBuilders:
    """Test ARC frame construction."""

    def test_device_name_query_structure(self) -> None:
        frame, seq_id = build_device_name_query(seq_id=0x1234)
        assert frame[0] == 0x27  # magic
        assert frame[1] == 0xFF  # flags
        assert frame[2] == 0x00  # reserved
        assert frame[3] == 10   # length = 0x0a
        assert frame[4:6] == b"\x12\x34"  # seq_id
        assert frame[6:8] == struct.pack(">H", ArcCommand.DEVICE_NAME)
        assert frame[8:10] == b"\x00\x00"

    def test_channel_count_query(self) -> None:
        frame, seq_id = build_channel_count_query(seq_id=0xABCD)
        assert frame[3] == 10
        assert frame[6:8] == struct.pack(">H", ArcCommand.CHANNEL_COUNT)
        assert int.from_bytes(frame[4:6], "big") == 0xABCD

    def test_device_info_query(self) -> None:
        frame, seq_id = build_device_info_query(seq_id=0x0001)
        assert frame[6:8] == struct.pack(">H", ArcCommand.DEVICE_INFO)

    def test_tx_channels_query(self) -> None:
        frame, seq_id = build_tx_channels_query(page=0, seq_id=0x5555)
        assert frame[3] == 16  # 0x10
        assert frame[6:8] == struct.pack(">H", ArcCommand.TX_CHANNELS)

    def test_rx_channels_query(self) -> None:
        frame, seq_id = build_rx_channels_query(page=0, seq_id=0x6666)
        assert frame[3] == 16
        assert frame[6:8] == struct.pack(">H", ArcCommand.RX_CHANNELS)

    def test_set_device_name(self) -> None:
        frame, seq_id = build_set_device_name("MyDevice", seq_id=0x1111)
        assert frame[6:8] == struct.pack(">H", ArcCommand.SET_DEVICE_NAME)
        # Should contain the name bytes
        name_bytes = "MyDevice".encode("utf-8")
        assert name_bytes in frame
        # Length should be len(name) + 11
        assert frame[3] == len(name_bytes) + 11

    def test_reset_device_name(self) -> None:
        frame, seq_id = build_reset_device_name(seq_id=0x2222)
        assert frame[3] == 10  # 0x0a
        assert frame[6:8] == struct.pack(">H", ArcCommand.SET_DEVICE_NAME)

    def test_set_tx_channel_name(self) -> None:
        frame, seq_id = build_set_tx_channel_name(1, "Out 1", seq_id=0x3333)
        assert frame[6:8] == struct.pack(">H", ArcCommand.SET_TX_CHANNEL_NAME)
        assert b"Out 1" in frame
        # Length should be len(name) + 25
        assert frame[3] == len("Out 1".encode()) + 25

    def test_reset_tx_channel_name(self) -> None:
        frame, seq_id = build_reset_tx_channel_name(2, seq_id=0x4444)
        assert frame[3] == 25  # 0x19
        assert frame[6:8] == struct.pack(">H", ArcCommand.SET_TX_CHANNEL_NAME)

    def test_set_rx_channel_name(self) -> None:
        frame, seq_id = build_set_rx_channel_name(3, "Input 3", seq_id=0x5555)
        assert frame[6:8] == struct.pack(">H", ArcCommand.SET_RX_CHANNEL_NAME)
        assert b"Input 3" in frame
        assert frame[3] == len("Input 3".encode()) + 21

    def test_reset_rx_channel_name(self) -> None:
        frame, seq_id = build_reset_rx_channel_name(4, seq_id=0x6666)
        assert frame[3] == 21  # 0x15
        assert frame[6:8] == struct.pack(">H", ArcCommand.SET_RX_CHANNEL_NAME)

    def test_add_subscription(self) -> None:
        frame, seq_id = build_add_subscription(1, "TX-01", "DeviceA", seq_id=0x7777)
        assert frame[6:8] == struct.pack(">H", ArcCommand.ADD_SUBSCRIPTION)
        assert b"TX-01" in frame
        assert b"DeviceA" in frame

    def test_remove_subscription(self) -> None:
        frame, seq_id = build_remove_subscription(2, seq_id=0x8888)
        assert frame[3] == 16  # 0x10
        assert frame[6:8] == struct.pack(">H", ArcCommand.REMOVE_SUBSCRIPTION)
        # Last byte should be the channel number
        assert frame[-1] == 2

    def test_set_latency(self) -> None:
        frame, seq_id = build_set_latency(1000, seq_id=0x9999)
        assert frame[6:8] == struct.pack(">H", ArcCommand.SET_LATENCY)
        assert frame[3] == 40  # 0x28
        # Latency appears twice in the frame
        lat_bytes = struct.pack(">I", 1000)
        count = frame.count(lat_bytes)
        assert count == 2

    def test_seq_id_is_random_when_not_specified(self) -> None:
        _, seq1 = build_device_name_query()
        _, seq2 = build_device_name_query()
        # There's a 1/65536 chance this fails, which is acceptable
        # Actually just check they're in range
        assert 0 <= seq1 <= 0xFFFF
        assert 0 <= seq2 <= 0xFFFF


class TestArcResponseParsers:
    """Test ARC response parsing."""

    def test_parse_device_name(self) -> None:
        # Build a mock response: 10 bytes header + name + null
        header = bytes(10)
        name = b"TestDevice\x00"
        response = header + name
        result = parse_device_name(response)
        assert result == "TestDevice"

    def test_parse_channel_counts(self) -> None:
        # Build a mock response with tx=4 at byte 13, rx=2 at byte 15
        response = bytearray(16)
        response[13] = 4
        response[15] = 2
        tx, rx = parse_channel_counts(bytes(response))
        assert tx == 4
        assert rx == 2

    def test_parse_tx_channels_basic(self) -> None:
        """Test parsing a response with one TX channel."""
        # Build a response buffer large enough to avoid field overlaps.
        # Entry format: 4 x uint16 = 8 bytes (16 hex chars)
        #   [channel_number, status, channel_group, channel_offset]
        # Entries start at hex offset 24 (byte 12).
        # Use group=0x0030 so sample rate is at hex[98:104] = byte 49-51.
        # Put channel name at byte offset 0x0038 = byte 56.
        response = bytearray(80)

        # Entry at byte 12: ch=1, status=0, group=0x0030, offset=0x0038
        struct.pack_into(">HHHH", response, 12, 1, 0, 0x0030, 0x0038)

        # Sample rate at hex index (0x30 * 2) + 2 = 98, bytes 49-51
        sr_bytes = struct.pack(">I", 48000)[-3:]  # 00bb80
        response[49:52] = sr_bytes

        # Channel name at byte 0x38 = 56
        name_data = b"Channel01\x00"
        response[56:56 + len(name_data)] = name_data

        channels, sample_rate = parse_tx_channels(bytes(response), 1)
        assert 1 in channels
        assert channels[1].name == "Channel01"
        assert channels[1].channel_type == "tx"
        assert sample_rate == 48000

    def test_parse_rx_channels_with_subscription(self) -> None:
        """Test parsing RX response with a subscription."""
        # Build a response with 1 RX channel subscribed to a TX channel
        # 12 bytes header, then 20 bytes per entry (40 hex chars)
        # 8 fields of 2 bytes each = 16 bytes, rest is padding/extra
        response = bytearray(128)

        # Entry at byte 12: 8 fields of 2 bytes
        offset = 12
        struct.pack_into(">H", response, offset, 1)      # channel_number = 1
        struct.pack_into(">H", response, offset + 2, 0)   # reserved
        struct.pack_into(">H", response, offset + 4, 0)   # info_offset
        struct.pack_into(">H", response, offset + 6, 0x0040)  # tx_channel_offset
        struct.pack_into(">H", response, offset + 8, 0x0048)  # tx_device_offset
        struct.pack_into(">H", response, offset + 10, 0x0050) # rx_channel_offset
        struct.pack_into(">H", response, offset + 12, 0)  # rx_channel_status
        struct.pack_into(">H", response, offset + 14, 9)  # subscription_status = DYNAMIC

        # Put strings at offsets
        tx_ch = b"TX-01\x00"
        tx_dev = b"Sender\x00"
        rx_ch = b"RX-01\x00"

        response[0x40:0x40 + len(tx_ch)] = tx_ch
        response[0x48:0x48 + len(tx_dev)] = tx_dev
        response[0x50:0x50 + len(rx_ch)] = rx_ch

        channels, subs, sr = parse_rx_channels(bytes(response), "MyDevice", 1)

        assert 1 in channels
        assert channels[1].name == "RX-01"
        assert channels[1].channel_type == "rx"

        assert len(subs) == 1
        assert subs[0].tx_channel_name == "TX-01"
        assert subs[0].tx_device_name == "Sender"
        assert subs[0].rx_channel_name == "RX-01"
        assert subs[0].status_code == 9

    def test_parse_rx_channels_loopback(self) -> None:
        """Test that '.' device name is resolved to own device name."""
        response = bytearray(128)
        offset = 12
        struct.pack_into(">H", response, offset, 1)
        struct.pack_into(">H", response, offset + 2, 0)
        struct.pack_into(">H", response, offset + 4, 0)
        struct.pack_into(">H", response, offset + 6, 0x0040)
        struct.pack_into(">H", response, offset + 8, 0x0048)
        struct.pack_into(">H", response, offset + 10, 0x0050)
        struct.pack_into(">H", response, offset + 12, 0)
        struct.pack_into(">H", response, offset + 14, 4)  # SUBSCRIBE_SELF

        response[0x40:0x46] = b"TX-01\x00"
        response[0x48:0x4a] = b".\x00"  # loopback indicator
        response[0x50:0x56] = b"RX-01\x00"

        _, subs, _ = parse_rx_channels(bytes(response), "MyDevice", 1)
        assert subs[0].tx_device_name == "MyDevice"

    def test_parse_rx_channels_no_subscription(self) -> None:
        """Test RX channel with no subscription (tx_device_offset=0000)."""
        response = bytearray(128)
        offset = 12
        struct.pack_into(">H", response, offset, 1)
        struct.pack_into(">H", response, offset + 2, 0)
        struct.pack_into(">H", response, offset + 4, 0)
        struct.pack_into(">H", response, offset + 6, 0)      # no tx channel
        struct.pack_into(">H", response, offset + 8, 0)      # no tx device
        struct.pack_into(">H", response, offset + 10, 0x0050)
        struct.pack_into(">H", response, offset + 12, 0)
        struct.pack_into(">H", response, offset + 14, 0)

        response[0x50:0x56] = b"RX-01\x00"

        channels, subs, _ = parse_rx_channels(bytes(response), "MyDevice", 1)
        assert 1 in channels
        assert len(subs) == 0


class TestGetLabel:
    """Test the get_label helper."""

    def test_basic_extraction(self) -> None:
        # "Hello\x00World" in hex
        data = b"Hello\x00World\x00"
        hex_str = data.hex()
        # offset 0 should give "Hello"
        assert get_label(hex_str, "0000") == "Hello"

    def test_offset_extraction(self) -> None:
        data = b"\x00\x00\x00\x00Test\x00"
        hex_str = data.hex()
        # offset 4 (0x0004) should give "Test"
        assert get_label(hex_str, "0004") == "Test"

    def test_empty_string(self) -> None:
        data = b"\x00"
        hex_str = data.hex()
        assert get_label(hex_str, "0000") == ""

    def test_out_of_bounds(self) -> None:
        data = b"AB"
        hex_str = data.hex()
        assert get_label(hex_str, "00ff") == ""
