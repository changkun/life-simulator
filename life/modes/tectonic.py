"""Mode: tectonic — simulation mode for the life package."""
import curses
import math
import random
import time

TECTONIC_PRESETS = [
    ("Pangaea Breakup", "Single supercontinent rifting apart", "pangaea"),
    ("Island Arcs", "Oceanic plates with subduction zones", "arcs"),
    ("Continental Collision", "Two large landmasses converging head-on", "collision"),
    ("Mid-Ocean Ridges", "Divergent boundaries creating new crust", "ridges"),
    ("Ring of Fire", "Subduction-driven volcanic ring around a central ocean", "ring"),
    ("Random Drift", "Random plate configuration with varied velocities", "random"),
]

TECTONIC_ELEV_CHARS = " .\u00b7~-=\u2248:;+*#%\u2592\u2593\u2588\u25b2"
TECTONIC_ELEV_THRESHOLDS = [
    -8000, -5000, -3000, -1500, -500, -100, 0, 100, 300, 600,
    1200, 2000, 3000, 4500, 6000, 7500, 9000,
]


def _enter_tectonic_mode(self):
    """Enter Tectonic Plates mode — show preset menu."""
    self.tectonic_menu = True
    self.tectonic_menu_sel = 0
    self._flash("Tectonic Plates — select a scenario")


def _exit_tectonic_mode(self):
    """Exit Tectonic Plates mode."""
    self.tectonic_mode = False
    self.tectonic_menu = False
    self.tectonic_running = False
    self._flash("Tectonic Plates mode OFF")




def _tectonic_init(self, preset_idx: int):
    """Initialize tectonic simulation from preset."""
    import random as _rand
    import math as _math

    preset = self.TECTONIC_PRESETS[preset_idx]
    self.tectonic_preset_name = preset[0]
    kind = preset[2]

    max_y, max_x = self.stdscr.getmaxyx()
    self.tectonic_rows = max(20, max_y - 4)
    self.tectonic_cols = max(40, max_x - 2)
    rows, cols = self.tectonic_rows, self.tectonic_cols

    # Initialize elevation: start with ocean baseline
    self.tectonic_elevation = [[-4000.0] * cols for _ in range(rows)]
    self.tectonic_plate_id = [[0] * cols for _ in range(rows)]
    self.tectonic_volcanic = []
    self.tectonic_generation = 0
    self.tectonic_age = 0

    # Generate plates using Voronoi-like seeding
    num_plates = 6 if kind != "collision" else 4
    self.tectonic_num_plates = num_plates

    # Seed plate centers
    seeds = []
    if kind == "pangaea":
        # Cluster seeds in center for supercontinent
        for i in range(num_plates):
            r = rows // 2 + _rand.randint(-rows // 6, rows // 6)
            c = cols // 2 + _rand.randint(-cols // 6, cols // 6)
            seeds.append((r, c))
    elif kind == "collision":
        # Two groups on left and right
        for i in range(2):
            r = rows // 2 + _rand.randint(-rows // 8, rows // 8)
            c = cols // 4 + _rand.randint(-cols // 8, cols // 8)
            seeds.append((r, c))
        for i in range(2):
            r = rows // 2 + _rand.randint(-rows // 8, rows // 8)
            c = 3 * cols // 4 + _rand.randint(-cols // 8, cols // 8)
            seeds.append((r, c))
    else:
        for i in range(num_plates):
            seeds.append((_rand.randint(0, rows - 1), _rand.randint(0, cols - 1)))

    # Assign cells to nearest seed (Voronoi)
    for r in range(rows):
        for c in range(cols):
            best = 0
            best_d = float('inf')
            for i, (sr, sc) in enumerate(seeds):
                # Wrap-around distance
                dr = min(abs(r - sr), rows - abs(r - sr))
                dc = min(abs(c - sc), cols - abs(c - sc))
                d = dr * dr + dc * dc
                if d < best_d:
                    best_d = d
                    best = i
            self.tectonic_plate_id[r][c] = best

    # Define plate properties
    plate_colors = [1, 2, 3, 4, 5, 6]
    plate_names = ["Pacifica", "Laurasia", "Gondwana", "Tethys", "Panthalassa", "Rodinia"]

    self.tectonic_plates = []
    for i in range(num_plates):
        if kind == "pangaea":
            # Plates radiate outward from center
            angle = 2 * _math.pi * i / num_plates
            vr = _math.sin(angle) * 0.4
            vc = _math.cos(angle) * 0.4
            is_continental = True
        elif kind == "collision":
            # Left plates move right, right plates move left
            vr = _rand.uniform(-0.1, 0.1)
            vc = 0.5 if i < 2 else -0.5
            is_continental = True
        elif kind == "arcs":
            vr = _rand.uniform(-0.3, 0.3)
            vc = _rand.uniform(-0.3, 0.3)
            is_continental = (i < 2)
        elif kind == "ridges":
            angle = 2 * _math.pi * i / num_plates
            vr = _math.sin(angle) * 0.3
            vc = _math.cos(angle) * 0.3
            is_continental = (i % 2 == 0)
        elif kind == "ring":
            # Outer plates converge toward center
            sr, sc = seeds[i]
            dr = rows // 2 - sr
            dc = cols // 2 - sc
            dist = _math.sqrt(dr * dr + dc * dc) + 0.01
            vr = dr / dist * 0.3
            vc = dc / dist * 0.3
            is_continental = (i == 0)
        else:  # random
            vr = _rand.uniform(-0.5, 0.5)
            vc = _rand.uniform(-0.5, 0.5)
            is_continental = _rand.random() < 0.4

        self.tectonic_plates.append({
            "vr": vr, "vc": vc,
            "color": plate_colors[i % len(plate_colors)],
            "name": plate_names[i % len(plate_names)],
            "continental": is_continental,
            "seed_r": seeds[i][0], "seed_c": seeds[i][1],
            "accum_r": 0.0, "accum_c": 0.0,  # fractional movement accumulator
        })

    # Set initial elevation based on plate type
    for r in range(rows):
        for c in range(cols):
            pid = self.tectonic_plate_id[r][c]
            if self.tectonic_plates[pid]["continental"]:
                self.tectonic_elevation[r][c] = _rand.uniform(200, 800)
            else:
                self.tectonic_elevation[r][c] = _rand.uniform(-5000, -3000)

    self.tectonic_menu = False
    self.tectonic_mode = True
    self.tectonic_running = True
    self.tectonic_show_plates = False
    self.tectonic_show_help = True
    self._flash(f"Tectonic Plates: {self.tectonic_preset_name}")




