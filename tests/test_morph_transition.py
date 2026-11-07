"""Tests for life.modes.morph_transition."""
from unittest.mock import MagicMock, patch

from life.modes.morph_transition import register
from tests.conftest import make_mock_app


def _app():
    app = make_mock_app()
    register(type(app))
    app._morph_transition_init()
    app.stdscr = MagicMock()
    app.stdscr.getmaxyx.return_value = (10, 20)
    app.stdscr.inch.return_value = ord(" ")
    app.tc_buf = MagicMock()
    app.tc_buf.cells = [(1, 1, "a", 10, 20, 30, False, False)]
    app.ghost_trail_active = False
    return app


def test_no_capture_when_disabled():
    app = _app()
    app._morph_on_mode_exit()
    assert not app._morph_active


def test_crossfade_runs_to_completion_and_clears():
    app = _app()
    app.morph_enabled = True
    app.morph_duration = 10
    app._morph_on_mode_exit()
    assert app._morph_active and (1, 1) in app._morph_old_frame
    app.tc_buf.cells = []
    with patch("sys.stdout"):
        for _ in range(app.morph_duration):
            app._morph_on_refresh()
    assert not app._morph_active
    assert app._morph_old_frame == {}


def test_keys_toggle_and_clamp():
    app = _app()
    app._flash = MagicMock()
    assert app._morph_handle_key(ord("[")) is False  # ignored while disabled
    assert app._morph_handle_key(ord("G")) is True and app.morph_enabled
    for _ in range(30):
        app._morph_handle_key(ord("["))
    assert app.morph_duration == 10
    for _ in range(40):
        app._morph_handle_key(ord("]"))
    assert app.morph_duration == 120
    app._morph_handle_key(ord(":"))
    assert app.morph_easing_idx == 2
    app._morph_handle_key(ord("G"))
    assert not app.morph_enabled and not app._morph_active
