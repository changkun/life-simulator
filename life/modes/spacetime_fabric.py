"""Mode: spacetime_fabric — general-relativistic cellular automaton.

The grid itself curves and warps in response to live cell density.
Dense clusters warp spacetime, causing gravitational lensing, time dilation,
geodesic motion, frame dragging, and gravitational waves.
"""
import curses
import math
import random
import time

# ══════════════════════════════════════════════════════════════════════
#  Spacetime Fabric — GR-coupled cellular automaton
# ══════════════════════════════════════════════════════════════════════

STF_PRESETS = [
    ("Binary Orbit",
     "Two dense clusters orbit each other, warping spacetime between them",
     0.6, 0.15, 0.8, 0.3),
    ("Gravitational Lens",
     "Central mass bends light — watch gliders curve around it",
     0.8, 0.20, 0.5, 0.2),
    ("Spacetime Soup",
     "Random soup with strong gravity — watch structure emerge from curvature",
     0.5, 0.10, 0.7, 0.4),
    ("Glider Geodesics",
     "Gliders follow curved paths around massive still lifes",
     0.7, 0.18, 0.6, 0.2),
    ("Frame Drag Vortex",
     "Rotating pulsar-like pattern drags neighboring cells into co-rotation",
     0.6, 0.12, 0.9, 0.5),
    ("Gravitational Waves",
     "Collapsing structures emit ripples that distort distant regions",
     0.5, 0.15, 0.7, 0.6),
]

# Glider (SE direction)
_GLIDER = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
# Block (still life)
_BLOCK = [(0, 0), (0, 1), (1, 0), (1, 1)]
# Blinker
_BLINKER = [(0, 0), (0, 1), (0, 2)]
# Pulsar-like rotator (simplified)
_ROTATOR = [
    (0, 1), (0, 2), (0, 3),
    (1, 0), (2, 0), (3, 0),
    (1, 4), (2, 4), (3, 4),
    (4, 1), (4, 2), (4, 3),
]


def _enter_spacetime_mode(self):
    """Enter Spacetime Fabric — show preset menu."""
    self.spacetime_menu = True
    self.spacetime_menu_sel = 0
    self._flash("Spacetime Fabric — select a configuration")


def _exit_spacetime_mode(self):
    """Exit Spacetime Fabric mode."""
    self.spacetime_mode = False
    self.spacetime_menu = False
    self.spacetime_running = False
    self._flash("Spacetime Fabric mode OFF")


