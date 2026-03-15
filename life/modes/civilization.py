"""Mode: civilization — procedural civilization & cultural evolution simulation.

A 2D world where tribes emerge on procedurally generated terrain, develop
technologies, establish trade routes, and compete for resources.  Cultural
traits diffuse across populations, alliances form and fracture, and
civilizations rise and fall over time.

Features terrain generation (mountains, rivers, forests, plains, desert),
agent-based tribes with tech trees, resource harvesting, trade networks,
cultural diffusion, diplomacy, warfare, and emergent historical narratives.

Presets: Pangaea, Archipelago, River Valleys, Tundra & Steppe,
Fertile Crescent, Random World.
"""
import curses
import math
import random
import time

# ── Terrain types ───────────────────────────────────────────────────
T_WATER = 0
T_PLAINS = 1
T_FOREST = 2
T_HILLS = 3
T_MOUNTAIN = 4
T_DESERT = 5
T_RIVER = 6
T_COAST = 7
T_TUNDRA = 8
T_JUNGLE = 9

TERRAIN_CHARS = {
    T_WATER: "~~", T_PLAINS: "..", T_FOREST: "TT", T_HILLS: "^^",
    T_MOUNTAIN: "MM", T_DESERT: "::", T_RIVER: "==", T_COAST: ".~",
    T_TUNDRA: "**", T_JUNGLE: "##",
}

# Resource yields per terrain
TERRAIN_FOOD = {
    T_WATER: 1, T_PLAINS: 4, T_FOREST: 2, T_HILLS: 1, T_MOUNTAIN: 0,
    T_DESERT: 0, T_RIVER: 5, T_COAST: 3, T_TUNDRA: 1, T_JUNGLE: 3,
}
TERRAIN_PROD = {
    T_WATER: 0, T_PLAINS: 1, T_FOREST: 3, T_HILLS: 3, T_MOUNTAIN: 4,
    T_DESERT: 1, T_RIVER: 1, T_COAST: 1, T_TUNDRA: 1, T_JUNGLE: 2,
}
TERRAIN_GOLD = {
    T_WATER: 2, T_PLAINS: 1, T_FOREST: 1, T_HILLS: 2, T_MOUNTAIN: 3,
    T_DESERT: 2, T_RIVER: 3, T_COAST: 3, T_TUNDRA: 0, T_JUNGLE: 2,
}

# ── Technology tree ─────────────────────────────────────────────────
# (name, cost, prerequisite index or -1, effect description)
TECH_TREE = [
    ("Fire",            10,  -1, "food+1"),
    ("Tool-Making",     15,  -1, "prod+1"),
    ("Agriculture",     25,   0, "food+2, settle"),
    ("Animal Husbandry",25,   0, "food+1, move+1"),
    ("Pottery",         20,   1, "trade+1"),
    ("Writing",         40,   4, "culture+2"),
    ("Bronze Working",  35,   1, "attack+1"),
    ("Wheel",           30,   1, "move+1, trade+1"),
    ("Irrigation",      35,   2, "food+2"),
    ("Masonry",         40,   6, "defense+2"),
    ("Currency",        50,   7, "trade+3"),
    ("Iron Working",    60,   6, "attack+2"),
    ("Philosophy",      55,   5, "culture+3"),
    ("Mathematics",     50,   5, "prod+2"),
    ("Navigation",      65,  10, "sea, trade+2"),
    ("Engineering",     70,  13, "prod+3, defense+1"),
    ("Theology",        60,  12, "culture+4"),
    ("Feudalism",       70,   9, "defense+2, food+1"),
    ("Gunpowder",       90,  11, "attack+4"),
    ("Printing Press", 100,  16, "culture+5"),
]

# ── Cultural traits ─────────────────────────────────────────────────
CULTURE_TRAITS = [
    "Warlike", "Peaceful", "Nomadic", "Agrarian", "Mercantile",
    "Religious", "Artistic", "Scientific", "Expansionist", "Isolationist",
]

# ── Civilization colors (up to 12 civs) ─────────────────────────────
CIV_SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnop"

