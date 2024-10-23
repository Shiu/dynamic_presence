"""Switch platform for Dynamic Presence integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ROOM_NAME, DEFAULT_SWITCH_STATES, DOMAIN, SWITCH_KEYS
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


class DynamicPresenceSwitch(SwitchEntity):
    """Representation of a Dynamic Presence switch."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        room: str,
        switch_key: str,
        initial_state: bool,
    ) -> None:
        """Initialize the Dynamic Presence switch."""
        self.coordinator = coordinator
        self._room = room
        self._switch_key = switch_key
        self._attr_name = switch_key.replace("_", " ").title()
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room}_{switch_key}"
        self._attr_device_info = coordinator.get_device_info(room)
        self._attr_is_on = initial_state

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        state = self.coordinator.data.get(self._switch_key, False)
        _LOGGER.info("Switch %s state requested: %s", self._switch_key, state)
        return state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_update_entity_value(self._switch_key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_update_entity_value(self._switch_key, False)

    async def _async_update_switch_state(
        self, state: bool, update_options: bool = True
    ) -> None:
        """Update switch state and persist changes if needed."""
        if self.coordinator.data.get(self._switch_key) != state:
            self.coordinator.data[self._switch_key] = state
            self.coordinator.async_set_updated_data(self.coordinator.data)

            if update_options:
                # Update the config entry options
                entry = self.coordinator.entry
                new_options = dict(entry.options)
                new_options[self._switch_key] = state
                self.coordinator.hass.config_entries.async_update_entry(
                    entry, options=new_options
                )

            _LOGGER.info("Updated %s to %s", self._switch_key, state)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update_config(self, options: dict) -> None:
        """Update the entity's configuration."""
        new_state = options.get(self._switch_key)
        if self.is_on != new_state:
            await self._async_update_switch_state(new_state, update_options=False)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence switch based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for switch_key in SWITCH_KEYS:
        initial_state = entry.options.get(
            switch_key,
            coordinator.data.get(switch_key, DEFAULT_SWITCH_STATES[switch_key]),
        )
        _LOGGER.info(
            "Setting up switch %s with initial state: %s", switch_key, initial_state
        )
        entity = DynamicPresenceSwitch(
            coordinator,
            room_name,
            switch_key,
            initial_state,
        )
        entities.append(entity)
        _LOGGER.debug("Created switch entity: %s", entity.entity_id)

    async_add_entities(entities)
    _LOGGER.info(
        "Added %d Dynamic Presence switch entities for %s", len(entities), room_name
    )


class ManageOnClearSwitch(SwitchEntity):
    """Representation of a switch to manage entities on clear."""


class ManageOnPresenceSwitch(SwitchEntity):
    """Representation of a switch to manage entities on presence."""
