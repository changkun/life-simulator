"""Tests for forest_fire mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.forest_fire import register
from life.modes.sandpile import FIRE_PRESETS


class TestForestFire:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.FIRE_PRESETS = FIRE_PRESETS
        # Instance attrs
        self.app.fire_mode = False
        self.app.fire_menu = False
        self.app.fire_menu_sel = 0
        self.app.fire_running = False
        self.app.fire_grid = []
        self.app.fire_counts = []
        self.app.fire_steps_per_frame = 1

    def test_enter(self):
        self.app._enter_fire_mode()
        assert self.app.fire_menu is True

    def test_init(self):
        self.app.fire_mode = True
        self.app._fire_init(0)  # Classic
        assert self.app.fire_mode is True
        assert len(self.app.fire_grid) > 0

    def test_step_no_crash(self):
        self.app.fire_mode = True
        self.app._fire_init(0)
        for _ in range(10):
            self.app._fire_step()
        assert self.app.fire_generation == 10
        assert len(self.app.fire_counts) == 10

    def test_all_presets(self):
        """Ensure all presets initialize without error."""
        for i in range(len(FIRE_PRESETS)):
            random.seed(42)
            self.app._fire_init(i)
            assert self.app.fire_mode is True
            self.app._fire_step()

    def test_exit_cleanup(self):
        self.app.fire_mode = True
        self.app._fire_init(0)
        self.app._exit_fire_mode()
        assert self.app.fire_mode is False