# ── Presets ──────────────────────────────────────────────────────────
CIV_PRESETS = [
    ("Pangaea",
     "One large continent — early conflict and rapid tech diffusion",
     {"land_pct": 0.65, "mountain_pct": 0.06, "forest_pct": 0.20,
      "desert_pct": 0.08, "river_count": 6, "num_tribes": 8,
      "start_pop": 50, "aggression": 0.4, "trade_bonus": 1.0}),

    ("Archipelago",
     "Scattered islands — navigation key, isolated cultures diverge",
     {"land_pct": 0.35, "mountain_pct": 0.04, "forest_pct": 0.12,
      "desert_pct": 0.03, "river_count": 3, "num_tribes": 10,
      "start_pop": 30, "aggression": 0.2, "trade_bonus": 0.5}),

    ("River Valleys",
     "Fertile river basins — agriculture blooms, dense populations",
     {"land_pct": 0.50, "mountain_pct": 0.08, "forest_pct": 0.15,
      "desert_pct": 0.12, "river_count": 10, "num_tribes": 6,
      "start_pop": 60, "aggression": 0.3, "trade_bonus": 1.5}),

    ("Tundra & Steppe",
     "Harsh northern plains — nomadic herders, slow development",
     {"land_pct": 0.55, "mountain_pct": 0.10, "forest_pct": 0.08,
      "desert_pct": 0.05, "river_count": 4, "num_tribes": 7,
      "start_pop": 35, "aggression": 0.5, "trade_bonus": 0.8}),

    ("Fertile Crescent",
     "Central fertile zone ringed by desert & mountains — cradle of civilization",
     {"land_pct": 0.55, "mountain_pct": 0.12, "forest_pct": 0.10,
      "desert_pct": 0.20, "river_count": 8, "num_tribes": 6,
      "start_pop": 55, "aggression": 0.35, "trade_bonus": 1.3}),

    ("Random World",
     "Fully randomized terrain and starting conditions",
     {"land_pct": None, "mountain_pct": None, "forest_pct": None,
      "desert_pct": None, "river_count": None, "num_tribes": None,
      "start_pop": None, "aggression": None, "trade_bonus": None}),
]

# ── Neighbour offsets ────────────────────────────────────────────────
_NBRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NBRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
           (0, 1), (1, -1), (1, 0), (1, 1)]


# ── Terrain generation ──────────────────────────────────────────────

def _generate_heightmap(rows, cols, octaves=5):
    """Simple value-noise heightmap via multi-octave random smoothing."""
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
    # Normalize 0..1
    lo = min(min(row) for row in hmap)
    hi = max(max(row) for row in hmap)
    rng = hi - lo if hi > lo else 1.0
    for r in range(rows):
        for c in range(cols):
            hmap[r][c] = (hmap[r][c] - lo) / rng
    return hmap


