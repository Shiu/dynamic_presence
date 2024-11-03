"""Presence detection module for Dynamic Presence integration.

This module contains the PresenceDetector class, which is responsible for
managing and updating the presence state based on a configured presence sensor.
It handles presence timeout logic and provides methods to update the presence state.
"""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_PRESENCE_SENSOR,
    CONF_PRESENCE_TIMEOUT,
    CONF_SHORT_ABSENCE_THRESHOLD,
)

logPresenceDetector = logging.getLogger("dynamic_presence.presence_detector")


class PresenceDetector:
    """Manage presence detection for Dynamic Presence integration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator) -> None:
        """Initialize the PresenceDetector instance.

        Args:
            hass: The Home Assistant instance.
            entry: The config entry containing the integration options.
            coordinator: The coordinator instance.

        """
        self.hass = hass
        self.coordinator = coordinator
        self.entry = entry
        self.presence_sensor = entry.options.get(
            CONF_PRESENCE_SENSOR, entry.data[CONF_PRESENCE_SENSOR]
        )
        self.presence_timeout = entry.options.get(CONF_PRESENCE_TIMEOUT, 300)
        self.last_presence_time = None
        self.last_absence_time = None
        self.presence_detected = False
        self.grace_period = timedelta(
            seconds=entry.options.get(CONF_SHORT_ABSENCE_THRESHOLD, 10)
        )
        self._grace_period_start = None

    async def calculate_durations(self, current_time: datetime):
        """Calculate and update occupancy and absence durations."""
        if self.presence_detected and self.last_presence_time:
            occupancy_duration = int(
                (current_time - self.last_presence_time).total_seconds()
            )
            self.coordinator.data.update(
                {
                    f"{self.coordinator.room_name}_occupancy_duration": occupancy_duration,
                    f"{self.coordinator.room_name}_absence_duration": 0,
                }
            )
        elif not self.presence_detected and self.last_absence_time:
            absence_duration = int(
                (current_time - self.last_absence_time).total_seconds()
            )
            self.coordinator.data.update(
                {
                    f"{self.coordinator.room_name}_occupancy_duration": 0,
                    f"{self.coordinator.room_name}_absence_duration": absence_duration,
                }
            )

    async def update_presence(self):
        """Update the presence state based on the presence sensor."""
        presence_sensor = self.hass.states.get(self.presence_sensor)
        if presence_sensor is None:
            logPresenceDetector.warning(
                "Presence sensor %s not found", self.presence_sensor
            )
            return

        new_presence = presence_sensor.state == "on"

        if new_presence:
            if not self.presence_detected:
                self.presence_detected = True
                self.last_presence_time = datetime.now()
                self.last_absence_time = None
                self._grace_period_start = None
                self.coordinator.data[
                    f"{self.coordinator.room_name}_absence_duration"
                ] = 0
                logPresenceDetector.debug("New occupancy detected, absence timer reset")
        elif self.presence_detected:
            if not self._grace_period_start:
                self._grace_period_start = datetime.now()
                logPresenceDetector.debug(
                    "Potential absence detected, grace period started"
                )
            elif (datetime.now() - self._grace_period_start) >= self.grace_period:
                self.presence_detected = False
                self.last_presence_time = None
                self.last_absence_time = self._grace_period_start
                self.coordinator.data[
                    f"{self.coordinator.room_name}_occupancy_duration"
                ] = 0
                logPresenceDetector.debug("Absence confirmed, occupancy timer reset")

        self.coordinator.data[f"{self.coordinator.room_name}_occupancy_state"] = (
            "on" if self.presence_detected else "off"
        )

        await self.coordinator.manage_entities(turn_on=self.presence_detected)

    def set_presence_timeout(self, new_timeout: int):
        """Update the presence timeout."""
        self.presence_timeout = new_timeout

    def update_from_options(self, options: dict):
        """Update detector values from new options."""
        self.presence_timeout = options.get(
            CONF_PRESENCE_TIMEOUT, self.presence_timeout
        )

    def is_presence_detected(self) -> bool:
        """Check if presence is currently detected."""
        if state := self.hass.states.get(self.presence_sensor):
            return state.state == "on"
        return False
