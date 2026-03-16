"""Tests for life.modes.ray_marching — Ray Marching mode."""
from tests.conftest import make_mock_app
from life.modes.ray_marching import register


def _make_app():
    app = make_mock_app()
    app.raymarch_mode = False
    app.raymarch_menu = False
    app.raymarch_menu_sel = 0
    app.raymarch_running = False
    app.raymarch_generation = 0
    app.raymarch_scene_name = ""
    app.raymarch_scene = ""
    app.raymarch_cam_theta = 0.0
    app.raymarch_cam_phi = 0.4
    app.raymarch_cam_dist = 4.0
    app.raymarch_auto_rotate = True
    app.raymarch_rotate_speed = 0.03
    app.raymarch_light_theta = 0.8
    app.raymarch_light_phi = 0.6
    app.raymarch_shadows = True
    app.raymarch_mandelbulb_power = 8.0
    type(app).RAYMARCH_PRESETS = [
        ("Sphere", "Perfect sphere with Phong shading", "sphere"),
        ("Torus", "Donut-shaped torus", "torus"),
        ("Multi-Object", "Sphere + torus + box scene", "multi"),
        ("Mandelbulb", "3D Mandelbrot fractal", "mandelbulb"),
        ("Infinite Spheres", "Repeating spheres via domain repetition", "infinite"),
        ("Smooth Blend", "Two spheres with smooth union", "blend"),
    ]
    type(app).RAYMARCH_SHADE_CHARS = " .:-=+*#%@"
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_raymarch_mode()
    assert app.raymarch_menu is True
    assert app.raymarch_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.raymarch_mode = True
    app._raymarch_init(0)
    assert app.raymarch_mode is True
    assert app.raymarch_menu is False
    for _ in range(10):
        app._raymarch_step()
    assert app.raymarch_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.raymarch_mode = True
    app._raymarch_init(0)
    app._exit_raymarch_mode()
    assert app.raymarch_mode is False
    assert app.raymarch_menu is False
    assert app.raymarch_running is False
