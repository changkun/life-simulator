"""Tests for spin_glass mode."""
from tests.conftest import make_mock_app
from life.modes.spin_glass import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.spinglass_mode = False
    app.spinglass_menu = False
    app.spinglass_menu_sel = 0
    app.spinglass_running = False
    app.spinglass_grid = []
    app.spinglass_coupling = []
    return app


def test_enter():
    app = _make_app()
    app._enter_spinglass_mode()
    assert app.spinglass_menu is True


def test_step_no_crash():
    app = _make_app()
    app.spinglass_mode = True
    app._spinglass_init(0)
    assert app.spinglass_mode is True
    for _ in range(10):
        app._spinglass_step()


def test_exit_cleanup():
    app = _make_app()
    app._spinglass_init(0)
    app._exit_spinglass_mode()
    assert app.spinglass_mode is False
    assert app.spinglass_grid == []
