"""Tests for life.modes.nuclear_reactor — Nuclear Reactor Physics mode."""
import curses
from tests.conftest import make_mock_app
from life.modes.nuclear_reactor import register, NUCLEAR_REACTOR_PRESETS


def _make_app():
    app = make_mock_app()
    app.nuclear_reactor_mode = False
    app.nuclear_reactor_menu = False
    app.nuclear_reactor_running = False
    register(type(app))
    return app


def test_enter_and_exit():
    app = _make_app()
    app._enter_nuclear_reactor_mode()
    assert app.nuclear_reactor_menu is True
    app._nuclear_reactor_init(0)
    app._exit_nuclear_reactor_mode()
    assert app.nuclear_reactor_mode is False
    assert app.nuclear_reactor_running is False


def test_menu_enter_key_variants():
    for key in (10, 13, curses.KEY_ENTER):
        app = _make_app()
        app._enter_nuclear_reactor_mode()
        app._handle_nuclear_reactor_menu_key(key)
        assert app.nuclear_reactor_menu is False
        assert app.nuclear_reactor_preset_name == NUCLEAR_REACTOR_PRESETS[0][0]


def test_all_presets_step():
    for idx in range(len(NUCLEAR_REACTOR_PRESETS)):
        app = _make_app()
        app._nuclear_reactor_init(idx)
        for _ in range(30):
            app._nuclear_reactor_step()
        assert app.nuclear_reactor_generation == 30


def test_decay_heat_scales_with_flux():
    """Decay heat must not jump to a large value from the first-step flux collapse."""
    app = _make_app()
    app._nuclear_reactor_init(0)
    for _ in range(20):
        app._nuclear_reactor_step()
    assert app.nuclear_reactor_decay_heat < 0.05
