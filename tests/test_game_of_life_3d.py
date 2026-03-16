"""Tests for life.modes.game_of_life_3d — 3D Game of Life mode."""
from tests.conftest import make_mock_app
from life.modes.game_of_life_3d import register


def _make_app():
    app = make_mock_app()
    app.gol3d_mode = False
    app.gol3d_menu = False
    app.gol3d_menu_sel = 0
    app.gol3d_running = False
    app.gol3d_generation = 0
    app.gol3d_preset_name = ""
    app.gol3d_size = 8  # use small grid for test speed
    app.gol3d_grid = []
    app.gol3d_population = 0
    app.gol3d_birth = set()
    app.gol3d_survive = set()
    app.gol3d_density = 0.0
    app.gol3d_cam_theta = 0.5
    app.gol3d_cam_phi = 0.5
    app.gol3d_cam_dist = 2.5
    app.gol3d_auto_rotate = True
    app.gol3d_rotate_speed = 0.02
    type(app).GOL3D_PRESETS = [
        ("5766", "B5/S6,7,8 — slow crystal growth", {5}, {6, 7, 8}, 0.15),
        ("Clouds", "B13-26/S14-25 — gas-like expansion", set(range(13, 27)), set(range(14, 26)), 0.4),
        ("Coral", "B5-8/S4-7 — organic branching", set(range(5, 9)), set(range(4, 8)), 0.2),
    ]
    type(app).GOL3D_SHADE_CHARS = " .:-=+*#%@"
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_gol3d_mode()
    assert app.gol3d_menu is True
    assert app.gol3d_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.gol3d_mode = True
    app._gol3d_init(0)
    assert app.gol3d_mode is True
    assert app.gol3d_menu is False
    for _ in range(10):
        app._gol3d_step()
    assert app.gol3d_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.gol3d_mode = True
    app._gol3d_init(0)
    app._exit_gol3d_mode()
    assert app.gol3d_mode is False
    assert app.gol3d_menu is False
    assert app.gol3d_running is False
