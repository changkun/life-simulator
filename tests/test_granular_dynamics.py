"""Tests for Granular Dynamics mode."""
import curses
import random

from tests.conftest import make_mock_app
from life.modes import granular_dynamics as gd


def _make_app():
    random.seed(1)
    app = make_mock_app()
    gd.register(type(app))
    app.granular_steps_per_frame = 1
    return app


def test_init_resets_statistics():
    app = _make_app()
    app._granular_init(0)
    app.granular_kinetic_energy = 5.0
    app.granular_jammed_fraction = 1.0
    app.granular_max_force = 9.0
    app._granular_init(0)
    assert app.granular_kinetic_energy == 0.0
    assert app.granular_jammed_fraction == 0.0
    assert app.granular_max_force == 0.0


def test_click_adds_grains_up_to_the_cap(monkeypatch):
    app = _make_app()
    app._granular_init(4)
    monkeypatch.setattr(curses, "getmouse", lambda: (0, 10, 5, 0, 0))
    for _ in range(200):
        app._handle_granular_key(curses.KEY_MOUSE)
    assert len(app.granular_particles) <= gd.GRANULAR_MAX_PARTICLES + 12
    assert app.granular_num_particles == len(app.granular_particles)
