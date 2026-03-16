"""Mode: ferrofluid — Ferrofluid Dynamics.

Simulates magnetic nanoparticle suspension (ferrofluid) that self-organises
into spikes, labyrinthine stripe patterns, and hexagonal lattices under
user-controlled magnetic fields.

Physics modelled:
  1. Magnetic body force: F_m = μ₀ M·∇H  (particles attracted to field maxima)
  2. Surface tension: smoothing / diffusion that opposes sharp gradients
  3. Gravity: downward pull on fluid height
  4. Rosensweig instability: when B exceeds a critical threshold, the flat
     surface becomes unstable and erupts into a hexagonal spike array
  5. Chain formation: under uniform fields, particles align into columns
  6. Labyrinthine patterns: thin-film ferrofluid in perpendicular field forms
     meandering stripe domains via competing dipolar and surface tension forces

Visualization:
  - Top-down view: height field rendered as density glyphs with magnetic
    colouring (dark = trough, bright = spike tip)
  - Side view: cross-section profile of the fluid surface
  - Colour encodes local magnetisation intensity
"""
import curses
import math
import random
import time

# ── Presets ──────────────────────────────────────────────────────────────────

FERROFLUID_PRESETS = [
    ("Rosensweig Spikes",
     "Normal-field instability — hexagonal spike array erupts above critical field",
     "rosensweig"),
    ("Labyrinthine Maze",
     "Thin-film ferrofluid in perpendicular field — meandering stripe domains",
     "labyrinthine"),
    ("Chain Columns",
     "Uniform vertical field aligns particles into columnar chains",
     "chains"),
    ("Field-Responsive Art",
     "Sweep a gradient field across the fluid — watch patterns morph in real time",
     "art"),
    ("Hedgehog Spikes",
     "Strong point-source field — radial spike array around a magnetic pole",
     "hedgehog"),
    ("Dual Magnets",
     "Two competing field sources — interference pattern with complex domain walls",
     "dual"),
]

# ── Glyphs & colours ────────────────────────────────────────────────────────

_HEIGHT_CHARS = ["  ", "· ", "░░", "▒▒", "▓▓", "██"]
_SPIKE_CHARS  = ["  ", "· ", "∧∧", "⋀⋀", "▲▲", "⏶⏶"]


def _ferro_height_color(h: float, mag: float) -> int:
    """Map fluid height + magnetisation to curses color pair."""
    if h > 0.7:
        return 1 if mag > 0.5 else 3   # red/yellow spike tips
    elif h > 0.4:
        return 3 if mag > 0.3 else 6   # yellow/white mid
    elif h > 0.15:
        return 6                         # white low
    else:
        return 4                         # blue/dark trough


def _ferro_mag_color(mag: float) -> int:
    """Map magnetisation intensity to colour."""
    if mag > 0.7:
        return 1   # red (strong)
    elif mag > 0.4:
        return 3   # yellow
    elif mag > 0.15:
        return 6   # white
    else:
        return 4   # blue (weak)


def _neighbors4(r, c, rows, cols):
    """Yield 4 von Neumann neighbours (toroidal)."""
    yield (r - 1) % rows, c
    yield (r + 1) % rows, c
    yield r, (c - 1) % cols
    yield r, (c + 1) % cols


def _neighbors8(r, c, rows, cols):
    """Yield 8 Moore neighbours (toroidal)."""
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            yield (r + dr) % rows, (c + dc) % cols


# ── Enter / Exit ────────────────────────────────────────────────────────────

def _enter_ferrofluid_mode(self):
    """Enter Ferrofluid Dynamics mode — show preset menu."""
    self.ferrofluid_menu = True
    self.ferrofluid_menu_sel = 0
    self._flash("Ferrofluid Dynamics — select a configuration")


def _exit_ferrofluid_mode(self):
    """Exit Ferrofluid Dynamics mode."""
    self.ferrofluid_mode = False
    self.ferrofluid_menu = False
    self.ferrofluid_running = False
    self._flash("Ferrofluid Dynamics OFF")


# ── Initialisation ──────────────────────────────────────────────────────────

