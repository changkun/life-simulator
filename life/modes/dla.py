"""Diffusion-Limited Aggregation — random walkers stick to a growing crystal."""
import curses
import math
import random
import time

from life.constants import SPEEDS

DLA_PRESETS = [
    # (name, description, setup_key)
    ("Crystal Growth", "Single seed — classic dendritic fractal", "single"),
    ("Multi-Seed", "Several seeds grow and merge", "multi"),
    ("Snowflake", "6-fold symmetry from center seed", "snowflake"),
    ("Electrodeposition", "Bottom-edge cathode with downward drift", "electro"),
    ("Line Seed", "Horizontal line seed — forest-like growth", "line"),
    ("Ring Seed", "Circular ring seed — inward/outward growth", "ring"),
]

# Steps without any attachment after which the crystal counts as complete.
DLA_IDLE_LIMIT = 400
# A walker that has not attached after DLA_LIFE_PER_CELL moves per grid cell
# (at least DLA_MIN_LIFE moves) is retired and respawned.
DLA_LIFE_PER_CELL = 2.0
DLA_MIN_LIFE = 1000
# How often (in steps) to look for walkers sealed inside crystal pockets.
DLA_CULL_EVERY = 20
# Hexagonal neighbour offsets (odd-r layout: odd rows are drawn half a cell
# to the right), indexed by row parity.  Used by the six-fold preset so that
# 60-degree rotations map lattice cells onto lattice cells exactly.
DLA_HEX_NEIGHBORS = (
    ((0, -1), (0, 1), (-1, -1), (-1, 0), (1, -1), (1, 0)),   # even row
    ((0, -1), (0, 1), (-1, 0), (-1, 1), (1, 0), (1, 1)),     # odd row
)
# Consecutive failed ring spawns before falling back to random free cells,
# and the crystal-free margin required for such a fallback spawn.
DLA_RING_FAILS = 6
DLA_FALLBACK_CLEARANCE = 2
DLA_RING_CLEARANCE = 2

def _enter_dla_mode(self):
    """Show the Diffusion-Limited Aggregation preset menu."""
    self.dla_menu = True
    self.dla_menu_sel = 0
    self._flash("Diffusion-Limited Aggregation — select a configuration")



def _exit_dla_mode(self):
    """Leave Diffusion-Limited Aggregation mode and clear its state."""
    self.dla_mode = False
    self.dla_menu = False
    self.dla_running = False
    self.dla_grid = []
    self.dla_walkers = []
    self._flash("DLA mode OFF")



