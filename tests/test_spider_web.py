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


class TestSwebSilk:
    def test_silk_reserve_never_negative(self):
        random.seed(5)
        app = _make_app()
        bonanza = next(i for i, p in enumerate(SWEB_PRESETS) if p[2] == "bonanza")
        app._sweb_init(bonanza)
        for _ in range(3000):
            app._sweb_step()
            assert app.sweb_spider.silk_reserve >= 0.0


class TestSwebPrey:
    def test_spider_target_follows_prey_across_cleanup(self):
        from life.modes.spider_web import _Prey, SP_RUSHING
        random.seed(5)
        app = _make_app()
        app._sweb_init(0)
        gone = _Prey(1.0, 1.0, 0)
        gone.alive = False
        keep = _Prey(app.sweb_cx, app.sweb_cy, 0)
        keep.trapped = True
        keep.node_idx = 0
        app.sweb_prey = [gone, keep]
        app.sweb_spider.state = SP_RUSHING
        app.sweb_spider.target_prey = 1
        app.sweb_prey_rate = 0.0
        app._sweb_step()
        assert app.sweb_prey == [keep]
        assert app.sweb_spider.target_prey == 0
