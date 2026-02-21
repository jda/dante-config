"""Exception hierarchy for the Dante client library."""

from __future__ import annotations


class DanteError(Exception):
    """Base exception for all Dante client errors."""


class DanteConnectionError(DanteError):
    """Failed to connect to a Dante device."""


class DanteTimeoutError(DanteError):
    """A command timed out waiting for a response."""


class DanteProtocolError(DanteError):
    """Received an invalid or unexpected protocol response."""


class DanteCommandError(DanteError):
    """A command was rejected or failed."""
