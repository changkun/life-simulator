"""Tests for cyclic_ca mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.cyclic_ca import register
from life.modes.sir_epidemic import CYCLIC_PRESETS, CYCLIC_COLORS


class TestCyclicCA:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.CYCLIC_PRESETS = CYCLIC_PRESETS
        cls.CYCLIC_COLORS = CYCLIC_COLORS
        # Instance attrs
        self.app.cyclic_mode = False
        self.app.cyclic_menu = False
        self.app.cyclic_menu_sel = 0
        self.app.cyclic_running = False
        self.app.cyclic_grid = []
        self.app.cyclic_steps_per_frame = 1

    def test_enter(self):
        self.app._enter_cyclic_mode()
        assert self.app.cyclic_menu is True

    def test_init(self):
        self.app.cyclic_mode = True
        self.app._cyclic_init(0)  # Classic Spirals
        assert self.app.cyclic_mode is True
        assert len(self.app.cyclic_grid) > 0
        assert self.app.cyclic_n_states == 8

    def test_step_no_crash(self):
        self.app.cyclic_mode = True
        self.app._cyclic_init(0)
        for _ in range(10):
            self.app._cyclic_step()
        assert self.app.cyclic_generation == 10

    def test_von_neumann_preset(self):
        """Test Von Neumann neighborhood preset."""
        self.app.cyclic_mode = True
        self.app._cyclic_init(4)  # Von Neumann
        assert self.app.cyclic_neighborhood == "von_neumann"
        self.app._cyclic_step()
        assert self.app.cyclic_generation == 1

    def test_all_presets(self):
        """Ensure all presets initialize without error."""
        for i in range(len(CYCLIC_PRESETS)):
            random.seed(42)
            self.app._cyclic_init(i)
            assert self.app.cyclic_mode is True
            self.app._cyclic_step()

    def test_exit_cleanup(self):
        self.app.cyclic_mode = True
        self.app._cyclic_init(0)
        self.app._exit_cyclic_mode()
        assert self.app.cyclic_mode is False
