"""Tests for immune_system mode."""
from tests.conftest import make_mock_app
from life.modes.immune_system import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.immune_mode = False
    app.immune_menu = False
    app.immune_menu_sel = 0
    app.immune_running = False
    app.immune_grid = []
    app.immune_entities = []
    return app


def test_enter():
    app = _make_app()
    app._enter_immune_mode()
    assert app.immune_menu is True


def test_step_no_crash():
    app = _make_app()
    app.immune_mode = True
    app._immune_init(0)
    assert app.immune_mode is True
    for _ in range(10):
        app._immune_step()


def test_exit_cleanup():
    app = _make_app()
    app._immune_init(0)
    app._exit_immune_mode()
    assert app.immune_mode is False
