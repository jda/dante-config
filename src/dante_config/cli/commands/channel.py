"""Channel listing and naming commands."""

from __future__ import annotations

import asyncclick as click
from dante_config import DanteClient


@click.group()
async def channel() -> None:
    """Audio channel commands."""


@channel.command("list")
@click.argument("host")
@click.option("--mac", default=None, help="Device MAC address (hex).")
@click.option(
    "--type",
    "channel_type",
    type=click.Choice(["tx", "rx", "all"]),
    default="all",
)
async def channel_list(host: str, mac: str | None, channel_type: str) -> None:
    """List audio channels on a device."""
    client = DanteClient(host, mac_address=mac)
    await client.connect()
    try:
        if channel_type in ("tx", "all"):
            tx_channels, sr = await client.get_tx_channels()
            click.echo(f"\nTX Channels (sample rate: {sr} Hz):")
            for num, ch in sorted(tx_channels.items()):
                friendly = f" ({ch.friendly_name})" if ch.friendly_name else ""
                click.echo(f"  {num:3d}: {ch.name}{friendly}")

        if channel_type in ("rx", "all"):
            name = await client.get_device_name()
            rx_channels, subs, sr = await client.get_rx_channels(device_name=name)
            click.echo(f"\nRX Channels (sample rate: {sr} Hz):")
            for num, ch in sorted(rx_channels.items()):
                click.echo(f"  {num:3d}: {ch.name}")
    finally:
        await client.close()


@channel.command("set-name")
@click.argument("host")
@click.argument("channel_type", type=click.Choice(["tx", "rx"]))
@click.argument("channel_number", type=int)
@click.argument("name")
async def channel_set_name(
    host: str, channel_type: str, channel_number: int, name: str
) -> None:
    """Set the name of a channel."""
    client = DanteClient(host)
    await client.connect()
    try:
        if channel_type == "tx":
            await client.set_tx_channel_name(channel_number, name)
        else:
            await client.set_rx_channel_name(channel_number, name)
        click.echo(
            f"Channel {channel_type.upper()} {channel_number} name set to: {name}"
        )
    finally:
        await client.close()
