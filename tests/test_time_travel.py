"""Tests for life.modes.time_travel — Universal Time-Travel History Scrubber."""
from tests.conftest import make_mock_app
from life.modes.time_travel import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    # Time travel is a cross-cutting feature, no enter menu.
    # Test that methods are bound.
    assert hasattr(app, '_tt_push')
    assert hasattr(app, '_tt_rewind')
    assert hasattr(app, '_tt_handle_key')


def test_step_no_crash():
    app = _make_app()
    # Push some snapshots, rewind, step forward
    # Simulate no active mode prefix (GoL-like), should do nothing
    for _ in range(10):
        app._tt_auto_record()
    # No mode prefix → no recording happens
    assert len(app.tt_history) == 0


def test_exit_cleanup():
    app = _make_app()
    # Time travel has no exit, just clear history
    app.tt_history = [{"_prefix": "test", "test_val": i} for i in range(5)]
    app.tt_pos = 2
    app._tt_restore(app.tt_history[0])
    # History remains, pos remains
    assert app.tt_pos == 2
    # Clear manually
    app.tt_history.clear()
    app.tt_pos = None
    assert app.tt_history == []
    assert app.tt_pos is None
