"""Dante audio networking device discovery and control library."""

from .client import DanteClient
from .const import (
    ArcCommand,
    Encoding,
    PORT_ARC,
    PORT_SETTINGS,
    SAMPLE_RATES,
    SettingsCommand,
    SubscriptionStatus,
)
from .discovery import DanteBrowser
from .exceptions import (
    DanteCommandError,
    DanteConnectionError,
    DanteError,
    DanteProtocolError,
    DanteTimeoutError,
)
from .models import (
    DanteChannel,
    DanteDeviceInfo,
    DanteServiceRecord,
    DanteSubscription,
)

__all__ = [
    "ArcCommand",
    "DanteBrowser",
    "DanteChannel",
    "DanteClient",
    "DanteCommandError",
    "DanteConnectionError",
    "DanteDeviceInfo",
    "DanteError",
    "DanteProtocolError",
    "DanteServiceRecord",
    "DanteSubscription",
    "DanteTimeoutError",
    "Encoding",
    "PORT_ARC",
    "PORT_SETTINGS",
    "SAMPLE_RATES",
    "SettingsCommand",
    "SubscriptionStatus",
]
