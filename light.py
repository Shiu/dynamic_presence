"""Light platform for Dynamic Presence integration."""
from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DynamicPresenceEntity


class DynamicPresenceLight(DynamicPresenceEntity, LightEntity):
    """Representation of a Dynamic Presence light."""

    def __init__(self, config_entry: ConfigEntry, key: str, name: str) -> None:
        """Initialize the light entity."""
        super().__init__(config_entry)
        self._key = key
        self._attr_name = f"{config_entry.title} {name}"
        self._attr_unique_id = f"{config_entry.entry_id}_{key}"

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.hass.data[DOMAIN][self.config_entry.entry_id]["data"].get(self._key, False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        self.hass.data[DOMAIN][self.config_entry.entry_id]["data"][self._key] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        self.hass.data[DOMAIN][self.config_entry.entry_id]["data"][self._key] = False
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Dynamic Presence light entities."""
    # Add your light entities here
