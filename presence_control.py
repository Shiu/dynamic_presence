"""State machine for Dynamic Presence integration."""

from enum import Enum
import logging
from typing import Dict, Any, TYPE_CHECKING
from datetime import datetime as dt

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers.event import async_call_later
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

    # 1. Core Initialization
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

    # 2. Properties
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

        if self._occupancy_start_time and self.state in [
            RoomState.OCCUPIED,
            RoomState.DETECTION_TIMEOUT,
        ]:
            durations["sensor_occupancy_duration"] = int(
                (current_time - self._occupancy_start_time).total_seconds()
            )

        if self._last_presence_time and self.state in [
            RoomState.COUNTDOWN,
            RoomState.VACANT,
        ]:
            durations["sensor_absence_duration"] = int(
                (current_time - self._last_presence_time).total_seconds()
            )

        if (
            durations["sensor_occupancy_duration"] % 30 == 0
        ) or self._last_logged_state != self.state:
            self._last_logged_state = self.state

        return durations

    @property
    def active_lights(self) -> list:
        """Get currently active light set based on mode."""
        return (
            self.coordinator.night_lights
            if self.is_night_mode_active()
            else self.coordinator.lights
        )

    # 3. State Management
    async def _update_state(self, new_state: RoomState) -> None:
        """Update state and notify coordinator."""
        if new_state == self._state:
            return

        if not self._validate_state_transition(new_state):
            return

        logPresenceControl.info(
            "State transition: %s -> %s (last presence: %s)",
            self._state.value,
            new_state.value,
            self._last_presence_time,
        )

        self._state = new_state

        if new_state == RoomState.OCCUPIED:
            self._occupancy_start_time = dt_util.utcnow()
        elif new_state == RoomState.VACANT:
            self._occupancy_start_time = None

        try:
            await self.coordinator.async_handle_state_changed(new_state)
        except (HomeAssistantError, ServiceNotFound) as err:
            logPresenceControl.error("Error notifying coordinator: %s", err)

    def _validate_state_transition(self, new_state: RoomState) -> bool:
        """Validate state transition."""
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
            return False
        return True

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

            if self.coordinator.light_controller.check_any_lights_on(
                self.active_lights
            ):
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

    async def handle_detection_timeout(self) -> None:
        """Handle detection timeout completion."""
        if self.state == RoomState.DETECTION_TIMEOUT:
            if self.coordinator.light_controller.check_any_lights_on(
                self.active_lights
            ):
                logPresenceControl.debug(
                    "Detection timeout expired, starting countdown"
                )
                await self._update_state(RoomState.COUNTDOWN)
                self._start_countdown_timer()
            else:
                logPresenceControl.debug(
                    "Detection timeout expired, all lights off - room is vacant"
                )
                await self._update_state(RoomState.VACANT)

    # 4. Timer Management
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
        if self._countdown_timer:
            self._countdown_timer()
            self._countdown_timer = None

        timeout = (
            self.coordinator.short_timeout
            if self.is_night_mode_active()
            else self.coordinator.long_timeout
        )

        logPresenceControl.debug(
            "Starting countdown timer: %s seconds",
            timeout,
        )

        self._countdown_timer = async_call_later(
            self.hass, timeout, self._countdown_timer_finished
        )

    async def _detection_timer_finished(self, _now) -> None:
        """Handle detection timer completion."""
        self._detection_timer = None
        if self._state == RoomState.DETECTION_TIMEOUT:
            logPresenceControl.debug(
                "Detection timeout expired, transitioning to countdown"
            )
            await self._update_state(RoomState.COUNTDOWN)
            self._start_countdown_timer()

    async def _countdown_timer_finished(self, _now) -> None:
        """Handle countdown timer completion."""
        self._countdown_timer = None
        if self._state == RoomState.COUNTDOWN:
            logPresenceControl.debug("Countdown finished, transitioning to vacant")
            await self._update_state(RoomState.VACANT)

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
                    if self.is_night_mode_active()
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

    # 5. Event Handlers
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

    # 6. Night Mode
    def is_night_time(self) -> bool:
        """Check if current time is within night time hours."""
        if not self._night_time_start or not self._night_time_end:
            return True

        now = dt.now(self.hass.config.time_zone)
        current_time = now.time()
        start_time = dt.strptime(self._night_time_start, "%H:%M").time()
        end_time = dt.strptime(self._night_time_end, "%H:%M").time()

        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            return current_time >= start_time or current_time <= end_time

    def _check_night_mode_switch(self) -> bool:
        """Check if night mode is forced by switch."""
        return self.coordinator.data.get("switch_night_mode", False)

    def is_night_mode_active(self) -> bool:
        """Check if night mode is currently active."""
        night_mode = self.coordinator.data.get("switch_night_mode", False)
        if night_mode:
            return True
        return False
