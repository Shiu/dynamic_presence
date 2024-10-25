"""Switch platform for Dynamic Presence integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ROOM_NAME, DOMAIN, SWITCH_DEFAULT_STATES, SWITCH_KEYS
from .coordinator import DynamicPresenceCoordinator

logSwitch = logging.getLogger("dynamic_presence.switch")


class DynamicPresenceSwitch(SwitchEntity):
    """Representation of a Dynamic Presence switch."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        room: str,
        switch_key: str,
    ) -> None:
        """Initialize the Dynamic Presence switch."""
        self.coordinator = coordinator
        self._room = room
        self._switch_key = switch_key
        self._attr_name = switch_key.replace("_", " ").title()
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room}_{switch_key}"
        self._attr_device_info = coordinator.get_device_info(room)
        self._default_state = SWITCH_DEFAULT_STATES.get(switch_key, False)
        self._attr_is_on = coordinator.data.get(switch_key, self._default_state)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get(self._switch_key, self._default_state)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_update_switch_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_update_switch_state(False)

    async def _async_update_switch_state(self, state: bool) -> None:
        """Update switch state."""
        # Update coordinator data
        self.coordinator.data[self._switch_key] = state
        # Save to options for persistence
        await self.coordinator.async_save_options(self._switch_key, state)
        # Notify listeners of the update
        self.coordinator.async_set_updated_data(self.coordinator.data)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update_config(self, options: dict) -> None:
        """Update the entity's configuration."""
        if self._switch_key in options:
            self._attr_is_on = options[self._switch_key]
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence switch based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for switch_key in SWITCH_KEYS:
        default_state = SWITCH_DEFAULT_STATES.get(switch_key, False)

        if switch_key not in entry.options:
            coordinator.data[switch_key] = default_state
            logSwitch.debug(
                "Switch %s set to default state %s",
                switch_key,
                coordinator.data[switch_key],
            )
        else:
            coordinator.data[switch_key] = entry.options[switch_key]
            logSwitch.debug(
                "Switch %s set to option state %s -second",
                switch_key,
                coordinator.data[switch_key],
            )
        entity = DynamicPresenceSwitch(
            coordinator,
            room_name,
            switch_key,
        )
        entities.append(entity)

    async_add_entities(entities)


class ManageOnClearSwitch(SwitchEntity):
    """Representation of a switch to manage entities on clear."""


class ManageOnPresenceSwitch(SwitchEntity):
    """Representation of a switch to manage entities on presence."""
