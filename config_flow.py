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
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CONTROLLED_ENTITIES,
    CONF_LIGHT_SENSOR,
    CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
    CONF_NIGHT_MODE_ENTITIES_ADDMODE,
    CONF_PRESENCE_SENSOR,
    CONF_ROOM_NAME,
    DOMAIN,
    NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE,
    NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE,
)

logConfigFlow = logging.getLogger("dynamic_presence.config_flow")


def validate_room_name(value):
    """Validate the room name."""
    if not isinstance(value, str):
        raise vol.Invalid("Room name must be a string")
    stripped = value.strip()
    if not stripped:
        raise vol.Invalid("Room name cannot be empty")
    return stripped


class DynamicPresenceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dynamic Presence."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> DynamicPresenceOptionsFlowHandler:
        """Get the options flow for this handler."""
        return DynamicPresenceOptionsFlowHandler(config_entry)

    def is_matching(self, other_flow: dict) -> bool:
        """Return True if other_flow matches this flow."""
        return False  # We don't use discovery, so always return False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                user_input[CONF_ROOM_NAME] = validate_room_name(
                    user_input[CONF_ROOM_NAME]
                )
                return self.async_create_entry(
                    title=f"Dynamic Presence {user_input[CONF_ROOM_NAME]}",
                    data=user_input,
                )
            except vol.Invalid:
                errors["base"] = "invalid_room_name"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ROOM_NAME): str,
                vol.Required(CONF_PRESENCE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "device_tracker"]
                    )
                ),
                vol.Required(CONF_CONTROLLED_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light", "switch", "input_boolean"], multiple=True
                    )
                ),
                vol.Optional(
                    CONF_NIGHT_MODE_CONTROLLED_ENTITIES
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light", "switch", "input_boolean"], multiple=True
                    )
                ),
                vol.Optional(
                    CONF_NIGHT_MODE_ENTITIES_ADDMODE,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE,
                            NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE,
                        ]
                    )
                ),
                vol.Optional(CONF_LIGHT_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class DynamicPresenceOptionsFlowHandler(OptionsFlow):
    """Handle options for the Dynamic Presence integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        logConfigFlow.debug("Initializing options flow for %s", config_entry.title)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get values from data if not in options
        schema_dict = {
            vol.Required(
                CONF_PRESENCE_SENSOR,
                default=self.config_entry.options.get(
                    CONF_PRESENCE_SENSOR,
                    self.config_entry.data.get(CONF_PRESENCE_SENSOR),
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "device_tracker"]
                )
            ),
            vol.Required(
                CONF_CONTROLLED_ENTITIES,
                default=self.config_entry.options.get(
                    CONF_CONTROLLED_ENTITIES,
                    self.config_entry.data.get(CONF_CONTROLLED_ENTITIES),
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["light", "switch", "input_boolean"], multiple=True
                )
            ),
            vol.Optional(
                CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
                default=self.config_entry.options.get(
                    CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
                    self.config_entry.data.get(CONF_NIGHT_MODE_CONTROLLED_ENTITIES),
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["light", "switch", "input_boolean"], multiple=True
                )
            ),
            vol.Optional(
                CONF_NIGHT_MODE_ENTITIES_ADDMODE,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE,
                        NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE,
                    ]
                )
            ),
            vol.Optional(
                CONF_LIGHT_SENSOR,
                default=self.config_entry.options.get(
                    CONF_LIGHT_SENSOR, self.config_entry.data.get(CONF_LIGHT_SENSOR)
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"])
            ),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))
