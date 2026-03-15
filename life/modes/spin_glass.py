"""Mode: spin_glass — continuous-spin magnetism with frustrated interactions and glassy dynamics."""
import curses
import math
import random
import time

# ── Arrow characters for 8 spin directions ──
SPIN_ARROWS = ["→", "↗", "↑", "↖", "←", "↙", "↓", "↘"]

# ── Presets ──
SPINGLASS_PRESETS = [
    # (name, description, coupling_type, temperature, ext_field, init_style)
    # coupling_type: "ferro", "antiferro", "random", "frustrated"
    ("Ferromagnetic", "Uniform J>0 — spins align, classic ordering", "ferro", 1.0, 0.0, "random"),
    ("Antiferromagnetic", "Uniform J<0 — checkerboard Néel order on square lattice", "antiferro", 0.5, 0.0, "random"),
    ("Spin Glass (±J)", "Random ±1 bonds — frustration, no long-range order", "random", 0.5, 0.0, "random"),
    ("Frustrated Lattice", "Triangular frustration — competing interactions", "frustrated", 0.3, 0.0, "random"),
    ("Critical FM", "T near Tc — large fluctuating domains", "ferro", 0.89, 0.0, "random"),
    ("Hot Disorder", "T=5.0 — paramagnetic chaos", "ferro", 5.0, 0.0, "random"),
    ("Quench to Glass", "Start hot, T=0.05 — watch aging & frozen domains", "random", 0.05, 0.0, "random"),
    ("Field-Cooled Glass", "Spin glass in external field — partial alignment", "random", 0.3, 0.5, "random"),
    ("Domain Coarsening", "FM quench — watch domains grow via curvature", "ferro", 0.3, 0.0, "random"),
    ("All Aligned + Heat", "Start ordered, heat to disorder", "ferro", 3.0, 0.0, "aligned"),
    ("Vortex Patterns", "Low-T ferro — watch topological defects", "ferro", 0.1, 0.0, "vortex"),
    ("Glass Aging", "Very low T glass — frozen but slowly evolving", "random", 0.01, 0.0, "random"),
]


def _enter_spinglass_mode(self):
    """Enter Spin Glass mode — show preset menu."""
    self.spinglass_menu = True
    self.spinglass_menu_sel = 0
    self._flash("Magnetism & Spin Glass — select a scenario")


def _exit_spinglass_mode(self):
    """Exit Spin Glass mode."""
    self.spinglass_mode = False
    self.spinglass_menu = False
    self.spinglass_running = False
    self.spinglass_grid = []
    self.spinglass_coupling = []
    self._flash("Spin Glass mode OFF")


