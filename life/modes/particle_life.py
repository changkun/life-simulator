"""Mode: plife — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS
from life.grid import Grid

def _enter_plife_mode(self):
    """Enter Particle Life mode — show preset menu."""
    self.plife_menu = True
    self.plife_menu_sel = 0
    self._flash("Particle Life — select a configuration")



def _exit_plife_mode(self):
    """Exit Particle Life mode."""
    self.plife_mode = False
    self.plife_menu = False
    self.plife_running = False
    self.plife_particles = []
    self.plife_rules = []
    self._flash("Particle Life mode OFF")



def _plife_init(self, preset_idx: int):
    """Initialize Particle Life simulation with the given preset."""
    name, _desc, num_types, density, max_r, friction, fscale, seed = self.PLIFE_PRESETS[preset_idx]
    self.plife_preset_name = name
    self.plife_num_types = num_types
    self.plife_max_radius = max_r
    self.plife_friction = friction
    self.plife_force_scale = fscale
    self.plife_generation = 0
    self.plife_running = False

    max_y, max_x = self.stdscr.getmaxyx()
    self.plife_rows = max(10, max_y - 3)
    self.plife_cols = max(10, (max_x - 1) // 2)

    rows, cols = self.plife_rows, self.plife_cols

    # Use seed for reproducible presets, or random
    rng = random.Random(seed) if seed is not None else random.Random()

    # Generate attraction/repulsion matrix: values in [-1, 1]
    self.plife_rules = []
    for i in range(num_types):
        row = []
        for j in range(num_types):
            row.append(rng.uniform(-1.0, 1.0))
        self.plife_rules.append(row)

    # Create particles
    self.plife_num_particles = max(30, int(rows * cols * density))
    self.plife_particles = []
    cr, cc = rows / 2.0, cols / 2.0
    radius = min(rows, cols) * 0.4
    for _ in range(self.plife_num_particles):
        angle = rng.random() * 2 * math.pi
        r_off = rng.random() * radius
        pr = cr + math.sin(angle) * r_off
        pc = cc + math.cos(angle) * r_off
        ptype = float(rng.randint(0, num_types - 1))
        self.plife_particles.append([pr % rows, pc % cols, 0.0, 0.0, ptype])

    self.plife_menu = False
    self.plife_mode = True
    self._flash(f"Particle Life: {name} — Space to start")



def _plife_step(self):
    """Advance Particle Life simulation by one step."""
    particles = self.plife_particles
    n = len(particles)
    rows, cols = self.plife_rows, self.plife_cols
    rules = self.plife_rules
    max_r = self.plife_max_radius
    max_r2 = max_r * max_r
    friction = self.plife_friction
    fscale = self.plife_force_scale
    half_rows = rows / 2.0
    half_cols = cols / 2.0

    new_particles = []
    for i in range(n):
        pr, pc, pvr, pvc, ptype = particles[i]
        pt = int(ptype)
        fr, fc = 0.0, 0.0

        for j in range(n):
            if i == j:
                continue
            qr, qc = particles[j][0], particles[j][1]
            qt = int(particles[j][4])

            # Toroidal distance
            dr = qr - pr
            dc = qc - pc
            if dr > half_rows:
                dr -= rows
            elif dr < -half_rows:
                dr += rows
            if dc > half_cols:
                dc -= cols
            elif dc < -half_cols:
                dc += cols

            dist2 = dr * dr + dc * dc
            if dist2 > max_r2 or dist2 < 0.01:
                continue

            dist = math.sqrt(dist2)
            # Normalized direction
            ndr = dr / dist
            ndc = dc / dist

            # Force profile: repel at very close range, then attraction/repulsion based on rule
            rel_dist = dist / max_r  # 0 to 1
            attraction = rules[pt][qt]

            if rel_dist < 0.3:
                # Strong short-range repulsion to prevent overlap
                force = (rel_dist / 0.3 - 1.0)
            else:
                # Attraction/repulsion based on rules, peaks at ~0.6 and fades to 0 at max_r
                force = attraction * (1.0 - abs(2.0 * rel_dist - 1.3) / 0.7)
                force = max(-1.0, min(1.0, force))

            fr += ndr * force * fscale
            fc += ndc * force * fscale

        # Apply forces and friction
        nvr = (pvr + fr) * (1.0 - friction)
        nvc = (pvc + fc) * (1.0 - friction)

        # Clamp velocity
        spd = math.sqrt(nvr * nvr + nvc * nvc)
        max_spd = 2.0
        if spd > max_spd:
            nvr = nvr / spd * max_spd
            nvc = nvc / spd * max_spd

        # Update position (toroidal wrap)
        nr = (pr + nvr) % rows
        nc = (pc + nvc) % cols
        new_particles.append([nr, nc, nvr, nvc, ptype])

    self.plife_particles = new_particles
    self.plife_generation += 1



def _handle_plife_menu_key(self, key: int) -> bool:
    """Handle input in Particle Life preset menu."""
    n = len(self.PLIFE_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.plife_menu_sel = (self.plife_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.plife_menu_sel = (self.plife_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._plife_init(self.plife_menu_sel)
    elif key in (ord("q"), 27):
        self.plife_menu = False
        self._flash("Particle Life cancelled")
    return True



def _handle_plife_key(self, key: int) -> bool:
    """Handle input in active Particle Life simulation."""
    if key == ord(" "):
        self.plife_running = not self.plife_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.plife_steps_per_frame):
            self._plife_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.PLIFE_PRESETS)
                    if p[0] == self.plife_preset_name), 0)
        self._plife_init(idx)
        self.plife_running = False
    elif key in (ord("R"), ord("m")):
        self.plife_mode = False
        self.plife_running = False
        self.plife_menu = True
        self.plife_menu_sel = 0
    elif key == ord("f") or key == ord("F"):
        delta = 0.05 if key == ord("f") else -0.05
        self.plife_friction = max(0.05, min(0.95, self.plife_friction + delta))
        self._flash(f"Friction: {self.plife_friction:.2f}")
    elif key == ord("d") or key == ord("D"):
        delta = 1.0 if key == ord("d") else -1.0
        self.plife_max_radius = max(5.0, min(40.0, self.plife_max_radius + delta))
        self._flash(f"Max radius: {self.plife_max_radius:.1f}")
    elif key == ord("g") or key == ord("G"):
        delta = 0.01 if key == ord("g") else -0.01
        self.plife_force_scale = max(0.01, min(0.20, self.plife_force_scale + delta))
        self._flash(f"Force scale: {self.plife_force_scale:.3f}")
    elif key == ord("x"):
        # Re-randomize rules with new seed
        rng = random.Random()
        self.plife_rules = []
        for i in range(self.plife_num_types):
            row = []
            for j in range(self.plife_num_types):
                row.append(rng.uniform(-1.0, 1.0))
            self.plife_rules.append(row)
        self._flash("Rules re-randomized!")
    elif key == ord("+") or key == ord("="):
        self.plife_steps_per_frame = min(10, self.plife_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.plife_steps_per_frame}")
    elif key == ord("-"):
        self.plife_steps_per_frame = max(1, self.plife_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.plife_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">") or key == ord("."):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_plife_mode()
    else:
        return True
    return True



def _draw_plife_menu(self, max_y: int, max_x: int):
    """Draw the Particle Life preset selection menu."""
    self.stdscr.erase()
    title = "── Particle Life (Primordial Soup) ── Select Configuration ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, nt, dens, mr, fric, fs, _seed) in enumerate(self.PLIFE_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<18s}  {desc}"
        params = f"    types={nt}  radius={mr:.0f}  friction={fric:.2f}  force={fs:.3f}"
        attr = curses.color_pair(6)
        if i == self.plife_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            self.stdscr.addstr(y + 1, 2, params[:max_x - 4], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_plife(self, max_y: int, max_x: int):
    """Draw the active Particle Life simulation."""
    self.stdscr.erase()
    particles = self.plife_particles
    rows, cols = self.plife_rows, self.plife_cols
    chars = self.PLIFE_CHARS
    colors = self.PLIFE_COLORS
    state = "▶ RUNNING" if self.plife_running else "⏸ PAUSED"

    # Title bar
    title = (f" Particle Life: {self.plife_preset_name}  |  gen {self.plife_generation}"
             f"  |  types={self.plife_num_types}"
             f"  r={self.plife_max_radius:.0f}"
             f"  fric={self.plife_friction:.2f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Grid area — render particles as colored symbols
    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Build occupancy grid: store particle index at each cell (last one wins)
    grid: dict[tuple[int, int], int] = {}
    for idx, (pr, pc, _vr, _vc, _pt) in enumerate(particles):
        ri = int(pr) % rows
        ci = int(pc) % cols
        if ri < view_rows and ci < view_cols:
            grid[(ri, ci)] = idx

    for (ri, ci), idx in grid.items():
        pt = int(particles[idx][4])
        ch = chars[pt % len(chars)]
        cp = colors[pt % len(colors)]
        # Brightness based on speed
        vr, vc = particles[idx][2], particles[idx][3]
        spd = math.sqrt(vr * vr + vc * vc)
        if spd > 1.0:
            attr = curses.color_pair(cp) | curses.A_BOLD
        elif spd > 0.3:
            attr = curses.color_pair(cp)
        else:
            attr = curses.color_pair(cp) | curses.A_DIM
        try:
            self.stdscr.addstr(1 + ri, ci * 2, ch + " ", attr)
        except curses.error:
            pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        avg_spd = 0.0
        for p in particles:
            avg_spd += math.sqrt(p[2] * p[2] + p[3] * p[3])
        avg_spd /= max(1, len(particles))
        info = (f" Gen {self.plife_generation}  |  particles={self.plife_num_particles}"
                f"  |  avg speed={avg_spd:.3f}"
                f"  |  steps/f={self.plife_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [f/F]=fric+/- [d/D]=radius+/- [g/G]=force+/- [x]=new rules [r]=reseed [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register plife mode methods on the App class."""
    App._enter_plife_mode = _enter_plife_mode
    App._exit_plife_mode = _exit_plife_mode
    App._plife_init = _plife_init
    App._plife_step = _plife_step
    App._handle_plife_menu_key = _handle_plife_menu_key
    App._handle_plife_key = _handle_plife_key
    App._draw_plife_menu = _draw_plife_menu
    App._draw_plife = _draw_plife

