"""Tests for life.modes.fluid_rope — Fluid Rope mode."""
from tests.conftest import make_mock_app
from life.modes.fluid_rope import register


def _make_app():
    app = make_mock_app()
    app.fluidrope_mode = False
    app.fluidrope_menu = False
    app.fluidrope_menu_sel = 0
    app.fluidrope_running = False
    app.fluidrope_dt = 0.02
    app.fluidrope_rope_segments = []
    app.fluidrope_pool = []
    app.fluidrope_trail = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_fluidrope_mode()
    assert app.fluidrope_menu is True


def test_step_no_crash():
    app = _make_app()
    app.fluidrope_mode = True
    app._fluidrope_init("honey")
    for _ in range(10):
        app._fluidrope_step()
    assert app.fluidrope_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.fluidrope_mode = True
    app._fluidrope_init("honey")
    app._exit_fluidrope_mode()
    assert app.fluidrope_mode is False
    assert app.fluidrope_rope_segments == []
