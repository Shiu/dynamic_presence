"""Coordinator for Dynamic Presence integration."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .active_room import ActiveRoom
from .const import (
    CONF_ROOM_NAME,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
    DEFAULT_VALUES,
    DOMAIN,
    NUMBER_CONFIG,
    SWITCH_KEYS,
)
from .night_mode import NightMode
from .presence_detector import PresenceDetector

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceCoordinator(DataUpdateCoordinator):
    """Coordinate between Dynamic Presence components."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.presence_detector = PresenceDetector(hass, entry)
        self.night_mode = NightMode(hass, entry)
        self.active_room = ActiveRoom(hass, entry)
        self.data = {}

        # Initialize number entities with default values
        for key, config in NUMBER_CONFIG.items():
            self.data[key] = entry.options.get(key, config["default"])

        # Initialize switch states
        for switch in SWITCH_KEYS:
            self.data[switch] = entry.options.get(
                switch, DEFAULT_VALUES.get(switch, True)
            )

        # Initialize time entities with default values
        self.data["night_mode_start"] = entry.options.get(
            "night_mode_start", DEFAULT_NIGHT_MODE_START
        )
        self.data["night_mode_end"] = entry.options.get(
            "night_mode_end", DEFAULT_NIGHT_MODE_END
        )

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            await self.presence_detector.update_presence()
            self.active_room.update_activity(self.presence_detector.presence_detected)

            room_name = (
                self.entry.data.get(CONF_ROOM_NAME, "Unknown Room")
                .lower()
                .replace(" ", "_")
            )

            updated_data = {
                f"{room_name}_occupancy_duration": self.presence_detector.get_presence_duration(),
                f"{room_name}_absence_duration": self.presence_detector.get_absence_duration(),
                f"{room_name}_active_room_status": "active"
                if self.active_room.is_active
                else "inactive",
                f"{room_name}_occupancy_state": "occupied"
                if self.presence_detector.presence_detected
                else "vacant",
                f"{room_name}_night_mode_status": "on"
                if self.night_mode.is_night_mode_active()
                else "off",
            }

            for key, value in updated_data.items():
                _LOGGER.debug("Updating %s with value: %s", key, value)
                self.data[key] = value

            _LOGGER.debug("Updated coordinator data: %s", self.data)
        except AttributeError as e:
            _LOGGER.error("AttributeError updating data: %s", str(e))
        except ValueError as e:
            _LOGGER.error("ValueError updating data: %s", str(e))
        except TypeError as e:
            _LOGGER.error("TypeError updating data: %s", str(e))

        return self.data

    async def async_update_presence_timeout(self, new_timeout: int):
        """Update the presence timeout."""
        self.presence_detector.set_presence_timeout(new_timeout)
        self.data["presence_timeout"] = new_timeout
        self.async_set_updated_data(self.data)

    async def async_update_night_mode_settings(
        self, enabled: bool, start: str, end: str
    ):
        """Update night mode settings."""
        self.night_mode.update_night_mode_settings(enabled, start, end)
        self.data["night_mode_enabled"] = enabled
        self.data["night_mode_start"] = start
        self.data["night_mode_end"] = end
        self.async_set_updated_data(self.data)

    async def async_update_active_room_settings(self, timeout: int, threshold: int):
        """Update active room settings."""
        self.active_room.update_settings(timeout, threshold)
        self.data["active_room_timeout"] = timeout
        self.data["active_room_threshold"] = threshold
        self.async_set_updated_data(self.data)

    async def async_update_switch(self, key: str, value: bool):
        """Update a switch."""
        self.data[key] = value
        self.async_set_updated_data(self.data)

    async def async_update_number(self, key: str, value: float):
        """Update a number."""
        self.data[key] = value
        self.async_set_updated_data(self.data)

    async def async_update_time(self, key: str, value: str):
        """Update a time."""
        self.data[key] = value
        self.async_set_updated_data(self.data)

    def get_entity_name(self, entity_type: str, name: str) -> str:
        """Get the entity name."""
        room_name = (
            self.entry.data.get(CONF_ROOM_NAME, "Unknown Room")
            .lower()
            .replace(" ", "_")
        )
        return f"{entity_type}.{room_name}_{name.lower().replace(' ', '_')}"

    def register_entity(
        self, entity: Entity, room: str, entity_type: str, specific_name: str
    ):
        """Register an entity."""
        entity_name = self.get_entity_name(room, entity_type, specific_name)
        self._entities[entity_name] = entity

    def update_entity_state(
        self, room: str, entity_type: str, specific_name: str, new_state
    ):
        """Update an entity state."""
        entity_name = self.get_entity_name(room, entity_type, specific_name)
        if entity_name in self._entities:
            self._entities[entity_name].async_write_ha_state()

    def get_device_info(self, room: str) -> dict:
        """Return device info for the given room."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"Dynamic Presence {room.capitalize()}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
            "sw_version": "1.0",
        }

    async def async_set_number_value(self, key: str, value: float):
        """Update a number value."""
        self.data[key] = value
        await self.async_update_number(key, value)
        self.async_set_updated_data(self.data)

    async def async_set_switch_value(self, key: str, value: bool):
        """Update a switch value."""
        self.data[key] = value
        await self.async_update_switch(key, value)
        self.async_set_updated_data(self.data)

    async def async_set_time_value(self, key: str, value: str):
        """Update a time value."""
        self.data[key] = value
        await self.async_update_time(key, value)
        self.async_set_updated_data(self.data)
