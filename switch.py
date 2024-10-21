"""Switch platform for Dynamic Presence integration."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DISABLE_ON_CLEAR,
    CONF_ENABLE,
    CONF_ENABLE_ON_PRESENCE,
    CONF_NIGHT_MODE_ENABLE,
    CONF_ROOM_NAME,
    DOMAIN,
)
from .coordinator import DynamicPresenceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Dynamic Presence switch based on a config entry."""
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")
    _LOGGER.info("Setting up Dynamic Presence switches for %s", room_name)

    coordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        DynamicPresenceSwitch(coordinator, CONF_ENABLE, "Enable/Disable"),
        DynamicPresenceSwitch(coordinator, CONF_NIGHT_MODE_ENABLE, "Night Mode Enable"),
        DynamicPresenceSwitch(
            coordinator, CONF_ENABLE_ON_PRESENCE, "Enable on Presence"
        ),
        DynamicPresenceSwitch(coordinator, CONF_DISABLE_ON_CLEAR, "Disable on Clear"),
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
        self, coordinator: DynamicPresenceCoordinator, key: str, name: str
    ) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._key = key
        self._attr_name = f"Dynamic Presence {name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.entry.entry_id)},
            "name": f"Dynamic Presence {coordinator.entry.data.get(CONF_ROOM_NAME, 'Unknown Room')}",
            "manufacturer": "Custom",
            "model": "Dynamic Presence",
        }

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get(self._key, False)

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.coordinator.async_update_switch(self._key, True)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.coordinator.async_update_switch(self._key, False)
