"""Mode: magfield — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_magfield_mode(self):
    """Enter Magnetic Field Lines mode — show preset menu."""
    self.magfield_menu = True
    self.magfield_menu_sel = 0
    self._flash("Magnetic Field Lines — select a configuration")



def _exit_magfield_mode(self):
    """Exit Magnetic Field Lines mode."""
    self.magfield_mode = False
    self.magfield_menu = False
    self.magfield_running = False
    self.magfield_particles = []
    self.magfield_trails = []
    self._flash("Magnetic Field Lines mode OFF")



def _magfield_init(self, preset_idx: int):
    """Initialize magnetic field simulation with the given preset."""
    import math
    name, _desc, preset_id = self.MAGFIELD_PRESETS[preset_idx]
    self.magfield_preset_name = name
    self.magfield_generation = 0
    self.magfield_running = False

    max_y, max_x = self.stdscr.getmaxyx()
    self.magfield_rows = max(10, max_y - 3)
    self.magfield_cols = max(10, max_x - 1)

    # Defaults
    self.magfield_dt = 0.02
    self.magfield_Bz = 1.0
    self.magfield_Ex = 0.0
    self.magfield_Ey = 0.0
    self.magfield_field_type = 0  # uniform
    self.magfield_max_trail = 300
    self.magfield_show_field = True
    self.magfield_viz_mode = 0
    self.magfield_steps_per_frame = 3

    cx = self.magfield_cols / 2.0
    cy = self.magfield_rows / 2.0
    particles = []

    if preset_id == "cyclotron":
        self.magfield_Bz = 1.5
        self.magfield_num_particles = 10
        self.magfield_field_type = 0
        for i in range(self.magfield_num_particles):
            angle = 2 * math.pi * i / self.magfield_num_particles
            r = min(cx, cy) * 0.4
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            speed = 3.0 + i * 0.5
            vx = speed * math.cos(angle + math.pi / 2)
            vy = speed * math.sin(angle + math.pi / 2)
            charge = 1.0
            mass = 1.0
            particles.append([x, y, vx, vy, charge, mass])

    elif preset_id == "exb":
        self.magfield_Bz = 2.0
        self.magfield_Ex = 0.0
        self.magfield_Ey = -1.5
        self.magfield_num_particles = 8
        self.magfield_field_type = 0
        for i in range(self.magfield_num_particles):
            x = cx - self.magfield_cols * 0.3
            y = cy + (i - self.magfield_num_particles / 2) * 3
            vx = 2.0
            vy = 0.0
            particles.append([x, y, vx, vy, 1.0, 1.0])

    elif preset_id == "bottle":
        self.magfield_Bz = 2.0
        self.magfield_num_particles = 12
        self.magfield_field_type = 2
        self.magfield_max_trail = 400
        for i in range(self.magfield_num_particles):
            x = cx + random.uniform(-5, 5)
            y = cy + random.uniform(-5, 5)
            speed = 2.5
            angle = random.uniform(0, 2 * math.pi)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            particles.append([x, y, vx, vy, 1.0, 1.0])

    elif preset_id == "dipole":
        self.magfield_Bz = 3.0
        self.magfield_num_particles = 10
        self.magfield_field_type = 1
        self.magfield_max_trail = 500
        for i in range(self.magfield_num_particles):
            angle = math.pi / 4 + random.uniform(-0.3, 0.3)
            r = min(cx, cy) * (0.3 + 0.15 * random.random())
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            speed = 2.0 + random.random() * 2
            vangle = angle + math.pi / 2 + random.uniform(-0.2, 0.2)
            vx = speed * math.cos(vangle)
            vy = speed * math.sin(vangle)
            particles.append([x, y, vx, vy, 1.0, 1.0])

    elif preset_id == "quadrupole":
        self.magfield_Bz = 2.0
        self.magfield_num_particles = 14
        self.magfield_field_type = 3
        self.magfield_max_trail = 350
        for i in range(self.magfield_num_particles):
            angle = 2 * math.pi * i / self.magfield_num_particles
            r = min(cx, cy) * 0.25
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            speed = 1.5 + random.random()
            vx = speed * math.cos(angle + math.pi / 3)
            vy = speed * math.sin(angle + math.pi / 3)
            particles.append([x, y, vx, vy, 1.0, 1.0])

    elif preset_id == "mixed":
        self.magfield_Bz = 2.0
        self.magfield_num_particles = 12
        self.magfield_field_type = 0
        for i in range(self.magfield_num_particles):
            angle = 2 * math.pi * i / self.magfield_num_particles
            r = min(cx, cy) * 0.3
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            speed = 3.0
            vx = speed * math.cos(angle + math.pi / 2)
            vy = speed * math.sin(angle + math.pi / 2)
            charge = 1.0 if i % 2 == 0 else -1.0
            particles.append([x, y, vx, vy, charge, 1.0])

    elif preset_id == "shear":
        self.magfield_Bz = 2.0
        self.magfield_num_particles = 10
        self.magfield_field_type = 0  # will compute spatially varying B
        self.magfield_max_trail = 400
        for i in range(self.magfield_num_particles):
            x = cx + random.uniform(-cx * 0.5, cx * 0.5)
            y = cy + random.uniform(-cy * 0.3, cy * 0.3)
            speed = 2.0 + random.random()
            angle = random.uniform(0, 2 * math.pi)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            particles.append([x, y, vx, vy, 1.0, 1.0])

    elif preset_id == "hall":
        self.magfield_Bz = 2.5
        self.magfield_Ex = 1.0
        self.magfield_Ey = 0.0
        self.magfield_num_particles = 10
        self.magfield_field_type = 0
        for i in range(self.magfield_num_particles):
            x = cx + random.uniform(-10, 10)
            y = cy + random.uniform(-10, 10)
            vx = 0.0
            vy = 0.5 * (i - self.magfield_num_particles / 2)
            particles.append([x, y, vx, vy, 1.0, 1.0])

    self.magfield_particles = particles
    self.magfield_trails = [[] for _ in range(len(particles))]
    self.magfield_menu = False
    self.magfield_mode = True
    self._flash(f"Magnetic Field: {name} — Space to start")



def _magfield_get_field(self, x: float, y: float) -> tuple[float, float, float]:
    """Return (Bz, Ex, Ey) at position (x, y) based on field configuration."""
    import math
    cx = self.magfield_cols / 2.0
    cy = self.magfield_rows / 2.0
    dx = x - cx
    dy = y - cy
    r2 = dx * dx + dy * dy + 1e-6
    r = math.sqrt(r2)

    Ex = self.magfield_Ex
    Ey = self.magfield_Ey

    if self.magfield_field_type == 0:
        # Uniform field — check if shear preset (spatially varying)
        if self.magfield_preset_name == "Magnetic Shear":
            # B varies linearly with x
            Bz = self.magfield_Bz * (0.5 + 1.5 * x / self.magfield_cols)
        else:
            Bz = self.magfield_Bz
    elif self.magfield_field_type == 1:
        # Dipole field: B ~ 1/r^3
        scale = min(cx, cy) * 0.3
        rn = max(r / scale, 0.3)
        Bz = self.magfield_Bz / (rn * rn * rn)
        # Dipole also creates radial gradient — mirror-like trapping
        if r > 1:
            Ex += -0.1 * dx / r
            Ey += -0.1 * dy / r
    elif self.magfield_field_type == 2:
        # Magnetic bottle: strong B at edges, weak at center
        # B(y) = B0 * (1 + mirror_ratio * (2*y/rows - 1)^2)
        fy = (y / self.magfield_rows - 0.5) * 2.0
        mirror_ratio = 3.0
        Bz = self.magfield_Bz * (1.0 + mirror_ratio * fy * fy)
        # Radial gradient force for confinement
        grad_B = self.magfield_Bz * mirror_ratio * 2.0 * fy / self.magfield_rows
        # Mirror force: F = -mu * grad(|B|), approximated
        Ey += -0.3 * grad_B
    elif self.magfield_field_type == 3:
        # Quadrupole: B increases linearly with distance from center
        rn = r / (min(cx, cy) * 0.5)
        Bz = self.magfield_Bz * max(0.1, rn)
        # Focusing gradient
        if r > 1:
            focus = 0.05 * self.magfield_Bz
            Ex += -focus * dx / r
            Ey += -focus * dy / r

    return (Bz, Ex, Ey)



def _magfield_step(self):
    """Advance magnetic field simulation by one timestep using Boris integrator."""
    dt = self.magfield_dt
    rows = self.magfield_rows
    cols = self.magfield_cols

    for i, p in enumerate(self.magfield_particles):
        x, y, vx, vy, charge, mass = p
        qm = charge / mass

        Bz, Ex, Ey = self._magfield_get_field(x, y)

        # Boris push algorithm for charged particle in EM fields
        # Half-step electric acceleration
        vx_minus = vx + qm * Ex * dt * 0.5
        vy_minus = vy + qm * Ey * dt * 0.5

        # Rotation in magnetic field
        t_val = qm * Bz * dt * 0.5
        s_val = 2.0 * t_val / (1.0 + t_val * t_val)

        vx_prime = vx_minus + vy_minus * t_val
        vy_prime = vy_minus - vx_minus * t_val

        vx_plus = vx_minus + vy_prime * s_val
        vy_plus = vy_minus - vx_prime * s_val

        # Second half-step electric acceleration
        vx_new = vx_plus + qm * Ex * dt * 0.5
        vy_new = vy_plus + qm * Ey * dt * 0.5

        # Update position
        x_new = x + vx_new * dt
        y_new = y + vy_new * dt

        # Boundary: reflect
        if x_new < 0:
            x_new = -x_new
            vx_new = -vx_new
        elif x_new >= cols:
            x_new = 2 * cols - x_new - 1
            vx_new = -vx_new
        if y_new < 0:
            y_new = -y_new
            vy_new = -vy_new
        elif y_new >= rows:
            y_new = 2 * rows - y_new - 1
            vy_new = -vy_new

        # Clamp to bounds
        x_new = max(0.0, min(cols - 0.01, x_new))
        y_new = max(0.0, min(rows - 0.01, y_new))

        p[0] = x_new
        p[1] = y_new
        p[2] = vx_new
        p[3] = vy_new

        # Record trail
        self.magfield_trails[i].append((x_new, y_new))
        if len(self.magfield_trails[i]) > self.magfield_max_trail:
            self.magfield_trails[i] = self.magfield_trails[i][-self.magfield_max_trail:]

    self.magfield_generation += 1



def _handle_magfield_menu_key(self, key: int) -> bool:
    """Handle keys in the Magnetic Field Lines preset menu."""
    if key == -1:
        return True
    n = len(self.MAGFIELD_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.magfield_menu_sel = (self.magfield_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.magfield_menu_sel = (self.magfield_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.magfield_menu = False
        self._flash("Magnetic Field Lines cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._magfield_init(self.magfield_menu_sel)
        return True
    return True



def _handle_magfield_key(self, key: int) -> bool:
    """Handle keys while in Magnetic Field Lines mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_magfield_mode()
        return True
    if key == ord(" "):
        self.magfield_running = not self.magfield_running
        self._flash("Playing" if self.magfield_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        for _ in range(self.magfield_steps_per_frame):
            self._magfield_step()
        return True
    if key == ord("b") or key == ord("B"):
        # Increase/decrease B-field
        if key == ord("B"):
            self.magfield_Bz = max(0.1, self.magfield_Bz - 0.2)
        else:
            self.magfield_Bz += 0.2
        self._flash(f"B-field: {self.magfield_Bz:.1f}")
        return True
    if key == ord("e"):
        # Toggle E-field on/off
        if abs(self.magfield_Ex) + abs(self.magfield_Ey) > 0.01:
            self._magfield_saved_E = (self.magfield_Ex, self.magfield_Ey)
            self.magfield_Ex = 0.0
            self.magfield_Ey = 0.0
            self._flash("E-field OFF")
        else:
            if hasattr(self, '_magfield_saved_E'):
                self.magfield_Ex, self.magfield_Ey = self._magfield_saved_E
            else:
                self.magfield_Ey = -1.0
            self._flash(f"E-field ON: ({self.magfield_Ex:.1f}, {self.magfield_Ey:.1f})")
        return True
    if key == ord("f"):
        self.magfield_show_field = not self.magfield_show_field
        self._flash(f"Field lines: {'ON' if self.magfield_show_field else 'OFF'}")
        return True
    if key == ord("v"):
        self.magfield_viz_mode = (self.magfield_viz_mode + 1) % 3
        labels = ["Trails", "Velocity Color", "Energy Color"]
        self._flash(f"Viz: {labels[self.magfield_viz_mode]}")
        return True
    if key == ord("c"):
        # Clear trails
        self.magfield_trails = [[] for _ in range(len(self.magfield_particles))]
        self._flash("Trails cleared")
        return True
    if key == ord("+") or key == ord("="):
        self.magfield_dt = min(0.2, self.magfield_dt * 1.5)
        self._flash(f"dt = {self.magfield_dt:.4f}")
        return True
    if key == ord("-"):
        self.magfield_dt = max(0.001, self.magfield_dt / 1.5)
        self._flash(f"dt = {self.magfield_dt:.4f}")
        return True
    if key == ord(">"):
        self.magfield_steps_per_frame = min(50, self.magfield_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.magfield_steps_per_frame}")
        return True
    if key == ord("<"):
        self.magfield_steps_per_frame = max(1, self.magfield_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.magfield_steps_per_frame}")
        return True
    if key == ord("["):
        self.magfield_max_trail = max(50, self.magfield_max_trail - 50)
        self._flash(f"Trail length: {self.magfield_max_trail}")
        return True
    if key == ord("]"):
        self.magfield_max_trail = min(2000, self.magfield_max_trail + 50)
        self._flash(f"Trail length: {self.magfield_max_trail}")
        return True
    if key == ord("p"):
        # Add a particle at center
        import math
        cx = self.magfield_cols / 2.0
        cy = self.magfield_rows / 2.0
        angle = random.uniform(0, 2 * math.pi)
        speed = 2.0 + random.random() * 2
        self.magfield_particles.append([
            cx + random.uniform(-5, 5),
            cy + random.uniform(-5, 5),
            speed * math.cos(angle),
            speed * math.sin(angle),
            1.0, 1.0
        ])
        self.magfield_trails.append([])
        self._flash(f"Added particle (total: {len(self.magfield_particles)})")
        return True
    if key == ord("r"):
        self._magfield_init(self.magfield_menu_sel)
        self._flash("Reset")
        return True
    if key == ord("R"):
        self.magfield_mode = False
        self.magfield_running = False
        self.magfield_menu = True
        self.magfield_menu_sel = 0
        return True
    return True



def _draw_magfield_menu(self, max_y: int, max_x: int):
    """Draw the Magnetic Field Lines preset selection menu."""
    self.stdscr.erase()
    title = "── Magnetic Field Lines ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Charged particles in electromagnetic fields"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.MAGFIELD_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.MAGFIELD_PRESETS):
        y = 5 + i
        if y >= max_y - 14:
            break
        line = f"  {name:<22s} {desc}"
        attr = curses.color_pair(6)
        if i == self.magfield_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_y = 5 + n + 1
    info_lines = [
        "Simulate charged particles moving through magnetic",
        "and electric fields using the Boris push algorithm.",
        "",
        "Watch cyclotron orbits, E×B drift, magnetic mirror",
        "trapping, and chaotic trajectories unfold as glowing",
        "particle trails spiral through configurable fields.",
        "",
        "Each particle color represents its charge sign;",
        "trail brightness fades with age.",
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



def _draw_magfield(self, max_y: int, max_x: int):
    """Draw the Magnetic Field Lines simulation."""
    import math
    self.stdscr.erase()
    rows = self.magfield_rows
    cols = self.magfield_cols
    draw_rows = min(rows, max_y - 2)
    draw_cols = min(cols, max_x - 1)

    # Draw field line indicators if enabled
    if self.magfield_show_field:
        field_spacing_x = max(4, draw_cols // 20)
        field_spacing_y = max(3, draw_rows // 12)
        for fy in range(1, draw_rows - 1, field_spacing_y):
            for fx in range(2, draw_cols - 1, field_spacing_x):
                Bz, Ex, Ey = self._magfield_get_field(float(fx), float(fy))
                # Show field strength with character
                strength = abs(Bz)
                if strength < 0.5:
                    ch = "·"
                elif strength < 1.5:
                    ch = "∘"
                elif strength < 3.0:
                    ch = "○"
                else:
                    ch = "◎"
                # Color by field direction/strength
                if Bz > 0:
                    color = curses.color_pair(4) | curses.A_DIM  # blue = into page
                else:
                    color = curses.color_pair(1) | curses.A_DIM  # red = out of page
                try:
                    self.stdscr.addch(fy, fx, ord(ch[0]) if len(ch) == 1 else ord('.'), color)
                except curses.error:
                    pass

                # Show E-field direction arrows if present
                emag = math.sqrt(Ex * Ex + Ey * Ey)
                if emag > 0.1 and fx + 1 < draw_cols:
                    if abs(Ex) > abs(Ey):
                        arrow = "→" if Ex > 0 else "←"
                    else:
                        arrow = "↓" if Ey > 0 else "↑"
                    try:
                        self.stdscr.addstr(fy, fx + 1, arrow[0] if len(arrow) == 1 else ">" if Ex > 0 else "<",
                                           curses.color_pair(3) | curses.A_DIM)
                    except curses.error:
                        pass

    # Particle trail characters by age (newest to oldest)
    trail_chars = "●◦∙·.·"

    # Color palette per particle
    pos_colors = [
        curses.color_pair(6),                          # cyan
        curses.color_pair(3),                          # green
        curses.color_pair(7),                          # white
        curses.color_pair(6) | curses.A_BOLD,          # bright cyan
        curses.color_pair(3) | curses.A_BOLD,          # bright green
        curses.color_pair(4) | curses.A_BOLD,          # bright blue
    ]
    neg_colors = [
        curses.color_pair(1),                          # red
        curses.color_pair(5),                          # magenta
        curses.color_pair(1) | curses.A_BOLD,          # bright red
        curses.color_pair(5) | curses.A_BOLD,          # bright magenta
    ]

    # Draw trails and particles
    for pi, (p, trail) in enumerate(zip(self.magfield_particles, self.magfield_trails)):
        charge = p[4]
        if charge > 0:
            base_color = pos_colors[pi % len(pos_colors)]
        else:
            base_color = neg_colors[pi % len(neg_colors)]

        # Draw trail
        trail_len = len(trail)
        for ti, (tx, ty) in enumerate(trail):
            sx = int(tx)
            sy = int(ty)
            if 0 <= sy < draw_rows and 0 <= sx < draw_cols:
                # Age: 0 = oldest, trail_len-1 = newest
                age_frac = ti / max(1, trail_len - 1)

                if self.magfield_viz_mode == 1:
                    # Velocity coloring
                    if ti < trail_len - 1:
                        dx = trail[ti + 1][0] - tx
                        dy = trail[ti + 1][1] - ty
                        speed = math.sqrt(dx * dx + dy * dy)
                    else:
                        speed = math.sqrt(p[2] * p[2] + p[3] * p[3]) * self.magfield_dt
                    if speed < 0.05:
                        color = curses.color_pair(4) | curses.A_DIM
                    elif speed < 0.15:
                        color = curses.color_pair(6)
                    elif speed < 0.3:
                        color = curses.color_pair(3) | curses.A_BOLD
                    else:
                        color = curses.color_pair(1) | curses.A_BOLD
                elif self.magfield_viz_mode == 2:
                    # Energy coloring — KE proxy from trail spacing
                    if ti < trail_len - 1:
                        dx = trail[ti + 1][0] - tx
                        dy = trail[ti + 1][1] - ty
                        ke = dx * dx + dy * dy
                    else:
                        ke = (p[2] * p[2] + p[3] * p[3]) * self.magfield_dt * self.magfield_dt
                    if ke < 0.01:
                        color = curses.color_pair(4) | curses.A_DIM
                    elif ke < 0.05:
                        color = curses.color_pair(6)
                    elif ke < 0.15:
                        color = curses.color_pair(7) | curses.A_BOLD
                    else:
                        color = curses.color_pair(1) | curses.A_BOLD
                else:
                    # Standard trail coloring with fade
                    if age_frac < 0.3:
                        color = base_color | curses.A_DIM
                    elif age_frac < 0.7:
                        color = base_color
                    else:
                        color = base_color | curses.A_BOLD

                # Choose trail character based on age
                char_idx = int((1.0 - age_frac) * (len(trail_chars) - 1))
                char_idx = max(0, min(len(trail_chars) - 1, char_idx))
                ch = trail_chars[char_idx]
                try:
                    self.stdscr.addstr(sy, sx, ch, color)
                except curses.error:
                    pass

        # Draw current particle position
        px = int(p[0])
        py = int(p[1])
        if 0 <= py < draw_rows and 0 <= px < draw_cols:
            pch = "⊕" if charge > 0 else "⊖"
            try:
                self.stdscr.addstr(py, px, pch[0] if len(pch.encode('utf-8')) > 1 else pch,
                                   base_color | curses.A_BOLD)
            except curses.error:
                # Fallback to ASCII
                try:
                    self.stdscr.addstr(py, px, "+" if charge > 0 else "-",
                                       base_color | curses.A_BOLD)
                except curses.error:
                    pass

    # Status bar
    field_names = ["Uniform", "Dipole", "Bottle", "Quadrupole"]
    viz_labels = ["Trails", "Velocity", "Energy"]
    ft = self.magfield_field_type if self.magfield_field_type < len(field_names) else 0
    status = (f" MagField: {self.magfield_preset_name}"
              f" │ Step: {self.magfield_generation:,}"
              f" │ {'▶' if self.magfield_running else '⏸'}"
              f" │ B={self.magfield_Bz:.1f}"
              f" │ Particles: {len(self.magfield_particles)}"
              f" │ Field: {field_names[ft]}"
              f" │ Viz: {viz_labels[self.magfield_viz_mode]}")
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
        hint = " Space=play  n=step  b/B=field  e=E-field  f=lines  v=viz  p=add  c=clear  [/]=trail  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register magfield mode methods on the App class."""
    App._enter_magfield_mode = _enter_magfield_mode
    App._exit_magfield_mode = _exit_magfield_mode
    App._magfield_init = _magfield_init
    App._magfield_get_field = _magfield_get_field
    App._magfield_step = _magfield_step
    App._handle_magfield_menu_key = _handle_magfield_menu_key
    App._handle_magfield_key = _handle_magfield_key
    App._draw_magfield_menu = _draw_magfield_menu
    App._draw_magfield = _draw_magfield

