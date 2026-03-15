"""Mode: galaxy — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import DENSITY_CHARS
from life.grid import Grid

def _galaxy_build_particles(self, preset: str):
    """Generate initial particle distribution for a galaxy preset."""
    rows, cols = self.galaxy_rows, self.galaxy_cols
    cx, cy = cols / 2.0, rows / 2.0
    self.galaxy_particles = []
    self.galaxy_halo_mass = 1000.0
    self.galaxy_halo_radius = 30.0
    self.galaxy_rotation_speed = 1.0
    self.galaxy_gas_density = 0.5
    self.galaxy_arm_count = 2

    if preset == "milky_way":
        # Central bulge
        for _ in range(50):
            r = random.gauss(0, 2.5)
            angle = random.uniform(0, 2 * math.pi)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            speed = 1.5 * random.gauss(0, 1)
            va = angle + math.pi / 2
            vx = speed * math.cos(va)
            vy = speed * math.sin(va)
            self.galaxy_particles.append([x, y, vx, vy, 1.0, 0.0])
        # Disk stars with spiral perturbation
        for i in range(200):
            r = random.uniform(3, min(cx, cy) * 0.8)
            base_angle = random.uniform(0, 2 * math.pi)
            # Logarithmic spiral perturbation
            spiral_offset = 0.3 * math.log(1 + r) * self.galaxy_arm_count
            arm = random.randint(0, self.galaxy_arm_count - 1)
            angle = base_angle + arm * (2 * math.pi / self.galaxy_arm_count)
            angle += spiral_offset + random.gauss(0, 0.3)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            # Circular orbital velocity
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            v_circ *= self.galaxy_rotation_speed
            va = angle + math.pi / 2
            vx = v_circ * math.cos(va) + random.gauss(0, 0.2)
            vy = v_circ * math.sin(va) + random.gauss(0, 0.2)
            self.galaxy_particles.append([x, y, vx, vy, 1.0, 0.0])
        # Gas disk
        for _ in range(100):
            r = random.uniform(2, min(cx, cy) * 0.7)
            arm = random.randint(0, self.galaxy_arm_count - 1)
            spiral_offset = 0.3 * math.log(1 + r) * self.galaxy_arm_count
            angle = random.uniform(0, 2 * math.pi) + arm * (2 * math.pi / self.galaxy_arm_count) + spiral_offset
            angle += random.gauss(0, 0.2)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            v_circ *= self.galaxy_rotation_speed
            va = angle + math.pi / 2
            vx = v_circ * math.cos(va) + random.gauss(0, 0.1)
            vy = v_circ * math.sin(va) + random.gauss(0, 0.1)
            self.galaxy_particles.append([x, y, vx, vy, 0.5, 1.0])

    elif preset == "grand_design":
        self.galaxy_arm_count = 2
        for _ in range(60):
            r = random.gauss(0, 2.0)
            angle = random.uniform(0, 2 * math.pi)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            speed = 1.2 * random.gauss(0, 1)
            va = angle + math.pi / 2
            self.galaxy_particles.append([x, y, speed * math.cos(va), speed * math.sin(va), 1.0, 0.0])
        for _ in range(250):
            r = random.uniform(3, min(cx, cy) * 0.85)
            arm = random.randint(0, 1)
            spiral_offset = 0.4 * math.log(1 + r) * 2
            angle = random.uniform(-0.2, 0.2) + arm * math.pi + spiral_offset
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            va = angle + math.pi / 2
            vx = v_circ * math.cos(va) + random.gauss(0, 0.15)
            vy = v_circ * math.sin(va) + random.gauss(0, 0.15)
            self.galaxy_particles.append([x, y, vx, vy, 1.0, 0.0])
        for _ in range(180):
            r = random.uniform(2, min(cx, cy) * 0.8)
            arm = random.randint(0, 1)
            spiral_offset = 0.4 * math.log(1 + r) * 2
            angle = random.uniform(-0.15, 0.15) + arm * math.pi + spiral_offset
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            va = angle + math.pi / 2
            self.galaxy_particles.append([x, y, v_circ * math.cos(va), v_circ * math.sin(va), 0.5, 1.0])

    elif preset == "whirlpool":
        # Main galaxy
        for _ in range(40):
            r = random.gauss(0, 2.0)
            angle = random.uniform(0, 2 * math.pi)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            speed = 1.0 * random.gauss(0, 1)
            va = angle + math.pi / 2
            self.galaxy_particles.append([x, y, speed * math.cos(va), speed * math.sin(va), 1.0, 0.0])
        for _ in range(180):
            r = random.uniform(3, min(cx, cy) * 0.6)
            arm = random.randint(0, 1)
            spiral_offset = 0.35 * math.log(1 + r) * 2
            angle = random.uniform(0, 2 * math.pi) + arm * math.pi + spiral_offset
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            va = angle + math.pi / 2
            vx = v_circ * math.cos(va) + random.gauss(0, 0.15)
            vy = v_circ * math.sin(va) + random.gauss(0, 0.15)
            self.galaxy_particles.append([x, y, vx, vy, 1.0, 0.0])
        # Companion galaxy offset
        comp_cx = cx + 30
        comp_cy = cy - 10
        for _ in range(60):
            r = random.uniform(0, 8)
            angle = random.uniform(0, 2 * math.pi)
            x = comp_cx + r * math.cos(angle)
            y = comp_cy + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * 200.0 * r / (r + 10.0) ** 2 + 0.1)
            va = angle + math.pi / 2
            # Also give it bulk velocity toward main galaxy
            vx = v_circ * math.cos(va) - 1.5
            vy = v_circ * math.sin(va) + 0.5
            self.galaxy_particles.append([x, y, vx, vy, 1.0, 0.0])

    elif preset == "elliptical":
        for _ in range(300):
            r = abs(random.gauss(0, min(cx, cy) * 0.3))
            angle = random.uniform(0, 2 * math.pi)
            # Slightly elliptical
            x = cx + r * math.cos(angle) * 1.3
            y = cy + r * math.sin(angle)
            # Isotropic velocity dispersion, no net rotation
            vx = random.gauss(0, 1.5)
            vy = random.gauss(0, 1.5)
            ptype = 0.0 if random.random() > 0.1 else 1.0
            self.galaxy_particles.append([x, y, vx, vy, 1.0, ptype])

    elif preset == "dwarf":
        for _ in range(80):
            r = abs(random.gauss(0, min(cx, cy) * 0.2))
            angle = random.uniform(0, 2 * math.pi)
            x = cx + r * math.cos(angle) + random.gauss(0, 2)
            y = cy + r * math.sin(angle) + random.gauss(0, 2)
            vx = random.gauss(0, 0.8)
            vy = random.gauss(0, 0.8)
            ptype = 0.0 if random.random() > 0.3 else 1.0
            self.galaxy_particles.append([x, y, vx, vy, 0.8, ptype])
        self.galaxy_halo_mass = 300.0
        self.galaxy_halo_radius = 15.0

    elif preset == "merger":
        # Galaxy 1 (left)
        g1x, g1y = cx - 15, cy
        for _ in range(120):
            r = random.uniform(0, min(cx, cy) * 0.35)
            arm = random.randint(0, 1)
            spiral_offset = 0.3 * math.log(1 + r) * 2
            angle = random.uniform(0, 2 * math.pi) + arm * math.pi + spiral_offset
            x = g1x + r * math.cos(angle)
            y = g1y + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * 500.0 * r / (r + 20.0) ** 2 + 0.1)
            va = angle + math.pi / 2
            vx = v_circ * math.cos(va) + 0.8
            vy = v_circ * math.sin(va) + 0.3
            ptype = 0.0 if random.random() > 0.3 else 1.0
            self.galaxy_particles.append([x, y, vx, vy, 1.0, ptype])
        # Galaxy 2 (right)
        g2x, g2y = cx + 15, cy
        for _ in range(120):
            r = random.uniform(0, min(cx, cy) * 0.35)
            arm = random.randint(0, 1)
            spiral_offset = 0.3 * math.log(1 + r) * 2
            angle = random.uniform(0, 2 * math.pi) + arm * math.pi + spiral_offset
            x = g2x + r * math.cos(angle)
            y = g2y + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * 500.0 * r / (r + 20.0) ** 2 + 0.1)
            va = angle + math.pi / 2
            vx = v_circ * math.cos(va) - 0.8
            vy = v_circ * math.sin(va) - 0.3
            ptype = 0.0 if random.random() > 0.3 else 1.0
            self.galaxy_particles.append([x, y, vx, vy, 1.0, ptype])

    elif preset == "ring":
        # Central cluster
        for _ in range(40):
            r = random.gauss(0, 2.0)
            angle = random.uniform(0, 2 * math.pi)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            vx = random.gauss(0, 0.5)
            vy = random.gauss(0, 0.5)
            self.galaxy_particles.append([x, y, vx, vy, 1.5, 0.0])
        # Expanding ring
        ring_r = min(cx, cy) * 0.5
        for _ in range(200):
            angle = random.uniform(0, 2 * math.pi)
            r = ring_r + random.gauss(0, 2.0)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            # Outward expansion + circular orbit
            v_rad = 0.5
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            va = angle + math.pi / 2
            vx = v_rad * math.cos(angle) + v_circ * math.cos(va)
            vy = v_rad * math.sin(angle) + v_circ * math.sin(va)
            ptype = 0.0 if random.random() > 0.4 else 1.0
            self.galaxy_particles.append([x, y, vx, vy, 1.0, ptype])

    elif preset == "barred":
        self.galaxy_arm_count = 2
        # Strong central bar
        for _ in range(80):
            bx = random.uniform(-8, 8)
            by = random.gauss(0, 1.5)
            angle = 0.4  # bar tilt
            rx = bx * math.cos(angle) - by * math.sin(angle)
            ry = bx * math.sin(angle) + by * math.cos(angle)
            x = cx + rx
            y = cy + ry
            r = math.sqrt(rx * rx + ry * ry) + 0.1
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            pa = math.atan2(ry, rx) + math.pi / 2
            vx = v_circ * math.cos(pa) * 0.7 + random.gauss(0, 0.3)
            vy = v_circ * math.sin(pa) * 0.7 + random.gauss(0, 0.3)
            self.galaxy_particles.append([x, y, vx, vy, 1.2, 0.0])
        # Trailing spiral arms from bar ends
        for _ in range(180):
            r = random.uniform(8, min(cx, cy) * 0.8)
            arm = random.randint(0, 1)
            spiral_offset = 0.35 * math.log(1 + r) * 2
            angle = arm * math.pi + spiral_offset + random.gauss(0, 0.25) + 0.4
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            v_circ = math.sqrt(self.galaxy_grav_const * self.galaxy_halo_mass * r / (r + self.galaxy_halo_radius) ** 2 + 0.1)
            va = angle + math.pi / 2
            vx = v_circ * math.cos(va) + random.gauss(0, 0.15)
            vy = v_circ * math.sin(va) + random.gauss(0, 0.15)
            ptype = 0.0 if random.random() > 0.35 else 1.0
            self.galaxy_particles.append([x, y, vx, vy, 1.0, ptype])



def _galaxy_init(self, preset: str):
    """Initialize galaxy simulation for a given preset."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.galaxy_rows = max_y - 3
    self.galaxy_cols = (max_x - 1) // 2
    if self.galaxy_rows < 10:
        self.galaxy_rows = 10
    if self.galaxy_cols < 10:
        self.galaxy_cols = 10
    self.galaxy_generation = 0
    self.galaxy_total_ke = 0.0
    self.galaxy_grav_const = 1.0
    self.galaxy_dt = 0.03
    self.galaxy_softening = 1.0
    self.galaxy_view = "combined"
    self.galaxy_show_halo = False
    self.galaxy_density = [[0.0] * self.galaxy_cols for _ in range(self.galaxy_rows)]
    self.galaxy_gas_grid = [[0.0] * self.galaxy_cols for _ in range(self.galaxy_rows)]
    self._galaxy_build_particles(preset)



