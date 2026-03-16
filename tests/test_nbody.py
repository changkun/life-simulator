"""Tests for nbody mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.nbody import register
from life.modes.particle_life import NBODY_PRESETS, NBODY_CHARS, NBODY_COLORS
from life.constants import SPEEDS


class TestNBody:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.NBODY_PRESETS = NBODY_PRESETS
        cls.NBODY_CHARS = NBODY_CHARS
        cls.NBODY_COLORS = NBODY_COLORS
        # Instance attrs
        self.app.nbody_mode = False
        self.app.nbody_menu = False
        self.app.nbody_menu_sel = 0
        self.app.nbody_running = False
        self.app.nbody_bodies = []
        self.app.nbody_trails = {}
        self.app.nbody_steps_per_frame = 2
        self.app.nbody_trail_len = 30
        self.app.nbody_show_trails = True
        self.app.nbody_center_mass = True

    def test_enter(self):
        self.app._enter_nbody_mode()
        assert self.app.nbody_menu is True

    def test_init_solar(self):
        self.app.nbody_mode = True
        self.app._nbody_init(0)  # Solar System
        assert self.app.nbody_mode is True
        assert len(self.app.nbody_bodies) > 0

    def test_init_binary(self):
        self.app.nbody_mode = True
        self.app._nbody_init(1)  # Binary Star
        assert self.app.nbody_mode is True
        assert len(self.app.nbody_bodies) >= 2

    def test_step_no_crash(self):
        self.app.nbody_mode = True
        self.app._nbody_init(0)
        for _ in range(10):
            self.app._nbody_step()
        assert self.app.nbody_generation == 10

    def test_all_presets(self):
        """Ensure all presets initialize without error."""
        for i in range(len(NBODY_PRESETS)):
            random.seed(42)
            self.app._nbody_init(i)
            assert self.app.nbody_mode is True
            self.app._nbody_step()

    def test_exit_cleanup(self):
        self.app.nbody_mode = True
        self.app._nbody_init(0)
        self.app._exit_nbody_mode()
        assert self.app.nbody_mode is False
