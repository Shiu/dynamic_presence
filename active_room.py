"""Active Room module for Dynamic Presence integration.

This module contains the ActiveRoom class, which manages the active room status.
It handles activity timeouts, thresholds, and provides methods to update
the active room status based on presence detection and configured settings.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    DEFAULT_ACTIVE_ROOM_THRESHOLD,
    DEFAULT_ACTIVE_ROOM_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class ActiveRoom:
    """Class to manage the active room state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the ActiveRoom class."""
        self.hass = hass
        self.entry = entry
        self.is_active = False
        self.active_room_timeout = entry.options.get(
            CONF_ACTIVE_ROOM_TIMEOUT, DEFAULT_ACTIVE_ROOM_TIMEOUT
        )
        self.active_room_threshold = entry.options.get(
            CONF_ACTIVE_ROOM_THRESHOLD, DEFAULT_ACTIVE_ROOM_THRESHOLD
        )

    def set_active(self, active: bool):
        """Set the active room status."""
        self.is_active = active
        return self.is_active

    def update_activity(self, occupancy_duration: int):
        """Update the active room status based on presence detection."""
        if occupancy_duration >= self.active_room_threshold:
            if not self.is_active:
                self.set_active(True)
                _LOGGER.info("Room set as active")
        elif self.is_active:
            self.set_active(False)
            _LOGGER.info("Room set as inactive")

    def update_settings(self, timeout: int, threshold: int):
        """Update active room settings."""
        self.active_room_timeout = timeout
        self.active_room_threshold = threshold

    def get_active(self) -> bool:
        """Get the current active state of the room."""
        return self.is_active

    def get_timeout(self) -> int:
        """Get the active room timeout value."""
        return self.active_room_timeout

    def get_threshold(self) -> int:
        """Get the active room threshold value."""
        return self.active_room_threshold
