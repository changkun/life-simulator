"""Tests for smoke_fire mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.smoke_fire import register


SMOKEFIRE_PRESETS = [
    ("Campfire", "Cozy campfire with rising smoke", "campfire"),
    ("Wildfire", "Spreading wildfire across vegetation", "wildfire"),
]


class TestSmokeFire:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.SMOKEFIRE_PRESETS = SMOKEFIRE_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_smokefire_mode()
        assert self.app.smokefire_menu is True
        assert self.app.smokefire_menu_sel == 0

    def test_step_no_crash(self):
        self.app.smokefire_mode = True
        self.app.smokefire_running = False
        self.app.smokefire_preset_name = "Campfire"
        self.app._smokefire_init("campfire")
        for _ in range(10):
            self.app._smokefire_step()
        assert self.app.smokefire_generation == 10

    def test_exit_cleanup(self):
        self.app.smokefire_mode = True
        self.app.smokefire_preset_name = "Campfire"
        self.app._smokefire_init("campfire")
        self.app._exit_smokefire_mode()
        assert self.app.smokefire_mode is False
        assert self.app.smokefire_menu is False
        assert self.app.smokefire_running is False
        assert self.app.smokefire_temp == []
