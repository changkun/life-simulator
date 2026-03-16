"""Mode: myco — Mycorrhizal Network & Wood Wide Web.

Underground fungal highway connecting forest trees.  Mycorrhizal hyphae branch
through soil linking root systems into a shared communication and resource-
trading network.  Mother trees detect stressed seedlings and route carbon /
phosphorus through the fungal mesh; pest-attacked trees broadcast chemical
alarm signals that propagate through the network triggering defensive responses
in neighbors; fungi take a carbon "tax" for brokering transfers.

Emergent phenomena:
  - Hub-and-spoke network topology around mother trees
  - Carbon/phosphorus flow from surplus to deficit
  - Alarm signal propagation (pest cascade)
  - Fungal carbon tax economics
  - Seasonal nutrient cycling (spring flush, autumn senescence)
  - Clear-cut fragmentation and network collapse
"""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

MYCO_PRESETS = [
    ("Old-Growth Cooperation",
     "Mature diverse forest — large mother trees fund seedlings via dense fungal mesh",
     "oldgrowth"),
    ("Drought Triage",
     "Prolonged drought stresses canopy — watch network reroute water & carbon to weakest",
     "drought"),
    ("Pest Cascade",
     "Bark beetle outbreak on east edge — alarm signals propagate through the web",
     "pest"),
    ("Clear-Cut Fragmentation",
     "Logging removes hub trees — network fragments into isolated islands",
     "clearcut"),
    ("Monoculture vs. Biodiversity",
     "Plantation monoculture on left, mixed old-growth on right — compare network resilience",
     "monoculture"),
    ("Seasonal Nutrient Cycling",
     "Four-season cycle — spring carbon flush, summer growth, autumn senescence, winter dormancy",
     "seasonal"),
]


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

# Tree species
SP_OAK = 0
SP_BIRCH = 1
SP_PINE = 2
SP_FIR = 3
SP_MAPLE = 4
SP_SEEDLING = 5

_SP_NAMES = ["Oak", "Birch", "Pine", "Fir", "Maple", "Seedling"]
_SP_GLYPHS = ['O', 'B', 'P', 'F', 'M', '.']
_SP_COLORS = [2, 3, 2, 2, 1, 2]  # color pair indices

# Soil nutrients
SOIL_CARBON = 0
SOIL_PHOSPHORUS = 1
SOIL_NITROGEN = 2

# Signal types
SIG_ALARM = 0      # pest warning
SIG_CARBON = 1     # carbon transfer
SIG_PHOSPHORUS = 2 # phosphorus transfer
SIG_WATER = 3      # water transfer

_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]


# ══════════════════════════════════════════════════════════════════════
#  Data classes
# ══════════════════════════════════════════════════════════════════════

class _Tree:
    """A tree in the forest — above-ground trunk + below-ground root system."""
    __slots__ = ('r', 'c', 'species', 'age', 'carbon', 'phosphorus', 'water',
                 'health', 'size', 'is_mother', 'defense_level', 'alarm_timer',
                 'pest_level', 'connected_hyphae', 'photosynthesis_rate',
                 'root_radius', 'dormant')

    def __init__(self, r, c, species, age=0, size=0.3):
        self.r = r
        self.c = c
        self.species = species
        self.age = age
        self.carbon = 0.5 + random.random() * 0.5
        self.phosphorus = 0.3 + random.random() * 0.3
        self.water = 0.5 + random.random() * 0.3
        self.health = 1.0
        self.size = size
        self.is_mother = False
        self.defense_level = 0.0
        self.alarm_timer = 0
        self.pest_level = 0.0
        self.connected_hyphae = []  # indices into hypha list
        self.photosynthesis_rate = 0.02 + random.random() * 0.01
        self.root_radius = max(1, int(size * 4))
        self.dormant = False


class _Hypha:
    """A fungal hypha connection between two trees."""
    __slots__ = ('tree_a', 'tree_b', 'thickness', 'age', 'carbon_flow',
                 'phosphorus_flow', 'signal_strength', 'signal_type',
                 'signal_timer', 'health', 'nodes')

    def __init__(self, tree_a, tree_b):
        self.tree_a = tree_a
        self.tree_b = tree_b
        self.thickness = 0.1 + random.random() * 0.2
        self.age = 0
        self.carbon_flow = 0.0       # positive = a→b
        self.phosphorus_flow = 0.0
        self.signal_strength = 0.0
        self.signal_type = -1
        self.signal_timer = 0
        self.health = 1.0
        # Intermediate path nodes for drawing
        self.nodes = []


class _Particle:
    """A visible nutrient/signal particle flowing through a hypha."""
    __slots__ = ('hypha_idx', 'progress', 'kind', 'color')

    def __init__(self, hypha_idx, kind, color):
        self.hypha_idx = hypha_idx
        self.progress = 0.0  # 0.0 = tree_a, 1.0 = tree_b
        self.kind = kind     # 'carbon', 'phosphorus', 'alarm', 'water'
        self.color = color


# ══════════════════════════════════════════════════════════════════════
#  Enter / Exit
# ══════════════════════════════════════════════════════════════════════

def _enter_myco_mode(self):
    """Enter mycorrhizal network mode — show preset menu."""
    self.myco_mode = True
    self.myco_menu = True
    self.myco_menu_sel = 0


