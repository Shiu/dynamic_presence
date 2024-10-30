"""Sensor platform for Dynamic Presence integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ROOM_NAME, DOMAIN, SENSOR_KEYS
from .coordinator import DynamicPresenceCoordinator


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
        self.coordinator = coordinator
        self._key = f"{room}_{key}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{self._key}"
        self._attr_name = f"dynamic_presence_{room}_{key}".replace("_", " ").title()
        self._attr_entity_id = f"sensor.dynamic_presence_{self._key}"
        self._attr_device_info = coordinator.get_device_info(room)
        self._attr_native_unit_of_measurement = unit

        # Set appropriate device class, state class and icon based on sensor type
        if "duration" in self._key:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:timer-outline"
        elif "light_level" in self._key:
            self._attr_device_class = SensorDeviceClass.ILLUMINANCE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:brightness-5"
        elif "active_room_status" in self._key:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["on", "off"]
            self._attr_icon = "mdi:home-circle"
        elif "night_mode_status" in self._key:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["on", "off"]
            self._attr_icon = "mdi:weather-night"
        elif "occupancy_state" in self._key:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["on", "off"]
            self._attr_icon = "mdi:motion-sensor"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._key.endswith("active_room_status"):
            return "on" if self.coordinator.is_active else "off"
        if self._key.endswith("night_mode_status"):
            return (
                "on" if self.coordinator.data.get("night_mode_active", False) else "off"
            )
        if self._key.endswith("occupancy_state"):
            return self.coordinator.data.get(self._key, "off")

        value = self.coordinator.data.get(self._key)
        if "duration" in self._key:
            return int(value) if value is not None else 0
        return value

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
