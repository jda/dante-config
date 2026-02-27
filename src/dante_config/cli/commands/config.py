"""Device configuration commands."""

from __future__ import annotations

import asyncclick as click
from dante_config import DanteClient, Encoding


@click.group()
async def config() -> None:
    """Device configuration commands."""


@config.command("sample-rate")
@click.argument("host")
@click.argument(
    "rate",
    type=click.Choice(["44100", "48000", "88200", "96000", "176400", "192000"]),
)
async def set_sample_rate(host: str, rate: str) -> None:
    """Set the device sample rate."""
    client = DanteClient(host)
    await client.connect()
    try:
        await client.set_sample_rate(int(rate))
        click.echo(f"Sample rate set to {rate} Hz")
    finally:
        await client.close()


@config.command("encoding")
@click.argument("host")
@click.argument("bits", type=click.Choice(["16", "24", "32"]))
async def set_encoding(host: str, bits: str) -> None:
    """Set the audio encoding bit depth."""
    encoding_map = {"16": Encoding.PCM16, "24": Encoding.PCM24, "32": Encoding.PCM32}
    client = DanteClient(host)
    await client.connect()
    try:
        await client.set_encoding(encoding_map[bits])
        click.echo(f"Encoding set to PCM {bits}-bit")
    finally:
        await client.close()


@config.command("latency")
@click.argument("host")
@click.argument("latency_us", type=int)
async def set_latency(host: str, latency_us: int) -> None:
    """Set the device latency in microseconds."""
    client = DanteClient(host)
    await client.connect()
    try:
        await client.set_latency(latency_us)
        click.echo(f"Latency set to {latency_us} us")
    finally:
        await client.close()


@config.command("aes67")
@click.argument("host")
@click.argument("state", type=click.Choice(["enable", "disable"]))
@click.option("--mac", default=None, help="Device MAC address (hex).")
async def set_aes67(host: str, state: str, mac: str | None) -> None:
    """Enable or disable AES67 mode."""
    client = DanteClient(host, mac_address=mac)
    await client.connect()
    try:
        await client.set_aes67(state == "enable")
        click.echo(f"AES67 {'enabled' if state == 'enable' else 'disabled'}")
    finally:
        await client.close()
