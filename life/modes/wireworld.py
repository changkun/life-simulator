"""Mode: ww — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS, SPEED_LABELS
from life.grid import Grid

def _ww_step(self):
    """Advance the Wireworld simulation by one generation."""
    new_grid: dict[tuple[int, int], int] = {}
    # Gather all cells that need checking: conductors and their neighbors
    check_cells: set[tuple[int, int]] = set()
    for (r, c), state in self.ww_grid.items():
        check_cells.add((r, c))
        if state == self.WW_CONDUCTOR:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % self.ww_rows
                    nc = (c + dc) % self.ww_cols
                    check_cells.add((nr, nc))

    for (r, c) in check_cells:
        state = self.ww_grid.get((r, c), self.WW_EMPTY)
        if state == self.WW_EMPTY:
            continue  # empty stays empty
        elif state == self.WW_HEAD:
            new_grid[(r, c)] = self.WW_TAIL
        elif state == self.WW_TAIL:
            new_grid[(r, c)] = self.WW_CONDUCTOR
        elif state == self.WW_CONDUCTOR:
            # Count electron head neighbors
            head_count = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % self.ww_rows
                    nc = (c + dc) % self.ww_cols
                    if self.ww_grid.get((nr, nc), 0) == self.WW_HEAD:
                        head_count += 1
            if head_count == 1 or head_count == 2:
                new_grid[(r, c)] = self.WW_HEAD
            else:
                new_grid[(r, c)] = self.WW_CONDUCTOR

    self.ww_grid = new_grid
    self.ww_generation += 1



def _ww_init(self, preset_cells: dict[tuple[int, int], int] | None = None):
    """Initialize the Wireworld grid."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.ww_rows = max_y - 5
    self.ww_cols = (max_x - 1) // 2
    if self.ww_rows < 10:
        self.ww_rows = 10
    if self.ww_cols < 10:
        self.ww_cols = 10
    self.ww_grid = {}
    self.ww_generation = 0
    self.ww_cursor_r = self.ww_rows // 2
    self.ww_cursor_c = self.ww_cols // 2
    if preset_cells:
        # Center the preset on the grid
        if preset_cells:
            min_r = min(r for r, c in preset_cells)
            max_r = max(r for r, c in preset_cells)
            min_c = min(c for r, c in preset_cells)
            max_c = max(c for r, c in preset_cells)
            off_r = self.ww_rows // 2 - (min_r + max_r) // 2
            off_c = self.ww_cols // 2 - (min_c + max_c) // 2
            for (r, c), state in preset_cells.items():
                nr = (r + off_r) % self.ww_rows
                nc = (c + off_c) % self.ww_cols
                self.ww_grid[(nr, nc)] = state



def _enter_ww_mode(self):
    """Enter Wireworld mode — show preset menu first."""
    self.ww_menu = True
    self.ww_menu_sel = 0
    self._flash("Wireworld — select a preset or start empty")



def _exit_ww_mode(self):
    """Exit Wireworld mode."""
    self.ww_mode = False
    self.ww_menu = False
    self.ww_running = False
    self.ww_grid = {}
    self._flash("Wireworld mode OFF")



