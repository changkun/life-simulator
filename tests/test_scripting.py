"""Tests for life.modes.scripting — Scripting & Choreography mode."""
from tests.conftest import make_mock_app
from life.modes.scripting import register


def _make_app():
    app = make_mock_app()
    app.script_mode = False
    app.script_menu = False
    app.script_menu_sel = 0
    app.script_menu_phase = 0
    app.script_running = False
    app.script_paused = False
    app.script_sim_state = None
    app.script_prev_density = None
    app.script_commands = []
    app.script_active_sweeps = []
    app.script_show_source = False
    # Post-processing attrs needed by scripting
    app.pp_active = set()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_scripting_mode()
    assert app.script_menu is True


def test_step_no_crash():
    app = _make_app()
    script = """\
mode game_of_life
wait 0.01s
mode wave
wait 0.01s
"""
    result = app._script_init(script, "Test Script")
    assert result is True
    assert app.script_mode is True
    for _ in range(10):
        app._script_step()
    # Should have advanced through the script
    assert app.script_generation >= 1


def test_exit_cleanup():
    app = _make_app()
    script = "mode gol\nwait 1s\n"
    app._script_init(script, "Test")
    app._exit_scripting_mode()
    assert app.script_mode is False
    assert app.script_running is False
    assert app.script_commands == []
    assert app.pp_active == set()
