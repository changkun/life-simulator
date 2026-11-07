"""Tests for core App behaviour: mode switches and the galaxy minimap."""
import pytest

from tests.real_app import patch_curses, _Screen
from life.app import App


@pytest.fixture
def app(monkeypatch):
    patch_curses(monkeypatch)
    return App(_Screen([]), None, 30, 60)


def test_mode_switch_closes_menu_left_open(app):
    app._enter_nca_mode()
    assert app.nca_menu and not app.nca_mode
    app._exit_current_modes()
    assert not app.nca_menu


def test_mode_switch_closes_rule_menu_left_open(app):
    app.compare_rule_menu = True
    app._exit_current_modes()
    assert not app.compare_rule_menu


def test_minimap_bins_galaxy_particles(app):
    app.galaxy_mode = True
    app.galaxy_rows, app.galaxy_cols = 10, 10
    app.galaxy_particles = [[3.5, 2.5, 0.0, 0.0, 1.0, 0.0],
                            [3.2, 2.9, 0.0, 0.0, 0.5, 1.0]]
    rows, cols, sample, *_ = app._get_minimap_data()
    assert (rows, cols) == (10, 10)
    assert sample(2, 3) == 1.0
    assert sample(0, 0) == 0.0
