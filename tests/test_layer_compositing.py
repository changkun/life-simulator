"""Tests for life.modes.layer_compositing — Layer Compositing mode."""
from tests.conftest import make_mock_app
from life.modes.layer_compositing import register


def _make_app():
    app = make_mock_app()
    app.comp_mode = False
    app.comp_menu = False
    app.comp_menu_sel = 0
    app.comp_menu_phase = 0
    app.comp_custom_layers = []
    app.comp_running = False
    app.comp_layers = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_comp_mode()
    assert app.comp_menu is True
    assert app.comp_menu_phase == 0


def test_step_no_crash():
    app = _make_app()
    layer_defs = [
        {"sim": "gol", "blend": "add", "opacity": 1.0, "tick_mult": 1},
        {"sim": "wave", "blend": "xor", "opacity": 0.8, "tick_mult": 1},
    ]
    app._comp_init(layer_defs)
    assert app.comp_mode is True
    assert len(app.comp_layers) == 2
    for _ in range(10):
        app._comp_step()
    assert app.comp_generation == 10


def test_exit_cleanup():
    app = _make_app()
    layer_defs = [
        {"sim": "gol", "blend": "add", "opacity": 1.0, "tick_mult": 1},
        {"sim": "rd", "blend": "add", "opacity": 0.5, "tick_mult": 2},
    ]
    app._comp_init(layer_defs)
    app._exit_comp_mode()
    assert app.comp_mode is False
    assert app.comp_layers == []
