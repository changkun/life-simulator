"""Mode: compare — simulation mode for the life package."""
import curses
import math
import random
import time


from life.colors import color_for_age
from life.constants import CELL_CHAR, SPEED_LABELS
from life.grid import Grid
from life.rules import RULE_PRESETS, parse_rule_string, rule_string
from life.utils import sparkline

def _enter_compare_mode(self):
    """Open the rule picker for the second grid to start comparison mode."""
    self.compare_rule_menu = True
    self.compare_rule_sel = 0



def _exit_compare_mode(self):
    """Leave comparison mode and discard the second grid."""
    self.compare_mode = False
    self.grid2 = None
    self.pop_history2.clear()
    self.compare_rule_menu = False
    self._flash("Comparison mode OFF")



def _handle_compare_rule_menu_key(self, key: int) -> bool:
    if key == -1:
        return True
    if key == 27 or key == ord("q"):  # ESC or q
        self.compare_rule_menu = False
        return True
    if key in (curses.KEY_UP, ord("k")):
        self.compare_rule_sel = (self.compare_rule_sel - 1) % len(self.rule_preset_list)
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.compare_rule_sel = (self.compare_rule_sel + 1) % len(self.rule_preset_list)
        return True
    if key in (10, 13, curses.KEY_ENTER):  # Enter — apply preset
        name = self.rule_preset_list[self.compare_rule_sel]
        preset = RULE_PRESETS[name]
        self._start_compare(set(preset["birth"]), set(preset["survival"]))
        return True
    if key == ord("/"):  # Custom rule entry
        self.compare_rule_menu = False
        rs = self._prompt_text("Second rule (e.g. B36/S23)")
        if rs:
            parsed = parse_rule_string(rs)
            if parsed:
                self._start_compare(parsed[0], parsed[1])
            else:
                self._flash("Invalid rule string (use format B.../S...)")
        return True
    return True



