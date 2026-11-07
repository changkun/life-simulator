"""Tests for fluid_life mode."""
import random

import pytest

from tests.conftest import make_mock_app
from life.modes.fluid_life import register, FL_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


class TestFluidLifeWalls:
    def setup_method(self):
        random.seed(42)
        self.app = _make_app()

    def test_wall_reflects_incoming_population(self):
        """A population streaming into a wall returns on the next step."""
        from life.modes.fluid_life import _fluidlife_lbm_step
        app = self.app
        app._fluidlife_init(0)
        rows, cols = app.fluidlife_rows, app.fluidlife_cols
        app.fluidlife_f = [[[0.0] * 9 for _ in range(cols)] for _ in range(rows)]
        r, c = rows // 2, cols // 2
        app.fluidlife_objects[r][c] = 1
        app.fluidlife_f[r][c - 1][1] = 0.5  # moving east, into the wall
        _fluidlife_lbm_step(app)
        assert app.fluidlife_f[r][c][3] == pytest.approx(0.5)


class TestFluidLifeStep:
    def setup_method(self):
        random.seed(42)
        self.app = _make_app()

    @pytest.mark.parametrize("idx", range(len(FL_PRESETS)))
    def test_preset_steps_without_blowup(self, idx):
        app = self.app
        app._fluidlife_init(idx)
        for _ in range(30):
            app._fluidlife_step()
        assert app.fluidlife_generation == 30
        assert all(0.0 <= v <= 1.0 for row in app.fluidlife_cells for v in row)
