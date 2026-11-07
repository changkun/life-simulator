"""Tests for ferrofluid mode."""
import random

from tests.conftest import make_mock_app
from life.modes.ferrofluid import register, FERROFLUID_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def _mean(h):
    return sum(map(sum, h)) / (len(h) * len(h[0]))


class TestFerrofluidEvolution:
    def setup_method(self):
        random.seed(42)
        self.app = _make_app()

    def test_every_preset_stays_between_empty_and_full(self):
        """No preset floods the grid or drains it empty."""
        for idx in range(len(FERROFLUID_PRESETS)):
            self.app._ferrofluid_init(idx)
            start = self.app.ferrofluid_h_target
            for _ in range(150):
                self.app._ferrofluid_step()
            h = self.app.ferrofluid_h
            assert abs(_mean(h) - start) < 0.05, FERROFLUID_PRESETS[idx][0]
            full = sum(1 for row in h for v in row if v > 0.99)
            assert full < 0.5 * len(h) * len(h[0]), FERROFLUID_PRESETS[idx][0]

    def test_supercritical_surface_develops_relief(self):
        self.app._ferrofluid_init(0)
        for _ in range(150):
            self.app._ferrofluid_step()
        h = self.app.ferrofluid_h
        assert max(map(max, h)) - min(map(min, h)) > 0.3

    def test_perturb_raises_volume_target(self):
        self.app._ferrofluid_init(0)
        before = self.app.ferrofluid_h_target
        self.app._ferrofluid_perturb(8, 8)
        assert self.app.ferrofluid_h_target > before
