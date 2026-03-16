"""Tests for life.modes.particle_collider — Particle Collider mode."""
from tests.conftest import make_mock_app
from life.modes.particle_collider import register


def _make_app():
    app = make_mock_app()
    app.collider_mode = False
    app.collider_menu = False
    app.collider_menu_sel = 0
    app.collider_running = False
    app.collider_speed = 1
    app.collider_beams = []
    app.collider_showers = []
    app.collider_trails = []
    app.collider_detections = []
    app.collider_detector_log = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_collider_mode()
    assert app.collider_menu is True


def test_step_no_crash():
    app = _make_app()
    app.collider_mode = True
    app._collider_init("lhc")
    for _ in range(10):
        app._collider_step()
    assert app.collider_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.collider_mode = True
    app._collider_init("lhc")
    app._exit_collider_mode()
    assert app.collider_mode is False
    assert app.collider_beams == []
