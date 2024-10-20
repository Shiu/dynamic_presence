"""Number platform for Dynamic Presence integration."""

import logging

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, UpdateFailed

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_NIGHT_MODE_SCALE,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_PRESENCE_TIMEOUT,
    DOMAIN,
    NUMBER_CONFIG,
)
from .controller import DynamicPresenceController

_LOGGER = logging.getLogger(__name__)


# pylint: disable=abstract-method
class DynamicPresenceNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Dynamic Presence number setting."""

    def __init__(
        self,
        coordinator: DynamicPresenceController,
        description: NumberEntityDescription,
    ) -> None:
        """Initialize the Dynamic Presence number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_name = description.name

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator is None or self.coordinator.data is None:
            _LOGGER.error(
                "Coordinator or coordinator data is None for %s", self.entity_id
            )
            return None

        value = self.coordinator.data.get(
            self.entity_description.key,
            NUMBER_CONFIG[self.entity_description.key]["default"],
        )
        _LOGGER.debug("Value for %s: %s", self.entity_id, value)
        return float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the new value of the number entity."""
        _LOGGER.info("Setting new value for %s: %s", self.entity_description.key, value)
        try:
            await self.coordinator.async_update_config(
                {self.entity_description.key: int(value)}
            )
        except Exception as e:
            _LOGGER.error(
                "Failed to set value for %s: %s", self.entity_description.key, e
            )
            raise UpdateFailed(
                f"Failed to set value for {self.entity_description.key}"
            ) from e


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence number entities based on a config entry."""
    controller: DynamicPresenceController = hass.data[DOMAIN][entry.entry_id]

    _LOGGER.info("Setting up number entities for %s", controller.room_name)

    # Wait for the coordinator to complete its first update
    await controller.async_config_entry_first_refresh()

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

    entities = [DynamicPresenceNumber(controller, desc) for desc in number_descriptions]

    async_add_entities(entities)
    _LOGGER.debug(
        "Added %d number entities for %s", len(entities), controller.room_name
    )
