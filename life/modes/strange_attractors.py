"""Mode: attractor — simulation mode for the life package."""
import curses
import math
import random
import time

ATTRACTOR_PRESETS = [
    # (name, description, attractor_type, params_dict)
    ("Lorenz — Classic Butterfly", "The iconic σ=10, ρ=28, β=8/3 chaotic attractor",
     "lorenz", {"sigma": 10.0, "rho": 28.0, "beta": 8.0 / 3.0}),
    ("Lorenz — High Rho", "More chaotic regime with ρ=99.96",
     "lorenz", {"sigma": 10.0, "rho": 99.96, "beta": 8.0 / 3.0}),
    ("Rössler — Spiral", "Gentle spiral with occasional folds",
     "rossler", {"a": 0.2, "b": 0.2, "c": 5.7}),
    ("Rössler — Funnel", "Wide funnel regime a=0.5",
     "rossler", {"a": 0.5, "b": 1.0, "c": 3.0}),
    ("Thomas — Cyclically Symmetric", "Smooth 3D helical chaos, b=0.208186",
     "thomas", {"b": 0.208186}),
    ("Aizawa — Torus Knot", "Toroidal attractor with complex structure",
     "aizawa", {"a": 0.95, "b": 0.7, "c": 0.6, "d": 3.5, "e": 0.25, "f": 0.1}),
    ("Halvorsen — Symmetric", "Three-fold rotational symmetry, a=1.89",
     "halvorsen", {"a": 1.89}),
    ("Chen — Double Scroll", "Similar to Lorenz with different topology",
     "chen", {"a": 35.0, "b": 3.0, "c": 28.0}),
]


def _enter_attractor_mode(self):
    """Enter Strange Attractor mode — show preset menu."""
    self.attractor_menu = True
    self.attractor_menu_sel = 0
    self._flash("Strange Attractors — select a system")



def _exit_attractor_mode(self):
    """Exit Strange Attractor mode."""
    self.attractor_mode = False
    self.attractor_menu = False
    self.attractor_running = False
    self.attractor_density = []
    self.attractor_trails = []
    self._flash("Strange Attractor mode OFF")



def _attractor_init(self, preset_idx: int):
    """Initialize the Strange Attractor with the given preset."""
    name, _desc, atype, params = self.ATTRACTOR_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.attractor_rows = rows
    self.attractor_cols = cols
    self.attractor_preset_name = name
    self.attractor_generation = 0
    self.attractor_steps_per_frame = 50
    self.attractor_type = atype
    self.attractor_params = dict(params)
    self.attractor_dt = 0.005
    self.attractor_angle_x = 0.3
    self.attractor_angle_z = 0.0
    self.attractor_zoom = 1.0
    self.attractor_max_density = 1.0

    # Clear density grid
    self.attractor_density = [[0.0] * cols for _ in range(rows)]

    # Initialize particles with small random offsets from an initial point
    n = self.attractor_num_particles
    self.attractor_trails = []

    if atype == "lorenz":
        for _ in range(n):
            self.attractor_trails.append((
                1.0 + random.gauss(0, 0.5),
                1.0 + random.gauss(0, 0.5),
                1.0 + random.gauss(0, 0.5),
            ))
    elif atype == "rossler":
        for _ in range(n):
            self.attractor_trails.append((
                random.gauss(0, 0.3),
                random.gauss(0, 0.3),
                random.gauss(0, 0.3),
            ))
    elif atype == "thomas":
        for _ in range(n):
            self.attractor_trails.append((
                random.gauss(1, 0.3),
                random.gauss(1, 0.3),
                random.gauss(1, 0.3),
            ))
    elif atype == "aizawa":
        for _ in range(n):
            self.attractor_trails.append((
                0.1 + random.gauss(0, 0.05),
                0.0 + random.gauss(0, 0.05),
                0.0 + random.gauss(0, 0.05),
            ))
    elif atype == "halvorsen":
        for _ in range(n):
            self.attractor_trails.append((
                -1.48 + random.gauss(0, 0.3),
                -1.51 + random.gauss(0, 0.3),
                2.04 + random.gauss(0, 0.3),
            ))
    elif atype == "chen":
        for _ in range(n):
            self.attractor_trails.append((
                -0.1 + random.gauss(0, 0.5),
                0.5 + random.gauss(0, 0.5),
                -0.6 + random.gauss(0, 0.5),
            ))

    # Warm up: run a few hundred steps to get particles onto the attractor
    for _ in range(300):
        self._attractor_step_no_density()

    self.attractor_mode = True
    self.attractor_menu = False
    self.attractor_running = False
    self._flash(f"Strange Attractor: {name} — Space to start")



