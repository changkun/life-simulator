"""Tests for primordial_soup mode."""
from tests.conftest import make_mock_app
from life.modes.primordial_soup import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.psoup_mode = False
    app.psoup_menu = False
    app.psoup_menu_sel = 0
    app.psoup_running = False
    app.psoup_grid = []
    app.psoup_energy_grid = []
    app.psoup_protocells = []
    return app


def test_enter():
    app = _make_app()
    app._enter_psoup_mode()
    assert app.psoup_menu is True


def test_step_no_crash():
    app = _make_app()
    app.psoup_mode = True
    app._psoup_init(0)
    assert app.psoup_mode is True
    for _ in range(10):
        app._psoup_step()


def test_exit_cleanup():
    app = _make_app()
    app._psoup_init(0)
    app._exit_psoup_mode()
    assert app.psoup_mode is False
    assert app.psoup_grid == []
