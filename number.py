"""Number platform for Dynamic Presence integration."""

import logging

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_NIGHT_MODE_SCALE,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_PRESENCE_TIMEOUT,
    CONF_ROOM_NAME,
    DOMAIN,
    NUMBER_CONFIG,
)
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceNumber(NumberEntity):
    """Representation of a Dynamic Presence number setting."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the Dynamic Presence number entity."""
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_name = f"Dynamic Presence {description.name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": f"Dynamic Presence {coordinator.entry.data.get(CONF_ROOM_NAME, 'Unknown Room')}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return float(
            self.coordinator.data.get(
                self.entity_description.key,
                NUMBER_CONFIG[self.entity_description.key]["default"],
            )
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the new value of the number entity."""
        await self.coordinator.async_update_number(
            self.entity_description.key, int(value)
        )

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence number entities based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    number_descriptions = [
        NumberEntityDescription(
            key=CONF_PRESENCE_TIMEOUT,
            name=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["name"],
            native_min_value=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["min"],
            native_max_value=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["max"],
            native_step=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["unit"],
        ),
        NumberEntityDescription(
            key=CONF_ACTIVE_ROOM_THRESHOLD,
            name=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["name"],
            native_min_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["min"],
            native_max_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["max"],
            native_step=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD][
                "unit"
            ],
        ),
        NumberEntityDescription(
            key=CONF_ACTIVE_ROOM_TIMEOUT,
            name=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["name"],
            native_min_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["min"],
            native_max_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["max"],
            native_step=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["unit"],
        ),
        NumberEntityDescription(
            key=CONF_NIGHT_MODE_TIMEOUT,
            name=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["name"],
            native_min_value=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["min"],
            native_max_value=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["max"],
            native_step=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["unit"],
        ),
        NumberEntityDescription(
            key=CONF_NIGHT_MODE_SCALE,
            name=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["name"],
            native_min_value=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["min"],
            native_max_value=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["max"],
            native_step=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["unit"],
        ),
    ]

    entities = [
        DynamicPresenceNumber(coordinator, desc) for desc in number_descriptions
    ]
    async_add_entities(entities)
