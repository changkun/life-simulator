"""Tests for Earthquake & Seismic Waves mode."""
import math
import random

from tests.conftest import make_mock_app
from life.modes.earthquake import register, QUAKE_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_wave_speeds_satisfy_cfl():
    app = _make_app()
    app._quake_init(0)
    # Explicit 2D wave scheme needs c^2 <= 0.5 to stay bounded.
    assert app.quake_p_speed ** 2 <= 0.5
    assert app.quake_s_speed ** 2 <= 0.5


def test_waves_stay_finite():
    random.seed(1)
    app = _make_app()
    for i in range(len(QUAKE_PRESETS)):
        app._quake_init(i)
        for _ in range(400):
            app._quake_step()
        for field in (app.quake_pwave, app.quake_swave):
            assert all(math.isfinite(v) and abs(v) < 1e3 for row in field for v in row)
