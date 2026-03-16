"""Tests for life.modes.shader_toy — Shader Toy mode."""
from tests.conftest import make_mock_app
from life.modes.shader_toy import register


def _make_app():
    app = make_mock_app()
    app.shadertoy_mode = False
    app.shadertoy_menu = False
    app.shadertoy_menu_sel = 0
    app.shadertoy_running = False
    app.shadertoy_generation = 0
    app.shadertoy_preset_name = ""
    app.shadertoy_preset_idx = 0
    app.shadertoy_time = 0.0
    app.shadertoy_speed = 1.0
    app.shadertoy_param_a = 1.0
    app.shadertoy_param_b = 1.0
    app.shadertoy_color_mode = 0
    type(app).SHADERTOY_PRESETS = [
        ("Plasma Waves", "Overlapping sine waves create flowing plasma"),
        ("Tunnel Zoom", "Infinite tunnel zoom with angular patterns"),
        ("Metaballs", "Soft organic blob shapes merging and splitting"),
        ("Moire Rings", "Interference rings creating moire patterns"),
        ("Fractal Flame", "Iterated function system fractal art"),
        ("Warp Grid", "Warped checkerboard grid"),
        ("Lava Lamp", "Floating blobs with smooth contours"),
        ("Matrix Rain", "Digital rain columns"),
        ("Kaleidoscope", "Mirror-symmetry kaleidoscope"),
        ("Spiral Galaxy", "Rotating spiral arms"),
    ]
    type(app).SHADERTOY_SHADE_CHARS = " .:-=+*#%@"
    type(app).SHADERTOY_COLOR_NAMES = ["Rainbow", "Fire", "Ocean", "Mono"]
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_shadertoy_mode()
    assert app.shadertoy_menu is True
    assert app.shadertoy_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.shadertoy_mode = True
    app._shadertoy_init(0)
    assert app.shadertoy_mode is True
    assert app.shadertoy_menu is False
    for _ in range(10):
        app._shadertoy_step()
    assert app.shadertoy_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.shadertoy_mode = True
    app._shadertoy_init(0)
    app._exit_shadertoy_mode()
    assert app.shadertoy_mode is False
    assert app.shadertoy_menu is False
    assert app.shadertoy_running is False
