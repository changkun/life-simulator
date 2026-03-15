"""Mode: boids — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS
from life.grid import Grid

def _enter_boids_mode(self):
    """Enter Boids mode — show preset menu."""
    self.boids_menu = True
    self.boids_menu_sel = 0
    self._flash("Boids — select a configuration")



def _exit_boids_mode(self):
    """Exit Boids mode."""
    self.boids_mode = False
    self.boids_menu = False
    self.boids_running = False
    self.boids_agents = []
    self._flash("Boids mode OFF")



def _boids_init(self, preset_idx: int):
    """Initialize Boids simulation with the given preset."""
    name, _desc, ratio, sr, ar, cr, sw, aw, cw, ms = self.BOIDS_PRESETS[preset_idx]
    self.boids_preset_name = name
    self.boids_separation_radius = sr
    self.boids_alignment_radius = ar
    self.boids_cohesion_radius = cr
    self.boids_separation_weight = sw
    self.boids_alignment_weight = aw
    self.boids_cohesion_weight = cw
    self.boids_max_speed = ms
    self.boids_generation = 0
    self.boids_running = False

    max_y, max_x = self.stdscr.getmaxyx()
    self.boids_rows = max(10, max_y - 3)
    self.boids_cols = max(10, (max_x - 1) // 2)

    rows, cols = self.boids_rows, self.boids_cols
    self.boids_num_agents = max(30, int(rows * cols * ratio))
    self.boids_agents = []
    cr_center, cc_center = rows / 2.0, cols / 2.0
    radius = min(rows, cols) * 0.35
    for _ in range(self.boids_num_agents):
        angle = random.random() * 2 * math.pi
        r_off = random.random() * radius
        br = cr_center + math.sin(angle) * r_off
        bc = cc_center + math.cos(angle) * r_off
        # Random initial velocity
        va = random.random() * 2 * math.pi
        spd = random.uniform(0.2, ms)
        vr = math.sin(va) * spd
        vc = math.cos(va) * spd
        self.boids_agents.append([br % rows, bc % cols, vr, vc])

    self.boids_menu = False
    self.boids_mode = True
    self._flash(f"Boids: {name} — Space to start")



def _boids_step(self):
    """Advance Boids simulation by one step (Reynolds' rules)."""
    agents = self.boids_agents
    n = len(agents)
    rows, cols = self.boids_rows, self.boids_cols
    sep_r = self.boids_separation_radius
    ali_r = self.boids_alignment_radius
    coh_r = self.boids_cohesion_radius
    sep_w = self.boids_separation_weight
    ali_w = self.boids_alignment_weight
    coh_w = self.boids_cohesion_weight
    max_spd = self.boids_max_speed

    # Precompute squared radii
    sep_r2 = sep_r * sep_r
    ali_r2 = ali_r * ali_r
    coh_r2 = coh_r * coh_r

    new_agents = []
    for i in range(n):
        ar, ac, avr, avc = agents[i]

        # Accumulators for the three rules
        sep_dr, sep_dc, sep_count = 0.0, 0.0, 0
        ali_vr, ali_vc, ali_count = 0.0, 0.0, 0
        coh_cr, coh_cc, coh_count = 0.0, 0.0, 0

        for j in range(n):
            if i == j:
                continue
            br, bc = agents[j][0], agents[j][1]
            # Toroidal distance
            dr = br - ar
            dc = bc - ac
            if dr > rows / 2:
                dr -= rows
            elif dr < -rows / 2:
                dr += rows
            if dc > cols / 2:
                dc -= cols
            elif dc < -cols / 2:
                dc += cols
            dist2 = dr * dr + dc * dc

            # Separation: steer away from nearby boids
            if dist2 < sep_r2 and dist2 > 0.001:
                sep_dr -= dr / dist2
                sep_dc -= dc / dist2
                sep_count += 1

            # Alignment: match velocity of neighbors
            if dist2 < ali_r2:
                ali_vr += agents[j][2]
                ali_vc += agents[j][3]
                ali_count += 1

            # Cohesion: steer towards center of neighbors
            if dist2 < coh_r2:
                coh_cr += dr
                coh_cc += dc
                coh_count += 1

        # Compute steering forces
        steer_r, steer_c = 0.0, 0.0

        if sep_count > 0:
            steer_r += sep_dr * sep_w
            steer_c += sep_dc * sep_w

        if ali_count > 0:
            steer_r += (ali_vr / ali_count - avr) * ali_w
            steer_c += (ali_vc / ali_count - avc) * ali_w

        if coh_count > 0:
            steer_r += (coh_cr / coh_count) * coh_w * 0.1
            steer_c += (coh_cc / coh_count) * coh_w * 0.1

        # Apply steering
        nvr = avr + steer_r * 0.1
        nvc = avc + steer_c * 0.1

        # Clamp speed
        spd = math.sqrt(nvr * nvr + nvc * nvc)
        if spd > max_spd:
            nvr = nvr / spd * max_spd
            nvc = nvc / spd * max_spd
        elif spd < 0.1:
            # Minimum speed to keep boids moving
            angle = random.random() * 2 * math.pi
            nvr = math.sin(angle) * 0.2
            nvc = math.cos(angle) * 0.2

        # Update position (toroidal wrap)
        nr = (ar + nvr) % rows
        nc = (ac + nvc) % cols
        new_agents.append([nr, nc, nvr, nvc])

    self.boids_agents = new_agents
    self.boids_generation += 1



def _handle_boids_menu_key(self, key: int) -> bool:
    """Handle input in Boids preset menu."""
    n = len(self.BOIDS_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.boids_menu_sel = (self.boids_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.boids_menu_sel = (self.boids_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._boids_init(self.boids_menu_sel)
    elif key in (ord("q"), 27):
        self.boids_menu = False
        self._flash("Boids cancelled")
    return True



def _handle_boids_key(self, key: int) -> bool:
    """Handle input in active Boids simulation."""
    if key == ord(" "):
        self.boids_running = not self.boids_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.boids_steps_per_frame):
            self._boids_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.BOIDS_PRESETS)
                    if p[0] == self.boids_preset_name), 0)
        self._boids_init(idx)
        self.boids_running = False
    elif key in (ord("R"), ord("m")):
        self.boids_mode = False
        self.boids_running = False
        self.boids_menu = True
        self.boids_menu_sel = 0
    elif key == ord("s") or key == ord("S"):
        delta = 0.5 if key == ord("s") else -0.5
        self.boids_separation_radius = max(1.0, min(15.0, self.boids_separation_radius + delta))
        self._flash(f"Separation radius: {self.boids_separation_radius:.1f}")
    elif key == ord("a") or key == ord("A"):
        delta = 1.0 if key == ord("a") else -1.0
        self.boids_alignment_radius = max(2.0, min(30.0, self.boids_alignment_radius + delta))
        self._flash(f"Alignment radius: {self.boids_alignment_radius:.1f}")
    elif key == ord("c") or key == ord("C"):
        delta = 1.0 if key == ord("c") else -1.0
        self.boids_cohesion_radius = max(2.0, min(40.0, self.boids_cohesion_radius + delta))
        self._flash(f"Cohesion radius: {self.boids_cohesion_radius:.1f}")
    elif key == ord("+") or key == ord("="):
        self.boids_steps_per_frame = min(10, self.boids_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.boids_steps_per_frame}")
    elif key == ord("-"):
        self.boids_steps_per_frame = max(1, self.boids_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.boids_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">") or key == ord("."):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_boids_mode()
    else:
        return True
    return True



