"""Tests for life.modes.mashup — Simulation Mashup mode."""
from tests.conftest import make_mock_app
from life.modes.mashup import register


def _make_app():
    app = make_mock_app()
    app.mashup_mode = False
    app.mashup_menu = False
    app.mashup_menu_sel = 0
    app.mashup_menu_phase = 0
    app.mashup_running = False
    app.mashup_sim_a = None
    app.mashup_sim_b = None
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_mashup_mode()
    assert app.mashup_menu is True
    assert app.mashup_menu_phase == 0


def test_step_no_crash():
    app = _make_app()
    app._mashup_init("gol", "wave")
    assert app.mashup_mode is True
    assert app.mashup_sim_a is not None
    assert app.mashup_sim_b is not None
    for _ in range(10):
        app._mashup_step()
    assert app.mashup_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app._mashup_init("gol", "wave")
    app._exit_mashup_mode()
    assert app.mashup_mode is False
    assert app.mashup_running is False
    assert app.mashup_sim_a is None
    assert app.mashup_sim_b is None
