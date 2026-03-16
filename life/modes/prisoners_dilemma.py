"""Mode: spd — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_spd_mode(self):
    """Enter Spatial Prisoner's Dilemma mode — show preset menu."""
    self.spd_menu = True
    self.spd_menu_sel = 0
    self._flash("Spatial Prisoner's Dilemma — select a scenario")



def _exit_spd_mode(self):
    """Exit Spatial Prisoner's Dilemma mode."""
    self.spd_mode = False
    self.spd_menu = False
    self.spd_running = False
    self.spd_grid = []
    self.spd_scores = []
    self._flash("Prisoner's Dilemma mode OFF")



def _spd_init(self, preset_idx: int):
    """Initialize SPD simulation with the given preset."""
    (name, _desc, T, R, P, S,
     init_coop) = self.SPD_PRESETS[preset_idx]
    self.spd_preset_name = name
    self.spd_generation = 0
    self.spd_running = False
    self.spd_steps_per_frame = 1
    self.spd_temptation = T
    self.spd_reward = R
    self.spd_punishment = P
    self.spd_sucker = S
    self.spd_init_coop_frac = init_coop

    max_y, max_x = self.stdscr.getmaxyx()
    self.spd_rows = max(10, max_y - 4)
    self.spd_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.spd_rows, self.spd_cols

    # Initialize grid: 0=cooperator, 1=defector
    self.spd_grid = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if random.random() >= init_coop:
                self.spd_grid[r][c] = 1  # defector

    self.spd_scores = [[0.0] * cols for _ in range(rows)]
    self._spd_compute_scores()
    self._spd_count()
    self.spd_menu = False
    self.spd_mode = True
    self._flash(f"Prisoner's Dilemma: {name} — Space to start")



def _spd_compute_scores(self):
    """Compute payoff scores for all cells by playing PD with neighbors."""
    grid = self.spd_grid
    rows, cols = self.spd_rows, self.spd_cols
    T, R, P, S = (self.spd_temptation, self.spd_reward,
                   self.spd_punishment, self.spd_sucker)
    scores = self.spd_scores

    for r in range(rows):
        for c in range(cols):
            total = 0.0
            my_strat = grid[r][c]
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    opp = grid[nr][nc]
                    if my_strat == 0:  # cooperator
                        if opp == 0:
                            total += R  # mutual cooperation
                        else:
                            total += S  # sucker
                    else:  # defector
                        if opp == 0:
                            total += T  # temptation
                        else:
                            total += P  # mutual defection
            scores[r][c] = total



def _spd_count(self):
    """Count cooperators and defectors."""
    coop = 0
    for row in self.spd_grid:
        for v in row:
            if v == 0:
                coop += 1
    total = self.spd_rows * self.spd_cols
    self.spd_coop_count = coop
    self.spd_defect_count = total - coop



def _spd_step(self):
    """Advance the SPD simulation by one generation.

    Each cell adopts the strategy of the neighbor (or itself)
    with the highest payoff score.
    """
    grid = self.spd_grid
    scores = self.spd_scores
    rows, cols = self.spd_rows, self.spd_cols

    new_grid = [row[:] for row in grid]

    for r in range(rows):
        for c in range(cols):
            best_score = scores[r][c]
            best_strat = grid[r][c]
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    if scores[nr][nc] > best_score:
                        best_score = scores[nr][nc]
                        best_strat = grid[nr][nc]
            new_grid[r][c] = best_strat

    self.spd_grid = new_grid
    self._spd_compute_scores()
    self._spd_count()
    self.spd_generation += 1



