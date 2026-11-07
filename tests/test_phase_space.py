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


def test_teleport_and_adopt_use_scanned_rule():
    """Lambda vs Mu picks rules at random, so the scanned rule must be reused."""
    app = _make_app()
    app.phasespace_axis_mode = 3
    phase_space._phasespace_start_scan(app)
    key = (app.phasespace_cx, app.phasespace_cy)
    src = app.phasespace_sims[key]
    for _ in range(5):
        phase_space._phasespace_teleport(app)
        g = app.phasespace_preview_grid
        assert (g.birth, g.survival) == (src.birth, src.survival)
    phase_space._phasespace_adopt(app)
    assert (app.grid.birth, app.grid.survival) == (src.birth, src.survival)


def test_pattern_entropy():
    from life.grid import Grid
    g = Grid(4, 4)
    assert phase_space._pattern_entropy(g) == 0.0
    g.population = 8
    assert phase_space._pattern_entropy(g) == pytest.approx(1.0)
    g.population = 16
    assert phase_space._pattern_entropy(g) == 0.0


def test_class_tables_cover_only_returned_classes():
    """Dead entries 'growing' and 'dying' are gone from both tables."""
    from life.modes import phase_space as ps
    assert "growing" not in ps._CLASS_COLORS and "dying" not in ps._CLASS_COLORS
    assert set(ps._COMPLEXITY_WEIGHTS) <= set(ps._CLASS_COLORS)
