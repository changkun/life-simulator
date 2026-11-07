"""Opening plain Game of Life must not leave the user on an empty grid.

Without --pattern the grid starts empty, and Game of Life has no enter
function, so the dashboard and mode browser used to open a blank screen.
"""
import pytest

from life.registry import MODE_REGISTRY
from tests.real_app import patch_curses, run_app

ENTER, ESC = 10, 27


@pytest.fixture(autouse=True)
def _fake_curses(monkeypatch):
    patch_curses(monkeypatch)


def _on_dashboard(app):
    app._dashboard_init()
    app.dashboard_show_favorites_only = False
    items = app._dashboard_get_visible_items()
    app.dashboard_sel = next(i for i, e in enumerate(items) if e["name"] == "Game of Life")


def _in_mode_browser(app):
    app.mode_browser = True
    app.mode_browser_filtered = list(MODE_REGISTRY)
    app.mode_browser_sel = next(i for i, e in enumerate(MODE_REGISTRY) if e["name"] == "Game of Life")


@pytest.mark.parametrize("setup, key", [
    (_on_dashboard, ENTER),
    (_on_dashboard, ESC),
    (_in_mode_browser, ENTER),
], ids=["dashboard-enter", "dashboard-esc", "mode-browser-enter"])
def test_opening_game_of_life_seeds_an_empty_grid(setup, key):
    app = run_app([key, -1], setup=setup)
    assert not app.dashboard and not app.mode_browser
    assert app.grid.population > 0
    assert not app.running
    assert app.pop_history == [app.grid.population]


def test_opening_game_of_life_keeps_an_existing_grid():
    def setup(app):
        for r, c in [(1, 2), (2, 3), (3, 1), (3, 2), (3, 3)]:  # glider
            app.grid.set_alive(r, c)
        _on_dashboard(app)

    app = run_app([ENTER, -1], setup=setup)
    assert not app.dashboard
    assert app.grid.population == 5
