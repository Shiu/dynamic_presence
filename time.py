"""Time platform for Dynamic Presence integration."""

# pylint: disable=W0223  # Method 'set_native_value' is abstract
# pylint: disable=W0239  # Method 'set_value' overrides final
# type: ignore[shadow-stdlib]

from datetime import time
import logging

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ROOM_NAME, DOMAIN, TIME_DEFAULT_VALUES, TIME_KEYS
from .coordinator import DynamicPresenceCoordinator


logTime = logging.getLogger("dynamic_presence.time")


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
        self._attr_name = f"dynamic_presence_{room}_{description.key}".replace(
            "_", " "
        ).title()
        self._attr_entity_id = f"time.dynamic_presence_{room}_{description.key}"
        self._attr_device_info = coordinator.get_device_info(room)

        # Time-specific attributes
        self._attr_native_value = coordinator.data.get(description.key)

    @property
    def native_value(self):
        """Return the time value."""
        value = self.coordinator.data.get(self.entity_description.key)
        if isinstance(value, str):
            return value
        return None

    async def async_set_value(self, value: time) -> None:
        """Set the time."""
        time_str = value.isoformat()
        await self.coordinator.async_save_options(self.entity_description.key, time_str)

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

    entities = []
    for time_key in TIME_KEYS:
        default_time = TIME_DEFAULT_VALUES.get(time_key)

        if time_key not in entry.options:
            coordinator.data[time_key] = default_time
            logTime.debug(
                "Time %s set to default value %s",
                time_key,
                coordinator.data[time_key],
            )
        else:
            coordinator.data[time_key] = entry.options[time_key]
            logTime.debug(
                "Time %s set to option value %s",
                time_key,
                coordinator.data[time_key],
            )

        entity = DynamicPresenceTime(
            coordinator,
            room_name,
            TimeEntityDescription(
                key=time_key,
                name=time_key.replace("_", " ").title(),
            ),
        )
        entities.append(entity)

    async_add_entities(entities)
