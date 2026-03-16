"""Tests for sandpile mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.sandpile import register
from life.modes.dla import SANDPILE_PRESETS, SANDPILE_CHARS, SANDPILE_OVERFLOW_CHAR
from life.constants import SPEEDS


class TestSandpile:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.SANDPILE_PRESETS = SANDPILE_PRESETS
        cls.SANDPILE_CHARS = SANDPILE_CHARS
        cls.SANDPILE_OVERFLOW_CHAR = SANDPILE_OVERFLOW_CHAR
        # Instance attrs
        self.app.sandpile_mode = False
        self.app.sandpile_menu = False
        self.app.sandpile_menu_sel = 0
        self.app.sandpile_running = False
        self.app.sandpile_grid = []
        self.app.sandpile_steps_per_frame = 1

    def test_enter(self):
        self.app._enter_sandpile_mode()
        assert self.app.sandpile_menu is True

    def test_init_single_tower(self):
        self.app.sandpile_mode = True
        self.app._sandpile_init(0)  # Single Tower
        assert self.app.sandpile_mode is True
        assert len(self.app.sandpile_grid) > 0

    def test_init_big_pile(self):
        self.app.sandpile_mode = True
        self.app._sandpile_init(1)  # Big Pile
        assert self.app.sandpile_mode is True
        cr = self.app.sandpile_rows // 2
        cc = self.app.sandpile_cols // 2
        assert self.app.sandpile_grid[cr][cc] == 10000

    def test_step_no_crash(self):
        self.app.sandpile_mode = True
        self.app._sandpile_init(0)  # Single Tower
        for _ in range(10):
            self.app._sandpile_step()
        assert self.app.sandpile_generation == 10

    def test_toppling(self):
        """Verify grains topple correctly."""
        self.app.sandpile_mode = True
        self.app._sandpile_init(1)  # Big Pile (10000 grains)
        self.app._sandpile_step()
        assert self.app.sandpile_topples > 0

    def test_exit_cleanup(self):
        self.app.sandpile_mode = True
        self.app._sandpile_init(0)
        self.app._exit_sandpile_mode()
        assert self.app.sandpile_mode is False
