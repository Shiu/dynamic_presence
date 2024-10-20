"""The Dynamic Presence integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError

from .const import (
    CONF_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_ROOM_NAME,
    DOMAIN,
)
from .controller import DynamicPresenceController

# Define the platforms used by this integration
PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dynamic Presence from a config entry."""
    _LOGGER.info("Setting up Dynamic Presence integration")

    # Initialize the domain data if it doesn't exist
    hass.data.setdefault(DOMAIN, {})

    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    _LOGGER.info("Setting up Dynamic Presence for room: %s", room_name)
    _LOGGER.debug("Config entry data: %s", entry.data)

    def raise_config_entry_not_ready(message: str):
        _LOGGER.error(message)
        raise ConfigEntryNotReady(message)

    try:
        # Create and set up the controller
        controller = DynamicPresenceController(hass, entry)
        _LOGGER.debug("DynamicPresenceController initialized for %s", room_name)

        setup_success = await controller.async_setup()
        _LOGGER.debug("Controller async_setup completed with result: %s", setup_success)

        if not setup_success:
            raise_config_entry_not_ready(
                f"Failed to set up Dynamic Presence for {room_name}"
            )
        else:
            # Store the controller in hass.data
            hass.data[DOMAIN][entry.entry_id] = controller

            # Set up all the platforms for this integration
            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

            # Register an update listener to handle config entry updates
            entry.async_on_unload(entry.add_update_listener(async_update_options))

            _LOGGER.info("Successfully set up Dynamic Presence for %s", room_name)
            return True

    except (HomeAssistantError, ConfigEntryNotReady) as ex:
        _LOGGER.exception(
            "Detailed error setting up Dynamic Presence for %s", room_name
        )
        raise ConfigEntryNotReady from ex


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for a config entry."""
    controller = hass.data[DOMAIN][entry.entry_id]
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    _LOGGER.info("Updating options for Dynamic Presence in %s", room_name)
    _LOGGER.debug("New options: %s", entry.options)

    # Check if night mode settings have changed
    night_mode_changed = any(
        entry.options.get(key) != entry.data.get(key)
        for key in [CONF_NIGHT_MODE_ENABLE, CONF_NIGHT_MODE_START, CONF_NIGHT_MODE_END]
    )

    if night_mode_changed:
        _LOGGER.info("Night mode settings have changed for %s", room_name)

    try:
        await controller.async_update_config(entry.options)
        _LOGGER.info("Successfully updated options for %s", room_name)
    except (HomeAssistantError, ValueError) as ex:
        _LOGGER.error("Failed to update options for %s: %s", room_name, ex)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    _LOGGER.info("Unloading Dynamic Presence integration for %s", room_name)

    controller = hass.data[DOMAIN][entry.entry_id]

    try:
        # Unload platforms first
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        if unload_ok:
            # Now unload the controller
            await controller.async_unload()
            hass.data[DOMAIN].pop(entry.entry_id)
            _LOGGER.info("Successfully unloaded Dynamic Presence for %s", room_name)
        else:
            _LOGGER.warning("Failed to unload all platforms for %s", room_name)

        return unload_ok
    except HomeAssistantError:
        _LOGGER.exception("Error unloading Dynamic Presence for %s", room_name)
        return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    _LOGGER.info(
        "Reloading Dynamic Presence for %s",
        entry.data.get(CONF_ROOM_NAME, "Unknown Room"),
    )
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
