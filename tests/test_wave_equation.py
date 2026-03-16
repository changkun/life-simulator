"""Tests for wave_equation mode."""
import random
from tests.conftest import make_mock_app
from life.modes.wave_equation import register


class TestWaveEquation:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_wave_mode()
        assert self.app.wave_menu is True
        assert self.app.wave_menu_sel == 0

    def test_step_no_crash(self):
        self.app.wave_mode = True
        self.app.wave_menu_sel = 0
        self.app._wave_init(0)
        for _ in range(10):
            self.app._wave_step()
        assert self.app.wave_generation == 10

    def test_exit_cleanup(self):
        self.app.wave_mode = True
        self.app.wave_menu_sel = 0
        self.app._wave_init(0)
        self.app._wave_step()
        self.app._exit_wave_mode()
        assert self.app.wave_mode is False
        assert self.app.wave_menu is False
        assert self.app.wave_running is False
        assert self.app.wave_u == []
        assert self.app.wave_u_prev == []
