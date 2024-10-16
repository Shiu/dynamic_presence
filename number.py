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
    DOMAIN,
    NUMBER_CONFIG,
)
from .entity import DynamicPresenceEntity

_LOGGER = logging.getLogger(__name__)

class DynamicPresenceNumber(DynamicPresenceEntity, NumberEntity):
    """Representation of a Dynamic Presence number setting.

    This class extends DynamicPresenceEntity and NumberEntity to provide
    functionality for numeric settings in the Dynamic Presence integration.
    """

    def __init__(self, coordinator, config_entry: ConfigEntry, description: NumberEntityDescription):
        """Initialize the Dynamic Presence number entity.

        Args:
            coordinator: The data update coordinator.
            config_entry: The config entry containing integration configuration.
            description: NumberEntityDescription object with entity metadata.

        """
        super().__init__(coordinator, config_entry, description)
        self._key = description.key

    @property
    def native_value(self) -> float:
        """Return the current value of the number entity.

        Returns:
            The current value as a float, or the default value if not set.

        """
        return self._get_coordinator_value(self._key, NUMBER_CONFIG[self._key]["default"])

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value of the number entity.

        Args:
            value: The new value to set.

        """
        await self.coordinator.async_update_config({self._key: int(value)})
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Dynamic Presence number entities based on a config entry.

    This function is called when a new config entry is added to set up the number entities
    for the Dynamic Presence integration.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for which to set up entities.
        async_add_entities: Callback to add new entities to Home Assistant.

    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DynamicPresenceNumber(coordinator, entry, NumberEntityDescription(
            key=CONF_PRESENCE_TIMEOUT,
            name=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["name"],
            native_min_value=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["min"],
            native_max_value=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["max"],
            native_step=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["unit"],
        )),
        DynamicPresenceNumber(coordinator, entry, NumberEntityDescription(
            key=CONF_ACTIVE_ROOM_THRESHOLD,
            name=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["name"],
            native_min_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["min"],
            native_max_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["max"],
            native_step=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["unit"],
        )),
        DynamicPresenceNumber(coordinator, entry, NumberEntityDescription(
            key=CONF_ACTIVE_ROOM_TIMEOUT,
            name=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["name"],
            native_min_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["min"],
            native_max_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["max"],
            native_step=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["unit"],
        )),
        DynamicPresenceNumber(coordinator, entry, NumberEntityDescription(
            key=CONF_NIGHT_MODE_TIMEOUT,
            name=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["name"],
            native_min_value=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["min"],
            native_max_value=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["max"],
            native_step=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["unit"],
        )),
        DynamicPresenceNumber(coordinator, entry, NumberEntityDescription(
            key=CONF_NIGHT_MODE_SCALE,
            name=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["name"],
            native_min_value=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["min"],
            native_max_value=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["max"],
            native_step=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["step"],
            native_unit_of_measurement=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["unit"],
        )),
    ])
