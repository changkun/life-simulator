"""Tests for life.modes.biofilm — Bacterial Quorum Sensing & Biofilm Formation."""
import random

from tests.conftest import make_mock_app
from life.modes.biofilm import register, BIOFILM_PRESETS


def _make_app():
    random.seed(7)
    app = make_mock_app()
    app.biofilm_mode = False
    app.biofilm_menu = False
    app.biofilm_running = False
    register(type(app))
    return app


def test_every_preset_initializes_and_steps():
    for i in range(len(BIOFILM_PRESETS)):
        app = _make_app()
        app._biofilm_init(i)
        for _ in range(5):
            app._biofilm_step()
        assert app.biofilm_generation == 5


def test_step_advances_one_tick_regardless_of_speed():
    # The dispatcher already calls the step function biofilm_speed times per
    # frame, so a single call must advance exactly one tick.
    app = _make_app()
    app._biofilm_init(0)
    app.biofilm_speed = 5
    app._biofilm_step()
    assert app.biofilm_generation == 1


def test_spatial_view_draws_glyphs_with_addstr():
    # addch(ord(ch)) truncates non-ASCII glyphs such as '▓' to one byte in
    # real curses, so the field must be drawn with addstr.
    from life.modes.biofilm import _draw_biofilm_spatial

    class Screen:
        def __init__(self):
            self.drawn = []

        def addstr(self, y, x, s, *a):
            self.drawn.append(s)

        def addch(self, *a):
            raise AssertionError("addch used")

    app = _make_app()
    app._biofilm_init(5)
    app.stdscr = Screen()
    _draw_biofilm_spatial(app, 40, 120)
    assert "░" in app.stdscr.drawn or "▓" in app.stdscr.drawn
