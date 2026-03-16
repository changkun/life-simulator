"""Mode: tmound — Termite Mound Construction & Stigmergy Simulation.

Thousands of simple termite agents build complex mound architecture through
pheromone-guided material placement (stigmergy).  Each termite follows purely
local rules — pick up soil if nearby, deposit where pheromone concentration is
high — yet the colony produces emergent ventilation shafts, brood chambers,
fungus gardens, and royal chambers.

Emergent phenomena:
  - Self-organized construction from local rules only
  - Ventilation shaft networks (chimney effect)
  - Chamber specialization (brood, fungus, royal)
  - Compass-aligned mound walls (magnetic termites)
  - Underground tunnel networks
  - Defensive fortification walls
"""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

TMOUND_PRESETS = [
    ("Cathedral Mound",
     "Towering spire mound with ventilation shafts & internal chambers",
     "cathedral"),
    ("Magnetic Termite Mound",
     "Flat wedge-shaped mound aligned N-S to regulate temperature",
     "magnetic"),
    ("Underground Network",
     "Subsurface tunnel system with foraging galleries & storage chambers",
     "underground"),
    ("Fungus Farming Colony",
     "Specialized chambers for cultivating fungal gardens with humidity control",
     "fungus"),
    ("Defensive Fortress",
     "Thick outer walls, narrow gates & soldier-patrolled perimeter",
     "fortress"),
    ("Mega-Colony",
     "Massive multi-queen colony with interconnected super-mound structures",
     "mega"),
]


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

# Cell material types
MAT_AIR = 0
MAT_SOIL = 1
MAT_WALL = 2       # hardened structural wall
MAT_CHAMBER = 3    # hollowed chamber space
MAT_FUNGUS = 4     # fungus garden substrate
MAT_ROYAL = 5      # royal chamber
MAT_TUNNEL = 6     # underground tunnel
MAT_SURFACE = 7    # ground surface level

# Pheromone types
PH_BUILD = 0       # "build here" pheromone
PH_DIG = 1         # "dig here" pheromone
PH_TRAIL = 2       # general trail pheromone

# Termite roles
ROLE_WORKER = 0
ROLE_BUILDER = 1
ROLE_DIGGER = 2
ROLE_SOLDIER = 3
ROLE_QUEEN = 4
ROLE_FUNGUS = 5    # fungus tender


# ══════════════════════════════════════════════════════════════════════
#  Termite agent class
# ══════════════════════════════════════════════════════════════════════

class _Termite:
    """A single termite agent."""
    __slots__ = ("r", "c", "role", "carrying", "energy", "heading",
                 "task_timer", "home_r", "home_c")

    def __init__(self, r, c, role=ROLE_WORKER):
        self.r = r
        self.c = c
        self.role = role
        self.carrying = False   # carrying soil/material
        self.energy = 1.0
        self.heading = random.random() * 2 * math.pi
        self.task_timer = 0
        self.home_r = r
        self.home_c = c


# ══════════════════════════════════════════════════════════════════════
#  Noise helper (simple value noise for terrain)
# ══════════════════════════════════════════════════════════════════════

def _value_noise_2d(rows, cols, scale=8.0, octaves=3, seed=None):
    """Generate a 2D noise grid in [0,1]."""
    rng = random.Random(seed)
    # Generate random grid at coarse scale
    gs = max(2, int(scale))
    gr = rows // gs + 2
    gc = cols // gs + 2
    grid = [[rng.random() for _ in range(gc)] for _ in range(gr)]
    result = [[0.0] * cols for _ in range(rows)]
    amp = 1.0
    total_amp = 0.0
    for _oct in range(octaves):
        for r in range(rows):
            fr = r / scale
            ir = int(fr)
            dr = fr - ir
            for c in range(cols):
                fc = c / scale
                ic = int(fc)
                dc = fc - ic
                ir0 = ir % gr
                ir1 = (ir + 1) % gr
                ic0 = ic % gc
                ic1 = (ic + 1) % gc
                v00 = grid[ir0][ic0]
                v10 = grid[ir1][ic0]
                v01 = grid[ir0][ic1]
                v11 = grid[ir1][ic1]
                v0 = v00 + (v10 - v00) * dr
                v1 = v01 + (v11 - v01) * dr
                result[r][c] += (v0 + (v1 - v0) * dc) * amp
        total_amp += amp
        amp *= 0.5
        scale *= 0.5
        gs = max(2, int(scale))
        gr = rows // gs + 2
        gc = cols // gs + 2
        grid = [[rng.random() for _ in range(gc)] for _ in range(gr)]
    if total_amp > 0:
        for r in range(rows):
            for c in range(cols):
                result[r][c] /= total_amp
    return result


# ══════════════════════════════════════════════════════════════════════
#  Initialization helpers
# ══════════════════════════════════════════════════════════════════════

