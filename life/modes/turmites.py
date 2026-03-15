"""Mode: turmite — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS, SPEED_LABELS

def _turmite_step(self):
    """Advance all turmite ants by one step."""
    for ant in self.turmite_ants:
        r, c = ant["r"], ant["c"]
        color = self.turmite_grid.get((r, c), 0)
        state = ant["state"]
        # Look up transition
        write_color, turn, new_state = self.turmite_table[state][color]
        # Write color
        if write_color == 0:
            self.turmite_grid.pop((r, c), None)
        else:
            self.turmite_grid[(r, c)] = write_color
        # Turn: 0=none, 1=right, 2=u-turn, 3=left
        ant["dir"] = (ant["dir"] + turn) % 4
        ant["state"] = new_state
        # Move forward
        dr = [-1, 0, 1, 0]
        dc = [0, 1, 0, -1]
        ant["r"] = (r + dr[ant["dir"]]) % self.turmite_rows
        ant["c"] = (c + dc[ant["dir"]]) % self.turmite_cols
    self.turmite_step_count += 1



def _turmite_init(self):
    """Initialize turmite grid and place a single ant at center."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.turmite_rows = max_y - 5
    self.turmite_cols = (max_x - 1) // 2
    if self.turmite_rows < 10:
        self.turmite_rows = 10
    if self.turmite_cols < 10:
        self.turmite_cols = 10
    self.turmite_grid = {}
    self.turmite_step_count = 0
    self.turmite_ants = []
    center_r = self.turmite_rows // 2
    center_c = self.turmite_cols // 2
    self.turmite_ants.append({"r": center_r, "c": center_c, "dir": 0, "state": 0})



def _enter_turmite_mode(self):
    """Enter Turmites mode — show preset menu."""
    self.turmite_menu = True
    self.turmite_menu_sel = 0
    self._flash("Turmites (2D Turing Machine) — select a preset")



def _exit_turmite_mode(self):
    """Exit Turmites mode."""
    self.turmite_mode = False
    self.turmite_menu = False
    self.turmite_running = False
    self.turmite_grid = {}
    self.turmite_ants = []
    self._flash("Turmites mode OFF")



