"""Coordinator for Dynamic Presence integration."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .active_room import ActiveRoom
from .const import (
    CONF_CONTROLLED_ENTITIES,
    CONF_MANAGE_ON_CLEAR,
    CONF_MANAGE_ON_PRESENCE,
    CONF_PRESENCE_SENSOR,
    CONF_ROOM_NAME,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
    DOMAIN,
    NUMBER_CONFIG,
    SWITCH_KEYS,
    TIME_KEYS,
)
from .presence_detector import PresenceDetector


class MessageFilter(logging.Filter):
    """Filter out specific messages."""

    def __init__(self, *phrases) -> None:
        """Initialize the filter."""
        super().__init__()
        self.phrases = phrases

    def filter(self, record) -> bool:
        """Filter out specific messages."""
        return not any(phrase in record.msg for phrase in self.phrases)


logCoordinator = logging.getLogger("dynamic_presence.coordinator")
# logCoordinator.addFilter(MessageFilter("Finished fetching", "Manually updated"))


class DynamicPresenceCoordinator(DataUpdateCoordinator):
    """Coordinate between Dynamic Presence components."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            name="Dynamic Presence",
            logger=logCoordinator,
        )
        self.entry = entry
        self.room_name = (
            entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
        )
        self.active_room = ActiveRoom(hass, entry)
        self.data = {}

        self.update_data_from_options(entry.options)

        # Set up event listener for presence sensor
        self.presence_sensor = entry.data[CONF_PRESENCE_SENSOR]
        hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)

        self.presence_detector = PresenceDetector(hass, entry, self)
        self.entities = {}

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        current_occupancy_duration = self.data.get("occupancy_duration", 0)
        await self.presence_detector.update_presence()
        self.data["occupancy_duration"] = current_occupancy_duration
        return self.data

    async def set_active_room_status(self, active: bool):
        """Set the active room status and update listeners."""
        self.active_room.set_active(active)
        self.data[f"{self.room_name}_active_room_status"] = active

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
        self.active_room.update_settings(timeout, threshold)
        self.data["active_room_timeout"] = timeout
        self.data["active_room_threshold"] = threshold
        self.async_set_updated_data(self.data)

    def get_entity_name(self, entity_type: str, name: str) -> str:
        """Get the entity name."""
        room_name = (
            self.entry.data.get(CONF_ROOM_NAME, "Unknown Room")
            .lower()
            .replace(" ", "_")
        )
        return f"{entity_type}.{room_name}_{name.lower().replace(' ', '_')}"

    def get_device_info(self, room: str) -> dict:
        """Return device info for the given room."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"Dynamic Presence {room.capitalize()}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
            "sw_version": "1.0",
        }

    async def _handle_state_change(self, event):
        """Handle state changes for the presence sensor."""
        if event.data.get("entity_id") == self.presence_sensor:
            if self.hass.states.get(self.presence_sensor) is None:
                logCoordinator.warning(
                    "Presence sensor %s not found", self.presence_sensor
                )
                return
            await self.async_refresh()

    async def update_controlled_entities(self):
        """Update controlled entities based on presence state."""
        controlled_entities = self.entry.data.get(CONF_CONTROLLED_ENTITIES, [])
        manage_on_presence = self.entry.options.get(CONF_MANAGE_ON_PRESENCE, True)
        manage_on_clear = self.entry.options.get(CONF_MANAGE_ON_CLEAR, True)

        for entity_id in controlled_entities:
            try:
                if self.presence_detected and manage_on_presence:
                    await self.hass.services.async_call(
                        "homeassistant", "turn_on", {"entity_id": entity_id}
                    )
                elif not self.presence_detected and manage_on_clear:
                    await self.hass.services.async_call(
                        "homeassistant", "turn_off", {"entity_id": entity_id}
                    )
            except HomeAssistantError:
                pass

    def update_data_from_options(self, options: dict):
        """Update coordinator data from options."""
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

    async def async_update_options(self, _: HomeAssistant, entry: ConfigEntry) -> None:
        """Update coordinator data from options."""
        # Only update changed values, not everything
        for key, value in entry.options.items():
            if key in self.data and self.data[key] != value:
                self.data[key] = value
        self.async_set_updated_data(self.data)

    async def async_save_options(self, key: str, value: Any) -> None:
        """Save a single option value to config entry."""
        new_options = dict(self.entry.options)
        new_options[key] = value
        self.data[key] = value  # Update data directly
        self.async_set_updated_data(self.data)  # Notify listeners
        # Save to options without triggering full reload
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
