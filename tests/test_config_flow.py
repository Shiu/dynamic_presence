"""Test the Dynamic Presence config flow."""
from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from ..config_flow import DynamicPresenceConfigFlow
from ..const import DOMAIN


class MockConfigEntry:
    """Mock class for config entry."""

    def __init__(self, domain, data, options):
        """Initialize mock config entry."""
        self.domain = domain
        self.data = data
        self.options = options
        self.entry_id = "test_entry_id"

    def add_to_hass(self, hass):
        """Mock method to add entry to hass."""


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["errors"] == {}

    with patch.object(
        DynamicPresenceConfigFlow, "async_step_user", return_value={"title": "Test Room"}
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "room_name": "Test Room",
                "presence_sensor": "binary_sensor.test_presence",
                "controlled_entities": ["light.test_light"],
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result2["title"] == "Test Room"
    assert result2["data"] == {
        "room_name": "Test Room",
        "presence_sensor": "binary_sensor.test_presence",
        "controlled_entities": ["light.test_light"],
    }


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "room_name": "Test Room",
            "presence_sensor": "binary_sensor.test_presence",
            "controlled_entities": ["light.test_light"],
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "presence_timeout": 300,
            "night_mode_enable": True,
            "night_mode_start": "22:00",
            "night_mode_end": "06:00",
        },
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert config_entry.options == {
        "presence_timeout": 300,
        "night_mode_enable": True,
        "night_mode_start": "22:00",
        "night_mode_end": "06:00",
    }
