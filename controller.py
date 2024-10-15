"""Controller for Dynamic Presence integration."""
from datetime import timedelta
import logging

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_PRESENCE_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class DynamicPresenceController:
    """Controller class for Dynamic Presence integration."""

    def __init__(self, hass: HomeAssistant, config_entry):
        """Initialize the Dynamic Presence controller."""
        self.hass = hass
        self.config_entry = config_entry
        self.presence_sensor = config_entry.data['presence_sensor']
        self.controlled_entities = config_entry.data['controlled_entities']
        self.presence_timeout = config_entry.data[CONF_PRESENCE_TIMEOUT]
        self.active_room_threshold = config_entry.data[CONF_ACTIVE_ROOM_THRESHOLD] * 60  # Convert to seconds
        self.active_room_timeout = config_entry.data[CONF_ACTIVE_ROOM_TIMEOUT]
        self._remove_state_listener = None
        self._timers = {}
        self.presence_start_time = None
        self.is_active_room = False
        self._enabled = True  # Set to True by default

    @property
    def is_enabled(self) -> bool:
        """Return whether the controller is enabled."""
        return self._enabled

    async def enable(self):
        """Enable the controller."""
        if not self._enabled:
            self._enabled = True
            await self.async_setup()  # Re-establish listeners and timers

    async def disable(self):
        """Disable the controller."""
        if self._enabled:
            self._enabled = False
            await self.async_unload()  # Cancel listeners and timers

    async def async_setup(self):
        """Set up the controller."""
        if self._enabled:
            self._remove_state_listener = async_track_state_change_event(
                self.hass, [self.presence_sensor], self.handle_presence_change
            )
            _LOGGER.debug("Set up state change listener for %s", self.presence_sensor)

    @callback
    def handle_presence_change(self, event: Event):
        """Handle changes in presence sensor state."""
        if not self._enabled:
            return

        new_state: State | None = event.data.get('new_state')
        if new_state is None:
            return

        _LOGGER.debug("Presence sensor %s changed to %s", event.data.get('entity_id'), new_state.state)

        if new_state.state == STATE_ON:
            _LOGGER.debug("Presence detected, calling handle_presence_detected")
            self.hass.async_create_task(self.handle_presence_detected())
        elif new_state.state == STATE_OFF:
            _LOGGER.debug("Presence cleared, calling handle_presence_clear")
            self.hass.async_create_task(self.handle_presence_clear())

    async def handle_presence_detected(self):
        """Handle presence detection."""
        _LOGGER.debug("Presence detected")
        self.cancel_timer("presence")
        await self.turn_on_entities()

        if self.presence_start_time is None:
            self.presence_start_time = dt_util.utcnow()
            _LOGGER.debug("Starting active room timer for %s seconds", self.active_room_threshold)
            self.start_timer("active_room")

        async_dispatcher_send(self.hass, f"{DOMAIN}_{self.config_entry.entry_id}_update")

    async def handle_presence_clear(self):
        """Handle presence clearing."""
        _LOGGER.debug("Presence cleared")
        self.cancel_timer("active_room")
        timeout = self.active_room_timeout if self.is_active_room else self.presence_timeout
        _LOGGER.debug("Starting presence timer for %s seconds", timeout)
        self.start_timer("presence")
        self.presence_start_time = None
        self.is_active_room = False

        async_dispatcher_send(self.hass, f"{DOMAIN}_{self.config_entry.entry_id}_update")

    def start_timer(self, timer_type: str, duration: int | None = None):
        """Start a timer."""
        if duration is None:
            if timer_type == "presence":
                duration = self.presence_timeout
            elif timer_type == "active_room":
                duration = self.active_room_threshold

        _LOGGER.debug("Starting %s timer for %s seconds", timer_type, duration)
        self.cancel_timer(timer_type)
        expiration_time = dt_util.utcnow() + timedelta(seconds=duration)
        self._timers[timer_type] = async_track_point_in_time(
            self.hass, self.timer_expired_callback(timer_type), expiration_time
        )
        _LOGGER.debug("%s timer started, will expire at %s", timer_type, expiration_time)

    def cancel_timer(self, timer_type: str):
        """Cancel a timer."""
        if self._timers.get(timer_type):
            _LOGGER.debug("Cancelling %s timer", timer_type)
            self._timers[timer_type]()
            self._timers[timer_type] = None

    @callback
    def timer_expired_callback(self, timer_type: str):
        """Create a callback for timer expiration."""
        @callback
        def timer_callback(_):
            _LOGGER.debug("%s timer expired", timer_type)
            self._timers[timer_type] = None
            if timer_type == "presence":
                _LOGGER.debug("Presence timer expired, turning off entities")
                self.hass.async_create_task(self.turn_off_entities())
            elif timer_type == "active_room":
                if self.hass.states.get(self.presence_sensor).state == STATE_ON:
                    _LOGGER.debug("Room became active")
                    self.is_active_room = True

            async_dispatcher_send(self.hass, f"{DOMAIN}_{self.config_entry.entry_id}_update")
        return timer_callback

    async def turn_on_entities(self):
        """Turn on controlled entities."""
        _LOGGER.debug("Turning on controlled entities: %s", self.controlled_entities)
        for entity_id in self.controlled_entities:
            await self.hass.services.async_call('homeassistant', 'turn_on', {'entity_id': entity_id})

    async def turn_off_entities(self):
        """Turn off controlled entities."""
        _LOGGER.debug("Turning off controlled entities: %s", self.controlled_entities)
        for entity_id in self.controlled_entities:
            await self.hass.services.async_call('homeassistant', 'turn_off', {'entity_id': entity_id})

    async def async_unload(self):
        """Unload the Dynamic Presence Controller."""
        if self._remove_state_listener:
            self._remove_state_listener()
            self._remove_state_listener = None
        for timer in self._timers.values():
            if timer:
                timer()
        self._timers.clear()

    async def async_update_config(self):
        """Update the controller configuration."""
        _LOGGER.info("Updating controller configuration")
        # Re-initialize relevant variables from the updated config
        self.presence_timeout = self.config_entry.data[CONF_PRESENCE_TIMEOUT]
        self.active_room_threshold = self.config_entry.data[CONF_ACTIVE_ROOM_THRESHOLD] * 60
        self.active_room_timeout = self.config_entry.data[CONF_ACTIVE_ROOM_TIMEOUT]

        _LOGGER.info("Controller configuration updated: presence_timeout=%s, active_room_threshold=%s, active_room_timeout=%s",
                     self.presence_timeout, self.active_room_threshold, self.active_room_timeout)

        # Temporarily comment out the dispatcher send
        # async_dispatcher_send(self.hass, f"{DOMAIN}_{self.config_entry.entry_id}_update")
