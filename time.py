"""Time platform for Dynamic Presence integration."""
from datetime import time  # type: ignore[name-shadowing]

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NIGHT_MODE_END, CONF_NIGHT_MODE_START, DOMAIN
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
        time_str = self._controller.config_entry.data.get(self._key, "00:00")
        hour, minute = map(int, time_str.split(":"))
        return time(hour, minute)

    async def async_set_value(self, value: time) -> None:
        """Update the current time value."""
        new_data = dict(self._controller.config_entry.data)
        new_data[self._key] = value.strftime("%H:%M")
        self.hass.config_entries.async_update_entry(self._controller.config_entry, data=new_data)
        await self._controller.async_update_config()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence time entities."""
    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    async_add_entities([
        DynamicPresenceTime(entry, controller, CONF_NIGHT_MODE_START, "Night Mode Start"),
        DynamicPresenceTime(entry, controller, CONF_NIGHT_MODE_END, "Night Mode End"),
    ])
