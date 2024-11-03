"""Number platform for Dynamic Presence integration."""

# pylint: disable=W0223  # Method 'set_native_value' is abstract
# pylint: disable=W0239  # Method 'set_value' overrides final
# type: ignore[shadow-stdlib]

import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NIGHT_MODE_SCALE, CONF_ROOM_NAME, DOMAIN, NUMBER_CONFIG
from .coordinator import DynamicPresenceCoordinator

logNumber = logging.getLogger("dynamic_presence.number")


class DynamicPresenceNumber(NumberEntity):
    """Representation of a Dynamic Presence number setting."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        room: str,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the Dynamic Presence number entity."""
        super().__init__()
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room}_{description.key}"
        self._attr_name = f"dynamic_presence_{room}_{description.key}".replace(
            "_", " "
        ).title()
        self._attr_entity_id = f"number.dynamic_presence_{room}_{description.key}"
        self._attr_device_info = coordinator.get_device_info(room)

        # Number-specific attributes
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_native_min_value = description.native_min_value
        self._attr_native_max_value = description.native_max_value
        self._attr_native_step = description.native_step
        self._attr_mode = description.mode
        self._attr_native_value = coordinator.data.get(description.key)

    @property
    def unique_id(self):
        """Return the unique ID for the entity."""
        return self._attr_unique_id

    @property
    def native_value(self):
        """Return the current value."""
        value = self.coordinator.data.get(self.entity_description.key)
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        await self.coordinator.async_save_options(self.entity_description.key, value)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update_config(self, options: dict) -> None:
        """Update the entity's configuration."""
        if self._attr_native_value != options.get(self.entity_description.key):
            self._attr_native_value = options.get(self.entity_description.key)
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence number entities based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")

    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for key, config in NUMBER_CONFIG.items():
        entity = DynamicPresenceNumber(
            coordinator,
            room_name,
            NumberEntityDescription(
                key=key,
                name=config["name"],
                native_min_value=config["min"],
                native_max_value=config["max"],
                native_step=config["step"],
                native_unit_of_measurement=config["unit"],
                mode=NumberMode.BOX
                if key != CONF_NIGHT_MODE_SCALE
                else NumberMode.SLIDER,
            ),
        )
        entities.append(entity)

    async_add_entities(entities)
