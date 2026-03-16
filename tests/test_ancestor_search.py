"""Tests for ancestor_search mode."""
from tests.conftest import make_mock_app
from life.modes.ancestor_search import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_ancestor_search()
    assert app.anc_mode is True
    assert app.anc_menu is True


def test_step_no_crash():
    app = _make_app()
    app._enter_ancestor_search()
    # Load a preset to start search
    app._anc_load_preset(0)  # block
    assert app.anc_engine is not None
    for _ in range(10):
        app._anc_step()


def test_exit_cleanup():
    app = _make_app()
    app._enter_ancestor_search()
    app._anc_load_preset(0)
    app._exit_ancestor_search()
    assert app.anc_mode is False
    assert app.anc_engine is None
