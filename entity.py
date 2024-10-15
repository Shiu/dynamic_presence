"""Base entity for Dynamic Presence integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN, NAME, VERSION


class DynamicPresenceEntity(Entity):
    """Base class for Dynamic Presence entities."""

    _attr_has_entity_name = True

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the Dynamic Presence entity."""
        self.config_entry = config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer=NAME,
            model="Dynamic Presence Controller",
            sw_version=VERSION,
        )
        self._remove_listener = None

    def generate_entity_id(self, platform: str, entity_type: str) -> str:
        """Generate a consistent entity ID."""
        room_name = self.config_entry.title.lower().replace(' ', '_')
        return f"{platform}.{room_name}_{entity_type}"

    @property
    def should_poll(self) -> bool:
        """Return False as entity pushes its state to HA."""
        return False

    @property
    def device_info(self):
        """Return device information about this entity."""
        return self._attr_device_info

    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._remove_listener = self.config_entry.add_update_listener(self.async_config_entry_updated)

    async def async_will_remove_from_hass(self):
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        if self._remove_listener:
            self._remove_listener()

    async def async_config_entry_updated(self, hass, entry):
        """Handle config entry updates."""
        # Implement this method in child classes if needed
