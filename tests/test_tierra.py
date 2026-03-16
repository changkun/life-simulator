"""Tests for tierra mode."""
from tests.conftest import make_mock_app
from life.modes.tierra import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.tierra_mode = False
    app.tierra_menu = False
    app.tierra_menu_sel = 0
    app.tierra_soup = None
    app.tierra_running = False
    app.tierra_view = "memory"
    app.tierra_scroll = 0
    app.mode_browser = False
    return app


def test_enter():
    app = _make_app()
    app._enter_tierra_mode()
    assert app.tierra_menu is True
    assert app.tierra_mode is True


def test_step_no_crash():
    app = _make_app()
    app.tierra_mode = True
    app._tierra_init(0)
    assert app.tierra_soup is not None
    app.tierra_running = True
    for _ in range(10):
        app._tierra_step()


def test_exit_cleanup():
    app = _make_app()
    app._tierra_init(0)
    app._exit_tierra_mode()
    assert app.tierra_mode is False
    assert app.tierra_soup is None
