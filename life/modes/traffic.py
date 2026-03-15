"""Mode: traffic — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_traffic_mode(self):
    """Enter Traffic Flow mode — show preset menu."""
    self.traffic_menu = True
    self.traffic_menu_sel = 0
    self._flash("Traffic Flow (Nagel-Schreckenberg) — select a scenario")



def _exit_traffic_mode(self):
    """Exit Traffic Flow mode."""
    self.traffic_mode = False
    self.traffic_menu = False
    self.traffic_running = False
    self.traffic_grid = []
    self._flash("Traffic Flow mode OFF")



def _traffic_init(self, preset_idx: int):
    """Initialize Traffic Flow with the given preset."""
    name, _desc, vmax, p_slow, density, lanes = self.TRAFFIC_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = min(lanes, max(2, max_y - 5))
    cols = max(20, max_x - 2)
    self.traffic_rows = rows
    self.traffic_cols = cols
    self.traffic_vmax = vmax
    self.traffic_p_slow = p_slow
    self.traffic_density = density
    self.traffic_preset_name = name
    self.traffic_generation = 0
    self.traffic_steps_per_frame = 1

    # Initialize grid: -1 = empty, 0..vmax = car with that speed
    self.traffic_grid = [[-1] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if random.random() < density:
                self.traffic_grid[r][c] = random.randint(0, vmax)

    self._traffic_compute_stats()
    self.traffic_mode = True
    self.traffic_menu = False
    self.traffic_running = False
    self._flash(f"Traffic: {name} — Space to start")



def _traffic_compute_stats(self):
    """Compute average speed and flow."""
    total_speed = 0
    car_count = 0
    for r in range(self.traffic_rows):
        for c in range(self.traffic_cols):
            v = self.traffic_grid[r][c]
            if v >= 0:
                total_speed += v
                car_count += 1
    if car_count > 0:
        self.traffic_avg_speed = total_speed / car_count
        self.traffic_flow = total_speed / (self.traffic_rows * self.traffic_cols)
    else:
        self.traffic_avg_speed = 0.0
        self.traffic_flow = 0.0



def _traffic_step(self):
    """Advance the Nagel-Schreckenberg model by one time step.

    Rules applied simultaneously to all cars:
    1. Acceleration: v = min(v + 1, vmax)
    2. Braking: v = min(v, gap) where gap = distance to next car - 1
    3. Randomization: with probability p_slow, v = max(v - 1, 0)
    4. Movement: car advances v cells forward
    """
    grid = self.traffic_grid
    rows, cols = self.traffic_rows, self.traffic_cols
    vmax = self.traffic_vmax
    p_slow = self.traffic_p_slow
    rand = random.random

    new_grid = [[-1] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            v = grid[r][c]
            if v < 0:
                continue  # empty cell

            # 1. Acceleration
            v = min(v + 1, vmax)

            # 2. Braking: find gap to next car ahead (same lane)
            gap = 0
            for d in range(1, cols):
                nc = (c + d) % cols
                if grid[r][nc] >= 0:
                    gap = d - 1
                    break
            else:
                gap = cols - 1  # no car ahead (wrap-around)
            v = min(v, gap)

            # 3. Randomization
            if v > 0 and rand() < p_slow:
                v -= 1

            # 4. Movement
            new_c = (c + v) % cols
            new_grid[r][new_c] = v

    self.traffic_grid = new_grid
    self.traffic_generation += 1
    self._traffic_compute_stats()



def _handle_traffic_menu_key(self, key: int) -> bool:
    """Handle input in Traffic Flow preset menu."""
    presets = self.TRAFFIC_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.traffic_menu_sel = (self.traffic_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.traffic_menu_sel = (self.traffic_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._traffic_init(self.traffic_menu_sel)
    elif key == ord("q") or key == 27:
        self.traffic_menu = False
        self._flash("Traffic Flow cancelled")
    return True



def _handle_traffic_key(self, key: int) -> bool:
    """Handle input in active Traffic Flow simulation."""
    if key == ord("q") or key == 27:
        self._exit_traffic_mode()
        return True
    if key == ord(" "):
        self.traffic_running = not self.traffic_running
        return True
    if key == ord("n") or key == ord("."):
        self._traffic_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.TRAFFIC_PRESETS) if p[0] == self.traffic_preset_name),
            0,
        )
        self._traffic_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.traffic_mode = False
        self.traffic_running = False
        self.traffic_menu = True
        self.traffic_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.traffic_steps_per_frame) if self.traffic_steps_per_frame in choices else 0
        self.traffic_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.traffic_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.traffic_steps_per_frame) if self.traffic_steps_per_frame in choices else 0
        self.traffic_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.traffic_steps_per_frame} steps/frame")
        return True
    # Density controls: d/D
    if key == ord("d"):
        self.traffic_density = max(0.01, self.traffic_density - 0.05)
        self._flash(f"Density: {self.traffic_density:.2f}")
        return True
    if key == ord("D"):
        self.traffic_density = min(0.95, self.traffic_density + 0.05)
        self._flash(f"Density: {self.traffic_density:.2f}")
        return True
    # Slowdown probability: p/P
    if key == ord("p"):
        self.traffic_p_slow = max(0.0, self.traffic_p_slow - 0.05)
        self._flash(f"P(slow): {self.traffic_p_slow:.2f}")
        return True
    if key == ord("P"):
        self.traffic_p_slow = min(1.0, self.traffic_p_slow + 0.05)
        self._flash(f"P(slow): {self.traffic_p_slow:.2f}")
        return True
    return True



def _draw_traffic_menu(self, max_y: int, max_x: int):
    """Draw the Traffic Flow preset selection menu."""
    self.stdscr.erase()
    title = "── Traffic Flow (Nagel-Schreckenberg) ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, vmax, p_slow, density, lanes) in enumerate(self.TRAFFIC_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.traffic_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.traffic_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:22s} v={vmax} p={p_slow:.1f} ρ={density:.2f} {lanes}L  {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], attr)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_traffic(self, max_y: int, max_x: int):
    """Draw the active Traffic Flow simulation."""
    self.stdscr.erase()
    grid = self.traffic_grid
    rows, cols = self.traffic_rows, self.traffic_cols
    state = "▶ RUNNING" if self.traffic_running else "⏸ PAUSED"

    # Car glyphs by speed: stopped -> fast
    car_chars = ["█", "▓", "▒", "░", "◈", "►"]
    # Color: stopped=red(1), slow=yellow(3), medium=cyan(6), fast=green(2)
    speed_colors = [1, 1, 3, 3, 6, 2]

    # Title bar
    title = (f" Traffic: {self.traffic_preset_name}  |  step {self.traffic_generation}"
             f"  |  vmax={self.traffic_vmax}  p={self.traffic_p_slow:.2f}"
             f"  ρ={self.traffic_density:.2f}"
             f"  |  avg v={self.traffic_avg_speed:.2f}"
             f"  flow={self.traffic_flow:.3f}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw lanes
    view_cols = min(cols, max_x - 2)
    for r in range(rows):
        sy = 2 + r * 2  # double-space lanes for readability
        if sy >= max_y - 3:
            break
        # Draw lane separator
        if r == 0 and sy - 1 >= 1:
            try:
                self.stdscr.addstr(sy - 1, 0, "─" * view_cols, curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass
        # Draw cars on this lane
        for c in range(view_cols):
            v = grid[r][c]
            if v >= 0:
                ci = min(v, len(car_chars) - 1)
                ch = car_chars[ci]
                color = speed_colors[min(v, len(speed_colors) - 1)]
                try:
                    self.stdscr.addstr(sy, c, ch, curses.color_pair(color) | curses.A_BOLD)
                except curses.error:
                    pass
            else:
                try:
                    self.stdscr.addstr(sy, c, "·", curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass
        # Lane separator below
        sep_y = sy + 1
        if sep_y < max_y - 3:
            try:
                self.stdscr.addstr(sep_y, 0, "─" * view_cols, curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        car_count = sum(1 for r in range(rows) for c in range(cols) if grid[r][c] >= 0)
        total = rows * cols
        info = (f" Step {self.traffic_generation}  |  {car_count} cars / {total} cells"
                f"  |  avg speed={self.traffic_avg_speed:.2f}/{self.traffic_vmax}"
                f"  flow={self.traffic_flow:.3f}"
                f"  |  steps/f={self.traffic_steps_per_frame}")
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [d/D]=density-/+ [p/P]=brake-/+ [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Fluid Dynamics (Lattice Boltzmann Method) — Mode F
# ══════════════════════════════════════════════════════════════════════

# D2Q9 lattice velocities: (ex, ey) for each of 9 directions
#   6 2 5
#   3 0 1
#   7 4 8
FLUID_EX = [0, 1, 0, -1,  0, 1, -1, -1,  1]
FLUID_EY = [0, 0, 1,  0, -1, 1,  1, -1, -1]
FLUID_W  = [4.0/9, 1.0/9, 1.0/9, 1.0/9, 1.0/9,
            1.0/36, 1.0/36, 1.0/36, 1.0/36]
FLUID_OPP = [0, 3, 4, 1, 2, 7, 8, 5, 6]  # opposite direction index

FLUID_SPEED_CHARS = [" ", "░", "▒", "▓", "█"]
FLUID_VORT_POS = ["·", "∘", "○", "◎", "◉"]   # counterclockwise
FLUID_VORT_NEG = ["·", "∙", "•", "●", "⬤"]    # clockwise

FLUID_PRESETS = [
    # (name, description, omega, inflow_speed, obstacle_type)
    ("Wind Tunnel", "Uniform flow past a cylindrical obstacle", 1.4, 0.10, "cylinder"),
    ("Von Kármán Street", "Vortex shedding behind a cylinder (low viscosity)", 1.85, 0.12, "cylinder_small"),
    ("Lid-Driven Cavity", "Enclosed box with moving top wall", 1.5, 0.10, "cavity"),
    ("Channel Flow", "Poiseuille flow between parallel walls", 1.6, 0.08, "channel"),
    ("Obstacle Course", "Flow weaving through multiple obstacles", 1.5, 0.10, "obstacles"),
    ("Turbulence", "High-speed chaotic flow with perturbations", 1.9, 0.15, "turbulence"),
]




def register(App):
    """Register traffic mode methods on the App class."""
    App._enter_traffic_mode = _enter_traffic_mode
    App._exit_traffic_mode = _exit_traffic_mode
    App._traffic_init = _traffic_init
    App._traffic_compute_stats = _traffic_compute_stats
    App._traffic_step = _traffic_step
    App._handle_traffic_menu_key = _handle_traffic_menu_key
    App._handle_traffic_key = _handle_traffic_key
    App._draw_traffic_menu = _draw_traffic_menu
    App._draw_traffic = _draw_traffic

