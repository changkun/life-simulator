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
