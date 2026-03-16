"""Tests for kuramoto mode."""
import random
from tests.conftest import make_mock_app
from life.modes.kuramoto import register


class TestKuramoto:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_kuramoto_mode()
        assert self.app.kuramoto_menu is True
        assert self.app.kuramoto_menu_sel == 0

    def test_step_no_crash(self):
        self.app.kuramoto_mode = True
        self.app.kuramoto_menu_sel = 0
        self.app._kuramoto_init(0)
        for _ in range(10):
            self.app._kuramoto_step()
        assert self.app.kuramoto_generation == 10

    def test_exit_cleanup(self):
        self.app.kuramoto_mode = True
        self.app.kuramoto_menu_sel = 0
        self.app._kuramoto_init(0)
        self.app._kuramoto_step()
        self.app._exit_kuramoto_mode()
        assert self.app.kuramoto_mode is False
        assert self.app.kuramoto_menu is False
        assert self.app.kuramoto_running is False
        assert self.app.kuramoto_phases == []
        assert self.app.kuramoto_nat_freq == []
