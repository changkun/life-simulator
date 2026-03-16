"""Tests for Schelling Segregation mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.schelling import register


class TestSchelling:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._schelling_init(0)
        assert self.app.schelling_mode is True
        assert self.app.schelling_generation == 0
        assert len(self.app.schelling_grid) > 0
        assert self.app.schelling_steps_per_frame == 1

    def test_step_no_crash(self):
        self.app._schelling_init(0)
        for _ in range(10):
            self.app._schelling_step()
        assert self.app.schelling_generation == 10

    def test_exit_cleanup(self):
        self.app._schelling_init(0)
        assert self.app.schelling_mode is True
        self.app._exit_schelling_mode()
        assert self.app.schelling_mode is False
        assert self.app.schelling_running is False