def _attractor_ode(self, x: float, y: float, z: float) -> tuple:
    """Compute dx/dt, dy/dt, dz/dt for the current attractor type."""
    p = self.attractor_params
    atype = self.attractor_type
    if atype == "lorenz":
        sigma, rho, beta = p["sigma"], p["rho"], p["beta"]
        dx = sigma * (y - x)
        dy = x * (rho - z) - y
        dz = x * y - beta * z
    elif atype == "rossler":
        a, b, c = p["a"], p["b"], p["c"]
        dx = -y - z
        dy = x + a * y
        dz = b + z * (x - c)
    elif atype == "thomas":
        b_val = p["b"]
        dx = math.sin(y) - b_val * x
        dy = math.sin(z) - b_val * y
        dz = math.sin(x) - b_val * z
    elif atype == "aizawa":
        a, b, c, d, e, f = p["a"], p["b"], p["c"], p["d"], p["e"], p["f"]
        dx = (z - b) * x - d * y
        dy = d * x + (z - b) * y
        dz = c + a * z - z * z * z / 3.0 - (x * x + y * y) * (1.0 + e * z) + f * z * x * x * x
    elif atype == "halvorsen":
        a = p["a"]
        dx = -a * x - 4.0 * y - 4.0 * z - y * y
        dy = -a * y - 4.0 * z - 4.0 * x - z * z
        dz = -a * z - 4.0 * x - 4.0 * y - x * x
    elif atype == "chen":
        a, b, c = p["a"], p["b"], p["c"]
        dx = a * (y - x)
        dy = (c - a) * x - x * z + c * y
        dz = x * y - b * z
    else:
        dx = dy = dz = 0.0
    return dx, dy, dz



def _attractor_step_no_density(self):
    """Advance particles one step without accumulating density (for warm-up)."""
    dt = self.attractor_dt
    new_trails = []
    for x, y, z in self.attractor_trails:
        dx1, dy1, dz1 = self._attractor_ode(x, y, z)
        mx = x + 0.5 * dt * dx1
        my = y + 0.5 * dt * dy1
        mz = z + 0.5 * dt * dz1
        dx2, dy2, dz2 = self._attractor_ode(mx, my, mz)
        nx = x + dt * dx2
        ny = y + dt * dy2
        nz = z + dt * dz2
        # Clamp to avoid divergence
        lim = 500.0
        nx = max(-lim, min(lim, nx))
        ny = max(-lim, min(lim, ny))
        nz = max(-lim, min(lim, nz))
        new_trails.append((nx, ny, nz))
    self.attractor_trails = new_trails



