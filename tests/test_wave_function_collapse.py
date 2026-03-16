"""Tests for wave_function_collapse mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.wave_function_collapse import register


class TestWFC:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        # WFC_PRESETS and WFC_TILE_CHARS are class-level attrs in App
        # We need to set them here since we use a mock App
        cls.WFC_PRESETS = [
            ("Island", "Land masses surrounded by ocean",
             5, ["water", "sand", "grass", "forest", "mountain"],
             {
                 0: {"N": {0, 1}, "S": {0, 1}, "E": {0, 1}, "W": {0, 1}},
                 1: {"N": {0, 1, 2}, "S": {0, 1, 2}, "E": {0, 1, 2}, "W": {0, 1, 2}},
                 2: {"N": {1, 2, 3}, "S": {1, 2, 3}, "E": {1, 2, 3}, "W": {1, 2, 3}},
                 3: {"N": {2, 3, 4}, "S": {2, 3, 4}, "E": {2, 3, 4}, "W": {2, 3, 4}},
                 4: {"N": {3, 4}, "S": {3, 4}, "E": {3, 4}, "W": {3, 4}},
             }),
        ]
        cls.WFC_TILE_CHARS = [
            ("░░", 2), ("██", 4), ("▓▓", 3), ("╬╬", 1), ("∧∧", 6),
            ("~~", 4), ("##", 5), ("⌂⌂", 7), ("≈≈", 4), ("··", 2),
        ]
        cls.WFC_PRESET_TILES = [
            [1, 2, 0, 3, 4],
        ]
        cls.WFC_UNCOLLAPSED_CHAR = "??"
        # Instance attrs
        self.app.wfc_mode = False
        self.app.wfc_menu = False
        self.app.wfc_menu_sel = 0
        self.app.wfc_running = False
        self.app.wfc_grid = []
        self.app.wfc_collapsed = []
        self.app.wfc_steps_per_frame = 1

    def test_enter(self):
        self.app._enter_wfc_mode()
        assert self.app.wfc_menu is True

    def test_init(self):
        self.app.wfc_mode = True
        self.app._wfc_init(0)
        assert self.app.wfc_mode is True
        assert self.app.wfc_menu is False
        assert len(self.app.wfc_grid) > 0

    def test_step_no_crash(self):
        self.app.wfc_mode = True
        self.app._wfc_init(0)
        for _ in range(10):
            self.app._wfc_step()
        assert self.app.wfc_generation >= 0

    def test_exit_cleanup(self):
        self.app.wfc_mode = True
        self.app._wfc_init(0)
        self.app._exit_wfc_mode()
        assert self.app.wfc_mode is False
