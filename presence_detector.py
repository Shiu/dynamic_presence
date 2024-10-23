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

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_CONTROLLED_ENTITIES,
    CONF_MANAGE_ON_CLEAR,
    CONF_MANAGE_ON_PRESENCE,
    CONF_PRESENCE_SENSOR,
    CONF_PRESENCE_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


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
        self.grace_period = timedelta(seconds=15)
        self.last_absence_start = None
        self.active_room_threshold = entry.options.get(
            CONF_ACTIVE_ROOM_THRESHOLD, 300
        )  # Default to 5 minutes

    async def update_presence(self):
        """Update the presence state based on the presence sensor."""
        presence_sensor = self.hass.states.get(self.presence_sensor)
        if presence_sensor is None:
            _LOGGER.warning("Presence sensor %s not found", self.presence_sensor)
            return

        new_presence = presence_sensor.state == "on"
        current_time = datetime.now()

        if new_presence:
            if not self.presence_detected:
                self.last_presence_time = current_time
                _LOGGER.debug("New occupancy detected")
            self.presence_detected = True
            self.last_absence_start = None
        elif self.presence_detected:
            if not self.last_absence_start:
                self.last_absence_start = current_time
                _LOGGER.debug("Potential absence detected, starting grace period")
            elif (current_time - self.last_absence_start) >= self.grace_period:
                self.presence_detected = False
                self.last_absence_time = self.last_absence_start
                _LOGGER.debug("Absence confirmed after grace period")

        if self.presence_detected:
            occupancy_duration = (
                int((current_time - self.last_presence_time).total_seconds())
                if self.last_presence_time
                else 0
            )
            absence_duration = 0

            _LOGGER.debug(
                "Occupancy duration: %s, Threshold: %s",
                occupancy_duration,
                self.active_room_threshold,
            )

            if occupancy_duration >= self.active_room_threshold:
                _LOGGER.debug(
                    "Occupancy duration %s reached threshold %s",
                    occupancy_duration,
                    self.active_room_threshold,
                )
                await self.coordinator.set_active_room_status(True)
            else:
                _LOGGER.debug(
                    "Occupancy duration %s not yet reached threshold %s",
                    occupancy_duration,
                    self.active_room_threshold,
                )
                await self.coordinator.set_active_room_status(False)
        else:
            occupancy_duration = 0
            absence_duration = (
                int((current_time - self.last_absence_time).total_seconds())
                if self.last_absence_time
                else 0
            )
            await self.coordinator.set_active_room_status(False)

        self.coordinator.data.update(
            {
                f"{self.coordinator.room_name}_occupancy_state": "occupied"
                if self.presence_detected
                else "vacant",
                f"{self.coordinator.room_name}_occupancy_duration": occupancy_duration,
                f"{self.coordinator.room_name}_absence_duration": absence_duration,
            }
        )

        _LOGGER.debug(
            "Updated coordinator data: %s",
            self.coordinator.data,
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
                _LOGGER.error(
                    "Error updating controlled entity %s: %s", entity_id, str(e)
                )

    async def set_room_active(self):
        """Set the room as active."""
        if not self.coordinator.active_room.is_active:
            self.coordinator.active_room.set_active(True)
            _LOGGER.debug("Room %s set as active", self.coordinator.room_name)
            await self.coordinator.async_update_listeners()

    def update_from_options(self, options: dict):
        """Update detector values from new options."""
        self.presence_timeout = options.get(
            CONF_PRESENCE_TIMEOUT, self.presence_timeout
        )
        self.active_room_threshold = options.get(
            CONF_ACTIVE_ROOM_THRESHOLD, self.active_room_threshold
        )
        # Add any other options that need to be updated
