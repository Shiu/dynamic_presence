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

    async def async_set_value(self, value: time) -> None:
        """Set the time."""
        await self.coordinator.async_set_time_value(self._key, value.isoformat())

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
