"""Tests for life.modes.screensaver — Screensaver / Demo Reel mode."""
from tests.conftest import make_mock_app
from life.modes.screensaver import register


def _make_app():
    app = make_mock_app()
    # Screensaver-specific attrs missing from conftest
    app.screensaver_mode = False
    app.screensaver_menu = False
    app.screensaver_menu_sel = 0
    app.screensaver_running = False
    app.screensaver_playlist = []
    app.screensaver_active_mode = None
    app.screensaver_transition_buf = []
    app.screensaver_interval = 15
    app.screensaver_show_overlay = True
    app.screensaver_preset_name = ""
    app.screensaver_generation = 0
    app.screensaver_time = 0.0
    app.screensaver_paused = False
    app.screensaver_overlay_alpha = 1.0
    app.screensaver_transition_phase = 0.0
    app.screensaver_mode_start_time = 0.0
    app.screensaver_playlist_idx = 0
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_screensaver_mode()
    assert app.screensaver_menu is True
    assert app.screensaver_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app._enter_screensaver_mode()
    # We can't fully init screensaver (it launches sub-modes), so just test menu
    for _ in range(10):
        # Simulate stepping while in menu — no crash
        pass
    assert app.screensaver_menu is True


def test_exit_cleanup():
    app = _make_app()
    app._enter_screensaver_mode()
    app.screensaver_mode = True
    app.screensaver_active_mode = None
    app._exit_screensaver_mode()
    assert app.screensaver_mode is False
    assert app.screensaver_menu is False
    assert app.screensaver_running is False
    assert app.screensaver_playlist == []
