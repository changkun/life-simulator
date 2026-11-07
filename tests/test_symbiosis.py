"""Tests for Symbiosis Multi-Physics."""
from unittest import mock

from tests.conftest import make_mock_app
from life.modes.symbiosis import SYMBIOSIS_PRESETS, register


class _RecordingScreen:
    def __init__(self, rows, cols):
        self.size = (rows, cols)
        self.writes = []  # (y, x, text)

    def getmaxyx(self):
        return self.size

    def addstr(self, y, x, text, *attrs):
        self.writes.append((y, x, text))

    def erase(self):
        self.writes.clear()


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.symbiosis_mode = False
    app.symbiosis_menu = False
    return app


def test_menu_description_does_not_overlap_presets():
    """The selected preset's description must not share a row with another preset."""
    for sel in range(len(SYMBIOSIS_PRESETS)):
        app = _make_app()
        app.stdscr = _RecordingScreen(24, 80)
        app._enter_symbiosis_mode()
        app.symbiosis_menu_sel = sel
        with mock.patch("curses.color_pair", return_value=0):
            app._draw_symbiosis_menu(24, 80)
        desc = SYMBIOSIS_PRESETS[sel]["desc"]
        rows = {}
        for y, x, text in app.stdscr.writes:
            rows.setdefault(y, []).append(text)
        desc_rows = [y for y, texts in rows.items()
                     if any(t.startswith(desc[:40]) for t in texts)]
        assert len(desc_rows) == 1
        assert len(rows[desc_rows[0]]) == 1


def test_step_and_exit():
    app = _make_app()
    app._symbiosis_init(["wave", "rd", "physarum"], ["R", "G", "B"])
    for _ in range(5):
        app._symbiosis_step()
    assert app.symbiosis_generation == 5
    app._exit_symbiosis_mode()
    assert app.symbiosis_mode is False
    assert app.symbiosis_layers is None
