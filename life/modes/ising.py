"""Mode: ising — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_ising_mode(self):
    """Enter Ising Model mode — show preset menu."""
    self.ising_menu = True
    self.ising_menu_sel = 0
    self._flash("Ising Model (magnetic spins) — select a scenario")



def _exit_ising_mode(self):
    """Exit Ising Model mode."""
    self.ising_mode = False
    self.ising_menu = False
    self.ising_running = False
    self.ising_grid = []
    self._flash("Ising Model mode OFF")



def _ising_init(self, preset_idx: int):
    """Initialize Ising Model with the given preset."""
    name, _desc, temp, field, init_style = self.ISING_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(10, (max_x - 1) // 2)
    self.ising_rows = rows
    self.ising_cols = cols
    self.ising_temperature = temp
    self.ising_ext_field = field
    self.ising_preset_name = name
    self.ising_generation = 0
    self.ising_steps_per_frame = 1

    # Initialize spin grid
    if init_style == "all_up":
        self.ising_grid = [[1] * cols for _ in range(rows)]
    elif init_style == "all_down":
        self.ising_grid = [[-1] * cols for _ in range(rows)]
    elif init_style == "half":
        self.ising_grid = [
            [1 if c < cols // 2 else -1 for c in range(cols)]
            for _ in range(rows)
        ]
    else:  # random
        self.ising_grid = [
            [random.choice((-1, 1)) for _ in range(cols)]
            for _ in range(rows)
        ]

    self._ising_compute_stats()
    self.ising_mode = True
    self.ising_menu = False
    self.ising_running = False
    self._flash(f"Ising: {name} — Space to start")



def _ising_compute_stats(self):
    """Compute magnetization and energy per spin."""
    grid = self.ising_grid
    rows, cols = self.ising_rows, self.ising_cols
    total_spin = 0
    total_energy = 0.0
    h = self.ising_ext_field
    for r in range(rows):
        for c in range(cols):
            s = grid[r][c]
            total_spin += s
            # Count only right and down neighbors to avoid double-counting
            sr = grid[r][(c + 1) % cols]
            sd = grid[(r + 1) % rows][c]
            total_energy += -s * (sr + sd)
            total_energy += -h * s
    n = rows * cols
    self.ising_magnetization = total_spin / n
    self.ising_energy = total_energy / n



def _ising_step(self):
    """Advance the Ising Model by one sweep (Metropolis algorithm).

    One sweep = N random single-spin-flip attempts where N = rows * cols.
    """
    grid = self.ising_grid
    rows, cols = self.ising_rows, self.ising_cols
    temp = self.ising_temperature
    h = self.ising_ext_field
    n = rows * cols
    rand = random.random
    randint_r = random.randint
    # Pre-compute Boltzmann factors for possible dE values
    # dE = 2*s*(sum_neighbors) + 2*h*s
    # sum_neighbors in {-4,-3,-2,-1,0,1,2,3,4} for 4 neighbors
    # So dE in {-8-2h, ..., 8+2h} but we only need positive dE cases
    if temp > 0:
        inv_temp = 1.0 / temp
    else:
        inv_temp = 1e10  # effectively zero temperature

    for _ in range(n):
        r = randint_r(0, rows - 1)
        c = randint_r(0, cols - 1)
        s = grid[r][c]
        # Sum of 4 nearest neighbors (periodic boundary)
        neighbors_sum = (grid[(r - 1) % rows][c] +
                         grid[(r + 1) % rows][c] +
                         grid[r][(c - 1) % cols] +
                         grid[r][(c + 1) % cols])
        # Energy change for flipping spin s -> -s
        dE = 2 * s * (neighbors_sum + h)
        if dE <= 0 or rand() < math.exp(-dE * inv_temp):
            grid[r][c] = -s

    self.ising_generation += 1
    self._ising_compute_stats()



def _handle_ising_menu_key(self, key: int) -> bool:
    """Handle input in Ising Model preset menu."""
    presets = self.ISING_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.ising_menu_sel = (self.ising_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.ising_menu_sel = (self.ising_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._ising_init(self.ising_menu_sel)
    elif key == ord("q") or key == 27:
        self.ising_menu = False
        self._flash("Ising Model cancelled")
    return True



def _handle_ising_key(self, key: int) -> bool:
    """Handle input in active Ising Model simulation."""
    if key == ord("q") or key == 27:
        self._exit_ising_mode()
        return True
    if key == ord(" "):
        self.ising_running = not self.ising_running
        return True
    if key == ord("n") or key == ord("."):
        self._ising_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.ISING_PRESETS) if p[0] == self.ising_preset_name),
            0,
        )
        self._ising_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.ising_mode = False
        self.ising_running = False
        self.ising_menu = True
        self.ising_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.ising_steps_per_frame) if self.ising_steps_per_frame in choices else 0
        self.ising_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.ising_steps_per_frame} sweeps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.ising_steps_per_frame) if self.ising_steps_per_frame in choices else 0
        self.ising_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.ising_steps_per_frame} sweeps/frame")
        return True
    # Temperature controls: t/T to decrease/increase
    if key == ord("t"):
        self.ising_temperature = max(0.01, self.ising_temperature - 0.1)
        self._flash(f"Temperature: {self.ising_temperature:.2f}")
        return True
    if key == ord("T"):
        self.ising_temperature = min(10.0, self.ising_temperature + 0.1)
        self._flash(f"Temperature: {self.ising_temperature:.2f}")
        return True
    # External field controls: f/F
    if key == ord("f"):
        self.ising_ext_field = max(-2.0, self.ising_ext_field - 0.1)
        self._flash(f"External field: {self.ising_ext_field:.2f}")
        return True
    if key == ord("F"):
        self.ising_ext_field = min(2.0, self.ising_ext_field + 0.1)
        self._flash(f"External field: {self.ising_ext_field:.2f}")
        return True
    return True



def _draw_ising_menu(self, max_y: int, max_x: int):
    """Draw the Ising Model preset selection menu."""
    self.stdscr.erase()
    title = "── Ising Model (Magnetic Spins) ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, temp, field, _init) in enumerate(self.ISING_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.ising_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.ising_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:22s} T={temp:<5.2f}  h={field:<4.1f}  {desc}"
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



def _draw_ising(self, max_y: int, max_x: int):
    """Draw the active Ising Model simulation."""
    self.stdscr.erase()
    grid = self.ising_grid
    rows, cols = self.ising_rows, self.ising_cols
    state = "▶ RUNNING" if self.ising_running else "⏸ PAUSED"

    # Title bar
    title = (f" Ising: {self.ising_preset_name}  |  sweep {self.ising_generation}"
             f"  |  T={self.ising_temperature:.2f}  h={self.ising_ext_field:.2f}"
             f"  |  ⟨m⟩={self.ising_magnetization:+.3f}"
             f"  E/N={self.ising_energy:+.3f}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            s = grid[r][c]
            sx = c * 2
            sy = 1 + r
            if s == 1:
                # Spin up: bright cyan
                try:
                    self.stdscr.addstr(sy, sx, "██", curses.color_pair(6) | curses.A_BOLD)
                except curses.error:
                    pass
            else:
                # Spin down: dark blue
                try:
                    self.stdscr.addstr(sy, sx, "░░", curses.color_pair(4))
                except curses.error:
                    pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Sweep {self.ising_generation}  |  T={self.ising_temperature:.2f}"
                f"  h={self.ising_ext_field:.2f}"
                f"  |  ⟨m⟩={self.ising_magnetization:+.3f}"
                f"  E/N={self.ising_energy:+.3f}"
                f"  |  sweeps/f={self.ising_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [t/T]=temp-/+ [f/F]=field-/+ [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Snowflake Growth (Reiter Crystal) — Mode *
# ══════════════════════════════════════════════════════════════════════

SNOWFLAKE_PRESETS = [
    # (name, description, alpha, beta, gamma, mu, symmetric)
    # alpha = deposition rate, beta = initial vapor (supersaturation),
    # gamma = noise amplitude, mu = diffusion rate (0-1), symmetric = enforce 6-fold
    ("Classic Dendrite", "Balanced growth — six-fold branching arms", 0.40, 0.40, 0.0001, 0.8, True),
    ("Thin Needles", "Low vapor — long thin branches", 0.30, 0.30, 0.0001, 0.9, True),
    ("Broad Plates", "High vapor — wide faceted plates", 0.50, 0.55, 0.0001, 0.5, True),
    ("Fernlike", "Fast deposition — highly branched fern shapes", 0.65, 0.35, 0.0001, 0.7, True),
    ("Stellar Dendrite", "Moderate vapor — classic star snowflake", 0.45, 0.45, 0.0001, 0.85, True),
    ("Sectored Plate", "High vapor, low deposition — sector plates", 0.20, 0.60, 0.0001, 0.6, True),
    ("Simple Hexagon", "Very high vapor — compact hexagonal prism", 0.15, 0.70, 0.0, 0.4, True),
    ("Hollow Columns", "Medium vapor — hollow column morphology", 0.35, 0.50, 0.0, 0.75, True),
    ("Noisy Crystal", "High noise — irregular natural look", 0.40, 0.40, 0.005, 0.8, False),
    ("Asymmetric Growth", "No symmetry — naturalistic random crystal", 0.40, 0.40, 0.001, 0.8, False),
    ("Fast Dendrite", "Rapid low-diffusion — dense fractal arms", 0.55, 0.35, 0.0001, 0.5, True),
    ("Sparse Frost", "Very low vapor — slow sparse crystal", 0.25, 0.25, 0.0001, 0.9, True),
]




def register(App):
    """Register ising mode methods on the App class."""
    from life.modes.hodgepodge import ISING_PRESETS
    App.ISING_PRESETS = ISING_PRESETS
    App._enter_ising_mode = _enter_ising_mode
    App._exit_ising_mode = _exit_ising_mode
    App._ising_init = _ising_init
    App._ising_compute_stats = _ising_compute_stats
    App._ising_step = _ising_step
    App._handle_ising_menu_key = _handle_ising_menu_key
    App._handle_ising_key = _handle_ising_key
    App._draw_ising_menu = _draw_ising_menu
    App._draw_ising = _draw_ising

