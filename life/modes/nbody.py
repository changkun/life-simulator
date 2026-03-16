"""Mode: nbody — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_nbody_mode(self):
    """Enter N-Body Gravity mode — show preset menu."""
    self.nbody_menu = True
    self.nbody_menu_sel = 0
    self._flash("N-Body Gravity — select a configuration")



def _exit_nbody_mode(self):
    """Exit N-Body Gravity mode."""
    self.nbody_mode = False
    self.nbody_menu = False
    self.nbody_running = False
    self.nbody_bodies = []
    self.nbody_trails = {}
    self._flash("N-Body Gravity mode OFF")



def _nbody_init(self, preset_idx: int):
    """Initialize N-Body simulation with the given preset."""
    name, _desc, setup_key = self.NBODY_PRESETS[preset_idx]
    self.nbody_preset_name = name
    self.nbody_generation = 0
    self.nbody_running = False
    self.nbody_trails = {}

    max_y, max_x = self.stdscr.getmaxyx()
    self.nbody_rows = max(20, max_y - 3)
    self.nbody_cols = max(20, (max_x - 1) // 2)
    rows, cols = self.nbody_rows, self.nbody_cols
    cr, cc = rows / 2.0, cols / 2.0

    self.nbody_bodies = []
    # Set defaults (may be overridden by preset)
    self.nbody_grav_const = 1.0
    self.nbody_dt = 0.02
    self.nbody_softening = 0.5

    if setup_key == "solar":
        # Central star
        self.nbody_bodies.append([cr, cc, 0.0, 0.0, 500.0])
        self.nbody_grav_const = 1.0
        self.nbody_dt = 0.02
        self.nbody_softening = 0.5
        # Planets at increasing radii
        radii = [6.0, 10.0, 15.0, 21.0, 28.0, 36.0]
        masses = [0.1, 0.3, 0.5, 1.0, 2.0, 0.2]
        for i, (rad, mass) in enumerate(zip(radii, masses)):
            angle = random.random() * 2 * math.pi
            pr = cr + rad * math.sin(angle)
            pc = cc + rad * math.cos(angle)
            # Circular orbital velocity: v = sqrt(G*M/r)
            v = math.sqrt(self.nbody_grav_const * 500.0 / rad)
            vr = v * math.cos(angle)
            vc = -v * math.sin(angle)
            self.nbody_bodies.append([pr, pc, vr, vc, mass])

    elif setup_key == "binary":
        sep = 12.0
        star_mass = 200.0
        # Orbital velocity for binary: v = sqrt(G*M/(4*r))
        v = math.sqrt(self.nbody_grav_const * star_mass / (4.0 * sep))
        self.nbody_bodies.append([cr - sep / 2, cc, 0.0, v, star_mass])
        self.nbody_bodies.append([cr + sep / 2, cc, 0.0, -v, star_mass])
        self.nbody_grav_const = 1.0
        self.nbody_dt = 0.02
        self.nbody_softening = 0.5
        # Add some small orbiting debris
        for _ in range(20):
            angle = random.random() * 2 * math.pi
            dist = 18.0 + random.random() * 15.0
            pr = cr + dist * math.sin(angle)
            pc = cc + dist * math.cos(angle)
            v_orb = math.sqrt(self.nbody_grav_const * 2 * star_mass / dist) * 0.9
            vr = v_orb * math.cos(angle)
            vc = -v_orb * math.sin(angle)
            self.nbody_bodies.append([pr, pc, vr, vc, 0.01])

    elif setup_key == "galaxy":
        # Two rotating disk galaxies
        self.nbody_grav_const = 0.5
        self.nbody_dt = 0.03
        self.nbody_softening = 1.0
        for gx, gy, vgr, vgc in [(cr - 15, cc - 10, 0.3, 0.2), (cr + 15, cc + 10, -0.3, -0.2)]:
            # Central black hole
            self.nbody_bodies.append([gx, gy, vgr, vgc, 100.0])
            # Disk particles
            for _ in range(40):
                angle = random.random() * 2 * math.pi
                dist = 2.0 + random.random() * 10.0
                pr = gx + dist * math.sin(angle)
                pc = gy + dist * math.cos(angle)
                v_orb = math.sqrt(self.nbody_grav_const * 100.0 / dist) * 0.8
                vr = vgr + v_orb * math.cos(angle)
                vc = vgc - v_orb * math.sin(angle)
                self.nbody_bodies.append([pr, pc, vr, vc, 0.1])

    elif setup_key == "random":
        self.nbody_grav_const = 0.8
        self.nbody_dt = 0.03
        self.nbody_softening = 0.8
        n_bodies = 60
        for _ in range(n_bodies):
            angle = random.random() * 2 * math.pi
            dist = random.random() * min(rows, cols) * 0.3
            pr = cr + dist * math.sin(angle)
            pc = cc + dist * math.cos(angle)
            mass = 0.5 + random.random() * 5.0
            # Small random initial velocity
            vr = (random.random() - 0.5) * 0.5
            vc = (random.random() - 0.5) * 0.5
            self.nbody_bodies.append([pr, pc, vr, vc, mass])

    elif setup_key == "figure8":
        # The famous figure-8 three-body solution (Chenciner & Montgomery)
        self.nbody_grav_const = 1.0
        self.nbody_dt = 0.01
        self.nbody_softening = 0.1
        scale = 8.0
        # Positions and velocities from the known solution (scaled)
        p1r, p1c = cr - 0.97000436 * scale, cc + 0.24308753 * scale
        p2r, p2c = cr + 0.97000436 * scale, cc - 0.24308753 * scale
        p3r, p3c = cr, cc
        vx3, vy3 = -0.93240737 * 0.5, -0.86473146 * 0.5
        vx1, vy1 = -vx3 / 2.0, -vy3 / 2.0
        vx2, vy2 = -vx3 / 2.0, -vy3 / 2.0
        m = 10.0
        self.nbody_bodies.append([p1r, p1c, vx1 * scale * 0.1, vy1 * scale * 0.1, m])
        self.nbody_bodies.append([p2r, p2c, vx2 * scale * 0.1, vy2 * scale * 0.1, m])
        self.nbody_bodies.append([p3r, p3c, vx3 * scale * 0.1, vy3 * scale * 0.1, m])

    elif setup_key == "lagrange":
        # Large central mass with trojans at L4/L5
        central_mass = 400.0
        self.nbody_grav_const = 1.0
        self.nbody_dt = 0.02
        self.nbody_softening = 0.5
        self.nbody_bodies.append([cr, cc, 0.0, 0.0, central_mass])
        # Planet
        planet_r = 20.0
        planet_mass = 4.0
        v_planet = math.sqrt(self.nbody_grav_const * central_mass / planet_r)
        self.nbody_bodies.append([cr + planet_r, cc, 0.0, -v_planet, planet_mass])
        # Trojans at L4 and L5 (60 degrees ahead/behind)
        for angle_offset in [math.pi / 3, -math.pi / 3]:
            angle = 0.0 + angle_offset  # planet starts at angle 0 (below center)
            tr = cr + planet_r * math.cos(angle)
            tc = cc + planet_r * math.sin(angle)
            vr = v_planet * math.sin(angle)
            vc = -v_planet * math.cos(angle)
            self.nbody_bodies.append([tr, tc, vr, vc, 0.01])
        # Some extra orbiting debris
        for _ in range(15):
            angle = random.random() * 2 * math.pi
            dist = 8.0 + random.random() * 14.0
            pr = cr + dist * math.sin(angle)
            pc = cc + dist * math.cos(angle)
            v_orb = math.sqrt(self.nbody_grav_const * central_mass / dist)
            vr = v_orb * math.cos(angle)
            vc = -v_orb * math.sin(angle)
            self.nbody_bodies.append([pr, pc, vr, vc, 0.01 + random.random() * 0.1])

    self.nbody_num_bodies = len(self.nbody_bodies)
    # Initialize trails
    for i in range(self.nbody_num_bodies):
        self.nbody_trails[i] = []

    self.nbody_menu = False
    self.nbody_mode = True
    self._flash(f"N-Body Gravity: {name} — Space to start")



def _nbody_step(self):
    """Advance N-Body simulation by one step using velocity Verlet integration."""
    bodies = self.nbody_bodies
    n = len(bodies)
    if n == 0:
        return
    G = self.nbody_grav_const
    dt = self.nbody_dt
    soft2 = self.nbody_softening * self.nbody_softening

    # Compute accelerations
    acc = [[0.0, 0.0] for _ in range(n)]
    for i in range(n):
        ri, ci, _vri, _vci, mi = bodies[i]
        for j in range(i + 1, n):
            rj, cj, _vrj, _vcj, mj = bodies[j]
            dr = rj - ri
            dc = cj - ci
            dist2 = dr * dr + dc * dc + soft2
            inv_dist3 = 1.0 / (dist2 * math.sqrt(dist2))
            fr = G * dr * inv_dist3
            fc = G * dc * inv_dist3
            acc[i][0] += fr * mj
            acc[i][1] += fc * mj
            acc[j][0] -= fr * mi
            acc[j][1] -= fc * mi

    # Update positions and velocities (leapfrog / velocity Verlet)
    new_bodies = []
    for i in range(n):
        ri, ci, vri, vci, mi = bodies[i]
        # Half-step velocity
        vri_half = vri + 0.5 * dt * acc[i][0]
        vci_half = vci + 0.5 * dt * acc[i][1]
        # Full-step position
        nr = ri + dt * vri_half
        nc = ci + dt * vci_half
        new_bodies.append([nr, nc, vri_half, vci_half, mi])

    # Recompute accelerations at new positions
    acc2 = [[0.0, 0.0] for _ in range(n)]
    for i in range(n):
        ri, ci = new_bodies[i][0], new_bodies[i][1]
        mi = new_bodies[i][4]
        for j in range(i + 1, n):
            rj, cj = new_bodies[j][0], new_bodies[j][1]
            mj = new_bodies[j][4]
            dr = rj - ri
            dc = cj - ci
            dist2 = dr * dr + dc * dc + soft2
            inv_dist3 = 1.0 / (dist2 * math.sqrt(dist2))
            fr = G * dr * inv_dist3
            fc = G * dc * inv_dist3
            acc2[i][0] += fr * mj
            acc2[i][1] += fc * mj
            acc2[j][0] -= fr * mi
            acc2[j][1] -= fc * mi

    # Complete velocity update
    for i in range(n):
        new_bodies[i][2] += 0.5 * dt * acc2[i][0]
        new_bodies[i][3] += 0.5 * dt * acc2[i][1]

    # Merge bodies that get too close (collision)
    merged = [False] * n
    final_bodies = []
    body_map: dict[int, int] = {}  # old index -> new index
    for i in range(n):
        if merged[i]:
            continue
        ri, ci, vri, vci, mi = new_bodies[i]
        for j in range(i + 1, n):
            if merged[j]:
                continue
            rj, cj, vrj, vcj, mj = new_bodies[j]
            dr = rj - ri
            dc = cj - ci
            dist2 = dr * dr + dc * dc
            # Merge if very close (based on mass)
            merge_dist = 0.3 + 0.1 * math.log1p(mi + mj)
            if dist2 < merge_dist * merge_dist:
                # Conservation of momentum
                total_m = mi + mj
                ri = (ri * mi + rj * mj) / total_m
                ci = (ci * mi + cj * mj) / total_m
                vri = (vri * mi + vrj * mj) / total_m
                vci = (vci * mi + vcj * mj) / total_m
                mi = total_m
                merged[j] = True
        new_idx = len(final_bodies)
        body_map[i] = new_idx
        final_bodies.append([ri, ci, vri, vci, mi])

    # Update trails
    new_trails: dict[int, list[tuple[int, int]]] = {}
    for old_i, new_i in body_map.items():
        ri, ci = final_bodies[new_i][0], final_bodies[new_i][1]
        trail = self.nbody_trails.get(old_i, [])[:]
        trail.append((int(ri), int(ci)))
        if len(trail) > self.nbody_trail_len:
            trail = trail[-self.nbody_trail_len:]
        if new_i not in new_trails:
            new_trails[new_i] = trail
        else:
            # Merge trails from merged bodies
            new_trails[new_i] = (new_trails[new_i] + trail)[-self.nbody_trail_len:]

    self.nbody_bodies = final_bodies
    self.nbody_num_bodies = len(final_bodies)
    self.nbody_trails = new_trails
    self.nbody_generation += 1



def _handle_nbody_menu_key(self, key: int) -> bool:
    """Handle input in N-Body preset menu."""
    n = len(self.NBODY_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.nbody_menu_sel = (self.nbody_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.nbody_menu_sel = (self.nbody_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._nbody_init(self.nbody_menu_sel)
    elif key in (ord("q"), 27):
        self.nbody_menu = False
        self._flash("N-Body Gravity cancelled")
    return True



def _handle_nbody_key(self, key: int) -> bool:
    """Handle input in active N-Body simulation."""
    if key == ord(" "):
        self.nbody_running = not self.nbody_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.nbody_steps_per_frame):
            self._nbody_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.NBODY_PRESETS)
                    if p[0] == self.nbody_preset_name), 0)
        self._nbody_init(idx)
        self.nbody_running = False
    elif key in (ord("R"), ord("m")):
        self.nbody_mode = False
        self.nbody_running = False
        self.nbody_menu = True
        self.nbody_menu_sel = 0
    elif key == ord("g") or key == ord("G"):
        delta = 0.1 if key == ord("g") else -0.1
        self.nbody_grav_const = max(0.1, min(5.0, self.nbody_grav_const + delta))
        self._flash(f"Gravity: {self.nbody_grav_const:.1f}")
    elif key == ord("d") or key == ord("D"):
        delta = 0.005 if key == ord("d") else -0.005
        self.nbody_dt = max(0.005, min(0.2, self.nbody_dt + delta))
        self._flash(f"Time step: {self.nbody_dt:.3f}")
    elif key == ord("s") or key == ord("S"):
        delta = 0.1 if key == ord("s") else -0.1
        self.nbody_softening = max(0.1, min(3.0, self.nbody_softening + delta))
        self._flash(f"Softening: {self.nbody_softening:.1f}")
    elif key == ord("t"):
        self.nbody_show_trails = not self.nbody_show_trails
        self._flash(f"Trails {'ON' if self.nbody_show_trails else 'OFF'}")
    elif key == ord("c"):
        self.nbody_center_mass = not self.nbody_center_mass
        self._flash(f"Center on CoM {'ON' if self.nbody_center_mass else 'OFF'}")
    elif key == ord("+") or key == ord("="):
        self.nbody_steps_per_frame = min(20, self.nbody_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.nbody_steps_per_frame}")
    elif key == ord("-"):
        self.nbody_steps_per_frame = max(1, self.nbody_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.nbody_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">") or key == ord("."):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_nbody_mode()
    else:
        return True
    return True



def _draw_nbody_menu(self, max_y: int, max_x: int):
    """Draw the N-Body preset selection menu."""
    self.stdscr.erase()
    title = "── N-Body Gravity Simulation ── Select Configuration ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _key) in enumerate(self.NBODY_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<20s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.nbody_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_nbody(self, max_y: int, max_x: int):
    """Draw the active N-Body simulation."""
    self.stdscr.erase()
    bodies = self.nbody_bodies
    n = len(bodies)
    rows, cols = self.nbody_rows, self.nbody_cols
    chars = self.NBODY_CHARS
    colors = self.NBODY_COLORS
    state = "▶ RUNNING" if self.nbody_running else "⏸ PAUSED"

    # Compute center of mass for view offset
    offset_r, offset_c = 0.0, 0.0
    if self.nbody_center_mass and n > 0:
        total_m = 0.0
        com_r, com_c = 0.0, 0.0
        for b in bodies:
            com_r += b[0] * b[4]
            com_c += b[1] * b[4]
            total_m += b[4]
        if total_m > 0:
            com_r /= total_m
            com_c /= total_m
            offset_r = com_r - rows / 2.0
            offset_c = com_c - cols / 2.0

    # Title bar
    title = (f" N-Body: {self.nbody_preset_name}  |  gen {self.nbody_generation}"
             f"  |  bodies={n}"
             f"  G={self.nbody_grav_const:.1f}"
             f"  dt={self.nbody_dt:.3f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 3
    view_cols = (max_x - 1) // 2

    # Draw trails
    if self.nbody_show_trails:
        for body_i, trail in self.nbody_trails.items():
            if body_i >= n:
                continue
            # Trail color matches body
            mass = bodies[body_i][4] if body_i < n else 1.0
            ci_idx = min(len(colors) - 1, int(math.log1p(mass)))
            cp = colors[ci_idx % len(colors)]
            trail_len = len(trail)
            for ti, (tr, tc) in enumerate(trail):
                sr = int(tr - offset_r)
                sc = int(tc - offset_c)
                if 0 <= sr < view_rows and 0 <= sc < view_cols:
                    # Fade trail: dimmer for older points
                    if ti < trail_len * 0.3:
                        attr = curses.color_pair(cp) | curses.A_DIM
                        ch = "·"
                    elif ti < trail_len * 0.7:
                        attr = curses.color_pair(cp) | curses.A_DIM
                        ch = "∘"
                    else:
                        attr = curses.color_pair(cp)
                        ch = "•"
                    try:
                        self.stdscr.addstr(1 + sr, sc * 2, ch + " ", attr)
                    except curses.error:
                        pass

    # Draw bodies
    for i, (br, bc, vr, vc, mass) in enumerate(bodies):
        sr = int(br - offset_r)
        sc = int(bc - offset_c)
        if 0 <= sr < view_rows and 0 <= sc < view_cols:
            # Character based on mass
            if mass >= 100.0:
                ch = "☉"
                ci_idx = 0  # Yellow for stars
            elif mass >= 10.0:
                ch = "●"
                ci_idx = min(len(colors) - 1, i % len(colors))
            elif mass >= 1.0:
                ch = "◆"
                ci_idx = min(len(colors) - 1, i % len(colors))
            else:
                ch = "·"
                ci_idx = min(len(colors) - 1, i % len(colors))
            cp = colors[ci_idx]
            # Brightness based on speed
            spd = math.sqrt(vr * vr + vc * vc)
            if spd > 2.0:
                attr = curses.color_pair(cp) | curses.A_BOLD
            elif spd > 0.5:
                attr = curses.color_pair(cp)
            else:
                attr = curses.color_pair(cp) | curses.A_DIM
            # Large masses always bold
            if mass >= 100.0:
                attr = curses.color_pair(cp) | curses.A_BOLD
            try:
                self.stdscr.addstr(1 + sr, sc * 2, ch + " ", attr)
            except curses.error:
                pass

    # Compute total energy for status
    total_ke = 0.0
    for b in bodies:
        spd2 = b[2] * b[2] + b[3] * b[3]
        total_ke += 0.5 * b[4] * spd2

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        info = (f" Gen {self.nbody_generation}  |  bodies={n}"
                f"  |  KE={total_ke:.1f}"
                f"  |  soft={self.nbody_softening:.1f}"
                f"  |  steps/f={self.nbody_steps_per_frame}")
        try:
            self.stdscr.addstr(status_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [g/G]=grav+/- [d/D]=dt+/- [s/S]=soft+/- [t]=trails [c]=center [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Diffusion-Limited Aggregation (DLA) — Mode D
# ══════════════════════════════════════════════════════════════════════

DLA_PRESETS = [
    # (name, description, setup_key)
    ("Crystal Growth", "Single seed — classic dendritic fractal", "single"),
    ("Multi-Seed", "Several seeds grow and merge", "multi"),
    ("Snowflake", "6-fold symmetry from center seed", "snowflake"),
    ("Electrodeposition", "Bottom-edge cathode with downward drift", "electro"),
    ("Line Seed", "Horizontal line seed — forest-like growth", "line"),
    ("Ring Seed", "Circular ring seed — inward/outward growth", "ring"),
]

# Characters for crystal age visualization (oldest -> newest)
DLA_CRYSTAL_CHARS = ["█", "▓", "▒", "░", "∙"]
DLA_WALKER_CHAR = "·"




def register(App):
    """Register nbody mode methods on the App class."""
    App._enter_nbody_mode = _enter_nbody_mode
    App._exit_nbody_mode = _exit_nbody_mode
    App._nbody_init = _nbody_init
    App._nbody_step = _nbody_step
    App._handle_nbody_menu_key = _handle_nbody_menu_key
    App._handle_nbody_key = _handle_nbody_key
    App._draw_nbody_menu = _draw_nbody_menu
    App._draw_nbody = _draw_nbody

