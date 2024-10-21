"""Constants for the Dynamic Presence integration."""

DOMAIN = "dynamic_presence"

CONF_ROOM_NAME = "room_name"
CONF_PRESENCE_SENSOR = "presence_sensor"
CONF_PRESENCE_TIMEOUT = "presence_timeout"
CONF_ACTIVE_ROOM_THRESHOLD = "active_room_threshold"
CONF_ACTIVE_ROOM_TIMEOUT = "active_room_timeout"
CONF_NIGHT_MODE_TIMEOUT = "night_mode_timeout"
CONF_NIGHT_MODE_SCALE = "night_mode_scale"
CONF_NIGHT_MODE_ENABLE = "night_mode_enable"
CONF_NIGHT_MODE_START = "night_mode_start"
CONF_NIGHT_MODE_END = "night_mode_end"
CONF_CONTROLLED_ENTITIES = "controlled_entities"
CONF_ENABLE = "enable"
CONF_MANAGE_ON_CLEAR = "manage_on_clear"
CONF_MANAGE_ON_PRESENCE = "manage_on_presence"

DEFAULT_PRESENCE_TIMEOUT = 300
DEFAULT_ACTIVE_ROOM_THRESHOLD = 600
DEFAULT_ACTIVE_ROOM_TIMEOUT = 1200
DEFAULT_NIGHT_MODE_TIMEOUT = 120
DEFAULT_NIGHT_MODE_SCALE = 0.5
DEFAULT_NIGHT_MODE_START = "23:00"
DEFAULT_NIGHT_MODE_END = "07:00"
DEFAULT_MANAGE_ON_CLEAR = True
DEFAULT_MANAGE_ON_PRESENCE = True
DEFAULT_ENABLE = True
DEFAULT_NIGHT_MODE_ENABLE = True

NUMBER_CONFIG = {
    CONF_PRESENCE_TIMEOUT: {
        "name": "Presence Timeout",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "s",
        "default": DEFAULT_PRESENCE_TIMEOUT,
    },
    CONF_ACTIVE_ROOM_THRESHOLD: {
        "name": "Active Room Threshold",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "s",
        "default": DEFAULT_ACTIVE_ROOM_THRESHOLD,
    },
    CONF_ACTIVE_ROOM_TIMEOUT: {
        "name": "Active Room Timeout",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "s",
        "default": DEFAULT_ACTIVE_ROOM_TIMEOUT,
    },
    CONF_NIGHT_MODE_TIMEOUT: {
        "name": "Night Mode Timeout",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "s",
        "default": DEFAULT_NIGHT_MODE_TIMEOUT,
    },
    CONF_NIGHT_MODE_SCALE: {
        "name": "Night Mode Scale",
        "min": 0.1,
        "max": 2,
        "step": 0.1,
        "unit": None,
        "default": DEFAULT_NIGHT_MODE_SCALE,
    },
}

SWITCH_KEYS = [
    CONF_MANAGE_ON_CLEAR,
    CONF_MANAGE_ON_PRESENCE,
    CONF_ENABLE,
    CONF_NIGHT_MODE_ENABLE,
]

TIME_KEYS = [
    "night_mode_start",
    "night_mode_end",
]

SENSOR_KEYS = [
    "absence_duration",
    "active_room_status",
    "night_mode_status",
    "occupancy_duration",
    "occupancy_state",
]

DEFAULT_VALUES = {
    CONF_MANAGE_ON_CLEAR: DEFAULT_MANAGE_ON_CLEAR,
    CONF_MANAGE_ON_PRESENCE: DEFAULT_MANAGE_ON_PRESENCE,
    CONF_ENABLE: DEFAULT_ENABLE,
    CONF_NIGHT_MODE_ENABLE: DEFAULT_NIGHT_MODE_ENABLE,
}
