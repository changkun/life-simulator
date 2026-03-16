"""Tests for molecular_dynamics mode."""
from tests.conftest import make_mock_app
from life.modes.molecular_dynamics import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.moldyn_mode = False
    app.moldyn_menu = False
    app.moldyn_menu_sel = 0
    app.moldyn_sim = None
    app.moldyn_running = False
    app.moldyn_view = 0
    app.mode_browser = False
    return app


def test_enter():
    app = _make_app()
    app._enter_moldyn_mode()
    assert app.moldyn_menu is True
    assert app.moldyn_mode is True


def test_step_no_crash():
    app = _make_app()
    app.moldyn_mode = True
    app._moldyn_init(5)  # Gas preset — fastest
    assert app.moldyn_sim is not None
    app.moldyn_running = True
    for _ in range(10):
        app._moldyn_step()


def test_exit_cleanup():
    app = _make_app()
    app._moldyn_init(5)
    app._exit_moldyn_mode()
    assert app.moldyn_mode is False
    assert app.moldyn_sim is None
