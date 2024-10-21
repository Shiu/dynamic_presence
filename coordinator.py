"""Coordinator for Dynamic Presence integration."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .active_room import ActiveRoom
from .const import (
    CONF_DISABLE_ON_CLEAR,
    CONF_ENABLE,
    CONF_ENABLE_ON_PRESENCE,
    CONF_NIGHT_MODE_ENABLE,
    DEFAULT_DISABLE_ON_CLEAR,
    DEFAULT_ENABLE,
    DEFAULT_ENABLE_ON_PRESENCE,
    DEFAULT_NIGHT_MODE_ENABLE,
    DOMAIN,
    NUMBER_CONFIG,
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
        self.data = {
            CONF_ENABLE: entry.options.get(CONF_ENABLE, DEFAULT_ENABLE),
            CONF_NIGHT_MODE_ENABLE: entry.options.get(
                CONF_NIGHT_MODE_ENABLE, DEFAULT_NIGHT_MODE_ENABLE
            ),
            CONF_ENABLE_ON_PRESENCE: entry.options.get(
                CONF_ENABLE_ON_PRESENCE, DEFAULT_ENABLE_ON_PRESENCE
            ),
            CONF_DISABLE_ON_CLEAR: entry.options.get(
                CONF_DISABLE_ON_CLEAR, DEFAULT_DISABLE_ON_CLEAR
            ),
        }

        # Initialize number entities with default values
        for key, config in NUMBER_CONFIG.items():
            self.data[key] = entry.options.get(key, config["default"])

        # Ensure switch states are preserved
        for switch in [
            CONF_ENABLE,
            CONF_NIGHT_MODE_ENABLE,
            CONF_ENABLE_ON_PRESENCE,
            CONF_DISABLE_ON_CLEAR,
        ]:
            if switch not in self.data:
                self.data[switch] = entry.options.get(switch, True)

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            await self.presence_detector.update_presence()
            self.active_room.update_activity(self.presence_detector.presence_detected)

            self.data.update(
                {
                    "presence_detected": self.presence_detector.presence_detected,
                    "last_presence_time": self.presence_detector.last_presence_time,
                    "is_night_mode": self.night_mode.is_night_mode_active(),
                    "is_active_room": self.active_room.is_active,
                    "presence_duration": self.presence_detector.get_presence_duration(),
                    "absence_duration": self.presence_detector.get_absence_duration(),
                    "active_room_status": "active"
                    if self.active_room.is_active
                    else "inactive",
                    "presence_sensor_state": "on"
                    if self.presence_detector.presence_detected
                    else "off",
                    "night_mode_status": "on"
                    if self.night_mode.is_night_mode_active()
                    else "off",
                }
            )

            _LOGGER.debug("Updated coordinator data: %s", self.data)
            return self.data
        except AttributeError as e:
            _LOGGER.error("Error updating data: %s", str(e))
        except (ValueError, TypeError) as e:
            _LOGGER.error("Unexpected error updating data: %s", str(e))
        else:
            _LOGGER.debug("Updated coordinator data: %s", self.data)

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
