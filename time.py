"""Time platform for Dynamic Presence integration."""

from datetime import time
import logging

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ROOM_NAME, DOMAIN, TIME_KEYS
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceTime(TimeEntity):
    """Representation of a Dynamic Presence time setting."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        room: str,
        description: TimeEntityDescription,
    ) -> None:
        """Initialize the Dynamic Presence time entity."""
        super().__init__()
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_name = description.name
        self.entity_id = f"time.dynamic_presence_{room}_{description.key}"
        self._attr_device_info = coordinator.get_device_info(room)
        self._key = description.key

    @property
    def native_value(self):
        """Return the time value."""
        return self.coordinator.data.get(self._key)

    async def _async_update_time_state(
        self, value: time, update_options: bool = True
    ) -> None:
        """Update time state and persist changes if needed."""
        time_str = value.isoformat()
        self.coordinator.data[self._key] = time_str
        self.coordinator.async_set_updated_data(self.coordinator.data)

        if update_options:
            # Update the config entry options
            entry = self.coordinator.entry
            new_options = dict(entry.options)
            new_options[self._key] = time_str
            self.coordinator.hass.config_entries.async_update_entry(
                entry, options=new_options
            )

        _LOGGER.info("Updated %s to %s", self._key, time_str)

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""
        await self.coordinator.async_update_entity_value(
            self.entity_description.key, value
        )

    async def async_update_config(self, options: dict) -> None:
        """Update the entity's configuration."""
        new_value = options.get(self._key)
        if self.native_value != new_value:
            await self._async_update_time_state(
                time.fromisoformat(new_value), update_options=False
            )

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def state(self) -> str | None:
        """Return the state of the time entity."""
        if self.native_value is None:
            return None
        if isinstance(self.native_value, str):
            return self.native_value
        return self.native_value.isoformat()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence time entities based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
    coordinator = hass.data[DOMAIN][entry.entry_id]

    time_entities = [
        DynamicPresenceTime(
            coordinator,
            room_name,
            TimeEntityDescription(
                key=key,
                name=key.replace("_", " ").title(),
            ),
        )
        for key in TIME_KEYS
    ]

    async_add_entities(time_entities)
    _LOGGER.debug("Added %d time entities for %s", len(time_entities), room_name)
