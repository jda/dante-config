"""Settings protocol frame builders and response parsers (port 8700)."""

from __future__ import annotations

import struct

from ..const import (
    SESSION_AES67,
    SESSION_ENCODING,
    SESSION_IDENTIFY,
    SESSION_QUERY,
    SESSION_SAMPLE_RATE,
    SettingsCommand,
    TARGET_RT_ZEROS,
    TARGET_ZEROS,
    VERSION_0727,
    VERSION_0731,
    VERSION_0734,
    VERSION_073D,
)
from .common import build_settings_frame, mac_str_to_bytes

# ---------------------------------------------------------------------------
# Frame Builders
# ---------------------------------------------------------------------------


def build_dante_model_query() -> bytes:
    """Build a query for the Dante model (0x0061)."""
    return build_settings_frame(
        command=SettingsCommand.DANTE_MODEL,
        session_id=SESSION_QUERY,
        version=VERSION_073D,
        target=TARGET_ZEROS,
        args=b"\x00\x00\x00\x00",
    )


def build_manufacturer_query() -> bytes:
    """Build a query for manufacturer info (0x00c1)."""
    return build_settings_frame(
        command=SettingsCommand.MANUFACTURER,
        session_id=SESSION_QUERY,
        version=VERSION_073D,
        target=TARGET_ZEROS,
        args=b"\x00\x00\x00\x00",
    )


def build_identify(mac: str | None = None) -> bytes:
    """Build an identify command to flash the device LED (0x0063)."""
    target = mac_str_to_bytes(mac) if mac else TARGET_ZEROS
    return build_settings_frame(
        command=SettingsCommand.IDENTIFY,
        session_id=SESSION_IDENTIFY,
        version=VERSION_0731,
        target=target,
        args=b"\x00\x00\x00\x64",
    )


def build_set_sample_rate(sample_rate: int) -> bytes:
    """Build a command to set the sample rate (0x0081)."""
    rate_bytes = struct.pack(">I", sample_rate)[-3:]  # 3-byte big-endian
    args = b"\x00\x00\x00\x64\x00\x00\x00\x01\x00" + rate_bytes
    return build_settings_frame(
        command=SettingsCommand.SAMPLE_RATE,
        session_id=SESSION_SAMPLE_RATE,
        version=VERSION_0727,
        target=TARGET_RT_ZEROS,
        args=args,
    )


def build_set_encoding(encoding: int) -> bytes:
    """Build a command to set the audio encoding (0x0083).

    encoding: one of Encoding.PCM16 (0x10), PCM24 (0x18), PCM32 (0x20).
    """
    args = b"\x00\x00\x00\x64\x00\x00\x00\x01\x00\x00\x00" + struct.pack(">B", encoding)
    # Pad to reach 64-byte total frame
    frame = build_settings_frame(
        command=SettingsCommand.ENCODING,
        session_id=SESSION_ENCODING,
        version=VERSION_0727,
        target=TARGET_RT_ZEROS,
        args=args,
    )
    # Pad to 64 bytes
    if len(frame) < 64:
        frame = frame + b"\x00" * (64 - len(frame))
        # Re-patch length
        frame_bytes = bytearray(frame)
        frame_bytes[3] = 64
        frame = bytes(frame_bytes)
    return frame


def build_reboot(mac: str) -> bytes:
    """Build a reboot command (0x0092). NOT YET WIRE-CONFIRMED."""
    return build_settings_frame(
        command=SettingsCommand.REBOOT,
        session_id=SESSION_QUERY,
        version=VERSION_0731,
        target=mac_str_to_bytes(mac),
        args=b"\x00\x00\x00\x00",
    )


def build_set_aes67(enabled: bool, mac: str | None = None) -> bytes:
    """Build a command to enable/disable AES67 (0x1006)."""
    target = mac_str_to_bytes(mac) if mac else bytes.fromhex("00385eba0000")
    enable_byte = b"\x01" if enabled else b"\x00"
    args = b"\x00\x00\x00\x64\x00\x01\x00" + enable_byte
    return build_settings_frame(
        command=SettingsCommand.AES67,
        session_id=SESSION_AES67,
        version=VERSION_0734,
        target=target,
        args=args,
    )


# ---------------------------------------------------------------------------
# Response Parsers
# ---------------------------------------------------------------------------


def parse_dante_model(response: bytes) -> tuple[str, str]:
    """Parse Dante model from a 0x0061 response.

    Returns (model_id, model).
    """
    model_id = ""
    model = ""
    if len(response) > 43:
        model_id = response[43:].partition(b"\x00")[0].decode("utf-8", errors="replace")
        model_id = model_id.replace("\x03", "")
    if len(response) > 88:
        model = response[88:].partition(b"\x00")[0].decode("utf-8", errors="replace")
    return model_id, model


def parse_manufacturer(response: bytes) -> tuple[str, str]:
    """Parse manufacturer info from a 0x00c1 response.

    Returns (manufacturer, model).
    """
    manufacturer = ""
    model = ""
    if len(response) > 76:
        manufacturer = (
            response[76:].partition(b"\x00")[0].decode("utf-8", errors="replace")
        )
    if len(response) > 204:
        model = response[204:].partition(b"\x00")[0].decode("utf-8", errors="replace")
    return manufacturer, model
