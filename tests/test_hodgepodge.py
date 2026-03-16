"""Tests for Hodgepodge Machine mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.hodgepodge import register


class TestHodgepodge:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._hodge_init(0)
        assert self.app.hodge_mode is True
        assert self.app.hodge_generation == 0
        assert len(self.app.hodge_grid) > 0
        assert self.app.hodge_steps_per_frame == 1

    def test_step_no_crash(self):
        self.app._hodge_init(0)
        for _ in range(10):
            self.app._hodge_step()
        assert self.app.hodge_generation == 10

    def test_exit_cleanup(self):
        self.app._hodge_init(0)
        assert self.app.hodge_mode is True
        self.app._exit_hodge_mode()
        assert self.app.hodge_mode is False
        assert self.app.hodge_running is False
