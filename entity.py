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

    @property
    def should_poll(self) -> bool:
        """Return False as entity pushes its state to HA."""
        return False
