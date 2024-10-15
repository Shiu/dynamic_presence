"""Number platform for Dynamic Presence integration."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_PRESENCE_TIMEOUT,
    DOMAIN,
)
from .entity import DynamicPresenceEntity

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceNumber(DynamicPresenceEntity, NumberEntity):
    """Representation of a Dynamic Presence number setting."""

    def __init__(self, entry: ConfigEntry, controller, key: str, name: str, min_value: float, max_value: float, step: float):
        """Initialize the number entity."""
        super().__init__(entry)
        self._controller = controller
        self._key = key
        self.entity_id = self.generate_entity_id("number", key)
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step

    @property
    def native_value(self) -> float:
        """Return the current value."""
        value = self._controller.config_entry.data.get(self._key)
        _LOGGER.debug("Getting native value for %s: %s", self._key, value)
        return value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.debug("Attempting to set %s to %s", self._key, value)
        if value != self.native_value:
            _LOGGER.info("Updating %s from %s to %s", self._key, self.native_value, value)
            new_data = dict(self._controller.config_entry.data)
            new_data[self._key] = value
            self.hass.config_entries.async_update_entry(self._controller.config_entry, data=new_data)
            # Temporarily comment out the controller update
            # await self._controller.async_update_config()
            _LOGGER.info("Updated %s to %s", self._key, value)
        else:
            _LOGGER.debug("Value for %s unchanged, skipping update", self._key)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence number entities."""
    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    async_add_entities([
        DynamicPresenceNumber(entry, controller, CONF_PRESENCE_TIMEOUT, "Presence Timeout", 0, 3600, 1),
        DynamicPresenceNumber(entry, controller, CONF_ACTIVE_ROOM_THRESHOLD, "Active Room Threshold", 0, 60, 1),
        DynamicPresenceNumber(entry, controller, CONF_ACTIVE_ROOM_TIMEOUT, "Active Room Timeout", 0, 3600, 1),
        DynamicPresenceNumber(entry, controller, CONF_NIGHT_MODE_TIMEOUT, "Night Mode Timeout", 0, 3600, 1),
    ])
