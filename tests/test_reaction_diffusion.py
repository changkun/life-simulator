"""Tests for reaction_diffusion mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.reaction_diffusion import register


RD_PRESETS = [
    ("Coral Growth", "Branching coral-like tendrils", 0.0545, 0.062),
    ("Mitosis", "Self-replicating spots", 0.0367, 0.0649),
    ("Spots", "Circular spots", 0.035, 0.065),
]

RD_DENSITY = ["  ", "\u2591\u2591", "\u2592\u2592", "\u2593\u2593", "\u2588\u2588"]


class TestReactionDiffusion:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.RD_PRESETS = RD_PRESETS
        cls.RD_DENSITY = RD_DENSITY
        # Set instance defaults matching app.py
        self.app.rd_Du = 0.16
        self.app.rd_Dv = 0.08
        self.app.rd_dt = 1.0
        self.app.rd_steps_per_frame = 4
        self.app.rd_preset_name = ""
        self.app.rd_feed = 0.035
        self.app.rd_kill = 0.065
        register(cls)

    def test_enter(self):
        self.app._enter_rd_mode()
        assert self.app.rd_menu is True
        assert self.app.rd_menu_sel == 0

    def test_init(self):
        self.app._rd_init(0)
        assert self.app.rd_mode is True
        assert self.app.rd_menu is False
        assert self.app.rd_generation == 0
        assert len(self.app.rd_U) > 0
        assert len(self.app.rd_V) > 0
        assert self.app.rd_feed == 0.0545
        assert self.app.rd_kill == 0.062

    def test_step_no_crash(self):
        self.app._rd_init(0)
        for _ in range(10):
            self.app._rd_step()
        assert self.app.rd_generation == 10

    def test_step_values_in_range(self):
        self.app._rd_init(0)
        for _ in range(5):
            self.app._rd_step()
        for row in self.app.rd_U:
            for val in row:
                assert 0.0 <= val <= 1.0
        for row in self.app.rd_V:
            for val in row:
                assert 0.0 <= val <= 1.0

    def test_exit_cleanup(self):
        self.app._rd_init(0)
        self.app._rd_step()
        self.app._exit_rd_mode()
        assert self.app.rd_mode is False
        assert self.app.rd_menu is False
        assert self.app.rd_running is False
        assert self.app.rd_U == []
        assert self.app.rd_V == []
