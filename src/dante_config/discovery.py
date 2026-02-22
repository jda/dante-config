"""mDNS browser for Dante device discovery."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from zeroconf import ServiceStateChange, Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

from .const import DANTE_SERVICE_TYPES, SERVICE_CMC
from .models import DanteDeviceInfo, DanteServiceRecord

_LOGGER = logging.getLogger(__name__)


class DanteBrowser:
    """Discovers Dante devices on the network via mDNS/Zeroconf.

    Accepts a `zeroconf.Zeroconf` instance — never creates its own.
    This allows HA to pass its shared instance, and CLI to create its own.
    """

    def __init__(self, zc: Zeroconf) -> None:
        self._zc = zc
        self._devices: dict[str, DanteDeviceInfo] = {}
        self._browser: AsyncServiceBrowser | None = None
        self._services_found: dict[str, dict[str, Any]] = {}

    async def discover(self, timeout: float = 5.0) -> dict[str, DanteDeviceInfo]:
        """Discover Dante devices for the given timeout period.

        Returns a dict of {server_name: DanteDeviceInfo}.
        """
        self._devices.clear()
        self._services_found.clear()

        self._browser = AsyncServiceBrowser(
            self._zc,
            DANTE_SERVICE_TYPES,
            handlers=[self._on_service_state_change],
        )

        await asyncio.sleep(timeout)

        # Process all collected services
        await self._assemble_devices()

        if self._browser:
            await self._browser.async_cancel()
            self._browser = None

        return dict(self._devices)

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Handle mDNS service state changes."""
        if state_change == ServiceStateChange.Added:
            self._services_found[name] = {
                "type": service_type,
                "name": name,
            }
        elif state_change == ServiceStateChange.Removed:
            self._services_found.pop(name, None)

    async def _assemble_devices(self) -> None:
        """Assemble devices from collected service records."""
        device_hosts: dict[str, dict[str, dict[str, Any]]] = {}

        for service_name, service_data in self._services_found.items():
            info = AsyncServiceInfo(service_data["type"], service_name)
            await info.async_request(self._zc, timeout=3000)

            if not info.server:
                continue

            server_name = info.server.rstrip(".")

            addresses = info.parsed_scoped_addresses()
            if not addresses:
                continue

            ipv4 = addresses[0]
            properties = {
                k.decode("utf-8", errors="replace"): (
                    v.decode("utf-8", errors="replace")
                    if isinstance(v, bytes)
                    else str(v)
                )
                for k, v in (info.properties or {}).items()
                if isinstance(k, bytes)
            }

            service_record = {
                "type": service_data["type"],
                "name": service_name,
                "port": info.port or 0,
                "properties": properties,
                "server_name": server_name,
                "ipv4": ipv4,
            }

            if server_name not in device_hosts:
                device_hosts[server_name] = {}
            device_hosts[server_name][service_name] = service_record

        # Build DanteDeviceInfo for each device
        for hostname, services in device_hosts.items():
            device = DanteDeviceInfo(server_name=hostname)

            for service_name, svc in services.items():
                if not device.ipv4:
                    device.ipv4 = svc["ipv4"]

                props = svc["properties"]

                device.services[service_name] = DanteServiceRecord(
                    name=service_name,
                    service_type=svc["type"],
                    port=svc["port"],
                    properties=props,
                )

                if svc["type"] == SERVICE_CMC and "id" in props:
                    device.mac_address = props["id"]

                if "model" in props:
                    device.model_id = props["model"]

                if "rate" in props:
                    try:
                        device.sample_rate = int(props["rate"])
                    except ValueError:
                        pass

                if props.get("router_info") == "Dante Via":
                    device.is_software = True

            self._devices[hostname] = device
