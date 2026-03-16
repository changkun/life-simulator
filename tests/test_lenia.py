"""Tests for lenia mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.lenia import register


LENIA_PRESETS = [
    # (name, desc, R, mu, sigma, dt)
    ("Orbium", "Smooth glider", 13, 0.15, 0.015, 0.1),
    ("Geminium", "Self-replicating blob", 10, 0.14, 0.014, 0.1),
]

LENIA_DENSITY = ["  ", "\u2591\u2591", "\u2592\u2592", "\u2593\u2593", "\u2588\u2588"]


class TestLenia:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.LENIA_PRESETS = LENIA_PRESETS
        cls.LENIA_DENSITY = LENIA_DENSITY
        # Instance defaults matching app.py
        self.app.lenia_R = 13
        self.app.lenia_mu = 0.15
        self.app.lenia_sigma = 0.015
        self.app.lenia_dt = 0.1
        self.app.lenia_steps_per_frame = 1
        self.app.lenia_preset_name = ""
        self.app.lenia_generation = 0
        self.app.lenia_grid = []
        self.app.lenia_kernel = []
        register(cls)

    def test_enter(self):
        self.app._enter_lenia_mode()
        assert self.app.lenia_menu is True
        assert self.app.lenia_menu_sel == 0

    def test_init(self):
        self.app.lenia_mode = True
        self.app._lenia_init(0)
        assert self.app.lenia_generation == 0
        assert len(self.app.lenia_grid) > 0
        assert len(self.app.lenia_kernel) > 0
        assert self.app.lenia_R == 13
        assert self.app.lenia_mu == 0.15

    def test_build_kernel(self):
        self.app.lenia_R = 5  # Use small kernel for speed
        self.app._lenia_build_kernel()
        k = self.app.lenia_kernel
        size = 2 * 5 + 1
        assert len(k) == size
        assert len(k[0]) == size
        # Kernel should sum approximately to 1 (normalized)
        total = sum(sum(row) for row in k)
        assert abs(total - 1.0) < 0.01

    def test_growth_function(self):
        self.app.lenia_mu = 0.15
        self.app.lenia_sigma = 0.015
        # At mu, growth should be maximum (2*exp(0) - 1 = 1.0)
        val = self.app._lenia_growth(0.15)
        assert abs(val - 1.0) < 0.01
        # Far from mu, growth should be ~-1
        val = self.app._lenia_growth(0.0)
        assert val < -0.9

    def test_step_no_crash(self):
        self.app.lenia_mode = True
        self.app.lenia_R = 3  # Small kernel for speed
        self.app._lenia_init(0)
        # Override to small grid for faster tests
        self.app.lenia_rows = 15
        self.app.lenia_cols = 15
        self.app.lenia_grid = [[0.0] * 15 for _ in range(15)]
        # Seed a small blob
        self.app.lenia_grid[7][7] = 0.5
        self.app.lenia_grid[7][8] = 0.5
        self.app.lenia_grid[8][7] = 0.5
        self.app._lenia_build_kernel()
        for _ in range(3):
            self.app._lenia_step()
        assert self.app.lenia_generation == 3

    def test_step_values_in_range(self):
        self.app.lenia_mode = True
        self.app.lenia_R = 3
        self.app._lenia_init(0)
        self.app.lenia_rows = 15
        self.app.lenia_cols = 15
        self.app.lenia_grid = [[random.random() * 0.5 for _ in range(15)] for _ in range(15)]
        self.app._lenia_build_kernel()
        for _ in range(3):
            self.app._lenia_step()
        for row in self.app.lenia_grid:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_exit_cleanup(self):
        self.app.lenia_mode = True
        self.app._lenia_init(0)
        self.app._exit_lenia_mode()
        assert self.app.lenia_mode is False
        assert self.app.lenia_menu is False
        assert self.app.lenia_running is False
        assert self.app.lenia_grid == []
        assert self.app.lenia_kernel == []
