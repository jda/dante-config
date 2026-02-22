"""Unit tests for Settings protocol frame construction and parsing."""

from dante_config.const import Encoding
from dante_config.protocol.settings import (
    build_dante_model_query,
    build_identify,
    build_manufacturer_query,
    build_reboot,
    build_set_aes67,
    build_set_encoding,
    build_set_sample_rate,
    parse_dante_model,
    parse_manufacturer,
)


class TestSettingsFrameBuilders:
    """Test Settings frame construction."""

    def test_settings_frame_magic(self) -> None:
        frame = build_identify()
        assert frame[0:2] == b"\xff\xff"

    def test_settings_frame_vendor(self) -> None:
        frame = build_identify()
        assert b"Audinate" in frame

    def test_identify_frame(self) -> None:
        frame = build_identify()
        assert len(frame) == 32
        # Session ID = 0x0bc8
        assert frame[4:6] == b"\x0b\xc8"
        # Command = 0x0063
        assert frame[26:28] == b"\x00\x63"
        # Args end with 0x00000064
        assert frame[28:32] == b"\x00\x00\x00\x64"

    def test_identify_with_mac(self) -> None:
        frame = build_identify(mac="aabbccddeeff")
        assert b"\xaa\xbb\xcc\xdd\xee\xff" in frame

    def test_dante_model_query(self) -> None:
        frame = build_dante_model_query("001122334455")
        assert len(frame) == 32
        # Session ID = 0x0fdb
        assert frame[4:6] == b"\x0f\xdb"
        # Version = 0x0731
        assert frame[24:26] == b"\x07\x31"
        # Command = 0x0061
        assert frame[26:28] == b"\x00\x61"
        # Target MAC
        assert frame[8:14] == bytes.fromhex("001122334455")

    def test_manufacturer_query(self) -> None:
        frame = build_manufacturer_query("aabbccddeeff")
        assert frame[26:28] == b"\x00\xc1"
        assert frame[8:14] == bytes.fromhex("aabbccddeeff")

    def test_set_sample_rate(self) -> None:
        frame = build_set_sample_rate(48000)
        # Session ID = 0x03d4
        assert frame[4:6] == b"\x03\xd4"
        # Version = 0x0727
        assert frame[24:26] == b"\x07\x27"
        # Command = 0x0081
        assert frame[26:28] == b"\x00\x81"
        # Target = RT + zeros
        assert frame[8:14] == bytes.fromhex("525400000000")
        # Sample rate bytes 00bb80 should be in the frame
        assert b"\x00\xbb\x80" in frame

    def test_set_sample_rate_44100(self) -> None:
        frame = build_set_sample_rate(44100)
        assert b"\x00\xac\x44" in frame

    def test_set_encoding_pcm24(self) -> None:
        frame = build_set_encoding(Encoding.PCM24)
        assert len(frame) == 64  # padded to 64 bytes
        # Session ID = 0x03d7
        assert frame[4:6] == b"\x03\xd7"
        # Command = 0x0083
        assert frame[26:28] == b"\x00\x83"
        # Encoding byte should be 0x18
        assert frame[39] == 0x18

    def test_set_encoding_pcm16(self) -> None:
        frame = build_set_encoding(Encoding.PCM16)
        assert frame[39] == 0x10

    def test_set_encoding_pcm32(self) -> None:
        frame = build_set_encoding(Encoding.PCM32)
        assert frame[39] == 0x20

    def test_reboot_frame(self) -> None:
        frame = build_reboot("001122334455")
        assert len(frame) == 32
        assert frame[4:6] == b"\x0f\xdb"
        assert frame[26:28] == b"\x00\x92"
        assert frame[8:14] == bytes.fromhex("001122334455")

    def test_aes67_enable(self) -> None:
        frame = build_set_aes67(True)
        # Command = 0x1006
        assert frame[26:28] == b"\x10\x06"
        # Last byte should be 0x01
        assert frame[-1] == 0x01

    def test_aes67_disable(self) -> None:
        frame = build_set_aes67(False)
        assert frame[-1] == 0x00


class TestSettingsResponseParsers:
    """Test Settings response parsing."""

    def test_parse_dante_model(self) -> None:
        # Build a mock response with model_id at byte 43 and model at byte 88
        response = bytearray(128)
        model_id = b"DAI1\x00"
        model = b"Dante AVIO Input\x00"
        response[43 : 43 + len(model_id)] = model_id
        response[88 : 88 + len(model)] = model

        mid, m = parse_dante_model(bytes(response))
        assert mid == "DAI1"
        assert m == "Dante AVIO Input"

    def test_parse_dante_model_with_control_char(self) -> None:
        response = bytearray(128)
        response[43:50] = b"\x03DAI1\x00X"
        response[88:100] = b"AVIO Input\x00X"
        mid, m = parse_dante_model(bytes(response))
        assert mid == "DAI1"  # \x03 should be stripped
        assert m == "AVIO Input"

    def test_parse_manufacturer(self) -> None:
        response = bytearray(256)
        manufacturer = b"Audinate\x00"
        model = b"Ultimo\x00"
        response[76 : 76 + len(manufacturer)] = manufacturer
        response[204 : 204 + len(model)] = model

        mfr, mdl = parse_manufacturer(bytes(response))
        assert mfr == "Audinate"
        assert mdl == "Ultimo"

    def test_parse_manufacturer_short_response(self) -> None:
        response = bytes(50)  # Too short for both fields
        mfr, mdl = parse_manufacturer(response)
        assert mfr == ""
        assert mdl == ""
