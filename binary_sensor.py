"""Binary sensor platform for Dynamic Presence integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up binary sensors from config entry."""
    coordinator: DynamicPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            DynamicPresenceBinarySensor(
                coordinator=coordinator,
                unique_id=f"{entry.entry_id}_occupancy",
                key="occupancy",
                device_class=BinarySensorDeviceClass.OCCUPANCY,
            )
        ]
    )


class DynamicPresenceBinarySensor(  # pylint: disable=abstract-method
    CoordinatorEntity[DynamicPresenceCoordinator], BinarySensorEntity
):
    """Binary sensor for Dynamic Presence."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        unique_id: str,
        key: str,
        device_class: BinarySensorDeviceClass | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_suggested_object_id = key
        self._attr_translation_key = key
        self._key = key
        self._attr_device_class = device_class
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if occupied."""
        return self.coordinator.data.get(self._key)
