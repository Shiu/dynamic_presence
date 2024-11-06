"""Coordinator for Dynamic Presence integration."""

from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .presence_control import PresenceControl, RoomState
from .const import (
    DOMAIN,
    CONF_PRESENCE_SENSOR,
    CONF_LIGHTS,
    CONF_NIGHT_LIGHTS,
    CONF_LIGHT_SENSOR,
    DEFAULT_NIGHT_MODE_START,
    DEFAULT_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    NUMBER_CONFIG,
    TIME_KEYS,
    SWITCH_KEYS,
    SWITCH_CONFIG,
)


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
logCoordinator.addFilter(MessageFilter("Finished fetching", "Manually updated"))


class DynamicPresenceCoordinator(DataUpdateCoordinator):
    """Coordinator for room presence management."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=logCoordinator,
            name=DOMAIN,
            update_interval=timedelta(seconds=1),
        )

        self.hass = hass
        self.entry = entry
        self.room_name = entry.title

        # Add device info
        self.device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Dynamic Presence {self.room_name}",
            "manufacturer": "Home Assistant",
            "model": "Dynamic Presence Controller",
        }

        # Load stored states from config entry data instead of options
        self._manual_states = entry.data.get("_manual_states", {})

        # Configuration values - still from options as these are user-configurable
        self.presence_sensor = entry.options.get(CONF_PRESENCE_SENSOR)
        self.lights = entry.options.get(CONF_LIGHTS, [])
        self.night_lights = entry.options.get(CONF_NIGHT_LIGHTS, [])
        self.light_sensor = entry.options.get(CONF_LIGHT_SENSOR)
        self._is_configured = bool(self.presence_sensor and self.lights)

        # State tracking
        self._presence_control = PresenceControl(hass, self)
        self._stored_states = {}

        # Data initialization - load from entry.data with defaults
        self.data = {
            # Binary sensors
            "binary_sensor_occupancy": False,
            # Sensors
            "sensor_occupancy_duration": 0,
            "sensor_absence_duration": 0,
            "sensor_light_level": 0,
            # Numbers - load from entry.data with defaults
            **{
                f"number_{key}": entry.data.get(key, config["default"])
                for key, config in NUMBER_CONFIG.items()
            },
            # Switches - load from entry.data with defaults
            **{
                f"switch_{key}": entry.data.get(key, SWITCH_CONFIG[key])
                for key in SWITCH_KEYS
            },
            # Time - load from entry.data with defaults
            **{
                f"time_{key}": entry.data.get(key, DEFAULT_NIGHT_MODE_START)
                if key == CONF_NIGHT_MODE_START
                else entry.data.get(key, DEFAULT_NIGHT_MODE_END)
                for key in TIME_KEYS
            },
        }

    async def async_config_entry_first_refresh(self) -> None:
        """Initialize the coordinator."""
        await self._async_update_data()
        self._async_setup_listeners()

    @callback
    def _async_setup_listeners(self) -> None:
        """Set up state change event listeners for presence and light entities.

        Registers callbacks for:
        - Presence sensor state changes
        - Light state changes (both regular and night mode lights)
        """
        if not self._is_configured:
            logCoordinator.debug("Skipping listener setup - not configured")
            return

        logCoordinator.debug(
            "Setting up state change listeners for room: %s", self.room_name
        )

        # Set up presence sensor listener
        logCoordinator.debug(
            "Setting up presence sensor listener for: %s", self.presence_sensor
        )
        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [self.presence_sensor],
                self._presence_control.handle_presence_event,
            )
        )

        # Set up light listeners
        active_lights = self.lights + self.night_lights
        logCoordinator.debug("Setting up light listeners for: %s", active_lights)
        for light in active_lights:
            self.entry.async_on_unload(
                async_track_state_change_event(
                    self.hass,
                    [light],
                    self._async_light_changed,
                )
            )

    @callback
    def _get_active_lights(self) -> list:
        """Get the currently active set of lights based on night mode state.

        Returns:
            list: Night mode lights if night mode is active, otherwise regular lights
        """
        return self.night_lights if self._is_night_mode() else self.lights

    @callback
    def is_night_mode(self) -> bool:
        """Check if night mode is currently active.

        Returns:
            bool: True if night mode is active, False otherwise
        """
        return self._is_night_mode()

    async def handle_state_changed(self, new_state: RoomState) -> None:
        """Handle state machine state changes and update lights accordingly.

        Args:
            new_state: The new RoomState to handle

        Triggers:
            - Light state updates based on occupancy
            - Data refresh for all entities
        """
        await self._handle_state_changed(new_state)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data."""
        if not hasattr(self, "_presence_control"):
            return self.data

        updated_data = self.data.copy()
        current_state = self._presence_control.state

        # Update occupancy binary sensor
        updated_data["binary_sensor_occupancy"] = current_state in [
            RoomState.OCCUPIED,
            RoomState.DETECTION_TIMEOUT,
        ]

        # Get duration data from presence control
        durations = self._presence_control.durations
        updated_data.update(durations)

        return updated_data

    async def _handle_state_changed(self, new_state: RoomState) -> None:
        """Handle state machine state changes."""
        if new_state == RoomState.OCCUPIED:
            await self._apply_light_states()
        elif new_state == RoomState.VACANT:
            await self._turn_off_lights()
        await self.async_refresh()

    async def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        if self._presence_control.state == RoomState.OCCUPIED:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            if new_state is not None:
                self._manual_states[entity_id] = new_state.state == STATE_ON
                # Store states immediately in entry data
                new_data = dict(self.entry.data) if self.entry.data else {}
                new_data["_manual_states"] = self._manual_states
                self.hass.config_entries.async_update_entry(self.entry, data=new_data)
                await self.async_refresh()

    async def _apply_light_states(self) -> None:
        """Apply stored light states or turn on lights."""
        if not self._manual_states:
            # No stored states, turn on all lights
            for light in self._get_active_lights():
                await self.hass.services.async_call(
                    "light", "turn_on", {"entity_id": light}, blocking=True
                )
        else:
            # Apply stored states
            for light, state in self._manual_states.items():
                service = "turn_on" if state else "turn_off"
                await self.hass.services.async_call(
                    "light", service, {"entity_id": light}, blocking=True
                )

    async def _turn_off_lights(self) -> None:
        """Turn off all active lights."""
        for light in self._get_active_lights():
            await self.hass.services.async_call(
                "light", "turn_off", {"entity_id": light}, blocking=True
            )

    async def async_entity_changed(
        self, entity_type: str, key: str, value: Any
    ) -> None:
        """Handle entity state changes."""
        # Update runtime data only
        self.data[f"{entity_type}_{key}"] = value
        self.async_set_updated_data(self.data)

        # Store in memory
        if not hasattr(self, "_stored_states"):
            self._stored_states = {}
        self._stored_states[key] = value

    async def async_save_options(self) -> None:
        """Save options to config entry - called during shutdown."""
        if hasattr(self, "_stored_states") and self._stored_states:
            new_data = dict(self.entry.data) if self.entry.data else {}
            new_data.update(self._stored_states)

            self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    async def async_switch_changed(self, key: str, value: bool) -> None:
        """Handle switch changes."""
        await self.async_entity_changed("switch", key, value)

    async def async_number_changed(self, key: str, value: float) -> None:
        """Handle number changes."""
        await self.async_entity_changed("number", key, value)
        await self._presence_control.update_timers("number", key)

    async def async_time_changed(self, key: str, value: str) -> None:
        """Handle time changes."""
        await self.async_entity_changed("time", key, value)

    def _is_night_mode(self) -> bool:
        """Check if night mode is active."""
        if not self.data["switch_night_mode"]:
            return False

        current_time = dt_util.now().time()
        start_time = dt_util.parse_time(self.data["time_night_mode_start"])
        end_time = dt_util.parse_time(self.data["time_night_mode_end"])

        # Handle overnight periods (when end time is less than start time)
        if end_time < start_time:
            return current_time >= start_time or current_time <= end_time

        # Normal period within same day
        return start_time <= current_time <= end_time
