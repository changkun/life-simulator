"""Tests for life.modes.ant_farm — Ant Farm mode."""
from tests.conftest import make_mock_app
from life.modes.ant_farm import register


def _make_app():
    app = make_mock_app()
    app.antfarm_mode = False
    app.antfarm_menu = False
    app.antfarm_menu_sel = 0
    app.antfarm_running = False
    app.antfarm_speed = 1
    app.antfarm_show_info = False
    app.antfarm_ants = []
    app.antfarm_grid = []
    app.antfarm_pheromone_food = []
    app.antfarm_pheromone_home = []
    app.antfarm_food_surface = []
    app.antfarm_rain_drops = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_antfarm_mode()
    assert app.antfarm_menu is True


def test_step_no_crash():
    app = _make_app()
    app.antfarm_mode = True
    app._antfarm_init("classic")
    for _ in range(10):
        app._antfarm_step()
    assert app.antfarm_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.antfarm_mode = True
    app._antfarm_init("classic")
    app._exit_antfarm_mode()
    assert app.antfarm_mode is False
    assert app.antfarm_ants == []
