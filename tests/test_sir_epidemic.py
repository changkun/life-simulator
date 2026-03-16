"""Tests for sir_epidemic mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.sir_epidemic import register
from life.modes.forest_fire import SIR_PRESETS
from life.constants import SPEEDS


class TestSIREpidemic:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.SIR_PRESETS = SIR_PRESETS
        # Instance attrs
        self.app.sir_mode = False
        self.app.sir_menu = False
        self.app.sir_menu_sel = 0
        self.app.sir_running = False
        self.app.sir_grid = []
        self.app.sir_infection_timer = []
        self.app.sir_counts = []
        self.app.sir_steps_per_frame = 1

    def test_enter(self):
        self.app._enter_sir_mode()
        assert self.app.sir_menu is True

    def test_init(self):
        self.app.sir_mode = True
        self.app._sir_init(0)  # Seasonal Flu
        assert self.app.sir_mode is True
        assert len(self.app.sir_grid) > 0
        assert len(self.app.sir_counts) == 1  # initial recording

    def test_step_no_crash(self):
        self.app.sir_mode = True
        self.app._sir_init(0)
        for _ in range(10):
            self.app._sir_step()
        assert self.app.sir_generation == 10
        assert len(self.app.sir_counts) == 11  # 1 initial + 10 steps

    def test_all_presets(self):
        """Ensure all presets initialize without error."""
        for i in range(len(SIR_PRESETS)):
            random.seed(42)
            self.app._sir_init(i)
            assert self.app.sir_mode is True
            self.app._sir_step()

    def test_exit_cleanup(self):
        self.app.sir_mode = True
        self.app._sir_init(0)
        self.app._exit_sir_mode()
        assert self.app.sir_mode is False
