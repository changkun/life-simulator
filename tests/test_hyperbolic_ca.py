"""Tests for hyperbolic_ca mode."""
from tests.conftest import make_mock_app
from life.modes.hyperbolic_ca import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.hyp_mode = False
    app.hyp_menu = False
    app.hyp_running = False
    app.hyp_cells = []
    app.hyp_adj = {}
    app.hyp_states = []
    app.hyp_ages = []
    return app


def test_enter():
    app = _make_app()
    app._enter_hyp_mode()
    assert app.hyp_menu is True


def test_step_no_crash():
    app = _make_app()
    app.hyp_mode = True
    app._hyp_init(0, 0)
    assert app.hyp_mode is True
    assert len(app.hyp_cells) > 0
    for _ in range(10):
        app._hyp_step()


def test_exit_cleanup():
    app = _make_app()
    app.hyp_mode = True
    app._hyp_init(0, 0)
    app._exit_hyp_mode()
    assert app.hyp_mode is False
    assert app.hyp_cells == []