def _tmound_make_terrain(self):
    """Generate initial terrain and material grid."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    preset_id = self.tmound_preset_id

    # Height noise for ground surface variation
    noise = _value_noise_2d(rows, cols, scale=max(4, cols // 8), octaves=3,
                            seed=random.randint(0, 99999))

    mat = [[MAT_AIR] * cols for _ in range(rows)]
    surface_row = self.tmound_surface_row

    for r in range(rows):
        for c in range(cols):
            # Surface level varies by noise
            local_surface = surface_row + int((noise[r][c] - 0.5) * 3)
            if r >= local_surface:
                mat[r][c] = MAT_SOIL
            if r == local_surface:
                mat[r][c] = MAT_SURFACE

    # Preset-specific terrain modifications
    if preset_id == "underground":
        # More soil, surface higher up
        for r in range(rows):
            for c in range(cols):
                if r >= surface_row - 2:
                    if mat[r][c] == MAT_AIR:
                        mat[r][c] = MAT_SOIL
    elif preset_id == "fortress":
        # Flat ground, some rocks
        for c in range(cols):
            for r in range(surface_row, rows):
                mat[r][c] = MAT_SOIL
            mat[surface_row][c] = MAT_SURFACE

    self.tmound_material = mat


def _tmound_make_pheromones(self):
    """Initialize pheromone grids."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    self.tmound_ph_build = [[0.0] * cols for _ in range(rows)]
    self.tmound_ph_dig = [[0.0] * cols for _ in range(rows)]
    self.tmound_ph_trail = [[0.0] * cols for _ in range(rows)]


