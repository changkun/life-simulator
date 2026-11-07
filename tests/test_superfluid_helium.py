"""Tests for life.modes.superfluid_helium — Superfluid Helium mode."""
import curses

import pytest

from tests.conftest import make_mock_app
from life.modes.superfluid_helium import SUPERFLUID_PRESETS, register


def _make_app():
    app = make_mock_app()
    app.superfluid_mode = False
    app.superfluid_menu = False
    app.superfluid_menu_sel = 0
    app.superfluid_running = False
    register(type(app))
    return app


def test_enter_shows_menu():
    app = _make_app()
    app._enter_superfluid_mode()
    assert app.superfluid_menu is True
    assert app.superfluid_menu_sel == 0


def test_exit_clears_flags():
    app = _make_app()
    app._superfluid_init(0)
    app.superfluid_running = True
    app._exit_superfluid_mode()
    assert app.superfluid_mode is False
    assert app.superfluid_menu is False
    assert app.superfluid_running is False


@pytest.mark.parametrize("idx", range(len(SUPERFLUID_PRESETS)))
def test_preset_starts_with_display_data(idx):
    app = _make_app()
    app._superfluid_init(idx)
    assert app.superfluid_mode is True
    assert app.superfluid_running is False
    assert app.superfluid_vortices
    # The first frame must already have flow arrows and a spectrum.
    assert any(v != 0.0 for row in app.superfluid_vx for v in row)
    assert app.superfluid_energy_spectrum


@pytest.mark.parametrize("idx", range(len(SUPERFLUID_PRESETS)))
def test_preset_evolves(idx):
    app = _make_app()
    app._superfluid_init(idx)
    before = ([v[:2] for v in app.superfluid_vortices],
              app.superfluid_T, [r[:] for r in app.superfluid_entropy])
    for _ in range(20):
        app._superfluid_step()
    assert app.superfluid_generation == 20
    after = ([v[:2] for v in app.superfluid_vortices],
             app.superfluid_T, app.superfluid_entropy)
    assert before != after


def test_temperature_keys_clamp():
    app = _make_app()
    app._superfluid_init(0)
    for _ in range(50):
        app._handle_superfluid_key(ord("t"))
    assert app.superfluid_T_target == pytest.approx(3.0)
    for _ in range(100):
        app._handle_superfluid_key(ord("T"))
    assert app.superfluid_T_target == pytest.approx(0.1)


def test_reset_restores_state():
    app = _make_app()
    app._superfluid_init(2)
    app._handle_superfluid_key(ord("p"))
    n = len(app.superfluid_vortices)
    app.superfluid_menu_sel = 2
    app._handle_superfluid_key(ord("r"))
    assert len(app.superfluid_vortices) < n
    assert app.superfluid_generation == 0


def test_menu_keys_wrap_and_cancel():
    app = _make_app()
    app._enter_superfluid_mode()
    app._handle_superfluid_menu_key(curses.KEY_UP)
    assert app.superfluid_menu_sel == len(SUPERFLUID_PRESETS) - 1
    app._handle_superfluid_menu_key(ord("q"))
    assert app.superfluid_menu is False
