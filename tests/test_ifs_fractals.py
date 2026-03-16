"""Tests for ifs_fractals mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.ifs_fractals import register


IFS_PRESETS = [
    ("Sierpinski", "Sierpinski triangle via chaos game", "sierpinski"),
    ("Fern", "Barnsley fern IFS", "fern"),
]


class TestIFSFractals:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.IFS_PRESETS = IFS_PRESETS
        register(cls)

    def test_enter(self):
        self.app._enter_ifs_mode()
        assert self.app.ifs_menu is True
        assert self.app.ifs_menu_sel == 0

    def test_step_no_crash(self):
        self.app.ifs_mode = True
        self.app.ifs_running = False
        self.app._ifs_init(0)
        for _ in range(10):
            self.app._ifs_step()
        assert self.app.ifs_generation >= 10

    def test_exit_cleanup(self):
        self.app.ifs_mode = True
        self.app._ifs_init(0)
        self.app._exit_ifs_mode()
        assert self.app.ifs_mode is False
        assert self.app.ifs_menu is False
        assert self.app.ifs_running is False
        assert self.app.ifs_points == []
