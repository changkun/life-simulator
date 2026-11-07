"""Wave Equation — a 2D membrane of ripples that reflect, absorb or wrap at the edges."""
import curses
import math
import random
import time

from life.colors import colormap_addstr, colormap_rgb

WAVE_PRESETS = [
    # (name, description, c, damping, boundary, init_type)
    # c = wave speed (Courant number, keep <= 0.5 for stability)
    # damping = per-step damping (1.0 = no damping)
    # boundary = reflect | absorb | wrap
    # init_type = center_drop | double_slit | corner_pulse | random_drops | ring | cross
    ("Center Drop", "Single drop in center — watch circular ripples", 0.45, 0.999, "reflect", "center_drop"),
    ("Reflecting Pool", "Drop with reflective walls — standing waves form", 0.40, 0.9995, "reflect", "center_drop"),
    ("Absorbing Edges", "Drop with absorbing boundaries — no reflections", 0.45, 0.999, "absorb", "center_drop"),
    ("Wraparound Torus", "Drop on toroidal surface — waves wrap around", 0.40, 0.999, "wrap", "center_drop"),
    ("Double Slit", "Plane wave through two slits — diffraction pattern", 0.35, 0.9995, "absorb", "double_slit"),
    ("Corner Pulse", "Pulse from corner — diagonal wave front", 0.45, 0.999, "reflect", "corner_pulse"),
    ("Rain Drops", "Random drops — chaotic interference patterns", 0.40, 0.999, "reflect", "random_drops"),
    ("Ring Wave", "Expanding ring — inward and outward propagation", 0.40, 0.999, "reflect", "ring"),
    ("Cross Pattern", "Cross-shaped initial disturbance", 0.40, 0.999, "reflect", "cross"),
    ("Undamped Pool", "No damping — energy conserved forever", 0.40, 1.0, "reflect", "center_drop"),
    ("Slow Ripple", "Very slow wave speed — watch propagation clearly", 0.20, 0.999, "reflect", "center_drop"),
    ("Fast Chaos", "Fast waves, random drops — turbulent surface", 0.48, 0.998, "wrap", "random_drops"),
]


def _enter_wave_mode(self):
    """Show the preset menu."""
    self.wave_menu = True
    self.wave_menu_sel = 0
    self._flash("2D Wave Equation — select a scenario")



def _exit_wave_mode(self):
    """Leave the mode and clear the membrane."""
    self.wave_mode = False
    self.wave_menu = False
    self.wave_running = False
    self.wave_u = []
    self.wave_u_prev = []
    self._flash("Wave Equation mode OFF")



