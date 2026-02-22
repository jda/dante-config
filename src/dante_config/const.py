"""Constants, enums, ports, and service types for the Dante protocol."""

from __future__ import annotations

from enum import IntEnum

# --- UDP Ports ---
PORT_ARC = 4440
PORT_SETTINGS = 8700
PORT_SETTINGS_MCAST = 8702
PORT_INFO = 8702

# --- mDNS Service Types ---
SERVICE_ARC = "_netaudio-arc._udp.local."
SERVICE_CMC = "_netaudio-cmc._udp.local."
SERVICE_CHAN = "_netaudio-chan._udp.local."
SERVICE_DBC = "_netaudio-dbc._udp.local."

DANTE_SERVICE_TYPES = [SERVICE_ARC, SERVICE_CMC, SERVICE_CHAN, SERVICE_DBC]

# --- Multicast ---
MULTICAST_GROUP_CONTROL = "224.0.0.231"
MULTICAST_GROUP_SETTINGS = "224.0.0.231"

# --- ARC Frame Constants ---
ARC_MAGIC = 0x28
ARC_FLAGS = 0x09
ARC_RESERVED = 0x00

# --- Settings Frame Constants ---
SETTINGS_MAGIC = 0xFFFF
SETTINGS_VENDOR = b"Audinate"  # 0x417564696e617465

# --- ARC Command Types ---


class ArcCommand(IntEnum):
    """ARC protocol command types (port 8800)."""

    CHANNEL_COUNT = 0x1000
    SET_DEVICE_NAME = 0x1001
    DEVICE_NAME = 0x1002
    DEVICE_INFO = 0x1003
    SET_LATENCY = 0x1101
    TX_CHANNELS = 0x2000
    TX_FRIENDLY_NAMES = 0x2010
    SET_TX_CHANNEL_NAME = 0x2013
    RX_CHANNELS = 0x3000
    SET_RX_CHANNEL_NAME = 0x3001
    ADD_SUBSCRIPTION = 0x3010
    REMOVE_SUBSCRIPTION = 0x3014


# --- Settings Command Types ---


class SettingsCommand(IntEnum):
    """Settings protocol command types (port 8700)."""

    DANTE_MODEL = 0x0061
    IDENTIFY = 0x0063
    SAMPLE_RATE = 0x0081
    ENCODING = 0x0083
    REBOOT = 0x0092
    MANUFACTURER = 0x00C1
    AES67 = 0x1006


# --- Settings Session IDs ---
SESSION_QUERY = 0x0FDB
SESSION_IDENTIFY = 0x0BC8
SESSION_SAMPLE_RATE = 0x03D4
SESSION_ENCODING = 0x03D7
SESSION_AES67 = 0x00FF

# --- Settings Versions ---
VERSION_0731 = 0x0731
VERSION_0727 = 0x0727
VERSION_0734 = 0x0734
VERSION_073D = 0x073D

# --- Settings Target Patterns ---
TARGET_RT_ZEROS = bytes.fromhex("525400000000")
TARGET_ZEROS = b"\x00" * 6


# --- Subscription Status ---


