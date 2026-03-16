"""Mode: tpool — Tide Pool & Intertidal Ecosystem.

Sinusoidal tidal cycles drive a vertical rocky-shore ecosystem where species
are stratified by exposure tolerance.  Barnacles cement high, sea stars hunt
mid-zone, anemones anchor in pools, urchins graze algae, kelp holds the low
zone, and hermit crabs roam for empty shells.

Emergent phenomena:
  - Tidal rise/fall with splash-zone spray and wave surge
  - Vertical zonation bands (spray → high → mid → low → subtidal)
  - Desiccation & heat stress at low tide, predation at high tide
  - Mussel bed competition for rock space
  - Sea star "wave of death" predation fronts
  - Algae bloom / grazing cycles
  - Hermit crab vacancy-chain shell swaps
"""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

TPOOL_PRESETS = [
    ("Pacific Rocky Shore",
     "Classic temperate intertidal with full zonation, ochre sea stars & mussels",
     "pacific"),
    ("Tropical Coral Flat",
     "Warm shallow reef flat exposed at spring tides — corals, urchins & parrotfish",
     "tropical"),
    ("Mussel Bed Dominance",
     "Dense mussel beds competing for rock space — watch dominance hierarchy emerge",
     "mussel_bed"),
    ("Sea Star Wasting Event",
     "Ochre stars hit by wasting disease — cascading trophic effects on mussel beds",
     "wasting"),
    ("Extreme Tidal Range",
     "Bay of Fundy–scale tides exposing huge vertical range twice daily",
     "extreme_tide"),
    ("Hermit Crab Shell Economy",
     "Dense hermit crab population — vacancy chains form when large shells appear",
     "hermit_economy"),
]


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

# Tile / substrate types
TILE_WATER = 0
TILE_ROCK = 1
TILE_SAND = 2
TILE_POOL = 3          # permanent tide pool depression
TILE_ALGAE_ROCK = 4    # rock covered in algae

# Zone bands (row ranges computed dynamically)
ZONE_SUBTIDAL = 0
ZONE_LOW = 1
ZONE_MID = 2
ZONE_HIGH = 3
ZONE_SPRAY = 4

# Species
SP_BARNACLE = 0
SP_MUSSEL = 1
SP_ANEMONE = 2
SP_SEA_STAR = 3
SP_URCHIN = 4
SP_KELP = 5
SP_HERMIT_CRAB = 6
SP_LIMPET = 7

_SP_NAMES = ["Barnacle", "Mussel", "Anemone", "Sea Star",
             "Urchin", "Kelp", "Hermit Crab", "Limpet"]

_NEIGHBORS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]


# ══════════════════════════════════════════════════════════════════════
#  Agent classes
# ══════════════════════════════════════════════════════════════════════

class _Sessile:
    """Barnacle, mussel, anemone, kelp — attached to rock."""
    __slots__ = ('r', 'c', 'kind', 'energy', 'age', 'stress', 'size')

    def __init__(self, r, c, kind, energy=1.0):
        self.r = r
        self.c = c
        self.kind = kind
        self.energy = energy
        self.age = 0
        self.stress = 0.0
        self.size = 0.3 + random.random() * 0.4


class _Mobile:
    """Sea star, urchin, hermit crab, limpet — moves on substrate."""
    __slots__ = ('r', 'c', 'kind', 'energy', 'age', 'stress',
                 'shell_size', 'heading')

    def __init__(self, r, c, kind, energy=1.0):
        self.r = r
        self.c = c
        self.kind = kind
        self.energy = energy
        self.age = 0
        self.stress = 0.0
        self.shell_size = 0.5 + random.random() * 0.5  # hermit crab shell
        self.heading = random.random() * 2 * math.pi


# ══════════════════════════════════════════════════════════════════════
#  Enter / Exit
# ══════════════════════════════════════════════════════════════════════

def _enter_tpool_mode(self):
    """Enter tide pool mode — show preset menu."""
    self.tpool_mode = True
    self.tpool_menu = True
    self.tpool_menu_sel = 0


