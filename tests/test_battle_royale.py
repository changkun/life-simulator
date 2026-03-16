"""Tests for life.modes.battle_royale — Battle Royale mode."""
import unittest.mock
from tests.conftest import make_mock_app
from life.modes.battle_royale import register


def _make_app():
    app = make_mock_app()
    app.br_mode = False
    app.br_menu = False
    app.br_menu_sel = 0
    app.br_menu_phase = 0
    app.br_custom_picks = []
    app.br_running = False
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_battle_royale()
    assert app.br_menu is True
    assert app.br_menu_phase == 0


def test_step_no_crash():
    app = _make_app()
    # _br_init calls curses.init_pair which needs a real curses screen
    # Patch it to avoid error
    with unittest.mock.patch("life.modes.battle_royale._init_br_colors"):
        app._br_init(["life", "highlife", "daynight", "seeds"])
    assert app.br_mode is True
    for _ in range(10):
        app._br_do_step()
    assert app.br_generation == 10


def test_exit_cleanup():
    app = _make_app()
    with unittest.mock.patch("life.modes.battle_royale._init_br_colors"):
        app._br_init(["life", "highlife", "daynight", "seeds"])
    app._exit_battle_royale()
    assert app.br_mode is False
    assert app.br_running is False
