"""Deep-Sea Bioluminescent Abyss simulation mode.

Models an abyssal ocean zone (1000m+ depth) with:
- Anglerfish lure signaling and predation
- Bioluminescent plankton disturbance cascades (chain-reaction light bursts)
- Giant squid chromatophore countershading
- Marine snow particle drift
- Hydrostatic pressure zones affecting creature metabolism
- Predator-prey interactions through light-based deception in total darkness

Three views: dark abyss scene, depth-pressure cross-section, time-series sparklines.
Six presets.
"""

import math
import random
import curses

# ── Presets ──────────────────────────────────────────────────────────────────

DEEPSEA_PRESETS = [
    ("Midnight Zone Ecosystem",
     "Balanced deep-sea community at 1000-4000m with diverse bioluminescent life",
     "midnight"),
    ("Anglerfish Hunting Ground",
     "Dense anglerfish population luring prey with deceptive bioluminescent lures",
     "anglerfish"),
    ("Bioluminescent Storm",
     "Massive plankton bloom triggers cascading chain-reaction light bursts",
     "biostorm"),
    ("Giant Squid Territory",
     "Giant squid dominate with chromatophore countershading and ink clouds",
     "squid"),
    ("Marine Snow Blizzard",
     "Heavy organic particle rain fuels a dense abyssal food web",
     "snow"),
    ("Abyssal Vent Oasis",
     "Hydrothermal vent chemosynthetic community in the hadal zone",
     "vent"),
]

# ── Constants ────────────────────────────────────────────────────────────────

# Creature types
CR_ANGLERFISH = 0
CR_SQUID = 1
CR_JELLYFISH = 2
CR_LANTERNFISH = 3
CR_HATCHETFISH = 4
CR_DRAGONFISH = 5
CR_SHRIMP = 6
CR_TUBEWORM = 7

CREATURE_NAMES = {
    CR_ANGLERFISH: "Anglerfish",
    CR_SQUID: "Giant Squid",
    CR_JELLYFISH: "Jellyfish",
    CR_LANTERNFISH: "Lanternfish",
    CR_HATCHETFISH: "Hatchetfish",
    CR_DRAGONFISH: "Dragonfish",
    CR_SHRIMP: "Shrimp",
    CR_TUBEWORM: "Tube Worm",
}

CREATURE_GLYPHS = {
    CR_ANGLERFISH: '§',
    CR_SQUID: '¶',
    CR_JELLYFISH: '~',
    CR_LANTERNFISH: '°',
    CR_HATCHETFISH: '◊',
    CR_DRAGONFISH: '≈',
    CR_SHRIMP: ',',
    CR_TUBEWORM: '|',
}

# Depth zones (rows mapped to depth)
ZONE_MESOPELAGIC = 0   # 200-1000m
ZONE_BATHYPELAGIC = 1  # 1000-4000m
ZONE_ABYSSOPELAGIC = 2 # 4000-6000m
ZONE_HADAL = 3         # 6000m+

ZONE_NAMES = ["Mesopelagic", "Bathypelagic", "Abyssopelagic", "Hadal"]
ZONE_DEPTHS = ["200-1000m", "1000-4000m", "4000-6000m", "6000m+"]
ZONE_PRESSURE = [100, 400, 600, 1100]  # atm

# Views
VIEW_ABYSS = "abyss"
VIEW_DEPTH = "depth"
VIEW_GRAPH = "graph"
VIEWS = [VIEW_ABYSS, VIEW_DEPTH, VIEW_GRAPH]
VIEW_LABELS = {VIEW_ABYSS: "Dark Abyss", VIEW_DEPTH: "Depth Section", VIEW_GRAPH: "Time Series"}

# Flash chars for bioluminescence intensity
_FLASH_CHARS = [' ', '·', '∙', '•', '○', '◎', '●', '◉', '*', '✦', '✧']
_SNOW_CHARS = ['.', ':', '·', ',']

# ── Creature class ───────────────────────────────────────────────────────────

class _Creature:
    __slots__ = ("x", "y", "ctype", "alive", "energy", "max_energy",
                 "flash_bright", "flash_timer", "flash_cooldown",
                 "lure_active", "lure_bright",
                 "vx", "vy", "speed", "size",
                 "metabolism", "prey_target", "state",
                 "chromatophore", "ink_cooldown",
                 "age", "depth_pref_min", "depth_pref_max")

    def __init__(self, x, y, ctype):
        self.x = x
        self.y = y
        self.ctype = ctype
        self.alive = True
        self.energy = 80.0
        self.max_energy = 100.0
        self.flash_bright = 0.0
        self.flash_timer = 0
        self.flash_cooldown = 0
        self.lure_active = False
        self.lure_bright = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 0.3
        self.size = 1.0
        self.metabolism = 1.0
        self.prey_target = None
        self.state = "idle"  # idle, hunting, fleeing, feeding, luring
        self.chromatophore = 0.0  # 0=dark, 1=bright (squid countershading)
        self.ink_cooldown = 0
        self.age = 0
        self.depth_pref_min = 0.0
        self.depth_pref_max = 1.0


class _Plankton:
    __slots__ = ("x", "y", "bright", "trigger_timer", "alive", "energy")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.bright = 0.0
        self.trigger_timer = 0
        self.alive = True
        self.energy = 30.0


class _Snow:
    __slots__ = ("x", "y", "size", "drift")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = random.random() * 0.8 + 0.2
        self.drift = random.uniform(-0.3, 0.3)


class _Vent:
    __slots__ = ("x", "y", "strength", "radius", "plume_phase")

    def __init__(self, x, y, strength=1.0):
        self.x = x
        self.y = y
        self.strength = strength
        self.radius = int(3 + strength * 4)
        self.plume_phase = random.random() * math.pi * 2


# ── Helper functions ─────────────────────────────────────────────────────────

def _dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _zone_for_row(row, total_rows):
    """Map a row to a depth zone."""
    frac = row / max(1, total_rows - 1)
    if frac < 0.2:
        return ZONE_MESOPELAGIC
    elif frac < 0.55:
        return ZONE_BATHYPELAGIC
    elif frac < 0.8:
        return ZONE_ABYSSOPELAGIC
    else:
        return ZONE_HADAL


def _pressure_at_row(row, total_rows):
    """Approximate pressure in atm based on depth."""
    frac = row / max(1, total_rows - 1)
    return 100 + frac * 1000


def _metabolism_factor(row, total_rows):
    """Deeper = slower metabolism due to cold and pressure."""
    frac = row / max(1, total_rows - 1)
    return max(0.3, 1.0 - frac * 0.6)


