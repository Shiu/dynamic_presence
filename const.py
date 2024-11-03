"""Constants for the Dynamic Presence integration."""

DOMAIN = "dynamic_presence"

CONF_ROOM_NAME = "room_name"
CONF_PRESENCE_SENSOR = "presence_sensor"
CONF_LIGHT_SENSOR = "light_sensor"
CONF_CONTROLLED_ENTITIES = "controlled_entities"
CONF_NIGHT_MODE_CONTROLLED_ENTITIES = "night_mode_controlled_entities"
CONF_NIGHT_MODE_ENTITIES_ADDMODE = "night_mode_entities_addmode"
NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE = "additive"
NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE = "exclusive"
CONF_PRESENCE_TIMEOUT = "presence_timeout"
CONF_ENABLE = "enable"
CONF_MANAGE_ON_CLEAR = "manage_on_clear"
CONF_MANAGE_ON_PRESENCE = "manage_on_presence"
CONF_ACTIVE_ROOM_THRESHOLD = "active_room_threshold"
CONF_SHORT_ABSENCE_THRESHOLD = "short_absence_threshold"
CONF_ACTIVE_ROOM_TIMEOUT = "active_room_timeout"
CONF_NIGHT_MODE_SCALE = "night_mode_scale"
CONF_NIGHT_MODE_ENABLE = "night_mode_enable"
CONF_NIGHT_MODE_START = "night_mode_start"
CONF_NIGHT_MODE_END = "night_mode_end"
CONF_LIGHT_THRESHOLD = "light_threshold"
CONF_NIGHT_MODE_OVERRIDE_ON_PRESENCE = "night_mode_override_on_presence"
CONF_REMOTE_CONTROL_TIMEOUT = "remote_control_timeout"

DEFAULT_PRESENCE_TIMEOUT = 180
DEFAULT_ACTIVE_ROOM_THRESHOLD = 600
DEFAULT_ACTIVE_ROOM_TIMEOUT = 600
DEFAULT_NIGHT_MODE_SCALE = 0.5
DEFAULT_SHORT_ABSENCE_THRESHOLD = 10
DEFAULT_NIGHT_MODE_START = "23:00"
DEFAULT_NIGHT_MODE_END = "08:00"
DEFAULT_MANAGE_ON_CLEAR = True
DEFAULT_MANAGE_ON_PRESENCE = True
DEFAULT_ENABLE = True
DEFAULT_NIGHT_MODE_ENABLE = True
DEFAULT_LIGHT_THRESHOLD = 20
DEFAULT_NIGHT_MODE_ENTITIES_ADDMODE = NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE
DEFAULT_NIGHT_MODE_OVERRIDE_ON_PRESENCE = False
DEFAULT_REMOTE_CONTROL_TIMEOUT = 60

NUMBER_CONFIG = {
    CONF_PRESENCE_TIMEOUT: {
        "name": "Presence Timeout",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "seconds",
        "default": DEFAULT_PRESENCE_TIMEOUT,
    },
    CONF_ACTIVE_ROOM_THRESHOLD: {
        "name": "Active Room Threshold",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "seconds",
        "default": DEFAULT_ACTIVE_ROOM_THRESHOLD,
    },
    CONF_ACTIVE_ROOM_TIMEOUT: {
        "name": "Active Room Timeout",
        "min": 1,
        "max": 3600,
        "step": 1,
        "unit": "seconds",
        "default": DEFAULT_ACTIVE_ROOM_TIMEOUT,
    },
    CONF_NIGHT_MODE_SCALE: {
        "name": "Night Mode Scale",
        "min": 0.1,
        "max": 2,
        "step": 0.1,
        "unit": None,
        "default": DEFAULT_NIGHT_MODE_SCALE,
    },
    CONF_SHORT_ABSENCE_THRESHOLD: {
        "name": "Short Absence Threshold",
        "min": 1,
        "max": 60,
        "step": 1,
        "unit": "seconds",
        "default": DEFAULT_SHORT_ABSENCE_THRESHOLD,
    },
    CONF_LIGHT_THRESHOLD: {
        "name": "Light Level Threshold",
        "min": 0,
        "max": 1000,
        "step": 10,
        "unit": "lx",
        "default": DEFAULT_LIGHT_THRESHOLD,
    },
    CONF_REMOTE_CONTROL_TIMEOUT: {
        "name": "Remote Control Timeout",
        "icon": "mdi:timer-outline",
        "default": DEFAULT_REMOTE_CONTROL_TIMEOUT,
        "min": 0,
        "max": 3600,
        "step": 1,
        "unit": "seconds",
    },
}

SWITCH_KEYS = [
    CONF_MANAGE_ON_CLEAR,
    CONF_MANAGE_ON_PRESENCE,
    CONF_ENABLE,
    CONF_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_OVERRIDE_ON_PRESENCE,
]

SWITCH_DEFAULT_STATES = {
    CONF_ENABLE: DEFAULT_ENABLE,
    CONF_MANAGE_ON_CLEAR: DEFAULT_MANAGE_ON_CLEAR,
    CONF_MANAGE_ON_PRESENCE: DEFAULT_MANAGE_ON_PRESENCE,
    CONF_NIGHT_MODE_ENABLE: DEFAULT_NIGHT_MODE_ENABLE,
    CONF_NIGHT_MODE_OVERRIDE_ON_PRESENCE: DEFAULT_NIGHT_MODE_OVERRIDE_ON_PRESENCE,
}

NIGHT_MODE_ENTITIES_ADDMODE_OPTIONS = [
    NIGHT_MODE_ENTITIES_ADDMODE_ADDITIVE,
    NIGHT_MODE_ENTITIES_ADDMODE_EXCLUSIVE,
]

TIME_KEYS = [
    "night_mode_start",
    "night_mode_end",
]

TIME_DEFAULT_VALUES = {
    "night_mode_start": DEFAULT_NIGHT_MODE_START,
    "night_mode_end": DEFAULT_NIGHT_MODE_END,
}

SENSOR_KEYS = [
    "light_level",
    "absence_duration",
    "active_room_status",
    "night_mode_status",
    "occupancy_duration",
    "occupancy_state",
    "remote_control_duration",
]

NIGHT_MODE_KEYS = [
    CONF_NIGHT_MODE_ENTITIES_ADDMODE,
]
