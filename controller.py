"""Controller for Dynamic Presence integration."""
from datetime import timedelta, time
import logging
from typing import Any, Callable, Dict

from homeassistant.const import STATE_ON
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_time, async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_PRESENCE_TIMEOUT,
    DOMAIN,
    NUMBER_CONFIG,
    DEFAULT_NIGHT_MODE_START,
    DEFAULT_NIGHT_MODE_END,
    CONF_CONTROLLED_ENTITIES,
    CONF_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_SCALE,
    CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
    CONF_NIGHT_MODE_ENTITIES_BEHAVIOR,
)

_LOGGER = logging.getLogger(__name__)

class DynamicPresenceController(DataUpdateCoordinator):
    """Controller class for Dynamic Presence integration."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the Dynamic Presence controller."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.hass = hass
        self.config_entry = config_entry
        self._enabled = True
        self._timers: dict[str, Callable[[], None]] = {}
        self._listeners: dict[str, Callable[[], None]] = {}
        self.presence_detected = False
        self.is_active_room = False
        self.presence_start_time: dt_util.dt.datetime | None = None
        self.last_presence_end_time: dt_util.dt.datetime | None = None
        self.presence_sensor = config_entry.data['presence_sensor']
        self.controlled_entities = config_entry.data.get(CONF_CONTROLLED_ENTITIES, [])
        
        self._load_config_values()

    def _load_config_values(self) -> None:
        """
        Load configuration values from the config entry.
        This method uses the _validate_config method to ensure all values are valid.
        """
        options = self._validate_config(self.config_entry.options)
        
        self.presence_timeout = options.get(
            CONF_PRESENCE_TIMEOUT, 
            NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["default"]
        )
        self.active_room_threshold = options.get(
            CONF_ACTIVE_ROOM_THRESHOLD,
            NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["default"]
        )
        self.active_room_timeout = options.get(
            CONF_ACTIVE_ROOM_TIMEOUT,
            NUMBER_CONFIG[CONF_ACTIVE_ROOM_TIMEOUT]["default"]
        )
        self.night_mode_timeout = options.get(
            CONF_NIGHT_MODE_TIMEOUT,
            NUMBER_CONFIG[CONF_NIGHT_MODE_TIMEOUT]["default"]
        )
        self.night_mode_start = options.get(CONF_NIGHT_MODE_START, DEFAULT_NIGHT_MODE_START)
        self.night_mode_end = options.get(CONF_NIGHT_MODE_END, DEFAULT_NIGHT_MODE_END)
        self.night_mode_enable = options.get(CONF_NIGHT_MODE_ENABLE, False)
        self.night_mode_scale = options.get(
            CONF_NIGHT_MODE_SCALE,
            NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["default"]
        )
        self.night_mode_controlled_entities = options.get(CONF_NIGHT_MODE_CONTROLLED_ENTITIES, [])
        self.night_mode_entities_behavior = options.get(CONF_NIGHT_MODE_ENTITIES_BEHAVIOR, "additive")
        
        _LOGGER.debug("Loaded config values: %s", {
            "presence_timeout": self.presence_timeout,
            "active_room_threshold": self.active_room_threshold,
            "active_room_timeout": self.active_room_timeout,
            "night_mode_timeout": self.night_mode_timeout,
            "night_mode_start": self.night_mode_start,
            "night_mode_end": self.night_mode_end,
            "night_mode_enable": self.night_mode_enable,
            "night_mode_scale": self.night_mode_scale,
            "night_mode_controlled_entities": self.night_mode_controlled_entities,
            "night_mode_entities_behavior": self.night_mode_entities_behavior,
        })

    # Properties
    @property
    def is_enabled(self) -> bool:
        """Return whether the controller is enabled."""
        return self._enabled

    @property
    def is_night_mode_enabled(self) -> bool:
        """Return whether night mode is enabled."""
        return self.night_mode_enable

    # Setup and teardown methods
    async def async_setup(self) -> bool:
        """
        Set up the controller.
        This method is called when the integration is being set up.
        It sets up the state change listener for the presence sensor.
        """
        try:
            if self._enabled:
                self._remove_state_listener = async_track_state_change_event(
                    self.hass, [self.presence_sensor], self.handle_presence_change
                )
                _LOGGER.info("Set up state change listener for %s", self.presence_sensor)
                _LOGGER.debug("Controlled entities: %s", self.controlled_entities)
            return True
        except Exception as e:
            _LOGGER.error("Error setting up Dynamic Presence Controller: %s", e)
            return False

    async def async_unload(self) -> None:
        """
        Unload the Dynamic Presence Controller.
        This method is called when the integration is being unloaded.
        It removes all listeners and cancels all timers.
        """
        try:
            if hasattr(self, '_remove_state_listener'):
                self._remove_state_listener()
            
            for timer in self._timers.values():
                timer()
            self._timers.clear()
            
            for remove_listener in self._listeners.values():
                remove_listener()
            self._listeners.clear()
            
        except Exception as e:
            _LOGGER.error("Error unloading Dynamic Presence Controller: %s", e)

    async def async_added_to_hass(self) -> None:
        """
        Called when entity is added to hass.
        This method restores the last known state of the controller.
        """
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self.presence_detected = state.state == STATE_ON
            self.is_active_room = state.attributes.get("is_active_room", False)
            last_changed = state.last_changed
            if self.presence_detected:
                self.presence_start_time = last_changed
            else:
                self.last_presence_end_time = last_changed
        
        self._dispatch_update()

    # Presence handling methods
    @callback
    def handle_presence_change(self, event: Event) -> None:
        """
        Handle changes to the presence sensor state.
        This method is called whenever the state of the presence sensor changes.
        """
        new_state = event.data.get('new_state')
        if new_state is None:
            return

        self.presence_detected = new_state.state == STATE_ON
        _LOGGER.info("Presence state changed to: %s", self.presence_detected)

        if self.presence_detected:
            self.hass.async_create_task(self.handle_presence_detected())
        else:
            self.hass.async_create_task(self.handle_presence_clear())

    async def handle_presence_detected(self) -> None:
        """
        Handle presence detection.
        This method is called when presence is detected in the room.
        It turns on controlled entities and starts the active room timer.
        """
        try:
            _LOGGER.debug("Presence detected")
            self.cancel_timer("presence")
            await self.turn_on_controlled_entities()

            if self.presence_start_time is None:
                self.presence_start_time = dt_util.utcnow()
                _LOGGER.debug("Starting active room timer for %s seconds", self.active_room_threshold)
                self.start_timer("active_room")

            self.presence_detected = True
            self.update_active_room_status()
            self._dispatch_update()
        except Exception as e:
            _LOGGER.error("Error in handle_presence_detected: %s", e)

    async def handle_presence_clear(self) -> None:
        """
        Handle presence clearing.
        This method is called when presence is no longer detected in the room.
        It starts the presence timer to turn off entities after a delay.
        """
        try:
            _LOGGER.debug("Presence cleared")
            self.cancel_timer("active_room")
            base_timeout = self.active_room_timeout if self.is_active_room else self.presence_timeout
            timeout = self.get_adjusted_timeout(base_timeout)
            _LOGGER.debug("Starting presence timer for %s seconds", timeout)
            self.start_timer("presence")
            self.presence_start_time = None
            self.last_presence_end_time = dt_util.utcnow()
            self.presence_detected = False
            self.update_active_room_status()
            self._dispatch_update()
        except Exception as e:
            _LOGGER.error("Error in handle_presence_clear: %s", e)

    # Timer methods
    def get_adjusted_timeout(self, base_timeout: float) -> float:
        """
        Get the timeout adjusted for night mode if active.
        During night mode, timeouts are scaled down to reduce the delay in turning off entities.
        """
        if self.is_night_mode_active():
            return base_timeout * self.night_mode_scale
        return base_timeout

    def start_timer(self, timer_name: str) -> None:
        """
        Start a timer.
        This method starts either the presence timer or the active room timer.
        """
        self.cancel_timer(timer_name)
        if timer_name == "presence":
            timeout = self.get_adjusted_timeout(self.presence_timeout)
        elif timer_name == "active_room":
            timeout = self.get_adjusted_timeout(self.active_room_threshold)
        else:
            _LOGGER.error(f"Unknown timer: {timer_name}")
            return

        next_update = dt_util.utcnow() + timedelta(seconds=timeout)
        self._timers[timer_name] = async_track_point_in_time(
            self.hass, self.timer_expired, next_update
        )
        _LOGGER.debug(f"Started {timer_name} timer for {timeout} seconds")

    def cancel_timer(self, timer_name: str) -> None:
        """Cancel a timer."""
        if timer_name in self._timers:
            self._timers[timer_name]()
            del self._timers[timer_name]

    async def timer_expired(self, _now: dt_util.dt.datetime) -> None:
        """
        Handle timer expiration.
        This method is called when either the presence timer or active room timer expires.
        """
        if "presence" in self._timers:
            await self.turn_off_controlled_entities()
            self.presence_detected = False
            self.is_active_room = False
        elif "active_room" in self._timers:
            self.is_active_room = True
        
        self._dispatch_update()

    # Entity control methods
    async def turn_on_controlled_entities(self):
        """
        Turn on controlled entities based on current mode.
        This method turns on the appropriate entities when presence is detected.
        """
        entities_to_turn_on = self.get_active_entities()
        for entity_id in entities_to_turn_on:
            domain = entity_id.split('.')[0]
            service = 'turn_on'
            service_data = {"entity_id": entity_id}           

            _LOGGER.info(f"Turning on {entity_id} with data: {service_data}")
            await self.hass.services.async_call(domain, service, service_data)

    async def turn_off_controlled_entities(self):
        """
        Turn off all controlled entities.
        This method turns off all entities when presence is no longer detected.
        """
        all_entities = list(set(self.controlled_entities + self.night_mode_controlled_entities))
        for entity_id in all_entities:
            domain = entity_id.split('.')[0]
            service = 'turn_off'
            _LOGGER.info(f"Turning off {entity_id}")
            await self.hass.services.async_call(domain, service, {"entity_id": entity_id})

    def get_active_entities(self):
        """
        Get the list of entities to control based on current mode.
        This method returns different sets of entities depending on whether night mode is active.
        """
        if self.is_night_mode_active():
            if self.night_mode_entities_behavior == "exclusive":
                return self.night_mode_controlled_entities
            else:  # additive
                return list(set(self.controlled_entities + self.night_mode_controlled_entities))
        else:
            return self.controlled_entities

    # Status update methods
    def update_active_room_status(self):
        """
        Update the active room status based on presence duration.
        A room becomes 'active' if presence is continuously detected for a certain duration.
        """
        if self.presence_detected and self.presence_start_time:
            presence_duration = (dt_util.utcnow() - self.presence_start_time).total_seconds()
            self.is_active_room = presence_duration >= self.active_room_threshold
        else:
            self.is_active_room = False

    def calculate_presence_duration(self):
        """Calculate the current presence duration."""
        if self.presence_detected and self.presence_start_time:
            return (dt_util.utcnow() - self.presence_start_time).total_seconds()
        return 0

    def calculate_absence_duration(self):
        """Calculate the current absence duration."""
        if not self.presence_detected and self.last_presence_end_time:
            return (dt_util.utcnow() - self.last_presence_end_time).total_seconds()
        return 0

    # Night mode methods
    def is_night_mode_active(self) -> bool:
        """
        Check if night mode is currently active.
        Night mode is active if it's enabled and the current time is within the night mode hours.
        """
        if not self.night_mode_enable:
            return False

        current_time = dt_util.now().time()
        start_time = dt_util.parse_time(self.night_mode_start)
        end_time = dt_util.parse_time(self.night_mode_end)

        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:  # Night mode spans midnight
            return current_time >= start_time or current_time <= end_time

    async def enable_night_mode(self):
        """Enable Night Mode."""
        self.night_mode_enable = True
        await self.async_update_config({CONF_NIGHT_MODE_ENABLE: True})
        self._dispatch_update()

    async def disable_night_mode(self):
        """Disable Night Mode."""
        self.night_mode_enable = False
        await self.async_update_config({CONF_NIGHT_MODE_ENABLE: False})
        self._dispatch_update()

    # Controller enable/disable methods
    async def enable(self):
        """Enable the Dynamic Presence Controller."""
        self._enabled = True
        await self.async_setup()
        self._dispatch_update()

    async def disable(self):
        """Disable the Dynamic Presence Controller."""
        self._enabled = False
        await self.async_unload()
        await self.turn_off_controlled_entities()
        self._dispatch_update()

    # Update methods
    def _dispatch_update(self) -> None:
        """Dispatch update to all entities."""
        async_dispatcher_send(self.hass, f"{DOMAIN}_{self.config_entry.entry_id}_update")

    async def _async_update_data(self) -> dict[str, Any]:
        """
        Fetch new state data for the sensor.
        This method is called regularly to update the state of the integration.
        """
        self.update_active_room_status()
        return {
            "presence_detected": self.presence_detected,
            "is_active_room": self.is_active_room,
            "presence_duration": self.calculate_presence_duration(),
            "absence_duration": self.calculate_absence_duration(),
            "presence_timeout": self.presence_timeout,
            "active_room_threshold": self.active_room_threshold,
            "active_room_timeout": self.active_room_timeout,
            "night_mode_timeout": self.night_mode_timeout,
            "night_mode_start": self.night_mode_start,
            "night_mode_end": self.night_mode_end,
            "night_mode_enable": self.night_mode_enable,
            "night_mode_scale": self.night_mode_scale,
            "is_night_mode_active": self.is_night_mode_active(),
            "controlled_entities": self.controlled_entities,
            "night_mode_controlled_entities": self.night_mode_controlled_entities,
            "night_mode_entities_behavior": self.night_mode_entities_behavior,
        }

    async def async_update_config(self, new_data: dict[str, Any]) -> None:
        """
        Update the controller configuration.
        This method is called when the user updates the integration's configuration.
        """
        try:
            validated_data = self._validate_config(new_data)
            self.config_entry.options = {**self.config_entry.options, **validated_data}
            self._load_config_values()
            self.hass.config_entries.async_update_entry(self.config_entry, options=self.config_entry.options)
            self._dispatch_update()
            await self.async_request_refresh()
            _LOGGER.info("Successfully updated Dynamic Presence configuration")
        except Exception as e:
            _LOGGER.error("Error updating Dynamic Presence configuration: %s", e)

    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration values.
        This method checks if the provided configuration values are valid and within expected ranges.
        If a value is invalid, it's replaced with the default value and a warning is logged.
        """
        validated = {}
        
        # Validate presence_timeout
        presence_timeout = config.get(CONF_PRESENCE_TIMEOUT)
        if presence_timeout is not None:
            if not isinstance(presence_timeout, (int, float)) or presence_timeout <= 0:
                _LOGGER.warning(f"Invalid presence_timeout: {presence_timeout}. Using default.")
                validated[CONF_PRESENCE_TIMEOUT] = NUMBER_CONFIG[CONF_PRESENCE_TIMEOUT]["default"]
            else:
                validated[CONF_PRESENCE_TIMEOUT] = presence_timeout
        
        # Validate active_room_threshold
        active_room_threshold = config.get(CONF_ACTIVE_ROOM_THRESHOLD)
        if active_room_threshold is not None:
            if not isinstance(active_room_threshold, (int, float)) or active_room_threshold <= 0:
                _LOGGER.warning(f"Invalid active_room_threshold: {active_room_threshold}. Using default.")
                validated[CONF_ACTIVE_ROOM_THRESHOLD] = NUMBER_CONFIG[CONF_ACTIVE_ROOM_THRESHOLD]["default"]
            else:
                validated[CONF_ACTIVE_ROOM_THRESHOLD] = active_room_threshold
        
        # Add similar validations for other configuration values...
        
        # Validate night_mode_scale
        night_mode_scale = config.get(CONF_NIGHT_MODE_SCALE)
        if night_mode_scale is not None:
            if not isinstance(night_mode_scale, (int, float)) or night_mode_scale <= 0 or night_mode_scale > 1:
                _LOGGER.warning(f"Invalid night_mode_scale: {night_mode_scale}. Using default.")
                validated[CONF_NIGHT_MODE_SCALE] = NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["default"]
            else:
                validated[CONF_NIGHT_MODE_SCALE] = night_mode_scale
        
        return validated
