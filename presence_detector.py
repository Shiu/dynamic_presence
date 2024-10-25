"""Presence detection module for Dynamic Presence integration.

This module contains the PresenceDetector class, which is responsible for
managing and updating the presence state based on a configured presence sensor.
It handles presence timeout logic and provides methods to update the presence state.
"""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_CONTROLLED_ENTITIES,
    CONF_MANAGE_ON_CLEAR,
    CONF_MANAGE_ON_PRESENCE,
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
        self.presence_sensor = entry.data[CONF_PRESENCE_SENSOR]
        self.presence_timeout = entry.options.get(CONF_PRESENCE_TIMEOUT, 300)
        self.last_presence_time = None
        self.last_absence_time = None
        self.presence_detected = False
        self.grace_period = timedelta(
            seconds=entry.options.get(CONF_SHORT_ABSENCE_THRESHOLD, 10)
        )
        self._timer = None
        self._grace_period_start = None

    async def start_timer(self) -> None:
        """Start the timer for updating durations and handling grace period."""
        if self._timer is None:
            self._timer = async_track_time_interval(
                self.hass, self._timer_update, timedelta(seconds=1)
            )

    async def _timer_update(self, _now: datetime) -> None:
        """Handle timer updates for durations and grace period."""
        current_time = datetime.now()

        # Handle grace period
        if self._grace_period_start and self.presence_detected:
            if (current_time - self._grace_period_start) >= self.grace_period:
                self.presence_detected = False
                self.last_absence_time = self._grace_period_start
                self._grace_period_start = None
                logPresenceDetector.debug("Grace period expired, marking as absent")
                await self.update_controlled_entities()

        # Update durations
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

        self.coordinator.async_set_updated_data(self.coordinator.data)

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
                # Person enters empty room
                self.presence_detected = True
                self.last_presence_time = datetime.now()
                self.last_absence_time = None  # Stop absence timer
                self._grace_period_start = None
                # Reset absence duration in coordinator
                self.coordinator.data[
                    f"{self.coordinator.room_name}_absence_duration"
                ] = 0
                logPresenceDetector.debug("New occupancy detected, absence timer reset")
        elif self.presence_detected:
            # Person has left room
            if not self._grace_period_start:
                # Start grace period
                self._grace_period_start = datetime.now()
                logPresenceDetector.debug(
                    "Potential absence detected, grace period started"
                )
            elif (datetime.now() - self._grace_period_start) >= self.grace_period:
                # Absence confirmed after grace period
                self.presence_detected = False
                self.last_presence_time = None  # Stop occupancy timer
                self.last_absence_time = (
                    self._grace_period_start
                )  # Start absence timer from when grace period began
                # Reset occupancy duration in coordinator
                self.coordinator.data[
                    f"{self.coordinator.room_name}_occupancy_duration"
                ] = 0
                logPresenceDetector.debug("Absence confirmed, occupancy timer reset")

        # Update basic presence state
        self.coordinator.data[f"{self.coordinator.room_name}_occupancy_state"] = (
            "occupied" if self.presence_detected else "vacant"
        )

        await self.update_controlled_entities()

    def set_presence_timeout(self, new_timeout: int):
        """Update the presence timeout."""
        self.presence_timeout = new_timeout

    def get_presence_duration(self):
        """Get the duration of the current presence in seconds."""
        if self.presence_detected and self.last_presence_time:
            return int((datetime.now() - self.last_presence_time).total_seconds())
        return 0

    def get_absence_duration(self):
        """Get the duration of the current absence."""
        if not self.presence_detected and self.last_presence_time:
            return (datetime.now() - self.last_presence_time).total_seconds()
        return 0

    async def _handle_state_change(self, event):
        """Handle state changes for the presence sensor."""
        if event.data.get("entity_id") == self.presence_sensor:
            await self.async_refresh()

    async def async_refresh(self):
        """Refresh data from the presence detector."""
        await self._async_update_data()
        self.async_set_updated_data(self.data)

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
            except HomeAssistantError as e:
                logPresenceDetector.error(
                    "Error updating controlled entity %s: %s", entity_id, str(e)
                )

    def update_from_options(self, options: dict):
        """Update detector values from new options."""
        self.presence_timeout = options.get(
            CONF_PRESENCE_TIMEOUT, self.presence_timeout
        )
        # Add any other options that need to be updated
