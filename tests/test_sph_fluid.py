"""Tests for life.modes.sph_fluid — SPH Fluid mode."""
from tests.conftest import make_mock_app
from life.modes.sph_fluid import register


def _make_app():
    app = make_mock_app()
    app.sph_mode = False
    app.sph_menu = False
    app.sph_menu_sel = 0
    app.sph_running = False
    app.sph_generation = 0
    app.sph_preset_name = ""
    app.sph_rows = 0
    app.sph_cols = 0
    app.sph_gravity = 9.8
    app.sph_rest_density = 1000.0
    app.sph_gas_const = 2000.0
    app.sph_h = 1.5
    app.sph_mass = 1.0
    app.sph_viscosity = 250.0
    app.sph_dt = 0.003
    app.sph_damping = 0.5
    app.sph_steps_per_frame = 3
    app.sph_particles = []
    app.sph_num_particles = 0
    app.sph_viz_mode = 0
    type(app).SPH_PRESETS = [
        ("Dam Break", "Column of water collapses sideways", "dam"),
        ("Double Dam", "Two water columns collide", "double_dam"),
        ("Drop Impact", "Block of fluid falls into pool", "drop"),
        ("Rain", "Scattered droplets fall under gravity", "rain"),
        ("Wave Pool", "Tilted water surface generates waves", "wave"),
        ("Fountain", "Upward jet creates a fountain", "fountain"),
    ]
    type(app).SPH_CHARS = " .:-=+*#%@"
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_sph_mode()
    assert app.sph_menu is True
    assert app.sph_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.sph_mode = True
    # Use "rain" preset for fewer particles
    app._sph_init(3)
    assert app.sph_mode is True
    assert app.sph_menu is False
    for _ in range(10):
        app._sph_step()
    assert app.sph_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.sph_mode = True
    app._sph_init(3)
    app._exit_sph_mode()
    assert app.sph_mode is False
    assert app.sph_menu is False
    assert app.sph_running is False
