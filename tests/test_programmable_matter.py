"""Tests for programmable_matter mode."""
from tests.conftest import make_mock_app
from life.modes import programmable_matter as pm


def _make_app():
    app = make_mock_app()
    pm.register(type(app))
    app.progmatter_mode = False
    app.progmatter_menu = False
    app.progmatter_menu_sel = 0
    app.progmatter_running = False
    return app


def test_all_presets_init_and_step():
    for idx in range(len(pm.PM_PRESETS)):
        app = _make_app()
        app._progmatter_init(idx)
        assert app.progmatter_mode is True
        for _ in range(5):
            app._progmatter_step()
        assert app.progmatter_generation == 5


def test_exit_cleanup():
    app = _make_app()
    app._progmatter_init(0)
    app.progmatter_running = True
    app._exit_progmatter_mode()
    assert app.progmatter_mode is False
    assert app.progmatter_running is False


def test_info_panel_keys_are_lowercase_and_handled():
    """The info panel lists lowercase keys, and each one is handled."""
    app = _make_app()
    app._progmatter_init(0)
    shown = []
    app.stdscr.addstr = lambda y, x, text, *a: shown.append(text)
    app.stdscr.getmaxyx = lambda: (50, 120)
    pm._draw_pm_info(app, 50, 120, False)
    keys = [t[0] for t in shown if t[1:6] == "     "]
    assert keys == ["s", "v", "d", "r", "i", "q"]
    for k in "svdri":
        assert app._handle_progmatter_key(ord(k)) is True
