"""Tests for ecosystem_evolution mode."""
from tests.conftest import make_mock_app
from life.modes.ecosystem_evolution import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.evoeco_mode = False
    app.evoeco_menu = False
    app.evoeco_menu_sel = 0
    app.evoeco_running = False
    return app


def test_enter():
    app = _make_app()
    app._enter_evoeco_mode()
    assert app.evoeco_menu is True


def test_step_no_crash():
    app = _make_app()
    app.evoeco_mode = True
    app._evoeco_init(0)
    assert app.evoeco_mode is True
    for _ in range(10):
        app._evoeco_step()


def test_exit_cleanup():
    app = _make_app()
    app._evoeco_init(0)
    app._exit_evoeco_mode()
    assert app.evoeco_mode is False
