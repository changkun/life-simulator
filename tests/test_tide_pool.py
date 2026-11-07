"""Tests for Tide Pool & Intertidal Ecosystem mode."""
import random

import pytest

from tests.conftest import make_mock_app
from life.modes.tide_pool import register, TPOOL_PRESETS, SP_LIMPET


def _app(seed=1):
    random.seed(seed)
    app = make_mock_app()
    register(type(app))
    return app


class TestTidePool:
    def test_enter_exit(self):
        app = _app()
        app._enter_tpool_mode()
        assert app.tpool_menu is True
        app._tpool_init(0)
        assert app.tpool_menu is False
        app._exit_tpool_mode()
        assert app.tpool_mode is False
        assert app.tpool_running is False

    @pytest.mark.parametrize("idx", range(len(TPOOL_PRESETS)))
    def test_every_preset_steps(self, idx):
        app = _app(idx)
        app._tpool_init(idx)
        for _ in range(100):
            app._tpool_step()
        assert app.tpool_generation == 100
        assert app.tpool_sessile and app.tpool_mobile

    def test_mobile_population_is_capped(self):
        app = _app(3)
        app._tpool_init(0)
        cap = max(20, app.tpool_rows * app.tpool_cols // 20)
        for _ in range(1500):
            app._tpool_step()
        limpets = sum(1 for m in app.tpool_mobile if m.kind == SP_LIMPET)
        assert limpets <= cap

    @pytest.mark.parametrize("key", [ord("q"), 27])
    def test_quit_key_exits_mode(self, key):
        app = _app()
        app._enter_tpool_mode()
        app._tpool_init(0)
        assert app.tpool_mode is True
        app._handle_tpool_key(key)
        assert app.tpool_mode is False