def _exit_myco_mode(self):
    """Exit mycorrhizal network mode."""
    self.myco_mode = False
    self.myco_menu = False
    for attr in list(vars(self)):
        if attr.startswith('myco_') and attr not in ('myco_mode',):
            try:
                delattr(self, attr)
            except AttributeError:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _myco_init(self, preset_idx: int):
    """Initialize mycorrhizal network simulation for the chosen preset."""
    name, _desc, pid = MYCO_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(20, max_x - 2)

    self.myco_menu = False
    self.myco_running = False
    self.myco_preset_name = name
    self.myco_preset_id = pid
    self.myco_rows = rows
    self.myco_cols = cols
    self.myco_generation = 0
    self.myco_speed = 1
    self.myco_view = "forest"  # forest | network | graphs

    # Season (0=spring, 1=summer, 2=autumn, 3=winter)
    self.myco_season = 0 if pid == "seasonal" else 1
    self.myco_season_tick = 0
    self.myco_season_length = 120  # ticks per season
    _SEASON_NAMES = ["Spring", "Summer", "Autumn", "Winter"]
    self.myco_season_names = _SEASON_NAMES

    # Environmental state
    self.myco_soil_moisture = [[0.5 + random.random() * 0.3
                                 for _ in range(cols)] for _ in range(rows)]
    self.myco_soil_nutrients = [[0.4 + random.random() * 0.2
                                  for _ in range(cols)] for _ in range(rows)]

    # Organisms
    self.myco_trees = []
    self.myco_hyphae = []
    self.myco_particles = []

    # Stats history for graphs
    self.myco_history = {
        'total_carbon_flow': [],
        'total_phosphorus_flow': [],
        'alarm_signals': [],
        'network_edges': [],
        'avg_tree_health': [],
        'mother_tree_count': [],
        'seedling_count': [],
        'fungal_tax': [],
        'avg_defense': [],
        'connected_components': [],
    }
    self.myco_history_keys = list(self.myco_history.keys())

    # Drought
    self.myco_drought = pid == "drought"
    self.myco_drought_intensity = 0.7 if pid == "drought" else 0.0

    # Pest state
    self.myco_pest_active = pid == "pest"
    self.myco_pest_origin_col = cols - 5 if pid == "pest" else -1

    # Fungal tax accumulator
    self.myco_fungal_carbon_pool = 0.0

    _myco_populate(self, pid)
    _myco_build_network(self)
    self._flash(f"Mycorrhizal Network: {name}")


