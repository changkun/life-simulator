"""Mode: lsystem — L-System Fractal Garden with seasonal cycles, wind, mutation & light competition."""
import curses
import math
import random
import time

from life.constants import SPEEDS


# ── Season constants ──────────────────────────────────────────────────────────

SEASON_SPRING = 0
SEASON_SUMMER = 1
SEASON_AUTUMN = 2
SEASON_WINTER = 3
SEASON_NAMES = ["Spring", "Summer", "Autumn", "Winter"]
SEASON_DURATION = 30  # steps per season


# ── Species library — L-system grammars ───────────────────────────────────────

SPECIES = {
    "binary_tree": {
        "axiom": "F", "rules": {"F": "FF+[+F-F-F]-[-F+F+F]"},
        "angle": 30.0, "length_scale": 0.5, "max_depth": 8,
        "flower": False, "deciduous": True, "color_trunk": 4, "color_leaf": 2,
    },
    "fern": {
        "axiom": "X", "rules": {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"},
        "angle": 22.0, "length_scale": 0.5, "max_depth": 7,
        "flower": False, "deciduous": False, "color_trunk": 2, "color_leaf": 2,
    },
    "bush": {
        "axiom": "F", "rules": {"F": "F[+F]F[-F][F]"},
        "angle": 25.7, "length_scale": 0.5, "max_depth": 6,
        "flower": True, "deciduous": True, "color_trunk": 3, "color_leaf": 2,
    },
    "seaweed": {
        "axiom": "F", "rules": {"F": "FF-[-F+F+F]+[+F-F-F]"},
        "angle": 18.0, "length_scale": 0.52, "max_depth": 7,
        "flower": False, "deciduous": False, "color_trunk": 6, "color_leaf": 6,
    },
    "willow": {
        "axiom": "F", "rules": {"F": "FF+[+F-F]-[-F+F+F]"},
        "angle": 20.0, "length_scale": 0.55, "max_depth": 7,
        "flower": False, "deciduous": True, "color_trunk": 3, "color_leaf": 2,
    },
    "pine": {
        "axiom": "F", "rules": {"F": "F[+F]F[-F]F"},
        "angle": 35.0, "length_scale": 0.45, "max_depth": 8,
        "flower": False, "deciduous": False, "color_trunk": 4, "color_leaf": 2,
    },
    "sakura": {
        "axiom": "F", "rules": {"F": "FF+[+F-F]-[-F+F]"},
        "angle": 28.0, "length_scale": 0.5, "max_depth": 7,
        "flower": True, "deciduous": True, "color_trunk": 4, "color_leaf": 5,
    },
    "bonsai": {
        "axiom": "F", "rules": {"F": "F[-F+F][+F-F]F"},
        "angle": 32.0, "length_scale": 0.48, "max_depth": 6,
        "flower": False, "deciduous": True, "color_trunk": 4, "color_leaf": 2,
    },
    "alien_tendril": {
        "axiom": "X", "rules": {"X": "F[+X][-X]FX", "F": "FF"},
        "angle": 40.0, "length_scale": 0.5, "max_depth": 7,
        "flower": True, "deciduous": False, "color_trunk": 5, "color_leaf": 6,
    },
    "coral": {
        "axiom": "F", "rules": {"F": "F[+F][--F]F[++F][-F]"},
        "angle": 24.0, "length_scale": 0.42, "max_depth": 5,
        "flower": False, "deciduous": False, "color_trunk": 1, "color_leaf": 5,
    },
    "vine": {
        "axiom": "X", "rules": {"X": "F-[[X]+X]+F[+FX]-X", "F": "FF"},
        "angle": 25.0, "length_scale": 0.5, "max_depth": 7,
        "flower": True, "deciduous": True, "color_trunk": 2, "color_leaf": 2,
    },
    "cactus": {
        "axiom": "F", "rules": {"F": "FF[-F][+F]"},
        "angle": 45.0, "length_scale": 0.55, "max_depth": 6,
        "flower": True, "deciduous": False, "color_trunk": 2, "color_leaf": 1,
    },
}


def _make_plant(species_id: str, x: float, y: float, mutation: float = 0.0) -> dict:
    """Create a plant dict from a species template with optional mutation."""
    sp = SPECIES[species_id]
    rules = {}
    for k, v in sp["rules"].items():
        rules[k] = v
    angle = sp["angle"]
    length_scale = sp["length_scale"]

    # Apply mutations
    if mutation > 0:
        angle += random.gauss(0, mutation * 5.0)
        angle = max(5.0, min(85.0, angle))
        length_scale += random.gauss(0, mutation * 0.05)
        length_scale = max(0.3, min(0.7, length_scale))
        # Occasionally mutate rules
        if random.random() < mutation * 0.3:
            for k in rules:
                rule = list(rules[k])
                if len(rule) > 2 and random.random() < 0.5:
                    idx = random.randint(0, len(rule) - 1)
                    choices = "F+-[]"
                    rule[idx] = random.choice(choices)
                    rules[k] = "".join(rule)

    return {
        "species": species_id,
        "x": x, "y": y,
        "axiom": sp["axiom"],
        "rules": rules,
        "angle": angle,
        "depth": 0,
        "string": sp["axiom"],
        "length_scale": length_scale,
        "max_depth": sp["max_depth"],
        "flower": sp["flower"],
        "deciduous": sp["deciduous"],
        "color_trunk": sp["color_trunk"],
        "color_leaf": sp["color_leaf"],
        "health": 1.0,  # 0..1 light-based health
        "age": 0,
        "seeds_dropped": 0,
    }


# ── Mode enter/exit ──────────────────────────────────────────────────────────

def _enter_lsystem_mode(self):
    """Enter L-System Fractal Garden mode — show preset menu."""
    self.lsystem_menu = True
    self.lsystem_menu_sel = 0
    self._flash("L-System Fractal Garden — select a preset")


def _exit_lsystem_mode(self):
    """Exit L-System Fractal Garden mode."""
    self.lsystem_mode = False
    self.lsystem_menu = False
    self.lsystem_running = False
    self.lsystem_plants = []
    self.lsystem_segments = []
    self.lsystem_leaves = []
    self._flash("L-System Garden OFF")


# ── Menu key handling ─────────────────────────────────────────────────────────

def _handle_lsystem_menu_key(self, key: int) -> bool:
    n = len(self.LSYSTEM_PRESETS)
    if key in (curses.KEY_UP, ord("k")):
        self.lsystem_menu_sel = (self.lsystem_menu_sel - 1) % n
    elif key in (curses.KEY_DOWN, ord("j")):
        self.lsystem_menu_sel = (self.lsystem_menu_sel + 1) % n
    elif key in (ord("q"), 27):
        self.lsystem_menu = False
    elif key in (ord("\n"), ord("\r"), curses.KEY_ENTER):
        name, _desc, preset_id = self.LSYSTEM_PRESETS[self.lsystem_menu_sel]
        self.lsystem_menu = False
        self.lsystem_mode = True
        self.lsystem_running = False
        self.lsystem_preset_name = name
        self._lsystem_init(preset_id)
    return True


# ── Simulation key handling ───────────────────────────────────────────────────

def _handle_lsystem_key(self, key: int) -> bool:
    if key in (ord("q"), 27):
        self._exit_lsystem_mode()
    elif key == ord(" "):
        self.lsystem_running = not self.lsystem_running
    elif key in (ord("n"), ord(".")):
        self._lsystem_step()
    elif key == ord("R"):
        self.lsystem_menu = True
        self.lsystem_menu_sel = 0
    elif key == ord("r"):
        # Reset current preset
        preset_id = ""
        for _n, _d, pid in self.LSYSTEM_PRESETS:
            if _n == self.lsystem_preset_name:
                preset_id = pid
                break
        if preset_id:
            self._lsystem_init(preset_id)
    elif key == ord("a"):
        for p in self.lsystem_plants:
            p["angle"] = max(5.0, p["angle"] - 2.0)
        self.lsystem_angle = max(5.0, self.lsystem_angle - 2.0)
        self._lsystem_rebuild_all()
    elif key == ord("A"):
        for p in self.lsystem_plants:
            p["angle"] = min(90.0, p["angle"] + 2.0)
        self.lsystem_angle = min(90.0, self.lsystem_angle + 2.0)
        self._lsystem_rebuild_all()
    elif key == ord("w"):
        # Decrease wind
        self.lsystem_wind = max(-1.0, self.lsystem_wind - 0.05)
        self._lsystem_rebuild_all()
    elif key == ord("W"):
        # Increase wind
        self.lsystem_wind = min(1.0, self.lsystem_wind + 0.05)
        self._lsystem_rebuild_all()
    elif key == ord("m"):
        # Toggle mutation
        self.lsystem_mutation = 0.0 if self.lsystem_mutation > 0 else 0.3
        self._flash(f"Mutation {'ON' if self.lsystem_mutation > 0 else 'OFF'}")
    elif key == ord("s"):
        # Advance season manually
        self.lsystem_season = (self.lsystem_season + 1) % 4
        self.lsystem_season_tick = 0
        self._lsystem_apply_season()
        self._lsystem_rebuild_all()
    elif key == ord("S"):
        # Toggle seasonal auto-cycle
        self.lsystem_seasons_auto = not self.lsystem_seasons_auto
        self._flash(f"Season cycle {'ON' if self.lsystem_seasons_auto else 'OFF'}")
    elif key == ord("g"):
        self.lsystem_growth_rate = max(0.2, self.lsystem_growth_rate - 0.1)
    elif key == ord("G"):
        self.lsystem_growth_rate = min(3.0, self.lsystem_growth_rate + 0.1)
    elif key in (curses.KEY_LEFT,):
        self.lsystem_light_dir = (self.lsystem_light_dir - 10) % 360
        self._lsystem_rebuild_all()
    elif key in (curses.KEY_RIGHT,):
        self.lsystem_light_dir = (self.lsystem_light_dir + 10) % 360
        self._lsystem_rebuild_all()
    elif key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
    elif key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
    return True


# ── Initialization ────────────────────────────────────────────────────────────

def _lsystem_init(self, preset: str) -> None:
    max_y, max_x = self.stdscr.getmaxyx()
    self.lsystem_rows = max(10, max_y - 3)
    self.lsystem_cols = max(10, max_x - 1)
    self.lsystem_generation = 0
    self.lsystem_current_depth = 0
    self.lsystem_plants = []
    self.lsystem_segments = []
    self.lsystem_leaves = []
    self.lsystem_wind = 0.0
    self.lsystem_wind_time = 0.0
    self.lsystem_season = SEASON_SPRING
    self.lsystem_season_tick = 0
    self.lsystem_seasons_auto = True
    self.lsystem_mutation = 0.0
    self.lsystem_seed_queue = []  # seeds waiting to sprout
    self.lsystem_fallen_leaves = []  # (x, y, char, color, ttl)
    # Light direction (degrees) — used by _lsystem_interpret for phototropism
    if not hasattr(self, 'lsystem_light_dir'):
        self.lsystem_light_dir = 0
    self._lsystem_build_preset(preset)


def _lsystem_build_preset(self, preset: str) -> None:
    cx = self.lsystem_cols // 2
    base_y = float(self.lsystem_rows - 1)

    if preset == "binary_tree":
        self.lsystem_max_depth = 8
        self.lsystem_angle = 30.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_plants = [_make_plant("binary_tree", float(cx), base_y)]
    elif preset == "fern":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 22.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_plants = [_make_plant("fern", float(cx), base_y)]
    elif preset == "bush":
        self.lsystem_max_depth = 6
        self.lsystem_angle = 25.7
        self.lsystem_growth_rate = 1.2
        self.lsystem_plants = [_make_plant("bush", float(cx), base_y)]
    elif preset == "seaweed":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 18.0
        self.lsystem_growth_rate = 0.8
        self.lsystem_plants = [_make_plant("seaweed", float(cx), base_y)]
    elif preset == "willow":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 20.0
        self.lsystem_growth_rate = 0.9
        self.lsystem_plants = [_make_plant("willow", float(cx), base_y)]
    elif preset == "pine":
        self.lsystem_max_depth = 8
        self.lsystem_angle = 35.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_plants = [_make_plant("pine", float(cx), base_y)]
    elif preset == "sakura":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 28.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_plants = [_make_plant("sakura", float(cx), base_y)]
    elif preset == "bonsai":
        self.lsystem_max_depth = 6
        self.lsystem_angle = 32.0
        self.lsystem_growth_rate = 0.6
        self.lsystem_plants = [_make_plant("bonsai", float(cx), base_y)]
    elif preset == "alien_flora":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 40.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_mutation = 0.3
        spread = self.lsystem_cols // 4
        for i, sp in enumerate(["alien_tendril", "coral", "alien_tendril"]):
            px = cx - spread + i * spread
            self.lsystem_plants.append(_make_plant(sp, float(px), base_y, mutation=0.2))
    elif preset == "garden":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 25.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_seasons_auto = True
        spread = self.lsystem_cols // 6
        species_list = ["binary_tree", "fern", "bush", "sakura", "pine"]
        for i, sp in enumerate(species_list):
            px = cx - 2 * spread + i * spread
            self.lsystem_plants.append(_make_plant(sp, float(px), base_y))
    elif preset == "competition":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 25.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_mutation = 0.15
        self.lsystem_seasons_auto = True
        spread = self.lsystem_cols // 8
        species_list = ["binary_tree", "fern", "bush", "willow", "pine", "sakura", "vine"]
        for i, sp in enumerate(species_list):
            px = cx - 3 * spread + i * spread
            self.lsystem_plants.append(_make_plant(sp, float(px), base_y, mutation=0.1))
    elif preset == "coral_reef":
        self.lsystem_max_depth = 5
        self.lsystem_angle = 24.0
        self.lsystem_growth_rate = 0.7
        spread = self.lsystem_cols // 5
        for i in range(4):
            sp = random.choice(["coral", "seaweed", "coral"])
            px = cx - int(1.5 * spread) + i * spread
            self.lsystem_plants.append(_make_plant(sp, float(px), base_y, mutation=0.15))
    elif preset == "desert":
        self.lsystem_max_depth = 6
        self.lsystem_angle = 45.0
        self.lsystem_growth_rate = 0.5
        spread = self.lsystem_cols // 4
        for i in range(3):
            px = cx - spread + i * spread
            self.lsystem_plants.append(_make_plant("cactus", float(px), base_y, mutation=0.1))

    self._lsystem_rebuild_all()


# ── L-system expansion & interpretation ───────────────────────────────────────

def _lsystem_expand(self, string: str, rules: dict[str, str]) -> str:
    result: list[str] = []
    for ch in string:
        result.append(rules.get(ch, ch))
    return "".join(result)


def _lsystem_interpret(self, plant: dict) -> tuple[list[tuple], list[tuple]]:
    """Interpret an L-system string into line segments and leaf positions.

    Returns (segments, leaves) where:
      segments: [(x1, y1, x2, y2, depth, color_trunk)]
      leaves:   [(x, y, is_flower, color_leaf, deciduous)]
    """
    string = plant["string"]
    angle_deg = plant["angle"]
    base_len = float(self.lsystem_rows) / (4.0 + plant["max_depth"] * 0.2)
    length = base_len
    length_scale = plant["length_scale"]
    start_x = plant["x"]
    start_y = plant["y"]
    color_trunk = plant.get("color_trunk", 4)
    color_leaf = plant.get("color_leaf", 2)
    is_flower = plant.get("flower", False)
    deciduous = plant.get("deciduous", True)

    # Wind effect: sinusoidal bend that increases with height
    wind = self.lsystem_wind
    wind_phase = self.lsystem_wind_time

    # Light direction bias
    light_bias = math.radians(self.lsystem_light_dir) * 0.15

    # Season effects
    season = self.lsystem_season
    show_leaves = True
    if season == SEASON_WINTER and deciduous:
        show_leaves = False
    elif season == SEASON_AUTUMN and deciduous:
        show_leaves = random.random() > 0.3  # some leaves remain

    segments: list[tuple] = []
    leaves: list[tuple] = []
    stack: list[tuple] = []

    x = start_x
    y = start_y
    heading = -math.pi / 2 + light_bias
    cur_len = length
    depth = 0
    max_h = 0.0  # track max height for wind scaling

    for ch in string:
        if ch == "F":
            # Wind bends branches proportional to height above ground
            height_frac = max(0.0, (start_y - y)) / max(1.0, float(self.lsystem_rows))
            wind_bend = wind * height_frac * 0.4 * math.sin(wind_phase + y * 0.1)
            adj_heading = heading + wind_bend

            nx = x + cur_len * math.cos(adj_heading)
            ny = y + cur_len * math.sin(adj_heading)
            segments.append((x, y, nx, ny, depth, color_trunk))
            x, y = nx, ny
        elif ch == "f":
            height_frac = max(0.0, (start_y - y)) / max(1.0, float(self.lsystem_rows))
            wind_bend = wind * height_frac * 0.4 * math.sin(wind_phase + y * 0.1)
            adj_heading = heading + wind_bend
            x += cur_len * math.cos(adj_heading)
            y += cur_len * math.sin(adj_heading)
        elif ch == "+":
            heading += math.radians(angle_deg)
        elif ch == "-":
            heading -= math.radians(angle_deg)
        elif ch == "[":
            stack.append((x, y, heading, cur_len, depth))
            cur_len *= length_scale
            depth += 1
        elif ch == "]":
            if stack:
                if show_leaves:
                    leaves.append((x, y, is_flower, color_leaf, deciduous))
                x, y, heading, cur_len, depth = stack.pop()
        elif ch == "X":
            pass

    return segments, leaves


def _lsystem_rebuild_all(self) -> None:
    """Rebuild all segments and leaves from current plant strings."""
    self.lsystem_segments = []
    self.lsystem_leaves = []
    for plant in self.lsystem_plants:
        segs, lvs = self._lsystem_interpret(plant)
        self.lsystem_segments.extend(segs)
        self.lsystem_leaves.extend(lvs)


# ── Light competition ─────────────────────────────────────────────────────────

def _lsystem_compute_light(self) -> None:
    """Compute light reaching each plant based on canopy overlap.

    Plants that are shaded by taller neighbors get reduced health.
    """
    if len(self.lsystem_plants) < 2:
        for p in self.lsystem_plants:
            p["health"] = 1.0
        return

    # Build light columns — which plant occupies highest point per x-column
    cols = self.lsystem_cols
    canopy_top: dict[int, list[tuple[float, int]]] = {}  # col -> [(y, plant_idx)]

    for pi, plant in enumerate(self.lsystem_plants):
        segs, _ = self._lsystem_interpret(plant)
        for x1, y1, x2, y2, depth, _ct in segs:
            for t_step in range(max(1, int(abs(x2 - x1) + abs(y2 - y1)))):
                t = t_step / max(1, int(abs(x2 - x1) + abs(y2 - y1)))
                px = x1 + t * (x2 - x1)
                py = y1 + t * (y2 - y1)
                c = int(round(px))
                if 0 <= c < cols:
                    if c not in canopy_top:
                        canopy_top[c] = []
                    canopy_top[c].append((py, pi))

    # For each plant, compute fraction of columns where it's the topmost
    plant_light = [0.0] * len(self.lsystem_plants)
    plant_total = [0] * len(self.lsystem_plants)

    for c, entries in canopy_top.items():
        for py, pi in entries:
            plant_total[pi] += 1
        # Topmost = lowest y value
        best_y = min(e[0] for e in entries)
        for py, pi in entries:
            if py <= best_y + 2.0:  # within 2 rows of top gets full light
                plant_light[pi] += 1
            else:
                plant_light[pi] += 0.3  # shaded

    for pi, plant in enumerate(self.lsystem_plants):
        if plant_total[pi] > 0:
            plant["health"] = min(1.0, plant_light[pi] / plant_total[pi])
        else:
            plant["health"] = 0.5


# ── Seasonal effects ─────────────────────────────────────────────────────────

def _lsystem_apply_season(self) -> None:
    """Apply seasonal effects to the garden."""
    season = self.lsystem_season

    if season == SEASON_AUTUMN:
        # Drop some leaves as fallen particles
        for lx, ly, is_flower, col, deciduous in self.lsystem_leaves:
            if deciduous and random.random() < 0.1:
                leaf_ch = random.choice([".", ",", "'", "`"])
                self.lsystem_fallen_leaves.append(
                    (lx + random.gauss(0, 1), ly, leaf_ch, 3, 20)  # (x, y, ch, color, ttl)
                )

    elif season == SEASON_SPRING:
        # Sprout any queued seeds
        new_plants = []
        for seed_x, seed_species, seed_mut in self.lsystem_seed_queue[:3]:
            base_y = float(self.lsystem_rows - 1)
            if len(self.lsystem_plants) + len(new_plants) < 12:
                new_plants.append(_make_plant(seed_species, seed_x, base_y, mutation=seed_mut))
        self.lsystem_plants.extend(new_plants)
        self.lsystem_seed_queue = self.lsystem_seed_queue[3:]

    # Prune dead plants in winter
    if season == SEASON_WINTER:
        self.lsystem_plants = [
            p for p in self.lsystem_plants if p["health"] > 0.15 or p["age"] < 3
        ]


# ── Seed dispersal ────────────────────────────────────────────────────────────

def _lsystem_drop_seeds(self) -> None:
    """Mature plants drop seeds that may sprout next spring."""
    for plant in self.lsystem_plants:
        if plant["depth"] >= plant["max_depth"] - 1 and plant["health"] > 0.5:
            if random.random() < 0.05:
                seed_x = plant["x"] + random.gauss(0, self.lsystem_cols * 0.15)
                seed_x = max(2.0, min(float(self.lsystem_cols - 2), seed_x))
                # Check not too close to existing plants
                too_close = any(abs(p["x"] - seed_x) < 5 for p in self.lsystem_plants)
                if not too_close:
                    self.lsystem_seed_queue.append(
                        (seed_x, plant["species"], self.lsystem_mutation)
                    )
                    plant["seeds_dropped"] += 1


# ── Step ──────────────────────────────────────────────────────────────────────

def _lsystem_step(self) -> None:
    """Advance the garden by one step: grow, compete, maybe change season."""
    # Wind fluctuation
    self.lsystem_wind_time += 0.3
    if abs(self.lsystem_wind) > 0.01:
        self.lsystem_wind += random.gauss(0, 0.005)
        self.lsystem_wind = max(-1.0, min(1.0, self.lsystem_wind))

    # Seasonal auto-cycle
    if self.lsystem_seasons_auto:
        self.lsystem_season_tick += 1
        if self.lsystem_season_tick >= SEASON_DURATION:
            self.lsystem_season_tick = 0
            self.lsystem_season = (self.lsystem_season + 1) % 4
            self._lsystem_apply_season()

    season = self.lsystem_season

    # Growth phase (spring/summer only at full rate; autumn slower; winter dormant)
    grow_chance = {SEASON_SPRING: 1.0, SEASON_SUMMER: 0.7, SEASON_AUTUMN: 0.2, SEASON_WINTER: 0.0}
    any_grew = False
    for plant in self.lsystem_plants:
        if plant["depth"] < plant["max_depth"]:
            effective_rate = self.lsystem_growth_rate * grow_chance.get(season, 0.5) * plant["health"]
            if random.random() < effective_rate:
                plant["string"] = self._lsystem_expand(plant["string"], plant["rules"])
                plant["depth"] += 1
                plant["age"] += 1
                any_grew = True

    if any_grew:
        self.lsystem_generation += 1

    # Light competition
    if len(self.lsystem_plants) > 1 and self.lsystem_generation % 3 == 0:
        self._lsystem_compute_light()

    # Seed dispersal (summer/autumn)
    if season in (SEASON_SUMMER, SEASON_AUTUMN) and self.lsystem_mutation > 0:
        self._lsystem_drop_seeds()

    # Update fallen leaves
    new_fallen = []
    for fx, fy, fch, fcol, fttl in self.lsystem_fallen_leaves:
        fy2 = fy + random.uniform(0.2, 0.8)
        fx2 = fx + self.lsystem_wind * 0.5 + random.gauss(0, 0.3)
        if fttl > 1 and fy2 < self.lsystem_rows - 1:
            new_fallen.append((fx2, fy2, fch, fcol, fttl - 1))
    self.lsystem_fallen_leaves = new_fallen

    self._lsystem_rebuild_all()


# ── Drawing: menu ─────────────────────────────────────────────────────────────

def _draw_lsystem_menu(self, max_y: int, max_x: int) -> None:
    self.stdscr.erase()
    title = "═══ L-System Fractal Garden ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    desc = "Botanical morphogenesis via Lindenmayer system grammars — with seasons, wind & mutation"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(desc)) // 2), desc[:max_x - 2], curses.A_DIM)
    except curses.error:
        pass

    start_y = 5
    for i, (name, description, _pid) in enumerate(self.LSYSTEM_PRESETS):
        if start_y + i >= max_y - 3:
            break
        marker = "▸ " if i == self.lsystem_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.lsystem_menu_sel else curses.A_NORMAL
        line = f"{marker}{name:<20s} {description}"
        try:
            self.stdscr.addstr(start_y + i, 4, line[:max_x - 6], attr)
        except curses.error:
            pass

    hint = " [Up/Down]=select  [Enter]=start  [q]=back"
    try:
        self.stdscr.addstr(max_y - 2, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ── Drawing: simulation ──────────────────────────────────────────────────────

def _draw_lsystem(self, max_y: int, max_x: int) -> None:
    self.stdscr.erase()

    rows = self.lsystem_rows
    cols = self.lsystem_cols

    # Character grid + color grid
    grid: list[list[str]] = [[" "] * cols for _ in range(rows)]
    color_grid: list[list[int]] = [[0] * cols for _ in range(rows)]

    season = self.lsystem_season

    # Trunk characters by depth
    trunk_chars = ["#", "|", "|", ":", ":", ".", ".", "."]
    branch_right = ["\\", "\\", "\\", "\\", ".", "."]
    branch_left = ["/", "/", "/", "/", ".", "."]

    # Season-based sky background (subtle)
    sky_colors = {
        SEASON_SPRING: 0, SEASON_SUMMER: 0,
        SEASON_AUTUMN: 0, SEASON_WINTER: 0,
    }

    # Draw segments
    for seg in self.lsystem_segments:
        x1, y1, x2, y2, depth, col_trunk = seg
        steps = max(int(max(abs(x2 - x1), abs(y2 - y1))), 1)
        for s in range(steps + 1):
            t = s / steps if steps > 0 else 0
            px = x1 + t * (x2 - x1)
            py = y1 + t * (y2 - y1)
            r = int(round(py))
            c = int(round(px))
            if 0 <= r < rows and 0 <= c < cols:
                dx = x2 - x1
                dy = y2 - y1
                adeg = math.degrees(math.atan2(dy, dx)) % 360 if (abs(dx) + abs(dy)) > 0.01 else 90.0

                d_idx = min(depth, len(trunk_chars) - 1)
                if 60 < adeg < 120 or 240 < adeg < 300:
                    ch = "-" if depth < 3 else "~" if depth < 5 else "."
                elif (30 < adeg <= 60) or (210 < adeg <= 240):
                    ch = branch_right[min(depth, len(branch_right) - 1)]
                elif (120 <= adeg < 150) or (300 <= adeg < 330):
                    ch = branch_left[min(depth, len(branch_left) - 1)]
                else:
                    ch = trunk_chars[d_idx]

                # Color based on depth and species trunk color
                if depth == 0:
                    col = col_trunk
                elif depth <= 2:
                    col = col_trunk if col_trunk != 4 else 3
                else:
                    col = 2  # green branches

                # Winter: bare trunks look grey
                if season == SEASON_WINTER and depth > 2:
                    col = 0

                if grid[r][c] == " " or color_grid[r][c] < col:
                    grid[r][c] = ch
                    color_grid[r][c] = col

    # Draw leaves (season-dependent)
    spring_leaves = ["*", "@", "&", "%", "o"]
    summer_leaves = ["@", "#", "&", "%", "o", "*"]
    autumn_leaves = [".", ",", "'", "`", "~"]
    flower_chars = ["*", "+", "o", "@"]

    for lx, ly, is_flower, col_leaf, deciduous in self.lsystem_leaves:
        r = int(round(ly))
        c = int(round(lx))
        if 0 <= r < rows and 0 <= c < cols:
            if grid[r][c] == " " or color_grid[r][c] <= 2:
                h = hash((r, c))
                if season == SEASON_SUMMER and is_flower:
                    ch = flower_chars[h % len(flower_chars)]
                    col = col_leaf if col_leaf != 2 else 5  # flowers in magenta
                elif season == SEASON_SPRING and is_flower and random.random() < 0.3:
                    ch = flower_chars[h % len(flower_chars)]
                    col = 5
                elif season == SEASON_AUTUMN and deciduous:
                    ch = autumn_leaves[h % len(autumn_leaves)]
                    col = 3  # yellow/brown
                elif season == SEASON_WINTER and deciduous:
                    continue  # bare
                else:
                    if season == SEASON_SPRING:
                        ch = spring_leaves[h % len(spring_leaves)]
                    else:
                        ch = summer_leaves[h % len(summer_leaves)]
                    col = col_leaf

                grid[r][c] = ch
                color_grid[r][c] = col

    # Draw fallen leaves (autumn effect)
    for fx, fy, fch, fcol, fttl in self.lsystem_fallen_leaves:
        r = int(round(fy))
        c = int(round(fx))
        if 0 <= r < rows and 0 <= c < cols and grid[r][c] == " ":
            grid[r][c] = fch
            color_grid[r][c] = fcol

    # Draw ground line
    ground_chars_by_season = {
        SEASON_SPRING: (".", ",", "'", "."),
        SEASON_SUMMER: (".", ",", "'", "."),
        SEASON_AUTUMN: (",", "'", ".", "`"),
        SEASON_WINTER: (".", " ", ".", " "),
    }
    gchars = ground_chars_by_season.get(season, (".", ",", "'", "."))
    for c in range(cols):
        if rows - 1 >= 0 and grid[rows - 1][c] == " ":
            grid[rows - 1][c] = gchars[c % len(gchars)]
            if season == SEASON_WINTER:
                color_grid[rows - 1][c] = 7  # white snow
            elif season == SEASON_AUTUMN:
                color_grid[rows - 1][c] = 3  # brown
            else:
                color_grid[rows - 1][c] = 2  # green grass

    # Draw seeds on ground
    for sx, sspecies, _smut in self.lsystem_seed_queue:
        sc = int(round(sx))
        if 0 <= sc < cols and rows - 2 >= 0:
            if grid[rows - 2][sc] == " ":
                grid[rows - 2][sc] = "o"
                color_grid[rows - 2][sc] = 3

    # Render to screen
    for r in range(min(rows, max_y - 2)):
        for c in range(min(cols, max_x - 1)):
            ch = grid[r][c]
            col = color_grid[r][c]
            if ch != " ":
                try:
                    attr = curses.color_pair(col)
                    if col == 2:
                        attr |= curses.A_BOLD
                    elif col == 5:
                        attr |= curses.A_BOLD
                    self.stdscr.addstr(r, c, ch, attr)
                except curses.error:
                    pass

    # Status bar
    plant_depths = "/".join(str(p["depth"]) for p in self.lsystem_plants)
    max_d = max((p["max_depth"] for p in self.lsystem_plants), default=0)
    n_plants = len(self.lsystem_plants)
    season_name = SEASON_NAMES[self.lsystem_season]
    season_pct = int(100 * self.lsystem_season_tick / SEASON_DURATION) if self.lsystem_seasons_auto else 0
    wind_str = f"{self.lsystem_wind:+.2f}" if abs(self.lsystem_wind) > 0.01 else "calm"

    status = (
        f" {self.lsystem_preset_name} | "
        f"Gen {self.lsystem_generation} | "
        f"Plants {n_plants} | "
        f"Depth {plant_depths}/{max_d} | "
        f"{season_name}"
    )
    if self.lsystem_seasons_auto:
        status += f" {season_pct}%"
    status += f" | Wind {wind_str}"
    if self.lsystem_mutation > 0:
        status += f" | Mut {self.lsystem_mutation:.0%}"
    status += f" | {'RUN' if self.lsystem_running else 'STOP'}"

    try:
        self.stdscr.addstr(max_y - 3, 0, status[:max_x - 1], curses.color_pair(6) | curses.A_BOLD)
    except curses.error:
        pass

    if self.message and time.monotonic() - self.message_time < 2.0:
        hint = f" {self.message}"
    else:
        hint = " [Space]=play [n]=step [a/A]=angle [w/W]=wind [s/S]=season [m]=mutate [r]=reset [R]=menu [q]=exit"
    try:
        self.stdscr.addstr(max_y - 2, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ── Registration ──────────────────────────────────────────────────────────────

LSYSTEM_PRESETS = [
    ("Binary Tree",    "Symmetric branching tree structure",               "binary_tree"),
    ("Fern",           "Naturalistic fern with curving fronds",            "fern"),
    ("Bush",           "Dense bushy shrub with many branches",             "bush"),
    ("Seaweed",        "Swaying underwater kelp strands",                  "seaweed"),
    ("Willow",         "Drooping willow tree with long tendrils",          "willow"),
    ("Pine",           "Coniferous tree with short angled branches",       "pine"),
    ("Sakura",         "Cherry blossom tree with spring flowers",          "sakura"),
    ("Bonsai",         "Carefully shaped miniature tree",                  "bonsai"),
    ("Garden",         "Multiple species competing for light",             "garden"),
    ("Alien Flora",    "Exotic extraterrestrial vegetation with mutation", "alien_flora"),
    ("Competition",    "7 species battle for light — survival of fittest", "competition"),
    ("Coral Reef",     "Underwater coral and seaweed colony",              "coral_reef"),
    ("Desert",         "Sparse cacti in arid landscape",                   "desert"),
]


def register(App):
    """Register L-System Fractal Garden mode methods on the App class."""
    App.LSYSTEM_PRESETS = LSYSTEM_PRESETS
    App._enter_lsystem_mode = _enter_lsystem_mode
    App._exit_lsystem_mode = _exit_lsystem_mode
    App._handle_lsystem_menu_key = _handle_lsystem_menu_key
    App._handle_lsystem_key = _handle_lsystem_key
    App._lsystem_init = _lsystem_init
    App._lsystem_build_preset = _lsystem_build_preset
    App._lsystem_expand = _lsystem_expand
    App._lsystem_interpret = _lsystem_interpret
    App._lsystem_rebuild_all = _lsystem_rebuild_all
    App._lsystem_step = _lsystem_step
    App._lsystem_compute_light = _lsystem_compute_light
    App._lsystem_apply_season = _lsystem_apply_season
    App._lsystem_drop_seeds = _lsystem_drop_seeds
    App._draw_lsystem_menu = _draw_lsystem_menu
    App._draw_lsystem = _draw_lsystem
