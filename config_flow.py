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
    CONF_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    CONF_PRESENCE_SENSOR,
    CONF_ROOM_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def validate_room_name(value):
    """Validate the room name."""
    if not isinstance(value, str):
        _LOGGER.error("Invalid room name: %s. Room name must be a string", value)
        raise vol.Invalid("Room name must be a string")
    stripped = value.strip()
    if not stripped:
        _LOGGER.error("Invalid room name: Empty string provided")
        raise vol.Invalid("Room name cannot be empty")
    _LOGGER.debug("Room name validated: %s", stripped)
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
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
        _LOGGER.debug("Initializing options flow for %s", config_entry.title)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {**self.config_entry.data, **self.config_entry.options}
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_PRESENCE_SENSOR, default=options.get(CONF_PRESENCE_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "device_tracker"]
                    )
                ),
                vol.Required(
                    CONF_CONTROLLED_ENTITIES,
                    default=options.get(CONF_CONTROLLED_ENTITIES, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light", "switch", "input_boolean"], multiple=True
                    )
                ),
                vol.Required(
                    CONF_NIGHT_MODE_ENABLE,
                    default=options.get(CONF_NIGHT_MODE_ENABLE, False),
                ): bool,
                vol.Optional(
                    CONF_NIGHT_MODE_START,
                    default=options.get(CONF_NIGHT_MODE_START, "22:00"),
                ): str,
                vol.Optional(
                    CONF_NIGHT_MODE_END,
                    default=options.get(CONF_NIGHT_MODE_END, "06:00"),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
