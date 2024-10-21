"""Switch platform for Dynamic Presence integration."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ROOM_NAME, DOMAIN, SWITCH_KEYS
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence switch based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room").lower().replace(" ", "_")
    coordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        DynamicPresenceSwitch(
            coordinator, room_name, key, key.replace("_", " ").title()
        )
        for key in SWITCH_KEYS
    ]

    async_add_entities(switches)
    _LOGGER.debug(
        "Added %d Dynamic Presence switches for %s",
        len(switches),
        room_name,
    )


class DynamicPresenceSwitch(SwitchEntity):
    """Representation of a Dynamic Presence switch."""

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        room: str,
        key: str,
        name: str,
    ) -> None:
        """Initialize the Dynamic Presence switch."""
        super().__init__()
        self.coordinator = coordinator
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room}_{key}"
        self._attr_has_entity_name = True
        self._attr_name = name
        self.entity_id = f"switch.dynamic_presence_{room}_{key}"
        self._attr_device_info = coordinator.get_device_info(room)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get(self._key, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.coordinator.async_set_switch_value(self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.coordinator.async_set_switch_value(self._key, False)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class ManageOnClearSwitch(SwitchEntity):
    """Representation of a switch to manage entities on clear."""


class ManageOnPresenceSwitch(SwitchEntity):
    """Representation of a switch to manage entities on presence."""
