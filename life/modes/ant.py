"""Mode: ant — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS, SPEED_LABELS

def _ant_step(self):
    """Advance all ants by one step."""
    for ant in self.ant_ants:
        r, c = ant["r"], ant["c"]
        color_state = self.ant_grid.get((r, c), 0)
        rule_len = len(self.ant_rule)
        turn = self.ant_rule[color_state % rule_len]
        # Turn: R = clockwise, L = counterclockwise
        # Directions: 0=up, 1=right, 2=down, 3=left
        if turn == "R":
            ant["dir"] = (ant["dir"] + 1) % 4
        else:  # L
            ant["dir"] = (ant["dir"] - 1) % 4
        # Flip color to next state
        new_state = (color_state + 1) % rule_len
        if new_state == 0:
            self.ant_grid.pop((r, c), None)
        else:
            self.ant_grid[(r, c)] = new_state
        # Move forward
        dr = [-1, 0, 1, 0]
        dc = [0, 1, 0, -1]
        ant["r"] = (r + dr[ant["dir"]]) % self.ant_rows
        ant["c"] = (c + dc[ant["dir"]]) % self.ant_cols
    self.ant_step_count += 1



def _ant_init(self):
    """Initialize the ant grid and place ants."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.ant_rows = max_y - 5
    self.ant_cols = (max_x - 1) // 2
    if self.ant_rows < 10:
        self.ant_rows = 10
    if self.ant_cols < 10:
        self.ant_cols = 10
    self.ant_grid = {}
    self.ant_step_count = 0
    self.ant_ants = []
    center_r = self.ant_rows // 2
    center_c = self.ant_cols // 2
    if self.ant_num_ants == 1:
        self.ant_ants.append({"r": center_r, "c": center_c, "dir": 0, "color_idx": 0})
    else:
        # Place ants symmetrically around center
        for i in range(self.ant_num_ants):
            angle_idx = (i * 4) // self.ant_num_ants  # spread directions
            offset = max(1, self.ant_rows // 8)
            dr = [-1, 0, 1, 0]
            dc = [0, 1, 0, -1]
            ar = center_r + dr[angle_idx % 4] * offset
            ac = center_c + dc[angle_idx % 4] * offset
            self.ant_ants.append({
                "r": ar % self.ant_rows,
                "c": ac % self.ant_cols,
                "dir": angle_idx % 4,
                "color_idx": i % len(self.ANT_COLORS),
            })



def _enter_ant_mode(self):
    """Enter Langton's Ant mode — show menu first."""
    self.ant_menu = True
    self.ant_menu_sel = 0
    self._flash("Langton's Ant — select a rule")



def _exit_ant_mode(self):
    """Exit Langton's Ant mode."""
    self.ant_mode = False
    self.ant_menu = False
    self.ant_running = False
    self.ant_grid = {}
    self.ant_ants = []
    self._flash("Langton's Ant mode OFF")



def _handle_ant_menu_key(self, key: int) -> bool:
    """Handle keys in the ant rule selection menu."""
    if key == -1:
        return True
    n_presets = len(self.ANT_PRESETS)
    total_items = n_presets + 4  # custom rule, num ants, steps/frame, start
    if key == curses.KEY_UP or key == ord("k"):
        self.ant_menu_sel = (self.ant_menu_sel - 1) % total_items
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.ant_menu_sel = (self.ant_menu_sel + 1) % total_items
        return True
    if key == ord("q") or key == 27:
        self.ant_menu = False
        self._flash("Langton's Ant cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if self.ant_menu_sel < n_presets:
            self.ant_rule = self.ANT_PRESETS[self.ant_menu_sel][0]
        elif self.ant_menu_sel == n_presets:
            # Custom rule input
            txt = self._prompt_text("Enter rule string (R/L chars, e.g. RLR)")
            if txt is not None:
                txt = txt.upper().strip()
                if len(txt) >= 2 and all(ch in "RL" for ch in txt):
                    self.ant_rule = txt
                else:
                    self._flash("Rule must be 2+ chars of R and L only")
                    return True
            else:
                return True
        elif self.ant_menu_sel == n_presets + 1:
            # Cycle number of ants
            choices = [1, 2, 3, 4]
            idx = choices.index(self.ant_num_ants) if self.ant_num_ants in choices else 0
            self.ant_num_ants = choices[(idx + 1) % len(choices)]
            return True
        elif self.ant_menu_sel == n_presets + 2:
            # Cycle steps per frame
            choices = [1, 5, 10, 50, 100, 500]
            idx = choices.index(self.ant_steps_per_frame) if self.ant_steps_per_frame in choices else 0
            self.ant_steps_per_frame = choices[(idx + 1) % len(choices)]
            return True
        elif self.ant_menu_sel == n_presets + 3:
            # Start
            pass
        # Start the mode
        self.ant_menu = False
        self.ant_mode = True
        self.ant_running = False
        self._ant_init()
        self._flash(f"Langton's Ant [{self.ant_rule}] — Space=play, n=step, q=exit")
        return True
    return True



def _handle_ant_key(self, key: int) -> bool:
    """Handle keys while in Langton's Ant mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_ant_mode()
        return True
    if key == ord(" "):
        self.ant_running = not self.ant_running
        self._flash("Playing" if self.ant_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.ant_running = False
        for _ in range(self.ant_steps_per_frame):
            self._ant_step()
        return True
    if key == ord("r"):
        self._ant_init()
        self._flash(f"Reset [{self.ant_rule}]")
        return True
    if key == ord("R") or key == ord("m"):
        self.ant_mode = False
        self.ant_running = False
        self.ant_menu = True
        self.ant_menu_sel = 0
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
    if key == ord("+") or key == ord("="):
        choices = [1, 5, 10, 50, 100, 500]
        idx = choices.index(self.ant_steps_per_frame) if self.ant_steps_per_frame in choices else 0
        if idx < len(choices) - 1:
            self.ant_steps_per_frame = choices[idx + 1]
        self._flash(f"Steps/frame: {self.ant_steps_per_frame}")
        return True
    if key == ord("-"):
        choices = [1, 5, 10, 50, 100, 500]
        idx = choices.index(self.ant_steps_per_frame) if self.ant_steps_per_frame in choices else 0
        if idx > 0:
            self.ant_steps_per_frame = choices[idx - 1]
        self._flash(f"Steps/frame: {self.ant_steps_per_frame}")
        return True
    return True



def _draw_ant_menu(self, max_y: int, max_x: int):
    """Draw the Langton's Ant rule selection menu."""
    title = "── Langton's Ant ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    subtitle = "Select a rule string (R=turn right, L=turn left per cell color)"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n_presets = len(self.ANT_PRESETS)
    for i, (rule, desc) in enumerate(self.ANT_PRESETS):
        y = 5 + i
        if y >= max_y - 8:
            break
        line = f"  {rule:<14s} {desc}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.ant_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    extra_y = 5 + min(n_presets, max_y - 13)
    extra_items = [
        f"  [Custom] Enter rule string manually",
        f"  [Ants: {self.ant_num_ants}] Number of ants (press Enter to cycle)",
        f"  [Steps/frame: {self.ant_steps_per_frame}] Simulation speed multiplier",
        f"  >>> Start with rule={self.ant_rule}, ants={self.ant_num_ants} <<<",
    ]
    for i, line in enumerate(extra_items):
        y = extra_y + i
        idx = n_presets + i
        if y >= max_y - 2:
            break
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if idx == self.ant_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    # Info section
    info_y = extra_y + len(extra_items) + 1
    if info_y < max_y - 3:
        info = "  Each char in the rule = what to do on that color (R=right turn, L=left turn)"
        try:
            self.stdscr.addstr(info_y, 1, info[:max_x - 2], curses.color_pair(1))
        except curses.error:
            pass
        if info_y + 1 < max_y - 2:
            info2 = "  Classic RL: highway emerges after ~10,000 steps"
            try:
                self.stdscr.addstr(info_y + 1, 1, info2[:max_x - 2], curses.color_pair(1))
            except curses.error:
                pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate [Enter]=select [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_ant(self, max_y: int, max_x: int):
    """Draw the Langton's Ant simulation."""
    # Title bar
    n_ants = len(self.ant_ants)
    title = f" Langton's Ant [{self.ant_rule}]  Ants: {n_ants}  Step: {self.ant_step_count}  Steps/frame: {self.ant_steps_per_frame}"
    state = " PLAY" if self.ant_running else " PAUSE"
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

    rule_len = len(self.ant_rule)
    # Color mapping for cell states
    state_colors = []
    for s in range(rule_len):
        state_colors.append(curses.color_pair(self.ANT_COLORS[s % len(self.ANT_COLORS)]))

    # Build set of ant positions for overlay
    ant_positions = {}
    for i, ant in enumerate(self.ant_ants):
        ant_positions[(ant["r"], ant["c"])] = i

    for y in range(draw_rows):
        row_idx = y
        if row_idx >= self.ant_rows:
            break
        screen_y = draw_start + y
        if screen_y >= max_y - 2:
            break
        # Build the line character by character
        for x in range(draw_cols):
            col_idx = x
            if col_idx >= self.ant_cols:
                break
            sx = x * 2
            if sx + 1 >= max_x:
                break
            cell_state = self.ant_grid.get((row_idx, col_idx), 0)
            if (row_idx, col_idx) in ant_positions:
                # Draw ant marker
                ant_idx = ant_positions[(row_idx, col_idx)]
                ant_color = self.ANT_COLORS[ant_idx % len(self.ANT_COLORS)]
                # Direction arrows: up, right, down, left
                arrows = ["\u25b2 ", "\u25b6 ", "\u25bc ", "\u25c0 "]
                ant_dir = self.ant_ants[ant_idx]["dir"]
                ch = arrows[ant_dir]
                try:
                    self.stdscr.addstr(screen_y, sx, ch,
                                       curses.color_pair(ant_color) | curses.A_BOLD)
                except curses.error:
                    pass
            elif cell_state > 0:
                color = state_colors[cell_state % rule_len]
                try:
                    self.stdscr.addstr(screen_y, sx, "\u2588\u2588", color)
                except curses.error:
                    pass
            # state 0 = empty, just leave blank

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        colored_cells = len(self.ant_grid)
        status = f" Rule: {self.ant_rule}  |  Step: {self.ant_step_count}  |  Colored: {colored_cells}  |  Ants: {n_ants}  |  Speed: {SPEED_LABELS[self.speed_idx]}"
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
            hint = " [Space]=play [n]=step [+/-]=steps/frame [r]=reset [R]=menu [</>]=speed [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register ant mode methods on the App class."""
    App._ant_step = _ant_step
    App._ant_init = _ant_init
    App._enter_ant_mode = _enter_ant_mode
    App._exit_ant_mode = _exit_ant_mode
    App._handle_ant_menu_key = _handle_ant_menu_key
    App._handle_ant_key = _handle_ant_key
    App._draw_ant_menu = _draw_ant_menu
    App._draw_ant = _draw_ant

