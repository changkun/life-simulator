"""Tests for fluid_lbm mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.fluid_lbm import register
from life.modes.traffic import (
    FLUID_PRESETS, FLUID_EX, FLUID_EY, FLUID_W, FLUID_OPP,
    FLUID_SPEED_CHARS, FLUID_VORT_POS, FLUID_VORT_NEG,
)


class TestFluidLBM:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        # Set class-level constants that fluid_lbm expects
        cls.FLUID_PRESETS = FLUID_PRESETS
        cls.FLUID_EX = FLUID_EX
        cls.FLUID_EY = FLUID_EY
        cls.FLUID_W = FLUID_W
        cls.FLUID_OPP = FLUID_OPP
        cls.FLUID_SPEED_CHARS = FLUID_SPEED_CHARS
        cls.FLUID_VORT_POS = FLUID_VORT_POS
        cls.FLUID_VORT_NEG = FLUID_VORT_NEG
        # Instance attributes
        self.app.fluid_mode = False
        self.app.fluid_menu = False
        self.app.fluid_menu_sel = 0
        self.app.fluid_running = False
        self.app.fluid_f = []
        self.app.fluid_obstacle = []
        self.app.fluid_steps_per_frame = 3

    def test_enter(self):
        self.app._enter_fluid_mode()
        assert self.app.fluid_menu is True

    def test_init_and_step(self):
        self.app.fluid_mode = True
        self.app._fluid_init(0)
        assert self.app.fluid_mode is True
        assert self.app.fluid_menu is False
        assert len(self.app.fluid_f) > 0

    def test_step_no_crash(self):
        self.app.fluid_mode = True
        self.app._fluid_init(0)
        for _ in range(5):
            self.app._fluid_step()
        assert self.app.fluid_generation == 5

    def test_get_macros(self):
        self.app.fluid_mode = True
        self.app._fluid_init(0)
        rho, ux, uy = self.app._fluid_get_macros()
        assert len(rho) == self.app.fluid_rows
        assert len(ux[0]) == self.app.fluid_cols

    def test_exit_cleanup(self):
        self.app.fluid_mode = True
        self.app._fluid_init(0)
        self.app._exit_fluid_mode()
        assert self.app.fluid_mode is False