class SubscriptionStatus(IntEnum):
    """Subscription status codes from RX channel queries."""

    NONE = 0
    UNRESOLVED = 1
    RESOLVED = 2
    RESOLVE_FAIL = 3
    SUBSCRIBE_SELF = 4
    RESOLVED_NONE = 5
    IDLE = 7
    IN_PROGRESS = 8
    DYNAMIC = 9
    STATIC = 10
    MANUAL = 14
    NO_CONNECTION = 15
    CHANNEL_FORMAT = 16
    BUNDLE_FORMAT = 17
    NO_RX = 18
    RX_FAIL = 19
    NO_TX = 20
    TX_FAIL = 21
    QOS_FAIL_RX = 22
    QOS_FAIL_TX = 23
    TX_REJECTED_ADDR = 24
    INVALID_MSG = 25
    CHANNEL_LATENCY = 26
    CLOCK_DOMAIN = 27
    UNSUPPORTED = 28
    RX_LINK_DOWN = 29
    TX_LINK_DOWN = 30
    DYNAMIC_PROTOCOL = 31
    INVALID_CHANNEL = 32
    TX_SCHEDULER_FAILURE = 33
    SUBSCRIBE_SELF_POLICY = 34
    TX_NOT_READY = 35
    RX_NOT_READY = 36
    TX_FANOUT_LIMIT_REACHED = 37
    TX_CHANNEL_ENCRYPTED = 38
    TX_RESPONSE_UNEXPECTED = 39
    SYSTEM_FAIL = 255

    @property
    def is_connected(self) -> bool:
        return self in _CONNECTED_STATUSES

    @property
    def is_error(self) -> bool:
        return self in _ERROR_STATUSES

    @property
    def is_transient(self) -> bool:
        return self in _TRANSIENT_STATUSES


_CONNECTED_STATUSES = frozenset(
    {
        SubscriptionStatus.SUBSCRIBE_SELF,
        SubscriptionStatus.DYNAMIC,
        SubscriptionStatus.STATIC,
        SubscriptionStatus.MANUAL,
    }
)

_TRANSIENT_STATUSES = frozenset(
    {
        SubscriptionStatus.NONE,
        SubscriptionStatus.UNRESOLVED,
        SubscriptionStatus.RESOLVED,
        SubscriptionStatus.RESOLVED_NONE,
        SubscriptionStatus.IDLE,
        SubscriptionStatus.IN_PROGRESS,
    }
)

_ERROR_STATUSES = frozenset(
    {
        SubscriptionStatus.RESOLVE_FAIL,
        SubscriptionStatus.NO_CONNECTION,
        SubscriptionStatus.CHANNEL_FORMAT,
        SubscriptionStatus.BUNDLE_FORMAT,
        SubscriptionStatus.NO_RX,
        SubscriptionStatus.RX_FAIL,
        SubscriptionStatus.NO_TX,
        SubscriptionStatus.TX_FAIL,
        SubscriptionStatus.QOS_FAIL_RX,
        SubscriptionStatus.QOS_FAIL_TX,
        SubscriptionStatus.TX_REJECTED_ADDR,
        SubscriptionStatus.INVALID_MSG,
        SubscriptionStatus.CHANNEL_LATENCY,
        SubscriptionStatus.CLOCK_DOMAIN,
        SubscriptionStatus.UNSUPPORTED,
        SubscriptionStatus.RX_LINK_DOWN,
        SubscriptionStatus.TX_LINK_DOWN,
        SubscriptionStatus.DYNAMIC_PROTOCOL,
        SubscriptionStatus.INVALID_CHANNEL,
        SubscriptionStatus.TX_SCHEDULER_FAILURE,
        SubscriptionStatus.SUBSCRIBE_SELF_POLICY,
        SubscriptionStatus.TX_NOT_READY,
        SubscriptionStatus.RX_NOT_READY,
        SubscriptionStatus.TX_FANOUT_LIMIT_REACHED,
        SubscriptionStatus.TX_CHANNEL_ENCRYPTED,
        SubscriptionStatus.TX_RESPONSE_UNEXPECTED,
        SubscriptionStatus.SYSTEM_FAIL,
    }
)


# --- Encoding Values ---


class Encoding(IntEnum):
    """Audio encoding bit depths."""

    PCM16 = 0x10
    PCM24 = 0x18
    PCM32 = 0x20


# --- Sample Rates ---
SAMPLE_RATES = {
    44100: bytes.fromhex("00ac44"),
    48000: bytes.fromhex("00bb80"),
    88200: bytes.fromhex("015888"),
    96000: bytes.fromhex("017700"),
    176400: bytes.fromhex("02b110"),
    192000: bytes.fromhex("02ee00"),
}
