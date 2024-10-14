"""Controller for Dynamic Presence integration."""
from datetime import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_PRESENCE_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

class DynamicPresenceController:
    """Controller class for Dynamic Presence."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the Dynamic Presence Controller."""
        self.hass = hass
        self.config_entry = config_entry
        self.presence_sensor = config_entry.data['presence_sensor']
        self.controlled_entities = config_entry.data['controlled_entities']
        self._remove_state_listener = None
        self._timers = {
            "presence": None,
            "active_room": None,
        }
        self.enabled_switch = f"switch.dynamic_presence_{config_entry.data['name'].lower().replace(' ', '_')}_enabled"
        self.presence_timeout = config_entry.data[CONF_PRESENCE_TIMEOUT]
        self.active_room_threshold = config_entry.data[CONF_ACTIVE_ROOM_THRESHOLD]
        self.active_room_timeout = config_entry.data[CONF_ACTIVE_ROOM_TIMEOUT]
        self.night_mode_start = config_entry.data[CONF_NIGHT_MODE_START]
        self.night_mode_end = config_entry.data[CONF_NIGHT_MODE_END]
        self.night_mode_timeout = config_entry.data[CONF_NIGHT_MODE_TIMEOUT]
        self.presence_start_time = None
        self.is_active_room = False
        _LOGGER.debug("Initializing DynamicPresenceController for %s", config_entry.data['name'])

    async def async_setup(self) -> None:
        """Set up the Dynamic Presence Controller."""
        self._remove_state_listener = async_track_state_change_event(
            self.hass, [self.presence_sensor], self.handle_presence_change
        )
        _LOGGER.debug("Set up state change listener for %s", self.presence_sensor)

        # Initialize state based on current presence sensor state
        presence_state = self.hass.states.get(self.presence_sensor)
        if presence_state:
            self.handle_presence_change(None)  # Remove await here

    async def async_unload(self) -> None:
        """Unload the Dynamic Presence Controller."""
        if self._remove_state_listener:
            self._remove_state_listener()
            self._remove_state_listener = None
        self.cancel_all_timers()

    @callback
    def handle_presence_change(self, event) -> None:
        """Handle changes in presence sensor state."""
        if not self.is_enabled():
            _LOGGER.debug("Dynamic Presence is not enabled, ignoring presence change")
            return

        new_state = self.hass.states.get(self.presence_sensor)
        if new_state is None:
            _LOGGER.debug("New state is None, ignoring presence change")
            return

        _LOGGER.debug("Presence sensor %s changed to %s", self.presence_sensor, new_state.state)

        if new_state.state == STATE_ON:
            self.hass.async_create_task(self.handle_presence_detected())
        elif new_state.state == STATE_OFF:
            self.hass.async_create_task(self.handle_presence_clear())

    def is_enabled(self) -> bool:
        """Check if the integration is enabled for this room."""
        state = self.hass.states.get(self.enabled_switch)
        enabled = state.state == STATE_ON if state else False
        _LOGGER.debug("Dynamic Presence enabled state: %s", enabled)
        return enabled

    async def handle_presence_detected(self) -> None:
        """Handle presence detection."""
        _LOGGER.debug("Presence detected, cancelling presence timer and turning on entities")
        self.cancel_timer("presence")
        for entity_id in self.controlled_entities:
            await self.hass.services.async_call('homeassistant', 'turn_on', {'entity_id': entity_id})

        if self.presence_start_time is None:
            self.presence_start_time = datetime.now()
            _LOGGER.debug("Starting active room timer for %s minutes", self.active_room_threshold)
            self.start_timer("active_room", self.active_room_threshold * 60)
        else:
            elapsed_time = (datetime.now() - self.presence_start_time).total_seconds() / 60
            if elapsed_time >= self.active_room_threshold and not self.is_active_room:
                _LOGGER.debug("Room became active after %s minutes", elapsed_time)
                self.is_active_room = True
                self.cancel_timer("active_room")

    async def handle_presence_clear(self) -> None:
        """Handle presence clearing."""
        self.cancel_timer("active_room")
        if self.is_active_room:
            _LOGGER.debug("Presence cleared in active room, starting timer for %s seconds", self.active_room_timeout)
            self.start_timer("presence", self.active_room_timeout)
        else:
            _LOGGER.debug("Presence cleared, starting timer for %s seconds", self.presence_timeout)
            self.start_timer("presence", self.presence_timeout)
        self.presence_start_time = None
        self.is_active_room = False

    def start_timer(self, timer_type: str, duration: int) -> None:
        """Start a timer."""
        _LOGGER.debug("Starting %s timer for %s seconds", timer_type, duration)
        self.cancel_timer(timer_type)
        self._timers[timer_type] = async_call_later(
            self.hass, duration, self.timer_expired_callback(timer_type)
        )

    def cancel_timer(self, timer_type: str) -> None:
        """Cancel a timer."""
        if self._timers[timer_type] is not None:
            _LOGGER.debug("Cancelling %s timer", timer_type)
            self._timers[timer_type]()
            self._timers[timer_type] = None

    def cancel_all_timers(self) -> None:
        """Cancel all timers."""
        for timer_type in self._timers:
            self.cancel_timer(timer_type)

    @callback
    def timer_expired_callback(self, timer_type: str):
        """Create a callback for timer expiration."""
        @callback
        def timer_callback(_):
            _LOGGER.debug("%s timer expired", timer_type)
            self._timers[timer_type] = None
            if timer_type == "presence":
                self.hass.async_create_task(self.turn_off_entities())
            elif timer_type == "active_room":
                if self.hass.states.get(self.presence_sensor).state == STATE_ON:
                    _LOGGER.debug("Room became active")
                    self.is_active_room = True
        return timer_callback

    async def turn_off_entities(self) -> None:
        """Turn off controlled entities."""
        for entity_id in self.controlled_entities:
            await self.hass.services.async_call('homeassistant', 'turn_off', {'entity_id': entity_id})

    def get_timer_state(self, timer_type: str) -> str:
        """Get the state of a timer."""
        if timer_type not in self._timers:
            return "idle"
        if self._timers[timer_type] is not None:
            remaining = (datetime.now() - self._timers[timer_type].call_time).total_seconds()
            return f"active - {remaining:.1f}s remaining"
        return "idle"
