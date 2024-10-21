"""Active room module for Dynamic Presence integration.

This module contains the ActiveRoom class, which manages the active room status.
It handles activity timeouts, thresholds, and provides methods to update
the active room status based on presence detection and configured settings.
"""

from datetime import datetime
import logging

from homeassistant.core import HomeAssistant

from .const import CONF_ACTIVE_ROOM_THRESHOLD, CONF_ACTIVE_ROOM_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class ActiveRoom:
    """Manage the active room status for Dynamic Presence integration."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the ActiveRoom instance.

        Args:
            hass: The Home Assistant instance.
            config_entry: The config entry containing the integration options.

        """
        self.hass = hass
        self.active_room_timeout = config_entry.options.get(
            CONF_ACTIVE_ROOM_TIMEOUT, 600
        )
        self.active_room_threshold = config_entry.options.get(
            CONF_ACTIVE_ROOM_THRESHOLD, 900
        )
        self.last_activity_time = None
        self.is_active = False

    def update_activity(self, presence_detected: bool):
        """Update the active room status based on presence detection."""
        current_time = datetime.now()
        if presence_detected:
            if (
                self.last_activity_time is None
                or (current_time - self.last_activity_time).total_seconds()
                > self.active_room_threshold
            ):
                self.is_active = True
            self.last_activity_time = current_time
        elif self.last_activity_time:
            time_since_last_activity = (
                current_time - self.last_activity_time
            ).total_seconds()
            if time_since_last_activity > self.active_room_timeout:
                self.is_active = False

    def update_settings(self, timeout: int, threshold: int):
        """Update active room settings."""
        self.active_room_timeout = timeout
        self.active_room_threshold = threshold
