"""Shared test fixtures."""

import pytest


@pytest.fixture
def sample_mac() -> str:
    """Return a sample MAC address."""
    return "001122334455"
