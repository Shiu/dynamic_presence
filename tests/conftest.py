"""Fixtures for Dynamic Presence tests."""
import sys
from pathlib import Path

import pytest

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

pytest_plugins = ["pytest_homeassistant_custom_component"]
