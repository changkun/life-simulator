"""Tests for Ising Model mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.ising import register


class TestIsing:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._ising_init(0)
        assert self.app.ising_mode is True
        assert self.app.ising_generation == 0
        assert len(self.app.ising_grid) > 0
        assert self.app.ising_steps_per_frame == 1
        assert hasattr(self.app, 'ising_magnetization')
        assert hasattr(self.app, 'ising_energy')

    def test_step_no_crash(self):
        self.app._ising_init(0)
        for _ in range(10):
            self.app._ising_step()
        assert self.app.ising_generation == 10

    def test_exit_cleanup(self):
        self.app._ising_init(0)
        assert self.app.ising_mode is True
        self.app._exit_ising_mode()
        assert self.app.ising_mode is False
        assert self.app.ising_running is False
