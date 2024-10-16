"""Test the Dynamic Presence controller."""
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from ..controller import DynamicPresenceController
from . import create_mock_dynamic_presence_config_entry


async def test_controller_initialization(hass: HomeAssistant):
    """Test controller initialization."""
    entry = create_mock_dynamic_presence_config_entry(hass)
    controller = DynamicPresenceController(hass, entry)

    assert controller.hass == hass
    assert controller.config_entry == entry
    assert controller.is_enabled  # Assume we've added this property
    assert not controller.presence_detected


async def test_async_setup(hass: HomeAssistant):
    """Test async_setup method."""
    entry = create_mock_dynamic_presence_config_entry(hass)
    controller = DynamicPresenceController(hass, entry)

    with patch.object(controller, '_setup_presence_sensor') as mock_setup_sensor, \
         patch.object(controller, '_setup_controlled_entities') as mock_setup_entities:
        setup_success = await controller.async_setup()

    assert setup_success
    mock_setup_sensor.assert_called_once()
    mock_setup_entities.assert_called_once()


async def test_presence_detection(hass: HomeAssistant):
    """Test presence detection logic."""
    entry = create_mock_dynamic_presence_config_entry(hass)
    controller = DynamicPresenceController(hass, entry)

    # Mock the presence sensor state
    hass.states.async_set('binary_sensor.test_presence', 'on')

    await controller.handle_presence_change(None)  # Assume we've made this method public
    assert controller.presence_detected

    hass.states.async_set('binary_sensor.test_presence', 'off')
    await controller.handle_presence_change(None)
    assert not controller.presence_detected

# Add more tests for other controller methods...
