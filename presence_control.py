"""State machine for Dynamic Presence integration."""

from datetime import timedelta
from enum import Enum
import logging
from typing import Dict, Any, TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers.event import async_track_point_in_utc_time, async_call_later
from homeassistant.helpers.template import TemplateError
from homeassistant.util import dt as dt_util


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
        hass: HomeAssistant,
        coordinator: "DynamicPresenceCoordinator",
    ) -> None:
        """Initialize the presence controller."""
        self.hass = hass
        self.coordinator = coordinator
        self._state = RoomState.VACANT
        self._last_presence_time = None
        self._detection_timeout_end = None
        self._detection_timer = None
        self._countdown_timer = None
        logPresenceControl.debug(
            "Presence control initialized in %s state", self._state.value
        )

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

        if self._last_presence_time is None:
            return durations

        if self._state in [RoomState.OCCUPIED, RoomState.DETECTION_TIMEOUT]:
            durations["sensor_occupancy_duration"] = int(
                (current_time - self._last_presence_time).total_seconds()
            )
        elif self._state in [RoomState.COUNTDOWN, RoomState.VACANT]:
            if self._detection_timeout_end:
                detection_timeout = self.coordinator.data["number_detection_timeout"]
                durations["sensor_absence_duration"] = detection_timeout + int(
                    (current_time - self._detection_timeout_end).total_seconds()
                )

        return durations

    async def handle_presence_event(self, event) -> None:
        """Handle presence sensor state changes."""
        logPresenceControl.debug(
            "Received presence event: %s",
            {
                "event_data": event.data,
                "event_type": getattr(event, "event_type", None),
            },
        )

        new_state = event.data.get("new_state")
        logPresenceControl.debug("Extracted new_state: %s", new_state)

        if new_state is None:
            logPresenceControl.debug("No new_state in event, ignoring")
            return

        # Log detailed state information
        logPresenceControl.debug(
            "Presence sensor state details: state=%s, attributes=%s",
            getattr(new_state, "state", None),
            getattr(new_state, "attributes", {}),
        )

        logPresenceControl.debug(
            "Current state: %s, New presence state: %s",
            self._state.value,
            new_state.state,
        )

        try:
            if new_state.state == "on":
                await self._on_presence_sensor_activated()
            else:
                await self._on_presence_sensor_deactivated()
        except (HomeAssistantError, ServiceNotFound) as err:
            logPresenceControl.warning(
                "Error handling presence event: %s", err, exc_info=True
            )

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
        self._cancel_detection_timer()
        self._cancel_countdown_timer()
        logPresenceControl.debug("All timers cancelled")

    @callback
    def _start_detection_timer(self) -> None:
        """Start the detection timeout timer."""
        if self._detection_timer:
            self._detection_timer.cancel()

        detection_timeout = self.coordinator.detection_timeout

        self._detection_timer = async_call_later(
            self.hass, detection_timeout, self._detection_timer_finished
        )
        logPresenceControl.debug(
            "Starting detection timer for %s seconds",
            detection_timeout,
        )

    async def _detection_timer_finished(self, _now) -> None:
        """Handle detection timer completion."""
        self._detection_timer = None
        await self.handle_detection_timeout()

    @callback
    def _start_countdown_timer(self) -> None:
        """Start the countdown timer."""
        if self._countdown_timer:
            self._countdown_timer.cancel()

        timeout = (
            self.coordinator.short_timeout
            if self.coordinator.is_night_mode()
            else self.coordinator.long_timeout
        )

        self._countdown_timer = async_call_later(
            self.hass, timeout, self._countdown_timer_finished
        )
        logPresenceControl.debug(
            "Starting countdown timer for %s seconds",
            timeout,
        )

    async def _countdown_timer_finished(self, _now) -> None:
        """Handle countdown timer completion."""
        self._countdown_timer = None
        await self.handle_countdown_finished()

    @callback
    def _update_countdown_timer(self) -> None:
        """Update countdown timer with new timeout value."""
        if self._countdown_timer is None:
            return

        try:
            # Calculate new timeout
            timeout = (
                self.coordinator.data["number_short_timeout"]
                if self.coordinator.is_night_mode()
                else self.coordinator.data["number_long_timeout"]
            )
            detection_timeout = self.coordinator.data["number_detection_timeout"]
            adjusted_timeout = timeout - detection_timeout

            # Calculate new expiration based on current time
            expiration_time = dt_util.utcnow() + timedelta(seconds=adjusted_timeout)

            logPresenceControl.debug(
                "Updating countdown timer for %s seconds (expires: %s)",
                adjusted_timeout,
                expiration_time,
            )

            self._cancel_countdown_timer()
            self._countdown_timer = async_track_point_in_utc_time(
                self.hass, self._on_countdown_timer_expired, expiration_time
            )
        except (HomeAssistantError, TemplateError) as err:
            logPresenceControl.warning(
                "Error updating countdown timer: %s", err, exc_info=True
            )

    async def _on_detection_timer_expired(self, _now) -> None:
        """Handle detection timer expiration."""
        if self._state != RoomState.DETECTION_TIMEOUT:
            return  # Ignore if not in correct state
        logPresenceControl.debug("Detection timer expired at %s", dt_util.utcnow())
        self._detection_timer = None
        await self.transition_to_countdown()
        self._start_countdown_timer()

    async def _on_countdown_timer_expired(self, _now) -> None:
        """Handle countdown timer expiration."""
        if self._state != RoomState.COUNTDOWN:
            return  # Ignore if not in correct state
        logPresenceControl.debug("Countdown timer expired at %s", dt_util.utcnow())
        self._countdown_timer = None
        await self.transition_to_vacant()

    async def _on_presence_sensor_activated(self) -> None:
        """Handle presence sensor turning ON."""
        self._cancel_timers()  # Cancel all timers when presence detected
        await self.handle_presence_detected()

    async def _on_presence_sensor_deactivated(self) -> None:
        """Handle presence sensor turning OFF."""
        await self.handle_presence_lost()

    async def handle_presence_detected(self) -> None:
        """Handle presence detection from any state.

        State Transition: ANY_STATE → OCCUPIED
        - Updates presence time (except in DETECTION_TIMEOUT)
        - Transitions to OCCUPIED state
        - Updates coordinator
        """
        try:
            # Update presence time unless in DETECTION_TIMEOUT
            if self._state != RoomState.DETECTION_TIMEOUT:
                self._last_presence_time = dt_util.utcnow()
                logPresenceControl.debug(
                    "Updated presence time to %s", self._last_presence_time
                )

            # Transition to OCCUPIED state
            await self._set_state(RoomState.OCCUPIED)

        except (HomeAssistantError, ServiceNotFound) as err:
            logPresenceControl.warning(
                "Failed to handle presence detection: %s", err, exc_info=True
            )
            raise

    async def handle_presence_lost(self) -> None:
        """Handle loss of presence."""
        if self._state == RoomState.OCCUPIED:
            await self._set_state(RoomState.DETECTION_TIMEOUT)
            self._start_detection_timer()  # Start timer after state change
        else:
            logPresenceControl.warning(
                "Invalid state transition: Cannot handle presence lost from %s state",
                self._state.value,
            )

    async def transition_to_countdown(self) -> None:
        """Transition to countdown state."""
        if self._state == RoomState.DETECTION_TIMEOUT:
            self._detection_timeout_end = dt_util.utcnow()
            await self._set_state(RoomState.COUNTDOWN)
        else:
            logPresenceControl.warning(
                "Invalid state transition: Cannot transition to COUNTDOWN from %s state",
                self._state.value,
            )

    async def transition_to_vacant(self) -> None:
        """Transition to vacant state."""
        if self._state == RoomState.COUNTDOWN:
            await self._set_state(RoomState.VACANT)
        else:
            logPresenceControl.warning(
                "Invalid state transition: Cannot transition to VACANT from %s state",
                self._state.value,
            )

    async def _set_state(self, new_state: RoomState) -> None:
        """Set new state and notify coordinator."""
        try:
            if new_state != self._state:
                old_state = self._state
                self._state = new_state
                logPresenceControl.info(
                    "State transition: %s -> %s (last presence: %s)",
                    old_state.value,
                    new_state.value,
                    self._last_presence_time,
                )
                await self.coordinator.handle_state_changed(new_state)
        except (HomeAssistantError, ServiceNotFound) as err:
            logPresenceControl.warning(
                "Error during state transition to %s: %s",
                new_state.value,
                err,
                exc_info=True,
            )
            # Restore previous state on error
            self._state = old_state
            raise

    async def update_timers(self, control_type: str, key: str) -> None:
        """Update running timers when control values change.

        Args:
            control_type: Type of control being updated (e.g., "number")
            key: Control key being updated (e.g., "detection_timeout")
        """
        try:
            if (
                self._state == RoomState.DETECTION_TIMEOUT
                and key == "detection_timeout"
            ):
                logPresenceControl.debug(
                    "Updating detection timer due to timeout change: %s",
                    self.coordinator.data["number_detection_timeout"],
                )
                self._start_detection_timer()
            elif self._state == RoomState.COUNTDOWN and key in [
                "long_timeout",
                "short_timeout",
            ]:
                logPresenceControl.debug(
                    "Updating countdown timer due to timeout change: %s/%s",
                    self.coordinator.data["number_long_timeout"],
                    self.coordinator.data["number_short_timeout"],
                )
                self._start_countdown_timer()
        except (HomeAssistantError, TemplateError) as err:
            logPresenceControl.warning(
                "Error updating timers for %s.%s: %s",
                control_type,
                key,
                err,
                exc_info=True,
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
            logPresenceControl.debug("Detection timeout expired, starting countdown")
            await self.transition_to(RoomState.COUNTDOWN)
            self._start_countdown_timer()

    async def handle_countdown_finished(self) -> None:
        """Handle countdown timer completion."""
        if self.state == RoomState.COUNTDOWN:
            logPresenceControl.debug("Countdown finished, room is now vacant")
            await self.transition_to(RoomState.VACANT)
            # Here we'll add light control logic later

    async def transition_to(self, new_state: RoomState) -> None:
        """Handle state transitions."""
        if new_state == self.state:
            return

        old_state = self.state
        self._state = new_state

        logPresenceControl.info(
            "State transition: %s -> %s (last presence: %s)",
            old_state.value,
            new_state.value,
            self._last_presence_time,
        )

        # Update coordinator data
        await self.coordinator.async_refresh()
