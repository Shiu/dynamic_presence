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
    """Representation of a Dynamic Presence number setting."""

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        description: NumberEntityDescription,
    ):
        """Initialize the Dynamic Presence number entity."""
        super().__init__(coordinator, config_entry, description)
        self._key = description.key
        _LOGGER.debug(
            "Initialized %s number entity for %s", self._key, coordinator.room_name
        )

    @property
    def native_value(self) -> float:
        """Return the current value of the number entity."""
        value = self._get_coordinator_value(
            self._key, NUMBER_CONFIG[self._key]["default"]
        )
        _LOGGER.debug("Retrieved value for %s: %s", self._key, value)
        return value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value of the number entity."""
        _LOGGER.info("Setting new value for %s: %s", self._key, value)
        await self.coordinator.async_update_config({self._key: int(value)})
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence number entities based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info("Setting up number entities for %s", coordinator.room_name)

    async_add_entities(
        [
            DynamicPresenceNumber(
                coordinator,
                entry,
                NumberEntityDescription(
                    key=CONF_PRESENCE_TIMEOUT,
                    name=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["name"],
                    native_min_value=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["min"],
                    native_max_value=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["max"],
                    native_step=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["step"],
                    native_unit_of_measurement=NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT][
                        "unit"
                    ],
                ),
            ),
            DynamicPresenceNumber(
                coordinator,
                entry,
                NumberEntityDescription(
                    key=CONF_ACTIVE_ROOM_THRESHOLD,
                    name=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["name"],
                    native_min_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["min"],
                    native_max_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["max"],
                    native_step=NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["step"],
                    native_unit_of_measurement=NUMBER_CONFIG[
                        CONF_ACTIVE_ROOM_THRESHOLD
                    ]["unit"],
                ),
            ),
            DynamicPresenceNumber(
                coordinator,
                entry,
                NumberEntityDescription(
                    key=CONF_ACTIVE_ROOM_TIMEOUT,
                    name=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["name"],
                    native_min_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["min"],
                    native_max_value=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["max"],
                    native_step=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["step"],
                    native_unit_of_measurement=NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT][
                        "unit"
                    ],
                ),
            ),
            DynamicPresenceNumber(
                coordinator,
                entry,
                NumberEntityDescription(
                    key=CONF_NIGHT_MODE_TIMEOUT,
                    name=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["name"],
                    native_min_value=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["min"],
                    native_max_value=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["max"],
                    native_step=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["step"],
                    native_unit_of_measurement=NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT][
                        "unit"
                    ],
                ),
            ),
            DynamicPresenceNumber(
                coordinator,
                entry,
                NumberEntityDescription(
                    key=CONF_NIGHT_MODE_SCALE,
                    name=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["name"],
                    native_min_value=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["min"],
                    native_max_value=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["max"],
                    native_step=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["step"],
                    native_unit_of_measurement=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE][
                        "unit"
                    ],
                ),
            ),
        ]
    )
    _LOGGER.debug("Added 5 number entities for %s", coordinator.room_name)
