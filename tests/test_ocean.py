"""Tests for life.modes.ocean — Ocean Currents mode."""
from tests.conftest import make_mock_app
from life.modes.ocean import register


def _make_app():
    app = make_mock_app()
    app.ocean_mode = False
    app.ocean_menu = False
    app.ocean_menu_sel = 0
    app.ocean_running = False
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_ocean_mode()
    assert app.ocean_menu is True


def test_step_no_crash():
    app = _make_app()
    app.ocean_mode = True
    app._ocean_init(0)
    for _ in range(10):
        app._ocean_step()
    assert app.ocean_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.ocean_mode = True
    app._ocean_init(0)
    app._exit_ocean_mode()
    assert app.ocean_mode is False
    assert app.ocean_running is False