def _generate_terrain(rows, cols, settings):
    """Build terrain grid from heightmap + settings."""
    hmap = _generate_heightmap(rows, cols)
    water_thresh = 1.0 - settings["land_pct"]
    mtn_thresh = 1.0 - settings["mountain_pct"]
    grid = [[T_WATER] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            h = hmap[r][c]
            if h < water_thresh:
                grid[r][c] = T_WATER
            elif h >= mtn_thresh:
                grid[r][c] = T_MOUNTAIN
            elif h > mtn_thresh - 0.04:
                grid[r][c] = T_HILLS
            else:
                grid[r][c] = T_PLAINS

    # Add forests
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == T_PLAINS and random.random() < settings["forest_pct"] * 1.5:
                # prefer mid-latitude
                lat_frac = abs(r / max(1, rows - 1) - 0.5) * 2
                if lat_frac < 0.7:
                    grid[r][c] = T_FOREST
                elif lat_frac > 0.8:
                    grid[r][c] = T_TUNDRA

    # Add deserts near equator/tropics
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == T_PLAINS:
                lat_frac = abs(r / max(1, rows - 1) - 0.5) * 2
                if lat_frac < 0.3 and random.random() < settings["desert_pct"] * 3:
                    grid[r][c] = T_DESERT
                elif lat_frac < 0.15 and grid[r][c] == T_FOREST:
                    if random.random() < 0.3:
                        grid[r][c] = T_JUNGLE

    # Carve rivers from mountains to water
    for _ in range(settings["river_count"]):
        # Find a mountain cell
        mtns = [(r, c) for r in range(rows) for c in range(cols)
                if grid[r][c] == T_MOUNTAIN]
        if not mtns:
            break
        sr, sc = random.choice(mtns)
        cr, cc = sr, sc
        for _step in range(rows + cols):
            if grid[cr][cc] == T_WATER:
                break
            if grid[cr][cc] not in (T_MOUNTAIN, T_RIVER):
                grid[cr][cc] = T_RIVER
            # Flow downhill
            best_h, best_pos = hmap[cr][cc], None
            for dr, dc in _NBRS4:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if hmap[nr][nc] < best_h:
                        best_h = hmap[nr][nc]
                        best_pos = (nr, nc)
            if best_pos is None:
                # Random walk if stuck
                dr, dc = random.choice(_NBRS4)
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    best_pos = (nr, nc)
                else:
                    break
            cr, cc = best_pos

    # Mark coasts
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == T_WATER:
                for dr, dc in _NBRS4:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if grid[nr][nc] not in (T_WATER, T_COAST, T_RIVER):
                            grid[r][c] = T_COAST
                            break

    return grid, hmap


# ── Tribe / Civilization class ──────────────────────────────────────

def _make_tribe(tid, r, c, pop, settings):
    """Create a new tribe dictionary."""
    traits = random.sample(CULTURE_TRAITS, 2)
    return {
        "id": tid,
        "name": f"Tribe-{CIV_SYMBOLS[tid % len(CIV_SYMBOLS)]}",
        "color_idx": (tid % 6) + 1,  # curses color pairs 1-6
        "pop": pop,
        "food": 20.0,
        "gold": 10.0,
        "prod": 5.0,
        "culture": 5.0,
        "attack": 1.0,
        "defense": 1.0,
        "move_range": 1,
        "techs": set(),      # set of tech indices researched
        "research_target": -1,
        "research_progress": 0.0,
        "traits": list(traits),
        "trait_strength": {t: random.uniform(0.3, 1.0) for t in traits},
        "settlements": [(r, c)],  # (row, col) of cities
        "territory": set(),
        "trade_partners": set(),
        "at_war_with": set(),
        "alive": True,
        "age": 0,
        "peak_pop": pop,
        "has_agriculture": False,
        "has_navigation": False,
        "aggression": settings["aggression"] + random.uniform(-0.15, 0.15),
    }


# ══════════════════════════════════════════════════════════════════════
#  Core mode functions
# ══════════════════════════════════════════════════════════════════════

def _enter_civ_mode(self):
    """Enter Civilization mode — show preset menu."""
    self.civ_menu = True
    self.civ_menu_sel = 0
    self._flash("Civilization & Cultural Evolution — select a scenario")


def _exit_civ_mode(self):
    """Exit Civilization mode."""
    self.civ_mode = False
    self.civ_menu = False
    self.civ_running = False
    self.civ_terrain = []
    self.civ_tribes = []
    self.civ_log = []
    self._flash("Civilization mode OFF")


def _civ_init(self, preset_idx: int):
    """Initialize the Civilization simulation with the given preset."""
    name, _desc, settings = self.CIV_PRESETS[preset_idx]
    settings = dict(settings)

    # Randomize if Random World
    if settings["land_pct"] is None:
        settings["land_pct"] = random.uniform(0.30, 0.70)
        settings["mountain_pct"] = random.uniform(0.03, 0.12)
        settings["forest_pct"] = random.uniform(0.05, 0.25)
        settings["desert_pct"] = random.uniform(0.02, 0.18)
        settings["river_count"] = random.randint(2, 10)
        settings["num_tribes"] = random.randint(4, 12)
        settings["start_pop"] = random.randint(25, 70)
        settings["aggression"] = random.uniform(0.15, 0.55)
        settings["trade_bonus"] = random.uniform(0.5, 2.0)

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(30, max_y - 4)
    cols = max(40, (max_x - 1) // 2)

    self.civ_rows = rows
    self.civ_cols = cols
    self.civ_preset_name = name
    self.civ_preset_idx = preset_idx
    self.civ_generation = 0
    self.civ_steps_per_frame = 1
    self.civ_settings = settings
    self.civ_view = "political"  # political / terrain / culture / trade

    # Generate terrain
    terrain, hmap = _generate_terrain(rows, cols, settings)
    self.civ_terrain = terrain
    self.civ_hmap = hmap

    # Territory ownership: -1 = unclaimed
    self.civ_territory = [[-1] * cols for _ in range(rows)]

    # Trade routes: list of (tribe_a, tribe_b, path_cells)
    self.civ_trade_routes = []

    # Event log
    self.civ_log = []

    # Cultural influence map per trait
    self.civ_culture_map = [[[0.0] * len(CULTURE_TRAITS)
                             for _ in range(cols)] for _ in range(rows)]

    # Place tribes on habitable land
    habitable = [(r, c) for r in range(rows) for c in range(cols)
                 if terrain[r][c] in (T_PLAINS, T_FOREST, T_RIVER, T_HILLS, T_COAST, T_JUNGLE)]
    random.shuffle(habitable)

    self.civ_tribes = []
    placed = 0
    min_dist = max(5, min(rows, cols) // (settings["num_tribes"] + 1))
    used = []
    for r, c in habitable:
        if placed >= settings["num_tribes"]:
            break
        # Ensure minimum distance from other tribes
        too_close = False
        for ur, uc in used:
            if abs(r - ur) + abs(c - uc) < min_dist:
                too_close = True
                break
        if too_close:
            continue
        tribe = _make_tribe(placed, r, c, settings["start_pop"], settings)
        self.civ_tribes.append(tribe)
        self.civ_territory[r][c] = placed
        # Claim small initial territory
        for dr, dc in _NBRS8:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if terrain[nr][nc] != T_WATER:
                    self.civ_territory[nr][nc] = placed
                    tribe["territory"].add((nr, nc))
        tribe["territory"].add((r, c))
        used.append((r, c))
        placed += 1

    # Statistics
    self.civ_stats = {
        "total_pop": sum(t["pop"] for t in self.civ_tribes),
        "num_civs": len(self.civ_tribes),
        "wars": 0,
        "trades": 0,
        "techs_discovered": 0,
        "cities_founded": 0,
        "fallen_civs": 0,
    }

    self.civ_menu = False
    self.civ_mode = True
    self.civ_running = False
    self._flash(f"Civilization: {name} — {placed} tribes, {rows}x{cols} world")


def _civ_step(self):
    """Advance the civilization simulation by one generation."""
    tribes = self.civ_tribes
    terrain = self.civ_terrain
    territory = self.civ_territory
    rows, cols = self.civ_rows, self.civ_cols
    gen = self.civ_generation
    settings = self.civ_settings

    alive_tribes = [t for t in tribes if t["alive"]]
    if len(alive_tribes) == 0:
        self.civ_running = False
        return

    for tribe in alive_tribes:
        tribe["age"] += 1

        # ── Resource gathering ──
        food_yield = 0.0
        prod_yield = 0.0
        gold_yield = 0.0
        for r, c in tribe["territory"]:
            tt = terrain[r][c]
            food_yield += TERRAIN_FOOD.get(tt, 0)
            prod_yield += TERRAIN_PROD.get(tt, 0)
            gold_yield += TERRAIN_GOLD.get(tt, 0)

        # Tech bonuses
        for ti in tribe["techs"]:
            eff = TECH_TREE[ti][3]
            if "food+" in eff:
                food_yield += int(eff.split("food+")[1][0])
            if "prod+" in eff:
                prod_yield += int(eff.split("prod+")[1][0])

        # Trait bonuses
        if "Agrarian" in tribe["traits"]:
            food_yield *= 1.0 + 0.2 * tribe["trait_strength"].get("Agrarian", 0)
        if "Mercantile" in tribe["traits"]:
            gold_yield *= 1.0 + 0.3 * tribe["trait_strength"].get("Mercantile", 0)

        # Trade income
        trade_income = len(tribe["trade_partners"]) * 2.0 * settings["trade_bonus"]
        gold_yield += trade_income

        tribe["food"] += food_yield * 0.1
        tribe["prod"] += prod_yield * 0.1
        tribe["gold"] += gold_yield * 0.1

        # ── Population growth ──
        food_per_cap = tribe["food"] / max(1, tribe["pop"])
        if food_per_cap > 1.0:
            growth = min(tribe["pop"] * 0.03, food_per_cap * 0.5)
            tribe["pop"] += max(1, int(growth))
            tribe["food"] -= growth * 0.5
        elif food_per_cap < 0.3:
            # Famine
            loss = max(1, int(tribe["pop"] * 0.05))
            tribe["pop"] -= loss
            if tribe["pop"] <= 0:
                tribe["alive"] = False
                tribe["pop"] = 0
                self.civ_log.append(f"Gen {gen}: {tribe['name']} perished from famine")
                self.civ_stats["fallen_civs"] += 1
                continue

        tribe["peak_pop"] = max(tribe["peak_pop"], tribe["pop"])

        # ── Research ──
        if tribe["research_target"] == -1:
            # Pick a tech to research
            available = []
            for i, (tname, cost, prereq, _eff) in enumerate(TECH_TREE):
                if i not in tribe["techs"]:
                    if prereq == -1 or prereq in tribe["techs"]:
                        available.append(i)
            if available:
                if "Scientific" in tribe["traits"]:
                    # Prefer higher-tier techs
                    available.sort(key=lambda x: TECH_TREE[x][1])
                tribe["research_target"] = random.choice(available)
                tribe["research_progress"] = 0.0

        if tribe["research_target"] >= 0:
            sci_mult = 1.0
            if "Scientific" in tribe["traits"]:
                sci_mult += 0.3 * tribe["trait_strength"].get("Scientific", 0)
            tribe["research_progress"] += (prod_yield * 0.05 + tribe["pop"] * 0.01) * sci_mult
            cost = TECH_TREE[tribe["research_target"]][1]
            if tribe["research_progress"] >= cost:
                ti = tribe["research_target"]
                tribe["techs"].add(ti)
                tname = TECH_TREE[ti][0]
                eff = TECH_TREE[ti][3]
                self.civ_log.append(f"Gen {gen}: {tribe['name']} discovered {tname}")
                self.civ_stats["techs_discovered"] += 1

                # Apply tech effects
                if "attack+" in eff:
                    tribe["attack"] += int(eff.split("attack+")[1][0])
                if "defense+" in eff:
                    tribe["defense"] += int(eff.split("defense+")[1][0])
                if "move+" in eff:
                    tribe["move_range"] = min(4, tribe["move_range"] + 1)
                if "culture+" in eff:
                    tribe["culture"] += int(eff.split("culture+")[1][0])
                if "trade+" in eff:
                    tribe["gold"] += int(eff.split("trade+")[1][0]) * 5
                if "settle" in eff:
                    tribe["has_agriculture"] = True
                if "sea" in eff:
                    tribe["has_navigation"] = True

                tribe["research_target"] = -1
                tribe["research_progress"] = 0.0

        # ── Territorial expansion ──
        if tribe["pop"] > len(tribe["territory"]) * 3 and random.random() < 0.4:
            # Expand to adjacent unclaimed land
            border = set()
            for r, c in tribe["territory"]:
                for dr, dc in _NBRS4:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if territory[nr][nc] == -1:
                            tt = terrain[nr][nc]
                            if tt != T_WATER or tribe["has_navigation"]:
                                if tt != T_MOUNTAIN:
                                    border.add((nr, nc))
            if border:
                nr, nc = random.choice(list(border))
                territory[nr][nc] = tribe["id"]
                tribe["territory"].add((nr, nc))

        # ── Found new settlements ──
        if (tribe["has_agriculture"] and tribe["pop"] > 80
                and len(tribe["settlements"]) < tribe["pop"] // 60
                and tribe["prod"] > 15 and random.random() < 0.15):
            # Find a good settlement spot in territory
            candidates = [(r, c) for r, c in tribe["territory"]
                          if terrain[r][c] in (T_PLAINS, T_RIVER, T_COAST)
                          and (r, c) not in tribe["settlements"]
                          and all(abs(r - sr) + abs(c - sc) > 4
                                  for sr, sc in tribe["settlements"])]
            if candidates:
                sr, sc = random.choice(candidates)
                tribe["settlements"].append((sr, sc))
                tribe["prod"] -= 10
                self.civ_log.append(f"Gen {gen}: {tribe['name']} founded a settlement")
                self.civ_stats["cities_founded"] += 1

    # ── Diplomacy & Trade ──
    for i, t1 in enumerate(alive_tribes):
        for j, t2 in enumerate(alive_tribes):
            if j <= i:
                continue
            # Check adjacency (territories touch)
            adjacent = False
            for r, c in t1["territory"]:
                if adjacent:
                    break
                for dr, dc in _NBRS4:
                    nr, nc = r + dr, c + dc
                    if (nr, nc) in t2["territory"]:
                        adjacent = True
                        break
            if not adjacent:
                continue

            # War logic
            if t2["id"] in t1["at_war_with"]:
                _resolve_conflict(t1, t2, terrain, territory, rows, cols, gen, self)
                continue

            # Trade
            if (t2["id"] not in t1["trade_partners"]
                    and t2["id"] not in t1["at_war_with"]):
                merc1 = "Mercantile" in t1["traits"]
                merc2 = "Mercantile" in t2["traits"]
                peace1 = "Peaceful" in t1["traits"]
                trade_chance = 0.08 + (0.1 if merc1 else 0) + (0.1 if merc2 else 0) + (0.05 if peace1 else 0)
                if random.random() < trade_chance:
                    t1["trade_partners"].add(t2["id"])
                    t2["trade_partners"].add(t1["id"])
                    self.civ_stats["trades"] += 1

            # War declaration
            if t2["id"] not in t1["trade_partners"]:
                war_chance = t1["aggression"] * 0.04
                if "Warlike" in t1["traits"]:
                    war_chance += 0.06 * t1["trait_strength"].get("Warlike", 0)
                if "Peaceful" in t1["traits"]:
                    war_chance *= 0.2
                if t1["pop"] > t2["pop"] * 1.5:
                    war_chance *= 1.5
                if random.random() < war_chance:
                    t1["at_war_with"].add(t2["id"])
                    t2["at_war_with"].add(t1["id"])
                    # Break trade
                    t1["trade_partners"].discard(t2["id"])
                    t2["trade_partners"].discard(t1["id"])
                    self.civ_log.append(f"Gen {gen}: {t1['name']} declared war on {t2['name']}")
                    self.civ_stats["wars"] += 1

    # ── Cultural diffusion ──
    culture_map = self.civ_culture_map
    for tribe in alive_tribes:
        for trait in tribe["traits"]:
            tidx = CULTURE_TRAITS.index(trait)
            strength = tribe["trait_strength"].get(trait, 0.5) * tribe["culture"] * 0.01
            for r, c in tribe["settlements"]:
                # Radiate from settlements
                radius = max(3, int(math.sqrt(tribe["culture"])))
                for dr in range(-radius, radius + 1):
                    for dc in range(-radius, radius + 1):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            dist = max(1, abs(dr) + abs(dc))
                            influence = strength / dist
                            culture_map[nr][nc][tidx] = min(
                                1.0, culture_map[nr][nc][tidx] + influence * 0.02)

    # Trait adoption: tribes near strong foreign culture may adopt traits
    for tribe in alive_tribes:
        if len(tribe["traits"]) >= 4:
            continue
        if random.random() > 0.02:
            continue
        # Sample culture at capital
        cr, cc = tribe["settlements"][0]
        for tidx, tname in enumerate(CULTURE_TRAITS):
            if tname in tribe["traits"]:
                continue
            if culture_map[cr][cc][tidx] > 0.5:
                tribe["traits"].append(tname)
                tribe["trait_strength"][tname] = 0.3
                self.civ_log.append(
                    f"Gen {gen}: {tribe['name']} adopted {tname} culture")
                break

    # Clean up dead tribe territories
    for tribe in tribes:
        if not tribe["alive"]:
            for r, c in list(tribe["territory"]):
                if territory[r][c] == tribe["id"]:
                    territory[r][c] = -1
            tribe["territory"].clear()

    # Update stats
    self.civ_stats["total_pop"] = sum(t["pop"] for t in tribes if t["alive"])
    self.civ_stats["num_civs"] = sum(1 for t in tribes if t["alive"])

    self.civ_generation += 1

    # Trim log
    if len(self.civ_log) > 200:
        self.civ_log = self.civ_log[-100:]


def _resolve_conflict(t1, t2, terrain, territory, rows, cols, gen, app):
    """Resolve one step of conflict between two tribes."""
    # Calculate military strength
    str1 = t1["attack"] * t1["pop"] * 0.01 + t1["defense"] * 0.5
    str2 = t2["attack"] * t2["pop"] * 0.01 + t2["defense"] * 0.5

    if "Warlike" in t1["traits"]:
        str1 *= 1.2
    if "Warlike" in t2["traits"]:
        str2 *= 1.2

    # Stochastic outcome
    r = random.random()
    total = str1 + str2
    if total == 0:
        return

    if r < str1 / total:
        winner, loser = t1, t2
    else:
        winner, loser = t2, t1

    # Casualties
    w_loss = max(1, int(loser["attack"] * 0.5))
    l_loss = max(1, int(winner["attack"] * 0.8))
    winner["pop"] = max(1, winner["pop"] - w_loss)
    loser["pop"] = max(0, loser["pop"] - l_loss)

    # Territory exchange
    border_cells = []
    for r, c in list(loser["territory"]):
        for dr, dc in _NBRS4:
            nr, nc = r + dr, c + dc
            if (nr, nc) in winner["territory"]:
                border_cells.append((r, c))
                break

    if border_cells:
        captured = random.choice(border_cells)
        cr, cc = captured
        loser["territory"].discard(captured)
        winner["territory"].add(captured)
        territory[cr][cc] = winner["id"]

    # Check for defeat
    if loser["pop"] <= 0 or len(loser["territory"]) == 0:
        loser["alive"] = False
        loser["pop"] = 0
        app.civ_log.append(
            f"Gen {gen}: {loser['name']} was conquered by {winner['name']}")
        app.civ_stats["fallen_civs"] += 1
        # Winner absorbs remaining territory
        for r, c in list(loser["territory"]):
            territory[r][c] = winner["id"]
            winner["territory"].add((r, c))
        loser["territory"].clear()
        winner["at_war_with"].discard(loser["id"])
    elif random.random() < 0.05:
        # Peace treaty
        t1["at_war_with"].discard(t2["id"])
        t2["at_war_with"].discard(t1["id"])
        app.civ_log.append(
            f"Gen {gen}: {t1['name']} and {t2['name']} signed peace")


# ── Menu & key handling ─────────────────────────────────────────────

def _handle_civ_menu_key(self, key):
    """Handle input on the preset selection menu."""
    if key == -1:
        return True
    n = len(self.CIV_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.civ_menu_sel = (self.civ_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.civ_menu_sel = (self.civ_menu_sel + 1) % n
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._civ_init(self.civ_menu_sel)
        return True
    if key == 27:  # Esc
        self.civ_menu = False
        self._flash("Civilization mode cancelled")
        return True
    return True


def _handle_civ_key(self, key):
    """Handle input during the running simulation."""
    if key == -1:
        return True
    if key == ord(" "):
        self.civ_running = not self.civ_running
        return True
    if key == ord("n"):
        self._civ_step()
        return True
    if key == ord("v"):
        views = ["political", "terrain", "culture", "trade"]
        idx = views.index(self.civ_view) if self.civ_view in views else 0
        self.civ_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.civ_view}")
        return True
    if key == ord("+") or key == ord("="):
        self.civ_steps_per_frame = min(20, self.civ_steps_per_frame + 1)
        self._flash(f"Speed: {self.civ_steps_per_frame}x")
        return True
    if key == ord("-"):
        self.civ_steps_per_frame = max(1, self.civ_steps_per_frame - 1)
        self._flash(f"Speed: {self.civ_steps_per_frame}x")
        return True
    if key == ord("l"):
        # Toggle log view
        self.civ_show_log = not getattr(self, "civ_show_log", False)
        return True
    if key == ord("r"):
        self._civ_init(self.civ_preset_idx)
        return True
    if key == ord("R"):
        self.civ_menu = True
        self.civ_mode = False
        self.civ_running = False
        return True
    if key == ord("q") or key == 27:
        self._exit_civ_mode()
        return True
    # Speed controls inherited from main app
    from life.constants import SPEEDS
    if key == ord("["):
        self.speed_idx = max(0, self.speed_idx - 1)
        return True
    if key == ord("]"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
        return True
    return True


# ── Drawing ─────────────────────────────────────────────────────────

def _draw_civ_menu(self, max_y, max_x):
    """Draw the preset selection menu."""
    self.stdscr.erase()
    title = "╔══ Civilization & Cultural Evolution ══╗"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Select a world to simulate:"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    y = 5
    for i, (name, desc, _settings) in enumerate(self.CIV_PRESETS):
        if y + 2 >= max_y:
            break
        marker = "▶ " if i == self.civ_menu_sel else "  "
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.civ_menu_sel else curses.color_pair(6)
        try:
            self.stdscr.addstr(y, 4, f"{marker}{name}", attr)
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


def _draw_civ(self, max_y, max_x):
    """Draw the main civilization simulation view."""
    self.stdscr.erase()
    terrain = self.civ_terrain
    territory = self.civ_territory
    tribes = self.civ_tribes
    rows, cols = self.civ_rows, self.civ_cols
    view = self.civ_view
    show_log = getattr(self, "civ_show_log", False)

    # Header
    alive = sum(1 for t in tribes if t["alive"])
    total_pop = sum(t["pop"] for t in tribes if t["alive"])
    header = (f" Gen {self.civ_generation}  |  {alive} civs  |  "
              f"Pop {total_pop}  |  View: {view}  |  "
              f"{'▶ RUNNING' if self.civ_running else '⏸ PAUSED'}  |  "
              f"{self.civ_preset_name}")
    try:
        self.stdscr.addstr(0, 0, header[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Calculate visible area
    draw_rows = min(rows, max_y - 4)
    draw_cols = min(cols, (max_x - 1) // 2)

    # Draw sidebar or log if enabled
    sidebar_x = draw_cols * 2 + 1
    sidebar_w = max_x - sidebar_x - 1

    if show_log and sidebar_w > 20:
        # Show event log
        try:
            self.stdscr.addstr(1, sidebar_x, "─ Event Log ─"[:sidebar_w],
                               curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass
        log_lines = self.civ_log[-(max_y - 5):]
        for li, line in enumerate(log_lines):
            try:
                self.stdscr.addstr(2 + li, sidebar_x, line[:sidebar_w],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass
    elif sidebar_w > 20:
        # Show civilization summaries
        sy = 1
        for tribe in sorted(tribes, key=lambda t: -t["pop"]):
            if not tribe["alive"]:
                continue
            if sy + 3 >= max_y - 3:
                break
            sym = CIV_SYMBOLS[tribe["id"] % len(CIV_SYMBOLS)]
            info = f"{sym} {tribe['name']} pop={tribe['pop']}"
            techs_str = f"  techs={len(tribe['techs'])} traits={','.join(tribe['traits'][:2])}"
            try:
                self.stdscr.addstr(sy, sidebar_x, info[:sidebar_w],
                                   curses.color_pair(tribe["color_idx"]) | curses.A_BOLD)
                self.stdscr.addstr(sy + 1, sidebar_x, techs_str[:sidebar_w],
                                   curses.color_pair(tribe["color_idx"]) | curses.A_DIM)
            except curses.error:
                pass
            sy += 2

    # Main map
    terrain_colors = {
        T_WATER: curses.color_pair(4),
        T_PLAINS: curses.color_pair(2),
        T_FOREST: curses.color_pair(1),
        T_HILLS: curses.color_pair(6),
        T_MOUNTAIN: curses.color_pair(7) | curses.A_BOLD,
        T_DESERT: curses.color_pair(2) | curses.A_DIM,
        T_RIVER: curses.color_pair(4) | curses.A_BOLD,
        T_COAST: curses.color_pair(4) | curses.A_DIM,
        T_TUNDRA: curses.color_pair(7),
        T_JUNGLE: curses.color_pair(1) | curses.A_BOLD,
    }

    for r in range(draw_rows):
        for c in range(draw_cols):
            sy = r + 1
            sx = c * 2
            if sy >= max_y - 2 or sx + 2 > sidebar_x - 1:
                continue

            tt = terrain[r][c]
            owner = territory[r][c]

            if view == "political":
                if owner >= 0 and owner < len(tribes) and tribes[owner]["alive"]:
                    tribe = tribes[owner]
                    sym = CIV_SYMBOLS[owner % len(CIV_SYMBOLS)]
                    # Check if settlement
                    is_city = (r, c) in tribe["settlements"]
                    if is_city:
                        ch = f"[{sym}"
                        attr = curses.color_pair(tribe["color_idx"]) | curses.A_BOLD
                    else:
                        ch = f"{sym}{sym}"
                        attr = curses.color_pair(tribe["color_idx"])
                else:
                    ch = TERRAIN_CHARS.get(tt, "  ")
                    attr = terrain_colors.get(tt, curses.color_pair(7))

            elif view == "terrain":
                ch = TERRAIN_CHARS.get(tt, "  ")
                attr = terrain_colors.get(tt, curses.color_pair(7))

            elif view == "culture":
                # Show dominant cultural trait
                culture_vals = self.civ_culture_map[r][c] if r < len(self.civ_culture_map) else [0] * len(CULTURE_TRAITS)
                max_val = max(culture_vals)
                if max_val > 0.1:
                    dom_idx = culture_vals.index(max_val)
                    intensity = min(1.0, max_val)
                    ch = CULTURE_TRAITS[dom_idx][:2]
                    # Color by trait category
                    pair = (dom_idx % 6) + 1
                    attr = curses.color_pair(pair)
                    if intensity > 0.7:
                        attr |= curses.A_BOLD
                    elif intensity < 0.3:
                        attr |= curses.A_DIM
                else:
                    ch = TERRAIN_CHARS.get(tt, "  ")
                    attr = terrain_colors.get(tt, curses.color_pair(7)) | curses.A_DIM

            elif view == "trade":
                if owner >= 0 and owner < len(tribes) and tribes[owner]["alive"]:
                    tribe = tribes[owner]
                    has_trade = len(tribe["trade_partners"]) > 0
                    if has_trade:
                        ch = "$$"
                        attr = curses.color_pair(2) | curses.A_BOLD
                    else:
                        sym = CIV_SYMBOLS[owner % len(CIV_SYMBOLS)]
                        ch = f"{sym}{sym}"
                        attr = curses.color_pair(tribe["color_idx"]) | curses.A_DIM
                else:
                    ch = TERRAIN_CHARS.get(tt, "  ")
                    attr = terrain_colors.get(tt, curses.color_pair(7)) | curses.A_DIM

            else:
                ch = "  "
                attr = curses.color_pair(7)

            try:
                self.stdscr.addstr(sy, sx, ch[:2], attr)
            except curses.error:
                pass

    # Stats bar
    stats_y = max_y - 3
    if stats_y > 1:
        wars = sum(len(t["at_war_with"]) for t in tribes if t["alive"]) // 2
        trades = sum(len(t["trade_partners"]) for t in tribes if t["alive"]) // 2
        top_tech = max((len(t["techs"]) for t in tribes if t["alive"]), default=0)
        stats_line = (f" Wars: {wars}  Trades: {trades}  "
                      f"Top tech: {top_tech}/{len(TECH_TREE)}  "
                      f"Fallen: {self.civ_stats['fallen_civs']}  "
                      f"Cities: {self.civ_stats['cities_founded']}")
        try:
            self.stdscr.addstr(stats_y, 0, stats_line[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Recent event
    event_y = max_y - 2
    if event_y > 1 and self.civ_log:
        last_event = self.civ_log[-1]
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
            hint = " [Space]=play [n]=step [v]=view [l]=log [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register civilization mode methods on the App class."""
    App._enter_civ_mode = _enter_civ_mode
    App._exit_civ_mode = _exit_civ_mode
    App._civ_init = _civ_init
    App._civ_step = _civ_step
    App._handle_civ_menu_key = _handle_civ_menu_key
    App._handle_civ_key = _handle_civ_key
    App._draw_civ_menu = _draw_civ_menu
    App._draw_civ = _draw_civ
    App.CIV_PRESETS = CIV_PRESETS
