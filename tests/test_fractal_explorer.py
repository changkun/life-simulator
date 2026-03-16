"""Tests for fractal_explorer mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.fractal_explorer import register


FRACTAL_PRESETS = [
    ("Mandelbrot Classic", "The full Mandelbrot set", "mandelbrot_classic"),
    ("Julia Dendrite", "Dendrite Julia set c=i", "julia_dendrite"),
]

FRACTAL_COLOR_SCHEMES = [
    ("Classic", [1, 2, 3, 4, 5, 6, 7]),
    ("Fire", [1, 3, 7]),
]

FRACTAL_DENSITY = " .:-=+*#%@"


class TestFractalExplorer:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.FRACTAL_PRESETS = FRACTAL_PRESETS
        cls.FRACTAL_COLOR_SCHEMES = FRACTAL_COLOR_SCHEMES
        cls.FRACTAL_DENSITY = FRACTAL_DENSITY
        # Attributes from App.__init__ needed by fractal mode
        self.app.fractal_julia_re = -0.7
        self.app.fractal_julia_im = 0.27015
        self.app.fractal_type = "mandelbrot"
        self.app.fractal_center_re = -0.5
        self.app.fractal_center_im = 0.0
        self.app.fractal_zoom = 1.0
        self.app.fractal_max_iter = 80
        self.app.fractal_dirty = True
        self.app.fractal_buffer = []
        self.app.fractal_color_scheme = 0
        self.app.fractal_smooth = True
        self.app.fractal_rows = 0
        self.app.fractal_cols = 0
        register(cls)

    def test_enter(self):
        self.app._enter_fractal_mode()
        assert self.app.fractal_menu is True
        assert self.app.fractal_menu_sel == 0

    def test_step_no_crash(self):
        self.app.fractal_mode = True
        self.app.fractal_preset_name = "Mandelbrot Classic"
        self.app._fractal_init("mandelbrot_classic")
        # Fractal mode computes on demand, not via step
        self.app._fractal_compute()
        assert len(self.app.fractal_buffer) > 0
        # Run compute 10 times (it's idempotent)
        for _ in range(10):
            self.app._fractal_compute()
        assert len(self.app.fractal_buffer) > 0

    def test_exit_cleanup(self):
        self.app.fractal_mode = True
        self.app.fractal_preset_name = "Mandelbrot Classic"
        self.app._fractal_init("mandelbrot_classic")
        self.app._exit_fractal_mode()
        assert self.app.fractal_mode is False
        assert self.app.fractal_menu is False
        assert self.app.fractal_running is False
        assert self.app.fractal_buffer == []
