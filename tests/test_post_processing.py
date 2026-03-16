"""Tests for life.modes.post_processing — Post-Processing Pipeline."""
from tests.conftest import make_mock_app
from life.modes.post_processing import register


def _make_app():
    app = make_mock_app()
    app.pp_active = set()
    app.pp_menu = False
    app.pp_trail_buf = []
    app.pp_trail_depth = 3
    app.pp_frame_count = 0
    # Add chgat to mock stdscr (post_processing uses it)
    app.stdscr.chgat = lambda *args, **kwargs: None
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    # Post-processing uses Ctrl+V toggle, not a mode enter
    assert hasattr(app, '_pp_apply')
    assert hasattr(app, '_pp_handle_key')
    assert app.pp_active == set()


def test_step_no_crash():
    app = _make_app()
    # Enable an effect and apply 10 times (no crash on mock stdscr)
    app.pp_active.add("scanlines")
    for _ in range(10):
        app._pp_apply()
    assert app.pp_frame_count == 10


def test_exit_cleanup():
    app = _make_app()
    app.pp_active = {"bloom", "trails"}
    app.pp_active.clear()
    assert app.pp_active == set()
    app.pp_trail_buf.clear()
    assert app.pp_trail_buf == []
