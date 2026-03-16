"""Tests for life.modes.orrery — Solar System Orrery mode."""
from tests.conftest import make_mock_app
from life.modes.orrery import register


def _make_app():
    app = make_mock_app()
    app.orrery_mode = False
    app.orrery_menu = False
    app.orrery_menu_sel = 0
    app.orrery_running = False
    app.orrery_dt = 0.002
    app.orrery_trail_len = 60
    app.orrery_planets = []
    app.orrery_asteroids = []
    app.orrery_comets = []
    app.orrery_bg_stars = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_orrery_mode()
    assert app.orrery_menu is True


def test_step_no_crash():
    app = _make_app()
    app.orrery_mode = True
    app.orrery_preset_name = "full"
    app._orrery_init("full")
    for _ in range(10):
        app._orrery_step()
    assert app.orrery_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.orrery_mode = True
    app.orrery_preset_name = "full"
    app._orrery_init("full")
    app._exit_orrery_mode()
    assert app.orrery_mode is False
    assert app.orrery_planets == []