def _attractor_step(self):
    """Advance particles one step and accumulate density on the grid."""
    dt = self.attractor_dt
    rows, cols = self.attractor_rows, self.attractor_cols
    density = self.attractor_density
    zoom = self.attractor_zoom
    ax = self.attractor_angle_x
    az = self.attractor_angle_z

    cos_ax = math.cos(ax)
    sin_ax = math.sin(ax)
    cos_az = math.cos(az)
    sin_az = math.sin(az)

    # Auto-scale: compute bounding box from current particles
    if self.attractor_trails:
        # Project all particles, find range
        pxs = []
        pys = []
        for x, y, z in self.attractor_trails:
            # Rotate around z-axis
            rx = x * cos_az - y * sin_az
            ry = x * sin_az + y * cos_az
            rz = z
            # Rotate around x-axis
            ry2 = ry * cos_ax - rz * sin_ax
            rz2 = ry * sin_ax + rz * cos_ax
            pxs.append(rx)
            pys.append(rz2)
        if pxs:
            min_px = min(pxs)
            max_px = max(pxs)
            min_py = min(pys)
            max_py = max(pys)
            range_x = max(max_px - min_px, 1.0)
            range_y = max(max_py - min_py, 1.0)
            cx = (min_px + max_px) * 0.5
            cy = (min_py + max_py) * 0.5
            scale = min(cols / range_x, rows / range_y) * 0.85 * zoom
        else:
            cx = cy = 0.0
            scale = 1.0
    else:
        cx = cy = 0.0
        scale = 1.0

    new_trails = []
    for x, y, z in self.attractor_trails:
        # RK2 integration
        dx1, dy1, dz1 = self._attractor_ode(x, y, z)
        mx = x + 0.5 * dt * dx1
        my = y + 0.5 * dt * dy1
        mz = z + 0.5 * dt * dz1
        dx2, dy2, dz2 = self._attractor_ode(mx, my, mz)
        nx = x + dt * dx2
        ny = y + dt * dy2
        nz = z + dt * dz2
        # Clamp
        lim = 500.0
        nx = max(-lim, min(lim, nx))
        ny = max(-lim, min(lim, ny))
        nz = max(-lim, min(lim, nz))
        new_trails.append((nx, ny, nz))

        # Project to 2D and accumulate density
        # Rotate around z-axis
        rx = nx * cos_az - ny * sin_az
        # ry = nx * sin_az + ny * cos_az (not needed for final x)
        ry_full = nx * sin_az + ny * cos_az
        rz = nz
        # Rotate around x-axis
        rz2 = ry_full * sin_ax + rz * cos_ax

        # Map to grid coordinates
        sc = int((rx - cx) * scale + cols * 0.5)
        sr = int((rz2 - cy) * scale + rows * 0.5)

        # Depth-based fade
        ry2 = ry_full * cos_ax - rz * sin_ax
        # We don't use ry2 for position, just for depth shading

        if 0 <= sr < rows and 0 <= sc < cols:
            density[sr][sc] += 1.0

    self.attractor_trails = new_trails
    self.attractor_generation += 1

    # Track max density for normalization (with decay)
    cur_max = 0.0
    for r in range(rows):
        for c in range(cols):
            if density[r][c] > cur_max:
                cur_max = density[r][c]
    if cur_max > self.attractor_max_density:
        self.attractor_max_density = cur_max
    else:
        self.attractor_max_density = max(1.0, self.attractor_max_density * 0.999)



