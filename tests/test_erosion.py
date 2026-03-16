"""Tests for Hydraulic Erosion mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.erosion import register


class TestErosion:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._erosion_init(0)
        assert self.app.erosion_mode is True
        assert self.app.erosion_generation == 0
        assert len(self.app.erosion_terrain) > 0
        assert self.app.erosion_steps_per_frame == 1

    def test_step_no_crash(self):
        self.app._erosion_init(0)
        for _ in range(10):
            self.app._erosion_step()
        assert self.app.erosion_generation == 10

    def test_exit_cleanup(self):
        self.app._erosion_init(0)
        assert self.app.erosion_mode is True
        self.app._exit_erosion_mode()
        assert self.app.erosion_mode is False
        assert self.app.erosion_running is False
