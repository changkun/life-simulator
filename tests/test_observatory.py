"""Tests for life.modes.observatory — Observatory mode."""
from tests.conftest import make_mock_app
from life.modes.observatory import register


def _make_app():
    app = make_mock_app()
    app.obs_mode = False
    app.obs_menu = False
    app.obs_menu_sel = 0
    app.obs_menu_phase = 0
    app.obs_running = False
    app.obs_viewports = []
    app.obs_focus = -1
    app.obs_pick_layout = None
    app.obs_pick_sims = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_observatory_mode()
    assert app.obs_menu is True
    assert app.obs_menu_phase == 0


def test_step_no_crash():
    app = _make_app()
    app._observatory_init(["gol", "wave", "rd", "fire"], 1)
    assert app.obs_mode is True
    assert len(app.obs_viewports) == 4
    for _ in range(10):
        app._observatory_step()
    assert app.obs_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app._observatory_init(["gol", "wave"], 0)
    app._exit_observatory_mode()
    assert app.obs_mode is False
    assert app.obs_running is False
    assert app.obs_viewports == []
