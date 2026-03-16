"""Tests for Lightning mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.lightning import register


class TestLightning:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._lightning_init(0)
        assert self.app.lightning_mode is True
        assert self.app.lightning_generation == 0
        assert len(self.app.lightning_grid) > 0
        assert self.app.lightning_steps_per_frame == 1
        assert self.app.lightning_channel_count == 1

    def test_step_no_crash(self):
        self.app._lightning_init(0)
        for _ in range(10):
            self.app._lightning_step()
        assert self.app.lightning_generation == 10

    def test_exit_cleanup(self):
        self.app._lightning_init(0)
        assert self.app.lightning_mode is True
        self.app._exit_lightning_mode()
        assert self.app.lightning_mode is False
        assert self.app.lightning_running is False