def _exit_tpool_mode(self):
    """Exit tide pool mode."""
    self.tpool_mode = False
    self.tpool_menu = False
    self.tpool_running = False
    for attr in list(vars(self)):
        if attr.startswith('tpool_') and attr not in ('tpool_mode',):
            try:
                delattr(self, attr)
            except AttributeError:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _tpool_init(self, preset_idx: int):
    """Initialize tide pool simulation for the chosen preset."""
    name, _desc, pid = TPOOL_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(20, max_x - 2)

    self.tpool_menu = False
    self.tpool_running = False
    self.tpool_preset_name = name
    self.tpool_preset_id = pid
    self.tpool_rows = rows
    self.tpool_cols = cols
    self.tpool_generation = 0
    self.tpool_speed = 1
    self.tpool_view = "shore"     # shore | cross_section | graphs

    # Tidal state
    self.tpool_tide_period = 240   # ticks per full tide cycle
    self.tpool_tide_phase = 0.0
    self.tpool_tide_amplitude = 0.35  # fraction of rows
    self.tpool_tide_level = 0.5       # 0 = lowest, 1 = highest
    self.tpool_wave_offset = 0.0

    # Zone boundaries (row indices — higher row = lower elevation)
    # spray zone at top, subtidal at bottom
    spray_end = int(rows * 0.10)
    high_end = int(rows * 0.30)
    mid_end = int(rows * 0.55)
    low_end = int(rows * 0.80)
    self.tpool_zones = [
        (0, spray_end),          # SPRAY
        (spray_end, high_end),   # HIGH
        (high_end, mid_end),     # MID
        (mid_end, low_end),      # LOW
        (low_end, rows),         # SUBTIDAL
    ]

    # Terrain
    self.tpool_grid = [[TILE_ROCK] * cols for _ in range(rows)]
    _tpool_make_terrain(self, pid)

    # Temperature / desiccation fields
    self.tpool_temp = [[0.0] * cols for _ in range(rows)]
    self.tpool_moisture = [[1.0] * cols for _ in range(rows)]

    # Algae density (0-1 per cell)
    self.tpool_algae = [[0.0] * cols for _ in range(rows)]

    # Organisms
    self.tpool_sessile = []    # list of _Sessile
    self.tpool_mobile = []     # list of _Mobile
    self.tpool_empty_shells = []  # (r, c, size) for hermit crab economy

    # Population history for graphs
    self.tpool_pop_history = {sp: [] for sp in range(8)}
    self.tpool_tide_history = []
    self.tpool_stress_history = []

    # Preset-specific tuning
    if pid == "extreme_tide":
        self.tpool_tide_amplitude = 0.45
        self.tpool_tide_period = 180
    elif pid == "tropical":
        self.tpool_tide_amplitude = 0.20
        self.tpool_tide_period = 300

    _tpool_populate(self, pid)
    self._flash(f"Tide Pool: {name}")


