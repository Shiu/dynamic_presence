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
        super().__init__(
            hass,
            logger=logCoordinator,
            name=DOMAIN,
            update_interval=timedelta(seconds=1),
        )

        self.hass = hass
        self.entry = entry
        self.room_name = entry.title

        # Initialize storage for runtime data
        self._store = DynamicPresenceStorage(hass, entry.entry_id)

        # Initialize manual states with empty dictionaries
        self._manual_states = {
            "main": {},
            "night": {},
        }

        # Configuration values from options
        self.presence_sensor = entry.options.get(CONF_PRESENCE_SENSOR)
        self.lights = entry.options.get(CONF_LIGHTS, [])
        self.night_lights = entry.options.get(CONF_NIGHT_LIGHTS, [])
        self.light_sensor = entry.options.get(CONF_LIGHT_SENSOR)

        # Initialize time settings with defaults
        self.night_mode_start = entry.options.get(
            CONF_NIGHT_MODE_START, DEFAULT_NIGHT_MODE_START
        )
        self.night_mode_end = entry.options.get(
            CONF_NIGHT_MODE_END, DEFAULT_NIGHT_MODE_END
        )

        # Initialize number settings with defaults
        self.detection_timeout = entry.options.get(
            CONF_DETECTION_TIMEOUT, DEFAULT_DETECTION_TIMEOUT
        )
        self.long_timeout = entry.options.get(CONF_LONG_TIMEOUT, DEFAULT_LONG_TIMEOUT)
        self.short_timeout = entry.options.get(
            CONF_SHORT_TIMEOUT, DEFAULT_SHORT_TIMEOUT
        )
        self.light_threshold = entry.options.get(
            CONF_LIGHT_THRESHOLD, DEFAULT_LIGHT_THRESHOLD
        )

        self._is_configured = bool(self.presence_sensor and self.lights)

        # State tracking
        self._presence_control = PresenceControl(self)

        # Device info
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Dynamic Presence {self.room_name}",
            manufacturer="Home Assistant",
            model="Dynamic Presence Controller",
        )

        # Runtime data initialization - only switches and sensors
        self.data = {
            # Binary sensors
            "binary_sensor_occupancy": DEFAULT_BINARY_SENSOR_OCCUPANCY,
            # Sensors
            "sensor_occupancy_duration": DEFAULT_SENSOR_OCCUPANCY_DURATION,
            "sensor_absence_duration": DEFAULT_SENSOR_ABSENCE_DURATION,
            "sensor_light_level": DEFAULT_SENSOR_LIGHT_LEVEL,
            # Runtime controls (switches only)
            "switch_automation": DEFAULT_SWITCH_AUTOMATION,
            "switch_auto_on": DEFAULT_SWITCH_AUTO_ON,
            "switch_auto_off": DEFAULT_SWITCH_AUTO_OFF,
            "switch_night_mode": DEFAULT_SWITCH_NIGHT_MODE,
            "switch_night_manual_on": DEFAULT_SWITCH_NIGHT_MANUAL_ON,
            SENSOR_MAIN_MANUAL_STATES: DEFAULT_SENSOR_MAIN_MANUAL_STATES,
            SENSOR_NIGHT_MANUAL_STATES: DEFAULT_SENSOR_NIGHT_MANUAL_STATES,
        }

        # Initialize coordinator
        hass.async_create_task(self.async_initialize())

    async def async_initialize(self) -> None:
        """Initialize the coordinator."""
        # Load stored manual states
        stored_data = await self._store.async_load()
        if stored_data:
            # Convert old format to new if needed
            if isinstance(stored_data, dict) and not (
                "main" in stored_data and "night" in stored_data
            ):
                self._manual_states = {
                    "main": stored_data,
                    "night": {light: True for light in self.night_lights},
                }
            else:
                self._manual_states = stored_data
        else:
            # Initialize new room with all lights ON in both modes
            self._manual_states = {
                "main": {light: True for light in self.lights},
                "night": {light: True for light in self.night_lights},
            }
            logCoordinator.debug("New room: Initializing all light states to ON")

        # For existing rooms, initialize any new lights
        for light in self.lights:
            if light not in self._manual_states["main"]:
                self._manual_states["main"][light] = True
                logCoordinator.debug("Initializing new main light %s to ON", light)

        for light in self.night_lights:
            if light not in self._manual_states["night"]:
                self._manual_states["night"][light] = True
                logCoordinator.debug("Initializing new night light %s to ON", light)

        # Clean up removed lights
        for light in list(self._manual_states["main"]):
            if light not in self.lights:
                self._manual_states["main"].pop(light)
                logCoordinator.debug(
                    "Removing manual state for deleted main light %s", light
                )

        for light in list(self._manual_states["night"]):
            if light not in self.night_lights:
                self._manual_states["night"].pop(light)
                logCoordinator.debug(
                    "Removing manual state for deleted night light %s", light
                )

        await self._store.async_save()

        # Set up listeners
        self._async_setup_listeners()

        # Initialize presence state based on current sensor state
        presence_entity = self.entry.options.get(CONF_PRESENCE_SENSOR)
        if presence_entity:
            presence_state = self.hass.states.get(presence_entity)
            if presence_state:
                logCoordinator.debug(
                    "Initializing presence state from sensor: %s", presence_state.state
                )
                if presence_state.state == "on":
                    await self._presence_control.handle_presence_detected()
                else:
                    await self._presence_control.handle_presence_lost()

    async def async_config_entry_first_refresh(self) -> None:
        """Initialize the coordinator."""
        # Load runtime states from storage
        stored_data = await self._store.async_load()

        # Initialize manual states
        if stored_data and "manual_states" in stored_data:
            if isinstance(stored_data["manual_states"], dict):
                if (
                    "main" in stored_data["manual_states"]
                    and "night" in stored_data["manual_states"]
                ):
                    self._manual_states = stored_data["manual_states"]
                else:
                    # Convert old format
                    self._manual_states = {
                        "main": stored_data["manual_states"],
                        "night": {light: True for light in self.night_lights},
                    }
        else:
            # Initialize new room with all lights ON in both modes
            self._manual_states = {
                "main": {light: True for light in self.lights},
                "night": {light: True for light in self.night_lights},
            }
            logCoordinator.debug("New room: Initializing all light states to ON")

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
    def active_lights(self) -> list[str]:
        """Get the currently active light entities based on mode."""
        if self._presence_control.is_night_mode_active():
            lights = self.entry.options.get(CONF_NIGHT_LIGHTS, [])
            logCoordinator.debug("Night mode active, using night lights: %s", lights)
            return lights
        lights = self.entry.options.get(CONF_LIGHTS, [])
        logCoordinator.debug("Normal mode active, using main lights: %s", lights)
        return lights

    @callback
    def _get_active_lights(self) -> list:
        """Get the currently active set of lights based on night mode state."""
        return self.night_lights if self.is_night_mode() else self.lights

    @property
    def manual_states(self) -> dict:
        """Get the current manual states of lights."""
        # Initialize if not exists
        if not self._manual_states:
            self._manual_states = {
                "main": {},
                "night": {},
            }

        # Return a copy to prevent direct modification
        return {
            "main": dict(self._manual_states.get("main", {})),
            "night": dict(self._manual_states.get("night", {})),
        }

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

    def check_night_mode_active(self) -> bool:
        """Check if night mode should be active based on all conditions."""
        # First check if night mode switch is enabled
        if not self.data["switch_night_mode"]:
            return False

        # Then check time conditions
        current_time = dt_util.now().time()
        start_time = dt_util.parse_time(self.night_mode_start)
        end_time = dt_util.parse_time(self.night_mode_end)

        if not start_time or not end_time:
            return False

        # Handle overnight periods (when end time is less than start time)
        if end_time < start_time:
            return current_time >= start_time or current_time <= end_time

        # Normal period within same day
        return start_time <= current_time <= end_time

    def _is_night_mode(self) -> bool:
        """Check if night mode is active."""
        return self.check_night_mode_active()

    def is_night_mode(self) -> bool:
        """Public method to check if night mode is active."""
        return self._is_night_mode()

    # 3. Manual State Management
    async def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        if self._presence_control.state == RoomState.OCCUPIED:
            try:
                entity_id = event.data.get("entity_id")
                new_state = event.data.get("new_state")
                if new_state is not None:
                    is_on = new_state.state == STATE_ON
                    # Store state in the appropriate dictionary
                    if self._presence_control.is_night_mode_active():
                        if entity_id in self.night_lights:
                            self._manual_states["night"][entity_id] = is_on
                    else:
                        if entity_id in self.lights:
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
        active_lights = self._get_active_lights()
        if not active_lights:
            return

        for light in active_lights:
            try:
                domain = light.split(".")[0]
                await self.hass.services.async_call(
                    domain, "turn_on", {"entity_id": light}, blocking=True
                )
            except ServiceNotFound as err:
                logCoordinator.error("Failed to turn on %s: %s", light, err)

    # 4. Light Control
    async def _turn_off_lights(self) -> None:
        """Turn off all active lights."""
        active_lights = self.active_lights

        if not active_lights:
            return

        try:
            await self.hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": active_lights},
                blocking=True,
            )
            logCoordinator.debug("Turning off active lights: %s", active_lights)
        except ServiceNotFound as err:
            logCoordinator.error("Failed to turn off lights: %s", err)

    # 5. Configuration and Options
    @callback
    def update_from_options(self, entry: ConfigEntry) -> None:
        """Update configuration from options."""
        self.presence_sensor = entry.options.get(CONF_PRESENCE_SENSOR)
        self.lights = entry.options.get(CONF_LIGHTS, [])
        self.night_lights = entry.options.get(CONF_NIGHT_LIGHTS, [])
        self.light_sensor = entry.options.get(CONF_LIGHT_SENSOR)

        self.night_mode_start = entry.options.get(
            CONF_NIGHT_MODE_START, DEFAULT_NIGHT_MODE_START
        )
        self.night_mode_end = entry.options.get(
            CONF_NIGHT_MODE_END, DEFAULT_NIGHT_MODE_END
        )

        self.detection_timeout = entry.options.get(
            CONF_DETECTION_TIMEOUT, DEFAULT_DETECTION_TIMEOUT
        )
        self.long_timeout = entry.options.get(CONF_LONG_TIMEOUT, DEFAULT_LONG_TIMEOUT)
        self.short_timeout = entry.options.get(
            CONF_SHORT_TIMEOUT, DEFAULT_SHORT_TIMEOUT
        )
        self.light_threshold = entry.options.get(
            CONF_LIGHT_THRESHOLD, DEFAULT_LIGHT_THRESHOLD
        )

        self._is_configured = bool(self.presence_sensor and self.lights)

    async def async_save_options(self) -> None:
        """Save manual states to config entry - called during shutdown."""
        if hasattr(self, "_manual_states") and self._manual_states:
            new_data = dict(self.entry.data) if self.entry.data else {}
            new_data.update(self._manual_states)

            self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    # 6. Event Handlers
    async def async_switch_changed(self, key: str, value: bool) -> None:
        """Handle switch changes."""
        await self.async_entity_changed("switch", key, value)

    async def async_entity_changed(
        self, entity_type: str, key: str, value: Any
    ) -> None:
        """Handle runtime control state changes."""
        try:
            # Update runtime data
            data_key = f"{entity_type}_{key}"
            self.data[data_key] = value
            self.async_set_updated_data(self.data)

            # Save to storage
            self._store.set_state(data_key, value)
            await self._store.async_save()

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
            active_lights = self.active_lights
            manual_states = self.manual_states
            mode = "night" if self._presence_control.is_night_mode_active() else "main"

            # If all stored states are off, turn on all lights
            all_lights_off = all(
                not manual_states[mode].get(light, True) for light in active_lights
            )

            if all_lights_off:
                logCoordinator.debug("All lights were off - turning on all lights")
                for light in active_lights:
                    try:
                        await self.hass.services.async_call(
                            "light",
                            "turn_on",
                            {"entity_id": light},
                            blocking=True,
                        )
                    except ServiceNotFound as err:
                        logCoordinator.error("Failed to turn on %s: %s", light, err)
            else:
                # Restore previous light states
                logCoordinator.debug("Restoring previous light states")
                for light in active_lights:
                    if manual_states[mode].get(
                        light, True
                    ):  # Default to ON for new lights
                        try:
                            await self.hass.services.async_call(
                                "light",
                                "turn_on",
                                {"entity_id": light},
                                blocking=True,
                            )
                        except ServiceNotFound as err:
                            logCoordinator.error("Failed to turn on %s: %s", light, err)

        elif new_state == RoomState.VACANT:
            await self._turn_off_lights()

        await self.async_refresh()

    async def async_number_changed(self, _key: str, _value: float) -> None:  # pylint: disable=unused-argument
        """Handle number changes - removed as numbers are now in options."""
        return

    async def async_time_changed(self, _key: str, _value: str) -> None:  # pylint: disable=unused-argument
        """Handle time changes - removed as times are now in options."""
        return

    # 7. Data Updates
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

        # Update light level only if sensor is configured
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

        is_night_mode = self._presence_control.is_night_mode_active()
        logCoordinator.debug("Night mode status: %s", is_night_mode)

        updated_data["binary_sensor_night_mode"] = is_night_mode

        return updated_data

    # 8. Timer Management
    async def update_timers(self, control_type: str, key: str) -> None:
        """Update running timers when control values change."""
        try:
            if (
                self._presence_control.state == RoomState.DETECTION_TIMEOUT
                and key == "detection_timeout"
            ):
                logCoordinator.debug(
                    "Updating detection timer: %s seconds",
                    self.detection_timeout,
                )
                await self._presence_control.start_detection_timer()
            elif self._presence_control.state == RoomState.COUNTDOWN and key in [
                "long_timeout",
                "short_timeout",
            ]:
                timeout = (
                    self.short_timeout if self.is_night_mode() else self.long_timeout
                )
                logCoordinator.debug(
                    "Updating countdown timer: %s seconds",
                    timeout,
                )
                await self._presence_control.start_countdown_timer()
        except (HomeAssistantError, TemplateError) as err:
            logCoordinator.warning(
                "Error updating timers for %s.%s: %s",
                control_type,
                key,
                err,
                exc_info=True,
            )
