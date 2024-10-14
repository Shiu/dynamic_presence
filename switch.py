"""Switch platform for Dynamic Presence integration."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .controller import DynamicPresenceController
from .entity import DynamicPresenceEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence switch."""
    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    async_add_entities([DynamicPresenceSwitch(entry, controller)])

class DynamicPresenceSwitch(DynamicPresenceEntity, SwitchEntity):
    """Representation of a Dynamic Presence switch."""

    def __init__(self, entry: ConfigEntry, controller: DynamicPresenceController):
        """Initialize the switch."""
        super().__init__(entry)
        self._controller = controller
        self._attr_name = "Dynamic Presence"
        self._attr_unique_id = f"{entry.entry_id}_dynamic_presence"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._controller.is_enabled

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._controller.enable()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._controller.disable()
        self.async_write_ha_state()
