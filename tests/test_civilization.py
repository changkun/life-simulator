"""Tests for civilization mode."""
from tests.conftest import make_mock_app
from life.modes.civilization import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.civ_mode = False
    app.civ_menu = False
    app.civ_menu_sel = 0
    app.civ_running = False
    app.civ_terrain = []
    app.civ_tribes = []
    app.civ_log = []
    return app


def test_enter():
    app = _make_app()
    app._enter_civ_mode()
    assert app.civ_menu is True


def test_step_no_crash():
    app = _make_app()
    app.civ_mode = True
    app._civ_init(0)
    assert app.civ_mode is True
    for _ in range(10):
        app._civ_step()


def test_exit_cleanup():
    app = _make_app()
    app._civ_init(0)
    app._exit_civ_mode()
    assert app.civ_mode is False
    assert app.civ_terrain == []
