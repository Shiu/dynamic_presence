"""Config flow for Dynamic Presence integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get

from .const import (
    DOMAIN,
    CONF_PRESENCE_SENSOR,
    CONF_LIGHTS,
    CONF_NIGHT_LIGHTS,
    CONF_LIGHT_SENSOR,
    CONF_ADJACENT_ROOMS,
    CONF_DETECTION_TIMEOUT,
    CONF_LONG_TIMEOUT,
    CONF_SHORT_TIMEOUT,
    CONF_LIGHT_THRESHOLD,
    DEFAULT_DETECTION_TIMEOUT,
    DEFAULT_LONG_TIMEOUT,
    DEFAULT_SHORT_TIMEOUT,
    DEFAULT_LIGHT_THRESHOLD,
)


class DynamicPresenceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dynamic Presence."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DynamicPresenceOptionsFlow:
        """Get the options flow for this handler."""
        return DynamicPresenceOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={CONF_NAME: user_input[CONF_NAME]},
                options={
                    CONF_PRESENCE_SENSOR: None,
                    CONF_LIGHTS: [],
                    CONF_DETECTION_TIMEOUT: DEFAULT_DETECTION_TIMEOUT,
                    CONF_LONG_TIMEOUT: DEFAULT_LONG_TIMEOUT,
                    CONF_SHORT_TIMEOUT: DEFAULT_SHORT_TIMEOUT,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                }
            ),
        )

    def is_matching(self, other_flow: str) -> bool:
        """Test if a match entry is matching this flow."""
        return False  # We don't support matching in this integration

    async def _async_validate_presence_sensor(self, entity_id: str) -> bool:
        """Validate presence sensor entity."""
        registry = async_get(self.hass)
        entity = registry.async_get(entity_id)
        return entity is not None and entity.domain == BINARY_SENSOR_DOMAIN

    async def _async_validate_lights(self, entity_ids: list[str]) -> bool:
        """Validate light entities."""
        registry = async_get(self.hass)
        for entity_id in entity_ids:
            entity = registry.async_get(entity_id)
            if entity is None or entity.domain != LIGHT_DOMAIN:
                return False
        return True


class DynamicPresenceOptionsFlow(OptionsFlow):
    """Handle options flow for Dynamic Presence."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            # Only update options, core settings from data should stay in data
            options = {
                CONF_PRESENCE_SENSOR: user_input[CONF_PRESENCE_SENSOR],
                CONF_LIGHTS: user_input[CONF_LIGHTS],
                CONF_NIGHT_LIGHTS: user_input[CONF_NIGHT_LIGHTS],
                CONF_ADJACENT_ROOMS: user_input.get(CONF_ADJACENT_ROOMS, []),
                CONF_DETECTION_TIMEOUT: user_input[CONF_DETECTION_TIMEOUT],
                CONF_LONG_TIMEOUT: user_input[CONF_LONG_TIMEOUT],
                CONF_SHORT_TIMEOUT: user_input[CONF_SHORT_TIMEOUT],
                CONF_LIGHT_THRESHOLD: user_input[CONF_LIGHT_THRESHOLD],
            }

            # Handle optional light sensor
            if CONF_LIGHT_SENSOR in user_input:
                options[CONF_LIGHT_SENSOR] = user_input[CONF_LIGHT_SENSOR]

            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                # Required entity selectors
                vol.Required(
                    CONF_PRESENCE_SENSOR,
                    default=self.config_entry.options.get(CONF_PRESENCE_SENSOR),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)
                ),
                vol.Required(
                    CONF_LIGHTS,
                    default=self.config_entry.options.get(CONF_LIGHTS, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=LIGHT_DOMAIN,
                        multiple=True,
                    )
                ),
                # Configurable settings from options
                vol.Optional(
                    CONF_NIGHT_LIGHTS,
                    default=self.config_entry.options.get(CONF_NIGHT_LIGHTS, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=LIGHT_DOMAIN,
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_LIGHT_SENSOR,
                    description={
                        "suggested_value": self.config_entry.options.get(
                            CONF_LIGHT_SENSOR
                        )
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=SENSOR_DOMAIN, multiple=False)
                ),
                vol.Optional(
                    CONF_ADJACENT_ROOMS,
                    default=self.config_entry.options.get(CONF_ADJACENT_ROOMS, []),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=entry.entry_id, label=entry.title
                            )
                            for entry in self.hass.config_entries.async_entries(DOMAIN)
                            if entry.entry_id != self.config_entry.entry_id
                        ],
                        multiple=True,
                        mode="dropdown",
                    )
                ),
                vol.Required(
                    CONF_DETECTION_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_DETECTION_TIMEOUT, DEFAULT_DETECTION_TIMEOUT
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=30, mode="box", step=1)
                ),
                vol.Required(
                    CONF_LONG_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_LONG_TIMEOUT, DEFAULT_LONG_TIMEOUT
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                vol.Required(
                    CONF_SHORT_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_SHORT_TIMEOUT, DEFAULT_SHORT_TIMEOUT
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                # Optional light threshold
                vol.Optional(
                    CONF_LIGHT_THRESHOLD,
                    default=self.config_entry.options.get(
                        CONF_LIGHT_THRESHOLD, DEFAULT_LIGHT_THRESHOLD
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=1000)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
