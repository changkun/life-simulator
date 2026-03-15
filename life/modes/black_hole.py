"""Mode: blackhole — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_blackhole_mode(self):
    """Enter Black Hole mode — show preset menu."""
    self.blackhole_menu = True
    self.blackhole_menu_sel = 0




def _exit_blackhole_mode(self):
    """Exit Black Hole mode and clean up."""
    self.blackhole_mode = False
    self.blackhole_menu = False
    self.blackhole_running = False
    self.blackhole_particles = []
    self.blackhole_bg_stars = []
    self.blackhole_lensed = []




def _blackhole_init(self, preset: str):
    """Initialize simulation grids and spawn particles for a preset."""
    import math
    import random as rng

    rows, cols = self.grid.rows, self.grid.cols
    self.blackhole_rows = rows
    self.blackhole_cols = cols
    self.blackhole_cx = cols / 2.0
    self.blackhole_cy = rows / 2.0
    self.blackhole_generation = 0
    self.blackhole_total_accreted = 0.0
    self.blackhole_particles = []
    self.blackhole_view = "combined"
    self.blackhole_show_horizon = True
    self.blackhole_photon_ring = True

    # Preset-specific parameters
    if preset == "stellar":
        self.blackhole_mass = 30.0
        self.blackhole_spin = 0.3
        self.blackhole_rs = min(rows, cols) * 0.04
        self.blackhole_jet_power = 0.4
        self.blackhole_accretion_rate = 0.8
        n_disk = 300
        n_hawking = 5
    elif preset == "supermassive":
        self.blackhole_mass = 100.0
        self.blackhole_spin = 0.6
        self.blackhole_rs = min(rows, cols) * 0.07
        self.blackhole_jet_power = 0.9
        self.blackhole_accretion_rate = 1.5
        n_disk = 500
        n_hawking = 3
    elif preset == "kerr":
        self.blackhole_mass = 60.0
        self.blackhole_spin = 0.95
        self.blackhole_rs = min(rows, cols) * 0.05
        self.blackhole_jet_power = 1.2
        self.blackhole_accretion_rate = 1.0
        n_disk = 400
        n_hawking = 4
    elif preset == "quasar":
        self.blackhole_mass = 200.0
        self.blackhole_spin = 0.8
        self.blackhole_rs = min(rows, cols) * 0.06
        self.blackhole_jet_power = 2.0
        self.blackhole_accretion_rate = 3.0
        n_disk = 600
        n_hawking = 2
    elif preset == "micro":
        self.blackhole_mass = 5.0
        self.blackhole_spin = 0.1
        self.blackhole_rs = min(rows, cols) * 0.02
        self.blackhole_jet_power = 0.1
        self.blackhole_accretion_rate = 0.3
        n_disk = 100
        n_hawking = 30
    elif preset == "binary":
        self.blackhole_mass = 40.0
        self.blackhole_spin = 0.5
        self.blackhole_rs = min(rows, cols) * 0.035
        self.blackhole_jet_power = 0.6
        self.blackhole_accretion_rate = 1.2
        n_disk = 400
        n_hawking = 6
    else:
        self.blackhole_mass = 50.0
        self.blackhole_spin = 0.5
        self.blackhole_rs = min(rows, cols) * 0.05
        self.blackhole_jet_power = 0.8
        self.blackhole_accretion_rate = 1.0
        n_disk = 350
        n_hawking = 5

    rs = self.blackhole_rs
    cx, cy = self.blackhole_cx, self.blackhole_cy
    max_r = min(rows, cols) * 0.45

    # Generate accretion disk particles in Keplerian orbits
    for _ in range(n_disk):
        # Orbital radius: inner stable circular orbit ~ 3*rs to max_r
        r_inner = 3.0 * rs * (1.0 - self.blackhole_spin * 0.3)
        r_orbit = r_inner + rng.random() ** 0.5 * (max_r - r_inner)
        angle = rng.uniform(0, 2 * math.pi)
        # Slight vertical spread for disk thickness
        spread = rng.gauss(0, 0.3) * (r_orbit / max_r)

        x = cx + r_orbit * math.cos(angle)
        y = cy + r_orbit * math.sin(angle) * 0.3 + spread  # flatten for inclination

        # Keplerian velocity: v = sqrt(GM/r)
        v_mag = math.sqrt(self.blackhole_mass / max(r_orbit, 1.0))
        # Add relativistic precession: slight radial component
        precession = self.blackhole_spin * 0.05 * v_mag / max(r_orbit, 1.0)
        vx = -v_mag * math.sin(angle) + precession * math.cos(angle)
        vy = v_mag * math.cos(angle) * 0.3 + precession * math.sin(angle) * 0.3

        # Temperature: hotter closer to center
        temp = min(1.0, (r_inner / max(r_orbit, 0.1)) ** 0.75)
        # type 0 = disk particle
        self.blackhole_particles.append([x, y, vx, vy, temp, 0.0, 0])

    # Generate jet particles along polar axis
    n_jet = int(30 * self.blackhole_jet_power)
    for _ in range(n_jet):
        # Jets emerge from near the poles
        jx = cx + rng.gauss(0, rs * 0.3)
        direction = rng.choice([-1, 1])  # up or down jet
        jy = cy + direction * rng.uniform(rs * 0.5, max_r * 0.8)
        jvx = rng.gauss(0, 0.1)
        jvy = direction * rng.uniform(1.5, 4.0) * self.blackhole_jet_power
        temp = rng.uniform(0.7, 1.0)
        self.blackhole_particles.append([jx, jy, jvx, jvy, temp, 0.0, 1])

    # Generate Hawking radiation particles near horizon
    for _ in range(n_hawking):
        angle = rng.uniform(0, 2 * math.pi)
        hr = rs * rng.uniform(1.0, 1.5)
        hx = cx + hr * math.cos(angle)
        hy = cy + hr * math.sin(angle) * 0.3
        speed = rng.uniform(0.5, 2.0)
        hvx = speed * math.cos(angle)
        hvy = speed * math.sin(angle) * 0.3
        self.blackhole_particles.append([hx, hy, hvx, hvy, 0.3, 0.0, 2])

    # Background stars for gravitational lensing
    self.blackhole_bg_stars = []
    n_stars = int(rows * cols * 0.01)
    for _ in range(n_stars):
        sx = rng.uniform(0, cols)
        sy = rng.uniform(0, rows)
        brightness = rng.uniform(0.2, 1.0)
        self.blackhole_bg_stars.append((sx, sy, brightness))

    # Initialize lensed star grid
    self.blackhole_lensed = [[0.0] * cols for _ in range(rows)]




def _blackhole_step(self):
    """Advance black hole simulation by one timestep."""
    import math
    import random as rng

    dt = self.blackhole_dt
    mass = self.blackhole_mass
    spin = self.blackhole_spin
    rs = self.blackhole_rs
    cx, cy = self.blackhole_cx, self.blackhole_cy
    rows, cols = self.blackhole_rows, self.blackhole_cols
    particles = self.blackhole_particles

    new_particles = []
    for p in particles:
        x, y, vx, vy, temp, age, ptype = p
        age += dt

        # Distance to black hole center (account for disk inclination)
        dx = x - cx
        dy = (y - cy) / 0.3  # un-flatten for true distance
        r = math.sqrt(dx * dx + dy * dy) + 0.01

        if ptype == 0:  # Disk particle
            # Gravitational acceleration: F = -GM/r^2
            acc = mass / (r * r)
            ax_g = -acc * dx / r
            ay_g = -acc * (y - cy) / (r * 0.3)  # keep in disk plane

            # Frame dragging from spin (Lense-Thirring effect)
            drag_strength = spin * mass / (r * r * r) * 0.5
            ax_g += drag_strength * (-(y - cy))
            ay_g += drag_strength * dx * 0.3

            # Relativistic precession correction
            v2 = vx * vx + vy * vy
            rel_factor = 1.0 + 3.0 * mass / (r * r) * 0.01
            ax_g *= rel_factor
            ay_g *= rel_factor

            vx += ax_g * dt
            vy += ay_g * dt

            # Viscous drag in disk (angular momentum transport)
            drag = 0.001 * self.blackhole_accretion_rate
            vx *= (1.0 - drag * dt)
            vy *= (1.0 - drag * dt)

            x += vx * dt
            y += vy * dt

            # Temperature: increases as particle spirals inward
            temp = min(1.0, mass / (r * 0.5 + 1.0))

            # Check if accreted (crossed event horizon)
            if r < rs:
                self.blackhole_total_accreted += 1
                # Occasionally spawn jet particle when matter accreted
                if rng.random() < 0.1 * self.blackhole_jet_power:
                    direction = rng.choice([-1, 1])
                    jvx = rng.gauss(0, 0.15)
                    jvy = direction * rng.uniform(2.0, 5.0) * self.blackhole_jet_power
                    new_particles.append([cx + rng.gauss(0, rs * 0.2), cy, jvx, jvy, 1.0, 0.0, 1])
                continue  # particle consumed

            # Re-emit particle if it goes too far
            if x < 0 or x >= cols or y < 0 or y >= rows:
                angle = rng.uniform(0, 2 * math.pi)
                r_inner = 3.0 * rs * (1.0 - spin * 0.3)
                max_orbit = min(rows, cols) * 0.45
                r_orbit = r_inner + rng.random() ** 0.5 * (max_orbit - r_inner)
                x = cx + r_orbit * math.cos(angle)
                y = cy + r_orbit * math.sin(angle) * 0.3
                v_mag = math.sqrt(mass / max(r_orbit, 1.0))
                vx = -v_mag * math.sin(angle)
                vy = v_mag * math.cos(angle) * 0.3
                temp = min(1.0, (r_inner / max(r_orbit, 0.1)) ** 0.75)

            new_particles.append([x, y, vx, vy, temp, age, 0])

        elif ptype == 1:  # Jet particle
            # Jets move mostly along polar axis with slight spread
            # Mild gravitational pull back
            if r > rs * 2:
                acc = mass / (r * r) * 0.05
                vx += -acc * dx / r * dt
                vy += -acc * (y - cy) / r * dt

            # Collimation by magnetic field (push toward axis)
            vx -= 0.02 * dx * dt

            x += vx * dt
            y += vy * dt
            temp *= (1.0 - 0.005)  # cool over time

            # Re-emit if out of bounds or too old
            if x < 0 or x >= cols or y < 0 or y >= rows or age > 50:
                direction = rng.choice([-1, 1])
                x = cx + rng.gauss(0, rs * 0.3)
                y = cy + direction * rs * 0.5
                vx = rng.gauss(0, 0.1)
                vy = direction * rng.uniform(1.5, 4.0) * self.blackhole_jet_power
                temp = rng.uniform(0.7, 1.0)
                age = 0.0

            new_particles.append([x, y, vx, vy, temp, age, 1])

        elif ptype == 2:  # Hawking radiation
            # Particles escape radially with quantum randomness
            escape_dir_x = dx / r
            escape_dir_y = (y - cy) / r
            acc_escape = 0.3 / (r + 1.0)
            vx += (acc_escape * escape_dir_x + rng.gauss(0, 0.1)) * dt
            vy += (acc_escape * escape_dir_y + rng.gauss(0, 0.1)) * dt

            x += vx * dt
            y += vy * dt
            temp *= (1.0 - 0.01)

            if x < 0 or x >= cols or y < 0 or y >= rows or age > 80:
                angle = rng.uniform(0, 2 * math.pi)
                hr = rs * rng.uniform(1.0, 1.5)
                x = cx + hr * math.cos(angle)
                y = cy + hr * math.sin(angle) * 0.3
                speed = rng.uniform(0.5, 2.0)
                vx = speed * math.cos(angle)
                vy = speed * math.sin(angle) * 0.3
                temp = 0.3
                age = 0.0

            new_particles.append([x, y, vx, vy, temp, age, 2])

    particles = new_particles + new_particles.__class__(new_particles[:0])  # just new_particles
    self.blackhole_particles = new_particles

    # Compute gravitational lensing of background stars
    lensed = self.blackhole_lensed
    for r_idx in range(rows):
        for c_idx in range(cols):
            lensed[r_idx][c_idx] *= 0.3  # fade previous frame

    for sx, sy, brightness in self.blackhole_bg_stars:
        # Compute apparent position due to lensing
        ddx = sx - cx
        ddy = (sy - cy)
        dist = math.sqrt(ddx * ddx + ddy * ddy) + 0.01

        # Einstein ring deflection: angle ~ 4GM / (c^2 * b)
        # Simplified: deflection inversely proportional to distance
        if dist < rs * 8:
            deflection = mass * 0.15 / (dist * dist + rs)
            # Lensed position shifts radially outward
            apparent_x = sx + deflection * ddx / dist
            apparent_y = sy + deflection * ddy / dist
            # Amplification factor (brighter near Einstein ring)
            amp = min(3.0, 1.0 + mass * 0.02 / (abs(dist - rs * 2.5) + 0.5))
            lensed_brightness = brightness * amp
        else:
            apparent_x = sx
            apparent_y = sy
            lensed_brightness = brightness

        # Plot the star at its apparent position
        ar = int(apparent_y)
        ac = int(apparent_x)
        if 0 <= ar < rows and 0 <= ac < cols:
            lensed[ar][ac] = max(lensed[ar][ac], lensed_brightness)

    self.blackhole_generation += 1




def _handle_blackhole_menu_key(self, key: int) -> bool:
    """Handle keys in the Black Hole preset menu."""
    n = len(BLACKHOLE_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.blackhole_menu_sel = (self.blackhole_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.blackhole_menu_sel = (self.blackhole_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.blackhole_menu = False
        self.blackhole_mode = False
        self._exit_blackhole_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = BLACKHOLE_PRESETS[self.blackhole_menu_sel]
        self.blackhole_preset_name = preset[0]
        self._blackhole_init(preset[2])
        self.blackhole_menu = False
        self.blackhole_mode = True
        self.blackhole_running = True
    else:
        return False
    return True




def _handle_blackhole_key(self, key: int) -> bool:
    """Handle keys during Black Hole simulation."""
    if key in (27, ord('q')):
        self._exit_blackhole_mode()
        return True
    elif key == ord(' '):
        self.blackhole_running = not self.blackhole_running
    elif key in (ord('n'), ord('.')):
        self._blackhole_step()
    elif key in (ord('r'),):
        # Reset with same preset
        for p in BLACKHOLE_PRESETS:
            if p[0] == self.blackhole_preset_name:
                self._blackhole_init(p[2])
                break
    elif key in (ord('R'), ord('m')):
        self.blackhole_running = False
        self.blackhole_menu = True
        self.blackhole_menu_sel = 0
    elif key == ord('v'):
        views = ["combined", "disk", "lensing", "jets"]
        idx = views.index(self.blackhole_view) if self.blackhole_view in views else 0
        self.blackhole_view = views[(idx + 1) % len(views)]
    elif key == ord('M'):
        self.blackhole_mass = min(500.0, self.blackhole_mass * 1.1)
        self.blackhole_rs *= 1.05
    elif key == ord('N'):
        self.blackhole_mass = max(1.0, self.blackhole_mass * 0.9)
        self.blackhole_rs *= 0.95
    elif key == ord('s'):
        self.blackhole_spin = min(0.99, self.blackhole_spin + 0.05)
    elif key == ord('S'):
        self.blackhole_spin = max(0.0, self.blackhole_spin - 0.05)
    elif key == ord('j'):
        self.blackhole_jet_power = min(5.0, self.blackhole_jet_power + 0.1)
    elif key == ord('J'):
        self.blackhole_jet_power = max(0.0, self.blackhole_jet_power - 0.1)
    elif key == ord('h'):
        self.blackhole_show_horizon = not self.blackhole_show_horizon
    elif key == ord('p'):
        self.blackhole_photon_ring = not self.blackhole_photon_ring
    elif key in (ord('+'), ord('=')):
        self.blackhole_dt = min(0.1, self.blackhole_dt * 1.2)
    elif key in (ord('-'), ord('_')):
        self.blackhole_dt = max(0.001, self.blackhole_dt * 0.8)
    else:
        return False
    return True




def _draw_blackhole_menu(self, max_y: int, max_x: int):
    """Draw the Black Hole preset selection menu."""
    self.stdscr.erase()
    title = "── Black Hole Accretion Disk ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Gravitational lensing, relativistic jets & Hawking radiation"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle, curses.A_DIM)
    except curses.error:
        pass

    y = 4
    for i, (name, desc, _key) in enumerate(BLACKHOLE_PRESETS):
        if y >= max_y - 6:
            break
        attr = curses.A_REVERSE if i == self.blackhole_menu_sel else 0
        try:
            label = f"  {name:<24s} {desc}"
            self.stdscr.addstr(y, 2, label[:max_x - 4], attr)
        except curses.error:
            pass
        y += 1

    # Info section
    y += 1
    info_lines = [
        "Controls during simulation:",
        "  Space=play/pause  n=step  v=view mode  r=reset  R=menu",
        "  M/N=mass+/-  s/S=spin+/-  j/J=jet+/-  h=horizon  p=photon ring",
        "  +/-=speed  q=exit",
    ]
    for line in info_lines:
        if y < max_y - 2:
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4], curses.A_DIM)
            except curses.error:
                pass
            y += 1

    # Footer
    try:
        footer = " ↑↓=select  Enter=start  q=back "
        self.stdscr.addstr(max_y - 1, max(0, (max_x - len(footer)) // 2), footer[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass




def _draw_blackhole(self, max_y: int, max_x: int):
    """Draw the Black Hole simulation."""
    import math

    self.stdscr.erase()
    rows = min(self.blackhole_rows, max_y - 2)
    cols = min(self.blackhole_cols, max_x)
    if rows < 3 or cols < 3:
        return

    cx, cy = self.blackhole_cx, self.blackhole_cy
    rs = self.blackhole_rs
    view = self.blackhole_view

    # Character palettes
    disk_chars = " .·:;+=*#@"
    star_chars = " .·+*"
    jet_chars = " .|!I"
    hawking_chars = " ·∙•"

    # Build display buffer
    buf = [[' '] * cols for _ in range(rows)]
    color_buf = [[0] * cols for _ in range(rows)]

    # Layer 1: Gravitational lensing of background stars
    if view in ("combined", "lensing"):
        lensed = self.blackhole_lensed
        for r in range(rows):
            for c in range(cols):
                if r < len(lensed) and c < len(lensed[0]):
                    val = lensed[r][c]
                    if val > 0.05:
                        idx = min(len(star_chars) - 1, int(val * (len(star_chars) - 1)))
                        if idx > 0:
                            buf[r][c] = star_chars[idx]
                            color_buf[r][c] = 7  # white/dim for stars

    # Layer 2: Photon ring (light orbiting at 1.5*rs)
    if self.blackhole_photon_ring and view in ("combined", "disk"):
        photon_r = 1.5 * rs
        for angle_i in range(120):
            angle = angle_i * math.pi * 2 / 120
            px = int(cx + photon_r * math.cos(angle))
            py = int(cy + photon_r * math.sin(angle) * 0.3)
            if 0 <= py < rows and 0 <= px < cols:
                buf[py][px] = '°'
                color_buf[py][px] = 4  # yellow

    # Layer 3: Accretion disk particles
    if view in ("combined", "disk"):
        for p in self.blackhole_particles:
            x, y, vx, vy, temp, age, ptype = p
            r_int = int(y)
            c_int = int(x)
            if not (0 <= r_int < rows and 0 <= c_int < cols):
                continue
            if ptype == 0:  # disk
                idx = min(len(disk_chars) - 1, int(temp * (len(disk_chars) - 1)))
                if idx > 0:
                    buf[r_int][c_int] = disk_chars[idx]
                    # Color by temperature: blue(cool) -> white -> yellow -> red(hot)
                    if temp < 0.25:
                        color_buf[r_int][c_int] = 5  # cyan
                    elif temp < 0.5:
                        color_buf[r_int][c_int] = 7  # white
                    elif temp < 0.75:
                        color_buf[r_int][c_int] = 4  # yellow
                    else:
                        color_buf[r_int][c_int] = 2  # red

    # Layer 4: Relativistic jets
    if view in ("combined", "jets"):
        for p in self.blackhole_particles:
            x, y, vx, vy, temp, age, ptype = p
            if ptype != 1:
                continue
            r_int = int(y)
            c_int = int(x)
            if not (0 <= r_int < rows and 0 <= c_int < cols):
                continue
            idx = min(len(jet_chars) - 1, int(temp * (len(jet_chars) - 1)))
            if idx > 0:
                buf[r_int][c_int] = jet_chars[idx]
                color_buf[r_int][c_int] = 6  # magenta for jets

    # Layer 5: Hawking radiation
    if view in ("combined",):
        for p in self.blackhole_particles:
            x, y, vx, vy, temp, age, ptype = p
            if ptype != 2:
                continue
            r_int = int(y)
            c_int = int(x)
            if not (0 <= r_int < rows and 0 <= c_int < cols):
                continue
            idx = min(len(hawking_chars) - 1, int(temp * (len(hawking_chars) - 1)))
            if idx > 0:
                buf[r_int][c_int] = hawking_chars[idx]
                color_buf[r_int][c_int] = 3  # green for Hawking

    # Layer 6: Event horizon (solid black disk)
    if self.blackhole_show_horizon:
        for r in range(rows):
            for c in range(cols):
                ddx = c - cx
                ddy = (r - cy) / 0.3
                dist = math.sqrt(ddx * ddx + ddy * ddy)
                if dist < rs:
                    buf[r][c] = ' '
                    color_buf[r][c] = 0
                elif dist < rs * 1.1:
                    buf[r][c] = '█'
                    color_buf[r][c] = 0  # event horizon boundary

    # Render to screen
    color_map = {0: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}
    for r in range(rows):
        line_parts = []
        for c in range(cols):
            ch = buf[r][c]
            line_parts.append(ch)
        try:
            self.stdscr.addstr(r, 0, ''.join(line_parts)[:cols])
        except curses.error:
            pass
        # Apply colors
        for c in range(cols):
            cv = color_buf[r][c]
            if cv != 0 and buf[r][c] != ' ':
                try:
                    pair = cv
                    self.stdscr.chgat(r, c, 1, curses.color_pair(pair) | curses.A_BOLD)
                except curses.error:
                    pass

    # Status bar
    status_y = min(rows, max_y - 2)
    n_disk = sum(1 for p in self.blackhole_particles if p[6] == 0)
    n_jet = sum(1 for p in self.blackhole_particles if p[6] == 1)
    n_hawk = sum(1 for p in self.blackhole_particles if p[6] == 2)
    status = (f" Gen:{self.blackhole_generation} │ {self.blackhole_preset_name} │ "
              f"M={self.blackhole_mass:.0f} spin={self.blackhole_spin:.2f} │ "
              f"Disk:{n_disk} Jet:{n_jet} Hawk:{n_hawk} │ "
              f"Accreted:{self.blackhole_total_accreted:.0f} │ view:{self.blackhole_view}")
    try:
        self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass

    # Hint bar
    hint = " Space=play n=step v=viz M/N=mass s/S=spin j/J=jets h=horizon p=photon +/-=speed r=reset R=menu q=exit"
    try:
        self.stdscr.addstr(status_y + 1, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Solar System Orrery — Keplerian orbital mechanics
# ══════════════════════════════════════════════════════════════════════════════

# Planet data: (name, symbol, semi-major axis AU, eccentricity, period years,
#               inclination deg (unused in 2D), color_pair_hint, radius_hint)
_ORRERY_PLANETS = [
    {"name": "Mercury", "sym": "☿", "a": 0.387, "e": 0.2056, "T": 0.241, "color": 7, "char": "m"},
    {"name": "Venus",   "sym": "♀", "a": 0.723, "e": 0.0068, "T": 0.615, "color": 3, "char": "v"},
    {"name": "Earth",   "sym": "⊕", "a": 1.000, "e": 0.0167, "T": 1.000, "color": 6, "char": "E"},
    {"name": "Mars",    "sym": "♂", "a": 1.524, "e": 0.0934, "T": 1.881, "color": 1, "char": "M"},
    {"name": "Jupiter", "sym": "♃", "a": 5.203, "e": 0.0484, "T": 11.86, "color": 3, "char": "J"},
    {"name": "Saturn",  "sym": "♄", "a": 9.537, "e": 0.0539, "T": 29.46, "color": 3, "char": "S"},
    {"name": "Uranus",  "sym": "⛢", "a": 19.19, "e": 0.0473, "T": 84.01, "color": 6, "char": "U"},
    {"name": "Neptune", "sym": "♆", "a": 30.07, "e": 0.0086, "T": 164.8, "color": 4, "char": "N"},
]

ORRERY_PRESETS = [
    ("Full Solar System", "All 8 planets with asteroid belt and comets", "full"),
    ("Inner Planets", "Mercury through Mars — zoomed in view", "inner"),
    ("Outer Planets", "Jupiter through Neptune — zoomed out view", "outer"),
    ("Earth & Neighbors", "Venus, Earth, Mars with detailed orbital info", "neighbors"),
    ("Comet Flyby", "Long-period comet passing through inner solar system", "comet"),
    ("Grand Alignment", "All planets starting near alignment", "alignment"),
]





def register(App):
    """Register blackhole mode methods on the App class."""
    App._enter_blackhole_mode = _enter_blackhole_mode
    App._exit_blackhole_mode = _exit_blackhole_mode
    App._blackhole_init = _blackhole_init
    App._blackhole_step = _blackhole_step
    App._handle_blackhole_menu_key = _handle_blackhole_menu_key
    App._handle_blackhole_key = _handle_blackhole_key
    App._draw_blackhole_menu = _draw_blackhole_menu
    App._draw_blackhole = _draw_blackhole

