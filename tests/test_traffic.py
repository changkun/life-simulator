"""Tests for Traffic Flow mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.traffic import register


class TestTraffic:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._traffic_init(0)
        assert self.app.traffic_mode is True
        assert self.app.traffic_generation == 0
        assert len(self.app.traffic_grid) > 0
        assert self.app.traffic_steps_per_frame == 1
        assert hasattr(self.app, 'traffic_avg_speed')

    def test_step_no_crash(self):
        self.app._traffic_init(0)
        for _ in range(10):
            self.app._traffic_step()
        assert self.app.traffic_generation == 10

    def test_exit_cleanup(self):
        self.app._traffic_init(0)
        assert self.app.traffic_mode is True
        self.app._exit_traffic_mode()
        assert self.app.traffic_mode is False
        assert self.app.traffic_running is False
