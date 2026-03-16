"""Tests for life.modes.black_hole — Black Hole mode."""
from tests.conftest import make_mock_app
from life.modes.black_hole import register


def _make_app():
    app = make_mock_app()
    app.blackhole_mode = False
    app.blackhole_menu = False
    app.blackhole_menu_sel = 0
    app.blackhole_running = False
    app.blackhole_dt = 0.02
    app.blackhole_particles = []
    app.blackhole_bg_stars = []
    app.blackhole_lensed = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_blackhole_mode()
    assert app.blackhole_menu is True


def test_step_no_crash():
    app = _make_app()
    app.blackhole_mode = True
    app.blackhole_preset_name = "stellar"
    app._blackhole_init("stellar")
    for _ in range(10):
        app._blackhole_step()
    assert app.blackhole_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.blackhole_mode = True
    app.blackhole_preset_name = "stellar"
    app._blackhole_init("stellar")
    app._exit_blackhole_mode()
    assert app.blackhole_mode is False
    assert app.blackhole_particles == []
