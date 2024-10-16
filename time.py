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
    """Representation of a Dynamic Presence time setting.

    This class extends DynamicPresenceEntity and TimeEntity to provide
    functionality for time-based settings in the Dynamic Presence integration.
    """

    def __init__(self, coordinator, config_entry: ConfigEntry, description: TimeEntityDescription):
        """Initialize the Dynamic Presence time entity.

        Args:
            coordinator: The data update coordinator.
            config_entry: The config entry containing integration configuration.
            description: TimeEntityDescription object with entity metadata.

        """
        super().__init__(coordinator, config_entry, description)
        self._key = description.key

    @property
    def native_value(self) -> time:
        """Get the current time value for the entity.

        Returns:
            A time object representing the current value, or None if not set.

        """
        time_str = self._get_coordinator_value(
            self._key,
            DEFAULT_NIGHT_MODE_START if self._key == CONF_NIGHT_MODE_START else DEFAULT_NIGHT_MODE_END
        )
        if time_str:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        return None

    async def async_set_value(self, value: time) -> None:
        """Set a new time value for the entity.

        Args:
        value: The new time value to set.

        """
        time_str = value.strftime("%H:%M")
        await self.coordinator.async_update_config({self._key: time_str})
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Dynamic Presence time entities based on a config entry.

    This function is called when a new config entry is added to set up the time entities
    for the Dynamic Presence integration.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for which to set up entities.
        async_add_entities: Callback to add new entities to Home Assistant.

    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DynamicPresenceTime(coordinator, entry, TimeEntityDescription(
            key=CONF_NIGHT_MODE_START,
            name="Night Mode Start",
            icon="mdi:clock-start",
        )),
        DynamicPresenceTime(coordinator, entry, TimeEntityDescription(
            key=CONF_NIGHT_MODE_END,
            name="Night Mode End",
            icon="mdi:clock-end",
        )),
    ])
