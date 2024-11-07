"""Sensor platform for Dynamic Presence integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime, LIGHT_LUX
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DynamicPresenceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator: DynamicPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        DynamicPresenceSensor(
            coordinator=coordinator,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            unique_id=f"{entry.entry_id}_occupancy_duration",
            key="occupancy_duration",
        ),
        DynamicPresenceSensor(
            coordinator=coordinator,
            device_class=SensorDeviceClass.DURATION,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            unique_id=f"{entry.entry_id}_absence_duration",
            key="absence_duration",
        ),
        ManualStatesSensor(coordinator),
    ]

    if coordinator.light_sensor:
        entities.append(
            DynamicPresenceSensor(
                coordinator=coordinator,
                device_class=SensorDeviceClass.ILLUMINANCE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=LIGHT_LUX,
                unique_id=f"{entry.entry_id}_light_level",
                key="light_level",
            )
        )

    async_add_entities(entities)


class DynamicPresenceSensor(
    CoordinatorEntity[DynamicPresenceCoordinator], SensorEntity
):
    """Base sensor for Dynamic Presence."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass,
        unique_id: str,
        key: str,
        native_unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_unique_id = unique_id
        self._attr_suggested_object_id = key
        self._attr_translation_key = key
        self._key = key
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(f"sensor_{self._key}", 0)


class ManualStatesSensor(DynamicPresenceSensor):
    """Sensor showing manual states of all configured lights."""

    def __init__(self, coordinator: DynamicPresenceCoordinator) -> None:
        """Initialize the manual states sensor."""
        super().__init__(
            coordinator=coordinator,
            device_class=None,  # Text sensor has no device class
            state_class=None,  # Text sensor has no state class
            unique_id=f"{coordinator.entry.entry_id}_manual_states",
            key="manual_states",
            native_unit_of_measurement=None,
        )

    @property
    def native_value(self) -> str:
        """Return formatted string of manual states."""
        states = self.coordinator.manual_states
        if not states:
            return "No manual states"

        state_strings = []
        for light, is_on in states.items():
            state_strings.append(f"{light.split('.')[-1]}: {'ON' if is_on else 'OFF'}")
        return ", ".join(state_strings)