def _tpool_make_terrain(self, pid):
    """Generate rocky shore terrain with pools and sand patches."""
    rows = self.tpool_rows
    cols = self.tpool_cols

    for r in range(rows):
        for c in range(cols):
            # Base is rock
            self.tpool_grid[r][c] = TILE_ROCK

    # Create tide pools (depressions that retain water)
    n_pools = random.randint(4, 8) if pid != "tropical" else random.randint(6, 12)
    zones = self.tpool_zones
    for _ in range(n_pools):
        # Pools mostly in mid and low zones
        zone_start = zones[2][0]  # MID start
        zone_end = zones[3][1]    # LOW end
        pr = random.randint(zone_start, zone_end - 1)
        pc = random.randint(2, cols - 3)
        pool_w = random.randint(3, 7)
        pool_h = random.randint(2, 4)
        for dr in range(-pool_h // 2, pool_h // 2 + 1):
            for dc in range(-pool_w // 2, pool_w // 2 + 1):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if random.random() < 0.75:
                        self.tpool_grid[nr][nc] = TILE_POOL

    # Sand patches in low / subtidal zone
    for _ in range(random.randint(3, 6)):
        sr = random.randint(zones[3][0], rows - 1)
        sc = random.randint(0, cols - 1)
        sw = random.randint(4, 10)
        sh = random.randint(2, 4)
        for dr in range(-sh, sh + 1):
            for dc in range(-sw, sw + 1):
                nr, nc = sr + dr, sc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if random.random() < 0.6:
                        self.tpool_grid[nr][nc] = TILE_SAND

    # Initial algae on rocks in mid-low zone
    for r in range(zones[2][0], rows):
        for c in range(cols):
            if self.tpool_grid[r][c] in (TILE_ROCK, TILE_POOL):
                self.tpool_algae[r][c] = random.random() * 0.5


def _tpool_populate(self, pid):
    """Seed organisms according to preset."""
    rows = self.tpool_rows
    cols = self.tpool_cols
    zones = self.tpool_zones
    sessile = self.tpool_sessile
    mobile = self.tpool_mobile

    def _in_zone(zone_id):
        """Return (start_row, end_row) for a zone."""
        # zones order: SPRAY=0, HIGH=1, MID=2, LOW=3, SUBTIDAL=4
        return zones[zone_id]

    def _rand_pos(zone_id):
        s, e = _in_zone(zone_id)
        return random.randint(s, max(s, e - 1)), random.randint(0, cols - 1)

    # --- Barnacles: HIGH zone ---
    n_barn = 60 if pid != "mussel_bed" else 30
    for _ in range(n_barn):
        r, c = _rand_pos(1)  # HIGH
        if self.tpool_grid[r][c] == TILE_ROCK:
            sessile.append(_Sessile(r, c, SP_BARNACLE))

    # --- Mussels: MID zone ---
    n_muss = 80 if pid == "mussel_bed" else (40 if pid != "tropical" else 15)
    for _ in range(n_muss):
        r, c = _rand_pos(2)  # MID
        if self.tpool_grid[r][c] == TILE_ROCK:
            sessile.append(_Sessile(r, c, SP_MUSSEL))

    # --- Anemones: pools and MID-LOW ---
    n_anem = 25 if pid != "tropical" else 40
    for _ in range(n_anem):
        r, c = _rand_pos(random.choice([2, 3]))
        if self.tpool_grid[r][c] in (TILE_ROCK, TILE_POOL):
            sessile.append(_Sessile(r, c, SP_ANEMONE))

    # --- Kelp: LOW-SUBTIDAL ---
    n_kelp = 30 if pid != "tropical" else 15
    for _ in range(n_kelp):
        r, c = _rand_pos(random.choice([3, 4]))
        if self.tpool_grid[r][c] in (TILE_ROCK, TILE_POOL):
            sessile.append(_Sessile(r, c, SP_KELP))

    # --- Limpets: HIGH-MID ---
    for _ in range(20):
        r, c = _rand_pos(random.choice([1, 2]))
        if self.tpool_grid[r][c] == TILE_ROCK:
            mobile.append(_Mobile(r, c, SP_LIMPET))

    # --- Sea Stars: MID-LOW ---
    n_stars = 15 if pid != "wasting" else 30
    for _ in range(n_stars):
        r, c = _rand_pos(random.choice([2, 3]))
        mobile.append(_Mobile(r, c, SP_SEA_STAR))

    # --- Urchins: LOW-SUBTIDAL ---
    n_urch = 20 if pid != "tropical" else 35
    for _ in range(n_urch):
        r, c = _rand_pos(random.choice([3, 4]))
        mobile.append(_Mobile(r, c, SP_URCHIN))

    # --- Hermit Crabs ---
    n_hermit = 40 if pid == "hermit_economy" else 15
    for _ in range(n_hermit):
        r, c = _rand_pos(random.choice([2, 3]))
        mobile.append(_Mobile(r, c, SP_HERMIT_CRAB))

    # Scatter some empty shells for hermit economy
    if pid == "hermit_economy":
        for _ in range(20):
            r, c = _rand_pos(random.choice([2, 3]))
            self.tpool_empty_shells.append((r, c, 0.3 + random.random() * 0.7))

    # Wasting event: stars start with disease stress
    if pid == "wasting":
        for m in mobile:
            if m.kind == SP_SEA_STAR:
                m.stress = 0.4 + random.random() * 0.3


# ══════════════════════════════════════════════════════════════════════
#  Simulation step
# ══════════════════════════════════════════════════════════════════════

def _tpool_step(self):
    """Advance tide pool simulation by one tick."""
    gen = self.tpool_generation
    rows = self.tpool_rows
    cols = self.tpool_cols
    grid = self.tpool_grid
    algae = self.tpool_algae
    temp = self.tpool_temp
    moist = self.tpool_moisture
    zones = self.tpool_zones
    pid = self.tpool_preset_id

    # ── 1. Update tide ──
    self.tpool_tide_phase += 2 * math.pi / self.tpool_tide_period
    if self.tpool_tide_phase > 2 * math.pi:
        self.tpool_tide_phase -= 2 * math.pi
    base_level = 0.5 + self.tpool_tide_amplitude * math.sin(self.tpool_tide_phase)
    # Add small wave noise
    self.tpool_wave_offset = 0.03 * math.sin(gen * 0.7) + 0.02 * math.sin(gen * 1.3)
    self.tpool_tide_level = max(0.0, min(1.0, base_level + self.tpool_wave_offset))

    # Water line row: tide_level=0 → bottom (rows-1), tide_level=1 → top (0)
    water_row = int((1.0 - self.tpool_tide_level) * rows)
    water_row = max(0, min(rows - 1, water_row))
    self.tpool_water_row = water_row

    # ── 2. Update temperature & moisture ──
    for r in range(rows):
        for c in range(cols):
            submerged = r >= water_row
            in_pool = grid[r][c] == TILE_POOL
            if submerged or in_pool:
                # Cool, wet
                temp[r][c] = max(0.0, temp[r][c] - 0.05)
                moist[r][c] = min(1.0, moist[r][c] + 0.1)
            else:
                # Exposed: heat up, dry out
                elev_factor = 1.0 - r / rows  # higher = more exposed
                temp[r][c] = min(1.0, temp[r][c] + 0.02 * (1.0 + elev_factor))
                moist[r][c] = max(0.0, moist[r][c] - 0.03 * (1.0 + elev_factor))

    # Splash zone: partial moisture above waterline
    splash_rows = max(1, int(rows * 0.05))
    for r in range(max(0, water_row - splash_rows), water_row):
        for c in range(cols):
            if random.random() < 0.3:
                moist[r][c] = min(1.0, moist[r][c] + 0.05)

    # ── 3. Algae growth / decay ──
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] in (TILE_ROCK, TILE_POOL, TILE_ALGAE_ROCK):
                light = max(0.1, 1.0 - r / rows * 0.5)  # less light deeper
                wet = moist[r][c]
                growth = 0.005 * light * wet
                algae[r][c] = min(1.0, algae[r][c] + growth)
                # Decay if too dry
                if moist[r][c] < 0.2:
                    algae[r][c] = max(0.0, algae[r][c] - 0.01)
                # Mark rock as algae-covered
                if algae[r][c] > 0.3 and grid[r][c] == TILE_ROCK:
                    grid[r][c] = TILE_ALGAE_ROCK
                elif algae[r][c] <= 0.1 and grid[r][c] == TILE_ALGAE_ROCK:
                    grid[r][c] = TILE_ROCK

    # ── 4. Sessile organisms ──
    new_sessile = []
    dead_sessile = set()
    for i, s in enumerate(self.tpool_sessile):
        submerged = s.r >= water_row or grid[s.r][s.c] == TILE_POOL
        s.age += 1

        # Stress from exposure
        if not submerged:
            dry_stress = (1.0 - moist[s.r][s.c]) * 0.02
            heat_stress = temp[s.r][s.c] * 0.015
            s.stress = min(1.0, s.stress + dry_stress + heat_stress)
        else:
            s.stress = max(0.0, s.stress - 0.01)

        # Feeding
        if s.kind == SP_BARNACLE:
            # Filter feed when submerged
            if submerged:
                s.energy = min(2.0, s.energy + 0.01)
            else:
                s.energy -= 0.005
        elif s.kind == SP_MUSSEL:
            if submerged:
                s.energy = min(2.0, s.energy + 0.012)
            else:
                s.energy -= 0.004
            s.size = min(1.0, s.size + 0.001)
        elif s.kind == SP_ANEMONE:
            if submerged:
                s.energy = min(2.0, s.energy + 0.008)
            else:
                s.energy -= 0.006
        elif s.kind == SP_KELP:
            if submerged:
                light = max(0.1, 1.0 - s.r / rows * 0.5)
                s.energy = min(2.5, s.energy + 0.015 * light)
                s.size = min(1.5, s.size + 0.002)
            else:
                s.stress = min(1.0, s.stress + 0.04)
                s.energy -= 0.01

        # Death
        if s.energy <= 0 or s.stress >= 1.0 or s.age > 2000:
            dead_sessile.add(i)
            # Mussel death frees rock space
            continue

        # Reproduction (budding/settlement)
        if s.energy > 1.5 and random.random() < 0.01:
            dr, dc = random.choice(_NEIGHBORS_8)
            nr, nc = s.r + dr, s.c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] in (TILE_ROCK, TILE_ALGAE_ROCK, TILE_POOL):
                    # Check not already occupied by sessile
                    occupied = any(x.r == nr and x.c == nc
                                   for x in self.tpool_sessile)
                    if not occupied:
                        new_sessile.append(_Sessile(nr, nc, s.kind))
                        s.energy -= 0.5

    self.tpool_sessile = [s for i, s in enumerate(self.tpool_sessile)
                          if i not in dead_sessile]
    self.tpool_sessile.extend(new_sessile)

    # ── 5. Mobile organisms ──
    new_mobile = []
    dead_mobile = set()
    # Build occupancy lookup for sessile
    sessile_pos = {}
    for s in self.tpool_sessile:
        sessile_pos.setdefault((s.r, s.c), []).append(s)

    for i, m in enumerate(self.tpool_mobile):
        submerged = m.r >= water_row or grid[m.r][m.c] == TILE_POOL
        m.age += 1

        # Stress
        if not submerged and m.kind != SP_LIMPET:
            m.stress = min(1.0, m.stress + 0.015)
            m.energy -= 0.003
        elif not submerged and m.kind == SP_LIMPET:
            # Limpets tolerate exposure
            m.stress = min(1.0, m.stress + 0.003)
            m.energy -= 0.001
        else:
            m.stress = max(0.0, m.stress - 0.02)

        # Wasting disease for sea stars
        if pid == "wasting" and m.kind == SP_SEA_STAR:
            m.stress = min(1.0, m.stress + 0.005)
            if m.stress > 0.7:
                m.energy -= 0.02

        # Movement
        if submerged or m.kind == SP_LIMPET:
            m.heading += (random.random() - 0.5) * 0.8
            dr = round(math.sin(m.heading))
            dc = round(math.cos(m.heading))
            nr = max(0, min(rows - 1, m.r + dr))
            nc = max(0, min(cols - 1, m.c + dc))
            if grid[nr][nc] != TILE_SAND or m.kind == SP_HERMIT_CRAB:
                m.r, m.c = nr, nc

        # Feeding behavior
        if m.kind == SP_SEA_STAR:
            # Eat mussels / barnacles
            prey_here = sessile_pos.get((m.r, m.c), [])
            for p in prey_here:
                if p.kind in (SP_MUSSEL, SP_BARNACLE) and submerged:
                    p.energy -= 0.3
                    m.energy = min(2.0, m.energy + 0.15)
                    break
        elif m.kind == SP_URCHIN:
            # Graze algae
            if algae[m.r][m.c] > 0.1:
                eaten = min(0.1, algae[m.r][m.c])
                algae[m.r][m.c] -= eaten
                m.energy = min(2.0, m.energy + eaten * 0.8)
            # Also eat kelp
            kelp_here = [s for s in sessile_pos.get((m.r, m.c), [])
                         if s.kind == SP_KELP]
            for k in kelp_here:
                k.energy -= 0.1
                m.energy = min(2.0, m.energy + 0.05)
        elif m.kind == SP_LIMPET:
            # Graze algae
            if algae[m.r][m.c] > 0.05:
                eaten = min(0.05, algae[m.r][m.c])
                algae[m.r][m.c] -= eaten
                m.energy = min(2.0, m.energy + eaten * 0.6)
        elif m.kind == SP_HERMIT_CRAB:
            # Scavenge + check for shell upgrades
            m.energy = min(2.0, m.energy + 0.003)
            # Vacancy chain: look for better shell
            shells_here = [(j, sh) for j, sh in enumerate(self.tpool_empty_shells)
                           if abs(sh[0] - m.r) <= 1 and abs(sh[1] - m.c) <= 1]
            for j, (sr, sc, sz) in shells_here:
                if sz > m.shell_size:
                    # Swap shells
                    old_size = m.shell_size
                    m.shell_size = sz
                    self.tpool_empty_shells[j] = (m.r, m.c, old_size)
                    break

        m.energy -= 0.002  # baseline metabolism

        # Death
        if m.energy <= 0 or m.stress >= 1.0 or m.age > 3000:
            dead_mobile.add(i)
            # Hermit crab drops shell
            if m.kind == SP_HERMIT_CRAB:
                self.tpool_empty_shells.append((m.r, m.c, m.shell_size))
            continue

        # Reproduction
        if m.energy > 1.6 and random.random() < 0.008:
            dr, dc = random.choice(_NEIGHBORS_8)
            nr = max(0, min(rows - 1, m.r + dr))
            nc = max(0, min(cols - 1, m.c + dc))
            child = _Mobile(nr, nc, m.kind)
            if m.kind == SP_HERMIT_CRAB:
                # Needs a shell
                if self.tpool_empty_shells:
                    sh_idx = random.randint(0, len(self.tpool_empty_shells) - 1)
                    child.shell_size = self.tpool_empty_shells[sh_idx][2]
                    self.tpool_empty_shells.pop(sh_idx)
                else:
                    child.shell_size = 0.2  # tiny makeshift shell
            new_mobile.append(child)
            m.energy -= 0.6

    self.tpool_mobile = [m for i, m in enumerate(self.tpool_mobile)
                         if i not in dead_mobile]
    self.tpool_mobile.extend(new_mobile)

    # ── 6. Record history ──
    counts = {}
    for s in self.tpool_sessile:
        counts[s.kind] = counts.get(s.kind, 0) + 1
    for m in self.tpool_mobile:
        counts[m.kind] = counts.get(m.kind, 0) + 1
    for sp in range(8):
        self.tpool_pop_history[sp].append(counts.get(sp, 0))
        # Keep last 200 ticks
        if len(self.tpool_pop_history[sp]) > 200:
            self.tpool_pop_history[sp].pop(0)

    self.tpool_tide_history.append(self.tpool_tide_level)
    if len(self.tpool_tide_history) > 200:
        self.tpool_tide_history.pop(0)

    avg_stress = 0.0
    total = len(self.tpool_sessile) + len(self.tpool_mobile)
    if total > 0:
        avg_stress = (sum(s.stress for s in self.tpool_sessile) +
                      sum(m.stress for m in self.tpool_mobile)) / total
    self.tpool_stress_history.append(avg_stress)
    if len(self.tpool_stress_history) > 200:
        self.tpool_stress_history.pop(0)

    self.tpool_generation += 1


