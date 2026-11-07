"""Timeline Branching — fork an alternate timeline from a past frame and run both side by side.

Scrub back with the time-travel keys, then press Ctrl+F to open the fork menu.
A fork copies the grid and runs the copy in a split view next to the original,
optionally under a different rule.

Keys in the split view:
  Space      play/pause both timelines
  n or .     step both timelines once
  < >        slower / faster
  Arrows     scroll the viewport
  Ctrl+F     close the branch view
  q          quit
"""
import curses
import time

from life.colors import color_for_age
from life.constants import CELL_CHAR, SPEED_LABELS, SPEEDS
from life.grid import Grid
from life.rules import parse_rule_string, rule_string
from life.utils import sparkline


# ── State initialization ──

def _tbranch_init(self):
    """Initialize timeline-branching state variables."""
    self.tbranch_mode = False          # whether branch split-view is active
    self.tbranch_grid: Grid | None = None       # the branched grid
    self.tbranch_pop_history: list[int] = []    # pop history for branch
    self.tbranch_origin_gen = 0        # generation at which the fork happened
    self.tbranch_fork_gen = 0          # fork point generation (in history)

    self.tbranch_fork_menu = False     # showing the fork-options menu
    self.tbranch_fork_menu_sel = 0     # selected option in fork menu


# ── Forking ──

def _tbranch_fork_from_current(self):
    """Copy the current grid into a branch grid and open the split view."""
    self.tbranch_grid = Grid(self.grid.rows, self.grid.cols)
    for r in range(self.grid.rows):
        for c in range(self.grid.cols):
            self.tbranch_grid.cells[r][c] = self.grid.cells[r][c]
    self.tbranch_grid.generation = self.grid.generation
    self.tbranch_grid.population = self.grid.population
    self.tbranch_grid.birth = set(self.grid.birth)
    self.tbranch_grid.survival = set(self.grid.survival)
    self.tbranch_grid.hex_mode = self.grid.hex_mode
    self.tbranch_grid.topology = self.grid.topology

    self.tbranch_pop_history = list(self.pop_history)
    self.tbranch_origin_gen = self.grid.generation
    self.tbranch_fork_gen = self.grid.generation
    self.tbranch_mode = True

    # Scrubbed back: drop the later history so the original continues from here.
    if self.timeline_pos is not None:
        self.history = self.history[:self.timeline_pos + 1]
        self.timeline_pos = None

    self.running = False
    r1 = rule_string(self.grid.birth, self.grid.survival)
    r2 = rule_string(self.tbranch_grid.birth, self.tbranch_grid.survival)
    self._flash(f"Forked at Gen {self.tbranch_fork_gen}  {r1} vs {r2}  (Ctrl+F to exit)")


def _tbranch_fork_with_rule(self):
    """Fork the current state, then prompt for a different rule on the branch."""
    rs = self._prompt_text("Branch rule (e.g. B36/S23)")
    if not rs:
        self._flash("Fork cancelled")
        return
    parsed = parse_rule_string(rs)
    if not parsed:
        self._flash("Invalid rule string (use format B.../S...)")
        return
    self._tbranch_fork_from_current()
    self.tbranch_grid.birth, self.tbranch_grid.survival = parsed
    r1 = rule_string(self.grid.birth, self.grid.survival)
    r2 = rule_string(self.tbranch_grid.birth, self.tbranch_grid.survival)
    self._flash(f"Forked at Gen {self.tbranch_fork_gen}  {r1} vs {r2}")


def _tbranch_fork_menu_open(self):
    """Open the fork menu."""
    self.tbranch_fork_menu = True
    self.tbranch_fork_menu_sel = 0


def _tbranch_exit(self):
    """Exit branch view and return to normal simulation."""
    self.tbranch_mode = False
    self.tbranch_grid = None
    self.tbranch_pop_history.clear()
    self.tbranch_fork_menu = False
    self._flash("Branch view closed")


# ── Key handling ──

def _tbranch_handle_key(self, key: int) -> bool:
    """Handle timeline-branch keys. Return True if the key was consumed."""
    if self.tbranch_fork_menu:
        return self._tbranch_handle_fork_menu_key(key)

    if self.tbranch_mode and self.tbranch_grid:
        return self._tbranch_handle_split_key(key)

    # Ctrl+F opens the fork menu only while scrubbed back; otherwise other modes get it.
    if key == 6 and self.timeline_pos is not None:
        self._tbranch_fork_menu_open()
        return True

    return False


def _tbranch_handle_fork_menu_key(self, key: int) -> bool:
    """Handle keys in the fork menu."""
    if key == -1:
        return True
    options = ["Fork with same rules", "Fork with different rule", "Cancel"]
    if key in (curses.KEY_UP, ord("k")):
        self.tbranch_fork_menu_sel = (self.tbranch_fork_menu_sel - 1) % len(options)
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.tbranch_fork_menu_sel = (self.tbranch_fork_menu_sel + 1) % len(options)
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self.tbranch_fork_menu = False
        if self.tbranch_fork_menu_sel == 0:
            self._tbranch_fork_from_current()
        elif self.tbranch_fork_menu_sel == 1:
            self._tbranch_fork_with_rule()
        return True
    if key == 27 or key == ord("q"):  # ESC or q
        self.tbranch_fork_menu = False
        return True
    return True


