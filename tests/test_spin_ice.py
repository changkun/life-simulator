"""Tests for spin_ice mode."""
from tests.conftest import make_mock_app
from life.modes.spin_ice import register, SPINICE_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.spinice_mode = False
    app.spinice_menu = False
    app.spinice_menu_sel = 0
    app.spinice_running = False
    return app


def test_ice_presets_start_in_ice_state():
    app = _make_app()
    for idx, (_n, _d, pid) in enumerate(SPINICE_PRESETS):
        if pid in ("equilibrium", "field_quench", "pauling"):
            app._spinice_init(idx)
            # Only the boundary may hold charge; the interior is 2-in/2-out.
            for r in range(1, app.spinice_vrows - 1):
                for c in range(1, app.spinice_vcols - 1):
                    assert app._vertex_charge(r, c) == 0, (pid, r, c)


def test_step_no_crash():
    app = _make_app()
    for idx in range(len(SPINICE_PRESETS)):
        app._spinice_init(idx)
        for _ in range(5):
            app._spinice_step()
