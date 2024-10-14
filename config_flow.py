"""Config flow for Dynamic Presence integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_CONTROLLED_ENTITIES,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_PRESENCE_SENSOR,
    CONF_PRESENCE_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class DynamicPresenceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dynamic Presence."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DynamicPresenceOptionsFlowHandler:
        """Get the options flow for this handler."""
        return DynamicPresenceOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate and process user input here
            # If valid, create the config entry
            title = f"Dynamic Presence {user_input[CONF_NAME]}"
            return self.async_create_entry(title=title, data=user_input)

        # Provide a form for the user to fill out
        data_schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_PRESENCE_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"])
            ),
            vol.Required(CONF_CONTROLLED_ENTITIES): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    multiple=True,
                    domain=['light', 'switch', 'input_boolean']
                )
            ),
            vol.Required(CONF_PRESENCE_TIMEOUT, default=300): int,
            vol.Required(CONF_ACTIVE_ROOM_THRESHOLD, default=15): int,
            vol.Required(CONF_ACTIVE_ROOM_TIMEOUT, default=600): int,
            vol.Required(CONF_NIGHT_MODE_START, default="22:00"): str,
            vol.Required(CONF_NIGHT_MODE_END, default="07:00"): str,
            vol.Required(CONF_NIGHT_MODE_TIMEOUT, default=60): int,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

class DynamicPresenceOptionsFlowHandler(OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        errors = {}
        if user_input is not None:
            # Validate and process user input here
            # If valid, update the config entry
            return self.async_create_entry(title="", data=user_input)

        options = {**self.config_entry.data, **self.config_entry.options}
        data_schema = vol.Schema({
            vol.Required(CONF_PRESENCE_SENSOR, default=options.get(CONF_PRESENCE_SENSOR)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["binary_sensor", "input_boolean"])
            ),
            vol.Required(CONF_CONTROLLED_ENTITIES, default=options.get(CONF_CONTROLLED_ENTITIES, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    multiple=True,
                    domain=['light', 'switch', 'input_boolean']
                )
            ),
            vol.Required(CONF_PRESENCE_TIMEOUT, default=options.get(CONF_PRESENCE_TIMEOUT, 300)): int,
            vol.Required(CONF_ACTIVE_ROOM_THRESHOLD, default=options.get(CONF_ACTIVE_ROOM_THRESHOLD, 15)): int,
            vol.Required(CONF_ACTIVE_ROOM_TIMEOUT, default=options.get(CONF_ACTIVE_ROOM_TIMEOUT, 600)): int,
            vol.Required(CONF_NIGHT_MODE_START, default=options.get(CONF_NIGHT_MODE_START, "22:00")): str,
            vol.Required(CONF_NIGHT_MODE_END, default=options.get(CONF_NIGHT_MODE_END, "07:00")): str,
            vol.Required(CONF_NIGHT_MODE_TIMEOUT, default=options.get(CONF_NIGHT_MODE_TIMEOUT, 60)): int,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