def _tmound_make_termites(self):
    """Create the initial termite population."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    preset_id = self.tmound_preset_id
    surface = self.tmound_surface_row
    n = self.tmound_num_termites

    termites = []
    cx = cols // 2
    cy = surface

    if preset_id == "cathedral":
        # Cluster near center, mostly builders
        for _ in range(n):
            r = cy + random.randint(-3, 5)
            c = cx + random.randint(-cols // 6, cols // 6)
            r = max(1, min(rows - 2, r))
            c = max(1, min(cols - 2, c))
            role = random.choices(
                [ROLE_WORKER, ROLE_BUILDER, ROLE_DIGGER],
                weights=[0.3, 0.5, 0.2])[0]
            t = _Termite(r, c, role)
            t.home_r = cy
            t.home_c = cx
            termites.append(t)
    elif preset_id == "magnetic":
        # Spread across E-W, build north-south aligned
        for _ in range(n):
            r = cy + random.randint(-2, 4)
            c = cx + random.randint(-cols // 4, cols // 4)
            r = max(1, min(rows - 2, r))
            c = max(1, min(cols - 2, c))
            role = random.choices(
                [ROLE_WORKER, ROLE_BUILDER, ROLE_DIGGER],
                weights=[0.3, 0.5, 0.2])[0]
            t = _Termite(r, c, role)
            t.home_r = cy
            t.home_c = cx
            termites.append(t)
    elif preset_id == "underground":
        # Start below surface, mostly diggers
        for _ in range(n):
            r = surface + random.randint(2, min(8, rows - surface - 2))
            c = cx + random.randint(-cols // 5, cols // 5)
            r = max(1, min(rows - 2, r))
            c = max(1, min(cols - 2, c))
            role = random.choices(
                [ROLE_WORKER, ROLE_DIGGER, ROLE_BUILDER],
                weights=[0.2, 0.6, 0.2])[0]
            t = _Termite(r, c, role)
            t.home_r = surface + 4
            t.home_c = cx
            termites.append(t)
    elif preset_id == "fungus":
        # Mixed roles with dedicated fungus tenders
        for _ in range(n):
            r = cy + random.randint(-2, 5)
            c = cx + random.randint(-cols // 5, cols // 5)
            r = max(1, min(rows - 2, r))
            c = max(1, min(cols - 2, c))
            role = random.choices(
                [ROLE_WORKER, ROLE_BUILDER, ROLE_DIGGER, ROLE_FUNGUS],
                weights=[0.2, 0.3, 0.2, 0.3])[0]
            t = _Termite(r, c, role)
            t.home_r = cy
            t.home_c = cx
            termites.append(t)
    elif preset_id == "fortress":
        # Soldiers on perimeter, builders inside
        for i in range(n):
            r = cy + random.randint(-2, 5)
            c = cx + random.randint(-cols // 4, cols // 4)
            r = max(1, min(rows - 2, r))
            c = max(1, min(cols - 2, c))
            if i < n // 5:
                role = ROLE_SOLDIER
            else:
                role = random.choices(
                    [ROLE_WORKER, ROLE_BUILDER, ROLE_DIGGER],
                    weights=[0.3, 0.4, 0.3])[0]
            t = _Termite(r, c, role)
            t.home_r = cy
            t.home_c = cx
            termites.append(t)
    else:  # mega
        # Multiple colony centers
        centers = []
        num_centers = random.randint(3, 5)
        spacing = cols // (num_centers + 1)
        for i in range(num_centers):
            cc = spacing * (i + 1)
            centers.append((cy, cc))
        per_center = n // num_centers
        for ci, (cr, cc) in enumerate(centers):
            for _ in range(per_center):
                r = cr + random.randint(-3, 5)
                c = cc + random.randint(-spacing // 3, spacing // 3)
                r = max(1, min(rows - 2, r))
                c = max(1, min(cols - 2, c))
                role = random.choices(
                    [ROLE_WORKER, ROLE_BUILDER, ROLE_DIGGER],
                    weights=[0.3, 0.4, 0.3])[0]
                t = _Termite(r, c, role)
                t.home_r = cr
                t.home_c = cc
                termites.append(t)
        self.tmound_centers = centers

    # Add queen(s)
    if preset_id == "mega":
        for cr, cc in self.tmound_centers:
            q = _Termite(cr + 2, cc, ROLE_QUEEN)
            q.home_r = cr + 2
            q.home_c = cc
            termites.append(q)
    else:
        q = _Termite(cy + 2, cx, ROLE_QUEEN)
        q.home_r = cy + 2
        q.home_c = cx
        termites.append(q)

    self.tmound_termites = termites


def _tmound_seed_pheromones(self):
    """Place initial build/dig pheromone seeds to bootstrap construction."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    preset_id = self.tmound_preset_id
    surface = self.tmound_surface_row
    cx = cols // 2
    ph_build = self.tmound_ph_build
    ph_dig = self.tmound_ph_dig

    if preset_id == "cathedral":
        # Build pheromone in a vertical column above surface, dig below
        for r in range(max(0, surface - 8), surface):
            for c in range(max(0, cx - 3), min(cols, cx + 4)):
                dist = abs(c - cx)
                ph_build[r][c] = max(0, 0.8 - dist * 0.15)
        for r in range(surface + 1, min(rows, surface + 6)):
            for c in range(max(0, cx - 5), min(cols, cx + 6)):
                ph_dig[r][c] = 0.5

    elif preset_id == "magnetic":
        # Build pheromone in a flat N-S band (left-right in terminal)
        for r in range(max(0, surface - 4), surface):
            for c in range(max(0, cx - 1), min(cols, cx + 2)):
                ph_build[r][c] = 0.7
        # Wider E-W (top-bottom) dig
        for r in range(surface + 1, min(rows, surface + 5)):
            for c in range(max(0, cx - 8), min(cols, cx + 9)):
                ph_dig[r][c] = 0.4

    elif preset_id == "underground":
        # Dig pheromone radiating from center below surface
        for r in range(surface + 1, min(rows, surface + 10)):
            for c in range(max(0, cx - 10), min(cols, cx + 11)):
                dist = math.sqrt((r - surface - 5) ** 2 + (c - cx) ** 2)
                ph_dig[r][c] = max(0, 0.7 - dist * 0.05)

    elif preset_id == "fungus":
        # Dig chambers, build walls around them
        for r in range(surface + 2, min(rows, surface + 7)):
            for c in range(max(0, cx - 6), min(cols, cx + 7)):
                ph_dig[r][c] = 0.5
        for r in range(max(0, surface - 3), surface):
            for c in range(max(0, cx - 4), min(cols, cx + 5)):
                ph_build[r][c] = 0.6

    elif preset_id == "fortress":
        # Ring of build pheromone for walls, dig in center
        for r in range(max(0, surface - 5), surface + 3):
            for c in range(max(0, cx - 12), min(cols, cx + 13)):
                dist = math.sqrt((r - surface) ** 2 + (c - cx) ** 2)
                if 8 < dist < 12:
                    ph_build[r][c] = 0.8
                elif dist < 6:
                    ph_dig[r][c] = 0.5

    elif preset_id == "mega":
        # Seeds at each colony center
        for cr, cc in self.tmound_centers:
            for r in range(max(0, cr - 5), min(rows, cr + 3)):
                for c in range(max(0, cc - 4), min(cols, cc + 5)):
                    dist = abs(c - cc) + abs(r - cr)
                    if r < cr:
                        ph_build[r][c] = max(0, 0.6 - dist * 0.08)
                    else:
                        ph_dig[r][c] = max(0, 0.5 - dist * 0.06)


# ══════════════════════════════════════════════════════════════════════
#  Simulation step
# ══════════════════════════════════════════════════════════════════════

_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)]

