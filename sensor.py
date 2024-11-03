"""Sensor platform for Dynamic Presence integration."""

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dynamic Presence sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    room_name = entry.data.get("room_name", "Unknown Room").lower().replace(" ", "_")

    sensors = []
    binary_sensors = []

    # Add binary sensors
    for key in ["occupancy_state", "active_room_status", "night_mode_status"]:
        binary_sensors.append(
            DynamicPresenceBinarySensor(
                coordinator,
                f"{room_name}_{key}",
                room_name,
            )
        )

    # Add regular sensors
    for key in [
        "occupancy_duration",
        "absence_duration",
        "remote_control_duration",
        "light_level",
    ]:
        sensors.append(
            DynamicPresenceSensor(
                coordinator,
                f"{room_name}_{key}",
                room_name,
            )
        )

    async_add_entities(sensors + binary_sensors)


class DynamicPresenceBinarySensor(BinarySensorEntity):
    """Binary sensor for Dynamic Presence."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key, room_name) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._key = key
        self._room_name = room_name
        self._attr_unique_id = f"dynamic_presence_{self._key}"
        self._attr_device_info = coordinator.get_device_info(room_name)
        self._attr_name = key.replace(f"{room_name}_", "").replace("_", " ").title()

        # Set device class and icon based on sensor type
        if key.endswith("occupancy_state"):
            self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        elif key.endswith("active_room_status"):
            self._attr_icon = "mdi:home-circle"

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key) == "on"


class DynamicPresenceSensor(SensorEntity):
    """Sensor for Dynamic Presence."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, key, room_name) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._key = key
        self._room_name = room_name
        self._attr_unique_id = f"dynamic_presence_{self._key}"
        self._attr_device_info = coordinator.get_device_info(room_name)
        self._attr_name = key.replace(f"{room_name}_", "").replace("_", " ").title()

        # Set device class and state class based on sensor type
        if key.endswith(
            ("occupancy_duration", "absence_duration", "remote_control_duration")
        ):
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key.endswith("light_level"):
            self._attr_device_class = SensorDeviceClass.ILLUMINANCE
            self._attr_native_unit_of_measurement = "lx"
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
