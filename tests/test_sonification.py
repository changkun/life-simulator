"""Tests for life.modes.sonification — Sonification Layer."""
from tests.conftest import make_mock_app
from life.modes.sonification import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    # sonify_play_cmd is set as class attr by register; override for testing
    app.sonify_play_cmd = None  # no audio playback in tests
    return app


def test_enter():
    app = _make_app()
    # Sonification is a toggle, not a mode with enter/menu
    assert hasattr(app, '_sonify_toggle')
    assert hasattr(app, '_sonify_frame')
    assert app.sonify_enabled is False


def test_step_no_crash():
    app = _make_app()
    # Toggle on then call frame 10 times — should not crash even with no player
    app.sonify_enabled = True
    for _ in range(10):
        app._sonify_frame()
    # No crash, metrics extraction may return None (no running mode)
    assert app.sonify_enabled is True


def test_exit_cleanup():
    app = _make_app()
    app.sonify_enabled = True
    result = app._sonify_toggle()
    assert result is False
    assert app.sonify_enabled is False
