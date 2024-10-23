"""Coordinator for Dynamic Presence integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_PRESENCE_SENSOR,
    CONF_ROOM_NAME,
    DEFAULT_ACTIVE_ROOM_THRESHOLD,
    DEFAULT_ACTIVE_ROOM_TIMEOUT,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
    DEFAULT_SWITCH_STATES,
    DOMAIN,
    NUMBER_CONFIG,
    SWITCH_KEYS,
    TIME_KEYS,
)
from .presence_detector import PresenceDetector

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate between Dynamic Presence components."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Dynamic Presence",
        )
        self.entry: ConfigEntry = entry
        self.room_name: str = (
            entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
        )
        self.data: dict[str, Any] = {}
        self.last_update: float | None = None
        self.presence_detected: bool = False
        self.is_active_room: bool = False
        self.active_room_timeout: int = entry.options.get(
            "active_room_timeout", DEFAULT_ACTIVE_ROOM_TIMEOUT
        )
        self.active_room_threshold: int = entry.options.get(
            "active_room_threshold", DEFAULT_ACTIVE_ROOM_THRESHOLD
        )
        self.data["occupancy_duration"] = 0
        self.data["absence_duration"] = 0

        _LOGGER.info("Initializing coordinator with options: %s", entry.options)
        self.update_data_from_options(entry.options)

        # Initialize switch states
        for switch_key in SWITCH_KEYS:
            self.data[switch_key] = entry.options.get(
                switch_key, DEFAULT_SWITCH_STATES[switch_key]
            )

        # Set up event listener for presence sensor
        self.presence_sensor: str = entry.data[CONF_PRESENCE_SENSOR]

        self.presence_detector: PresenceDetector = PresenceDetector(hass, entry, self)
        hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)

    async def _async_update_data(self):
        """Update timers."""
        now = self.hass.loop.time()
        if self.last_update is None:
            self.last_update = now
            return self.data

        time_elapsed = now - self.last_update
        self.last_update = now

        if self.presence_detected:
            self.data["occupancy_duration"] += time_elapsed
        else:
            self.data["absence_duration"] += time_elapsed

        return self.data

    async def set_active_room_status(self, active: bool):
        """Set the active room status and update listeners."""
        previous_status = self.is_active_room
        self.is_active_room = active
        self.data[f"{self.room_name}_active_room_status"] = active
        if previous_status != active:
            _LOGGER.info(
                "Active room status changed from %s to %s", previous_status, active
            )
        else:
            _LOGGER.debug("Active room status unchanged: %s", active)
        _LOGGER.debug("Updated coordinator data: %s", self.data)
        self.async_set_updated_data(self.data)

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
        self.active_room_timeout = timeout
        self.active_room_threshold = threshold
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
            "identifiers": {(DOMAIN, f"{self.entry.entry_id}_{room}")},
            "name": f"Dynamic Presence {room.capitalize()}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
            "sw_version": "1.0",
        }

    async def async_update_entity_value(self, key: str, value: Any) -> None:
        """Update an entity value and refresh data."""
        self.data[key] = value
        _LOGGER.info("Coordinator: Updated %s to %s", key, value)

        # Update the config entry options
        new_options = dict(self.entry.options)
        new_options[key] = value
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)

        self.async_set_updated_data(self.data)

    async def async_set_number_value(self, key: str, value: float) -> None:
        """Set a number value and update data."""
        await self.async_update_entity_value(key, value)

    async def async_set_switch_value(self, key: str, value: bool) -> None:
        """Update a switch value."""
        await self.async_update_entity_value(key, value)

    async def async_set_time_value(self, key: str, value: str) -> None:
        """Update a time value."""
        await self.async_update_entity_value(key, value)

    async def _handle_state_change(self, event):
        """Handle state changes for the presence sensor."""
        if event.data.get("entity_id") == self.presence_sensor:
            if self.hass.states.get(self.presence_sensor) is None:
                _LOGGER.warning("Presence sensor %s not found", self.presence_sensor)
                return
            await self.presence_detector.update_presence()
            await self.async_request_refresh()

    async def async_refresh(self):
        """Refresh data from the presence detector."""
        await self._async_update_data()
        self.async_set_updated_data(self.data)

    def update_data_from_options(self, options: dict):
        """Update coordinator data from options."""
        current_occupancy_duration = self.data.get("occupancy_duration", 0)
        _LOGGER.info("Updating coordinator data from options: %s", options)
        for key in TIME_KEYS:
            self.data[key] = options.get(key)
        for key, config in NUMBER_CONFIG.items():
            self.data[key] = options.get(key, config["default"])
        for key in SWITCH_KEYS:
            self.data[key] = options.get(key)
        self.data["night_mode_start"] = options.get(
            "night_mode_start", DEFAULT_NIGHT_MODE_START
        )
        self.data["night_mode_end"] = options.get(
            "night_mode_end", DEFAULT_NIGHT_MODE_END
        )
        self.data["occupancy_duration"] = current_occupancy_duration
        _LOGGER.info("Updated coordinator data: %s", self.data)

    async def async_update_options(self, options: dict) -> None:
        """Update options and refresh data."""
        self.update_data_from_options(options)
        await self.async_request_refresh()

        # Update individual entities
        for entity in self.entities.values():
            if hasattr(entity, "async_update_config"):
                await entity.async_update_config(options)
