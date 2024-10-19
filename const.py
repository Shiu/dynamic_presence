"""Constants for the Dynamic Presence integration."""

import logging
from homeassistant.const import UnitOfTime

_LOGGER = logging.getLogger(__name__)

# Basic integration information
DOMAIN = "dynamic_presence"
NAME = "Dynamic Presence"
VERSION = "0.3.0"  # Updated version number

# Configuration keys
CONF_ROOM_NAME = "room_name"
CONF_PRESENCE_SENSOR = "presence_sensor"
CONF_CONTROLLED_ENTITIES = "controlled_entities"
CONF_PRESENCE_TIMEOUT = "presence_timeout"
CONF_ACTIVE_ROOM_TIMEOUT = "active_room_timeout"
CONF_ACTIVE_ROOM_THRESHOLD = "active_room_threshold"
CONF_NIGHT_MODE_TIMEOUT = "night_mode_timeout"
CONF_NIGHT_MODE_START = "night_mode_start"
CONF_NIGHT_MODE_END = "night_mode_end"
CONF_ENABLE = "enable"  # Used to enable/disable the entire Dynamic Presence integration

# New constants for night mode features
CONF_NIGHT_MODE_ENABLE = "night_mode_enable"
CONF_NIGHT_MODE_CONTROLLED_ENTITIES = "night_mode_controlled_entities"
CONF_NIGHT_MODE_ENTITIES_BEHAVIOR = "night_mode_entities_behavior"
CONF_NIGHT_MODE_SCALE = "night_mode_scale"

# Configuration for number entities with default values
NUMBER_CONFIG = {
    CONF_PRESENCE_TIMEOUT: {
        "name": "Presence Timeout",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 300,
    },
    CONF_ACTIVE_ROOM_TIMEOUT: {
        "name": "Active Room Timeout",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 600,
    },
    CONF_ACTIVE_ROOM_THRESHOLD: {
        "name": "Active Room Threshold",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 900,
    },
    CONF_NIGHT_MODE_TIMEOUT: {
        "name": "Night Mode Timeout",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": UnitOfTime.SECONDS,
        "default": 60,
    },
    CONF_NIGHT_MODE_SCALE: {  # Configuration for night mode scale
        "name": "Night Mode Scale",
        "min": 0.1,
        "max": 2,
        "step": 0.1,
        "unit": None,
        "default": 0.5,
    },
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
    CONF_NIGHT_MODE_SCALE,
    CONF_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_ENTITIES_BEHAVIOR,
]

# Night mode entities behavior options
NIGHT_MODE_BEHAVIOR_ADDITIVE = (
    "additive"  # Night mode entities are added to normal mode entities
)
NIGHT_MODE_BEHAVIOR_EXCLUSIVE = (
    "exclusive"  # Only night mode entities are used during night mode
)

# Default night mode entities behavior
DEFAULT_NIGHT_MODE_ENTITIES_BEHAVIOR = NIGHT_MODE_BEHAVIOR_EXCLUSIVE

_LOGGER.debug("Dynamic Presence constants loaded. Version: %s", VERSION)
