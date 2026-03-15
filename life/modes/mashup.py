"""Mode: mashup — layer two simulations on the same grid with emergent coupling."""
import curses
import math
import random
import time

from life.constants import SPEEDS

# Density visualization characters (5 levels: blank, light, medium, dense, solid)
_DENSITY = " ░▒▓█"

# ── Mashable simulation catalogue ────────────────────────────────────

MASHUP_SIMS = [
    {"name": "Game of Life",        "id": "gol",      "desc": "Conway's classic cellular automaton"},
    {"name": "Wave Equation",       "id": "wave",     "desc": "2D wave propagation and interference"},
    {"name": "Reaction-Diffusion",  "id": "rd",       "desc": "Gray-Scott pattern formation"},
    {"name": "Forest Fire",         "id": "fire",     "desc": "Fire spread with tree regrowth"},
    {"name": "Boids Flocking",      "id": "boids",    "desc": "Reynolds flocking agents"},
    {"name": "Ising Model",         "id": "ising",    "desc": "Magnetic spin lattice"},
    {"name": "Rock-Paper-Scissors", "id": "rps",      "desc": "Cyclic dominance competition"},
    {"name": "Physarum Slime",      "id": "physarum",  "desc": "Slime mold trail network"},
]

_SIM_BY_ID = {s["id"]: s for s in MASHUP_SIMS}

MASHUP_PRESETS = [
    ("Boids + Wave Equation", "boids", "wave",
     "Waves steer flocking boids; boids create ripples"),
    ("Fire + Game of Life", "fire", "gol",
     "Living cells fuel fire; fire clears life; life regrows"),
    ("Reaction-Diffusion + Ising", "rd", "ising",
     "Chemical patterns polarize spins; spins modulate reactions"),
    ("Boids + Physarum Slime", "boids", "physarum",
     "Flock follows slime trails; boids deposit pheromone"),
    ("Wave + Reaction-Diffusion", "wave", "rd",
     "Waves modulate reactions; reactions spawn wave pulses"),
    ("Fire + Boids", "fire", "boids",
     "Fire repels boids; dense flocks fuel combustion"),
    ("Ising + Rock-Paper-Scissors", "ising", "rps",
     "Spin alignment guides invasion; invasions flip spins"),
    ("Game of Life + Wave", "gol", "wave",
     "Life cells pulse waves; wave energy births new cells"),
]


# ════════════════════════════════════════════════════════════════════
#  Mini-simulation engines
#
#  Each engine exposes three functions:
#    init(rows, cols) -> state_dict
#    step(state, other_density, coupling_strength) -> None  (mutates)
#    density(state) -> list[list[float]]  in [0, 1]
# ════════════════════════════════════════════════════════════════════


# ── Game of Life ─────────────────────────────────────────────────────

def _init_gol(rows, cols):
    g = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if random.random() < 0.2:
                g[r][c] = 1
    return {"type": "gol", "g": g, "rows": rows, "cols": cols}


def _step_gol(s, od, st):
    rows, cols = s["rows"], s["cols"]
    g = s["g"]
    ng = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    n += g[(r + dr) % rows][(c + dc) % cols]
            alive = g[r][c]
            # Coupling: other density can trigger spontaneous birth
            birth_extra = od[r][c] * st * 0.4 if od else 0.0
            if alive:
                ng[r][c] = 1 if n in (2, 3) else 0
            else:
                if n == 3 or (n == 2 and random.random() < birth_extra):
                    ng[r][c] = 1
    s["g"] = ng


def _density_gol(s):
    return [[float(v) for v in row] for row in s["g"]]


# ── Wave Equation ────────────────────────────────────────────────────

def _init_wave(rows, cols):
    u = [[0.0] * cols for _ in range(rows)]
    up = [[0.0] * cols for _ in range(rows)]
    cr, cc = rows // 2, cols // 2
    for r in range(rows):
        for c in range(cols):
            dx = (c - cc) / max(cols, 1) * 4
            dy = (r - cr) / max(rows, 1) * 4
            u[r][c] = math.exp(-(dx * dx + dy * dy) * 2.0)
    return {"type": "wave", "u": u, "up": up, "rows": rows, "cols": cols,
            "c": 0.3, "damp": 0.998}


