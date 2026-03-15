"""Mode: hodge — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_hodge_mode(self):
    """Enter Hodgepodge Machine mode — show preset menu."""
    self.hodge_menu = True
    self.hodge_menu_sel = 0
    self._flash("Hodgepodge Machine (BZ reaction) — select a scenario")



def _exit_hodge_mode(self):
    """Exit Hodgepodge Machine mode."""
    self.hodge_mode = False
    self.hodge_menu = False
    self.hodge_running = False
    self.hodge_grid = []
    self._flash("Hodgepodge Machine mode OFF")



def _hodge_init(self, preset_idx: int):
    """Initialize Hodgepodge Machine with the given preset."""
    (name, _desc, n_states, k1, k2, g) = self.HODGE_PRESETS[preset_idx]
    self.hodge_preset_name = name
    self.hodge_generation = 0
    self.hodge_running = False
    self.hodge_n_states = n_states
    self.hodge_k1 = k1
    self.hodge_k2 = k2
    self.hodge_g = g

    max_y, max_x = self.stdscr.getmaxyx()
    self.hodge_rows = max(10, max_y - 4)
    self.hodge_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.hodge_rows, self.hodge_cols

    # Random initial state
    self.hodge_grid = [
        [random.randint(0, n_states - 1) for _ in range(cols)]
        for _ in range(rows)
    ]

    self.hodge_menu = False
    self.hodge_mode = True
    self._flash(f"Hodgepodge: {name} — Space to start")



def _hodge_step(self):
    """Advance the Hodgepodge Machine by one generation.

    Rules (Gerhardt-Schuster model):
    - Healthy cell (state 0): counts infected neighbors (a) and ill
      neighbors (b) among Moore neighborhood. New state = floor(a/k1 + b/k2).
      Clamped to [0, n-1].
    - Infected cell (state 1..n-2): new state = min(n-1,
      floor(sum_of_neighbor_states / count_of_non_zero_neighbors + g)).
      This is the average infected/ill neighbor state plus g.
    - Ill cell (state n-1): becomes healthy (state 0).
    """
    rows, cols = self.hodge_rows, self.hodge_cols
    grid = self.hodge_grid
    n = self.hodge_n_states
    k1 = self.hodge_k1
    k2 = self.hodge_k2
    g = self.hodge_g
    ill = n - 1

    new_grid = [row[:] for row in grid]

    for r in range(rows):
        for c in range(cols):
            current = grid[r][c]
            if current == ill:
                # Ill -> healthy
                new_grid[r][c] = 0
            elif current == 0:
                # Healthy: count infected and ill neighbors
                a = 0  # infected neighbors
                b = 0  # ill neighbors
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = (r + dr) % rows
                        nc = (c + dc) % cols
                        nv = grid[nr][nc]
                        if nv == ill:
                            b += 1
                        elif nv > 0:
                            a += 1
                new_val = a // k1 + b // k2
                new_grid[r][c] = min(new_val, ill)
            else:
                # Infected: average of infected/ill neighbor states + g
                s = current  # include self
                count = 1
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = (r + dr) % rows
                        nc = (c + dc) % cols
                        nv = grid[nr][nc]
                        if nv > 0:
                            s += nv
                            count += 1
                new_val = min(ill, s // count + g)
                new_grid[r][c] = new_val

    self.hodge_grid = new_grid
    self.hodge_generation += 1



def _handle_hodge_menu_key(self, key: int) -> bool:
    """Handle input in Hodgepodge Machine preset menu."""
    n = len(self.HODGE_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.hodge_menu_sel = (self.hodge_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.hodge_menu_sel = (self.hodge_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._hodge_init(self.hodge_menu_sel)
    elif key in (ord("q"), 27):
        self.hodge_menu = False
        self._flash("Hodgepodge Machine cancelled")
    return True



def _handle_hodge_key(self, key: int) -> bool:
    """Handle input in active Hodgepodge Machine simulation."""
    if key == ord(" "):
        self.hodge_running = not self.hodge_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.hodge_steps_per_frame):
            self._hodge_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.HODGE_PRESETS)
                    if p[0] == self.hodge_preset_name), 0)
        self._hodge_init(idx)
    elif key in (ord("R"), ord("m")):
        self.hodge_mode = False
        self.hodge_menu = True
    elif key == ord("g"):
        self.hodge_g = min(200, self.hodge_g + 1)
        self._flash(f"g (illness speed): {self.hodge_g}")
    elif key == ord("G"):
        self.hodge_g = max(1, self.hodge_g - 1)
        self._flash(f"g (illness speed): {self.hodge_g}")
    elif key == ord("s"):
        self.hodge_n_states = min(255, self.hodge_n_states + 10)
        self._flash(f"States: {self.hodge_n_states}")
    elif key == ord("S"):
        self.hodge_n_states = max(10, self.hodge_n_states - 10)
        ns = self.hodge_n_states
        for r in range(self.hodge_rows):
            for c in range(self.hodge_cols):
                if self.hodge_grid[r][c] >= ns:
                    self.hodge_grid[r][c] = self.hodge_grid[r][c] % ns
        self._flash(f"States: {self.hodge_n_states}")
    elif key == ord("+") or key == ord("="):
        self.hodge_steps_per_frame = min(20, self.hodge_steps_per_frame + 1)
    elif key == ord("-"):
        self.hodge_steps_per_frame = max(1, self.hodge_steps_per_frame - 1)
    elif key in (ord("q"), 27):
        self._exit_hodge_mode()
    else:
        return True
    return True



def _draw_hodge_menu(self, max_y: int, max_x: int):
    """Draw the Hodgepodge Machine preset selection menu."""
    self.stdscr.erase()
    title = "── Hodgepodge Machine (BZ Reaction) ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.HODGE_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        selected = "▶" if i == self.hodge_menu_sel else " "
        line = f" {selected} {name:20} {desc}"
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.hodge_menu_sel else curses.color_pair(6)
        try:
            self.stdscr.addstr(y, 0, line[:max_x - 1], attr)
        except curses.error:
            pass

    foot_y = min(3 + len(self.HODGE_PRESETS) + 1, max_y - 1)
    if foot_y < max_y:
        try:
            self.stdscr.addstr(foot_y, 2, "[j/k]=navigate  [Enter]=select  [q]=cancel",
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_hodge(self, max_y: int, max_x: int):
    """Draw the active Hodgepodge Machine simulation."""
    self.stdscr.erase()
    grid = self.hodge_grid
    rows, cols = self.hodge_rows, self.hodge_cols
    n_states = self.hodge_n_states
    state = "▶ RUNNING" if self.hodge_running else "⏸ PAUSED"

    # Title bar
    title = (f" Hodgepodge: {self.hodge_preset_name}  |  gen {self.hodge_generation}"
             f"  |  states={n_states}  k1={self.hodge_k1}  k2={self.hodge_k2}"
             f"  g={self.hodge_g}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2
    n_colors = len(self.HODGE_COLORS)

    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            sx = c * 2
            sy = 1 + r
            if val == 0:
                # Healthy: leave blank (black)
                continue
            # Map state to color index based on fraction through states
            ci = (val * n_colors) // n_states
            ci = min(ci, n_colors - 1)
            pair, ch = self.HODGE_COLORS[ci]
            try:
                self.stdscr.addstr(sy, sx, ch, curses.color_pair(pair))
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Gen {self.hodge_generation}  |  states={n_states}"
                f"  |  k1={self.hodge_k1}  k2={self.hodge_k2}  g={self.hodge_g}"
                f"  |  steps/f={self.hodge_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [g/G]=g+/- [s/S]=states+/- [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Ising Model (magnetic spin lattice) — Mode #
# ══════════════════════════════════════════════════════════════════════

ISING_PRESETS = [
    # (name, description, temperature, ext_field, init_style)
    # init_style: "random", "all_up", "all_down", "half"
    ("Critical Point", "T≈2.27 — phase transition with fractal domains", 2.269, 0.0, "random"),
    ("Low Temperature", "T=1.0 — ordered, large aligned domains", 1.0, 0.0, "random"),
    ("Very Cold", "T=0.5 — near ground state, almost uniform", 0.5, 0.0, "random"),
    ("High Temperature", "T=4.0 — disordered, random-looking spins", 4.0, 0.0, "random"),
    ("Quench to Cold", "Start random, T=0.1 — watch domains coarsen", 0.1, 0.0, "random"),
    ("External Field", "T=2.0 with field h=0.5 — biased alignment", 2.0, 0.5, "random"),
    ("Domain Wall", "T=1.5 — half up / half down, watch boundary evolve", 1.5, 0.0, "half"),
    ("All Up + Heat", "Start aligned, T=3.0 — watch order melt", 3.0, 0.0, "all_up"),
]




def register(App):
    """Register hodge mode methods on the App class."""
    App._enter_hodge_mode = _enter_hodge_mode
    App._exit_hodge_mode = _exit_hodge_mode
    App._hodge_init = _hodge_init
    App._hodge_step = _hodge_step
    App._handle_hodge_menu_key = _handle_hodge_menu_key
    App._handle_hodge_key = _handle_hodge_key
    App._draw_hodge_menu = _draw_hodge_menu
    App._draw_hodge = _draw_hodge

