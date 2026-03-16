"""Mode: terrain — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_terrain_mode(self):
    """Enter Terrain Generation & Erosion mode — show preset menu."""
    self.terrain_menu = True
    self.terrain_menu_sel = 0
    self._flash("Terrain Generation — select a landscape")



def _exit_terrain_mode(self):
    """Exit Terrain Generation mode."""
    self.terrain_mode = False
    self.terrain_menu = False
    self.terrain_running = False
    self.terrain_heightmap = []
    self.terrain_vegetation = []
    self.terrain_hardness = []
    self._flash("Terrain mode OFF")



def _terrain_generate(self, rows: int, cols: int, terrain_type: str):
    """Generate initial terrain using layered noise with type-specific features."""
    heightmap = [[0.0] * cols for _ in range(rows)]

    def _smooth_noise(freq: float, amp: float):
        sr = max(2, int(rows / freq))
        sc = max(2, int(cols / freq))
        sparse_r = max(2, rows // sr + 2)
        sparse_c = max(2, cols // sc + 2)
        sparse = [[random.random() for _ in range(sparse_c)] for _ in range(sparse_r)]
        for r in range(rows):
            for c in range(cols):
                gr = r / sr
                gc = c / sc
                r0 = int(gr) % sparse_r
                r1 = (r0 + 1) % sparse_r
                c0 = int(gc) % sparse_c
                c1 = (c0 + 1) % sparse_c
                fr = gr - int(gr)
                fc = gc - int(gc)
                top = sparse[r0][c0] * (1 - fc) + sparse[r0][c1] * fc
                bot = sparse[r1][c0] * (1 - fc) + sparse[r1][c1] * fc
                heightmap[r][c] += (top * (1 - fr) + bot * fr) * amp

    if terrain_type == "continental":
        _smooth_noise(3, 0.5)
        _smooth_noise(6, 0.3)
        _smooth_noise(12, 0.15)
        _smooth_noise(24, 0.05)
        # Add continental shelf — lower edges
        for r in range(rows):
            for c in range(cols):
                edge = min(r, rows - 1 - r, c, cols - 1 - c) / max(1, min(rows, cols) * 0.3)
                heightmap[r][c] *= min(1.0, edge * 1.5)
    elif terrain_type == "archipelago":
        _smooth_noise(4, 0.3)
        _smooth_noise(8, 0.2)
        _smooth_noise(16, 0.1)
        # Add island peaks
        n_islands = random.randint(4, 8)
        for _ in range(n_islands):
            ir = random.randint(rows // 6, rows * 5 // 6)
            ic = random.randint(cols // 6, cols * 5 // 6)
            rad = random.uniform(0.08, 0.2) * min(rows, cols)
            peak = random.uniform(0.4, 0.7)
            for r in range(rows):
                for c in range(cols):
                    d = math.sqrt((r - ir) ** 2 + (c - ic) ** 2)
                    heightmap[r][c] += peak * max(0, 1.0 - (d / rad) ** 2)
    elif terrain_type == "alpine":
        _smooth_noise(3, 0.55)
        _smooth_noise(6, 0.3)
        _smooth_noise(12, 0.15)
        # Exaggerate peaks
        for r in range(rows):
            for c in range(cols):
                heightmap[r][c] = heightmap[r][c] ** 1.4
    elif terrain_type == "plains":
        _smooth_noise(5, 0.3)
        _smooth_noise(10, 0.2)
        _smooth_noise(20, 0.1)
        # Flatten midrange
        for r in range(rows):
            for c in range(cols):
                h = heightmap[r][c]
                heightmap[r][c] = 0.3 + 0.4 * h  # compress to middle range
    elif terrain_type == "rift":
        _smooth_noise(4, 0.4)
        _smooth_noise(8, 0.2)
        _smooth_noise(16, 0.1)
        # Central rift valley
        mid_c = cols // 2
        for r in range(rows):
            for c in range(cols):
                dist = abs(c - mid_c) / max(1, cols)
                # V-shape rift
                rift_depth = 0.35 * max(0, 1.0 - abs(dist - 0.0) * 8)
                heightmap[r][c] -= rift_depth
                # Raised escarpments on either side
                if 0.08 < dist < 0.2:
                    heightmap[r][c] += 0.15
    elif terrain_type == "coastal":
        _smooth_noise(4, 0.4)
        _smooth_noise(8, 0.25)
        _smooth_noise(16, 0.1)
        # Gradient from land (left) to sea (right)
        for r in range(rows):
            for c in range(cols):
                grad = 1.0 - (c / max(1, cols - 1))
                heightmap[r][c] = heightmap[r][c] * 0.6 + grad * 0.5

    # Normalize to [0, 1]
    min_h = min(heightmap[r][c] for r in range(rows) for c in range(cols))
    max_h = max(heightmap[r][c] for r in range(rows) for c in range(cols))
    rng = max_h - min_h if max_h > min_h else 1.0
    for r in range(rows):
        for c in range(cols):
            heightmap[r][c] = (heightmap[r][c] - min_h) / rng
    return heightmap



def _terrain_init(self, preset_idx: int):
    """Initialize terrain simulation with chosen preset."""
    (name, _desc, uplift, thermal, veg, sea, ttype) = self.TERRAIN_PRESETS[preset_idx]
    self.terrain_preset_name = name
    self.terrain_generation = 0
    self.terrain_running = False
    self.terrain_uplift_rate = uplift
    self.terrain_thermal_rate = thermal
    self.terrain_veg_growth = veg
    self.terrain_sea_level = sea
    self.terrain_rain_rate = 0.01
    self.terrain_total_uplift = 0.0
    self.terrain_total_eroded = 0.0
    self.terrain_view = "topo"

    max_y, max_x = self.stdscr.getmaxyx()
    self.terrain_rows = max(10, max_y - 4)
    self.terrain_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.terrain_rows, self.terrain_cols

    self.terrain_heightmap = self._terrain_generate(rows, cols, ttype)
    # Initialize vegetation: grows above sea level, none below
    self.terrain_vegetation = [
        [0.1 if self.terrain_heightmap[r][c] > sea + 0.05 else 0.0
         for c in range(cols)] for r in range(rows)]
    # Rock hardness: varies spatially
    self.terrain_hardness = [
        [0.5 + 0.5 * random.random() for _ in range(cols)]
        for _ in range(rows)]

    self.terrain_menu = False
    self.terrain_mode = True
    self._flash(f"Terrain: {name} — Space to start")



def _terrain_step(self):
    """Advance terrain simulation by one geological time step.

    Combines:
    1. Tectonic uplift — slow deformation raising terrain
    2. Thermal erosion — rockslides on steep slopes
    3. Hydraulic erosion — rain-driven water erosion
    4. Vegetation growth — stabilises soil, reduces erosion
    """
    hmap = self.terrain_heightmap
    veg = self.terrain_vegetation
    hard = self.terrain_hardness
    rows, cols = self.terrain_rows, self.terrain_cols
    sea = self.terrain_sea_level

    # ── 1. Tectonic uplift ──
    # Non-uniform uplift: stronger in centre, weaker at edges
    uplift = self.terrain_uplift_rate
    cr, cc = rows // 2, cols // 2
    max_dist = math.sqrt(cr ** 2 + cc ** 2)
    total_up = 0.0
    for r in range(rows):
        for c in range(cols):
            d = math.sqrt((r - cr) ** 2 + (c - cc) ** 2)
            factor = max(0.2, 1.0 - 0.6 * (d / max_dist))
            up = uplift * factor * (0.8 + 0.4 * random.random())
            hmap[r][c] += up
            total_up += up
    self.terrain_total_uplift += total_up

    # ── 2. Thermal erosion (rockslides on steep slopes) ──
    thermal = self.terrain_thermal_rate
    talus_threshold = 0.06  # max stable height diff
    eroded = 0.0
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            h = hmap[r][c]
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                diff = h - hmap[nr][nc]
                if diff > talus_threshold:
                    # Vegetation stabilises: reduce erosion
                    veg_factor = max(0.1, 1.0 - veg[r][c] * 0.8)
                    # Harder rock erodes less
                    hard_factor = 1.0 / (0.5 + hard[r][c])
                    transfer = thermal * (diff - talus_threshold) * 0.5 * veg_factor * hard_factor
                    transfer = min(transfer, diff * 0.25)
                    hmap[r][c] -= transfer
                    hmap[nr][nc] += transfer
                    eroded += transfer
                    # Damage vegetation on sliding slope
                    veg[r][c] = max(0.0, veg[r][c] - transfer * 2)

    # ── 3. Hydraulic erosion (simplified rain erosion) ──
    rain = self.terrain_rain_rate
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if hmap[r][c] <= sea:
                continue  # underwater — no rain erosion
            # Find steepest downhill
            h = hmap[r][c]
            best_diff = 0.0
            best_nr, best_nc = r, c
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                diff = h - hmap[nr][nc]
                if diff > best_diff:
                    best_diff = diff
                    best_nr, best_nc = nr, nc
            if best_diff > 0.005:
                veg_factor = max(0.05, 1.0 - veg[r][c] * 0.9)
                erode_amt = rain * best_diff * veg_factor * (0.7 + 0.6 * random.random())
                erode_amt = min(erode_amt, hmap[r][c] * 0.05)
                hmap[r][c] -= erode_amt
                # Deposit some downstream
                hmap[best_nr][best_nc] += erode_amt * 0.6
                eroded += erode_amt * 0.4  # net loss (carried to sea)

    self.terrain_total_eroded += eroded

    # ── 4. Vegetation dynamics ──
    vg = self.terrain_veg_growth
    for r in range(rows):
        for c in range(cols):
            h = hmap[r][c]
            if h <= sea:
                veg[r][c] = 0.0  # no vegetation underwater
            elif h < sea + 0.05:
                # Coastal/beach — sparse
                veg[r][c] = min(0.2, veg[r][c] + vg * 0.2)
            elif h > 0.85:
                # Alpine/snow — very sparse
                veg[r][c] = max(0.0, veg[r][c] - vg * 0.3)
            elif h > 0.7:
                # High altitude — slow growth
                veg[r][c] = min(0.4, veg[r][c] + vg * 0.3)
            else:
                # Temperate zone — good growth
                # Flat areas grow faster
                slope = 0.0
                if 0 < r < rows - 1 and 0 < c < cols - 1:
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        slope += abs(hmap[r + dr][c + dc] - h)
                slope_penalty = min(1.0, slope * 5)
                growth = vg * (1.0 - slope_penalty * 0.7)
                veg[r][c] = min(1.0, veg[r][c] + growth)

    # Normalise heightmap to prevent runaway values
    min_h = min(hmap[r][c] for r in range(rows) for c in range(cols))
    max_h = max(hmap[r][c] for r in range(rows) for c in range(cols))
    if max_h - min_h > 2.0:
        rng = max_h - min_h
        for r in range(rows):
            for c in range(cols):
                hmap[r][c] = (hmap[r][c] - min_h) / rng

    self.terrain_generation += 1



def _handle_terrain_menu_key(self, key: int) -> bool:
    """Handle input in terrain preset menu."""
    n = len(self.TERRAIN_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.terrain_menu_sel = (self.terrain_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.terrain_menu_sel = (self.terrain_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._terrain_init(self.terrain_menu_sel)
    elif key in (ord("q"), 27):
        self.terrain_menu = False
        self._flash("Terrain cancelled")
    return True



def _handle_terrain_key(self, key: int) -> bool:
    """Handle input in active terrain simulation."""
    if key == ord(" "):
        self.terrain_running = not self.terrain_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.terrain_steps_per_frame):
            self._terrain_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.TERRAIN_PRESETS)
                    if p[0] == self.terrain_preset_name), 0)
        self._terrain_init(idx)
        self.terrain_running = False
    elif key in (ord("R"), ord("m")):
        self.terrain_mode = False
        self.terrain_running = False
        self.terrain_menu = True
        self.terrain_menu_sel = 0
    elif key == ord("v"):
        views = ["topo", "elevation", "vegetation", "erosion"]
        idx = views.index(self.terrain_view) if self.terrain_view in views else 0
        self.terrain_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.terrain_view}")
    elif key == ord("u") or key == ord("U"):
        delta = 0.001 if key == ord("u") else -0.001
        self.terrain_uplift_rate = max(0.0, min(0.02, self.terrain_uplift_rate + delta))
        self._flash(f"Uplift = {self.terrain_uplift_rate:.4f}")
    elif key == ord("t") or key == ord("T"):
        delta = 0.005 if key == ord("t") else -0.005
        self.terrain_thermal_rate = max(0.0, min(0.1, self.terrain_thermal_rate + delta))
        self._flash(f"Thermal = {self.terrain_thermal_rate:.3f}")
    elif key == ord("w") or key == ord("W"):
        delta = 0.002 if key == ord("w") else -0.002
        self.terrain_rain_rate = max(0.0, min(0.05, self.terrain_rain_rate + delta))
        self._flash(f"Rain = {self.terrain_rain_rate:.3f}")
    elif key == ord("g") or key == ord("G"):
        delta = 0.002 if key == ord("g") else -0.002
        self.terrain_veg_growth = max(0.0, min(0.05, self.terrain_veg_growth + delta))
        self._flash(f"Veg growth = {self.terrain_veg_growth:.3f}")
    elif key == ord("s") or key == ord("S"):
        delta = 0.02 if key == ord("s") else -0.02
        self.terrain_sea_level = max(0.0, min(0.6, self.terrain_sea_level + delta))
        self._flash(f"Sea level = {self.terrain_sea_level:.2f}")
    elif key == ord("+") or key == ord("="):
        self.terrain_steps_per_frame = min(20, self.terrain_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.terrain_steps_per_frame}")
    elif key == ord("-"):
        self.terrain_steps_per_frame = max(1, self.terrain_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.terrain_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_terrain_mode()
    else:
        return True
    return True



def _draw_terrain_menu(self, max_y: int, max_x: int):
    """Draw the terrain preset selection menu."""
    self.stdscr.erase()
    title = "── Terrain Generation & Erosion ── Select Landscape ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.TERRAIN_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<24s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.terrain_menu_sel:
            attr = curses.color_pair(3) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_terrain(self, max_y: int, max_x: int):
    """Draw the active Terrain Generation & Erosion simulation."""
    self.stdscr.erase()
    hmap = self.terrain_heightmap
    veg = self.terrain_vegetation
    rows, cols = self.terrain_rows, self.terrain_cols
    gen = self.terrain_generation
    sea = self.terrain_sea_level
    state = "▶ RUNNING" if self.terrain_running else "⏸ PAUSED"
    view = self.terrain_view

    # Title bar
    title = (f" Terrain: {self.terrain_preset_name}  |  epoch {gen}"
             f"  |  uplift={self.terrain_uplift_rate:.4f}"
             f"  |  view={view}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 3
    view_cols = (max_x - 1) // 2

    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            sx = c * 2
            sy = 1 + r
            h = hmap[r][c]
            v = veg[r][c]

            if view == "topo":
                # Topographic map with elevation bands
                if h < sea - 0.10:
                    attr = curses.color_pair(120)  # deep ocean
                    ch = "██"
                elif h < sea - 0.03:
                    attr = curses.color_pair(121)  # ocean
                    ch = "▓▓"
                elif h < sea:
                    attr = curses.color_pair(122)  # shallow water
                    ch = "░░"
                elif h < sea + 0.04:
                    attr = curses.color_pair(123)  # beach
                    ch = "░░"
                elif h < sea + 0.15:
                    if v > 0.5:
                        attr = curses.color_pair(125)  # forest
                        ch = "██" if v > 0.7 else "▓▓"
                    else:
                        attr = curses.color_pair(124)  # grass
                        ch = "▒▒"
                elif h < sea + 0.30:
                    if v > 0.4:
                        attr = curses.color_pair(126)  # dense forest
                        ch = "██"
                    else:
                        attr = curses.color_pair(125)  # lowland
                        ch = "▒▒"
                elif h < sea + 0.45:
                    attr = curses.color_pair(127)  # highland
                    ch = "▓▓" if v > 0.2 else "▒▒"
                elif h < sea + 0.55:
                    attr = curses.color_pair(128)  # mountain
                    ch = "▓▓"
                elif h < sea + 0.65:
                    attr = curses.color_pair(129)  # alpine
                    ch = "▒▒"
                else:
                    attr = curses.color_pair(130) | curses.A_BOLD  # snow
                    ch = "██"
            elif view == "elevation":
                # Raw elevation grayscale-like using existing pairs
                if h < 0.1:
                    attr = curses.color_pair(120); ch = "░░"
                elif h < 0.2:
                    attr = curses.color_pair(121); ch = "░░"
                elif h < 0.3:
                    attr = curses.color_pair(122); ch = "▒▒"
                elif h < 0.4:
                    attr = curses.color_pair(124); ch = "▒▒"
                elif h < 0.5:
                    attr = curses.color_pair(127); ch = "▒▒"
                elif h < 0.6:
                    attr = curses.color_pair(128); ch = "▓▓"
                elif h < 0.7:
                    attr = curses.color_pair(129); ch = "▓▓"
                elif h < 0.85:
                    attr = curses.color_pair(129) | curses.A_BOLD; ch = "██"
                else:
                    attr = curses.color_pair(130) | curses.A_BOLD; ch = "██"
            elif view == "vegetation":
                # Vegetation density
                if h < sea:
                    attr = curses.color_pair(121); ch = "~~"
                elif v < 0.05:
                    attr = curses.color_pair(128); ch = "··"
                elif v < 0.2:
                    attr = curses.color_pair(127); ch = "░░"
                elif v < 0.4:
                    attr = curses.color_pair(124); ch = "▒▒"
                elif v < 0.6:
                    attr = curses.color_pair(125); ch = "▓▓"
                elif v < 0.8:
                    attr = curses.color_pair(126); ch = "██"
                else:
                    attr = curses.color_pair(131) | curses.A_BOLD; ch = "██"
            else:  # erosion view — highlight steep slopes
                if h < sea:
                    attr = curses.color_pair(121); ch = "██"
                else:
                    slope = 0.0
                    if 0 < r < rows - 1 and 0 < c < cols - 1:
                        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            slope += abs(hmap[r + dr][c + dc] - h)
                    if slope > 0.15:
                        attr = curses.color_pair(1) | curses.A_BOLD; ch = "██"  # red=steep
                    elif slope > 0.08:
                        attr = curses.color_pair(3); ch = "▓▓"  # yellow
                    elif slope > 0.03:
                        attr = curses.color_pair(2); ch = "▒▒"  # green
                    else:
                        attr = curses.color_pair(4); ch = "░░"  # blue=flat

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Stats bar
    stats_y = max_y - 2
    if stats_y > 1:
        stats = (f" eroded={self.terrain_total_eroded:.1f}"
                 f"  thermal={self.terrain_thermal_rate:.3f}"
                 f"  rain={self.terrain_rain_rate:.3f}"
                 f"  veg={self.terrain_veg_growth:.3f}"
                 f"  sea={self.terrain_sea_level:.2f}")
        try:
            self.stdscr.addstr(stats_y, 0, stats[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [u/U]=uplift [t/T]=thermal [w/W]=rain [g/G]=veg [s/S]=sea [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


TERRAIN_PRESETS = [
    # (name, description, uplift_rate, thermal_rate, veg_growth, sea_level, terrain_type)
    ("Continental", "Large landmass with continental shelf", 0.001, 0.02, 0.005, 0.25, "continental"),
    ("Archipelago", "Scattered island chain", 0.0008, 0.015, 0.008, 0.35, "archipelago"),
    ("Alpine Peaks", "Towering mountains with deep valleys", 0.0015, 0.03, 0.003, 0.15, "alpine"),
    ("Rolling Plains", "Gentle grasslands with lazy rivers", 0.0005, 0.01, 0.01, 0.20, "plains"),
    ("Great Rift", "Rift valley with raised escarpments", 0.0012, 0.025, 0.006, 0.22, "rift"),
    ("Coastal Erosion", "Land-sea gradient with active erosion", 0.0008, 0.02, 0.007, 0.30, "coastal"),
]


def register(App):
    """Register terrain mode methods on the App class."""
    App.TERRAIN_PRESETS = TERRAIN_PRESETS
    App._enter_terrain_mode = _enter_terrain_mode
    App._exit_terrain_mode = _exit_terrain_mode
    App._terrain_generate = _terrain_generate
    App._terrain_init = _terrain_init
    App._terrain_step = _terrain_step
    App._handle_terrain_menu_key = _handle_terrain_menu_key
    App._handle_terrain_key = _handle_terrain_key
    App._draw_terrain_menu = _draw_terrain_menu
    App._draw_terrain = _draw_terrain

