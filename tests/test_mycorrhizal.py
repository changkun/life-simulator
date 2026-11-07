"""Tests for the Mycorrhizal Network & Wood Wide Web mode."""
import random

from tests.conftest import make_mock_app
from life.modes.mycorrhizal import register, MYCO_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


class TestMycoLifecycle:
    def setup_method(self):
        random.seed(7)
        self.app = _make_app()

    def test_exit_keeps_base_flags(self):
        """Exit must leave the flags the App constructor defines."""
        self.app._enter_myco_mode()
        self.app._myco_init(0)
        self.app.myco_running = True
        self.app._exit_myco_mode()
        assert self.app.myco_mode is False
        assert self.app.myco_menu is False
        assert self.app.myco_running is False
        assert "myco_trees" not in vars(self.app)

    def test_reenter_shows_menu(self):
        self.app._enter_myco_mode()
        self.app._myco_init(0)
        self.app._exit_myco_mode()
        self.app._enter_myco_mode()
        assert self.app.myco_mode is True
        assert self.app.myco_menu is True
        assert self.app.myco_menu_sel == 0

    def test_presets_evolve(self):
        for idx in range(len(MYCO_PRESETS)):
            self.app._myco_init(idx)
            for _ in range(150):
                self.app._myco_step()
            assert self.app.myco_generation == 150
            assert self.app.myco_trees
