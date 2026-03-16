"""Tests for ant mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.ant import register


class TestAnt:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_ant_mode()
        assert self.app.ant_menu is True
        assert self.app.ant_menu_sel == 0

    def test_init_single_ant(self):
        self.app.ant_mode = True
        self.app.ant_num_ants = 1
        self.app._ant_init()
        assert len(self.app.ant_ants) == 1
        assert self.app.ant_grid == {}
        assert self.app.ant_step_count == 0

    def test_init_multiple_ants(self):
        self.app.ant_mode = True
        self.app.ant_num_ants = 4
        self.app._ant_init()
        assert len(self.app.ant_ants) == 4

    def test_step_no_crash(self):
        self.app.ant_mode = True
        self.app.ant_num_ants = 1
        self.app._ant_init()
        for _ in range(10):
            self.app._ant_step()
        assert self.app.ant_step_count == 10

    def test_step_classic_rl(self):
        self.app.ant_mode = True
        self.app.ant_rule = "RL"
        self.app.ant_num_ants = 1
        self.app._ant_init()
        # After one step: ant turns right on empty (state 0, rule char 'R'),
        # flips the cell to state 1, and moves forward
        self.app._ant_step()
        assert self.app.ant_step_count == 1
        # The cell the ant was on should have been colored
        assert len(self.app.ant_grid) > 0

    def test_step_wraps_around(self):
        self.app.ant_mode = True
        self.app.ant_rule = "RL"
        self.app.ant_num_ants = 1
        self.app._ant_init()
        # Run many steps to ensure wrapping doesn't crash
        for _ in range(100):
            self.app._ant_step()
        assert self.app.ant_step_count == 100

    def test_exit_cleanup(self):
        self.app.ant_mode = True
        self.app._ant_init()
        self.app._ant_step()
        self.app._exit_ant_mode()
        assert self.app.ant_mode is False
        assert self.app.ant_menu is False
        assert self.app.ant_running is False
        assert self.app.ant_grid == {}
        assert self.app.ant_ants == []
