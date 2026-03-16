"""Tests for Lotka-Volterra (Predator-Prey) mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.lotka_volterra import register


class TestLotkaVolterra:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._lv_init(0)
        assert self.app.lv_mode is True
        assert self.app.lv_generation == 0
        assert len(self.app.lv_grid) > 0
        assert len(self.app.lv_counts) == 1
        assert self.app.lv_steps_per_frame == 1

    def test_step_no_crash(self):
        self.app._lv_init(0)
        for _ in range(10):
            self.app._lv_step()
        assert self.app.lv_generation == 10

    def test_exit_cleanup(self):
        self.app._lv_init(0)
        assert self.app.lv_mode is True
        self.app._exit_lv_mode()
        assert self.app.lv_mode is False
        assert self.app.lv_running is False