def _wave_init(self, preset_idx: int):
    """Set up the membrane for the preset, paused with zero initial velocity."""
    name, _desc, c, damping, boundary, init_type = self.WAVE_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.wave_rows = rows
    self.wave_cols = cols
    self.wave_c = c
    self.wave_damping = damping
    self.wave_boundary = boundary
    self.wave_preset_name = name
    self.wave_generation = 0
    self.wave_steps_per_frame = 1
    self.wave_init_type = init_type

    self.wave_u = [[0.0] * cols for _ in range(rows)]
    self.wave_u_prev = [[0.0] * cols for _ in range(rows)]

    cr, cc = rows // 2, cols // 2
    if init_type == "center_drop":
        for r in range(rows):
            for c2 in range(cols):
                dx = (c2 - cc) / max(cols, 1) * 4
                dy = (r - cr) / max(rows, 1) * 4
                self.wave_u[r][c2] = math.exp(-(dx * dx + dy * dy) * 2.0)
    elif init_type == "corner_pulse":
        for r in range(min(8, rows)):
            for c2 in range(min(8, cols)):
                dx = r / 8.0
                dy = c2 / 8.0
                self.wave_u[r][c2] = math.exp(-(dx * dx + dy * dy) * 2.0) * 0.8
    elif init_type == "random_drops":
        for _ in range(max(5, (rows * cols) // 200)):
            dr = random.randint(2, rows - 3)
            dc = random.randint(2, cols - 3)
            amp = random.uniform(-1.0, 1.0)
            for rr in range(-2, 3):
                for rc in range(-2, 3):
                    nr, nc = dr + rr, dc + rc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        d = math.sqrt(rr * rr + rc * rc)
                        self.wave_u[nr][nc] += amp * math.exp(-d * d * 0.5)
    elif init_type == "ring":
        radius = min(rows, cols) // 6
        for r in range(rows):
            for c2 in range(cols):
                d = math.sqrt((r - cr) ** 2 + (c2 - cc) ** 2)
                self.wave_u[r][c2] = math.exp(-((d - radius) ** 2) * 0.2)
    elif init_type == "cross":
        thick = max(2, min(rows, cols) // 20)
        for r in range(rows):
            for c2 in range(cols):
                if abs(r - cr) <= thick or abs(c2 - cc) <= thick:
                    dx = (c2 - cc) / max(cols, 1) * 2
                    dy = (r - cr) / max(rows, 1) * 2
                    self.wave_u[r][c2] = 0.5 * math.exp(-(dx * dx + dy * dy) * 0.5)
    elif init_type == "double_slit":
        # Plane wave on left edge + barrier with two slits
        self.wave_slit_wall_col = cols // 4
        slit_gap = max(3, rows // 10)
        slit_width = max(2, rows // 20)
        slit1_center = cr - slit_gap
        slit2_center = cr + slit_gap
        self.wave_slit_openings = []
        for s_center in (slit1_center, slit2_center):
            for dy in range(-slit_width, slit_width + 1):
                sr = s_center + dy
                if 0 <= sr < rows:
                    self.wave_slit_openings.append(sr)
        self.wave_slit_openings = set(self.wave_slit_openings)
        # Initial plane wave pulse on left side
        for r in range(rows):
            for c2 in range(min(self.wave_slit_wall_col, cols)):
                x = c2 / max(self.wave_slit_wall_col, 1)
                self.wave_u[r][c2] = 0.5 * math.sin(x * math.pi)

    # Equal u and u_prev mean zero initial velocity.
    self.wave_u_prev = [row[:] for row in self.wave_u]

    self.wave_mode = True
    self.wave_menu = False
    self.wave_running = False
    self._flash(f"Wave Equation: {name} — Space to start, click to pluck")



def _wave_step(self):
    """Advance the 2D wave equation by one time step.

    Uses the standard finite-difference scheme:
        u_next[r][c] = 2*u[r][c] - u_prev[r][c] + c²*(Laplacian(u))
    with per-step damping.
    """
    u = self.wave_u
    u_prev = self.wave_u_prev
    rows, cols = self.wave_rows, self.wave_cols
    c2 = self.wave_c * self.wave_c
    damp = self.wave_damping
    boundary = self.wave_boundary
    is_slit = getattr(self, 'wave_init_type', '') == 'double_slit'

    u_next = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            # For double-slit: wall cells are fixed at 0
            if is_slit:
                wall_col = self.wave_slit_wall_col
                if c == wall_col and r not in self.wave_slit_openings:
                    u_next[r][c] = 0.0
                    continue

            # Get neighbors based on boundary condition
            if boundary == "wrap":
                up = u[(r - 1) % rows][c]
                dn = u[(r + 1) % rows][c]
                lt = u[r][(c - 1) % cols]
                rt = u[r][(c + 1) % cols]
            elif boundary == "absorb":
                # At boundary: use 0 (absorbing)
                up = u[r - 1][c] if r > 0 else 0.0
                dn = u[r + 1][c] if r < rows - 1 else 0.0
                lt = u[r][c - 1] if c > 0 else 0.0
                rt = u[r][c + 1] if c < cols - 1 else 0.0
            else:  # reflect
                # Neumann boundary: derivative = 0, use same value
                up = u[r - 1][c] if r > 0 else u[r][c]
                dn = u[r + 1][c] if r < rows - 1 else u[r][c]
                lt = u[r][c - 1] if c > 0 else u[r][c]
                rt = u[r][c + 1] if c < cols - 1 else u[r][c]

            laplacian = up + dn + lt + rt - 4.0 * u[r][c]
            u_next[r][c] = damp * (2.0 * u[r][c] - u_prev[r][c] + c2 * laplacian)

    # Double slit: a plane-wave source keeps driving the left edge.
    if is_slit:
        t = self.wave_generation * 0.15
        for r in range(rows):
            u_next[r][0] = 0.5 * math.sin(t)
            if cols > 1:
                u_next[r][1] = 0.5 * math.sin(t - 0.1)

    self.wave_u_prev = u
    self.wave_u = u_next
    self.wave_generation += 1



def _handle_wave_menu_key(self, key: int) -> bool:
    """Handle keys in the preset menu."""
    presets = self.WAVE_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.wave_menu_sel = (self.wave_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.wave_menu_sel = (self.wave_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._wave_init(self.wave_menu_sel)
    elif key == ord("q") or key == 27:
        self.wave_menu = False
        self._flash("Wave Equation cancelled")
    return True



def _handle_wave_key(self, key: int) -> bool:
    """Handle keys while the simulation runs."""
    if key == ord("q") or key == 27:
        self._exit_wave_mode()
        return True
    if key == ord(" "):
        self.wave_running = not self.wave_running
        return True
    if key == ord("n") or key == ord("."):
        self._wave_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.WAVE_PRESETS) if p[0] == self.wave_preset_name),
            0,
        )
        self._wave_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.wave_mode = False
        self.wave_running = False
        self.wave_menu = True
        self.wave_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.wave_steps_per_frame) if self.wave_steps_per_frame in choices else 0
        self.wave_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.wave_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.wave_steps_per_frame) if self.wave_steps_per_frame in choices else 0
        self.wave_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.wave_steps_per_frame} steps/frame")
        return True
    if key == ord("c"):
        self.wave_c = max(0.05, self.wave_c - 0.05)
        self._flash(f"Wave speed (c): {self.wave_c:.2f}")
        return True
    if key == ord("C"):
        self.wave_c = min(0.50, self.wave_c + 0.05)
        self._flash(f"Wave speed (c): {self.wave_c:.2f}")
        return True
    if key == ord("d"):
        self.wave_damping = max(0.95, self.wave_damping - 0.001)
        self._flash(f"Damping: {self.wave_damping:.4f}")
        return True
    if key == ord("D"):
        self.wave_damping = min(1.0, self.wave_damping + 0.001)
        self._flash(f"Damping: {self.wave_damping:.4f}")
        return True
    if key == ord("b"):
        modes = ["reflect", "absorb", "wrap"]
        idx = modes.index(self.wave_boundary) if self.wave_boundary in modes else 0
        self.wave_boundary = modes[(idx + 1) % len(modes)]
        self._flash(f"Boundary: {self.wave_boundary}")
        return True
    if key == ord("p"):
        rows, cols = self.wave_rows, self.wave_cols
        dr = random.randint(3, rows - 4)
        dc = random.randint(3, cols - 4)
        amp = random.choice([-1.0, 1.0])
        for rr in range(-3, 4):
            for rc in range(-3, 4):
                nr, nc = dr + rr, dc + rc
                if 0 <= nr < rows and 0 <= nc < cols:
                    d = math.sqrt(rr * rr + rc * rc)
                    self.wave_u[nr][nc] += amp * math.exp(-d * d * 0.3)
        self._flash("Pluck!")
        return True
    # Mouse click to pluck at cursor position
    if key == curses.KEY_MOUSE:
        try:
            _, mx, my, _, _ = curses.getmouse()
            r = my - 1
            c = mx // 2
            rows, cols = self.wave_rows, self.wave_cols
            if 0 <= r < rows and 0 <= c < cols:
                for rr in range(-3, 4):
                    for rc in range(-3, 4):
                        nr, nc = r + rr, c + rc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            d = math.sqrt(rr * rr + rc * rc)
                            self.wave_u[nr][nc] += math.exp(-d * d * 0.3)
        except curses.error:
            pass
        return True
    return True



def _draw_wave_menu(self, max_y: int, max_x: int):
    """Draw the preset menu."""
    self.stdscr.erase()
    title = "── 2D Wave Equation ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, c, damp, boundary, init) in enumerate(self.WAVE_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.wave_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.wave_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:22s} c={c:<5.2f} damp={damp:<6.4f} {boundary:7s}  {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], attr)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " j/k=move  Enter=select  q/Esc=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_wave(self, max_y: int, max_x: int):
    """Draw the membrane, title bar and key hints."""
    self.stdscr.erase()
    u = self.wave_u
    rows, cols = self.wave_rows, self.wave_cols
    state = "▶ RUNNING" if self.wave_running else "⏸ PAUSED"

    # Title bar
    title = (f" ≈ Wave Equation: {self.wave_preset_name}  |  step {self.wave_generation}"
             f"  |  c={self.wave_c:.2f}  damp={self.wave_damping:.4f}"
             f"  |  {self.wave_boundary}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    tc_buf = getattr(self, 'tc_buf', None)
    use_tc = tc_buf is not None and tc_buf.enabled

    for r in range(view_rows):
        for c in range(view_cols):
            sy = 1 + r
            sx = c * 2
            v = u[r][c]
            av = abs(v)

            if av < 0.02:
                continue

            # Glyph density follows amplitude.
            if av < 0.1:
                ch = "··"
            elif av < 0.3:
                ch = "░░"
            elif av < 0.6:
                ch = "▒▒"
            elif av < 0.85:
                ch = "▓▓"
            else:
                ch = "██"

            if use_tc:
                # Map signed wave value to diverging colour:
                # negative (troughs) → ocean, positive (crests) → inferno
                if v > 0:
                    colormap_addstr(self.stdscr, sy, sx, ch,
                                    'inferno', min(1.0, av),
                                    bold=(av > 0.5), tc_buf=tc_buf)
                else:
                    colormap_addstr(self.stdscr, sy, sx, ch,
                                    'ocean', min(1.0, av),
                                    bold=(av > 0.5), tc_buf=tc_buf)
            else:
                if av < 0.1:
                    if v > 0:
                        attr = curses.color_pair(4) | curses.A_DIM
                    else:
                        attr = curses.color_pair(5) | curses.A_DIM
                elif av < 0.3:
                    if v > 0:
                        attr = curses.color_pair(4)
                    else:
                        attr = curses.color_pair(5)
                elif av < 0.6:
                    if v > 0:
                        attr = curses.color_pair(6) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(4) | curses.A_BOLD
                elif av < 0.85:
                    if v > 0:
                        attr = curses.color_pair(3) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(2) | curses.A_BOLD
                else:
                    if v > 0:
                        attr = curses.color_pair(7) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(5) | curses.A_BOLD
                try:
                    self.stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass

    # For double-slit: draw the barrier wall
    if getattr(self, 'wave_init_type', '') == 'double_slit':
        wall_c = self.wave_slit_wall_col
        sx = wall_c * 2
        if sx < max_x - 1:
            for r in range(view_rows):
                if r not in self.wave_slit_openings:
                    try:
                        self.stdscr.addstr(1 + r, sx, "██", curses.color_pair(7))
                    except curses.error:
                        pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " Space=play  n=step  c/C=wave speed  d/D=damping  b=boundary  p=pluck  +/-=steps/frame  r=reset  R=menu  q=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register wave mode methods on the App class."""
    App.WAVE_PRESETS = WAVE_PRESETS
    App._enter_wave_mode = _enter_wave_mode
    App._exit_wave_mode = _exit_wave_mode
    App._wave_init = _wave_init
    App._wave_step = _wave_step
    App._handle_wave_menu_key = _handle_wave_menu_key
    App._handle_wave_key = _handle_wave_key
    App._draw_wave_menu = _draw_wave_menu
    App._draw_wave = _draw_wave

