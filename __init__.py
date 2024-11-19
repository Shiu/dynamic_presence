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

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


from .const import CONF_ADJACENT_ROOMS, DOMAIN
from .coordinator import DynamicPresenceCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

logInit = logging.getLogger("dynamic_presence.init")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dynamic Presence from a config entry."""
    coordinator = DynamicPresenceCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

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
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Log initial state
    logInit.debug(
        "Options update for %s - Current options: %s",
        coordinator.room_name,
        entry.options,
    )

    # Store previous state and configuration
    had_night_mode = coordinator.has_night_mode
    had_light_sensor = coordinator.has_light_sensor
    adjacent_rooms = entry.options.get(CONF_ADJACENT_ROOMS, [])

    logInit.debug("Stored adjacent rooms before update: %s", adjacent_rooms)

    # Update coordinator
    coordinator.update_from_options(entry)

    if (
        coordinator.has_night_mode != had_night_mode
        or coordinator.has_light_sensor != had_light_sensor
    ):
        logInit.debug(
            "Configuration changed - night_mode: %s -> %s, light_sensor: %s -> %s",
            had_night_mode,
            coordinator.has_night_mode,
            had_light_sensor,
            coordinator.has_light_sensor,
        )

        # Clean up entity registry first
        ent_reg = er.async_get(hass)
        entries = er.async_entries_for_config_entry(ent_reg, entry.entry_id)

        # Remove entities that shouldn't exist anymore
        for entity_entry in entries:
            if (
                not coordinator.has_night_mode
                and "night" in entity_entry.unique_id
                or not coordinator.has_light_sensor
                and "light_level" in entity_entry.unique_id
            ):
                logInit.debug("Removing entity: %s", entity_entry.entity_id)
                ent_reg.async_remove(entity_entry.entity_id)

        # Create new options with preserved adjacent rooms
        new_options = dict(entry.options)
        new_options[CONF_ADJACENT_ROOMS] = adjacent_rooms

        logInit.debug("Updating entry with new options: %s", new_options)

        # Update entry with preserved adjacent rooms
        hass.config_entries.async_update_entry(
            entry,
            options=new_options,
        )

        logInit.debug("Entry options after update: %s", entry.options)

        # Trigger a reload of the entry
        await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    # First unload the entry
    await async_unload_entry(hass, entry)

    # Then clear references from other rooms
    await async_clear_adjacent_room_references(hass, entry.entry_id)
