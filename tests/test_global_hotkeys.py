"""Global hotkeys must not take keys the active mode binds.

App.run() offers each key to global toggles and overlays (minimap Tab, ghost
trail g, morph G, time travel u [ ], parameter tuner P, detector I, mouse
clicks) before the active mode. These tests drive the real App through
run() and check that a key the mode binds reaches the mode, while the
overlays keep working where the key is free.
"""
import curses
import time

import pytest

import life.colors
from life.app import App
from life.key_scan import handler_keys
from life.registry import MODE_DISPATCH, MODE_REGISTRY


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


@pytest.fixture(autouse=True)
def _fake_curses(monkeypatch):
    for name, value in {
        "start_color": lambda: None, "use_default_colors": lambda: None,
        "init_pair": lambda *a: None, "init_color": lambda *a: None,
        "color_pair": lambda n: 0, "curs_set": lambda v: 0,
        "mousemask": lambda m: (m, 0), "has_colors": lambda: True,
        "can_change_color": lambda: False, "napms": lambda ms: None,
        "doupdate": lambda: None, "beep": lambda: None,
        "COLORS": 256, "COLOR_PAIRS": 256,
    }.items():
        monkeypatch.setattr(curses, name, value, raising=False)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    monkeypatch.setattr(life.colors, "_TRUECOLOR", False)


def _run(keys, setup=None):
    """Build an App, apply setup(app), feed keys through run(), return app."""
    app = App(_Screen(keys), None, 30, 60)
    if setup:
        setup(app)
    try:
        app.run()
    except _Done:
        pass
    return app


def _enter(attr):
    entry = next(e for e in MODE_REGISTRY if e.get("attr") == attr and e.get("enter"))
    return lambda app: getattr(app, entry["enter"])()


def _spy_dispatch(app, seen):
    orig = app._dispatch_mode_key

    def spy(key):
        seen.append(key)
        return orig(key)

    app._dispatch_mode_key = spy


@pytest.mark.parametrize("attr, key, overlay_flag", [
    ("galaxy_mode", ord("g"), "ghost_trail_active"),
    ("galaxy_mode", ord("G"), "morph_enabled"),
    ("psoup_mode", ord("u"), None),
    ("ns_mode", ord("["), None),
    ("lv_mode", ord("P"), "param_tuner_active"),
    ("aquarium_mode", ord("I"), "compdet_active"),
    ("symphony_mode", 9, "show_minimap"),
    ("wave_mode", curses.KEY_MOUSE, None),
])
def test_mode_gets_keys_it_binds(attr, key, overlay_flag):
    seen = []

    def setup(app):
        _enter(attr)(app)
        _spy_dispatch(app, seen)

    app = _run([10, -1, key, -1], setup)
    assert getattr(app, attr), f"{attr} should still be active"
    assert key in seen, f"{attr} never received key {key}"
    if overlay_flag:
        assert not getattr(app, overlay_flag)
    assert app.tt_pos is None


def test_overlays_still_toggle_in_game_of_life():
    app = _run([ord("g"), 9, ord("G")])
    assert app.ghost_trail_active
    assert app.show_minimap
    assert app.morph_enabled


def test_overlays_still_toggle_in_modes_that_leave_the_key_free():
    app = _run([10, -1, ord("g"), -1, 9], _enter("ising_mode"))
    assert app.ising_mode
    assert app.ghost_trail_active
    assert app.show_minimap


def test_click_in_a_mode_leaves_the_life_grid_alone(monkeypatch):
    monkeypatch.setattr(curses, "getmouse",
                        lambda: (0, 20, 10, 0, curses.BUTTON1_PRESSED))

    def setup(app):
        _enter("ising_mode")(app)
        app._life_cells_before = app.grid.population

    app = _run([10, -1, curses.KEY_MOUSE, -1], setup)
    assert app.ising_mode
    assert app.grid.population == app._life_cells_before


def test_click_in_game_of_life_still_draws(monkeypatch):
    monkeypatch.setattr(curses, "getmouse",
                        lambda: (0, 20, 10, 0, curses.BUTTON1_PRESSED))
    app = _run([curses.KEY_MOUSE])
    assert app.grid.population == 1


def test_scanner_reads_every_mode_handler():
    """Every mode handler binds q or Esc; if the scan misses both, it is blind."""
    blind = [md["attr"] for md in MODE_DISPATCH
             if not {27, ord("q")} & handler_keys(getattr(App, md["keys"]), App)]
    assert not blind


def test_scanner_patterns():
    LIMIT = (ord("x"), ord("y"))

    def helper(self, key):
        return key == ord("h")

    def handler(self, key):
        ch = key
        if key == ord("a") or key in (10, curses.KEY_UP):
            return True
        if ord("1") <= key <= ord("3"):
            return True
        if chr(key) in "bc" or ch == 27 or key in LIMIT:
            return True
        return helper(self, key)

    handler.__globals__["LIMIT"] = LIMIT
    handler.__globals__["helper"] = helper
    try:
        keys = handler_keys(handler)
    finally:
        del handler.__globals__["LIMIT"], handler.__globals__["helper"]
    expected = {ord(c) for c in "a123bcxyh"} | {10, 27, curses.KEY_UP}
    assert keys == expected
