"""Tests for embryogenesis mode."""
import random

from tests.conftest import make_mock_app
from life.modes.embryogenesis import register, EMBRYO_PRESETS


class TestEmbryogenesis:
    def setup_method(self):
        random.seed(7)
        self.app = make_mock_app()
        register(type(self.app))
        self.app.embryo_mode = False
        self.app.embryo_menu = False
        self.app.embryo_running = False

    def test_all_presets_step(self):
        for i in range(len(EMBRYO_PRESETS)):
            self.app._embryo_init(i)
            for _ in range(60):
                self.app._embryo_step()
            assert len(self.app.embryo_cells) > 1

    def test_cells_never_overlap(self):
        """Movement and sorting must keep one cell per grid position."""
        for i in range(len(EMBRYO_PRESETS)):
            self.app._embryo_init(i)
            for _ in range(300):
                self.app._embryo_step()
            cells = self.app.embryo_cells
            assert len({(c.r, c.c) for c in cells}) == len(cells)

    def test_exit_keeps_app_flags(self):
        self.app._enter_embryo_mode()
        self.app._embryo_init(0)
        self.app._exit_embryo_mode()
        assert self.app.embryo_mode is False
        assert self.app.embryo_menu is False
        assert self.app.embryo_running is False
        assert "embryo_cells" not in vars(self.app)
