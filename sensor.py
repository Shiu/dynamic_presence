"""Sensor platform for Dynamic Presence integration."""

import logging
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTime
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, CONF_ROOM_NAME
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence sensor based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    _LOGGER.info("Setting up Dynamic Presence sensors for %s", room_name)

    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        DynamicPresenceSensor(
            coordinator, "presence_duration", "Presence Duration", UnitOfTime.SECONDS
        ),
        DynamicPresenceSensor(
            coordinator, "absence_duration", "Absence Duration", UnitOfTime.SECONDS
        ),
        DynamicPresenceSensor(
            coordinator, "active_room_status", "Active Room Status", None
        ),
        DynamicPresenceSensor(
            coordinator, "presence_sensor_state", "Presence Sensor State", None
        ),
        DynamicPresenceSensor(
            coordinator, "night_mode_status", "Night Mode Status", None
        ),
    ]

    async_add_entities(sensors)
    _LOGGER.debug("Added %d Dynamic Presence sensors for %s", len(sensors), room_name)


class DynamicPresenceSensor(SensorEntity):
    """Representation of a Dynamic Presence sensor."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        key: str,
        name: str,
        unit: str | None,
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._key = key
        self._attr_name = f"Dynamic Presence {name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": f"Dynamic Presence {coordinator.entry.data.get(CONF_ROOM_NAME, 'Unknown Room')}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity."""
        await self.coordinator.async_request_refresh()
