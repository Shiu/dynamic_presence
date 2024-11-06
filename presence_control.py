"""State machine for Dynamic Presence integration."""

from enum import Enum
import logging
from typing import Callable

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

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
        state_changed_callback: Callable,
    ) -> None:
        """Initialize the presence controller."""
        self.hass = hass
        self._state = RoomState.VACANT
        self._state_changed_callback = state_changed_callback
        self._last_presence_time = None
        self._detection_timeout_end = None
        logPresenceControl.debug("Presence control initialized")

    @property
    def state(self) -> RoomState:
        """Return current state."""
        return self._state

    @property
    def last_presence_time(self):
        """Return last presence time."""
        return self._last_presence_time

    async def _set_state(self, new_state: RoomState) -> None:
        """Set new state and notify callback."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            logPresenceControl.debug(
                "State transition: %s -> %s (last presence: %s)",
                old_state.value,
                new_state.value,
                self._last_presence_time,
            )
            if self._state_changed_callback:
                await self._state_changed_callback(new_state)

    async def handle_presence_detected(self) -> None:
        """Handle presence detection."""
        if self._state == RoomState.DETECTION_TIMEOUT:
            # Keep existing last_presence_time since occupancy wasn't really lost
            pass
        else:
            # For all other states, reset the presence time
            self._last_presence_time = dt_util.utcnow()

        await self._set_state(RoomState.OCCUPIED)

    async def handle_presence_lost(self) -> None:
        """Handle loss of presence."""
        if self._state == RoomState.OCCUPIED:
            await self._set_state(RoomState.DETECTION_TIMEOUT)

    async def transition_to_countdown(self) -> None:
        """Transition to countdown state."""
        if self._state == RoomState.DETECTION_TIMEOUT:
            self._detection_timeout_end = dt_util.utcnow()
            await self._set_state(RoomState.COUNTDOWN)

    async def transition_to_vacant(self) -> None:
        """Transition to vacant state."""
        if self._state == RoomState.COUNTDOWN:
            await self._set_state(RoomState.VACANT)
