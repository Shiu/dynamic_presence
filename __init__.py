"""The Dynamic Presence integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ROOM_NAME, DOMAIN
from .coordinator import DynamicPresenceCoordinator

PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dynamic Presence from a config entry."""
    _LOGGER.info("Setting up Dynamic Presence with entry: %s", entry.as_dict())
    _LOGGER.info("Current options: %s", entry.options)

    coordinator = DynamicPresenceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("Dynamic Presence setup completed")
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.info("Updating options: %s", entry.options)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_data_from_options(entry.options)
    await coordinator.async_request_refresh()

    # Reload the config entry
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    _LOGGER.info("Unloaded Dynamic Presence for %s", room_name)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