def _init_creature(c, ctype, rows, cols, preset_id):
    """Configure creature stats based on type."""
    if ctype == CR_ANGLERFISH:
        c.speed = 0.15
        c.size = 2.5
        c.max_energy = 150.0
        c.energy = 150.0
        c.metabolism = 0.4
        c.depth_pref_min = 0.2
        c.depth_pref_max = 0.8
        c.lure_active = True
        c.lure_bright = 0.0
    elif ctype == CR_SQUID:
        c.speed = 0.6
        c.size = 4.0
        c.max_energy = 200.0
        c.energy = 200.0
        c.metabolism = 0.8
        c.depth_pref_min = 0.1
        c.depth_pref_max = 0.7
    elif ctype == CR_JELLYFISH:
        c.speed = 0.08
        c.size = 1.5
        c.max_energy = 60.0
        c.energy = 60.0
        c.metabolism = 0.2
        c.depth_pref_min = 0.0
        c.depth_pref_max = 0.9
    elif ctype == CR_LANTERNFISH:
        c.speed = 0.4
        c.size = 0.8
        c.max_energy = 50.0
        c.energy = 50.0
        c.metabolism = 0.6
        c.depth_pref_min = 0.0
        c.depth_pref_max = 0.5
    elif ctype == CR_HATCHETFISH:
        c.speed = 0.35
        c.size = 0.6
        c.max_energy = 40.0
        c.energy = 40.0
        c.metabolism = 0.5
        c.depth_pref_min = 0.1
        c.depth_pref_max = 0.4
    elif ctype == CR_DRAGONFISH:
        c.speed = 0.25
        c.size = 2.0
        c.max_energy = 120.0
        c.energy = 120.0
        c.metabolism = 0.5
        c.depth_pref_min = 0.3
        c.depth_pref_max = 0.9
    elif ctype == CR_SHRIMP:
        c.speed = 0.3
        c.size = 0.4
        c.max_energy = 30.0
        c.energy = 30.0
        c.metabolism = 0.4
        c.depth_pref_min = 0.2
        c.depth_pref_max = 1.0
    elif ctype == CR_TUBEWORM:
        c.speed = 0.0
        c.size = 1.0
        c.max_energy = 200.0
        c.energy = 200.0
        c.metabolism = 0.1
        c.depth_pref_min = 0.8
        c.depth_pref_max = 1.0


def _sparkline(values, width, height, max_y_scr, max_x_scr, start_y, start_x,
               stdscr, color_pair, label=""):
    """Draw a sparkline graph."""
    if not values or height < 2 or width < 4:
        return
    # Trim label
    if label and start_x + len(label) + 1 < max_x_scr and start_y < max_y_scr:
        try:
            stdscr.addstr(start_y, start_x, label[:width],
                          color_pair | curses.A_BOLD)
        except curses.error:
            pass
        start_y += 1
        height -= 1

    recent = values[-width:] if len(values) > width else values
    if not recent:
        return
    mn = min(recent)
    mx = max(recent)
    rng = mx - mn if mx > mn else 1.0

    blocks = " ▁▂▃▄▅▆▇█"
    for i, v in enumerate(recent):
        col = start_x + i
        if col >= max_x_scr - 1:
            break
        norm = (v - mn) / rng
        idx = int(norm * (len(blocks) - 1))
        ch = blocks[idx]
        row = start_y + height - 1
        if 0 <= row < max_y_scr:
            try:
                stdscr.addstr(row, col, ch, color_pair)
            except curses.error:
                pass


# ── Mode functions ───────────────────────────────────────────────────────────

def _enter_deepsea_mode(self):
    """Enter Deep-Sea Bioluminescent Abyss mode — show preset menu."""
    self.deepsea_mode = True
    self.deepsea_menu = True
    self.deepsea_menu_sel = 0


def _exit_deepsea_mode(self):
    """Exit Deep-Sea mode — cleanup all state."""
    self.deepsea_mode = False
    self.deepsea_menu = False
    self.deepsea_running = False
    for attr in list(vars(self)):
        if attr.startswith('deepsea_') and attr != 'deepsea_mode':
            try:
                delattr(self, attr)
            except AttributeError:
                pass


