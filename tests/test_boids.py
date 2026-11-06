"""Tests for boids mode."""
import random
import math
import pytest
from tests.conftest import make_mock_app
from life.modes.boids import register, BOIDS_PRESETS, BOIDS_ARROWS


class TestBoids:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        # Instance defaults
        self.app.boids_steps_per_frame = 1
        self.app.boids_preset_name = ""
        self.app.boids_num_agents = 0
        register(cls)

    def test_enter(self):
        self.app._enter_boids_mode()
        assert self.app.boids_menu is True
        assert self.app.boids_menu_sel == 0

    def test_init(self):
        self.app._boids_init(0)
        assert self.app.boids_mode is True
        assert self.app.boids_menu is False
        assert self.app.boids_generation == 0
        assert len(self.app.boids_agents) > 0
        assert self.app.boids_preset_name == BOIDS_PRESETS[0][0]

    def test_step_no_crash(self):
        self.app._boids_init(0)
        for _ in range(10):
            self.app._boids_step()
        assert self.app.boids_generation == 10

    def test_agents_stay_in_bounds(self):
        self.app._boids_init(0)
        for _ in range(10):
            self.app._boids_step()
        rows, cols = self.app.boids_rows, self.app.boids_cols
        for agent in self.app.boids_agents:
            assert 0 <= agent[0] < rows
            assert 0 <= agent[1] < cols

    def test_speed_clamped(self):
        self.app._boids_init(0)
        for _ in range(10):
            self.app._boids_step()
        for agent in self.app.boids_agents:
            spd = math.sqrt(agent[2] ** 2 + agent[3] ** 2)
            assert spd <= self.app.boids_max_speed + 0.01

    def test_exit_cleanup(self):
        self.app._boids_init(0)
        self.app._boids_step()
        self.app._exit_boids_mode()
        assert self.app.boids_mode is False
        assert self.app.boids_menu is False
        assert self.app.boids_running is False
        assert self.app.boids_agents == []
