"""Time platform for Dynamic Presence integration."""
# type: ignore[attr-defined]  # Ignore Pylance warning about overriding stdlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    _hass: HomeAssistant,  # pylint: disable=unused-argument
    _entry: ConfigEntry,  # pylint: disable=unused-argument
    _async_add_entities: AddEntitiesCallback,  # pylint: disable=unused-argument
) -> None:
    """Set up time entities from config entry."""
    # Time settings are now handled through config entry options
    return
