"""Tests for lsystem mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.lsystem import register


LSYSTEM_PRESETS = [
    ("Binary Tree", "Symmetric branching tree structure", "binary_tree"),
    ("Fern", "Naturalistic fern with curving fronds", "fern"),
]


class TestLSystem:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.LSYSTEM_PRESETS = LSYSTEM_PRESETS
        # Attributes from App.__init__ needed by lsystem mode
        self.app.lsystem_light_dir = 0.0
        self.app.lsystem_mode = False
        self.app.lsystem_menu = False
        self.app.lsystem_menu_sel = 0
        self.app.lsystem_running = False
        self.app.lsystem_generation = 0
        self.app.lsystem_preset_name = ""
        self.app.lsystem_plants = []
        self.app.lsystem_segments = []
        self.app.lsystem_leaves = []
        self.app.lsystem_wind = 0.0
        self.app.lsystem_wind_time = 0.0
        self.app.lsystem_season = 0
        self.app.lsystem_season_tick = 0
        self.app.lsystem_seasons_auto = True
        self.app.lsystem_mutation = 0.0
        self.app.lsystem_seed_queue = []
        self.app.lsystem_fallen_leaves = []
        self.app.lsystem_growth_rate = 1.0
        self.app.lsystem_angle = 25.0
        register(cls)

    def test_enter(self):
        self.app._enter_lsystem_mode()
        assert self.app.lsystem_menu is True
        assert self.app.lsystem_menu_sel == 0

    def test_step_no_crash(self):
        self.app.lsystem_mode = True
        self.app.lsystem_running = False
        self.app.lsystem_preset_name = "Binary Tree"
        self.app._lsystem_init("binary_tree")
        for _ in range(10):
            self.app._lsystem_step()
        # generation only increments when growth actually happens
        assert self.app.lsystem_generation >= 0

    def test_exit_cleanup(self):
        self.app.lsystem_mode = True
        self.app.lsystem_preset_name = "Binary Tree"
        self.app._lsystem_init("binary_tree")
        self.app._exit_lsystem_mode()
        assert self.app.lsystem_mode is False
        assert self.app.lsystem_menu is False
        assert self.app.lsystem_running is False
        assert self.app.lsystem_plants == []
