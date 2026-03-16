"""Tests for falling_sand mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.falling_sand import register


# Sand element type constants
SAND_EMPTY = 0
SAND_SAND = 1
SAND_WATER = 2
SAND_FIRE = 3
SAND_STONE = 4
SAND_PLANT = 5
SAND_OIL = 6
SAND_STEAM = 7

SAND_PRESETS = [
    ("Empty", "Start with an empty grid", "empty"),
    ("Hourglass", "Sand flowing through a narrow gap", "hourglass"),
]

SAND_ELEM_NAMES = {
    0: "empty", 1: "sand", 2: "water", 3: "fire",
    4: "stone", 5: "plant", 6: "oil", 7: "steam",
}
SAND_ELEM_COLORS = {
    0: 0, 1: 3, 2: 4, 3: 1, 4: 6, 5: 2, 6: 5, 7: 7,
}
SAND_ELEM_CHARS = {
    1: "\u2591\u2591", 2: "\u2248\u2248", 3: "\u2588\u2588",
    4: "\u2588\u2588", 5: "\u2663\u2663", 6: "\u2592\u2592",
    7: "\u00b0\u00b0",
}


class TestFallingSand:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.SAND_EMPTY = SAND_EMPTY
        cls.SAND_SAND = SAND_SAND
        cls.SAND_WATER = SAND_WATER
        cls.SAND_FIRE = SAND_FIRE
        cls.SAND_STONE = SAND_STONE
        cls.SAND_PLANT = SAND_PLANT
        cls.SAND_OIL = SAND_OIL
        cls.SAND_STEAM = SAND_STEAM
        cls.SAND_PRESETS = SAND_PRESETS
        cls.SAND_ELEM_NAMES = SAND_ELEM_NAMES
        cls.SAND_ELEM_COLORS = SAND_ELEM_COLORS
        cls.SAND_ELEM_CHARS = SAND_ELEM_CHARS
        register(cls)

    def test_enter(self):
        self.app._enter_sand_mode()
        assert self.app.sand_menu is True
        assert self.app.sand_menu_sel == 0

    def test_init_empty(self):
        self.app.sand_mode = True
        self.app.sand_running = False
        self.app._sand_init("empty")
        assert self.app.sand_grid == {}
        assert self.app.sand_generation == 0

    def test_init_with_preset(self):
        self.app.sand_mode = True
        self.app.sand_running = False
        self.app._sand_init("hourglass")
        assert len(self.app.sand_grid) > 0

    def test_step_no_crash(self):
        self.app.sand_mode = True
        self.app.sand_running = False
        self.app._sand_init("empty")
        # Place some sand particles
        self.app.sand_grid[(5, 10)] = (SAND_SAND, 0)
        self.app.sand_grid[(5, 11)] = (SAND_SAND, 0)
        self.app.sand_grid[(5, 12)] = (SAND_SAND, 0)
        for _ in range(10):
            self.app._sand_step()
        assert self.app.sand_generation == 10

    def test_sand_falls(self):
        self.app.sand_mode = True
        self.app._sand_init("empty")
        self.app.sand_grid[(5, 10)] = (SAND_SAND, 0)
        self.app._sand_step()
        # Sand should have moved down
        assert (5, 10) not in self.app.sand_grid
        assert (6, 10) in self.app.sand_grid

    def test_stone_stays(self):
        self.app.sand_mode = True
        self.app._sand_init("empty")
        self.app.sand_grid[(5, 10)] = (SAND_STONE, 0)
        self.app._sand_step()
        assert self.app.sand_grid.get((5, 10)) == (SAND_STONE, 0)

    def test_paint(self):
        self.app.sand_mode = True
        self.app._sand_init("empty")
        self.app.sand_brush = SAND_SAND
        self.app.sand_brush_size = 1
        self.app.sand_cursor_r = 10
        self.app.sand_cursor_c = 10
        self.app._sand_paint()
        assert (10, 10) in self.app.sand_grid

    def test_exit_cleanup(self):
        self.app.sand_mode = True
        self.app._sand_init("empty")
        self.app.sand_grid[(5, 5)] = (SAND_SAND, 0)
        self.app._exit_sand_mode()
        assert self.app.sand_mode is False
        assert self.app.sand_menu is False
        assert self.app.sand_running is False
        assert self.app.sand_grid == {}
