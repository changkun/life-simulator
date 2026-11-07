"""Tests for Glacier Dynamics & Ice Age Cycles."""
import pytest
from tests.conftest import make_mock_app
from life.modes.glacier import register, GLACIER_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def _start(preset_id):
    app = _make_app()
    idx = [p[2] for p in GLACIER_PRESETS].index(preset_id)
    app._glacier_init(idx)
    return app


class TestGlacierKeys:
    def test_heinrich_key_triggers_event_on_next_step(self):
        app = _start("lgm")
        app._handle_glacier_key(ord("h"))
        ice_before = sum(app.glacier_ice)
        app._glacier_step()
        assert app.glacier_heinrich_active is True
        assert app.glacier_heinrich_cooldown > 0
        assert sum(app.glacier_ice) < ice_before
        app._glacier_step()
        assert app.glacier_heinrich_active is False


@pytest.mark.parametrize("pid", [p[2] for p in GLACIER_PRESETS])
def test_presets_step_and_stay_bounded(pid):
    app = _start(pid)
    for _ in range(300):
        app._glacier_step()
    assert all(0.0 <= t <= 1.2 for t in app.glacier_temp)
    assert all(0.0 <= i <= 3.0 for i in app.glacier_ice)
    assert 150.0 <= app.glacier_co2 <= 4000.0
