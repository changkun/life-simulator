"""Tests for life.modes.sparkline_hud."""
from life.grid import Grid
from life.modes.sparkline_hud import SparklineHUDState, _braille_sparkline, _format_compact


def test_braille_sparkline_shape_and_constant_data():
    lines = _braille_sparkline([5.0] * 10, 4, 2)
    assert len(lines) == 2 and all(len(line) == 4 for line in lines)
    assert _braille_sparkline([], 4, 2) == ["    ", "    "]


def test_braille_sparkline_uses_latest_points():
    lines = _braille_sparkline(list(range(100)), 4, 2)
    assert all(len(line) == 4 for line in lines)


def test_format_compact():
    assert _format_compact(2_500_000) == "2.5M"
    assert _format_compact(1500) == "1.5k"
    assert _format_compact(0.005) == "0.005"


def test_state_samples_and_bounds_history():
    grid = Grid(10, 10)
    grid.set_alive(1, 1)
    hud = SparklineHUDState()
    for _ in range(hud.max_points + 20):
        hud.update(grid, 0.5)
    assert len(hud.pop_history) == hud.max_points
    assert len(hud.energy_history) == len(hud.diversity_history) == hud.max_points
    hud.reset()
    assert not hud.pop_history and hud.update_counter == 0
