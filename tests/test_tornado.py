"""Tests for life.modes.tornado — Tornado mode."""
from tests.conftest import make_mock_app
from life.modes.tornado import register


def _make_app():
    app = make_mock_app()
    app.tornado_mode = False
    app.tornado_menu = False
    app.tornado_menu_sel = 0
    app.tornado_running = False
    app.tornado_dt = 0.03
    app.tornado_speed = 2
    app.tornado_show_info = False
    app.tornado_max_destruction = 500
    app.tornado_rain_particles = []
    app.tornado_debris = []
    app.tornado_lightning_segments = []
    app.tornado_destruction = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_tornado_mode()
    assert app.tornado_menu is True


def test_step_no_crash():
    app = _make_app()
    app.tornado_mode = True
    app.tornado_preset_name = "ef3"
    app._tornado_init("ef3")
    for _ in range(10):
        app._tornado_step()
    assert app.tornado_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.tornado_mode = True
    app.tornado_preset_name = "ef3"
    app._tornado_init("ef3")
    app._exit_tornado_mode()
    assert app.tornado_mode is False
    assert app.tornado_rain_particles == []
