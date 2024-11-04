"""Switch platform for Dynamic Presence integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_AUTOMATION,
    CONF_AUTO_ON,
    CONF_AUTO_OFF,
    CONF_NIGHT_MODE,
    CONF_NIGHT_MANUAL_ON,
)
from .coordinator import DynamicPresenceCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches from a config entry."""
    coordinator: DynamicPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        DynamicPresenceSwitch(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_{CONF_AUTOMATION}",
            key=CONF_AUTOMATION,
        ),
        DynamicPresenceSwitch(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_{CONF_AUTO_ON}",
            key=CONF_AUTO_ON,
        ),
        DynamicPresenceSwitch(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_{CONF_AUTO_OFF}",
            key=CONF_AUTO_OFF,
        ),
        DynamicPresenceSwitch(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_{CONF_NIGHT_MODE}",
            key=CONF_NIGHT_MODE,
        ),
        DynamicPresenceSwitch(
            coordinator=coordinator,
            unique_id=f"{entry.entry_id}_{CONF_NIGHT_MANUAL_ON}",
            key=CONF_NIGHT_MANUAL_ON,
        ),
    ]

    async_add_entities(entities)


class DynamicPresenceSwitch(
    CoordinatorEntity[DynamicPresenceCoordinator], SwitchEntity
):
    """Switch for Dynamic Presence."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: DynamicPresenceCoordinator,
        unique_id: str,
        key: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._attr_suggested_object_id = key
        self._attr_translation_key = key
        self._key = key
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(f"switch_{self._key}", False)

    def turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.hass.async_create_task(self.async_turn_on(**kwargs))

    def turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self.hass.async_create_task(self.async_turn_off(**kwargs))

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        await self.coordinator.async_switch_changed(self._key, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.coordinator.async_switch_changed(self._key, False)
