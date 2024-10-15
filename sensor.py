"""Sensor platform for Dynamic Presence integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DynamicPresenceEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence sensor entities."""
    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    async_add_entities([DynamicPresenceStateSensor(entry, controller)])

class DynamicPresenceStateSensor(DynamicPresenceEntity, SensorEntity):
    """Representation of a Dynamic Presence state sensor."""

    def __init__(self, entry: ConfigEntry, controller):
        """Initialize the sensor entity."""
        super().__init__(entry)
        self._controller = controller
        self.entity_id = self.generate_entity_id("sensor", "state")
        self._attr_name = "State"
        self._attr_unique_id = f"{entry.entry_id}_state"

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{self.config_entry.entry_id}_update",
                self.async_write_ha_state
            )
        )

    @property
    def native_value(self) -> str:
        """Return the current state."""
        if self._controller.is_active_room:
            return "Active"
        if self._controller.presence_start_time is not None:
            return "Occupied"
        return "Vacant"