def _draw_boids_menu(self, max_y: int, max_x: int):
    """Draw the Boids preset selection menu."""
    self.stdscr.erase()
    title = "── Boids Flocking Simulation ── Select Configuration ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, ratio, sr, ar, cr, sw, aw, cw, ms) in enumerate(self.BOIDS_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<14s}  {desc}"
        params = f"    sep={sr:.1f}  ali={ar:.1f}  coh={cr:.1f}  spd={ms:.1f}"
        attr = curses.color_pair(6)
        if i == self.boids_menu_sel:
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



def _draw_boids(self, max_y: int, max_x: int):
    """Draw the active Boids simulation."""
    self.stdscr.erase()
    agents = self.boids_agents
    rows, cols = self.boids_rows, self.boids_cols
    arrows = self.BOIDS_ARROWS
    state = "▶ RUNNING" if self.boids_running else "⏸ PAUSED"

    # Title bar
    title = (f" Boids: {self.boids_preset_name}  |  gen {self.boids_generation}"
             f"  |  sep={self.boids_separation_radius:.1f}"
             f"  ali={self.boids_alignment_radius:.1f}"
             f"  coh={self.boids_cohesion_radius:.1f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Grid area — render boids as directional arrows
    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Build occupancy grid: store index of boid at each cell (last one wins)
    grid: dict[tuple[int, int], int] = {}
    for idx, (br, bc, vr, vc) in enumerate(agents):
        ri = int(br) % rows
        ci = int(bc) % cols
        if ri < view_rows and ci < view_cols:
            grid[(ri, ci)] = idx

    for (ri, ci), idx in grid.items():
        vr, vc = agents[idx][2], agents[idx][3]
        # Compute direction from velocity → 8-way arrow
        angle = math.atan2(vc, vr)  # atan2(x, y) for row=down, col=right
        # Map angle to 0-7: 0=up, 1=NE, 2=right, 3=SE, 4=down, 5=SW, 6=left, 7=NW
        # vr positive = moving down, vc positive = moving right
        angle_deg = math.degrees(math.atan2(vc, vr))
        dir_idx = int((angle_deg + 180 + 22.5) / 45.0) % 8
        arrow = arrows[dir_idx]

        # Color based on speed
        spd = math.sqrt(vr * vr + vc * vc)
        if spd > self.boids_max_speed * 0.7:
            attr = curses.color_pair(6) | curses.A_BOLD
        elif spd > self.boids_max_speed * 0.3:
            attr = curses.color_pair(6)
        else:
            attr = curses.color_pair(6) | curses.A_DIM
        try:
            self.stdscr.addstr(1 + ri, ci * 2, arrow + " ", attr)
        except curses.error:
            pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        avg_spd = 0.0
        for a in agents:
            avg_spd += math.sqrt(a[2] * a[2] + a[3] * a[3])
        avg_spd /= max(1, len(agents))
        info = (f" Gen {self.boids_generation}  |  boids={self.boids_num_agents}"
                f"  |  avg speed={avg_spd:.3f}"
                f"  |  steps/f={self.boids_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [s/S]=sep+/- [a/A]=ali+/- [c/C]=coh+/- [r]=reseed [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Particle Life (Primordial Soup) — Mode 10 (key '0')
# ══════════════════════════════════════════════════════════════════════

# Particle type display characters and color pairs
PLIFE_CHARS = ["●", "◆", "■", "▲", "★", "◉", "♦", "✦"]
PLIFE_COLORS = [1, 2, 3, 4, 5, 6, 7, 1]  # color pair indices

PLIFE_PRESETS = [
    # (name, description, num_types, density, max_radius, friction, force_scale, seed_or_none)
    ("Primordial Soup", "Random rules — classic emergent life", 6, 0.06, 15.0, 0.5, 0.05, None),
    ("Symbiosis", "Species that orbit and depend on each other", 4, 0.05, 18.0, 0.4, 0.04, 42),
    ("Clusters", "Tight self-organizing clumps", 3, 0.08, 12.0, 0.6, 0.06, 123),
    ("Predator-Prey", "Chasing and fleeing dynamics", 5, 0.05, 20.0, 0.3, 0.04, 7),
    ("Galaxy", "Spiraling orbital structures", 4, 0.04, 25.0, 0.35, 0.03, 314),
    ("Chaos", "High energy, many types, wild behavior", 8, 0.07, 14.0, 0.25, 0.07, None),
]




def register(App):
    """Register boids mode methods on the App class."""
    App._enter_boids_mode = _enter_boids_mode
    App._exit_boids_mode = _exit_boids_mode
    App._boids_init = _boids_init
    App._boids_step = _boids_step
    App._handle_boids_menu_key = _handle_boids_menu_key
    App._handle_boids_key = _handle_boids_key
    App._draw_boids_menu = _draw_boids_menu
    App._draw_boids = _draw_boids