# ══════════════════════════════════════════════════════════════════════
#  Key handlers
# ══════════════════════════════════════════════════════════════════════

def _handle_tpool_menu_key(self, key: int) -> bool:
    """Handle key input in the preset selection menu."""
    n = len(TPOOL_PRESETS)
    if key == ord("q") or key == 27:
        self.tpool_mode = False
        self.tpool_menu = False
        return True
    if key == curses.KEY_UP or key == ord("k"):
        self.tpool_menu_sel = (self.tpool_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.tpool_menu_sel = (self.tpool_menu_sel + 1) % n
        return True
    if key in (10, 13, curses.KEY_ENTER):
        _tpool_init(self, self.tpool_menu_sel)
        return True
    return True


def _handle_tpool_key(self, key: int) -> bool:
    """Handle key input during simulation."""
    if key == ord(" "):
        self.tpool_running = not self.tpool_running
        self._flash("Running" if self.tpool_running else "Paused")
        return True

    if key == ord("n") or key == ord("."):
        _tpool_step(self)
        return True

    if key == ord("v"):
        views = ["shore", "cross_section", "graphs"]
        cur = views.index(self.tpool_view) if self.tpool_view in views else 0
        self.tpool_view = views[(cur + 1) % len(views)]
        self._flash(f"View: {self.tpool_view}")
        return True

    if key == ord("+") or key == ord("="):
        self.tpool_speed = min(20, self.tpool_speed + 1)
        self._flash(f"Speed: {self.tpool_speed}x")
        return True

    if key == ord("-") or key == ord("_"):
        self.tpool_speed = max(1, self.tpool_speed - 1)
        self._flash(f"Speed: {self.tpool_speed}x")
        return True

    if key == ord("r"):
        idx = next((i for i, p in enumerate(TPOOL_PRESETS)
                     if p[0] == self.tpool_preset_name), 0)
        _tpool_init(self, idx)
        return True

    if key == ord("R") or key == ord("m"):
        self.tpool_running = False
        self.tpool_menu = True
        self.tpool_menu_sel = 0
        return True

    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing — menu
# ══════════════════════════════════════════════════════════════════════

def _draw_tpool_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    self.stdscr.erase()

    title = "── Tide Pool & Intertidal Ecosystem ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2),
                           title[:max_x - 1],
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(TPOOL_PRESETS):
        y = 4 + i * 3
        if y >= max_y - 6:
            break
        marker = "▸ " if i == self.tpool_menu_sel else "  "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.tpool_menu_sel
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

    hints = " [↑/↓] Navigate   [Enter] Select   [q/Esc] Back"
    hy = max_y - 2
    if 0 < hy < max_y:
        try:
            self.stdscr.addstr(hy, 2, hints[:max_x - 4],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — main dispatcher
# ══════════════════════════════════════════════════════════════════════

def _draw_tpool(self, max_y: int, max_x: int):
    """Draw the active tide pool simulation."""
    self.stdscr.erase()

    # Title bar
    tide_pct = int(self.tpool_tide_level * 100)
    n_org = len(self.tpool_sessile) + len(self.tpool_mobile)
    title = (f" Tide Pool: {self.tpool_preset_name}"
             f" | t={self.tpool_generation}"
             f" | tide={tide_pct}%"
             f" | pop={n_org}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass

    view = self.tpool_view
    if view == "shore":
        _draw_tpool_shore(self, max_y, max_x)
    elif view == "cross_section":
        _draw_tpool_cross(self, max_y, max_x)
    elif view == "graphs":
        _draw_tpool_graphs(self, max_y, max_x)

    # Hint bar
    hint_y = max_y - 1
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


# ══════════════════════════════════════════════════════════════════════
#  Drawing — shore view (main ecosystem)
# ══════════════════════════════════════════════════════════════════════

def _draw_tpool_shore(self, max_y: int, max_x: int):
    """Rocky shore view with animated water level."""
    rows = self.tpool_rows
    cols = self.tpool_cols
    grid = self.tpool_grid
    algae = self.tpool_algae
    water_row = getattr(self, 'tpool_water_row', rows // 2)
    gen = self.tpool_generation

    view_rows = max_y - 3  # leave room for title + info + hint
    view_cols = max_x - 2
    r_scale = max(1, rows / view_rows) if rows > view_rows else 1
    c_scale = max(1, cols / view_cols) if cols > view_cols else 1

    # Build organism lookup
    org_map = {}
    for s in self.tpool_sessile:
        org_map[(s.r, s.c)] = (s.kind, s.stress)
    for m in self.tpool_mobile:
        org_map[(m.r, m.c)] = (m.kind, m.stress)

    for vr in range(min(view_rows, rows)):
        sr = int(vr * r_scale)
        if sr >= rows:
            break
        for vc in range(min(view_cols, cols)):
            sc = int(vc * c_scale)
            if sc >= cols:
                break

            x = vc + 1
            y = vr + 1
            if y >= max_y - 1 or x >= max_x - 1:
                continue

            submerged = sr >= water_row
            tile = grid[sr][sc]
            org = org_map.get((sr, sc))

            ch = ' '
            attr = curses.color_pair(0)

            if org is not None:
                kind, stress = org
                stressed = stress > 0.5
                if kind == SP_BARNACLE:
                    ch = '^'
                    attr = curses.color_pair(7) if not stressed else curses.color_pair(1)
                elif kind == SP_MUSSEL:
                    ch = 'M'
                    attr = curses.color_pair(4) | curses.A_BOLD
                elif kind == SP_ANEMONE:
                    ch = '*'
                    attr = curses.color_pair(5) | curses.A_BOLD
                elif kind == SP_SEA_STAR:
                    ch = 'X'
                    attr = curses.color_pair(1) | curses.A_BOLD
                elif kind == SP_URCHIN:
                    ch = 'o'
                    attr = curses.color_pair(5)
                elif kind == SP_KELP:
                    ch = '|'
                    attr = curses.color_pair(2) | curses.A_BOLD
                elif kind == SP_HERMIT_CRAB:
                    ch = '@'
                    attr = curses.color_pair(3) | curses.A_BOLD
                elif kind == SP_LIMPET:
                    ch = 'n'
                    attr = curses.color_pair(7)
            elif tile == TILE_WATER or (submerged and tile != TILE_ROCK
                                        and tile != TILE_ALGAE_ROCK):
                # Water
                wave = (gen + sc) % 4
                ch = '~' if wave < 2 else '≈' if wave < 3 else '~'
                attr = curses.color_pair(4) | curses.A_DIM
            elif tile == TILE_POOL and not submerged:
                ch = '~'
                attr = curses.color_pair(6)
            elif tile == TILE_ALGAE_ROCK:
                if algae[sr][sc] > 0.6:
                    ch = '%'
                    attr = curses.color_pair(2)
                else:
                    ch = '.'
                    attr = curses.color_pair(2) | curses.A_DIM
            elif tile == TILE_ROCK:
                ch = '#' if not submerged else '.'
                attr = curses.color_pair(7) | curses.A_DIM
            elif tile == TILE_SAND:
                ch = ':'
                attr = curses.color_pair(3) | curses.A_DIM
            elif submerged:
                ch = '~'
                attr = curses.color_pair(4) | curses.A_DIM

            # Water overlay: submerged non-organism cells get blue tint
            if submerged and org is None and tile not in (TILE_POOL,):
                attr = curses.color_pair(4) | curses.A_DIM

            # Splash zone spray
            if not submerged and sr >= water_row - 3 and sr < water_row:
                if random.random() < 0.15 and org is None:
                    ch = '.'
                    attr = curses.color_pair(6)

            try:
                self.stdscr.addstr(y, x, ch, attr)
            except curses.error:
                pass

    # Water line indicator
    wl_y = int(water_row / r_scale) + 1 if r_scale > 0 else water_row + 1
    if 0 < wl_y < max_y - 1:
        try:
            self.stdscr.addstr(wl_y, 0, '>', curses.color_pair(6) | curses.A_BOLD)
        except curses.error:
            pass

    # Zone labels on right edge
    zone_names = ["SPRAY", "HIGH", "MID", "LOW", "SUBTIDAL"]
    for zi, (zs, ze) in enumerate(self.tpool_zones):
        label_r = int(((zs + ze) / 2) / r_scale) + 1
        if 0 < label_r < max_y - 1 and max_x > len(zone_names[zi]) + 3:
            try:
                self.stdscr.addstr(label_r, max_x - len(zone_names[zi]) - 2,
                                   zone_names[zi],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    n_sess = len(self.tpool_sessile)
    n_mob = len(self.tpool_mobile)
    info = (f" sessile={n_sess} mobile={n_mob}"
            f" shells={len(self.tpool_empty_shells)}"
            f" tide={'HIGH' if self.tpool_tide_level > 0.65 else 'MID' if self.tpool_tide_level > 0.35 else 'LOW'}")
    try:
        self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — cross-section view (zonation bands)
# ══════════════════════════════════════════════════════════════════════

def _draw_tpool_cross(self, max_y: int, max_x: int):
    """Tidal cross-section showing zonation bands and water level."""
    rows = self.tpool_rows
    zones = self.tpool_zones
    water_row = getattr(self, 'tpool_water_row', rows // 2)
    view_h = max_y - 4
    view_w = max_x - 4

    zone_names = ["SPRAY", "HIGH INTERTIDAL", "MID INTERTIDAL",
                  "LOW INTERTIDAL", "SUBTIDAL"]
    zone_colors = [7, 3, 2, 6, 4]
    zone_species = [
        "Lichens, cyanobacteria",
        "Barnacles, limpets, periwinkles",
        "Mussels, anemones, sea stars",
        "Kelp, urchins, hermit crabs",
        "Full submersion — diverse community",
    ]

    # Count organisms per zone
    zone_counts = [0] * 5
    for s in self.tpool_sessile:
        for zi, (zs, ze) in enumerate(zones):
            if zs <= s.r < ze:
                zone_counts[zi] += 1
                break
    for m in self.tpool_mobile:
        for zi, (zs, ze) in enumerate(zones):
            if zs <= m.r < ze:
                zone_counts[zi] += 1
                break

    # Draw zones as horizontal bands
    rows_per_zone = max(2, view_h // 5)
    for zi in range(5):
        base_y = 2 + zi * rows_per_zone
        color = curses.color_pair(zone_colors[zi])

        # Zone header
        if base_y < max_y - 2:
            zs, ze = zones[zi]
            submerged = (zs + ze) // 2 >= water_row
            state = "[submerged]" if submerged else "[exposed]"
            header = f" {zone_names[zi]} — pop: {zone_counts[zi]} {state}"
            try:
                self.stdscr.addstr(base_y, 2, header[:view_w],
                                   color | curses.A_BOLD)
            except curses.error:
                pass

        # Species info
        if base_y + 1 < max_y - 2:
            try:
                self.stdscr.addstr(base_y + 1, 4,
                                   zone_species[zi][:view_w - 2],
                                   color | curses.A_DIM)
            except curses.error:
                pass

        # Density bar
        if base_y + 2 < max_y - 2 and rows_per_zone > 2:
            bar_len = min(zone_counts[zi], view_w - 6)
            bar = '█' * bar_len
            try:
                self.stdscr.addstr(base_y + 2, 4, bar[:view_w - 4], color)
            except curses.error:
                pass

    # Water level marker
    water_frac = 1.0 - self.tpool_tide_level
    wl_y = 2 + int(water_frac * (5 * rows_per_zone))
    wl_y = max(2, min(max_y - 3, wl_y))
    wl_label = f"~~~ WATER LEVEL (tide={int(self.tpool_tide_level*100)}%) ~~~"
    try:
        self.stdscr.addstr(wl_y, max(2, (max_x - len(wl_label)) // 2),
                           wl_label[:max_x - 2],
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — population & stress graphs
# ══════════════════════════════════════════════════════════════════════

def _draw_tpool_graphs(self, max_y: int, max_x: int):
    """Population time-series and stress/tide graphs."""
    view_h = max_y - 4
    view_w = max_x - 4
    graph_h = max(3, view_h // 3)
    graph_w = min(200, view_w - 10)

    # --- Tide level graph ---
    _draw_sparkline(self, 2, 2, graph_h, graph_w,
                    self.tpool_tide_history, "Tide Level",
                    curses.color_pair(4), max_y, max_x)

    # --- Population graph ---
    # Show top 4 species by current pop
    species_order = sorted(range(8),
                           key=lambda sp: self.tpool_pop_history[sp][-1]
                           if self.tpool_pop_history[sp] else 0,
                           reverse=True)[:4]
    sp_colors = [1, 2, 3, 4, 5, 6, 7, 3]
    base_y = 3 + graph_h
    try:
        self.stdscr.addstr(base_y, 2, "Population:",
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    for rank, sp in enumerate(species_order):
        hist = self.tpool_pop_history[sp]
        if not hist or max(hist) == 0:
            continue
        label = f"  {_SP_NAMES[sp]}: {hist[-1]}"
        ly = base_y + 1 + rank
        if ly >= max_y - 2:
            break
        color = curses.color_pair(sp_colors[sp % len(sp_colors)])
        try:
            self.stdscr.addstr(ly, 2, label[:view_w], color)
        except curses.error:
            pass
        # Mini sparkline
        _draw_mini_spark(self, ly, 30, min(graph_w - 28, 60),
                         hist, color, max_y, max_x)

    # --- Stress graph ---
    stress_y = base_y + 7
    _draw_sparkline(self, stress_y, 2, max(3, graph_h - 1), graph_w,
                    self.tpool_stress_history, "Avg Stress",
                    curses.color_pair(1), max_y, max_x)


def _draw_sparkline(self, base_y, base_x, height, width,
                    data, label, color, max_y, max_x):
    """Draw a simple sparkline graph."""
    if base_y >= max_y - 1:
        return
    try:
        self.stdscr.addstr(base_y, base_x, f"{label}:",
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if not data:
        return
    mn = min(data)
    mx = max(data)
    rng = mx - mn if mx > mn else 1.0
    bars = "▁▂▃▄▅▆▇█"
    n = len(bars)

    # Render last `width` data points
    visible = data[-width:]
    for i, v in enumerate(visible):
        x = base_x + i
        y = base_y + 1
        if x >= max_x - 1 or y >= max_y - 1:
            continue
        idx = int((v - mn) / rng * (n - 1))
        idx = max(0, min(n - 1, idx))
        try:
            self.stdscr.addstr(y, x, bars[idx], color)
        except curses.error:
            pass


def _draw_mini_spark(self, y, x, width, data, color, max_y, max_x):
    """Tiny inline sparkline."""
    if not data or y >= max_y - 1:
        return
    bars = "▁▂▃▄▅▆▇█"
    n = len(bars)
    visible = data[-width:]
    mn = min(visible) if visible else 0
    mx = max(visible) if visible else 1
    rng = mx - mn if mx > mn else 1.0
    for i, v in enumerate(visible):
        cx = x + i
        if cx >= max_x - 1:
            break
        idx = int((v - mn) / rng * (n - 1))
        idx = max(0, min(n - 1, idx))
        try:
            self.stdscr.addstr(y, cx, bars[idx], color | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register tide pool mode methods on the App class."""
    App.TPOOL_PRESETS = TPOOL_PRESETS
    App._enter_tpool_mode = _enter_tpool_mode
    App._exit_tpool_mode = _exit_tpool_mode
    App._tpool_init = _tpool_init
    App._tpool_step = _tpool_step
    App._handle_tpool_menu_key = _handle_tpool_menu_key
    App._handle_tpool_key = _handle_tpool_key
    App._draw_tpool_menu = _draw_tpool_menu
    App._draw_tpool = _draw_tpool
