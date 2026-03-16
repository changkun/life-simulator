"""Mode: city — City Growth & Urban Simulation.

Emergent urban development where residential, commercial, and industrial zones
self-organize around road networks via land-value gradients, population pressure,
and zoning attraction/repulsion rules.

Emergent phenomena:
  - Organic road network growth following population demand
  - Traffic-driven congestion feedback loops
  - NIMBYism and gentrification waves
  - Infrastructure decay and renewal cycles
  - Population migration between neighborhoods
  - Land value gradients shaping urban morphology
"""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

# Zone types
Z_EMPTY = 0
Z_ROAD = 1
Z_RESIDENTIAL = 2
Z_COMMERCIAL = 3
Z_INDUSTRIAL = 4
Z_PARK = 5
Z_WATER = 6
Z_RUIN = 7

ZONE_CHARS = {
    Z_EMPTY: " ",
    Z_ROAD: "·",
    Z_RESIDENTIAL: "▪",
    Z_COMMERCIAL: "◆",
    Z_INDUSTRIAL: "▲",
    Z_PARK: "♣",
    Z_WATER: "~",
    Z_RUIN: "░",
}

ZONE_NAMES = {
    Z_EMPTY: "empty",
    Z_ROAD: "road",
    Z_RESIDENTIAL: "residential",
    Z_COMMERCIAL: "commercial",
    Z_INDUSTRIAL: "industrial",
    Z_PARK: "park",
    Z_WATER: "water",
    Z_RUIN: "ruin",
}

# Density levels for residential/commercial/industrial
DENSITY_CHARS = {
    Z_RESIDENTIAL: [" ", "·", "▪", "▫", "▣", "█"],
    Z_COMMERCIAL: [" ", "·", "◇", "◆", "◈", "█"],
    Z_INDUSTRIAL: [" ", "·", "△", "▲", "▼", "█"],
}


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

CITY_PRESETS = [
    ("Medieval Town",
     "Small walled settlement growing organically from a central market square",
     "medieval"),
    ("Suburban Sprawl",
     "Low-density residential spread with car-dependent arterial roads",
     "suburban"),
    ("Dense Metropolis",
     "High-rise downtown core with radial transit and intense land competition",
     "metropolis"),
    ("Coastal City",
     "Port city constrained by coastline — waterfront gentrification and harbor industry",
     "coastal"),
    ("Post-Apocalyptic Regrowth",
     "Ruins of a collapsed city slowly reclaimed by scattered survivors",
     "postapoc"),
    ("Megacity",
     "Sprawling megacity with multiple centers, extreme density, and infrastructure strain",
     "megacity"),
]


# ══════════════════════════════════════════════════════════════════════
#  Helper: Terrain generation
# ══════════════════════════════════════════════════════════════════════

