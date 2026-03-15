"""Mode: fdtd — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_fdtd_mode(self):
    """Enter FDTD EM Wave mode — show preset menu."""
    self.fdtd_menu = True
    self.fdtd_menu_sel = 0
    self._flash("FDTD EM Wave Propagation — select a scenario")



def _exit_fdtd_mode(self):
    """Exit FDTD EM Wave mode."""
    self.fdtd_mode = False
    self.fdtd_menu = False
    self.fdtd_running = False
    self.fdtd_Ez = []
    self.fdtd_Hx = []
    self.fdtd_Hy = []
    self.fdtd_eps = []
    self.fdtd_sigma = []
    self.fdtd_sources = []
    self._flash("FDTD EM Wave mode OFF")



def _fdtd_init(self, preset_idx: int):
    """Initialize FDTD simulation with the given preset."""
    name, _desc, preset_id = self.FDTD_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(30, max_y - 4)
    cols = max(30, (max_x - 1) // 2)
    self.fdtd_rows = rows
    self.fdtd_cols = cols
    self.fdtd_preset_name = name
    self.fdtd_generation = 0
    self.fdtd_running = False
    self.fdtd_steps_per_frame = 2
    self.fdtd_viz_mode = 0
    self.fdtd_courant = 0.5
    self.fdtd_pml_width = max(6, min(rows, cols) // 12)

    # Initialize fields to zero
    self.fdtd_Ez = [[0.0] * cols for _ in range(rows)]
    self.fdtd_Hx = [[0.0] * cols for _ in range(rows)]
    self.fdtd_Hy = [[0.0] * cols for _ in range(rows)]

    # Default: free space (eps=1, sigma=0)
    self.fdtd_eps = [[1.0] * cols for _ in range(rows)]
    self.fdtd_sigma = [[0.0] * cols for _ in range(rows)]

    # Set up PML absorbing boundaries (graded conductivity)
    pml = self.fdtd_pml_width
    for r in range(rows):
        for c in range(cols):
            # Distance from each edge
            d = min(r, rows - 1 - r, c, cols - 1 - c)
            if d < pml:
                depth = (pml - d) / pml
                self.fdtd_sigma[r][c] = 0.8 * depth * depth

    self.fdtd_sources = []
    cr, cc = rows // 2, cols // 2

    if preset_id == "point":
        self.fdtd_freq = 0.15
        self.fdtd_sources.append({"r": cr, "c": cc, "freq": 0.15, "phase": 0.0, "amp": 1.0})

    elif preset_id == "double_slit":
        self.fdtd_freq = 0.12
        wall_c = cols // 3
        slit_gap = max(4, rows // 8)
        slit_w = max(2, rows // 25)
        # Build wall
        for r in range(rows):
            is_slit = False
            for sc in (cr - slit_gap, cr + slit_gap):
                if abs(r - sc) <= slit_w:
                    is_slit = True
            if not is_slit:
                self.fdtd_sigma[r][wall_c] = 100.0
                self.fdtd_eps[r][wall_c] = 1.0
        # Plane wave source line on the left
        src_c = pml + 3
        for r in range(pml, rows - pml):
            self.fdtd_sources.append({"r": r, "c": src_c, "freq": 0.12, "phase": 0.0, "amp": 0.5})

    elif preset_id == "single_slit":
        self.fdtd_freq = 0.12
        wall_c = cols // 3
        slit_w = max(3, rows // 15)
        for r in range(rows):
            if abs(r - cr) > slit_w:
                self.fdtd_sigma[r][wall_c] = 100.0
        src_c = pml + 3
        for r in range(pml, rows - pml):
            self.fdtd_sources.append({"r": r, "c": src_c, "freq": 0.12, "phase": 0.0, "amp": 0.5})

    elif preset_id == "waveguide":
        self.fdtd_freq = 0.15
        guide_half = max(4, rows // 10)
        # Top and bottom walls of waveguide
        for c in range(cols):
            for wall_r in (cr - guide_half, cr + guide_half):
                if 0 <= wall_r < rows:
                    self.fdtd_sigma[wall_r][c] = 100.0
        self.fdtd_sources.append({"r": cr, "c": pml + 3, "freq": 0.15, "phase": 0.0, "amp": 1.0})

    elif preset_id == "lens":
        self.fdtd_freq = 0.12
        lens_c = cols // 3
        lens_radius = max(8, min(rows, cols) // 5)
        lens_thick = max(3, cols // 20)
        # Dielectric lens (convex shape)
        for r in range(rows):
            dy = abs(r - cr)
            if dy < lens_radius:
                # Lens profile: thickest at center
                thickness = int(lens_thick * (1.0 - (dy / lens_radius) ** 2))
                for dc in range(-thickness // 2, thickness // 2 + 1):
                    lc = lens_c + dc
                    if 0 <= lc < cols:
                        self.fdtd_eps[r][lc] = 4.0  # glass-like dielectric
        # Plane wave source
        src_c = pml + 3
        for r in range(pml, rows - pml):
            self.fdtd_sources.append({"r": r, "c": src_c, "freq": 0.12, "phase": 0.0, "amp": 0.5})

    elif preset_id == "dipole":
        self.fdtd_freq = 0.15
        sep = max(3, rows // 10)
        self.fdtd_sources.append({"r": cr - sep, "c": cc, "freq": 0.15, "phase": 0.0, "amp": 1.0})
        self.fdtd_sources.append({"r": cr + sep, "c": cc, "freq": 0.15, "phase": math.pi, "amp": 1.0})

    elif preset_id == "phased_array":
        self.fdtd_freq = 0.15
        n_src = 8
        spacing = max(3, rows // (n_src + 2))
        start_r = cr - (n_src - 1) * spacing // 2
        for i in range(n_src):
            sr = start_r + i * spacing
            if 0 < sr < rows:
                # Progressive phase shift for beam steering (~30 degrees)
                phase = i * 0.4
                self.fdtd_sources.append({"r": sr, "c": cc, "freq": 0.15, "phase": phase, "amp": 0.8})

    elif preset_id == "corner_reflector":
        self.fdtd_freq = 0.15
        refl_size = max(8, min(rows, cols) // 5)
        # Vertical wall
        for r in range(cr - refl_size, cr + refl_size + 1):
            if 0 <= r < rows:
                rc = cc + refl_size
                if rc < cols:
                    self.fdtd_sigma[r][rc] = 100.0
        # Horizontal wall
        for c in range(cc, cc + refl_size + 1):
            if c < cols:
                rr = cr + refl_size
                if rr < rows:
                    self.fdtd_sigma[rr][c] = 100.0
                rr2 = cr - refl_size
                if 0 <= rr2:
                    self.fdtd_sigma[rr2][c] = 100.0
        self.fdtd_sources.append({"r": cr, "c": cc - refl_size // 2, "freq": 0.15, "phase": 0.0, "amp": 1.0})

    elif preset_id == "cavity":
        self.fdtd_freq = 0.20
        cav_h = max(8, rows // 4)
        cav_w = max(10, cols // 4)
        r0, r1 = cr - cav_h, cr + cav_h
        c0, c1 = cc - cav_w, cc + cav_w
        for r in range(max(0, r0), min(rows, r1 + 1)):
            for c in (c0, c1):
                if 0 <= c < cols:
                    self.fdtd_sigma[r][c] = 100.0
        for c in range(max(0, c0), min(cols, c1 + 1)):
            for r in (r0, r1):
                if 0 <= r < rows:
                    self.fdtd_sigma[r][c] = 100.0
        self.fdtd_sources.append({"r": cr, "c": cc, "freq": 0.20, "phase": 0.0, "amp": 1.0})

    elif preset_id == "scatter":
        self.fdtd_freq = 0.12
        # Place circular dielectric scatterers
        scat_radius = max(3, min(rows, cols) // 15)
        positions = [
            (cr - rows // 5, cc + cols // 6),
            (cr + rows // 5, cc + cols // 6),
            (cr, cc + cols // 3),
        ]
        for sr, sc in positions:
            for r in range(rows):
                for c in range(cols):
                    d = math.sqrt((r - sr) ** 2 + (c - sc) ** 2)
                    if d < scat_radius:
                        self.fdtd_eps[r][c] = 6.0
        # Plane wave source
        src_c = pml + 3
        for r in range(pml, rows - pml):
            self.fdtd_sources.append({"r": r, "c": src_c, "freq": 0.12, "phase": 0.0, "amp": 0.5})

    self.fdtd_mode = True
    self.fdtd_menu = False
    self._flash(f"FDTD: {name} — Space to start")



def _fdtd_step(self):
    """Advance FDTD simulation by one time step using Yee algorithm.

    2D TM mode (Ez, Hx, Hy):
        Hx(n+1/2) = Hx(n-1/2) - (dt/mu0) * dEz/dy
        Hy(n+1/2) = Hy(n-1/2) + (dt/mu0) * dEz/dx
        Ez(n+1)   = C1*Ez(n) + C2*(dHy/dx - dHx/dy)
    where C1, C2 incorporate eps and sigma for lossy media / PML.
    """
    Ez = self.fdtd_Ez
    Hx = self.fdtd_Hx
    Hy = self.fdtd_Hy
    eps = self.fdtd_eps
    sigma = self.fdtd_sigma
    rows, cols = self.fdtd_rows, self.fdtd_cols
    dt = self.fdtd_courant  # dt/dx = courant, dx=1

    # Update H fields (half step)
    for r in range(rows - 1):
        Hx_row = Hx[r]
        Ez_row = Ez[r]
        Ez_row_next = Ez[r + 1]
        for c in range(cols):
            Hx_row[c] -= dt * (Ez_row_next[c] - Ez_row[c])

    for r in range(rows):
        Hy_row = Hy[r]
        Ez_row = Ez[r]
        for c in range(cols - 1):
            Hy_row[c] += dt * (Ez_row[c + 1] - Ez_row[c])

    # Update E field
    for r in range(1, rows - 1):
        Ez_row = Ez[r]
        Hx_row = Hx[r]
        Hx_prev = Hx[r - 1]
        Hy_row = Hy[r]
        eps_row = eps[r]
        sig_row = sigma[r]
        for c in range(1, cols - 1):
            s = sig_row[c]
            e = eps_row[c]
            if s > 0.0:
                # Lossy update (PML or conductor)
                c1 = (1.0 - 0.5 * s * dt / e) / (1.0 + 0.5 * s * dt / e)
                c2 = (dt / e) / (1.0 + 0.5 * s * dt / e)
            else:
                c1 = 1.0
                c2 = dt / e
            curl_h = (Hy_row[c] - Hy_row[c - 1]) - (Hx_row[c] - Hx_prev[c])
            Ez_row[c] = c1 * Ez_row[c] + c2 * curl_h

    # Inject sources (soft sources: add to Ez)
    t = self.fdtd_generation
    for src in self.fdtd_sources:
        sr, sc = src["r"], src["c"]
        if 0 < sr < rows - 1 and 0 < sc < cols - 1:
            val = src["amp"] * math.sin(2.0 * math.pi * src["freq"] * t + src["phase"])
            # Gaussian envelope ramp-up for smooth start
            if t < 30:
                val *= (1.0 - math.exp(-((t / 10.0) ** 2)))
            Ez[sr][sc] += val

    self.fdtd_generation += 1



def _handle_fdtd_menu_key(self, key: int) -> bool:
    """Handle input in FDTD preset menu."""
    presets = self.FDTD_PRESETS
    n = len(presets)
    if key == curses.KEY_UP or key == ord("k"):
        self.fdtd_menu_sel = (self.fdtd_menu_sel - 1) % n
    elif key == curses.KEY_DOWN or key == ord("j"):
        self.fdtd_menu_sel = (self.fdtd_menu_sel + 1) % n
    elif key in (10, 13, curses.KEY_ENTER):
        self._fdtd_init(self.fdtd_menu_sel)
    elif key == ord("q") or key == 27:
        self.fdtd_menu = False
        self._flash("FDTD cancelled")
    return True



def _handle_fdtd_key(self, key: int) -> bool:
    """Handle input in active FDTD simulation."""
    if key == ord("q") or key == 27:
        self._exit_fdtd_mode()
        return True
    if key == ord(" "):
        self.fdtd_running = not self.fdtd_running
        return True
    if key == ord("n") or key == ord("."):
        self._fdtd_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.FDTD_PRESETS) if p[0] == self.fdtd_preset_name),
            0,
        )
        self._fdtd_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.fdtd_mode = False
        self.fdtd_running = False
        self.fdtd_menu = True
        self.fdtd_menu_sel = 0
        return True
    if key == ord("v"):
        self.fdtd_viz_mode = (self.fdtd_viz_mode + 1) % 3
        labels = ["Ez field", "|E| intensity", "|H| magnitude"]
        self._flash(f"Viz: {labels[self.fdtd_viz_mode]}")
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 8, 12, 20]
        idx = choices.index(self.fdtd_steps_per_frame) if self.fdtd_steps_per_frame in choices else 0
        self.fdtd_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.fdtd_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 8, 12, 20]
        idx = choices.index(self.fdtd_steps_per_frame) if self.fdtd_steps_per_frame in choices else 0
        self.fdtd_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.fdtd_steps_per_frame} steps/frame")
        return True
    if key == ord("f"):
        self.fdtd_freq = min(0.30, self.fdtd_freq + 0.01)
        for src in self.fdtd_sources:
            src["freq"] = self.fdtd_freq
        self._flash(f"Frequency: {self.fdtd_freq:.2f}")
        return True
    if key == ord("F"):
        self.fdtd_freq = max(0.03, self.fdtd_freq - 0.01)
        for src in self.fdtd_sources:
            src["freq"] = self.fdtd_freq
        self._flash(f"Frequency: {self.fdtd_freq:.2f}")
        return True
    # Mouse click to add a point source
    if key == curses.KEY_MOUSE:
        try:
            _, mx, my, _, _ = curses.getmouse()
            r = my - 1
            c = mx // 2
            if 0 < r < self.fdtd_rows - 1 and 0 < c < self.fdtd_cols - 1:
                self.fdtd_sources.append({
                    "r": r, "c": c,
                    "freq": self.fdtd_freq, "phase": 0.0, "amp": 1.0,
                })
                self._flash(f"Source added at ({r},{c})")
        except curses.error:
            pass
        return True
    if key == ord("p"):
        # Add a random point source
        r = random.randint(self.fdtd_pml_width + 2, self.fdtd_rows - self.fdtd_pml_width - 3)
        c = random.randint(self.fdtd_pml_width + 2, self.fdtd_cols - self.fdtd_pml_width - 3)
        self.fdtd_sources.append({
            "r": r, "c": c,
            "freq": self.fdtd_freq, "phase": random.uniform(0, 2 * math.pi), "amp": 1.0,
        })
        self._flash("Random source added")
        return True
    if key == ord("c"):
        # Clear all fields (keep sources and geometry)
        rows, cols = self.fdtd_rows, self.fdtd_cols
        self.fdtd_Ez = [[0.0] * cols for _ in range(rows)]
        self.fdtd_Hx = [[0.0] * cols for _ in range(rows)]
        self.fdtd_Hy = [[0.0] * cols for _ in range(rows)]
        self.fdtd_generation = 0
        self._flash("Fields cleared")
        return True
    return True



def _draw_fdtd_menu(self, max_y: int, max_x: int):
    """Draw the FDTD preset selection menu."""
    self.stdscr.erase()
    title = "── FDTD Electromagnetic Wave Propagation ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(self.FDTD_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.fdtd_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.fdtd_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:22s}  {desc}"
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



def _draw_fdtd(self, max_y: int, max_x: int):
    """Draw the active FDTD simulation."""
    self.stdscr.erase()
    Ez = self.fdtd_Ez
    Hx = self.fdtd_Hx
    Hy = self.fdtd_Hy
    eps = self.fdtd_eps
    sigma = self.fdtd_sigma
    rows, cols = self.fdtd_rows, self.fdtd_cols
    state = "▶ RUNNING" if self.fdtd_running else "⏸ PAUSED"
    viz_labels = ["Ez field", "|E| intensity", "|H| mag"]

    # Title bar
    title = (f" EM FDTD: {self.fdtd_preset_name}  |  step {self.fdtd_generation}"
             f"  |  freq={self.fdtd_freq:.2f}  |  {viz_labels[self.fdtd_viz_mode]}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Render fields
    for r in range(view_rows):
        for c in range(view_cols):
            sy = 1 + r
            sx = c * 2

            # Check for conductor/barrier
            if sigma[r][c] >= 50.0:
                try:
                    self.stdscr.addstr(sy, sx, "██", curses.color_pair(7))
                except curses.error:
                    pass
                continue

            # Check for dielectric material
            is_dielectric = eps[r][c] > 1.5

            if self.fdtd_viz_mode == 0:
                # Ez field — signed, show positive/negative
                v = Ez[r][c]
                av = abs(v)
            elif self.fdtd_viz_mode == 1:
                # |E| intensity
                v = Ez[r][c]
                av = abs(v)
                v = av  # always positive for intensity
            else:
                # |H| magnitude
                hx = Hx[r][c] if r < rows else 0.0
                hy = Hy[r][c] if c < cols else 0.0
                av = math.sqrt(hx * hx + hy * hy)
                v = av

            if av < 0.01:
                # Show dielectric background if present
                if is_dielectric:
                    try:
                        self.stdscr.addstr(sy, sx, "░░", curses.color_pair(4) | curses.A_DIM)
                    except curses.error:
                        pass
                continue

            # Map value to character and color
            if av < 0.05:
                ch = "··"
                if self.fdtd_viz_mode == 0 and v < 0:
                    attr = curses.color_pair(5) | curses.A_DIM
                else:
                    attr = curses.color_pair(4) | curses.A_DIM
            elif av < 0.15:
                ch = "░░"
                if self.fdtd_viz_mode == 0 and v < 0:
                    attr = curses.color_pair(5)
                else:
                    attr = curses.color_pair(4)
            elif av < 0.35:
                ch = "▒▒"
                if self.fdtd_viz_mode == 0 and v < 0:
                    attr = curses.color_pair(5) | curses.A_BOLD
                else:
                    attr = curses.color_pair(6)
            elif av < 0.60:
                ch = "▓▓"
                if self.fdtd_viz_mode == 0 and v < 0:
                    attr = curses.color_pair(2) | curses.A_BOLD
                else:
                    attr = curses.color_pair(3) | curses.A_BOLD
            else:
                ch = "██"
                if self.fdtd_viz_mode == 0 and v < 0:
                    attr = curses.color_pair(1) | curses.A_BOLD
                else:
                    attr = curses.color_pair(7) | curses.A_BOLD

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Draw source positions
    for src in self.fdtd_sources:
        sr, sc = src["r"], src["c"]
        if 0 <= sr < view_rows and 0 <= sc < view_cols:
            try:
                self.stdscr.addstr(1 + sr, sc * 2, "◉ "[:2], curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                try:
                    self.stdscr.addstr(1 + sr, sc * 2, "* ", curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=viz [f/F]=freq+/- [p]=source [c]=clear [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register fdtd mode methods on the App class."""
    App._enter_fdtd_mode = _enter_fdtd_mode
    App._exit_fdtd_mode = _exit_fdtd_mode
    App._fdtd_init = _fdtd_init
    App._fdtd_step = _fdtd_step
    App._handle_fdtd_menu_key = _handle_fdtd_menu_key
    App._handle_fdtd_key = _handle_fdtd_key
    App._draw_fdtd_menu = _draw_fdtd_menu
    App._draw_fdtd = _draw_fdtd

