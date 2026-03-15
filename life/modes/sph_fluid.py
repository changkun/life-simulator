"""Mode: sph — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_sph_mode(self):
    """Enter SPH mode — show preset menu."""
    self.sph_menu = True
    self.sph_menu_sel = 0
    self._flash("Smoothed Particle Hydrodynamics — select a configuration")



def _exit_sph_mode(self):
    """Exit SPH mode."""
    self.sph_mode = False
    self.sph_menu = False
    self.sph_running = False
    self.sph_particles = []
    self._flash("SPH mode OFF")



def _sph_init(self, preset_idx: int):
    """Initialize SPH simulation with the given preset."""
    import random
    import math
    name, _desc, preset_id = self.SPH_PRESETS[preset_idx]
    self.sph_preset_name = name
    self.sph_generation = 0
    self.sph_running = False
    self.sph_viz_mode = 0

    max_y, max_x = self.stdscr.getmaxyx()
    self.sph_rows = max(10, max_y - 3)
    self.sph_cols = max(10, (max_x - 1) // 2)
    rows = self.sph_rows
    cols = self.sph_cols

    # Default physics parameters
    self.sph_gravity = 9.8
    self.sph_rest_density = 1000.0
    self.sph_gas_const = 2000.0
    self.sph_h = 1.5
    self.sph_mass = 1.0
    self.sph_viscosity = 250.0
    self.sph_dt = 0.003
    self.sph_damping = 0.5
    self.sph_steps_per_frame = 3

    self.sph_particles = []

    if preset_id == "dam":
        # Column of water on the left side
        spacing = self.sph_h * 0.6
        for y_i in range(int(rows * 0.1 / spacing), int(rows * 0.95 / spacing)):
            for x_i in range(int(cols * 0.05 / spacing), int(cols * 0.3 / spacing)):
                px = x_i * spacing + random.uniform(-0.01, 0.01)
                py = y_i * spacing + random.uniform(-0.01, 0.01)
                self.sph_particles.append([px, py, 0.0, 0.0, 0.0, 0.0])

    elif preset_id == "double_dam":
        spacing = self.sph_h * 0.6
        # Left column
        for y_i in range(int(rows * 0.2 / spacing), int(rows * 0.95 / spacing)):
            for x_i in range(int(cols * 0.05 / spacing), int(cols * 0.25 / spacing)):
                px = x_i * spacing + random.uniform(-0.01, 0.01)
                py = y_i * spacing + random.uniform(-0.01, 0.01)
                self.sph_particles.append([px, py, 0.0, 0.0, 0.0, 0.0])
        # Right column
        for y_i in range(int(rows * 0.2 / spacing), int(rows * 0.95 / spacing)):
            for x_i in range(int(cols * 0.75 / spacing), int(cols * 0.95 / spacing)):
                px = x_i * spacing + random.uniform(-0.01, 0.01)
                py = y_i * spacing + random.uniform(-0.01, 0.01)
                self.sph_particles.append([px, py, 0.0, 0.0, 0.0, 0.0])

    elif preset_id == "drop":
        spacing = self.sph_h * 0.6
        # Pool at bottom
        for y_i in range(int(rows * 0.7 / spacing), int(rows * 0.95 / spacing)):
            for x_i in range(int(cols * 0.1 / spacing), int(cols * 0.9 / spacing)):
                px = x_i * spacing + random.uniform(-0.01, 0.01)
                py = y_i * spacing + random.uniform(-0.01, 0.01)
                self.sph_particles.append([px, py, 0.0, 0.0, 0.0, 0.0])
        # Dense block above
        for y_i in range(int(rows * 0.1 / spacing), int(rows * 0.35 / spacing)):
            for x_i in range(int(cols * 0.35 / spacing), int(cols * 0.65 / spacing)):
                px = x_i * spacing + random.uniform(-0.01, 0.01)
                py = y_i * spacing + random.uniform(-0.01, 0.01)
                self.sph_particles.append([px, py, 0.0, 0.0, 0.0, 0.0])

    elif preset_id == "rain":
        spacing = self.sph_h * 0.6
        # Scattered particles across the top half
        num_drops = max(50, int(rows * cols * 0.015))
        for _ in range(num_drops):
            px = random.uniform(cols * 0.05, cols * 0.95)
            py = random.uniform(rows * 0.05, rows * 0.5)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(0.0, 2.0)
            self.sph_particles.append([px, py, vx, vy, 0.0, 0.0])
        self.sph_steps_per_frame = 4

    elif preset_id == "wave":
        spacing = self.sph_h * 0.6
        # Pool tilted — higher on left
        for y_i in range(int(rows * 0.4 / spacing), int(rows * 0.95 / spacing)):
            for x_i in range(int(cols * 0.05 / spacing), int(cols * 0.95 / spacing)):
                px = x_i * spacing
                frac = px / cols  # 0 on left, 1 on right
                top_line = rows * 0.4 + frac * rows * 0.35
                py = y_i * spacing
                if py > top_line:
                    py_a = py + random.uniform(-0.01, 0.01)
                    self.sph_particles.append([px + random.uniform(-0.01, 0.01), py_a, 0.0, 0.0, 0.0, 0.0])

    elif preset_id == "fountain":
        spacing = self.sph_h * 0.6
        # Small pool at the bottom center
        for y_i in range(int(rows * 0.8 / spacing), int(rows * 0.95 / spacing)):
            for x_i in range(int(cols * 0.2 / spacing), int(cols * 0.8 / spacing)):
                px = x_i * spacing + random.uniform(-0.01, 0.01)
                py = y_i * spacing + random.uniform(-0.01, 0.01)
                self.sph_particles.append([px, py, 0.0, 0.0, 0.0, 0.0])
        self.sph_steps_per_frame = 4

    self.sph_num_particles = len(self.sph_particles)
    self.sph_menu = False
    self.sph_mode = True
    self._flash(f"SPH: {name} ({self.sph_num_particles} particles) — Space to start")



def _sph_step(self):
    """Advance SPH simulation by one timestep.

    Uses the standard SPH formulation:
    1. Compute density at each particle using kernel summation
    2. Compute pressure from equation of state
    3. Compute pressure gradient and viscosity forces
    4. Integrate with symplectic Euler
    5. Handle boundary collisions
    """
    import math
    particles = self.sph_particles
    n = len(particles)
    if n == 0:
        return

    h = self.sph_h
    h2 = h * h
    mass = self.sph_mass
    rho0 = self.sph_rest_density
    k = self.sph_gas_const
    mu = self.sph_viscosity
    g = self.sph_gravity
    dt = self.sph_dt
    rows = self.sph_rows
    cols = self.sph_cols
    damping = self.sph_damping

    # Precompute kernel normalization constants
    # Poly6 kernel: W(r,h) = 315/(64*pi*h^9) * (h^2 - r^2)^3
    poly6_coeff = 315.0 / (64.0 * math.pi * h ** 9)
    # Spiky gradient kernel: grad W = -45/(pi*h^6) * (h-r)^2 * r_hat
    spiky_coeff = -45.0 / (math.pi * h ** 6)
    # Viscosity Laplacian kernel: lap W = 45/(pi*h^6) * (h-r)
    visc_lap_coeff = 45.0 / (math.pi * h ** 6)

    # --- Step 1: Compute density for each particle ---
    for i in range(n):
        rho = 0.0
        xi, yi = particles[i][0], particles[i][1]
        for j in range(n):
            dx = particles[j][0] - xi
            dy = particles[j][1] - yi
            r2 = dx * dx + dy * dy
            if r2 < h2:
                diff = h2 - r2
                rho += mass * poly6_coeff * diff * diff * diff
        particles[i][4] = max(rho, rho0 * 0.1)  # clamp to avoid zero density

    # --- Step 2: Compute pressure from equation of state ---
    for i in range(n):
        particles[i][5] = k * (particles[i][4] - rho0)

    # --- Step 3: Compute forces (pressure + viscosity + gravity) ---
    ax = [0.0] * n
    ay = [0.0] * n
    for i in range(n):
        xi, yi = particles[i][0], particles[i][1]
        vxi, vyi = particles[i][2], particles[i][3]
        rhoi = particles[i][4]
        pi_val = particles[i][5]
        fx, fy = 0.0, 0.0

        for j in range(n):
            if i == j:
                continue
            dx = particles[j][0] - xi
            dy = particles[j][1] - yi
            r2 = dx * dx + dy * dy
            if r2 >= h2 or r2 < 1e-8:
                continue
            r = math.sqrt(r2)
            rhoj = particles[j][4]
            pj_val = particles[j][5]

            # Pressure force (Spiky kernel gradient)
            diff = h - r
            pressure_mag = -mass * (pi_val + pj_val) / (2.0 * rhoj) * spiky_coeff * diff * diff / r
            fx += pressure_mag * dx
            fy += pressure_mag * dy

            # Viscosity force (Laplacian of viscosity kernel)
            visc_mag = mu * mass * (1.0 / rhoj) * visc_lap_coeff * (h - r)
            fx += visc_mag * (particles[j][2] - vxi)
            fy += visc_mag * (particles[j][3] - vyi)

        # Acceleration = force / density + gravity
        ax[i] = fx / rhoi
        ay[i] = fy / rhoi + g

    # --- Step 4: Integrate (symplectic Euler) ---
    for i in range(n):
        particles[i][2] += ax[i] * dt
        particles[i][3] += ay[i] * dt
        particles[i][0] += particles[i][2] * dt
        particles[i][1] += particles[i][3] * dt

    # --- Step 5: Boundary collision handling ---
    margin = h * 0.3
    for i in range(n):
        # Left wall
        if particles[i][0] < margin:
            particles[i][0] = margin
            particles[i][2] *= -damping
        # Right wall
        if particles[i][0] > cols - margin:
            particles[i][0] = cols - margin
            particles[i][2] *= -damping
        # Top wall
        if particles[i][1] < margin:
            particles[i][1] = margin
            particles[i][3] *= -damping
        # Bottom wall
        if particles[i][1] > rows - margin:
            particles[i][1] = rows - margin
            particles[i][3] *= -damping

    # Fountain preset: inject upward velocity at bottom center each step
    if self.sph_preset_name == "Fountain":
        cx = cols / 2.0
        for i in range(n):
            dx = abs(particles[i][0] - cx)
            if dx < 2.0 and particles[i][1] > rows * 0.85:
                particles[i][3] = -15.0  # strong upward kick
                particles[i][2] *= 0.3   # reduce horizontal drift

    self.sph_generation += 1



def _handle_sph_menu_key(self, key: int) -> bool:
    """Handle keys in the SPH preset menu."""
    if key == -1:
        return True
    n = len(self.SPH_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.sph_menu_sel = (self.sph_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.sph_menu_sel = (self.sph_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.sph_menu = False
        self._flash("SPH cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._sph_init(self.sph_menu_sel)
        return True
    return True



def _handle_sph_key(self, key: int) -> bool:
    """Handle keys while in SPH mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_sph_mode()
        return True
    if key == ord(" "):
        self.sph_running = not self.sph_running
        self._flash("Playing" if self.sph_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self._sph_step()
        return True
    if key == ord("v"):
        self.sph_viz_mode = (self.sph_viz_mode + 1) % 3
        labels = ["Density", "Velocity", "Pressure"]
        self._flash(f"Viz: {labels[self.sph_viz_mode]}")
        return True
    if key == ord(">"):
        self.sph_steps_per_frame = min(20, self.sph_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.sph_steps_per_frame}")
        return True
    if key == ord("<"):
        self.sph_steps_per_frame = max(1, self.sph_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.sph_steps_per_frame}")
        return True
    if key == ord("+") or key == ord("="):
        self.sph_gravity *= 1.2
        self._flash(f"Gravity = {self.sph_gravity:.1f}")
        return True
    if key == ord("-"):
        self.sph_gravity = max(0.1, self.sph_gravity / 1.2)
        self._flash(f"Gravity = {self.sph_gravity:.1f}")
        return True
    if key == ord("r"):
        self._sph_init(self.sph_menu_sel)
        self._flash("Reset")
        return True
    if key == ord("R"):
        self.sph_mode = False
        self.sph_running = False
        self.sph_menu = True
        self.sph_menu_sel = 0
        return True
    return True



def _draw_sph_menu(self, max_y: int, max_x: int):
    """Draw the SPH preset selection menu."""
    self.stdscr.erase()
    title = "── Smoothed Particle Hydrodynamics (SPH) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Free-surface fluid simulation with particle-based physics"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.SPH_PRESETS)
    for i, (pname, desc, _pid) in enumerate(self.SPH_PRESETS):
        y = 5 + i
        if y >= max_y - 14:
            break
        line = f"  {pname:<22s} {desc}"
        attr = curses.color_pair(6)
        if i == self.sph_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_y = 5 + n + 1
    info_lines = [
        "Simulates fluid as free-moving particles.",
        "Each particle carries mass, velocity, and density.",
        "",
        "Pressure and viscosity forces computed via",
        "smoothing kernels (Poly6 / Spiky / Viscosity).",
        "",
        "Captures dam breaks, splashing, and free-surface",
        "flows that grid-based methods cannot.",
    ]
    for i, line in enumerate(info_lines):
        y = info_y + i
        if y >= max_y - 3:
            break
        try:
            self.stdscr.addstr(y, max(1, (max_x - len(line)) // 2),
                               line[:max_x - 2], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    footer = "↑/↓ select · Enter confirm · q cancel"
    try:
        self.stdscr.addstr(max_y - 2, max(0, (max_x - len(footer)) // 2), footer,
                           curses.color_pair(7))
    except curses.error:
        pass



def _draw_sph(self, max_y: int, max_x: int):
    """Draw the active SPH simulation."""
    import math
    self.stdscr.erase()
    particles = self.sph_particles
    rows = self.sph_rows
    cols = self.sph_cols
    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Build occupancy grid: accumulate particle info per cell
    # grid stores (count, total_density, total_speed, total_pressure)
    grid: dict[tuple[int, int], list[float]] = {}
    for p in particles:
        ci = int(p[0])
        ri = int(p[1])
        if 0 <= ri < view_rows and 0 <= ci < view_cols:
            key = (ri, ci)
            if key not in grid:
                grid[key] = [0.0, 0.0, 0.0, 0.0]
            grid[key][0] += 1.0
            grid[key][1] += p[4]  # density
            grid[key][2] += math.sqrt(p[2] * p[2] + p[3] * p[3])  # speed
            grid[key][3] += p[5]  # pressure

    # Find max values for normalization
    max_density = 1.0
    max_speed = 1.0
    max_pressure = 1.0
    for info in grid.values():
        cnt = info[0]
        if cnt > 0:
            d = info[1] / cnt
            s = info[2] / cnt
            pr = abs(info[3] / cnt)
            if d > max_density:
                max_density = d
            if s > max_speed:
                max_speed = s
            if pr > max_pressure:
                max_pressure = pr

    chars = self.SPH_CHARS

    for (ri, ci), info in grid.items():
        cnt = info[0]
        if cnt <= 0:
            continue

        # Choose value to display based on viz mode
        if self.sph_viz_mode == 0:
            # Density
            val = info[1] / cnt / max_density
        elif self.sph_viz_mode == 1:
            # Velocity
            val = info[2] / cnt / max_speed
        else:
            # Pressure
            val = abs(info[3] / cnt) / max_pressure

        val = max(0.0, min(1.0, val))

        # Character intensity based on count and value
        intensity = min(1.0, cnt / 3.0) * 0.4 + val * 0.6
        idx = int(intensity * (len(chars) - 1))
        idx = max(1, min(len(chars) - 1, idx))  # at least show a dot
        ch = chars[idx]

        # Color based on viz mode and value
        if self.sph_viz_mode == 0:
            # Density: blue → cyan → white
            if val < 0.3:
                attr = curses.color_pair(4) | curses.A_DIM
            elif val < 0.6:
                attr = curses.color_pair(4)
            elif val < 0.8:
                attr = curses.color_pair(6)
            else:
                attr = curses.color_pair(6) | curses.A_BOLD
        elif self.sph_viz_mode == 1:
            # Velocity: blue → green → yellow → red
            if val < 0.25:
                attr = curses.color_pair(4) | curses.A_DIM
            elif val < 0.5:
                attr = curses.color_pair(2)
            elif val < 0.75:
                attr = curses.color_pair(7)
            else:
                attr = curses.color_pair(3) | curses.A_BOLD
        else:
            # Pressure: green (low) → yellow → red (high)
            if val < 0.3:
                attr = curses.color_pair(2) | curses.A_DIM
            elif val < 0.6:
                attr = curses.color_pair(7)
            else:
                attr = curses.color_pair(3) | curses.A_BOLD

        try:
            self.stdscr.addstr(1 + ri, ci * 2, ch + " ", attr)
        except curses.error:
            pass

    # Status bar
    viz_labels = ["Density", "Velocity", "Pressure"]
    status = (f" SPH: {self.sph_preset_name}"
              f" │ Step: {self.sph_generation}"
              f" │ {'▶' if self.sph_running else '⏸'}"
              f" │ {self.sph_num_particles} particles"
              f" │ g={self.sph_gravity:.1f}"
              f" │ Viz: {viz_labels[self.sph_viz_mode]}")
    try:
        self.stdscr.addstr(0, 0, status[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Hint bar
    hint_y = max_y - 1
    now = time.monotonic()
    if self.message and now - self.message_time < 3.0:
        hint = f" {self.message}"
    else:
        hint = " Space=play  n=step  v=viz mode  +/-=gravity  >/<=speed  r=reset  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register sph mode methods on the App class."""
    App._enter_sph_mode = _enter_sph_mode
    App._exit_sph_mode = _exit_sph_mode
    App._sph_init = _sph_init
    App._sph_step = _sph_step
    App._handle_sph_menu_key = _handle_sph_menu_key
    App._handle_sph_key = _handle_sph_key
    App._draw_sph_menu = _draw_sph_menu
    App._draw_sph = _draw_sph

