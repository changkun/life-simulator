"""Tests for hex_grid mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.hex_grid import register


class TestHexGrid:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_hex_browser()
        assert self.app.hex_mode is True
        assert self.app.grid.hex_mode is True
        assert self.app.grid.birth == {2}
        assert self.app.grid.survival == {3, 4}

    def test_step_no_crash(self):
        self.app._enter_hex_browser()
        # The hex mode uses the grid's step, seed some cells
        self.app.grid.set_alive(5, 5)
        self.app.grid.set_alive(5, 6)
        self.app.grid.set_alive(6, 5)
        for _ in range(10):
            self.app.grid.step()

    def test_exit_cleanup(self):
        self.app._enter_hex_browser()
        self.app._exit_hex_browser()
        assert self.app.hex_mode is False
        assert self.app.grid.hex_mode is False
        assert self.app.grid.birth == {3}
        assert self.app.grid.survival == {2, 3}
