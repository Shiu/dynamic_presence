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
    CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
    CONF_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_ENTITIES_BEHAVIOR,
    CONF_NIGHT_MODE_SCALE,
    CONF_NIGHT_MODE_START,
    CONF_PRESENCE_SENSOR,
    CONF_ROOM_NAME,
    CONFIG_OPTIONS_ORDER,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_ENTITIES_BEHAVIOR,
    DEFAULT_NIGHT_MODE_START,
    DOMAIN,
    NIGHT_MODE_BEHAVIOR_ADDITIVE,
    NIGHT_MODE_BEHAVIOR_EXCLUSIVE,
    NUMBER_CONFIG,
)

_LOGGER = logging.getLogger(__name__)


def validate_room_name(value):
    """Validate the room name."""
    if not isinstance(value, str):
        _LOGGER.error("Invalid room name: %s. Room name must be a string.", value)
        raise vol.Invalid("Room name must be a string")
    stripped = value.strip()
    if not stripped:
        _LOGGER.error("Invalid room name: Empty string provided.")
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
        """Handle the initial step.

        This method is called when a user initiates the integration setup.
        It defines the initial configuration options and processes user input.
        """
        if user_input is not None:
            _LOGGER.info("Processing user input for Dynamic Presence setup")
            _LOGGER.debug("User input: %s", user_input)

            user_input[CONF_NIGHT_MODE_START] = user_input.get(
                CONF_NIGHT_MODE_START, DEFAULT_NIGHT_MODE_START
            )
            user_input[CONF_NIGHT_MODE_END] = user_input.get(
                CONF_NIGHT_MODE_END, DEFAULT_NIGHT_MODE_END
            )
            if not user_input.get(CONF_CONTROLLED_ENTITIES):
                _LOGGER.warning(
                    "Dynamic Presence configured without any controlled entities for room %s",
                    user_input[CONF_ROOM_NAME],
                )

            _LOGGER.info(
                "Creating entry for Dynamic Presence: %s", user_input[CONF_ROOM_NAME]
            )
            return self.async_create_entry(
                title=f"Dynamic Presence {user_input[CONF_ROOM_NAME]}", data=user_input
            )

        _LOGGER.debug("Showing initial configuration form for Dynamic Presence")
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ROOM_NAME): validate_room_name,
                vol.Required(CONF_PRESENCE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "input_boolean"]
                    )
                ),
                vol.Required(CONF_CONTROLLED_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        multiple=True, domain=["light", "switch", "input_boolean"]
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    def is_matching(self, other_flow: ConfigFlow) -> bool:
        """Check if the config entry matches the other flow."""
        _LOGGER.debug("Checking if config entry matches other flow")
        return False


class DynamicPresenceOptionsFlowHandler(OptionsFlow):
    """Handle options for the Dynamic Presence integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        _LOGGER.debug("Initializing options flow for %s", config_entry.title)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options.

        This method is called when a user accesses the integration options.
        It defines all configurable options and processes user input.
        """
        if user_input is not None:
            _LOGGER.info("Processing options update for %s", self.config_entry.title)
            _LOGGER.debug("New options: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        options = {**self.config_entry.data, **self.config_entry.options}
        _LOGGER.debug("Current options: %s", options)

        data_schema = vol.Schema(
            {
                # Presence sensor selection
                vol.Required(
                    CONF_PRESENCE_SENSOR, default=options.get(CONF_PRESENCE_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "input_boolean"]
                    )
                ),
                # Controlled entities selection
                vol.Required(
                    CONF_CONTROLLED_ENTITIES,
                    default=options.get(CONF_CONTROLLED_ENTITIES, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        multiple=True, domain=["light", "switch", "input_boolean"]
                    )
                ),
                # Night mode enable/disable
                vol.Required(
                    CONF_NIGHT_MODE_ENABLE,
                    default=options.get(CONF_NIGHT_MODE_ENABLE, False),
                ): bool,
                # Night mode controlled entities
                vol.Optional(
                    CONF_NIGHT_MODE_CONTROLLED_ENTITIES,
                    default=options.get(CONF_NIGHT_MODE_CONTROLLED_ENTITIES, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        multiple=True, domain=["light", "switch", "input_boolean"]
                    )
                ),
                # Night mode entities behavior
                vol.Optional(
                    CONF_NIGHT_MODE_ENTITIES_BEHAVIOR,
                    default=options.get(
                        CONF_NIGHT_MODE_ENTITIES_BEHAVIOR,
                        DEFAULT_NIGHT_MODE_ENTITIES_BEHAVIOR,
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            NIGHT_MODE_BEHAVIOR_ADDITIVE,
                            NIGHT_MODE_BEHAVIOR_EXCLUSIVE,
                        ],
                        mode="dropdown",
                    )
                ),
                # Night mode scale factor
                vol.Optional(
                    CONF_NIGHT_MODE_SCALE,
                    default=options.get(
                        CONF_NIGHT_MODE_SCALE,
                        NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["default"],
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["min"],
                        max=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["max"],
                        step=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE]["step"],
                        mode="slider",
                        unit_of_measurement=NUMBER_CONFIG[CONF_NIGHT_MODE_SCALE][
                            "unit"
                        ],
                    )
                ),
                # Dynamic generation of number config options
                **{
                    vol.Required(
                        key,
                        default=options.get(
                            key,
                            NUMBER_CONFIG[key]["default"]
                            if key in NUMBER_CONFIG
                            else DEFAULT_NIGHT_MODE_START
                            if key == CONF_NIGHT_MODE_START
                            else DEFAULT_NIGHT_MODE_END,
                        ),
                    ): (
                        selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=NUMBER_CONFIG[key]["min"],
                                max=NUMBER_CONFIG[key]["max"],
                                step=NUMBER_CONFIG[key]["step"],
                                mode="box",
                                unit_of_measurement=NUMBER_CONFIG[key]["unit"],
                            )
                        )
                        if key in NUMBER_CONFIG
                        else selector.TimeSelector()
                        if key in [CONF_NIGHT_MODE_START, CONF_NIGHT_MODE_END]
                        else str
                    )
                    for key in CONFIG_OPTIONS_ORDER
                },
            }
        )

        _LOGGER.debug("Showing options form for %s", self.config_entry.title)
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