def _tectonic_step(self):
    """Advance tectonic simulation by one time step."""
    import random as _rand
    import math as _math

    rows, cols = self.tectonic_rows, self.tectonic_cols
    elev = self.tectonic_elevation
    pid_map = self.tectonic_plate_id
    plates = self.tectonic_plates
    self.tectonic_generation += 1
    self.tectonic_age += 1  # each step = 1 MY

    speed = self.tectonic_speed_scale

    # Move plates: shift plate_id and elevation
    new_pid = [row[:] for row in pid_map]
    new_elev = [row[:] for row in elev]

    for pi, plate in enumerate(plates):
        plate["accum_r"] += plate["vr"] * speed
        plate["accum_c"] += plate["vc"] * speed

        shift_r = int(plate["accum_r"])
        shift_c = int(plate["accum_c"])

        if shift_r == 0 and shift_c == 0:
            continue

        plate["accum_r"] -= shift_r
        plate["accum_c"] -= shift_c

        # Move all cells of this plate
        for r in range(rows):
            for c in range(cols):
                if pid_map[r][c] == pi:
                    nr = (r + shift_r) % rows
                    nc = (c + shift_c) % cols
                    new_pid[nr][nc] = pi
                    new_elev[nr][nc] = elev[r][c]

    self.tectonic_plate_id = new_pid
    self.tectonic_elevation = new_elev
    elev = new_elev
    pid_map = new_pid

    # Detect boundaries and apply geological processes
    new_volcanic = []
    for r in range(rows):
        for c in range(cols):
            my_pid = pid_map[r][c]
            my_plate = plates[my_pid]

            # Check neighbors for plate boundaries
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr = (r + dr) % rows
                nc = (c + dc) % cols
                n_pid = pid_map[nr][nc]

                if n_pid == my_pid:
                    continue

                n_plate = plates[n_pid]

                # Compute relative velocity toward boundary
                rel_vr = my_plate["vr"] - n_plate["vr"]
                rel_vc = my_plate["vc"] - n_plate["vc"]
                # Dot product with boundary normal (dr, dc)
                convergence = rel_vr * dr + rel_vc * dc

                if convergence > 0.1:
                    # CONVERGENT boundary
                    if my_plate["continental"] and n_plate["continental"]:
                        # Continental-continental: mountain building
                        uplift = convergence * _rand.uniform(40, 120) * speed
                        elev[r][c] = min(9000, elev[r][c] + uplift)
                    elif my_plate["continental"]:
                        # Oceanic subducts under continental: volcanic arc
                        elev[r][c] = min(6000, elev[r][c] + convergence * _rand.uniform(20, 60) * speed)
                        if _rand.random() < 0.02 * convergence * speed:
                            new_volcanic.append((r, c))
                    else:
                        # Oceanic-oceanic: trench + island arc
                        elev[r][c] = max(-11000, elev[r][c] - convergence * _rand.uniform(30, 80) * speed)
                        if _rand.random() < 0.01 * convergence * speed:
                            # Island arc behind trench
                            br = (r - dr * 2) % rows
                            bc = (c - dc * 2) % cols
                            elev[br][bc] = min(3000, elev[br][bc] + _rand.uniform(100, 400))
                            new_volcanic.append((br, bc))

                elif convergence < -0.1:
                    # DIVERGENT boundary: rift valley / mid-ocean ridge
                    rift_rate = abs(convergence)
                    if my_plate["continental"] and elev[r][c] > 0:
                        # Continental rift valley
                        elev[r][c] = max(-2000, elev[r][c] - rift_rate * _rand.uniform(20, 60) * speed)
                    else:
                        # Mid-ocean ridge: new crust forms slightly elevated
                        elev[r][c] = _rand.uniform(-2500, -1500)
                        if _rand.random() < 0.03 * rift_rate * speed:
                            new_volcanic.append((r, c))

                else:
                    # TRANSFORM boundary: earthquakes, minor elevation change
                    if _rand.random() < 0.1:
                        elev[r][c] += _rand.uniform(-50, 50) * speed

    # Volcanic activity: hotspot eruptions raise elevation
    for vr, vc in self.tectonic_volcanic:
        if _rand.random() < 0.7:
            elev[vr][vc] = min(5000, elev[vr][vc] + _rand.uniform(50, 200) * speed)
            # Volcanic material spreads
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr = (vr + dr) % rows
                nc = (vc + dc) % cols
                elev[nr][nc] += _rand.uniform(10, 40) * speed
            if _rand.random() < 0.05:
                pass  # volcano goes dormant (not re-added)
            else:
                new_volcanic.append((vr, vc))

    # Random hotspot volcanism
    if _rand.random() < 0.01:
        hr = _rand.randint(0, rows - 1)
        hc = _rand.randint(0, cols - 1)
        new_volcanic.append((hr, hc))
        elev[hr][hc] = min(4000, elev[hr][hc] + _rand.uniform(200, 600))

    self.tectonic_volcanic = new_volcanic

    # Erosion: smooth toward neighbors, slightly reduce peaks
    if self.tectonic_generation % 3 == 0:
        for r in range(rows):
            for c in range(cols):
                avg = 0.0
                cnt = 0
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    avg += elev[nr][nc]
                    cnt += 1
                avg /= cnt
                # Blend slightly toward neighbor average (erosion)
                elev[r][c] = elev[r][c] * 0.97 + avg * 0.03
                # Extra erosion for very high peaks
                if elev[r][c] > 5000:
                    elev[r][c] -= _rand.uniform(5, 20)

    # Isostatic adjustment: very deep trenches slowly rebound
    for r in range(rows):
        for c in range(cols):
            if elev[r][c] < -9000:
                elev[r][c] += _rand.uniform(10, 50)




