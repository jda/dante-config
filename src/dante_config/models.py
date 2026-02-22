"""Typed dataclasses for Dante device data."""

from __future__ import annotations

from dataclasses import dataclass, field

from .const import PORT_ARC, SERVICE_ARC, SubscriptionStatus


@dataclass
class DanteChannel:
    """A single TX or RX audio channel."""

    number: int
    name: str
    channel_type: str  # "tx" or "rx"
    friendly_name: str | None = None
    status_code: int = 0
    enabled: bool = True


@dataclass
class DanteSubscription:
    """An audio subscription linking an RX channel to a TX channel."""

    rx_channel_name: str
    rx_device_name: str
    tx_channel_name: str
    tx_device_name: str
    status_code: int = 0

    @property
    def status(self) -> SubscriptionStatus:
        try:
            return SubscriptionStatus(self.status_code)
        except ValueError:
            return SubscriptionStatus.NONE

    @property
    def is_connected(self) -> bool:
        return self.status.is_connected

    @property
    def is_error(self) -> bool:
        return self.status.is_error


@dataclass
class DanteServiceRecord:
    """An mDNS service record for a Dante device."""

    name: str
    service_type: str
    port: int
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class DanteDeviceInfo:
    """Complete state snapshot of a Dante device."""

    name: str = ""
    server_name: str = ""
    ipv4: str = ""
    mac_address: str = ""
    model_id: str = ""
    model: str = ""
    manufacturer: str = ""
    dante_model: str = ""
    sample_rate: int = 0
    encoding: int = 0
    latency: int = 0
    tx_count: int = 0
    rx_count: int = 0
    tx_channels: dict[int, DanteChannel] = field(default_factory=dict)
    rx_channels: dict[int, DanteChannel] = field(default_factory=dict)
    subscriptions: list[DanteSubscription] = field(default_factory=list)
    services: dict[str, DanteServiceRecord] = field(default_factory=dict)
    is_software: bool = False

    @property
    def arc_port(self) -> int:
        """Return the ARC port from mDNS services, or the default."""
        svc = self.services.get(SERVICE_ARC)
        return svc.port if svc is not None else PORT_ARC
