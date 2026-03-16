"""Tests for life.modes.flythrough_3d — 3D Terrain Flythrough mode."""
from tests.conftest import make_mock_app
from life.modes.flythrough_3d import register


def _make_app():
    app = make_mock_app()
    app.flythrough_mode = False
    app.flythrough_menu = False
    app.flythrough_menu_sel = 0
    app.flythrough_running = False
    app.flythrough_generation = 0
    app.flythrough_preset_name = ""
    app.flythrough_heightmap = []
    app.flythrough_map_size = 0
    app.flythrough_cam_x = 0.0
    app.flythrough_cam_y = 0.0
    app.flythrough_cam_z = 0.0
    app.flythrough_cam_yaw = 0.0
    app.flythrough_cam_pitch = -0.2
    app.flythrough_cam_speed = 0.5
    app.flythrough_fov = 1.2
    app.flythrough_time = 0.3
    app.flythrough_auto_time = True
    app.flythrough_time_speed = 0.002
    type(app).FLYTHROUGH_PRESETS = [
        ("Rolling Hills", "Gentle rolling terrain with grass and trees", "hills"),
        ("Mountains", "Sharp alpine peaks with snow caps", "mountains"),
        ("Canyon", "Deep canyon carved through mesa landscape", "canyon"),
        ("Islands", "Archipelago of volcanic islands", "islands"),
        ("Glacial Valley", "U-shaped valley with ice features", "glacial"),
        ("Alien World", "Bizarre alien terrain with strange formations", "alien"),
    ]
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_flythrough_mode()
    assert app.flythrough_menu is True
    assert app.flythrough_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.flythrough_mode = True
    app._flythrough_init(0)
    assert app.flythrough_mode is True
    assert app.flythrough_menu is False
    for _ in range(10):
        app._flythrough_step()
    assert app.flythrough_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.flythrough_mode = True
    app._flythrough_init(0)
    app._exit_flythrough_mode()
    assert app.flythrough_mode is False
    assert app.flythrough_menu is False
    assert app.flythrough_running is False
