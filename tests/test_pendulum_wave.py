"""Tests for life.modes.pendulum_wave — Pendulum Wave mode."""
from tests.conftest import make_mock_app
from life.modes.pendulum_wave import register


def _make_app():
    app = make_mock_app()
    app.pwave_mode = False
    app.pwave_menu = False
    app.pwave_menu_sel = 0
    app.pwave_running = False
    app.pwave_max_trail = 40
    app.pwave_lengths = []
    app.pwave_angles = []
    app.pwave_trail = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_pwave_mode()
    assert app.pwave_menu is True


def test_step_no_crash():
    app = _make_app()
    app.pwave_mode = True
    app.pwave_preset_name = "classic"
    app._pwave_init("classic")
    for _ in range(10):
        app._pwave_step()
    assert app.pwave_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.pwave_mode = True
    app.pwave_preset_name = "classic"
    app._pwave_init("classic")
    app._exit_pwave_mode()
    assert app.pwave_mode is False
    assert app.pwave_lengths == []
