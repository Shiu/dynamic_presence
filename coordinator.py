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
        self._presence_control = PresenceControl(hass, self)
        self._manual_states = {}

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
        }

        # Initialize coordinator
        hass.async_create_task(self.async_initialize())

    async def async_config_entry_first_refresh(self) -> None:
        """Initialize the coordinator."""
        # Load runtime states from storage
        await self._store.async_load()

        # Update runtime data from storage (switches and sensors only)
        for key, value in self._store.data.states.items():
            if key.startswith(("switch_", "binary_sensor_", "sensor_")):
                self.data[key] = value

        # Load manual light states
        self._manual_states = dict(self._store.data.manual_states)

        await self._async_update_data()
        self._async_setup_listeners()

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

    @callback
    def _get_active_lights(self) -> list:
        """Get the currently active set of lights based on night mode state."""
        return self.night_lights if self.is_night_mode() else self.lights

    @callback
    def is_night_mode(self) -> bool:
        """Check if night mode is currently active.

        Returns:
            bool: True if night mode is active, False otherwise
        """
        return self._is_night_mode()

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

        # Update light level if sensor configured
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

        return updated_data

    async def _handle_state_changed(self, new_state: RoomState) -> None:
        """Handle room state changes."""
        if new_state == RoomState.OCCUPIED:
            active_lights = self.active_lights
            # If all stored states are off, turn on all lights
            all_lights_off = all(
                not self._manual_states.get(light, True) for light in active_lights
            )

            if all_lights_off:
                logCoordinator.debug("All lights were off - turning on all lights")
                for light in active_lights:
                    try:
                        domain = light.split(".")[0]
                        await self.hass.services.async_call(
                            domain, "turn_on", {"entity_id": light}, blocking=True
                        )
                    except ServiceNotFound as err:
                        logCoordinator.error("Failed to turn on %s: %s", light, err)
            else:
                # Restore previous light states
                logCoordinator.debug("Restoring previous light states")
                for light in active_lights:
                    if self._manual_states.get(light, False):
                        try:
                            domain = light.split(".")[0]
                            await self.hass.services.async_call(
                                domain, "turn_on", {"entity_id": light}, blocking=True
                            )
                        except ServiceNotFound as err:
                            logCoordinator.error("Failed to turn on %s: %s", light, err)
        elif new_state == RoomState.VACANT:
            await self._turn_off_lights()

        await self.async_refresh()

    async def _async_light_changed(self, event) -> None:
        """Handle light state changes."""
        if self._presence_control.state == RoomState.OCCUPIED:
            try:
                entity_id = event.data.get("entity_id")
                new_state = event.data.get("new_state")
                if new_state is not None:
                    is_on = new_state.state == STATE_ON
                    self._manual_states[entity_id] = is_on
                    self._store.set_manual_state(entity_id, is_on)
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

    async def _turn_off_lights(self) -> None:
        """Turn off all active lights."""
        active_lights = self._get_active_lights()
        for light in active_lights:
            try:
                domain = light.split(".")[0]
                await self.hass.services.async_call(
                    domain, "turn_off", {"entity_id": light}, blocking=True
                )
            except ServiceNotFound as err:
                logCoordinator.error("Failed to turn off %s: %s", light, err)

    async def async_save_options(self) -> None:
        """Save manual states to config entry - called during shutdown."""
        if hasattr(self, "_manual_states") and self._manual_states:
            new_data = dict(self.entry.data) if self.entry.data else {}
            new_data.update(self._manual_states)

            self.hass.config_entries.async_update_entry(self.entry, data=new_data)

    async def async_switch_changed(self, key: str, value: bool) -> None:
        """Handle switch changes."""
        await self.async_entity_changed("switch", key, value)

    async def async_number_changed(self, _key: str, _value: float) -> None:  # pylint: disable=unused-argument
        """Handle number changes - removed as numbers are now in options."""
        return

    async def async_time_changed(self, _key: str, _value: str) -> None:  # pylint: disable=unused-argument
        """Handle time changes - removed as times are now in options."""
        return

    def _is_night_mode(self) -> bool:
        """Check if night mode is active."""
        if not self.data["switch_night_mode"]:
            return False

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

    async def handle_state_changed(self, new_state: RoomState) -> None:
        """Public method to handle state changes."""
        await self._handle_state_changed(new_state)

    @property
    def active_lights(self):
        """Get list of currently active lights based on mode."""
        if self.is_night_mode():
            return self.night_lights
        return self.lights

    async def clear_manual_states(self) -> None:
        """Clear all manual light states."""
        self._manual_states.clear()
        await self._store.async_save()

    async def _async_init_manual_states(self) -> None:
        """Initialize manual states by polling current light states."""
        active_lights = self.active_lights
        for light in active_lights:
            try:
                state = self.hass.states.get(light)
                if state:
                    self._manual_states[light] = state.state == STATE_ON
                    logCoordinator.debug(
                        "Initialized light %s state to %s",
                        light,
                        self._manual_states[light],
                    )
            except HomeAssistantError as err:
                logCoordinator.error("Failed to get state for %s: %s", light, err)

        await self._store.async_save()

    async def async_initialize(self) -> None:
        """Initialize the coordinator."""
        # Load stored manual states
        stored_data = await self._store.async_load()
        if stored_data:
            self._manual_states = stored_data

        # Initialize states from current light states
        await self._async_init_manual_states()

        # Set up listeners
        self._async_setup_listeners()
