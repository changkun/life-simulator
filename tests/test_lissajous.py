"""Tests for life.modes.lissajous — Lissajous Curve mode."""
from tests.conftest import make_mock_app
from life.modes.lissajous import register


def _make_app():
    app = make_mock_app()
    app.lissajous_mode = False
    app.lissajous_menu = False
    app.lissajous_menu_sel = 0
    app.lissajous_running = False
    app.lissajous_show_info = False
    app.lissajous_trail = []
    app.lissajous_canvas = {}
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_lissajous_mode()
    assert app.lissajous_menu is True


def test_step_no_crash():
    app = _make_app()
    app.lissajous_mode = True
    app._lissajous_init("classic_3_2")
    for _ in range(10):
        app._lissajous_step()
    assert app.lissajous_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.lissajous_mode = True
    app._lissajous_init("classic_3_2")
    app._exit_lissajous_mode()
    assert app.lissajous_mode is False
    assert app.lissajous_trail == []
