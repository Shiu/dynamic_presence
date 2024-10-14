"""The Dynamic Presence integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_PRESENCE_TIMEOUT,
    DOMAIN,
)
from .controller import DynamicPresenceController

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.NUMBER, Platform.TIME, Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Dynamic Presence component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dynamic Presence from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Ensure all required configuration values are present
    config = dict(entry.data)
    config.setdefault(CONF_PRESENCE_TIMEOUT, 300)
    config.setdefault(CONF_ACTIVE_ROOM_THRESHOLD, 15)
    config.setdefault(CONF_ACTIVE_ROOM_TIMEOUT, 600)
    config.setdefault(CONF_NIGHT_MODE_START, "22:00")
    config.setdefault(CONF_NIGHT_MODE_END, "07:00")
    config.setdefault(CONF_NIGHT_MODE_TIMEOUT, 60)

    # Update the existing entry
    hass.config_entries.async_update_entry(entry, data=config)

    controller = DynamicPresenceController(hass, entry)
    await controller.async_setup()

    hass.data[DOMAIN][entry.entry_id] = {
        "controller": controller,
        "config": config,
        "data": config.copy()  # Initialize data with config values
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        controller = hass.data[DOMAIN][entry.entry_id]["controller"]
        await controller.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)
