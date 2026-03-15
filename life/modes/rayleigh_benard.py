"""Mode: rbc — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_rbc_mode(self):
    """Enter Rayleigh-Bénard Convection mode — show preset menu."""
    self.rbc_menu = True
    self.rbc_menu_sel = 0
    self._flash("Rayleigh-Bénard Convection — select a configuration")



def _exit_rbc_mode(self):
    """Exit Rayleigh-Bénard Convection mode."""
    self.rbc_mode = False
    self.rbc_menu = False
    self.rbc_running = False
    self.rbc_T = []
    self.rbc_vx = []
    self.rbc_vy = []
    self._flash("Rayleigh-Bénard Convection mode OFF")



def _rbc_init(self, preset_idx: int):
    """Initialize Rayleigh-Bénard convection with the given preset."""
    import math
    import random
    name, _desc, preset_id = self.RBC_PRESETS[preset_idx]
    self.rbc_preset_name = name
    self.rbc_generation = 0
    self.rbc_running = False

    max_y, max_x = self.stdscr.getmaxyx()
    self.rbc_rows = max(10, max_y - 3)
    self.rbc_cols = max(10, max_x - 1)
    rows = self.rbc_rows
    cols = self.rbc_cols
    self.rbc_dx = 1.0

    # Defaults
    self.rbc_Pr = 0.71
    self.rbc_T_hot = 1.0
    self.rbc_T_cold = 0.0
    self.rbc_viz_mode = 0

    # Initialize fields
    self.rbc_vx = [[0.0] * cols for _ in range(rows)]
    self.rbc_vy = [[0.0] * cols for _ in range(rows)]

    # Linear temperature gradient from hot (bottom) to cold (top)
    self.rbc_T = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        frac = r / max(1, rows - 1)  # 0 at top, 1 at bottom
        base_T = self.rbc_T_cold + (self.rbc_T_hot - self.rbc_T_cold) * frac
        for c in range(cols):
            self.rbc_T[r][c] = base_T

    if preset_id == "classic":
        self.rbc_Ra = 2000.0
        self.rbc_dt = 0.004
        self.rbc_steps_per_frame = 3
        # Small sinusoidal perturbation to seed rolls
        for r in range(1, rows - 1):
            for c in range(cols):
                self.rbc_T[r][c] += 0.02 * math.sin(2 * math.pi * c / cols * 4)
    elif preset_id == "gentle":
        self.rbc_Ra = 500.0
        self.rbc_dt = 0.006
        self.rbc_steps_per_frame = 2
        for r in range(1, rows - 1):
            for c in range(cols):
                self.rbc_T[r][c] += 0.01 * math.sin(2 * math.pi * c / cols * 2)
    elif preset_id == "turbulent":
        self.rbc_Ra = 8000.0
        self.rbc_dt = 0.002
        self.rbc_steps_per_frame = 5
        for r in range(1, rows - 1):
            for c in range(cols):
                self.rbc_T[r][c] += 0.05 * math.sin(2 * math.pi * c / cols * 8) \
                                  + 0.03 * random.uniform(-1, 1)
    elif preset_id == "hexagons":
        self.rbc_Ra = 3000.0
        self.rbc_dt = 0.003
        self.rbc_steps_per_frame = 3
        for r in range(1, rows - 1):
            for c in range(cols):
                # Superpose modes to seed hexagonal patterns
                x = 2 * math.pi * c / cols
                y = 2 * math.pi * r / rows
                self.rbc_T[r][c] += 0.03 * (math.sin(6 * x) +
                                             math.sin(3 * x + 3 * y * 1.732) +
                                             math.sin(3 * x - 3 * y * 1.732))
    elif preset_id == "mantle":
        self.rbc_Ra = 1200.0
        self.rbc_Pr = 10.0  # high Prandtl for viscous mantle
        self.rbc_dt = 0.005
        self.rbc_steps_per_frame = 2
        for r in range(1, rows - 1):
            for c in range(cols):
                self.rbc_T[r][c] += 0.015 * math.sin(2 * math.pi * c / cols * 3)
    elif preset_id == "solar":
        self.rbc_Ra = 10000.0
        self.rbc_Pr = 0.025  # low Prandtl for plasma
        self.rbc_dt = 0.001
        self.rbc_steps_per_frame = 8
        for r in range(1, rows - 1):
            for c in range(cols):
                self.rbc_T[r][c] += 0.04 * random.uniform(-1, 1)
    elif preset_id == "asymmetric":
        self.rbc_Ra = 3000.0
        self.rbc_dt = 0.003
        self.rbc_steps_per_frame = 3
        # Hot spot on the left side of the bottom
        for r in range(1, rows - 1):
            for c in range(cols):
                cx = cols // 4
                dist = abs(c - cx)
                self.rbc_T[r][c] += 0.08 * math.exp(-dist * dist / (cols * cols / 16.0)) * (rows - r) / rows
    elif preset_id == "random":
        self.rbc_Ra = 4000.0
        self.rbc_dt = 0.003
        self.rbc_steps_per_frame = 4
        for r in range(1, rows - 1):
            for c in range(cols):
                self.rbc_T[r][c] += 0.06 * random.uniform(-1, 1)

    self.rbc_menu = False
    self.rbc_mode = True
    self._flash(f"Rayleigh-Bénard: {name} — Space to start")



def _rbc_step(self):
    """Advance the Rayleigh-Bénard convection by one timestep.

    Uses a simplified 2D Boussinesq approximation:
    - Temperature advection-diffusion
    - Buoyancy-driven velocity update
    - Simple pressure relaxation via diffusion of velocity field
    """
    rows = self.rbc_rows
    cols = self.rbc_cols
    dt = self.rbc_dt
    Ra = self.rbc_Ra
    Pr = self.rbc_Pr
    T = self.rbc_T
    vx = self.rbc_vx
    vy = self.rbc_vy

    # Thermal diffusivity and viscosity scale
    kappa = 1.0   # thermal diffusivity (normalized)
    nu = Pr       # kinematic viscosity = Pr * kappa

    # --- Temperature advection-diffusion ---
    T_new = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if r == 0:
                T_new[r][c] = self.rbc_T_cold  # top boundary: cold
                continue
            if r == rows - 1:
                T_new[r][c] = self.rbc_T_hot   # bottom boundary: hot
                continue

            # Neighbors (periodic in x, clamped in y)
            rp = min(r + 1, rows - 1)
            rm = max(r - 1, 0)
            cp = (c + 1) % cols
            cm = (c - 1) % cols

            # Diffusion (Laplacian)
            lap_T = (T[rm][c] + T[rp][c] + T[r][cm] + T[r][cp] - 4.0 * T[r][c])

            # Advection (upwind)
            u = vx[r][c]
            v = vy[r][c]
            if u > 0:
                dTdx = T[r][c] - T[r][cm]
            else:
                dTdx = T[r][cp] - T[r][c]
            if v > 0:
                dTdy = T[r][c] - T[rm][c]
            else:
                dTdy = T[rp][c] - T[r][c]

            T_new[r][c] = T[r][c] + dt * (kappa * lap_T - u * dTdx - v * dTdy)

    self.rbc_T = T_new
    T = T_new

    # --- Velocity update: buoyancy + diffusion ---
    vx_new = [[0.0] * cols for _ in range(rows)]
    vy_new = [[0.0] * cols for _ in range(rows)]
    # Reference temperature for buoyancy
    T_ref = 0.5 * (self.rbc_T_hot + self.rbc_T_cold)
    buoyancy_coeff = Ra * dt * 0.0001  # scaled buoyancy

    for r in range(1, rows - 1):
        for c in range(cols):
            cp = (c + 1) % cols
            cm = (c - 1) % cols
            rp = min(r + 1, rows - 1)
            rm = max(r - 1, 0)

            # Viscous diffusion of velocity
            lap_vx = (vx[rm][c] + vx[rp][c] + vx[r][cm] + vx[r][cp] - 4.0 * vx[r][c])
            lap_vy = (vy[rm][c] + vy[rp][c] + vy[r][cm] + vy[r][cp] - 4.0 * vy[r][c])

            # Advection of velocity (simple upwind)
            u = vx[r][c]
            v = vy[r][c]
            if u > 0:
                dvx_dx = vx[r][c] - vx[r][cm]
                dvy_dx = vy[r][c] - vy[r][cm]
            else:
                dvx_dx = vx[r][cp] - vx[r][c]
                dvy_dx = vy[r][cp] - vy[r][c]
            if v > 0:
                dvx_dy = vx[r][c] - vx[rm][c]
                dvy_dy = vy[r][c] - vy[rm][c]
            else:
                dvx_dy = vx[rp][c] - vx[r][c]
                dvy_dy = vy[rp][c] - vy[r][c]

            vx_new[r][c] = vx[r][c] + dt * (nu * lap_vx - u * dvx_dx - v * dvx_dy)
            # Buoyancy acts in vertical direction (negative r = up)
            # Hot fluid rises (negative vy when T > T_ref, since row 0 is top)
            vy_new[r][c] = vy[r][c] + dt * (nu * lap_vy - u * dvy_dx - v * dvy_dy) \
                          - buoyancy_coeff * (T[r][c] - T_ref)

    # --- Simple pressure projection (divergence reduction) ---
    # A few Gauss-Seidel iterations to reduce divergence
    for _ in range(4):
        for r in range(1, rows - 1):
            for c in range(cols):
                cp = (c + 1) % cols
                cm = (c - 1) % cols
                rp = min(r + 1, rows - 1)
                rm = max(r - 1, 0)
                div = 0.25 * (vx_new[r][cp] - vx_new[r][cm] + vy_new[rp][c] - vy_new[rm][c])
                vx_new[r][c] += 0.0
                # Correct velocities to reduce divergence
                vx_new[r][c] += div * 0.25
                vy_new[r][c] += div * 0.25
                # Push divergence to neighbors
                vx_new[r][cp] -= div * 0.125
                vx_new[r][cm] += div * 0.125
                vy_new[rp][c] -= div * 0.125
                vy_new[rm][c] += div * 0.125

    # Enforce boundary conditions: no-slip at top/bottom
    for c in range(cols):
        vx_new[0][c] = 0.0
        vy_new[0][c] = 0.0
        vx_new[rows - 1][c] = 0.0
        vy_new[rows - 1][c] = 0.0

    # Clamp velocities for stability
    max_v = 5.0
    for r in range(rows):
        for c in range(cols):
            if vx_new[r][c] > max_v:
                vx_new[r][c] = max_v
            elif vx_new[r][c] < -max_v:
                vx_new[r][c] = -max_v
            if vy_new[r][c] > max_v:
                vy_new[r][c] = max_v
            elif vy_new[r][c] < -max_v:
                vy_new[r][c] = -max_v

    self.rbc_vx = vx_new
    self.rbc_vy = vy_new
    self.rbc_generation += 1



def _handle_rbc_menu_key(self, key: int) -> bool:
    """Handle keys in the Rayleigh-Bénard preset menu."""
    if key == -1:
        return True
    n = len(self.RBC_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.rbc_menu_sel = (self.rbc_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.rbc_menu_sel = (self.rbc_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.rbc_menu = False
        self._flash("Rayleigh-Bénard cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._rbc_init(self.rbc_menu_sel)
        return True
    return True



def _handle_rbc_key(self, key: int) -> bool:
    """Handle keys while in Rayleigh-Bénard Convection mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_rbc_mode()
        return True
    if key == ord(" "):
        self.rbc_running = not self.rbc_running
        self._flash("Playing" if self.rbc_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self._rbc_step()
        return True
    if key == ord("v"):
        self.rbc_viz_mode = (self.rbc_viz_mode + 1) % 3
        labels = ["Temperature", "Velocity magnitude", "Vorticity"]
        self._flash(f"Viz: {labels[self.rbc_viz_mode]}")
        return True
    if key == ord(">"):
        self.rbc_steps_per_frame = min(20, self.rbc_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.rbc_steps_per_frame}")
        return True
    if key == ord("<"):
        self.rbc_steps_per_frame = max(1, self.rbc_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.rbc_steps_per_frame}")
        return True
    if key == ord("+") or key == ord("="):
        self.rbc_Ra *= 1.2
        self._flash(f"Ra = {self.rbc_Ra:.0f}")
        return True
    if key == ord("-"):
        self.rbc_Ra = max(100.0, self.rbc_Ra / 1.2)
        self._flash(f"Ra = {self.rbc_Ra:.0f}")
        return True
    if key == ord("r"):
        self._rbc_init(self.rbc_menu_sel)
        self._flash("Reset")
        return True
    if key == ord("R"):
        self.rbc_mode = False
        self.rbc_running = False
        self.rbc_menu = True
        self.rbc_menu_sel = 0
        return True
    return True



def _draw_rbc_menu(self, max_y: int, max_x: int):
    """Draw the Rayleigh-Bénard preset selection menu."""
    self.stdscr.erase()
    title = "── Rayleigh-Bénard Convection ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Thermal convection cells — heated from below"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.RBC_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.RBC_PRESETS):
        y = 5 + i
        if y >= max_y - 14:
            break
        line = f"  {name:<22s} {desc}"
        attr = curses.color_pair(6)
        if i == self.rbc_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    # Info section
    info_y = 5 + n + 1
    info_lines = [
        "Simulates buoyancy-driven convection in a fluid",
        "heated from below and cooled from above.",
        "",
        "Hot fluid rises, cold fluid sinks, forming",
        "self-organizing convection rolls and cells.",
        "",
        "Seen in: boiling water, Earth's mantle,",
        "the Sun's surface, atmospheric weather cells.",
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



def _draw_rbc(self, max_y: int, max_x: int):
    """Draw the Rayleigh-Bénard Convection simulation."""
    import math
    self.stdscr.erase()
    rows = self.rbc_rows
    cols = self.rbc_cols

    # Compute visualization field
    if self.rbc_viz_mode == 0:
        # Temperature
        field = self.rbc_T
        label = "Temperature"
    elif self.rbc_viz_mode == 1:
        # Velocity magnitude
        field = [[0.0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                field[r][c] = math.sqrt(self.rbc_vx[r][c] ** 2 + self.rbc_vy[r][c] ** 2)
        label = "Velocity"
    else:
        # Vorticity (curl of velocity)
        field = [[0.0] * cols for _ in range(rows)]
        for r in range(1, rows - 1):
            for c in range(cols):
                cp = (c + 1) % cols
                cm = (c - 1) % cols
                rp = min(r + 1, rows - 1)
                rm = max(r - 1, 0)
                field[r][c] = (self.rbc_vy[r][cp] - self.rbc_vy[r][cm]) - \
                              (self.rbc_vx[rp][c] - self.rbc_vx[rm][c])
        label = "Vorticity"

    # Find field range for normalization
    fmin = float('inf')
    fmax = float('-inf')
    for r in range(rows):
        for c in range(cols):
            v = field[r][c]
            if v < fmin:
                fmin = v
            if v > fmax:
                fmax = v
    frange = fmax - fmin if fmax > fmin else 1.0

    # Character ramp for intensity
    if self.rbc_viz_mode == 0:
        # Temperature: cold to hot
        ramp = " ·:;=+*#%@"
    elif self.rbc_viz_mode == 1:
        # Velocity magnitude
        ramp = " ·∘○◎●◉⬤"
    else:
        # Vorticity
        ramp = " ·~≈∿≋⊛⊚"

    # Color pairs for temperature visualization
    # Use existing color pairs: 1=white, 2=green, 3=red, 4=blue, 5=magenta, 6=cyan, 7=yellow
    def temp_color(normalized: float) -> int:
        """Map normalized value [0,1] to a color pair for thermal display."""
        if self.rbc_viz_mode == 2:
            # Vorticity: blue for negative, red for positive
            if normalized < 0.4:
                return curses.color_pair(4)  # blue (cold/clockwise)
            elif normalized > 0.6:
                return curses.color_pair(3)  # red (hot/counter-clockwise)
            else:
                return curses.color_pair(7)  # yellow (neutral)
        elif self.rbc_viz_mode == 1:
            # Velocity: dim to bright
            if normalized < 0.25:
                return curses.color_pair(4) | curses.A_DIM  # blue
            elif normalized < 0.5:
                return curses.color_pair(6)  # cyan
            elif normalized < 0.75:
                return curses.color_pair(7)  # yellow
            else:
                return curses.color_pair(3) | curses.A_BOLD  # red
        else:
            # Temperature: blue (cold) → cyan → yellow → red (hot)
            if normalized < 0.2:
                return curses.color_pair(4) | curses.A_DIM  # dark blue
            elif normalized < 0.35:
                return curses.color_pair(4)  # blue
            elif normalized < 0.5:
                return curses.color_pair(6)  # cyan
            elif normalized < 0.65:
                return curses.color_pair(7)  # yellow
            elif normalized < 0.8:
                return curses.color_pair(3)  # red
            else:
                return curses.color_pair(3) | curses.A_BOLD  # bright red

    # Render field
    draw_rows = min(rows, max_y - 2)
    draw_cols = min(cols, max_x - 1)
    for r in range(draw_rows):
        line_chars = []
        for c in range(draw_cols):
            norm = (field[r][c] - fmin) / frange
            norm = max(0.0, min(1.0, norm))
            idx = int(norm * (len(ramp) - 1))
            ch = ramp[idx]
            color = temp_color(norm)
            try:
                self.stdscr.addstr(r + 1, c, ch, color)
            except curses.error:
                pass

    # Status bar
    status = (f" Rayleigh-Bénard: {self.rbc_preset_name}"
              f" │ Step: {self.rbc_generation}"
              f" │ {'▶' if self.rbc_running else '⏸'}"
              f" │ Ra={self.rbc_Ra:.0f}"
              f" │ Pr={self.rbc_Pr:.2f}"
              f" │ Viz: {label}")
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
        hint = " Space=play  n=step  v=viz mode  +/-=Ra  >/<=speed  r=reset  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register rbc mode methods on the App class."""
    App._enter_rbc_mode = _enter_rbc_mode
    App._exit_rbc_mode = _exit_rbc_mode
    App._rbc_init = _rbc_init
    App._rbc_step = _rbc_step
    App._handle_rbc_menu_key = _handle_rbc_menu_key
    App._handle_rbc_key = _handle_rbc_key
    App._draw_rbc_menu = _draw_rbc_menu
    App._draw_rbc = _draw_rbc

