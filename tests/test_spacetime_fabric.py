"""Tests for spacetime_fabric mode."""
import curses
from tests.conftest import make_mock_app
from life.modes.spacetime_fabric import register, STF_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.spacetime_mode = False
    app.spacetime_menu = False
    app.spacetime_menu_sel = 0
    app.spacetime_running = False
    return app


def test_keypad_enter_selects_preset():
    app = _make_app()
    app._enter_spacetime_mode()
    app._handle_spacetime_menu_key(curses.KEY_ENTER)
    assert app.spacetime_mode is True
    assert app.spacetime_menu is False


def test_keypad_enter_toggles_cell():
    app = _make_app()
    app._spacetime_init(0)
    r, c = app.spacetime_cursor_r, app.spacetime_cursor_c
    before = app.spacetime_cells[r][c]
    app._handle_spacetime_key(curses.KEY_ENTER)
    assert app.spacetime_cells[r][c] == 1 - before


def test_presets_step():
    app = _make_app()
    for idx in range(len(STF_PRESETS)):
        app._spacetime_init(idx)
        for _ in range(3):
            app._spacetime_step()


def test_lensing_controls_arrow_reach():
    from life.modes.spacetime_fabric import _lensing_visible
    assert not _lensing_visible(0.5, 0.0)
    assert not _lensing_visible(0.05, 0.15)
    assert _lensing_visible(0.12, 0.15)
    assert _lensing_visible(0.05, 0.5)


def test_hint_bar_fits_80_columns():
    """Every key in the hint bar, q=exit included, fits a 24x80 terminal."""
    app = _make_app()
    app._spacetime_init(0)
    app.message = ""
    app.tc_buf = None
    lines = []
    app.stdscr.addstr = lambda y, x, s, *a: lines.append(s)
    app._draw_spacetime(24, 80)
    hint = [s for s in lines if "q=exit" in s][-1]
    assert len(hint) <= 79
    assert hint.rstrip().endswith("q=exit")
