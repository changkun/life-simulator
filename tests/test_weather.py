"""Tests for life.modes.weather — Atmospheric Weather mode."""
from tests.conftest import make_mock_app
from life.modes.weather import register


def _make_app():
    app = make_mock_app()
    app.weather_mode = False
    app.weather_menu = False
    app.weather_menu_sel = 0
    app.weather_running = False
    app.weather_coriolis = 0.15
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_weather_mode()
    assert app.weather_menu is True


def test_step_no_crash():
    app = _make_app()
    app.weather_mode = True
    app._weather_init(0)
    for _ in range(10):
        app._weather_step()
    assert app.weather_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.weather_mode = True
    app._weather_init(0)
    app._exit_weather_mode()
    assert app.weather_mode is False
    assert app.weather_running is False