def _handle_turmite_menu_key(self, key: int) -> bool:
    """Handle keys in the turmite preset selection menu."""
    if key == -1:
        return True
    n_presets = len(self.TURMITE_PRESETS)
    total_items = n_presets + 2  # steps/frame, start
    if key == curses.KEY_UP or key == ord("k"):
        self.turmite_menu_sel = (self.turmite_menu_sel - 1) % total_items
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.turmite_menu_sel = (self.turmite_menu_sel + 1) % total_items
        return True
    if key == ord("q") or key == 27:
        self.turmite_menu = False
        self._flash("Turmites cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if self.turmite_menu_sel < n_presets:
            name, desc, nc, ns, table = self.TURMITE_PRESETS[self.turmite_menu_sel]
            self.turmite_num_colors = nc
            self.turmite_num_states = ns
            self.turmite_table = [row[:] for row in table]
            self.turmite_preset_name = name
        elif self.turmite_menu_sel == n_presets:
            # Cycle steps per frame
            choices = [1, 5, 10, 50, 100, 500]
            idx = choices.index(self.turmite_steps_per_frame) if self.turmite_steps_per_frame in choices else 0
            self.turmite_steps_per_frame = choices[(idx + 1) % len(choices)]
            return True
        elif self.turmite_menu_sel == n_presets + 1:
            # Start — use whatever preset was last selected (default first)
            if not self.turmite_table:
                name, desc, nc, ns, table = self.TURMITE_PRESETS[0]
                self.turmite_num_colors = nc
                self.turmite_num_states = ns
                self.turmite_table = [row[:] for row in table]
                self.turmite_preset_name = name
        # Start the mode
        self.turmite_menu = False
        self.turmite_mode = True
        self.turmite_running = False
        self._turmite_init()
        self._flash(f"Turmites [{self.turmite_preset_name}] — Space=play, n=step, q=exit")
        return True
    return True



def _handle_turmite_key(self, key: int) -> bool:
    """Handle keys while in Turmites mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_turmite_mode()
        return True
    if key == ord(" "):
        self.turmite_running = not self.turmite_running
        self._flash("Playing" if self.turmite_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.turmite_running = False
        for _ in range(self.turmite_steps_per_frame):
            self._turmite_step()
        return True
    if key == ord("r"):
        self._turmite_init()
        self._flash(f"Reset [{self.turmite_preset_name}]")
        return True
    if key == ord("R") or key == ord("m"):
        self.turmite_mode = False
        self.turmite_running = False
        self.turmite_menu = True
        self.turmite_menu_sel = 0
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
        idx = choices.index(self.turmite_steps_per_frame) if self.turmite_steps_per_frame in choices else 0
        if idx < len(choices) - 1:
            self.turmite_steps_per_frame = choices[idx + 1]
        self._flash(f"Steps/frame: {self.turmite_steps_per_frame}")
        return True
    if key == ord("-"):
        choices = [1, 5, 10, 50, 100, 500]
        idx = choices.index(self.turmite_steps_per_frame) if self.turmite_steps_per_frame in choices else 0
        if idx > 0:
            self.turmite_steps_per_frame = choices[idx - 1]
        self._flash(f"Steps/frame: {self.turmite_steps_per_frame}")
        return True
    return True



def _draw_turmite_menu(self, max_y: int, max_x: int):
    """Draw the Turmites preset selection menu."""
    title = "── Turmites (2D Turing Machine) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    subtitle = "Select a turmite preset (state-transition table defines behavior)"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n_presets = len(self.TURMITE_PRESETS)
    for i, (name, desc, nc, ns, table) in enumerate(self.TURMITE_PRESETS):
        y = 5 + i
        if y >= max_y - 8:
            break
        line = f"  {name:<18s} {desc}  ({ns}S/{nc}C)"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.turmite_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    extra_y = 5 + min(n_presets, max_y - 13)
    extra_items = [
        f"  [Steps/frame: {self.turmite_steps_per_frame}] Simulation speed multiplier",
        f"  >>> Start with {self.turmite_preset_name or self.TURMITE_PRESETS[0][0]} <<<",
    ]
    for i, line in enumerate(extra_items):
        y = extra_y + i
        idx = n_presets + i
        if y >= max_y - 2:
            break
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if idx == self.turmite_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    # Info section
    info_y = extra_y + len(extra_items) + 1
    if info_y < max_y - 3:
        info = "  Turmites generalize Langton's Ant: an ant with internal states"
        try:
            self.stdscr.addstr(info_y, 1, info[:max_x - 2], curses.color_pair(1))
        except curses.error:
            pass
        if info_y + 1 < max_y - 2:
            info2 = "  reads/writes colors and turns based on a state-transition table"
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



def _draw_turmite(self, max_y: int, max_x: int):
    """Draw the Turmites simulation."""
    # Title bar
    n_ants = len(self.turmite_ants)
    title = f" Turmites [{self.turmite_preset_name}]  States: {self.turmite_num_states}  Colors: {self.turmite_num_colors}  Step: {self.turmite_step_count}  Steps/f: {self.turmite_steps_per_frame}"
    state_str = " PLAY" if self.turmite_running else " PAUSE"
    title += f"  {state_str}"
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

    num_colors = self.turmite_num_colors
    state_colors = []
    for s in range(num_colors):
        state_colors.append(curses.color_pair(self.TURMITE_COLORS[s % len(self.TURMITE_COLORS)]))

    # Build set of ant positions for overlay
    ant_positions = {}
    for i, ant in enumerate(self.turmite_ants):
        ant_positions[(ant["r"], ant["c"])] = i

    for y in range(draw_rows):
        row_idx = y
        if row_idx >= self.turmite_rows:
            break
        screen_y = draw_start + y
        if screen_y >= max_y - 2:
            break
        for x in range(draw_cols):
            col_idx = x
            if col_idx >= self.turmite_cols:
                break
            sx = x * 2
            if sx + 1 >= max_x:
                break
            cell_color = self.turmite_grid.get((row_idx, col_idx), 0)
            if (row_idx, col_idx) in ant_positions:
                ant_idx = ant_positions[(row_idx, col_idx)]
                ant_obj = self.turmite_ants[ant_idx]
                ant_color_idx = (ant_obj["state"] + 1) % len(self.TURMITE_COLORS)
                arrows = ["\u25b2 ", "\u25b6 ", "\u25bc ", "\u25c0 "]
                ch = arrows[ant_obj["dir"]]
                try:
                    self.stdscr.addstr(screen_y, sx, ch,
                                       curses.color_pair(self.TURMITE_COLORS[ant_color_idx]) | curses.A_BOLD)
                except curses.error:
                    pass
            elif cell_color > 0:
                color = state_colors[cell_color % num_colors]
                try:
                    self.stdscr.addstr(screen_y, sx, "\u2588\u2588", color)
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        colored_cells = len(self.turmite_grid)
        ant_state = self.turmite_ants[0]["state"] if self.turmite_ants else 0
        status = f" Preset: {self.turmite_preset_name}  |  Step: {self.turmite_step_count}  |  Colored: {colored_cells}  |  Ant state: {ant_state}  |  Speed: {SPEED_LABELS[self.speed_idx]}"
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

# ══════════════════════════════════════════════════════════════════════
#  Traffic Flow (Nagel-Schreckenberg model) — Mode T
# ══════════════════════════════════════════════════════════════════════

TRAFFIC_PRESETS = [
    # (name, description, vmax, p_slow, density, lanes)
    ("Light Traffic", "Low density — free flow, cars cruise at vmax", 5, 0.3, 0.10, 4),
    ("Moderate Traffic", "Medium density — occasional slowdowns appear", 5, 0.3, 0.25, 4),
    ("Heavy Traffic", "High density — phantom jams emerge spontaneously", 5, 0.3, 0.40, 4),
    ("Congested", "Very high density — stop-and-go waves dominate", 5, 0.3, 0.55, 4),
    ("Slow Road", "Low speed limit (vmax=2) — tighter packing", 2, 0.3, 0.35, 4),
    ("Cautious Drivers", "High random braking — frequent disruptions", 5, 0.5, 0.25, 4),
    ("Aggressive Drivers", "Low random braking — smooth until it isn't", 5, 0.1, 0.30, 4),
    ("Highway (8 lanes)", "Wide highway with moderate traffic", 5, 0.3, 0.25, 8),
]




def register(App):
    """Register turmite mode methods on the App class."""
    App._turmite_step = _turmite_step
    App._turmite_init = _turmite_init
    App._enter_turmite_mode = _enter_turmite_mode
    App._exit_turmite_mode = _exit_turmite_mode
    App._handle_turmite_menu_key = _handle_turmite_menu_key
    App._handle_turmite_key = _handle_turmite_key
    App._draw_turmite_menu = _draw_turmite_menu
    App._draw_turmite = _draw_turmite

