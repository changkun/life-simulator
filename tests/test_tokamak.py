"""Tests for life.modes.tokamak — Tokamak Fusion Plasma Confinement."""
import random

from tests.conftest import make_mock_app
from life.modes.tokamak import register


def _make_app():
    app = make_mock_app(rows=24, cols=80)
    app.tokamak_mode = False
    app.tokamak_menu = False
    app.tokamak_running = False
    register(type(app))
    return app


def test_reset_clears_beta():
    """Restarting a preset must not show beta left over from the last run."""
    random.seed(2)
    app = _make_app()
    app._tokamak_init(3)
    for _ in range(5):
        app._tokamak_step()
    assert app.tokamak_beta > 0
    app._tokamak_init(3)
    assert app.tokamak_beta == 0.0
