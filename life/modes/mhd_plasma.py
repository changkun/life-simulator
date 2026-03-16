"""Mode: mhd — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_mhd_mode(self):
    """Enter MHD Plasma mode — show preset menu."""
    self.mhd_menu = True
    self.mhd_menu_sel = 0
    self._flash("Magnetohydrodynamics (MHD) Plasma — select a scenario")



def _exit_mhd_mode(self):
    """Exit MHD Plasma mode."""
    self.mhd_mode = False
    self.mhd_menu = False
    self.mhd_running = False
    self.mhd_rho = []
    self.mhd_vx = []
    self.mhd_vy = []
    self.mhd_bx = []
    self.mhd_by = []
    self._flash("MHD Plasma mode OFF")



def _mhd_init(self, preset_idx: int):
    """Initialize the MHD simulation with the given preset."""
    name, _desc, resistivity, viscosity, pressure, init_type = self.MHD_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.mhd_rows = rows
    self.mhd_cols = cols
    self.mhd_resistivity = resistivity
    self.mhd_viscosity = viscosity
    self.mhd_pressure_coeff = pressure
    self.mhd_preset_name = name
    self.mhd_generation = 0
    self.mhd_steps_per_frame = 2
    self.mhd_view = "current"

    # Initialize grids
    self.mhd_rho = [[1.0] * cols for _ in range(rows)]
    self.mhd_vx = [[0.0] * cols for _ in range(rows)]
    self.mhd_vy = [[0.0] * cols for _ in range(rows)]
    self.mhd_bx = [[0.0] * cols for _ in range(rows)]
    self.mhd_by = [[0.0] * cols for _ in range(rows)]

    cr, cc = rows // 2, cols // 2

    if init_type == "harris":
        # Harris current sheet: Bx reverses sign across midplane
        # with a thin current layer — classic reconnection setup
        width = max(2.0, rows * 0.05)
        for r in range(rows):
            y_norm = (r - cr) / width
            bx_val = math.tanh(y_norm)
            for c in range(cols):
                self.mhd_bx[r][c] = bx_val
                # Small perturbation to seed tearing instability
                px = (c - cc) / max(cols, 1) * 2.0 * math.pi
                self.mhd_vy[r][c] = 0.01 * math.sin(px) * math.exp(-y_norm * y_norm)
                # Pressure balance: higher density at the sheet
                self.mhd_rho[r][c] = 1.0 + 0.5 / (math.cosh(y_norm) ** 2)

    elif init_type == "orszag_tang":
        # Orszag-Tang vortex: classic MHD turbulence test problem
        for r in range(rows):
            for c in range(cols):
                x = c / cols * 2.0 * math.pi
                y = r / rows * 2.0 * math.pi
                self.mhd_vx[r][c] = -0.5 * math.sin(y)
                self.mhd_vy[r][c] = 0.5 * math.sin(x)
                self.mhd_bx[r][c] = -math.sin(y)
                self.mhd_by[r][c] = math.sin(2.0 * x)

    elif init_type == "island":
        # Magnetic island / tearing mode
        width = max(2.0, rows * 0.08)
        for r in range(rows):
            y_norm = (r - cr) / width
            for c in range(cols):
                x_norm = (c - cc) / max(cols, 1) * 4.0 * math.pi
                self.mhd_bx[r][c] = math.tanh(y_norm)
                # Island perturbation
                self.mhd_by[r][c] = 0.1 * math.sin(x_norm) * math.exp(-y_norm * y_norm * 0.5)
                self.mhd_rho[r][c] = 1.0 + 0.3 / (math.cosh(y_norm) ** 2)

    elif init_type == "blast":
        # Blast wave in magnetized plasma
        br = min(rows, cols) * 0.08
        for r in range(rows):
            for c in range(cols):
                dx = c - cc
                dy = r - cr
                dist = math.sqrt(dx * dx + dy * dy)
                # Uniform background B field
                self.mhd_bx[r][c] = 0.5
                # High pressure/density region at center
                if dist < br:
                    self.mhd_rho[r][c] = 3.0 * math.exp(-(dist / br) ** 2 * 2.0)
                # Outward velocity from center
                if dist > 0.5:
                    self.mhd_vx[r][c] = 0.3 * dx / dist * math.exp(-(dist / br) ** 2)
                    self.mhd_vy[r][c] = 0.3 * dy / dist * math.exp(-(dist / br) ** 2)

    elif init_type == "kh":
        # Kelvin-Helmholtz shear flow with magnetic field
        width = max(2.0, rows * 0.06)
        for r in range(rows):
            y_norm = (r - cr) / width
            for c in range(cols):
                x_norm = c / cols * 2.0 * math.pi
                self.mhd_vx[r][c] = 0.5 * math.tanh(y_norm)
                # Small transverse perturbation
                self.mhd_vy[r][c] = 0.02 * math.sin(x_norm * 2.0) * math.exp(-y_norm * y_norm * 0.5)
                # Background magnetic field along flow
                self.mhd_bx[r][c] = 0.3
                self.mhd_rho[r][c] = 1.0 + 0.2 / (math.cosh(y_norm) ** 2)

    elif init_type == "double_harris":
        # Two current sheets at 1/4 and 3/4 height
        width = max(2.0, rows * 0.04)
        for r in range(rows):
            y1 = (r - rows // 4) / width
            y2 = (r - 3 * rows // 4) / width
            for c in range(cols):
                px = (c - cc) / max(cols, 1) * 2.0 * math.pi
                self.mhd_bx[r][c] = math.tanh(y1) - math.tanh(y2) - 1.0
                self.mhd_vy[r][c] = (0.01 * math.sin(px) *
                                      (math.exp(-y1 * y1) + math.exp(-y2 * y2)))
                self.mhd_rho[r][c] = (1.0 + 0.3 / (math.cosh(y1) ** 2) +
                                       0.3 / (math.cosh(y2) ** 2))

    elif init_type == "flux_rope":
        # Twisted magnetic structure
        radius = min(rows, cols) * 0.2
        for r in range(rows):
            for c in range(cols):
                dx = c - cc
                dy = r - cr
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 0.5:
                    dist = 0.5
                norm_r = dist / radius
                twist = math.exp(-norm_r * norm_r)
                # Azimuthal B field (twisted rope)
                self.mhd_bx[r][c] = -twist * dy / dist * 0.8
                self.mhd_by[r][c] = twist * dx / dist * 0.8
                self.mhd_rho[r][c] = 1.0 + 0.5 * twist

    elif init_type == "random":
        # Random turbulent initial conditions
        for r in range(rows):
            for c in range(cols):
                self.mhd_vx[r][c] = random.gauss(0, 0.15)
                self.mhd_vy[r][c] = random.gauss(0, 0.15)
                self.mhd_bx[r][c] = random.gauss(0, 0.3)
                self.mhd_by[r][c] = random.gauss(0, 0.3)
                self.mhd_rho[r][c] = 1.0 + random.uniform(-0.2, 0.2)

    self.mhd_mode = True
    self.mhd_menu = False
    self.mhd_running = False
    self._flash(f"MHD Plasma: {name} — Space to start")



def _mhd_step(self):
    """Advance the MHD simulation by one time step.

    Solves the incompressible resistive MHD equations using finite differences:
        ∂ρ/∂t = -∇·(ρv) + ν_ρ∇²ρ          (continuity)
        ∂v/∂t = -(v·∇)v - ∇p/ρ + (J×B)/ρ + ν∇²v   (momentum + Lorentz force)
        ∂B/∂t = ∇×(v×B) + η∇²B             (induction + resistive diffusion)
    where J = ∇×B is the current density.
    """
    rho = self.mhd_rho
    vx = self.mhd_vx
    vy = self.mhd_vy
    bx = self.mhd_bx
    by = self.mhd_by
    rows, cols = self.mhd_rows, self.mhd_cols
    eta = self.mhd_resistivity
    nu = self.mhd_viscosity
    pcoeff = self.mhd_pressure_coeff
    dt = 0.02

    new_rho = [[0.0] * cols for _ in range(rows)]
    new_vx = [[0.0] * cols for _ in range(rows)]
    new_vy = [[0.0] * cols for _ in range(rows)]
    new_bx = [[0.0] * cols for _ in range(rows)]
    new_by = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        rp = (r + 1) % rows
        rm = (r - 1) % rows
        for c in range(cols):
            cp = (c + 1) % cols
            cm = (c - 1) % cols

            # Local values
            rv = rho[r][c]
            u = vx[r][c]
            v = vy[r][c]
            bxv = bx[r][c]
            byv = by[r][c]

            # Ensure density stays positive
            if rv < 0.1:
                rv = 0.1

            inv_rho = 1.0 / rv

            # Laplacians (5-point stencil, periodic)
            lap_vx = vx[rm][c] + vx[rp][c] + vx[r][cm] + vx[r][cp] - 4.0 * u
            lap_vy = vy[rm][c] + vy[rp][c] + vy[r][cm] + vy[r][cp] - 4.0 * v
            lap_bx = bx[rm][c] + bx[rp][c] + bx[r][cm] + bx[r][cp] - 4.0 * bxv
            lap_by = by[rm][c] + by[rp][c] + by[r][cm] + by[r][cp] - 4.0 * byv
            lap_rho = rho[rm][c] + rho[rp][c] + rho[r][cm] + rho[r][cp] - 4.0 * rv

            # Gradients (central differences)
            drho_dx = (rho[r][cp] - rho[r][cm]) * 0.5
            drho_dy = (rho[rp][c] - rho[rm][c]) * 0.5

            dvx_dx = (vx[r][cp] - vx[r][cm]) * 0.5
            dvx_dy = (vx[rp][c] - vx[rm][c]) * 0.5
            dvy_dx = (vy[r][cp] - vy[r][cm]) * 0.5
            dvy_dy = (vy[rp][c] - vy[rm][c]) * 0.5

            dbx_dx = (bx[r][cp] - bx[r][cm]) * 0.5
            dbx_dy = (bx[rp][c] - bx[rm][c]) * 0.5
            dby_dx = (by[r][cp] - by[r][cm]) * 0.5
            dby_dy = (by[rp][c] - by[rm][c]) * 0.5

            # Current density: Jz = dBy/dx - dBx/dy (only z-component in 2D)
            jz = dby_dx - dbx_dy

            # Lorentz force: J × B (in 2D: Jz × B gives force in xy-plane)
            fx_lorentz = jz * byv
            fy_lorentz = -jz * bxv

            # Pressure gradient (isothermal: p = pcoeff * rho)
            fx_pressure = -pcoeff * drho_dx * inv_rho
            fy_pressure = -pcoeff * drho_dy * inv_rho

            # Advection: -(v · ∇)v
            fx_adv = -(u * dvx_dx + v * dvx_dy)
            fy_adv = -(u * dvy_dx + v * dvy_dy)

            # Momentum equation
            dvx_dt = fx_adv + fx_pressure + fx_lorentz * inv_rho + nu * lap_vx
            dvy_dt = fy_adv + fy_pressure + fy_lorentz * inv_rho + nu * lap_vy

            # Induction equation: ∂B/∂t = ∇×(v×B) + η∇²B
            # In 2D: v×B has only z-component: Ez = u*By - v*Bx
            # ∂Bx/∂t = -∂Ez/∂y + η∇²Bx
            # ∂By/∂t =  ∂Ez/∂x + η∇²By
            # Compute Ez at neighboring points for curl
            ez_rp = vx[rp][c] * by[rp][c] - vy[rp][c] * bx[rp][c]
            ez_rm = vx[rm][c] * by[rm][c] - vy[rm][c] * bx[rm][c]
            ez_cp = vx[r][cp] * by[r][cp] - vy[r][cp] * bx[r][cp]
            ez_cm = vx[r][cm] * by[r][cm] - vy[r][cm] * bx[r][cm]

            dez_dy = (ez_rp - ez_rm) * 0.5
            dez_dx = (ez_cp - ez_cm) * 0.5

            dbx_dt = -dez_dy + eta * lap_bx
            dby_dt = dez_dx + eta * lap_by

            # Continuity: ∂ρ/∂t = -∇·(ρv) + small diffusion for stability
            drho_dt = -(u * drho_dx + v * drho_dy + rv * (dvx_dx + dvy_dy)) + 0.01 * lap_rho

            # Euler step
            new_rho[r][c] = max(0.1, rv + dt * drho_dt)
            new_vx[r][c] = u + dt * dvx_dt
            new_vy[r][c] = v + dt * dvy_dt
            new_bx[r][c] = bxv + dt * dbx_dt
            new_by[r][c] = byv + dt * dby_dt

            # Soft clamp to prevent blowup
            clamp = 2.0
            new_vx[r][c] = max(-clamp, min(clamp, new_vx[r][c]))
            new_vy[r][c] = max(-clamp, min(clamp, new_vy[r][c]))
            new_bx[r][c] = max(-clamp, min(clamp, new_bx[r][c]))
            new_by[r][c] = max(-clamp, min(clamp, new_by[r][c]))

    self.mhd_rho = new_rho
    self.mhd_vx = new_vx
    self.mhd_vy = new_vy
    self.mhd_bx = new_bx
    self.mhd_by = new_by
    self.mhd_generation += 1



def _handle_mhd_menu_key(self, key: int) -> bool:
    """Handle input in MHD Plasma preset menu."""
    presets = self.MHD_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.mhd_menu_sel = (self.mhd_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.mhd_menu_sel = (self.mhd_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._mhd_init(self.mhd_menu_sel)
    elif key == ord("q") or key == 27:
        self.mhd_menu = False
        self._flash("MHD Plasma cancelled")
    return True



def _handle_mhd_key(self, key: int) -> bool:
    """Handle input in active MHD Plasma simulation."""
    if key == ord("q") or key == 27:
        self._exit_mhd_mode()
        return True
    if key == ord(" "):
        self.mhd_running = not self.mhd_running
        return True
    if key == ord("n") or key == ord("."):
        self._mhd_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.MHD_PRESETS) if p[0] == self.mhd_preset_name),
            0,
        )
        self._mhd_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.mhd_mode = False
        self.mhd_running = False
        self.mhd_menu = True
        self.mhd_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.mhd_steps_per_frame) if self.mhd_steps_per_frame in choices else 0
        self.mhd_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.mhd_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.mhd_steps_per_frame) if self.mhd_steps_per_frame in choices else 0
        self.mhd_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.mhd_steps_per_frame} steps/frame")
        return True
    # Resistivity: e/E
    if key == ord("e"):
        self.mhd_resistivity = max(0.001, self.mhd_resistivity - 0.002)
        self._flash(f"Resistivity η={self.mhd_resistivity:.3f}")
        return True
    if key == ord("E"):
        self.mhd_resistivity = min(0.1, self.mhd_resistivity + 0.002)
        self._flash(f"Resistivity η={self.mhd_resistivity:.3f}")
        return True
    # Viscosity: v/V
    if key == ord("w"):
        self.mhd_viscosity = max(0.001, self.mhd_viscosity - 0.002)
        self._flash(f"Viscosity ν={self.mhd_viscosity:.3f}")
        return True
    if key == ord("W"):
        self.mhd_viscosity = min(0.1, self.mhd_viscosity + 0.002)
        self._flash(f"Viscosity ν={self.mhd_viscosity:.3f}")
        return True
    # View mode: v
    if key == ord("v"):
        views = ["current", "density", "magnetic", "velocity"]
        idx = views.index(self.mhd_view) if self.mhd_view in views else 0
        self.mhd_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.mhd_view}")
        return True
    # Perturb: p — add random magnetic perturbation
    if key == ord("p"):
        rows, cols = self.mhd_rows, self.mhd_cols
        pr = random.randint(3, rows - 4)
        pc = random.randint(3, cols - 4)
        for dr in range(-4, 5):
            for dc in range(-4, 5):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    d = math.sqrt(dr * dr + dc * dc)
                    amp = 0.3 * math.exp(-d * d * 0.2)
                    self.mhd_bx[nr][nc] += amp * random.uniform(-1, 1)
                    self.mhd_by[nr][nc] += amp * random.uniform(-1, 1)
        self._flash("Magnetic perturbation!")
        return True
    # Mouse click to add perturbation
    if key == curses.KEY_MOUSE:
        try:
            _, mx, my, _, _ = curses.getmouse()
            r = my - 1
            c = mx // 2
            rows, cols = self.mhd_rows, self.mhd_cols
            if 0 <= r < rows and 0 <= c < cols:
                for rr in range(-4, 5):
                    for rc in range(-4, 5):
                        nr, nc = r + rr, c + rc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            d = math.sqrt(rr * rr + rc * rc)
                            amp = 0.4 * math.exp(-d * d * 0.2)
                            self.mhd_by[nr][nc] += amp
                            self.mhd_rho[nr][nc] += amp * 0.5
        except curses.error:
            pass
        return True
    return True



def _draw_mhd_menu(self, max_y: int, max_x: int):
    """Draw the MHD Plasma preset selection menu."""
    self.stdscr.erase()
    title = "── Magnetohydrodynamics (MHD) Plasma ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, eta, nu, pr, init) in enumerate(self.MHD_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.mhd_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.mhd_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:22s} η={eta:<6.3f} ν={nu:<6.3f} P={pr:<4.1f}  {desc}"
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



def _draw_mhd(self, max_y: int, max_x: int):
    """Draw the active MHD Plasma simulation.

    Visualization depends on view mode:
    - current: current density Jz = dBy/dx - dBx/dy (shows reconnection sites)
    - density: plasma density
    - magnetic: magnetic field magnitude
    - velocity: flow speed
    """
    self.stdscr.erase()
    rows, cols = self.mhd_rows, self.mhd_cols
    state = "▶ RUNNING" if self.mhd_running else "⏸ PAUSED"

    title = (f" ⚡ MHD Plasma: {self.mhd_preset_name}  |  step {self.mhd_generation}"
             f"  |  η={self.mhd_resistivity:.3f} ν={self.mhd_viscosity:.3f}"
             f"  |  view={self.mhd_view}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    bx = self.mhd_bx
    by = self.mhd_by
    rho = self.mhd_rho
    vxg = self.mhd_vx
    vyg = self.mhd_vy

    for r in range(view_rows):
        sy = 1 + r
        rp = (r + 1) % rows
        rm = (r - 1) % rows
        for col in range(view_cols):
            sx = col * 2
            cp = (col + 1) % cols
            cm = (col - 1) % cols

            if self.mhd_view == "current":
                # Current density: Jz = dBy/dx - dBx/dy
                jz = ((by[r][cp] - by[r][cm]) * 0.5 -
                      (bx[rp][col] - bx[rm][col]) * 0.5)
                val = jz
                # Signed quantity — use diverging colormap
                mag = min(abs(val) * 3.0, 1.0)
                if mag < 0.02:
                    continue
                if mag > 0.7:
                    ch = "██"
                elif mag > 0.4:
                    ch = "▓▓"
                elif mag > 0.2:
                    ch = "▒▒"
                elif mag > 0.08:
                    ch = "░░"
                else:
                    ch = "··"
                if val > 0:
                    # Positive current — warm colors
                    if mag > 0.6:
                        attr = curses.color_pair(3) | curses.A_BOLD  # yellow
                    elif mag > 0.3:
                        attr = curses.color_pair(1) | curses.A_BOLD  # red
                    else:
                        attr = curses.color_pair(1)  # dim red
                else:
                    # Negative current — cool colors
                    if mag > 0.6:
                        attr = curses.color_pair(6) | curses.A_BOLD  # cyan
                    elif mag > 0.3:
                        attr = curses.color_pair(4) | curses.A_BOLD  # blue
                    else:
                        attr = curses.color_pair(4)  # dim blue

            elif self.mhd_view == "density":
                val = rho[r][col] - 0.8  # offset so background ~1.0 is dim
                mag = min(abs(val) * 2.0, 1.0)
                if mag < 0.02:
                    continue
                if mag > 0.7:
                    ch = "██"
                elif mag > 0.4:
                    ch = "▓▓"
                elif mag > 0.2:
                    ch = "▒▒"
                else:
                    ch = "░░"
                if val > 0.5:
                    attr = curses.color_pair(3) | curses.A_BOLD  # bright yellow (high density)
                elif val > 0.2:
                    attr = curses.color_pair(2) | curses.A_BOLD  # green
                elif val > 0:
                    attr = curses.color_pair(2)  # dim green
                else:
                    attr = curses.color_pair(4) | curses.A_DIM  # blue (low density)

            elif self.mhd_view == "magnetic":
                bmag = math.sqrt(bx[r][col] ** 2 + by[r][col] ** 2)
                mag = min(bmag * 1.5, 1.0)
                if mag < 0.02:
                    continue
                if mag > 0.7:
                    ch = "██"
                elif mag > 0.4:
                    ch = "▓▓"
                elif mag > 0.2:
                    ch = "▒▒"
                else:
                    ch = "░░"
                # Color by field direction
                angle = math.atan2(by[r][col], bx[r][col])
                if -0.78 < angle < 0.78:
                    attr = curses.color_pair(1) | curses.A_BOLD  # red (rightward)
                elif 0.78 < angle < 2.36:
                    attr = curses.color_pair(3) | curses.A_BOLD  # yellow (upward)
                elif angle > 2.36 or angle < -2.36:
                    attr = curses.color_pair(6) | curses.A_BOLD  # cyan (leftward)
                else:
                    attr = curses.color_pair(4) | curses.A_BOLD  # blue (downward)

            else:  # velocity
                spd = math.sqrt(vxg[r][col] ** 2 + vyg[r][col] ** 2)
                mag = min(spd * 3.0, 1.0)
                if mag < 0.02:
                    continue
                if mag > 0.7:
                    ch = "██"
                elif mag > 0.4:
                    ch = "▓▓"
                elif mag > 0.2:
                    ch = "▒▒"
                else:
                    ch = "░░"
                if mag > 0.6:
                    attr = curses.color_pair(3) | curses.A_BOLD  # yellow (fast)
                elif mag > 0.3:
                    attr = curses.color_pair(5) | curses.A_BOLD  # magenta
                else:
                    attr = curses.color_pair(5) | curses.A_DIM  # dim magenta

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
            hint = " [Space]=play [n]=step [e/E]=resistivity [w/W]=viscosity [v]=view [p]=perturb [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


#  Strange Attractors — Mode |
# ══════════════════════════════════════════════════════════════════════

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




def register(App):
    """Register mhd mode methods on the App class."""
    from life.modes.chemotaxis import MHD_PRESETS
    App.MHD_PRESETS = MHD_PRESETS
    App._enter_mhd_mode = _enter_mhd_mode
    App._exit_mhd_mode = _exit_mhd_mode
    App._mhd_init = _mhd_init
    App._mhd_step = _mhd_step
    App._handle_mhd_menu_key = _handle_mhd_menu_key
    App._handle_mhd_key = _handle_mhd_key
    App._draw_mhd_menu = _draw_mhd_menu
    App._draw_mhd = _draw_mhd

