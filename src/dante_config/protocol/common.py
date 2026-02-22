"""Common frame builder helpers shared by ARC and Settings protocols."""

from __future__ import annotations

import random
import struct

from ..const import (
    ARC_FLAGS,
    ARC_MAGIC,
    ARC_RESERVED,
    SETTINGS_MAGIC,
    SETTINGS_VENDOR,
)


def random_seq_id() -> int:
    """Generate a random 16-bit sequence ID."""
    return random.randint(0, 0xFFFF)


def build_arc_frame(
    command: int, args: bytes = b"", seq_id: int | None = None
) -> tuple[bytes, int]:
    """Build an ARC protocol frame (port 8800).

    Returns (frame_bytes, seq_id).
    """
    if seq_id is None:
        seq_id = random_seq_id()
    header = struct.pack(
        ">BBBBH",
        ARC_MAGIC,
        ARC_FLAGS,
        ARC_RESERVED,
        0,  # placeholder for length (1 byte)
        seq_id,
    )
    command_bytes = struct.pack(">H", command)
    frame = header + command_bytes + args
    # Patch length byte at offset 3
    frame_bytes = bytearray(frame)
    frame_bytes[3] = len(frame_bytes)
    return bytes(frame_bytes), seq_id


def build_settings_frame(
    command: int,
    session_id: int,
    version: int,
    target: bytes,
    args: bytes = b"",
) -> bytes:
    """Build a Settings protocol frame (port 8700)."""
    header = struct.pack(
        ">HBB", SETTINGS_MAGIC, 0x00, 0
    )  # magic + reserved + length placeholder
    session = struct.pack(">H", session_id)
    padding1 = b"\x00\x00"
    target_bytes = target
    padding2 = b"\x00\x00"
    vendor = SETTINGS_VENDOR
    ver = struct.pack(">H", version)
    cmd = struct.pack(">H", command)

    frame = (
        header
        + session
        + padding1
        + target_bytes
        + padding2
        + vendor
        + ver
        + cmd
        + args
    )
    # Patch length byte at offset 3
    frame_bytes = bytearray(frame)
    frame_bytes[3] = len(frame_bytes)
    return bytes(frame_bytes)


def get_label(hex_str: str, offset_hex: str) -> str:
    """Extract a null-terminated string from a hex response at a given offset.

    The offset is a hex string representing the byte offset into the response.
    """
    byte_offset = int(offset_hex, 16)
    hex_index = byte_offset * 2
    if hex_index >= len(hex_str):
        return ""
    hex_substring = hex_str[hex_index:]
    raw_bytes = bytes.fromhex(hex_substring)
    label = raw_bytes.partition(b"\x00")[0].decode("utf-8", errors="replace")
    return label


def mac_str_to_bytes(mac: str) -> bytes:
    """Convert a MAC address string (hex, with or without separators) to 6 bytes."""
    cleaned = mac.replace(":", "").replace("-", "").replace(".", "")
    if len(cleaned) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")
    return bytes.fromhex(cleaned)
