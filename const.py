"""Constants for the Dynamic Presence integration."""
from homeassistant.const import UnitOfTime

DOMAIN = "dynamic_presence"
NAME = "Dynamic Presence"
VERSION = "0.2.0"

CONF_PRESENCE_SENSOR = "presence_sensor"
CONF_CONTROLLED_ENTITIES = "controlled_entities"
CONF_PRESENCE_TIMEOUT = "presence_timeout"
CONF_ACTIVE_ROOM_TIMEOUT = "active_room_timeout"
CONF_ACTIVE_ROOM_THRESHOLD = "active_room_threshold"
CONF_NIGHT_MODE_TIMEOUT = "night_mode_timeout"
CONF_NIGHT_MODE_START = "night_mode_start"
CONF_NIGHT_MODE_END = "night_mode_end"
CONF_ENABLE = "enable"  # Instead of CONF_SWITCH

# Configuration for number entities with default values
NUMBER_CONFIG = {
    CONF_PRESENCE_TIMEOUT: {
        "name": "Presence Timeout",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 300
    },
    CONF_ACTIVE_ROOM_TIMEOUT: {
        "name": "Active Room Timeout",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 600
    },
    CONF_ACTIVE_ROOM_THRESHOLD: {
        "name": "Active Room Threshold",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 900
    },
    CONF_NIGHT_MODE_TIMEOUT: {
        "name": "Night Mode Timeout",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 60
    }
}

# Default values for time settings
DEFAULT_NIGHT_MODE_START = "23:00"
DEFAULT_NIGHT_MODE_END = "07:00"

# Define the order of configuration options
CONFIG_OPTIONS_ORDER = [
    CONF_PRESENCE_TIMEOUT,
    CONF_ACTIVE_ROOM_TIMEOUT,
    CONF_ACTIVE_ROOM_THRESHOLD,
    CONF_NIGHT_MODE_TIMEOUT,
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_END,
]
