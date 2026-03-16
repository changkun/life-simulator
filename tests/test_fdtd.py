"""Tests for life.modes.fdtd — FDTD EM Waves mode."""
from tests.conftest import make_mock_app
from life.modes.fdtd import register


def _make_app():
    app = make_mock_app()
    app.fdtd_mode = False
    app.fdtd_menu = False
    app.fdtd_menu_sel = 0
    app.fdtd_running = False
    app.fdtd_generation = 0
    app.fdtd_preset_name = ""
    app.fdtd_rows = 0
    app.fdtd_cols = 0
    app.fdtd_steps_per_frame = 2
    app.fdtd_Ez = []
    app.fdtd_Hx = []
    app.fdtd_Hy = []
    app.fdtd_eps = []
    app.fdtd_sigma = []
    app.fdtd_sources = []
    app.fdtd_pml_width = 8
    app.fdtd_viz_mode = 0
    app.fdtd_freq = 0.15
    app.fdtd_courant = 0.5
    type(app).FDTD_PRESETS = [
        ("Point Source", "Single oscillating point source", "point"),
        ("Double Slit", "Wave diffraction through two slits", "double_slit"),
        ("Single Slit", "Diffraction through a single slit", "single_slit"),
        ("Waveguide", "EM wave confined in a metal waveguide", "waveguide"),
        ("Dielectric Lens", "Focusing by a convex dielectric lens", "lens"),
        ("Dipole Antenna", "Two sources with opposite phase", "dipole"),
        ("Phased Array", "Beam steering with phase-shifted sources", "phased_array"),
        ("Corner Reflector", "Reflection from a 90-degree corner", "corner_reflector"),
        ("Resonant Cavity", "Standing waves in a metal box", "cavity"),
        ("Scatterers", "Wave scattering off dielectric cylinders", "scatter"),
    ]
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_fdtd_mode()
    assert app.fdtd_menu is True
    assert app.fdtd_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.fdtd_mode = True
    app._fdtd_init(0)
    assert app.fdtd_mode is True
    assert app.fdtd_menu is False
    for _ in range(10):
        app._fdtd_step()
    assert app.fdtd_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.fdtd_mode = True
    app._fdtd_init(0)
    app._exit_fdtd_mode()
    assert app.fdtd_mode is False
    assert app.fdtd_menu is False
    assert app.fdtd_running is False
