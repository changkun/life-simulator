"""Tests for Deep-Sea Bioluminescent Abyss mode."""
import curses
import random

import pytest

from tests.conftest import make_mock_app
from life.modes.deep_sea import register, DEEPSEA_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


class TestDeepSeaLifecycle:
    def test_exit_keeps_app_flags(self):
        app = _make_app()
        app._enter_deepsea_mode()
        app._deepsea_init(0)
        app.deepsea_running = True
        app._exit_deepsea_mode()
        assert app.deepsea_mode is False
        assert app.deepsea_menu is False
        assert app.deepsea_running is False
        assert "deepsea_creatures" not in vars(app)

    def test_reenter_after_exit(self):
        app = _make_app()
        app._enter_deepsea_mode()
        app._deepsea_init(1)
        app._exit_deepsea_mode()
        app._enter_deepsea_mode()
        assert app.deepsea_menu is True
        assert app.deepsea_menu_sel == 0

    @pytest.mark.parametrize("enter_key", [10, ord(" ")])
    def test_menu_start_keys(self, enter_key):
        app = _make_app()
        app._enter_deepsea_mode()
        app._handle_deepsea_menu_key(enter_key)
        assert app.deepsea_menu is False
        assert app.deepsea_running is True

    @pytest.mark.parametrize("idx", range(len(DEEPSEA_PRESETS)))
    def test_presets_step(self, idx):
        random.seed(idx)
        app = _make_app()
        app._deepsea_init(idx)
        for _ in range(30):
            app._deepsea_step()
        assert app.deepsea_generation == 30
