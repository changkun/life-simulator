"""Mode: chladni — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_chladni_mode(self):
    """Enter Chladni Plate Vibration Patterns mode — show preset menu."""
    self.chladni_menu = True
    self.chladni_menu_sel = 0
    self._flash("Chladni Plate Vibration Patterns — select a configuration")



def _exit_chladni_mode(self):
    """Exit Chladni Plate Vibration Patterns mode."""
    self.chladni_mode = False
    self.chladni_menu = False
    self.chladni_running = False
    self.chladni_plate = []
    self.chladni_velocity = []
    self.chladni_sand = []
    self._flash("Chladni Plate mode OFF")



def _chladni_init(self, preset_idx: int):
    """Initialize Chladni plate simulation with the given preset."""
    import math
    import random
    name, _desc, preset_id = self.CHLADNI_PRESETS[preset_idx]
    self.chladni_preset_name = name
    self.chladni_generation = 0
    self.chladni_running = False
    self.chladni_time = 0.0

    max_y, max_x = self.stdscr.getmaxyx()
    self.chladni_rows = max(10, max_y - 3)
    self.chladni_cols = max(10, max_x - 1)
    rows = self.chladni_rows
    cols = self.chladni_cols

    # Defaults
    self.chladni_damping = 0.02
    self.chladni_drive_amp = 0.5
    self.chladni_dt = 0.05
    self.chladni_c = 1.0
    self.chladni_steps_per_frame = 3
    self.chladni_viz_mode = 0
    self.chladni_sand_settle_rate = 0.1

    # Parse preset
    if preset_id == "sweep":
        self.chladni_m = 1
        self.chladni_n = 2
        self.chladni_freq = 0.5
    elif "_" in preset_id:
        parts = preset_id.split("_")
        self.chladni_m = int(parts[0])
        self.chladni_n = int(parts[1])
        # Frequency related to mode numbers for a square plate
        self.chladni_freq = math.sqrt(self.chladni_m ** 2 + self.chladni_n ** 2) * 0.3

    # Initialize fields
    self.chladni_plate = [[0.0] * cols for _ in range(rows)]
    self.chladni_velocity = [[0.0] * cols for _ in range(rows)]

    # Initialize sand uniformly
    self.chladni_sand = [[1.0] * cols for _ in range(rows)]

    # Small random perturbation to break symmetry
    for r in range(rows):
        for c in range(cols):
            self.chladni_plate[r][c] = 0.001 * random.uniform(-1, 1)

    self.chladni_menu = False
    self.chladni_mode = True
    self._flash(f"Chladni Plate: {name} — Space to start")



def _chladni_step(self):
    """Advance the Chladni plate simulation by one timestep.

    Solves the 2D plate vibration equation with damping and sinusoidal driving:
      d²z/dt² = c²∇⁴z - γ dz/dt + A sin(ωt) δ(center)

    where ∇⁴ is the biharmonic operator (plate stiffness), γ is damping,
    and the plate is driven at the center at frequency ω.

    Sand particles migrate toward nodal lines (where displacement ≈ 0).
    """
    import math
    rows = self.chladni_rows
    cols = self.chladni_cols
    dt = self.chladni_dt
    c = self.chladni_c
    damping = self.chladni_damping
    plate = self.chladni_plate
    vel = self.chladni_velocity
    sand = self.chladni_sand

    self.chladni_time += dt

    # Driving force at center
    cr = rows // 2
    cc = cols // 2
    drive = self.chladni_drive_amp * math.sin(2 * math.pi * self.chladni_freq * self.chladni_time)

    # Update plate using biharmonic operator (∇⁴ approximation)
    # ∇⁴z ≈ 20z - 8(neighbors) + 2(diagonals) + (next-neighbors)
    accel = [[0.0] * cols for _ in range(rows)]
    for r in range(2, rows - 2):
        for ci in range(2, cols - 2):
            # Biharmonic stencil (13-point)
            biharm = (
                20.0 * plate[r][ci]
                - 8.0 * (plate[r - 1][ci] + plate[r + 1][ci] +
                         plate[r][ci - 1] + plate[r][ci + 1])
                + 2.0 * (plate[r - 1][ci - 1] + plate[r - 1][ci + 1] +
                         plate[r + 1][ci - 1] + plate[r + 1][ci + 1])
                + plate[r - 2][ci] + plate[r + 2][ci] +
                plate[r][ci - 2] + plate[r][ci + 2]
            )
            accel[r][ci] = -c * c * biharm - damping * vel[r][ci]

    # Apply driving force at center
    accel[cr][cc] += drive

    # Velocity Verlet integration
    for r in range(2, rows - 2):
        for ci in range(2, cols - 2):
            vel[r][ci] += accel[r][ci] * dt
            plate[r][ci] += vel[r][ci] * dt

    # Clamp for stability
    max_disp = 2.0
    for r in range(rows):
        for ci in range(cols):
            if plate[r][ci] > max_disp:
                plate[r][ci] = max_disp
                vel[r][ci] = 0.0
            elif plate[r][ci] < -max_disp:
                plate[r][ci] = -max_disp
                vel[r][ci] = 0.0

    # Boundary conditions: clamped edges (displacement = 0)
    for r in range(rows):
        plate[r][0] = 0.0
        plate[r][1] = 0.0
        plate[r][cols - 1] = 0.0
        plate[r][cols - 2] = 0.0
        vel[r][0] = 0.0
        vel[r][1] = 0.0
        vel[r][cols - 1] = 0.0
        vel[r][cols - 2] = 0.0
    for ci in range(cols):
        plate[0][ci] = 0.0
        plate[1][ci] = 0.0
        plate[rows - 1][ci] = 0.0
        plate[rows - 2][ci] = 0.0
        vel[0][ci] = 0.0
        vel[1][ci] = 0.0
        vel[rows - 1][ci] = 0.0
        vel[rows - 2][ci] = 0.0

    # Sand migration: sand moves away from high-amplitude regions toward nodes
    settle = self.chladni_sand_settle_rate
    sand_new = [[0.0] * cols for _ in range(rows)]
    for r in range(1, rows - 1):
        for ci in range(1, cols - 1):
            amp = abs(plate[r][ci])
            # Gradient of amplitude — sand flows downhill in amplitude
            amp_r_up = abs(plate[r - 1][ci])
            amp_r_dn = abs(plate[r + 1][ci])
            amp_c_lt = abs(plate[r][ci - 1])
            amp_c_rt = abs(plate[r][ci + 1])

            # Net flow: sand moves toward lower amplitude neighbors
            total_flow = 0.0
            flow_out = settle * amp * sand[r][ci]

            # Distribute outgoing sand proportionally to amplitude difference
            neighbors = [(r - 1, ci, amp_r_up), (r + 1, ci, amp_r_dn),
                         (r, ci - 1, amp_c_lt), (r, ci + 1, amp_c_rt)]
            for nr, nc, n_amp in neighbors:
                if amp > n_amp:
                    diff = amp - n_amp
                    sand_new[nr][nc] += flow_out * diff * 0.25
                    total_flow += flow_out * diff * 0.25

            sand_new[r][ci] += sand[r][ci] - min(total_flow, sand[r][ci] * 0.5)

    self.chladni_sand = sand_new

    # Harmonic sweep mode: slowly increase frequency
    if self.CHLADNI_PRESETS[self.chladni_menu_sel][2] == "sweep":
        self.chladni_freq += 0.0005

    self.chladni_generation += 1



def _handle_chladni_menu_key(self, key: int) -> bool:
    """Handle keys in the Chladni Plate preset menu."""
    if key == -1:
        return True
    n = len(self.CHLADNI_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.chladni_menu_sel = (self.chladni_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.chladni_menu_sel = (self.chladni_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.chladni_menu = False
        self._flash("Chladni Plate cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._chladni_init(self.chladni_menu_sel)
        return True
    return True



def _handle_chladni_key(self, key: int) -> bool:
    """Handle keys while in Chladni Plate Vibration Patterns mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_chladni_mode()
        return True
    if key == ord(" "):
        self.chladni_running = not self.chladni_running
        self._flash("Playing" if self.chladni_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self._chladni_step()
        return True
    if key == ord("v"):
        self.chladni_viz_mode = (self.chladni_viz_mode + 1) % 3
        labels = ["Sand density", "Plate displacement", "Vibrational energy"]
        self._flash(f"Viz: {labels[self.chladni_viz_mode]}")
        return True
    if key == ord("m"):
        self.chladni_m = self.chladni_m % 9 + 1
        import math
        self.chladni_freq = math.sqrt(self.chladni_m ** 2 + self.chladni_n ** 2) * 0.3
        self._flash(f"Mode: m={self.chladni_m}, n={self.chladni_n}, f={self.chladni_freq:.2f}")
        return True
    if key == ord("N"):
        self.chladni_n = self.chladni_n % 9 + 1
        import math
        self.chladni_freq = math.sqrt(self.chladni_m ** 2 + self.chladni_n ** 2) * 0.3
        self._flash(f"Mode: m={self.chladni_m}, n={self.chladni_n}, f={self.chladni_freq:.2f}")
        return True
    if key == ord(">"):
        self.chladni_steps_per_frame = min(20, self.chladni_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.chladni_steps_per_frame}")
        return True
    if key == ord("<"):
        self.chladni_steps_per_frame = max(1, self.chladni_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.chladni_steps_per_frame}")
        return True
    if key == ord("+") or key == ord("="):
        self.chladni_drive_amp *= 1.2
        self._flash(f"Drive amplitude: {self.chladni_drive_amp:.3f}")
        return True
    if key == ord("-"):
        self.chladni_drive_amp = max(0.01, self.chladni_drive_amp / 1.2)
        self._flash(f"Drive amplitude: {self.chladni_drive_amp:.3f}")
        return True
    if key == ord("d"):
        self.chladni_damping *= 1.3
        self._flash(f"Damping: {self.chladni_damping:.4f}")
        return True
    if key == ord("D"):
        self.chladni_damping = max(0.001, self.chladni_damping / 1.3)
        self._flash(f"Damping: {self.chladni_damping:.4f}")
        return True
    if key == ord("f"):
        self.chladni_freq *= 1.1
        self._flash(f"Frequency: {self.chladni_freq:.3f}")
        return True
    if key == ord("F"):
        self.chladni_freq = max(0.1, self.chladni_freq / 1.1)
        self._flash(f"Frequency: {self.chladni_freq:.3f}")
        return True
    if key == ord("s"):
        # Redistribute sand uniformly
        for r in range(self.chladni_rows):
            for ci in range(self.chladni_cols):
                self.chladni_sand[r][ci] = 1.0
        self._flash("Sand redistributed")
        return True
    if key == ord("r"):
        self._chladni_init(self.chladni_menu_sel)
        self._flash("Reset")
        return True
    if key == ord("R"):
        self.chladni_mode = False
        self.chladni_running = False
        self.chladni_menu = True
        self.chladni_menu_sel = 0
        return True
    return True



def _draw_chladni_menu(self, max_y: int, max_x: int):
    """Draw the Chladni Plate preset selection menu."""
    self.stdscr.erase()
    title = "── Chladni Plate Vibration Patterns ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Nodal line patterns on a vibrating plate"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.CHLADNI_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.CHLADNI_PRESETS):
        y = 5 + i
        if y >= max_y - 14:
            break
        line = f"  {name:<22s} {desc}"
        attr = curses.color_pair(6)
        if i == self.chladni_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_y = 5 + n + 1
    info_lines = [
        "Simulates Chladni figures — the beautiful nodal",
        "patterns that form when sand settles on a vibrating",
        "metal plate at resonant frequencies.",
        "",
        "First demonstrated by Ernst Chladni in 1787,",
        "these patterns reveal standing wave nodes where",
        "the plate remains stationary.",
        "",
        "Sand collects along nodal lines, creating",
        "stunning geometric figures.",
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



def _draw_chladni(self, max_y: int, max_x: int):
    """Draw the Chladni Plate Vibration Patterns simulation."""
    import math
    self.stdscr.erase()
    rows = self.chladni_rows
    cols = self.chladni_cols

    # Compute visualization field
    if self.chladni_viz_mode == 0:
        # Sand density
        field = self.chladni_sand
        label = "Sand"
    elif self.chladni_viz_mode == 1:
        # Plate displacement
        field = self.chladni_plate
        label = "Displacement"
    else:
        # Vibrational energy (kinetic)
        field = [[0.0] * cols for _ in range(rows)]
        for r in range(rows):
            for ci in range(cols):
                field[r][ci] = 0.5 * self.chladni_velocity[r][ci] ** 2
        label = "Energy"

    # Find field range for normalization
    fmin = float('inf')
    fmax = float('-inf')
    for r in range(rows):
        for ci in range(cols):
            v = field[r][ci]
            if v < fmin:
                fmin = v
            if v > fmax:
                fmax = v
    frange = fmax - fmin if fmax > fmin else 1.0

    # Character ramps
    if self.chladni_viz_mode == 0:
        # Sand: sparse to dense
        ramp = " ·:;=+*#%@"
    elif self.chladni_viz_mode == 1:
        # Displacement: negative to positive
        ramp = "▼▽∨·-·∧△▲"
    else:
        # Energy
        ramp = " ·∘○◎●◉⬤"

    def chladni_color(normalized: float) -> int:
        """Map normalized value to color for Chladni display."""
        if self.chladni_viz_mode == 0:
            # Sand: dark to bright yellow/white
            if normalized < 0.15:
                return curses.color_pair(4) | curses.A_DIM
            elif normalized < 0.3:
                return curses.color_pair(6) | curses.A_DIM
            elif normalized < 0.5:
                return curses.color_pair(6)
            elif normalized < 0.7:
                return curses.color_pair(7)
            elif normalized < 0.85:
                return curses.color_pair(7) | curses.A_BOLD
            else:
                return curses.color_pair(1) | curses.A_BOLD
        elif self.chladni_viz_mode == 1:
            # Displacement: blue (down) to red (up)
            if normalized < 0.3:
                return curses.color_pair(4)
            elif normalized < 0.45:
                return curses.color_pair(6)
            elif normalized < 0.55:
                return curses.color_pair(1)
            elif normalized < 0.7:
                return curses.color_pair(7)
            else:
                return curses.color_pair(3)
        else:
            # Energy: dim to bright
            if normalized < 0.25:
                return curses.color_pair(4) | curses.A_DIM
            elif normalized < 0.5:
                return curses.color_pair(5)
            elif normalized < 0.75:
                return curses.color_pair(3)
            else:
                return curses.color_pair(3) | curses.A_BOLD

    # Render field
    draw_rows = min(rows, max_y - 2)
    draw_cols = min(cols, max_x - 1)
    for r in range(draw_rows):
        for ci in range(draw_cols):
            norm = (field[r][ci] - fmin) / frange
            norm = max(0.0, min(1.0, norm))
            idx = int(norm * (len(ramp) - 1))
            ch = ramp[idx]
            color = chladni_color(norm)
            try:
                self.stdscr.addstr(r + 1, ci, ch, color)
            except curses.error:
                pass

    # Status bar
    status = (f" Chladni: {self.chladni_preset_name}"
              f" │ Step: {self.chladni_generation}"
              f" │ {'▶' if self.chladni_running else '⏸'}"
              f" │ m={self.chladni_m} n={self.chladni_n}"
              f" │ f={self.chladni_freq:.2f}"
              f" │ γ={self.chladni_damping:.3f}"
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
        hint = " Space=play  n=step  v=viz  m/N=modes  f/F=freq  d/D=damp  +/-=amp  s=sand  r=reset  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register chladni mode methods on the App class."""
    App._enter_chladni_mode = _enter_chladni_mode
    App._exit_chladni_mode = _exit_chladni_mode
    App._chladni_init = _chladni_init
    App._chladni_step = _chladni_step
    App._handle_chladni_menu_key = _handle_chladni_menu_key
    App._handle_chladni_key = _handle_chladni_key
    App._draw_chladni_menu = _draw_chladni_menu
    App._draw_chladni = _draw_chladni