def _galaxy_step(self):
    """Advance galaxy simulation by one timestep using leapfrog integration."""
    particles = self.galaxy_particles
    if not particles:
        return
    rows, cols = self.galaxy_rows, self.galaxy_cols
    cx, cy = cols / 2.0, rows / 2.0
    dt = self.galaxy_dt
    G = self.galaxy_grav_const
    halo_mass = self.galaxy_halo_mass
    halo_r = self.galaxy_halo_radius
    soft = self.galaxy_softening
    n = len(particles)

    # Build density grid for grid-based force calculation
    grid_res = 4  # bin size for grid force
    gw = (cols // grid_res) + 1
    gh = (rows // grid_res) + 1
    grid_mass = [[0.0] * gw for _ in range(gh)]
    grid_cx = [[0.0] * gw for _ in range(gh)]
    grid_cy_arr = [[0.0] * gw for _ in range(gh)]

    for p in particles:
        gi = int(p[1] / grid_res)
        gj = int(p[0] / grid_res)
        if 0 <= gi < gh and 0 <= gj < gw:
            grid_mass[gi][gj] += p[4]
            grid_cx[gi][gj] += p[0] * p[4]
            grid_cy_arr[gi][gj] += p[1] * p[4]

    # Compute center of mass for occupied bins
    for gi in range(gh):
        for gj in range(gw):
            m = grid_mass[gi][gj]
            if m > 0:
                grid_cx[gi][gj] /= m
                grid_cy_arr[gi][gj] /= m
            else:
                grid_cx[gi][gj] = (gj + 0.5) * grid_res
                grid_cy_arr[gi][gj] = (gi + 0.5) * grid_res

    total_ke = 0.0

    for p in particles:
        px, py = p[0], p[1]
        ax, ay = 0.0, 0.0

        # 1. Dark matter halo gravity (NFW-like)
        dx = px - cx
        dy = py - cy
        r = math.sqrt(dx * dx + dy * dy) + 0.01
        # F = -G * M_halo * r / (r + r_s)^2
        f_halo = -G * halo_mass * r / ((r + halo_r) ** 2)
        ax += f_halo * dx / r
        ay += f_halo * dy / r

        # 2. Grid-based particle-particle gravity
        pi = int(py / grid_res)
        pj = int(px / grid_res)
        for di in range(-2, 3):
            for dj in range(-2, 3):
                gi = pi + di
                gj = pj + dj
                if 0 <= gi < gh and 0 <= gj < gw:
                    m = grid_mass[gi][gj]
                    if m < 0.01:
                        continue
                    gdx = grid_cx[gi][gj] - px
                    gdy = grid_cy_arr[gi][gj] - py
                    dist2 = gdx * gdx + gdy * gdy + soft * soft
                    dist = math.sqrt(dist2)
                    force = G * m / dist2
                    ax += force * gdx / dist
                    ay += force * gdy / dist

        # 3. Gas pressure (repulsion at high density)
        if p[5] > 0.5:  # gas particle
            gi_p = int(py / grid_res)
            gj_p = int(px / grid_res)
            if 0 <= gi_p < gh and 0 <= gj_p < gw:
                local_density = grid_mass[gi_p][gj_p]
                if local_density > 3.0:
                    # Pressure pushes outward from dense region
                    pressure = 0.5 * (local_density - 3.0)
                    pdx = px - grid_cx[gi_p][gj_p]
                    pdy = py - grid_cy_arr[gi_p][gj_p]
                    pd = math.sqrt(pdx * pdx + pdy * pdy) + 0.1
                    ax += pressure * pdx / pd
                    ay += pressure * pdy / pd
            # Gas cooling (velocity damping)
            p[2] *= 0.998
            p[3] *= 0.998

        # Leapfrog integration: kick
        p[2] += ax * dt
        p[3] += ay * dt

        # Leapfrog integration: drift
        p[0] += p[2] * dt
        p[1] += p[3] * dt

        # Boundary wrap
        if p[0] < 0:
            p[0] += cols
        elif p[0] >= cols:
            p[0] -= cols
        if p[1] < 0:
            p[1] += rows
        elif p[1] >= rows:
            p[1] -= rows

        # Kinetic energy
        total_ke += 0.5 * p[4] * (p[2] * p[2] + p[3] * p[3])

    self.galaxy_total_ke = total_ke
    self.galaxy_generation += 1



def _enter_galaxy_mode(self):
    """Enter galaxy formation mode."""
    self.galaxy_menu = True
    self.galaxy_menu_sel = 0



def _exit_galaxy_mode(self):
    """Exit galaxy formation mode and clean up."""
    self.galaxy_mode = False
    self.galaxy_menu = False
    self.galaxy_running = False
    self.galaxy_particles = []
    self.galaxy_density = []
    self.galaxy_gas_grid = []



def _handle_galaxy_menu_key(self, key: int) -> bool:
    """Handle input in galaxy preset menu."""
    n = len(self.GALAXY_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.galaxy_menu_sel = (self.galaxy_menu_sel - 1) % n
    elif key == curses.KEY_DOWN or key == ord("j"):
        self.galaxy_menu_sel = (self.galaxy_menu_sel + 1) % n
    elif key == ord("q") or key == 27:
        self.galaxy_menu = False
        return True
    elif key in (ord("\n"), ord("\r"), curses.KEY_ENTER):
        name, _desc, preset_id = self.GALAXY_PRESETS[self.galaxy_menu_sel]
        self.galaxy_menu = False
        self.galaxy_mode = True
        self.galaxy_running = False
        self.galaxy_preset_name = name
        self._galaxy_init(preset_id)
    return True



def _handle_galaxy_key(self, key: int) -> bool:
    """Handle input during galaxy simulation."""
    if key == ord("q") or key == 27:
        self._exit_galaxy_mode()
        return True
    if key == ord(" "):
        self.galaxy_running = not self.galaxy_running
        self._flash("Playing" if self.galaxy_running else "Paused")
    elif key == ord("n") or key == ord("."):
        self._galaxy_step()
    elif key == ord("r"):
        # Reset with same preset
        for _n, _d, pid in self.GALAXY_PRESETS:
            if _n == self.galaxy_preset_name:
                self._galaxy_init(pid)
                self._flash("Reset")
                break
    elif key == ord("R") or key == ord("m"):
        self.galaxy_mode = False
        self.galaxy_menu = True
        self.galaxy_menu_sel = 0
    elif key == ord("v"):
        views = ["combined", "stars", "gas", "velocity"]
        idx = views.index(self.galaxy_view) if self.galaxy_view in views else 0
        self.galaxy_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.galaxy_view}")
    elif key == ord("g"):
        self.galaxy_grav_const = min(5.0, self.galaxy_grav_const + 0.1)
        self._flash(f"Gravity: {self.galaxy_grav_const:.1f}")
    elif key == ord("G"):
        self.galaxy_grav_const = max(0.1, self.galaxy_grav_const - 0.1)
        self._flash(f"Gravity: {self.galaxy_grav_const:.1f}")
    elif key == ord("d"):
        self.galaxy_dt = min(0.2, self.galaxy_dt + 0.005)
        self._flash(f"dt: {self.galaxy_dt:.3f}")
    elif key == ord("D"):
        self.galaxy_dt = max(0.005, self.galaxy_dt - 0.005)
        self._flash(f"dt: {self.galaxy_dt:.3f}")
    elif key == ord("w"):
        self.galaxy_rotation_speed = min(3.0, self.galaxy_rotation_speed + 0.1)
        self._flash(f"Rotation: {self.galaxy_rotation_speed:.1f}")
    elif key == ord("W"):
        self.galaxy_rotation_speed = max(0.1, self.galaxy_rotation_speed - 0.1)
        self._flash(f"Rotation: {self.galaxy_rotation_speed:.1f}")
    elif key == ord("f"):
        self.galaxy_gas_density = min(1.0, self.galaxy_gas_density + 0.05)
        self._flash(f"Gas fraction: {self.galaxy_gas_density:.2f}")
    elif key == ord("F"):
        self.galaxy_gas_density = max(0.0, self.galaxy_gas_density - 0.05)
        self._flash(f"Gas fraction: {self.galaxy_gas_density:.2f}")
    elif key == ord("h"):
        self.galaxy_show_halo = not self.galaxy_show_halo
        self._flash("Halo: ON" if self.galaxy_show_halo else "Halo: OFF")
    elif key == ord("+") or key == ord("="):
        self.galaxy_steps_per_frame = min(10, self.galaxy_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.galaxy_steps_per_frame}")
    elif key == ord("-") or key == ord("_"):
        self.galaxy_steps_per_frame = max(1, self.galaxy_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.galaxy_steps_per_frame}")
    return True



def _draw_galaxy_menu(self, max_y: int, max_x: int):
    """Draw the galaxy formation preset selection menu."""
    self.stdscr.erase()
    title = "── Galaxy Formation ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Spiral galaxy dynamics with dark matter halo and gravitational interactions"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.GALAXY_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.GALAXY_PRESETS):
        y = 5 + i
        if y >= max_y - 12:
            break
        line = f"  {name:<18s} {desc}"
        attr = curses.color_pair(6)
        if i == self.galaxy_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_lines = [
        "",
        "Particles orbit a central dark matter halo. Gravitational",
        "interactions produce emergent spiral arm structure.",
        "Stars, gas clouds, and dark matter interact dynamically.",
        "",
        "Controls: v=view, g/G=gravity, d/D=dt, w/W=rotation,",
        "          f/F=gas fraction, h=halo, +/-=steps/frame, q=exit",
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
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_galaxy(self, max_y: int, max_x: int):
    """Draw the galaxy simulation."""
    self.stdscr.erase()
    particles = self.galaxy_particles
    rows, cols = self.galaxy_rows, self.galaxy_cols

    # Density characters (increasing density)
    DENSITY_CHARS = [" ", "·", "∘", "○", "◎", "●", "◉", "█"]
    ARROW_CHARS = ["→", "↗", "↑", "↖", "←", "↙", "↓", "↘"]

    # Clear density grids
    star_grid = [[0.0] * cols for _ in range(rows)]
    gas_grid = [[0.0] * cols for _ in range(rows)]
    vx_grid = [[0.0] * cols for _ in range(rows)]
    vy_grid = [[0.0] * cols for _ in range(rows)]
    count_grid = [[0] * cols for _ in range(rows)]

    # Bin particles
    for p in particles:
        r = int(p[1])
        c = int(p[0])
        if 0 <= r < rows and 0 <= c < cols:
            if p[5] < 0.5:  # star
                star_grid[r][c] += p[4]
            else:  # gas
                gas_grid[r][c] += p[4]
            vx_grid[r][c] += p[2]
            vy_grid[r][c] += p[3]
            count_grid[r][c] += 1

    # Draw dark matter halo if enabled
    halo_grid = [[0.0] * cols for _ in range(rows)]
    if self.galaxy_show_halo:
        hcx, hcy = cols / 2.0, rows / 2.0
        hr = self.galaxy_halo_radius
        for r in range(rows):
            for c in range(cols):
                dx = c - hcx
                dy = r - hcy
                dist = math.sqrt(dx * dx + dy * dy)
                # NFW density profile falls off as 1/(r * (1+r/rs)^2)
                halo_grid[r][c] = self.galaxy_halo_mass / ((dist + 1.0) * (1.0 + dist / hr) ** 2) * 0.001

    view = self.galaxy_view

    for r in range(min(rows, max_y - 2)):
        line_parts = []
        for c in range(min(cols, (max_x - 1) // 2)):
            sd = star_grid[r][c]
            gd = gas_grid[r][c]
            hd = halo_grid[r][c] if self.galaxy_show_halo else 0.0

            if view == "velocity" and count_grid[r][c] > 0:
                # Show velocity direction
                avg_vx = vx_grid[r][c] / count_grid[r][c]
                avg_vy = vy_grid[r][c] / count_grid[r][c]
                speed = math.sqrt(avg_vx * avg_vx + avg_vy * avg_vy)
                if speed > 0.1:
                    angle = math.atan2(-avg_vy, avg_vx)  # screen y is inverted
                    idx = int((angle + math.pi) / (2 * math.pi) * 8 + 0.5) % 8
                    ch = ARROW_CHARS[idx]
                    # Color by speed
                    if speed > 3.0:
                        cp = 3  # yellow = fast
                    elif speed > 1.0:
                        cp = 1  # cyan = medium
                    else:
                        cp = 4  # blue = slow
                    try:
                        self.stdscr.addstr(r + 1, c * 2, ch + " ", curses.color_pair(cp))
                    except curses.error:
                        pass
                continue

            if view == "stars":
                density = sd
            elif view == "gas":
                density = gd
            else:  # combined
                density = sd + gd + hd

            if density < 0.01 and hd < 0.01:
                continue

            # Map density to character
            if density < 0.3:
                di = 1
            elif density < 0.8:
                di = 2
            elif density < 1.5:
                di = 3
            elif density < 2.5:
                di = 4
            elif density < 4.0:
                di = 5
            elif density < 6.0:
                di = 6
            else:
                di = 7

            ch = DENSITY_CHARS[di]

            # Choose color
            if view == "gas" or (view == "combined" and gd > sd and gd > 0.1):
                if gd > 2.0:
                    cp = 5  # magenta = dense gas
                else:
                    cp = 4  # blue = gas
            elif view == "stars" or sd > 0.1:
                if sd > 3.0:
                    cp = 7  # bold white = bright star region
                elif sd > 1.0:
                    cp = 6  # white
                else:
                    cp = 1  # cyan = faint stars
            elif hd > 0.01:
                cp = 4  # blue = dark matter
                di = min(di, 3)
                ch = DENSITY_CHARS[di]
            else:
                cp = 6

            try:
                self.stdscr.addstr(r + 1, c * 2, ch + " ", curses.color_pair(cp))
            except curses.error:
                pass

    # Status bar
    n_stars = sum(1 for p in particles if p[5] < 0.5)
    n_gas = sum(1 for p in particles if p[5] >= 0.5 and p[5] < 1.5)
    status = (f" Galaxy [{self.galaxy_preset_name}]  Gen:{self.galaxy_generation}"
              f"  Stars:{n_stars} Gas:{n_gas}  KE:{self.galaxy_total_ke:.1f}"
              f"  G:{self.galaxy_grav_const:.1f} dt:{self.galaxy_dt:.3f}"
              f"  View:{self.galaxy_view}")
    try:
        self.stdscr.addstr(0, 0, status[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Hint bar
    if self.message and time.monotonic() - self.message_time < 2.0:
        hint = f" {self.message}"
    else:
        hint = " [Space]=play [n]=step [v]=view [g/G]=grav [d/D]=dt [w/W]=rot [f/F]=gas [h]=halo [R]=menu [q]=exit"
    hint_y = max_y - 2
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register galaxy mode methods on the App class."""
    App._galaxy_build_particles = _galaxy_build_particles
    App._galaxy_init = _galaxy_init
    App._galaxy_step = _galaxy_step
    App._enter_galaxy_mode = _enter_galaxy_mode
    App._exit_galaxy_mode = _exit_galaxy_mode
    App._handle_galaxy_menu_key = _handle_galaxy_menu_key
    App._handle_galaxy_key = _handle_galaxy_key
    App._draw_galaxy_menu = _draw_galaxy_menu
    App._draw_galaxy = _draw_galaxy

