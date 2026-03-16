"""Tests for life.modes.aquarium — ASCII Aquarium mode."""
from tests.conftest import make_mock_app
from life.modes.aquarium import register


def _make_app():
    app = make_mock_app()
    app.aquarium_mode = False
    app.aquarium_menu = False
    app.aquarium_menu_sel = 0
    app.aquarium_running = False
    app.aquarium_speed = 1
    app.aquarium_show_info = False
    app.aquarium_fish = []
    app.aquarium_seaweed = []
    app.aquarium_bubbles = []
    app.aquarium_food = []
    app.aquarium_sand = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_aquarium_mode()
    assert app.aquarium_menu is True


def test_step_no_crash():
    app = _make_app()
    app.aquarium_mode = True
    app._aquarium_init("tropical")
    for _ in range(10):
        app._aquarium_step()
    assert app.aquarium_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.aquarium_mode = True
    app._aquarium_init("tropical")
    app._exit_aquarium_mode()
    assert app.aquarium_mode is False
    assert app.aquarium_fish == []
