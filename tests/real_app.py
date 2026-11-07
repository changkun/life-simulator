"""Drive the real App through App.run() with scripted keys.

The screen is a stub: getch() returns the scripted keys, then ends the run;
every other window call does nothing. Call patch_curses() first (from a
fixture) so App can set up colours without a terminal.
"""
import curses
import time

import life.colors
from life.app import App


class _Done(BaseException):
    """Raised by the fake screen when the scripted keys run out."""


class _Screen:
    """Minimal curses window: scripted getch, every other call a no-op."""

    def __init__(self, keys, rows=40, cols=120):
        self.keys = list(keys)
        self.rows, self.cols = rows, cols

    def getch(self, *args):
        if not self.keys:
            raise _Done
        return self.keys.pop(0)

    def getmaxyx(self):
        return self.rows, self.cols

    def getstr(self, *args):
        return b""

    def inch(self, *args):
        return ord(" ")

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def patch_curses(monkeypatch):
    """Stub the curses calls App makes outside the window object."""
    for name, value in {
        "start_color": lambda: None, "use_default_colors": lambda: None,
        "init_pair": lambda *a: None, "init_color": lambda *a: None,
        "color_pair": lambda n: 0, "curs_set": lambda v: 0,
        "mousemask": lambda m: (m, 0), "has_colors": lambda: True,
        "can_change_color": lambda: False, "napms": lambda ms: None,
        "doupdate": lambda: None, "beep": lambda: None,
        "pair_number": lambda attr: 0, "pair_content": lambda n: (7, 0),
        "color_content": lambda n: (0, 0, 0),
        "COLORS": 256, "COLOR_PAIRS": 256,
    }.items():
        monkeypatch.setattr(curses, name, value, raising=False)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(life.colors, "_TRUECOLOR", False)


def run_app(keys, setup=None):
    """Build an App, apply setup(app), feed keys through run(), return app."""
    app = App(_Screen(keys), None, 30, 60)
    if setup:
        setup(app)
    try:
        app.run()
    except _Done:
        pass
    return app
