"""Coordinator for Dynamic Presence integration."""

from datetime import timedelta
import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers.template import TemplateError
from homeassistant.util import dt as dt_util

from homeassistant.const import STATE_ON

from .light_control import LightController
from .presence_control import PresenceControl, RoomState
from .storage_collection import DynamicPresenceStorage
from .const import (
    DEFAULT_BINARY_SENSOR_OCCUPANCY,
    DOMAIN,
    CONF_PRESENCE_SENSOR,
    CONF_LIGHTS,
    CONF_NIGHT_LIGHTS,
    CONF_LIGHT_SENSOR,
    DEFAULT_NIGHT_MODE_START,
    DEFAULT_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_END,
    CONF_DETECTION_TIMEOUT,
    DEFAULT_DETECTION_TIMEOUT,
    CONF_LONG_TIMEOUT,
    DEFAULT_LONG_TIMEOUT,
    CONF_SHORT_TIMEOUT,
    DEFAULT_SHORT_TIMEOUT,
    CONF_LIGHT_THRESHOLD,
    DEFAULT_LIGHT_THRESHOLD,
    DEFAULT_SENSOR_OCCUPANCY_DURATION,
    DEFAULT_SENSOR_ABSENCE_DURATION,
    DEFAULT_SENSOR_LIGHT_LEVEL,
    DEFAULT_SWITCH_AUTOMATION,
    DEFAULT_SWITCH_AUTO_ON,
    DEFAULT_SWITCH_AUTO_OFF,
    DEFAULT_SWITCH_NIGHT_MODE,
    DEFAULT_SWITCH_NIGHT_MANUAL_ON,
    SENSOR_MAIN_MANUAL_STATES,
    SENSOR_NIGHT_MANUAL_STATES,
    DEFAULT_SENSOR_MAIN_MANUAL_STATES,
    DEFAULT_SENSOR_NIGHT_MANUAL_STATES,
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

    # 1. Core Initialization
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        # 1. Parent initialization
        super().__init__(
            hass,
            logger=logCoordinator,
            name=DOMAIN,
            update_interval=timedelta(seconds=1),
        )

        # 2. Core attributes
        self.hass = hass
        self.entry = entry
        self.room_name = entry.title
        self._store = DynamicPresenceStorage(hass, entry.entry_id)

        # 3. State containers initialization
        self._manual_states = {"main": {}, "night": {}}
        self.data = self._get_default_data()

        # 4. Configuration attributes
        self._init_config_attributes()
        self.update_from_options(entry)
        self._is_configured = bool(self._presence_sensor and self._lights)

        # 5. Controllers initialization
        self._presence_control = PresenceControl(self)
        self.light_controller = LightController(hass)

        # 6. Device info
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Dynamic Presence {self.room_name}",
            manufacturer="Home Assistant",
            model="Dynamic Presence Controller",
        )

        # Initialize coordinator
        hass.async_create_task(self.async_initialize())

    def _init_config_attributes(self) -> None:
        """Initialize configuration attributes with defaults."""
        self._presence_sensor = None
        self._lights = []
        self._night_lights = []
        self._light_sensor = None
        self._night_mode_start = DEFAULT_NIGHT_MODE_START
        self._night_mode_end = DEFAULT_NIGHT_MODE_END
        self._detection_timeout = DEFAULT_DETECTION_TIMEOUT
        self._long_timeout = DEFAULT_LONG_TIMEOUT
        self._short_timeout = DEFAULT_SHORT_TIMEOUT
        self._light_threshold = DEFAULT_LIGHT_THRESHOLD

    def _get_default_data(self) -> dict[str, Any]:
        """Get default runtime data."""
        return {
            "binary_sensor_occupancy": DEFAULT_BINARY_SENSOR_OCCUPANCY,
            "sensor_occupancy_duration": DEFAULT_SENSOR_OCCUPANCY_DURATION,
            "sensor_absence_duration": DEFAULT_SENSOR_ABSENCE_DURATION,
            "sensor_light_level": DEFAULT_SENSOR_LIGHT_LEVEL,
            "switch_automation": DEFAULT_SWITCH_AUTOMATION,
            "switch_auto_on": DEFAULT_SWITCH_AUTO_ON,
            "switch_auto_off": DEFAULT_SWITCH_AUTO_OFF,
            "switch_night_mode": DEFAULT_SWITCH_NIGHT_MODE,
            "switch_night_manual_on": DEFAULT_SWITCH_NIGHT_MANUAL_ON,
            SENSOR_MAIN_MANUAL_STATES: DEFAULT_SENSOR_MAIN_MANUAL_STATES,
            SENSOR_NIGHT_MANUAL_STATES: DEFAULT_SENSOR_NIGHT_MANUAL_STATES,
        }

    # Properties for cached attributes
    @property
    def presence_sensor(self) -> str | None:
        """Get the presence sensor entity ID."""
        return self._presence_sensor

    @property
    def lights(self) -> list[str]:
        """Get the list of main lights."""
        return self._lights

    @property
    def night_lights(self) -> list[str]:
        """Get the list of night lights."""
        return self._night_lights

    @property
    def light_sensor(self) -> str | None:
        """Get the light sensor entity ID."""
        return self._light_sensor

    @property
    def night_mode_start(self) -> str:
        """Get night mode start time."""
        return self._night_mode_start

    @property
    def night_mode_end(self) -> str:
        """Get night mode end time."""
        return self._night_mode_end

    @property
    def detection_timeout(self) -> int:
        """Get detection timeout value."""
        return self._detection_timeout

    @property
    def long_timeout(self) -> int:
        """Get long timeout value."""
        return self._long_timeout

    @property
    def short_timeout(self) -> int:
        """Get short timeout value."""
        return self._short_timeout

    @property
    def light_threshold(self) -> int:
        """Get light threshold value."""
        return self._light_threshold

    @property
    def has_night_mode(self) -> bool:
        """Check if night mode is configured."""
        return bool(self._night_lights)

    @property
    def has_light_sensor(self) -> bool:
        """Check if light sensor is configured."""
        return bool(self._light_sensor)

    @property
    def presence_control(self) -> "PresenceControl":
        """Return the presence control instance."""
        return self._presence_control

    async def async_initialize(self) -> None:
        """Initialize the coordinator."""
        stored_manual_states = await self._store.async_load()

        # First load stored states if available
        if stored_manual_states and isinstance(stored_manual_states, dict):
            self._manual_states = stored_manual_states
        else:
            self._manual_states = {}

        # Ensure main states exist and initialize new lights
        if "main" not in self._manual_states:
            self._manual_states["main"] = {}

        # Initialize any new main lights to their stored state or True
        for light in self.lights:
            if light not in self._manual_states["main"]:
                self._manual_states["main"][light] = True
                logCoordinator.debug("Initializing new main light %s", light)

        # Handle night mode states if enabled
        if self.has_night_mode:
            if "night" not in self._manual_states:
                self._manual_states["night"] = {}

            # Initialize any new night lights to their stored state or True
            for light in self.night_lights:
                if light not in self._manual_states["night"]:
                    self._manual_states["night"][light] = True
                    logCoordinator.debug("Initializing new night light %s", light)

        # Clean up removed lights
        for light in list(self._manual_states["main"].keys()):
            if light not in self.lights:
                self._manual_states["main"].pop(light)
                logCoordinator.debug("Removed main light %s", light)

        if "night" in self._manual_states:
            for light in list(self._manual_states["night"].keys()):
                if light not in self.night_lights:
                    self._manual_states["night"].pop(light)
                    logCoordinator.debug("Removed night light %s", light)

        # Save the updated states
        await self._store.async_save()
        self._async_setup_listeners()

        # Initialize presence state based on current sensor state
        await self._init_presence_state()

    async def _init_presence_state(self) -> None:
        """Initialize presence state based on current sensor state."""
        if self.presence_sensor:
            presence_state = self.hass.states.get(self.presence_sensor)
            if presence_state:
                logCoordinator.debug(
                    "Initializing presence state from sensor: %s", presence_state.state
                )
                await self._presence_control.initialize_from_state(presence_state.state)

    async def async_config_entry_first_refresh(self) -> None:
        """Initialize the coordinator."""
        # Load storage once
        await self._store.async_load()

        # Initialize states from storage
        stored_manual_states = self._store.data.manual_states
        if stored_manual_states:
            if "main" in stored_manual_states and "night" in stored_manual_states:
                self._manual_states = stored_manual_states
            else:
                # Convert old format
                self._manual_states = {
                    "main": stored_manual_states,
                    "night": {light: True for light in self.night_lights},
                }
        else:
            # Initialize new room with all lights ON in both modes
            self._manual_states = {
                "main": {light: True for light in self.lights},
                "night": {light: True for light in self.night_lights},
            }

        # Load switch states
        stored_states = self._store.data.states
        switch_keys = [
            "automation",
            "auto_on",
            "auto_off",
            "night_mode",
            "night_manual_on",
        ]
        for key in switch_keys:
            stored_key = f"switch_{key}"
            if stored_key in stored_states:
                self.data[stored_key] = stored_states[stored_key]

        # Set up listeners and initialize presence state
        self._async_setup_listeners()
        await self._init_presence_state()

        await self._store.async_save()
        await self._async_update_data()

    @callback
    def _async_setup_listeners(self) -> None:
        """Set up state change event listeners."""
        if not self._is_configured:
            return

        self.entry.async_on_unload(
            async_track_state_change_event(
                self.hass,
                [self.presence_sensor],
                self._presence_control.handle_presence_event,
            )
        )

        active_lights = self.lights + self.night_lights
        for light in active_lights:
            self.entry.async_on_unload(
                async_track_state_change_event(
                    self.hass,
                    [light],
                    self._async_light_changed,
                )
            )

    # 2. Properties and State Access
    @property
    def active_lights(self) -> list:
        """Get the currently active light set based on mode."""
        # First check if night mode is configured
        if not self.has_night_mode:
            return self.lights

        # If night mode is configured, check if it's currently active
        # (requires both night mode switch ON and within night time hours)
        return (
            self.night_lights
            if self.data.get("binary_sensor_night_mode", False)
            else self.lights
        )

    @property
    def manual_states(self) -> dict:
        """Get the current manual states of lights."""
        if not self._manual_states:
            self._manual_states = {
                "main": {},
                "night": {},
            }
        return self._manual_states

    @property
    def switch_state(self, switch_id: str) -> bool:
        """Get switch state.

        Args:
            switch_id: The switch identifier to check

        Returns:
            bool: True if switch is on, False otherwise
        """
        switch_entity = self.entry.options.get(switch_id)
        if not switch_entity:
            return False
        state = self.hass.states.get(switch_entity)
        return state is not None and state.state == "on"

    # 3. Manual State Management
    async def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        if self._presence_control.state == RoomState.OCCUPIED:
            try:
                entity_id = event.data.get("entity_id")
                new_state = event.data.get("new_state")
                if new_state is not None:
                    is_on = new_state.state == STATE_ON

                    # First determine which mode we're in
                    mode = "main"
                    if (
                        self.has_night_mode
                        and self._presence_control.is_night_mode_active()
                    ):
                        mode = "night"

                    # Update the appropriate manual state based on current mode
                    if mode == "night" and entity_id in self.night_lights:
                        self._manual_states["night"][entity_id] = is_on
                    elif mode == "main" and entity_id in self.lights:
                        self._manual_states["main"][entity_id] = is_on

                    await self._store.async_save()
                    await self.async_refresh()
            except (HomeAssistantError, ServiceNotFound, TemplateError) as err:
                logCoordinator.error(
                    "Error handling light change for %s: %s",
                    entity_id,
                    err,
                    exc_info=True,
                )

    async def _apply_light_states(self) -> None:
        """Apply stored light states or turn on lights."""
        active_lights = self.active_lights
        if not active_lights:
            return
        await self.light_controller.turn_on_lights(active_lights)

    # 4. Light Control
    async def _turn_off_lights(self) -> None:
        """Turn off all active lights."""
        active_lights = self.active_lights
        if not active_lights:
            return
        await self.light_controller.turn_off_lights(active_lights)

    # 5. Configuration and Options
    @callback
    def update_from_options(self, entry: ConfigEntry | dict) -> None:
        """Update configuration from options.

        Args:
            entry: Either a ConfigEntry object or a dict of options
        """
        # Get options dict, handling both ConfigEntry and direct dict input
        options = entry.options if isinstance(entry, ConfigEntry) else entry

        # Core configuration
        self._presence_sensor = options.get(CONF_PRESENCE_SENSOR)
        self._lights = options.get(CONF_LIGHTS, [])

        # Night mode configuration
        self._night_lights = options.get(CONF_NIGHT_LIGHTS, [])
        if self.has_night_mode:
            self._night_mode_start = options.get(
                CONF_NIGHT_MODE_START, DEFAULT_NIGHT_MODE_START
            )
            self._night_mode_end = options.get(
                CONF_NIGHT_MODE_END, DEFAULT_NIGHT_MODE_END
            )
            # Initialize night mode manual states if needed
            if "night" not in self._manual_states:
                self._manual_states["night"] = {
                    light: True for light in self._night_lights
                }

        # Light sensor configuration
        self._light_sensor = options.get(CONF_LIGHT_SENSOR)
        if self.has_light_sensor:
            self._light_threshold = options.get(
                CONF_LIGHT_THRESHOLD, DEFAULT_LIGHT_THRESHOLD
            )

        # General timeouts (always needed)
        self._detection_timeout = options.get(
            CONF_DETECTION_TIMEOUT, DEFAULT_DETECTION_TIMEOUT
        )
        self._long_timeout = options.get(CONF_LONG_TIMEOUT, DEFAULT_LONG_TIMEOUT)
        self._short_timeout = options.get(CONF_SHORT_TIMEOUT, DEFAULT_SHORT_TIMEOUT)

        self._is_configured = bool(self._presence_sensor and self._lights)

        logCoordinator.debug(
            "Updated options for %s: presence=%s, lights=%d, night_lights=%d",
            self.room_name,
            self._presence_sensor,
            len(self._lights),
            len(self._night_lights),
        )

    async def async_save_options(self) -> None:
        """Save manual states to config entry - called during shutdown."""
        if hasattr(self, "_manual_states") and self._manual_states:
            new_data = dict(self.entry.data) if self.entry.data else {}
            new_data.update(self._manual_states)

            self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    # 6. Event Handlers
    async def async_entity_changed(
        self, entity_type: str, key: str, value: Any
    ) -> None:
        """Handle runtime control state changes."""
        try:
            # Update runtime data
            data_key = f"{entity_type}_{key}"
            self.data[data_key] = value
            self.async_set_updated_data(self.data)

            # Handle night mode changes
            if data_key == "switch_night_mode":
                await self._handle_mode_changed(value)

            # Save to storage
            if entity_type == "switch":
                self._store.set_state(data_key, value)
                await self._store.async_save()

            # Update timers if needed
            if entity_type == "number":
                await self._presence_control.update_timers(entity_type, key)

        except (HomeAssistantError, ServiceNotFound, TemplateError) as err:
            logCoordinator.error(
                "Error updating %s.%s to %s: %s",
                entity_type,
                key,
                value,
                err,
                exc_info=True,
            )

    async def async_handle_state_changed(self, new_state: RoomState) -> None:
        """Public method to handle state changes."""
        await self._handle_state_changed(new_state)

    async def _handle_state_changed(self, new_state: RoomState) -> None:
        """Handle room state changes."""
        if new_state == RoomState.OCCUPIED:
            # First check light level if sensor configured
            if self.has_light_sensor:
                current_light_level = self.data.get("sensor_light_level", 0)
                if current_light_level >= self.light_threshold:
                    logCoordinator.debug(
                        "Light level %s above threshold %s - skipping light activation",
                        current_light_level,
                        self.light_threshold,
                    )
                    return
            auto_on = self.data.get("switch_auto_on", False)
            night_manual_on = False
            is_night_mode = False

            if self.has_night_mode:
                night_manual_on = self.data.get("switch_night_manual_on", False)
                is_night_mode = self._presence_control.is_night_mode_active()

            # Don't turn on lights if Night Manual-On is enabled during night mode
            if not auto_on or (is_night_mode and night_manual_on):
                logCoordinator.debug(
                    "Skipping light activation: auto_on=%s, night_mode=%s, night_manual_on=%s",
                    auto_on,
                    is_night_mode,
                    night_manual_on,
                )
                return

            mode = "night" if is_night_mode else "main"
            lights_to_control = self.night_lights if mode == "night" else self.lights

            # Special case: If ALL manual states are OFF, reset them to ON
            all_lights_off = all(
                not self._manual_states[mode].get(light, True)
                for light in lights_to_control
            )

            if all_lights_off:
                logCoordinator.debug("All manual states were OFF - resetting to ON")
                # Reset all manual states to ON
                for light in lights_to_control:
                    self._manual_states[mode][light] = True
                await self._store.async_save()
                # Turn on all lights
                await self.light_controller.turn_on_lights(lights_to_control)
            else:
                # Normal case: Restore previous manual states
                logCoordinator.debug("Restoring previous manual states")
                for light in lights_to_control:
                    if self._manual_states[mode].get(light, True):
                        await self.hass.services.async_call(
                            "light",
                            "turn_on",
                            {"entity_id": light},
                            blocking=True,
                        )

        elif new_state == RoomState.VACANT:
            # Check if we should turn off lights based on Auto-Off
            auto_off = self.data.get("switch_auto_off", False)
            if not auto_off:
                logCoordinator.debug("Auto-off disabled - keeping current light states")
                return

            mode = "night" if self._presence_control.is_night_mode_active() else "main"
            lights_to_control = self.night_lights if mode == "night" else self.lights

            # Turn off all lights from both sets
            all_lights = set(self.lights + self.night_lights)
            for light in all_lights:
                try:
                    await self.hass.services.async_call(
                        "light",
                        "turn_off",
                        {"entity_id": light},
                        blocking=True,
                    )
                except ServiceNotFound as err:
                    logCoordinator.error("Failed to turn off %s: %s", light, err)

        await self.async_refresh()

    async def _handle_mode_changed(self, is_night_mode: bool) -> None:
        """Handle transition between normal and night mode."""
        if (
            not self.has_night_mode
            or self._presence_control.state != RoomState.OCCUPIED
        ):
            return

        if self._presence_control.state == RoomState.OCCUPIED:
            # Get the new set of lights to control
            lights_to_control = self.night_lights if is_night_mode else self.lights
            mode = "night" if is_night_mode else "main"

            # Turn off lights that aren't in the new mode's set
            all_lights = set(self.lights + self.night_lights)
            for light in all_lights:
                if light not in lights_to_control:
                    try:
                        await self.hass.services.async_call(
                            "light",
                            "turn_off",
                            {"entity_id": light},
                            blocking=True,
                        )
                    except ServiceNotFound as err:
                        logCoordinator.error("Failed to turn off %s: %s", light, err)

            # Turn on lights according to their manual states in the new mode
            for light in lights_to_control:
                if self._manual_states[mode].get(light, True):
                    try:
                        await self.hass.services.async_call(
                            "light",
                            "turn_on",
                            {"entity_id": light},
                            blocking=True,
                        )
                    except ServiceNotFound as err:
                        logCoordinator.error("Failed to turn on %s: %s", light, err)

        await self.async_refresh()

    # 7. Data Updates
    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data."""
        if not hasattr(self, "_presence_control"):
            return self.data

        updated_data = self.data.copy()

        # Update state-based sensors
        current_state = self._presence_control.state
        updated_data["binary_sensor_occupancy"] = current_state in [
            RoomState.OCCUPIED,
            RoomState.DETECTION_TIMEOUT,
        ]

        # Update durations
        updated_data.update(self._presence_control.durations)

        # Update light sensor if configured
        if self.light_sensor:
            try:
                state = self.hass.states.get(self.light_sensor)
                if state and state.state not in ("unknown", "unavailable"):
                    updated_data["sensor_light_level"] = float(state.state)
            except (ValueError, TypeError) as err:
                logCoordinator.warning(
                    "Error reading light sensor %s: %s",
                    self.light_sensor,
                    err,
                )

        # Update night mode status - requires BOTH switch ON and within time window
        switch_on = bool(self.data.get("switch_night_mode", False))
        is_night_time = self.is_night_time()
        updated_data["binary_sensor_night_mode"] = switch_on and is_night_time

        return updated_data

    # 8. Night Mode Management
    def is_night_mode_active(self) -> bool:
        """Check if night mode is active for light control."""
        return bool(self.data.get("binary_sensor_night_mode", False))

    def is_night_time(self) -> bool:
        """Check if current time is within night time hours."""
        if not self.night_mode_start or not self.night_mode_end:
            logCoordinator.debug(
                "Night time check - No times configured: start=%s, end=%s",
                self.night_mode_start,
                self.night_mode_end,
            )
            return False

        current_time = dt_util.now().time()
        start_time = dt_util.parse_time(self.night_mode_start)
        end_time = dt_util.parse_time(self.night_mode_end)

        # For overnight periods (e.g., 20:00 to 08:00)
        if start_time > end_time:
            # Is night if time is after start OR before end
            is_night = current_time >= start_time or current_time <= end_time
        else:
            # For same-day periods (e.g., 08:00 to 20:00)
            is_night = start_time <= current_time <= end_time

        return is_night

    def _check_night_mode_switch(self) -> bool:
        """Check if night mode is forced by switch."""
        switch_state = bool(self.data.get("switch_night_mode", False))
        logCoordinator.debug("Night mode switch state: %s", switch_state)
        return switch_state

    async def handle_mode_change(self) -> None:
        """Handle transition between normal and night mode."""
        is_night_mode = self.is_night_mode_active()
        lights_to_control = self.night_lights if is_night_mode else self.lights

        if self._presence_control.state == RoomState.OCCUPIED:
            await self.light_controller.update_active_lights(
                is_night_mode,
                lights_to_control,
                self._manual_states,
                self.has_night_mode,
            )

        await self.async_refresh()
