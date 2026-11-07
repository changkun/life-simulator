"""Every mode must fit an 80x24 terminal, using only one-cell characters.

For each mode in MODE_REGISTRY this drives the real App.run() loop on a
recording 80x24 screen (tests.conftest.MockStdscr):

  1. enter the mode and draw its preset menu (or its first frame);
  2. pick the first preset, start the run, step a few frames, drawing each;
  3. cycle the mode's alternate views (the graphs view and the like) and
     draw each one.

Any text that runs past column 79 or row 23, or that contains a wide or
emoji character, is reported with the mode, the stage, the row and the text.

A failure here means a hint bar, status line or label needs shortening, or
needs clipping to ``max_x - 1``.  Please fix the drawing code rather than
adding the mode to SKIP; if a skip is really needed, give it a reason.
"""
import curses
import random
import re
import sys

import pytest

from life.registry import MODE_DISPATCH, MODE_REGISTRY
from tests.conftest import MockStdscr
from tests.real_app import patch_curses

ROWS, COLS = 24, 80
ENTER = 10
STEPS = 4
MAX_VIEWS = 6

# Modes left out of the check, each with the reason why.
SKIP: dict[str, str] = {}

# Keys that move a preset menu to its "start" choice when the first item
# does not start the run.  Enter is pressed after these.
START_KEYS: dict[str, list[int]] = {
    # Settings menus whose start item is near the end (Up wraps to it).
    "Evolutionary Playground": [curses.KEY_UP, curses.KEY_UP],
    "Phase Space Navigator": [curses.KEY_UP],
    # Settings menus with the start item further down the list.
    "Auto-Discovery": [curses.KEY_DOWN] * 5,
    "Evolution Lab": [curses.KEY_DOWN] * 6,
    "Genesis Protocol": [curses.KEY_DOWN] * 5,
    "Neural Cellular Automata": [curses.KEY_DOWN] * 7,
    # Two-step menus: pick a tiling/topology, then a rule.
    "Hyperbolic Cellular Automata": [ENTER],
    "Graph Cellular Automata": [ENTER],
}


def _seed_hall_of_fame(app):
    """Rule Phylogenetics analyses saved Genesis results; give it some."""
    app.phylo_entries = [
        {"label": "B3/S23", "classification": "glider", "score": 10, "round": 0},
        {"label": "B36/S23", "classification": "glider", "score": 9, "round": 0},
        {"label": "B2/S", "classification": "chaotic", "score": 40, "round": 1},
        {"label": "B1357/S1357", "classification": "replicator", "score": 5,
         "round": 1},
    ]


# Extra state a mode needs before its menu can start a run.
SETUP = {"Rule Phylogenetics": _seed_hall_of_fame}

# Keys that cycle a mode's alternate views when it is not plain "v".
VIEW_KEYS: dict[str, int] = {"Symbiosis Multi-Physics": ord("F")}


class _Done(BaseException):
    """Raised by the screen when the script runs out."""


class LayoutScreen(MockStdscr):
    """Recording screen whose getch() runs a script.

    Each script item is a key, or a callable taking the App and returning a
    key (or None to end the run).  The frame drawn before each getch() is
    tagged with the current ``stage`` so violations say where they came from.
    """

    def __init__(self, script):
        super().__init__(ROWS, COLS)
        self.script = list(script)
        self.app = None
        self.stage = "menu"
        self.found = []
        self.started = False

    def _record(self, y, x, text):
        before = len(self.violations)
        super()._record(y, x, text)
        for v in self.violations[before:]:
            self.found.append((self.stage,) + v)

    def getch(self, *args):
        if not self.script:
            raise _Done
        item = self.script.pop(0)
        key = item(self.app) if callable(item) else item
        if key is None:
            raise _Done
        return key

    def getstr(self, *args):
        return b""

    def inch(self, *args):
        return ord(" ")

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *args, **kwargs: None


@pytest.fixture(autouse=True)
def _fake_curses(monkeypatch, tmp_path):
    patch_curses(monkeypatch)
    # Keep modes that save galleries or hall-of-fame files out of ~.
    import life  # noqa: F401  (make sure the package is loaded)
    from life.constants import SAVE_DIR
    for mod in [m for n, m in sys.modules.items()
                if n == "life" or n.startswith("life.")]:
        for name, val in list(vars(mod).items()):
            if isinstance(val, str) and val.startswith(SAVE_DIR):
                monkeypatch.setattr(
                    mod, name, str(tmp_path) + val[len(SAVE_DIR):])