def _tbranch_handle_split_key(self, key: int) -> bool:
    """Handle keys in the branch split view."""
    if key == -1:
        return True

    if key == 6:  # Ctrl+F
        self._tbranch_exit()
        return True

    if key == ord(" "):
        self.running = not self.running
        self._flash("Playing" if self.running else "Paused")
        return True

    if key == ord("n") or key == ord("."):
        self.running = False
        self._push_history()
        self.grid.step()
        self._record_pop()
        self.tbranch_grid.step()
        self.tbranch_pop_history.append(self.tbranch_grid.population)
        gens_since = self.grid.generation - self.tbranch_fork_gen
        self._flash(f"Step +{gens_since} from fork")
        return True

    if key == ord("<") or key == ord(","):
        if self.speed_idx > 0:
            self.speed_idx -= 1
            self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
            self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True

    if key == curses.KEY_UP:
        self.cursor_r = max(0, self.cursor_r - 1)
        return True
    if key == curses.KEY_DOWN:
        self.cursor_r = min(self.grid.rows - 1, self.cursor_r + 1)
        return True
    if key == curses.KEY_LEFT:
        self.cursor_c = max(0, self.cursor_c - 1)
        return True
    if key == curses.KEY_RIGHT:
        self.cursor_c = min(self.grid.cols - 1, self.cursor_c + 1)
        return True

    if key == ord("q"):
        import sys
        sys.exit(0)

    return True  # consume all keys while in split view


# ── Stepping (called from main loop when running) ──

def _tbranch_step(self):
    """Advance the branch grid; the main loop steps the original."""
    if not self.tbranch_mode or not self.tbranch_grid:
        return
    self.tbranch_grid.step()
    self.tbranch_pop_history.append(self.tbranch_grid.population)


# ── Drawing ──

