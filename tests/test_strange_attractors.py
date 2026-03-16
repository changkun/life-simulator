"""Tests for strange_attractors mode."""
import random
from tests.conftest import make_mock_app
from life.modes.strange_attractors import register


class TestStrangeAttractors:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))
        # attractor_num_particles is normally set in app.__init__
        self.app.attractor_num_particles = 20

    def test_enter(self):
        self.app._enter_attractor_mode()
        assert self.app.attractor_menu is True
        assert self.app.attractor_menu_sel == 0

    def test_step_no_crash(self):
        self.app.attractor_mode = True
        self.app.attractor_menu_sel = 0
        self.app._attractor_init(0)
        for _ in range(10):
            self.app._attractor_step()
        assert self.app.attractor_generation == 10

    def test_exit_cleanup(self):
        self.app.attractor_mode = True
        self.app.attractor_menu_sel = 0
        self.app._attractor_init(0)
        self.app._attractor_step()
        self.app._exit_attractor_mode()
        assert self.app.attractor_mode is False
        assert self.app.attractor_menu is False
        assert self.app.attractor_running is False
        assert self.app.attractor_density == []
        assert self.app.attractor_trails == []