def _step_wave(s, od, st):
    rows, cols = s["rows"], s["cols"]
    u, up = s["u"], s["up"]
    c2 = s["c"] ** 2
    damp = s["damp"]
    nu = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            lap = (u[(r - 1) % rows][c] + u[(r + 1) % rows][c] +
                   u[r][(c - 1) % cols] + u[r][(c + 1) % cols] - 4 * u[r][c])
            force = od[r][c] * st * 0.3 if od else 0.0
            nu[r][c] = (2 * u[r][c] - up[r][c] + c2 * lap + force) * damp
    s["up"] = u
    s["u"] = nu


def _density_wave(s):
    rows, cols = s["rows"], s["cols"]
    mx = 0.001
    for r in range(rows):
        for c in range(cols):
            v = abs(s["u"][r][c])
            if v > mx:
                mx = v
    return [[min(1.0, abs(s["u"][r][c]) / mx) for c in range(cols)]
            for r in range(rows)]


# ── Reaction-Diffusion (Gray-Scott) ─────────────────────────────────

def _init_rd(rows, cols):
    U = [[1.0] * cols for _ in range(rows)]
    V = [[0.0] * cols for _ in range(rows)]
    cr, cc = rows // 2, cols // 2
    for r in range(max(0, cr - 5), min(rows, cr + 5)):
        for c in range(max(0, cc - 5), min(cols, cc + 5)):
            U[r][c] = 0.5 + random.random() * 0.1
            V[r][c] = 0.25 + random.random() * 0.1
    return {"type": "rd", "U": U, "V": V, "rows": rows, "cols": cols,
            "f": 0.035, "k": 0.065, "Du": 0.16, "Dv": 0.08}


def _step_rd(s, od, st):
    rows, cols = s["rows"], s["cols"]
    U, V = s["U"], s["V"]
    f, k, Du, Dv = s["f"], s["k"], s["Du"], s["Dv"]
    nU = [[0.0] * cols for _ in range(rows)]
    nV = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            u, v = U[r][c], V[r][c]
            lu = (U[(r - 1) % rows][c] + U[(r + 1) % rows][c] +
                  U[r][(c - 1) % cols] + U[r][(c + 1) % cols] - 4 * u)
            lv = (V[(r - 1) % rows][c] + V[(r + 1) % rows][c] +
                  V[r][(c - 1) % cols] + V[r][(c + 1) % cols] - 4 * v)
            uvv = u * v * v
            f_local = f + (od[r][c] * st * 0.02 if od else 0.0)
            nU[r][c] = max(0.0, min(1.0, u + Du * lu - uvv + f_local * (1 - u)))
            nV[r][c] = max(0.0, min(1.0, v + Dv * lv + uvv - (f_local + k) * v))
    s["U"] = nU
    s["V"] = nV


def _density_rd(s):
    return [[min(1.0, max(0.0, v)) for v in row] for row in s["V"]]


# ── Forest Fire ──────────────────────────────────────────────────────

