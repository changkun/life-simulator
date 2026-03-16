"""Tests for self_modifying_rules mode."""
import curses
from unittest.mock import patch
from tests.conftest import make_mock_app
from life.modes.self_modifying_rules import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.smr_mode = False
    app.smr_menu = False
    app.smr_menu_sel = 0
    app.smr_running = False
    return app


def test_enter():
    app = _make_app()
    app._enter_smr_mode()
    assert app.smr_menu is True


def test_step_no_crash():
    app = _make_app()
    app.smr_mode = True
    with patch("life.modes.self_modifying_rules._init_smr_colors"):
        app._smr_init(0)
    assert app.smr_mode is True
    for _ in range(10):
        app._smr_step()


def test_exit_cleanup():
    app = _make_app()
    with patch("life.modes.self_modifying_rules._init_smr_colors"):
        app._smr_init(0)
    app._exit_smr_mode()
    assert app.smr_mode is False
