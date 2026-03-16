"""Tests for life.modes.param_explorer — Parameter Space Explorer mode."""
from tests.conftest import make_mock_app
from life.modes.param_explorer import register


def _make_app():
    app = make_mock_app()
    app.pexplorer_mode = False
    app.pexplorer_menu = False
    app.pexplorer_menu_sel = 0
    app.pexplorer_running = False
    app.pexplorer_sims = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_param_explorer_mode()
    assert app.pexplorer_menu is True
    assert app.pexplorer_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app._pexplorer_init(0)  # Init with first explorable mode (RD)
    assert app.pexplorer_mode is True
    assert app.pexplorer_menu is False
    app.pexplorer_running = True
    for _ in range(10):
        app._pexplorer_step()
    assert app.pexplorer_generation == 20  # 2 steps per frame * 10


def test_exit_cleanup():
    app = _make_app()
    app._pexplorer_init(0)
    app._exit_param_explorer_mode()
    assert app.pexplorer_mode is False
    assert app.pexplorer_running is False
    assert app.pexplorer_sims == []
