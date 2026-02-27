"""Top-level CLI group with AsyncZeroconf lifecycle."""

from __future__ import annotations

try:
    import asyncclick as click
except ImportError:
    raise SystemExit(
        "The dante CLI requires additional dependencies. "
        "Install with: pip install dante-config[cli]"
    ) from None

from .commands.channel import channel
from .commands.config import config
from .commands.device import device
from .commands.discover import discover
from .commands.subscription import subscription


@click.group()
@click.pass_context
async def cli(ctx: click.Context) -> None:
    """Dante audio networking device control CLI."""
    ctx.ensure_object(dict)


cli.add_command(discover)
cli.add_command(device)
cli.add_command(channel)
cli.add_command(subscription)
cli.add_command(config)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
