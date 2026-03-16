"""Tests for Turmites mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.turmites import register


class TestTurmites:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    def test_enter(self):
        self.app._enter_turmite_mode()
        assert self.app.turmite_menu is True
        assert self.app.turmite_steps_per_frame == 1
        # Simulate selecting first preset and starting
        name, desc, nc, ns, table = self.app.TURMITE_PRESETS[0]
        self.app.turmite_num_colors = nc
        self.app.turmite_num_states = ns
        self.app.turmite_table = [row[:] for row in table]
        self.app.turmite_preset_name = name
        self.app.turmite_menu = False
        self.app.turmite_mode = True
        self.app.turmite_running = False
        self.app._turmite_init()
        assert self.app.turmite_mode is True
        assert self.app.turmite_step_count == 0
        assert len(self.app.turmite_ants) == 1

    def test_step_no_crash(self):
        self.app._enter_turmite_mode()
        name, desc, nc, ns, table = self.app.TURMITE_PRESETS[0]
        self.app.turmite_num_colors = nc
        self.app.turmite_num_states = ns
        self.app.turmite_table = [row[:] for row in table]
        self.app.turmite_preset_name = name
        self.app.turmite_mode = True
        self.app.turmite_menu = False
        self.app._turmite_init()
        for _ in range(10):
            self.app._turmite_step()
        assert self.app.turmite_step_count == 10

    def test_exit_cleanup(self):
        self.app._enter_turmite_mode()
        name, desc, nc, ns, table = self.app.TURMITE_PRESETS[0]
        self.app.turmite_num_colors = nc
        self.app.turmite_num_states = ns
        self.app.turmite_table = [row[:] for row in table]
        self.app.turmite_preset_name = name
        self.app.turmite_mode = True
        self.app.turmite_menu = False
        self.app._turmite_init()
        self.app._exit_turmite_mode()
        assert self.app.turmite_mode is False
        assert self.app.turmite_running is False
