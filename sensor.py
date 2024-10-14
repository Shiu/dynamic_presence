"""Sensor platform for Dynamic Presence integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DynamicPresenceEntity


class DynamicPresenceTimerSensor(DynamicPresenceEntity, SensorEntity):
    """Representation of a Dynamic Presence timer sensor."""

    def __init__(self, config_entry: ConfigEntry, timer_type: str):
        """Initialize the sensor."""
        super().__init__(config_entry)
        self._timer_type = timer_type
        self._attr_name = f"{timer_type.replace('_', ' ').title()} Timer"
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{timer_type}_timer"

    @property
    def state(self):
        """Return the state of the sensor."""
        controller = self.hass.data[DOMAIN][self.config_entry.entry_id]["controller"]
        return controller.get_timer_state(self._timer_type)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence timer sensors."""
    timer_types = ["presence", "active_room", "night_mode"]
    entities = [DynamicPresenceTimerSensor(entry, timer_type) for timer_type in timer_types]
    async_add_entities(entities)