def _dla_init(self, preset_idx: int):
    """Start Diffusion-Limited Aggregation with the given preset."""
    name, _desc, setup_key = self.DLA_PRESETS[preset_idx]
    self.dla_preset_name = name
    self.dla_generation = 0
    self.dla_running = False
    self.dla_crystal_count = 0
    self.dla_bias_r = 0.0
    self.dla_bias_c = 0.0
    self.dla_symmetry = 1
    self.dla_stickiness = 1.0
    self.dla_complete = False
    self.dla_idle_steps = 0

    max_y, max_x = self.stdscr.getmaxyx()
    self.dla_rows = max(20, max_y - 3)
    self.dla_cols = max(20, (max_x - 1) // 2)
    rows, cols = self.dla_rows, self.dla_cols
    cr, cc = rows // 2, cols // 2

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
        # Every attachment is copied into up to 12 symmetric images, so far
        # fewer walkers give the same deposition rate; many more fill the
        # disc solid instead of growing thin arms.
        self.dla_num_walkers = 30
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

    # Seed-aware spawn geometry: the spawn region must enclose the seeds.
    if setup_key != "electro":
        seed_extent = max(
            (math.hypot(sr - cr, sc - cc) for sr, sc in self.dla_seeds),
            default=0.0)
        self.dla_max_radius = max(self.dla_max_radius, seed_extent)
    self.dla_reach = None
    self.dla_walker_born = {}

    # Spawn initial walkers
    self._dla_spawn_walkers()

    self.dla_menu = False
    self.dla_mode = True
    self._flash(f"DLA: {name} — Space to start")



def _dla_spawn_walkers(self):
    """Spawn walkers on a ring around the crystal.

    The ring is a circle while the crystal is small.  Once the circle hits
    the short side of the grid, only that axis is capped: the ring becomes an
    ellipse fitted to the grid, so the crystal can keep growing into the
    wide dimension of a rectangular grid.
    """
    rows, cols = self.dla_rows, self.dla_cols
    cr, cc = rows // 2, cols // 2
    # Spawn radius is a bit beyond the max crystal radius
    want_r = self.dla_max_radius + 10
    sym = self.dla_symmetry > 1
    if sym:
        # Six-fold symmetry needs an isotropic region.
        axis_r = axis_c = min(want_r, min(rows, cols) // 2 - 1)
    else:
        axis_r = min(want_r, rows // 2 - 1)
        axis_c = min(want_r, cols // 2 - 1)
    spawn_r = max(axis_r, axis_c)
    self.dla_spawn_radius = spawn_r
    grid = self.dla_grid
    reach = getattr(self, "dla_reach", None)
    if not (isinstance(reach, list) and len(reach) == rows
            and len(reach[0]) == cols):
        reach = None

    # Bounded attempts: the spawn region may be (nearly) full of crystal.
    attempts = 0
    ring_fails = 0
    max_attempts = 20 * max(1, self.dla_num_walkers)
    while len(self.dla_walkers) < self.dla_num_walkers and attempts < max_attempts:
        attempts += 1
        clearance = DLA_RING_CLEARANCE
        if ring_fails >= DLA_RING_FAILS and not (sym or self.dla_bias_r != 0.0):
            # The ring is (nearly) full of crystal: spawn at a random free
            # cell of the grid that is a few cells clear of the crystal, so
            # the open parts of the grid still get filled diffusively.
            wr = random.randint(0, rows - 1)
            wc = random.randint(0, cols - 1)
            clearance = DLA_FALLBACK_CLEARANCE
        elif not sym and self.dla_bias_r != 0.0:
            # Biased drift (e.g. electrodeposition): spawn from opposite side
            wr = random.randint(0, max(1, rows // 3))
            wc = random.randint(0, cols - 1)
        else:
            # General: spawn on a (possibly elliptical) ring around center
            angle = random.random() * 2 * math.pi
            scale = 0.8 + 0.4 * random.random()
            wr = cr + int(axis_r * scale * math.sin(angle))
            wc = cc + int(axis_c * scale * math.cos(angle))
        # Points that fall off the grid are rejected, not clamped: clamping
        # piles walkers onto the border line and grows a solid wall there.
        if not (0 <= wr < rows and 0 <= wc < cols):
            continue
        if grid[wr][wc] != 0:
            continue
        if reach is not None and not reach[wr][wc]:
            continue  # sealed inside a crystal pocket
        # Never spawn a walker touching the crystal: it would attach on
        # its first move, so once the crystal reaches the (grid-capped)
        # spawn ring the spawn itself would grow the crystal along the
        # ring instead of walkers diffusing in from outside.
        touching = False
        for ar in range(max(0, wr - clearance), min(rows, wr + clearance + 1)):
            row = grid[ar]
            for ac in range(max(0, wc - clearance), min(cols, wc + clearance + 1)):
                if row[ac] > 0:
                    touching = True
                    break
            if touching:
                break
        if touching:
            if clearance == DLA_RING_CLEARANCE:
                ring_fails += 1
        else:
            self.dla_walkers.append([wr, wc])
            ring_fails = 0



def _dla_reachable(self):
    """Flood-fill (8-connected) the free cells reachable from the grid edge.

    Returns a list of bytearrays (1 = a walker there can still wander out to
    the open space) or None when the whole border is crystal.
    """
    rows, cols = self.dla_rows, self.dla_cols
    grid = self.dla_grid
    reach = [bytearray(cols) for _ in range(rows)]
    stack = []
    for r in range(rows):
        for c in ((0, cols - 1) if 0 < r < rows - 1 else range(cols)):
            if grid[r][c] == 0 and not reach[r][c]:
                reach[r][c] = 1
                stack.append((r, c))
    if not stack:
        return None
    while stack:
        r, c = stack.pop()
        for nr in range(max(0, r - 1), min(rows, r + 2)):
            grow = grid[nr]
            rrow = reach[nr]
            for nc in range(max(0, c - 1), min(cols, c + 2)):
                if grow[nc] == 0 and not rrow[nc]:
                    rrow[nc] = 1
                    stack.append((nr, nc))
    return reach



def _dla_step(self):
    """Advance every walker by one move and attach those that touch the crystal."""
    if getattr(self, "dla_complete", False):
        return
    rows, cols = self.dla_rows, self.dla_cols
    grid = self.dla_grid
    cr, cc = rows // 2, cols // 2
    gen = self.dla_generation + 1
    kill_radius = self.dla_spawn_radius + 20

    new_walkers = []
    attached_any = False

    # Retire walkers that cannot attach: those sealed inside crystal pockets
    # (found by flood fill) and those that have wandered for too long.
    if gen % DLA_CULL_EVERY == 0 or not isinstance(
            getattr(self, "dla_reach", None), list):
        self.dla_reach = self._dla_reachable()
        reach = self.dla_reach
        if reach is not None:
            self.dla_walkers = [w for w in self.dla_walkers if reach[w[0]][w[1]]]
    hexlat = self.dla_symmetry == 6
    max_life = max(DLA_MIN_LIFE, DLA_LIFE_PER_CELL * rows * cols)
    born = getattr(self, "dla_walker_born", None)
    if not isinstance(born, dict):
        born = {}
    new_born = {}

    for w in self.dla_walkers:
        wr, wc = w[0], w[1]
        b = born.get(id(w), gen)
        if gen - b > max_life:
            continue  # lifetime exceeded: drop, respawn below
        new_born[id(w)] = b

        # Random walk with optional bias
        if hexlat:
            dr, dc = random.choice(DLA_HEX_NEIGHBORS[wr & 1])
        else:
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
        for adr, adc in (DLA_HEX_NEIGHBORS[nr & 1] if hexlat else
                         [(-1, 0), (1, 0), (0, -1), (0, 1),
                          (-1, -1), (-1, 1), (1, -1), (1, 1)]):
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
    self.dla_walker_born = {id(w): new_born[id(w)] for w in new_walkers
                            if id(w) in new_born}
    self.dla_generation = gen

    # Replenish walkers
    if attached_any or len(self.dla_walkers) < self.dla_num_walkers:
        self._dla_spawn_walkers()

    # Completion: the spawn ring is capped by the grid, so the crystal
    # eventually fills the reachable space and nothing attaches any more.
    if attached_any:
        self.dla_idle_steps = 0
    else:
        self.dla_idle_steps = getattr(self, "dla_idle_steps", 0) + 1
        if self.dla_idle_steps >= DLA_IDLE_LIMIT:
            self.dla_complete = True
            self.dla_running = False
            self._flash("Crystal complete — r=restart, R=menu")



def _dla_symmetric_images(self, r: int, c: int):
    """Return the distinct images of (r, c) under the preset's symmetry, itself first.

    Six-fold: the lattice is hexagonal (odd-r offset rows), so the six 60
    degree rotations and the mirror images are exact in cube coordinates --
    no rounding, hence no duplicate or stray cells.  Other fold counts rotate
    the offset in Euclidean space and round (grid cells are drawn two
    characters wide, i.e. square, so no aspect correction is needed).
    """
    cr, cc = self.dla_rows // 2, self.dla_cols // 2
    sym = self.dla_symmetry
    images = [(r, c)]
    seen = {(r, c)}

    def add(rr, rc):
        if (rr, rc) not in seen:
            seen.add((rr, rc))
            images.append((rr, rc))

    if sym == 6:
        # odd-r offset -> cube (x, y, z), relative to the centre cell
        cx = cc - (cr - (cr & 1)) // 2
        x = c - (r - (r & 1)) // 2 - cx
        z = r - cr
        y = -x - z
        for mirror in (False, True):
            px, py, pz = (x, z, y) if mirror else (x, y, z)
            for _ in range(6):
                rz = cr + pz
                rx = cx + px
                add(rz, rx + (rz - (rz & 1)) // 2)
                px, py, pz = -pz, -px, -py
    else:
        dr, dc = r - cr, c - cc
        for k in range(1, sym):
            angle = 2 * math.pi * k / sym
            add(int(round(cr + dr * math.cos(angle) - dc * math.sin(angle))),
                int(round(cc + dr * math.sin(angle) + dc * math.cos(angle))))
    return images



def _dla_attach_symmetric(self, r: int, c: int, gen: int):
    """Attach a crystal cell together with its symmetric images.

    The walker's own cell is always attached.  Images are deduplicated and
    only placed where they touch the existing crystal, so symmetric copies
    extend the arms instead of scattering detached cells.
    """
    rows, cols = self.dla_rows, self.dla_cols
    cr, cc = rows // 2, cols // 2
    grid = self.dla_grid

    for i, (rr, rc) in enumerate(self._dla_symmetric_images(r, c)):
        if not (0 <= rr < rows and 0 <= rc < cols) or grid[rr][rc] != 0:
            continue
        if i > 0:
            touching = False
            for ar in range(max(0, rr - 1), min(rows, rr + 2)):
                for ac in range(max(0, rc - 1), min(cols, rc + 2)):
                    if grid[ar][ac] > 0:
                        touching = True
                        break
                if touching:
                    break
            if not touching:
                continue
        grid[rr][rc] = gen
        self.dla_crystal_count += 1
        dist = math.sqrt((rr - cr) ** 2 + (rc - cc) ** 2)
        if dist > self.dla_max_radius:
            self.dla_max_radius = dist



def _handle_dla_menu_key(self, key: int) -> bool:
    """Handle keys in the preset menu."""
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
    """Handle keys while the simulation is active."""
    if key == ord(" "):
        if getattr(self, "dla_complete", False):
            self._flash("Crystal complete — r=restart, R=menu")
        else:
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
        # Finer steps below 100 (Snowflake runs with 30 walkers)
        step = 50 if self.dla_num_walkers >= 100 else 10
        delta = step if key == ord("w") else -step
        self.dla_num_walkers = max(10, min(2000, self.dla_num_walkers + delta))
        self._flash(f"Walkers: {self.dla_num_walkers}")
    elif key == ord("+") or key == ord("="):
        self.dla_steps_per_frame = min(50, self.dla_steps_per_frame + 2)
        self._flash(f"Steps/frame: {self.dla_steps_per_frame}")
    elif key == ord("-"):
        self.dla_steps_per_frame = max(1, self.dla_steps_per_frame - 2)
        self._flash(f"Steps/frame: {self.dla_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_dla_mode()
    else:
        return True
    return True



def _draw_dla_menu(self, max_y: int, max_x: int):
    """Draw the preset menu."""
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
    """Draw the crystal, walkers, status line and hint bar."""
    self.stdscr.erase()
    grid = self.dla_grid
    rows, cols = self.dla_rows, self.dla_cols
    state = "▶ RUNNING" if self.dla_running else "⏸ PAUSED"
    if getattr(self, "dla_complete", False):
        state = "■ COMPLETE"
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

    max_gen = max(gen, 1)

    hexlat = self.dla_symmetry == 6

    # Draw crystal cells
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            if val > 0:
                # Older cells are cool and dim, newer ones warm and bright.
                age_frac = val / max_gen
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

                # Glyph density follows the number of crystal neighbours.
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
                    self.stdscr.addstr(1 + r, c * 2 + (r & 1 if hexlat else 0), ch + " ",
                                       curses.color_pair(cp) | attr_extra)
                except curses.error:
                    pass

    # Walkers
    for w in self.dla_walkers:
        wr, wc = w[0], w[1]
        if 0 <= wr < view_rows and 0 <= wc < view_cols:
            try:
                self.stdscr.addstr(1 + wr, wc * 2 + (wr & 1 if hexlat else 0), "· ",
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
            hint = " [Space]=play [n]=step [s/S]=sticky+/- [w/W]=walkers+/- [+/-]=steps/frame [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register dla mode methods on the App class."""
    App.DLA_PRESETS = DLA_PRESETS
    App._enter_dla_mode = _enter_dla_mode
    App._exit_dla_mode = _exit_dla_mode
    App._dla_init = _dla_init
    App._dla_spawn_walkers = _dla_spawn_walkers
    App._dla_reachable = _dla_reachable
    App._dla_step = _dla_step
    App._dla_symmetric_images = _dla_symmetric_images
    App._dla_attach_symmetric = _dla_attach_symmetric
    App._handle_dla_menu_key = _handle_dla_menu_key
    App._handle_dla_key = _handle_dla_key
    App._draw_dla_menu = _draw_dla_menu
    App._draw_dla = _draw_dla

