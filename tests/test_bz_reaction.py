"""Tests for bz_reaction mode."""
import random
from tests.conftest import make_mock_app
from life.modes.bz_reaction import register


class TestBZReaction:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_bz_mode()
        assert self.app.bz_menu is True
        assert self.app.bz_menu_sel == 0

    def test_step_no_crash(self):
        self.app.bz_mode = True
        self.app.bz_menu_sel = 0
        self.app._bz_init(0)
        for _ in range(10):
            self.app._bz_step()
        assert self.app.bz_generation == 10

    def test_exit_cleanup(self):
        self.app.bz_mode = True
        self.app.bz_menu_sel = 0
        self.app._bz_init(0)
        self.app._bz_step()
        self.app._exit_bz_mode()
        assert self.app.bz_mode is False
        assert self.app.bz_menu is False
        assert self.app.bz_running is False
        assert self.app.bz_a == []
        assert self.app.bz_b == []
        assert self.app.bz_c == []
