"""Mode: blueprint — simulation mode for the life package."""
import curses
import math
import random
import time


from life.patterns import PATTERNS
from life.utils import _save_blueprints

def _enter_blueprint_mode(self):
    """Start blueprint region selection at current cursor position."""
    self.blueprint_mode = True
    self.blueprint_anchor = (self.cursor_r, self.cursor_c)
    self._flash("Blueprint: move cursor to select region, Enter=capture, Esc=cancel")



def _blueprint_region(self) -> tuple[int, int, int, int]:
    """Return (min_r, min_c, max_r, max_c) of the current blueprint selection."""
    ar, ac = self.blueprint_anchor
    cr, cc = self.cursor_r, self.cursor_c
    return (min(ar, cr), min(ac, cc), max(ar, cr), max(ac, cc))



def _capture_blueprint(self):
    """Capture the selected region as a named blueprint pattern."""
    min_r, min_c, max_r, max_c = self._blueprint_region()
    # Collect alive cells in the region, normalised to (0,0) origin
    cells = []
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            gr = r % self.grid.rows
            gc = c % self.grid.cols
            if self.grid.cells[gr][gc] > 0:
                cells.append((r - min_r, c - min_c))
    if not cells:
        self._flash("No alive cells in selection — blueprint not saved")
        self.blueprint_mode = False
        self.blueprint_anchor = None
        return
    width = max_c - min_c + 1
    height = max_r - min_r + 1
    self.blueprint_mode = False
    self.blueprint_anchor = None
    # Prompt for a name
    name = self._prompt_text(f"Blueprint name ({len(cells)} cells, {width}x{height})")
    if not name:
        self._flash("Blueprint cancelled")
        return
    # Sanitize name (lowercase, replace spaces with underscores)
    safe_name = name.strip().lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    if not safe_name:
        self._flash("Invalid name")
        return
    # Don't overwrite built-in patterns
    if safe_name in PATTERNS:
        self._flash(f"Cannot overwrite built-in pattern '{safe_name}'")
        return
    desc = f"Custom blueprint ({len(cells)} cells, {width}x{height})"
    self.blueprints[safe_name] = {"description": desc, "cells": cells}
    _save_blueprints(self.blueprints)
    self._rebuild_pattern_list()
    self._flash(f"Saved blueprint: {safe_name}")



def _stamp_blueprint(self, name: str):
    """Overlay a blueprint pattern centered on the current cursor."""
    pat = self._get_pattern(name)
    if not pat:
        self._flash(f"Unknown pattern: {name}")
        return
    max_r = max(r for r, c in pat["cells"]) if pat["cells"] else 0
    max_c = max(c for r, c in pat["cells"]) if pat["cells"] else 0
    off_r = self.cursor_r - max_r // 2
    off_c = self.cursor_c - max_c // 2
    for r, c in pat["cells"]:
        gr = (r + off_r) % self.grid.rows
        gc = (c + off_c) % self.grid.cols
        self.grid.set_alive(gr, gc)
    self._flash(f"Stamped: {name}")



def _delete_blueprint(self, name: str):
    """Delete a user-saved blueprint."""
    if name in self.blueprints:
        del self.blueprints[name]
        _save_blueprints(self.blueprints)
        self._rebuild_pattern_list()
        self._flash(f"Deleted blueprint: {name}")



def _handle_blueprint_mode_key(self, key: int) -> bool:
    """Handle keys while in blueprint selection mode."""
    if key == -1:
        return True
    if key == 27:  # ESC
        self.blueprint_mode = False
        self.blueprint_anchor = None
        self._flash("Blueprint selection cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):  # Enter — capture
        self._capture_blueprint()
        return True
    # Cursor movement (same as normal mode)
    if key in (curses.KEY_UP, ord("k")):
        self.cursor_r = (self.cursor_r - 1) % self.grid.rows
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.cursor_r = (self.cursor_r + 1) % self.grid.rows
        return True
    if key in (curses.KEY_LEFT, ord("l") - 4):  # 'h' already used
        self.cursor_c = (self.cursor_c - 1) % self.grid.cols
        return True
    if key in (curses.KEY_RIGHT, ord("l")):
        self.cursor_c = (self.cursor_c + 1) % self.grid.cols
        return True
    return True



def _handle_blueprint_menu_key(self, key: int) -> bool:
    """Handle keys in the blueprint library menu."""
    if key == -1:
        return True
    bp_names = sorted(self.blueprints.keys())
    if not bp_names:
        self.blueprint_menu = False
        return True
    if key == 27 or key == ord("q"):
        self.blueprint_menu = False
        return True
    if key in (curses.KEY_UP, ord("k")):
        self.blueprint_sel = (self.blueprint_sel - 1) % len(bp_names)
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.blueprint_sel = (self.blueprint_sel + 1) % len(bp_names)
        return True
    if key in (10, 13, curses.KEY_ENTER):  # Enter — stamp at cursor
        name = bp_names[self.blueprint_sel]
        self._stamp_blueprint(name)
        self.blueprint_menu = False
        self._reset_cycle_detection()
        return True
    if key == ord("D") or key == curses.KEY_DC:  # D or Delete — remove
        name = bp_names[self.blueprint_sel]
        self._delete_blueprint(name)
        bp_names = sorted(self.blueprints.keys())
        if not bp_names:
            self.blueprint_menu = False
        else:
            self.blueprint_sel = min(self.blueprint_sel, len(bp_names) - 1)
        return True
    return True



def _draw_blueprint_menu(self, max_y: int, max_x: int):
    """Draw the blueprint library menu."""
    bp_names = sorted(self.blueprints.keys())
    title = "── Blueprint Library (Enter=stamp, D=delete, q/Esc=close) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    if not bp_names:
        msg = "No blueprints saved yet. Press W to create one."
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(msg)) // 2), msg,
                               curses.color_pair(6))
        except curses.error:
            pass
        return
    for i, name in enumerate(bp_names):
        y = 3 + i
        if y >= max_y - 1:
            break
        desc = self.blueprints[name]["description"]
        line = f"  {name:<20s} {desc}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.blueprint_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line, attr)
        except curses.error:
            pass




def register(App):
    """Register blueprint mode methods on the App class."""
    App._enter_blueprint_mode = _enter_blueprint_mode
    App._blueprint_region = _blueprint_region
    App._capture_blueprint = _capture_blueprint
    App._stamp_blueprint = _stamp_blueprint
    App._delete_blueprint = _delete_blueprint
    App._handle_blueprint_mode_key = _handle_blueprint_mode_key
    App._handle_blueprint_menu_key = _handle_blueprint_menu_key
    App._draw_blueprint_menu = _draw_blueprint_menu

