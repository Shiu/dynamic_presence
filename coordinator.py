"""Coordinator for Dynamic Presence integration."""

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_CONTROLLED_ENTITIES,
    CONF_LIGHT_SENSOR,
    CONF_LIGHT_THRESHOLD,
    CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
    CONF_NIGHT_MODE_ENTITIES_ADDMODE,
    CONF_PRESENCE_SENSOR,
    CONF_ROOM_NAME,
    DEFAULT_ACTIVE_ROOM_THRESHOLD,
    DEFAULT_LIGHT_THRESHOLD,
    DOMAIN,
    NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE,
    NIGHT_MODE_KEYS,
    NUMBER_CONFIG,
    SWITCH_DEFAULT_STATES,
    SWITCH_KEYS,
    TIME_DEFAULT_VALUES,
    TIME_KEYS,
)
from .presence_detector import PresenceDetector


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
    """Coordinate between Dynamic Presence components."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            name="Dynamic Presence",
            logger=logCoordinator,
            update_interval=timedelta(seconds=1),
        )
        self.entry = entry
        self.room_name = (
            entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
        )

        # Initialize data with existing values or defaults
        self.data = {}

        # Get existing values from entry data and options
        combined_data = {**entry.data, **entry.options}

        # Initialize all configuration values
        for key, default in {
            **TIME_DEFAULT_VALUES,
            **{k: v["default"] for k, v in NUMBER_CONFIG.items()},
            **SWITCH_DEFAULT_STATES,
            **{k: NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE for k in NIGHT_MODE_KEYS},
        }.items():
            self.data[key] = combined_data.get(key, default)

        self.is_active = False
        self.active_room_threshold = combined_data.get(
            CONF_ACTIVE_ROOM_THRESHOLD, DEFAULT_ACTIVE_ROOM_THRESHOLD
        )

        # Set up event listener for presence sensor
        self.presence_sensor = entry.data[CONF_PRESENCE_SENSOR]
        hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)

        self.presence_detector = PresenceDetector(hass, entry, self)
        self._stored_manage_on_presence = None
        self.entities = {}

    async def _async_update_data(self):
        """Update data from presence detector."""
        current_time = datetime.now()
        new_data = dict(self.data)

        # Update light level if sensor is configured
        if light_sensor := self.entry.data.get(CONF_LIGHT_SENSOR):
            if state := self.hass.states.get(light_sensor):
                try:
                    new_light_level = int(float(state.state))
                    if new_light_level != self.data.get(
                        f"{self.room_name}_light_level"
                    ):
                        new_data[f"{self.room_name}_light_level"] = new_light_level
                except (ValueError, TypeError):
                    logCoordinator.warning(
                        "Invalid light level value from sensor %s: %s",
                        light_sensor,
                        state.state,
                    )
                    new_data[f"{self.room_name}_light_level"] = None

        # Update presence state and durations
        await self.presence_detector.update_presence()
        await self.presence_detector.calculate_durations(current_time)

        # Check active room status
        await self._check_active_room_status()

        # Update night mode status
        new_night_mode = self._is_night_mode_active()
        if new_night_mode != self.data.get("night_mode_active"):
            new_data["night_mode_active"] = new_night_mode
            self._handle_night_mode_override()

        # Only update if data has actually changed
        if new_data != self.data:
            self.data = new_data
            return new_data
        return self.data

    async def _check_active_room_status(self):
        """Check and update active room status based on occupancy duration."""
        occupancy_duration = self.data.get(f"{self.room_name}_occupancy_duration", 0)
        absence_duration = self.data.get(f"{self.room_name}_absence_duration", 0)
        is_occupied = self.data.get(f"{self.room_name}_occupancy_state") == "occupied"

        if is_occupied and occupancy_duration >= self.active_room_threshold:
            if not self.is_active:
                self.is_active = True
                self.data[f"{self.room_name}_active_room_status"] = True
                logCoordinator.debug(
                    "Room %s activated after %s seconds",
                    self.room_name,
                    occupancy_duration,
                )
        elif not is_occupied and self.is_active:
            # Only deactivate if absence duration exceeds active room timeout
            if absence_duration >= self.data.get("active_room_timeout"):
                self.is_active = False
                self.data[f"{self.room_name}_active_room_status"] = False
                logCoordinator.debug(
                    "Room %s deactivated after timeout", self.room_name
                )

    async def async_update_presence_timeout(self, timeout: int):
        """Update the presence timeout."""
        self.presence_detector.set_presence_timeout(timeout)
        self.data["presence_timeout"] = timeout
        await self.async_save_options("presence_timeout", timeout)

    def get_entity_name(self, entity_type: str, name: str) -> str:
        """Get the entity name."""
        room_name = (
            self.entry.data.get(CONF_ROOM_NAME, "Unknown Room")
            .lower()
            .replace(" ", "_")
        )
        return f"{entity_type}.{room_name}_{name.lower().replace(' ', '_')}"

    def get_device_info(self, room: str) -> dict:
        """Return device info for the given room."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"Dynamic Presence {room.capitalize()}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
            "sw_version": "1.0",
        }

    async def _handle_state_change(self, event):
        """Handle state changes for the presence sensor."""
        if event.data.get("entity_id") == self.presence_sensor:
            if self.hass.states.get(self.presence_sensor) is None:
                logCoordinator.warning(
                    "Presence sensor %s not found", self.presence_sensor
                )
                return
            await self.async_refresh()

    def update_data_from_options(self, options: dict):
        """Update coordinator data from options."""
        # Only update values that are actually present in options
        for key in TIME_KEYS:
            if key in options:
                self.data[key] = options[key]

        for key in NUMBER_CONFIG:
            if key in options:
                self.data[key] = options[key]

        for key in NIGHT_MODE_KEYS:
            if key in options:
                self.data[key] = options[key]

        for key in SWITCH_KEYS:
            if key not in options:
                continue

            new_value = options[key]
            if (
                key == "manage_on_presence"
                and new_value is True
                and self.data.get("night_mode_active")
                and self.data.get("night_mode_override_on_presence")
            ):
                self._stored_manage_on_presence = True
                self.data[key] = False
                continue

            self.data[key] = new_value

    async def async_update_options(self, _: HomeAssistant, entry: ConfigEntry) -> None:
        """Update coordinator data from options."""
        # Only update changed values, not everything
        for key, value in entry.options.items():
            if key in self.data and self.data[key] != value:
                self.data[key] = value
        self.async_set_updated_data(self.data)

    async def async_save_options(self, key: str, value: Any) -> None:
        """Save a single option value to config entry."""
        new_options = dict(self.entry.options)
        new_data = dict(self.entry.data)

        # Update both options and data
        new_options[key] = value
        new_data[key] = value

        # Update coordinator's internal state
        self.data[key] = value
        self.async_set_updated_data(self.data)

        # Save to config entry
        self.hass.config_entries.async_update_entry(
            self.entry, data=new_data, options=new_options
        )

    async def async_update_controlled_entities(self, entities: list):
        """Update controlled entities list."""
        self.data["controlled_entities"] = entities
        new_options = dict(self.entry.options)
        new_options[CONF_CONTROLLED_ENTITIES] = entities

        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, CONF_CONTROLLED_ENTITIES: entities}
        )

    def _is_room_dark(self) -> bool:
        """Check if room is too dark and needs lights."""
        light_level = self.data.get(f"{self.room_name}_light_level")
        threshold = self.data.get(CONF_LIGHT_THRESHOLD, DEFAULT_LIGHT_THRESHOLD)

        if light_level is not None:
            return light_level < threshold

        # If no light sensor or invalid reading, default to True (assume room needs light)
        return True

    def _get_current_timeout(self) -> int:
        """Get the current timeout based on active status and night mode."""
        base_timeout = (
            self.data.get("active_room_timeout")
            if self.is_active
            else self.data.get("presence_timeout")
        )

        if self.data.get("night_mode_enable") and self.data.get(
            "night_mode_active", False
        ):
            scale = self.data.get("night_mode_scale", 0.5)
            return int(base_timeout * scale)

        return base_timeout

    def _get_controlled_entities(self) -> list:
        """Get the list of entities to control based on night mode and addmode."""
        regular_entities = self.entry.data.get(CONF_CONTROLLED_ENTITIES, [])
        night_entities = self.entry.data.get(CONF_NIGHT_MODE_CONTROLLED_ENTITIES, [])

        if not self.data.get("night_mode_enable") or not self.data.get(
            "night_mode_active", False
        ):
            return regular_entities

        # We're in night mode, handle entities based on addmode
        addmode = self.data.get(CONF_NIGHT_MODE_ENTITIES_ADDMODE)
        if addmode == NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE:
            return night_entities if night_entities else regular_entities
        # ADDITIVE
        return list(set(regular_entities + night_entities))

    async def manage_entities(self, turn_on: bool = False):
        """Manage controlled entities based on presence and light conditions."""
        if not self.data.get("enable", True):
            return

        if turn_on and not self.data.get("manage_on_presence", True):
            return

        if not turn_on and not self.data.get("manage_on_clear", True):
            return

        # Re-enable manage_on_clear when presence detected
        if self.presence_detector.is_presence_detected():
            if not self.data.get("manage_on_clear", True):
                await self.async_save_options("manage_on_clear", True)
                logCoordinator.debug(
                    "Re-enabled manage_on_clear due to presence detection"
                )

        # For turning off, check if absence duration has exceeded timeout
        if not turn_on:
            absence_duration = self.data.get(f"{self.room_name}_absence_duration", 0)
            timeout = self._get_current_timeout()

            if absence_duration < timeout:
                # Don't turn off yet, timeout not reached
                return

            service = "turn_off"
        else:
            # Check current state of entities before deciding to turn on
            entities = self._get_controlled_entities()
            any_on = False
            for entity_id in entities:
                if state := self.hass.states.get(entity_id):
                    if state.state == "on":
                        any_on = True
                        break

            # If lights are already on, keep them on
            if any_on:
                return

            # If lights are off, only turn on if room is dark
            if not self._is_room_dark():
                logCoordinator.debug("Room is bright enough, keeping lights off")
                return

            service = "turn_on"

        # Get the appropriate list of entities based on night mode and addmode
        entities = self._get_controlled_entities()

        for entity_id in entities:
            try:
                await self.hass.services.async_call(
                    "homeassistant", service, {"entity_id": entity_id}
                )
                logCoordinator.debug("%s %s", service, entity_id)
            except (ValueError, TimeoutError) as e:
                logCoordinator.error("Failed to %s %s: %s", service, entity_id, str(e))

    def _is_night_mode_active(self) -> bool:
        """Check if current time is within night mode hours."""
        if not self.data.get("night_mode_enable"):
            logCoordinator.debug("Night mode not enabled")
            return False

        start = self.data.get("night_mode_start")
        end = self.data.get("night_mode_end")

        if not start or not end:
            logCoordinator.warning("Night mode start or end time not set")
            return False

        current_time = dt_util.now().strftime("%H:%M")
        start = start[:5] if len(start) > 5 else start
        end = end[:5] if len(end) > 5 else end

        logCoordinator.debug(
            "Night mode check - Enable: %s, Current: %s, Start: %s, End: %s",
            self.data.get("night_mode_enable"),
            current_time,
            start,
            end,
        )

        if start <= end:
            is_active = start <= current_time < end
        else:  # Handles case where night mode spans midnight
            is_active = current_time >= start or current_time < end

        logCoordinator.debug("Night mode active: %s", is_active)
        return is_active

    def _handle_night_mode_override(self) -> None:
        """Handle night mode override for manage on presence."""
        if (
            self.data.get("night_mode_enable")
            and self.data.get("night_mode_active")
            and self.data.get("night_mode_override_on_presence")
        ):
            if self._stored_manage_on_presence is None:
                self._stored_manage_on_presence = self.data.get(
                    "manage_on_presence", True
                )
                self.data["manage_on_presence"] = False
                self.async_set_updated_data(self.data)
                logCoordinator.debug("Night mode override: disabled manage_on_presence")
        elif self._stored_manage_on_presence is not None:
            self.data["manage_on_presence"] = self._stored_manage_on_presence
            self._stored_manage_on_presence = None
            self.async_set_updated_data(self.data)
            logCoordinator.debug("Night mode override: restored manage_on_presence")
