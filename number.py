"""Number platform for Dynamic Presence integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime, LIGHT_LUX
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_DETECTION_TIMEOUT,
    CONF_LONG_TIMEOUT,
    CONF_SHORT_TIMEOUT,
    CONF_LIGHT_THRESHOLD,
    CONF_LIGHT_SENSOR,
)
from .coordinator import DynamicPresenceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up numbers from a config entry."""
    coordinator: DynamicPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        DynamicPresenceNumber(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_detection_timeout",
            key=CONF_DETECTION_TIMEOUT,
            native_min_value=1,
            native_max_value=60,
            native_step=1,
            native_unit_of_measurement=UnitOfTime.SECONDS,
        ),
        DynamicPresenceNumber(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_long_timeout",
            key=CONF_LONG_TIMEOUT,
            native_min_value=1,
            native_max_value=3600,
            native_step=1,
            native_unit_of_measurement=UnitOfTime.SECONDS,
        ),
        DynamicPresenceNumber(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_short_timeout",
            key=CONF_SHORT_TIMEOUT,
            native_min_value=1,
            native_max_value=300,
            native_step=1,
            native_unit_of_measurement=UnitOfTime.SECONDS,
        ),
    ]

    # Only add light threshold if light sensor is configured
    if coordinator.light_sensor or entry.options.get(CONF_LIGHT_SENSOR):
        entities.append(
            DynamicPresenceNumber(
                coordinator=coordinator,
                unique_id=f"{entry.entry_id}_light_threshold",
                key=CONF_LIGHT_THRESHOLD,
                native_min_value=0,
                native_max_value=1000,
                native_step=1,
                native_unit_of_measurement=LIGHT_LUX,
            )
        )

    async_add_entities(entities)


class DynamicPresenceNumber(  # pylint: disable=abstract-method
    CoordinatorEntity[DynamicPresenceCoordinator], NumberEntity
):
    """Number entity for Dynamic Presence."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        unique_id: str,
        key: str,
        native_min_value: float,
        native_max_value: float,
        native_step: float,
        native_unit_of_measurement: str | None = None,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_suggested_object_id = key
        self._attr_translation_key = key
        self._key = key
        self._attr_native_min_value = native_min_value
        self._attr_native_max_value = native_max_value
        self._attr_native_step = native_step
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(
            f"number_{self._key}", self.coordinator.entry.options.get(self._key)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.coordinator.async_number_changed(self._key, value)