def _dispatch_for(entry):
    return next((md for md in MODE_DISPATCH if md["attr"] == entry["attr"]), None)


def _view_attrs(app, prefix):
    """Snapshot of the mode's view-selector attributes."""
    pat = re.compile(rf"{re.escape(prefix)}_(\w+_)?view(_mode|_idx)?")
    return {n: repr(v) for n, v in vars(app).items()
            if pat.fullmatch(n) and isinstance(v, (str, int))}


def _script(entry):
    md = _dispatch_for(entry)
    prefix = md["prefix"] if md else None
    state = {}

    def start(app):
        # Leave the preset menu with its first choice.
        app.stdscr.stage = "run"
        return ENTER

    def ensure_running(app):
        # Make sure the simulation is actually running, and note whether
        # the mode really got past its menu.
        if md:
            app.stdscr.started = (getattr(app, md["attr"], False)
                                  and not getattr(app, md["menu_attr"], False))
            if app.stdscr.started and hasattr(app, md["running_attr"]):
                setattr(app, md["running_attr"], True)
        else:
            app.stdscr.started = True
            if entry["enter"] is None:
                app.running = True
        return -1

    def view_key(app):
        app.stdscr.stage = "view"
        if prefix is None or not getattr(app, md["attr"], False):
            return None
        snap = _view_attrs(app, prefix)
        if not snap:
            return None
        if "first" not in state:
            state["first"] = snap
        elif snap == state["first"]:
            return None                       # back where we started
        return VIEW_KEYS.get(entry["name"], ord("v"))

    def view_changed(app):
        snap = _view_attrs(app, prefix) if prefix else {}
        if snap == state.get("first"):
            return None                       # key did not change the view
        app.stdscr.stage = "view " + ", ".join(
            f"{k}={v}" for k, v in snap.items() if state["first"].get(k) != v)
        return -1

    keys = START_KEYS.get(entry["name"], [])
    script = keys + [start, ensure_running] + [-1] * STEPS
    for _ in range(MAX_VIEWS):
        script += [view_key, view_changed]
    return script


def _run_mode(entry):
    from life.app import App

    random.seed(1234)

    screen = LayoutScreen(_script(entry))
    app = App(screen, None, 30, 60)
    screen.app = app
    if entry["enter"]:
        getattr(app, entry["enter"])()
    if entry["name"] in SETUP:
        SETUP[entry["name"]](app)
    try:
        app.run()
    except _Done:
        pass
    return screen


def _format(name, found):
    seen, lines = set(), []
    for stage, y, x, text, reason in found:
        key = (stage, y, text.strip(), reason)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  [{stage}] row {y} col {x}: {reason}: {text!r}")
    more = ""
    if len(lines) > 15:
        more = f"\n  ... and {len(lines) - 15} more"
    return f"{name}: {len(lines)} layout problem(s) at {COLS}x{ROWS}\n" + \
        "\n".join(lines[:15]) + more


_NAMES = [e["name"] for e in MODE_REGISTRY]


@pytest.mark.parametrize("entry", MODE_REGISTRY, ids=_NAMES)
def test_mode_fits_80x24(entry):
    if entry["name"] in SKIP:
        pytest.skip(SKIP[entry["name"]])
    screen = _run_mode(entry)
    assert screen.started, (
        f"{entry['name']}: still in its menu after Enter, so the run was "
        f"never drawn; add its start keys to START_KEYS")
    assert not screen.found, _format(entry["name"], screen.found)


def test_screen_flags_overflow_and_wide_text():
    """The recording screen itself catches the problems this file guards."""
    scr = MockStdscr(ROWS, COLS)
    scr.addstr(0, 0, "x" * COLS)                 # exactly fits
    scr.addstr(ROWS - 1, 0, "ok")
    assert scr.violations == []
    scr.addstr(1, 75, "123456")                  # runs to column 80
    scr.addstr(ROWS, 0, "x")                     # row 24
    scr.addnstr(2, 70, "y" * 40, 10)             # clipped to fit: fine
    scr.addch(3, COLS, ord("z"))                 # column 80
    scr.addstr(4, 0, "fire \U0001F525")          # emoji
    scr.addstr(5, 0, "\u5b57")                  # CJK, double width
    scr.addch(6, 0, 0x400071)                    # an ACS-style chtype is fine
    reasons = [v[3] for v in scr.violations]
    assert len(reasons) == 5, reasons
