"""Tests for mycelium mode."""
from tests.conftest import make_mock_app
from life.modes.mycelium import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.mycelium_mode = False
    app.mycelium_menu = False
    app.mycelium_menu_sel = 0
    app.mycelium_running = False
    return app


def test_enter():
    app = _make_app()
    app._enter_mycelium_mode()
    assert app.mycelium_menu is True


def test_step_no_crash():
    app = _make_app()
    app.mycelium_mode = True
    app._mycelium_init(0)
    assert app.mycelium_mode is True
    for _ in range(10):
        app._mycelium_step()


def test_exit_cleanup():
    app = _make_app()
    app._mycelium_init(0)
    app._exit_mycelium_mode()
    assert app.mycelium_mode is False
