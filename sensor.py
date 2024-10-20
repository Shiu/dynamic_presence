"""Sensor platform for Dynamic Presence."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .entity import DynamicPresenceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Dynamic Presence sensor entities.

    This function is called when a new config entry is added. It creates and adds
    all the sensor entities for the Dynamic Presence integration.
    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.info("Setting up Dynamic Presence sensors for %s", coordinator.room_name)

    # Wait for the coordinator to complete its first update
    await coordinator.async_config_entry_first_refresh()

    sensors = [
        PresenceDurationSensor(coordinator, entry),
        AbsenceDurationSensor(coordinator, entry),
        ActiveRoomStatusSensor(coordinator, entry),
        PresenceSensorStateSensor(coordinator, entry),
        NightModeStatusSensor(coordinator, entry),
    ]

    async_add_entities(sensors)
    _LOGGER.debug(
        "Added %d Dynamic Presence sensors for %s", len(sensors), coordinator.room_name
    )


class DynamicPresenceSensor(DynamicPresenceEntity, SensorEntity):
    """Base class for Dynamic Presence sensors.

    This class extends DynamicPresenceEntity and SensorEntity to provide
    common functionality for all Dynamic Presence sensors.
    """

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, description)
        _LOGGER.debug(
            "Initialized %s sensor for %s", description.name, coordinator.room_name
        )


class PresenceDurationSensor(DynamicPresenceSensor):
    """Representation of a Presence Duration sensor."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the Presence Duration sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="presence_duration",
                name="Presence Duration",
                icon="mdi:timer",
                native_unit_of_measurement="seconds",
            ),
        )

    @property
    def native_value(self) -> int:
        """Return the current presence duration in seconds.

        Calculates the time difference between now and when presence was first detected.
        """
        if self.coordinator.presence_detected and self.coordinator.presence_start_time:
            duration = int(
                (
                    dt_util.utcnow() - self.coordinator.presence_start_time
                ).total_seconds()
            )
            _LOGGER.debug(
                "Presence duration for %s: %d seconds",
                self.coordinator.room_name,
                duration,
            )
            return duration
        return 0


class AbsenceDurationSensor(DynamicPresenceSensor):
    """Representation of an Absence Duration sensor."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the Absence Duration sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="absence_duration",
                name="Absence Duration",
                icon="mdi:timer-off",
                native_unit_of_measurement="seconds",
            ),
        )

    @property
    def native_value(self) -> int:
        """Return the current absence duration in seconds.

        Calculates the time difference between now and when presence was last detected.
        """
        if (
            not self.coordinator.presence_detected
            and self.coordinator.last_presence_end_time
        ):
            duration = int(
                (
                    dt_util.utcnow() - self.coordinator.last_presence_end_time
                ).total_seconds()
            )
            _LOGGER.debug(
                "Absence duration for %s: %d seconds",
                self.coordinator.room_name,
                duration,
            )
            return duration
        return 0


class ActiveRoomStatusSensor(DynamicPresenceSensor):
    """Representation of an Active Room Status sensor."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the Active Room Status sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="active_room_status",
                name="Active Room Status",
                icon="mdi:home-circle",
            ),
        )

    @property
    def native_value(self) -> str:
        """Return the current active room status.

        Returns "Active" if the room is currently active, "Inactive" otherwise.
        """
        status = "Active" if self.coordinator.is_active_room else "Inactive"
        _LOGGER.debug(
            "Active room status for %s: %s", self.coordinator.room_name, status
        )
        return status


class PresenceSensorStateSensor(DynamicPresenceSensor):
    """Representation of a Presence Sensor State sensor."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the Presence Sensor State sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="presence_sensor_state",
                name="Presence Sensor State",
                icon="mdi:motion-sensor",
            ),
        )

    @property
    def native_value(self) -> str:
        """Return the current state of the presence sensor.

        Returns "Detected" if presence is currently detected, "Clear" otherwise.
        """
        state = "Detected" if self.coordinator.presence_detected else "Clear"
        _LOGGER.debug(
            "Presence sensor state for %s: %s", self.coordinator.room_name, state
        )
        return state


class NightModeStatusSensor(DynamicPresenceSensor):
    """Representation of a Night Mode Status sensor."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the Night Mode Status sensor."""
        super().__init__(
            coordinator,
            entry,
            SensorEntityDescription(
                key="night_mode_status",
                name="Night Mode Status",
                icon="mdi:weather-night",
            ),
        )

    @property
    def native_value(self) -> str:
        """Return the current status of Night Mode."""
        if self.coordinator is None:
            _LOGGER.error("Coordinator is None for %s", self.entity_id)
            return "Unknown"
        try:
            status = "Active" if self.coordinator.is_night_mode_active() else "Inactive"
            _LOGGER.debug(
                "Night mode status for %s: %s", self.coordinator.room_name, status
            )
            return status
        except Exception:
            _LOGGER.exception("Error getting night mode status for %s", self.entity_id)
            return "Error"
