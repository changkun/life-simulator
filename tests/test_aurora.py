"""Tests for life.modes.aurora — Aurora Borealis mode."""
from tests.conftest import make_mock_app
from life.modes.aurora import register


def _make_app():
    app = make_mock_app()
    app.aurora_mode = False
    app.aurora_menu = False
    app.aurora_menu_sel = 0
    app.aurora_running = False
    app.aurora_curtains = []
    app.aurora_particles = []
    app.aurora_stars = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_aurora_mode()
    assert app.aurora_menu is True


def test_step_no_crash():
    app = _make_app()
    app.aurora_mode = True
    app.aurora_preset_name = "quiet"
    app._aurora_init("quiet")
    for _ in range(10):
        app._aurora_step()
    assert app.aurora_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.aurora_mode = True
    app.aurora_preset_name = "quiet"
    app._aurora_init("quiet")
    app._exit_aurora_mode()
    assert app.aurora_mode is False
    assert app.aurora_curtains == []