def _spacetime_init(self, preset_idx: int):
    """Initialize the GR-coupled CA simulation."""
    name, _desc, gravity_str, lens_str, drag_str, wave_str = STF_PRESETS[preset_idx]
    self.spacetime_preset_name = name
    self.spacetime_preset_idx = preset_idx
    self.spacetime_gravity = gravity_str      # strength of gravitational pull
    self.spacetime_lensing = lens_str         # visual lensing strength
    self.spacetime_drag = drag_str            # frame dragging coefficient
    self.spacetime_wave_str = wave_str        # gravitational wave amplitude
    self.spacetime_generation = 0
    self.spacetime_running = False
    self.spacetime_viz = 0  # 0=fabric, 1=curvature, 2=time dilation, 3=CA only
    self.spacetime_cursor_r = 0
    self.spacetime_cursor_c = 0
    self.spacetime_show_metric = True
    self.spacetime_ca_interval = 2

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(10, (max_x - 1) // 2)
    self.spacetime_rows = rows
    self.spacetime_cols = cols

    # CA grid: 0=dead, 1=alive
    self.spacetime_cells = [[0] * cols for _ in range(rows)]
    # Cell age
    self.spacetime_age = [[0] * cols for _ in range(rows)]

    # Metric tensor field: curvature at each point (scalar approximation)
    # Positive = mass present, causes attraction
    self.spacetime_curvature = [[0.0] * cols for _ in range(rows)]
    # Time dilation factor: 1.0 = normal, <1.0 = slower near mass
    self.spacetime_dilation = [[1.0] * cols for _ in range(rows)]
    # Gravitational wave field (perturbation to metric)
    self.spacetime_gwave = [[0.0] * cols for _ in range(rows)]
    self.spacetime_gwave_vel = [[0.0] * cols for _ in range(rows)]
    # Angular momentum field for frame dragging
    self.spacetime_angular = [[0.0] * cols for _ in range(rows)]
    # Tick accumulator: cells update when accumulator >= 1.0
    self.spacetime_tick_acc = [[0.0] * cols for _ in range(rows)]
    # Mass density (smoothed from cell pattern)
    self.spacetime_mass = [[0.0] * cols for _ in range(rows)]
    # Previous mass for detecting sudden changes (gravitational waves)
    self.spacetime_prev_mass = [[0.0] * cols for _ in range(rows)]

    # Seed initial pattern
    _spacetime_seed(self, preset_idx)

    self.spacetime_menu = False
    self.spacetime_mode = True
    self._flash(f"Spacetime Fabric: {name} — Space to start")


def _spacetime_seed(self, preset_idx: int):
    """Seed initial CA patterns based on preset."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    cells = self.spacetime_cells

    if preset_idx == 0:  # Binary Orbit — two dense clusters
        # Cluster 1 (block of random cells)
        cr1, cc1 = rows // 3, cols // 3
        cr2, cc2 = 2 * rows // 3, 2 * cols // 3
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                r1, c1 = (cr1 + dr) % rows, (cc1 + dc) % cols
                r2, c2 = (cr2 + dr) % rows, (cc2 + dc) % cols
                if random.random() < 0.7:
                    cells[r1][c1] = 1
                if random.random() < 0.7:
                    cells[r2][c2] = 1

    elif preset_idx == 1:  # Gravitational Lens — central mass + gliders
        # Dense central block
        cr, cc = rows // 2, cols // 2
        for dr in range(-4, 5):
            for dc in range(-4, 5):
                r2, c2 = (cr + dr) % rows, (cc + dc) % cols
                if abs(dr) + abs(dc) <= 5:
                    cells[r2][c2] = 1
        # Gliders approaching from left
        for i in range(4):
            sr = rows // 4 + i * (rows // 5)
            sc = 3
            for dr, dc in _GLIDER:
                r2, c2 = (sr + dr) % rows, (sc + dc) % cols
                cells[r2][c2] = 1

    elif preset_idx == 2:  # Spacetime Soup
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.18:
                    cells[r][c] = 1

    elif preset_idx == 3:  # Glider Geodesics — still lifes + gliders
        # Place blocks as massive objects
        positions = [(rows // 4, cols // 4), (rows // 4, 3 * cols // 4),
                     (3 * rows // 4, cols // 4), (3 * rows // 4, 3 * cols // 4),
                     (rows // 2, cols // 2)]
        for pr, pc in positions:
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    r2, c2 = (pr + dr) % rows, (pc + dc) % cols
                    cells[r2][c2] = 1
        # Launch gliders from edges
        for i in range(6):
            sr = rows // 6 + i * (rows // 7)
            for dr, dc in _GLIDER:
                r2, c2 = (sr + dr) % rows, (3 + dc) % cols
                cells[r2][c2] = 1

    elif preset_idx == 4:  # Frame Drag Vortex
        cr, cc = rows // 2, cols // 2
        for dr, dc in _ROTATOR:
            r2, c2 = (cr + dr - 2) % rows, (cc + dc - 2) % cols
            cells[r2][c2] = 1
        # Surrounding loose cells
        for _ in range(30):
            r2 = (cr + random.randint(-8, 8)) % rows
            c2 = (cc + random.randint(-8, 8)) % cols
            cells[r2][c2] = 1

    elif preset_idx == 5:  # Gravitational Waves
        # Several dense clusters that will collapse
        for _ in range(5):
            cr = random.randint(rows // 4, 3 * rows // 4)
            cc = random.randint(cols // 4, 3 * cols // 4)
            for dr in range(-3, 4):
                for dc in range(-3, 4):
                    r2, c2 = (cr + dr) % rows, (cc + dc) % cols
                    if random.random() < 0.6:
                        cells[r2][c2] = 1


def _spacetime_compute_mass(self):
    """Compute smoothed mass density from cell pattern using Gaussian blur."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    cells = self.spacetime_cells
    mass = self.spacetime_mass

    # Save previous mass for gravitational wave detection
    prev = self.spacetime_prev_mass
    for r in range(rows):
        for c in range(cols):
            prev[r][c] = mass[r][c]

    # Reset mass
    for r in range(rows):
        for c in range(cols):
            mass[r][c] = 0.0

    # Accumulate mass with Gaussian-like kernel (radius 5)
    # Use a simple box blur approximation for speed
    radius = 4
    for r in range(rows):
        for c in range(cols):
            if not cells[r][c]:
                continue
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    dist_sq = dr * dr + dc * dc
                    if dist_sq > radius * radius:
                        continue
                    weight = 1.0 / (1.0 + dist_sq)
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    mass[nr][nc] += weight


def _spacetime_compute_curvature(self):
    """Compute spacetime curvature from mass density (Poisson equation approx)."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    mass = self.spacetime_mass
    curv = self.spacetime_curvature
    gravity = self.spacetime_gravity

    # Curvature is proportional to mass density
    max_mass = 0.001
    for r in range(rows):
        for c in range(cols):
            if mass[r][c] > max_mass:
                max_mass = mass[r][c]

    for r in range(rows):
        for c in range(cols):
            curv[r][c] = (mass[r][c] / max_mass) * gravity


def _spacetime_compute_dilation(self):
    """Compute time dilation from curvature (Schwarzschild-like)."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    curv = self.spacetime_curvature
    dil = self.spacetime_dilation

    for r in range(rows):
        for c in range(cols):
            # Time runs slower near massive objects
            # dilation = sqrt(1 - 2*phi) where phi is gravitational potential
            phi = curv[r][c]
            dil[r][c] = max(0.1, math.sqrt(max(0.01, 1.0 - 1.5 * phi)))


def _spacetime_compute_angular(self):
    """Compute angular momentum field for frame dragging."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    cells = self.spacetime_cells
    angular = self.spacetime_angular
    drag = self.spacetime_drag

    # Detect rotation by looking at asymmetric neighbor patterns
    for r in range(rows):
        for c in range(cols):
            angular[r][c] = 0.0

    # Compute local angular momentum from cell pattern
    for r in range(rows):
        for c in range(cols):
            if not cells[r][c]:
                continue
            # Cross product of position relative to local center of mass
            # with the cell's "implied velocity" from neighbor asymmetry
            n_up = cells[(r - 1) % rows][c]
            n_down = cells[(r + 1) % rows][c]
            n_left = cells[r][(c - 1) % cols]
            n_right = cells[r][(c + 1) % cols]
            # Angular momentum ~ cross product of gradient
            ang = (n_right - n_left) * 0.5 - (n_down - n_up) * 0.5
            # Spread angular momentum with falloff
            radius = 3
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    dist_sq = dr * dr + dc * dc
                    if dist_sq > radius * radius or dist_sq == 0:
                        continue
                    weight = drag / (1.0 + dist_sq)
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    angular[nr][nc] += ang * weight


def _spacetime_gwave_step(self):
    """Propagate gravitational waves (2D wave equation on the metric)."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    gw = self.spacetime_gwave
    gw_vel = self.spacetime_gwave_vel
    mass = self.spacetime_mass
    prev_mass = self.spacetime_prev_mass
    wave_str = self.spacetime_wave_str

    damping = 0.97
    c_sq = 0.2  # wave speed squared

    new_gw = [[0.0] * cols for _ in range(rows)]
    new_vel = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            # Laplacian of gwave field
            lap = (gw[(r + 1) % rows][c] + gw[(r - 1) % rows][c]
                   + gw[r][(c + 1) % cols] + gw[r][(c - 1) % cols]
                   - 4.0 * gw[r][c])

            # Source: sudden mass changes emit waves
            dm = mass[r][c] - prev_mass[r][c]
            source = dm * wave_str * 0.5

            new_vel[r][c] = (gw_vel[r][c] + c_sq * lap + source) * damping
            new_gw[r][c] = gw[r][c] + new_vel[r][c]

    self.spacetime_gwave = new_gw
    self.spacetime_gwave_vel = new_vel


def _spacetime_geodesic_displacement(self, r, c):
    """Compute geodesic displacement for a cell at (r, c).

    Cells move along geodesics: they accelerate toward regions of
    higher curvature (gravitational attraction).
    """
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    curv = self.spacetime_curvature
    angular = self.spacetime_angular
    gw = self.spacetime_gwave
    gravity = self.spacetime_gravity

    # Gradient of curvature (gravitational force)
    dc_dr = (curv[(r + 1) % rows][c] - curv[(r - 1) % rows][c]) * 0.5
    dc_dc = (curv[r][(c + 1) % cols] - curv[r][(c - 1) % cols]) * 0.5

    # Gravitational pull toward higher curvature
    dr_grav = dc_dr * gravity * 3.0
    dc_grav = dc_dc * gravity * 3.0

    # Frame dragging: angular momentum causes tangential displacement
    ang = angular[r][c]
    dr_drag = -ang * 0.5  # tangential = perpendicular to radial
    dc_drag = ang * 0.5

    # Gravitational wave perturbation
    gw_grad_r = (gw[(r + 1) % rows][c] - gw[(r - 1) % rows][c]) * 0.5
    gw_grad_c = (gw[r][(c + 1) % cols] - gw[r][(c - 1) % cols]) * 0.5
    dr_wave = gw_grad_r * 0.3
    dc_wave = gw_grad_c * 0.3

    return dr_grav + dr_drag + dr_wave, dc_grav + dc_drag + dc_wave


def _spacetime_ca_step(self):
    """Apply Game of Life with time dilation.

    Cells near massive regions tick slower — they only update when their
    tick accumulator reaches 1.0.
    """
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    cells = self.spacetime_cells
    age = self.spacetime_age
    dil = self.spacetime_dilation
    acc = self.spacetime_tick_acc

    new_cells = [[0] * cols for _ in range(rows)]
    new_age = [[0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            # Accumulate time — dilation < 1 means slower ticking
            acc[r][c] += dil[r][c]

            if acc[r][c] >= 1.0:
                acc[r][c] -= 1.0
                # Normal GoL update
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = (r + dr) % rows
                        nc = (c + dc) % cols
                        if cells[nr][nc]:
                            n += 1
                alive = cells[r][c]
                if alive:
                    if n == 2 or n == 3:
                        new_cells[r][c] = 1
                        new_age[r][c] = age[r][c] + 1
                else:
                    if n == 3:
                        new_cells[r][c] = 1
                        new_age[r][c] = 1
            else:
                # Cell doesn't tick this step — keep current state
                new_cells[r][c] = cells[r][c]
                new_age[r][c] = age[r][c]

    self.spacetime_cells = new_cells
    self.spacetime_age = new_age


def _spacetime_advect(self):
    """Move cells along geodesics (gravitational motion)."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    cells = self.spacetime_cells
    age = self.spacetime_age

    new_cells = [[0] * cols for _ in range(rows)]
    new_age = [[0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            if not cells[r][c]:
                continue
            dr, dc = _spacetime_geodesic_displacement(self, r, c)
            nr = (r + int(round(dr))) % rows
            nc = (c + int(round(dc))) % cols
            if new_cells[nr][nc] == 0:
                new_cells[nr][nc] = 1
                new_age[nr][nc] = age[r][c]
            else:
                # Collision — stay if possible
                if new_cells[r][c] == 0:
                    new_cells[r][c] = 1
                    new_age[r][c] = age[r][c]

    self.spacetime_cells = new_cells
    self.spacetime_age = new_age


def _spacetime_step(self):
    """One combined step of the spacetime simulation."""
    gen = self.spacetime_generation

    # 1. Compute mass density from cells
    _spacetime_compute_mass(self)

    # 2. Derive curvature, dilation, angular momentum
    _spacetime_compute_curvature(self)
    _spacetime_compute_dilation(self)
    _spacetime_compute_angular(self)

    # 3. Propagate gravitational waves
    _spacetime_gwave_step(self)

    # 4. Geodesic advection (move cells along curved spacetime)
    _spacetime_advect(self)

    # 5. CA update with time dilation
    if gen % self.spacetime_ca_interval == 0:
        _spacetime_ca_step(self)

    self.spacetime_generation += 1


def _spacetime_count_population(self):
    """Count live cells."""
    total = 0
    for row in self.spacetime_cells:
        for c in row:
            if c:
                total += 1
    return total


# ── Key handling ──────────────────────────────────────────────────────

def _handle_spacetime_menu_key(self, key: int) -> bool:
    """Handle input in preset selection menu."""
    n = len(STF_PRESETS)
    if key in (ord('j'), curses.KEY_DOWN):
        self.spacetime_menu_sel = (self.spacetime_menu_sel + 1) % n
    elif key in (ord('k'), curses.KEY_UP):
        self.spacetime_menu_sel = (self.spacetime_menu_sel - 1) % n
    elif key in (ord('\n'), ord('\r')):
        _spacetime_init(self, self.spacetime_menu_sel)
    elif key in (ord('q'), 27):
        self.spacetime_menu = False
        self._flash("Spacetime Fabric cancelled")
    return True


def _handle_spacetime_key(self, key: int) -> bool:
    """Handle input in active simulation."""
    rows = self.spacetime_rows
    cols = self.spacetime_cols

    if key == ord(' '):
        self.spacetime_running = not self.spacetime_running
    elif key in (ord('n'), ord('.')):
        _spacetime_step(self)
    elif key == ord('v'):
        self.spacetime_viz = (self.spacetime_viz + 1) % 4
        names = ["Fabric", "Curvature", "Time Dilation", "CA Only"]
        self._flash(f"Viz: {names[self.spacetime_viz]}")
    elif key == ord('m'):
        self.spacetime_show_metric = not self.spacetime_show_metric
    elif key == curses.KEY_UP or key == ord('w'):
        self.spacetime_cursor_r = (self.spacetime_cursor_r - 1) % rows
    elif key == curses.KEY_DOWN or key == ord('s'):
        self.spacetime_cursor_r = (self.spacetime_cursor_r + 1) % rows
    elif key == curses.KEY_LEFT or key == ord('a'):
        self.spacetime_cursor_c = (self.spacetime_cursor_c - 1) % cols
    elif key == curses.KEY_RIGHT or key == ord('d'):
        self.spacetime_cursor_c = (self.spacetime_cursor_c + 1) % cols
    elif key in (ord('\n'), ord('\r'), ord('e')):
        cr, cc = self.spacetime_cursor_r, self.spacetime_cursor_c
        self.spacetime_cells[cr][cc] = 1 - self.spacetime_cells[cr][cc]
        if self.spacetime_cells[cr][cc]:
            self.spacetime_age[cr][cc] = 1
    elif key == ord('g') or key == ord('G'):
        delta = 0.05 if key == ord('g') else -0.05
        self.spacetime_gravity = max(0.1, min(2.0, self.spacetime_gravity + delta))
        self._flash(f"Gravity: {self.spacetime_gravity:.2f}")
    elif key == ord('l') or key == ord('L'):
        delta = 0.02 if key == ord('l') else -0.02
        self.spacetime_lensing = max(0.0, min(1.0, self.spacetime_lensing + delta))
        self._flash(f"Lensing: {self.spacetime_lensing:.2f}")
    elif key == ord('f') or key == ord('F'):
        delta = 0.05 if key == ord('f') else -0.05
        self.spacetime_drag = max(0.0, min(2.0, self.spacetime_drag + delta))
        self._flash(f"Frame drag: {self.spacetime_drag:.2f}")
    elif key == ord('c') or key == ord('C'):
        delta = 1 if key == ord('c') else -1
        self.spacetime_ca_interval = max(1, min(10, self.spacetime_ca_interval + delta))
        self._flash(f"CA interval: every {self.spacetime_ca_interval} steps")
    elif key == ord('r'):
        _spacetime_init(self, self.spacetime_preset_idx)
    elif key == ord('R'):
        self.spacetime_mode = False
        self.spacetime_running = False
        self.spacetime_menu = True
        self.spacetime_menu_sel = 0
    elif key in (ord('q'), 27):
        _exit_spacetime_mode(self)
    return True


# ── Drawing ───────────────────────────────────────────────────────────

def _draw_spacetime_menu(self, max_y: int, max_x: int):
    """Draw preset selection menu."""
    self.stdscr.erase()
    title = "── Spacetime Fabric ── General-Relativistic Cellular Automaton ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Grid geometry warps in response to mass · Time dilation · Geodesic motion · Gravitational waves"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc, grav, lens, drag, wave) in enumerate(STF_PRESETS):
        y = 4 + i * 3
        if y >= max_y - 3:
            break
        line = f"  {name}"
        params = f"    gravity={grav:.2f}  lensing={lens:.2f}  drag={drag:.2f}  waves={wave:.2f}"
        detail = f"    {desc}"
        attr = curses.color_pair(6)
        if i == self.spacetime_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            self.stdscr.addstr(y + 1, 2, detail[:max_x - 4], curses.color_pair(6) | curses.A_DIM)
            self.stdscr.addstr(y + 2, 2, params[:max_x - 4], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def _draw_spacetime(self, max_y: int, max_x: int):
    """Draw the spacetime fabric simulation."""
    self.stdscr.erase()
    rows = self.spacetime_rows
    cols = self.spacetime_cols
    cells = self.spacetime_cells
    cell_age = self.spacetime_age
    curv = self.spacetime_curvature
    dil = self.spacetime_dilation
    gw = self.spacetime_gwave
    angular = self.spacetime_angular
    viz = self.spacetime_viz

    state = "▶ RUNNING" if self.spacetime_running else "⏸ PAUSED"
    pop = _spacetime_count_population(self)
    viz_names = ["Fabric", "Curvature", "Time Dilation", "CA Only"]

    title = (f" Spacetime Fabric: {self.spacetime_preset_name}  |  gen {self.spacetime_generation}"
             f"  |  pop {pop}  |  G={self.spacetime_gravity:.2f}"
             f"  |  {viz_names[viz]}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)
    cursor_r = self.spacetime_cursor_r
    cursor_c = self.spacetime_cursor_c

    # Find max values for normalization
    max_curv = 0.001
    max_gw = 0.001
    for r in range(view_rows):
        for c in range(view_cols):
            if curv[r][c] > max_curv:
                max_curv = curv[r][c]
            if abs(gw[r][c]) > max_gw:
                max_gw = abs(gw[r][c])

    # Fabric distortion characters (represent curvature visually)
    fabric_chars = [' ', '·', '∙', '•', '●', '⬤']
    # Gravitational lensing displacement chars
    lens_chars = {
        (1, 0): '→', (-1, 0): '←', (0, -1): '↑', (0, 1): '↓',
        (1, -1): '↗', (-1, -1): '↖', (1, 1): '↘', (-1, 1): '↙',
        (0, 0): '·',
    }

    tc_buf = getattr(self, 'tc_buf', None)
    use_tc = tc_buf is not None and tc_buf.enabled

    for r in range(view_rows):
        for c in range(view_cols):
            sx = c * 2
            sy = 1 + r
            is_cursor = (r == cursor_r and c == cursor_c)
            alive = cells[r][c]
            cv = curv[r][c]
            cv_norm = min(1.0, cv / max_curv) if max_curv > 0.001 else 0.0
            gw_val = gw[r][c]
            gw_norm = min(1.0, abs(gw_val) / max_gw) if max_gw > 0.001 else 0.0
            dl = dil[r][c]

            if viz == 0:  # Fabric view — cells + curvature + waves
                if alive:
                    a = cell_age[r][c]
                    if a > 20:
                        attr = curses.color_pair(1) | curses.A_BOLD  # red
                    elif a > 10:
                        attr = curses.color_pair(3)  # yellow
                    elif a > 3:
                        attr = curses.color_pair(2) | curses.A_BOLD  # green
                    else:
                        attr = curses.color_pair(5) | curses.A_BOLD  # cyan
                    ch = "██"
                    try:
                        self.stdscr.addstr(sy, sx, ch, attr)
                    except curses.error:
                        pass
                else:
                    # Show spacetime fabric distortion
                    combined = cv_norm + gw_norm * 0.5
                    combined = min(1.0, combined)
                    if combined > 0.02:
                        # Show gravitational lensing direction
                        if self.spacetime_show_metric and cv_norm > 0.1:
                            # Gradient of curvature = direction of pull
                            gr = (curv[(r + 1) % rows][c] - curv[(r - 1) % rows][c])
                            gc = (curv[r][(c + 1) % cols] - curv[r][(c - 1) % cols])
                            dx = 1 if gc > 0.01 else (-1 if gc < -0.01 else 0)
                            dy = 1 if gr > 0.01 else (-1 if gr < -0.01 else 0)
                            ch = lens_chars.get((dx, dy), '·')
                        else:
                            lvl = int(combined * 5)
                            lvl = min(5, max(0, lvl))
                            ch = fabric_chars[lvl]

                        # Color: purple/magenta for curvature, blue for waves
                        if gw_norm > cv_norm:
                            if gw_val > 0:
                                attr = curses.color_pair(4) | (curses.A_BOLD if gw_norm > 0.5 else 0)
                            else:
                                attr = curses.color_pair(5) | (curses.A_BOLD if gw_norm > 0.5 else 0)
                        else:
                            if cv_norm > 0.5:
                                attr = curses.color_pair(6) | curses.A_BOLD
                            elif cv_norm > 0.2:
                                attr = curses.color_pair(6)
                            else:
                                attr = curses.color_pair(6) | curses.A_DIM

                        try:
                            self.stdscr.addstr(sy, sx, ch + " ", attr)
                        except curses.error:
                            pass

            elif viz == 1:  # Curvature heatmap
                if alive:
                    try:
                        self.stdscr.addstr(sy, sx, "██", curses.color_pair(2) | curses.A_BOLD)
                    except curses.error:
                        pass
                elif cv_norm > 0.02:
                    lvl = int(cv_norm * 4)
                    lvl = min(4, max(0, lvl))
                    ch = [" ", "░", "▒", "▓", "█"][lvl]
                    if ch != " ":
                        if cv_norm > 0.6:
                            attr = curses.color_pair(1) | curses.A_BOLD
                        elif cv_norm > 0.3:
                            attr = curses.color_pair(3)
                        else:
                            attr = curses.color_pair(6) | curses.A_DIM
                        try:
                            self.stdscr.addstr(sy, sx, ch + " ", attr)
                        except curses.error:
                            pass

            elif viz == 2:  # Time dilation
                if alive:
                    # Color cells by how dilated their time is
                    if dl < 0.4:
                        attr = curses.color_pair(1) | curses.A_BOLD  # very slow = red
                    elif dl < 0.7:
                        attr = curses.color_pair(3)  # slow = yellow
                    elif dl < 0.9:
                        attr = curses.color_pair(2)  # slightly slow = green
                    else:
                        attr = curses.color_pair(5)  # normal = cyan
                    try:
                        self.stdscr.addstr(sy, sx, "██", attr)
                    except curses.error:
                        pass
                else:
                    # Show dilation field
                    dl_norm = 1.0 - dl  # invert: 0 = normal time, 1 = frozen
                    if dl_norm > 0.05:
                        lvl = int(dl_norm * 4)
                        lvl = min(4, max(0, lvl))
                        ch = [" ", "░", "▒", "▓", "█"][lvl]
                        if ch != " ":
                            if dl_norm > 0.5:
                                attr = curses.color_pair(1) | curses.A_BOLD
                            elif dl_norm > 0.25:
                                attr = curses.color_pair(3) | curses.A_DIM
                            else:
                                attr = curses.color_pair(6) | curses.A_DIM
                            try:
                                self.stdscr.addstr(sy, sx, ch + " ", attr)
                            except curses.error:
                                pass

            elif viz == 3:  # CA only
                if alive:
                    a = cell_age[r][c]
                    if a > 20:
                        attr = curses.color_pair(1) | curses.A_BOLD
                    elif a > 10:
                        attr = curses.color_pair(3)
                    elif a > 3:
                        attr = curses.color_pair(2) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(5) | curses.A_BOLD
                    try:
                        self.stdscr.addstr(sy, sx, "██", attr)
                    except curses.error:
                        pass

            # Cursor overlay
            if is_cursor:
                try:
                    self.stdscr.addstr(sy, sx, "[]", curses.color_pair(7) | curses.A_REVERSE)
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        avg_dil = 0.0
        cnt = 0
        for r in range(min(view_rows, rows)):
            for c in range(min(view_cols, cols)):
                avg_dil += dil[r][c]
                cnt += 1
        avg_dil /= max(1, cnt)
        info = (f" Gen {self.spacetime_generation}  |  grid={rows}×{cols}"
                f"  |  pop={pop}  |  avg dilation={avg_dil:.3f}"
                f"  |  CA every {self.spacetime_ca_interval} steps"
                f"  |  drag={self.spacetime_drag:.2f}"
                f"  |  cursor=({cursor_r},{cursor_c})")
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
            hint = " [Space]=play [n]=step [v]=viz [g/G]=gravity [l/L]=lens [f/F]=drag [↑↓←→]=move [Enter]=toggle [r]=reset [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _is_spacetime_auto_stepping(self) -> bool:
    """Return True if auto-stepping."""
    return self.spacetime_running


# ── Registration ──────────────────────────────────────────────────────

def register(App):
    """Register Spacetime Fabric mode methods on the App class."""
    App._enter_spacetime_mode = _enter_spacetime_mode
    App._exit_spacetime_mode = _exit_spacetime_mode
    App._spacetime_init = _spacetime_init
    App._spacetime_step = _spacetime_step
    App._handle_spacetime_menu_key = _handle_spacetime_menu_key
    App._handle_spacetime_key = _handle_spacetime_key
    App._draw_spacetime_menu = _draw_spacetime_menu
    App._draw_spacetime = _draw_spacetime
    App._is_spacetime_auto_stepping = _is_spacetime_auto_stepping