def _spinglass_init(self, preset_idx: int):
    """Initialize Spin Glass with the given preset."""
    presets = self.SPINGLASS_PRESETS
    name, _desc, coupling_type, temp, field, init_style = presets[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(10, (max_x - 1) // 2)
    self.spinglass_rows = rows
    self.spinglass_cols = cols
    self.spinglass_temperature = temp
    self.spinglass_ext_field = field
    self.spinglass_preset_name = name
    self.spinglass_coupling_type = coupling_type
    self.spinglass_generation = 0
    self.spinglass_steps_per_frame = 1
    self.spinglass_view = 0  # 0=spin arrows, 1=energy density, 2=stats

    # Initialize spin grid — continuous angles in [0, 2*pi)
    two_pi = 2.0 * math.pi
    if init_style == "aligned":
        self.spinglass_grid = [[0.0] * cols for _ in range(rows)]
    elif init_style == "vortex":
        # Create a vortex pattern centered in grid
        cr, cc = rows / 2.0, cols / 2.0
        self.spinglass_grid = [
            [math.atan2(r - cr, c - cc) % two_pi for c in range(cols)]
            for r in range(rows)
        ]
    else:  # random
        self.spinglass_grid = [
            [random.random() * two_pi for _ in range(cols)]
            for _ in range(rows)
        ]

    # Initialize coupling constants J_ij for each bond (right, down)
    # Store as two grids: J_right[r][c] and J_down[r][c]
    if coupling_type == "ferro":
        j_right = [[1.0] * cols for _ in range(rows)]
        j_down = [[1.0] * cols for _ in range(rows)]
    elif coupling_type == "antiferro":
        j_right = [[-1.0] * cols for _ in range(rows)]
        j_down = [[-1.0] * cols for _ in range(rows)]
    elif coupling_type == "random":
        # Edwards-Anderson spin glass: J = ±1 randomly
        j_right = [[random.choice((-1.0, 1.0)) for _ in range(cols)] for _ in range(rows)]
        j_down = [[random.choice((-1.0, 1.0)) for _ in range(cols)] for _ in range(rows)]
    else:  # frustrated — mix of positive and negative with bias
        j_right = [[1.0 if random.random() < 0.6 else -1.0 for _ in range(cols)] for _ in range(rows)]
        j_down = [[1.0 if random.random() < 0.6 else -1.0 for _ in range(cols)] for _ in range(rows)]
    self.spinglass_coupling = (j_right, j_down)

    # History for plots
    self.spinglass_mag_history = []
    self.spinglass_energy_history = []
    self.spinglass_suscept_history = []
    self.spinglass_mag_sq_history = []

    self._spinglass_compute_stats()
    self.spinglass_mode = True
    self.spinglass_menu = False
    self.spinglass_running = False
    self._flash(f"Spin Glass: {name} — Space to start")


def _spinglass_compute_stats(self):
    """Compute magnetization, energy, susceptibility."""
    grid = self.spinglass_grid
    rows, cols = self.spinglass_rows, self.spinglass_cols
    j_right, j_down = self.spinglass_coupling
    h = self.spinglass_ext_field
    n = rows * cols

    mx_sum = 0.0
    my_sum = 0.0
    total_energy = 0.0

    for r in range(rows):
        for c in range(cols):
            theta = grid[r][c]
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            mx_sum += cos_t
            my_sum += sin_t

            # Right neighbor
            theta_r = grid[r][(c + 1) % cols]
            total_energy -= j_right[r][c] * math.cos(theta - theta_r)
            # Down neighbor
            theta_d = grid[(r + 1) % rows][c]
            total_energy -= j_down[r][c] * math.cos(theta - theta_d)
            # External field (pointing right, theta=0)
            total_energy -= h * cos_t

    self.spinglass_magnetization = math.sqrt(mx_sum * mx_sum + my_sum * my_sum) / n
    self.spinglass_mx = mx_sum / n
    self.spinglass_my = my_sum / n
    self.spinglass_energy = total_energy / n

    # Track history (keep last 200 points)
    self.spinglass_mag_history.append(self.spinglass_magnetization)
    self.spinglass_energy_history.append(self.spinglass_energy)
    m2 = (mx_sum / n) ** 2 + (my_sum / n) ** 2
    self.spinglass_mag_sq_history.append(m2)
    if len(self.spinglass_mag_history) > 200:
        self.spinglass_mag_history.pop(0)
        self.spinglass_energy_history.pop(0)
        self.spinglass_mag_sq_history.pop(0)

    # Susceptibility from fluctuations: chi = N * (<m^2> - <m>^2) / T
    if len(self.spinglass_mag_sq_history) >= 10:
        avg_m2 = sum(self.spinglass_mag_sq_history[-20:]) / min(20, len(self.spinglass_mag_sq_history))
        avg_m = sum(self.spinglass_mag_history[-20:]) / min(20, len(self.spinglass_mag_history))
        t = max(self.spinglass_temperature, 0.001)
        self.spinglass_susceptibility = n * max(0.0, avg_m2 - avg_m * avg_m) / t
    else:
        self.spinglass_susceptibility = 0.0


def _spinglass_step(self):
    """Advance Spin Glass by one sweep (Metropolis on continuous spins)."""
    grid = self.spinglass_grid
    rows, cols = self.spinglass_rows, self.spinglass_cols
    j_right, j_down = self.spinglass_coupling
    temp = self.spinglass_temperature
    h = self.spinglass_ext_field
    n = rows * cols
    two_pi = 2.0 * math.pi
    rand = random.random
    randint_r = random.randint

    if temp > 0:
        inv_temp = 1.0 / temp
    else:
        inv_temp = 1e10

    # Trial step size — adapts: small at low T, large at high T
    delta = min(math.pi, 0.3 + temp * 0.5)

    cos = math.cos
    exp = math.exp

    for _ in range(n):
        r = randint_r(0, rows - 1)
        c = randint_r(0, cols - 1)
        theta_old = grid[r][c]

        # Propose new angle
        theta_new = (theta_old + (rand() - 0.5) * 2.0 * delta) % two_pi

        # Compute energy change
        # Neighbors: right, left, down, up
        rc1 = (c + 1) % cols
        cm1 = (c - 1) % cols
        r1 = (r + 1) % rows
        rm1 = (r - 1) % rows

        # Bond to right neighbor
        dE = -j_right[r][c] * (cos(theta_new - grid[r][rc1]) - cos(theta_old - grid[r][rc1]))
        # Bond from left neighbor to us
        dE -= j_right[r][cm1] * (cos(grid[r][cm1] - theta_new) - cos(grid[r][cm1] - theta_old))
        # Bond to down neighbor
        dE -= j_down[r][c] * (cos(theta_new - grid[r1][c]) - cos(theta_old - grid[r1][c]))
        # Bond from up neighbor to us
        dE -= j_down[rm1][c] * (cos(grid[rm1][c] - theta_new) - cos(grid[rm1][c] - theta_old))
        # External field
        dE -= h * (cos(theta_new) - cos(theta_old))

        if dE <= 0 or rand() < exp(-dE * inv_temp):
            grid[r][c] = theta_new

    self.spinglass_generation += 1
    self._spinglass_compute_stats()


def _handle_spinglass_menu_key(self, key: int) -> bool:
    """Handle input in Spin Glass preset menu."""
    presets = self.SPINGLASS_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.spinglass_menu_sel = (self.spinglass_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.spinglass_menu_sel = (self.spinglass_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._spinglass_init(self.spinglass_menu_sel)
    elif key == ord("q") or key == 27:
        self.spinglass_menu = False
        self.spinglass_mode = False
        self._flash("Spin Glass cancelled")
    return True


def _handle_spinglass_key(self, key: int) -> bool:
    """Handle input in active Spin Glass simulation."""
    if key == ord("q") or key == 27:
        self._exit_spinglass_mode()
        return True
    if key == ord(" "):
        self.spinglass_running = not self.spinglass_running
        return True
    if key == ord("n") or key == ord("."):
        self._spinglass_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.SPINGLASS_PRESETS) if p[0] == self.spinglass_preset_name),
            0,
        )
        self._spinglass_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.spinglass_mode = False
        self.spinglass_running = False
        self.spinglass_menu = True
        self.spinglass_menu_sel = 0
        return True
    if key == ord("v"):
        self.spinglass_view = (self.spinglass_view + 1) % 3
        views = ["Spin Arrows", "Energy Density", "Statistics"]
        self._flash(f"View: {views[self.spinglass_view]}")
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.spinglass_steps_per_frame) if self.spinglass_steps_per_frame in choices else 0
        self.spinglass_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.spinglass_steps_per_frame} sweeps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.spinglass_steps_per_frame) if self.spinglass_steps_per_frame in choices else 0
        self.spinglass_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.spinglass_steps_per_frame} sweeps/frame")
        return True
    # Temperature controls: t/T
    if key == ord("t"):
        self.spinglass_temperature = max(0.01, self.spinglass_temperature - 0.05)
        self._flash(f"Temperature: {self.spinglass_temperature:.3f}")
        return True
    if key == ord("T"):
        self.spinglass_temperature = min(10.0, self.spinglass_temperature + 0.05)
        self._flash(f"Temperature: {self.spinglass_temperature:.3f}")
        return True
    # Quench: Q — instant drop to very low T
    if key == ord("Q"):
        self.spinglass_temperature = 0.01
        self._flash("QUENCH! T → 0.01")
        return True
    # Anneal: A — gradual increase
    if key == ord("a"):
        self.spinglass_temperature = min(10.0, self.spinglass_temperature + 0.5)
        self._flash(f"Anneal: T → {self.spinglass_temperature:.2f}")
        return True
    # External field: f/F
    if key == ord("f"):
        self.spinglass_ext_field = max(-2.0, self.spinglass_ext_field - 0.1)
        self._flash(f"External field: {self.spinglass_ext_field:.2f}")
        return True
    if key == ord("F"):
        self.spinglass_ext_field = min(2.0, self.spinglass_ext_field + 0.1)
        self._flash(f"External field: {self.spinglass_ext_field:.2f}")
        return True
    return True