def _handle_spd_menu_key(self, key: int) -> bool:
    """Handle input in SPD preset menu."""
    n = len(self.SPD_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.spd_menu_sel = (self.spd_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.spd_menu_sel = (self.spd_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._spd_init(self.spd_menu_sel)
    elif key in (ord("q"), 27):
        self.spd_menu = False
        self._flash("Prisoner's Dilemma cancelled")
    return True



def _handle_spd_key(self, key: int) -> bool:
    """Handle input in active SPD simulation."""
    if key == ord(" "):
        self.spd_running = not self.spd_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.spd_steps_per_frame):
            self._spd_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.SPD_PRESETS)
                    if p[0] == self.spd_preset_name), 0)
        self._spd_init(idx)
        self.spd_running = False
    elif key in (ord("R"), ord("m")):
        self.spd_mode = False
        self.spd_running = False
        self.spd_menu = True
        self.spd_menu_sel = 0
    elif key == ord("t") or key == ord("T"):
        delta = 0.05 if key == ord("t") else -0.05
        self.spd_temptation = max(0.0, min(5.0, self.spd_temptation + delta))
        self._spd_compute_scores()
        self._flash(f"Temptation T={self.spd_temptation:.2f}")
    elif key == ord("+") or key == ord("="):
        self.spd_steps_per_frame = min(20, self.spd_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.spd_steps_per_frame}")
    elif key == ord("-"):
        self.spd_steps_per_frame = max(1, self.spd_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.spd_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_spd_mode()
    else:
        return True
    return True



def _draw_spd_menu(self, max_y: int, max_x: int):
    """Draw the SPD preset selection menu."""
    self.stdscr.erase()
    title = "── Spatial Prisoner's Dilemma ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.SPD_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<24s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.spd_menu_sel:
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



def _draw_spd(self, max_y: int, max_x: int):
    """Draw the active Spatial Prisoner's Dilemma simulation."""
    self.stdscr.erase()
    grid = self.spd_grid
    scores = self.spd_scores
    rows, cols = self.spd_rows, self.spd_cols
    state = "▶ RUNNING" if self.spd_running else "⏸ PAUSED"
    gen = self.spd_generation
    coop = self.spd_coop_count
    defect = self.spd_defect_count
    total = coop + defect

    # Title bar
    pct = f"{100 * coop / total:.0f}%" if total > 0 else "N/A"
    title = (f" PD: {self.spd_preset_name}  |  gen {gen}"
             f"  |  C:{coop} D:{defect} ({pct} coop)"
             f"  |  T={self.spd_temptation:.2f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    # Find max score for intensity scaling
    max_score = 0.001
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            s = scores[r][c]
            if s > max_score:
                max_score = s

    # Draw grid
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            sx = c * 2
            sy = 1 + r
            s = scores[r][c]
            intensity = s / max_score if max_score > 0 else 0

            if val == 0:  # cooperator — cyan/green
                if intensity > 0.7:
                    attr = curses.color_pair(2) | curses.A_BOLD
                    ch = "██"
                elif intensity > 0.4:
                    attr = curses.color_pair(2)
                    ch = "▓▓"
                else:
                    attr = curses.color_pair(2) | curses.A_DIM
                    ch = "░░"
            else:  # defector — red
                if intensity > 0.7:
                    attr = curses.color_pair(5) | curses.A_BOLD
                    ch = "██"
                elif intensity > 0.4:
                    attr = curses.color_pair(5)
                    ch = "▓▓"
                else:
                    attr = curses.color_pair(5) | curses.A_DIM
                    ch = "░░"
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Cooperation bar
    status_y = max_y - 3
    if status_y > 1 and total > 0:
        bar_w = min(40, max_x - 30)
        coop_w = int(bar_w * coop / total)
        defect_w = bar_w - coop_w
        bx = 2
        try:
            self.stdscr.addstr(status_y, bx, "█" * coop_w, curses.color_pair(2))
            bx += coop_w
            if defect_w > 0:
                self.stdscr.addstr(status_y, bx, "█" * defect_w, curses.color_pair(5) | curses.A_BOLD)
            bx += defect_w
            legend = f"  Coop:{coop} Defect:{defect} ({pct})"
            self.stdscr.addstr(status_y, bx + 1, legend[:max_x - bx - 2],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Gen {gen}  |  T={self.spd_temptation:.2f}"
                f"  R={self.spd_reward:.1f}"
                f"  P={self.spd_punishment:.1f}"
                f"  S={self.spd_sucker:.1f}"
                f"  |  steps/f={self.spd_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [t/T]=temptation+/- [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Turmites (2D Turing Machine) — Mode Q
# ══════════════════════════════════════════════════════════════════════

# Each preset: (name, description, num_colors, num_states, table)
# table[state][color] = (write_color, turn, new_state)
# turn: 0=no turn, 1=right, 2=u-turn, 3=left
TURMITE_PRESETS = [
    ("Langton's Ant", "Classic RL ant — highway after ~10k steps", 2, 1,
     [[(1, 1, 0), (1, 3, 0)]]),
    ("Fibonacci Spiral", "Produces a Fibonacci-like spiral pattern", 2, 2,
     [[(1, 1, 1), (1, 1, 0)],
      [(1, 0, 0), (0, 0, 1)]]),
    ("Square Builder", "Builds a growing filled square", 2, 2,
     [[(1, 1, 0), (0, 1, 1)],
      [(1, 3, 1), (0, 3, 0)]]),
    ("Snowflake", "Symmetric crystal-like growth", 2, 3,
     [[(1, 1, 1), (1, 3, 2)],
      [(1, 1, 0), (0, 0, 2)],
      [(1, 3, 0), (0, 3, 1)]]),
    ("Chaos", "Complex chaotic behavior", 2, 2,
     [[(1, 1, 1), (1, 3, 0)],
      [(0, 3, 0), (0, 1, 1)]]),
    ("Highway Builder", "Builds a long highway quickly", 2, 2,
     [[(1, 1, 1), (1, 1, 0)],
      [(1, 3, 0), (0, 1, 1)]]),
    ("Spiral Growth", "Expanding spiral with internal structure", 2, 3,
     [[(1, 1, 1), (1, 3, 0)],
      [(0, 1, 2), (1, 3, 1)],
      [(1, 3, 0), (0, 1, 2)]]),
    ("Diamond", "Grows a diamond-shaped region", 2, 2,
     [[(1, 1, 1), (0, 3, 0)],
      [(1, 3, 0), (1, 1, 1)]]),
    ("Worm Trail", "Leaves a distinctive worm-like trail", 2, 3,
     [[(1, 1, 1), (1, 1, 0)],
      [(0, 3, 2), (0, 0, 0)],
      [(1, 1, 0), (0, 3, 1)]]),
    ("3-Color Spiral", "3-color turmite with spiral behavior", 3, 2,
     [[(1, 1, 1), (2, 3, 0), (0, 1, 0)],
      [(2, 1, 0), (0, 3, 1), (1, 3, 1)]]),
]

TURMITE_COLORS = [1, 2, 3, 4, 5, 6, 7, 8]




def register(App):
    """Register spd mode methods on the App class."""
    from life.modes.schelling import SPD_PRESETS
    App.SPD_PRESETS = SPD_PRESETS
    App._enter_spd_mode = _enter_spd_mode
    App._exit_spd_mode = _exit_spd_mode
    App._spd_init = _spd_init
    App._spd_compute_scores = _spd_compute_scores
    App._spd_count = _spd_count
    App._spd_step = _spd_step
    App._handle_spd_menu_key = _handle_spd_menu_key
    App._handle_spd_key = _handle_spd_key
    App._draw_spd_menu = _draw_spd_menu
    App._draw_spd = _draw_spd

