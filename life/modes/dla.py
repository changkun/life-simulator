"""Mode: dla — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

# ══════════════════════════════════════════════════════════════════════
#  Diffusion-Limited Aggregation (DLA) — Mode D
# ══════════════════════════════════════════════════════════════════════

DLA_PRESETS = [
    # (name, description, setup_key)
    ("Crystal Growth", "Single seed — classic dendritic fractal", "single"),
    ("Multi-Seed", "Several seeds grow and merge", "multi"),
    ("Snowflake", "6-fold symmetry from center seed", "snowflake"),
    ("Electrodeposition", "Bottom-edge cathode with downward drift", "electro"),
    ("Line Seed", "Horizontal line seed — forest-like growth", "line"),
    ("Ring Seed", "Circular ring seed — inward/outward growth", "ring"),
]

# Characters for crystal age visualization (oldest -> newest)
DLA_CRYSTAL_CHARS = ["█", "▓", "▒", "░", "∙"]
DLA_WALKER_CHAR = "·"

def _enter_dla_mode(self):
    """Enter DLA mode — show preset menu."""
    self.dla_menu = True
    self.dla_menu_sel = 0
    self._flash("Diffusion-Limited Aggregation — select a configuration")



def _exit_dla_mode(self):
    """Exit DLA mode."""
    self.dla_mode = False
    self.dla_menu = False
    self.dla_running = False
    self.dla_grid = []
    self.dla_walkers = []
    self._flash("DLA mode OFF")



def _dla_init(self, preset_idx: int):
    """Initialize DLA simulation with the given preset."""
    name, _desc, setup_key = self.DLA_PRESETS[preset_idx]
    self.dla_preset_name = name
    self.dla_generation = 0
    self.dla_running = False
    self.dla_crystal_count = 0
    self.dla_bias_r = 0.0
    self.dla_bias_c = 0.0
    self.dla_symmetry = 1
    self.dla_stickiness = 1.0

    max_y, max_x = self.stdscr.getmaxyx()
    self.dla_rows = max(20, max_y - 3)
    self.dla_cols = max(20, (max_x - 1) // 2)
    rows, cols = self.dla_rows, self.dla_cols
    cr, cc = rows // 2, cols // 2

    # Initialize empty grid
    self.dla_grid = [[0] * cols for _ in range(rows)]
    self.dla_seeds = []
    self.dla_walkers = []
    self.dla_max_radius = 5.0

    if setup_key == "single":
        self.dla_grid[cr][cc] = 1
        self.dla_seeds = [(cr, cc)]
        self.dla_crystal_count = 1
        self.dla_num_walkers = 300
        self.dla_steps_per_frame = 10

    elif setup_key == "multi":
        seed_positions = [
            (cr - rows // 4, cc - cols // 4),
            (cr - rows // 4, cc + cols // 4),
            (cr + rows // 4, cc - cols // 4),
            (cr + rows // 4, cc + cols // 4),
            (cr, cc),
        ]
        for sr, sc in seed_positions:
            sr = max(1, min(rows - 2, sr))
            sc = max(1, min(cols - 2, sc))
            self.dla_grid[sr][sc] = 1
            self.dla_seeds.append((sr, sc))
            self.dla_crystal_count += 1
        self.dla_num_walkers = 400
        self.dla_steps_per_frame = 10

    elif setup_key == "snowflake":
        self.dla_grid[cr][cc] = 1
        self.dla_seeds = [(cr, cc)]
        self.dla_crystal_count = 1
        self.dla_symmetry = 6
        self.dla_num_walkers = 300
        self.dla_steps_per_frame = 10
        self.dla_stickiness = 0.7  # lower stickiness = more branching

    elif setup_key == "electro":
        # Bottom edge is the seed (cathode)
        for c in range(cols):
            self.dla_grid[rows - 1][c] = 1
            self.dla_seeds.append((rows - 1, c))
            self.dla_crystal_count += 1
        self.dla_bias_r = 0.15  # drift downward toward cathode (positive = increasing row)
        self.dla_num_walkers = 500
        self.dla_steps_per_frame = 8
        self.dla_max_radius = float(rows)

    elif setup_key == "line":
        # Horizontal line seed in the middle
        for c in range(cols // 4, 3 * cols // 4):
            self.dla_grid[cr][c] = 1
            self.dla_seeds.append((cr, c))
            self.dla_crystal_count += 1
        self.dla_num_walkers = 400
        self.dla_steps_per_frame = 10

    elif setup_key == "ring":
        # Circular ring seed
        ring_r = min(rows, cols) // 5
        for angle_i in range(360):
            a = math.radians(angle_i)
            sr = cr + int(ring_r * math.sin(a))
            sc = cc + int(ring_r * math.cos(a))
            if 0 <= sr < rows and 0 <= sc < cols and self.dla_grid[sr][sc] == 0:
                self.dla_grid[sr][sc] = 1
                self.dla_seeds.append((sr, sc))
                self.dla_crystal_count += 1
        self.dla_num_walkers = 400
        self.dla_steps_per_frame = 10

    # Spawn initial walkers
    self._dla_spawn_walkers()

    self.dla_menu = False
    self.dla_mode = True
    self._flash(f"DLA: {name} — Space to start")



def _dla_spawn_walkers(self):
    """Spawn walkers on a ring around the crystal."""
    rows, cols = self.dla_rows, self.dla_cols
    cr, cc = rows // 2, cols // 2
    # Spawn radius is a bit beyond the max crystal radius
    spawn_r = min(self.dla_max_radius + 10, min(rows, cols) // 2 - 2)
    self.dla_spawn_radius = spawn_r

    while len(self.dla_walkers) < self.dla_num_walkers:
        if self.dla_symmetry > 1:
            # For symmetric presets, spawn uniformly
            angle = random.random() * 2 * math.pi
            dist = spawn_r * (0.8 + 0.4 * random.random())
            wr = cr + int(dist * math.sin(angle))
            wc = cc + int(dist * math.cos(angle))
        elif self.dla_bias_r != 0.0:
            # Biased drift (e.g. electrodeposition): spawn from opposite side
            wr = random.randint(0, max(1, rows // 3))
            wc = random.randint(0, cols - 1)
        else:
            # General: spawn on ring around center
            angle = random.random() * 2 * math.pi
            dist = spawn_r * (0.8 + 0.4 * random.random())
            wr = cr + int(dist * math.sin(angle))
            wc = cc + int(dist * math.cos(angle))
        # Clamp to grid
        wr = max(0, min(rows - 1, wr))
        wc = max(0, min(cols - 1, wc))
        if self.dla_grid[wr][wc] == 0:
            self.dla_walkers.append([wr, wc])



def _dla_step(self):
    """Advance DLA simulation by one step."""
    rows, cols = self.dla_rows, self.dla_cols
    grid = self.dla_grid
    cr, cc = rows // 2, cols // 2
    gen = self.dla_generation + 1
    kill_radius = self.dla_spawn_radius + 20

    new_walkers = []
    attached_any = False

    for w in self.dla_walkers:
        wr, wc = w[0], w[1]

        # Random walk with optional bias
        dr = random.choice([-1, 0, 1])
        dc = random.choice([-1, 0, 1])
        if self.dla_bias_r != 0.0 and random.random() < abs(self.dla_bias_r):
            dr = -1 if self.dla_bias_r < 0 else 1
        if self.dla_bias_c != 0.0 and random.random() < abs(self.dla_bias_c):
            dc = -1 if self.dla_bias_c < 0 else 1

        nr, nc = wr + dr, wc + dc

        # Boundary handling
        if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
            new_walkers.append(w)
            continue

        # Check if new position is already crystal
        if grid[nr][nc] > 0:
            new_walkers.append(w)
            continue

        # Move walker
        w[0], w[1] = nr, nc

        # Check if adjacent to crystal
        adjacent = False
        for adr, adc in [(-1, 0), (1, 0), (0, -1), (0, 1),
                         (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            ar, ac = nr + adr, nc + adc
            if 0 <= ar < rows and 0 <= ac < cols and grid[ar][ac] > 0:
                adjacent = True
                break

        if adjacent and (self.dla_stickiness >= 1.0 or random.random() < self.dla_stickiness):
            # Attach walker to crystal
            if self.dla_symmetry > 1:
                # Apply rotational symmetry
                self._dla_attach_symmetric(nr, nc, gen)
            else:
                grid[nr][nc] = gen
                self.dla_crystal_count += 1
                # Update max radius
                dist = math.sqrt((nr - cr) ** 2 + (nc - cc) ** 2)
                if dist > self.dla_max_radius:
                    self.dla_max_radius = dist
            attached_any = True
        else:
            # Kill walker if too far from center
            dist = math.sqrt((nr - cr) ** 2 + (nc - cc) ** 2)
            if dist > kill_radius:
                continue  # drop this walker
            new_walkers.append(w)

    self.dla_walkers = new_walkers
    self.dla_generation = gen

    # Replenish walkers
    if attached_any or len(self.dla_walkers) < self.dla_num_walkers:
        self._dla_spawn_walkers()



def _dla_attach_symmetric(self, r: int, c: int, gen: int):
    """Attach a crystal cell with rotational symmetry."""
    rows, cols = self.dla_rows, self.dla_cols
    cr, cc = rows // 2, cols // 2
    grid = self.dla_grid
    sym = self.dla_symmetry

    # Get offset from center
    dr = r - cr
    dc = c - cc

    for k in range(sym):
        angle = 2 * math.pi * k / sym
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        # Rotate the offset
        rr = int(round(cr + dr * cos_a - dc * sin_a))
        rc = int(round(cc + dr * sin_a + dc * cos_a))
        if 0 <= rr < rows and 0 <= rc < cols and grid[rr][rc] == 0:
            grid[rr][rc] = gen
            self.dla_crystal_count += 1
            dist = math.sqrt((rr - cr) ** 2 + (rc - cc) ** 2)
            if dist > self.dla_max_radius:
                self.dla_max_radius = dist
        # Also mirror for full snowflake symmetry
        if sym == 6:
            rr2 = int(round(cr + dc * sin_a + dr * cos_a))
            rc2 = int(round(cc + dc * cos_a - dr * sin_a))
            if 0 <= rr2 < rows and 0 <= rc2 < cols and grid[rr2][rc2] == 0:
                grid[rr2][rc2] = gen
                self.dla_crystal_count += 1
                dist2 = math.sqrt((rr2 - cr) ** 2 + (rc2 - cc) ** 2)
                if dist2 > self.dla_max_radius:
                    self.dla_max_radius = dist2



def _handle_dla_menu_key(self, key: int) -> bool:
    """Handle input in DLA preset menu."""
    n = len(self.DLA_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.dla_menu_sel = (self.dla_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.dla_menu_sel = (self.dla_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._dla_init(self.dla_menu_sel)
    elif key in (ord("q"), 27):
        self.dla_menu = False
        self._flash("DLA cancelled")
    return True



def _handle_dla_key(self, key: int) -> bool:
    """Handle input in active DLA simulation."""
    if key == ord(" "):
        self.dla_running = not self.dla_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.dla_steps_per_frame):
            self._dla_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.DLA_PRESETS)
                    if p[0] == self.dla_preset_name), 0)
        self._dla_init(idx)
        self.dla_running = False
    elif key in (ord("R"), ord("m")):
        self.dla_mode = False
        self.dla_running = False
        self.dla_menu = True
        self.dla_menu_sel = 0
    elif key == ord("s") or key == ord("S"):
        delta = 0.1 if key == ord("s") else -0.1
        self.dla_stickiness = max(0.1, min(1.0, self.dla_stickiness + delta))
        self._flash(f"Stickiness: {self.dla_stickiness:.1f}")
    elif key == ord("w") or key == ord("W"):
        delta = 50 if key == ord("w") else -50
        self.dla_num_walkers = max(50, min(2000, self.dla_num_walkers + delta))
        self._flash(f"Walkers: {self.dla_num_walkers}")
    elif key == ord("+") or key == ord("="):
        self.dla_steps_per_frame = min(50, self.dla_steps_per_frame + 2)
        self._flash(f"Steps/frame: {self.dla_steps_per_frame}")
    elif key == ord("-"):
        self.dla_steps_per_frame = max(1, self.dla_steps_per_frame - 2)
        self._flash(f"Steps/frame: {self.dla_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">") or key == ord("."):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_dla_mode()
    else:
        return True
    return True



def _draw_dla_menu(self, max_y: int, max_x: int):
    """Draw the DLA preset selection menu."""
    self.stdscr.erase()
    title = "── Diffusion-Limited Aggregation ── Select Configuration ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _key) in enumerate(self.DLA_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<20s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.dla_menu_sel:
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



def _draw_dla(self, max_y: int, max_x: int):
    """Draw the active DLA simulation."""
    self.stdscr.erase()
    grid = self.dla_grid
    rows, cols = self.dla_rows, self.dla_cols
    state = "▶ RUNNING" if self.dla_running else "⏸ PAUSED"
    gen = self.dla_generation

    # Title bar
    title = (f" DLA: {self.dla_preset_name}  |  gen {gen}"
             f"  |  crystal={self.dla_crystal_count}"
             f"  |  walkers={len(self.dla_walkers)}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 3
    view_cols = (max_x - 1) // 2

    # Color palette for crystal age: older=dimmer, newer=brighter
    # Use color pairs: 1=red, 2=green, 3=yellow, 4=blue, 5=magenta, 6=cyan, 7=white
    max_gen = max(gen, 1)

    # Draw crystal cells
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            if val > 0:
                # Color based on age (when it was attached)
                age_frac = val / max_gen if max_gen > 0 else 0.0
                # Older cells: cool colors (blue/cyan), newer: warm (yellow/white)
                if age_frac < 0.2:
                    cp = 4  # blue (oldest)
                    attr_extra = curses.A_DIM
                elif age_frac < 0.4:
                    cp = 6  # cyan
                    attr_extra = curses.A_DIM
                elif age_frac < 0.6:
                    cp = 2  # green
                    attr_extra = 0
                elif age_frac < 0.8:
                    cp = 3  # yellow
                    attr_extra = 0
                else:
                    cp = 7  # white (newest)
                    attr_extra = curses.A_BOLD

                # Character based on density of neighbors
                neighbors = 0
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] > 0:
                        neighbors += 1
                if neighbors >= 3:
                    ch = "█"
                elif neighbors >= 2:
                    ch = "▓"
                elif neighbors >= 1:
                    ch = "▒"
                else:
                    ch = "░"

                try:
                    self.stdscr.addstr(1 + r, c * 2, ch + " ",
                                       curses.color_pair(cp) | attr_extra)
                except curses.error:
                    pass

    # Draw walkers (dim dots)
    for w in self.dla_walkers:
        wr, wc = w[0], w[1]
        if 0 <= wr < view_rows and 0 <= wc < view_cols:
            try:
                self.stdscr.addstr(1 + wr, wc * 2, "· ",
                                   curses.color_pair(1) | curses.A_DIM)
            except curses.error:
                pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        info = (f" Gen {gen}  |  crystal={self.dla_crystal_count}"
                f"  |  walkers={len(self.dla_walkers)}/{self.dla_num_walkers}"
                f"  |  stick={self.dla_stickiness:.1f}"
                f"  |  radius={self.dla_max_radius:.0f}"
                f"  |  steps/f={self.dla_steps_per_frame}")
        try:
            self.stdscr.addstr(status_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [s/S]=sticky+/- [w/W]=walkers+/- [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Abelian Sandpile — Mode P
# ══════════════════════════════════════════════════════════════════════

SANDPILE_PRESETS = [
    # (name, description, drop_mode, drop_amount, initial_pile, steps_per_frame)
    ("Single Tower", "Drop grains one at a time onto center — classic fractal", "center", 1, 0, 1),
    ("Big Pile", "Start with a tall pile in the center and let it collapse", "center", 0, 10000, 10),
    ("Random Rain", "Grains drop at random locations continuously", "random", 1, 0, 1),
    ("Four Corners", "Simultaneous piles in four corners", "corners", 1, 0, 1),
    ("Diamond Seed", "Start with grains arranged in a diamond", "diamond", 1, 0, 1),
    ("Checkerboard", "Start with alternating 3-grain cells", "checkerboard", 0, 0, 5),
    ("Max Stable", "Fill grid with 3 grains everywhere, then perturb center", "max_stable", 0, 0, 5),
    ("Identity Element", "The sandpile identity — unique fractal from 2·max minus topple(2·max)", "identity", 0, 0, 10),
    ("Random Fill", "Random grain counts (0-3) everywhere, then perturb center", "random_fill", 0, 0, 5),
]

# Grain count -> (character, color_pair)
SANDPILE_CHARS = {
    0: (" ", 0),
    1: ("░░", 4),   # 1 grain — blue
    2: ("▒▒", 2),   # 2 grains — green
    3: ("▓▓", 3),   # 3 grains — yellow
}
# ≥4 shown during topple as bright red
SANDPILE_OVERFLOW_CHAR = ("██", 1)




def register(App):
    """Register dla mode methods on the App class."""
    App._enter_dla_mode = _enter_dla_mode
    App._exit_dla_mode = _exit_dla_mode
    App._dla_init = _dla_init
    App._dla_spawn_walkers = _dla_spawn_walkers
    App._dla_step = _dla_step
    App._dla_attach_symmetric = _dla_attach_symmetric
    App._handle_dla_menu_key = _handle_dla_menu_key
    App._handle_dla_key = _handle_dla_key
    App._draw_dla_menu = _draw_dla_menu
    App._draw_dla = _draw_dla

