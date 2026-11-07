"""Tests for the Spider Orb Web Construction & Prey Capture mode."""
import random

from tests.conftest import make_mock_app
from life.modes.spider_web import register, SWEB_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


class TestSwebLifecycle:
    def setup_method(self):
        random.seed(11)
        self.app = _make_app()

    def test_exit_keeps_base_flags(self):
        """Exit must leave the flags the App constructor defines."""
        self.app._enter_sweb_mode()
        self.app._sweb_init(0)
        self.app.sweb_running = True
        self.app._exit_sweb_mode()
        assert self.app.sweb_mode is False
        assert self.app.sweb_menu is False
        assert self.app.sweb_running is False
        assert "sweb_nodes" not in vars(self.app)

    def test_reenter_shows_menu(self):
        self.app._enter_sweb_mode()
        self.app._sweb_init(0)
        self.app._exit_sweb_mode()
        self.app._enter_sweb_mode()
        assert self.app.sweb_mode is True
        assert self.app.sweb_menu is True
        assert self.app.sweb_menu_sel == 0

    def test_presets_run(self):
        for idx in range(len(SWEB_PRESETS)):
            self.app._sweb_init(idx)
            for _ in range(200):
                self.app._sweb_step()
            assert self.app.sweb_generation == 200