def _tectonic_elev_char(self, e: float) -> str:
    """Return ASCII character for elevation value."""
    chars = self.TECTONIC_ELEV_CHARS
    thresholds = self.TECTONIC_ELEV_THRESHOLDS
    for i, t in enumerate(thresholds):
        if e < t:
            return chars[i]
    return chars[-1]




def _tectonic_elev_color(self, e: float) -> int:
    """Return curses color pair for elevation value."""
    import curses
    if e < -3000:
        return curses.color_pair(5)  # deep ocean (magenta/blue)
    elif e < -500:
        return curses.color_pair(5)  # ocean
    elif e < 0:
        return curses.color_pair(7)  # shallow water (cyan)
    elif e < 300:
        return curses.color_pair(3)  # lowland (green)
    elif e < 1200:
        return curses.color_pair(3) | curses.A_BOLD  # hills
    elif e < 3000:
        return curses.color_pair(4)  # mountains (yellow)
    elif e < 6000:
        return curses.color_pair(4) | curses.A_BOLD  # high mountains
    else:
        return curses.color_pair(1) | curses.A_BOLD  # peaks (white/bright)




def _handle_tectonic_menu_key(self, key: int) -> bool:
    """Handle input in tectonic preset menu."""
    import curses
    n = len(self.TECTONIC_PRESETS)
    if key == curses.KEY_DOWN or key == ord('j'):
        self.tectonic_menu_sel = (self.tectonic_menu_sel + 1) % n
    elif key == curses.KEY_UP or key == ord('k'):
        self.tectonic_menu_sel = (self.tectonic_menu_sel - 1) % n
    elif key in (10, 13, curses.KEY_ENTER):
        self._tectonic_init(self.tectonic_menu_sel)
    elif key == 27:
        self.tectonic_menu = False
        self.tectonic_mode = False
        self._flash("Tectonic Plates cancelled")
    else:
        return True
    return True




