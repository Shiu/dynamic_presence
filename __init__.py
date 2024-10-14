"""The Dynamic Presence integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .controller import DynamicPresenceController

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.NUMBER, Platform.TIME, Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dynamic Presence from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    controller = DynamicPresenceController(hass, entry)
    await controller.async_setup()

    hass.data[DOMAIN][entry.entry_id] = {
        "controller": controller,
    }

    # Set up all platforms for this device/entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entry when its updated
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        controller = hass.data[DOMAIN][entry.entry_id]["controller"]
        await controller.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
