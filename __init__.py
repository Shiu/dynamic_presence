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
    await coordinator.presence_detector.start_timer()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Dynamic Presence setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.presence_detector.stop_timer()
    _LOGGER.info("Unloaded Dynamic Presence for %s", room_name)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
