"""Discover Dante devices on the network."""

from __future__ import annotations

import json

import asyncclick as click
from dante_config import DanteBrowser
from zeroconf.asyncio import AsyncZeroconf


@click.command()
@click.option("--timeout", default=5, type=float, help="Discovery timeout in seconds.")
@click.option("--json-output", "output_json", is_flag=True, help="Output as JSON.")
async def discover(timeout: float, output_json: bool) -> None:
    """Discover Dante devices on the local network."""
    azc = AsyncZeroconf()
    try:
        browser = DanteBrowser(azc.zeroconf)
        click.echo(f"Discovering Dante devices for {timeout}s...")
        devices = await browser.discover(timeout=timeout)

        if not devices:
            click.echo("No devices found.")
            return

        if output_json:
            data = {}
            for name, dev in devices.items():
                data[name] = {
                    "name": dev.name or name,
                    "ipv4": dev.ipv4,
                    "mac_address": dev.mac_address,
                    "model_id": dev.model_id,
                    "sample_rate": dev.sample_rate,
                }
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"\nFound {len(devices)} device(s):\n")
            for server_name, dev in devices.items():
                click.echo(f"  {server_name}")
                click.echo(f"    IP:    {dev.ipv4}")
                if dev.mac_address:
                    click.echo(f"    MAC:   {dev.mac_address}")
                if dev.model_id:
                    click.echo(f"    Model: {dev.model_id}")
                if dev.sample_rate:
                    click.echo(f"    Rate:  {dev.sample_rate} Hz")
                click.echo()
    finally:
        await azc.async_close()
