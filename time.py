"""Time platform for Dynamic Presence integration."""
# type: ignore[name-shadowing]

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DynamicPresenceEntity


class DynamicPresenceTime(DynamicPresenceEntity, TimeEntity):
    """Representation of a Dynamic Presence time setting."""

    def __init__(self, entry: ConfigEntry, controller, key: str, name: str):
        """Initialize the time entity."""
        super().__init__(entry)
        self._controller = controller
        self._key = key
        self.entity_id = self.generate_entity_id("time", key)
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    @property
    def native_value(self) -> time:
        """Return the current time value."""
        time_str = self._controller.config_entry.data.get(self._key)
        if time_str:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        return None

    async def async_set_value(self, value: time) -> None:
        """Update the current value."""
        time_str = value.strftime("%H:%M")
        changes = {self._key: time_str}
        await self._controller.async_update_config(changes)
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence time entities."""
    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    async_add_entities([
        DynamicPresenceTime(entry, controller, "night_mode_start", "Night Mode Start"),
        DynamicPresenceTime(entry, controller, "night_mode_end", "Night Mode End"),
    ])
