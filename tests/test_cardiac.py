"""Tests for life.modes.cardiac — Cardiac Electrophysiology & Arrhythmia."""
import random

from tests.conftest import make_mock_app
from life.modes.cardiac import register, CARDIAC_PRESETS, TISSUE_EMPTY, TISSUE_SCAR


def _make_app():
    random.seed(3)
    app = make_mock_app()
    app.cardiac_mode = False
    app.cardiac_menu = False
    app.cardiac_running = False
    register(type(app))
    return app


def test_every_preset_initializes_and_steps():
    for i in range(len(CARDIAC_PRESETS)):
        app = _make_app()
        app._cardiac_init(i)
        for _ in range(20):
            app._cardiac_step()
        assert app.cardiac_generation == 20


def test_voltage_does_not_saturate_the_clamps():
    # Coupling above the explicit-diffusion stability limit made cells flip
    # between the voltage clamps (-2.5 and 3.0) every tick.
    app = _make_app()
    app._cardiac_init(0)
    for _ in range(150):
        app._cardiac_step()
    stuck = 0
    for r in range(app.cardiac_rows):
        for c in range(app.cardiac_cols):
            if app.cardiac_tissue[r][c] in (TISSUE_EMPTY, TISSUE_SCAR):
                continue
            if app.cardiac_V[r][c] <= -2.5 or app.cardiac_V[r][c] >= 3.0:
                stuck += 1
    assert stuck == 0


def test_escape_leaves_the_run():
    app = _make_app()
    app._cardiac_init(0)
    assert app._handle_cardiac_key(27) is True
    assert app.cardiac_mode is False
