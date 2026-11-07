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


def test_freeze_lasts_ten_turns_at_any_tick_rate():
    app = _make_app()
    app.labyrinth_ca_ticks = 3
    app.labyrinth_inventory[ll.ITEM_FREEZE] = 1
    ll._labyrinth_use_freeze(app)
    pr, pc = app.labyrinth_player_r, app.labyrinth_player_c
    for _ in range(9):
        ll._labyrinth_player_turn(app, 0, 0)
    assert app.labyrinth_frozen_mask[pr][pc] == 1
    ll._labyrinth_player_turn(app, 0, 0)
    assert app.labyrinth_frozen_mask[pr][pc] == 0


def test_exit_clears_state():
    app = _make_app()
    app._exit_labyrinth_mode()
    assert app.labyrinth_mode is False
    assert app.labyrinth_cells is None
