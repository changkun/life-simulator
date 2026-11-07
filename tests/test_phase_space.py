"""Tests for life.modes.phase_space — Phase Space Navigator mode."""
import pytest

from tests.conftest import make_mock_app
from life.modes import phase_space
from life.modes.phase_space import register


def _make_app(rows=40, cols=120):
    app = make_mock_app(rows=rows, cols=cols)
    register(type(app))
    app._phasespace_init()
    return app


@pytest.mark.parametrize("size", [(24, 80), (40, 120), (60, 200)])
def test_cursor_stays_on_drawn_columns(size):
    """The heatmap must fit left of the info panel, so every column is drawn."""
    rows, cols = size
    app = _make_app(rows, cols)
    phase_space._phasespace_start_scan(app)
    last_px = 5 + (app.phasespace_grid_w - 1) * 2
    assert last_px + 1 < cols - 40
