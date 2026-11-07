"""Tests for Wildfire Spread & Firefighting mode."""
import math
import random

import pytest

from tests.conftest import make_mock_app
from life.modes.wildfire import register, WFIRE_PRESETS


def _app(seed=1):
    random.seed(seed)
    app = make_mock_app()
    register(type(app))
    return app


def _burning(app):
    return sum(1 for row in app.wfire_intensity for v in row if v > 0.0)


class TestWildfire:
    def test_enter_exit(self):
        app = _app()
        app._enter_wfire_mode()
        assert app.wfire_menu is True
        app._wfire_init(0)
        assert app.wfire_mode is True
        app._exit_wfire_mode()
        assert app.wfire_mode is False
        assert app.wfire_running is False

    @pytest.mark.parametrize("idx", range(len(WFIRE_PRESETS)))
    def test_every_preset_starts_burning(self, idx):
        app = _app(idx)
        app._wfire_init(idx)
        assert _burning(app) > 0

    @pytest.mark.parametrize("idx", range(len(WFIRE_PRESETS)))
    def test_intensity_stays_finite_and_fire_burns_out(self, idx):
        app = _app(idx)
        app._wfire_init(idx)
        for _ in range(400):
            app._wfire_step()
            assert math.isfinite(app.wfire_max_intensity)
            assert app.wfire_max_intensity <= 5.0
        assert app.wfire_active_cells == 0
        assert app.wfire_area_fraction > 0.0


def test_fire_spreads_downwind():
    """With an east wind the burned area must reach further east than west."""
    app = _app(3)
    app._wfire_init(0)
    for r in range(app.wfire_rows):
        for c in range(app.wfire_cols):
            app.wfire_fuel[r][c] = 0       # uniform grass
            app.wfire_moisture[r][c] = 0.1
            app.wfire_elevation[r][c] = 0.0
            app.wfire_intensity[r][c] = 0.0
    app.wfire_fighters = []
    app.wfire_wind_dir = 0.0
    app.wfire_wind_speed = 1.5
    app._wfire_make_wind()
    r0, c0 = app.wfire_rows // 2, app.wfire_cols // 2
    app.wfire_intensity[r0][c0] = 2.0
    for _ in range(30):
        app._wfire_step()
    cols = [c for row in app.wfire_burned
            for c, b in enumerate(row) if b]
    assert max(cols) - c0 > c0 - min(cols)


def test_canyon_fire_runs_down_the_canyon():
    """The southward wind must carry the fire over most of the canyon length."""
    app = _app(5)
    app._wfire_init(5)
    for _ in range(300):
        app._wfire_step()
    rows = [r for r in range(app.wfire_rows)
            for c in range(app.wfire_cols) if app.wfire_burned[r][c]]
    assert max(rows) - min(rows) > app.wfire_rows // 2


def test_elevation_stays_within_max_elevation():
    app = _app(2)
    app._wfire_init(1)  # Mountain Wildfire
    top = max(max(row) for row in app.wfire_elevation)
    assert top <= app.wfire_max_elevation * 1.5 + 1e-9
    rock = sum(row.count(5) for row in app.wfire_fuel)
    assert rock < 0.5 * app.wfire_rows * app.wfire_cols
