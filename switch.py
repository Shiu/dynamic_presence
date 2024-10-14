"""Switch platform for Dynamic Presence integration."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import DynamicPresenceEntity


class DynamicPresenceSwitch(DynamicPresenceEntity, SwitchEntity):
    """Representation of a Dynamic Presence switch."""

    def __init__(self, config_entry: ConfigEntry, key: str, name: str) -> None:
        """Initialize the switch entity."""
        super().__init__(config_entry)
        self._key = key
        self._attr_name = f"{name}"
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_{key}"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.hass.data[DOMAIN][self.config_entry.entry_id].get("data", {}).get(self._key, True)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self.hass.data[DOMAIN][self.config_entry.entry_id]["data"][self._key] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self.hass.data[DOMAIN][self.config_entry.entry_id]["data"][self._key] = False
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Dynamic Presence switch entities."""
    entities = [
        DynamicPresenceSwitch(entry, "enabled", "Enabled"),
        # Add any other switches you want to create here
    ]
    async_add_entities(entities)
