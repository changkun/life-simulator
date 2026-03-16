"""Tests for aco mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.aco import register


# ACO_PRESETS and ACO_DENSITY are referenced on self but never defined as class attrs
# Define them here for testing
ACO_PRESETS = [
    ("Foraging", "Classic foraging — ants search for food", 0.01, 0.3, 0.1, 0.05, 3, 3),
    ("Dense Colony", "Many ants, strong pheromone", 0.005, 0.5, 0.15, 0.08, 5, 4),
]

ACO_DENSITY = ["  ", "░░", "▒▒", "▓▓", "██"]


class TestACO:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.ACO_PRESETS = ACO_PRESETS
        cls.ACO_DENSITY = ACO_DENSITY
        # Instance attrs
        self.app.aco_mode = False
        self.app.aco_menu = False
        self.app.aco_menu_sel = 0
        self.app.aco_running = False
        self.app.aco_pheromone = []
        self.app.aco_ants = []
        self.app.aco_food = []
        self.app.aco_steps_per_frame = 2

    def test_enter(self):
        self.app._enter_aco_mode()
        assert self.app.aco_menu is True

    def test_init(self):
        self.app.aco_mode = True
        self.app._aco_init(0)
        assert self.app.aco_mode is True
        assert self.app.aco_menu is False
        assert len(self.app.aco_pheromone) > 0
        assert len(self.app.aco_ants) > 0

    def test_step_no_crash(self):
        self.app.aco_mode = True
        self.app._aco_init(0)
        for _ in range(10):
            self.app._aco_step()
        assert self.app.aco_generation == 10

    def test_exit_cleanup(self):
        self.app.aco_mode = True
        self.app._aco_init(0)
        self.app._exit_aco_mode()
        assert self.app.aco_mode is False
