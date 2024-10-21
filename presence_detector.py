"""Presence detection module for Dynamic Presence integration.

This module contains the PresenceDetector class, which is responsible for
managing and updating the presence state based on a configured presence sensor.
It handles presence timeout logic and provides methods to update the presence state.
"""

from datetime import datetime
import logging

from homeassistant.core import HomeAssistant

from .const import CONF_PRESENCE_SENSOR, CONF_PRESENCE_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class PresenceDetector:
    """Manage presence detection for Dynamic Presence integration."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the PresenceDetector instance.

        Args:
            hass: The Home Assistant instance.
            config_entry: The config entry containing the integration options.

        """
        self.hass = hass
        self.presence_sensor = config_entry.data[CONF_PRESENCE_SENSOR]
        self.presence_timeout = config_entry.options.get(CONF_PRESENCE_TIMEOUT, 300)
        self.last_presence_time = None
        self.presence_detected = False

    async def update_presence(self):
        """Update the presence state based on the presence sensor."""
        presence_sensor = self.hass.states.get(self.presence_sensor)
        if presence_sensor is None:
            _LOGGER.error("Presence sensor not found")
            return

        self.presence_detected = presence_sensor.state == "on"
        if self.presence_detected:
            self.last_presence_time = datetime.now()
        elif self.last_presence_time:
            time_since_last_presence = datetime.now() - self.last_presence_time
            if time_since_last_presence.total_seconds() > self.presence_timeout:
                self.presence_detected = False
                self.last_presence_time = None

    def set_presence_timeout(self, new_timeout: int):
        """Update the presence timeout."""
        self.presence_timeout = new_timeout