def _init_fire(rows, cols):
    g = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if random.random() < 0.6:
                g[r][c] = 1
    for _ in range(max(1, rows * cols // 200)):
        g[random.randint(0, rows - 1)][random.randint(0, cols - 1)] = 2
    return {"type": "fire", "g": g, "rows": rows, "cols": cols,
            "p_grow": 0.01, "p_ignite": 0.0005}


def _step_fire(s, od, st):
    rows, cols = s["rows"], s["cols"]
    g = s["g"]
    ng = [[0] * cols for _ in range(rows)]
    pg, pi = s["p_grow"], s["p_ignite"]
    for r in range(rows):
        for c in range(cols):
            cell = g[r][c]
            if cell == 2:
                ng[r][c] = 0
            elif cell == 1:
                has_fire = False
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        if g[(r + dr) % rows][(c + dc) % cols] == 2:
                            has_fire = True
                            break
                    if has_fire:
                        break
                extra = od[r][c] * st * 0.05 if od else 0.0
                if has_fire or random.random() < pi + extra:
                    ng[r][c] = 2
                else:
                    ng[r][c] = 1
            else:
                if random.random() < pg:
                    ng[r][c] = 1
    s["g"] = ng


def _density_fire(s):
    return [[1.0 if v == 2 else (0.3 if v == 1 else 0.0) for v in row]
            for row in s["g"]]


# ── Boids Flocking ───────────────────────────────────────────────────

def _init_boids(rows, cols):
    n = max(30, rows * cols // 25)
    agents = []
    cr, cc = rows / 2.0, cols / 2.0
    radius = min(rows, cols) * 0.35
    for _ in range(n):
        a = random.random() * 2 * math.pi
        ro = random.random() * radius
        br = (cr + math.sin(a) * ro) % rows
        bc = (cc + math.cos(a) * ro) % cols
        va = random.random() * 2 * math.pi
        spd = random.uniform(0.2, 0.8)
        agents.append([br, bc, math.sin(va) * spd, math.cos(va) * spd])
    return {"type": "boids", "agents": agents, "rows": rows, "cols": cols,
            "sep_r": 3.0, "ali_r": 8.0, "coh_r": 10.0,
            "sep_w": 1.5, "ali_w": 1.0, "coh_w": 1.0, "max_spd": 1.0}


def _step_boids(s, od, st):
    agents = s["agents"]
    n = len(agents)
    rows, cols = s["rows"], s["cols"]
    sr, ar, cr2 = s["sep_r"], s["ali_r"], s["coh_r"]
    sw, aw, cw = s["sep_w"], s["ali_w"], s["coh_w"]
    ms = s["max_spd"]
    new_agents = []
    for i in range(n):
        br, bc, vr, vc = agents[i]
        sep_r2, sep_c2 = 0.0, 0.0
        ali_r2, ali_c2 = 0.0, 0.0
        coh_r2, coh_c2 = 0.0, 0.0
        sc, ac, cc2 = 0, 0, 0
        for j in range(n):
            if i == j:
                continue
            dr = agents[j][0] - br
            dc = agents[j][1] - bc
            if dr > rows / 2:
                dr -= rows
            if dr < -rows / 2:
                dr += rows
            if dc > cols / 2:
                dc -= cols
            if dc < -cols / 2:
                dc += cols
            d = math.sqrt(dr * dr + dc * dc) + 0.001
            if d < sr:
                sep_r2 -= dr / d
                sep_c2 -= dc / d
                sc += 1
            if d < ar:
                ali_r2 += agents[j][2]
                ali_c2 += agents[j][3]
                ac += 1
            if d < cr2:
                coh_r2 += dr
                coh_c2 += dc
                cc2 += 1
        if sc > 0:
            vr += sep_r2 / sc * sw
            vc += sep_c2 / sc * sw
        if ac > 0:
            vr += (ali_r2 / ac - vr) * aw * 0.1
            vc += (ali_c2 / ac - vc) * aw * 0.1
        if cc2 > 0:
            vr += coh_r2 / cc2 * cw * 0.01
            vc += coh_c2 / cc2 * cw * 0.01
        # Coupling: steer toward gradient of other density
        if od and st > 0:
            ri, ci = int(br) % rows, int(bc) % cols
            gr_d = (od[(ri + 1) % rows][ci] - od[(ri - 1) % rows][ci]) * 0.5
            gc_d = (od[ri][(ci + 1) % cols] - od[ri][(ci - 1) % cols]) * 0.5
            vr += gr_d * st * 2.0
            vc += gc_d * st * 2.0
        spd = math.sqrt(vr * vr + vc * vc)
        if spd > ms:
            vr = vr / spd * ms
            vc = vc / spd * ms
        new_agents.append([(br + vr) % rows, (bc + vc) % cols, vr, vc])
    s["agents"] = new_agents


def _density_boids(s):
    rows, cols = s["rows"], s["cols"]
    d = [[0.0] * cols for _ in range(rows)]
    for br, bc, _, _ in s["agents"]:
        ri, ci = int(br) % rows, int(bc) % cols
        d[ri][ci] = min(1.0, d[ri][ci] + 0.5)
    return d


# ── Ising Model ──────────────────────────────────────────────────────

def _init_ising(rows, cols):
    g = [[random.choice([-1, 1]) for _ in range(cols)] for _ in range(rows)]
    return {"type": "ising", "g": g, "rows": rows, "cols": cols, "T": 2.3}


def _step_ising(s, od, st):
    rows, cols = s["rows"], s["cols"]
    g = s["g"]
    T = s["T"]
    flips = rows * cols
    for _ in range(flips):
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        spin = g[r][c]
        nb = (g[(r - 1) % rows][c] + g[(r + 1) % rows][c] +
              g[r][(c - 1) % cols] + g[r][(c + 1) % cols])
        h = od[r][c] * st * 2.0 if od else 0.0
        dE = 2 * spin * (nb + h)
        if dE <= 0 or random.random() < math.exp(-dE / max(T, 0.01)):
            g[r][c] = -spin


def _density_ising(s):
    return [[(v + 1) / 2.0 for v in row] for row in s["g"]]


# ── Rock-Paper-Scissors ──────────────────────────────────────────────

def _init_rps(rows, cols):
    g = [[random.randint(0, 2) for _ in range(cols)] for _ in range(rows)]
    return {"type": "rps", "g": g, "rows": rows, "cols": cols}


def _step_rps(s, od, st):
    rows, cols = s["rows"], s["cols"]
    g = s["g"]
    for _ in range(rows * cols // 2):
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        dr, dc = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
        nr, nc = (r + dr) % rows, (c + dc) % cols
        me, them = g[r][c], g[nr][nc]
        if (them - me) % 3 == 1:
            prob = 0.5 + (od[r][c] * st * 0.3 if od else 0.0)
            if random.random() < prob:
                g[r][c] = them


def _density_rps(s):
    return [[v / 2.0 for v in row] for row in s["g"]]


# ── Physarum Slime Mold ──────────────────────────────────────────────

def _init_physarum(rows, cols):
    n = max(50, rows * cols // 15)
    agents = []
    for _ in range(n):
        agents.append([random.random() * rows, random.random() * cols,
                       random.random() * 2 * math.pi])
    trail = [[0.0] * cols for _ in range(rows)]
    return {"type": "physarum", "agents": agents, "trail": trail,
            "rows": rows, "cols": cols,
            "sensor_dist": 4.0, "sensor_angle": 0.5,
            "turn_speed": 0.4, "deposit": 0.5, "decay": 0.95}


def _step_physarum(s, od, st):
    rows, cols = s["rows"], s["cols"]
    trail = s["trail"]
    agents = s["agents"]
    sd = s["sensor_dist"]
    sa = s["sensor_angle"]
    ts = s["turn_speed"]
    dep = s["deposit"]
    decay = s["decay"]

    for agent in agents:
        r, c, angle = agent

        def _sense(a):
            sr2 = (r + math.sin(a) * sd) % rows
            sc2 = (c + math.cos(a) * sd) % cols
            return trail[int(sr2) % rows][int(sc2) % cols]

        fl = _sense(angle - sa)
        fc = _sense(angle)
        fr = _sense(angle + sa)
        if fc >= fl and fc >= fr:
            pass
        elif fl > fr:
            agent[2] -= ts
        else:
            agent[2] += ts
        # Coupling: bias toward high other-density areas
        if od and st > 0:
            ri, ci = int(r) % rows, int(c) % cols
            gr_d = (od[(ri + 1) % rows][ci] - od[(ri - 1) % rows][ci]) * 0.5
            gc_d = (od[ri][(ci + 1) % cols] - od[ri][(ci - 1) % cols]) * 0.5
            if abs(gr_d) + abs(gc_d) > 0.01:
                target = math.atan2(gc_d, gr_d)
                diff = target - agent[2]
                while diff > math.pi:
                    diff -= 2 * math.pi
                while diff < -math.pi:
                    diff += 2 * math.pi
                agent[2] += diff * st * 0.3
        # Move
        agent[0] = (r + math.sin(agent[2]) * 0.5) % rows
        agent[1] = (c + math.cos(agent[2]) * 0.5) % cols
        # Deposit
        ri, ci = int(agent[0]) % rows, int(agent[1]) % cols
        trail[ri][ci] = min(1.0, trail[ri][ci] + dep)

    # Diffuse and decay trail
    nt = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            avg = trail[r][c] * 0.6
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                avg += trail[(r + dr) % rows][(c + dc) % cols] * 0.1
            nt[r][c] = avg * decay
            if od and st > 0:
                nt[r][c] = min(1.0, nt[r][c] + od[r][c] * st * 0.05)
    s["trail"] = nt


def _density_physarum(s):
    return [[min(1.0, v) for v in row] for row in s["trail"]]


# ════════════════════════════════════════════════════════════════════
#  Engine dispatch table
# ════════════════════════════════════════════════════════════════════

_ENGINES = {
    "gol":      (_init_gol,      _step_gol,      _density_gol),
    "wave":     (_init_wave,     _step_wave,     _density_wave),
    "rd":       (_init_rd,       _step_rd,       _density_rd),
    "fire":     (_init_fire,     _step_fire,     _density_fire),
    "boids":    (_init_boids,    _step_boids,    _density_boids),
    "ising":    (_init_ising,    _step_ising,    _density_ising),
    "rps":      (_init_rps,      _step_rps,      _density_rps),
    "physarum": (_init_physarum, _step_physarum, _density_physarum),
}


# ════════════════════════════════════════════════════════════════════
#  Mode entry / exit
# ════════════════════════════════════════════════════════════════════

def _enter_mashup_mode(self):
    """Enter Mashup mode — show combo selection menu."""
    self.mashup_menu = True
    self.mashup_menu_sel = 0
    self.mashup_menu_phase = 0
    self._flash("Simulation Mashup — pick a combo")


def _exit_mashup_mode(self):
    """Exit Mashup mode and clean up."""
    self.mashup_mode = False
    self.mashup_menu = False
    self.mashup_running = False
    self.mashup_sim_a = None
    self.mashup_sim_b = None
    self._flash("Mashup mode OFF")


# ════════════════════════════════════════════════════════════════════
#  Initialization
# ════════════════════════════════════════════════════════════════════

def _mashup_init(self, id_a, id_b):
    """Initialize both simulations on a shared grid."""
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.mashup_rows = rows
    self.mashup_cols = cols
    self.mashup_sim_a_id = id_a
    self.mashup_sim_b_id = id_b
    self.mashup_sim_a_name = _SIM_BY_ID[id_a]["name"]
    self.mashup_sim_b_name = _SIM_BY_ID[id_b]["name"]

    init_a, _, dens_a = _ENGINES[id_a]
    init_b, _, dens_b = _ENGINES[id_b]
    self.mashup_sim_a = init_a(rows, cols)
    self.mashup_sim_b = init_b(rows, cols)
    self.mashup_generation = 0
    self.mashup_running = False
    self.mashup_coupling = 0.5

    # Compute initial density maps
    self.mashup_density_a = dens_a(self.mashup_sim_a)
    self.mashup_density_b = dens_b(self.mashup_sim_b)

    self.mashup_menu = False
    self.mashup_mode = True
    self._flash(f"Mashup: {self.mashup_sim_a_name} + {self.mashup_sim_b_name} — Space to start")


# ════════════════════════════════════════════════════════════════════
#  Simulation step
# ════════════════════════════════════════════════════════════════════

def _mashup_step(self):
    """Advance both simulations by one step with mutual coupling."""
    _, step_a, density_a = _ENGINES[self.mashup_sim_a_id]
    _, step_b, density_b = _ENGINES[self.mashup_sim_b_id]

    # Each sim receives the other's density as coupling input
    step_a(self.mashup_sim_a, self.mashup_density_b, self.mashup_coupling)
    step_b(self.mashup_sim_b, self.mashup_density_a, self.mashup_coupling)

    # Refresh density maps
    self.mashup_density_a = density_a(self.mashup_sim_a)
    self.mashup_density_b = density_b(self.mashup_sim_b)

    self.mashup_generation += 1


# ════════════════════════════════════════════════════════════════════
#  Menu drawing
# ════════════════════════════════════════════════════════════════════

def _draw_mashup_menu(self, max_y, max_x):
    """Draw the mashup mode selection menu."""
    self.stdscr.erase()
    phase = self.mashup_menu_phase

    title = "── Simulation Mashup ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if phase == 0:
        # ── Preset selection ──
        subtitle = "Choose a preset mashup or build your own:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass

        for i, (name, _, _, desc) in enumerate(MASHUP_PRESETS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.mashup_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            line = f"{marker}{name}"
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            except curses.error:
                pass
            if sel:
                try:
                    self.stdscr.addstr(y, 2 + len(line) + 2,
                                       desc[:max_x - len(line) - 6],
                                       curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass

        # Custom option at the end
        ci = len(MASHUP_PRESETS)
        y = 5 + ci
        if y < max_y - 3:
            sel = self.mashup_menu_sel == ci
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(3)
            try:
                self.stdscr.addstr(y, 2, f"{marker}Custom Mashup..."[:max_x - 4], attr)
            except curses.error:
                pass

    elif phase == 1:
        # ── Pick Simulation A ──
        subtitle = "Select Simulation A:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass
        for i, sim in enumerate(MASHUP_SIMS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.mashup_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    elif phase == 2:
        # ── Pick Simulation B ──
        subtitle = f"Sim A: {_SIM_BY_ID[self.mashup_pick_a]['name']}  |  Select Simulation B:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2),
                               subtitle[:max_x - 2], curses.color_pair(6))
        except curses.error:
            pass
        available = [s for s in MASHUP_SIMS if s["id"] != self.mashup_pick_a]
        for idx, sim in enumerate(available):
            y = 5 + idx
            if y >= max_y - 3:
                break
            sel = idx == self.mashup_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [Up/Down]=navigate  [Enter]=select  [Esc]=back/exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Menu key handling
# ════════════════════════════════════════════════════════════════════

def _handle_mashup_menu_key(self, key):
    """Handle input in the mashup combo selection menu."""
    if key == -1:
        return True
    phase = self.mashup_menu_phase

    if phase == 0:
        n = len(MASHUP_PRESETS) + 1  # +1 for Custom
    elif phase == 1:
        n = len(MASHUP_SIMS)
    else:
        n = len([s for s in MASHUP_SIMS if s["id"] != self.mashup_pick_a])

    if key == curses.KEY_UP or key == ord("k"):
        self.mashup_menu_sel = (self.mashup_menu_sel - 1) % max(1, n)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.mashup_menu_sel = (self.mashup_menu_sel + 1) % max(1, n)
        return True
    if key == 27:  # Esc
        if phase > 0:
            self.mashup_menu_phase = phase - 1
            self.mashup_menu_sel = 0
        else:
            self.mashup_menu = False
            self._flash("Mashup cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if phase == 0:
            sel = self.mashup_menu_sel
            if sel < len(MASHUP_PRESETS):
                _, id_a, id_b, _ = MASHUP_PRESETS[sel]
                self._mashup_init(id_a, id_b)
            else:
                self.mashup_menu_phase = 1
                self.mashup_menu_sel = 0
        elif phase == 1:
            self.mashup_pick_a = MASHUP_SIMS[self.mashup_menu_sel]["id"]
            self.mashup_menu_phase = 2
            self.mashup_menu_sel = 0
        elif phase == 2:
            available = [s for s in MASHUP_SIMS if s["id"] != self.mashup_pick_a]
            id_b = available[self.mashup_menu_sel]["id"]
            self._mashup_init(self.mashup_pick_a, id_b)
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Main simulation drawing
# ════════════════════════════════════════════════════════════════════

def _draw_mashup(self, max_y, max_x):
    """Draw the overlaid mashup simulation."""
    self.stdscr.erase()

    state = "▶ RUNNING" if self.mashup_running else "⏸ PAUSED"
    title = (f" MASHUP: {self.mashup_sim_a_name} + {self.mashup_sim_b_name}"
             f"  |  gen {self.mashup_generation}"
             f"  |  coupling={self.mashup_coupling:.2f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # ── Render overlaid density grid ──
    rows = self.mashup_rows
    cols = self.mashup_cols
    da = self.mashup_density_a
    db = self.mashup_density_b
    view_rows = min(rows, max_y - 4)
    view_cols = min(cols, (max_x - 1) // 2)

    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 2:
            break
        da_row = da[r] if r < len(da) else []
        db_row = db[r] if r < len(db) else []
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            va = da_row[c] if c < len(da_row) else 0.0
            vb = db_row[c] if c < len(db_row) else 0.0
            mx = max(va, vb)
            if mx < 0.01:
                continue

            # Density glyph
            di = max(1, min(4, int(mx * 4.0)))
            ch = _DENSITY[di]

            # Color based on which sim dominates
            if va > vb * 2 + 0.05:
                pair = 6   # cyan: Sim A
            elif vb > va * 2 + 0.05:
                pair = 1   # red: Sim B
            elif va > 0.01 and vb > 0.01:
                pair = 5   # magenta: overlap
            elif va > vb:
                pair = 6
            else:
                pair = 1

            # Brightness from intensity
            if mx > 0.7:
                attr = curses.color_pair(pair) | curses.A_BOLD
            elif mx > 0.3:
                attr = curses.color_pair(pair)
            else:
                attr = curses.color_pair(pair) | curses.A_DIM

            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass

    # ── Legend bar ──
    legend_y = max_y - 3
    if legend_y > 1:
        legend = (f" ■ {self.mashup_sim_a_name}=cyan"
                  f"  ■ {self.mashup_sim_b_name}=red"
                  f"  ■ overlap=magenta")
        try:
            self.stdscr.addstr(legend_y, 0, legend[:max_x - 1],
                               curses.color_pair(7))
        except curses.error:
            pass

    # ── Status bar ──
    status_y = max_y - 2
    if status_y > 1:
        sa = sb = 0.0
        cnt = max(1, rows * cols)
        for r in range(min(rows, len(da))):
            for c in range(min(cols, len(da[r]) if r < len(da) else 0)):
                sa += da[r][c]
            for c in range(min(cols, len(db[r]) if r < len(db) else 0)):
                sb += db[r][c]
        sa /= cnt
        sb /= cnt
        status = (f" gen {self.mashup_generation}  |"
                  f"  A density={sa:.3f}  B density={sb:.3f}  |"
                  f"  coupling={self.mashup_coupling:.2f}")
        try:
            self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # ── Hint bar ──
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [+/-]=coupling [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Simulation key handling
# ════════════════════════════════════════════════════════════════════

def _handle_mashup_key(self, key):
    """Handle input during active mashup simulation."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_mashup_mode()
        return True
    if key == ord(" "):
        self.mashup_running = not self.mashup_running
        self._flash("Playing" if self.mashup_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.mashup_running = False
        self._mashup_step()
        return True
    if key == ord("+") or key == ord("="):
        self.mashup_coupling = min(1.0, self.mashup_coupling + 0.05)
        self._flash(f"Coupling: {self.mashup_coupling:.2f}")
        return True
    if key == ord("-") or key == ord("_"):
        self.mashup_coupling = max(0.0, self.mashup_coupling - 0.05)
        self._flash(f"Coupling: {self.mashup_coupling:.2f}")
        return True
    if key == ord("0"):
        self.mashup_coupling = 0.0
        self._flash("Coupling: OFF (independent)")
        return True
    if key == ord("5"):
        self.mashup_coupling = 0.5
        self._flash("Coupling: 0.50 (default)")
        return True
    if key == ord("r"):
        self._mashup_init(self.mashup_sim_a_id, self.mashup_sim_b_id)
        self._flash("Reset!")
        return True
    if key == ord("R"):
        self.mashup_mode = False
        self.mashup_running = False
        self.mashup_menu = True
        self.mashup_menu_phase = 0
        self.mashup_menu_sel = 0
        return True
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Registration
# ════════════════════════════════════════════════════════════════════

def register(App):
    """Register mashup mode methods on the App class."""
    App._enter_mashup_mode = _enter_mashup_mode
    App._exit_mashup_mode = _exit_mashup_mode
    App._mashup_init = _mashup_init
    App._mashup_step = _mashup_step
    App._handle_mashup_menu_key = _handle_mashup_menu_key
    App._handle_mashup_key = _handle_mashup_key
    App._draw_mashup_menu = _draw_mashup_menu
    App._draw_mashup = _draw_mashup
    App.MASHUP_SIMS = MASHUP_SIMS
    App.MASHUP_PRESETS = MASHUP_PRESETS
