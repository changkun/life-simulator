"""Tests for navier_stokes mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.navier_stokes import register


NS_PRESETS = [
    ("Dye Playground", "Empty canvas for dye injection", "playground"),
    ("Vortex Pair", "Two counter-rotating vortices", "vortex_pair"),
]

NS_DYE_CHARS = [" ", "\u2591", "\u2592", "\u2593", "\u2588"]
NS_VEL_CHARS = [" ", "\u00b7", "\u2218", "\u25cb", "\u25cf"]
NS_VORT_POS = [" ", "\u00b7", "\u2218", "\u25cb", "\u25c9"]
NS_VORT_NEG = [" ", "\u00b7", "\u2219", "\u2022", "\u2b24"]


class TestNavierStokes:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.NS_PRESETS = NS_PRESETS
        cls.NS_DYE_CHARS = NS_DYE_CHARS
        cls.NS_VEL_CHARS = NS_VEL_CHARS
        cls.NS_VORT_POS = NS_VORT_POS
        cls.NS_VORT_NEG = NS_VORT_NEG
        # Attributes from App.__init__ needed by NS mode
        self.app.ns_viscosity = 0.0001
        self.app.ns_diffusion = 0.00001
        self.app.ns_dt = 0.1
        self.app.ns_iterations = 20
        self.app.ns_inject_radius = 3
        self.app.ns_inject_strength = 80.0
        self.app.ns_dye_hue = 0.0
        self.app.ns_steps_per_frame = 4
        self.app.ns_viz_mode = 0
        register(cls)

    def test_enter(self):
        self.app._enter_ns_mode()
        assert self.app.ns_menu is True
        assert self.app.ns_menu_sel == 0

    def test_step_no_crash(self):
        self.app.ns_mode = True
        self.app.ns_running = False
        self.app._ns_init(0)
        for _ in range(10):
            self.app._ns_step()
        assert self.app.ns_generation == 10

    def test_exit_cleanup(self):
        self.app.ns_mode = True
        self.app._ns_init(0)
        self.app._exit_ns_mode()
        assert self.app.ns_mode is False
        assert self.app.ns_menu is False
        assert self.app.ns_running is False
        assert self.app.ns_vx == []
