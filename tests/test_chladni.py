"""Tests for chladni mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.chladni import register


CHLADNI_PRESETS = [
    ("Mode (2,3)", "Classic Chladni figure m=2 n=3", "2_3"),
    ("Sweep", "Frequency sweep through modes", "sweep"),
]


class TestChladni:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.CHLADNI_PRESETS = CHLADNI_PRESETS
        # Attributes from App.__init__ needed by chladni mode
        self.app.chladni_menu_sel = 0
        register(cls)

    def test_enter(self):
        self.app._enter_chladni_mode()
        assert self.app.chladni_menu is True
        assert self.app.chladni_menu_sel == 0

    def test_step_no_crash(self):
        self.app.chladni_mode = True
        self.app.chladni_running = False
        self.app._chladni_init(0)
        for _ in range(10):
            self.app._chladni_step()
        assert self.app.chladni_generation == 10

    def test_exit_cleanup(self):
        self.app.chladni_mode = True
        self.app._chladni_init(0)
        self.app._exit_chladni_mode()
        assert self.app.chladni_mode is False
        assert self.app.chladni_menu is False
        assert self.app.chladni_running is False
        assert self.app.chladni_plate == []