def _handle_tectonic_key(self, key: int) -> bool:
    """Handle input in active tectonic simulation."""
    if key == -1:
        return True
    if key == ord(' '):
        self.tectonic_running = not self.tectonic_running
        self._flash("Paused" if not self.tectonic_running else "Running")
    elif key == ord('+') or key == ord('='):
        self.tectonic_speed_scale = min(5.0, self.tectonic_speed_scale + 0.25)
        self._flash(f"Speed: {self.tectonic_speed_scale:.1f}x")
    elif key == ord('-'):
        self.tectonic_speed_scale = max(0.25, self.tectonic_speed_scale - 0.25)
        self._flash(f"Speed: {self.tectonic_speed_scale:.1f}x")
    elif key == ord('p'):
        self.tectonic_show_plates = not self.tectonic_show_plates
        self._flash("Plate view: " + ("ON" if self.tectonic_show_plates else "OFF"))
    elif key == ord('?'):
        self.tectonic_show_help = not self.tectonic_show_help
    elif key == ord('r'):
        # Restart with same preset
        idx = self.tectonic_menu_sel
        self._tectonic_init(idx)
    elif key == ord('m'):
        self.tectonic_menu = True
        self.tectonic_menu_sel = 0
        self.tectonic_running = False
    elif key == 27:
        self.tectonic_mode = False
        self.tectonic_running = False
        self._flash("Tectonic Plates mode OFF")
    else:
        return True
    return True




def _draw_tectonic_menu(self, max_y: int, max_x: int):
    """Draw tectonic preset selection menu."""
    import curses
    title = "═══ Tectonic Plates ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(4))
        self.stdscr.addstr(3, 2, "Select a tectonic scenario:",
                           curses.color_pair(3))
        for i, (name, desc, _) in enumerate(self.TECTONIC_PRESETS):
            y = 5 + i * 2
            if y >= max_y - 2:
                break
            marker = "▸ " if i == self.tectonic_menu_sel else "  "
            attr = curses.A_BOLD | curses.color_pair(4) if i == self.tectonic_menu_sel else curses.color_pair(3)
            self.stdscr.addstr(y, 3, f"{marker}{name}", attr)
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], curses.A_DIM)
        foot_y = min(5 + len(self.TECTONIC_PRESETS) * 2 + 1, max_y - 2)
        self.stdscr.addstr(foot_y, 3, "Enter=Select  Esc=Cancel",
                           curses.A_DIM | curses.color_pair(6))
    except curses.error:
        pass




