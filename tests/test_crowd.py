"""Tests for Crowd Dynamics & Evacuation mode."""
import random

from tests.conftest import make_mock_app
from life.modes.crowd import register, CROWD_PRESETS


def _make():
    app = make_mock_app()
    register(type(app))
    return app


def test_presets_init_and_step():
    random.seed(3)
    app = _make()
    for i in range(len(CROWD_PRESETS)):
        app._crowd_init(i)
        assert app.crowd_mode is True
        assert app.crowd_initial_count > 0
        for _ in range(5):
            app._crowd_step()
        assert app.crowd_generation == 5


def test_enter_and_exit():
    app = _make()
    app._enter_crowd_mode()
    assert app.crowd_menu is True
    app._crowd_init(0)
    app._exit_crowd_mode()
    assert app.crowd_mode is False and app.crowd_running is False


def _run(app, idx, steps):
    app._crowd_init(idx)
    for _ in range(steps):
        app._crowd_step()
    return app.crowd_escaped_count / app.crowd_initial_count


def test_boundary_and_mid_wall_exits_are_reachable():
    # Concert aims between two exits and Black Friday exits sit on the top
    # edge; both used to strand every agent.
    random.seed(5)
    app = _make()
    names = [p[0] for p in CROWD_PRESETS]
    for name in ("Concert Venue", "Black Friday Rush"):
        assert _run(app, names.index(name), 800) > 0.3, name


def test_counterflow_groups_cross_the_corridor():
    random.seed(5)
    app = _make()
    app._crowd_init([p[0] for p in CROWD_PRESETS].index("Counterflow Corridors"))
    for a in app.crowd_agents:
        if a.group == 0:
            assert a.target_x > app.crowd_cols / 2 > a.x
        else:
            assert a.target_x < app.crowd_cols / 2 < a.x
