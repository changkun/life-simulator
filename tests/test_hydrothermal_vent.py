"""Tests for Deep Sea Hydrothermal Vent Ecosystem."""
import pytest
from tests.conftest import make_mock_app
from life.constants import SPEEDS
from life.modes.hydrothermal_vent import register, HVENT_PRESETS


def _start(idx=0):
    app = make_mock_app()
    register(type(app))
    app._hvent_init(idx)
    return app


def test_speed_keys_move_through_speed_table():
    app = _start()
    app.speed_idx = 2
    app._handle_hvent_key(ord("+"))
    assert app.speed_idx == 3
    app._handle_hvent_key(ord("-"))
    app._handle_hvent_key(ord("-"))
    assert app.speed_idx == 1
    app.speed_idx = len(SPEEDS) - 1
    app._handle_hvent_key(ord("+"))
    assert app.speed_idx == len(SPEEDS) - 1
    app.speed_idx = 0
    app._handle_hvent_key(ord("-"))
    assert app.speed_idx == 0


@pytest.mark.parametrize("idx", range(len(HVENT_PRESETS)))
def test_presets_step(idx):
    app = _start(idx)
    for _ in range(50):
        app._hvent_step()
    assert app.hvent_generation == 50
    assert len(app.hvent_fauna) <= app.hvent_rows * app.hvent_cols // 4
