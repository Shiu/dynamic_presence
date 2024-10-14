"""Number platform for Dynamic Presence integration."""
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


class DynamicPresenceNumber(DynamicPresenceEntity, NumberEntity):
    """Representation of a Dynamic Presence number setting."""

    def __init__(self, config_entry: ConfigEntry, key: str, name: str, min_value: float, max_value: float, step: float) -> None:
        """Initialize the number entity."""
        super().__init__(config_entry)
        self._key = key
        self._attr_name = f"{name}"
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{key}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.hass.data[DOMAIN][self.config_entry.entry_id].get("data", {}).get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self.hass.data[DOMAIN][self.config_entry.entry_id]["data"][self._key] = value
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence number entities."""
    entities = [
        DynamicPresenceNumber(entry, CONF_PRESENCE_TIMEOUT, "Presence Timeout", 0, 3600, 1),
        DynamicPresenceNumber(entry, CONF_ACTIVE_ROOM_THRESHOLD, "Active Room Threshold", 0, 60, 1),
        DynamicPresenceNumber(entry, CONF_ACTIVE_ROOM_TIMEOUT, "Active Room Timeout", 0, 3600, 1),
        DynamicPresenceNumber(entry, CONF_NIGHT_MODE_TIMEOUT, "Night Mode Timeout", 0, 3600, 1),
    ]
    async_add_entities(entities)
