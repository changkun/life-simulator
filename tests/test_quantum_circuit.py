"""Tests for quantum_circuit mode."""
from tests.conftest import make_mock_app
from life.modes.quantum_circuit import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.qcirc_mode = False
    app.qcirc_menu = False
    app.qcirc_menu_sel = 0
    app.qcirc_running = False
    app.qcirc_state = None
    return app


def test_enter():
    app = _make_app()
    app._enter_qcirc_mode()
    assert app.qcirc_menu is True


def test_step_no_crash():
    app = _make_app()
    app.qcirc_mode = True
    app._qcirc_init(0)  # Bell state
    assert app.qcirc_state is not None
    for _ in range(10):
        app._qcirc_step()


def test_exit_cleanup():
    app = _make_app()
    app._qcirc_init(0)
    app._exit_qcirc_mode()
    assert app.qcirc_mode is False
    assert app.qcirc_state is None
