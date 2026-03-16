"""Tests for double_pendulum mode."""
import math
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.double_pendulum import register


DPEND_PRESETS = [
    ("Classic", "Standard double pendulum at 135 degrees", "classic"),
    ("Gentle", "Small-angle near-periodic motion", "gentle"),
]


class TestDoublePendulum:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.DPEND_PRESETS = DPEND_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_dpend_mode()
        assert self.app.dpend_menu is True
        assert self.app.dpend_menu_sel == 0

    def test_step_no_crash(self):
        self.app.dpend_mode = True
        self.app.dpend_running = False
        self.app._dpend_init(0)
        for _ in range(10):
            self.app._dpend_step()
        assert self.app.dpend_generation == 10

    def test_exit_cleanup(self):
        self.app.dpend_mode = True
        self.app._dpend_init(0)
        self.app._exit_dpend_mode()
        assert self.app.dpend_mode is False
        assert self.app.dpend_menu is False
        assert self.app.dpend_running is False
        assert self.app.dpend_trail1 == []
