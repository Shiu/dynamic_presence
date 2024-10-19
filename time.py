"""Time platform for Dynamic Presence integration."""
# type: ignore[name-shadowing]

from datetime import time
import logging

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
    DOMAIN,
)
from .entity import DynamicPresenceEntity

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceTime(DynamicPresenceEntity, TimeEntity):
    """Representation of a Dynamic Presence time setting."""

    def __init__(
        self, coordinator, config_entry: ConfigEntry, description: TimeEntityDescription
    ):
        """Initialize the Dynamic Presence time entity."""
        super().__init__(coordinator, config_entry, description)
        self._key = description.key
        _LOGGER.debug(
            "Initialized %s time entity for %s", self._key, coordinator.room_name
        )

    @property
    def native_value(self) -> time:
        """Get the current time value for the entity."""
        time_str = self._get_coordinator_value(
            self._key,
            DEFAULT_NIGHT_MODE_START
            if self._key == CONF_NIGHT_MODE_START
            else DEFAULT_NIGHT_MODE_END,
        )
        if time_str:
            hour, minute = map(int, time_str.split(":"))
            _LOGGER.debug("Retrieved time value for %s: %s", self._key, time_str)
            return time(hour, minute)
        _LOGGER.warning("No time value found for %s, using None", self._key)
        return None

    async def async_set_value(self, value: time) -> None:
        """Set a new time value for the entity."""
        time_str = value.strftime("%H:%M")
        _LOGGER.info("Setting new time value for %s: %s", self._key, time_str)
        await self.coordinator.async_update_config({self._key: time_str})
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence time entities based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info("Setting up time entities for %s", coordinator.room_name)

    entities = [
        DynamicPresenceTime(
            coordinator,
            entry,
            TimeEntityDescription(
                key=CONF_NIGHT_MODE_START,
                name="Night Mode Start",
                icon="mdi:clock-start",
            ),
        ),
        DynamicPresenceTime(
            coordinator,
            entry,
            TimeEntityDescription(
                key=CONF_NIGHT_MODE_END,
                name="Night Mode End",
                icon="mdi:clock-end",
            ),
        ),
    ]

    async_add_entities(entities)
    _LOGGER.debug("Added %d time entities for %s", len(entities), coordinator.room_name)
