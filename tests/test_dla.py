"""Tests for dla mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.dla import register
from life.modes.nbody import DLA_PRESETS
from life.constants import SPEEDS


class TestDLA:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.DLA_PRESETS = DLA_PRESETS
        # Instance attrs
        self.app.dla_mode = False
        self.app.dla_menu = False
        self.app.dla_menu_sel = 0
        self.app.dla_running = False
        self.app.dla_grid = []
        self.app.dla_walkers = []
        self.app.dla_steps_per_frame = 5

    def test_enter(self):
        self.app._enter_dla_mode()
        assert self.app.dla_menu is True

    def test_init_single(self):
        self.app.dla_mode = True
        self.app._dla_init(0)  # Crystal Growth (single seed)
        assert self.app.dla_mode is True
        assert self.app.dla_crystal_count >= 1
        assert len(self.app.dla_walkers) > 0

    def test_step_no_crash(self):
        self.app.dla_mode = True
        self.app._dla_init(0)
        for _ in range(10):
            self.app._dla_step()
        assert self.app.dla_generation == 10

    def test_all_presets(self):
        """Ensure all presets initialize without error."""
        for i in range(len(DLA_PRESETS)):
            random.seed(42)
            self.app._dla_init(i)
            assert self.app.dla_mode is True
            self.app._dla_step()

    def test_exit_cleanup(self):
        self.app.dla_mode = True
        self.app._dla_init(0)
        self.app._exit_dla_mode()
        assert self.app.dla_mode is False
