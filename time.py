"""Time platform for Dynamic Presence integration."""
from datetime import datetime, time  # type: ignore[name-shadowing]

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NIGHT_MODE_END, CONF_NIGHT_MODE_START, DOMAIN
from .entity import DynamicPresenceEntity


class DynamicPresenceTime(DynamicPresenceEntity, TimeEntity):
    """Representation of a Dynamic Presence time setting."""

    def __init__(self, config_entry: ConfigEntry, key: str, name: str) -> None:
        """Initialize the time entity."""
        super().__init__(config_entry)
        self._key = key
        self._attr_name = f"{name}"
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{key}"

    @property
    def native_value(self) -> time:
        """Return the time value."""
        time_str = self.hass.data[DOMAIN][self.config_entry.entry_id].get("data", {}).get(self._key, "00:00")
        try:
            # Try parsing with seconds
            return datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            # If that fails, try parsing without seconds
            return datetime.strptime(time_str, "%H:%M").time()

    async def async_set_value(self, value: time) -> None:
        """Set the time."""
        time_str = value.strftime("%H:%M")
        self.hass.data[DOMAIN][self.config_entry.entry_id]["data"][self._key] = time_str
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence time entities."""
    entities = [
        DynamicPresenceTime(entry, CONF_NIGHT_MODE_START, "Night Mode Start"),
        DynamicPresenceTime(entry, CONF_NIGHT_MODE_END, "Night Mode End"),
    ]
    async_add_entities(entities)
