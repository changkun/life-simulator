"""Tests for life.modes.rule_editor — Live Rule Editor mode."""
from tests.conftest import make_mock_app
from life.modes.rule_editor import register


def _make_app():
    app = make_mock_app()
    app.re_mode = False
    app.re_menu = False
    app.re_menu_sel = 0
    app.re_menu_tab = 0
    app.re_saved_rules = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_rule_editor_mode()
    assert app.re_menu is True
    assert app.re_mode is False


def test_step_no_crash():
    app = _make_app()
    app._re_init()
    assert app.re_mode is True
    assert app.re_grid is not None
    for _ in range(10):
        app._re_step()
    assert app.re_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app._re_init()
    app._exit_rule_editor_mode()
    assert app.re_mode is False
    assert app.re_menu is False
