"""Mode: ns — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_ns_mode(self):
    """Enter Navier-Stokes Fluid Dynamics mode — show preset menu."""
    self.ns_menu = True
    self.ns_menu_sel = 0
    self._flash("Navier-Stokes Fluid Dynamics — select a configuration")



def _exit_ns_mode(self):
    """Exit Navier-Stokes mode."""
    self.ns_mode = False
    self.ns_menu = False
    self.ns_running = False
    self.ns_vx = []
    self.ns_vy = []
    self.ns_vx0 = []
    self.ns_vy0 = []
    self.ns_p = []
    self.ns_div = []
    self.ns_dye = []
    self.ns_dye0 = []
    self.ns_obstacles = []
    self._flash("Navier-Stokes mode OFF")



def _ns_make_grid(self, val: float = 0.0) -> list[list[float]]:
    return [[val] * self.ns_cols for _ in range(self.ns_rows)]



def _ns_init(self, preset_idx: int):
    """Initialize Navier-Stokes simulation with the given preset."""
    name, _desc, preset_id = self.NS_PRESETS[preset_idx]
    self.ns_preset_name = name
    self.ns_generation = 0
    self.ns_running = False
    self.ns_viz_mode = 0
    self.ns_dye_hue = 0.0

    max_y, max_x = self.stdscr.getmaxyx()
    self.ns_rows = max(10, max_y - 3)
    self.ns_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.ns_rows, self.ns_cols

    self.ns_cursor_r = rows // 2
    self.ns_cursor_c = cols // 2
    self.ns_prev_cursor_r = self.ns_cursor_r
    self.ns_prev_cursor_c = self.ns_cursor_c

    self.ns_vx = self._ns_make_grid()
    self.ns_vy = self._ns_make_grid()
    self.ns_vx0 = self._ns_make_grid()
    self.ns_vy0 = self._ns_make_grid()
    self.ns_p = self._ns_make_grid()
    self.ns_div = self._ns_make_grid()
    self.ns_dye = self._ns_make_grid()
    self.ns_dye0 = self._ns_make_grid()
    self.ns_obstacles = [[False] * cols for _ in range(rows)]

    if preset_id == "vortex_pair":
        cx, cy = cols // 2, rows // 2
        strength = 40.0
        offset = min(rows, cols) // 6
        for r in range(rows):
            for c in range(cols):
                # Vortex 1 (counterclockwise)
                dx1 = c - (cx - offset)
                dy1 = r - cy
                dist1 = max(1.0, (dx1 * dx1 + dy1 * dy1) ** 0.5)
                factor1 = strength / (dist1 + 5.0)
                # Vortex 2 (clockwise)
                dx2 = c - (cx + offset)
                dy2 = r - cy
                dist2 = max(1.0, (dx2 * dx2 + dy2 * dy2) ** 0.5)
                factor2 = strength / (dist2 + 5.0)
                self.ns_vx[r][c] = -dy1 / dist1 * factor1 + dy2 / dist2 * factor2
                self.ns_vy[r][c] = dx1 / dist1 * factor1 - dx2 / dist2 * factor2
                # Dye in vortex cores
                if dist1 < offset:
                    self.ns_dye[r][c] = max(0.0, 1.0 - dist1 / offset)
                if dist2 < offset:
                    self.ns_dye[r][c] = max(self.ns_dye[r][c], 1.0 - dist2 / offset)

    elif preset_id == "jet":
        self.ns_viscosity = 0.00005
        # Jet enters from left side at middle
        jet_width = rows // 6
        mid = rows // 2
        for r in range(mid - jet_width, mid + jet_width):
            if 0 <= r < rows:
                for c in range(min(5, cols)):
                    self.ns_vx[r][c] = 60.0
                    self.ns_dye[r][c] = 1.0

    elif preset_id == "karman":
        self.ns_viscosity = 0.00008
        # Circular obstacle
        cr, cc = rows // 2, cols // 4
        radius = min(rows, cols) // 10
        for r in range(rows):
            for c in range(cols):
                dr = r - cr
                dc = c - cc
                if dr * dr + dc * dc <= radius * radius:
                    self.ns_obstacles[r][c] = True
        # Uniform inflow
        for r in range(rows):
            self.ns_vx[r][0] = 30.0
            self.ns_vx[r][1] = 30.0

    elif preset_id == "four_corners":
        sz = min(rows, cols) // 8
        for r in range(sz):
            for c in range(sz):
                self.ns_dye[r][c] = 1.0
                self.ns_vx[r][c] = 20.0
                self.ns_vy[r][c] = 20.0
                self.ns_dye[rows - 1 - r][c] = 0.8
                self.ns_vx[rows - 1 - r][c] = 20.0
                self.ns_vy[rows - 1 - r][c] = -20.0
                self.ns_dye[r][cols - 1 - c] = 0.6
                self.ns_vx[r][cols - 1 - c] = -20.0
                self.ns_vy[r][cols - 1 - c] = 20.0
                self.ns_dye[rows - 1 - r][cols - 1 - c] = 0.4
                self.ns_vx[rows - 1 - r][cols - 1 - c] = -20.0
                self.ns_vy[rows - 1 - r][cols - 1 - c] = -20.0

    elif preset_id == "shear":
        mid = rows // 2
        for r in range(rows):
            for c in range(cols):
                if r < mid:
                    self.ns_vx[r][c] = 15.0
                else:
                    self.ns_vx[r][c] = -15.0
                # Perturbation to trigger instability
                if abs(r - mid) < 3:
                    import math
                    self.ns_vy[r][c] = 3.0 * math.sin(2.0 * math.pi * c / cols * 6)
                    self.ns_dye[r][c] = 0.8

    self.ns_menu = False
    self.ns_mode = True
    self._flash(f"Navier-Stokes: {name} — Space to start, arrows+Enter to inject dye")



def _ns_diffuse(self, x: list[list[float]], x0: list[list[float]], diff: float, dt: float):
    """Diffuse a field using Gauss-Seidel relaxation."""
    rows, cols = self.ns_rows, self.ns_cols
    a = dt * diff * rows * cols
    if a < 1e-12:
        for r in range(rows):
            for c in range(cols):
                x[r][c] = x0[r][c]
        return
    obstacles = self.ns_obstacles
    for _ in range(self.ns_iterations):
        for r in range(rows):
            for c in range(cols):
                if obstacles[r][c]:
                    x[r][c] = 0.0
                    continue
                rn = (r - 1) % rows
                rs = (r + 1) % rows
                cw = (c - 1) % cols
                ce = (c + 1) % cols
                neighbors = 0.0
                count = 0.0
                if not obstacles[rn][c]:
                    neighbors += x[rn][c]
                    count += 1.0
                if not obstacles[rs][c]:
                    neighbors += x[rs][c]
                    count += 1.0
                if not obstacles[r][cw]:
                    neighbors += x[r][cw]
                    count += 1.0
                if not obstacles[r][ce]:
                    neighbors += x[r][ce]
                    count += 1.0
                if count > 0:
                    x[r][c] = (x0[r][c] + a * neighbors) / (1.0 + a * count)



def _ns_advect(self, d: list[list[float]], d0: list[list[float]],
               vx: list[list[float]], vy: list[list[float]], dt: float):
    """Advect a field through the velocity field using semi-Lagrangian method."""
    rows, cols = self.ns_rows, self.ns_cols
    dt0_x = dt * cols
    dt0_y = dt * rows
    obstacles = self.ns_obstacles
    for r in range(rows):
        for c in range(cols):
            if obstacles[r][c]:
                d[r][c] = 0.0
                continue
            # Trace backward
            x = c - dt0_x * vx[r][c]
            y = r - dt0_y * vy[r][c]
            # Wrap around
            x = x % cols
            y = y % rows
            # Bilinear interpolation
            i0 = int(y)
            j0 = int(x)
            i1 = (i0 + 1) % rows
            j1 = (j0 + 1) % cols
            s1 = y - i0
            s0 = 1.0 - s1
            t1 = x - j0
            t0 = 1.0 - t1
            d[r][c] = (s0 * (t0 * d0[i0][j0] + t1 * d0[i0][j1]) +
                       s1 * (t0 * d0[i1][j0] + t1 * d0[i1][j1]))



def _ns_project(self):
    """Project velocity field to be divergence-free (pressure solve)."""
    rows, cols = self.ns_rows, self.ns_cols
    vx, vy = self.ns_vx, self.ns_vy
    p, div = self.ns_p, self.ns_div
    obstacles = self.ns_obstacles
    h_x = 1.0 / cols
    h_y = 1.0 / rows

    # Compute divergence
    for r in range(rows):
        for c in range(cols):
            if obstacles[r][c]:
                div[r][c] = 0.0
                p[r][c] = 0.0
                continue
            rn = (r - 1) % rows
            rs = (r + 1) % rows
            cw = (c - 1) % cols
            ce = (c + 1) % cols
            div[r][c] = -0.5 * (h_x * (vx[r][ce] - vx[r][cw]) +
                                 h_y * (vy[rs][c] - vy[rn][c]))
            p[r][c] = 0.0

    # Pressure solve (Gauss-Seidel)
    for _ in range(self.ns_iterations):
        for r in range(rows):
            for c in range(cols):
                if obstacles[r][c]:
                    continue
                rn = (r - 1) % rows
                rs = (r + 1) % rows
                cw = (c - 1) % cols
                ce = (c + 1) % cols
                neighbors = 0.0
                count = 0.0
                if not obstacles[rn][c]:
                    neighbors += p[rn][c]
                    count += 1.0
                if not obstacles[rs][c]:
                    neighbors += p[rs][c]
                    count += 1.0
                if not obstacles[r][cw]:
                    neighbors += p[r][cw]
                    count += 1.0
                if not obstacles[r][ce]:
                    neighbors += p[r][ce]
                    count += 1.0
                if count > 0:
                    p[r][c] = (div[r][c] + neighbors) / count

    # Subtract pressure gradient from velocity
    for r in range(rows):
        for c in range(cols):
            if obstacles[r][c]:
                vx[r][c] = 0.0
                vy[r][c] = 0.0
                continue
            rn = (r - 1) % rows
            rs = (r + 1) % rows
            cw = (c - 1) % cols
            ce = (c + 1) % cols
            vx[r][c] -= 0.5 * (p[r][ce] - p[r][cw]) * cols
            vy[r][c] -= 0.5 * (p[rs][c] - p[rn][c]) * rows



def _ns_step(self):
    """Advance Navier-Stokes simulation by one timestep."""
    rows, cols = self.ns_rows, self.ns_cols
    dt = self.ns_dt
    visc = self.ns_viscosity
    diff = self.ns_diffusion
    preset = self.ns_preset_name

    # Apply continuous sources for some presets
    if preset == "Jet Stream":
        mid = rows // 2
        jet_w = rows // 6
        for r in range(mid - jet_w, mid + jet_w):
            if 0 <= r < rows:
                self.ns_vx[r][0] = 60.0
                self.ns_vx[r][1] = 60.0
                self.ns_dye[r][0] = 1.0
                self.ns_dye[r][1] = 1.0

    if preset == "Karman Vortices":
        for r in range(rows):
            if not self.ns_obstacles[r][0]:
                self.ns_vx[r][0] = 30.0
                self.ns_vx[r][1] = 30.0
                # Dye bands for visualization
                if r % 8 < 2:
                    self.ns_dye[r][0] = 1.0

    # ── Velocity step ──
    # Swap vx/vx0 and vy/vy0
    self.ns_vx0, self.ns_vx = self.ns_vx, self.ns_vx0
    self.ns_vy0, self.ns_vy = self.ns_vy, self.ns_vy0
    # Diffuse velocity
    self._ns_diffuse(self.ns_vx, self.ns_vx0, visc, dt)
    self._ns_diffuse(self.ns_vy, self.ns_vy0, visc, dt)
    # Project to remove divergence
    self._ns_project()
    # Swap for advection
    self.ns_vx0, self.ns_vx = self.ns_vx, self.ns_vx0
    self.ns_vy0, self.ns_vy = self.ns_vy, self.ns_vy0
    # Advect velocity
    self._ns_advect(self.ns_vx, self.ns_vx0, self.ns_vx0, self.ns_vy0, dt)
    self._ns_advect(self.ns_vy, self.ns_vy0, self.ns_vx0, self.ns_vy0, dt)
    # Project again
    self._ns_project()

    # ── Dye/density step ──
    self.ns_dye0, self.ns_dye = self.ns_dye, self.ns_dye0
    self._ns_diffuse(self.ns_dye, self.ns_dye0, diff, dt)
    self.ns_dye0, self.ns_dye = self.ns_dye, self.ns_dye0
    self._ns_advect(self.ns_dye, self.ns_dye0, self.ns_vx, self.ns_vy, dt)

    # Slight dye dissipation
    for r in range(rows):
        for c in range(cols):
            self.ns_dye[r][c] *= 0.999

    self.ns_generation += 1
    self.ns_dye_hue = (self.ns_dye_hue + 0.005) % 1.0



def _handle_ns_menu_key(self, key: int) -> bool:
    """Handle keys in the Navier-Stokes preset menu."""
    if key == -1:
        return True
    n = len(self.NS_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.ns_menu_sel = (self.ns_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.ns_menu_sel = (self.ns_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.ns_menu = False
        self._flash("Navier-Stokes cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._ns_init(self.ns_menu_sel)
        return True
    return True



def _handle_ns_key(self, key: int) -> bool:
    """Handle keys while in Navier-Stokes mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_ns_mode()
        return True
    if key == ord(" "):
        self.ns_running = not self.ns_running
        self._flash("Playing" if self.ns_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self._ns_step()
        return True
    if key == ord("R"):
        self.ns_mode = False
        self.ns_menu = True
        self.ns_menu_sel = 0
        self._flash("Navier-Stokes — select a configuration")
        return True
    # Cursor movement
    if key == curses.KEY_UP or key == ord("k"):
        self.ns_prev_cursor_r = self.ns_cursor_r
        self.ns_prev_cursor_c = self.ns_cursor_c
        self.ns_cursor_r = max(0, self.ns_cursor_r - 1)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.ns_prev_cursor_r = self.ns_cursor_r
        self.ns_prev_cursor_c = self.ns_cursor_c
        self.ns_cursor_r = min(self.ns_rows - 1, self.ns_cursor_r + 1)
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        self.ns_prev_cursor_r = self.ns_cursor_r
        self.ns_prev_cursor_c = self.ns_cursor_c
        self.ns_cursor_c = max(0, self.ns_cursor_c - 1)
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        self.ns_prev_cursor_r = self.ns_cursor_r
        self.ns_prev_cursor_c = self.ns_cursor_c
        self.ns_cursor_c = min(self.ns_cols - 1, self.ns_cursor_c + 1)
        return True
    # Inject dye + velocity at cursor
    if key in (10, 13, curses.KEY_ENTER) or key == ord("f"):
        r, c = self.ns_cursor_r, self.ns_cursor_c
        dr = self.ns_cursor_r - self.ns_prev_cursor_r
        dc = self.ns_cursor_c - self.ns_prev_cursor_c
        rad = self.ns_inject_radius
        strength = self.ns_inject_strength
        for ri in range(max(0, r - rad), min(self.ns_rows, r + rad + 1)):
            for ci in range(max(0, c - rad), min(self.ns_cols, c + rad + 1)):
                if self.ns_obstacles[ri][ci]:
                    continue
                dist = ((ri - r) ** 2 + (ci - c) ** 2) ** 0.5
                if dist <= rad:
                    falloff = 1.0 - dist / (rad + 1)
                    self.ns_dye[ri][ci] = min(1.0, self.ns_dye[ri][ci] + falloff * 0.8)
                    self.ns_vx[ri][ci] += dc * strength * falloff
                    self.ns_vy[ri][ci] += dr * strength * falloff
        self._flash("Dye injected")
        return True
    # Place/remove obstacle
    if key == ord("o"):
        r, c = self.ns_cursor_r, self.ns_cursor_c
        rad = 2
        placing = not self.ns_obstacles[r][c]
        for ri in range(max(0, r - rad), min(self.ns_rows, r + rad + 1)):
            for ci in range(max(0, c - rad), min(self.ns_cols, c + rad + 1)):
                dist = ((ri - r) ** 2 + (ci - c) ** 2) ** 0.5
                if dist <= rad:
                    self.ns_obstacles[ri][ci] = placing
                    if placing:
                        self.ns_vx[ri][ci] = 0.0
                        self.ns_vy[ri][ci] = 0.0
                        self.ns_dye[ri][ci] = 0.0
        self._flash("Obstacle " + ("placed" if placing else "removed"))
        return True
    # Visualization mode
    if key == ord("v"):
        self.ns_viz_mode = (self.ns_viz_mode + 1) % 4
        labels = ["Dye density", "Velocity magnitude", "Vorticity", "Pressure"]
        self._flash(f"Viz: {labels[self.ns_viz_mode]}")
        return True
    # Adjust viscosity
    if key == ord("V"):
        self.ns_viscosity *= 2.0
        self._flash(f"Viscosity: {self.ns_viscosity:.6f}")
        return True
    if key == ord("v") and False:  # handled above
        pass
    if key == ord("b"):
        self.ns_viscosity = max(0.000001, self.ns_viscosity / 2.0)
        self._flash(f"Viscosity: {self.ns_viscosity:.6f}")
        return True
    # Adjust inject strength
    if key == ord("+") or key == ord("="):
        self.ns_inject_strength = min(200.0, self.ns_inject_strength + 10.0)
        self._flash(f"Inject strength: {self.ns_inject_strength:.0f}")
        return True
    if key == ord("-"):
        self.ns_inject_strength = max(10.0, self.ns_inject_strength - 10.0)
        self._flash(f"Inject strength: {self.ns_inject_strength:.0f}")
        return True
    # Adjust inject radius
    if key == ord("]"):
        self.ns_inject_radius = min(10, self.ns_inject_radius + 1)
        self._flash(f"Inject radius: {self.ns_inject_radius}")
        return True
    if key == ord("["):
        self.ns_inject_radius = max(1, self.ns_inject_radius - 1)
        self._flash(f"Inject radius: {self.ns_inject_radius}")
        return True
    # Speed
    if key == ord(">"):
        self.ns_steps_per_frame = min(20, self.ns_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.ns_steps_per_frame}")
        return True
    if key == ord("<"):
        self.ns_steps_per_frame = max(1, self.ns_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.ns_steps_per_frame}")
        return True
    # Clear dye
    if key == ord("c"):
        self.ns_dye = self._ns_make_grid()
        self._flash("Dye cleared")
        return True
    # Clear velocity
    if key == ord("C"):
        self.ns_vx = self._ns_make_grid()
        self.ns_vy = self._ns_make_grid()
        self._flash("Velocity cleared")
        return True
    return True



def _draw_ns_menu(self, max_y: int, max_x: int):
    """Draw the Navier-Stokes preset selection menu."""
    self.stdscr.erase()
    title = "── Navier-Stokes Fluid Dynamics ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "2D incompressible fluid solver with dye advection & pressure projection"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.NS_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.NS_PRESETS):
        y = 5 + i
        if y >= max_y - 12:
            break
        line = f"  {name:<20s} {desc}"
        attr = curses.color_pair(6)
        if i == self.ns_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_lines = [
        "",
        "Real-time 2D Navier-Stokes fluid simulation.",
        "Velocity fields are diffused, advected, and projected to be divergence-free.",
        "Inject dye with the cursor to visualize fluid flow, vortices, and turbulence.",
        "",
        "Controls: arrows/hjkl=cursor  Enter/f=inject dye+velocity  o=obstacle",
        "          v=viz mode  b/V=viscosity  +/-=strength  [/]=radius",
        "          c=clear dye  C=clear velocity  >/<=speed  R=menu  q=exit",
    ]
    base_y = 5 + n + 1
    for i, line in enumerate(info_lines):
        y = base_y + i
        if y >= max_y - 2:
            break
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    footer = "↑/↓ select · Enter confirm · q cancel"
    try:
        self.stdscr.addstr(max_y - 2, max(0, (max_x - len(footer)) // 2), footer,
                           curses.color_pair(7))
    except curses.error:
        pass



def _draw_ns(self, max_y: int, max_x: int):
    """Draw the Navier-Stokes simulation."""
    self.stdscr.erase()
    rows, cols = self.ns_rows, self.ns_cols
    viz = self.ns_viz_mode

    # Compute visualization field
    if viz == 0:
        # Dye density
        field = self.ns_dye
    elif viz == 1:
        # Velocity magnitude
        field = self._ns_make_grid()
        for r in range(rows):
            for c in range(cols):
                field[r][c] = (self.ns_vx[r][c] ** 2 + self.ns_vy[r][c] ** 2) ** 0.5
    elif viz == 2:
        # Vorticity (curl of velocity)
        field = self._ns_make_grid()
        for r in range(rows):
            for c in range(cols):
                rn = (r - 1) % rows
                rs = (r + 1) % rows
                cw = (c - 1) % cols
                ce = (c + 1) % cols
                field[r][c] = (self.ns_vx[rs][c] - self.ns_vx[rn][c]) - \
                              (self.ns_vy[r][ce] - self.ns_vy[r][cw])
    else:
        # Pressure
        field = self.ns_p

    # Find min/max for normalization
    fmax = 0.001
    fmin = 0.0
    if viz == 2 or viz == 3:
        # Signed fields
        for r in range(rows):
            for c in range(cols):
                v = abs(field[r][c])
                if v > fmax:
                    fmax = v
        fmin = -fmax
    else:
        for r in range(rows):
            for c in range(cols):
                if field[r][c] > fmax:
                    fmax = field[r][c]

    for r in range(min(rows, max_y - 2)):
        for c in range(min(cols, (max_x - 1) // 2)):
            sc = c * 2
            if self.ns_obstacles[r][c]:
                try:
                    self.stdscr.addstr(r + 1, sc, "██", curses.color_pair(7))
                except curses.error:
                    pass
                continue

            val = field[r][c]
            if viz == 0:
                # Dye: map to intensity
                norm = min(1.0, max(0.0, val / fmax)) if fmax > 0 else 0.0
                idx = int(norm * 4)
                idx = min(4, max(0, idx))
                ch = self.NS_DYE_CHARS[idx]
                # Color based on dye hue cycling
                import math
                hue_offset = (r * 0.02 + c * 0.015 + self.ns_dye_hue) % 1.0
                if norm < 0.05:
                    color = 0
                elif hue_offset < 0.17:
                    color = 2  # green
                elif hue_offset < 0.33:
                    color = 3  # cyan
                elif hue_offset < 0.50:
                    color = 4  # yellow/blue
                elif hue_offset < 0.67:
                    color = 5  # magenta
                elif hue_offset < 0.83:
                    color = 6  # red
                else:
                    color = 7  # white
                attr = curses.color_pair(color)
                if norm > 0.7:
                    attr |= curses.A_BOLD
            elif viz == 1:
                # Velocity: blue scale
                norm = min(1.0, val / fmax) if fmax > 0 else 0.0
                idx = int(norm * 4)
                idx = min(4, max(0, idx))
                ch = self.NS_VEL_CHARS[idx]
                if norm > 0.5:
                    color = 3  # cyan
                elif norm > 0.2:
                    color = 4  # blue
                else:
                    color = 6
                attr = curses.color_pair(color)
                if norm > 0.7:
                    attr |= curses.A_BOLD
            elif viz == 2:
                # Vorticity: positive = counterclockwise, negative = clockwise
                norm = val / fmax if fmax > 0 else 0.0
                anorm = min(1.0, abs(norm))
                idx = int(anorm * 4)
                idx = min(4, max(0, idx))
                if norm >= 0:
                    ch = self.NS_VORT_POS[idx]
                    color = 5  # magenta
                else:
                    ch = self.NS_VORT_NEG[idx]
                    color = 2  # green
                attr = curses.color_pair(color)
                if anorm > 0.6:
                    attr |= curses.A_BOLD
            else:
                # Pressure
                norm = val / fmax if fmax > 0 else 0.0
                anorm = min(1.0, abs(norm))
                idx = int(anorm * 4)
                idx = min(4, max(0, idx))
                ch = self.NS_DYE_CHARS[idx]
                if norm >= 0:
                    color = 4  # yellow/blue
                else:
                    color = 6  # red
                attr = curses.color_pair(color)

            try:
                self.stdscr.addstr(r + 1, sc, ch * 2 if len(ch) == 1 else ch, attr)
            except curses.error:
                pass

    # Draw cursor
    cr, cc = self.ns_cursor_r, self.ns_cursor_c
    if cr < max_y - 2 and cc * 2 < max_x - 1:
        try:
            self.stdscr.addstr(cr + 1, cc * 2, "╋╋", curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Status bar
    viz_labels = ["Dye", "Velocity", "Vorticity", "Pressure"]
    status = (f" Navier-Stokes: {self.ns_preset_name}"
              f" │ Gen: {self.ns_generation}"
              f" │ {'▶' if self.ns_running else '⏸'}"
              f" │ Viz: {viz_labels[self.ns_viz_mode]}"
              f" │ ν={self.ns_viscosity:.1e}"
              f" │ Cursor: ({self.ns_cursor_r},{self.ns_cursor_c})")
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
        hint = " arrows=move  f/Enter=inject  o=obstacle  v=viz  b/V=viscosity  +/-=strength  [/]=radius  c/C=clear  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register ns mode methods on the App class."""
    App._enter_ns_mode = _enter_ns_mode
    App._exit_ns_mode = _exit_ns_mode
    App._ns_make_grid = _ns_make_grid
    App._ns_init = _ns_init
    App._ns_diffuse = _ns_diffuse
    App._ns_advect = _ns_advect
    App._ns_project = _ns_project
    App._ns_step = _ns_step
    App._handle_ns_menu_key = _handle_ns_menu_key
    App._handle_ns_key = _handle_ns_key
    App._draw_ns_menu = _draw_ns_menu
    App._draw_ns = _draw_ns

