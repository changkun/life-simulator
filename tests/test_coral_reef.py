"""Tests for coral_reef mode."""
from tests.conftest import make_mock_app
from life.modes.coral_reef import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.reef_mode = False
    app.reef_menu = False
    app.reef_menu_sel = 0
    app.reef_running = False
    app.reef_grid = []
    app.reef_entities = []
    return app


def test_enter():
    app = _make_app()
    app._enter_reef_mode()
    assert app.reef_menu is True


def test_step_no_crash():
    app = _make_app()
    app.reef_mode = True
    app._reef_init(0)
    assert app.reef_mode is True
    for _ in range(10):
        app._reef_step()


def test_exit_cleanup():
    app = _make_app()
    app._reef_init(0)
    app._exit_reef_mode()
    assert app.reef_mode is False
    assert app.reef_grid == []
