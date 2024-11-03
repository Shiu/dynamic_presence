"""Coordinator for Dynamic Presence integration."""

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, UnknownEntry
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
    CONF_REMOTE_CONTROL_TIMEOUT,
    CONF_ROOM_NAME,
    DEFAULT_ACTIVE_ROOM_THRESHOLD,
    DEFAULT_LIGHT_THRESHOLD,
    DEFAULT_REMOTE_CONTROL_TIMEOUT,
    DOMAIN,
    NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE,
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
        self.is_active = False
        self.presence_sensor = entry.options.get(
            CONF_PRESENCE_SENSOR, entry.data.get(CONF_PRESENCE_SENSOR)
        )
        self.presence_detector = None  # Will be set later

        # Initialize tracking attributes
        self._manual_states = {}  # Permanent storage
        self._temp_manual_states = {}  # Temporary storage
        self._entity_types = {}  # Cache entity types
        self._remote_control_timeout = None
        self._remote_control_start_time = None
        self._stored_manage_on_clear = None
        self._stored_manage_on_presence = None

        # Get existing values from entry data and options
        combined_data = {**entry.data, **entry.options}

        # Time values
        for key in TIME_KEYS:
            self.data[key] = combined_data.get(key, TIME_DEFAULT_VALUES[key])

        # Number values
        for key, config in NUMBER_CONFIG.items():
            self.data[key] = combined_data.get(key, config["default"])

        # Switch values
        for key in SWITCH_KEYS:
            self.data[key] = combined_data.get(key, SWITCH_DEFAULT_STATES[key])

        # Night mode values
        for key in NIGHT_MODE_KEYS:
            self.data[key] = combined_data.get(
                key, NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE
            )

        self.active_room_threshold = combined_data.get(
            CONF_ACTIVE_ROOM_THRESHOLD, DEFAULT_ACTIVE_ROOM_THRESHOLD
        )

        # Set up event listener for presence sensor
        hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)

        # Add listener for controlled entities
        hass.bus.async_listen(EVENT_STATE_CHANGED, self._detect_manual_changes)

        self.presence_detector = PresenceDetector(hass, entry, self)

        self._processing_state_change = False  # Add this flag

    async def _async_update_data(self):
        """Update data from presence detector."""
        current_time = datetime.now()

        # Update light level if sensor is configured
        if light_sensor := self.entry.options.get(
            CONF_LIGHT_SENSOR, self.entry.data.get(CONF_LIGHT_SENSOR)
        ):
            if state := self.hass.states.get(light_sensor):
                try:
                    self.data[f"{self.room_name}_light_level"] = int(float(state.state))
                except (ValueError, TypeError):
                    logCoordinator.warning(
                        "Invalid light level value from sensor %s: %s",
                        light_sensor,
                        state.state,
                    )
                    self.data[f"{self.room_name}_light_level"] = None

        # Calculate remote control duration
        if self._remote_control_timeout is not None:
            duration = int(
                (current_time - self._remote_control_start_time).total_seconds()
            )
            self.data[f"{self.room_name}_remote_control_duration"] = duration

            # Check if we've exceeded the timeout
            timeout = self.entry.options.get(
                CONF_REMOTE_CONTROL_TIMEOUT, DEFAULT_REMOTE_CONTROL_TIMEOUT
            )
            if duration >= timeout:
                # Cancel the timer and handle timeout
                self._remote_control_timeout = None
                await self.manage_entities(turn_on=False)
                await self._restore_manage_on_clear("remote control timeout")
        else:
            self.data[f"{self.room_name}_remote_control_duration"] = 0

        # Update presence state
        await self.presence_detector.update_presence()

        # Update durations
        await self.presence_detector.calculate_durations(current_time)

        # Check active room status
        await self._check_active_room_status()

        # Update night mode status
        night_mode_active = (
            self.data.get("night_mode_enable") and self._is_night_mode_active()
        )
        self.data[f"{self.room_name}_night_mode_status"] = (
            "on" if night_mode_active else "off"
        )

        # Handle night mode override
        self._handle_night_mode_override()

        return self.data

    def _store_temp_manual_state(self, entity_id: str, state: bool):
        """Store manual state temporarily until room becomes occupied."""
        self._temp_manual_states[entity_id] = state
        logCoordinator.debug(
            "Stored temporary manual state for %s: %s (Current manual states: %s)",
            entity_id,
            state,
            self._manual_states,
        )

    def _apply_temp_manual_states(self):
        """Apply temporary manual states when room becomes occupied."""
        if self._temp_manual_states:
            logCoordinator.debug(
                "Before applying temp states - Manual states: %s, Temp states: %s",
                self._manual_states,
                self._temp_manual_states,
            )
            self._manual_states.update(self._temp_manual_states)
            self._temp_manual_states.clear()
            logCoordinator.debug(
                "After applying temp states - Manual states: %s", self._manual_states
            )

    def _update_manual_states(
        self,
        entity_id: str,
        new_state: bool | None = None,
        clear_type: str | None = None,
    ):
        """Update manual states for entities.

        Args:
            entity_id: The entity ID to update
            new_state: The new state to set (True=ON, False=OFF, None=clear)
            clear_type: If provided, clear all manual states for this entity type
        """

        if clear_type:
            # Clear all manual states for the specified type
            for ent_id in list(self._manual_states.keys()):
                if self._get_entity_type(ent_id) == clear_type:
                    del self._manual_states[ent_id]
            logCoordinator.debug("Cleared manual states for type: %s", clear_type)
            return

        if new_state is None:
            if entity_id in self._manual_states:
                del self._manual_states[entity_id]
                logCoordinator.debug("Cleared manual state for: %s", entity_id)
            return

        if self.data.get(f"{self.room_name}_occupancy_state") == "on":
            self._manual_states[entity_id] = new_state
            logCoordinator.debug(
                "Updated manual state for %s to %s", entity_id, new_state
            )

    def _get_manual_states(self, entity_type: str) -> None:
        """Reset manual states if conditions are met."""
        self._update_manual_states(None, clear_type=entity_type)

    async def manage_entities(self, turn_on: bool = False):
        """Manage controlled entities."""
        if not self.data.get("enable", True):
            return

        if turn_on and not self.data.get("manage_on_presence", True):
            return

        if not turn_on and not self.data.get("manage_on_clear", True):
            return

        # For turning off, check if absence duration has exceeded timeout
        if not turn_on:
            # Skip timeout check if bypass flag is set
            if not self.data.get(f"{self.room_name}_bypass_presence_timeout", False):
                absence_duration = self.data.get(
                    f"{self.room_name}_absence_duration", 0
                )
                timeout = self._get_current_timeout()

                if absence_duration < timeout:
                    # Don't turn off yet, timeout not reached
                    return

                # Clear manual states if flag was set (all lights were on when leaving)
                if self.data.get(f"{self.room_name}_clear_states_after_timeout", False):
                    logCoordinator.debug(
                        "Presence timeout reached, clearing manual states"
                    )
                    self._get_manual_states("light")
                    self.data[f"{self.room_name}_clear_states_after_timeout"] = False

        # Get controlled entities
        entities = self._get_controlled_entities()

        # Check current states
        any_on = False
        for entity_id in entities:
            if state := self.hass.states.get(entity_id):
                if state.state == "on":
                    any_on = True
                    break

        service = "turn_off"
        if turn_on:
            # If lights are already on, keep them on
            if any_on:
                return

            # If lights are off, only turn on if room is dark
            if not self._is_room_dark():
                logCoordinator.debug("Room is bright enough, keeping lights off")
                return

            service = "turn_on"

        for entity_id in entities:
            try:
                # When turning on, respect manual states
                if turn_on and entity_id in self._manual_states:
                    if not self._manual_states[entity_id]:  # If manual state was OFF
                        continue

                current_state = self.hass.states.get(entity_id)
                if current_state is None:
                    continue

                # Only send command if state needs to change
                if (service == "turn_on" and current_state.state == "off") or (
                    service == "turn_off" and current_state.state == "on"
                ):
                    await self.hass.services.async_call(
                        "homeassistant", service, {"entity_id": entity_id}
                    )
                    logCoordinator.debug("%s %s", service, entity_id)
            except (ValueError, TimeoutError) as e:
                logCoordinator.error("Failed to %s %s: %s", service, entity_id, str(e))

    async def _handle_state_change(self, event):
        """Handle state changes for the presence sensor."""
        if self._processing_state_change:
            return

        try:
            self._processing_state_change = True
            entity_id = event.data.get("entity_id")

            # Handle presence sensor changes
            if entity_id == self.presence_sensor:
                new_state = event.data.get("new_state")
                if new_state:
                    is_occupied = new_state.state == "on"
                    if is_occupied:
                        if self._remote_control_timeout is not None:
                            self._remote_control_timeout = None
                            await self._restore_manage_on_clear("presence detected")
                            logCoordinator.debug(
                                "Room is occupied, applying temp states"
                            )
                            self._apply_temp_manual_states()
                    else:  # Room becomes empty
                        if self._are_all_lights_off():
                            # All lights off - clear states after grace period
                            self.data[f"{self.room_name}_bypass_presence_timeout"] = (
                                True
                            )
                            logCoordinator.debug(
                                "All lights off when leaving, clearing states after grace"
                            )
                        else:
                            # Check if all lights are on
                            all_lights_on = True
                            for ent_id in self._get_controlled_entities():
                                if self._get_entity_type(ent_id) == "light":
                                    if state := self.hass.states.get(ent_id):
                                        if state.state != "on":
                                            all_lights_on = False
                                            break

                            if all_lights_on:
                                # All lights on - clear states after presence timeout
                                self.data[
                                    f"{self.room_name}_clear_states_after_timeout"
                                ] = True
                                logCoordinator.debug(
                                    "All lights on when leaving, clearing states after timeout"
                                )
                            else:
                                # Mixed states - keep manual states
                                logCoordinator.debug(
                                    "Mixed light states when leaving room, keeping manual states"
                                )
                            self.data[f"{self.room_name}_bypass_presence_timeout"] = (
                                False
                            )

            # Handle occupancy state changes (after grace period)
            elif (
                entity_id == f"sensor.dynamic_presence_{self.room_name}_occupancy_state"
            ):
                new_state = event.data.get("new_state")
                if new_state and new_state.state == "vacant":
                    if self.data.get(
                        f"{self.room_name}_bypass_presence_timeout", False
                    ):
                        logCoordinator.debug(
                            "Grace period complete, clearing manual states"
                        )
                        self._get_manual_states("light")

        finally:
            self._processing_state_change = False

    async def _detect_manual_changes(self, event):
        """Detect if entity state changes were triggered manually."""
        entity_id = event.data.get("entity_id")

        # Skip non-controlled entities and sensors
        if (
            entity_id not in self._get_controlled_entities()
            or entity_id.startswith("sensor.")
            or entity_id.startswith("binary_sensor.")
        ):
            return

        new_state = event.data.get("new_state")
        if not new_state or new_state.context.user_id is None:
            return

        new_state_on = new_state.state == "on"

        # Always store in temp states first
        self._store_temp_manual_state(entity_id, new_state_on)

        # If room is occupied, apply to manual states
        if self.data.get(f"{self.room_name}_occupancy_state") == "on":
            logCoordinator.debug(
                "Room is occupied, applying temp states -detect_manual_changes"
            )
            self._apply_temp_manual_states()

        # Handle remote control timeout if turning on lights in empty room
        if new_state_on and self._get_entity_type(entity_id) == "light":
            if self.data.get(f"{self.room_name}_occupancy_state") != "on":
                await self._start_remote_control_timeout()

    async def _start_remote_control_timeout(self):
        """Start remote control timeout when manually turning on lights in empty room."""
        # Cancel existing timer if running
        if self._remote_control_timeout is not None:
            self._remote_control_timeout = None

        # Store current manage_on_clear state and disable it
        if self._stored_manage_on_clear is None:
            self._stored_manage_on_clear = self.data.get("manage_on_clear", True)
            await self.async_save_options("manage_on_clear", False)
            logCoordinator.debug(
                "Disabled manage_on_clear due to manual ON in empty room"
            )

        self._remote_control_start_time = datetime.now()
        self._remote_control_timeout = True

    async def _restore_manage_on_clear(self, reason: str):
        """Restore manage_on_clear setting."""
        if self._stored_manage_on_clear is not None:
            await self.async_save_options(
                "manage_on_clear", self._stored_manage_on_clear
            )
            self._stored_manage_on_clear = None
            logCoordinator.debug("Restored manage_on_clear after %s", reason)

    def _get_entity_type(self, entity_id: str) -> str:
        """Get the domain/type of an entity."""
        if entity_id not in self._entity_types:
            self._entity_types[entity_id] = entity_id.split(".")[0]
        return self._entity_types[entity_id]

    def _get_controlled_entities(self) -> list:
        """Get the list of entities to control based on night mode and addmode."""
        regular_entities = self.entry.options.get(
            CONF_CONTROLLED_ENTITIES, self.entry.data.get(CONF_CONTROLLED_ENTITIES, [])
        )
        night_entities = self.entry.options.get(
            CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
            self.entry.data.get(CONF_NIGHT_MODE_CONTROLLED_ENTITIES, []),
        )

        # If night mode is not enabled or not active, use regular entities
        if not self.data.get("night_mode_enable") or not self._is_night_mode_active():
            return regular_entities

        # Get the add mode setting with default to additive
        addmode = self.entry.options.get(
            CONF_NIGHT_MODE_ENTITIES_ADDMODE, NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE
        )

        # In exclusive mode:
        # - If night entities exist, use only those
        # - If no night entities, fall back to regular entities
        if addmode == NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE:
            if night_entities:
                return night_entities
            return regular_entities

        # In additive mode, combine both lists
        return list(set(regular_entities + night_entities))

    def _get_current_timeout(self) -> int:
        """Get the current timeout based on active status and night mode."""
        base_timeout = (
            self.data.get("active_room_timeout")
            if self.is_active
            else self.data.get("presence_timeout")
        )

        if self.data.get("night_mode_enable") and self._is_night_mode_active():
            scale = self.data.get("night_mode_scale")
            return int(base_timeout * scale)

        return base_timeout

    def _is_room_dark(self) -> bool:
        """Check if room is too dark and needs lights."""
        light_level = self.data.get(f"{self.room_name}_light_level")
        threshold = self.data.get(CONF_LIGHT_THRESHOLD, DEFAULT_LIGHT_THRESHOLD)

        if light_level is not None:
            return light_level < threshold

        # If no light sensor or invalid reading, default to True (assume room needs light)
        return True

    def _is_night_mode_active(self) -> bool:
        """Check if night mode is active based on current time."""
        if not self.data.get("night_mode_enable"):
            return False

        current_time = dt_util.now().strftime("%H:%M")
        start = self.data.get(
            "night_mode_start", TIME_DEFAULT_VALUES["night_mode_start"]
        )
        end = self.data.get("night_mode_end", TIME_DEFAULT_VALUES["night_mode_end"])

        # Trim seconds if present
        start = start[:5] if len(start) > 5 else start
        end = end[:5] if len(end) > 5 else end

        if start <= end:
            is_active = start <= current_time < end
        else:  # Handles case where night mode spans midnight
            is_active = current_time >= start or current_time < end

        return is_active

    def _handle_night_mode_override(self) -> None:
        """Handle night mode override for manage on presence."""
        if (
            self.data.get("night_mode_enable")
            and self._is_night_mode_active()
            and self.data.get("night_mode_override_on_presence")
        ):
            # Store current manage_on_presence state if not already stored
            if self._stored_manage_on_presence is None:
                self._stored_manage_on_presence = self.data.get(
                    "manage_on_presence", True
                )
                self.data["manage_on_presence"] = False
                logCoordinator.debug(
                    "Night mode override: disabled manage_on_presence (stored: %s)",
                    self._stored_manage_on_presence,
                )
                # Make sure changes are saved
                self.async_set_updated_data(self.data)
        elif self._stored_manage_on_presence is not None:
            # Restore previous state when night mode ends or override is disabled
            self.data["manage_on_presence"] = self._stored_manage_on_presence
            logCoordinator.debug(
                "Night mode override: restored manage_on_presence to %s",
                self._stored_manage_on_presence,
            )
            self._stored_manage_on_presence = None

        # Make sure changes are saved and propagated
        if "manage_on_presence" in self.data:
            self.async_set_updated_data(self.data)

    async def _check_active_room_status(self):
        """Check and update active room status based on occupancy duration."""
        occupancy_duration = self.data.get(f"{self.room_name}_occupancy_duration", 0)
        absence_duration = self.data.get(f"{self.room_name}_absence_duration", 0)
        is_occupied = self.data.get(f"{self.room_name}_occupancy_state") == "on"

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

    async def async_update_presence_timeout(self, timeout: int):
        """Update the presence timeout."""
        self.presence_detector.set_presence_timeout(timeout)
        self.data["presence_timeout"] = timeout
        await self.async_save_options("presence_timeout", timeout)

    async def async_update_controlled_entities(self, entities: list):
        """Update controlled entities list."""
        new_options = dict(self.entry.options)
        new_options[CONF_CONTROLLED_ENTITIES] = entities
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)

    async def async_update_options(self, _: HomeAssistant, entry: ConfigEntry) -> None:
        """Update coordinator data from options."""
        # Only update changed values, not everything
        for key, value in entry.options.items():
            if key in self.data and self.data[key] != value:
                self.data[key] = value
        self.async_set_updated_data(self.data)

    async def async_save_options(self, key: str, value: Any) -> None:
        """Save a single option value to config entry."""
        try:
            new_options = dict(self.entry.options)
            new_data = dict(self.entry.data)

            # Update both options and data
            new_options[key] = value
            new_data[key] = value

            # Update coordinator's internal state
            if key in NUMBER_CONFIG:
                # Handle number inputs
                setattr(self, key, value)
            elif key in SWITCH_KEYS:
                # Handle switch inputs
                setattr(self, key, value)
            elif key in TIME_KEYS:
                # Handle time inputs
                setattr(self, key, value)

            self.data[key] = value  # Update coordinator data
            self.async_set_updated_data(self.data)  # Notify listeners

            # Save to config entry
            self.hass.config_entries.async_update_entry(
                self.entry, data=new_data, options=new_options
            )
        except UnknownEntry:
            logCoordinator.warning("Failed to save options: config entry not found.")

    def get_entity_name(self, entity_type: str, name: str) -> str:
        """Get the entity name."""
        room_name = (
            self.entry.data.get(CONF_ROOM_NAME, "Unknown Room")
            .lower()
            .replace(" ", "_")
        )
        return f"{entity_type}.dynamic_presence_{room_name}_{name.lower().replace(' ', '_')}"

    def get_device_info(self, room: str) -> dict:
        """Return device info for the given room."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": f"Dynamic Presence {room.capitalize()}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
            "sw_version": "1.0",
        }

    def _are_all_lights_off(self) -> bool:
        """Check if all controlled lights are off."""
        type_entities = [
            entity_id
            for entity_id in self._get_controlled_entities()
            if self._get_entity_type(entity_id) == "light"
        ]

        if not type_entities:
            return False

        # Count how many are on/off
        on_count = 0
        for entity_id in type_entities:
            if state := self.hass.states.get(entity_id):
                if state.state == "on":
                    on_count += 1

        return on_count == 0