_NEIGHBORS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _tmound_step(self):
    """Advance termite mound simulation by one tick."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    mat = self.tmound_material
    ph_build = self.tmound_ph_build
    ph_dig = self.tmound_ph_dig
    ph_trail = self.tmound_ph_trail
    termites = self.tmound_termites
    preset_id = self.tmound_preset_id
    rng = random.random
    surface = self.tmound_surface_row

    evap_rate = self.tmound_evap_rate
    diffuse_rate = self.tmound_diffuse_rate
    build_threshold = self.tmound_build_threshold
    dig_threshold = self.tmound_dig_threshold

    # ── 1. Pheromone diffusion & evaporation ──
    new_build = [[0.0] * cols for _ in range(rows)]
    new_dig = [[0.0] * cols for _ in range(rows)]
    new_trail = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            # Evaporate
            b = ph_build[r][c] * (1.0 - evap_rate)
            d = ph_dig[r][c] * (1.0 - evap_rate)
            t = ph_trail[r][c] * (1.0 - evap_rate * 1.5)

            # Diffuse from neighbors
            nb = 0.0
            nd = 0.0
            nt = 0.0
            nn = 0
            for dr, dc in _NEIGHBORS_4:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    nb += ph_build[nr][nc]
                    nd += ph_dig[nr][nc]
                    nt += ph_trail[nr][nc]
                    nn += 1
            if nn > 0:
                avg_b = nb / nn
                avg_d = nd / nn
                avg_t = nt / nn
                b += (avg_b - ph_build[r][c]) * diffuse_rate
                d += (avg_d - ph_dig[r][c]) * diffuse_rate
                t += (avg_t - ph_trail[r][c]) * diffuse_rate

            new_build[r][c] = max(0.0, min(1.0, b))
            new_dig[r][c] = max(0.0, min(1.0, d))
            new_trail[r][c] = max(0.0, min(1.0, t))

    self.tmound_ph_build = new_build
    self.tmound_ph_dig = new_dig
    self.tmound_ph_trail = new_trail
    ph_build = new_build
    ph_dig = new_dig
    ph_trail = new_trail

    # ── 2. Move & act each termite ──
    built_cells = 0
    dug_cells = 0

    for tm in termites:
        if tm.role == ROLE_QUEEN:
            # Queen stays put, emits build/dig pheromone
            if 0 <= tm.r < rows and 0 <= tm.c < cols:
                ph_build[tm.r][tm.c] = min(1.0, ph_build[tm.r][tm.c] + 0.05)
                if tm.r + 1 < rows:
                    ph_dig[tm.r + 1][tm.c] = min(1.0, ph_dig[tm.r + 1][tm.c] + 0.03)
                # Mark royal chamber
                mat[tm.r][tm.c] = MAT_ROYAL
            continue

        # ── Movement ──
        # Bias toward pheromone gradients
        best_r, best_c = tm.r, tm.c
        best_score = -999.0

        # Shuffle neighbor order to break ties randomly
        neighbors = list(_NEIGHBORS_8)
        random.shuffle(neighbors)

        for dr, dc in neighbors:
            nr, nc = tm.r + dr, tm.c + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            cell = mat[nr][nc]
            # Can't walk into solid wall
            if cell == MAT_WALL and not tm.carrying and tm.role != ROLE_DIGGER:
                continue

            score = 0.0

            if tm.role == ROLE_BUILDER or (tm.role == ROLE_WORKER and tm.carrying):
                # Builders follow build pheromone to deposit
                if tm.carrying:
                    score = ph_build[nr][nc] * 3.0
                    # Prefer depositing next to existing structure
                    adj_soil = 0
                    for dr2, dc2 in _NEIGHBORS_4:
                        ar, ac = nr + dr2, nc + dc2
                        if 0 <= ar < rows and 0 <= ac < cols:
                            if mat[ar][ac] in (MAT_SOIL, MAT_WALL):
                                adj_soil += 1
                    score += adj_soil * 0.3
                else:
                    # Look for material to pick up
                    if cell == MAT_SOIL:
                        score = 2.0
                    score += ph_trail[nr][nc] * 0.5

            elif tm.role == ROLE_DIGGER:
                # Diggers follow dig pheromone
                if not tm.carrying:
                    score = ph_dig[nr][nc] * 3.0
                    if cell == MAT_SOIL:
                        score += 1.5
                else:
                    # Carry material away from dig zone, toward build zone
                    score = ph_build[nr][nc] * 2.0 - ph_dig[nr][nc] * 1.0

            elif tm.role == ROLE_WORKER:
                # General trail following with random walk
                score = ph_trail[nr][nc] * 1.5

            elif tm.role == ROLE_SOLDIER:
                # Patrol perimeter — follow trail, prefer edges of structure
                score = ph_trail[nr][nc] * 1.0
                if cell == MAT_AIR:
                    adj_struct = 0
                    for dr2, dc2 in _NEIGHBORS_4:
                        ar, ac = nr + dr2, nc + dc2
                        if 0 <= ar < rows and 0 <= ac < cols:
                            if mat[ar][ac] in (MAT_WALL, MAT_SOIL):
                                adj_struct += 1
                    if adj_struct > 0:
                        score += 1.0

            elif tm.role == ROLE_FUNGUS:
                # Tend fungus gardens — go to chambers
                if cell == MAT_FUNGUS:
                    score = 3.0
                elif cell == MAT_CHAMBER:
                    score = 2.0
                score += ph_dig[nr][nc] * 0.5

            # Random noise for exploration
            score += rng() * 0.8

            # Slight homeward bias
            home_dist_now = abs(tm.r - tm.home_r) + abs(tm.c - tm.home_c)
            home_dist_new = abs(nr - tm.home_r) + abs(nc - tm.home_c)
            if home_dist_new < home_dist_now:
                score += 0.2

            if score > best_score:
                best_score = score
                best_r, best_c = nr, nc

        # Move
        old_r, old_c = tm.r, tm.c
        tm.r, tm.c = best_r, best_c

        # Leave trail pheromone
        if 0 <= old_r < rows and 0 <= old_c < cols:
            ph_trail[old_r][old_c] = min(1.0, ph_trail[old_r][old_c] + 0.1)

        # ── Actions at new position ──
        r, c = tm.r, tm.c
        if not (0 <= r < rows and 0 <= c < cols):
            continue

        cell = mat[r][c]

        # Builder/Worker: pick up or deposit
        if tm.role in (ROLE_BUILDER, ROLE_WORKER):
            if tm.carrying:
                # Deposit if build pheromone is high enough and cell is air
                if cell == MAT_AIR and ph_build[r][c] > build_threshold:
                    # Check structural support — need adjacent solid
                    support = 0
                    for dr, dc in _NEIGHBORS_4:
                        ar, ac = r + dr, c + dc
                        if 0 <= ar < rows and 0 <= ac < cols:
                            if mat[ar][ac] in (MAT_SOIL, MAT_WALL, MAT_SURFACE):
                                support += 1
                    if support > 0 or r >= surface:
                        mat[r][c] = MAT_WALL
                        tm.carrying = False
                        # Reinforce build pheromone (stigmergy!)
                        ph_build[r][c] = min(1.0, ph_build[r][c] + 0.3)
                        built_cells += 1
            else:
                # Pick up loose soil
                if cell == MAT_SOIL and r < surface + 3:
                    # Only pick up surface/near-surface soil
                    mat[r][c] = MAT_AIR
                    tm.carrying = True

        # Digger: dig tunnels/chambers
        elif tm.role == ROLE_DIGGER:
            if not tm.carrying:
                if cell == MAT_SOIL and ph_dig[r][c] > dig_threshold:
                    mat[r][c] = MAT_CHAMBER
                    tm.carrying = True
                    ph_dig[r][c] = min(1.0, ph_dig[r][c] + 0.2)
                    dug_cells += 1
            else:
                # Deposit material at build site or surface
                if cell == MAT_AIR and (ph_build[r][c] > build_threshold * 0.5
                                        or r <= surface - 2):
                    support = 0
                    for dr, dc in _NEIGHBORS_4:
                        ar, ac = r + dr, c + dc
                        if 0 <= ar < rows and 0 <= ac < cols:
                            if mat[ar][ac] in (MAT_SOIL, MAT_WALL, MAT_SURFACE):
                                support += 1
                    if support > 0:
                        mat[r][c] = MAT_WALL
                        tm.carrying = False
                        ph_build[r][c] = min(1.0, ph_build[r][c] + 0.2)
                        built_cells += 1

        # Fungus tender: convert chambers to fungus gardens
        elif tm.role == ROLE_FUNGUS:
            if cell == MAT_CHAMBER:
                # Check humidity (proximity to soil)
                soil_near = 0
                for dr, dc in _NEIGHBORS_8:
                    ar, ac = r + dr, c + dc
                    if 0 <= ar < rows and 0 <= ac < cols:
                        if mat[ar][ac] in (MAT_SOIL, MAT_WALL):
                            soil_near += 1
                if soil_near >= 3 and rng() < 0.15:
                    mat[r][c] = MAT_FUNGUS

        # Soldier: reinforce walls
        elif tm.role == ROLE_SOLDIER:
            if cell == MAT_SOIL:
                # Check if near the edge of structure (adjacent to air)
                near_air = False
                for dr, dc in _NEIGHBORS_4:
                    ar, ac = r + dr, c + dc
                    if 0 <= ar < rows and 0 <= ac < cols:
                        if mat[ar][ac] in (MAT_AIR, MAT_CHAMBER):
                            near_air = True
                            break
                if near_air and rng() < 0.1:
                    mat[r][c] = MAT_WALL

    # ── 3. Ventilation shaft formation (cathedral preset) ──
    if preset_id == "cathedral" and self.tmound_generation % 20 == 0:
        # Warm air rises — occasionally open vertical channels
        cx = cols // 2
        for c in range(max(0, cx - 2), min(cols, cx + 3)):
            for r in range(max(0, surface - 12), surface):
                if mat[r][c] == MAT_WALL and rng() < 0.03:
                    # Check if there's a chamber below
                    below_chamber = False
                    for br in range(r + 1, min(rows, r + 4)):
                        if mat[br][c] in (MAT_CHAMBER, MAT_AIR):
                            below_chamber = True
                            break
                    if below_chamber:
                        mat[r][c] = MAT_TUNNEL

    # ── 4. Magnetic alignment (magnetic preset) ──
    if preset_id == "magnetic":
        # Bias build pheromone toward north-south (vertical in terminal)
        # and suppress east-west building
        for r in range(rows):
            for c in range(cols):
                dist_from_center = abs(c - cols // 2)
                if dist_from_center > 2:
                    ph_build[r][c] *= 0.95  # suppress wide builds

    # ── 5. Update statistics ──
    self.tmound_generation += 1
    self.tmound_built_total += built_cells
    self.tmound_dug_total += dug_cells

    # Count cell types
    wall_count = 0
    chamber_count = 0
    fungus_count = 0
    tunnel_count = 0
    for r in range(rows):
        for c in range(cols):
            m = mat[r][c]
            if m == MAT_WALL:
                wall_count += 1
            elif m == MAT_CHAMBER:
                chamber_count += 1
            elif m == MAT_FUNGUS:
                fungus_count += 1
            elif m == MAT_TUNNEL:
                tunnel_count += 1

    self.tmound_wall_cells = wall_count
    self.tmound_chamber_cells = chamber_count
    self.tmound_fungus_cells = fungus_count
    self.tmound_tunnel_cells = tunnel_count


# ══════════════════════════════════════════════════════════════════════
#  Enter / exit
# ══════════════════════════════════════════════════════════════════════

def _enter_tmound_mode(self):
    """Enter Termite Mound mode — show preset menu."""
    self.tmound_menu = True
    self.tmound_menu_sel = 0
    self._flash("Termite Mound Construction & Stigmergy — select a scenario")


def _exit_tmound_mode(self):
    """Exit Termite Mound mode."""
    self.tmound_mode = False
    self.tmound_menu = False
    self.tmound_running = False
    self._flash("Termite Mound mode OFF")


# ══════════════════════════════════════════════════════════════════════
#  Preset init
# ══════════════════════════════════════════════════════════════════════

def _tmound_init(self, preset_idx: int):
    """Initialize termite mound simulation with the given preset."""
    name, _desc, preset_id = TMOUND_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()

    cols = max(20, max_x - 2)
    rows = max(12, max_y - 4)

    self.tmound_rows = rows
    self.tmound_cols = cols
    self.tmound_preset_name = name
    self.tmound_preset_id = preset_id
    self.tmound_generation = 0
    self.tmound_running = False
    self.tmound_steps_per_frame = 1
    self.tmound_view = "mound"  # mound, pheromone, structure

    # Surface row — where ground level is
    if preset_id == "cathedral":
        self.tmound_surface_row = rows * 2 // 3
    elif preset_id == "underground":
        self.tmound_surface_row = rows // 3
    elif preset_id == "magnetic":
        self.tmound_surface_row = rows * 2 // 3
    elif preset_id == "mega":
        self.tmound_surface_row = rows * 3 // 5
    else:
        self.tmound_surface_row = rows // 2

    # Termite count
    if preset_id == "mega":
        self.tmound_num_termites = min(3000, rows * cols // 4)
    elif preset_id == "fortress":
        self.tmound_num_termites = min(1500, rows * cols // 6)
    else:
        self.tmound_num_termites = min(1200, rows * cols // 5)

    # Pheromone parameters
    self.tmound_evap_rate = 0.02
    self.tmound_diffuse_rate = 0.15
    self.tmound_build_threshold = 0.15
    self.tmound_dig_threshold = 0.12

    # Preset-specific tuning
    if preset_id == "cathedral":
        self.tmound_build_threshold = 0.12
        self.tmound_diffuse_rate = 0.18
    elif preset_id == "underground":
        self.tmound_dig_threshold = 0.08
        self.tmound_evap_rate = 0.015
    elif preset_id == "fungus":
        self.tmound_evap_rate = 0.018
        self.tmound_dig_threshold = 0.10
    elif preset_id == "fortress":
        self.tmound_build_threshold = 0.10
        self.tmound_diffuse_rate = 0.20
    elif preset_id == "mega":
        self.tmound_evap_rate = 0.025
        self.tmound_diffuse_rate = 0.12

    # Statistics
    self.tmound_built_total = 0
    self.tmound_dug_total = 0
    self.tmound_wall_cells = 0
    self.tmound_chamber_cells = 0
    self.tmound_fungus_cells = 0
    self.tmound_tunnel_cells = 0
    self.tmound_centers = []

    # Build world
    self._tmound_make_terrain()
    self._tmound_make_pheromones()
    self._tmound_make_termites()
    self._tmound_seed_pheromones()

    # Finalize
    self.tmound_mode = True
    self.tmound_menu = False
    self._flash(f"Termite Mound: {name} — Space to start")


# ══════════════════════════════════════════════════════════════════════
#  Key handlers
# ══════════════════════════════════════════════════════════════════════

def _handle_tmound_menu_key(self, key: int) -> bool:
    """Handle key input in preset menu."""
    n = len(TMOUND_PRESETS)

    if key == ord("q") or key == 27:
        self.tmound_mode = False
        self.tmound_menu = False
        return True

    if key == curses.KEY_UP or key == ord("k"):
        self.tmound_menu_sel = (self.tmound_menu_sel - 1) % n
        return True

    if key == curses.KEY_DOWN or key == ord("j"):
        self.tmound_menu_sel = (self.tmound_menu_sel + 1) % n
        return True

    if key in (10, 13, curses.KEY_ENTER):
        self._tmound_init(self.tmound_menu_sel)
        return True

    return True


def _handle_tmound_key(self, key: int) -> bool:
    """Handle key input during simulation."""
    if key == ord(" "):
        self.tmound_running = not self.tmound_running
        self._flash("Running" if self.tmound_running else "Paused")
        return True

    if key == ord("n") or key == ord("."):
        self._tmound_step()
        return True

    if key == ord("r"):
        idx = next((i for i, p in enumerate(TMOUND_PRESETS)
                     if p[0] == self.tmound_preset_name), 0)
        self._tmound_init(idx)
        return True

    if key == ord("R") or key == ord("m"):
        self.tmound_mode = False
        self.tmound_running = False
        self.tmound_menu = True
        self.tmound_menu_sel = 0
        return True

    if key == ord("v"):
        views = ["mound", "pheromone", "structure"]
        cur = views.index(self.tmound_view) if self.tmound_view in views else 0
        self.tmound_view = views[(cur + 1) % len(views)]
        self._flash(f"View: {self.tmound_view}")
        return True

    if key == ord("+") or key == ord("="):
        self.tmound_steps_per_frame = min(20, self.tmound_steps_per_frame + 1)
        self._flash(f"Speed: {self.tmound_steps_per_frame}x")
        return True

    if key == ord("-") or key == ord("_"):
        self.tmound_steps_per_frame = max(1, self.tmound_steps_per_frame - 1)
        self._flash(f"Speed: {self.tmound_steps_per_frame}x")
        return True

    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing — menu
# ══════════════════════════════════════════════════════════════════════

def _draw_tmound_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    self.stdscr.erase()

    title = "── Termite Mound Construction & Stigmergy ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(TMOUND_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 6:
            break

        marker = "▸ " if i == self.tmound_menu_sel else "  "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.tmound_menu_sel
                else curses.color_pair(7))

        try:
            self.stdscr.addstr(y, 3, f"{marker}{name}"[:max_x - 4], attr)
        except curses.error:
            pass

        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hint_y = max_y - 3
    hints = [
        " [↑/↓] Navigate   [Enter] Select   [q/Esc] Back",
        " Emergent mound architecture from stigmergic construction",
    ]
    for i, h in enumerate(hints):
        hy = hint_y + i
        if 0 < hy < max_y:
            try:
                self.stdscr.addstr(hy, 2, h[:max_x - 4],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — simulation views
# ══════════════════════════════════════════════════════════════════════

def _draw_tmound(self, max_y: int, max_x: int):
    """Draw the active termite mound simulation."""
    self.stdscr.erase()
    state = "▶ RUNNING" if self.tmound_running else "⏸ PAUSED"

    title = (f" Termite Mound: {self.tmound_preset_name}  |  "
             f"t={self.tmound_generation}  "
             f"termites={len(self.tmound_termites)}  "
             f"|  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view = self.tmound_view
    if view == "mound":
        _draw_tmound_mound(self, max_y, max_x)
    elif view == "pheromone":
        _draw_tmound_pheromone(self, max_y, max_x)
    elif view == "structure":
        _draw_tmound_structure(self, max_y, max_x)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" walls={self.tmound_wall_cells}"
                f"  chambers={self.tmound_chamber_cells}"
                f"  fungus={self.tmound_fungus_cells}"
                f"  tunnels={self.tmound_tunnel_cells}"
                f"  built={self.tmound_built_total}"
                f"  dug={self.tmound_dug_total}")
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if hasattr(self, 'message') and self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_tmound_mound(self, max_y: int, max_x: int):
    """Draw the main mound view with termites."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    mat = self.tmound_material

    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break

        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols or sx >= max_x - 1:
                break

            m = mat[r][c]

            if m == MAT_WALL:
                ch = "█"
                attr = curses.color_pair(3) | curses.A_BOLD  # yellow - built walls
            elif m == MAT_SOIL:
                ch = "▓"
                attr = curses.color_pair(1)  # red-brown soil
            elif m == MAT_SURFACE:
                ch = "▔"
                attr = curses.color_pair(2)  # green surface
            elif m == MAT_CHAMBER:
                ch = "○"
                attr = curses.color_pair(6)  # cyan chamber
            elif m == MAT_FUNGUS:
                ch = "♣"
                attr = curses.color_pair(2) | curses.A_BOLD  # green fungus
            elif m == MAT_ROYAL:
                ch = "♛"
                attr = curses.color_pair(5) | curses.A_BOLD  # magenta royal
            elif m == MAT_TUNNEL:
                ch = "·"
                attr = curses.color_pair(6) | curses.A_DIM  # dim tunnel
            else:  # AIR
                ch = " "
                attr = 0

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass

    # Draw termites on top
    termites = self.tmound_termites
    for tm in termites:
        ty = 1 + tm.r // max(1, row_scale)
        tx = tm.c // max(1, col_scale)
        if 1 <= ty < max_y - 2 and 0 <= tx < max_x - 1:
            if tm.role == ROLE_QUEEN:
                ch = "♛"
                attr = curses.color_pair(5) | curses.A_BOLD
            elif tm.role == ROLE_SOLDIER:
                ch = "●"
                attr = curses.color_pair(1) | curses.A_BOLD
            elif tm.role == ROLE_FUNGUS:
                ch = "◆"
                attr = curses.color_pair(2)
            elif tm.carrying:
                ch = "◇"
                attr = curses.color_pair(3)
            else:
                ch = "·"
                attr = curses.color_pair(7) | curses.A_DIM

            try:
                self.stdscr.addstr(ty, tx, ch, attr)
            except curses.error:
                pass


