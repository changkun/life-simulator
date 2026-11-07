"""Tests for life.modes.recursive_sim — Sim-in-a-Cell."""
import curses

from tests.conftest import make_mock_app
from life.modes.recursive_sim import register, RECURSIVE_PRESETS, CELL_SIZES


def _make_app():
    app = make_mock_app()
    app.rsim_mode = False
    app.rsim_menu = False
    app.rsim_running = False
    register(type(app))
    return app


def test_enter_opens_menu():
    app = _make_app()
    app._enter_recursive_mode()
    assert app.rsim_menu is True
    assert app.rsim_menu_phase == 0


def test_every_preset_starts_and_steps():
    app = _make_app()
    for _, macro_id, micro_id, _ in RECURSIVE_PRESETS:
        app._rsim_init(macro_id, micro_id, CELL_SIZES[0][0])
        assert app.rsim_mode is True
        for _ in range(3):
            app._rsim_step()
        assert app.rsim_generation == 3


def test_coupling_keys_clamp():
    app = _make_app()
    app._rsim_init("gol", "gol", 6)
    for _ in range(30):
        app._handle_rsim_key(ord("+"))
    assert app.rsim_coupling == 1.0
    app._handle_rsim_key(ord("0"))
    assert app.rsim_coupling == 0.0


def test_zoom_in_navigate_and_back():
    app = _make_app()
    app._rsim_init("gol", "gol", 6)
    app._handle_rsim_key(10)
    assert app.rsim_zoom_cell == (0, 0)
    app._handle_rsim_key(curses.KEY_UP)
    assert app.rsim_zoom_cell == (app.rsim_macro_rows - 1, 0)
    app._handle_rsim_key(27)
    assert app.rsim_zoom_cell is None


def test_exit_clears_state():
    app = _make_app()
    app._rsim_init("gol", "gol", 6)
    app.rsim_running = True
    app._handle_rsim_key(10)
    app._exit_recursive_mode()
    assert app.rsim_mode is False
    assert app.rsim_running is False
    assert app.rsim_cells is None
    assert app.rsim_zoom_cell is None
