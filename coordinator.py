"""Coordinator for Dynamic Presence integration."""

from datetime import timedelta
import logging
from enum import Enum
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import (
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_PRESENCE_SENSOR,
    CONF_LIGHTS,
    CONF_NIGHT_LIGHTS,
    CONF_LIGHT_SENSOR,
    CONF_DETECTION_TIMEOUT,
    CONF_LONG_TIMEOUT,
    CONF_SHORT_TIMEOUT,
    DEFAULT_DETECTION_TIMEOUT,
    DEFAULT_LONG_TIMEOUT,
    DEFAULT_SHORT_TIMEOUT,
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


class RoomState(Enum):
    """Room state machine states."""

    VACANT = "vacant"
    OCCUPIED = "occupied"
    DETECTION_TIMEOUT = "detection_timeout"
    COUNTDOWN = "countdown"
    UNCONFIGURED = "unconfigured"


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

        # Get values from options without validation
        self.presence_sensor = entry.options.get(CONF_PRESENCE_SENSOR)
        self.lights = entry.options.get(CONF_LIGHTS, [])

        # Track configuration state
        self._is_configured = bool(self.presence_sensor and self.lights)
        if not self._is_configured:
            self._state = RoomState.UNCONFIGURED

        self.night_lights = entry.options.get(CONF_NIGHT_LIGHTS, [])
        self.light_sensor = entry.options.get(CONF_LIGHT_SENSOR)

        # State management
        self._state = RoomState.VACANT
        self._last_presence_time = None
        self._manual_states = {}

        # Timers
        self._detection_timer = None
        self._countdown_timer = None
        self._detection_timeout = entry.options.get(
            CONF_DETECTION_TIMEOUT, DEFAULT_DETECTION_TIMEOUT
        )
        self._long_timeout = entry.options.get(CONF_LONG_TIMEOUT, DEFAULT_LONG_TIMEOUT)
        self._short_timeout = entry.options.get(
            CONF_SHORT_TIMEOUT, DEFAULT_SHORT_TIMEOUT
        )

        # Device info
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Dynamic Presence {self.room_name}",
            manufacturer="Home Assistant",
            model="Dynamic Presence Controller",
        )

        # Initialize data with saved values from entry.options or defaults
        self.data = {
            # Binary sensors
            "binary_sensor_occupancy": False,
            # Sensors
            "sensor_occupancy_duration": 0,
            "sensor_absence_duration": 0,
            "sensor_light_level": 0,
            # Numbers - load from entry.options with defaults
            **{
                f"number_{key}": entry.options.get(key, config["default"])
                for key, config in NUMBER_CONFIG.items()
            },
            # Switches - load from entry.options with defaults
            **{
                f"switch_{key}": entry.options.get(key, SWITCH_CONFIG[key])
                for key in SWITCH_KEYS
            },
            # Time - load from entry.options with defaults
            **{
                f"time_{key}": entry.options.get(key, DEFAULT_NIGHT_MODE_START)
                if key == CONF_NIGHT_MODE_START
                else entry.options.get(key, DEFAULT_NIGHT_MODE_END)
                for key in TIME_KEYS
            },
        }

    async def async_config_entry_first_refresh(self) -> None:
        """Initialize the coordinator."""
        await self._async_update_data()
        self._async_setup_listeners()

    @callback
    def _async_setup_listeners(self) -> None:
        """Set up state change listeners."""
        # Skip setting up listeners if not configured
        if not self._is_configured:
            return

        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [self.presence_sensor],
                self._async_presence_changed,
            )
        )

        for light in self.lights + self.night_lights:
            self.entry.async_on_unload(
                async_track_state_change_event(
                    self.hass,
                    [light],
                    self._async_light_changed,
                )
            )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data."""
        # Preserve existing data
        updated_data = self.data.copy() if self.data else {}

        # Update binary sensors
        updated_data["binary_sensor_occupancy"] = self._state == RoomState.OCCUPIED

        # Update sensors
        if self._state == RoomState.OCCUPIED and self._last_presence_time:
            updated_data["sensor_occupancy_duration"] = int(
                (dt_util.utcnow() - self._last_presence_time).total_seconds()
            )
            updated_data["sensor_absence_duration"] = 0
        elif self._last_presence_time and self._state != RoomState.OCCUPIED:
            updated_data["sensor_absence_duration"] = int(
                (dt_util.utcnow() - self._last_presence_time).total_seconds()
            )
            updated_data["sensor_occupancy_duration"] = 0

        # Update light level if sensor configured
        if self.light_sensor:
            state = self.hass.states.get(self.light_sensor)
            if state:
                try:
                    updated_data["sensor_light_level"] = float(state.state)
                except (ValueError, TypeError):
                    pass

        # Update state machine info
        updated_data.update(
            {
                "state": self._state.value,
                "last_presence": self._last_presence_time,
                "manual_states": self._manual_states.copy(),
            }
        )

        return updated_data

    async def _async_presence_changed(self, event) -> None:
        """Handle presence sensor state changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.state == STATE_ON:
            await self._handle_presence_detected()
        else:
            await self._handle_presence_lost()

    async def _handle_presence_detected(self) -> None:
        """Handle presence detection."""
        self._last_presence_time = dt_util.utcnow()
        self._cancel_timers()

        if self._state != RoomState.OCCUPIED:
            self._state = RoomState.OCCUPIED
            await self._apply_light_states()

        await self.async_refresh()

    async def _handle_presence_lost(self) -> None:
        """Handle loss of presence."""
        if self._state == RoomState.OCCUPIED:
            self._state = RoomState.DETECTION_TIMEOUT
            self._start_detection_timer()

        await self.async_refresh()

    def _cancel_timers(self) -> None:
        """Cancel all active timers."""
        if self._detection_timer:
            self._detection_timer()
            self._detection_timer = None
        if self._countdown_timer:
            self._countdown_timer()
            self._countdown_timer = None

    def _start_detection_timer(self) -> None:
        """Start the detection timeout timer."""
        self._cancel_timers()
        self._detection_timer = self.hass.loop.call_later(
            self._detection_timeout,
            self.hass.async_create_task,
            self._handle_detection_timeout(),
        )

    async def _handle_detection_timeout(self) -> None:
        """Handle detection timeout expiration."""
        self._detection_timer = None
        if self._state == RoomState.DETECTION_TIMEOUT:
            self._state = RoomState.COUNTDOWN
            self._start_countdown_timer()
            await self.async_refresh()

    def _start_countdown_timer(self) -> None:
        """Start the vacancy countdown timer."""
        self._cancel_timers()
        timeout = self._short_timeout if self._is_night_mode() else self._long_timeout
        self._countdown_timer = self.hass.loop.call_later(
            timeout,
            self.hass.async_create_task,
            self._handle_countdown_timeout(),
        )

    async def _handle_countdown_timeout(self) -> None:
        """Handle countdown timeout expiration."""
        self._countdown_timer = None
        if self._state == RoomState.COUNTDOWN:
            self._state = RoomState.VACANT
            await self._turn_off_lights()
            await self.async_refresh()

    async def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        if self._state == RoomState.OCCUPIED:
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            if new_state is not None:
                self._manual_states[entity_id] = new_state.state == STATE_ON
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

    def _get_active_lights(self) -> list:
        """Get the currently active light set based on night mode."""
        return self.night_lights if self._is_night_mode() else self.lights

    def _is_night_mode(self) -> bool:
        """Check if night mode is active."""
        # This will be implemented when night mode configuration is added
        return False

    async def async_entity_changed(
        self, entity_type: str, key: str, value: Any
    ) -> None:
        """Handle entity state changes."""
        self.data[f"{entity_type}_{key}"] = value
        # Store in config entry options
        new_options = dict(self.entry.options)
        new_options[key] = value
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
        self.async_set_updated_data(self.data)

    # These methods now just call the common method with the appropriate type
    async def async_switch_changed(self, key: str, value: bool) -> None:
        """Handle switch changes."""
        await self.async_entity_changed("switch", key, value)

    async def async_number_changed(self, key: str, value: float) -> None:
        """Handle number changes."""
        await self.async_entity_changed("number", key, value)

    async def async_time_changed(self, key: str, value: str) -> None:
        """Handle time changes."""
        await self.async_entity_changed("time", key, value)