def _tbranch_draw_fork_menu(self, max_y: int, max_x: int):
    """Draw the fork menu overlay."""
    options = ["Fork with same rules", "Fork with different rule", "Cancel"]
    box_w = 50
    box_h = len(options) + 6
    start_y = max(0, (max_y - box_h) // 2)
    start_x = max(0, (max_x - box_w) // 2)

    title = " Fork Timeline Branch "
    try:
        self.stdscr.addstr(start_y, start_x, "┌" + "─" * (box_w - 2) + "┐",
                           curses.color_pair(7) | curses.A_BOLD)
        self.stdscr.addstr(start_y, start_x + (box_w - len(title)) // 2, title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    gen_info = f"Fork from Gen {self.grid.generation}"
    r1 = rule_string(self.grid.birth, self.grid.survival)
    info_line = f"{gen_info}  (current rule: {r1})"
    try:
        self.stdscr.addstr(start_y + 1, start_x, "│" + " " * (box_w - 2) + "│",
                           curses.color_pair(6))
        self.stdscr.addstr(start_y + 1, start_x + 2, info_line[:box_w - 4],
                           curses.color_pair(6))
    except curses.error:
        pass

    try:
        self.stdscr.addstr(start_y + 2, start_x, "├" + "─" * (box_w - 2) + "┤",
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, opt in enumerate(options):
        y = start_y + 3 + i
        if y >= max_y - 1:
            break
        attr = curses.color_pair(6)
        if i == self.tbranch_fork_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        line = f"  {opt}"
        try:
            self.stdscr.addstr(y, start_x, "│" + " " * (box_w - 2) + "│",
                               curses.color_pair(6) | curses.A_DIM)
            self.stdscr.addstr(y, start_x + 2, line[:box_w - 4], attr)
        except curses.error:
            pass

    bottom_y = start_y + 3 + len(options)
    try:
        self.stdscr.addstr(bottom_y, start_x, "└" + "─" * (box_w - 2) + "┘",
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    hint = "↑↓=select  Enter=confirm  Esc=cancel"
    try:
        self.stdscr.addstr(bottom_y + 1, start_x + (box_w - len(hint)) // 2,
                           hint, curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def _tbranch_draw_split(self, max_y: int, max_x: int):
    """Draw the branch split-view: original (left) vs branch (right)."""
    half_x = max_x // 2
    divider_x = half_x
    vis_rows = max_y - 6  # room for labels, sparklines, status, hints

    left_cell_cols = divider_x // 2
    right_cell_cols = (max_x - divider_x - 1) // 2

    self.view_r = self.cursor_r - vis_rows // 2
    self.view_c = self.cursor_c - left_cell_cols // 2

    for sy in range(min(vis_rows, self.grid.rows)):
        gr = (self.view_r + sy) % self.grid.rows
        for sx in range(min(left_cell_cols, self.grid.cols)):
            gc = (self.view_c + sx) % self.grid.cols
            age = self.grid.cells[gr][gc]
            px = sx * 2
            py = sy
            if py >= max_y - 5 or px + 1 >= divider_x:
                continue
            if age > 0:
                try:
                    self.stdscr.addstr(py, px, CELL_CHAR, color_for_age(age))
                except curses.error:
                    pass

    for sy in range(min(vis_rows, max_y - 5)):
        try:
            self.stdscr.addstr(sy, divider_x, "│", curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    right_start = divider_x + 1
    for sy in range(min(vis_rows, self.tbranch_grid.rows)):
        gr = (self.view_r + sy) % self.tbranch_grid.rows
        for sx in range(min(right_cell_cols, self.tbranch_grid.cols)):
            gc = (self.view_c + sx) % self.tbranch_grid.cols
            age = self.tbranch_grid.cells[gr][gc]
            px = right_start + sx * 2
            py = sy
            if py >= max_y - 5 or px + 1 >= max_x:
                continue
            if age > 0:
                try:
                    self.stdscr.addstr(py, px, CELL_CHAR, color_for_age(age))
                except curses.error:
                    pass

    r1 = rule_string(self.grid.birth, self.grid.survival)
    r2 = rule_string(self.tbranch_grid.birth, self.tbranch_grid.survival)
    gens_since = self.grid.generation - self.tbranch_fork_gen

    label_y = max_y - 6
    if label_y > 0:
        l1 = f" ORIGINAL  {r1}  Gen:{self.grid.generation}  Pop:{self.grid.population}"
        l2 = f" BRANCH  {r2}  Gen:{self.tbranch_grid.generation}  Pop:{self.tbranch_grid.population}"
        try:
            self.stdscr.addstr(label_y, 0, l1[:divider_x], curses.color_pair(7) | curses.A_BOLD)
            self.stdscr.addstr(label_y, right_start, l2[:max_x - right_start - 1],
                               curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    spark_y = max_y - 5
    if spark_y > 0:
        spark_w = divider_x - 2
        if spark_w > 0 and len(self.pop_history) > 1:
            try:
                s1 = sparkline(self.pop_history, spark_w)
                self.stdscr.addstr(spark_y, 0, " " + s1, curses.color_pair(1))
            except curses.error:
                pass
        spark_w2 = max_x - right_start - 1
        if spark_w2 > 0 and len(self.tbranch_pop_history) > 1:
            try:
                s2 = sparkline(self.tbranch_pop_history, spark_w2)
                self.stdscr.addstr(spark_y, right_start, " " + s2, curses.color_pair(1))
            except curses.error:
                pass

    fork_y = max_y - 4
    if fork_y > 0:
        fork_info = f" Fork point: Gen {self.tbranch_fork_gen}  │  +{gens_since} generations since fork"
        if r1 != r2:
            fork_info += f"  │  Rules differ: {r1} vs {r2}"
        fork_info = fork_info[:max_x - 1]
        try:
            self.stdscr.addstr(fork_y, 0, fork_info,
                               curses.color_pair(3) | curses.A_DIM)
        except curses.error:
            pass

    div_y = max_y - 3
    if div_y > 0:
        # Divergence is the share of cells whose alive state differs.
        diff_count = 0
        total = self.grid.rows * self.grid.cols
        for r in range(self.grid.rows):
            for c in range(self.grid.cols):
                a = self.grid.cells[r][c] > 0
                b = self.tbranch_grid.cells[r][c] > 0
                if a != b:
                    diff_count += 1
        pct = diff_count / max(1, total) * 100
        div_bar_w = max_x - 30
        if div_bar_w > 2:
            filled = max(0, min(div_bar_w, int(pct / 100 * div_bar_w)))
            bar = "█" * filled + "░" * (div_bar_w - filled)
            div_str = f" Divergence: {pct:5.1f}% {bar}"
            div_str = div_str[:max_x - 1]
            try:
                self.stdscr.addstr(div_y, 0, div_str, curses.color_pair(6))
            except curses.error:
                pass

    status_y = max_y - 2
    if status_y > 0:
        state = "▶ PLAY" if self.running else "⏸ PAUSE"
        speed = SPEED_LABELS[self.speed_idx]
        status = (
            f" {state}  │  Speed: {speed}  │  "
            f"BRANCH VIEW: {r1} vs {r2}  │  "
            f"+{gens_since} gens from fork"
        )
        status = status[:max_x - 1]
        try:
            self.stdscr.addstr(status_y, 0, status, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " Space=play/pause  n=step  </>=speed  Arrows=scroll  Ctrl+F=exit branch  q=quit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ── Registration ──

def register(App):
    """Bind the timeline-branch methods to App."""
    App._tbranch_init = _tbranch_init
    App._tbranch_fork_from_current = _tbranch_fork_from_current
    App._tbranch_fork_with_rule = _tbranch_fork_with_rule
    App._tbranch_fork_menu_open = _tbranch_fork_menu_open
    App._tbranch_exit = _tbranch_exit
    App._tbranch_handle_key = _tbranch_handle_key
    App._tbranch_handle_fork_menu_key = _tbranch_handle_fork_menu_key
    App._tbranch_handle_split_key = _tbranch_handle_split_key
    App._tbranch_step = _tbranch_step
    App._tbranch_draw_fork_menu = _tbranch_draw_fork_menu
    App._tbranch_draw_split = _tbranch_draw_split
