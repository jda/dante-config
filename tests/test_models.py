"""Unit tests for data models."""

import pytest

from dante_config.const import SubscriptionStatus
from dante_config.models import (
    DanteChannel,
    DanteDeviceInfo,
    DanteServiceRecord,
    DanteSubscription,
)


class TestSubscriptionStatus:
    """Test SubscriptionStatus enum properties."""

    def test_connected_statuses(self) -> None:
        assert SubscriptionStatus.DYNAMIC.is_connected
        assert SubscriptionStatus.STATIC.is_connected
        assert SubscriptionStatus.MANUAL.is_connected
        assert SubscriptionStatus.SUBSCRIBE_SELF.is_connected

    def test_error_statuses(self) -> None:
        assert SubscriptionStatus.RESOLVE_FAIL.is_error
        assert SubscriptionStatus.NO_CONNECTION.is_error
        assert SubscriptionStatus.SYSTEM_FAIL.is_error
        assert SubscriptionStatus.QOS_FAIL_TX.is_error

    def test_transient_statuses(self) -> None:
        assert SubscriptionStatus.NONE.is_transient
        assert SubscriptionStatus.IN_PROGRESS.is_transient
        assert SubscriptionStatus.RESOLVED.is_transient

    def test_not_connected(self) -> None:
        assert not SubscriptionStatus.NONE.is_connected
        assert not SubscriptionStatus.RESOLVE_FAIL.is_connected

    def test_not_error(self) -> None:
        assert not SubscriptionStatus.DYNAMIC.is_error
        assert not SubscriptionStatus.NONE.is_error


class TestDanteSubscription:
    """Test DanteSubscription model."""

    def test_status_property(self) -> None:
        sub = DanteSubscription(
            rx_channel_name="RX1",
            rx_device_name="Dev",
            tx_channel_name="TX1",
            tx_device_name="Src",
            status_code=9,
        )
        assert sub.status == SubscriptionStatus.DYNAMIC
        assert sub.is_connected
        assert not sub.is_error

    def test_unknown_status_code(self) -> None:
        sub = DanteSubscription(
            rx_channel_name="RX1",
            rx_device_name="Dev",
            tx_channel_name="TX1",
            tx_device_name="Src",
            status_code=200,  # unknown
        )
        assert sub.status == SubscriptionStatus.NONE


class TestDanteDeviceInfo:
    """Test DanteDeviceInfo model."""

    def test_defaults(self) -> None:
        info = DanteDeviceInfo()
        assert info.name == ""
        assert info.tx_count == 0
        assert info.rx_count == 0
        assert info.tx_channels == {}
        assert info.rx_channels == {}
        assert info.subscriptions == []
        assert info.services == {}
        assert info.is_software is False

    def test_with_channels(self) -> None:
        tx = DanteChannel(number=1, name="TX-01", channel_type="tx")
        rx = DanteChannel(number=1, name="RX-01", channel_type="rx")
        info = DanteDeviceInfo(
            name="TestDevice",
            tx_count=1,
            rx_count=1,
            tx_channels={1: tx},
            rx_channels={1: rx},
        )
        assert info.tx_channels[1].name == "TX-01"
        assert info.rx_channels[1].name == "RX-01"


class TestDanteChannel:
    """Test DanteChannel model."""

    def test_defaults(self) -> None:
        ch = DanteChannel(number=1, name="Ch1", channel_type="tx")
        assert ch.friendly_name is None
        assert ch.status_code == 0
        assert ch.enabled is True

    def test_with_friendly_name(self) -> None:
        ch = DanteChannel(
            number=1,
            name="01",
            channel_type="tx",
            friendly_name="Main Left",
        )
        assert ch.friendly_name == "Main Left"
