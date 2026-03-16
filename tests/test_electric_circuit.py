"""Tests for electric_circuit mode."""
from tests.conftest import make_mock_app
from life.modes.electric_circuit import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.circuit_mode = False
    app.circuit_menu = False
    app.circuit_menu_sel = 0
    app.circuit_running = False
    return app


def test_enter():
    app = _make_app()
    app._enter_circuit_mode()
    assert app.circuit_menu is True


def test_step_no_crash():
    app = _make_app()
    app.circuit_mode = True
    app._circuit_init(0)
    assert app.circuit_mode is True
    for _ in range(10):
        app._circuit_step()


def test_exit_cleanup():
    app = _make_app()
    app._circuit_init(0)
    app._exit_circuit_mode()
    assert app.circuit_mode is False
