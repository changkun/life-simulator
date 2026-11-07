"""Tests for life.modes.stellar — Stellar Lifecycle & Supernova mode."""
from tests.conftest import make_mock_app
from life.modes import stellar
from life.modes.stellar import register, STELLAR_PRESETS


class _Recorder:
    """Screen stub that records addstr calls."""

    def __init__(self):
        self.calls = []

    def getmaxyx(self):
        return 40, 120

    def addstr(self, y, x, text, *attr):
        self.calls.append((y, x, text))


def _make_app():
    app = make_mock_app()
    app.stellar_mode = False
    app.stellar_menu = False
    app.stellar_menu_sel = 0
    app.stellar_running = False
    register(type(app))
    return app


def test_presets_start_and_evolve():
    app = _make_app()
    for idx in range(len(STELLAR_PRESETS)):
        app._stellar_init(idx)
        before = [s.stage for s in app.stellar_stars]
        for _ in range(400):
            app._stellar_step()
        assert app.stellar_generation == 400
        assert [s.stage for s in app.stellar_stars[:len(before)]] != before


def test_core_section_shell_widths_follow_layers():
    app = _make_app()
    app._stellar_init(0)
    app.stdscr = _Recorder()
    s = app.stellar_stars[0]
    s.stage = stellar.STAGE_SUPERNOVA
    # Iron core holds half the star; hydrogen holds almost none.
    s.shell_layers = [0.01, 0.1, 0.1, 0.1, 0.19, 0.5]
    app.stellar_selected_idx = 0
    stellar._draw_stellar_core_section(app, 40, 120)
    chars = [c[2] for c in app.stdscr.calls if len(c[2]) == 1]
    assert chars.count('F') + chars.count('.') > 0
    # Fe cells must outnumber H cells (they were swapped before the fix).
    assert chars.count('F') > chars.count('H')
