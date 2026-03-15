"""Mode: ecosystem evolution & speciation — landscape-scale macro-evolution.

Populations evolve across varied biomes, speciate through geographic isolation
(allopatric) and niche divergence (sympatric), develop novel traits via
mutation/recombination, compete for ecological niches, form emergent food webs,
and go extinct under environmental pressure.

A real-time phylogenetic tree is rendered alongside the spatial map showing
species branching, radiation events, and mass extinctions.

Presets: Continental Drift, Island Archipelago, Adaptive Radiation,
Mass Extinction & Recovery, Pangaea Supercontinent, Random Landscape.
"""
import curses
import math
import random
import time

# ── Biome types ────────────────────────────────────────────────────
B_OCEAN = 0
B_GRASSLAND = 1
B_FOREST = 2
B_DESERT = 3
B_TUNDRA = 4
B_MOUNTAIN = 5
B_RIVER = 6
B_SWAMP = 7
B_REEF = 8
B_VOLCANIC = 9

BIOME_CHARS = {
    B_OCEAN: "~~", B_GRASSLAND: "::", B_FOREST: "TT", B_DESERT: "..",
    B_TUNDRA: "**", B_MOUNTAIN: "MM", B_RIVER: "==", B_SWAMP: "%%",
    B_REEF: "@@", B_VOLCANIC: "VV",
}

# Carrying capacity multiplier per biome
BIOME_CAPACITY = {
    B_OCEAN: 0.3, B_GRASSLAND: 1.0, B_FOREST: 0.8, B_DESERT: 0.15,
    B_TUNDRA: 0.2, B_MOUNTAIN: 0.1, B_RIVER: 1.2, B_SWAMP: 0.5,
    B_REEF: 0.6, B_VOLCANIC: 0.05,
}

# Movement cost (higher = harder to cross)
BIOME_MOVE_COST = {
    B_OCEAN: 5, B_GRASSLAND: 1, B_FOREST: 2, B_DESERT: 3,
    B_TUNDRA: 3, B_MOUNTAIN: 8, B_RIVER: 2, B_SWAMP: 3,
    B_REEF: 4, B_VOLCANIC: 10,
}

# ── Trophic levels ─────────────────────────────────────────────────
TROPHIC_PRODUCER = 0
TROPHIC_HERBIVORE = 1
TROPHIC_PREDATOR = 2
TROPHIC_APEX = 3

TROPHIC_NAMES = ["Producer", "Herbivore", "Predator", "Apex"]
TROPHIC_CHARS = ["♣ ", "♠ ", "♦ ", "♛ "]

# ── Trait definitions ──────────────────────────────────────────────
# Each trait is (name, min_val, max_val)
TRAIT_DEFS = [
    ("size", 0.1, 5.0),
    ("speed", 0.1, 3.0),
    ("camouflage", 0.0, 1.0),
    ("cold_tolerance", 0.0, 1.0),
    ("heat_tolerance", 0.0, 1.0),
    ("aquatic", 0.0, 1.0),
    ("aggression", 0.0, 1.0),
    ("fertility", 0.2, 3.0),
]

_NBRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NBRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
           (0, 1), (1, -1), (1, 0), (1, 1)]

# ── Species ID counter ─────────────────────────────────────────────
_next_species_id = 0


def _new_species_id():
    global _next_species_id
    _next_species_id += 1
    return _next_species_id


# ── Presets ─────────────────────────────────────────────────────────
EVOECO_PRESETS = [
    ("Continental Drift",
     "Two landmasses drift apart — allopatric speciation accelerates",
     {"land_pct": 0.55, "mountain_pct": 0.08, "forest_pct": 0.20,
      "desert_pct": 0.10, "river_count": 5, "swamp_pct": 0.05,
      "num_founders": 6, "mutation_rate": 0.04, "drift_event": True,
      "extinction_rate": 0.001, "climate_shift": 0.0}),

    ("Island Archipelago",
     "Scattered islands each become evolutionary labs — Darwin's finches writ large",
     {"land_pct": 0.25, "mountain_pct": 0.04, "forest_pct": 0.12,
      "desert_pct": 0.03, "river_count": 2, "swamp_pct": 0.02,
      "num_founders": 4, "mutation_rate": 0.06, "drift_event": False,
      "extinction_rate": 0.002, "climate_shift": 0.0}),

    ("Adaptive Radiation",
     "Single ancestral species colonizes an empty world — explosive diversification",
     {"land_pct": 0.50, "mountain_pct": 0.10, "forest_pct": 0.18,
      "desert_pct": 0.08, "river_count": 6, "swamp_pct": 0.04,
      "num_founders": 1, "mutation_rate": 0.08, "drift_event": False,
      "extinction_rate": 0.0005, "climate_shift": 0.0}),

    ("Mass Extinction & Recovery",
     "Rich ecosystem hit by cataclysm — survivors radiate into empty niches",
     {"land_pct": 0.50, "mountain_pct": 0.07, "forest_pct": 0.22,
      "desert_pct": 0.06, "river_count": 5, "swamp_pct": 0.04,
      "num_founders": 10, "mutation_rate": 0.05, "drift_event": False,
      "extinction_rate": 0.001, "climate_shift": 0.0,
      "mass_extinction_gen": 150}),

    ("Pangaea Supercontinent",
     "One vast landmass — species spread freely, competition fierce",
     {"land_pct": 0.70, "mountain_pct": 0.06, "forest_pct": 0.25,
      "desert_pct": 0.12, "river_count": 8, "swamp_pct": 0.06,
      "num_founders": 8, "mutation_rate": 0.03, "drift_event": False,
      "extinction_rate": 0.001, "climate_shift": 0.0}),

    ("Random Landscape",
     "Fully randomized terrain, species, and evolutionary parameters",
     {"land_pct": None, "mountain_pct": None, "forest_pct": None,
      "desert_pct": None, "river_count": None, "swamp_pct": None,
      "num_founders": None, "mutation_rate": None, "drift_event": None,
      "extinction_rate": None, "climate_shift": None}),
]


# ── Terrain generation ─────────────────────────────────────────────