def _draw_spinglass_menu(self, max_y: int, max_x: int):
    """Draw the Spin Glass preset selection menu."""
    self.stdscr.erase()
    title = "── Magnetism & Spin Glass ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    presets = self.SPINGLASS_PRESETS
    for i, (name, desc, ctype, temp, field, _init) in enumerate(presets):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.spinglass_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.spinglass_menu_sel else curses.color_pair(7)
        coupling_tag = {"ferro": "FM", "antiferro": "AF", "random": "±J", "frustrated": "FR"}
        tag = coupling_tag.get(ctype, "??")
        line = f"{marker}{name:22s} [{tag}] T={temp:<5.2f}  h={field:<4.1f}  {desc}"
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


def _spinglass_local_energy(grid, j_right, j_down, rows, cols, r, c):
    """Compute local energy density at site (r,c)."""
    theta = grid[r][c]
    e = 0.0
    # Right bond
    e -= j_right[r][c] * math.cos(theta - grid[r][(c + 1) % cols])
    # Left bond
    e -= j_right[r][(c - 1) % cols] * math.cos(grid[r][(c - 1) % cols] - theta)
    # Down bond
    e -= j_down[r][c] * math.cos(theta - grid[(r + 1) % rows][c])
    # Up bond
    e -= j_down[(r - 1) % rows][c] * math.cos(grid[(r - 1) % rows][c] - theta)
    return e * 0.5  # avoid double counting


