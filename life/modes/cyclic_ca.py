"""Mode: cyclic — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_cyclic_mode(self):
    """Enter Cyclic CA mode — show preset menu."""
    self.cyclic_menu = True
    self.cyclic_menu_sel = 0
    self._flash("Cyclic Cellular Automaton — select a scenario")



def _exit_cyclic_mode(self):
    """Exit Cyclic CA mode."""
    self.cyclic_mode = False
    self.cyclic_menu = False
    self.cyclic_running = False
    self.cyclic_grid = []
    self._flash("Cyclic CA mode OFF")



def _cyclic_init(self, preset_idx: int):
    """Initialize Cyclic CA with the given preset."""
    (name, _desc, n_states, threshold, neighborhood) = self.CYCLIC_PRESETS[preset_idx]
    self.cyclic_preset_name = name
    self.cyclic_generation = 0
    self.cyclic_running = False
    self.cyclic_n_states = n_states
    self.cyclic_threshold = threshold
    self.cyclic_neighborhood = neighborhood

    max_y, max_x = self.stdscr.getmaxyx()
    self.cyclic_rows = max(10, max_y - 4)
    self.cyclic_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.cyclic_rows, self.cyclic_cols

    # Random initial state
    self.cyclic_grid = [
        [random.randint(0, n_states - 1) for _ in range(cols)]
        for _ in range(rows)
    ]

    self.cyclic_menu = False
    self.cyclic_mode = True
    self._flash(f"Cyclic CA: {name} — Space to start")



def _cyclic_step(self):
    """Advance the Cyclic CA by one generation.

    A cell in state s advances to (s+1) % n_states if at least
    `threshold` of its neighbors are already in state (s+1) % n_states.
    """
    rows, cols = self.cyclic_rows, self.cyclic_cols
    grid = self.cyclic_grid
    n_states = self.cyclic_n_states
    threshold = self.cyclic_threshold
    moore = self.cyclic_neighborhood == "moore"

    new_grid = [row[:] for row in grid]

    for r in range(rows):
        for c in range(cols):
            current = grid[r][c]
            successor = (current + 1) % n_states
            count = 0
            if moore:
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = (r + dr) % rows
                        nc = (c + dc) % cols
                        if grid[nr][nc] == successor:
                            count += 1
            else:
                # Von Neumann (4 neighbors)
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    if grid[nr][nc] == successor:
                        count += 1
            if count >= threshold:
                new_grid[r][c] = successor

    self.cyclic_grid = new_grid
    self.cyclic_generation += 1



def _handle_cyclic_menu_key(self, key: int) -> bool:
    """Handle input in Cyclic CA preset menu."""
    n = len(self.CYCLIC_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.cyclic_menu_sel = (self.cyclic_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.cyclic_menu_sel = (self.cyclic_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._cyclic_init(self.cyclic_menu_sel)
    elif key in (ord("q"), 27):
        self.cyclic_menu = False
        self._flash("Cyclic CA cancelled")
    return True



def _handle_cyclic_key(self, key: int) -> bool:
    """Handle input in active Cyclic CA simulation."""
    if key == ord(" "):
        self.cyclic_running = not self.cyclic_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.cyclic_steps_per_frame):
            self._cyclic_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.CYCLIC_PRESETS)
                    if p[0] == self.cyclic_preset_name), 0)
        self._cyclic_init(idx)
    elif key in (ord("R"), ord("m")):
        self.cyclic_mode = False
        self.cyclic_menu = True
    elif key == ord("t"):
        self.cyclic_threshold = min(8, self.cyclic_threshold + 1)
        self._flash(f"Threshold: {self.cyclic_threshold}")
    elif key == ord("T"):
        self.cyclic_threshold = max(1, self.cyclic_threshold - 1)
        self._flash(f"Threshold: {self.cyclic_threshold}")
    elif key == ord("s"):
        self.cyclic_n_states = min(16, self.cyclic_n_states + 1)
        self._flash(f"States: {self.cyclic_n_states}")
    elif key == ord("S"):
        self.cyclic_n_states = max(2, self.cyclic_n_states - 1)
        ns = self.cyclic_n_states
        for r in range(self.cyclic_rows):
            for c in range(self.cyclic_cols):
                if self.cyclic_grid[r][c] >= ns:
                    self.cyclic_grid[r][c] = self.cyclic_grid[r][c] % ns
        self._flash(f"States: {self.cyclic_n_states}")
    elif key == ord("+") or key == ord("="):
        self.cyclic_steps_per_frame = min(20, self.cyclic_steps_per_frame + 1)
    elif key == ord("-"):
        self.cyclic_steps_per_frame = max(1, self.cyclic_steps_per_frame - 1)
    elif key in (ord("q"), 27):
        self._exit_cyclic_mode()
    else:
        return True
    return True



def _draw_cyclic_menu(self, max_y: int, max_x: int):
    """Draw the Cyclic CA preset selection menu."""
    self.stdscr.erase()
    title = "── Cyclic Cellular Automaton ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.CYCLIC_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        selected = "▶" if i == self.cyclic_menu_sel else " "
        line = f" {selected} {name:20} {desc}"
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.cyclic_menu_sel else curses.color_pair(6)
        try:
            self.stdscr.addstr(y, 0, line[:max_x - 1], attr)
        except curses.error:
            pass

    foot_y = min(3 + len(self.CYCLIC_PRESETS) + 1, max_y - 1)
    if foot_y < max_y:
        try:
            self.stdscr.addstr(foot_y, 2, "[j/k]=navigate  [Enter]=select  [q]=cancel",
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_cyclic(self, max_y: int, max_x: int):
    """Draw the active Cyclic CA simulation."""
    self.stdscr.erase()
    grid = self.cyclic_grid
    rows, cols = self.cyclic_rows, self.cyclic_cols
    n_states = self.cyclic_n_states
    state = "▶ RUNNING" if self.cyclic_running else "⏸ PAUSED"

    # Title bar
    title = (f" Cyclic CA: {self.cyclic_preset_name}  |  gen {self.cyclic_generation}"
             f"  |  states={n_states}  thresh={self.cyclic_threshold}"
             f"  |  {self.cyclic_neighborhood}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2
    n_colors = len(self.CYCLIC_COLORS)

    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            sx = c * 2
            sy = 1 + r
            ci = val % n_colors
            pair, ch = self.CYCLIC_COLORS[ci]
            try:
                self.stdscr.addstr(sy, sx, ch, curses.color_pair(pair))
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Gen {self.cyclic_generation}  |  states={n_states}"
                f"  |  threshold={self.cyclic_threshold}"
                f"  |  neighborhood={self.cyclic_neighborhood}"
                f"  |  steps/f={self.cyclic_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [t/T]=thresh+/- [s/S]=states+/- [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Hodgepodge Machine (Belousov-Zhabotinsky reaction) — Mode ~
# ══════════════════════════════════════════════════════════════════════

HODGE_PRESETS = [
    # (name, description, n_states, k1, k2, g)
    ("Classic Spirals", "Smooth spirals — the iconic BZ pattern", 100, 2, 3, 28),
    ("Tight Spirals", "Dense tightly-wound spiral waves", 200, 1, 2, 45),
    ("Target Waves", "Concentric expanding rings", 100, 3, 3, 18),
    ("Chaotic Mix", "Turbulent interacting wavefronts", 50, 2, 3, 10),
    ("Slow Waves", "Large slow-moving spirals", 150, 1, 1, 55),
    ("Fast Reaction", "Rapid small-scale spiral activity", 60, 3, 4, 8),
    ("Crystal Growth", "Angular geometric wave patterns", 80, 1, 4, 35),
    ("Thin Filaments", "Delicate thin spiral arms", 255, 2, 3, 80),
]

# Color gradient: map state fraction to (color_pair, character) for visual variety
HODGE_COLORS = [
    (1, "██"),  # Red       — low infection
    (3, "██"),  # Yellow
    (2, "██"),  # Green
    (6, "██"),  # Cyan
    (4, "██"),  # Blue
    (5, "██"),  # Magenta   — high infection
    (7, "██"),  # White     — near ill
    (1, "░░"),  # Red dim   — wrapping back
]




def register(App):
    """Register cyclic mode methods on the App class."""
    App._enter_cyclic_mode = _enter_cyclic_mode
    App._exit_cyclic_mode = _exit_cyclic_mode
    App._cyclic_init = _cyclic_init
    App._cyclic_step = _cyclic_step
    App._handle_cyclic_menu_key = _handle_cyclic_menu_key
    App._handle_cyclic_key = _handle_cyclic_key
    App._draw_cyclic_menu = _draw_cyclic_menu
    App._draw_cyclic = _draw_cyclic