def _evo_heightmap(rows, cols, octaves=5):
    """Value-noise heightmap."""
    hmap = [[random.random() for _ in range(cols)] for _ in range(rows)]
    for _oct in range(octaves):
        smoothed = [[0.0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                total = hmap[r][c]
                count = 1
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        total += hmap[nr][nc]
                        count += 1
                smoothed[r][c] = total / count
        hmap = smoothed
    lo = min(min(row) for row in hmap)
    hi = max(max(row) for row in hmap)
    rng = hi - lo if hi > lo else 1.0
    for r in range(rows):
        for c in range(cols):
            hmap[r][c] = (hmap[r][c] - lo) / rng
    return hmap


def _evo_gen_terrain(rows, cols, settings):
    """Generate biome grid from heightmap + settings."""
    hmap = _evo_heightmap(rows, cols)
    water_thresh = 1.0 - settings["land_pct"]
    mtn_thresh = 1.0 - settings["mountain_pct"]
    grid = [[B_OCEAN] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            h = hmap[r][c]
            if h < water_thresh:
                # Ocean or reef (shallow coast)
                if h > water_thresh - 0.04:
                    grid[r][c] = B_REEF
                else:
                    grid[r][c] = B_OCEAN
            elif h >= mtn_thresh:
                grid[r][c] = B_MOUNTAIN
            else:
                grid[r][c] = B_GRASSLAND

    # Forests (mid-latitude)
    for r in range(rows):
        lat = abs(r / max(1, rows - 1) - 0.5) * 2
        for c in range(cols):
            if grid[r][c] == B_GRASSLAND:
                if lat < 0.6 and random.random() < settings["forest_pct"] * 1.5:
                    grid[r][c] = B_FOREST
                elif lat > 0.75:
                    grid[r][c] = B_TUNDRA

    # Desert near equator
    for r in range(rows):
        lat = abs(r / max(1, rows - 1) - 0.5) * 2
        for c in range(cols):
            if grid[r][c] == B_GRASSLAND and lat < 0.3:
                if random.random() < settings["desert_pct"] * 3:
                    grid[r][c] = B_DESERT

    # Swamps near rivers / low ground
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == B_GRASSLAND and random.random() < settings["swamp_pct"]:
                grid[r][c] = B_SWAMP

    # Rivers
    for _ in range(settings["river_count"]):
        mtns = [(r, c) for r in range(rows) for c in range(cols)
                if grid[r][c] == B_MOUNTAIN]
        if not mtns:
            break
        cr, cc = random.choice(mtns)
        for _step in range(rows + cols):
            if grid[cr][cc] == B_OCEAN:
                break
            if grid[cr][cc] not in (B_MOUNTAIN, B_RIVER):
                grid[cr][cc] = B_RIVER
            best_h, best_pos = hmap[cr][cc], None
            for dr, dc in _NBRS4:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if hmap[nr][nc] < best_h:
                        best_h = hmap[nr][nc]
                        best_pos = (nr, nc)
            if best_pos is None:
                dr, dc = random.choice(_NBRS4)
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    best_pos = (nr, nc)
                else:
                    break
            cr, cc = best_pos

    # Volcanic hotspots
    num_volcanoes = max(1, int(rows * cols * 0.001))
    for _ in range(num_volcanoes):
        vr = random.randint(0, rows - 1)
        vc = random.randint(0, cols - 1)
        if grid[vr][vc] in (B_MOUNTAIN,):
            grid[vr][vc] = B_VOLCANIC

    return grid, hmap


# ── Species & Population ───────────────────────────────────────────

def _make_species(parent_id, trophic, traits, name_prefix="Sp"):
    """Create a new species dict."""
    sid = _new_species_id()
    return {
        "id": sid,
        "parent_id": parent_id,
        "name": f"{name_prefix}-{sid}",
        "trophic": trophic,
        "traits": dict(traits),  # {trait_name: value}
        "color_idx": (sid % 6) + 1,
        "born_gen": 0,
        "extinct_gen": -1,
        "alive": True,
        "peak_pop": 0,
        "total_pop": 0,
        "niche_biomes": set(),  # biomes this species thrives in
    }


def _make_population(species_id, r, c, size):
    """A local population of a species at a grid cell."""
    return {
        "species_id": species_id,
        "r": r, "c": c,
        "size": size,
        "fitness": 1.0,
        "genetic_drift": random.uniform(-0.02, 0.02),
    }


def _random_traits(trophic):
    """Generate random traits appropriate for a trophic level."""
    traits = {}
    for tname, tmin, tmax in TRAIT_DEFS:
        traits[tname] = random.uniform(tmin, tmax)
    # Bias by trophic level
    if trophic == TROPHIC_PRODUCER:
        traits["speed"] = random.uniform(0.0, 0.2)
        traits["aggression"] = 0.0
        traits["size"] = random.uniform(0.1, 1.0)
        traits["fertility"] = random.uniform(1.5, 3.0)
    elif trophic == TROPHIC_HERBIVORE:
        traits["aggression"] = random.uniform(0.0, 0.3)
        traits["fertility"] = random.uniform(0.8, 2.0)
    elif trophic == TROPHIC_PREDATOR:
        traits["aggression"] = random.uniform(0.4, 0.8)
        traits["speed"] = random.uniform(1.0, 2.5)
        traits["fertility"] = random.uniform(0.3, 1.0)
    elif trophic == TROPHIC_APEX:
        traits["aggression"] = random.uniform(0.7, 1.0)
        traits["size"] = random.uniform(2.5, 5.0)
        traits["speed"] = random.uniform(1.5, 3.0)
        traits["fertility"] = random.uniform(0.2, 0.6)
    return traits


def _mutate_traits(traits, mutation_rate):
    """Mutate trait values."""
    new_traits = dict(traits)
    for tname, tmin, tmax in TRAIT_DEFS:
        if random.random() < mutation_rate:
            delta = random.gauss(0, (tmax - tmin) * 0.1)
            new_traits[tname] = max(tmin, min(tmax, new_traits[tname] + delta))
    return new_traits


def _trait_distance(t1, t2):
    """Euclidean distance in normalized trait space."""
    dist_sq = 0.0
    for tname, tmin, tmax in TRAIT_DEFS:
        rng = tmax - tmin if tmax > tmin else 1.0
        d = (t1.get(tname, 0) - t2.get(tname, 0)) / rng
        dist_sq += d * d
    return math.sqrt(dist_sq)


def _fitness_in_biome(species, biome):
    """Calculate fitness of a species in a given biome."""
    traits = species["traits"]
    fit = 1.0

    # Aquatic fitness
    if biome in (B_OCEAN, B_REEF):
        fit *= 0.2 + 0.8 * traits["aquatic"]
    elif biome == B_RIVER:
        fit *= 0.6 + 0.4 * traits["aquatic"]
    elif biome == B_SWAMP:
        fit *= 0.5 + 0.5 * traits["aquatic"]
    else:
        fit *= 1.0 - 0.3 * traits["aquatic"]

    # Temperature adaptation
    if biome == B_TUNDRA:
        fit *= 0.3 + 0.7 * traits["cold_tolerance"]
    elif biome == B_DESERT:
        fit *= 0.3 + 0.7 * traits["heat_tolerance"]
    elif biome == B_VOLCANIC:
        fit *= 0.1 + 0.3 * traits["heat_tolerance"]

    # Mountain penalty for large, slow species
    if biome == B_MOUNTAIN:
        fit *= max(0.1, 1.0 - traits["size"] * 0.15)

    # Producers benefit from sunlight (grassland, forest)
    if species["trophic"] == TROPHIC_PRODUCER:
        if biome in (B_GRASSLAND, B_FOREST, B_SWAMP):
            fit *= 1.3
        elif biome in (B_OCEAN, B_REEF):
            fit *= 0.8

    return max(0.01, fit)


# ── Phylogenetic tree node ─────────────────────────────────────────

def _make_phylo_node(species_id, parent_id, born_gen, name, trophic):
    """Create a phylogenetic tree node."""
    return {
        "species_id": species_id,
        "parent_id": parent_id,
        "born_gen": born_gen,
        "extinct_gen": -1,
        "name": name,
        "trophic": trophic,
        "children": [],
    }


# ══════════════════════════════════════════════════════════════════════
#  Core mode functions
# ══════════════════════════════════════════════════════════════════════

def _enter_evoeco_mode(self):
    """Enter Ecosystem Evolution mode — show preset menu."""
    self.evoeco_menu = True
    self.evoeco_menu_sel = 0
    self._flash("Ecosystem Evolution & Speciation — select a scenario")


def _exit_evoeco_mode(self):
    """Exit Ecosystem Evolution mode."""
    self.evoeco_mode = False
    self.evoeco_menu = False
    self.evoeco_running = False
    self.evoeco_biome = []
    self.evoeco_species = []
    self.evoeco_pops = []
    self.evoeco_phylo = []
    self.evoeco_log = []
    self._flash("Ecosystem Evolution mode OFF")


def _evoeco_init(self, preset_idx):
    """Initialize the ecosystem evolution simulation."""
    global _next_species_id
    _next_species_id = 0

    name, _desc, settings = self.EVOECO_PRESETS[preset_idx]
    settings = dict(settings)

    # Randomize if needed
    if settings["land_pct"] is None:
        settings["land_pct"] = random.uniform(0.25, 0.70)
        settings["mountain_pct"] = random.uniform(0.03, 0.12)
        settings["forest_pct"] = random.uniform(0.08, 0.25)
        settings["desert_pct"] = random.uniform(0.02, 0.15)
        settings["river_count"] = random.randint(2, 8)
        settings["swamp_pct"] = random.uniform(0.02, 0.08)
        settings["num_founders"] = random.randint(2, 10)
        settings["mutation_rate"] = random.uniform(0.02, 0.08)
        settings["drift_event"] = random.choice([True, False])
        settings["extinction_rate"] = random.uniform(0.0005, 0.003)
        settings["climate_shift"] = random.uniform(0.0, 0.01)

    max_y, max_x = self.stdscr.getmaxyx()
    # Reserve right panel for phylogenetic tree
    map_cols = max(30, (max_x - 1) // 2 - 20)
    rows = max(25, max_y - 4)
    cols = max(30, map_cols)

    self.evoeco_rows = rows
    self.evoeco_cols = cols
    self.evoeco_preset_name = name
    self.evoeco_preset_idx = preset_idx
    self.evoeco_generation = 0
    self.evoeco_steps_per_frame = 1
    self.evoeco_settings = settings
    self.evoeco_view = "species"  # species / biome / fitness / foodweb

    # Generate terrain
    biome, hmap = _evo_gen_terrain(rows, cols, settings)
    self.evoeco_biome = biome
    self.evoeco_hmap = hmap

    # Climate temperature map (varies by latitude and altitude)
    self.evoeco_temp = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        lat = abs(r / max(1, rows - 1) - 0.5) * 2  # 0=equator, 1=pole
        for c in range(cols):
            base_temp = 1.0 - lat * 0.8  # warm at equator
            alt_penalty = hmap[r][c] * 0.3
            self.evoeco_temp[r][c] = max(0.0, min(1.0, base_temp - alt_penalty))

    # Species list
    self.evoeco_species = []
    # Populations: list of population dicts
    self.evoeco_pops = []
    # Phylogenetic tree nodes
    self.evoeco_phylo = []
    # Population grid: species_id at each cell (-1 = empty), for fast lookup
    self.evoeco_pop_grid = [[-1] * cols for _ in range(rows)]
    # Pop size grid
    self.evoeco_pop_size = [[0] * cols for _ in range(rows)]
    # Event log
    self.evoeco_log = []
    # Mass extinction tracking
    self.evoeco_mass_extinction_gen = settings.get("mass_extinction_gen", -1)
    self.evoeco_mass_extinction_done = False

    # Speciation counter for stats
    self.evoeco_speciation_events = 0
    self.evoeco_extinction_events = 0
    self.evoeco_radiation_events = 0

    # Pop history for graph
    self.evoeco_pop_history = []  # list of (gen, num_species, total_pop)

    # Food web edges: (predator_species_id, prey_species_id)
    self.evoeco_food_web = set()

    # Place founder species
    habitable = [(r, c) for r in range(rows) for c in range(cols)
                 if biome[r][c] not in (B_OCEAN, B_VOLCANIC, B_MOUNTAIN)]
    random.shuffle(habitable)

    trophic_distribution = [TROPHIC_PRODUCER, TROPHIC_PRODUCER,
                            TROPHIC_HERBIVORE, TROPHIC_HERBIVORE,
                            TROPHIC_PREDATOR, TROPHIC_APEX]

    placed = 0
    min_dist = max(4, min(rows, cols) // (settings["num_founders"] + 1))
    used = []

    for idx in range(settings["num_founders"]):
        trophic = trophic_distribution[idx % len(trophic_distribution)]
        traits = _random_traits(trophic)
        sp = _make_species(0, trophic, traits)
        sp["born_gen"] = 0
        self.evoeco_species.append(sp)

        # Phylo node
        node = _make_phylo_node(sp["id"], 0, 0, sp["name"], trophic)
        self.evoeco_phylo.append(node)

        # Place populations
        for r, c in habitable:
            if placed > 200:
                break
            too_close = any(abs(r - ur) + abs(c - uc) < min_dist
                           for ur, uc in used)
            if too_close:
                continue

            pop = _make_population(sp["id"], r, c, random.randint(5, 20))
            self.evoeco_pops.append(pop)
            self.evoeco_pop_grid[r][c] = sp["id"]
            self.evoeco_pop_size[r][c] = pop["size"]
            used.append((r, c))
            sp["total_pop"] += pop["size"]
            sp["niche_biomes"].add(biome[r][c])
            placed += 1
            break

    # Build initial food web
    _rebuild_food_web(self)

    # Stats
    self.evoeco_stats = {
        "num_species": len(self.evoeco_species),
        "total_pop": sum(p["size"] for p in self.evoeco_pops),
        "speciations": 0,
        "extinctions": 0,
        "mass_extinctions": 0,
    }

    self.evoeco_menu = False
    self.evoeco_mode = True
    self.evoeco_running = False
    self._flash(f"Ecosystem Evolution: {name} — {len(self.evoeco_species)} founder species")


def _rebuild_food_web(self):
    """Build food web edges based on trophic levels and trait compatibility."""
    self.evoeco_food_web.clear()
    alive_species = [s for s in self.evoeco_species if s["alive"]]
    for pred in alive_species:
        if pred["trophic"] == TROPHIC_PRODUCER:
            continue
        for prey in alive_species:
            if prey["trophic"] >= pred["trophic"]:
                continue
            # Size ratio check: predator should be bigger
            if pred["traits"]["size"] > prey["traits"]["size"] * 0.5:
                # Speed check: predator should be fast enough
                if pred["traits"]["speed"] > prey["traits"]["speed"] * 0.4:
                    self.evoeco_food_web.add((pred["id"], prey["id"]))


def _evoeco_step(self):
    """Advance the ecosystem by one generation."""
    species_list = self.evoeco_species
    pops = self.evoeco_pops
    biome = self.evoeco_biome
    pop_grid = self.evoeco_pop_grid
    pop_size = self.evoeco_pop_size
    rows, cols = self.evoeco_rows, self.evoeco_cols
    gen = self.evoeco_generation
    settings = self.evoeco_settings

    alive_species = {s["id"]: s for s in species_list if s["alive"]}
    if not alive_species:
        self.evoeco_running = False
        return

    # ── Mass extinction event ──
    if (self.evoeco_mass_extinction_gen > 0
            and gen == self.evoeco_mass_extinction_gen
            and not self.evoeco_mass_extinction_done):
        self.evoeco_mass_extinction_done = True
        # Kill 70% of populations
        kill_count = 0
        for pop in pops:
            if random.random() < 0.70:
                pop["size"] = 0
                kill_count += 1
        self.evoeco_log.append(f"Gen {gen}: *** MASS EXTINCTION — 70% of populations wiped out ***")
        self.evoeco_stats["mass_extinctions"] += 1
        # Increase mutation rate temporarily
        settings["mutation_rate"] = min(0.15, settings["mutation_rate"] * 2.5)

    # ── Continental drift (barrier formation) ──
    if settings.get("drift_event") and gen == 80:
        mid_c = cols // 2
        for r in range(rows):
            if biome[r][mid_c] not in (B_OCEAN,):
                biome[r][mid_c] = B_OCEAN
            if mid_c + 1 < cols and biome[r][mid_c + 1] not in (B_OCEAN,):
                biome[r][mid_c + 1] = B_OCEAN
        self.evoeco_log.append(f"Gen {gen}: Continental drift — ocean barrier forms!")

    # ── Climate shift ──
    if settings["climate_shift"] > 0 and gen % 50 == 0 and gen > 0:
        shift = settings["climate_shift"]
        for r in range(rows):
            for c in range(cols):
                self.evoeco_temp[r][c] = max(0, min(1,
                    self.evoeco_temp[r][c] + random.uniform(-shift, shift)))
        self.evoeco_log.append(f"Gen {gen}: Climate shift event")

    # ── Population dynamics ──
    new_pops = []
    species_pop_count = {}  # species_id -> total pop

    # Clear grid for rebuild
    for r in range(rows):
        for c in range(cols):
            pop_grid[r][c] = -1
            pop_size[r][c] = 0

    random.shuffle(pops)

    for pop in pops:
        if pop["size"] <= 0:
            continue
        sid = pop["species_id"]
        if sid not in alive_species:
            continue

        sp = alive_species[sid]
        r, c = pop["r"], pop["c"]
        if r < 0 or r >= rows or c < 0 or c >= cols:
            continue
        b = biome[r][c]

        # Fitness
        fit = _fitness_in_biome(sp, b)

        # Food availability
        if sp["trophic"] == TROPHIC_PRODUCER:
            # Producers grow based on biome capacity
            food_avail = BIOME_CAPACITY.get(b, 0.5) * fit
        else:
            # Consumers need prey nearby
            food_avail = 0.0
            for dr, dc in _NBRS8:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    prey_sid = pop_grid[nr][nc]
                    if prey_sid >= 0 and (sid, prey_sid) in self.evoeco_food_web:
                        food_avail += pop_size[nr][nc] * 0.1
            # Also check current cell
            if pop_grid[r][c] >= 0 and pop_grid[r][c] != sid:
                prey_sid = pop_grid[r][c]
                if (sid, prey_sid) in self.evoeco_food_web:
                    food_avail += pop_size[r][c] * 0.15

        # Growth / decline
        capacity = max(1, int(BIOME_CAPACITY.get(b, 0.5) * 30 * fit))
        fertility = sp["traits"]["fertility"]
        growth_rate = fertility * food_avail * fit * 0.3

        if pop["size"] < capacity:
            new_size = pop["size"] + max(0, int(growth_rate))
        else:
            # Over capacity — decline
            new_size = pop["size"] - max(1, int(pop["size"] * 0.1))

        # Random extinction pressure
        if random.random() < settings["extinction_rate"]:
            new_size = int(new_size * 0.5)

        # Competition with other species at same cell
        if pop_grid[r][c] >= 0 and pop_grid[r][c] != sid:
            other_sid = pop_grid[r][c]
            if other_sid in alive_species:
                other_sp = alive_species[other_sid]
                if other_sp["trophic"] == sp["trophic"]:
                    # Direct competition
                    my_str = sp["traits"]["size"] * fit
                    oth_str = other_sp["traits"]["size"] * _fitness_in_biome(other_sp, b)
                    if my_str < oth_str:
                        new_size = int(new_size * 0.7)

        new_size = max(0, min(capacity * 2, new_size))
        pop["size"] = new_size
        pop["fitness"] = fit

        if new_size > 0:
            new_pops.append(pop)
            pop_grid[r][c] = sid
            pop_size[r][c] = new_size
            species_pop_count[sid] = species_pop_count.get(sid, 0) + new_size

    self.evoeco_pops = new_pops

    # ── Dispersal / Migration ──
    dispersal_pops = []
    for pop in self.evoeco_pops:
        if pop["size"] < 3:
            continue
        sid = pop["species_id"]
        if sid not in alive_species:
            continue
        sp = alive_species[sid]
        if random.random() > sp["traits"]["speed"] * 0.15:
            continue

        r, c = pop["r"], pop["c"]
        # Try to spread to adjacent cell
        dirs = list(_NBRS4)
        random.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                b = biome[nr][nc]
                move_cost = BIOME_MOVE_COST.get(b, 5)
                if sp["traits"]["speed"] < move_cost * 0.3:
                    continue
                if pop_grid[nr][nc] == -1:
                    migrants = max(1, pop["size"] // 5)
                    pop["size"] -= migrants
                    new_pop = _make_population(sid, nr, nc, migrants)
                    dispersal_pops.append(new_pop)
                    pop_grid[nr][nc] = sid
                    pop_size[nr][nc] = migrants
                    break

    self.evoeco_pops.extend(dispersal_pops)

    # ── Speciation ──
    # Check for allopatric speciation (isolated populations diverge)
    species_positions = {}
    for pop in self.evoeco_pops:
        if pop["size"] <= 0:
            continue
        sid = pop["species_id"]
        if sid not in species_positions:
            species_positions[sid] = []
        species_positions[sid].append(pop)

    for sid, sp_pops in species_positions.items():
        if sid not in alive_species:
            continue
        if len(sp_pops) < 2:
            continue
        sp = alive_species[sid]

        # Check for geographic clusters far enough apart
        if len(sp_pops) >= 4 and random.random() < settings["mutation_rate"] * 0.5:
            # Find two most distant populations
            max_dist = 0
            pop_a, pop_b = sp_pops[0], sp_pops[1]
            sample = random.sample(sp_pops, min(10, len(sp_pops)))
            for i in range(len(sample)):
                for j in range(i + 1, len(sample)):
                    d = abs(sample[i]["r"] - sample[j]["r"]) + abs(sample[i]["c"] - sample[j]["c"])
                    if d > max_dist:
                        max_dist = d
                        pop_a, pop_b = sample[i], sample[j]

            # Allopatric speciation if distance is large enough
            min_spec_dist = max(8, min(rows, cols) // 5)
            if max_dist > min_spec_dist:
                # The distant population becomes a new species
                new_traits = _mutate_traits(sp["traits"], settings["mutation_rate"] * 3)
                new_sp = _make_species(sp["id"], sp["trophic"], new_traits)
                new_sp["born_gen"] = gen
                self.evoeco_species.append(new_sp)
                alive_species[new_sp["id"]] = new_sp

                # Phylo node
                node = _make_phylo_node(new_sp["id"], sp["id"], gen, new_sp["name"], new_sp["trophic"])
                self.evoeco_phylo.append(node)
                # Link to parent
                for pn in self.evoeco_phylo:
                    if pn["species_id"] == sp["id"]:
                        pn["children"].append(new_sp["id"])
                        break

                # Convert distant populations
                mid_r = (pop_a["r"] + pop_b["r"]) // 2
                mid_c = (pop_a["c"] + pop_b["c"]) // 2
                converted = 0
                for p in sp_pops:
                    dist_to_b = abs(p["r"] - pop_b["r"]) + abs(p["c"] - pop_b["c"])
                    dist_to_a = abs(p["r"] - pop_a["r"]) + abs(p["c"] - pop_a["c"])
                    if dist_to_b < dist_to_a:
                        p["species_id"] = new_sp["id"]
                        pop_grid[p["r"]][p["c"]] = new_sp["id"]
                        converted += 1

                self.evoeco_log.append(
                    f"Gen {gen}: Allopatric speciation! {sp['name']} → {new_sp['name']} ({converted} pops)")
                self.evoeco_speciation_events += 1
                self.evoeco_stats["speciations"] += 1

        # Sympatric speciation (niche divergence)
        if len(sp_pops) >= 3 and random.random() < settings["mutation_rate"] * 0.2:
            # Different biomes occupied → niche divergence
            biomes_occupied = set()
            for p in sp_pops:
                biomes_occupied.add(biome[p["r"]][p["c"]])
            if len(biomes_occupied) >= 3:
                new_traits = _mutate_traits(sp["traits"], settings["mutation_rate"] * 4)
                # Shift trophic level occasionally
                new_trophic = sp["trophic"]
                if random.random() < 0.15:
                    new_trophic = min(TROPHIC_APEX, sp["trophic"] + 1)
                    new_traits["aggression"] = min(1.0, new_traits["aggression"] + 0.2)
                    new_traits["size"] = min(5.0, new_traits["size"] * 1.3)

                new_sp = _make_species(sp["id"], new_trophic, new_traits)
                new_sp["born_gen"] = gen
                self.evoeco_species.append(new_sp)
                alive_species[new_sp["id"]] = new_sp

                node = _make_phylo_node(new_sp["id"], sp["id"], gen, new_sp["name"], new_sp["trophic"])
                self.evoeco_phylo.append(node)
                for pn in self.evoeco_phylo:
                    if pn["species_id"] == sp["id"]:
                        pn["children"].append(new_sp["id"])
                        break

                # Convert some populations in specialized biomes
                target_biome = random.choice(list(biomes_occupied))
                converted = 0
                for p in sp_pops:
                    if biome[p["r"]][p["c"]] == target_biome and random.random() < 0.5:
                        p["species_id"] = new_sp["id"]
                        pop_grid[p["r"]][p["c"]] = new_sp["id"]
                        converted += 1

                label = "Sympatric" if new_trophic == sp["trophic"] else "Trophic shift"
                self.evoeco_log.append(
                    f"Gen {gen}: {label} speciation! {sp['name']} → {new_sp['name']}")
                self.evoeco_speciation_events += 1
                self.evoeco_stats["speciations"] += 1

    # ── Extinction check ──
    for sp in species_list:
        if not sp["alive"]:
            continue
        total = sum(p["size"] for p in self.evoeco_pops if p["species_id"] == sp["id"])
        sp["total_pop"] = total
        sp["peak_pop"] = max(sp["peak_pop"], total)
        if total == 0:
            sp["alive"] = False
            sp["extinct_gen"] = gen
            for pn in self.evoeco_phylo:
                if pn["species_id"] == sp["id"]:
                    pn["extinct_gen"] = gen
                    break
            self.evoeco_log.append(f"Gen {gen}: {sp['name']} ({TROPHIC_NAMES[sp['trophic']]}) went extinct")
            self.evoeco_extinction_events += 1
            self.evoeco_stats["extinctions"] += 1

    # ── Update niche biomes ──
    for sp in species_list:
        if not sp["alive"]:
            continue
        sp["niche_biomes"] = set()
        for p in self.evoeco_pops:
            if p["species_id"] == sp["id"] and p["size"] > 0:
                sp["niche_biomes"].add(biome[p["r"]][p["c"]])

    # ── Rebuild food web periodically ──
    if gen % 10 == 0:
        _rebuild_food_web(self)

    # ── Adaptive radiation detection ──
    alive_count = sum(1 for s in species_list if s["alive"])
    if len(self.evoeco_pop_history) > 0:
        prev_count = self.evoeco_pop_history[-1][1]
        if alive_count > prev_count * 1.5 and alive_count - prev_count >= 3:
            self.evoeco_log.append(f"Gen {gen}: *** Adaptive radiation! Species count surged to {alive_count} ***")
            self.evoeco_radiation_events += 1

    # Track history
    total_pop = sum(p["size"] for p in self.evoeco_pops)
    self.evoeco_pop_history.append((gen, alive_count, total_pop))
    if len(self.evoeco_pop_history) > 500:
        self.evoeco_pop_history = self.evoeco_pop_history[-300:]

    # Update stats
    self.evoeco_stats["num_species"] = alive_count
    self.evoeco_stats["total_pop"] = total_pop

    self.evoeco_generation += 1

    # Trim log
    if len(self.evoeco_log) > 200:
        self.evoeco_log = self.evoeco_log[-100:]


# ── Menu & key handling ────────────────────────────────────────────

def _handle_evoeco_menu_key(self, key):
    """Handle input on the preset selection menu."""
    if key == -1:
        return True
    n = len(self.EVOECO_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.evoeco_menu_sel = (self.evoeco_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.evoeco_menu_sel = (self.evoeco_menu_sel + 1) % n
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._evoeco_init(self.evoeco_menu_sel)
        return True
    if key == 27:  # Esc
        self.evoeco_menu = False
        self._flash("Ecosystem Evolution mode cancelled")
        return True
    return True


def _handle_evoeco_key(self, key):
    """Handle input during the running simulation."""
    if key == -1:
        return True
    if key == ord(" "):
        self.evoeco_running = not self.evoeco_running
        return True
    if key == ord("n"):
        self._evoeco_step()
        return True
    if key == ord("v"):
        views = ["species", "biome", "fitness", "foodweb"]
        idx = views.index(self.evoeco_view) if self.evoeco_view in views else 0
        self.evoeco_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.evoeco_view}")
        return True
    if key == ord("+") or key == ord("="):
        self.evoeco_steps_per_frame = min(20, self.evoeco_steps_per_frame + 1)
        self._flash(f"Speed: {self.evoeco_steps_per_frame}x")
        return True
    if key == ord("-"):
        self.evoeco_steps_per_frame = max(1, self.evoeco_steps_per_frame - 1)
        self._flash(f"Speed: {self.evoeco_steps_per_frame}x")
        return True
    if key == ord("l"):
        self.evoeco_show_log = not getattr(self, "evoeco_show_log", False)
        return True
    if key == ord("t"):
        # Toggle phylogenetic tree panel
        self.evoeco_show_tree = not getattr(self, "evoeco_show_tree", True)
        self._flash(f"Phylo tree: {'ON' if self.evoeco_show_tree else 'OFF'}")
        return True
    if key == ord("r"):
        self._evoeco_init(self.evoeco_preset_idx)
        return True
    if key == ord("R"):
        self.evoeco_menu = True
        self.evoeco_mode = False
        self.evoeco_running = False
        return True
    if key == ord("q") or key == 27:
        self._exit_evoeco_mode()
        return True
    from life.constants import SPEEDS
    if key == ord("["):
        self.speed_idx = max(0, self.speed_idx - 1)
        return True
    if key == ord("]"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
        return True
    return True


# ── Drawing ────────────────────────────────────────────────────────

def _draw_evoeco_menu(self, max_y, max_x):
    """Draw the preset selection menu."""
    self.stdscr.erase()
    title = "╔══ Ecosystem Evolution & Speciation ══╗"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Select an evolutionary scenario:"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    y = 5
    for i, (pname, desc, _settings) in enumerate(self.EVOECO_PRESETS):
        if y + 2 >= max_y:
            break
        marker = "▶ " if i == self.evoeco_menu_sel else "  "
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.evoeco_menu_sel else curses.color_pair(6)
        try:
            self.stdscr.addstr(y, 4, f"{marker}{pname}", attr)
            self.stdscr.addstr(y + 1, 8, desc[:max_x - 10],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass
        y += 3

    hint = " [↑↓]=select [Enter]=start [Esc]=cancel"
    if max_y - 1 > 0:
        try:
            self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_evoeco(self, max_y, max_x):
    """Draw the main ecosystem evolution view with phylogenetic tree."""
    self.stdscr.erase()
    biome_grid = self.evoeco_biome
    pop_grid = self.evoeco_pop_grid
    pop_size_grid = self.evoeco_pop_size
    species_list = self.evoeco_species
    rows, cols = self.evoeco_rows, self.evoeco_cols
    view = self.evoeco_view
    show_log = getattr(self, "evoeco_show_log", False)
    show_tree = getattr(self, "evoeco_show_tree", True)

    # Species lookup
    sp_by_id = {s["id"]: s for s in species_list}

    # Layout: map on left, phylo tree / sidebar on right
    tree_width = 35 if show_tree and max_x > 80 else 0
    map_char_width = max_x - tree_width - 1
    draw_cols = min(cols, map_char_width // 2)
    draw_rows = min(rows, max_y - 4)

    # Header
    alive = sum(1 for s in species_list if s["alive"])
    total_pop = self.evoeco_stats.get("total_pop", 0)
    header = (f" Gen {self.evoeco_generation}  |  {alive} species  |  "
              f"Pop {total_pop}  |  View: {view}  |  "
              f"{'▶ RUN' if self.evoeco_running else '⏸ PAUSE'}  |  "
              f"{self.evoeco_preset_name}")
    try:
        self.stdscr.addstr(0, 0, header[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Biome colors
    biome_colors = {
        B_OCEAN: curses.color_pair(4),
        B_GRASSLAND: curses.color_pair(2),
        B_FOREST: curses.color_pair(1),
        B_DESERT: curses.color_pair(2) | curses.A_DIM,
        B_TUNDRA: curses.color_pair(7),
        B_MOUNTAIN: curses.color_pair(7) | curses.A_BOLD,
        B_RIVER: curses.color_pair(4) | curses.A_BOLD,
        B_SWAMP: curses.color_pair(1) | curses.A_DIM,
        B_REEF: curses.color_pair(4) | curses.A_DIM,
        B_VOLCANIC: curses.color_pair(3) | curses.A_BOLD,
    }

    # Draw map
    for r in range(draw_rows):
        for c in range(draw_cols):
            sy = r + 1
            sx = c * 2
            if sy >= max_y - 2 or sx + 2 > map_char_width:
                continue

            b = biome_grid[r][c]
            sid = pop_grid[r][c]

            if view == "species":
                if sid >= 0 and sid in sp_by_id and sp_by_id[sid]["alive"]:
                    sp = sp_by_id[sid]
                    ch = TROPHIC_CHARS[sp["trophic"]]
                    attr = curses.color_pair(sp["color_idx"])
                    if pop_size_grid[r][c] > 10:
                        attr |= curses.A_BOLD
                else:
                    ch = BIOME_CHARS.get(b, "  ")
                    attr = biome_colors.get(b, curses.color_pair(7))

            elif view == "biome":
                ch = BIOME_CHARS.get(b, "  ")
                attr = biome_colors.get(b, curses.color_pair(7))

            elif view == "fitness":
                if sid >= 0 and sid in sp_by_id and sp_by_id[sid]["alive"]:
                    sp = sp_by_id[sid]
                    fit = _fitness_in_biome(sp, b)
                    if fit > 0.8:
                        ch = "██"
                        attr = curses.color_pair(2) | curses.A_BOLD
                    elif fit > 0.5:
                        ch = "▓▓"
                        attr = curses.color_pair(2)
                    elif fit > 0.3:
                        ch = "░░"
                        attr = curses.color_pair(6)
                    else:
                        ch = "··"
                        attr = curses.color_pair(3)
                else:
                    ch = BIOME_CHARS.get(b, "  ")
                    attr = biome_colors.get(b, curses.color_pair(7)) | curses.A_DIM

            elif view == "foodweb":
                if sid >= 0 and sid in sp_by_id and sp_by_id[sid]["alive"]:
                    sp = sp_by_id[sid]
                    tl = sp["trophic"]
                    # Color by trophic level
                    colors_tl = [curses.color_pair(2), curses.color_pair(6),
                                 curses.color_pair(3), curses.color_pair(5)]
                    ch = TROPHIC_CHARS[tl]
                    attr = colors_tl[tl]
                    # Highlight cells with predator-prey interaction
                    has_interaction = False
                    for dr, dc in _NBRS4:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            other = pop_grid[nr][nc]
                            if other >= 0 and ((sid, other) in self.evoeco_food_web
                                               or (other, sid) in self.evoeco_food_web):
                                has_interaction = True
                                break
                    if has_interaction:
                        attr |= curses.A_BOLD
                else:
                    ch = BIOME_CHARS.get(b, "  ")
                    attr = biome_colors.get(b, curses.color_pair(7)) | curses.A_DIM
            else:
                ch = "  "
                attr = curses.color_pair(7)

            try:
                self.stdscr.addstr(sy, sx, ch[:2], attr)
            except curses.error:
                pass

    # ── Phylogenetic tree / sidebar ──
    tree_x = draw_cols * 2 + 1
    if tree_width > 0 and tree_x < max_x - 5:
        if show_log:
            # Show event log
            try:
                self.stdscr.addstr(1, tree_x, "─ Event Log ─"[:tree_width],
                                   curses.color_pair(7) | curses.A_BOLD)
            except curses.error:
                pass
            log_lines = self.evoeco_log[-(max_y - 5):]
            for li, line in enumerate(log_lines):
                try:
                    self.stdscr.addstr(2 + li, tree_x, line[:tree_width],
                                       curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass
        else:
            # Draw phylogenetic tree
            try:
                self.stdscr.addstr(1, tree_x, "─ Phylogenetic Tree ─"[:tree_width],
                                   curses.color_pair(7) | curses.A_BOLD)
            except curses.error:
                pass

            # Find root nodes (parent_id == 0 or parent not in tree)
            all_ids = {pn["species_id"] for pn in self.evoeco_phylo}
            roots = [pn for pn in self.evoeco_phylo
                     if pn["parent_id"] == 0 or pn["parent_id"] not in all_ids]

            tree_lines = []
            _build_tree_lines(self.evoeco_phylo, sp_by_id, roots, tree_lines,
                              self.evoeco_generation, depth=0, max_lines=max_y - 6)

            for li, (line_text, line_attr) in enumerate(tree_lines):
                if 2 + li >= max_y - 3:
                    break
                try:
                    self.stdscr.addstr(2 + li, tree_x, line_text[:tree_width], line_attr)
                except curses.error:
                    pass

            # Species count summary below tree
            summary_y = min(2 + len(tree_lines) + 1, max_y - 5)
            if summary_y < max_y - 3:
                producers = sum(1 for s in species_list if s["alive"] and s["trophic"] == TROPHIC_PRODUCER)
                herbivores = sum(1 for s in species_list if s["alive"] and s["trophic"] == TROPHIC_HERBIVORE)
                predators = sum(1 for s in species_list if s["alive"] and s["trophic"] == TROPHIC_PREDATOR)
                apex = sum(1 for s in species_list if s["alive"] and s["trophic"] == TROPHIC_APEX)
                try:
                    self.stdscr.addstr(summary_y, tree_x,
                                       f"♣{producers} ♠{herbivores} ♦{predators} ♛{apex}"[:tree_width],
                                       curses.color_pair(6))
                    self.stdscr.addstr(summary_y + 1, tree_x,
                                       f"Web: {len(self.evoeco_food_web)} links"[:tree_width],
                                       curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass

    # Stats bar
    stats_y = max_y - 3
    if stats_y > 1:
        spec_events = self.evoeco_stats.get("speciations", 0)
        ext_events = self.evoeco_stats.get("extinctions", 0)
        mass_ext = self.evoeco_stats.get("mass_extinctions", 0)
        web_links = len(self.evoeco_food_web)
        stats_line = (f" Speciations: {spec_events}  Extinctions: {ext_events}  "
                      f"Mass ext: {mass_ext}  Food web: {web_links} links")
        try:
            self.stdscr.addstr(stats_y, 0, stats_line[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Recent event
    event_y = max_y - 2
    if event_y > 1 and self.evoeco_log:
        last_event = self.evoeco_log[-1]
        try:
            self.stdscr.addstr(event_y, 0, f" {last_event}"[:max_x - 1],
                               curses.color_pair(2) | curses.A_DIM)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [t]=tree [l]=log [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _build_tree_lines(phylo_nodes, sp_by_id, roots, lines, cur_gen, depth, max_lines):
    """Recursively build phylogenetic tree display lines."""
    node_map = {pn["species_id"]: pn for pn in phylo_nodes}

    for root in roots:
        if len(lines) >= max_lines:
            return
        _render_phylo_node(node_map, sp_by_id, root, lines, cur_gen, depth, max_lines)


def _render_phylo_node(node_map, sp_by_id, node, lines, cur_gen, depth, max_lines):
    """Render a single phylo node and its children."""
    if len(lines) >= max_lines:
        return

    indent = "  " * min(depth, 8)
    sid = node["species_id"]
    sp = sp_by_id.get(sid)
    trophic_sym = TROPHIC_CHARS[node["trophic"]].strip() if node["trophic"] < len(TROPHIC_CHARS) else "?"

    if sp and sp["alive"]:
        pop = sp.get("total_pop", 0)
        name = sp["name"]
        text = f"{indent}├─{trophic_sym} {name} ({pop})"
        attr = curses.color_pair(sp["color_idx"])
    else:
        ext_gen = node.get("extinct_gen", -1)
        name = node["name"]
        if ext_gen >= 0:
            text = f"{indent}├─{trophic_sym} {name} †{ext_gen}"
        else:
            text = f"{indent}├─{trophic_sym} {name}"
        attr = curses.color_pair(7) | curses.A_DIM

    lines.append((text, attr))

    # Render children
    children = node.get("children", [])
    for child_id in children:
        if child_id in node_map:
            _render_phylo_node(node_map, sp_by_id, node_map[child_id],
                               lines, cur_gen, depth + 1, max_lines)


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register ecosystem evolution mode methods on the App class."""
    App._enter_evoeco_mode = _enter_evoeco_mode
    App._exit_evoeco_mode = _exit_evoeco_mode
    App._evoeco_init = _evoeco_init
    App._evoeco_step = _evoeco_step
    App._handle_evoeco_menu_key = _handle_evoeco_menu_key
    App._handle_evoeco_key = _handle_evoeco_key
    App._draw_evoeco_menu = _draw_evoeco_menu
    App._draw_evoeco = _draw_evoeco
    App.EVOECO_PRESETS = EVOECO_PRESETS
