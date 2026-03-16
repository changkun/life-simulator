"""Tests for wolfram mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.wolfram import register


class TestWolfram:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_wolfram_mode()
        assert self.app.wolfram_menu is True
        assert self.app.wolfram_menu_sel == 0

    def test_init_center_seed(self):
        self.app.wolfram_mode = True
        self.app.wolfram_seed_mode = "center"
        self.app._wolfram_init()
        assert len(self.app.wolfram_rows) == 1
        row0 = self.app.wolfram_rows[0]
        assert row0[len(row0) // 2] == 1
        assert sum(row0) == 1

    def test_init_random_seed(self):
        self.app.wolfram_mode = True
        self.app.wolfram_seed_mode = "random"
        self.app._wolfram_init()
        assert len(self.app.wolfram_rows) == 1
        # Random seed should have at least some alive cells
        assert len(self.app.wolfram_rows[0]) > 0

    def test_step_no_crash(self):
        self.app.wolfram_mode = True
        self.app._wolfram_init()
        for _ in range(10):
            self.app._wolfram_step()
        assert len(self.app.wolfram_rows) == 11

    def test_step_rule_30_deterministic(self):
        random.seed(42)
        self.app.wolfram_mode = True
        self.app.wolfram_rule = 30
        self.app.wolfram_seed_mode = "center"
        self.app._wolfram_init()
        self.app._wolfram_step()
        # Rule 30 from center seed: 010 -> second row should have 111
        row1 = self.app.wolfram_rows[1]
        w = len(row1)
        mid = w // 2
        assert row1[mid - 1] == 1
        assert row1[mid] == 1
        assert row1[mid + 1] == 1

    def test_apply_rule(self):
        # Rule 30: binary 00011110
        assert self.app._wolfram_apply_rule(30, 0, 0, 0) == 0
        assert self.app._wolfram_apply_rule(30, 0, 0, 1) == 1
        assert self.app._wolfram_apply_rule(30, 0, 1, 0) == 1
        assert self.app._wolfram_apply_rule(30, 0, 1, 1) == 1
        assert self.app._wolfram_apply_rule(30, 1, 0, 0) == 1
        assert self.app._wolfram_apply_rule(30, 1, 0, 1) == 0
        assert self.app._wolfram_apply_rule(30, 1, 1, 0) == 0
        assert self.app._wolfram_apply_rule(30, 1, 1, 1) == 0

    def test_exit_cleanup(self):
        self.app.wolfram_mode = True
        self.app._wolfram_init()
        self.app._wolfram_step()
        self.app._exit_wolfram_mode()
        assert self.app.wolfram_mode is False
        assert self.app.wolfram_menu is False
        assert self.app.wolfram_running is False
        assert self.app.wolfram_rows == []
