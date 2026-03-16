"""Tests for morphogenesis mode."""
from tests.conftest import make_mock_app
from life.modes.morphogenesis import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.morpho_mode = False
    app.morpho_menu = False
    app.morpho_menu_sel = 0
    app.morpho_running = False
    app.morpho_cells = []
    app.morpho_genome_map = []
    app.morpho_morph_A = []
    app.morpho_morph_B = []
    app.morpho_nutrient = []
    app.morpho_age = []
    return app


def test_enter():
    app = _make_app()
    app._enter_morpho_mode()
    assert app.morpho_menu is True


def test_step_no_crash():
    app = _make_app()
    app.morpho_mode = True
    app._morpho_init(0)
    assert app.morpho_mode is True
    for _ in range(10):
        app._morpho_step()


def test_exit_cleanup():
    app = _make_app()
    app._morpho_init(0)
    app._exit_morpho_mode()
    assert app.morpho_mode is False
    assert app.morpho_cells == []