def _is_domain_wall(grid, rows, cols, r, c):
    """Check if site (r,c) is at a domain wall (large angle difference with neighbors)."""
    theta = grid[r][c]
    threshold = math.pi * 0.6
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = (r + dr) % rows, (c + dc) % cols
        diff = abs(theta - grid[nr][nc])
        if diff > math.pi:
            diff = 2.0 * math.pi - diff
        if diff > threshold:
            return True
    return False


def _draw_spinglass(self, max_y: int, max_x: int):
    """Draw the active Spin Glass simulation."""
    self.stdscr.erase()
    grid = self.spinglass_grid
    rows, cols = self.spinglass_rows, self.spinglass_cols
    j_right, j_down = self.spinglass_coupling
    state = "▶ RUN" if self.spinglass_running else "⏸ PAUSED"
    views = ["Spins", "Energy", "Stats"]

    # Title bar
    title = (f" SpinGlass: {self.spinglass_preset_name}  |  sweep {self.spinglass_generation}"
             f"  |  T={self.spinglass_temperature:.3f}"
             f"  h={self.spinglass_ext_field:.2f}"
             f"  |  |m|={self.spinglass_magnetization:.3f}"
             f"  E/N={self.spinglass_energy:.3f}"
             f"  χ={self.spinglass_susceptibility:.1f}"
             f"  |  [{views[self.spinglass_view]}] {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    if self.spinglass_view == 0:
        # Spin arrow view with color-coded energy
        _draw_spinglass_arrows(self, grid, j_right, j_down, rows, cols, view_rows, view_cols)
    elif self.spinglass_view == 1:
        # Energy density heatmap
        _draw_spinglass_energy(self, grid, j_right, j_down, rows, cols, view_rows, view_cols)
    else:
        # Statistics / time series
        _draw_spinglass_stats(self, max_y, max_x)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        coupling_tag = {"ferro": "Ferromagnetic", "antiferro": "Antiferromagnetic",
                        "random": "Spin Glass (±J)", "frustrated": "Frustrated"}
        ctype_str = coupling_tag.get(self.spinglass_coupling_type, "?")
        info = (f" Sweep {self.spinglass_generation}  |  {ctype_str}"
                f"  |  T={self.spinglass_temperature:.3f}"
                f"  |  |m|={self.spinglass_magnetization:.3f}"
                f"  mx={self.spinglass_mx:+.3f} my={self.spinglass_my:+.3f}"
                f"  |  sweeps/f={self.spinglass_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [t/T]=temp [Q]=quench [a]=anneal [f/F]=field [v]=view [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_spinglass_arrows(self, grid, j_right, j_down, rows, cols, view_rows, view_cols):
    """Draw spin arrows with color-coded energy density and domain wall highlighting."""
    pi = math.pi
    two_pi = 2.0 * pi
    addstr = self.stdscr.addstr

    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            theta = grid[r][c]
            sx = c * 2
            sy = 1 + r

            # Map angle to arrow character (8 directions)
            idx = int((theta / two_pi * 8 + 0.5) % 8)
            arrow = SPIN_ARROWS[idx]

            # Compute local energy for coloring
            e = _spinglass_local_energy(grid, j_right, j_down, rows, cols, r, c)

            # Domain wall detection
            is_wall = _is_domain_wall(grid, rows, cols, r, c)

            if is_wall:
                # Domain walls: bright white on dark
                color = curses.color_pair(7) | curses.A_BOLD
            elif e < -1.5:
                # Very low energy (well-ordered): bright cyan
                color = curses.color_pair(6) | curses.A_BOLD
            elif e < -0.5:
                # Low energy: green
                color = curses.color_pair(2)
            elif e < 0.5:
                # Medium energy: yellow
                color = curses.color_pair(3)
            elif e < 1.5:
                # High energy: red
                color = curses.color_pair(1)
            else:
                # Very high energy (frustrated): magenta
                color = curses.color_pair(5) | curses.A_BOLD

            try:
                addstr(sy, sx, arrow + " ", color)
            except curses.error:
                pass


def _draw_spinglass_energy(self, grid, j_right, j_down, rows, cols, view_rows, view_cols):
    """Draw energy density heatmap."""
    # Block characters for energy levels
    blocks = " ░▒▓█"
    addstr = self.stdscr.addstr

    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            sx = c * 2
            sy = 1 + r

            e = _spinglass_local_energy(grid, j_right, j_down, rows, cols, r, c)

            # Map energy to block character: -2 (low) to +2 (high)
            level = int((e + 2.0) / 4.0 * (len(blocks) - 1))
            level = max(0, min(len(blocks) - 1, level))
            ch = blocks[level]

            if e < -1.0:
                color = curses.color_pair(4)  # blue — low energy
            elif e < 0.0:
                color = curses.color_pair(6)  # cyan
            elif e < 1.0:
                color = curses.color_pair(3)  # yellow
            else:
                color = curses.color_pair(1) | curses.A_BOLD  # red — high energy

            try:
                addstr(sy, sx, ch + ch, color)
            except curses.error:
                pass


def _draw_spinglass_stats(self, max_y: int, max_x: int):
    """Draw time-series plots for magnetization, energy, susceptibility."""
    plot_h = max(5, (max_y - 6) // 3)
    plot_w = max(20, max_x - 4)
    addstr = self.stdscr.addstr

    def draw_plot(y_start, data, label, color_pair, lo, hi):
        """Draw a simple ASCII line plot."""
        if not data:
            return
        try:
            addstr(y_start, 1, f"{label} (range {lo:.2f}..{hi:.2f})", curses.color_pair(color_pair) | curses.A_BOLD)
        except curses.error:
            pass

        # Scale data to plot height
        rng = hi - lo if hi > lo else 1.0
        points = data[-plot_w:]
        for i, val in enumerate(points):
            yr = int((1.0 - (val - lo) / rng) * (plot_h - 1))
            yr = max(0, min(plot_h - 1, yr))
            py = y_start + 1 + yr
            px = 2 + i
            if py < max_y - 2 and px < max_x - 1:
                try:
                    addstr(py, px, "█", curses.color_pair(color_pair))
                except curses.error:
                    pass
        # Draw axis
        for dy in range(plot_h):
            py = y_start + 1 + dy
            if py < max_y - 2:
                try:
                    addstr(py, 1, "│", curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

    # Magnetization plot
    mag_data = self.spinglass_mag_history
    draw_plot(1, mag_data, "|m| Magnetization", 6, 0.0, 1.0)

    # Energy plot
    e_data = self.spinglass_energy_history
    if e_data:
        e_lo = min(e_data)
        e_hi = max(e_data)
        if e_lo == e_hi:
            e_lo -= 0.5
            e_hi += 0.5
    else:
        e_lo, e_hi = -2.0, 2.0
    draw_plot(2 + plot_h, e_data, "E/N Energy per spin", 3, e_lo, e_hi)

    # Susceptibility plot
    if len(self.spinglass_mag_sq_history) >= 10:
        # Compute running susceptibility
        n = self.spinglass_rows * self.spinglass_cols
        t = max(self.spinglass_temperature, 0.001)
        chi_data = []
        mag_h = self.spinglass_mag_history
        mag2_h = self.spinglass_mag_sq_history
        window = 10
        for i in range(window, len(mag_h)):
            avg_m2 = sum(mag2_h[i - window:i]) / window
            avg_m = sum(mag_h[i - window:i]) / window
            chi = n * max(0.0, avg_m2 - avg_m * avg_m) / t
            chi_data.append(chi)
        if chi_data:
            chi_lo = 0.0
            chi_hi = max(chi_data) if max(chi_data) > 0 else 1.0
            draw_plot(3 + 2 * plot_h, chi_data, "χ Susceptibility", 2, chi_lo, chi_hi)


def register(App):
    """Register spin glass mode methods on the App class."""
    App._enter_spinglass_mode = _enter_spinglass_mode
    App._exit_spinglass_mode = _exit_spinglass_mode
    App._spinglass_init = _spinglass_init
    App._spinglass_compute_stats = _spinglass_compute_stats
    App._spinglass_step = _spinglass_step
    App._handle_spinglass_menu_key = _handle_spinglass_menu_key
    App._handle_spinglass_key = _handle_spinglass_key
    App._draw_spinglass_menu = _draw_spinglass_menu
    App._draw_spinglass = _draw_spinglass
    App.SPINGLASS_PRESETS = SPINGLASS_PRESETS
