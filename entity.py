"""Base entity for Dynamic Presence integration."""

import logging
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from typing import Any

from .const import DOMAIN, NAME, VERSION

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceEntity(CoordinatorEntity, Entity):
    """
    Base class for Dynamic Presence entities.

    This class provides common functionality for all entities in the Dynamic Presence
    integration. It inherits from CoordinatorEntity to leverage the data update
    coordinator pattern, and from Entity to provide basic entity functionality.
    """

    # Indicates that this entity uses the parent device's name as a prefix
    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry: ConfigEntry, description) -> None:
        """
        Initialize the Dynamic Presence entity.

        Args:
            coordinator: The data update coordinator.
            config_entry: The config entry containing integration configuration.
            description: EntityDescription object with entity metadata.
        """
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.entity_description = description

        # Set up device info for the entity
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer=NAME,
            model="Dynamic Presence Controller",
            sw_version=VERSION,
        )

        # Generate a unique ID for the entity
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"

        _LOGGER.debug(
            "Initialized %s entity for %s", description.key, config_entry.title
        )

    @property
    def should_poll(self) -> bool:
        """
        Determine if the entity should be polled for updates.

        Returns:
            False, as the entity pushes its state to Home Assistant via the coordinator.
        """
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updated data from the coordinator.

        This method is called when the coordinator has new data. It triggers
        the entity to update its state in Home Assistant.
        """
        _LOGGER.debug("Updating state for %s", self.entity_id)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """
        Set up the entity when it's added to Home Assistant.

        This method is called when the entity is added to Home Assistant.
        It ensures that the entity has the latest state from the coordinator.
        """
        _LOGGER.debug("Adding %s to Home Assistant", self.entity_id)
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def _get_coordinator_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the coordinator's data with a default."""
        value = self.coordinator.data.get(key, default)
        _LOGGER.debug(
            "Getting coordinator value for %s: %s = %s", self.entity_id, key, value
        )
        return value