def _deepsea_init(self, preset_idx):
    """Initialize simulation from chosen preset."""
    name, desc, preset_id = DEEPSEA_PRESETS[preset_idx]
    self.deepsea_preset_name = name
    self.deepsea_preset_id = preset_id
    self.deepsea_preset_idx = preset_idx

    max_y, max_x = self.stdscr.getmaxyx()
    self.deepsea_rows = max(20, max_y - 4)
    self.deepsea_cols = max(40, max_x - 1)
    rows = self.deepsea_rows
    cols = self.deepsea_cols

    self.deepsea_generation = 0
    self.deepsea_view = VIEW_ABYSS
    self.deepsea_running = False
    self.deepsea_max_history = 200

    # History buffers
    self.deepsea_flash_history = []
    self.deepsea_predation_history = []
    self.deepsea_plankton_history = []
    self.deepsea_creature_history = []
    self.deepsea_snow_history = []
    self.deepsea_anglerfish_history = []
    self.deepsea_squid_history = []
    self.deepsea_jellyfish_history = []
    self.deepsea_cascade_history = []
    self.deepsea_energy_history = []

    # Stats
    self.deepsea_total_flashes = 0
    self.deepsea_total_predations = 0
    self.deepsea_total_cascades = 0

    # Flash map for rendering glow effects
    self.deepsea_flash_map = [[0.0] * cols for _ in range(rows)]

    # Vents
    self.deepsea_vents = []

    # Preset-specific configuration
    n_creatures = {}
    n_plankton = 0
    n_snow = 0
    n_vents = 0

    if preset_id == "midnight":
        n_creatures = {
            CR_ANGLERFISH: 4, CR_SQUID: 2, CR_JELLYFISH: 15,
            CR_LANTERNFISH: 25, CR_HATCHETFISH: 15, CR_DRAGONFISH: 3,
            CR_SHRIMP: 20, CR_TUBEWORM: 0,
        }
        n_plankton = min(400, rows * cols // 8)
        n_snow = 60
        n_vents = 0
    elif preset_id == "anglerfish":
        n_creatures = {
            CR_ANGLERFISH: 12, CR_SQUID: 1, CR_JELLYFISH: 8,
            CR_LANTERNFISH: 40, CR_HATCHETFISH: 20, CR_DRAGONFISH: 2,
            CR_SHRIMP: 25, CR_TUBEWORM: 0,
        }
        n_plankton = min(300, rows * cols // 10)
        n_snow = 40
        n_vents = 0
    elif preset_id == "biostorm":
        n_creatures = {
            CR_ANGLERFISH: 2, CR_SQUID: 1, CR_JELLYFISH: 25,
            CR_LANTERNFISH: 15, CR_HATCHETFISH: 10, CR_DRAGONFISH: 1,
            CR_SHRIMP: 15, CR_TUBEWORM: 0,
        }
        n_plankton = min(1200, rows * cols // 3)
        n_snow = 30
        n_vents = 0
    elif preset_id == "squid":
        n_creatures = {
            CR_ANGLERFISH: 2, CR_SQUID: 8, CR_JELLYFISH: 10,
            CR_LANTERNFISH: 20, CR_HATCHETFISH: 10, CR_DRAGONFISH: 2,
            CR_SHRIMP: 15, CR_TUBEWORM: 0,
        }
        n_plankton = min(350, rows * cols // 9)
        n_snow = 50
        n_vents = 0
    elif preset_id == "snow":
        n_creatures = {
            CR_ANGLERFISH: 3, CR_SQUID: 1, CR_JELLYFISH: 12,
            CR_LANTERNFISH: 20, CR_HATCHETFISH: 15, CR_DRAGONFISH: 2,
            CR_SHRIMP: 30, CR_TUBEWORM: 5,
        }
        n_plankton = min(500, rows * cols // 6)
        n_snow = 200
        n_vents = 0
    elif preset_id == "vent":
        n_creatures = {
            CR_ANGLERFISH: 2, CR_SQUID: 1, CR_JELLYFISH: 8,
            CR_LANTERNFISH: 10, CR_HATCHETFISH: 5, CR_DRAGONFISH: 2,
            CR_SHRIMP: 35, CR_TUBEWORM: 20,
        }
        n_plankton = min(400, rows * cols // 8)
        n_snow = 40
        n_vents = 4

    # Create vents
    for _ in range(n_vents):
        vx = random.randint(5, cols - 6)
        vy = rows - random.randint(1, max(2, rows // 8))
        self.deepsea_vents.append(_Vent(vx, vy, random.uniform(0.6, 1.2)))

    # Create creatures
    creatures = []
    for ctype, count in n_creatures.items():
        for _ in range(count):
            cx = random.uniform(1, cols - 2)
            cy_min = 1
            cy_max = rows - 2
            cy = random.uniform(cy_min, cy_max)
            c = _Creature(cx, cy, ctype)
            _init_creature(c, ctype, rows, cols, preset_id)
            # Place in preferred depth zone
            frac_min = c.depth_pref_min
            frac_max = c.depth_pref_max
            c.y = random.uniform(frac_min * rows, frac_max * rows)
            c.y = _clamp(c.y, 1, rows - 2)
            creatures.append(c)
    self.deepsea_creatures = creatures

    # Create plankton
    plankton = []
    for _ in range(n_plankton):
        px = random.uniform(0, cols - 1)
        py = random.uniform(0, rows - 1)
        p = _Plankton(px, py)
        plankton.append(p)
    self.deepsea_plankton = plankton

    # Create marine snow
    snow = []
    for _ in range(n_snow):
        sx = random.uniform(0, cols - 1)
        sy = random.uniform(0, rows - 1)
        snow.append(_Snow(sx, sy))
    self.deepsea_snow = snow

    # Ink clouds: list of (x, y, radius, age)
    self.deepsea_ink_clouds = []


def _deepsea_step(self):
    """Advance simulation by one tick."""
    self.deepsea_generation += 1
    gen = self.deepsea_generation
    rows = self.deepsea_rows
    cols = self.deepsea_cols
    creatures = self.deepsea_creatures
    plankton = self.deepsea_plankton
    snow = self.deepsea_snow
    vents = self.deepsea_vents
    flash_map = self.deepsea_flash_map

    tick_flashes = 0
    tick_predations = 0
    tick_cascades = 0

    # ── Decay flash map ──
    for r in range(rows):
        for c in range(cols):
            flash_map[r][c] *= 0.7

    # ── Marine snow drift ──
    for s in snow:
        s.y += 0.15 + s.size * 0.1
        s.x += s.drift + math.sin(gen * 0.05 + s.x * 0.1) * 0.1
        if s.y >= rows:
            s.y = 0
            s.x = random.uniform(0, cols - 1)
            s.drift = random.uniform(-0.3, 0.3)

    # ── Vent plumes ──
    for v in vents:
        v.plume_phase += 0.1
        # Vents feed nearby tubeworms and attract shrimp
        for c in creatures:
            if not c.alive:
                continue
            d = _dist(c.x, c.y, v.x, v.y)
            if d < v.radius:
                if c.ctype in (CR_TUBEWORM, CR_SHRIMP):
                    c.energy = min(c.max_energy, c.energy + 0.5 * v.strength)

    # ── Plankton bioluminescence cascade ──
    for p in plankton:
        if not p.alive:
            continue
        # Decay brightness
        if p.bright > 0:
            p.bright *= 0.85
            if p.bright < 0.02:
                p.bright = 0.0
        if p.trigger_timer > 0:
            p.trigger_timer -= 1

        # Energy drain
        p.energy -= 0.01
        if p.energy <= 0:
            p.alive = False
            continue

        # Marine snow feeds plankton
        for s in snow:
            if abs(p.x - s.x) < 1.5 and abs(p.y - s.y) < 1.5:
                p.energy = min(30.0, p.energy + 0.3)
                break

    # Trigger cascade: creatures moving near plankton disturb them
    for c in creatures:
        if not c.alive:
            continue
        speed_sq = c.vx * c.vx + c.vy * c.vy
        if speed_sq < 0.01:
            continue
        disturb_r = 2.0 + c.size
        for p in plankton:
            if not p.alive or p.trigger_timer > 0:
                continue
            if abs(p.x - c.x) < disturb_r and abs(p.y - c.y) < disturb_r:
                d = _dist(p.x, p.y, c.x, c.y)
                if d < disturb_r:
                    p.bright = min(1.0, p.bright + 0.6)
                    p.trigger_timer = 8
                    tick_flashes += 1
                    pr, pc_ = int(p.y), int(p.x)
                    if 0 <= pr < rows and 0 <= pc_ < cols:
                        flash_map[pr][pc_] = min(1.0, flash_map[pr][pc_] + 0.5)

    # Cascade propagation: bright plankton trigger neighbors
    cascade_triggered = True
    cascade_rounds = 0
    while cascade_triggered and cascade_rounds < 3:
        cascade_triggered = False
        cascade_rounds += 1
        for p in plankton:
            if not p.alive or p.bright < 0.3 or p.trigger_timer != 7:
                continue
            # Trigger nearby plankton
            for p2 in plankton:
                if p2 is p or not p2.alive or p2.trigger_timer > 0:
                    continue
                d = _dist(p.x, p.y, p2.x, p2.y)
                if d < 3.0:
                    cascade_strength = p.bright * (1.0 - d / 3.0) * 0.5
                    if cascade_strength > 0.15:
                        p2.bright = min(1.0, p2.bright + cascade_strength)
                        p2.trigger_timer = 7
                        cascade_triggered = True
                        tick_cascades += 1
                        tick_flashes += 1
                        pr, pc_ = int(p2.y), int(p2.x)
                        if 0 <= pr < rows and 0 <= pc_ < cols:
                            flash_map[pr][pc_] = min(1.0, flash_map[pr][pc_] + 0.3)

    # ── Creature behavior ──
    alive_creatures = [c for c in creatures if c.alive]
    for c in creatures:
        if not c.alive:
            continue
        c.age += 1
        if c.flash_cooldown > 0:
            c.flash_cooldown -= 1
        if c.ink_cooldown > 0:
            c.ink_cooldown -= 1

        # Metabolism cost (affected by depth pressure)
        meta_factor = _metabolism_factor(c.y, rows)
        c.energy -= c.metabolism * meta_factor * 0.15

        # Death from starvation
        if c.energy <= 0:
            c.alive = False
            continue

        # Decay flash
        if c.flash_bright > 0:
            c.flash_bright *= 0.8
            if c.flash_bright < 0.02:
                c.flash_bright = 0.0

        # Type-specific behavior
        if c.ctype == CR_ANGLERFISH:
            _anglerfish_behavior(c, alive_creatures, plankton, flash_map,
                                 rows, cols, gen)
            if c.prey_target and not c.prey_target.alive:
                c.prey_target = None
                c.state = "luring"
        elif c.ctype == CR_SQUID:
            _squid_behavior(c, alive_creatures, plankton, flash_map,
                            rows, cols, gen, self.deepsea_ink_clouds)
        elif c.ctype == CR_JELLYFISH:
            _jellyfish_behavior(c, plankton, flash_map, rows, cols, gen)
        elif c.ctype == CR_LANTERNFISH:
            _prey_fish_behavior(c, alive_creatures, flash_map, rows, cols, gen)
        elif c.ctype == CR_HATCHETFISH:
            _prey_fish_behavior(c, alive_creatures, flash_map, rows, cols, gen)
        elif c.ctype == CR_DRAGONFISH:
            _dragonfish_behavior(c, alive_creatures, flash_map, rows, cols, gen)
        elif c.ctype == CR_SHRIMP:
            _shrimp_behavior(c, alive_creatures, flash_map, rows, cols, gen)
        elif c.ctype == CR_TUBEWORM:
            # Sessile — just pulse gently
            if gen % 20 == 0:
                c.flash_bright = 0.3
                cr, cc = int(c.y), int(c.x)
                if 0 <= cr < rows and 0 <= cc < cols:
                    flash_map[cr][cc] = min(1.0, flash_map[cr][cc] + 0.2)

        # Predation check
        if c.ctype in (CR_ANGLERFISH, CR_SQUID, CR_DRAGONFISH) and c.state == "hunting":
            prey = c.prey_target
            if prey and prey.alive:
                d = _dist(c.x, c.y, prey.x, prey.y)
                if d < 1.5:
                    # Capture!
                    prey.alive = False
                    c.energy = min(c.max_energy, c.energy + prey.energy * 0.6)
                    c.state = "idle"
                    c.prey_target = None
                    tick_predations += 1
                    # Flash on capture
                    c.flash_bright = 1.0
                    cr, cc = int(c.y), int(c.x)
                    if 0 <= cr < rows and 0 <= cc < cols:
                        flash_map[cr][cc] = 1.0
                    tick_flashes += 1

        # Movement with bounds
        c.x += c.vx
        c.y += c.vy
        c.x = _clamp(c.x, 0, cols - 1)
        c.y = _clamp(c.y, 0, rows - 1)

        # Depth preference drift
        frac = c.y / max(1, rows - 1)
        if frac < c.depth_pref_min:
            c.vy += 0.05
        elif frac > c.depth_pref_max:
            c.vy -= 0.05

        # Damping
        c.vx *= 0.9
        c.vy *= 0.9

    # ── Age ink clouds ──
    new_ink = []
    for ix, iy, ir, ia in self.deepsea_ink_clouds:
        ia += 1
        ir += 0.2
        if ia < 30:
            new_ink.append((ix, iy, ir, ia))
    self.deepsea_ink_clouds = new_ink

    # ── Respawn dead creatures occasionally ──
    alive_count = sum(1 for c in creatures if c.alive)
    if alive_count < len(creatures) * 0.4 and gen % 30 == 0:
        for c in creatures:
            if not c.alive and random.random() < 0.15:
                c.alive = True
                c.energy = c.max_energy * 0.7
                c.x = random.uniform(1, cols - 2)
                c.y = random.uniform(c.depth_pref_min * rows, c.depth_pref_max * rows)
                c.y = _clamp(c.y, 1, rows - 2)
                c.flash_bright = 0.0
                c.state = "idle"
                c.prey_target = None
                c.age = 0

    # ── Respawn plankton ──
    alive_plankton = sum(1 for p in plankton if p.alive)
    if alive_plankton < len(plankton) * 0.6 and gen % 10 == 0:
        for p in plankton:
            if not p.alive and random.random() < 0.2:
                p.alive = True
                p.energy = 30.0
                p.bright = 0.0
                p.trigger_timer = 0
                p.x = random.uniform(0, cols - 1)
                p.y = random.uniform(0, rows - 1)

    # ── Update stats ──
    self.deepsea_total_flashes += tick_flashes
    self.deepsea_total_predations += tick_predations
    self.deepsea_total_cascades += tick_cascades

    # Record history
    mh = self.deepsea_max_history
    self.deepsea_flash_history.append(tick_flashes)
    if len(self.deepsea_flash_history) > mh:
        self.deepsea_flash_history.pop(0)
    self.deepsea_predation_history.append(tick_predations)
    if len(self.deepsea_predation_history) > mh:
        self.deepsea_predation_history.pop(0)
    self.deepsea_plankton_history.append(alive_plankton)
    if len(self.deepsea_plankton_history) > mh:
        self.deepsea_plankton_history.pop(0)
    self.deepsea_creature_history.append(alive_count)
    if len(self.deepsea_creature_history) > mh:
        self.deepsea_creature_history.pop(0)

    snow_count = len(snow)
    self.deepsea_snow_history.append(snow_count)
    if len(self.deepsea_snow_history) > mh:
        self.deepsea_snow_history.pop(0)

    angler_ct = sum(1 for c in creatures if c.alive and c.ctype == CR_ANGLERFISH)
    squid_ct = sum(1 for c in creatures if c.alive and c.ctype == CR_SQUID)
    jelly_ct = sum(1 for c in creatures if c.alive and c.ctype == CR_JELLYFISH)
    self.deepsea_anglerfish_history.append(angler_ct)
    if len(self.deepsea_anglerfish_history) > mh:
        self.deepsea_anglerfish_history.pop(0)
    self.deepsea_squid_history.append(squid_ct)
    if len(self.deepsea_squid_history) > mh:
        self.deepsea_squid_history.pop(0)
    self.deepsea_jellyfish_history.append(jelly_ct)
    if len(self.deepsea_jellyfish_history) > mh:
        self.deepsea_jellyfish_history.pop(0)

    self.deepsea_cascade_history.append(tick_cascades)
    if len(self.deepsea_cascade_history) > mh:
        self.deepsea_cascade_history.pop(0)

    avg_energy = 0
    if alive_count > 0:
        avg_energy = sum(c.energy for c in creatures if c.alive) / alive_count
    self.deepsea_energy_history.append(avg_energy)
    if len(self.deepsea_energy_history) > mh:
        self.deepsea_energy_history.pop(0)


# ── Creature behaviors ───────────────────────────────────────────────────────

def _anglerfish_behavior(c, alive_creatures, plankton, flash_map,
                         rows, cols, gen):
    """Anglerfish: lure with bioluminescent esca, ambush prey."""
    # Pulse lure
    c.lure_bright = 0.4 + 0.4 * math.sin(gen * 0.15 + c.x)
    if c.lure_bright > 0.5:
        cr, cc = int(c.y), int(c.x)
        if 0 <= cr < rows and 0 <= cc < cols:
            flash_map[cr][cc] = min(1.0, flash_map[cr][cc] + c.lure_bright * 0.4)

    if c.state == "luring" or c.state == "idle":
        c.state = "luring"
        # Wait for prey to approach the lure
        best_prey = None
        best_d = 8.0
        for other in alive_creatures:
            if other is c or not other.alive:
                continue
            if other.ctype in (CR_ANGLERFISH, CR_SQUID, CR_DRAGONFISH):
                continue  # Don't hunt other predators
            d = _dist(c.x, c.y, other.x, other.y)
            if d < best_d:
                best_d = d
                best_prey = other
        if best_prey and best_d < 5.0:
            c.prey_target = best_prey
            c.state = "hunting"
        else:
            # Slow drift
            c.vx += random.uniform(-0.02, 0.02)
            c.vy += random.uniform(-0.02, 0.02)

    elif c.state == "hunting":
        prey = c.prey_target
        if prey and prey.alive:
            dx = prey.x - c.x
            dy = prey.y - c.y
            d = max(0.1, math.sqrt(dx * dx + dy * dy))
            # Slow approach
            c.vx += (dx / d) * 0.03
            c.vy += (dy / d) * 0.03
        else:
            c.state = "luring"
            c.prey_target = None


def _squid_behavior(c, alive_creatures, plankton, flash_map,
                    rows, cols, gen, ink_clouds):
    """Giant squid: chromatophore countershading, ink defense, active hunting."""
    # Countershading: match ambient darkness (deeper = darker)
    depth_frac = c.y / max(1, rows - 1)
    c.chromatophore = max(0.0, 1.0 - depth_frac * 1.5)

    # Threat detection — flee from larger predators (dragonfish)
    nearest_threat = None
    threat_d = 12.0
    for other in alive_creatures:
        if other is c or not other.alive:
            continue
        if other.ctype == CR_DRAGONFISH and other.size >= c.size:
            d = _dist(c.x, c.y, other.x, other.y)
            if d < threat_d:
                threat_d = d
                nearest_threat = other

    if nearest_threat and threat_d < 6.0:
        # Flee and ink
        dx = c.x - nearest_threat.x
        dy = c.y - nearest_threat.y
        d = max(0.1, math.sqrt(dx * dx + dy * dy))
        c.vx += (dx / d) * 0.15
        c.vy += (dy / d) * 0.15
        if c.ink_cooldown <= 0:
            ink_clouds.append((c.x, c.y, 1.5, 0))
            c.ink_cooldown = 40
            # Flash to startle
            c.flash_bright = 0.8
            cr, cc = int(c.y), int(c.x)
            if 0 <= cr < rows and 0 <= cc < cols:
                flash_map[cr][cc] = min(1.0, flash_map[cr][cc] + 0.6)
        c.state = "fleeing"
        return

    # Hunt smaller creatures
    if c.state != "hunting" or not c.prey_target or not c.prey_target.alive:
        best = None
        best_d = 10.0
        for other in alive_creatures:
            if other is c or not other.alive:
                continue
            if other.size < c.size * 0.6:
                d = _dist(c.x, c.y, other.x, other.y)
                if d < best_d:
                    best_d = d
                    best = other
        if best:
            c.prey_target = best
            c.state = "hunting"
        else:
            c.state = "idle"
            c.vx += random.uniform(-0.08, 0.08)
            c.vy += random.uniform(-0.08, 0.08)
            return

    if c.state == "hunting" and c.prey_target and c.prey_target.alive:
        prey = c.prey_target
        dx = prey.x - c.x
        dy = prey.y - c.y
        d = max(0.1, math.sqrt(dx * dx + dy * dy))
        c.vx += (dx / d) * 0.08
        c.vy += (dy / d) * 0.08
        # Bioluminescent flash during chase
        if d < 4.0 and c.flash_cooldown <= 0:
            c.flash_bright = 0.6
            c.flash_cooldown = 15
            cr, cc = int(c.y), int(c.x)
            if 0 <= cr < rows and 0 <= cc < cols:
                flash_map[cr][cc] = min(1.0, flash_map[cr][cc] + 0.4)


def _jellyfish_behavior(c, plankton, flash_map, rows, cols, gen):
    """Jellyfish: passive drift with rhythmic bioluminescent pulses."""
    # Gentle sinusoidal drift
    c.vx += math.sin(gen * 0.03 + c.y * 0.1) * 0.01
    c.vy += math.cos(gen * 0.02 + c.x * 0.1) * 0.01 - 0.005  # slight upward

    # Periodic glow pulse
    pulse = 0.5 + 0.5 * math.sin(gen * 0.1 + c.x + c.y)
    if pulse > 0.8:
        c.flash_bright = pulse * 0.5
        cr, cc = int(c.y), int(c.x)
        if 0 <= cr < rows and 0 <= cc < cols:
            flash_map[cr][cc] = min(1.0, flash_map[cr][cc] + pulse * 0.3)

    # Feed on nearby plankton
    for p in plankton:
        if p.alive and _dist(c.x, c.y, p.x, p.y) < 2.0:
            p.alive = False
            c.energy = min(c.max_energy, c.energy + 5.0)
            break


def _prey_fish_behavior(c, alive_creatures, flash_map, rows, cols, gen):
    """Lanternfish/Hatchetfish: schooling, flee predators, counterillumination."""
    # Counterillumination: ventral photophores match dim light from above
    depth_frac = c.y / max(1, rows - 1)
    if depth_frac < 0.4:
        c.flash_bright = max(c.flash_bright, 0.15 * (1.0 - depth_frac))

    # Flee nearest predator
    nearest_pred = None
    pred_d = 15.0
    for other in alive_creatures:
        if other is c or not other.alive:
            continue
        if other.ctype in (CR_ANGLERFISH, CR_SQUID, CR_DRAGONFISH):
            d = _dist(c.x, c.y, other.x, other.y)
            if d < pred_d:
                pred_d = d
                nearest_pred = other

    if nearest_pred and pred_d < 6.0:
        dx = c.x - nearest_pred.x
        dy = c.y - nearest_pred.y
        d = max(0.1, math.sqrt(dx * dx + dy * dy))
        c.vx += (dx / d) * 0.12
        c.vy += (dy / d) * 0.12
        c.state = "fleeing"
        # Panic flash
        if c.flash_cooldown <= 0:
            c.flash_bright = 0.7
            c.flash_cooldown = 10
            cr, cc = int(c.y), int(c.x)
            if 0 <= cr < rows and 0 <= cc < cols:
                flash_map[cr][cc] = min(1.0, flash_map[cr][cc] + 0.3)
    else:
        c.state = "idle"
        # School with same-type neighbors
        sx, sy, cnt = 0.0, 0.0, 0
        for other in alive_creatures:
            if other is c or not other.alive or other.ctype != c.ctype:
                continue
            d = _dist(c.x, c.y, other.x, other.y)
            if d < 8.0:
                sx += other.x - c.x
                sy += other.y - c.y
                cnt += 1
        if cnt > 0:
            c.vx += (sx / cnt) * 0.02
            c.vy += (sy / cnt) * 0.02

        # Attracted to anglerfish lures (fatal attraction!)
        for other in alive_creatures:
            if other.ctype == CR_ANGLERFISH and other.alive and other.lure_bright > 0.5:
                d = _dist(c.x, c.y, other.x, other.y)
                if 3.0 < d < 12.0:
                    dx = other.x - c.x
                    dy = other.y - c.y
                    dist = max(0.1, math.sqrt(dx * dx + dy * dy))
                    c.vx += (dx / dist) * 0.03 * other.lure_bright
                    c.vy += (dy / dist) * 0.03 * other.lure_bright

        # Random drift
        c.vx += random.uniform(-0.04, 0.04)
        c.vy += random.uniform(-0.04, 0.04)

    # Feed on plankton energy passively
    c.energy = min(c.max_energy, c.energy + 0.05)


def _dragonfish_behavior(c, alive_creatures, flash_map, rows, cols, gen):
    """Dragonfish: red bioluminescent searchlight, active predator."""
    # Dragonfish has red photophores invisible to most prey
    # Periodic red flash (rendered differently)
    if gen % 8 == 0:
        c.flash_bright = 0.5
        cr, cc = int(c.y), int(c.x)
        if 0 <= cr < rows and 0 <= cc < cols:
            flash_map[cr][cc] = min(1.0, flash_map[cr][cc] + 0.3)

    # Hunt
    if not c.prey_target or not c.prey_target.alive:
        best = None
        best_d = 12.0
        for other in alive_creatures:
            if other is c or not other.alive:
                continue
            if other.ctype in (CR_LANTERNFISH, CR_HATCHETFISH, CR_SHRIMP, CR_JELLYFISH):
                d = _dist(c.x, c.y, other.x, other.y)
                if d < best_d:
                    best_d = d
                    best = other
        if best:
            c.prey_target = best
            c.state = "hunting"
        else:
            c.state = "idle"
            c.vx += random.uniform(-0.04, 0.04)
            c.vy += random.uniform(-0.04, 0.04)
    else:
        prey = c.prey_target
        dx = prey.x - c.x
        dy = prey.y - c.y
        d = max(0.1, math.sqrt(dx * dx + dy * dy))
        c.vx += (dx / d) * 0.06
        c.vy += (dy / d) * 0.06


def _shrimp_behavior(c, alive_creatures, flash_map, rows, cols, gen):
    """Shrimp: bioluminescent vomit defense, scavenging."""
    # Flee predators with luminous spew
    nearest_pred = None
    pred_d = 8.0
    for other in alive_creatures:
        if other is c or not other.alive:
            continue
        if other.ctype in (CR_ANGLERFISH, CR_DRAGONFISH, CR_SQUID):
            d = _dist(c.x, c.y, other.x, other.y)
            if d < pred_d:
                pred_d = d
                nearest_pred = other

    if nearest_pred and pred_d < 4.0:
        dx = c.x - nearest_pred.x
        dy = c.y - nearest_pred.y
        d = max(0.1, math.sqrt(dx * dx + dy * dy))
        c.vx += (dx / d) * 0.15
        c.vy += (dy / d) * 0.15
        # Bioluminescent vomit
        if c.flash_cooldown <= 0:
            c.flash_bright = 1.0
            c.flash_cooldown = 20
            cr, cc = int(c.y), int(c.x)
            if 0 <= cr < rows and 0 <= cc < cols:
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        rr, rc = cr + dr, cc + dc
                        if 0 <= rr < rows and 0 <= rc < cols:
                            flash_map[rr][rc] = min(1.0, flash_map[rr][rc] + 0.4)
    else:
        c.state = "idle"
        c.vx += random.uniform(-0.05, 0.05)
        c.vy += random.uniform(-0.05, 0.05)
        c.energy = min(c.max_energy, c.energy + 0.03)


# ── Key handlers ─────────────────────────────────────────────────────────────

def _handle_deepsea_menu_key(self, key):
    """Handle keys in preset selection menu."""
    if key == curses.KEY_DOWN or key == ord('j'):
        self.deepsea_menu_sel = (self.deepsea_menu_sel + 1) % len(DEEPSEA_PRESETS)
    elif key == curses.KEY_UP or key == ord('k'):
        self.deepsea_menu_sel = (self.deepsea_menu_sel - 1) % len(DEEPSEA_PRESETS)
    elif key in (ord('\n'), ord(' ')):
        self.deepsea_menu = False
        _deepsea_init(self, self.deepsea_menu_sel)
        self.deepsea_running = True
    elif key == ord('q'):
        _exit_deepsea_mode(self)


def _handle_deepsea_key(self, key):
    """Handle keys during simulation."""
    if key == ord(' '):
        self.deepsea_running = not self.deepsea_running
    elif key == ord('v'):
        idx = VIEWS.index(self.deepsea_view)
        self.deepsea_view = VIEWS[(idx + 1) % len(VIEWS)]
    elif key == ord('r'):
        self.deepsea_menu = True
        self.deepsea_menu_sel = self.deepsea_preset_idx
    elif key == ord('q'):
        _exit_deepsea_mode(self)


# ── Drawing functions ────────────────────────────────────────────────────────

def _draw_deepsea_menu(self, max_y, max_x):
    """Draw preset selection menu."""
    title = "═══ Deep-Sea Bioluminescent Abyss ═══"
    try:
        self.stdscr.addstr(0, max(0, (max_x - len(title)) // 2),
                           title[:max_x - 1], curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "The Abyssal Zone — Where Light Is Life"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(subtitle)) // 2),
                           subtitle[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc, _) in enumerate(DEEPSEA_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        prefix = " ● " if i == self.deepsea_menu_sel else "   "
        label = f"{prefix}{name}"
        attr = curses.A_REVERSE | curses.A_BOLD if i == self.deepsea_menu_sel else 0
        try:
            self.stdscr.addstr(y, 2, label[:max_x - 3], attr)
        except curses.error:
            pass
        if i == self.deepsea_menu_sel and y + 1 < max_y - 2:
            try:
                self.stdscr.addstr(y + 1, 6, desc[:max_x - 7], curses.A_DIM)
            except curses.error:
                pass

    help_y = max_y - 1
    help_text = " ↑↓ Select   ENTER Start   Q Quit"
    try:
        self.stdscr.addstr(help_y, 0, help_text[:max_x - 1],
                           curses.color_pair(7) | curses.A_DIM)
    except curses.error:
        pass


def _draw_deepsea(self, max_y, max_x):
    """Dispatch to the active view."""
    view = self.deepsea_view
    if view == VIEW_ABYSS:
        _draw_deepsea_abyss(self, max_y, max_x)
    elif view == VIEW_DEPTH:
        _draw_deepsea_depth(self, max_y, max_x)
    else:
        _draw_deepsea_graph(self, max_y, max_x)

    # Status bar
    gen = self.deepsea_generation
    alive = sum(1 for c in self.deepsea_creatures if c.alive)
    plankton_alive = sum(1 for p in self.deepsea_plankton if p.alive)
    flashes = self.deepsea_total_flashes
    preds = self.deepsea_total_predations
    vname = VIEW_LABELS.get(view, view)
    status = (f" Gen:{gen}  Creatures:{alive}  Plankton:{plankton_alive}"
              f"  Flashes:{flashes}  Kills:{preds}  [{vname}]")
    try:
        self.stdscr.addstr(max_y - 1, 0, status[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    help_line = " SPACE Pause  V View  R Reset  Q Quit"
    if max_y - 2 > 1:
        try:
            self.stdscr.addstr(max_y - 2, 0, help_line[:max_x - 1],
                               curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass


def _draw_deepsea_abyss(self, max_y, max_x):
    """View 1: Dark abyss with bioluminescent flashes."""
    rows = min(self.deepsea_rows, max_y - 3)
    cols = min(self.deepsea_cols, max_x)
    flash_map = self.deepsea_flash_map
    gen = self.deepsea_generation

    # Background: near-black ocean with subtle depth gradient
    for r in range(rows):
        zone = _zone_for_row(r, rows)
        # Darker as we go deeper
        base_attr = curses.color_pair(7) | curses.A_DIM
        line = []
        for c_ in range(cols):
            fm = flash_map[r][c_] if r < self.deepsea_rows and c_ < self.deepsea_cols else 0
            if fm > 0.05:
                idx = int(fm * (len(_FLASH_CHARS) - 1))
                idx = min(idx, len(_FLASH_CHARS) - 1)
                line.append(_FLASH_CHARS[idx])
            else:
                # Sparse background particles
                if random.random() < 0.002:
                    line.append('·')
                else:
                    line.append(' ')
        row_str = ''.join(line)
        try:
            self.stdscr.addstr(r, 0, row_str[:max_x - 1], base_attr)
        except curses.error:
            pass

    # Draw glow overlay from flash_map
    for r in range(rows):
        for c_ in range(cols):
            if r >= self.deepsea_rows or c_ >= self.deepsea_cols:
                continue
            fm = flash_map[r][c_]
            if fm > 0.15:
                idx = int(fm * (len(_FLASH_CHARS) - 1))
                idx = min(idx, len(_FLASH_CHARS) - 1)
                ch = _FLASH_CHARS[idx]
                if fm > 0.6:
                    attr = curses.color_pair(5) | curses.A_BOLD  # cyan/bright
                elif fm > 0.3:
                    attr = curses.color_pair(4) | curses.A_BOLD  # blue/green
                else:
                    attr = curses.color_pair(7)
                try:
                    self.stdscr.addstr(r, c_, ch, attr)
                except curses.error:
                    pass

    # Draw marine snow
    for s in self.deepsea_snow:
        sr, sc = int(s.y), int(s.x)
        if 0 <= sr < rows and 0 <= sc < cols:
            ch = _SNOW_CHARS[int(s.size * (len(_SNOW_CHARS) - 1))]
            try:
                self.stdscr.addstr(sr, sc, ch, curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass

    # Draw hydrothermal vents
    for v in self.deepsea_vents:
        vy, vx = int(v.y), int(v.x)
        if 0 <= vy < rows and 0 <= vx < cols:
            # Vent opening
            try:
                self.stdscr.addstr(vy, max(0, vx - 1), "▓█▓"[:min(3, max_x - vx + 1)],
                                   curses.color_pair(2) | curses.A_BOLD)
            except curses.error:
                pass
            # Plume above
            plume_h = int(3 + 2 * math.sin(v.plume_phase))
            for ph in range(1, plume_h + 1):
                pr = vy - ph
                if 0 <= pr < rows:
                    wobble = int(math.sin(v.plume_phase + ph * 0.5) * 1.5)
                    px = vx + wobble
                    if 0 <= px < cols:
                        pch = '░' if ph > plume_h // 2 else '▒'
                        try:
                            self.stdscr.addstr(pr, px, pch,
                                               curses.color_pair(2))
                        except curses.error:
                            pass

    # Draw ink clouds
    for ix, iy, ir, ia in self.deepsea_ink_clouds:
        opacity = max(0.0, 1.0 - ia / 30.0)
        r_int = int(ir)
        for dr in range(-r_int, r_int + 1):
            for dc in range(-r_int, r_int + 1):
                rr = int(iy) + dr
                rc = int(ix) + dc
                if 0 <= rr < rows and 0 <= rc < cols:
                    if dr * dr + dc * dc <= r_int * r_int:
                        ch = '▓' if opacity > 0.5 else '░'
                        try:
                            self.stdscr.addstr(rr, rc, ch,
                                               curses.color_pair(7) | curses.A_DIM)
                        except curses.error:
                            pass

    # Draw plankton
    for p in self.deepsea_plankton:
        if not p.alive:
            continue
        pr, pc = int(p.y), int(p.x)
        if 0 <= pr < rows and 0 <= pc < cols:
            if p.bright > 0.05:
                idx = int(p.bright * (len(_FLASH_CHARS) - 1))
                idx = min(idx, len(_FLASH_CHARS) - 1)
                ch = _FLASH_CHARS[idx]
                if p.bright > 0.6:
                    attr = curses.color_pair(5) | curses.A_BOLD
                elif p.bright > 0.3:
                    attr = curses.color_pair(4)
                else:
                    attr = curses.color_pair(7)
                try:
                    self.stdscr.addstr(pr, pc, ch, attr)
                except curses.error:
                    pass

    # Draw creatures
    for c in self.deepsea_creatures:
        if not c.alive:
            continue
        cr, cc = int(c.y), int(c.x)
        if cr < 0 or cr >= rows or cc < 0 or cc >= cols:
            continue

        glyph = CREATURE_GLYPHS.get(c.ctype, '?')

        # Color by type
        if c.ctype == CR_ANGLERFISH:
            # Anglerfish: yellow/amber lure
            if c.lure_bright > 0.4:
                attr = curses.color_pair(4) | curses.A_BOLD
                # Draw lure above
                lr = cr - 1
                if 0 <= lr < rows:
                    lure_ch = '*' if c.lure_bright > 0.6 else '·'
                    try:
                        self.stdscr.addstr(lr, cc, lure_ch,
                                           curses.color_pair(4) | curses.A_BOLD)
                    except curses.error:
                        pass
            else:
                attr = curses.color_pair(7)
        elif c.ctype == CR_SQUID:
            if c.flash_bright > 0.2:
                attr = curses.color_pair(3) | curses.A_BOLD  # red flash
            elif c.chromatophore > 0.3:
                attr = curses.color_pair(5) | curses.A_BOLD
            else:
                attr = curses.color_pair(7) | curses.A_DIM
        elif c.ctype == CR_JELLYFISH:
            if c.flash_bright > 0.2:
                attr = curses.color_pair(5) | curses.A_BOLD  # cyan pulse
            else:
                attr = curses.color_pair(5) | curses.A_DIM
        elif c.ctype == CR_DRAGONFISH:
            if c.flash_bright > 0.2:
                attr = curses.color_pair(2) | curses.A_BOLD  # red searchlight
            else:
                attr = curses.color_pair(2) | curses.A_DIM
        elif c.ctype in (CR_LANTERNFISH, CR_HATCHETFISH):
            if c.flash_bright > 0.2:
                attr = curses.color_pair(4) | curses.A_BOLD  # green/yellow
            else:
                attr = curses.color_pair(4) | curses.A_DIM
        elif c.ctype == CR_SHRIMP:
            if c.flash_bright > 0.2:
                attr = curses.color_pair(3) | curses.A_BOLD  # bright burst
            else:
                attr = curses.color_pair(7) | curses.A_DIM
        elif c.ctype == CR_TUBEWORM:
            attr = curses.color_pair(2) | curses.A_DIM
        else:
            attr = curses.color_pair(7)

        try:
            self.stdscr.addstr(cr, cc, glyph, attr)
        except curses.error:
            pass


def _draw_deepsea_depth(self, max_y, max_x):
    """View 2: Depth-pressure cross-section with creature distribution."""
    rows = min(self.deepsea_rows, max_y - 3)
    cols = min(self.deepsea_cols, max_x)
    creatures = self.deepsea_creatures

    # Title
    try:
        self.stdscr.addstr(0, 2, "Depth-Pressure Profile"[:max_x - 3],
                           curses.A_BOLD)
    except curses.error:
        pass

    # Draw depth zones with labels and pressure
    zone_boundaries = [0, int(rows * 0.2), int(rows * 0.55),
                       int(rows * 0.8), rows]
    zone_chars = ['░', '▒', '▓', '█']

    for z in range(4):
        top = zone_boundaries[z]
        bot = zone_boundaries[z + 1]
        # Zone label
        mid = (top + bot) // 2
        if mid < rows and mid > 0:
            label = f" {ZONE_NAMES[z]} ({ZONE_DEPTHS[z]}) ~{ZONE_PRESSURE[z]} atm "
            try:
                self.stdscr.addstr(mid, 1, label[:max_x - 2],
                                   curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw zone background
        for r in range(top, min(bot, rows)):
            # Pressure gradient bar on left
            if r < max_y - 3:
                try:
                    self.stdscr.addstr(r, 0, zone_chars[z],
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

    # Count creatures per zone per type
    zone_counts = [[0] * 8 for _ in range(4)]
    for c in creatures:
        if not c.alive:
            continue
        z = _zone_for_row(c.y, self.deepsea_rows)
        if 0 <= z < 4 and 0 <= c.ctype < 8:
            zone_counts[z][c.ctype] += 1

    # Draw creature distribution bars
    bar_start_x = 35
    if bar_start_x < cols:
        for z in range(4):
            top = zone_boundaries[z]
            bot = zone_boundaries[z + 1]
            y = (top + bot) // 2 + 1
            if y >= rows:
                continue
            x = bar_start_x
            for ct in range(8):
                cnt = zone_counts[z][ct]
                if cnt == 0:
                    continue
                glyph = CREATURE_GLYPHS.get(ct, '?')
                bar = glyph * min(cnt, max(1, (cols - x - 5) // 8))
                cname = CREATURE_NAMES.get(ct, "?")
                label = f"{bar} {cname}:{cnt}"
                if x + len(label) < cols and y < max_y - 3:
                    color = curses.color_pair(4) if ct < 4 else curses.color_pair(5)
                    try:
                        self.stdscr.addstr(y, x, label[:cols - x - 1],
                                           color | curses.A_DIM)
                    except curses.error:
                        pass
                    y += 1
                    if y >= bot or y >= max_y - 3:
                        break

    # Draw plankton density by zone
    plankton_per_zone = [0] * 4
    for p in self.deepsea_plankton:
        if p.alive:
            z = _zone_for_row(p.y, self.deepsea_rows)
            if 0 <= z < 4:
                plankton_per_zone[z] += 1

    info_x = 2
    info_y = rows - 6 if rows > 8 else 1
    if info_y > 0 and info_y < max_y - 3:
        try:
            self.stdscr.addstr(info_y, info_x, "Plankton density by zone:"[:max_x - 3],
                               curses.A_BOLD)
        except curses.error:
            pass
        for z in range(4):
            zy = info_y + 1 + z
            if zy >= max_y - 3:
                break
            bar_len = min(plankton_per_zone[z] // 3, cols - 25)
            bar = '█' * max(0, bar_len)
            label = f"  {ZONE_NAMES[z]:15s} {bar} ({plankton_per_zone[z]})"
            try:
                self.stdscr.addstr(zy, info_x, label[:max_x - 3],
                                   curses.color_pair(5) | curses.A_DIM)
            except curses.error:
                pass


def _draw_deepsea_graph(self, max_y, max_x):
    """View 3: Time-series sparkline graphs."""
    try:
        self.stdscr.addstr(0, 2, "Deep-Sea Abyss — Time Series"[:max_x - 3],
                           curses.A_BOLD)
    except curses.error:
        pass

    graph_width = max(10, max_x - 25)
    graph_height = 2
    y = 2
    graphs = [
        (self.deepsea_flash_history, "Flash Events", curses.color_pair(4)),
        (self.deepsea_cascade_history, "Cascade Events", curses.color_pair(5)),
        (self.deepsea_predation_history, "Predation", curses.color_pair(2)),
        (self.deepsea_plankton_history, "Plankton Pop.", curses.color_pair(4)),
        (self.deepsea_creature_history, "Creature Pop.", curses.color_pair(3)),
        (self.deepsea_anglerfish_history, "Anglerfish", curses.color_pair(2)),
        (self.deepsea_squid_history, "Giant Squid", curses.color_pair(5)),
        (self.deepsea_jellyfish_history, "Jellyfish", curses.color_pair(5)),
        (self.deepsea_energy_history, "Avg Energy", curses.color_pair(4)),
        (self.deepsea_snow_history, "Marine Snow", curses.color_pair(7)),
    ]

    for data, label, color in graphs:
        if y + graph_height + 1 >= max_y - 3:
            break
        _sparkline(data, graph_width, graph_height, max_y, max_x,
                   y, 20, self.stdscr, color, label)
        y += graph_height + 1


# ── Registration ─────────────────────────────────────────────────────────────

def register(App):
    """Register Deep-Sea Bioluminescent Abyss mode methods on the App class."""
    App.DEEPSEA_PRESETS = DEEPSEA_PRESETS
    App._enter_deepsea_mode = _enter_deepsea_mode
    App._exit_deepsea_mode = _exit_deepsea_mode
    App._deepsea_init = _deepsea_init
    App._deepsea_step = _deepsea_step
    App._handle_deepsea_menu_key = _handle_deepsea_menu_key
    App._handle_deepsea_key = _handle_deepsea_key
    App._draw_deepsea_menu = _draw_deepsea_menu
    App._draw_deepsea = _draw_deepsea
    App._draw_deepsea_abyss = _draw_deepsea_abyss
    App._draw_deepsea_depth = _draw_deepsea_depth
    App._draw_deepsea_graph = _draw_deepsea_graph
