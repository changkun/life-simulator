"""Tests for life.modes.planetary_atmos — Planetary Atmosphere & Weather System."""
import random

import pytest

from tests.conftest import make_mock_app
from life.modes.planetary_atmos import register, PLANETARY_ATMOS_PRESETS


def _make_app():
    app = make_mock_app()
    app.planetary_atmos_mode = False
    app.planetary_atmos_menu = False
    app.planetary_atmos_running = False
    register(type(app))
    return app


def _mean(grid):
    return sum(sum(row) for row in grid) / (len(grid) * len(grid[0]))


def test_enter_shows_menu():
    app = _make_app()
    app._enter_planetary_atmos_mode()
    assert app.planetary_atmos_mode is True
    assert app.planetary_atmos_menu is True


@pytest.mark.parametrize("idx", range(len(PLANETARY_ATMOS_PRESETS)))
def test_temperature_does_not_saturate(idx):
    """Radiative cooling balances heating, so the planet does not hit the temperature clamp."""
    random.seed(1)
    app = _make_app()
    app._planetary_atmos_init(idx)
    for _ in range(200):
        app._planetary_atmos_step()
    temp = app.planetary_atmos_temp
    assert _mean(temp) < 1.0
    assert min(min(row) for row in temp) < 0.5
