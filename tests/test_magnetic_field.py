"""Tests for life.modes.magnetic_field — Magnetic Field Lines mode."""
from tests.conftest import make_mock_app
from life.modes.magnetic_field import register


def _make_app():
    app = make_mock_app()
    app.magfield_mode = False
    app.magfield_menu = False
    app.magfield_menu_sel = 0
    app.magfield_running = False
    app.magfield_generation = 0
    app.magfield_preset_name = ""
    app.magfield_rows = 0
    app.magfield_cols = 0
    app.magfield_steps_per_frame = 3
    app.magfield_dt = 0.02
    app.magfield_particles = []
    app.magfield_trails = []
    app.magfield_max_trail = 300
    app.magfield_Bz = 1.0
    app.magfield_Ex = 0.0
    app.magfield_Ey = 0.0
    app.magfield_field_type = 0
    app.magfield_show_field = True
    app.magfield_num_particles = 12
    app.magfield_viz_mode = 0
    type(app).MAGFIELD_PRESETS = [
        ("Cyclotron Orbits", "Circular orbits in uniform magnetic field", "cyclotron"),
        ("E x B Drift", "Crossed electric and magnetic fields", "exb"),
        ("Magnetic Bottle", "Mirror confinement with converging field lines", "bottle"),
        ("Dipole Field", "Planetary magnetosphere-like dipole", "dipole"),
        ("Quadrupole", "Linear focusing quadrupole field", "quadrupole"),
        ("Mixed Charges", "Positive and negative charges together", "mixed"),
        ("Magnetic Shear", "Spatially varying magnetic field", "shear"),
        ("Hall Effect", "Drift in crossed E and B fields", "hall"),
    ]
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_magfield_mode()
    assert app.magfield_menu is True
    assert app.magfield_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.magfield_mode = True
    app._magfield_init(0)
    assert app.magfield_mode is True
    assert app.magfield_menu is False
    for _ in range(10):
        app._magfield_step()
    assert app.magfield_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.magfield_mode = True
    app._magfield_init(0)
    app._exit_magfield_mode()
    assert app.magfield_mode is False
    assert app.magfield_menu is False
    assert app.magfield_running is False
