"""Tests for life.modes.accretion — Planetary Accretion mode."""
import pytest

from tests.conftest import make_mock_app
from life.modes.accretion import ACCRETION_PRESETS, _make_body, register


def _make_app():
    app = make_mock_app()
    app.accretion_mode = False
    app.accretion_menu = False
    app.accretion_menu_sel = 0
    app.accretion_running = False
    register(type(app))
    return app


@pytest.mark.parametrize("preset", [p[2] for p in ACCRETION_PRESETS])
def test_presets_start_and_step(preset):
    app = _make_app()
    app._accretion_init(preset)
    assert app.accretion_bodies
    for _ in range(200):
        app._accretion_step()
    assert app.accretion_generation == 200
    assert len(app.accretion_history["planet_count"]) == 200


def test_merge_uses_premerge_masses_for_semi_major_axis():
    app = _make_app()
    app._accretion_init("calm")
    big = _make_body(1.0, 10.0)
    small = _make_body(1.1, 10.0)
    big["angle"] = small["angle"] = 0.0
    app.accretion_bodies = [big, small]
    app.accretion_dust = []
    app.accretion_gas_remaining = 0.0
    app._accretion_step()
    assert len(app.accretion_bodies) == 1
    assert app.accretion_bodies[0]["a"] == pytest.approx(1.05, abs=0.01)


def test_exit_clears_state():
    app = _make_app()
    app._accretion_init("calm")
    app._exit_accretion_mode()
    assert app.accretion_mode is False
    assert app.accretion_bodies == []
    assert app.accretion_dust == []
