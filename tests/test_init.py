"""Tests for the Dynamic Presence integration."""

from homeassistant.setup import async_setup_component


async def test_setup(hass):
    """Test the setup of the Dynamic Presence integration."""
    assert await async_setup_component(hass, "dynamic_presence", {})
    await hass.async_block_till_done()
    assert hass.data["dynamic_presence"] is not None
