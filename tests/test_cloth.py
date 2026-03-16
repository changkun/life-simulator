"""Tests for cloth mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.cloth import register


CLOTH_PRESETS = [
    ("Hanging", "Cloth pinned along the top edge", "hanging"),
    ("Curtain", "Cloth pinned at two points", "curtain"),
]


class TestCloth:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.CLOTH_PRESETS = CLOTH_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_cloth_mode()
        assert self.app.cloth_menu is True
        assert self.app.cloth_menu_sel == 0

    def test_step_no_crash(self):
        self.app.cloth_mode = True
        self.app.cloth_running = False
        self.app.cloth_preset_name = "Hanging"
        self.app._cloth_init("hanging")
        for _ in range(10):
            self.app._cloth_step()
        assert self.app.cloth_generation == 10

    def test_exit_cleanup(self):
        self.app.cloth_mode = True
        self.app.cloth_preset_name = "Hanging"
        self.app._cloth_init("hanging")
        self.app._exit_cloth_mode()
        assert self.app.cloth_mode is False
        assert self.app.cloth_menu is False
        assert self.app.cloth_running is False
        assert self.app.cloth_points == []
