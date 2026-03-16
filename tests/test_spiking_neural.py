"""Tests for spiking_neural mode."""
import random
from tests.conftest import make_mock_app
from life.modes.spiking_neural import register


class TestSpikingNeural:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_snn_mode()
        assert self.app.snn_menu is True
        assert self.app.snn_menu_sel == 0

    def test_step_no_crash(self):
        self.app.snn_mode = True
        self.app.snn_menu_sel = 0
        self.app._snn_init(0)
        for _ in range(10):
            self.app._snn_step()
        assert self.app.snn_generation == 10

    def test_exit_cleanup(self):
        self.app.snn_mode = True
        self.app.snn_menu_sel = 0
        self.app._snn_init(0)
        self.app._snn_step()
        self.app._exit_snn_mode()
        assert self.app.snn_mode is False
        assert self.app.snn_menu is False
        assert self.app.snn_running is False
        assert self.app.snn_v == []
        assert self.app.snn_u == []
        assert self.app.snn_fired == []
        assert self.app.snn_fire_history == []
