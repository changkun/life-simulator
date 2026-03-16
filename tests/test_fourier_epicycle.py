"""Tests for life.modes.fourier_epicycle — Fourier Epicycle mode."""
from tests.conftest import make_mock_app
from life.modes.fourier_epicycle import register


def _make_app():
    app = make_mock_app()
    app.fourier_mode = False
    app.fourier_menu = False
    app.fourier_menu_sel = 0
    app.fourier_running = False
    app.fourier_phase = "menu"
    app.fourier_path = []
    app.fourier_coeffs = []
    app.fourier_trace = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_fourier_mode()
    assert app.fourier_menu is True


def test_step_no_crash():
    app = _make_app()
    app.fourier_mode = True
    app._fourier_init("circle")
    for _ in range(10):
        app._fourier_step()
    assert len(app.fourier_trace) == 10


def test_exit_cleanup():
    app = _make_app()
    app.fourier_mode = True
    app._fourier_init("circle")
    app._exit_fourier_mode()
    assert app.fourier_mode is False
    assert app.fourier_path == []
