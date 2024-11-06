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

# Switch configuration
CONF_AUTOMATION = "automation"
CONF_AUTO_ON = "auto_on"
CONF_AUTO_OFF = "auto_off"
CONF_NIGHT_MODE = "night_mode"
CONF_NIGHT_MANUAL_ON = "night_manual_on"

# Default values
DEFAULT_DETECTION_TIMEOUT = 5  # seconds
DEFAULT_LONG_TIMEOUT = 180  # 3 minutes
DEFAULT_SHORT_TIMEOUT = 30  # 30 seconds
DEFAULT_LIGHT_THRESHOLD = 10  # lux
DEFAULT_NIGHT_MODE_START = "23:00:00"
DEFAULT_NIGHT_MODE_END = "08:00:00"

# Switch defaults
DEFAULT_AUTOMATION = True
DEFAULT_AUTO_ON = True
DEFAULT_AUTO_OFF = True
DEFAULT_NIGHT_MODE = True
DEFAULT_NIGHT_MANUAL_ON = False

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
        "max": 100,
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
        "max": 1000,
        "step": 10,
        "unit": "lx",
        "default": DEFAULT_LIGHT_THRESHOLD,
    },
}

# Switch configuration with defaults
SWITCH_CONFIG = {
    CONF_AUTOMATION: DEFAULT_AUTOMATION,
    CONF_AUTO_ON: DEFAULT_AUTO_ON,
    CONF_AUTO_OFF: DEFAULT_AUTO_OFF,
    CONF_NIGHT_MODE: DEFAULT_NIGHT_MODE,
    CONF_NIGHT_MANUAL_ON: DEFAULT_NIGHT_MANUAL_ON,
}

# Entity keys
SWITCH_KEYS = [
    CONF_AUTOMATION,
    CONF_AUTO_ON,
    CONF_AUTO_OFF,
    CONF_NIGHT_MODE,
    CONF_NIGHT_MANUAL_ON,
]

# Add these new constants
CONF_NIGHT_MODE_START = "night_mode_start"
CONF_NIGHT_MODE_END = "night_mode_end"

# Update TIME_KEYS to use constants
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
