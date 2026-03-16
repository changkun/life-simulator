"""Tests for life.modes.volcano — Volcanic Eruption mode."""
from tests.conftest import make_mock_app
from life.modes.volcano import register


def _make_app():
    app = make_mock_app()
    app.volcano_mode = False
    app.volcano_menu = False
    app.volcano_menu_sel = 0
    app.volcano_running = False
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_volcano_mode()
    assert app.volcano_menu is True


def test_step_no_crash():
    app = _make_app()
    app.volcano_mode = True
    app._volcano_init(0)
    for _ in range(10):
        app._volcano_step()
    assert app.volcano_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.volcano_mode = True
    app._volcano_init(0)
    app._exit_volcano_mode()
    assert app.volcano_mode is False
    assert app.volcano_running is False
