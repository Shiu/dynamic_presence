"""State machine for Dynamic Presence integration."""

from enum import Enum
import logging
from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime as dt

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers.event import async_call_later
from homeassistant.const import STATE_ON
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NIGHT_MODE_SWITCH,
    CONF_NIGHT_TIME_START,
    CONF_NIGHT_TIME_END,
)

if TYPE_CHECKING:
    from .coordinator import DynamicPresenceCoordinator

logPresenceControl = logging.getLogger("dynamic_presence.presence_control")


class RoomState(Enum):
    """Room state machine states."""

    VACANT = "vacant"
    OCCUPIED = "occupied"
    DETECTION_TIMEOUT = "detection_timeout"
    COUNTDOWN = "countdown"


class PresenceControl:
    """Presence state machine controller."""

    def __init__(
        self,
        coordinator: "DynamicPresenceCoordinator",
    ) -> None:
        """Initialize the presence controller."""
        self.coordinator = coordinator
        self.hass = coordinator.hass
        self._state = RoomState.VACANT
        self._switches = {}
        self._last_presence_time = None
        self._occupancy_start_time = None
        self._last_logged_state = None
        self._detection_timer = None
        self._countdown_timer = None
        self._night_mode_switch = coordinator.entry.options.get(CONF_NIGHT_MODE_SWITCH)
        self._night_mode_state = False
        self._night_time_start = coordinator.entry.options.get(CONF_NIGHT_TIME_START)
        self._night_time_end = coordinator.entry.options.get(CONF_NIGHT_TIME_END)

    @property
    @callback
    def state(self) -> RoomState:
        """Return current state."""
        return self._state

    @property
    @callback
    def durations(self) -> Dict[str, Any]:
        """Get current duration values."""
        current_time = dt_util.utcnow()
        durations = {
            "sensor_occupancy_duration": 0,
            "sensor_absence_duration": 0,
        }

        # Calculate occupancy duration from start time
        if self._occupancy_start_time and self.state in [
            RoomState.OCCUPIED,
            RoomState.DETECTION_TIMEOUT,
        ]:
            durations["sensor_occupancy_duration"] = int(
                (current_time - self._occupancy_start_time).total_seconds()
            )

        # Calculate absence duration from last presence
        if self._last_presence_time and self.state in [
            RoomState.COUNTDOWN,
            RoomState.VACANT,
        ]:
            durations["sensor_absence_duration"] = int(
                (current_time - self._last_presence_time).total_seconds()
            )

        # Only log on significant changes (every 30 seconds) or state transitions
        if (
            durations["sensor_occupancy_duration"] % 30 == 0
        ) or self._last_logged_state != self.state:
            self._last_logged_state = self.state

        return durations

    async def handle_presence_event(self, event) -> None:
        """Handle presence sensor state changes."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        try:
            if new_state.state == "on":
                await self._on_presence_sensor_activated()
            else:
                await self._on_presence_sensor_deactivated()
        except (HomeAssistantError, ServiceNotFound) as err:
            logPresenceControl.warning("Error handling presence event: %s", err)

    @callback
    def _cancel_detection_timer(self) -> None:
        """Cancel detection timer."""
        if self._detection_timer is not None:
            logPresenceControl.debug("Cancelling detection timer")
            self._detection_timer = None

    @callback
    def _cancel_countdown_timer(self) -> None:
        """Cancel countdown timer."""
        if self._countdown_timer is not None:
            logPresenceControl.debug("Cancelling countdown timer")
            self._countdown_timer = None

    @callback
    def _cancel_timers(self) -> None:
        """Cancel all active timers."""
        if self._detection_timer:
            self._detection_timer()
            self._detection_timer = None

        if self._countdown_timer:
            self._countdown_timer()
            self._countdown_timer = None

        logPresenceControl.debug("All timers cancelled")

    @callback
    def _start_detection_timer(self) -> None:
        """Start the detection timeout timer."""
        if self._detection_timer:
            self._detection_timer()
            self._detection_timer = None

        detection_timeout = self.coordinator.detection_timeout
        self._detection_timer = async_call_later(
            self.hass, detection_timeout, self._detection_timer_finished
        )
        logPresenceControl.debug(
            "Starting detection timer for %s seconds",
            detection_timeout,
        )

    @callback
    def _start_countdown_timer(self) -> None:
        """Start the countdown timer."""
        if self._countdown_timer is not None:
            self._countdown_timer()
            self._countdown_timer = None

        base_timeout = (
            self.coordinator.short_timeout
            if self.coordinator.is_night_mode()
            else self.coordinator.long_timeout
        )

        # Subtract detection timeout from the countdown period
        adjusted_timeout = max(0, base_timeout - self.coordinator.detection_timeout)

        self._countdown_timer = async_call_later(
            self.hass, adjusted_timeout, self._countdown_timer_finished
        )
        logPresenceControl.debug(
            "Starting countdown timer for %s seconds",
            adjusted_timeout,
        )

    async def _on_presence_sensor_activated(self) -> None:
        """Handle presence sensor activation."""
        self._last_presence_time = dt_util.utcnow()
        if self._state != RoomState.OCCUPIED:
            self._occupancy_start_time = self._last_presence_time
            await self._update_state(RoomState.OCCUPIED)

    async def _on_presence_sensor_deactivated(self) -> None:
        """Handle presence sensor deactivation."""
        self._last_presence_time = dt_util.utcnow()
        if self._state == RoomState.OCCUPIED:
            await self._update_state(RoomState.DETECTION_TIMEOUT)
            self._start_detection_timer()

    async def handle_presence_detected(self) -> None:
        """Handle presence detection."""
        if self._state != RoomState.OCCUPIED:
            logPresenceControl.debug("Presence detected - transitioning to occupied")
            self._cancel_timers()
            await self._update_state(RoomState.OCCUPIED)
        else:
            logPresenceControl.debug("Already in occupied state")

    async def handle_presence_lost(self) -> None:
        """Handle loss of presence from OCCUPIED state."""
        if self._state == RoomState.OCCUPIED:
            self._last_presence_time = dt_util.utcnow()

            # Check if any lights are on before starting detection timer
            any_lights_on = False
            for light in self.coordinator.active_lights:
                try:
                    state = self.hass.states.get(light)
                    if state and state.state == STATE_ON:
                        any_lights_on = True
                        break
                except HomeAssistantError as err:
                    logPresenceControl.error("Error checking light state: %s", err)

            if any_lights_on:
                await self._update_state(RoomState.DETECTION_TIMEOUT)
                self._start_detection_timer()
            else:
                logPresenceControl.debug("All lights already off - room is vacant")
                await self._update_state(RoomState.VACANT)
        else:
            logPresenceControl.debug(
                "Ignoring presence lost in %s state",
                self._state.value,
            )

    async def update_timers(self, control_type: str, key: str) -> None:
        """Update running timers when control values change."""
        try:
            if (
                self._state == RoomState.DETECTION_TIMEOUT
                and key == "detection_timeout"
            ):
                logPresenceControl.debug(
                    "Updating detection timer: %s seconds",
                    self.coordinator.detection_timeout,
                )
                self._start_detection_timer()
            elif self._state == RoomState.COUNTDOWN and key in [
                "long_timeout",
                "short_timeout",
            ]:
                timeout = (
                    self.coordinator.short_timeout
                    if self.coordinator.is_night_mode()
                    else self.coordinator.long_timeout
                )
                logPresenceControl.debug(
                    "Updating countdown timer: %s seconds",
                    timeout,
                )
                self._start_countdown_timer()
        except (HomeAssistantError, ServiceNotFound) as err:
            logPresenceControl.warning(
                "Error updating timers for %s.%s: %s",
                control_type,
                key,
                err,
            )

    async def start_detection_timer(self) -> None:
        """Public method to start detection timer."""
        await self._start_detection_timer()

    async def start_countdown_timer(self) -> None:
        """Public method to start countdown timer."""
        await self._start_countdown_timer()

    async def handle_detection_timeout(self) -> None:
        """Handle detection timeout completion."""
        if self.state == RoomState.DETECTION_TIMEOUT:
            # Check if any lights are still on
            any_lights_on = False
            for light in self.coordinator.active_lights:
                try:
                    state = self.hass.states.get(light)
                    if state and state.state == STATE_ON:
                        any_lights_on = True
                        break
                except HomeAssistantError as err:
                    logPresenceControl.error("Error checking light state: %s", err)

            if any_lights_on:
                logPresenceControl.debug(
                    "Detection timeout expired, starting countdown"
                )
                await self._update_state(RoomState.COUNTDOWN)
                self._start_countdown_timer()
            else:
                logPresenceControl.debug(
                    "Detection timeout expired, all lights off - clearing manual states"
                )
                await self.coordinator.clear_manual_states()
                logPresenceControl.debug("Room is now vacant")
                await self._update_state(RoomState.VACANT)

    async def _update_state(self, new_state: RoomState) -> None:
        """Update state and notify coordinator."""
        if new_state == self._state:
            return

        # Validate state transition
        valid_transitions = {
            RoomState.VACANT: [RoomState.OCCUPIED],
            RoomState.OCCUPIED: [RoomState.DETECTION_TIMEOUT, RoomState.VACANT],
            RoomState.DETECTION_TIMEOUT: [RoomState.OCCUPIED, RoomState.COUNTDOWN],
            RoomState.COUNTDOWN: [RoomState.OCCUPIED, RoomState.VACANT],
        }

        if new_state not in valid_transitions[self._state]:
            logPresenceControl.warning(
                "Invalid state transition attempted: %s -> %s",
                self._state.value,
                new_state.value,
            )
            return

        logPresenceControl.info(
            "State transition: %s -> %s (last presence: %s)",
            self._state.value,
            new_state.value,
            self._last_presence_time,
        )

        self._state = new_state
        logPresenceControl.debug("Notifying coordinator of state change")

        try:
            await self.coordinator.async_handle_state_changed(new_state)
        except (HomeAssistantError, ServiceNotFound) as err:
            logPresenceControl.error("Error notifying coordinator: %s", err)

    async def _countdown_timer_finished(self, _now) -> None:
        """Handle countdown timer completion."""
        self._countdown_timer = None
        if self._state == RoomState.COUNTDOWN:
            logPresenceControl.debug("Countdown finished, room is now vacant")
            await self._update_state(RoomState.VACANT)

    async def _detection_timer_finished(self, _now) -> None:
        """Handle detection timer completion."""
        self._detection_timer = None
        if self._state == RoomState.DETECTION_TIMEOUT:
            logPresenceControl.debug("Detection timeout expired, starting countdown")
            await self._update_state(RoomState.COUNTDOWN)
            self._start_countdown_timer()

    @property
    def night_mode_switch_state(self) -> bool:
        """Get the current state of the night mode switch."""
        if not self._night_mode_switch:
            return False
        state = self.hass.states.get(self._night_mode_switch)
        return state is not None and state.state == "on"

    def is_night_time(self) -> bool:
        """Check if current time is within night time hours."""
        if not self._night_time_start or not self._night_time_end:
            return True  # If no time constraints, always allow night mode

        now = dt.now(self.hass.config.time_zone)
        current_time = now.time()
        start_time = dt.strptime(self._night_time_start, "%H:%M").time()
        end_time = dt.strptime(self._night_time_end, "%H:%M").time()

        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:  # Handles overnight periods (e.g., 22:00 - 06:00)
            return current_time >= start_time or current_time <= end_time

    def is_night_mode_active(self) -> bool:
        """Check if night mode is currently active."""
        return self.coordinator.check_night_mode_active()
