"""Tests for life.modes.cinematic_demo — Cinematic Demo Reel mode."""
from tests.conftest import make_mock_app
from life.modes.cinematic_demo import register


def _make_app():
    app = make_mock_app()
    app.cinem_mode = False
    app.cinem_menu = False
    app.cinem_menu_sel = 0
    app.cinem_running = False
    app.cinem_sim_state = None
    app.cinem_prev_density = None
    app.cinem_paused = False
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_cinematic_demo_mode()
    assert app.cinem_menu is True


def test_step_no_crash():
    app = _make_app()
    app._cinematic_init(0)  # "The Grand Tour"
    assert app.cinem_mode is True
    assert app.cinem_running is True
    for _ in range(10):
        app._cinematic_step()
    assert app.cinem_generation >= 10


def test_exit_cleanup():
    app = _make_app()
    app._cinematic_init(0)
    app._exit_cinematic_demo_mode()
    assert app.cinem_mode is False
    assert app.cinem_running is False
    assert app.cinem_sim_state is None