def _draw_compare_rule_menu(self, max_y: int, max_x: int):
    title = "── Pick Second Rule for Comparison (Enter=select, /=custom, q/Esc=cancel) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    current = rule_string(self.grid.birth, self.grid.survival)
    current_line = f"Left panel rule: {current}  —  Select rule for right panel:"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(current_line)) // 2), current_line,
                           curses.color_pair(6))
    except curses.error:
        pass
    for i, name in enumerate(self.rule_preset_list):
        y = 5 + i
        if y >= max_y - 1:
            break
        preset = RULE_PRESETS[name]
        rs = rule_string(preset["birth"], preset["survival"])
        line = f"  {name:<20s} {rs}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.compare_rule_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line, attr)
        except curses.error:
            pass
    tip_y = 5 + len(self.rule_preset_list) + 1
    if tip_y < max_y - 1:
        tip = "Press / to type a custom rule string (e.g. B36/S23)"
        try:
            self.stdscr.addstr(tip_y, max(0, (max_x - len(tip)) // 2), tip,
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

def _start_compare(self, birth2: set, survival2: set):
    """Clone the current grid into a second grid with different rules and start comparison."""
    self.grid2 = Grid(self.grid.rows, self.grid.cols)
    # Copy cell state from the primary grid
    for r in range(self.grid.rows):
        for c in range(self.grid.cols):
            self.grid2.cells[r][c] = self.grid.cells[r][c]
    self.grid2.generation = self.grid.generation
    self.grid2.population = self.grid.population
    # Apply the chosen rule to the second grid
    self.grid2.birth = birth2
    self.grid2.survival = survival2
    self.pop_history2 = list(self.pop_history)
    self.compare_mode = True
    self.compare_rule_menu = False
    r1 = rule_string(self.grid.birth, self.grid.survival)
    r2 = rule_string(birth2, survival2)
    self._flash(f"Comparing: {r1} vs {r2}  (V to exit)")


# ── Race mode ──



def _draw_compare(self, max_y: int, max_x: int):
    """Draw split-screen comparison of two grids side by side."""
    # Layout: [left grid] [divider col] [right grid]
    # Each cell = 2 screen columns, divider = 1 column
    half_x = max_x // 2
    divider_x = half_x  # column for the vertical divider
    vis_rows = max_y - 4  # leave room for status + sparkline

    # Each panel's cell columns
    left_cell_cols = (divider_x) // 2
    right_cell_cols = (max_x - divider_x - 1) // 2

    # Centre viewport on cursor for both panels
    self.view_r = self.cursor_r - vis_rows // 2
    self.view_c = self.cursor_c - left_cell_cols // 2

    # Draw left panel (grid 1)
    for sy in range(min(vis_rows, self.grid.rows)):
        gr = (self.view_r + sy) % self.grid.rows
        for sx in range(min(left_cell_cols, self.grid.cols)):
            gc = (self.view_c + sx) % self.grid.cols
            age = self.grid.cells[gr][gc]
            px = sx * 2
            py = sy
            if py >= max_y - 3 or px + 1 >= divider_x:
                continue
            if age > 0:
                try:
                    self.stdscr.addstr(py, px, CELL_CHAR, color_for_age(age))
                except curses.error:
                    pass

    # Draw vertical divider
    for sy in range(min(vis_rows, max_y - 3)):
        try:
            self.stdscr.addstr(sy, divider_x, "│", curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Draw right panel (grid 2)
    right_start = divider_x + 1
    for sy in range(min(vis_rows, self.grid2.rows)):
        gr = (self.view_r + sy) % self.grid2.rows
        for sx in range(min(right_cell_cols, self.grid2.cols)):
            gc = (self.view_c + sx) % self.grid2.cols
            age = self.grid2.cells[gr][gc]
            px = right_start + sx * 2
            py = sy
            if py >= max_y - 3 or px + 1 >= max_x:
                continue
            if age > 0:
                try:
                    self.stdscr.addstr(py, px, CELL_CHAR, color_for_age(age))
                except curses.error:
                    pass

    # Panel labels
    r1 = rule_string(self.grid.birth, self.grid.survival)
    r2 = rule_string(self.grid2.birth, self.grid2.survival)
    label_y = max_y - 4
    if label_y > 0:
        l1 = f" {r1}  Pop: {self.grid.population}"
        l2 = f" {r2}  Pop: {self.grid2.population}"
        try:
            self.stdscr.addstr(label_y, 0, l1[:divider_x], curses.color_pair(7) | curses.A_BOLD)
            self.stdscr.addstr(label_y, right_start, l2[:max_x - right_start - 1],
                               curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Dual sparklines
    spark_y = max_y - 3
    if spark_y > 0:
        spark_w = divider_x - 2
        if spark_w > 0 and len(self.pop_history) > 1:
            try:
                s1 = sparkline(self.pop_history, spark_w)
                self.stdscr.addstr(spark_y, 0, " " + s1, curses.color_pair(1))
            except curses.error:
                pass
        spark_w2 = max_x - right_start - 1
        if spark_w2 > 0 and len(self.pop_history2) > 1:
            try:
                s2 = sparkline(self.pop_history2, spark_w2)
                self.stdscr.addstr(spark_y, right_start, " " + s2, curses.color_pair(1))
            except curses.error:
                pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        state = "▶ PLAY" if self.running else "⏸ PAUSE"
        speed = SPEED_LABELS[self.speed_idx]
        status = (
            f" Gen: {self.grid.generation}  │  "
            f"{state}  │  Speed: {speed}  │  "
            f"COMPARE: {r1} vs {r2}"
        )
        status = status[:max_x - 1]
        try:
            self.stdscr.addstr(status_y, 0, status, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play/pause [n]=step [+/-]=speed [V]=exit compare [Arrows]=scroll [q]=quit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass




def register(App):
    """Register compare mode methods on the App class."""
    App._enter_compare_mode = _enter_compare_mode
    App._exit_compare_mode = _exit_compare_mode
    App._start_compare = _start_compare
    App._handle_compare_rule_menu_key = _handle_compare_rule_menu_key
    App._draw_compare_rule_menu = _draw_compare_rule_menu
    App._draw_compare = _draw_compare

