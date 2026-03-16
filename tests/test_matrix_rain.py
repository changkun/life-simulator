"""Tests for life.modes.matrix_rain — Matrix Digital Rain mode."""
from tests.conftest import make_mock_app
from life.modes.matrix_rain import register


def _make_app():
    app = make_mock_app()
    app.matrix_mode = False
    app.matrix_menu = False
    app.matrix_menu_sel = 0
    app.matrix_running = False
    app.matrix_show_info = False
    app.matrix_columns = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_matrix_mode()
    assert app.matrix_menu is True


def test_step_no_crash():
    app = _make_app()
    app.matrix_mode = True
    app.matrix_preset_name = "classic"
    app._matrix_init("classic")
    for _ in range(10):
        app._matrix_step()
    assert app.matrix_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.matrix_mode = True
    app.matrix_preset_name = "classic"
    app._matrix_init("classic")
    app._exit_matrix_mode()
    assert app.matrix_mode is False
    assert app.matrix_columns == []
