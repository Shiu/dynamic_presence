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
    CONF_CONTROLLED_ENTITIES,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_PRESENCE_SENSOR,
    CONFIG_OPTIONS_ORDER,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
    DOMAIN,
    NUMBER_CONFIG,
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
            **{vol.Required(key, default=NUMBER_CONFIG[key]["default"] if key in NUMBER_CONFIG else
                                         DEFAULT_NIGHT_MODE_START if key == CONF_NIGHT_MODE_START else
                                         DEFAULT_NIGHT_MODE_END):
               (selector.NumberSelector(
                   selector.NumberSelectorConfig(
                       min=NUMBER_CONFIG[key]["min"],
                       max=NUMBER_CONFIG[key]["max"],
                       step=NUMBER_CONFIG[key]["step"],
                       mode="box",
                       unit_of_measurement=NUMBER_CONFIG[key]["unit"]
                   )
               ) if key in NUMBER_CONFIG else
                selector.TimeSelector() if key in [CONF_NIGHT_MODE_START, CONF_NIGHT_MODE_END] else
                str)
               for key in CONFIG_OPTIONS_ORDER}
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
        if user_input is not None:
            # Update both data and options
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
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
            **{vol.Required(key, default=options.get(key, NUMBER_CONFIG[key]["default"] if key in NUMBER_CONFIG else
                                                          DEFAULT_NIGHT_MODE_START if key == CONF_NIGHT_MODE_START else
                                                          DEFAULT_NIGHT_MODE_END)):
               int if key in NUMBER_CONFIG else str
               for key in CONFIG_OPTIONS_ORDER}
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors={},
        )
