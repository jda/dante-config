"""Device management commands."""

from __future__ import annotations

import json

import asyncclick as click
from dante_config import DanteBrowser, DanteClient
from zeroconf.asyncio import AsyncZeroconf


@click.group()
async def device() -> None:
    """Device information and control commands."""


@device.command("list")
@click.option("--timeout", default=5, type=float, help="Discovery timeout in seconds.")
async def device_list(timeout: float) -> None:
    """List all discovered Dante devices."""
    azc = AsyncZeroconf()
    try:
        browser = DanteBrowser(azc.zeroconf)
        devices = await browser.discover(timeout=timeout)
        if not devices:
            click.echo("No devices found.")
            return
        for name, dev in devices.items():
            click.echo(f"{name:30s}  {dev.ipv4:15s}  {dev.mac_address or '-':12s}")
    finally:
        await azc.async_close()


@device.command("info")
@click.argument("host")
@click.option("--mac", default=None, help="Device MAC address (hex).")
@click.option("--json-output", "output_json", is_flag=True, help="Output as JSON.")
async def device_info(host: str, mac: str | None, output_json: bool) -> None:
    """Show detailed info for a Dante device."""
    client = DanteClient(host, mac_address=mac)
    await client.connect()
    try:
        info = await client.get_full_state()
        if output_json:
            data = {
                "name": info.name,
                "ipv4": info.ipv4,
                "mac_address": info.mac_address,
                "manufacturer": info.manufacturer,
                "model": info.model,
                "dante_model": info.dante_model,
                "sample_rate": info.sample_rate,
                "tx_count": info.tx_count,
                "rx_count": info.rx_count,
            }
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"Name:         {info.name}")
            click.echo(f"IP:           {info.ipv4}")
            click.echo(f"MAC:          {info.mac_address}")
            click.echo(f"Manufacturer: {info.manufacturer}")
            click.echo(f"Model:        {info.model}")
            click.echo(f"Dante Model:  {info.dante_model}")
            click.echo(f"Sample Rate:  {info.sample_rate} Hz")
            click.echo(f"TX Channels:  {info.tx_count}")
            click.echo(f"RX Channels:  {info.rx_count}")
    finally:
        await client.close()


@device.command("identify")
@click.argument("host")
@click.option("--mac", default=None, help="Device MAC address (hex).")
async def device_identify(host: str, mac: str | None) -> None:
    """Flash the device LED for identification."""
    client = DanteClient(host, mac_address=mac)
    await client.connect()
    try:
        await client.identify()
        click.echo("Identify command sent.")
    finally:
        await client.close()


@device.command("set-name")
@click.argument("host")
@click.argument("name")
async def device_set_name(host: str, name: str) -> None:
    """Set the device name."""
    client = DanteClient(host)
    await client.connect()
    try:
        await client.set_device_name(name)
        click.echo(f"Device name set to: {name}")
    finally:
        await client.close()


@device.command("reboot")
@click.argument("host")
@click.option(
    "--mac",
    required=True,
    help="Device MAC address (hex, required for reboot).",
)
async def device_reboot(host: str, mac: str) -> None:
    """Reboot a Dante device."""
    client = DanteClient(host, mac_address=mac)
    await client.connect()
    try:
        await client.reboot()
        click.echo("Reboot command sent.")
    finally:
        await client.close()
