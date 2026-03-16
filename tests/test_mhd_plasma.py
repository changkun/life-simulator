"""Tests for mhd_plasma mode."""
import random
from tests.conftest import make_mock_app
from life.modes.mhd_plasma import register


class TestMHDPlasma:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_mhd_mode()
        assert self.app.mhd_menu is True
        assert self.app.mhd_menu_sel == 0

    def test_step_no_crash(self):
        self.app.mhd_mode = True
        self.app.mhd_menu_sel = 0
        self.app._mhd_init(0)
        for _ in range(10):
            self.app._mhd_step()
        assert self.app.mhd_generation == 10

    def test_exit_cleanup(self):
        self.app.mhd_mode = True
        self.app.mhd_menu_sel = 0
        self.app._mhd_init(0)
        self.app._mhd_step()
        self.app._exit_mhd_mode()
        assert self.app.mhd_mode is False
        assert self.app.mhd_menu is False
        assert self.app.mhd_running is False
        assert self.app.mhd_rho == []
        assert self.app.mhd_vx == []
        assert self.app.mhd_vy == []
        assert self.app.mhd_bx == []
        assert self.app.mhd_by == []
