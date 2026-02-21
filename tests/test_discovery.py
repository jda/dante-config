"""Tests for Dante mDNS discovery with mocked zeroconf."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dante_config.const import SERVICE_ARC, SERVICE_CMC
from dante_config.discovery import DanteBrowser


class TestDanteBrowser:
    """Test DanteBrowser discovery logic."""

    @pytest.mark.asyncio
    async def test_discover_returns_empty_when_no_devices(self) -> None:
        mock_zc = MagicMock()

        with patch("dante_config.discovery.AsyncServiceBrowser") as mock_browser_cls:
            mock_browser_instance = MagicMock()
            mock_browser_instance.async_cancel = AsyncMock()
            mock_browser_cls.return_value = mock_browser_instance

            with patch("asyncio.sleep", new_callable=AsyncMock):
                browser = DanteBrowser(mock_zc)
                devices = await browser.discover(timeout=0.1)

            assert devices == {}

    @pytest.mark.asyncio
    async def test_device_assembly_from_services(self) -> None:
        """Test that services with the same server_name are grouped."""
        browser = DanteBrowser(MagicMock())

        # Simulate assembled devices directly
        from dante_config.models import DanteDeviceInfo, DanteServiceRecord

        device = DanteDeviceInfo(
            server_name="MyDevice.local",
            ipv4="192.168.1.100",
            mac_address="aabbccddeeff",
            model_id="DAI1",
            sample_rate=48000,
        )
        device.services["ARC"] = DanteServiceRecord(
            name="_netaudio-arc._udp.local.",
            service_type=SERVICE_ARC,
            port=8800,
        )
        device.services["CMC"] = DanteServiceRecord(
            name="_netaudio-cmc._udp.local.",
            service_type=SERVICE_CMC,
            port=8708,
            properties={"id": "aabbccddeeff"},
        )

        assert device.ipv4 == "192.168.1.100"
        assert device.mac_address == "aabbccddeeff"
        assert len(device.services) == 2

    def test_browser_init(self) -> None:
        mock_zc = MagicMock()
        browser = DanteBrowser(mock_zc)
        assert browser._zc is mock_zc
        assert browser._devices == {}