def _city_make_terrain(preset_id, rows, cols):
    """Generate initial zone grid, land value, and population grids."""
    zone = [[Z_EMPTY] * cols for _ in range(rows)]
    density = [[0] * cols for _ in range(rows)]  # 0-5
    land_value = [[50.0] * cols for _ in range(rows)]
    population = [[0] * cols for _ in range(rows)]
    traffic = [[0.0] * cols for _ in range(rows)]
    decay = [[0.0] * cols for _ in range(rows)]

    cx, cy = cols // 2, rows // 2

    if preset_id == "medieval":
        # Central market square
        for dr in range(-2, 3):
            for dc in range(-3, 4):
                r, c = cy + dr, cx + dc
                if 0 <= r < rows and 0 <= c < cols:
                    zone[r][c] = Z_ROAD
        # Initial buildings around market
        for _ in range(15):
            r = cy + random.randint(-4, 4)
            c = cx + random.randint(-5, 5)
            if 0 <= r < rows and 0 <= c < cols and zone[r][c] == Z_EMPTY:
                zone[r][c] = random.choice([Z_RESIDENTIAL, Z_RESIDENTIAL, Z_COMMERCIAL])
                density[r][c] = 1
                population[r][c] = random.randint(2, 8)
                land_value[r][c] = 70.0
        # Roads from center
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            for i in range(1, min(rows, cols) // 4):
                r, c = cy + dr * i, cx + dc * i
                if 0 <= r < rows and 0 <= c < cols:
                    zone[r][c] = Z_ROAD

    elif preset_id == "suburban":
        # Grid road pattern
        for r in range(rows):
            for c in range(cols):
                if r % 8 == 0 or c % 12 == 0:
                    zone[r][c] = Z_ROAD
        # Scatter some initial houses
        for _ in range(20):
            r = random.randint(1, rows - 2)
            c = random.randint(1, cols - 2)
            if zone[r][c] == Z_EMPTY:
                zone[r][c] = Z_RESIDENTIAL
                density[r][c] = 1
                population[r][c] = random.randint(2, 5)
        # A couple strip malls
        for _ in range(3):
            r = (random.randint(0, rows // 8)) * 8
            c = random.randint(2, cols - 3)
            for dc in range(min(4, cols - c)):
                if 0 <= r < rows and 0 <= c + dc < cols:
                    if zone[r][c + dc] == Z_ROAD:
                        continue
                    zone[r][c + dc] = Z_COMMERCIAL
                    density[r][c + dc] = 1
                    land_value[r][c + dc] = 60.0

    elif preset_id == "metropolis":
        # Radial roads from center
        for angle_idx in range(8):
            angle = angle_idx * math.pi / 4
            for i in range(1, max(rows, cols)):
                r = int(cy + i * math.sin(angle))
                c = int(cx + i * math.cos(angle))
                if 0 <= r < rows and 0 <= c < cols:
                    zone[r][c] = Z_ROAD
                else:
                    break
        # Ring roads
        for ring in range(3, max(rows, cols) // 2, 5):
            for angle_step in range(60):
                a = angle_step * math.pi / 30
                r = int(cy + ring * math.sin(a))
                c = int(cx + ring * math.cos(a))
                if 0 <= r < rows and 0 <= c < cols:
                    zone[r][c] = Z_ROAD
        # Dense core
        for dr in range(-3, 4):
            for dc in range(-4, 5):
                r, c = cy + dr, cx + dc
                if 0 <= r < rows and 0 <= c < cols and zone[r][c] != Z_ROAD:
                    zone[r][c] = Z_COMMERCIAL
                    density[r][c] = 4
                    population[r][c] = random.randint(20, 50)
                    land_value[r][c] = 95.0
        # Residential ring
        for dr in range(-7, 8):
            for dc in range(-9, 10):
                r, c = cy + dr, cx + dc
                if 0 <= r < rows and 0 <= c < cols and zone[r][c] == Z_EMPTY:
                    dist = math.sqrt(dr * dr + dc * dc)
                    if 4 < dist < 8:
                        zone[r][c] = Z_RESIDENTIAL
                        density[r][c] = 3
                        population[r][c] = random.randint(10, 30)
                        land_value[r][c] = 75.0

    elif preset_id == "coastal":
        # Water on the right side (coastline)
        coast_x = int(cols * 0.7)
        for r in range(rows):
            wave = int(3 * math.sin(r * 0.3))
            for c in range(coast_x + wave, cols):
                if 0 <= c < cols:
                    zone[r][c] = Z_WATER
                    land_value[r][c] = 0.0
        # Harbor / industrial zone near coast
        harbor_r = rows // 2
        for dr in range(-3, 4):
            for dc in range(-4, 1):
                r = harbor_r + dr
                c = coast_x + dc - 1
                if 0 <= r < rows and 0 <= c < cols and zone[r][c] != Z_WATER:
                    zone[r][c] = Z_INDUSTRIAL
                    density[r][c] = 2
                    population[r][c] = random.randint(5, 15)
                    land_value[r][c] = 40.0
        # Main road along coast
        for r in range(rows):
            c = coast_x - 5
            if 0 <= c < cols:
                zone[r][c] = Z_ROAD
        for c in range(coast_x - 5):
            if c % 10 == 0:
                for r in range(rows):
                    if r % 6 == 0:
                        zone[r][c] = Z_ROAD
        # Initial town center inland
        tcx = cols // 3
        for dr in range(-2, 3):
            for dc in range(-3, 4):
                r, c = cy + dr, tcx + dc
                if 0 <= r < rows and 0 <= c < cols and zone[r][c] == Z_EMPTY:
                    zone[r][c] = random.choice([Z_RESIDENTIAL, Z_COMMERCIAL])
                    density[r][c] = 2
                    population[r][c] = random.randint(5, 15)
                    land_value[r][c] = 65.0
        # Waterfront gets high land value
        for r in range(rows):
            for dc in range(1, 8):
                c = coast_x - dc
                if 0 <= c < cols and zone[r][c] != Z_WATER:
                    land_value[r][c] = max(land_value[r][c], 80.0 - dc * 5)

    elif preset_id == "postapoc":
        # Ruined grid city
        for r in range(rows):
            for c in range(cols):
                if r % 5 == 0 or c % 7 == 0:
                    zone[r][c] = Z_ROAD if random.random() < 0.6 else Z_RUIN
        # Scatter ruins
        for _ in range(int(rows * cols * 0.15)):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            if zone[r][c] == Z_EMPTY:
                zone[r][c] = Z_RUIN
                decay[r][c] = 0.8 + 0.2 * random.random()
                land_value[r][c] = 10.0 + 20.0 * random.random()
        # Small survivor settlements
        for _ in range(4):
            sr = random.randint(3, rows - 4)
            sc = random.randint(3, cols - 4)
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    r, c = sr + dr, sc + dc
                    if 0 <= r < rows and 0 <= c < cols:
                        if zone[r][c] in (Z_EMPTY, Z_RUIN):
                            zone[r][c] = Z_RESIDENTIAL
                            density[r][c] = 1
                            population[r][c] = random.randint(1, 4)
                            land_value[r][c] = 30.0
                            decay[r][c] = 0.0

    elif preset_id == "megacity":
        # Multiple city centers
        centers = []
        for _ in range(4):
            cr = random.randint(rows // 5, 4 * rows // 5)
            cc = random.randint(cols // 5, 4 * cols // 5)
            centers.append((cr, cc))
        # Roads connecting centers
        for i, (r1, c1) in enumerate(centers):
            for r2, c2 in centers[i + 1:]:
                # L-shaped road
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    if 0 <= r1 < rows and 0 <= c < cols:
                        zone[r1][c] = Z_ROAD
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    if 0 <= r < rows and 0 <= c2 < cols:
                        zone[r][c2] = Z_ROAD
        # Grid overlay
        for r in range(rows):
            for c in range(cols):
                if r % 6 == 0 or c % 8 == 0:
                    if zone[r][c] == Z_EMPTY:
                        zone[r][c] = Z_ROAD
        # Dense zones around centers
        for cr, cc in centers:
            zone_type = random.choice([Z_COMMERCIAL, Z_COMMERCIAL, Z_INDUSTRIAL])
            for dr in range(-3, 4):
                for dc in range(-4, 5):
                    r, c = cr + dr, cc + dc
                    if 0 <= r < rows and 0 <= c < cols and zone[r][c] == Z_EMPTY:
                        dist = abs(dr) + abs(dc)
                        if dist < 3:
                            zone[r][c] = zone_type
                            density[r][c] = 4
                            population[r][c] = random.randint(30, 80)
                            land_value[r][c] = 90.0
                        elif dist < 6:
                            zone[r][c] = Z_RESIDENTIAL
                            density[r][c] = 3
                            population[r][c] = random.randint(15, 40)
                            land_value[r][c] = 70.0
        # Scattered industrial on periphery
        for _ in range(10):
            r = random.choice([random.randint(0, rows // 5),
                               random.randint(4 * rows // 5, rows - 1)])
            c = random.randint(0, cols - 1)
            if 0 <= r < rows and 0 <= c < cols and zone[r][c] == Z_EMPTY:
                zone[r][c] = Z_INDUSTRIAL
                density[r][c] = 2
                population[r][c] = random.randint(10, 25)
                land_value[r][c] = 35.0

    return zone, density, land_value, population, traffic, decay


# ══════════════════════════════════════════════════════════════════════
#  Simulation logic
# ══════════════════════════════════════════════════════════════════════

def _city_count_neighbors(zone, r, c, rows, cols, ztype):
    """Count cells of given zone type in 8-neighborhood."""
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if zone[nr][nc] == ztype:
                    count += 1
    return count


def _city_road_access(zone, r, c, rows, cols):
    """Return distance to nearest road (Manhattan, up to 5)."""
    for dist in range(1, 6):
        for dr in range(-dist, dist + 1):
            for dc in range(-dist, dist + 1):
                if abs(dr) + abs(dc) != dist:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if zone[nr][nc] == Z_ROAD:
                        return dist
    return 6  # no road nearby


def _city_step(self):
    """Advance the city simulation by one generation."""
    zone = self.city_zone
    density = self.city_density
    land_value = self.city_land_value
    population = self.city_population
    traffic = self.city_traffic
    decay_grid = self.city_decay
    rows = self.city_rows
    cols = self.city_cols
    gen = self.city_generation
    preset_id = self.city_preset_id

    growth_rate = self.city_growth_rate
    rng = random.random

    total_pop = 0
    total_zones = {Z_RESIDENTIAL: 0, Z_COMMERCIAL: 0, Z_INDUSTRIAL: 0}

    # ── Phase 1: Update land values ──
    new_lv = [row[:] for row in land_value]
    for r in range(rows):
        for c in range(cols):
            if zone[r][c] == Z_WATER:
                continue
            lv = land_value[r][c]

            # Road access boosts value
            road_dist = _city_road_access(zone, r, c, rows, cols)
            if road_dist <= 2:
                lv += 0.3
            elif road_dist >= 5:
                lv -= 0.1

            # Commercial neighbors boost value
            com_n = _city_count_neighbors(zone, r, c, rows, cols, Z_COMMERCIAL)
            lv += com_n * 0.15

            # Industrial neighbors decrease value (NIMBY)
            ind_n = _city_count_neighbors(zone, r, c, rows, cols, Z_INDUSTRIAL)
            lv -= ind_n * 0.4

            # Park neighbors boost value
            park_n = _city_count_neighbors(zone, r, c, rows, cols, Z_PARK)
            lv += park_n * 0.25

            # Ruin neighbors decrease value
            ruin_n = _city_count_neighbors(zone, r, c, rows, cols, Z_RUIN)
            lv -= ruin_n * 0.3

            # Traffic congestion decreases value
            lv -= traffic[r][c] * 0.2

            # Decay pressure
            if decay_grid[r][c] > 0.5:
                lv -= 0.5

            # Distance from center bonus (gentrification pressure)
            cr, cc = rows // 2, cols // 2
            dist_center = math.sqrt((r - cr) ** 2 + (c - cc) ** 2)
            max_dist = math.sqrt(cr ** 2 + cc ** 2)
            centrality = 1.0 - (dist_center / max(max_dist, 1))
            lv += centrality * 0.1

            new_lv[r][c] = max(0.0, min(100.0, lv))
    self.city_land_value = new_lv
    land_value = new_lv

    # ── Phase 2: Traffic simulation ──
    new_traffic = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            pop = population[r][c]
            if pop > 0 and zone[r][c] in (Z_RESIDENTIAL, Z_COMMERCIAL, Z_INDUSTRIAL):
                # People generate traffic toward commercial areas
                commute_amount = pop * 0.05
                # Spread traffic along nearby roads
                for dr in range(-3, 4):
                    for dc in range(-3, 4):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if zone[nr][nc] == Z_ROAD:
                                dist = abs(dr) + abs(dc)
                                new_traffic[nr][nc] += commute_amount / max(dist, 1)
    # Decay old traffic, blend with new
    for r in range(rows):
        for c in range(cols):
            traffic[r][c] = traffic[r][c] * 0.5 + new_traffic[r][c]
            traffic[r][c] = min(traffic[r][c], 20.0)
    self.city_traffic = traffic

    # ── Phase 3: Growth / Zoning changes ──
    changes = []  # (r, c, new_zone, new_density, new_pop)

    for r in range(rows):
        for c in range(cols):
            z = zone[r][c]
            if z == Z_WATER:
                continue

            lv = land_value[r][c]
            road_dist = _city_road_access(zone, r, c, rows, cols)

            if z == Z_EMPTY:
                # ── New development ──
                if road_dist > 3:
                    # Maybe build a road toward population
                    if rng() < 0.002 * growth_rate:
                        res_n = _city_count_neighbors(zone, r, c, rows, cols, Z_RESIDENTIAL)
                        if res_n >= 1:
                            changes.append((r, c, Z_ROAD, 0, 0))
                    continue

                # Zoning probability based on land value and neighbors
                res_n = _city_count_neighbors(zone, r, c, rows, cols, Z_RESIDENTIAL)
                com_n = _city_count_neighbors(zone, r, c, rows, cols, Z_COMMERCIAL)
                ind_n = _city_count_neighbors(zone, r, c, rows, cols, Z_INDUSTRIAL)

                # Residential: attracted to roads, other residential, some commercial
                res_prob = 0.005 * growth_rate
                if road_dist <= 2:
                    res_prob *= 2.0
                if res_n >= 2:
                    res_prob *= 1.5
                if com_n >= 1:
                    res_prob *= 1.3
                if ind_n >= 2:
                    res_prob *= 0.3  # NIMBY
                if lv > 60:
                    res_prob *= 1.5
                elif lv < 30:
                    res_prob *= 0.5

                # Commercial: attracted to high land value, roads, people
                com_prob = 0.003 * growth_rate
                if road_dist <= 1:
                    com_prob *= 3.0
                if res_n >= 2:
                    com_prob *= 2.0  # needs customers
                if lv > 70:
                    com_prob *= 2.0
                if com_n >= 3:
                    com_prob *= 0.5  # saturation

                # Industrial: attracted to roads, repelled by high land value
                ind_prob = 0.002 * growth_rate
                if road_dist <= 1:
                    ind_prob *= 2.0
                if lv < 40:
                    ind_prob *= 2.0
                elif lv > 70:
                    ind_prob *= 0.2  # too expensive
                if ind_n >= 1:
                    ind_prob *= 1.5  # clustering

                # Park: rare, appears in high-value residential areas
                park_prob = 0.0005 * growth_rate
                if res_n >= 3 and lv > 50:
                    park_prob *= 3.0

                # Roll the dice
                roll = rng()
                cumul = 0.0
                for prob, ztype in [(res_prob, Z_RESIDENTIAL), (com_prob, Z_COMMERCIAL),
                                     (ind_prob, Z_INDUSTRIAL), (park_prob, Z_PARK)]:
                    cumul += prob
                    if roll < cumul:
                        if ztype == Z_PARK:
                            changes.append((r, c, Z_PARK, 0, 0))
                        else:
                            init_pop = random.randint(2, 8) if ztype == Z_RESIDENTIAL else random.randint(3, 12)
                            changes.append((r, c, ztype, 1, init_pop))
                        break

            elif z == Z_ROAD:
                # Roads can degrade in post-apocalyptic setting
                if preset_id == "postapoc" and rng() < 0.0005:
                    changes.append((r, c, Z_RUIN, 0, 0))

            elif z in (Z_RESIDENTIAL, Z_COMMERCIAL, Z_INDUSTRIAL):
                # ── Existing zone: density change, population dynamics ──
                d = density[r][c]
                pop = population[r][c]

                if z in total_zones:
                    total_zones[z] += 1
                total_pop += pop

                # Population growth in occupied zones
                if pop > 0:
                    # Growth based on land value and zone type
                    growth = 0.0
                    if z == Z_RESIDENTIAL:
                        com_nearby = _city_count_neighbors(zone, r, c, rows, cols, Z_COMMERCIAL)
                        growth = 0.02 * growth_rate * (1.0 + com_nearby * 0.3)
                        ind_nearby = _city_count_neighbors(zone, r, c, rows, cols, Z_INDUSTRIAL)
                        growth -= 0.01 * ind_nearby  # pollution pushback
                    elif z == Z_COMMERCIAL:
                        res_nearby = _city_count_neighbors(zone, r, c, rows, cols, Z_RESIDENTIAL)
                        growth = 0.015 * growth_rate * (1.0 + res_nearby * 0.2)
                    elif z == Z_INDUSTRIAL:
                        growth = 0.01 * growth_rate
                        if road_dist <= 1:
                            growth *= 1.5

                    # Congestion penalty
                    if traffic[r][c] > 5.0:
                        growth -= 0.005 * traffic[r][c]

                    pop_change = int(pop * growth)
                    if pop_change == 0 and rng() < abs(growth):
                        pop_change = 1 if growth > 0 else -1

                    new_pop = max(0, pop + pop_change)
                    max_pop = (d + 1) * 20
                    new_pop = min(new_pop, max_pop)

                    # Density increase if population warrants
                    new_d = d
                    if d < 5 and new_pop > d * 15 and lv > 40 + d * 10:
                        if rng() < 0.01 * growth_rate:
                            new_d = d + 1
                            new_pop = min(new_pop, (new_d + 1) * 20)

                    if new_pop != pop or new_d != d:
                        changes.append((r, c, z, new_d, new_pop))

                # ── Gentrification ──
                # High land value + low density residential -> commercial takeover
                if z == Z_RESIDENTIAL and d <= 2 and lv > 80:
                    if rng() < 0.003 * growth_rate:
                        changes.append((r, c, Z_COMMERCIAL, d + 1, pop))

                # ── Infrastructure decay ──
                decay_val = decay_grid[r][c]
                if pop == 0 and d > 0:
                    decay_grid[r][c] = min(1.0, decay_val + 0.01)
                elif pop > 0:
                    decay_grid[r][c] = max(0.0, decay_val - 0.005)

                if decay_val > 0.9 and rng() < 0.005:
                    changes.append((r, c, Z_RUIN, 0, 0))

                # ── Migration: abandon high-traffic, low-value zones ──
                if z == Z_RESIDENTIAL and traffic[r][c] > 8.0 and lv < 30:
                    if rng() < 0.01:
                        lost = max(1, pop // 4)
                        changes.append((r, c, z, d, max(0, pop - lost)))

            elif z == Z_RUIN:
                # Ruins can be reclaimed if adjacent to active zones
                active_n = (_city_count_neighbors(zone, r, c, rows, cols, Z_RESIDENTIAL) +
                            _city_count_neighbors(zone, r, c, rows, cols, Z_COMMERCIAL))
                if active_n >= 2 and rng() < 0.003 * growth_rate:
                    changes.append((r, c, Z_RESIDENTIAL, 1, random.randint(1, 5)))
                    decay_grid[r][c] = 0.0

    # ── Phase 4: Road growth ──
    # Extend road network toward population clusters not well-served
    if rng() < 0.05 * growth_rate:
        # Find a populated cell far from roads
        best_r, best_c, best_score = -1, -1, 0
        for _ in range(20):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            if zone[r][c] in (Z_RESIDENTIAL, Z_COMMERCIAL, Z_INDUSTRIAL):
                rd = _city_road_access(zone, r, c, rows, cols)
                score = population[r][c] * rd
                if score > best_score:
                    best_r, best_c, best_score = r, c, score
        if best_r >= 0 and best_score > 10:
            # Build road toward this cell from nearest road
            for dist in range(1, 6):
                for dr in range(-dist, dist + 1):
                    for dc in range(-dist, dist + 1):
                        if abs(dr) + abs(dc) != dist:
                            continue
                        nr, nc = best_r + dr, best_c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and zone[nr][nc] == Z_ROAD:
                            # Build road from road toward target
                            step_r = 1 if best_r > nr else (-1 if best_r < nr else 0)
                            step_c = 1 if best_c > nc else (-1 if best_c < nc else 0)
                            cr, cc = nr, nc
                            for _ in range(dist):
                                if rng() < 0.5 and step_r != 0:
                                    cr += step_r
                                elif step_c != 0:
                                    cc += step_c
                                elif step_r != 0:
                                    cr += step_r
                                if 0 <= cr < rows and 0 <= cc < cols:
                                    if zone[cr][cc] == Z_EMPTY:
                                        changes.append((cr, cc, Z_ROAD, 0, 0))
                            dist = 0  # break outer loops
                            break
                    if dist == 0:
                        break
                if dist == 0:
                    break

    # Apply changes
    for r, c, new_z, new_d, new_pop in changes:
        zone[r][c] = new_z
        density[r][c] = new_d
        population[r][c] = new_pop

    # Update stats
    total_pop = sum(population[r][c] for r in range(rows) for c in range(cols))
    self.city_total_pop = total_pop
    self.city_zone_counts = total_zones
    self.city_avg_land_value = (
        sum(land_value[r][c] for r in range(rows) for c in range(cols)
            if zone[r][c] != Z_WATER) /
        max(1, sum(1 for r in range(rows) for c in range(cols) if zone[r][c] != Z_WATER)))
    self.city_avg_traffic = (
        sum(traffic[r][c] for r in range(rows) for c in range(cols)
            if zone[r][c] == Z_ROAD) /
        max(1, sum(1 for r in range(rows) for c in range(cols) if zone[r][c] == Z_ROAD)))

    # History
    self.city_history.append((total_pop, self.city_avg_land_value, self.city_avg_traffic))
    if len(self.city_history) > 2000:
        self.city_history = self.city_history[-2000:]

    self.city_generation += 1


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _enter_city_mode(self):
    """Enter City Growth mode — show preset menu."""
    self.city_menu = True
    self.city_menu_sel = 0
    self._flash("City Growth & Urban Simulation — select a scenario")


def _exit_city_mode(self):
    """Exit City Growth mode."""
    self.city_mode = False
    self.city_menu = False
    self.city_running = False
    self._flash("City Growth mode OFF")


def _city_init(self, preset_idx: int):
    """Initialize city simulation with the given preset."""
    name, _desc, preset_id = self.CITY_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()

    rows = max(15, max_y - 5)
    cols = max(20, max_x - 2)
    self.city_rows = rows
    self.city_cols = cols

    self.city_preset_name = name
    self.city_preset_id = preset_id
    self.city_generation = 0
    self.city_running = False
    self.city_menu = False
    self.city_mode = True

    self.city_growth_rate = 1.0
    self.city_view = "zone"  # zone, value, traffic, population

    (self.city_zone, self.city_density, self.city_land_value,
     self.city_population, self.city_traffic, self.city_decay) = \
        _city_make_terrain(preset_id, rows, cols)

    self.city_total_pop = sum(
        self.city_population[r][c] for r in range(rows) for c in range(cols))
    self.city_zone_counts = {Z_RESIDENTIAL: 0, Z_COMMERCIAL: 0, Z_INDUSTRIAL: 0}
    self.city_avg_land_value = 50.0
    self.city_avg_traffic = 0.0

    self.city_history = []


# ══════════════════════════════════════════════════════════════════════
#  Key handling
# ══════════════════════════════════════════════════════════════════════

def _handle_city_menu_key(self, key: int) -> bool:
    """Handle input in City Growth preset menu."""
    presets = self.CITY_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.city_menu_sel = (self.city_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.city_menu_sel = (self.city_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._city_init(self.city_menu_sel)
    elif key == ord("q") or key == 27:
        self.city_menu = False
        self._flash("City Growth mode cancelled")
    return True


def _handle_city_key(self, key: int) -> bool:
    """Handle input in active City simulation."""
    if key == ord("q") or key == 27:
        self._exit_city_mode()
        return True
    if key == ord(" "):
        self.city_running = not self.city_running
        return True
    if key == ord("n") or key == ord("."):
        self._city_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.CITY_PRESETS)
             if p[0] == self.city_preset_name), 0)
        self._city_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.city_mode = False
        self.city_running = False
        self.city_menu = True
        self.city_menu_sel = 0
        return True
    # View modes
    if key == ord("v"):
        views = ["zone", "value", "traffic", "population"]
        idx = views.index(self.city_view) if self.city_view in views else 0
        self.city_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.city_view}")
        return True
    # Growth rate
    if key == ord("+") or key == ord("="):
        self.city_growth_rate = min(5.0, self.city_growth_rate * 1.3)
        self._flash(f"Growth rate = {self.city_growth_rate:.2f}")
        return True
    if key == ord("-"):
        self.city_growth_rate = max(0.1, self.city_growth_rate / 1.3)
        self._flash(f"Growth rate = {self.city_growth_rate:.2f}")
        return True
    # Manual zoning: place park
    if key == ord("p"):
        # Place a park near center of view
        cr, cc = self.city_rows // 2, self.city_cols // 2
        for _ in range(10):
            r = cr + random.randint(-5, 5)
            c = cc + random.randint(-5, 5)
            if 0 <= r < self.city_rows and 0 <= c < self.city_cols:
                if self.city_zone[r][c] == Z_EMPTY:
                    self.city_zone[r][c] = Z_PARK
                    self._flash("Park placed!")
                    break
        return True
    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing
# ══════════════════════════════════════════════════════════════════════

def _draw_city_menu(self, max_y: int, max_x: int):
    """Draw the City Growth preset selection menu."""
    self.stdscr.erase()
    title = "── City Growth & Urban Simulation ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(self.CITY_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 8:
            break
        marker = "▸ " if i == self.city_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.city_menu_sel else curses.color_pair(7)
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(y, 3, line[:max_x - 4], attr)
        except curses.error:
            pass
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Legend
    legend_y = max_y - 6
    if legend_y > 0:
        lines = [
            "Zones self-organize via land-value gradients & population pressure.",
            "Emergent: organic road growth, gentrification, NIMBY effects, decay.",
            "Watch residential sprawl, commercial clustering, and traffic feedback.",
        ]
        for i, line in enumerate(lines):
            try:
                self.stdscr.addstr(legend_y + i, 3, line[:max_x - 4],
                                   curses.color_pair(6))
            except curses.error:
                pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_city(self, max_y: int, max_x: int):
    """Draw the active City simulation."""
    self.stdscr.erase()
    state = "▶ RUNNING" if self.city_running else "⏸ PAUSED"
    pop = self.city_total_pop

    title = (f" City: {self.city_preset_name}  |  "
             f"pop={pop}  gen={self.city_generation}"
             f"  view={self.city_view}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if self.city_view == "zone":
        _draw_city_zone_view(self, max_y, max_x)
    elif self.city_view == "value":
        _draw_city_value_view(self, max_y, max_x)
    elif self.city_view == "traffic":
        _draw_city_traffic_view(self, max_y, max_x)
    elif self.city_view == "population":
        _draw_city_pop_view(self, max_y, max_x)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" R={self.city_zone_counts.get(Z_RESIDENTIAL, 0)}"
                f" C={self.city_zone_counts.get(Z_COMMERCIAL, 0)}"
                f" I={self.city_zone_counts.get(Z_INDUSTRIAL, 0)}"
                f"  avgLV={self.city_avg_land_value:.1f}"
                f"  avgTraffic={self.city_avg_traffic:.1f}"
                f"  growth={self.city_growth_rate:.2f}x")
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [+/-]=growth [p]=park [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_city_zone_view(self, max_y, max_x):
    """Draw the zone map."""
    zone = self.city_zone
    density = self.city_density
    rows = self.city_rows
    cols = self.city_cols

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
            if c >= cols:
                break
            z = zone[r][c]
            d = density[r][c]

            if z == Z_EMPTY:
                continue
            elif z == Z_WATER:
                ch = "~"
                attr = curses.color_pair(4) | curses.A_BOLD
            elif z == Z_ROAD:
                ch = "·"
                attr = curses.color_pair(7) | curses.A_DIM
            elif z == Z_RESIDENTIAL:
                chars = DENSITY_CHARS[Z_RESIDENTIAL]
                ch = chars[min(d, len(chars) - 1)]
                if d >= 4:
                    attr = curses.color_pair(2) | curses.A_BOLD
                elif d >= 2:
                    attr = curses.color_pair(2)
                else:
                    attr = curses.color_pair(2) | curses.A_DIM
            elif z == Z_COMMERCIAL:
                chars = DENSITY_CHARS[Z_COMMERCIAL]
                ch = chars[min(d, len(chars) - 1)]
                if d >= 4:
                    attr = curses.color_pair(4) | curses.A_BOLD
                elif d >= 2:
                    attr = curses.color_pair(4)
                else:
                    attr = curses.color_pair(4) | curses.A_DIM
            elif z == Z_INDUSTRIAL:
                chars = DENSITY_CHARS[Z_INDUSTRIAL]
                ch = chars[min(d, len(chars) - 1)]
                if d >= 4:
                    attr = curses.color_pair(5) | curses.A_BOLD
                elif d >= 2:
                    attr = curses.color_pair(5)
                else:
                    attr = curses.color_pair(5) | curses.A_DIM
            elif z == Z_PARK:
                ch = "♣"
                attr = curses.color_pair(3) | curses.A_BOLD
            elif z == Z_RUIN:
                ch = "░"
                attr = curses.color_pair(7) | curses.A_DIM
            else:
                continue

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass


def _draw_city_value_view(self, max_y, max_x):
    """Draw land value heatmap."""
    land_value = self.city_land_value
    zone = self.city_zone
    rows = self.city_rows
    cols = self.city_cols

    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    heat_chars = " ·░▒▓█"

    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break
        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols:
                break
            if zone[r][c] == Z_WATER:
                try:
                    self.stdscr.addstr(screen_y, sx, "~", curses.color_pair(4))
                except curses.error:
                    pass
                continue

            lv = land_value[r][c]
            idx = int(lv / 100.0 * (len(heat_chars) - 1))
            idx = max(0, min(len(heat_chars) - 1, idx))
            ch = heat_chars[idx]
            if ch == " ":
                continue

            if lv > 75:
                attr = curses.color_pair(1) | curses.A_BOLD  # red = expensive
            elif lv > 50:
                attr = curses.color_pair(5)  # magenta
            elif lv > 25:
                attr = curses.color_pair(3)  # green
            else:
                attr = curses.color_pair(4) | curses.A_DIM  # blue = cheap

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass


def _draw_city_traffic_view(self, max_y, max_x):
    """Draw traffic congestion heatmap."""
    traffic = self.city_traffic
    zone = self.city_zone
    rows = self.city_rows
    cols = self.city_cols

    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    heat_chars = " ·░▒▓█"

    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break
        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols:
                break
            if zone[r][c] == Z_WATER:
                try:
                    self.stdscr.addstr(screen_y, sx, "~", curses.color_pair(4))
                except curses.error:
                    pass
                continue

            t = traffic[r][c]
            if t < 0.1:
                if zone[r][c] == Z_ROAD:
                    try:
                        self.stdscr.addstr(screen_y, sx, "·", curses.color_pair(7) | curses.A_DIM)
                    except curses.error:
                        pass
                continue

            idx = int(t / 10.0 * (len(heat_chars) - 1))
            idx = max(0, min(len(heat_chars) - 1, idx))
            ch = heat_chars[idx]
            if ch == " ":
                continue

            if t > 8:
                attr = curses.color_pair(1) | curses.A_BOLD  # red = jammed
            elif t > 4:
                attr = curses.color_pair(5)  # yellow
            elif t > 1:
                attr = curses.color_pair(3)  # green = flowing
            else:
                attr = curses.color_pair(2) | curses.A_DIM

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass


def _draw_city_pop_view(self, max_y, max_x):
    """Draw population density heatmap."""
    population = self.city_population
    zone = self.city_zone
    rows = self.city_rows
    cols = self.city_cols

    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    heat_chars = " ·░▒▓█"

    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break
        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols:
                break
            if zone[r][c] == Z_WATER:
                try:
                    self.stdscr.addstr(screen_y, sx, "~", curses.color_pair(4))
                except curses.error:
                    pass
                continue

            p = population[r][c]
            if p == 0:
                if zone[r][c] == Z_ROAD:
                    try:
                        self.stdscr.addstr(screen_y, sx, "·", curses.color_pair(7) | curses.A_DIM)
                    except curses.error:
                        pass
                continue

            idx = int(p / 50.0 * (len(heat_chars) - 1))
            idx = max(0, min(len(heat_chars) - 1, idx))
            ch = heat_chars[idx]
            if ch == " ":
                ch = "·"

            if p > 40:
                attr = curses.color_pair(1) | curses.A_BOLD
            elif p > 20:
                attr = curses.color_pair(5)
            elif p > 8:
                attr = curses.color_pair(3)
            else:
                attr = curses.color_pair(2) | curses.A_DIM

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register city growth mode methods on the App class."""
    App.CITY_PRESETS = CITY_PRESETS
    App._enter_city_mode = _enter_city_mode
    App._exit_city_mode = _exit_city_mode
    App._city_init = _city_init
    App._city_step = _city_step
    App._handle_city_menu_key = _handle_city_menu_key
    App._handle_city_key = _handle_city_key
    App._draw_city_menu = _draw_city_menu
    App._draw_city = _draw_city
    App._draw_city_zone_view = _draw_city_zone_view
    App._draw_city_value_view = _draw_city_value_view
    App._draw_city_traffic_view = _draw_city_traffic_view
    App._draw_city_pop_view = _draw_city_pop_view
