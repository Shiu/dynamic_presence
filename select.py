"""Select entities for Dynamic Presence."""

# pylint: disable=W0223  # Method 'set_native_value' is abstract
# pylint: disable=W0239  # Method 'set_value' overrides final
# type: ignore[shadow-stdlib]

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NIGHT_MODE_ENTITIES_ADDMODE,
    CONF_ROOM_NAME,
    DOMAIN,
    NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE,
    NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE,
)
from .coordinator import DynamicPresenceCoordinator


class NightModeAddModeSelect(SelectEntity):
    """Select entity for Night Mode Entities Add Mode."""

    _attr_has_entity_name = True
    _attr_options = [
        NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE,
        NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE,
    ]

    def __init__(self, coordinator: DynamicPresenceCoordinator, room_name: str) -> None:
        """Initialize the select entity."""
        super().__init__()
        self.coordinator = coordinator
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_{room_name}_night_mode_entities_addmode"
        )
        self._attr_name = "Night Mode Entities Add Mode"
        self._attr_entity_id = (
            f"select.dynamic_presence_{room_name}_night_mode_entities_addmode"
        )
        self._attr_device_info = coordinator.get_device_info(room_name)

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        return self.coordinator.data.get(CONF_NIGHT_MODE_ENTITIES_ADDMODE)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_save_options(
            CONF_NIGHT_MODE_ENTITIES_ADDMODE, option
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dynamic Presence select based on a config entry."""
    coordinator: DynamicPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]
    room_name = entry.data.get(CONF_ROOM_NAME, "Unknown Room")

    async_add_entities(
        [
            NightModeAddModeSelect(coordinator, room_name),
        ]
    )
