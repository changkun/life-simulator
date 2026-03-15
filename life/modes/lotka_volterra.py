"""Mode: lv — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_lv_mode(self):
    """Enter Predator-Prey mode — show preset menu."""
    self.lv_menu = True
    self.lv_menu_sel = 0
    self._flash("Predator-Prey (Lotka-Volterra) — select a scenario")



def _exit_lv_mode(self):
    """Exit Predator-Prey mode."""
    self.lv_mode = False
    self.lv_menu = False
    self.lv_running = False
    self.lv_grid = []
    self.lv_energy = []
    self.lv_grass_timer = []
    self.lv_counts = []
    self._flash("Predator-Prey mode OFF")



def _lv_init(self, preset_idx: int):
    """Initialize Predator-Prey simulation with the given preset."""
    (name, _desc, grass_regrow, prey_gain, pred_gain,
     prey_breed, pred_breed, prey_init_e, pred_init_e,
     prey_density, pred_density) = self.LV_PRESETS[preset_idx]
    self.lv_preset_name = name
    self.lv_generation = 0
    self.lv_running = False
    self.lv_grass_regrow = grass_regrow
    self.lv_prey_gain = prey_gain
    self.lv_pred_gain = pred_gain
    self.lv_prey_breed = prey_breed
    self.lv_pred_breed = pred_breed
    self.lv_prey_initial_energy = prey_init_e
    self.lv_pred_initial_energy = pred_init_e
    self.lv_counts = []

    max_y, max_x = self.stdscr.getmaxyx()
    self.lv_rows = max(10, max_y - 4)
    self.lv_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.lv_rows, self.lv_cols

    # Initialize grid: 0=grass, -1=empty (eaten grass regrowing)
    self.lv_grid = [[0] * cols for _ in range(rows)]
    self.lv_energy = [[0] * cols for _ in range(rows)]
    self.lv_grass_timer = [[0] * cols for _ in range(rows)]

    # Place prey
    for r in range(rows):
        for c in range(cols):
            if random.random() < prey_density:
                self.lv_grid[r][c] = 1  # prey
                self.lv_energy[r][c] = random.randint(1, prey_init_e)

    # Place predators (overwrite some cells)
    for r in range(rows):
        for c in range(cols):
            if self.lv_grid[r][c] != 1 and random.random() < pred_density:
                self.lv_grid[r][c] = 2  # predator
                self.lv_energy[r][c] = random.randint(1, pred_init_e)

    self._lv_record_counts()
    self.lv_menu = False
    self.lv_mode = True
    self._flash(f"Ecosystem: {name} — Space to start")



def _lv_record_counts(self):
    """Count grass, prey, predator populations."""
    g = prey = pred = 0
    for row in self.lv_grid:
        for cell in row:
            if cell == 0:
                g += 1
            elif cell == 1:
                prey += 1
            elif cell == 2:
                pred += 1
    self.lv_counts.append((g, prey, pred))



def _lv_step(self):
    """Advance the Predator-Prey simulation by one step."""
    rows, cols = self.lv_rows, self.lv_cols
    grid = self.lv_grid
    energy = self.lv_energy
    timers = self.lv_grass_timer

    # Collect all prey and predators with shuffled order
    prey_cells = []
    pred_cells = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                prey_cells.append((r, c))
            elif grid[r][c] == 2:
                pred_cells.append((r, c))
    random.shuffle(prey_cells)
    random.shuffle(pred_cells)

    # 4-connected neighbors
    dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    # Phase 1: Move prey
    moved_prey: set[tuple[int, int]] = set()
    for r, c in prey_cells:
        if grid[r][c] != 1:
            continue  # already eaten or moved
        # Look for grass neighbors to eat
        neighbors = []
        grass_neighbors = []
        for dr, dc in dirs:
            nr, nc = (r + dr) % rows, (c + dc) % cols
            neighbors.append((nr, nc))
            if grid[nr][nc] == 0:
                grass_neighbors.append((nr, nc))

        if grass_neighbors:
            # Move to a random grass cell and eat it
            nr, nc = random.choice(grass_neighbors)
        else:
            # Move to any empty (-1) neighbor if available
            empty = [(nr, nc) for nr, nc in neighbors
                     if grid[nr][nc] == -1]
            if empty:
                nr, nc = random.choice(empty)
            else:
                continue  # can't move

        # Check if destination is grass (eating)
        ate_grass = (grid[nr][nc] == 0)

        # Move prey
        grid[r][c] = -1  # leave empty
        timers[r][c] = self.lv_grass_regrow
        grid[nr][nc] = 1
        e = energy[r][c] - 1  # lose 1 energy per step
        if ate_grass:
            e += self.lv_prey_gain
        energy[nr][nc] = e
        energy[r][c] = 0

        # Check death (starvation)
        if e <= 0:
            grid[nr][nc] = -1
            timers[nr][nc] = self.lv_grass_regrow
            energy[nr][nc] = 0
            continue

        moved_prey.add((nr, nc))

        # Check reproduction
        if e >= self.lv_prey_breed:
            # Offspring goes to old cell
            energy[nr][nc] = e // 2
            grid[r][c] = 1
            energy[r][c] = e // 2
            timers[r][c] = 0

    # Phase 2: Move predators
    for r, c in pred_cells:
        if grid[r][c] != 2:
            continue  # already moved or dead
        neighbors = []
        prey_neighbors = []
        for dr, dc in dirs:
            nr, nc = (r + dr) % rows, (c + dc) % cols
            neighbors.append((nr, nc))
            if grid[nr][nc] == 1:
                prey_neighbors.append((nr, nc))

        if prey_neighbors:
            # Hunt: move to a prey cell
            nr, nc = random.choice(prey_neighbors)
            ate_prey = True
        else:
            # Move to empty or grass cell
            free = [(nr, nc) for nr, nc in neighbors
                    if grid[nr][nc] in (-1, 0)]
            if free:
                nr, nc = random.choice(free)
                ate_prey = False
            else:
                # Can't move, just lose energy
                energy[r][c] -= 1
                if energy[r][c] <= 0:
                    grid[r][c] = -1
                    timers[r][c] = self.lv_grass_regrow
                    energy[r][c] = 0
                continue

        was_grass = (grid[nr][nc] == 0)

        # Move predator
        grid[r][c] = -1
        timers[r][c] = self.lv_grass_regrow
        grid[nr][nc] = 2
        e = energy[r][c] - 1
        if ate_prey:
            e += self.lv_pred_gain
        energy[nr][nc] = e
        energy[r][c] = 0

        # Check death
        if e <= 0:
            grid[nr][nc] = -1
            timers[nr][nc] = self.lv_grass_regrow
            energy[nr][nc] = 0
            continue

        # Check reproduction
        if e >= self.lv_pred_breed:
            energy[nr][nc] = e // 2
            grid[r][c] = 2
            energy[r][c] = e // 2
            timers[r][c] = 0

    # Phase 3: Regrow grass
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == -1:
                timers[r][c] -= 1
                if timers[r][c] <= 0:
                    grid[r][c] = 0  # grass regrows
                    timers[r][c] = 0

    self.lv_generation += 1
    self._lv_record_counts()



def _handle_lv_menu_key(self, key: int) -> bool:
    """Handle input in Predator-Prey preset menu."""
    n = len(self.LV_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.lv_menu_sel = (self.lv_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.lv_menu_sel = (self.lv_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._lv_init(self.lv_menu_sel)
    elif key in (ord("q"), 27):
        self.lv_menu = False
        self._flash("Predator-Prey cancelled")
    return True



def _handle_lv_key(self, key: int) -> bool:
    """Handle input in active Predator-Prey simulation."""
    if key == ord(" "):
        self.lv_running = not self.lv_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.lv_steps_per_frame):
            self._lv_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.LV_PRESETS)
                    if p[0] == self.lv_preset_name), 0)
        self._lv_init(idx)
        self.lv_running = False
    elif key in (ord("R"), ord("m")):
        self.lv_mode = False
        self.lv_running = False
        self.lv_menu = True
        self.lv_menu_sel = 0
    elif key == ord("g") or key == ord("G"):
        delta = 1 if key == ord("g") else -1
        self.lv_grass_regrow = max(1, min(30, self.lv_grass_regrow + delta))
        self._flash(f"Grass regrowth: {self.lv_grass_regrow}")
    elif key == ord("b") or key == ord("B"):
        delta = 1 if key == ord("b") else -1
        self.lv_prey_breed = max(2, min(30, self.lv_prey_breed + delta))
        self._flash(f"Prey breed threshold: {self.lv_prey_breed}")
    elif key == ord("p"):
        self.lv_pred_breed = min(30, self.lv_pred_breed + 1)
        self._flash(f"Predator breed threshold: {self.lv_pred_breed}")
    elif key == ord("P"):
        self.lv_pred_breed = max(2, self.lv_pred_breed - 1)
        self._flash(f"Predator breed threshold: {self.lv_pred_breed}")
    elif key == ord("+") or key == ord("="):
        self.lv_steps_per_frame = min(20, self.lv_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.lv_steps_per_frame}")
    elif key == ord("-"):
        self.lv_steps_per_frame = max(1, self.lv_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.lv_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_lv_mode()
    else:
        return True
    return True



def _draw_lv_menu(self, max_y: int, max_x: int):
    """Draw the Predator-Prey preset selection menu."""
    self.stdscr.erase()
    title = "── Predator-Prey (Lotka-Volterra) ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.LV_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<22s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.lv_menu_sel:
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



def _draw_lv(self, max_y: int, max_x: int):
    """Draw the active Predator-Prey simulation."""
    self.stdscr.erase()
    grid = self.lv_grid
    rows, cols = self.lv_rows, self.lv_cols
    state = "▶ RUNNING" if self.lv_running else "⏸ PAUSED"
    gen = self.lv_generation

    # Current counts
    if self.lv_counts:
        g_count, prey_count, pred_count = self.lv_counts[-1]
    else:
        g_count = prey_count = pred_count = 0

    # Title bar
    title = (f" Ecosystem: {self.lv_preset_name}  |  step {gen}"
             f"  |  🌿{g_count} 🐇{prey_count} 🐺{pred_count}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    # Draw grid
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            sx = c * 2
            sy = 1 + r
            if val == 0:
                # Grass — green
                attr = curses.color_pair(2)
                ch = "░░"
            elif val == 1:
                # Prey — yellow/white bold
                attr = curses.color_pair(3) | curses.A_BOLD
                ch = "██"
            elif val == 2:
                # Predator — red bold
                attr = curses.color_pair(1) | curses.A_BOLD
                ch = "██"
            else:
                # Empty (-1) — dim/dark
                attr = curses.color_pair(6) | curses.A_DIM
                ch = "  "
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Population bar chart
    status_y = max_y - 3
    if status_y > 1 and self.lv_counts:
        total = g_count + prey_count + pred_count
        if total > 0:
            bar_w = min(40, max_x - 30)
            g_w = int(bar_w * g_count / total)
            prey_w = int(bar_w * prey_count / total)
            pred_w = bar_w - g_w - prey_w
            bx = 2
            try:
                self.stdscr.addstr(status_y, bx, "█" * g_w, curses.color_pair(2))
                bx += g_w
                self.stdscr.addstr(status_y, bx, "█" * prey_w, curses.color_pair(3) | curses.A_BOLD)
                bx += prey_w
                if pred_w > 0:
                    self.stdscr.addstr(status_y, bx, "█" * pred_w, curses.color_pair(1) | curses.A_BOLD)
                bx += pred_w
                legend = f"  Grass:{g_count} Prey:{prey_count} Pred:{pred_count}"
                self.stdscr.addstr(status_y, bx + 1, legend[:max_x - bx - 2],
                                   curses.color_pair(6))
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Step {gen}  |  regrow={self.lv_grass_regrow}"
                f"  |  prey-breed={self.lv_prey_breed}"
                f"  |  pred-breed={self.lv_pred_breed}"
                f"  |  prey-gain={self.lv_prey_gain}"
                f"  |  pred-gain={self.lv_pred_gain}"
                f"  |  steps/f={self.lv_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [g/G]=grass+/- [b/B]=prey-breed+/- [p/P]=pred-breed+/- [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Schelling Segregation Model — Mode K
# ══════════════════════════════════════════════════════════════════════

SCHELLING_PRESETS = [
    # (name, description, tolerance, density, n_groups)
    ("Mild Preference",
     "Low tolerance threshold — quick segregation",
     0.30, 0.90, 2),
    ("Classic Schelling",
     "Original 1/3 threshold — dramatic segregation",
     0.375, 0.90, 2),
    ("Moderate Bias",
     "Higher tolerance — slower, stronger clustering",
     0.50, 0.85, 2),
    ("Strong Preference",
     "High tolerance — fast, near-total segregation",
     0.625, 0.90, 2),
    ("Three Groups",
     "Three populations with moderate preference",
     0.375, 0.85, 3),
    ("Four Cultures",
     "Four groups — complex boundary dynamics",
     0.35, 0.80, 4),
    ("Sparse City",
     "Low density — lots of room to relocate",
     0.40, 0.50, 2),
    ("Packed Metropolis",
     "Very high density — few vacancies, slow churn",
     0.375, 0.97, 2),
]




def register(App):
    """Register lv mode methods on the App class."""
    App._enter_lv_mode = _enter_lv_mode
    App._exit_lv_mode = _exit_lv_mode
    App._lv_init = _lv_init
    App._lv_record_counts = _lv_record_counts
    App._lv_step = _lv_step
    App._handle_lv_menu_key = _handle_lv_menu_key
    App._handle_lv_key = _handle_lv_key
    App._draw_lv_menu = _draw_lv_menu
    App._draw_lv = _draw_lv

