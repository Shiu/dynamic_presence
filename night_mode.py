"""Night mode module for Dynamic Presence integration.

This module contains the NightMode class, which manages the night mode functionality.
It handles night mode time ranges, checks if night mode is currently active,
and provides methods to update night mode settings.
"""

from datetime import datetime, time
import logging

from homeassistant.core import HomeAssistant

from .const import (
    CONF_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_END,
    CONF_NIGHT_MODE_START,
    DEFAULT_NIGHT_MODE_END,
    DEFAULT_NIGHT_MODE_START,
)

_LOGGER = logging.getLogger(__name__)


class NightMode:
    """Manage night mode functionality for Dynamic Presence integration."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the NightMode instance.

        Args:
            hass: The Home Assistant instance.
            config_entry: The config entry containing the integration options.

        """
        self.hass = hass
        self.night_mode_enabled = config_entry.options.get(
            CONF_NIGHT_MODE_ENABLE, False
        )
        self.night_mode_start = self._parse_time(
            config_entry.options.get(CONF_NIGHT_MODE_START, DEFAULT_NIGHT_MODE_START)
        )
        self.night_mode_end = self._parse_time(
            config_entry.options.get(CONF_NIGHT_MODE_END, DEFAULT_NIGHT_MODE_END)
        )

    def _parse_time(self, time_str: str) -> time:
        hours, minutes = map(int, time_str.split(":"))
        return time(hour=hours, minute=minutes)

    def is_night_mode_active(self) -> bool:
        """Check if night mode is currently active."""
        if not self.night_mode_enabled:
            return False

        current_time = datetime.now().time()
        if self.night_mode_start <= self.night_mode_end:
            return self.night_mode_start <= current_time <= self.night_mode_end
        # Night mode spans midnight
        return (
            current_time >= self.night_mode_start or current_time <= self.night_mode_end
        )

    def update_night_mode_settings(self, enabled: bool, start: str, end: str):
        """Update night mode settings."""
        self.night_mode_enabled = enabled
        self.night_mode_start = self._parse_time(start)
        self.night_mode_end = self._parse_time(end)