def _myco_populate(self, pid):
    """Seed trees according to preset."""
    rows = self.myco_rows
    cols = self.myco_cols
    trees = self.myco_trees

    def _place_tree(species, r, c, age=None, size=None):
        if age is None:
            age = random.randint(0, 500)
        if size is None:
            size = 0.2 + random.random() * 0.6
        t = _Tree(r, c, species, age, size)
        if size > 0.7 and species != SP_SEEDLING:
            t.is_mother = True
            t.root_radius = max(3, int(size * 6))
        trees.append(t)

    if pid == "oldgrowth":
        # Dense diverse old-growth forest
        species_pool = [SP_OAK, SP_BIRCH, SP_PINE, SP_FIR, SP_MAPLE]
        # Place 4-6 mother trees
        for _ in range(random.randint(4, 6)):
            r = random.randint(3, rows - 4)
            c = random.randint(3, cols - 4)
            sp = random.choice(species_pool)
            _place_tree(sp, r, c, age=random.randint(800, 2000), size=0.8 + random.random() * 0.2)
        # Fill with mature trees
        for _ in range(35):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            sp = random.choice(species_pool)
            _place_tree(sp, r, c, age=random.randint(200, 800), size=0.4 + random.random() * 0.4)
        # Seedlings
        for _ in range(20):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            _place_tree(SP_SEEDLING, r, c, age=random.randint(0, 50), size=0.1 + random.random() * 0.15)

    elif pid == "drought":
        species_pool = [SP_OAK, SP_PINE, SP_FIR, SP_BIRCH]
        for _ in range(5):
            r = random.randint(3, rows - 4)
            c = random.randint(3, cols - 4)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(500, 1500), size=0.7 + random.random() * 0.3)
        for _ in range(30):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(100, 600), size=0.3 + random.random() * 0.4)
        for _ in range(15):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            _place_tree(SP_SEEDLING, r, c, age=random.randint(0, 30), size=0.1 + random.random() * 0.1)
        # Start with reduced water
        for r in range(rows):
            for c in range(cols):
                self.myco_soil_moisture[r][c] *= 0.3

    elif pid == "pest":
        species_pool = [SP_OAK, SP_BIRCH, SP_PINE, SP_FIR, SP_MAPLE]
        for _ in range(5):
            r = random.randint(3, rows - 4)
            c = random.randint(3, cols - 4)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(500, 1200), size=0.7 + random.random() * 0.3)
        for _ in range(35):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(100, 500), size=0.3 + random.random() * 0.5)
        for _ in range(12):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            _place_tree(SP_SEEDLING, r, c, age=0, size=0.1)
        # Infect trees on east edge
        for t in trees:
            if t.c > cols - 10:
                t.pest_level = 0.3 + random.random() * 0.4

    elif pid == "clearcut":
        species_pool = [SP_OAK, SP_BIRCH, SP_PINE, SP_FIR, SP_MAPLE]
        # Left side: intact old-growth
        for _ in range(4):
            r = random.randint(3, rows - 4)
            c = random.randint(2, cols // 3)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(600, 1500), size=0.7 + random.random() * 0.3)
        for _ in range(20):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols // 3)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(100, 600), size=0.3 + random.random() * 0.5)
        # Right side: only stumps and seedlings (clear-cut)
        for _ in range(8):
            r = random.randint(1, rows - 2)
            c = random.randint(2 * cols // 3, cols - 2)
            _place_tree(SP_SEEDLING, r, c, age=random.randint(0, 20), size=0.1)
        # Middle: transition zone with some surviving trees
        for _ in range(6):
            r = random.randint(1, rows - 2)
            c = random.randint(cols // 3, 2 * cols // 3)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(50, 300), size=0.25 + random.random() * 0.3)

    elif pid == "monoculture":
        # Left half: pine monoculture
        for _ in range(25):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols // 2 - 2)
            _place_tree(SP_PINE, r, c,
                        age=random.randint(100, 400), size=0.3 + random.random() * 0.3)
        # Right half: mixed old-growth
        species_pool = [SP_OAK, SP_BIRCH, SP_FIR, SP_MAPLE]
        for _ in range(3):
            r = random.randint(3, rows - 4)
            c = random.randint(cols // 2 + 2, cols - 3)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(600, 1200), size=0.7 + random.random() * 0.3)
        for _ in range(20):
            r = random.randint(1, rows - 2)
            c = random.randint(cols // 2 + 1, cols - 2)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(100, 600), size=0.3 + random.random() * 0.5)
        for _ in range(10):
            r = random.randint(1, rows - 2)
            c = random.randint(cols // 2 + 1, cols - 2)
            _place_tree(SP_SEEDLING, r, c, age=0, size=0.1)

    elif pid == "seasonal":
        species_pool = [SP_OAK, SP_BIRCH, SP_MAPLE, SP_PINE, SP_FIR]
        for _ in range(5):
            r = random.randint(3, rows - 4)
            c = random.randint(3, cols - 4)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(500, 1500), size=0.7 + random.random() * 0.3)
        for _ in range(30):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            _place_tree(random.choice(species_pool), r, c,
                        age=random.randint(100, 500), size=0.3 + random.random() * 0.5)
        for _ in range(15):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            _place_tree(SP_SEEDLING, r, c, age=0, size=0.1 + random.random() * 0.1)


def _myco_build_network(self):
    """Build the mycorrhizal hyphal network connecting nearby trees."""
    trees = self.myco_trees
    hyphae = self.myco_hyphae
    hyphae.clear()

    n = len(trees)
    # Connect trees within root radius range
    for i in range(n):
        ti = trees[i]
        for j in range(i + 1, n):
            tj = trees[j]
            dist = math.sqrt((ti.r - tj.r) ** 2 + (ti.c - tj.c) ** 2)
            max_reach = ti.root_radius + tj.root_radius
            if dist <= max_reach and dist > 0:
                # Probability of connection decreases with distance
                prob = 1.0 - (dist / max_reach) * 0.6
                # Mother trees connect more readily
                if ti.is_mother or tj.is_mother:
                    prob = min(1.0, prob + 0.3)
                # Same species bonus (ectomycorrhizal specificity)
                if ti.species == tj.species:
                    prob = min(1.0, prob + 0.15)
                if random.random() < prob:
                    h = _Hypha(i, j)
                    h.thickness = 0.1 + 0.1 * (ti.size + tj.size) / 2
                    # Compute intermediate path nodes for drawing
                    h.nodes = _compute_hypha_path(ti, tj)
                    idx = len(hyphae)
                    hyphae.append(h)
                    ti.connected_hyphae.append(idx)
                    tj.connected_hyphae.append(idx)


def _compute_hypha_path(ta, tb):
    """Compute a slightly curved underground path between two trees."""
    nodes = []
    steps = max(3, int(math.sqrt((ta.r - tb.r)**2 + (ta.c - tb.c)**2)))
    for s in range(steps + 1):
        t = s / steps
        # Linear interpolation with slight random wobble
        r = ta.r + (tb.r - ta.r) * t + (random.random() - 0.5) * 1.5
        c = ta.c + (tb.c - ta.c) * t + (random.random() - 0.5) * 1.5
        nodes.append((r, c))
    return nodes


# ══════════════════════════════════════════════════════════════════════
#  Simulation step
# ══════════════════════════════════════════════════════════════════════

def _myco_step(self):
    """Advance mycorrhizal network simulation by one tick."""
    gen = self.myco_generation
    trees = self.myco_trees
    hyphae = self.myco_hyphae
    pid = self.myco_preset_id

    # ── 1. Season update ──
    self.myco_season_tick += 1
    if self.myco_season_tick >= self.myco_season_length:
        self.myco_season_tick = 0
        self.myco_season = (self.myco_season + 1) % 4

    season = self.myco_season
    season_phase = self.myco_season_tick / self.myco_season_length
    # Season factors
    if season == 0:  # Spring
        photo_mult = 0.7 + 0.3 * season_phase
        growth_mult = 1.2
        dormancy = False
    elif season == 1:  # Summer
        photo_mult = 1.0
        growth_mult = 1.0
        dormancy = False
    elif season == 2:  # Autumn
        photo_mult = 1.0 - 0.5 * season_phase
        growth_mult = 0.5
        dormancy = False
    else:  # Winter
        photo_mult = 0.1
        growth_mult = 0.1
        dormancy = True

    # ── 2. Drought update ──
    if self.myco_drought:
        self.myco_drought_intensity = min(1.0,
            self.myco_drought_intensity + 0.001)
        for r in range(self.myco_rows):
            for c in range(self.myco_cols):
                self.myco_soil_moisture[r][c] = max(0.05,
                    self.myco_soil_moisture[r][c] - 0.002 * self.myco_drought_intensity)
    else:
        # Normal soil moisture recovery
        for r in range(self.myco_rows):
            for c in range(self.myco_cols):
                if season != 3:  # not winter
                    target = 0.5 + 0.2 * (1.0 if season == 0 else 0.5)
                    self.myco_soil_moisture[r][c] += (target - self.myco_soil_moisture[r][c]) * 0.01

    # ── 3. Pest spread ──
    if self.myco_pest_active:
        for t in trees:
            if t.pest_level > 0:
                t.pest_level = min(1.0, t.pest_level + 0.005)
                t.health = max(0.0, t.health - t.pest_level * 0.01)
                # Spread to nearby trees
                if random.random() < t.pest_level * 0.02:
                    for t2 in trees:
                        if t2 is not t and t2.pest_level < 0.1:
                            d = math.sqrt((t.r - t2.r)**2 + (t.c - t2.c)**2)
                            if d < 8:
                                # Defense reduces infection
                                infection_chance = 0.1 * (1.0 - t2.defense_level)
                                if random.random() < infection_chance:
                                    t2.pest_level = 0.1

    # ── 4. Tree physiology ──
    total_carbon_flow = 0.0
    total_phosphorus_flow = 0.0
    alarm_count = 0
    fungal_tax = 0.0

    for ti, t in enumerate(trees):
        t.age += 1
        t.dormant = dormancy and t.species not in (SP_PINE, SP_FIR)

        if not t.dormant:
            # Photosynthesis (carbon gain)
            soil_m = self.myco_soil_moisture[min(t.r, self.myco_rows-1)][min(t.c, self.myco_cols-1)]
            photo = t.photosynthesis_rate * t.size * photo_mult * soil_m
            if t.species == SP_SEEDLING:
                photo *= 0.3
            t.carbon = min(3.0, t.carbon + photo)

            # Root phosphorus uptake
            soil_n = self.myco_soil_nutrients[min(t.r, self.myco_rows-1)][min(t.c, self.myco_cols-1)]
            p_uptake = 0.005 * t.root_radius * soil_n
            t.phosphorus = min(2.0, t.phosphorus + p_uptake)

            # Water uptake
            w_uptake = 0.01 * t.root_radius * soil_m
            t.water = min(2.0, t.water + w_uptake)

            # Growth
            if t.carbon > 0.8 and t.phosphorus > 0.3 and t.water > 0.3:
                growth = 0.0002 * growth_mult
                t.size = min(1.0, t.size + growth)
                if t.species == SP_SEEDLING and t.size > 0.25:
                    # Graduate to a real tree species
                    t.species = random.choice([SP_OAK, SP_BIRCH, SP_PINE, SP_FIR, SP_MAPLE])
                t.root_radius = max(1, int(t.size * (6 if t.is_mother else 4)))
        else:
            # Dormant: minimal metabolism
            t.carbon = max(0.0, t.carbon - 0.002)

        # Metabolism cost
        metab = 0.005 * t.size * (0.3 if t.dormant else 1.0)
        t.carbon = max(0.0, t.carbon - metab)
        t.water = max(0.0, t.water - metab * 0.5)

        # Health update
        stress = 0.0
        if t.carbon < 0.2:
            stress += 0.3
        if t.water < 0.15:
            stress += 0.3
        if t.phosphorus < 0.1:
            stress += 0.2
        if t.pest_level > 0:
            stress += t.pest_level * 0.5
        t.health = max(0.0, min(1.0, t.health + (0.01 if stress < 0.2 else -stress * 0.01)))

        # Pest alarm broadcasting
        if t.pest_level > 0.2 and t.alarm_timer <= 0:
            t.alarm_timer = 30
            alarm_count += 1
            # Send alarm through connected hyphae
            for hi in t.connected_hyphae:
                if hi < len(hyphae):
                    h = hyphae[hi]
                    h.signal_type = SIG_ALARM
                    h.signal_strength = t.pest_level * 0.8
                    h.signal_timer = 20
                    # Spawn alarm particle
                    self.myco_particles.append(
                        _Particle(hi, 'alarm', 1))
        if t.alarm_timer > 0:
            t.alarm_timer -= 1

        # Defense decay
        t.defense_level = max(0.0, t.defense_level - 0.005)

        # Mother tree detection: check if neighbors are stressed
        if t.is_mother and not t.dormant:
            for hi in t.connected_hyphae:
                if hi >= len(hyphae):
                    continue
                h = hyphae[hi]
                other_idx = h.tree_b if h.tree_a == ti else h.tree_a
                if other_idx >= len(trees):
                    continue
                other = trees[other_idx]

                # Carbon sharing: mother sends to stressed trees
                if t.carbon > 1.0 and other.carbon < 0.4:
                    transfer = min(0.03, t.carbon * 0.05)
                    tax = transfer * 0.1  # fungal tax
                    t.carbon -= transfer
                    other.carbon += transfer - tax
                    fungal_tax += tax
                    h.carbon_flow = transfer
                    total_carbon_flow += transfer
                    if random.random() < 0.3:
                        self.myco_particles.append(
                            _Particle(hi, 'carbon', 2))

                # Phosphorus sharing
                if t.phosphorus > 0.8 and other.phosphorus < 0.2:
                    transfer = min(0.02, t.phosphorus * 0.04)
                    tax = transfer * 0.1
                    t.phosphorus -= transfer
                    other.phosphorus += transfer - tax
                    fungal_tax += tax * 0.5
                    h.phosphorus_flow = transfer
                    total_phosphorus_flow += transfer
                    if random.random() < 0.2:
                        self.myco_particles.append(
                            _Particle(hi, 'phosphorus', 5))

                # Water sharing during drought
                if self.myco_drought and t.water > 0.8 and other.water < 0.3:
                    transfer = min(0.02, t.water * 0.03)
                    t.water -= transfer
                    other.water += transfer
                    if random.random() < 0.2:
                        self.myco_particles.append(
                            _Particle(hi, 'water', 4))

    # ── 5. Signal propagation through network ──
    for h in hyphae:
        if h.signal_timer > 0:
            h.signal_timer -= 1
            # Deliver signal to receiving tree
            if h.signal_timer == 10:  # mid-propagation delivery
                if h.signal_type == SIG_ALARM:
                    for tidx in (h.tree_a, h.tree_b):
                        if tidx < len(trees):
                            t = trees[tidx]
                            t.defense_level = min(1.0,
                                t.defense_level + h.signal_strength * 0.5)
                            # Cascade: re-broadcast alarm
                            if h.signal_strength > 0.3:
                                for hi2 in t.connected_hyphae:
                                    if hi2 < len(hyphae) and hyphae[hi2] is not h:
                                        h2 = hyphae[hi2]
                                        if h2.signal_timer <= 0:
                                            h2.signal_type = SIG_ALARM
                                            h2.signal_strength = h.signal_strength * 0.6
                                            h2.signal_timer = 15
                                            self.myco_particles.append(
                                                _Particle(hi2, 'alarm', 1))
        else:
            h.signal_strength *= 0.9
            h.carbon_flow *= 0.8
            h.phosphorus_flow *= 0.8

    # ── 6. Non-mother tree trading (mutualism) ──
    for h in hyphae:
        if h.signal_timer > 0:
            continue
        ta = trees[h.tree_a] if h.tree_a < len(trees) else None
        tb = trees[h.tree_b] if h.tree_b < len(trees) else None
        if ta is None or tb is None:
            continue
        if ta.dormant and tb.dormant:
            continue

        # Carbon flows from surplus to deficit
        diff_c = ta.carbon - tb.carbon
        if abs(diff_c) > 0.3:
            transfer = diff_c * 0.02
            tax = abs(transfer) * 0.08
            ta.carbon -= transfer
            tb.carbon += transfer - (tax if transfer > 0 else -tax)
            fungal_tax += tax
            h.carbon_flow = transfer
            total_carbon_flow += abs(transfer)

    # ── 7. Update particles ──
    new_particles = []
    for p in self.myco_particles:
        p.progress += 0.08
        if p.progress < 1.0:
            new_particles.append(p)
    self.myco_particles = new_particles

    # Cap particles
    if len(self.myco_particles) > 200:
        self.myco_particles = self.myco_particles[-200:]

    # ── 8. Hypha health & growth ──
    dead_hyphae = set()
    for i, h in enumerate(hyphae):
        h.age += 1
        # Hyphae grow thicker with use
        use = abs(h.carbon_flow) + abs(h.phosphorus_flow) + h.signal_strength
        h.thickness = min(1.0, h.thickness + use * 0.001)
        # Decay unused hyphae
        if use < 0.001:
            h.health -= 0.002
        else:
            h.health = min(1.0, h.health + 0.001)
        if h.health <= 0:
            dead_hyphae.add(i)

    # Remove dead hyphae
    if dead_hyphae:
        # Remap indices
        new_hyphae = []
        remap = {}
        for i, h in enumerate(hyphae):
            if i not in dead_hyphae:
                remap[i] = len(new_hyphae)
                new_hyphae.append(h)
        self.myco_hyphae = new_hyphae
        hyphae = self.myco_hyphae
        # Update tree references
        for t in trees:
            t.connected_hyphae = [remap[hi] for hi in t.connected_hyphae
                                   if hi in remap]
        # Update particle references
        self.myco_particles = [p for p in self.myco_particles
                                if p.hypha_idx in remap]
        for p in self.myco_particles:
            p.hypha_idx = remap[p.hypha_idx]

    # ── 9. Tree death & new seedlings ──
    dead_trees = set()
    for i, t in enumerate(trees):
        if t.health <= 0 or t.carbon <= 0:
            dead_trees.add(i)

    if dead_trees:
        new_trees = []
        remap_t = {}
        for i, t in enumerate(trees):
            if i not in dead_trees:
                remap_t[i] = len(new_trees)
                new_trees.append(t)
        self.myco_trees = new_trees
        trees = self.myco_trees
        # Remap hypha tree references
        valid_hyphae = []
        for h in hyphae:
            if h.tree_a in remap_t and h.tree_b in remap_t:
                h.tree_a = remap_t[h.tree_a]
                h.tree_b = remap_t[h.tree_b]
                valid_hyphae.append(h)
        self.myco_hyphae = valid_hyphae
        hyphae = self.myco_hyphae
        # Rebuild connected_hyphae references
        for t in trees:
            t.connected_hyphae = []
        for i, h in enumerate(hyphae):
            if h.tree_a < len(trees):
                trees[h.tree_a].connected_hyphae.append(i)
            if h.tree_b < len(trees):
                trees[h.tree_b].connected_hyphae.append(i)
        self.myco_particles = []

    # Occasional new seedling
    if not dormancy and random.random() < 0.01 and len(trees) < 80:
        # Seedlings appear near mother trees
        mothers = [t for t in trees if t.is_mother]
        if mothers:
            mom = random.choice(mothers)
            dr = random.randint(-5, 5)
            dc = random.randint(-5, 5)
            nr = max(1, min(self.myco_rows - 2, mom.r + dr))
            nc = max(1, min(self.myco_cols - 2, mom.c + dc))
            seedling = _Tree(nr, nc, SP_SEEDLING, age=0, size=0.1)
            trees.append(seedling)
            # Try to connect to nearby trees
            si = len(trees) - 1
            for ti, t in enumerate(trees[:-1]):
                d = math.sqrt((t.r - nr)**2 + (t.c - nc)**2)
                if d <= t.root_radius + 2 and random.random() < 0.5:
                    h = _Hypha(ti, si)
                    h.nodes = _compute_hypha_path(t, seedling)
                    hi = len(hyphae)
                    hyphae.append(h)
                    t.connected_hyphae.append(hi)
                    seedling.connected_hyphae.append(hi)

    # Occasional new hypha connection
    if random.random() < 0.02:
        for i in range(len(trees)):
            for j in range(i + 1, len(trees)):
                if any(h.tree_a == i and h.tree_b == j or
                       h.tree_a == j and h.tree_b == i for h in hyphae):
                    continue
                ti, tj = trees[i], trees[j]
                d = math.sqrt((ti.r - tj.r)**2 + (ti.c - tj.c)**2)
                if d <= ti.root_radius + tj.root_radius and d > 0:
                    if random.random() < 0.1:
                        h = _Hypha(i, j)
                        h.nodes = _compute_hypha_path(ti, tj)
                        hi = len(hyphae)
                        hyphae.append(h)
                        ti.connected_hyphae.append(hi)
                        tj.connected_hyphae.append(hi)
                        break
            else:
                continue
            break

    # ── 10. Fungal carbon pool ──
    self.myco_fungal_carbon_pool += fungal_tax
    # Fungi spend carbon to maintain hyphae
    maint_cost = len(hyphae) * 0.0005
    self.myco_fungal_carbon_pool = max(0.0,
        self.myco_fungal_carbon_pool - maint_cost)

    # ── 11. Record history ──
    hist = self.myco_history
    hist['total_carbon_flow'].append(total_carbon_flow)
    hist['total_phosphorus_flow'].append(total_phosphorus_flow)
    hist['alarm_signals'].append(alarm_count)
    hist['network_edges'].append(len(hyphae))
    avg_h = (sum(t.health for t in trees) / len(trees)) if trees else 0
    hist['avg_tree_health'].append(avg_h)
    hist['mother_tree_count'].append(sum(1 for t in trees if t.is_mother))
    hist['seedling_count'].append(sum(1 for t in trees if t.species == SP_SEEDLING))
    hist['fungal_tax'].append(fungal_tax)
    avg_def = (sum(t.defense_level for t in trees) / len(trees)) if trees else 0
    hist['avg_defense'].append(avg_def)
    # Connected components (BFS)
    cc = _count_components(trees, hyphae)
    hist['connected_components'].append(cc)

    for k in hist:
        if len(hist[k]) > 200:
            hist[k].pop(0)

    self.myco_generation += 1


def _count_components(trees, hyphae):
    """Count connected components in the network."""
    n = len(trees)
    if n == 0:
        return 0
    visited = [False] * n
    components = 0
    # Build adjacency
    adj = [[] for _ in range(n)]
    for h in hyphae:
        if h.tree_a < n and h.tree_b < n:
            adj[h.tree_a].append(h.tree_b)
            adj[h.tree_b].append(h.tree_a)
    for i in range(n):
        if not visited[i]:
            components += 1
            stack = [i]
            while stack:
                node = stack.pop()
                if visited[node]:
                    continue
                visited[node] = True
                for nb in adj[node]:
                    if not visited[nb]:
                        stack.append(nb)
    return components


# ══════════════════════════════════════════════════════════════════════
#  Key handlers
# ══════════════════════════════════════════════════════════════════════

def _handle_myco_menu_key(self, key: int) -> bool:
    """Handle key input in the preset selection menu."""
    n = len(MYCO_PRESETS)
    if key == ord("q") or key == 27:
        self.myco_mode = False
        self.myco_menu = False
        return True
    if key == curses.KEY_UP or key == ord("k"):
        self.myco_menu_sel = (self.myco_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.myco_menu_sel = (self.myco_menu_sel + 1) % n
        return True
    if key in (10, 13, curses.KEY_ENTER):
        _myco_init(self, self.myco_menu_sel)
        return True
    return True


def _handle_myco_key(self, key: int) -> bool:
    """Handle key input during simulation."""
    if key == ord(" "):
        self.myco_running = not self.myco_running
        self._flash("Running" if self.myco_running else "Paused")
        return True

    if key == ord("n") or key == ord("."):
        _myco_step(self)
        return True

    if key == ord("v"):
        views = ["forest", "network", "graphs"]
        cur = views.index(self.myco_view) if self.myco_view in views else 0
        self.myco_view = views[(cur + 1) % len(views)]
        self._flash(f"View: {self.myco_view}")
        return True

    if key == ord("+") or key == ord("="):
        self.myco_speed = min(20, self.myco_speed + 1)
        self._flash(f"Speed: {self.myco_speed}x")
        return True

    if key == ord("-") or key == ord("_"):
        self.myco_speed = max(1, self.myco_speed - 1)
        self._flash(f"Speed: {self.myco_speed}x")
        return True

    if key == ord("r"):
        idx = next((i for i, p in enumerate(MYCO_PRESETS)
                     if p[0] == self.myco_preset_name), 0)
        _myco_init(self, idx)
        return True

    if key == ord("R") or key == ord("m"):
        self.myco_running = False
        self.myco_menu = True
        self.myco_menu_sel = 0
        return True

    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing — menu
# ══════════════════════════════════════════════════════════════════════

def _draw_myco_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    self.stdscr.erase()

    title = "── Mycorrhizal Network & Wood Wide Web ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2),
                           title[:max_x - 1],
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(MYCO_PRESETS):
        y = 4 + i * 3
        if y >= max_y - 6:
            break
        marker = "▸ " if i == self.myco_menu_sel else "  "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.myco_menu_sel
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

    hints = " [Up/Down] Navigate   [Enter] Select   [q/Esc] Back"
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

def _draw_myco(self, max_y: int, max_x: int):
    """Draw the active mycorrhizal network simulation."""
    self.stdscr.erase()

    # Title bar
    season_name = self.myco_season_names[self.myco_season]
    n_trees = len(self.myco_trees)
    n_hyphae = len(self.myco_hyphae)
    title = (f" Mycorrhizal: {self.myco_preset_name}"
             f" | t={self.myco_generation}"
             f" | {season_name}"
             f" | trees={n_trees} hyphae={n_hyphae}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass

    view = self.myco_view
    if view == "forest":
        _draw_myco_forest(self, max_y, max_x)
    elif view == "network":
        _draw_myco_network(self, max_y, max_x)
    elif view == "graphs":
        _draw_myco_graphs(self, max_y, max_x)

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
#  Drawing — forest view (split above/below ground)
# ══════════════════════════════════════════════════════════════════════

def _draw_myco_forest(self, max_y: int, max_x: int):
    """Split view: above-ground canopy over below-ground hyphal network."""
    trees = self.myco_trees
    hyphae = self.myco_hyphae
    particles = self.myco_particles
    rows = self.myco_rows
    cols = self.myco_cols

    view_h = max_y - 3
    view_w = max_x - 2
    # Split: top 40% = canopy, bottom 60% = underground
    split_y = max(3, int(view_h * 0.4))
    ground_y = split_y + 1  # row index in screen coords

    r_scale = max(1.0, rows / (view_h - split_y - 2))
    c_scale = max(1.0, cols / view_w)

    season = self.myco_season
    gen = self.myco_generation

    # ── Ground line ──
    ground_screen_y = ground_y
    if ground_screen_y < max_y - 1:
        ground_line = '─' * min(view_w, max_x - 2)
        try:
            self.stdscr.addstr(ground_screen_y, 1, ground_line[:max_x - 2],
                               curses.color_pair(3) | curses.A_DIM)
        except curses.error:
            pass

    # ── Above ground: canopy ──
    for t in trees:
        sx = int(t.c / c_scale) + 1
        # Tree trunk at ground line, canopy above
        trunk_y = ground_screen_y - 1
        if sx < 1 or sx >= max_x - 1:
            continue

        # Canopy (size determines how many rows of canopy)
        canopy_h = max(1, int(t.size * (split_y - 2)))
        canopy_w = max(1, int(t.size * 4))

        # Color based on species and season
        if t.species == SP_SEEDLING:
            canopy_ch = ','
            color = curses.color_pair(2)
        else:
            # Season-dependent canopy
            if season == 2 and t.species in (SP_OAK, SP_BIRCH, SP_MAPLE):
                # Autumn colors
                canopy_ch = random.choice(['*', '%', '#']) if t.size > 0.5 else '+'
                color = curses.color_pair(3) | curses.A_BOLD  # yellow/autumn
                if t.species == SP_MAPLE:
                    color = curses.color_pair(1) | curses.A_BOLD  # red
            elif season == 3 and t.species not in (SP_PINE, SP_FIR):
                # Winter: bare
                canopy_ch = '.'
                color = curses.color_pair(7) | curses.A_DIM
            else:
                canopy_ch = '#' if t.size > 0.6 else '+' if t.size > 0.3 else ','
                color = curses.color_pair(2) | curses.A_BOLD
                if t.species in (SP_PINE, SP_FIR):
                    color = curses.color_pair(2)

            # Pest indicator
            if t.pest_level > 0.3:
                color = curses.color_pair(1)
                canopy_ch = 'x'

            # Mother tree indicator
            if t.is_mother:
                color |= curses.A_BOLD

        # Draw canopy
        for dy in range(canopy_h):
            cy = trunk_y - 1 - dy
            if cy < 1 or cy >= max_y - 1:
                continue
            # Wider at bottom, narrower at top
            w = max(1, int(canopy_w * (1.0 - dy / max(1, canopy_h) * 0.6)))
            for dx in range(-w // 2, w // 2 + 1):
                cx = sx + dx
                if 1 <= cx < max_x - 1:
                    try:
                        self.stdscr.addstr(cy, cx, canopy_ch, color)
                    except curses.error:
                        pass

        # Trunk
        if 1 <= trunk_y < max_y - 1 and 1 <= sx < max_x - 1:
            trunk_ch = '|' if t.size > 0.3 else ':'
            try:
                self.stdscr.addstr(trunk_y, sx, trunk_ch,
                                   curses.color_pair(3))
            except curses.error:
                pass

        # Mother tree marker
        if t.is_mother and 1 <= trunk_y < max_y - 1:
            if sx - 1 >= 1:
                try:
                    self.stdscr.addstr(trunk_y, sx - 1, 'M',
                                       curses.color_pair(3) | curses.A_BOLD)
                except curses.error:
                    pass

    # ── Below ground: hyphal network ──
    underground_start = ground_y + 1
    underground_h = max_y - underground_start - 2

    # Draw soil background
    for yr in range(underground_start, min(max_y - 2, underground_start + underground_h)):
        for xc in range(1, min(max_x - 1, view_w + 1)):
            depth = (yr - underground_start) / max(1, underground_h)
            if random.random() < 0.03:
                try:
                    self.stdscr.addstr(yr, xc, '.',
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

    # Draw hyphae
    for hi, h in enumerate(hyphae):
        if h.tree_a >= len(trees) or h.tree_b >= len(trees):
            continue
        ta = trees[h.tree_a]
        tb = trees[h.tree_b]

        # Compute path in screen coords (underground)
        for node_r, node_c in h.nodes:
            # Map to underground screen space
            sy = underground_start + int((node_r / rows) * underground_h * 0.8)
            sx_pos = int(node_c / c_scale) + 1
            if underground_start <= sy < max_y - 2 and 1 <= sx_pos < max_x - 1:
                # Color by activity
                if h.signal_timer > 0 and h.signal_type == SIG_ALARM:
                    ch = '!'
                    color = curses.color_pair(1) | curses.A_BOLD
                elif abs(h.carbon_flow) > 0.01:
                    ch = '~'
                    color = curses.color_pair(2)
                elif abs(h.phosphorus_flow) > 0.01:
                    ch = '~'
                    color = curses.color_pair(5)
                elif h.thickness > 0.5:
                    ch = '='
                    color = curses.color_pair(7) | curses.A_DIM
                else:
                    ch = '-'
                    color = curses.color_pair(7) | curses.A_DIM

                # Pulse animation for active hyphae
                if h.signal_timer > 0 or abs(h.carbon_flow) > 0.01:
                    if (gen + hi) % 3 == 0:
                        color |= curses.A_BOLD

                try:
                    self.stdscr.addstr(sy, sx_pos, ch, color)
                except curses.error:
                    pass

    # Draw flowing particles
    for p in particles:
        if p.hypha_idx >= len(hyphae):
            continue
        h = hyphae[p.hypha_idx]
        if not h.nodes:
            continue
        # Interpolate position along path
        idx_f = p.progress * (len(h.nodes) - 1)
        idx = int(idx_f)
        idx = max(0, min(len(h.nodes) - 1, idx))
        node_r, node_c = h.nodes[idx]
        sy = underground_start + int((node_r / rows) * underground_h * 0.8)
        sx_pos = int(node_c / c_scale) + 1
        if underground_start <= sy < max_y - 2 and 1 <= sx_pos < max_x - 1:
            if p.kind == 'carbon':
                ch, color = 'C', curses.color_pair(2) | curses.A_BOLD
            elif p.kind == 'phosphorus':
                ch, color = 'P', curses.color_pair(5) | curses.A_BOLD
            elif p.kind == 'alarm':
                ch, color = '!', curses.color_pair(1) | curses.A_BOLD
            elif p.kind == 'water':
                ch, color = 'W', curses.color_pair(4) | curses.A_BOLD
            else:
                ch, color = '*', curses.color_pair(7)
            try:
                self.stdscr.addstr(sy, sx_pos, ch, color)
            except curses.error:
                pass

    # Draw root systems (tree positions underground)
    for t in trees:
        sx = int(t.c / c_scale) + 1
        root_y = underground_start + 1
        if underground_start <= root_y < max_y - 2 and 1 <= sx < max_x - 1:
            ch = 'V' if t.is_mother else 'v'
            color = curses.color_pair(3) | (curses.A_BOLD if t.is_mother else 0)
            try:
                self.stdscr.addstr(root_y, sx, ch, color)
            except curses.error:
                pass

    # ── Info bar ──
    info_y = max_y - 2
    fungal = self.myco_fungal_carbon_pool
    info = (f" trees={len(trees)} hyphae={len(hyphae)}"
            f" fungal_C={fungal:.2f}"
            f" season={self.myco_season_names[self.myco_season]}")
    if self.myco_drought:
        info += f" DROUGHT={int(self.myco_drought_intensity*100)}%"
    if self.myco_pest_active:
        pest_count = sum(1 for t in trees if t.pest_level > 0.1)
        info += f" PEST({pest_count})"
    try:
        self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — network topology view
# ══════════════════════════════════════════════════════════════════════

def _draw_myco_network(self, max_y: int, max_x: int):
    """Network topology diagram — nodes = trees, edges = hyphae."""
    trees = self.myco_trees
    hyphae = self.myco_hyphae
    rows = self.myco_rows
    cols = self.myco_cols
    gen = self.myco_generation

    view_h = max_y - 4
    view_w = max_x - 4

    r_scale = max(1.0, rows / view_h)
    c_scale = max(1.0, cols / (view_w - 2))

    # Draw edges first (underneath nodes)
    for hi, h in enumerate(hyphae):
        if h.tree_a >= len(trees) or h.tree_b >= len(trees):
            continue
        ta = trees[h.tree_a]
        tb = trees[h.tree_b]

        # Draw a line between the two trees using Bresenham-like approach
        y1 = int(ta.r / r_scale) + 2
        x1 = int(ta.c / c_scale) + 2
        y2 = int(tb.r / r_scale) + 2
        x2 = int(tb.c / c_scale) + 2

        # Edge character based on activity
        if h.signal_timer > 0 and h.signal_type == SIG_ALARM:
            edge_ch = '!'
            edge_color = curses.color_pair(1) | curses.A_BOLD
        elif abs(h.carbon_flow) > 0.01:
            edge_ch = '~'
            edge_color = curses.color_pair(2) | curses.A_BOLD
        elif abs(h.phosphorus_flow) > 0.01:
            edge_ch = '~'
            edge_color = curses.color_pair(5)
        elif h.thickness > 0.5:
            edge_ch = '-'
            edge_color = curses.color_pair(7)
        else:
            edge_ch = '.'
            edge_color = curses.color_pair(7) | curses.A_DIM

        # Simple line drawing
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for s in range(1, steps):
            t = s / steps
            py = int(y1 + (y2 - y1) * t)
            px = int(x1 + (x2 - x1) * t)
            if 2 <= py < max_y - 2 and 2 <= px < max_x - 2:
                try:
                    self.stdscr.addstr(py, px, edge_ch, edge_color)
                except curses.error:
                    pass

    # Draw nodes (trees)
    for ti, t in enumerate(trees):
        sy = int(t.r / r_scale) + 2
        sx = int(t.c / c_scale) + 2
        if sy < 2 or sy >= max_y - 2 or sx < 2 or sx >= max_x - 2:
            continue

        # Node appearance based on role and state
        if t.is_mother:
            ch = 'M'
            color = curses.color_pair(2) | curses.A_BOLD
        elif t.species == SP_SEEDLING:
            ch = 's'
            color = curses.color_pair(2) | curses.A_DIM
        else:
            ch = _SP_GLYPHS[t.species]
            color = curses.color_pair(_SP_COLORS[t.species])

        # Health-based dimming
        if t.health < 0.4:
            color = curses.color_pair(1)  # red for stressed
        elif t.pest_level > 0.3:
            color = curses.color_pair(1) | curses.A_BOLD
        elif t.defense_level > 0.3:
            color = curses.color_pair(4) | curses.A_BOLD  # blue = defending

        # Size indicator: draw label for important trees
        try:
            self.stdscr.addstr(sy, sx, ch, color)
        except curses.error:
            pass

        # Connection count below node for mothers
        if t.is_mother and sy + 1 < max_y - 2:
            n_conn = len(t.connected_hyphae)
            try:
                self.stdscr.addstr(sy + 1, sx, str(min(9, n_conn)),
                                   curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass

    # Legend
    legend_y = max_y - 3
    if legend_y > 3:
        legend = "M=Mother O=Oak B=Birch P=Pine F=Fir s=seedling  ~=flow !=alarm .=hypha"
        try:
            self.stdscr.addstr(legend_y, 2, legend[:max_x - 4],
                               curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass

    # Stats
    info_y = max_y - 2
    cc = self.myco_history['connected_components'][-1] if self.myco_history['connected_components'] else 0
    info = (f" Components={cc}"
            f" Edges={len(hyphae)}"
            f" Mothers={sum(1 for t in trees if t.is_mother)}"
            f" Seedlings={sum(1 for t in trees if t.species == SP_SEEDLING)}")
    try:
        self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — graphs view
# ══════════════════════════════════════════════════════════════════════

def _draw_myco_graphs(self, max_y: int, max_x: int):
    """Time-series sparkline graphs for key metrics."""
    hist = self.myco_history
    view_h = max_y - 3
    view_w = max_x - 4
    graph_w = min(200, view_w - 25)

    labels = [
        ("Carbon Flow", 'total_carbon_flow', 2),
        ("Phosphorus Flow", 'total_phosphorus_flow', 5),
        ("Alarm Signals", 'alarm_signals', 1),
        ("Network Edges", 'network_edges', 7),
        ("Avg Tree Health", 'avg_tree_health', 2),
        ("Mother Trees", 'mother_tree_count', 3),
        ("Seedlings", 'seedling_count', 2),
        ("Fungal Tax", 'fungal_tax', 3),
        ("Avg Defense", 'avg_defense', 4),
        ("Components", 'connected_components', 6),
    ]

    bars = "▁▂▃▄▅▆▇█"
    n_bars = len(bars)

    for gi, (label, key, cp) in enumerate(labels):
        base_y = 2 + gi * 2
        if base_y + 1 >= max_y - 2:
            break

        data = hist.get(key, [])
        # Label with current value
        cur_val = data[-1] if data else 0
        if isinstance(cur_val, float):
            lbl = f"{label}: {cur_val:.3f}"
        else:
            lbl = f"{label}: {cur_val}"
        try:
            self.stdscr.addstr(base_y, 2, lbl[:22],
                               curses.color_pair(cp) | curses.A_BOLD)
        except curses.error:
            pass

        # Sparkline
        if data:
            visible = data[-graph_w:]
            mn = min(visible)
            mx = max(visible)
            rng = mx - mn if mx > mn else 1.0
            color = curses.color_pair(cp)
            for i, v in enumerate(visible):
                x = 24 + i
                if x >= max_x - 1:
                    break
                idx = int((v - mn) / rng * (n_bars - 1))
                idx = max(0, min(n_bars - 1, idx))
                try:
                    self.stdscr.addstr(base_y, x, bars[idx], color)
                except curses.error:
                    pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register mycorrhizal network mode methods on the App class."""
    App.MYCO_PRESETS = MYCO_PRESETS
    App._enter_myco_mode = _enter_myco_mode
    App._exit_myco_mode = _exit_myco_mode
    App._myco_init = _myco_init
    App._myco_step = _myco_step
    App._handle_myco_menu_key = _handle_myco_menu_key
    App._handle_myco_key = _handle_myco_key
    App._draw_myco_menu = _draw_myco_menu
    App._draw_myco = _draw_myco
