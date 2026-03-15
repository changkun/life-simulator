"""Mode: lightning — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_lightning_mode(self):
    """Enter Lightning / Dielectric Breakdown mode — show preset menu."""
    self.lightning_menu = True
    self.lightning_menu_sel = 0
    self._flash("Lightning / Dielectric Breakdown — select a scenario")



def _exit_lightning_mode(self):
    """Exit Lightning mode."""
    self.lightning_mode = False
    self.lightning_menu = False
    self.lightning_running = False
    self.lightning_grid = []
    self.lightning_potential = []
    self.lightning_age = []
    self._flash("Lightning mode OFF")



def _lightning_init(self, preset_idx: int):
    """Initialize lightning simulation with the given preset."""
    (name, _desc, eta, source) = self.LIGHTNING_PRESETS[preset_idx]
    self.lightning_preset_name = name
    self.lightning_generation = 0
    self.lightning_running = False
    self.lightning_eta = eta
    self.lightning_source = source

    max_y, max_x = self.stdscr.getmaxyx()
    self.lightning_rows = max(10, max_y - 4)
    self.lightning_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.lightning_rows, self.lightning_cols

    # Initialize empty grid
    self.lightning_grid = [[0] * cols for _ in range(rows)]
    self.lightning_age = [[0] * cols for _ in range(rows)]
    self.lightning_channel_count = 0

    # Set initial discharge source
    if source == "top":
        # Discharge starts from center of top row
        c = cols // 2
        self.lightning_grid[0][c] = 1
        self.lightning_age[0][c] = 0
        self.lightning_channel_count = 1
    elif source == "center":
        # Discharge starts from center
        r, c = rows // 2, cols // 2
        self.lightning_grid[r][c] = 1
        self.lightning_age[r][c] = 0
        self.lightning_channel_count = 1
    elif source == "point":
        # Discharge from a single point near top-center
        r, c = rows // 4, cols // 2
        self.lightning_grid[r][c] = 1
        self.lightning_age[r][c] = 0
        self.lightning_channel_count = 1

    # Compute initial potential field
    self.lightning_potential = [[0.0] * cols for _ in range(rows)]
    self._lightning_solve_potential()

    self.lightning_menu = False
    self.lightning_mode = True
    self._flash(f"Lightning: {name} — Space to start")



def _lightning_solve_potential(self):
    """Solve the electric potential using iterative relaxation (Laplace).

    Boundary conditions:
    - Discharge channel cells: potential = 0
    - Bottom row (or boundary for center/point): potential = 1
    - Other boundaries: Neumann (zero gradient)
    """
    grid = self.lightning_grid
    rows, cols = self.lightning_rows, self.lightning_cols
    pot = self.lightning_potential
    source = self.lightning_source

    # Initialize potential: channel=0, ground=1
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                pot[r][c] = 0.0
            else:
                pot[r][c] = 0.5  # initial guess

    # Set ground boundary
    if source == "top":
        for c in range(cols):
            if grid[rows - 1][c] == 0:
                pot[rows - 1][c] = 1.0
    else:
        # For center/point: ground is at all edges
        for c in range(cols):
            if grid[0][c] == 0:
                pot[0][c] = 1.0
            if grid[rows - 1][c] == 0:
                pot[rows - 1][c] = 1.0
        for r in range(rows):
            if grid[r][0] == 0:
                pot[r][0] = 1.0
            if grid[r][cols - 1] == 0:
                pot[r][cols - 1] = 1.0

    # Iterative Gauss-Seidel relaxation
    # Fewer iterations for speed; enough for reasonable field approximation
    iterations = min(80, max(rows, cols))
    for _ in range(iterations):
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 1:
                    continue  # channel is fixed at 0
                # Ground boundary
                if source == "top" and r == rows - 1:
                    continue
                if source != "top":
                    if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                        continue

                # Average of neighbors (with boundary handling)
                total = 0.0
                count = 0
                if r > 0:
                    total += pot[r - 1][c]
                    count += 1
                if r < rows - 1:
                    total += pot[r + 1][c]
                    count += 1
                if c > 0:
                    total += pot[r][c - 1]
                    count += 1
                if c < cols - 1:
                    total += pot[r][c + 1]
                    count += 1
                if count > 0:
                    pot[r][c] = total / count



def _lightning_step(self):
    """Advance lightning simulation by one step.

    Dielectric Breakdown Model:
    1. Find all empty cells adjacent to the discharge channel (growth candidates)
    2. Compute growth probability proportional to (local E-field)^eta
    3. Pick one candidate weighted by probability and add it to channel
    4. Re-solve potential field
    """
    grid = self.lightning_grid
    pot = self.lightning_potential
    rows, cols = self.lightning_rows, self.lightning_cols
    eta = self.lightning_eta

    # Find growth candidates: empty cells adjacent to channel
    candidates = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 1:
                # Check 4-connected neighbors for empty cells
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if grid[nr][nc] == 0:
                            candidates.append((nr, nc))

    if not candidates:
        self.lightning_running = False
        return

    # Remove duplicates
    candidates = list(set(candidates))

    # Compute weights: potential^eta (potential at candidate gives E-field proxy)
    weights = []
    for (r, c) in candidates:
        phi = pot[r][c]
        w = phi ** eta if phi > 0 else 0.0
        weights.append(w)

    total_w = sum(weights)
    if total_w <= 0:
        # No valid growth sites
        self.lightning_running = False
        return

    # Weighted random selection
    rval = random.random() * total_w
    cumulative = 0.0
    chosen = candidates[0]
    for i, (r, c) in enumerate(candidates):
        cumulative += weights[i]
        if cumulative >= rval:
            chosen = (r, c)
            break

    # Add chosen cell to discharge channel
    cr, cc = chosen
    grid[cr][cc] = 1
    self.lightning_age[cr][cc] = self.lightning_generation
    self.lightning_channel_count += 1

    # Check if we've reached ground
    source = self.lightning_source
    reached_ground = False
    if source == "top" and cr == rows - 1:
        reached_ground = True
    elif source != "top":
        if cr == 0 or cr == rows - 1 or cc == 0 or cc == cols - 1:
            reached_ground = True

    if reached_ground:
        self.lightning_running = False

    # Re-solve potential
    self._lightning_solve_potential()
    self.lightning_generation += 1



def _handle_lightning_menu_key(self, key: int) -> bool:
    """Handle input in lightning preset menu."""
    n = len(self.LIGHTNING_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.lightning_menu_sel = (self.lightning_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.lightning_menu_sel = (self.lightning_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._lightning_init(self.lightning_menu_sel)
    elif key in (ord("q"), 27):
        self.lightning_menu = False
        self._flash("Lightning cancelled")
    return True



def _handle_lightning_key(self, key: int) -> bool:
    """Handle input in active lightning simulation."""
    if key == ord(" "):
        self.lightning_running = not self.lightning_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.lightning_steps_per_frame):
            self._lightning_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.LIGHTNING_PRESETS)
                    if p[0] == self.lightning_preset_name), 0)
        self._lightning_init(idx)
        self.lightning_running = False
    elif key in (ord("R"), ord("m")):
        self.lightning_mode = False
        self.lightning_running = False
        self.lightning_menu = True
        self.lightning_menu_sel = 0
    elif key == ord("e") or key == ord("E"):
        delta = 0.25 if key == ord("e") else -0.25
        self.lightning_eta = max(0.1, min(10.0, self.lightning_eta + delta))
        self._flash(f"Eta (branching) = {self.lightning_eta:.2f}")
    elif key == ord("+") or key == ord("="):
        self.lightning_steps_per_frame = min(20, self.lightning_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.lightning_steps_per_frame}")
    elif key == ord("-"):
        self.lightning_steps_per_frame = max(1, self.lightning_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.lightning_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_lightning_mode()
    else:
        return True
    return True



def _draw_lightning_menu(self, max_y: int, max_x: int):
    """Draw the lightning preset selection menu."""
    self.stdscr.erase()
    title = "── Lightning / Dielectric Breakdown ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.LIGHTNING_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<24s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.lightning_menu_sel:
            attr = curses.color_pair(3) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_lightning(self, max_y: int, max_x: int):
    """Draw the active Lightning / Dielectric Breakdown simulation."""
    self.stdscr.erase()
    grid = self.lightning_grid
    age = self.lightning_age
    rows, cols = self.lightning_rows, self.lightning_cols
    gen = self.lightning_generation
    state = "▶ RUNNING" if self.lightning_running else "⏸ PAUSED"
    chan = self.lightning_channel_count

    # Title bar
    title = (f" Lightning: {self.lightning_preset_name}  |  step {gen}"
             f"  |  channels: {chan}"
             f"  |  η={self.lightning_eta:.2f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(3) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 3
    view_cols = (max_x - 1) // 2

    # Draw grid
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            sx = c * 2
            sy = 1 + r
            if grid[r][c] == 1:
                # Discharge channel — color by age for visual effect
                cell_age = gen - age[r][c] if gen > 0 else 0
                if cell_age <= 2:
                    # Fresh growth — bright white/yellow
                    attr = curses.color_pair(3) | curses.A_BOLD
                    ch = "██"
                elif cell_age <= 8:
                    # Recent — cyan
                    attr = curses.color_pair(6) | curses.A_BOLD
                    ch = "▓▓"
                elif cell_age <= 20:
                    # Older — blue
                    attr = curses.color_pair(4)
                    ch = "▒▒"
                else:
                    # Old — dim blue
                    attr = curses.color_pair(4) | curses.A_DIM
                    ch = "░░"
                try:
                    self.stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass
            else:
                # Empty — show faint potential field
                phi = self.lightning_potential[r][c] if r < len(self.lightning_potential) else 0
                if phi > 0.7:
                    try:
                        self.stdscr.addstr(sy, sx, "··", curses.color_pair(5) | curses.A_DIM)
                    except curses.error:
                        pass
                elif phi > 0.4:
                    try:
                        self.stdscr.addstr(sy, sx, "· ", curses.color_pair(5) | curses.A_DIM)
                    except curses.error:
                        pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [e/E]=eta+/- [+/-]=steps/f [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Hydraulic Erosion — Mode $
# ══════════════════════════════════════════════════════════════════════

# Each preset: (name, description, rain_rate, evap_rate, solubility, deposition, terrain_type)
EROSION_PRESETS = [
    ("River Valley",
     "Gentle terrain — wide meandering rivers",
     0.012, 0.004, 0.008, 0.015, "gentle"),
    ("Mountain Gorge",
     "Steep terrain — deep narrow canyons",
     0.015, 0.003, 0.015, 0.010, "steep"),
    ("Coastal Plateau",
     "Flat plateau with coastal cliffs — branching drainage",
     0.010, 0.005, 0.010, 0.020, "plateau"),
    ("Badlands",
     "Heavily eroded terrain — dense dendritic networks",
     0.020, 0.003, 0.020, 0.008, "rough"),
    ("Alpine Peaks",
     "High mountain terrain — glacial-style carving",
     0.008, 0.002, 0.012, 0.012, "alpine"),
    ("Rolling Hills",
     "Smooth undulating terrain — gentle streams",
     0.010, 0.006, 0.006, 0.025, "hills"),
    ("Canyon Lands",
     "Layered mesa terrain — slot canyon formation",
     0.018, 0.003, 0.018, 0.010, "mesa"),
    ("Volcanic Island",
     "Central peak with radial drainage",
     0.014, 0.004, 0.014, 0.012, "volcano"),
]




def register(App):
    """Register lightning mode methods on the App class."""
    App._enter_lightning_mode = _enter_lightning_mode
    App._exit_lightning_mode = _exit_lightning_mode
    App._lightning_init = _lightning_init
    App._lightning_solve_potential = _lightning_solve_potential
    App._lightning_step = _lightning_step
    App._handle_lightning_menu_key = _handle_lightning_menu_key
    App._handle_lightning_key = _handle_lightning_key
    App._draw_lightning_menu = _draw_lightning_menu
    App._draw_lightning = _draw_lightning