def _draw_tectonic(self, max_y: int, max_x: int):
    """Render tectonic simulation as ASCII topographic map."""
    import curses
    rows, cols = self.tectonic_rows, self.tectonic_cols
    elev = self.tectonic_elevation
    pid_map = self.tectonic_plate_id
    plates = self.tectonic_plates

    # Build set of volcanic cells for quick lookup
    volc_set = set(self.tectonic_volcanic)

    # Draw elevation map
    draw_rows = min(rows, max_y - 3)
    draw_cols = min(cols, max_x - 1)

    for r in range(draw_rows):
        line_chars = []
        line_attrs = []
        for c in range(draw_cols):
            e = elev[r][c]
            if (r, c) in volc_set and e > -500:
                ch = '^'
                attr = curses.color_pair(2) | curses.A_BOLD  # red volcano
            else:
                ch = self._tectonic_elev_char(e)
                if self.tectonic_show_plates:
                    pid = pid_map[r][c]
                    attr = curses.color_pair(plates[pid]["color"])
                else:
                    attr = self._tectonic_elev_color(e)
            line_chars.append(ch)
            line_attrs.append(attr)

        # Write line
        try:
            for c_idx, (ch, attr) in enumerate(zip(line_chars, line_attrs)):
                self.stdscr.addch(r, c_idx, ord(ch), attr)
        except curses.error:
            pass

    # Status bar
    status_y = min(draw_rows, max_y - 2)
    try:
        # Find elevation stats
        flat_elev = [elev[r][c] for r in range(rows) for c in range(cols)]
        min_e = min(flat_elev)
        max_e = max(flat_elev)
        avg_e = sum(flat_elev) / len(flat_elev)
        land_cells = sum(1 for e in flat_elev if e > 0)
        land_pct = land_cells / len(flat_elev) * 100

        status = (f" Age: {self.tectonic_age} MY │ "
                  f"Plates: {self.tectonic_num_plates} │ "
                  f"Land: {land_pct:.0f}% │ "
                  f"Elev: {min_e:.0f}m..{max_e:.0f}m │ "
                  f"Volcanoes: {len(self.tectonic_volcanic)} │ "
                  f"Speed: {self.tectonic_speed_scale:.1f}x ")
        self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                           curses.color_pair(0) | curses.A_REVERSE)
    except curses.error:
        pass

    # Legend bar
    try:
        legend = " ≈ocean  -coast  =plain  *hills  #mountain  ▲peak  ^volcano "
        self.stdscr.addstr(status_y + 1, 0, legend[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    # Help overlay
    if self.tectonic_show_help:
        help_lines = [
            "Controls:",
            " Space  Pause/Resume",
            " +/-    Speed up/down",
            " p      Toggle plate view",
            " r      Restart scenario",
            " m      Preset menu",
            " ?      Toggle this help",
            " Esc    Exit mode",
        ]
        hx = max(0, max_x - 24)
        hy = 1
        try:
            for i, line in enumerate(help_lines):
                if hy + i >= max_y - 3:
                    break
                self.stdscr.addstr(hy + i, hx, line[:24],
                                   curses.A_DIM | curses.color_pair(6))
        except curses.error:
            pass


# Bind methods to App class


def register(App):
    """Register tectonic mode methods and constants on the App class."""
    # Class-level constants (from original monolith)
    if not hasattr(App, 'TECTONIC_PRESETS'):
        App.TECTONIC_PRESETS = TECTONIC_PRESETS
    if not hasattr(App, 'TECTONIC_ELEV_CHARS'):
        App.TECTONIC_ELEV_CHARS = TECTONIC_ELEV_CHARS
    if not hasattr(App, 'TECTONIC_ELEV_THRESHOLDS'):
        App.TECTONIC_ELEV_THRESHOLDS = TECTONIC_ELEV_THRESHOLDS
    App._enter_tectonic_mode = _enter_tectonic_mode
    App._exit_tectonic_mode = _exit_tectonic_mode
    App._tectonic_init = _tectonic_init
    App._tectonic_step = _tectonic_step
    App._tectonic_elev_char = _tectonic_elev_char
    App._tectonic_elev_color = _tectonic_elev_color
    App._handle_tectonic_menu_key = _handle_tectonic_menu_key
    App._handle_tectonic_key = _handle_tectonic_key
    App._draw_tectonic_menu = _draw_tectonic_menu
    App._draw_tectonic = _draw_tectonic

