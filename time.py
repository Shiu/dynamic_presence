"""Time platform for Dynamic Presence integration."""

from datetime import time
import logging

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_ROOM_NAME,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
    DOMAIN,
)
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence time entities based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    _LOGGER.info("Setting up time entities for %s", room_name)

    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        DynamicPresenceTime(coordinator, CONF_NIGHT_MODE_START, "Night Mode Start"),
        DynamicPresenceTime(coordinator, CONF_NIGHT_MODE_END, "Night Mode End"),
    ]

    async_add_entities(entities)
    _LOGGER.debug("Added %d time entities for %s", len(entities), room_name)


class DynamicPresenceTime(TimeEntity):
    """Representation of a Dynamic Presence time setting."""

    def __init__(
        self, coordinator: DynamicPresenceCoordinator, key: str, name: str
    ) -> None:
        """Initialize the time entity."""
        self.coordinator = coordinator
        self._key = key
        self._attr_name = f"Dynamic Presence {name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": f"Dynamic Presence {coordinator.entry.data.get(CONF_ROOM_NAME, 'Unknown Room')}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
        }

    @property
    def native_value(self) -> time:
        """Return the time value."""
        default_value = (
            DEFAULT_NIGHT_MODE_START
            if self._key == CONF_NIGHT_MODE_START
            else DEFAULT_NIGHT_MODE_END
        )
        value = self.coordinator.data.get(self._key, default_value)
        if isinstance(value, str):
            try:
                hours, minutes = map(int, value.split(":"))
                return time(hour=hours, minute=minutes)
            except ValueError:
                _LOGGER.error("Invalid time format for %s: %s", self._key, value)
        return time(
            hour=int(default_value.split(":", maxsplit=1)[0]),
            minute=int(default_value.split(":", maxsplit=1)[1]),
        )

    async def async_set_value(self, value: time) -> None:
        """Set the time value."""
        await self.coordinator.async_update_time(self._key, value.strftime("%H:%M"))

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
