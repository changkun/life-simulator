"""Mode: rule_editor — Live Rule Editor.

Interactive REPL/editor where users type Python expressions to define
custom cellular automaton rules and see them execute on the grid in
real time.  Expressions can reference ``neighbors`` (list of 8 neighbor
states), ``sum(neighbors)``, ``age`` (current cell age), ``x``, ``y``
(cell coordinates), ``step`` (generation number), and ``random()``
(random float 0-1).

Includes ~10 starter snippets and save/load to
``~/.life_saves/custom_rules.json``.
"""
import curses
import json
import math
import os
import random as _random
import time

from life.constants import SAVE_DIR, SPEEDS, SPEED_LABELS
from life.grid import Grid

# ── Constants ────────────────────────────────────────────────────────

_DENSITY = ["  ", "░░", "▒▒", "▓▓", "██"]

_CUSTOM_RULES_FILE = os.path.join(SAVE_DIR, "custom_rules.json")

# Starter snippets: (name, birth_expr, survival_expr)
_STARTER_SNIPPETS = [
    ("Classic Life (B3/S23)",
     "sum(neighbors) == 3",
     "sum(neighbors) in (2, 3)"),
    ("HighLife (B36/S23)",
     "sum(neighbors) in (3, 6)",
     "sum(neighbors) in (2, 3)"),
    ("Day & Night (B3678/S34678)",
     "sum(neighbors) in (3, 6, 7, 8)",
     "sum(neighbors) in (3, 4, 6, 7, 8)"),
    ("Seeds (B2/S—)",
     "sum(neighbors) == 2",
     "False"),
    ("Diamoeba (B35678/S5678)",
     "sum(neighbors) in (3, 5, 6, 7, 8)",
     "sum(neighbors) in (5, 6, 7, 8)"),
    ("Age-Dependent Decay",
     "sum(neighbors) == 3",
     "sum(neighbors) in (2, 3) and age < 10"),
    ("Positional Bias",
     "sum(neighbors) == 3 and (x + y) % 3 == 0",
     "sum(neighbors) in (2, 3)"),
    ("Stochastic Life",
     "sum(neighbors) == 3 or (sum(neighbors) == 2 and random() < 0.05)",
     "sum(neighbors) in (2, 3)"),
    ("Pulse (step-dependent)",
     "sum(neighbors) == 3 or (sum(neighbors) == 1 and step % 10 < 3)",
     "sum(neighbors) in (2, 3)"),
    ("Anneal (B4678/S35678)",
     "sum(neighbors) in (4, 6, 7, 8)",
     "sum(neighbors) in (3, 5, 6, 7, 8)"),
]

# ── Compilation helpers ──────────────────────────────────────────────

def _compile_expr(expr_str):
    """Compile a rule expression string to a code object.

    Returns (code_obj, None) on success or (None, error_str) on failure.
    """
    if not expr_str.strip():
        return None, "empty expression"
    try:
        code = compile(expr_str, "<rule>", "eval")
        return code, None
    except SyntaxError as exc:
        return None, f"syntax error: {exc.msg}"
    except Exception as exc:
        return None, str(exc)


def _eval_rule(code, neighbors, age, x, y, step):
    """Evaluate a compiled rule expression.

    Returns bool result, or None on error.
    """
    try:
        result = eval(code, {"__builtins__": {}}, {
            "neighbors": neighbors,
            "sum": sum,
            "len": len,
            "min": min,
            "max": max,
            "abs": abs,
            "any": any,
            "all": all,
            "age": age,
            "x": x,
            "y": y,
            "step": step,
            "random": _random.random,
            "math": math,
            "True": True,
            "False": False,
            "int": int,
            "float": float,
        })
        return bool(result)
    except Exception:
        return None

# ── Save / Load helpers ──────────────────────────────────────────────

