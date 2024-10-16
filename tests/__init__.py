"""Tests for the Dynamic Presence integration."""
from unittest.mock import patch

from homeassistant.const import CONF_PLATFORM
from homeassistant.setup import async_setup_component

from ..const import DOMAIN


async def setup_dynamic_presence(hass, config=None):
    """Set up the Dynamic Presence integration in Home Assistant."""
    config = config or {
        DOMAIN: {
            CONF_PLATFORM: "test",
            "room_name": "Test Room",
            "presence_sensor": "binary_sensor.test_presence",
            "controlled_entities": ["light.test_light"],
        }
    }
    with patch("custom_components.dynamic_presence.async_setup_entry", return_value=True):
        assert await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

class MockConfigEntry:
    """Mock class for config entry."""

    def __init__(self, domain, data, options):
        """Initialize mock config entry."""
        self.domain = domain
        self.data = data
        self.options = options
        self.entry_id = "test_entry_id"

    def add_to_hass(self, hass):
        """Mock method to add entry to hass."""

def create_mock_dynamic_presence_config_entry(hass):
    """Create a mock Dynamic Presence config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "room_name": "Test Room",
            "presence_sensor": "binary_sensor.test_presence",
            "controlled_entities": ["light.test_light"],
        },
        options={},
    )
