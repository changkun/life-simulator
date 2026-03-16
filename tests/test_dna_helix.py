"""Tests for life.modes.dna_helix — DNA Helix & GA mode."""
from tests.conftest import make_mock_app
from life.modes.dna_helix import register


def _make_app():
    app = make_mock_app()
    app.dnahelix_mode = False
    app.dnahelix_menu = False
    app.dnahelix_menu_sel = 0
    app.dnahelix_running = False
    app.dnahelix_speed = 1
    app.dnahelix_show_info = False
    app.dnahelix_population = []
    app.dnahelix_target = []
    app.dnahelix_best_genome = []
    app.dnahelix_fitness_history = []
    app.dnahelix_solved = False
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_dnahelix_mode()
    assert app.dnahelix_menu is True


def test_step_no_crash():
    app = _make_app()
    app.dnahelix_mode = True
    app.dnahelix_preset_name = "classic"
    app._dnahelix_init("classic")
    for _ in range(10):
        app._dnahelix_step()
    assert app.dnahelix_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.dnahelix_mode = True
    app.dnahelix_preset_name = "classic"
    app._dnahelix_init("classic")
    app._exit_dnahelix_mode()
    assert app.dnahelix_mode is False
    assert app.dnahelix_population == []