def _load_custom_rules():
    """Load saved custom rules from disk."""
    if not os.path.exists(_CUSTOM_RULES_FILE):
        return []
    try:
        with open(_CUSTOM_RULES_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_custom_rules(rules):
    """Persist custom rules list to disk."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(_CUSTOM_RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)

# ── Mode functions ───────────────────────────────────────────────────

def _enter_rule_editor_mode(self):
    """Enter the Live Rule Editor mode — starts with snippet menu."""
    self.re_mode = False
    self.re_menu = True
    self.re_menu_sel = 0
    self.re_menu_tab = 0  # 0=snippets, 1=saved
    self.re_saved_rules = _load_custom_rules()
    self._flash("Live Rule Editor — pick a starter or type your own")


def _exit_rule_editor_mode(self):
    """Leave the rule editor."""
    self.re_mode = False
    self.re_menu = False
    self._flash("Rule Editor OFF")


def _re_init(self, birth_expr="sum(neighbors) == 3",
             survival_expr="sum(neighbors) in (2, 3)",
             rule_name="Custom Rule"):
    """Initialize the live rule editor with given expressions."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.re_rows = max_y - 6  # leave room for editor panel
    self.re_cols = (max_x - 1) // 2
    if self.re_rows < 5:
        self.re_rows = 5
    if self.re_cols < 10:
        self.re_cols = 10

    # Grid state: 0 = dead, >0 = age (alive)
    self.re_grid = [[0] * self.re_cols for _ in range(self.re_rows)]
    self.re_generation = 0
    self.re_population = 0
    self.re_running = False

    # Seed with random ~25% fill
    for r in range(self.re_rows):
        for c in range(self.re_cols):
            if _random.random() < 0.25:
                self.re_grid[r][c] = 1
    self.re_population = sum(
        1 for r in range(self.re_rows) for c in range(self.re_cols) if self.re_grid[r][c]
    )

    # Rule expressions
    self.re_birth_expr = birth_expr
    self.re_survival_expr = survival_expr
    self.re_rule_name = rule_name

    # Compile
    self.re_birth_code, self.re_birth_err = _compile_expr(birth_expr)
    self.re_survival_code, self.re_survival_err = _compile_expr(survival_expr)

    # Editor state
    self.re_editing = None  # None, "birth", "survival", "name"
    self.re_edit_buf = ""
    self.re_edit_cursor = 0
    self.re_focus = 0  # 0=birth, 1=survival, 2=name

    # Pop history for sparkline
    self.re_pop_history = []

    self.re_mode = True
    self.re_menu = False


def _re_step(self):
    """Advance the custom rule simulation by one generation."""
    if self.re_birth_code is None and self.re_survival_code is None:
        return  # both broken, skip

    rows, cols = self.re_rows, self.re_cols
    old = self.re_grid
    new = [[0] * cols for _ in range(rows)]
    pop = 0
    step = self.re_generation

    for r in range(rows):
        for c in range(cols):
            # Gather neighbors (toroidal)
            nbrs = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    nbrs.append(old[nr][nc])

            alive = old[r][c] > 0
            age = old[r][c]

            if alive:
                # Survival check
                if self.re_survival_code is not None:
                    result = _eval_rule(self.re_survival_code, nbrs, age, c, r, step)
                    survives = result if result is not None else False
                else:
                    survives = False
                if survives:
                    new[r][c] = age + 1
                    pop += 1
                # else: dies → stays 0
            else:
                # Birth check
                if self.re_birth_code is not None:
                    result = _eval_rule(self.re_birth_code, nbrs, 0, c, r, step)
                    born = result if result is not None else False
                else:
                    born = False
                if born:
                    new[r][c] = 1
                    pop += 1

    self.re_grid = new
    self.re_population = pop
    self.re_generation += 1
    self.re_pop_history.append(pop)
    if len(self.re_pop_history) > 200:
        self.re_pop_history.pop(0)


def _re_save_rule(self):
    """Save the current rule to custom_rules.json."""
    entry = {
        "name": self.re_rule_name,
        "birth": self.re_birth_expr,
        "survival": self.re_survival_expr,
    }
    self.re_saved_rules = _load_custom_rules()
    # Replace if same name exists
    replaced = False
    for i, r in enumerate(self.re_saved_rules):
        if r.get("name") == entry["name"]:
            self.re_saved_rules[i] = entry
            replaced = True
            break
    if not replaced:
        self.re_saved_rules.append(entry)
    _save_custom_rules(self.re_saved_rules)
    self._flash(f"Saved: {self.re_rule_name}")


def _re_adopt_to_gol(self):
    """Try to translate the current rule to standard B/S format and apply to main grid."""
    # Only works for simple sum-based rules
    birth_set = set()
    survival_set = set()
    for n in range(9):
        nbrs = [1] * n + [0] * (8 - n)
        if self.re_birth_code is not None:
            res = _eval_rule(self.re_birth_code, nbrs, 0, 0, 0, 0)
            if res:
                birth_set.add(n)
        if self.re_survival_code is not None:
            res = _eval_rule(self.re_survival_code, nbrs, 5, 0, 0, 0)
            if res:
                survival_set.add(n)
    self.grid.birth = birth_set
    self.grid.survival = survival_set
    self._flash(f"Adopted B{''.join(map(str, sorted(birth_set)))}/S{''.join(map(str, sorted(survival_set)))}")


def _re_randomize_grid(self):
    """Re-seed the grid with random cells."""
    for r in range(self.re_rows):
        for c in range(self.re_cols):
            self.re_grid[r][c] = 1 if _random.random() < 0.25 else 0
    self.re_population = sum(
        1 for r in range(self.re_rows) for c in range(self.re_cols) if self.re_grid[r][c]
    )
    self.re_generation = 0
    self.re_pop_history.clear()


def _re_import_from_ep(self):
    """Import the selected genome from Evolutionary Playground (if available)."""
    if not hasattr(self, 'ep_genomes') or not self.ep_genomes:
        self._flash("No EP genomes available")
        return
    idx = min(self.ep_cursor, len(self.ep_genomes) - 1)
    genome = self.ep_genomes[idx]
    birth = sorted(genome["birth"])
    survival = sorted(genome["survival"])
    self.re_birth_expr = f"sum(neighbors) in ({', '.join(map(str, birth))})" if len(birth) > 1 else f"sum(neighbors) == {birth[0]}" if birth else "False"
    self.re_survival_expr = f"sum(neighbors) in ({', '.join(map(str, survival))})" if len(survival) > 1 else f"sum(neighbors) == {survival[0]}" if survival else "False"
    self.re_birth_code, self.re_birth_err = _compile_expr(self.re_birth_expr)
    self.re_survival_code, self.re_survival_err = _compile_expr(self.re_survival_expr)
    self.re_rule_name = f"EP-{','.join(map(str, birth))}/{','.join(map(str, survival))}"
    self._flash(f"Imported from EP: B{','.join(map(str, birth))}/S{','.join(map(str, survival))}")


# ── Input handling ───────────────────────────────────────────────────

def _handle_re_menu_key(self, key):
    """Handle keys in the snippet/load menu."""
    if key == ord("q") or key == 27:
        self._exit_rule_editor_mode()
        return True

    # Tab between snippets and saved
    if key == ord("\t"):
        self.re_menu_tab = 1 - self.re_menu_tab
        self.re_menu_sel = 0
        return True

    items = _STARTER_SNIPPETS if self.re_menu_tab == 0 else self.re_saved_rules

    if key == ord("j") or key == curses.KEY_DOWN:
        if items:
            self.re_menu_sel = (self.re_menu_sel + 1) % len(items)
        return True
    if key == ord("k") or key == curses.KEY_UP:
        if items:
            self.re_menu_sel = (self.re_menu_sel - 1) % len(items)
        return True

    if key in (ord("\n"), curses.KEY_ENTER, 10, 13):
        if not items:
            return True
        if self.re_menu_tab == 0:
            name, birth, surv = items[self.re_menu_sel]
            self._re_init(birth, surv, name)
        else:
            entry = items[self.re_menu_sel]
            self._re_init(entry.get("birth", "False"),
                          entry.get("survival", "False"),
                          entry.get("name", "Saved Rule"))
        return True

    # 'n' for new blank rule
    if key == ord("n"):
        self._re_init("False", "False", "New Rule")
        return True

    # Delete saved rule with 'x'
    if key == ord("x") and self.re_menu_tab == 1 and self.re_saved_rules:
        del self.re_saved_rules[self.re_menu_sel]
        _save_custom_rules(self.re_saved_rules)
        if self.re_menu_sel >= len(self.re_saved_rules):
            self.re_menu_sel = max(0, len(self.re_saved_rules) - 1)
        self._flash("Rule deleted")
        return True

    return True


def _handle_re_key(self, key):
    """Handle keys in the active rule editor."""
    # If we're editing a text field, route to editor
    if self.re_editing is not None:
        return _handle_re_edit_key(self, key)

    if key == ord("q") or key == 27:
        self._exit_rule_editor_mode()
        return True

    # Play/pause
    if key == ord(" "):
        self.re_running = not self.re_running
        return True

    # Step one generation
    if key == ord("."):
        self._re_step()
        return True

    # Focus navigation
    if key == ord("\t"):
        self.re_focus = (self.re_focus + 1) % 3
        return True

    # Enter to edit focused field
    if key in (ord("\n"), curses.KEY_ENTER, 10, 13):
        if self.re_focus == 0:
            self.re_editing = "birth"
            self.re_edit_buf = self.re_birth_expr
        elif self.re_focus == 1:
            self.re_editing = "survival"
            self.re_edit_buf = self.re_survival_expr
        else:
            self.re_editing = "name"
            self.re_edit_buf = self.re_rule_name
        self.re_edit_cursor = len(self.re_edit_buf)
        return True

    # Speed controls
    if key == ord("+") or key == ord("="):
        self.speed_idx = min(self.speed_idx + 1, len(SPEEDS) - 1)
        return True
    if key == ord("-"):
        self.speed_idx = max(self.speed_idx - 1, 0)
        return True

    # Save
    if key == ord("S"):
        self._re_save_rule()
        return True

    # Adopt to main GoL grid
    if key == ord("a"):
        self._re_adopt_to_gol()
        return True

    # Randomize grid
    if key == ord("r"):
        self._re_randomize_grid()
        return True

    # Clear grid
    if key == ord("c"):
        self.re_grid = [[0] * self.re_cols for _ in range(self.re_rows)]
        self.re_population = 0
        self.re_generation = 0
        self.re_pop_history.clear()
        return True

    # Import from EP
    if key == ord("i"):
        self._re_import_from_ep()
        return True

    # Back to menu
    if key == ord("m"):
        self.re_mode = False
        self.re_menu = True
        self.re_menu_sel = 0
        self.re_saved_rules = _load_custom_rules()
        return True

    return True


def _handle_re_edit_key(self, key):
    """Handle keys while editing an expression text field."""
    # Escape: cancel edit
    if key == 27:
        self.re_editing = None
        return True

    # Enter: confirm edit
    if key in (ord("\n"), curses.KEY_ENTER, 10, 13):
        if self.re_editing == "birth":
            self.re_birth_expr = self.re_edit_buf
            self.re_birth_code, self.re_birth_err = _compile_expr(self.re_edit_buf)
        elif self.re_editing == "survival":
            self.re_survival_expr = self.re_edit_buf
            self.re_survival_code, self.re_survival_err = _compile_expr(self.re_edit_buf)
        elif self.re_editing == "name":
            self.re_rule_name = self.re_edit_buf
        self.re_editing = None
        return True

    # Backspace
    if key in (curses.KEY_BACKSPACE, 127, 8):
        if self.re_edit_cursor > 0:
            self.re_edit_buf = (self.re_edit_buf[:self.re_edit_cursor - 1]
                                + self.re_edit_buf[self.re_edit_cursor:])
            self.re_edit_cursor -= 1
        return True

    # Delete
    if key == curses.KEY_DC:
        if self.re_edit_cursor < len(self.re_edit_buf):
            self.re_edit_buf = (self.re_edit_buf[:self.re_edit_cursor]
                                + self.re_edit_buf[self.re_edit_cursor + 1:])
        return True

    # Arrow keys
    if key == curses.KEY_LEFT:
        self.re_edit_cursor = max(0, self.re_edit_cursor - 1)
        return True
    if key == curses.KEY_RIGHT:
        self.re_edit_cursor = min(len(self.re_edit_buf), self.re_edit_cursor + 1)
        return True
    if key == curses.KEY_HOME:
        self.re_edit_cursor = 0
        return True
    if key == curses.KEY_END:
        self.re_edit_cursor = len(self.re_edit_buf)
        return True

    # Ctrl+A: select all (go to start)
    if key == 1:
        self.re_edit_cursor = 0
        return True
    # Ctrl+E: end
    if key == 5:
        self.re_edit_cursor = len(self.re_edit_buf)
        return True
    # Ctrl+K: kill to end of line
    if key == 11:
        self.re_edit_buf = self.re_edit_buf[:self.re_edit_cursor]
        return True
    # Ctrl+U: kill to start of line
    if key == 21:
        self.re_edit_buf = self.re_edit_buf[self.re_edit_cursor:]
        self.re_edit_cursor = 0
        return True

    # Printable character
    if 32 <= key <= 126:
        ch = chr(key)
        self.re_edit_buf = (self.re_edit_buf[:self.re_edit_cursor]
                            + ch
                            + self.re_edit_buf[self.re_edit_cursor:])
        self.re_edit_cursor += 1
        return True

    return True


# ── Drawing ──────────────────────────────────────────────────────────

def _draw_re_menu(self, max_y, max_x):
    """Draw the snippet / saved rules selection menu."""
    self.stdscr.erase()
    row = 1
    title = "═══ Live Rule Editor ═══"
    if max_x > len(title) + 2:
        self.stdscr.addstr(row, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD)
    row += 2

    # Tabs
    tab_strs = ["[Snippets]", "[Saved Rules]"]
    tab_line = "  ".join(
        f" {s} " if i != self.re_menu_tab else f">{s}<"
        for i, s in enumerate(tab_strs)
    )
    try:
        self.stdscr.addstr(row, 2, f"Tab to switch:  {tab_line}")
    except curses.error:
        pass
    row += 2

    items = _STARTER_SNIPPETS if self.re_menu_tab == 0 else self.re_saved_rules

    if not items:
        try:
            msg = "No saved rules yet." if self.re_menu_tab == 1 else "No snippets."
            self.stdscr.addstr(row, 4, msg, curses.A_DIM)
        except curses.error:
            pass
        row += 2
    else:
        visible = max_y - row - 6
        scroll = max(0, self.re_menu_sel - visible + 1)
        for i in range(scroll, min(len(items), scroll + visible)):
            if self.re_menu_tab == 0:
                name, birth, surv = items[i]
            else:
                name = items[i].get("name", "?")
                birth = items[i].get("birth", "?")
                surv = items[i].get("survival", "?")

            prefix = "▸ " if i == self.re_menu_sel else "  "
            attr = curses.A_REVERSE if i == self.re_menu_sel else 0
            label = f"{prefix}{name}"
            try:
                self.stdscr.addstr(row, 2, label[:max_x - 4], attr)
            except curses.error:
                pass
            row += 1
            detail = f"    B: {birth}"
            try:
                self.stdscr.addstr(row, 2, detail[:max_x - 4], curses.A_DIM)
            except curses.error:
                pass
            row += 1
            detail2 = f"    S: {surv}"
            try:
                self.stdscr.addstr(row, 2, detail2[:max_x - 4], curses.A_DIM)
            except curses.error:
                pass
            row += 1

    # Footer
    footer_row = max_y - 3
    hints = "Enter=Load  n=New blank  Tab=Switch tab  q=Quit"
    if self.re_menu_tab == 1:
        hints += "  x=Delete"
    try:
        self.stdscr.addstr(footer_row, 2, hints[:max_x - 4], curses.A_DIM)
    except curses.error:
        pass


def _draw_re(self, max_y, max_x):
    """Draw the live rule editor: grid on top, editor panel at bottom."""
    self.stdscr.erase()

    # ── Title bar ──
    status = "▶ Running" if self.re_running else "‖ Paused"
    title = f" {self.re_rule_name}  │  Gen {self.re_generation}  │  Pop {self.re_population}  │  {status} "
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.A_BOLD | curses.A_REVERSE)
        # Pad the rest of line
        pad = max_x - 1 - len(title)
        if pad > 0:
            self.stdscr.addstr(0, len(title), " " * pad, curses.A_REVERSE)
    except curses.error:
        pass

    # ── Grid area ──
    grid_top = 1
    grid_height = max(1, max_y - 7)  # leave 6 rows for editor panel
    grid_width = (max_x - 1) // 2

    for r in range(min(self.re_rows, grid_height)):
        for c in range(min(self.re_cols, grid_width)):
            val = self.re_grid[r][c]
            if val > 0:
                # Color by age
                age_idx = min(val, 7)
                try:
                    pair = curses.color_pair(age_idx % 7 + 1)
                    bright = curses.A_BOLD if val > 3 else 0
                    self.stdscr.addstr(grid_top + r, c * 2, "██", pair | bright)
                except curses.error:
                    pass

    # ── Editor panel ──
    panel_top = max_y - 6
    sep = "─" * (max_x - 1)
    try:
        self.stdscr.addstr(panel_top, 0, sep[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    # Birth expression
    row = panel_top + 1
    _draw_re_field(self, row, max_x, "Birth", self.re_birth_expr,
                   self.re_birth_err, self.re_focus == 0,
                   self.re_editing == "birth", self.re_edit_buf,
                   self.re_edit_cursor)
    # Survival expression
    row = panel_top + 2
    _draw_re_field(self, row, max_x, "Surv ", self.re_survival_expr,
                   self.re_survival_err, self.re_focus == 1,
                   self.re_editing == "survival", self.re_edit_buf,
                   self.re_edit_cursor)
    # Name field
    row = panel_top + 3
    _draw_re_field(self, row, max_x, "Name ", self.re_rule_name,
                   None, self.re_focus == 2,
                   self.re_editing == "name", self.re_edit_buf,
                   self.re_edit_cursor)

    # Hints bar
    row = panel_top + 5
    if self.re_editing:
        hints = "Enter=Confirm  Esc=Cancel  ←→=Move  Ctrl+K=Kill"
    else:
        hints = "Enter=Edit  Tab=Next  Space=Play/Pause  .=Step  r=Rand  c=Clear  S=Save  a=Adopt  i=EP import  m=Menu  q=Quit"
    try:
        self.stdscr.addstr(row, 0, hints[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


def _draw_re_field(self, row, max_x, label, value, error, focused, editing,
                   edit_buf, edit_cursor):
    """Draw a single editable field in the editor panel."""
    prefix = "▸" if focused else " "
    attr = curses.A_BOLD if focused else 0

    if editing:
        # Show editable buffer with cursor
        display = f"{prefix}{label}: {edit_buf}"
        try:
            self.stdscr.addstr(row, 0, display[:max_x - 1], attr)
            # Position cursor visually
            cursor_x = len(f"{prefix}{label}: ") + edit_cursor
            if cursor_x < max_x - 1:
                self.stdscr.addstr(row, cursor_x, "▏", curses.A_BLINK | curses.A_BOLD)
        except curses.error:
            pass
    else:
        display = f"{prefix}{label}: {value}"
        try:
            self.stdscr.addstr(row, 0, display[:max_x - 1], attr)
        except curses.error:
            pass
        if error:
            err_display = f"  ✗ {error}"
            try:
                self.stdscr.addstr(row, min(len(display), max_x - len(err_display) - 1),
                                   err_display[:max_x - 1],
                                   curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass


# ── Registration ─────────────────────────────────────────────────────

def register(App):
    """Attach rule-editor methods to the App class."""
    App._enter_rule_editor_mode = _enter_rule_editor_mode
    App._exit_rule_editor_mode = _exit_rule_editor_mode
    App._re_init = _re_init
    App._re_step = _re_step
    App._re_save_rule = _re_save_rule
    App._re_adopt_to_gol = _re_adopt_to_gol
    App._re_randomize_grid = _re_randomize_grid
    App._re_import_from_ep = _re_import_from_ep
    App._handle_re_menu_key = _handle_re_menu_key
    App._handle_re_key = _handle_re_key
    App._draw_re_menu = _draw_re_menu
    App._draw_re = _draw_re
