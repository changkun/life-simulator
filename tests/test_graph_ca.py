"""Tests for graph_ca mode."""
from tests.conftest import make_mock_app
from life.modes.graph_ca import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.gca_mode = False
    app.gca_menu = False
    app.gca_running = False
    app.gca_n = 0
    app.gca_adj = {}
    app.gca_states = []
    app.gca_ages = []
    app.gca_pos_x = []
    app.gca_pos_y = []
    return app


def test_enter():
    app = _make_app()
    app._enter_gca_mode()
    assert app.gca_menu is True


def test_step_no_crash():
    app = _make_app()
    app.gca_mode = True
    app._gca_init(0, 0, node_count=30)
    assert app.gca_mode is True
    assert app.gca_n > 0
    for _ in range(10):
        app._gca_step()


def test_exit_cleanup():
    app = _make_app()
    app.gca_mode = True
    app._gca_init(0, 0, node_count=30)
    app._exit_gca_mode()
    assert app.gca_mode is False
    assert app.gca_n == 0
