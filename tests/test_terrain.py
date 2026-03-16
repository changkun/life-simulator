"""Tests for terrain mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.terrain import register


TERRAIN_PRESETS = [
    ("Continental", "Large landmass with continental shelf", 0.001, 0.02, 0.005, 0.25, "continental"),
    ("Archipelago", "Scattered island chain", 0.0008, 0.015, 0.008, 0.35, "archipelago"),
]


class TestTerrain:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.TERRAIN_PRESETS = TERRAIN_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_terrain_mode()
        assert self.app.terrain_menu is True
        assert self.app.terrain_menu_sel == 0

    def test_step_no_crash(self):
        self.app.terrain_mode = True
        self.app._terrain_init(0)
        for _ in range(10):
            self.app._terrain_step()
        assert self.app.terrain_generation == 10

    def test_exit_cleanup(self):
        self.app.terrain_mode = True
        self.app._terrain_init(0)
        self.app._exit_terrain_mode()
        assert self.app.terrain_mode is False
        assert self.app.terrain_menu is False
        assert self.app.terrain_running is False
        assert self.app.terrain_heightmap == []
