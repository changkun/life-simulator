"""Tests for wireworld mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.wireworld import register


# Wireworld state constants (from docs/classic-ca.md)
WW_EMPTY = 0
WW_CONDUCTOR = 1
WW_HEAD = 2
WW_TAIL = 3

# Minimal presets for testing
WW_PRESETS = [
    ("Empty", "Start with an empty grid", None),
    ("Diode", "Simple one-way signal", {
        (5, 5): WW_CONDUCTOR,
        (5, 6): WW_CONDUCTOR,
        (5, 7): WW_HEAD,
        (5, 8): WW_TAIL,
        (5, 9): WW_CONDUCTOR,
    }),
]


class TestWireworld:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.WW_EMPTY = WW_EMPTY
        cls.WW_CONDUCTOR = WW_CONDUCTOR
        cls.WW_HEAD = WW_HEAD
        cls.WW_TAIL = WW_TAIL
        cls.WW_PRESETS = WW_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_ww_mode()
        assert self.app.ww_menu is True
        assert self.app.ww_menu_sel == 0

    def test_init_empty(self):
        self.app.ww_mode = True
        self.app.ww_running = False
        self.app.ww_drawing = True
        self.app._ww_init()
        assert self.app.ww_grid == {}
        assert self.app.ww_generation == 0
        assert self.app.ww_rows >= 10
        assert self.app.ww_cols >= 10

    def test_init_with_preset(self):
        cells = WW_PRESETS[1][2]
        self.app.ww_mode = True
        self.app.ww_running = False
        self.app.ww_drawing = True
        self.app._ww_init(cells)
        assert len(self.app.ww_grid) > 0
        # All cell states should be valid wireworld states
        for state in self.app.ww_grid.values():
            assert state in (WW_CONDUCTOR, WW_HEAD, WW_TAIL)

    def test_step_no_crash(self):
        self.app.ww_mode = True
        self.app.ww_running = False
        self.app.ww_drawing = True
        self.app._ww_init()
        # Place a simple circuit: conductor with an electron
        self.app.ww_grid[(5, 5)] = WW_CONDUCTOR
        self.app.ww_grid[(5, 6)] = WW_CONDUCTOR
        self.app.ww_grid[(5, 7)] = WW_HEAD
        self.app.ww_grid[(5, 8)] = WW_TAIL
        self.app.ww_grid[(5, 9)] = WW_CONDUCTOR
        for _ in range(10):
            self.app._ww_step()
        assert self.app.ww_generation == 10

    def test_step_head_becomes_tail(self):
        self.app.ww_mode = True
        self.app._ww_init()
        self.app.ww_grid[(5, 5)] = WW_HEAD
        self.app._ww_step()
        assert self.app.ww_grid.get((5, 5)) == WW_TAIL

    def test_step_tail_becomes_conductor(self):
        self.app.ww_mode = True
        self.app._ww_init()
        self.app.ww_grid[(5, 5)] = WW_TAIL
        self.app._ww_step()
        assert self.app.ww_grid.get((5, 5)) == WW_CONDUCTOR

    def test_step_conductor_activation(self):
        self.app.ww_mode = True
        self.app._ww_init()
        # Conductor with exactly 1 head neighbor should become head
        self.app.ww_grid[(5, 5)] = WW_CONDUCTOR
        self.app.ww_grid[(5, 6)] = WW_HEAD
        self.app._ww_step()
        assert self.app.ww_grid.get((5, 5)) == WW_HEAD

    def test_exit_cleanup(self):
        self.app.ww_mode = True
        self.app._ww_init()
        self.app._exit_ww_mode()
        assert self.app.ww_mode is False
        assert self.app.ww_menu is False
        assert self.app.ww_running is False
        assert self.app.ww_grid == {}
