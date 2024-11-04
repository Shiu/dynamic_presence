"""Time platform for Dynamic Presence integration."""

# type: ignore[shadow-stdlib]

from __future__ import annotations
from datetime import datetime, time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DEFAULT_NIGHT_MODE_START,
    DEFAULT_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_END,
)
from .coordinator import DynamicPresenceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up time entities from config entry."""
    coordinator: DynamicPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        DynamicPresenceTime(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_{CONF_NIGHT_MODE_START}",
            key=CONF_NIGHT_MODE_START,
            default_time=DEFAULT_NIGHT_MODE_START,
        ),
        DynamicPresenceTime(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_{CONF_NIGHT_MODE_END}",
            key=CONF_NIGHT_MODE_END,
            default_time=DEFAULT_NIGHT_MODE_END,
        ),
    ]

    async_add_entities(entities)


class DynamicPresenceTime(  # pylint: disable=abstract-method
    CoordinatorEntity[DynamicPresenceCoordinator], TimeEntity
):
    """Time entity for Dynamic Presence."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        unique_id: str,
        key: str,
        default_time: str,
    ) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_suggested_object_id = key
        self._attr_translation_key = key
        self._key = key
        self._default_time = f"{default_time}:00"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> time | None:
        """Return the time value."""
        if self.coordinator.data is None:
            return None
        time_str = self.coordinator.data.get(f"time_{self._key}", self._default_time)
        try:
            return datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            return datetime.strptime(self._default_time, "%H:%M:%S").time()

    async def async_set_value(self, value: time) -> None:
        """Update the time."""
        await self.coordinator.async_time_changed(self._key, value.strftime("%H:%M:%S"))
