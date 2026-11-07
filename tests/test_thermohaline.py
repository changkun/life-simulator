"""Tests for life.modes.thermohaline — Ocean Thermohaline Circulation."""
import curses

import pytest

from tests.conftest import make_mock_app
from life.modes.thermohaline import THERMOHALINE_PRESETS, _append_metric, register


def _make_app():
    app = make_mock_app()
    app.thermohaline_mode = False
    app.thermohaline_menu = False
    app.thermohaline_running = False
    register(type(app))
    return app


def test_enter_shows_menu():
    app = _make_app()
    app._enter_thermohaline_mode()
    assert app.thermohaline_mode is True
    assert app.thermohaline_menu is True
    assert app.thermohaline_menu_sel == 0


def test_exit_clears_state():
    app = _make_app()
    app._thermohaline_init(0)
    app._exit_thermohaline_mode()
    assert app.thermohaline_mode is False
    assert app.thermohaline_menu is False
    assert app.thermohaline_running is False
    assert "thermohaline_temp" not in vars(app)


@pytest.mark.parametrize("idx", range(len(THERMOHALINE_PRESETS)))
def test_preset_evolves_and_stays_bounded(idx):
    app = _make_app()
    app._thermohaline_init(idx)
    before = [row[:] for row in app.thermohaline_temp]
    for _ in range(20):
        app._thermohaline_step()
    assert app.thermohaline_generation == 20
    assert app.thermohaline_temp != before
    assert len(app.thermohaline_history["mean_sst"]) == 20
    for row in app.thermohaline_salinity:
        assert all(0.0 <= s <= 1.0 for s in row)
    assert 0.0 <= app.thermohaline_amoc_strength <= 1.5


def test_history_is_capped():
    hist = {"x": []}
    for i in range(310):
        _append_metric(hist, "x", i)
    assert len(hist["x"]) == 300
    assert hist["x"][0] == 10


def test_hosing_keys_clamp():
    app = _make_app()
    app._thermohaline_init(0)
    for _ in range(20):
        app._handle_thermohaline_key(ord("+"))
    assert app.thermohaline_hosing_rate == pytest.approx(0.05)
    for _ in range(20):
        app._handle_thermohaline_key(ord("-"))
    assert app.thermohaline_hosing_rate == 0.0


def test_view_cycles_and_reset_keeps_preset():
    app = _make_app()
    app._thermohaline_init(3)
    app._handle_thermohaline_key(ord("v"))
    assert app.thermohaline_view == "crosssection"
    app._thermohaline_step()
    app._handle_thermohaline_key(ord("r"))
    assert app.thermohaline_generation == 0
    assert app.thermohaline_preset_id == THERMOHALINE_PRESETS[3][2]
    assert app.thermohaline_view == "currents"


def test_menu_keys():
    app = _make_app()
    app._enter_thermohaline_mode()
    app._handle_thermohaline_menu_key(curses.KEY_UP)
    assert app.thermohaline_menu_sel == len(THERMOHALINE_PRESETS) - 1
    app._handle_thermohaline_menu_key(10)
    assert app.thermohaline_menu is False
    assert app.thermohaline_running is True
