"""Storage collection for Dynamic Presence integration."""

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import storage
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION

logStorage = logging.getLogger(__name__)

# Data type constants
RUNTIME_PREFIXES = ["switch_", "binary_sensor_", "sensor_"]
CONFIG_PREFIXES = ["number_", "time_"]


@dataclass
class DynamicPresenceStorageData:
    """Dynamic Presence storage data."""

    states: dict[str, Any]
    manual_states: dict[str, bool]


class DynamicPresenceStorage:
    """Class to hold Dynamic Presence storage data."""

    # 1. Core Initialization
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the storage."""
        self.hass = hass
        self.entry_id = entry_id
        self.storage: Store = storage.Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}",
            private=True,
            atomic_writes=True,
        )
        self._data: DynamicPresenceStorageData | None = None

    @property
    def data(self) -> DynamicPresenceStorageData:
        """Get the storage data."""
        if self._data is None:
            raise RuntimeError("Storage data not loaded. Call async_load first.")
        return self._data

    # 2. State Type Validation
    def is_runtime_state(self, key: str) -> bool:
        """Check if key represents a runtime state."""
        return any(key.startswith(prefix) for prefix in RUNTIME_PREFIXES)

    def is_config_value(self, key: str) -> bool:
        """Check if key represents a configuration value."""
        return any(key.startswith(prefix) for prefix in CONFIG_PREFIXES)

    # 3. Data Access
    def get_config_value(self, key: str) -> Any:
        """Get a configuration value.

        Raises:
            ValueError: If key is not a configuration value
        """
        if not self.is_config_value(key):
            raise ValueError(f"Key {key} is not a configuration value")
        return self.data.states.get(key)

    def get_state(self, key: str) -> Any:
        """Get a state value from storage."""
        return self.data.states.get(key)

    def get_manual_state(self, entity_id: str) -> bool:
        """Get a manual state from storage."""
        return self.data.manual_states.get(entity_id, False)

    # 4. Data Modification
    def set_runtime_state(self, key: str, value: Any) -> None:
        """Set a runtime state value.

        Raises:
            ValueError: If key is not a runtime state
        """
        if not self.is_runtime_state(key):
            raise ValueError(f"Key {key} is not a runtime state")
        logStorage.debug("Setting runtime state %s = %s", key, value)
        self.data.states[key] = value

    def set_state(self, key: str, value: Any) -> None:
        """Set a state value in storage.

        Raises:
            ValueError: If key is not a valid state type
        """
        if not (self.is_runtime_state(key) or self.is_config_value(key)):
            raise ValueError(f"Invalid state key: {key}")
        logStorage.debug("Setting state %s = %s", key, value)
        self.data.states[key] = value

    def set_manual_state(self, entity_id: str, value: bool) -> None:
        """Set a manual state in storage."""
        logStorage.debug("Setting manual state %s = %s", entity_id, value)
        self.data.manual_states[entity_id] = value

    # 5. Storage Operations
    async def async_load(self) -> dict | None:
        """Load the storage data."""
        stored = await self.storage.async_load()

        # Extract data with defaults if storage is empty or incomplete
        if stored is None:
            stored = {}

        states = stored.get("states", {})
        manual_states = stored.get("manual_states", {"main": {}, "night": {}})

        self._data = DynamicPresenceStorageData(
            states=states, manual_states=manual_states
        )

        logStorage.debug("Loaded storage data for %s: %s", self.entry_id, self._data)

        return manual_states

    async def async_save(self) -> None:
        """Save data to storage."""
        if self._data is None:
            return

        await self.storage.async_save(
            {"states": self._data.states, "manual_states": self._data.manual_states}
        )

        logStorage.debug("Saved storage data for %s: %s", self.entry_id, self._data)
