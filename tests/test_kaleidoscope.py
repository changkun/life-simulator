"""Tests for life.modes.kaleidoscope — Kaleidoscope mode."""
from tests.conftest import make_mock_app
from life.modes.kaleidoscope import register


def _make_app():
    app = make_mock_app()
    app.kaleido_mode = False
    app.kaleido_menu = False
    app.kaleido_menu_sel = 0
    app.kaleido_running = False
    app.kaleido_canvas = {}
    app.kaleido_seeds = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_kaleido_mode()
    assert app.kaleido_menu is True


def test_step_no_crash():
    app = _make_app()
    app.kaleido_mode = True
    app._kaleido_init("snowflake")
    for _ in range(10):
        app._kaleido_step()
    assert app.kaleido_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.kaleido_mode = True
    app._kaleido_init("snowflake")
    app._exit_kaleido_mode()
    assert app.kaleido_mode is False
    assert app.kaleido_canvas == {}
