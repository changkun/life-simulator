"""Tests for life.modes.butterfly_effect — Butterfly Effect mode."""
import pytest

from tests.conftest import make_mock_app
from life.modes.butterfly_effect import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app._butterfly_init()
    return app


def _start_running(app):
    app._enter_butterfly_mode()
    app._butterfly_handle_key(10)  # Enter: perturb the pick cell
    assert not app.butterfly_picking


def test_q_while_running_exits_mode_not_app():
    app = _make_app()
    _start_running(app)
    app._butterfly_handle_key(ord("q"))  # must not raise SystemExit
    assert app.butterfly_mode is False
    assert app.butterfly_grid is None


def test_step_diverges_after_perturbation():
    app = _make_app()
    app.grid.set_alive(5, 5)
    app.grid.set_alive(5, 6)
    app.grid.set_alive(5, 7)
    app.cursor_r, app.cursor_c = 6, 8
    _start_running(app)
    for _ in range(3):
        app._butterfly_handle_key(ord("n"))
    assert app.butterfly_steps_since_fork == 3
    assert app.butterfly_max_divergence > 0
