"""Tests for quantum_walk mode."""
import random
from tests.conftest import make_mock_app
from life.modes.quantum_walk import register


class TestQuantumWalk:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_qwalk_mode()
        assert self.app.qwalk_menu is True
        assert self.app.qwalk_menu_sel == 0

    def test_step_no_crash(self):
        self.app.qwalk_mode = True
        self.app.qwalk_menu_sel = 0
        self.app._qwalk_init(0)
        for _ in range(10):
            self.app._qwalk_step()
        assert self.app.qwalk_generation == 10

    def test_exit_cleanup(self):
        self.app.qwalk_mode = True
        self.app.qwalk_menu_sel = 0
        self.app._qwalk_init(0)
        self.app._qwalk_step()
        self.app._exit_qwalk_mode()
        assert self.app.qwalk_mode is False
        assert self.app.qwalk_menu is False
        assert self.app.qwalk_running is False
        assert self.app.qwalk_amp_re == []
        assert self.app.qwalk_amp_im == []
        assert self.app.qwalk_prob == []
