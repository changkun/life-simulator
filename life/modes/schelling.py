"""Mode: schelling — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_schelling_mode(self):
    """Enter Schelling Segregation mode — show preset menu."""
    self.schelling_menu = True
    self.schelling_menu_sel = 0
    self._flash("Schelling Segregation Model — select a scenario")



def _exit_schelling_mode(self):
    """Exit Schelling Segregation mode."""
    self.schelling_mode = False
    self.schelling_menu = False
    self.schelling_running = False
    self.schelling_grid = []
    self.schelling_counts = []
    self._flash("Schelling Segregation mode OFF")



def _schelling_init(self, preset_idx: int):
    """Initialize Schelling simulation with the given preset."""
    (name, _desc, tolerance, density,
     n_groups) = self.SCHELLING_PRESETS[preset_idx]
    self.schelling_preset_name = name
    self.schelling_generation = 0
    self.schelling_running = False
    self.schelling_tolerance = tolerance
    self.schelling_density = density
    self.schelling_n_groups = n_groups
    self.schelling_counts = []

    max_y, max_x = self.stdscr.getmaxyx()
    self.schelling_rows = max(10, max_y - 4)
    self.schelling_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.schelling_rows, self.schelling_cols

    # Initialize grid: 0=empty, 1..n_groups = group
    self.schelling_grid = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if random.random() < density:
                self.schelling_grid[r][c] = random.randint(1, n_groups)

    self._schelling_record_counts()
    self.schelling_menu = False
    self.schelling_mode = True
    self._flash(f"Segregation: {name} — Space to start")



def _schelling_record_counts(self):
    """Count happy and unhappy agents."""
    happy = 0
    unhappy = 0
    grid = self.schelling_grid
    rows, cols = self.schelling_rows, self.schelling_cols
    tol = self.schelling_tolerance
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 0:
                continue
            my_group = grid[r][c]
            similar = 0
            total = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    if grid[nr][nc] != 0:
                        total += 1
                        if grid[nr][nc] == my_group:
                            similar += 1
            if total == 0:
                happy += 1
            elif similar / total >= tol:
                happy += 1
            else:
                unhappy += 1
    self.schelling_happy_count = happy
    self.schelling_unhappy_count = unhappy
    self.schelling_counts.append((happy, unhappy))



def _schelling_step(self):
    """Advance the Schelling simulation by one step."""
    grid = self.schelling_grid
    rows, cols = self.schelling_rows, self.schelling_cols
    tol = self.schelling_tolerance

    # Find all unhappy agents and all empty cells
    unhappy_agents: list[tuple[int, int]] = []
    empty_cells: list[tuple[int, int]] = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 0:
                empty_cells.append((r, c))
            else:
                my_group = grid[r][c]
                similar = 0
                total = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = (r + dr) % rows
                        nc = (c + dc) % cols
                        if grid[nr][nc] != 0:
                            total += 1
                            if grid[nr][nc] == my_group:
                                similar += 1
                if total > 0 and similar / total < tol:
                    unhappy_agents.append((r, c))

    if not unhappy_agents or not empty_cells:
        self.schelling_generation += 1
        self._schelling_record_counts()
        return

    # Shuffle and relocate unhappy agents to random empty cells
    random.shuffle(unhappy_agents)
    random.shuffle(empty_cells)

    n_moves = min(len(unhappy_agents), len(empty_cells))
    for i in range(n_moves):
        ar, ac = unhappy_agents[i]
        er, ec = empty_cells[i]
        grid[er][ec] = grid[ar][ac]
        grid[ar][ac] = 0

    self.schelling_generation += 1
    self._schelling_record_counts()



def _handle_schelling_menu_key(self, key: int) -> bool:
    """Handle input in Schelling preset menu."""
    n = len(self.SCHELLING_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.schelling_menu_sel = (self.schelling_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.schelling_menu_sel = (self.schelling_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._schelling_init(self.schelling_menu_sel)
    elif key in (ord("q"), 27):
        self.schelling_menu = False
        self._flash("Schelling Segregation cancelled")
    return True



def _handle_schelling_key(self, key: int) -> bool:
    """Handle input in active Schelling simulation."""
    if key == ord(" "):
        self.schelling_running = not self.schelling_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.schelling_steps_per_frame):
            self._schelling_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.SCHELLING_PRESETS)
                    if p[0] == self.schelling_preset_name), 0)
        self._schelling_init(idx)
        self.schelling_running = False
    elif key in (ord("R"), ord("m")):
        self.schelling_mode = False
        self.schelling_running = False
        self.schelling_menu = True
        self.schelling_menu_sel = 0
    elif key == ord("t") or key == ord("T"):
        delta = 0.025 if key == ord("t") else -0.025
        self.schelling_tolerance = max(0.05, min(0.95, self.schelling_tolerance + delta))
        self._flash(f"Tolerance: {self.schelling_tolerance:.1%}")
    elif key == ord("+") or key == ord("="):
        self.schelling_steps_per_frame = min(20, self.schelling_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.schelling_steps_per_frame}")
    elif key == ord("-"):
        self.schelling_steps_per_frame = max(1, self.schelling_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.schelling_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_schelling_mode()
    else:
        return True
    return True



def _draw_schelling_menu(self, max_y: int, max_x: int):
    """Draw the Schelling preset selection menu."""
    self.stdscr.erase()
    title = "── Schelling Segregation Model ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.SCHELLING_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<22s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.schelling_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_schelling(self, max_y: int, max_x: int):
    """Draw the active Schelling Segregation simulation."""
    self.stdscr.erase()
    grid = self.schelling_grid
    rows, cols = self.schelling_rows, self.schelling_cols
    state = "▶ RUNNING" if self.schelling_running else "⏸ PAUSED"
    gen = self.schelling_generation
    happy = self.schelling_happy_count
    unhappy = self.schelling_unhappy_count
    total_agents = happy + unhappy

    # Title bar
    pct = f"{100 * happy / total_agents:.0f}%" if total_agents > 0 else "N/A"
    title = (f" Segregation: {self.schelling_preset_name}  |  step {gen}"
             f"  |  happy:{happy} unhappy:{unhappy} ({pct} satisfied)"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    # Color pairs for groups: 1=red, 2=green, 3=yellow, 4=cyan, 5=magenta
    group_colors = [1, 2, 3, 4, 5]

    # Draw grid
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            sx = c * 2
            sy = 1 + r
            if val == 0:
                # Empty cell
                attr = curses.color_pair(6) | curses.A_DIM
                ch = "  "
            else:
                # Agent of group val (1-indexed)
                cp = group_colors[(val - 1) % len(group_colors)]
                attr = curses.color_pair(cp) | curses.A_BOLD
                ch = "██"
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Satisfaction bar
    status_y = max_y - 3
    if status_y > 1 and total_agents > 0:
        bar_w = min(40, max_x - 30)
        happy_w = int(bar_w * happy / total_agents)
        unhappy_w = bar_w - happy_w
        bx = 2
        try:
            self.stdscr.addstr(status_y, bx, "█" * happy_w, curses.color_pair(2))
            bx += happy_w
            if unhappy_w > 0:
                self.stdscr.addstr(status_y, bx, "█" * unhappy_w, curses.color_pair(1) | curses.A_BOLD)
            bx += unhappy_w
            legend = f"  Happy:{happy} Unhappy:{unhappy} ({pct})"
            self.stdscr.addstr(status_y, bx + 1, legend[:max_x - bx - 2],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Step {gen}  |  tolerance={self.schelling_tolerance:.1%}"
                f"  |  density={self.schelling_density:.0%}"
                f"  |  groups={self.schelling_n_groups}"
                f"  |  steps/f={self.schelling_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [t/T]=tolerance+/- [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Spatial Prisoner's Dilemma (Evolutionary Game Theory) — Mode @
# ══════════════════════════════════════════════════════════════════════

# Each preset: (name, description, T, R, P, S, init_coop_frac)
# T=temptation, R=reward, P=punishment, S=sucker
SPD_PRESETS = [
    ("Classic",
     "Standard PD — cooperators form clusters",
     1.5, 1.0, 0.0, 0.0, 0.5),
    ("Weak Dilemma",
     "Low temptation — cooperation spreads easily",
     1.2, 1.0, 0.0, 0.0, 0.5),
    ("Strong Dilemma",
     "High temptation — defection dominates",
     2.0, 1.0, 0.0, 0.0, 0.5),
    ("Snowdrift / Hawk-Dove",
     "Mutual defection is costly — coexistence regime",
     1.5, 1.0, 0.1, 0.5, 0.5),
    ("Stag Hunt",
     "High reward for mutual cooperation",
     1.2, 1.5, 0.0, 0.0, 0.4),
    ("Critical Threshold",
     "Right at the phase transition — fragile clusters",
     1.65, 1.0, 0.0, 0.0, 0.5),
    ("Mostly Defectors",
     "Few cooperators try to survive",
     1.4, 1.0, 0.0, 0.0, 0.15),
    ("Mostly Cooperators",
     "Defectors try to invade cooperative society",
     1.4, 1.0, 0.0, 0.0, 0.85),
]




def register(App):
    """Register schelling mode methods on the App class."""
    App._enter_schelling_mode = _enter_schelling_mode
    App._exit_schelling_mode = _exit_schelling_mode
    App._schelling_init = _schelling_init
    App._schelling_record_counts = _schelling_record_counts
    App._schelling_step = _schelling_step
    App._handle_schelling_menu_key = _handle_schelling_menu_key
    App._handle_schelling_key = _handle_schelling_key
    App._draw_schelling_menu = _draw_schelling_menu
    App._draw_schelling = _draw_schelling

