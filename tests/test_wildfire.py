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
    def test_intensity_stays_finite_and_fire_burns_out(self, idx):
        app = _app(idx)
        app._wfire_init(idx)
        for _ in range(400):
            app._wfire_step()
            assert math.isfinite(app.wfire_max_intensity)
            assert app.wfire_max_intensity <= 5.0
        assert app.wfire_active_cells == 0
