"""Tests for life.modes.optics — Geometric Optics & Light mode."""
from tests.conftest import make_mock_app
from life.modes.optics import register, OPTICS_PRESETS


def _make_app():
    app = make_mock_app()
    app.optics_mode = False
    app.optics_menu = False
    app.optics_running = False
    register(type(app))
    return app


def test_all_presets_init_and_step():
    for idx in range(len(OPTICS_PRESETS)):
        app = _make_app()
        app._optics_init(idx)
        assert app.optics_ray_points
        for _ in range(10):
            app._optics_step()
        assert app.optics_generation == 10


def test_source_wobble_stays_near_preset_angle():
    """The source must oscillate around its preset angle, not drift away."""
    app = _make_app()
    app._optics_init(0)
    base = app.optics_sources[0][2]
    for _ in range(400):
        app._optics_step()
        assert abs(app.optics_sources[0][2] - base) <= 0.15 + 1e-9


def test_reset_restores_source_angle():
    app = _make_app()
    app._optics_init(1)
    base = app.optics_sources[0][2]
    for _ in range(50):
        app._optics_step()
    app._handle_optics_key(ord("r"))
    assert app.optics_sources[0][2] == base
