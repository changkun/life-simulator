"""Tests for life.modes.living_labyrinth — Living Labyrinth mode."""
from tests.conftest import make_mock_app
from life.modes import living_labyrinth as ll


def _make_app():
    app = make_mock_app()
    ll.register(type(app))
    app._enter_labyrinth_mode()
    return app


def test_enter_resets_rule_and_tick_rate():
    app = _make_app()
    app.labyrinth_rule_idx = 3
    app.labyrinth_ca_ticks = 4
    app._exit_labyrinth_mode()
    app._enter_labyrinth_mode()
    assert app.labyrinth_rule_idx == 0
    assert app.labyrinth_ca_ticks == 1
    assert app.labyrinth_birth == {3}


def test_exit_clears_state():
    app = _make_app()
    app._exit_labyrinth_mode()
    assert app.labyrinth_mode is False
    assert app.labyrinth_cells is None