def _ferrofluid_init(self, preset_idx: int):
    """Set up the ferrofluid simulation for the chosen preset."""
    name, _desc, kind = FERROFLUID_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(16, max_y - 4)
    cols = max(16, (max_x - 1) // 2)
    self.ferrofluid_rows = rows
    self.ferrofluid_cols = cols
    self.ferrofluid_preset_name = name
    self.ferrofluid_preset_kind = kind
    self.ferrofluid_generation = 0
    self.ferrofluid_view = "top"          # top | side | magnetisation
    self.ferrofluid_steps_per_frame = 2

    # Physics parameters
    self.ferrofluid_B = 0.0               # applied field strength
    self.ferrofluid_B_max = 2.0           # max field
    self.ferrofluid_B_crit = 0.45         # critical field for Rosensweig
    self.ferrofluid_gamma = 0.08          # surface tension coefficient
    self.ferrofluid_gravity = 0.03        # gravity strength
    self.ferrofluid_mu = 0.6              # magnetic susceptibility
    self.ferrofluid_damping = 0.97        # velocity damping
    self.ferrofluid_field_angle = 0.0     # field direction (0 = perpendicular/up)
    self.ferrofluid_field_gx = 0.0        # field gradient x component
    self.ferrofluid_field_gy = 0.0        # field gradient y component

    # Per-cell state: height h, velocity v, magnetisation M
    h = [[0.0] * cols for _ in range(rows)]
    v = [[0.0] * cols for _ in range(rows)]
    M = [[0.0] * cols for _ in range(rows)]  # local magnetisation magnitude

    if kind == "rosensweig":
        self.ferrofluid_B = 0.6
        self.ferrofluid_gamma = 0.08
        self.ferrofluid_gravity = 0.03
        _init_flat_with_noise(h, rows, cols, base=0.3, noise=0.02)
    elif kind == "labyrinthine":
        self.ferrofluid_B = 0.5
        self.ferrofluid_gamma = 0.12
        self.ferrofluid_gravity = 0.01
        self.ferrofluid_mu = 0.8
        _init_thin_film(h, rows, cols)
    elif kind == "chains":
        self.ferrofluid_B = 0.7
        self.ferrofluid_gamma = 0.05
        self.ferrofluid_gravity = 0.04
        _init_random_droplets(h, rows, cols)
    elif kind == "art":
        self.ferrofluid_B = 0.3
        self.ferrofluid_gamma = 0.06
        self.ferrofluid_gravity = 0.02
        self.ferrofluid_field_gx = 0.01
        _init_flat_with_noise(h, rows, cols, base=0.25, noise=0.05)
    elif kind == "hedgehog":
        self.ferrofluid_B = 0.8
        self.ferrofluid_gamma = 0.07
        self.ferrofluid_gravity = 0.025
        _init_flat_with_noise(h, rows, cols, base=0.35, noise=0.01)
    elif kind == "dual":
        self.ferrofluid_B = 0.65
        self.ferrofluid_gamma = 0.09
        self.ferrofluid_gravity = 0.02
        _init_flat_with_noise(h, rows, cols, base=0.3, noise=0.03)

    self.ferrofluid_h = h
    self.ferrofluid_v = v
    self.ferrofluid_M = M
    self.ferrofluid_mode = True
    self.ferrofluid_menu = False
    self.ferrofluid_running = False
    self._flash(f"Ferrofluid: {name} — Space to start, B={self.ferrofluid_B:.2f}")


# ── Preset placement helpers ────────────────────────────────────────────────

def _init_flat_with_noise(h, rows, cols, base=0.3, noise=0.02):
    """Flat fluid surface with small random perturbation."""
    for r in range(rows):
        for c in range(cols):
            h[r][c] = base + random.uniform(-noise, noise)


def _init_thin_film(h, rows, cols):
    """Thin film with stripy initial perturbation for labyrinthine onset."""
    for r in range(rows):
        for c in range(cols):
            # Seed with faint stripes + noise to trigger labyrinthine instability
            stripe = 0.03 * math.sin(2.0 * math.pi * c / max(cols, 1) * 3)
            stripe += 0.02 * math.sin(2.0 * math.pi * r / max(rows, 1) * 2.7)
            h[r][c] = 0.25 + stripe + random.uniform(-0.01, 0.01)


def _init_random_droplets(h, rows, cols):
    """Random droplets that will coalesce into chains under field."""
    for r in range(rows):
        for c in range(cols):
            h[r][c] = 0.05
    # Place ~30 droplets
    n_drops = max(20, rows * cols // 50)
    for _ in range(n_drops):
        cr, cc = random.randint(0, rows - 1), random.randint(0, cols - 1)
        rad = random.randint(1, 3)
        amp = random.uniform(0.3, 0.6)
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                d2 = dr * dr + dc * dc
                if d2 <= rad * rad:
                    rr = (cr + dr) % rows
                    rc = (cc + dc) % cols
                    h[rr][rc] = max(h[rr][rc], amp * (1.0 - d2 / (rad * rad + 1)))


# ── Magnetic field computation ──────────────────────────────────────────────

def _compute_field(self, r, c):
    """Compute the applied magnetic field magnitude and gradient at (r, c).

    Returns (B_local, dBdr, dBdc) — field magnitude and its spatial gradient.
    """
    rows, cols = self.ferrofluid_rows, self.ferrofluid_cols
    kind = self.ferrofluid_preset_kind
    B0 = self.ferrofluid_B
    cr, cc = rows / 2.0, cols / 2.0

    if kind == "hedgehog":
        # Point source at centre
        dr = r - cr
        dc = c - cc
        dist = math.sqrt(dr * dr + dc * dc) + 1.0
        B_local = B0 * 8.0 / (dist + 3.0)
        # Gradient points radially outward from source (particles attracted inward)
        grad_r = -B0 * 8.0 * dr / ((dist + 3.0) ** 2 * dist + 0.01)
        grad_c = -B0 * 8.0 * dc / ((dist + 3.0) ** 2 * dist + 0.01)
        return B_local, grad_r, grad_c

    elif kind == "dual":
        # Two sources at 1/3 and 2/3 of width
        b_total = 0.0
        gr_total = 0.0
        gc_total = 0.0
        for src_c in (cols / 3.0, 2 * cols / 3.0):
            dr = r - cr
            dc = c - src_c
            dist = math.sqrt(dr * dr + dc * dc) + 1.0
            b = B0 * 6.0 / (dist + 3.0)
            b_total += b
            gr_total += -B0 * 6.0 * dr / ((dist + 3.0) ** 2 * dist + 0.01)
            gc_total += -B0 * 6.0 * dc / ((dist + 3.0) ** 2 * dist + 0.01)
        return b_total, gr_total, gc_total

    elif kind == "art":
        # Sweeping gradient field
        t = self.ferrofluid_generation * 0.02
        gx = self.ferrofluid_field_gx
        gy = self.ferrofluid_field_gy
        sweep = 0.3 * math.sin(t) * (c - cc) / max(cols, 1)
        sweep += 0.2 * math.cos(t * 0.7) * (r - cr) / max(rows, 1)
        B_local = B0 + sweep + gx * (c - cc) + gy * (r - cr)
        B_local = max(0.0, B_local)
        grad_r = 0.2 * math.cos(t * 0.7) / max(rows, 1) + gy
        grad_c = 0.3 * math.sin(t) / max(cols, 1) + gx
        return B_local, grad_r * B0, grad_c * B0

    else:
        # Uniform field (Rosensweig, labyrinthine, chains)
        # Small gradient from field_gx/gy for interactivity
        gx = self.ferrofluid_field_gx
        gy = self.ferrofluid_field_gy
        B_local = B0 + gx * (c - cc) + gy * (r - cr)
        B_local = max(0.0, B_local)
        return B_local, gy * B0, gx * B0


# ── Physics step ────────────────────────────────────────────────────────────

def _ferrofluid_step(self):
    """Advance the ferrofluid simulation by one timestep.

    The dynamics combine:
      1. Magnetic body force: particles move toward field maxima
         F_m ~ μ₀ χ H (∂H/∂x) — the Kelvin force on paramagnetic fluid
      2. Rosensweig instability: above critical B, height perturbations grow
         because magnetic pressure at spike tips exceeds surface tension restoring force
      3. Surface tension: Laplacian diffusion smooths the height field
      4. Gravity: pulls fluid down, opposing spike growth
      5. Dipolar interaction: neighbouring high-h cells attract (chain formation)
      6. Velocity damping: viscous loss
    """
    rows, cols = self.ferrofluid_rows, self.ferrofluid_cols
    h = self.ferrofluid_h
    v = self.ferrofluid_v
    M = self.ferrofluid_M
    gamma = self.ferrofluid_gamma
    grav = self.ferrofluid_gravity
    mu = self.ferrofluid_mu
    damping = self.ferrofluid_damping
    B_crit = self.ferrofluid_B_crit
    kind = self.ferrofluid_preset_kind

    new_v = [[0.0] * cols for _ in range(rows)]
    new_h = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            hi = h[r][c]

            # Compute local magnetic field and gradient
            B_local, dBdr, dBdc = _compute_field(self, r, c)

            # Update local magnetisation: M = χ * H (linear susceptibility)
            M[r][c] = mu * B_local

            # -- Magnetic body force --
            # Kelvin force: F ~ M * grad(B)
            # For Rosensweig: instability when B > B_crit, taller regions
            # experience stronger field → positive feedback
            mag_force = mu * hi * (B_local - B_crit)
            if B_local > B_crit:
                # Above critical field: height perturbations amplified
                mag_force += 0.5 * mu * (B_local - B_crit) ** 2 * hi

            # Gradient force (for non-uniform fields)
            # Drives fluid toward field maxima
            grad_force = mu * hi * math.sqrt(dBdr * dBdr + dBdc * dBdc) * 0.3

            # -- Surface tension (Laplacian of h) --
            laplacian = 0.0
            n_count = 0
            for nr, nc in _neighbors4(r, c, rows, cols):
                laplacian += h[nr][nc]
                n_count += 1
            laplacian = laplacian / n_count - hi

            surface_force = gamma * laplacian

            # -- Gravity --
            grav_force = -grav * hi

            # -- Dipolar chaining force --
            # Neighbouring cells with similar high magnetisation attract
            chain_force = 0.0
            if kind in ("chains", "rosensweig", "hedgehog"):
                for nr, nc in _neighbors4(r, c, rows, cols):
                    chain_force += 0.02 * mu * B_local * (h[nr][nc] - hi)

            # -- Total force → acceleration → velocity --
            total_force = mag_force + grad_force + surface_force + grav_force + chain_force
            new_vi = v[r][c] * damping + total_force
            new_vi = max(-0.5, min(0.5, new_vi))  # clamp velocity
            new_v[r][c] = new_vi

            # -- Update height --
            new_hi = hi + new_vi
            new_h[r][c] = max(0.0, min(1.0, new_hi))

    # -- Labyrinthine: add long-range dipolar repulsion for stripe formation --
    if kind == "labyrinthine":
        B0 = self.ferrofluid_B
        if B0 > 0.1:
            for r in range(rows):
                for c in range(cols):
                    repulsion = 0.0
                    hi = new_h[r][c]
                    for nr, nc in _neighbors8(r, c, rows, cols):
                        repulsion += (hi - new_h[nr][nc])
                    # Dipolar repulsion favours alternating high/low domains
                    new_v[r][c] += 0.015 * mu * B0 * repulsion

    # -- Chain alignment pass: encourage vertical/horizontal alignment --
    if kind == "chains":
        B0 = self.ferrofluid_B
        fa = self.ferrofluid_field_angle
        for r in range(rows):
            for c in range(cols):
                hi = new_h[r][c]
                if hi < 0.1:
                    continue
                # Align along field direction (default: vertical columns)
                cos_a = math.cos(fa)
                sin_a = math.sin(fa)
                # Neighbours along field direction attract more
                r_up = (r - 1) % rows
                r_dn = (r + 1) % rows
                c_lt = (c - 1) % cols
                c_rt = (c + 1) % cols
                align_v = (new_h[r_up][c] + new_h[r_dn][c]) * abs(cos_a)
                align_h = (new_h[r][c_lt] + new_h[r][c_rt]) * abs(sin_a)
                new_v[r][c] += 0.01 * mu * B0 * (align_v + align_h - 2 * hi) * 0.5

    self.ferrofluid_h = new_h
    self.ferrofluid_v = new_v
    self.ferrofluid_generation += 1


# ── Interaction ─────────────────────────────────────────────────────────────

def _ferrofluid_perturb(self, r, c):
    """Drop a blob of ferrofluid at (r, c)."""
    rows, cols = self.ferrofluid_rows, self.ferrofluid_cols
    if r < 0 or r >= rows or c < 0 or c >= cols:
        return
    rad = 3
    for dr in range(-rad, rad + 1):
        for dc in range(-rad, rad + 1):
            d2 = dr * dr + dc * dc
            if d2 <= rad * rad:
                rr = (r + dr) % rows
                rc = (c + dc) % cols
                add = 0.4 * (1.0 - d2 / (rad * rad + 1))
                self.ferrofluid_h[rr][rc] = min(1.0, self.ferrofluid_h[rr][rc] + add)
    self._flash(f"Added fluid at ({r},{c})")


# ── Key handlers ────────────────────────────────────────────────────────────

def _handle_ferrofluid_menu_key(self, key: int) -> bool:
    """Handle input in Ferrofluid preset menu."""
    n = len(FERROFLUID_PRESETS)
    if key in (curses.KEY_UP, ord("k")):
        self.ferrofluid_menu_sel = (self.ferrofluid_menu_sel - 1) % n
    elif key in (curses.KEY_DOWN, ord("j")):
        self.ferrofluid_menu_sel = (self.ferrofluid_menu_sel + 1) % n
    elif key in (10, 13, curses.KEY_ENTER):
        self._ferrofluid_init(self.ferrofluid_menu_sel)
    elif key in (27, ord("q")):
        self.ferrofluid_menu = False
        self._flash("Ferrofluid cancelled")
    return True


def _handle_ferrofluid_key(self, key: int) -> bool:
    """Handle input in active Ferrofluid simulation."""
    if key == ord(" "):
        self.ferrofluid_running = not self.ferrofluid_running
        self._flash("Running" if self.ferrofluid_running else "Paused")
    elif key in (ord("n"), ord(".")):
        self.ferrofluid_running = False
        self._ferrofluid_step()
    elif key == ord("+") or key == ord("="):
        self.ferrofluid_steps_per_frame = min(20, self.ferrofluid_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.ferrofluid_steps_per_frame}")
    elif key == ord("-"):
        self.ferrofluid_steps_per_frame = max(1, self.ferrofluid_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.ferrofluid_steps_per_frame}")
    elif key == ord("v"):
        views = ["top", "side", "magnetisation"]
        idx = views.index(self.ferrofluid_view) if self.ferrofluid_view in views else 0
        self.ferrofluid_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.ferrofluid_view}")
    elif key == ord("b"):
        self.ferrofluid_B = min(self.ferrofluid_B_max, self.ferrofluid_B + 0.05)
        self._flash(f"Field B: {self.ferrofluid_B:.2f}")
    elif key == ord("B"):
        self.ferrofluid_B = max(0.0, self.ferrofluid_B - 0.05)
        self._flash(f"Field B: {self.ferrofluid_B:.2f}")
    elif key == ord("g"):
        self.ferrofluid_gamma = min(0.5, self.ferrofluid_gamma + 0.01)
        self._flash(f"Surface tension γ: {self.ferrofluid_gamma:.2f}")
    elif key == ord("G"):
        self.ferrofluid_gamma = max(0.0, self.ferrofluid_gamma - 0.01)
        self._flash(f"Surface tension γ: {self.ferrofluid_gamma:.2f}")
    elif key == ord("a"):
        self.ferrofluid_field_angle += 0.15
        self._flash(f"Field angle: {math.degrees(self.ferrofluid_field_angle):.0f}°")
    elif key == ord("A"):
        self.ferrofluid_field_angle -= 0.15
        self._flash(f"Field angle: {math.degrees(self.ferrofluid_field_angle):.0f}°")
    elif key == ord("f"):
        self.ferrofluid_field_gx = min(0.05, self.ferrofluid_field_gx + 0.005)
        self._flash(f"Field gradient X: {self.ferrofluid_field_gx:.3f}")
    elif key == ord("F"):
        self.ferrofluid_field_gx = max(-0.05, self.ferrofluid_field_gx - 0.005)
        self._flash(f"Field gradient X: {self.ferrofluid_field_gx:.3f}")
    elif key == ord("r"):
        self._ferrofluid_init(self.ferrofluid_menu_sel)
    elif key in (ord("R"), ord("m")):
        self.ferrofluid_mode = False
        self.ferrofluid_running = False
        self.ferrofluid_menu = True
        self.ferrofluid_menu_sel = 0
        self._flash("Ferrofluid — select a configuration")
    elif key == curses.KEY_MOUSE:
        try:
            _, mx, my, _, bstate = curses.getmouse()
            if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
                gr = my - 1
                gc = mx // 2
                self._ferrofluid_perturb(gr, gc)
        except curses.error:
            pass
    elif key in (27, ord("q")):
        self._exit_ferrofluid_mode()
    else:
        return True
    return True


# ── Drawing ─────────────────────────────────────────────────────────────────

def _draw_ferrofluid_menu(self, max_y: int, max_x: int):
    """Draw the Ferrofluid preset selection menu."""
    self.stdscr.erase()
    title = "── Ferrofluid Dynamics ── Select Configuration ──"
    try:
        self.stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(6) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(FERROFLUID_PRESETS):
        y = 2 + i * 2
        if y >= max_y - 2:
            break
        marker = "▶ " if i == self.ferrofluid_menu_sel else "  "
        attr = curses.A_BOLD if i == self.ferrofluid_menu_sel else 0
        try:
            self.stdscr.addstr(y, 2, f"{marker}{name}", curses.color_pair(3) | attr)
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate [Enter]=select [q]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_ferrofluid(self, max_y: int, max_x: int):
    """Draw the active Ferrofluid simulation."""
    self.stdscr.erase()
    rows, cols = self.ferrofluid_rows, self.ferrofluid_cols
    h = self.ferrofluid_h
    M = self.ferrofluid_M
    B = self.ferrofluid_B

    # Compute stats
    max_h = 0.0
    avg_h = 0.0
    spike_count = 0
    for r in range(rows):
        for c in range(cols):
            val = h[r][c]
            avg_h += val
            if val > max_h:
                max_h = val
            if val > 0.6:
                spike_count += 1
    avg_h /= max(1, rows * cols)

    # Title bar
    state = "▶ RUNNING" if self.ferrofluid_running else "⏸ PAUSED"
    B_status = "SUPERCRITICAL" if B > self.ferrofluid_B_crit else "subcritical"
    title = (f" Ferrofluid: {self.ferrofluid_preset_name}  │  "
             f"T={self.ferrofluid_generation}  │  {state}  │  "
             f"B={B:.2f} ({B_status})  │  "
             f"Spikes: {spike_count}")
    title = title[:max_x - 1]
    try:
        tc = curses.color_pair(1 if B > self.ferrofluid_B_crit else 4)
        self.stdscr.addstr(0, 0, title, tc | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    if self.ferrofluid_view == "side":
        _draw_ferrofluid_side(self, max_y, max_x, view_rows, view_cols)
    elif self.ferrofluid_view == "magnetisation":
        _draw_ferrofluid_mag(self, max_y, max_x, view_rows, view_cols)
    else:
        _draw_ferrofluid_top(self, max_y, max_x, view_rows, view_cols)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" h̄={avg_h:.3f}  │  max={max_h:.3f}  │  "
                f"γ={self.ferrofluid_gamma:.2f}  │  "
                f"g={self.ferrofluid_gravity:.2f}  │  "
                f"View: {self.ferrofluid_view}")
        info = info[:max_x - 1]
        try:
            self.stdscr.addstr(info_y, 0, info, curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [b/B]=field [g/G]=tension [a/A]=angle [f/F]=gradient [click]=drop [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_ferrofluid_top(self, max_y, max_x, view_rows, view_cols):
    """Top-down view: height field as density glyphs."""
    h = self.ferrofluid_h
    M = self.ferrofluid_M
    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 2:
            break
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            val = h[r][c]
            mag = M[r][c] if r < len(M) and c < len(M[0]) else 0.0
            if val < 0.02:
                continue
            # Choose glyph based on height
            idx = int(min(val, 1.0) * (len(_HEIGHT_CHARS) - 1))
            # Use spike chars for tall features
            if val > 0.65:
                ch = _SPIKE_CHARS[min(idx, len(_SPIKE_CHARS) - 1)]
            else:
                ch = _HEIGHT_CHARS[idx]
            cp = _ferro_height_color(val, mag)
            bold = curses.A_BOLD if val > 0.5 else 0
            try:
                self.stdscr.addstr(sy, sx, ch, curses.color_pair(cp) | bold)
            except curses.error:
                pass


def _draw_ferrofluid_side(self, max_y, max_x, view_rows, view_cols):
    """Side view: cross-section profile through the middle row."""
    h = self.ferrofluid_h
    mid_row = self.ferrofluid_rows // 2
    profile_height = max_y - 4
    if profile_height < 4:
        return

    # Draw a cross-section at the middle row
    for c in range(view_cols):
        sx = c * 2
        if sx + 1 >= max_x:
            break
        val = h[mid_row][c]
        col_height = int(val * profile_height)
        for dy in range(col_height):
            sy = max_y - 3 - dy
            if sy < 1 or sy >= max_y - 1:
                continue
            # Gradient: base is darker, tip is brighter
            frac = dy / max(col_height, 1)
            if frac > 0.7:
                cp = 1   # red tip
                ch = "██"
            elif frac > 0.4:
                cp = 3   # yellow mid
                ch = "▓▓"
            elif frac > 0.15:
                cp = 6   # white
                ch = "▒▒"
            else:
                cp = 4   # blue base
                ch = "░░"
            bold = curses.A_BOLD if frac > 0.6 else 0
            try:
                self.stdscr.addstr(sy, sx, ch, curses.color_pair(cp) | bold)
            except curses.error:
                pass

    # Draw baseline
    baseline_y = max_y - 3
    if 0 < baseline_y < max_y:
        for sx in range(0, min(view_cols * 2, max_x - 1), 2):
            try:
                self.stdscr.addstr(baseline_y, sx, "──", curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    # Label
    try:
        self.stdscr.addstr(1, 1, f"Side view — cross-section at row {mid_row}",
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def _draw_ferrofluid_mag(self, max_y, max_x, view_rows, view_cols):
    """Magnetisation view: show local M intensity."""
    M = self.ferrofluid_M
    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 2:
            break
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            mag = M[r][c] if r < len(M) and c < len(M[0]) else 0.0
            if mag < 0.02:
                continue
            norm = min(mag / max(self.ferrofluid_B * self.ferrofluid_mu + 0.01, 0.1), 1.0)
            idx = int(norm * (len(_HEIGHT_CHARS) - 1))
            ch = _HEIGHT_CHARS[idx]
            cp = _ferro_mag_color(norm)
            bold = curses.A_BOLD if norm > 0.5 else 0
            try:
                self.stdscr.addstr(sy, sx, ch, curses.color_pair(cp) | bold)
            except curses.error:
                pass


# ── Registration ────────────────────────────────────────────────────────────

def register(App):
    """Register Ferrofluid Dynamics mode methods on the App class."""
    App.FERROFLUID_PRESETS = FERROFLUID_PRESETS
    App._enter_ferrofluid_mode = _enter_ferrofluid_mode
    App._exit_ferrofluid_mode = _exit_ferrofluid_mode
    App._ferrofluid_init = _ferrofluid_init
    App._ferrofluid_step = _ferrofluid_step
    App._ferrofluid_perturb = _ferrofluid_perturb
    App._compute_field = _compute_field
    App._handle_ferrofluid_menu_key = _handle_ferrofluid_menu_key
    App._handle_ferrofluid_key = _handle_ferrofluid_key
    App._draw_ferrofluid_menu = _draw_ferrofluid_menu
    App._draw_ferrofluid = _draw_ferrofluid
