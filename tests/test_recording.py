"""Tests for life.modes.recording — Recording & Export."""
import unittest.mock
from tests.conftest import make_mock_app
from life.modes.recording import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    # Recording uses Ctrl+X toggle, not mode enter
    assert hasattr(app, '_cast_rec_toggle')
    assert hasattr(app, '_cast_rec_capture')
    assert app.cast_recording is False


def test_step_no_crash():
    app = _make_app()
    app._cast_rec_start()
    assert app.cast_recording is True
    # Patch curses.pair_number to avoid initscr() requirement
    with unittest.mock.patch("curses.pair_number", return_value=0):
        with unittest.mock.patch("curses.pair_content", return_value=(0, 0)):
            app.cast_last_capture = 0.0
            for _ in range(10):
                app.cast_last_capture = 0.0
                app._cast_rec_capture()
    assert len(app.cast_frames) == 10


def test_exit_cleanup():
    app = _make_app()
    app._cast_rec_start()
    with unittest.mock.patch("curses.pair_number", return_value=0):
        with unittest.mock.patch("curses.pair_content", return_value=(0, 0)):
            app.cast_last_capture = 0.0
            app._cast_rec_capture()
    assert len(app.cast_frames) == 1
    app._cast_rec_stop()  # stop sets cast_recording=False and opens export menu
    assert app.cast_recording is False
    assert app.cast_export_menu is True
    app._cast_rec_discard()
    assert app.cast_frames == []
    assert app.cast_export_menu is False
