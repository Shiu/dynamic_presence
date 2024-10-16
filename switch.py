"""Switch platform for Dynamic Presence integration."""
import logging

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLE, CONF_NIGHT_MODE_ENABLE, DOMAIN
from .entity import DynamicPresenceEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence switches.

    This function is called when a new config entry is added to set up the switch entities
    for the Dynamic Presence integration.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for which to set up entities.
        async_add_entities: Callback to add new entities to Home Assistant.

    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DynamicPresenceSwitch(coordinator, entry),
        NightModeEnableSwitch(coordinator, entry)
    ])

class DynamicPresenceSwitch(DynamicPresenceEntity, SwitchEntity):
    """Representation of a Dynamic Presence switch.

    This switch enables or disables the entire Dynamic Presence integration.
    """

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the switch.

        Args:
            coordinator: The data update coordinator.
            entry: The config entry containing integration configuration.

        """
        super().__init__(coordinator, entry, SwitchEntityDescription(
            key=CONF_ENABLE,
            name=f"{entry.data.get('name', 'Dynamic Presence')} Enable",
            icon="mdi:power",
        ))

    @property
    def is_on(self) -> bool:
        """Return true if the Dynamic Presence integration is enabled."""
        return self.coordinator.is_enabled

    async def async_turn_on(self, **kwargs):
        """Enable the Dynamic Presence integration."""
        await self.coordinator.enable()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Disable the Dynamic Presence integration."""
        await self.coordinator.disable()
        self.async_write_ha_state()

class NightModeEnableSwitch(DynamicPresenceEntity, SwitchEntity):
    """Representation of a Night Mode Enable switch.

    This switch enables or disables the Night Mode feature of the Dynamic Presence integration.
    """

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the Night Mode Enable switch.

        Args:
            coordinator: The data update coordinator.
            entry: The config entry containing integration configuration.

        """
        super().__init__(coordinator, entry, SwitchEntityDescription(
            key=CONF_NIGHT_MODE_ENABLE,
            name="Night Mode Enable",
            icon="mdi:weather-night",
        ))

    @property
    def is_on(self) -> bool:
        """Return true if Night Mode is enabled."""
        return self.coordinator.is_night_mode_enabled

    async def async_turn_on(self, **kwargs):
        """Enable Night Mode."""
        await self.coordinator.enable_night_mode()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Disable Night Mode."""
        await self.coordinator.disable_night_mode()
        self.async_write_ha_state()
