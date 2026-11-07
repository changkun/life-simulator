"""Tests for life.modes.termite_mound — Termite Mound Construction & Stigmergy."""
from tests.conftest import make_mock_app
from life.modes.termite_mound import register, TMOUND_PRESETS


def _make_app():
    app = make_mock_app()
    app.tmound_mode = False
    app.tmound_menu = False
    app.tmound_menu_sel = 0
    app.tmound_running = False
    app.message = ""
    app.message_time = 0.0
    app._flash = lambda msg, *a, **k: None
    register(type(app))
    return app


def test_presets_start_and_change_the_mound():
    app = _make_app()
    for idx in range(len(TMOUND_PRESETS)):
        app._tmound_init(idx)
        assert app.tmound_mode and not app.tmound_menu
        before = [row[:] for row in app.tmound_material]
        for _ in range(100):
            app._tmound_step()
        assert app.tmound_generation == 100
        assert app.tmound_material != before


def test_hint_bar_keys_are_handled():
    app = _make_app()
    app._tmound_init(0)
    app._handle_tmound_key(ord(" "))
    assert app.tmound_running
    app._handle_tmound_key(ord("n"))
    assert app.tmound_generation == 1
    app._handle_tmound_key(ord("v"))
    assert app.tmound_view == "pheromone"
    app._handle_tmound_key(ord("+"))
    assert app.tmound_steps_per_frame == 2
    app._handle_tmound_key(ord("-"))
    assert app.tmound_steps_per_frame == 1
    app._handle_tmound_key(ord("r"))
    assert app.tmound_generation == 0 and not app.tmound_running
    app._handle_tmound_key(ord("R"))
    assert app.tmound_menu and not app.tmound_mode
    app._handle_tmound_menu_key(ord("\n"))
    assert app.tmound_mode
    app._handle_tmound_key(ord("q"))
    assert not app.tmound_mode and not app.tmound_running
