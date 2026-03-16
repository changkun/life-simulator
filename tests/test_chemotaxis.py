"""Tests for chemotaxis mode."""
import random
from tests.conftest import make_mock_app
from life.modes.chemotaxis import register


class TestChemotaxis:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_chemo_mode()
        assert self.app.chemo_menu is True
        assert self.app.chemo_menu_sel == 0

    def test_step_no_crash(self):
        self.app.chemo_mode = True
        self.app.chemo_menu_sel = 0
        self.app._chemo_init(0)
        for _ in range(10):
            self.app._chemo_step()
        assert self.app.chemo_generation == 10

    def test_exit_cleanup(self):
        self.app.chemo_mode = True
        self.app.chemo_menu_sel = 0
        self.app._chemo_init(0)
        self.app._chemo_step()
        self.app._exit_chemo_mode()
        assert self.app.chemo_mode is False
        assert self.app.chemo_menu is False
        assert self.app.chemo_running is False
        assert self.app.chemo_bacteria == []
        assert self.app.chemo_nutrient == []
        assert self.app.chemo_signal == []
