"""Light control for Dynamic Presence integration."""

import logging
from typing import List, Optional

from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound

logLightController = logging.getLogger("dynamic_presence.light_controller")


class LightController:
    """Handles all light-related operations."""

    # 1. Core Initialization
    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize light controller."""
        self.hass = hass

    # 2. Light State Checks
    def check_any_lights_on(self, lights: List[str]) -> bool:
        """Check if any of the specified lights are on."""
        for light in lights:
            try:
                state = self.hass.states.get(light)
                if state and state.state == STATE_ON:
                    return True
            except HomeAssistantError as err:
                logLightController.error("Error checking light state: %s", err)
        return False

    def get_light_state(self, light: str) -> Optional[bool]:
        """Get state of a specific light."""
        try:
            state = self.hass.states.get(light)
            if state:
                return state.state == STATE_ON
        except HomeAssistantError as err:
            logLightController.error("Error getting light state: %s", err)
        return None

    # 3. Light Operations
    async def turn_on_lights(self, lights: List[str]) -> None:
        """Turn on specified lights."""
        if not lights:
            return

        for light in lights:
            try:
                domain = light.split(".")[0]
                await self.hass.services.async_call(
                    domain, "turn_on", {"entity_id": light}, blocking=True
                )
            except ServiceNotFound as err:
                logLightController.error("Failed to turn on %s: %s", light, err)

    async def turn_off_lights(self, lights: List[str]) -> None:
        """Turn off specified lights."""
        if not lights:
            return

        try:
            await self.hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": lights},
                blocking=True,
            )
            logLightController.debug("Turning off lights: %s", lights)
        except ServiceNotFound as err:
            logLightController.error("Failed to turn off lights: %s", err)

    async def update_active_lights(
        self, is_night_mode: bool, lights_to_control: list, manual_states: dict
    ) -> None:
        """Update which lights are active based on mode."""
        # Turn off lights that aren't in the new mode's set
        all_lights = set(lights_to_control)
        for light in all_lights:
            if light not in lights_to_control:
                await self.turn_off_lights([light])

        # Turn on lights according to their manual states
        mode = "night" if is_night_mode else "main"
        lights_to_turn_on = [
            light for light in lights_to_control if manual_states[mode].get(light, True)
        ]
        if lights_to_turn_on:
            await self.turn_on_lights(lights_to_turn_on)