def _handle_attractor_menu_key(self, key: int) -> bool:
    """Handle input in Strange Attractor preset menu."""
    presets = self.ATTRACTOR_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.attractor_menu_sel = (self.attractor_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.attractor_menu_sel = (self.attractor_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._attractor_init(self.attractor_menu_sel)
    elif key == ord("q") or key == 27:
        self.attractor_menu = False
        self._flash("Strange Attractor cancelled")
    return True



def _handle_attractor_key(self, key: int) -> bool:
    """Handle input in active Strange Attractor simulation."""
    if key == ord("q") or key == 27:
        self._exit_attractor_mode()
        return True
    if key == ord(" "):
        self.attractor_running = not self.attractor_running
        return True
    if key == ord("n") or key == ord("."):
        self._attractor_step()
        return True
    if key == ord("r"):
        # Reset: re-init current preset
        idx = next(
            (i for i, p in enumerate(self.ATTRACTOR_PRESETS) if p[0] == self.attractor_preset_name),
            0,
        )
        self._attractor_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.attractor_mode = False
        self.attractor_running = False
        self.attractor_menu = True
        self.attractor_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [10, 20, 50, 100, 200, 500]
        idx = choices.index(self.attractor_steps_per_frame) if self.attractor_steps_per_frame in choices else 2
        self.attractor_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.attractor_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [10, 20, 50, 100, 200, 500]
        idx = choices.index(self.attractor_steps_per_frame) if self.attractor_steps_per_frame in choices else 2
        self.attractor_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.attractor_steps_per_frame} steps/frame")
        return True
    # Rotation controls
    if key == curses.KEY_LEFT or key == ord("h"):
        self.attractor_angle_z -= 0.1
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        self.attractor_angle_z += 0.1
        return True
    if key == curses.KEY_UP or key == ord("k"):
        self.attractor_angle_x -= 0.1
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.attractor_angle_x += 0.1
        return True
    # Zoom
    if key == ord("z"):
        self.attractor_zoom = min(5.0, self.attractor_zoom * 1.15)
        self._flash(f"Zoom: {self.attractor_zoom:.2f}x")
        return True
    if key == ord("Z"):
        self.attractor_zoom = max(0.2, self.attractor_zoom / 1.15)
        self._flash(f"Zoom: {self.attractor_zoom:.2f}x")
        return True
    # dt adjustment
    if key == ord("d"):
        self.attractor_dt = max(0.0005, self.attractor_dt * 0.8)
        self._flash(f"dt={self.attractor_dt:.4f}")
        return True
    if key == ord("D"):
        self.attractor_dt = min(0.05, self.attractor_dt * 1.25)
        self._flash(f"dt={self.attractor_dt:.4f}")
        return True
    # Clear density (fresh heatmap)
    if key == ord("c"):
        rows, cols = self.attractor_rows, self.attractor_cols
        self.attractor_density = [[0.0] * cols for _ in range(rows)]
        self.attractor_max_density = 1.0
        self._flash("Density cleared")
        return True
    # Parameter tuning: 1/2 adjust first param, 3/4 adjust second
    if key == ord("1") or key == ord("2"):
        p = self.attractor_params
        delta = 1 if key == ord("2") else -1
        atype = self.attractor_type
        if atype == "lorenz":
            p["sigma"] = max(1.0, p["sigma"] + delta * 0.5)
            self._flash(f"σ={p['sigma']:.1f}")
        elif atype == "rossler":
            p["a"] = max(0.01, p["a"] + delta * 0.02)
            self._flash(f"a={p['a']:.3f}")
        elif atype == "thomas":
            p["b"] = max(0.01, p["b"] + delta * 0.01)
            self._flash(f"b={p['b']:.4f}")
        elif atype == "halvorsen":
            p["a"] = max(0.1, p["a"] + delta * 0.05)
            self._flash(f"a={p['a']:.3f}")
        elif atype == "chen":
            p["a"] = max(1.0, p["a"] + delta * 1.0)
            self._flash(f"a={p['a']:.1f}")
        elif atype == "aizawa":
            p["a"] = max(0.1, p["a"] + delta * 0.05)
            self._flash(f"a={p['a']:.3f}")
        return True
    if key == ord("3") or key == ord("4"):
        p = self.attractor_params
        delta = 1 if key == ord("4") else -1
        atype = self.attractor_type
        if atype == "lorenz":
            p["rho"] = max(0.5, p["rho"] + delta * 1.0)
            self._flash(f"ρ={p['rho']:.1f}")
        elif atype == "rossler":
            p["c"] = max(0.5, p["c"] + delta * 0.2)
            self._flash(f"c={p['c']:.1f}")
        elif atype == "chen":
            p["c"] = max(1.0, p["c"] + delta * 1.0)
            self._flash(f"c={p['c']:.1f}")
        elif atype == "aizawa":
            p["d"] = max(0.5, p["d"] + delta * 0.1)
            self._flash(f"d={p['d']:.2f}")
        return True
    return True



def _draw_attractor_menu(self, max_y: int, max_x: int):
    """Draw the Strange Attractor preset selection menu."""
    self.stdscr.erase()
    title = "── Strange Attractors ── Select System ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, atype, _params) in enumerate(self.ATTRACTOR_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.attractor_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.attractor_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:30s}  {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], attr)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_attractor(self, max_y: int, max_x: int):
    """Draw the active Strange Attractor simulation as a density heatmap."""
    self.stdscr.erase()
    rows, cols = self.attractor_rows, self.attractor_cols
    state = "▶ RUNNING" if self.attractor_running else "⏸ PAUSED"

    # Build param string
    p = self.attractor_params
    pstr = " ".join(f"{k}={v:.2f}" for k, v in p.items())

    title = (f" 🦋 {self.attractor_preset_name}  |  step {self.attractor_generation}"
             f"  |  {pstr}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)
    density = self.attractor_density
    norm = max(self.attractor_max_density, 1.0)

    # Use logarithmic scaling for better contrast
    log_norm = math.log1p(norm)

    for r in range(view_rows):
        sy = 1 + r
        for c in range(view_cols):
            d = density[r][c]
            if d < 0.5:
                continue
            # Log-scale normalization
            val = math.log1p(d) / log_norm if log_norm > 0 else 0.0
            val = min(val, 1.0)

            sx = c * 2

            if val > 0.8:
                ch = "██"
                attr = curses.color_pair(3) | curses.A_BOLD  # bright yellow
            elif val > 0.55:
                ch = "▓▓"
                attr = curses.color_pair(1) | curses.A_BOLD  # bright red
            elif val > 0.35:
                ch = "▒▒"
                attr = curses.color_pair(5) | curses.A_BOLD  # magenta
            elif val > 0.18:
                ch = "░░"
                attr = curses.color_pair(4) | curses.A_BOLD  # blue
            elif val > 0.08:
                ch = "··"
                attr = curses.color_pair(4)  # dim blue
            else:
                ch = "  "
                attr = curses.color_pair(4) | curses.A_DIM
                continue

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [arrows]=rotate [z/Z]=zoom [1-4]=params [d/D]=dt [c]=clear [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Quantum Cellular Automaton (Quantum Walk) — Mode ^
# ══════════════════════════════════════════════════════════════════════

QWALK_PRESETS = [
    # (name, description, coin_type, init_type, boundary)
    ("Hadamard — Single Source",
     "Classic Hadamard coin, single central walker, periodic boundary",
     "hadamard", "single", "periodic"),
    ("Hadamard — Absorbing Edges",
     "Hadamard coin walk with absorbing boundary conditions",
     "hadamard", "single", "absorbing"),
    ("Grover — Diffusion Coin",
     "Grover diffusion operator as coin — stronger interference",
     "grover", "single", "periodic"),
    ("DFT — Fourier Coin",
     "Discrete Fourier Transform coin — asymmetric spreading",
     "dft", "single", "periodic"),
    ("Hadamard — Gaussian Packet",
     "Gaussian wave packet initial state — localized spreading",
     "hadamard", "gaussian", "periodic"),
    ("Grover — Dual Source",
     "Two walkers that interfere with each other",
     "grover", "dual", "periodic"),
    ("Hadamard — Decoherent",
     "Hadamard coin with decoherence — classical-like diffusion",
     "hadamard", "single_decoherent", "periodic"),
    ("DFT — Gaussian Absorbing",
     "Fourier coin, Gaussian packet, absorbing edges",
     "dft", "gaussian", "absorbing"),
]




def register(App):
    """Register attractor mode methods on the App class."""
    App.ATTRACTOR_PRESETS = ATTRACTOR_PRESETS
    App._enter_attractor_mode = _enter_attractor_mode
    App._exit_attractor_mode = _exit_attractor_mode
    App._attractor_init = _attractor_init
    App._attractor_ode = _attractor_ode
    App._attractor_step_no_density = _attractor_step_no_density
    App._attractor_step = _attractor_step
    App._handle_attractor_menu_key = _handle_attractor_menu_key
    App._handle_attractor_key = _handle_attractor_key
    App._draw_attractor_menu = _draw_attractor_menu
    App._draw_attractor = _draw_attractor

