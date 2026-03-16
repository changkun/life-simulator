"""Tests for rayleigh_benard mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.rayleigh_benard import register


RBC_PRESETS = [
    ("Classic", "Standard Rayleigh-Benard convection rolls", "classic"),
    ("Gentle", "Low Rayleigh number gentle convection", "gentle"),
]


class TestRayleighBenard:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.RBC_PRESETS = RBC_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_rbc_mode()
        assert self.app.rbc_menu is True
        assert self.app.rbc_menu_sel == 0

    def test_step_no_crash(self):
        self.app.rbc_mode = True
        self.app.rbc_running = False
        self.app._rbc_init(0)
        for _ in range(10):
            self.app._rbc_step()
        assert self.app.rbc_generation == 10

    def test_exit_cleanup(self):
        self.app.rbc_mode = True
        self.app._rbc_init(0)
        self.app._exit_rbc_mode()
        assert self.app.rbc_mode is False
        assert self.app.rbc_menu is False
        assert self.app.rbc_running is False
        assert self.app.rbc_T == []
