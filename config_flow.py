"""Config flow for Dynamic Presence integration."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
    ConfigEntryState,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)

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
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
    DEFAULT_NIGHT_MODE_END,
    NUMBER_CONFIG,
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
        errors = {}

        if user_input is not None:
            # Validate presence sensor
            if not await self._async_validate_presence_sensor(
                user_input[CONF_PRESENCE_SENSOR]
            ):
                errors[CONF_PRESENCE_SENSOR] = "invalid_presence_sensor"

            # Validate lights
            if not await self._async_validate_lights(user_input[CONF_LIGHTS]):
                errors[CONF_LIGHTS] = "invalid_lights"

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                    },
                    options={
                        CONF_PRESENCE_SENSOR: user_input[CONF_PRESENCE_SENSOR],
                        CONF_LIGHTS: user_input[CONF_LIGHTS],
                        CONF_NIGHT_LIGHTS: [],
                        CONF_DETECTION_TIMEOUT: NUMBER_CONFIG[CONF_DETECTION_TIMEOUT][
                            "default"
                        ],
                        CONF_LONG_TIMEOUT: NUMBER_CONFIG[CONF_LONG_TIMEOUT]["default"],
                        CONF_SHORT_TIMEOUT: NUMBER_CONFIG[CONF_SHORT_TIMEOUT][
                            "default"
                        ],
                        CONF_LIGHT_THRESHOLD: NUMBER_CONFIG[CONF_LIGHT_THRESHOLD][
                            "default"
                        ],
                        CONF_NIGHT_MODE_START: DEFAULT_NIGHT_MODE_START,
                        CONF_NIGHT_MODE_END: DEFAULT_NIGHT_MODE_END,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_PRESENCE_SENSOR): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=BINARY_SENSOR_DOMAIN,
                        )
                    ),
                    vol.Required(CONF_LIGHTS): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=LIGHT_DOMAIN,
                            multiple=True,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    def is_matching(self, other_flow: str) -> bool:
        """Test if a match entry is matching this flow."""
        return False  # We don't support matching in this integration

    async def _async_validate_presence_sensor(self, entity_id: str) -> bool:
        """Validate presence sensor entity and device class."""
        registry = async_get(self.hass)
        entity = registry.async_get(entity_id)

        if entity is None or entity.domain != BINARY_SENSOR_DOMAIN:
            return False

        # Get the entity state to check device class
        state = self.hass.states.get(entity_id)
        if state is None:
            return False

        device_class = state.attributes.get("device_class")
        valid_device_classes = [
            BinarySensorDeviceClass.MOTION,
            BinarySensorDeviceClass.OCCUPANCY,
            BinarySensorDeviceClass.PRESENCE,
        ]

        return device_class in valid_device_classes

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

    def _get_adjacent_room_options(self) -> list[selector.SelectOptionDict]:
        """Get list of available adjacent rooms."""
        return [
            selector.SelectOptionDict(value=entry.entry_id, label=entry.title)
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.entry_id != self.config_entry.entry_id
            and entry.state == ConfigEntryState.LOADED  # Only show active rooms
        ]

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            options = {
                CONF_PRESENCE_SENSOR: user_input[CONF_PRESENCE_SENSOR],
                CONF_LIGHTS: user_input[CONF_LIGHTS],
                CONF_NIGHT_LIGHTS: user_input[CONF_NIGHT_LIGHTS],
                CONF_ADJACENT_ROOMS: user_input.get(CONF_ADJACENT_ROOMS, []),
                CONF_DETECTION_TIMEOUT: user_input[CONF_DETECTION_TIMEOUT],
                CONF_LONG_TIMEOUT: user_input[CONF_LONG_TIMEOUT],
                CONF_SHORT_TIMEOUT: user_input[CONF_SHORT_TIMEOUT],
                CONF_LIGHT_THRESHOLD: user_input[CONF_LIGHT_THRESHOLD],
                CONF_NIGHT_MODE_START: user_input[CONF_NIGHT_MODE_START],
                CONF_NIGHT_MODE_END: user_input[CONF_NIGHT_MODE_END],
            }

            # Only add light sensor if it's actually selected and not None/empty
            light_sensor = user_input.get(CONF_LIGHT_SENSOR)
            if light_sensor:  # This will handle None, empty string, or empty list
                options[CONF_LIGHT_SENSOR] = light_sensor

            return self.async_create_entry(title="", data=options)

        schema = vol.Schema(
            {
                # Entity Selections - Group 1
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
                # Night Mode Settings - Group 2
                vol.Optional(
                    CONF_NIGHT_LIGHTS,
                    default=self.config_entry.options.get(CONF_NIGHT_LIGHTS, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=LIGHT_DOMAIN,
                        multiple=True,
                    )
                ),
                vol.Required(
                    CONF_NIGHT_MODE_START,
                    default=self.config_entry.options.get(
                        CONF_NIGHT_MODE_START, DEFAULT_NIGHT_MODE_START
                    ),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_NIGHT_MODE_END,
                    default=self.config_entry.options.get(
                        CONF_NIGHT_MODE_END, DEFAULT_NIGHT_MODE_END
                    ),
                ): selector.TimeSelector(),
                # Timeout Settings - Group 2
                vol.Required(
                    CONF_DETECTION_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_DETECTION_TIMEOUT,
                        NUMBER_CONFIG[CONF_DETECTION_TIMEOUT]["default"],
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=NUMBER_CONFIG[CONF_DETECTION_TIMEOUT]["min"],
                        max=NUMBER_CONFIG[CONF_DETECTION_TIMEOUT]["max"],
                        mode="box",
                        step=NUMBER_CONFIG[CONF_DETECTION_TIMEOUT]["step"],
                        unit_of_measurement=NUMBER_CONFIG[CONF_DETECTION_TIMEOUT][
                            "unit"
                        ],
                    )
                ),
                vol.Required(
                    CONF_LONG_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_LONG_TIMEOUT, NUMBER_CONFIG[CONF_LONG_TIMEOUT]["default"]
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=NUMBER_CONFIG[CONF_LONG_TIMEOUT]["min"],
                        max=NUMBER_CONFIG[CONF_LONG_TIMEOUT]["max"],
                        mode="box",
                        step=NUMBER_CONFIG[CONF_LONG_TIMEOUT]["step"],
                        unit_of_measurement=NUMBER_CONFIG[CONF_LONG_TIMEOUT]["unit"],
                    )
                ),
                vol.Required(
                    CONF_SHORT_TIMEOUT,
                    default=self.config_entry.options.get(
                        CONF_SHORT_TIMEOUT, NUMBER_CONFIG[CONF_SHORT_TIMEOUT]["default"]
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=NUMBER_CONFIG[CONF_SHORT_TIMEOUT]["min"],
                        max=NUMBER_CONFIG[CONF_SHORT_TIMEOUT]["max"],
                        mode="box",
                        step=NUMBER_CONFIG[CONF_SHORT_TIMEOUT]["step"],
                        unit_of_measurement=NUMBER_CONFIG[CONF_SHORT_TIMEOUT]["unit"],
                    )
                ),
                # Light Settings - Group 3
                vol.Optional(
                    CONF_LIGHT_SENSOR,
                    description={
                        "suggested_value": self.config_entry.options.get(
                            CONF_LIGHT_SENSOR
                        )
                    },
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=SENSOR_DOMAIN)
                ),
                vol.Optional(
                    CONF_LIGHT_THRESHOLD,
                    default=self.config_entry.options.get(
                        CONF_LIGHT_THRESHOLD,
                        NUMBER_CONFIG[CONF_LIGHT_THRESHOLD]["default"],
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=NUMBER_CONFIG[CONF_LIGHT_THRESHOLD]["min"],
                        max=NUMBER_CONFIG[CONF_LIGHT_THRESHOLD]["max"],
                        mode="box",
                        step=NUMBER_CONFIG[CONF_LIGHT_THRESHOLD]["step"],
                        unit_of_measurement=NUMBER_CONFIG[CONF_LIGHT_THRESHOLD]["unit"],
                    )
                ),
                # Room Settings - Group 4
                vol.Optional(
                    CONF_ADJACENT_ROOMS,
                    default=self.config_entry.options.get(CONF_ADJACENT_ROOMS, []),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._get_adjacent_room_options(),
                        multiple=True,
                        mode="dropdown",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
