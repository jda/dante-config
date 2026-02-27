"""Subscription management commands."""

from __future__ import annotations

import asyncclick as click
from dante_config import DanteClient, SubscriptionStatus


@click.group()
async def subscription() -> None:
    """Audio subscription (routing) commands."""


@subscription.command("list")
@click.argument("host")
@click.option("--mac", default=None, help="Device MAC address (hex).")
async def subscription_list(host: str, mac: str | None) -> None:
    """List all subscriptions on a device."""
    client = DanteClient(host, mac_address=mac)
    await client.connect()
    try:
        name = await client.get_device_name()
        _, subs, _ = await client.get_rx_channels(device_name=name)

        if not subs:
            click.echo("No active subscriptions.")
            return

        click.echo(f"\nSubscriptions on {name}:\n")
        for sub in subs:
            try:
                status = SubscriptionStatus(sub.status_code)
                status_str = status.name
            except ValueError:
                status_str = f"UNKNOWN({sub.status_code})"
            click.echo(
                f"  {sub.rx_channel_name:20s} <- "
                f"{sub.tx_device_name}:{sub.tx_channel_name}  "
                f"[{status_str}]"
            )
    finally:
        await client.close()


@subscription.command("add")
@click.argument("host")
@click.argument("rx_channel", type=int)
@click.argument("tx_channel_name")
@click.argument("tx_device_name")
async def subscription_add(
    host: str, rx_channel: int, tx_channel_name: str, tx_device_name: str
) -> None:
    """Subscribe RX channel to a TX channel on another device."""
    client = DanteClient(host)
    await client.connect()
    try:
        await client.add_subscription(rx_channel, tx_channel_name, tx_device_name)
        click.echo(f"Subscribed RX {rx_channel} to {tx_device_name}:{tx_channel_name}")
    finally:
        await client.close()


@subscription.command("remove")
@click.argument("host")
@click.argument("rx_channel", type=int)
async def subscription_remove(host: str, rx_channel: int) -> None:
    """Remove subscription from an RX channel."""
    client = DanteClient(host)
    await client.connect()
    try:
        await client.remove_subscription(rx_channel)
        click.echo(f"Removed subscription from RX {rx_channel}")
    finally:
        await client.close()
