"""Tests for nn_training mode."""
from tests.conftest import make_mock_app
from life.modes.nn_training import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.nntrain_mode = False
    app.nntrain_menu = False
    app.nntrain_menu_sel = 0
    app.nntrain_running = False
    app.nntrain_net = None
    app.nntrain_data = None
    return app


def test_enter():
    app = _make_app()
    app._enter_nntrain_mode()
    assert app.nntrain_menu is True


def test_step_no_crash():
    app = _make_app()
    app.nntrain_mode = True
    app._nntrain_init(0)  # XOR — small, fast
    assert app.nntrain_net is not None
    for _ in range(10):
        app._nntrain_step()


def test_exit_cleanup():
    app = _make_app()
    app._nntrain_init(0)
    app._exit_nntrain_mode()
    assert app.nntrain_mode is False
    assert app.nntrain_net is None
