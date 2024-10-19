"""Switch platform for Dynamic Presence integration."""

import logging

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLE, CONF_NIGHT_MODE_ENABLE, DOMAIN
from .entity import DynamicPresenceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Dynamic Presence switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info("Setting up Dynamic Presence switches for %s", coordinator.room_name)

    switches = [
        DynamicPresenceSwitch(coordinator, entry),
        NightModeEnableSwitch(coordinator, entry),
    ]

    async_add_entities(switches)
    _LOGGER.debug(
        "Added %d Dynamic Presence switches for %s",
        len(switches),
        coordinator.room_name,
    )


class DynamicPresenceSwitch(DynamicPresenceEntity, SwitchEntity):
    """Representation of a Dynamic Presence switch."""

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the switch."""
        super().__init__(
            coordinator,
            entry,
            SwitchEntityDescription(
                key=CONF_ENABLE,
                name=f"{entry.data.get('name', 'Dynamic Presence')} Enable",
                icon="mdi:power",
            ),
        )
        _LOGGER.debug(
            "Initialized Dynamic Presence switch for %s", coordinator.room_name
        )

    @property
    def is_on(self) -> bool:
        """Return true if the Dynamic Presence integration is enabled."""
        state = self.coordinator.is_enabled
        _LOGGER.debug(
            "Dynamic Presence state for %s: %s",
            self.coordinator.room_name,
            "Enabled" if state else "Disabled",
        )
        return state

    async def async_turn_on(self, **kwargs):
        """Enable the Dynamic Presence integration."""
        _LOGGER.info("Enabling Dynamic Presence for %s", self.coordinator.room_name)
        await self.coordinator.enable()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Disable the Dynamic Presence integration."""
        _LOGGER.info("Disabling Dynamic Presence for %s", self.coordinator.room_name)
        await self.coordinator.disable()
        self.async_write_ha_state()


class NightModeEnableSwitch(DynamicPresenceEntity, SwitchEntity):
    """Representation of a Night Mode Enable switch.

    This switch enables or disables the Night Mode feature of the Dynamic Presence integration.
    """

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the Night Mode Enable switch."""
        super().__init__(
            coordinator,
            entry,
            SwitchEntityDescription(
                key=CONF_NIGHT_MODE_ENABLE,
                name="Night Mode Enable",
                icon="mdi:weather-night",
            ),
        )
        _LOGGER.debug("Initialized Night Mode switch for %s", coordinator.room_name)

    @property
    def is_on(self) -> bool:
        """Return true if Night Mode is enabled."""
        state = self.coordinator.is_night_mode_enabled
        _LOGGER.debug(
            "Night Mode state for %s: %s",
            self.coordinator.room_name,
            "Enabled" if state else "Disabled",
        )
        return state

    async def async_turn_on(self, **kwargs):
        """Enable Night Mode."""
        _LOGGER.info("Enabling Night Mode for %s", self.coordinator.room_name)
        await self.coordinator.enable_night_mode()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Disable Night Mode."""
        _LOGGER.info("Disabling Night Mode for %s", self.coordinator.room_name)
        await self.coordinator.disable_night_mode()
        self.async_write_ha_state()
