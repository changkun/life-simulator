"""Tests for timeline_branch mode."""
from tests.conftest import make_mock_app
from life.modes.timeline_branch import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    # Additional attrs needed
    app._push_history = lambda: None
    app._record_pop = lambda: None
    return app


def test_enter():
    app = _make_app()
    app._tbranch_fork_from_current()
    assert app.tbranch_mode is True
    assert app.tbranch_grid is not None


def test_step_no_crash():
    app = _make_app()
    app._tbranch_fork_from_current()
    for _ in range(10):
        app._tbranch_step()
    assert app.tbranch_grid.generation > 0


def test_exit_cleanup():
    app = _make_app()
    app._tbranch_fork_from_current()
    app._tbranch_exit()
    assert app.tbranch_mode is False
    assert app.tbranch_grid is None
