"""The help screen scrolls when it is taller than the terminal."""
import curses

import pytest

from tests.real_app import _Screen, patch_curses, run_app


@pytest.fixture(autouse=True)
def _fake_curses(monkeypatch):
    patch_curses(monkeypatch)


class _Recorder(_Screen):
    def __init__(self, rows, cols):
        super().__init__([], rows, cols)
        self.lines = {}

    def addstr(self, y, x, text, *args):
        if y >= self.rows:
            raise curses.error
        self.lines[y] = text


def _draw(app, rows):
    screen = _Recorder(rows, 80)
    app.stdscr = screen
    app._draw_help(rows, 80)
    return screen.lines


def test_help_scrolls_and_other_keys_close_it():
    app = run_app([ord("?"), ord("j"), ord("j"), curses.KEY_NPAGE, curses.KEY_UP])
    assert app.show_help
    assert app.help_scroll > 2
    app = run_app([ord("?"), ord("j"), ord("x")])
    assert not app.show_help


def test_help_fits_a_short_terminal_with_a_footer():
    app = run_app([ord("?")])
    app.help_scroll = 10_000
    lines = _draw(app, 24)
    assert sorted(lines) == list(range(24))
    assert "of" in lines[23] and "scroll" in lines[23]
    assert lines[22].startswith("╚")


def test_help_is_centred_when_it_fits():
    app = run_app([ord("?")])
    lines = _draw(app, 200)
    assert app.help_scroll == 0
    assert all(len(text) == 50 for text in lines.values())
