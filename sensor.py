"""Sensor platform for Dynamic Presence integration."""

import logging
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTime
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_ROOM_NAME,
    SENSOR_KEYS,
)
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence sensor based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        DynamicPresenceSensor(
            coordinator,
            room_name,
            key,
            key.replace("_", " ").title(),
            UnitOfTime.SECONDS if "duration" in key else None,
        )
        for key in SENSOR_KEYS
    ]

    async_add_entities(sensors)
    _LOGGER.debug("Added %d Dynamic Presence sensors for %s", len(sensors), room_name)


class DynamicPresenceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Dynamic Presence sensor."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        room: str,
        key: str,
        name: str,
        unit: str | None,
    ) -> None:
        """Initialize the Dynamic Presence sensor."""
        super().__init__(coordinator)
        self._key = f"{room}_{key}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{self._key}"
        self._attr_has_entity_name = True
        self._attr_name = name
        self.entity_id = f"sensor.dynamic_presence_{self._key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = coordinator.get_device_info(room)
        _LOGGER.debug("Initialized sensor: %s with key: %s", self.entity_id, self._key)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self._key)
        _LOGGER.debug("Sensor %s returning value: %s", self.entity_id, value)
        return value

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug("Sensor %s added to hass", self.entity_id)