def _draw_tmound_pheromone(self, max_y: int, max_x: int):
    """Draw pheromone concentration overlay."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    ph_build = self.tmound_ph_build
    ph_dig = self.tmound_ph_dig

    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    chars = " .·:;+=#%@"

    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break

        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols or sx >= max_x - 1:
                break

            b = ph_build[r][c]
            d = ph_dig[r][c]

            if b > d:
                idx = min(9, int(b * 10))
                ch = chars[idx]
                attr = curses.color_pair(3)  # yellow = build
                if b > 0.5:
                    attr |= curses.A_BOLD
            elif d > 0.01:
                idx = min(9, int(d * 10))
                ch = chars[idx]
                attr = curses.color_pair(4)  # blue = dig
                if d > 0.5:
                    attr |= curses.A_BOLD
            else:
                ch = " "
                attr = 0

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass


def _draw_tmound_structure(self, max_y: int, max_x: int):
    """Draw structural analysis view — walls, chambers, tunnels only."""
    rows = self.tmound_rows
    cols = self.tmound_cols
    mat = self.tmound_material

    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break

        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols or sx >= max_x - 1:
                break

            m = mat[r][c]

            if m == MAT_WALL:
                # Color by adjacency for structural view
                adj_air = 0
                for dr, dc in _NEIGHBORS_4:
                    ar, ac = r + dr, c + dc
                    if 0 <= ar < rows and 0 <= ac < cols:
                        if mat[ar][ac] in (MAT_AIR, MAT_CHAMBER, MAT_TUNNEL):
                            adj_air += 1
                if adj_air >= 2:
                    ch = "█"
                    attr = curses.color_pair(3) | curses.A_BOLD  # exterior wall
                else:
                    ch = "▓"
                    attr = curses.color_pair(3)  # interior wall
            elif m == MAT_CHAMBER:
                ch = "░"
                attr = curses.color_pair(6)
            elif m == MAT_FUNGUS:
                ch = "░"
                attr = curses.color_pair(2) | curses.A_BOLD
            elif m == MAT_ROYAL:
                ch = "♛"
                attr = curses.color_pair(5) | curses.A_BOLD
            elif m == MAT_TUNNEL:
                ch = "·"
                attr = curses.color_pair(7)
            elif m == MAT_SURFACE:
                ch = "─"
                attr = curses.color_pair(2) | curses.A_DIM
            else:
                ch = " "
                attr = 0

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register termite mound mode methods on the App class."""
    App.TMOUND_PRESETS = TMOUND_PRESETS
    App._enter_tmound_mode = _enter_tmound_mode
    App._exit_tmound_mode = _exit_tmound_mode
    App._tmound_init = _tmound_init
    App._tmound_make_terrain = _tmound_make_terrain
    App._tmound_make_pheromones = _tmound_make_pheromones
    App._tmound_make_termites = _tmound_make_termites
    App._tmound_seed_pheromones = _tmound_seed_pheromones
    App._tmound_step = _tmound_step
    App._handle_tmound_menu_key = _handle_tmound_menu_key
    App._handle_tmound_key = _handle_tmound_key
    App._draw_tmound_menu = _draw_tmound_menu
    App._draw_tmound = _draw_tmound
    App._draw_tmound_mound = _draw_tmound_mound
    App._draw_tmound_pheromone = _draw_tmound_pheromone
    App._draw_tmound_structure = _draw_tmound_structure
