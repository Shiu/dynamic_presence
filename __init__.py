"""Dynamic Presence Integration for Home Assistant.

This integration provides automatic light control based on room presence.
Features:
- Automatic light control based on presence detection
- Configurable timeouts for presence detection
- Night mode with separate light control
- Manual override handling
- Light sensor integration
- Adjacent room control
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
)
from homeassistant.core import HomeAssistant

from .const import CONF_ADJACENT_ROOMS, DOMAIN
from .coordinator import DynamicPresenceCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dynamic Presence from a config entry."""
    coordinator = DynamicPresenceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_clear_adjacent_room_references(
    hass: HomeAssistant, removed_entry_id: str
) -> None:
    """Remove references to a room from all other rooms' adjacent rooms lists."""
    entries = hass.config_entries.async_entries(DOMAIN)

    for entry in entries:
        if entry.entry_id != removed_entry_id:  # Skip the room being removed
            adjacent_rooms = entry.options.get(CONF_ADJACENT_ROOMS, [])
            if removed_entry_id in adjacent_rooms:
                # Remove the deleted room from adjacent_rooms
                new_adjacent_rooms = [
                    room for room in adjacent_rooms if room != removed_entry_id
                ]
                new_options = dict(entry.options)
                new_options[CONF_ADJACENT_ROOMS] = new_adjacent_rooms

                # Update the config entry
                hass.config_entries.async_update_entry(
                    entry,
                    options=new_options,
                )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await async_clear_adjacent_room_references(hass, entry.entry_id)
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)
