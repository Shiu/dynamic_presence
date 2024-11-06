"""Constants for the Dynamic Presence integration."""

from typing import Final

DOMAIN: Final = "dynamic_presence"

# Configuration keys
CONF_ROOM_NAME = "room_name"
CONF_PRESENCE_SENSOR = "presence_sensor"
CONF_LIGHT_SENSOR = "light_sensor"
CONF_LIGHTS = "lights"
CONF_NIGHT_LIGHTS = "night_lights"
CONF_ADJACENT_ROOMS = "adjacent_rooms"

# Timeout configuration
CONF_DETECTION_TIMEOUT = "detection_timeout"
CONF_LONG_TIMEOUT = "long_timeout"
CONF_SHORT_TIMEOUT = "short_timeout"
CONF_LIGHT_THRESHOLD = "light_threshold"
CONF_NIGHT_MODE_START = "night_mode_start"
CONF_NIGHT_MODE_END = "night_mode_end"

# Switch configuration
CONF_AUTOMATION = "automation"
CONF_AUTO_ON = "auto_on"
CONF_AUTO_OFF = "auto_off"
CONF_NIGHT_MODE = "night_mode"
CONF_NIGHT_MANUAL_ON = "night_manual_on"

# Default values
DEFAULT_DETECTION_TIMEOUT = 5  # seconds
DEFAULT_LONG_TIMEOUT = 120  # 30 seconds
DEFAULT_SHORT_TIMEOUT = 20  # 5 seconds
DEFAULT_LIGHT_THRESHOLD = 100  # lux
DEFAULT_NIGHT_MODE_START = "23:00:00"
DEFAULT_NIGHT_MODE_END = "08:00:00"

# Default sensor values
DEFAULT_SENSOR_OCCUPANCY_DURATION = 0
DEFAULT_SENSOR_ABSENCE_DURATION = 0
DEFAULT_SENSOR_LIGHT_LEVEL = 0
DEFAULT_BINARY_SENSOR_OCCUPANCY = False

# Default switch states
DEFAULT_SWITCH_AUTOMATION = True
DEFAULT_SWITCH_AUTO_ON = True
DEFAULT_SWITCH_AUTO_OFF = True
DEFAULT_SWITCH_NIGHT_MODE = True
DEFAULT_SWITCH_NIGHT_MANUAL_ON = False

# State constants
STATE_OCCUPIED = "occupied"
STATE_VACANT = "vacant"
STATE_DETECTION_TIMEOUT = "detection_timeout"
STATE_COUNTDOWN = "countdown"

# Entity configuration
NUMBER_CONFIG = {
    CONF_DETECTION_TIMEOUT: {
        "name": "Detection Timeout",
        "min": 1,
        "max": 120,
        "step": 1,
        "unit": "seconds",
        "default": DEFAULT_DETECTION_TIMEOUT,
    },
    CONF_LONG_TIMEOUT: {
        "name": "Long Timeout",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "seconds",
        "default": DEFAULT_LONG_TIMEOUT,
    },
    CONF_SHORT_TIMEOUT: {
        "name": "Short Timeout",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "seconds",
        "default": DEFAULT_SHORT_TIMEOUT,
    },
    CONF_LIGHT_THRESHOLD: {
        "name": "Light Level Threshold",
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": "lx",
        "default": DEFAULT_LIGHT_THRESHOLD,
    },
}

# Switch configuration with defaults
SWITCH_CONFIG = {
    CONF_AUTOMATION: DEFAULT_SWITCH_AUTOMATION,
    CONF_AUTO_ON: DEFAULT_SWITCH_AUTO_ON,
    CONF_AUTO_OFF: DEFAULT_SWITCH_AUTO_OFF,
    CONF_NIGHT_MODE: DEFAULT_SWITCH_NIGHT_MODE,
    CONF_NIGHT_MANUAL_ON: DEFAULT_SWITCH_NIGHT_MANUAL_ON,
}

# Entity keys
SWITCH_KEYS = [
    CONF_AUTOMATION,
    CONF_AUTO_ON,
    CONF_AUTO_OFF,
    CONF_NIGHT_MODE,
    CONF_NIGHT_MANUAL_ON,
]

TIME_KEYS = [
    CONF_NIGHT_MODE_START,
    CONF_NIGHT_MODE_END,
]

SENSOR_KEYS = [
    "occupancy_state",
    "absence_duration",
    "occupancy_duration",
    "light_level",
    "night_mode_status",
]

# Storage
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.storage"

# Services
SERVICE_CLEAR_MANUAL_STATES = "clear_manual_states"

# Attributes
ATTR_OCCUPANCY_DURATION = "occupancy_duration"
ATTR_ABSENCE_DURATION = "absence_duration"
ATTR_LIGHT_LEVEL = "light_level"
ATTR_NIGHT_MODE = "night_mode"
