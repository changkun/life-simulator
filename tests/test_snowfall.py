"""Tests for life.modes.snowfall — Snowfall & Blizzard mode."""
from tests.conftest import make_mock_app
from life.modes.snowfall import register


def _make_app():
    app = make_mock_app()
    app.snowfall_mode = False
    app.snowfall_menu = False
    app.snowfall_menu_sel = 0
    app.snowfall_running = False
    app.snowfall_dt = 0.03
    app.snowfall_speed = 2
    app.snowfall_show_info = False
    app.snowfall_flakes = []
    app.snowfall_accumulation = []
    app.snowfall_drift_particles = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_snowfall_mode()
    assert app.snowfall_menu is True


def test_step_no_crash():
    app = _make_app()
    app.snowfall_mode = True
    app.snowfall_preset_name = "gentle"
    app._snowfall_init("gentle")
    for _ in range(10):
        app._snowfall_step()
    assert app.snowfall_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.snowfall_mode = True
    app.snowfall_preset_name = "gentle"
    app._snowfall_init("gentle")
    app._exit_snowfall_mode()
    assert app.snowfall_mode is False
    assert app.snowfall_flakes == []
