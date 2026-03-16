"""Tests for artificial_chemistry mode."""
from tests.conftest import make_mock_app
from life.modes.artificial_chemistry import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.achem_mode = False
    app.achem_menu = False
    app.achem_menu_sel = 0
    app.achem_running = False
    app.achem_grid = []
    app.achem_energy = []
    app.achem_mol_history = []
    return app


def test_enter():
    app = _make_app()
    app._enter_achem_mode()
    assert app.achem_menu is True


def test_step_no_crash():
    app = _make_app()
    app.achem_mode = True
    app._achem_init(0)
    assert app.achem_mode is True
    for _ in range(10):
        app._achem_step()


def test_exit_cleanup():
    app = _make_app()
    app._achem_init(0)
    app._exit_achem_mode()
    assert app.achem_mode is False
    assert app.achem_grid == []