def _handle_ww_menu_key(self, key: int) -> bool:
    """Handle keys in the Wireworld preset selection menu."""
    if key == -1:
        return True
    n_presets = len(self.WW_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.ww_menu_sel = (self.ww_menu_sel - 1) % n_presets
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.ww_menu_sel = (self.ww_menu_sel + 1) % n_presets
        return True
    if key == ord("q") or key == 27:
        self.ww_menu = False
        self._flash("Wireworld cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        name, desc, cells = self.WW_PRESETS[self.ww_menu_sel]
        self.ww_menu = False
        self.ww_mode = True
        self.ww_running = False
        self.ww_drawing = True
        self._ww_init(cells if cells else None)
        self._flash(f"Wireworld [{name}] — e=draw, Space=play, n=step, q=exit")
        return True
    return True



def _handle_ww_key(self, key: int) -> bool:
    """Handle keys while in Wireworld mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_ww_mode()
        return True
    if key == ord(" "):
        self.ww_running = not self.ww_running
        if self.ww_running:
            self.ww_drawing = False
        self._flash("Playing" if self.ww_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.ww_running = False
        self._ww_step()
        return True
    if key == ord("r"):
        self._ww_init()
        self._flash("Grid cleared")
        return True
    if key == ord("R") or key == ord("m"):
        self.ww_mode = False
        self.ww_running = False
        self.ww_menu = True
        self.ww_menu_sel = 0
        return True
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    # Cursor movement
    if key == curses.KEY_UP or key == ord("k"):
        self.ww_cursor_r = (self.ww_cursor_r - 1) % self.ww_rows
        if self.ww_drawing and not self.ww_running:
            self._ww_paint()
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.ww_cursor_r = (self.ww_cursor_r + 1) % self.ww_rows
        if self.ww_drawing and not self.ww_running:
            self._ww_paint()
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        self.ww_cursor_c = (self.ww_cursor_c - 1) % self.ww_cols
        if self.ww_drawing and not self.ww_running:
            self._ww_paint()
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        self.ww_cursor_c = (self.ww_cursor_c + 1) % self.ww_cols
        if self.ww_drawing and not self.ww_running:
            self._ww_paint()
        return True
    # Drawing controls
    if key == ord("e"):
        self.ww_drawing = not self.ww_drawing
        self._flash("Draw mode ON" if self.ww_drawing else "Draw mode OFF")
        return True
    if key == ord("1"):
        self.ww_draw_state = self.WW_CONDUCTOR
        self._flash("Brush: conductor (orange)")
        return True
    if key == ord("2"):
        self.ww_draw_state = self.WW_HEAD
        self._flash("Brush: electron head (blue)")
        return True
    if key == ord("3"):
        self.ww_draw_state = self.WW_TAIL
        self._flash("Brush: electron tail (white)")
        return True
    if key == ord("0"):
        self.ww_draw_state = self.WW_EMPTY
        self._flash("Brush: eraser")
        return True
    # Toggle cell at cursor
    if key == 10 or key == 13 or key == curses.KEY_ENTER:
        pos = (self.ww_cursor_r, self.ww_cursor_c)
        current = self.ww_grid.get(pos, self.WW_EMPTY)
        # Cycle through states: empty -> conductor -> head -> tail -> empty
        next_state = (current + 1) % 4
        if next_state == self.WW_EMPTY:
            self.ww_grid.pop(pos, None)
        else:
            self.ww_grid[pos] = next_state
        return True
    return True



def _ww_paint(self):
    """Paint the current draw_state at cursor position."""
    pos = (self.ww_cursor_r, self.ww_cursor_c)
    if self.ww_draw_state == self.WW_EMPTY:
        self.ww_grid.pop(pos, None)
    else:
        self.ww_grid[pos] = self.ww_draw_state



def _draw_ww_menu(self, max_y: int, max_x: int):
    """Draw the Wireworld preset selection menu."""
    title = "── Wireworld ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    subtitle = "4-state cellular automaton for circuit simulation"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n_presets = len(self.WW_PRESETS)
    for i, (name, desc, _cells) in enumerate(self.WW_PRESETS):
        y = 5 + i
        if y >= max_y - 8:
            break
        line = f"  {name:<14s} {desc}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.ww_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    # Info section
    info_y = 5 + min(n_presets, max_y - 13) + 1
    info_lines = [
        "States: empty (black), conductor (orange), electron head (blue), electron tail (white)",
        "Rules: head->tail, tail->conductor, conductor->head if 1 or 2 head neighbors",
        "Draw circuits, add electrons, and watch signals flow!",
    ]
    for i, info in enumerate(info_lines):
        y = info_y + i
        if y >= max_y - 2:
            break
        try:
            self.stdscr.addstr(y, 2, info[:max_x - 3], curses.color_pair(1))
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate [Enter]=select [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_ww(self, max_y: int, max_x: int):
    """Draw the Wireworld simulation."""
    # Title bar
    heads = sum(1 for s in self.ww_grid.values() if s == self.WW_HEAD)
    tails = sum(1 for s in self.ww_grid.values() if s == self.WW_TAIL)
    conductors = sum(1 for s in self.ww_grid.values() if s == self.WW_CONDUCTOR)
    title = f" Wireworld  Gen: {self.ww_generation}  Conductors: {conductors}  Heads: {heads}  Tails: {tails}"
    state = " PLAY" if self.ww_running else " PAUSE"
    if self.ww_drawing and not self.ww_running:
        brush_names = {0: "eraser", 1: "conductor", 2: "head", 3: "tail"}
        state += f"  DRAW [{brush_names[self.ww_draw_state]}]"
    title += f"  {state}"
    title = title[:max_x - 1]
    try:
        self.stdscr.addstr(0, 0, title, curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw grid
    draw_start = 1
    draw_rows = max_y - 3
    draw_cols = (max_x - 1) // 2
    if draw_rows < 1:
        draw_rows = 1

    # Color mapping: conductor=yellow/orange(3), head=blue(5), tail=white(8)
    for y in range(draw_rows):
        row_idx = y
        if row_idx >= self.ww_rows:
            break
        screen_y = draw_start + y
        if screen_y >= max_y - 2:
            break
        for x in range(draw_cols):
            col_idx = x
            if col_idx >= self.ww_cols:
                break
            sx = x * 2
            if sx + 1 >= max_x:
                break
            cell_state = self.ww_grid.get((row_idx, col_idx), self.WW_EMPTY)
            is_cursor = (row_idx == self.ww_cursor_r and col_idx == self.ww_cursor_c)
            if is_cursor and not self.ww_running:
                # Draw cursor
                if cell_state == self.WW_EMPTY:
                    ch = "[]"
                else:
                    ch = "\u2588\u2588"
                try:
                    self.stdscr.addstr(screen_y, sx, ch,
                                       curses.color_pair(7) | curses.A_BOLD)
                except curses.error:
                    pass
            elif cell_state == self.WW_HEAD:
                try:
                    self.stdscr.addstr(screen_y, sx, "\u2588\u2588",
                                       curses.color_pair(5))  # blue
                except curses.error:
                    pass
            elif cell_state == self.WW_TAIL:
                try:
                    self.stdscr.addstr(screen_y, sx, "\u2588\u2588",
                                       curses.color_pair(8))  # white
                except curses.error:
                    pass
            elif cell_state == self.WW_CONDUCTOR:
                try:
                    self.stdscr.addstr(screen_y, sx, "\u2588\u2588",
                                       curses.color_pair(3))  # yellow/orange
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        total_cells = len(self.ww_grid)
        status = f" Gen: {self.ww_generation}  |  Cells: {total_cells} (C:{conductors} H:{heads} T:{tails})  |  Speed: {SPEED_LABELS[self.speed_idx]}"
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
            hint = " [Space]=play [n]=step [e]=draw [0-3]=brush [Enter]=cycle [r]=clear [R]=menu [</>]=speed [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register ww mode methods on the App class."""
    App._ww_step = _ww_step
    App._ww_init = _ww_init
    App._enter_ww_mode = _enter_ww_mode
    App._exit_ww_mode = _exit_ww_mode
    App._handle_ww_menu_key = _handle_ww_menu_key
    App._handle_ww_key = _handle_ww_key
    App._ww_paint = _ww_paint
    App._draw_ww_menu = _draw_ww_menu
    App._draw_ww = _draw_ww

