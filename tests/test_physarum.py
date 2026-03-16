"""Tests for physarum mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.physarum import register


# (name, desc, sensor_angle, sensor_dist, turn_speed, move_speed, deposit, decay, ratio)
PHYSARUM_PRESETS = [
    ("Classic", "Standard slime mold behavior", 0.4, 9.0, 0.3, 1.0, 0.5, 0.02, 0.03),
    ("Branching", "Dense branching network", 0.6, 12.0, 0.4, 1.2, 0.6, 0.015, 0.04),
]

PHYSARUM_DENSITY = ["  ", "\u2591\u2591", "\u2592\u2592", "\u2593\u2593", "\u2588\u2588"]


class TestPhysarum:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.PHYSARUM_PRESETS = PHYSARUM_PRESETS
        cls.PHYSARUM_DENSITY = PHYSARUM_DENSITY
        # Instance defaults
        self.app.physarum_steps_per_frame = 2
        self.app.physarum_preset_name = ""
        self.app.physarum_num_agents = 0
        register(cls)

    def test_enter(self):
        self.app._enter_physarum_mode()
        assert self.app.physarum_menu is True
        assert self.app.physarum_menu_sel == 0

    def test_init(self):
        self.app._physarum_init(0)
        assert self.app.physarum_mode is True
        assert self.app.physarum_menu is False
        assert self.app.physarum_generation == 0
        assert len(self.app.physarum_agents) > 0
        assert len(self.app.physarum_trail) > 0
        assert self.app.physarum_preset_name == "Classic"

    def test_step_no_crash(self):
        self.app._physarum_init(0)
        for _ in range(10):
            self.app._physarum_step()
        assert self.app.physarum_generation == 10

    def test_agents_stay_in_bounds(self):
        self.app._physarum_init(0)
        for _ in range(10):
            self.app._physarum_step()
        rows, cols = self.app.physarum_rows, self.app.physarum_cols
        for agent in self.app.physarum_agents:
            assert 0 <= agent[0] < rows
            assert 0 <= agent[1] < cols

    def test_trail_values_non_negative(self):
        self.app._physarum_init(0)
        for _ in range(10):
            self.app._physarum_step()
        for row in self.app.physarum_trail:
            for val in row:
                assert val >= 0.0

    def test_sense(self):
        self.app._physarum_init(0)
        # Sense should return a float value from the trail
        val = self.app._physarum_sense(5.0, 5.0, 0.0, 0.0)
        assert isinstance(val, float)

    def test_exit_cleanup(self):
        self.app._physarum_init(0)
        self.app._physarum_step()
        self.app._exit_physarum_mode()
        assert self.app.physarum_mode is False
        assert self.app.physarum_menu is False
        assert self.app.physarum_running is False
        assert self.app.physarum_trail == []
        assert self.app.physarum_agents == []
