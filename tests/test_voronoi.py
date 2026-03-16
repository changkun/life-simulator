"""Tests for voronoi mode."""
import random
from tests.conftest import make_mock_app
from life.modes.voronoi import register


class TestVoronoi:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_voronoi_mode()
        assert self.app.voronoi_menu is True
        assert self.app.voronoi_menu_sel == 0

    def test_step_no_crash(self):
        self.app.voronoi_mode = True
        self.app.voronoi_menu_sel = 0
        self.app._voronoi_init(0)
        for _ in range(10):
            self.app._voronoi_step()
        assert self.app.voronoi_generation == 10

    def test_exit_cleanup(self):
        self.app.voronoi_mode = True
        self.app.voronoi_menu_sel = 0
        self.app._voronoi_init(0)
        self.app._voronoi_step()
        self.app._exit_voronoi_mode()
        assert self.app.voronoi_mode is False
        assert self.app.voronoi_menu is False
        assert self.app.voronoi_running is False
        assert self.app.voronoi_grid == []
        assert self.app.voronoi_seeds == []
