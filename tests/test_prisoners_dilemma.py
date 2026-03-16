"""Tests for Prisoner's Dilemma mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.prisoners_dilemma import register


class TestPrisonersDilemma:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._spd_init(0)
        assert self.app.spd_mode is True
        assert self.app.spd_generation == 0
        assert len(self.app.spd_grid) > 0
        assert self.app.spd_steps_per_frame == 1
        assert hasattr(self.app, 'spd_coop_count')

    def test_step_no_crash(self):
        self.app._spd_init(0)
        for _ in range(10):
            self.app._spd_step()
        assert self.app.spd_generation == 10

    def test_exit_cleanup(self):
        self.app._spd_init(0)
        assert self.app.spd_mode is True
        self.app._exit_spd_mode()
        assert self.app.spd_mode is False
        assert self.app.spd_running is False
