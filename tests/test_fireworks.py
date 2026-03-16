"""Tests for fireworks mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.fireworks import register


FIREWORKS_PRESETS = [
    ("Gentle", "Slow, graceful single fireworks", "gentle"),
    ("Finale", "Rapid multi-burst grand finale", "finale"),
]

FIREWORKS_COLORS = [1, 2, 3, 4, 5, 6, 7]
FIREWORKS_PATTERNS = ["spherical", "ring", "willow", "crossette"]
FIREWORKS_CHARS = {
    "spark": [".", "*", "+", "o", "@"],
    "trail": [".", ",", "'"],
    "rocket": ["|", "!", "^"],
}


class TestFireworks:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.FIREWORKS_PRESETS = FIREWORKS_PRESETS
        cls.FIREWORKS_COLORS = FIREWORKS_COLORS
        cls.FIREWORKS_PATTERNS = FIREWORKS_PATTERNS
        cls.FIREWORKS_CHARS = FIREWORKS_CHARS
        register(cls)

    def test_enter(self):
        self.app._enter_fireworks_mode()
        assert self.app.fireworks_menu is True
        assert self.app.fireworks_menu_sel == 0

    def test_step_no_crash(self):
        self.app.fireworks_mode = True
        self.app.fireworks_running = True
        self.app.fireworks_preset_name = "Gentle"
        self.app._fireworks_init("gentle")
        for _ in range(10):
            self.app._fireworks_step()
        assert self.app.fireworks_generation == 10

    def test_exit_cleanup(self):
        self.app.fireworks_mode = True
        self.app.fireworks_preset_name = "Gentle"
        self.app._fireworks_init("gentle")
        self.app._exit_fireworks_mode()
        assert self.app.fireworks_mode is False
        assert self.app.fireworks_menu is False
        assert self.app.fireworks_running is False
        assert self.app.fireworks_particles == []
