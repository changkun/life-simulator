"""Tests for rock_paper_scissors mode."""
import random
from tests.conftest import make_mock_app
from life.modes.rock_paper_scissors import register


class TestRockPaperScissors:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_rps_mode()
        assert self.app.rps_menu is True
        assert self.app.rps_menu_sel == 0

    def test_step_no_crash(self):
        self.app.rps_mode = True
        self.app.rps_menu_sel = 0
        self.app._rps_init(0)
        for _ in range(10):
            self.app._rps_step()
        assert self.app.rps_generation == 10

    def test_exit_cleanup(self):
        self.app.rps_mode = True
        self.app.rps_menu_sel = 0
        self.app._rps_init(0)
        self.app._rps_step()
        self.app._exit_rps_mode()
        assert self.app.rps_mode is False
        assert self.app.rps_menu is False
        assert self.app.rps_running is False
        assert self.app.rps_grid == []
