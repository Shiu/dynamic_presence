"""Number platform for Dynamic Presence integration."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUMBER_CONFIG
from .entity import DynamicPresenceEntity

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceNumber(DynamicPresenceEntity, NumberEntity):
    """Representation of a Dynamic Presence number setting."""

    def __init__(self, entry: ConfigEntry, controller, key: str):
        """Initialize the number entity."""
        super().__init__(entry)
        self._controller = controller
        self._key = key
        self.entity_id = self.generate_entity_id("number", key)
        self._attr_name = NUMBER_CONFIG[key]["name"]
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_min_value = NUMBER_CONFIG[key]["min"]
        self._attr_native_max_value = NUMBER_CONFIG[key]["max"]
        self._attr_native_step = NUMBER_CONFIG[key]["step"]
        self._attr_native_unit_of_measurement = NUMBER_CONFIG[key]["unit"]

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._controller.config_entry.data.get(self._key, NUMBER_CONFIG[self._key]["default"])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self._controller.async_update_config({self._key: int(value)})
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._controller.async_add_listener(self._handle_coordinator_update)
        )

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence number entities."""
    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    async_add_entities([
        DynamicPresenceNumber(entry, controller, key)
        for key in NUMBER_CONFIG
    ])
