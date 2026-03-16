"""Tests for galaxy mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.galaxy import register


GALAXY_PRESETS = [
    ("Dwarf", "Small irregular galaxy", "dwarf"),
    ("Elliptical", "Giant elliptical galaxy", "elliptical"),
]


class TestGalaxy:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.GALAXY_PRESETS = GALAXY_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_galaxy_mode()
        assert self.app.galaxy_menu is True
        assert self.app.galaxy_menu_sel == 0

    def test_step_no_crash(self):
        self.app.galaxy_mode = True
        self.app.galaxy_running = False
        self.app.galaxy_preset_name = "Dwarf"
        self.app._galaxy_init("dwarf")
        for _ in range(10):
            self.app._galaxy_step()
        assert self.app.galaxy_generation == 10

    def test_exit_cleanup(self):
        self.app.galaxy_mode = True
        self.app.galaxy_preset_name = "Dwarf"
        self.app._galaxy_init("dwarf")
        self.app._exit_galaxy_mode()
        assert self.app.galaxy_mode is False
        assert self.app.galaxy_menu is False
        assert self.app.galaxy_running is False
        assert self.app.galaxy_particles == []
