"""Mode: volcano — simulation mode for the life package."""
import curses
import math
import random
import time

VOLCANO_PRESETS = [
    ("Strombolian", "Mild, rhythmic eruptions with lava fountains and slow flows", "strombolian"),
    ("Plinian", "Catastrophic explosive eruption with massive ash column", "plinian"),
    ("Hawaiian", "Effusive shield volcano with fluid lava rivers", "hawaiian"),
    ("Vulcanian", "Viscous magma with violent bursts and pyroclastic surges", "vulcanian"),
    ("Caldera Collapse", "Mega-eruption draining a magma chamber into caldera", "caldera"),
    ("Fissure Eruption", "Curtain of fire along a rift with lava flooding a plain", "fissure"),
]

LAVA_CHARS = ' .·:;+*#@█'
TERRAIN_CHARS = ' ░▒▓█'
ASH_CHARS = ' .,:;░▒▓█'
ROCK_CHARS = ' .:;oO0@#'


def _enter_volcano_mode(self):
    """Enter Volcanic Eruption mode — show preset menu."""
    self.volcano_menu = True
    self.volcano_menu_sel = 0
    self._flash("Volcanic Eruption — select a scenario")




def _exit_volcano_mode(self):
    """Exit Volcanic Eruption mode."""
    self.volcano_mode = False
    self.volcano_menu = False
    self.volcano_running = False
    self._flash("Volcanic Eruption mode OFF")




def _volcano_init(self, preset_idx: int):
    """Initialize volcanic simulation from preset."""
    import random as _rand
    import math as _math

    name, desc, ptype = VOLCANO_PRESETS[preset_idx]
    self.volcano_preset_name = name
    self.volcano_menu = False
    self.volcano_mode = True
    self.volcano_running = True
    self.volcano_generation = 0
    self.volcano_tick = 0
    self.volcano_show_help = True
    self.volcano_speed_scale = 1.0
    self.volcano_layer = "default"
    self.volcano_eruption_log = []

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max_y - 3
    cols = max_x - 1
    self.volcano_rows = rows
    self.volcano_cols = cols

    # Initialize grids
    self.volcano_terrain = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.volcano_lava = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.volcano_lava_temp = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.volcano_rock = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.volcano_ash = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.volcano_gas = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.volcano_pyroclastic = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.volcano_vents = []
    self.volcano_chambers = []
    self.volcano_particles = []

    # Base wind
    self.volcano_wind_u = _rand.uniform(-0.5, 0.5)
    self.volcano_wind_v = _rand.uniform(-0.3, 0.3)

    mid_r, mid_c = rows // 2, cols // 2

    if ptype == "strombolian":
        # Single conical volcano, moderate eruptions
        _volcano_build_cone(self, mid_r, mid_c, min(rows, cols) // 3, 0.85)
        self.volcano_vents.append({
            "r": mid_r, "c": mid_c, "strength": 0.6, "active": True,
            "type": "strombolian", "eject_rate": 0.4, "lava_rate": 0.3,
        })
        self.volcano_chambers.append({
            "r": mid_r, "c": mid_c, "pressure": 0.5, "max_pressure": 1.0,
            "recharge_rate": 0.015, "radius": min(rows, cols) // 4,
            "magma_volume": 0.7, "viscosity": 0.5,
        })

    elif ptype == "plinian":
        # Tall stratovolcano, massive explosive eruption
        _volcano_build_cone(self, mid_r, mid_c, min(rows, cols) // 3, 0.95)
        self.volcano_vents.append({
            "r": mid_r, "c": mid_c, "strength": 1.0, "active": True,
            "type": "plinian", "eject_rate": 0.9, "lava_rate": 0.1,
        })
        self.volcano_chambers.append({
            "r": mid_r, "c": mid_c, "pressure": 0.85, "max_pressure": 1.0,
            "recharge_rate": 0.005, "radius": min(rows, cols) // 3,
            "magma_volume": 0.9, "viscosity": 0.8,
        })
        self.volcano_wind_u = _rand.uniform(0.3, 1.0)  # strong prevailing wind
        self.volcano_wind_v = _rand.uniform(-0.3, 0.3)

    elif ptype == "hawaiian":
        # Broad shield volcano with fluid lava
        _volcano_build_cone(self, mid_r, mid_c, min(rows, cols) * 2 // 5, 0.5)
        self.volcano_vents.append({
            "r": mid_r, "c": mid_c, "strength": 0.5, "active": True,
            "type": "hawaiian", "eject_rate": 0.15, "lava_rate": 0.8,
        })
        # Secondary vent on flank
        flank_r = mid_r + rows // 6
        flank_c = mid_c + cols // 8
        if flank_r < rows and flank_c < cols:
            self.volcano_vents.append({
                "r": flank_r, "c": flank_c, "strength": 0.3, "active": True,
                "type": "hawaiian", "eject_rate": 0.1, "lava_rate": 0.6,
            })
        self.volcano_chambers.append({
            "r": mid_r, "c": mid_c, "pressure": 0.6, "max_pressure": 1.0,
            "recharge_rate": 0.02, "radius": min(rows, cols) // 3,
            "magma_volume": 0.8, "viscosity": 0.2,
        })

    elif ptype == "vulcanian":
        # Viscous dome-building volcano with violent bursts
        _volcano_build_cone(self, mid_r, mid_c, min(rows, cols) // 4, 0.75)
        self.volcano_vents.append({
            "r": mid_r, "c": mid_c, "strength": 0.8, "active": True,
            "type": "vulcanian", "eject_rate": 0.7, "lava_rate": 0.2,
        })
        self.volcano_chambers.append({
            "r": mid_r, "c": mid_c, "pressure": 0.7, "max_pressure": 1.0,
            "recharge_rate": 0.008, "radius": min(rows, cols) // 5,
            "magma_volume": 0.6, "viscosity": 0.9,
        })

    elif ptype == "caldera":
        # Supervolcano caldera collapse
        # Build a broad raised plateau with a depression
        _volcano_build_cone(self, mid_r, mid_c, min(rows, cols) * 2 // 5, 0.6)
        # Caldera depression in center
        caldera_r = min(rows, cols) // 6
        for r in range(rows):
            for c in range(cols):
                dr = r - mid_r
                dc = c - mid_c
                dist = _math.sqrt(dr * dr + dc * dc)
                if dist < caldera_r:
                    depression = 0.25 * (1.0 - dist / caldera_r)
                    self.volcano_terrain[r][c] = max(0.05, self.volcano_terrain[r][c] - depression)
        # Multiple vents along the ring
        for angle in range(0, 360, 90):
            rad = _math.radians(angle)
            vr = int(mid_r + caldera_r * 0.7 * _math.sin(rad))
            vc = int(mid_c + caldera_r * 1.2 * _math.cos(rad))
            vr = max(1, min(rows - 2, vr))
            vc = max(1, min(cols - 2, vc))
            self.volcano_vents.append({
                "r": vr, "c": vc, "strength": 0.7, "active": True,
                "type": "plinian", "eject_rate": 0.8, "lava_rate": 0.4,
            })
        self.volcano_chambers.append({
            "r": mid_r, "c": mid_c, "pressure": 0.9, "max_pressure": 1.0,
            "recharge_rate": 0.003, "radius": min(rows, cols) // 3,
            "magma_volume": 1.0, "viscosity": 0.6,
        })

    elif ptype == "fissure":
        # Linear fissure eruption
        # Gentle terrain with a rift
        for r in range(rows):
            for c in range(cols):
                self.volcano_terrain[r][c] = 0.15 + _rand.uniform(-0.03, 0.03)
        # Build fissure line across the middle
        fissure_c_start = cols // 4
        fissure_c_end = cols * 3 // 4
        n_vents = 6
        for i in range(n_vents):
            vc = fissure_c_start + i * (fissure_c_end - fissure_c_start) // (n_vents - 1)
            vr = mid_r + _rand.randint(-2, 2)
            self.volcano_vents.append({
                "r": vr, "c": vc, "strength": 0.4, "active": True,
                "type": "hawaiian", "eject_rate": 0.1, "lava_rate": 0.7,
            })
            # Small ridges along fissure
            for dr in range(-1, 2):
                rr = max(0, min(rows - 1, vr + dr))
                self.volcano_terrain[rr][vc] += 0.1
        self.volcano_chambers.append({
            "r": mid_r, "c": mid_c, "pressure": 0.65, "max_pressure": 1.0,
            "recharge_rate": 0.018, "radius": cols // 3,
            "magma_volume": 0.85, "viscosity": 0.15,
        })

    self._flash(f"Volcanic Eruption: {self.volcano_preset_name}")




def _volcano_build_cone(self, center_r, center_c, radius, peak_height):
    """Build a volcanic cone on the terrain grid."""
    import math as _math
    import random as _rand
    rows, cols = self.volcano_rows, self.volcano_cols
    radius = max(1, radius)
    for r in range(rows):
        for c in range(cols):
            dr = r - center_r
            dc = (c - center_c) * 0.6  # wider E-W for terminal aspect ratio
            dist = _math.sqrt(dr * dr + dc * dc)
            if dist < radius:
                height = peak_height * (1.0 - dist / radius) ** 1.3
                noise = _rand.uniform(-0.02, 0.02)
                self.volcano_terrain[r][c] = max(self.volcano_terrain[r][c], height + noise)
            else:
                # Gentle foothills
                falloff = _math.exp(-(dist - radius) ** 2 / (radius * 0.5) ** 2)
                base = 0.08 * falloff + _rand.uniform(-0.01, 0.01)
                self.volcano_terrain[r][c] = max(self.volcano_terrain[r][c], base)




def _volcano_step(self):
    """Advance volcanic simulation by one time step."""
    import random as _rand
    import math as _math

    self.volcano_generation += 1
    self.volcano_tick += 1
    rows, cols = self.volcano_rows, self.volcano_cols
    speed = self.volcano_speed_scale

    # ── Magma chamber pressure dynamics ──
    for chamber in self.volcano_chambers:
        # Pressure recharges over time (magma influx from below)
        if chamber["magma_volume"] > 0.05:
            chamber["pressure"] += chamber["recharge_rate"] * speed
            chamber["pressure"] = min(chamber["max_pressure"], chamber["pressure"])

    # ── Eruption events from vents ──
    for vent in self.volcano_vents:
        if not vent["active"]:
            continue
        # Find associated chamber
        chamber = None
        for ch in self.volcano_chambers:
            dr = vent["r"] - ch["r"]
            dc = vent["c"] - ch["c"]
            if _math.sqrt(dr * dr + dc * dc) < ch["radius"]:
                chamber = ch
                break
        if not chamber:
            continue

        pressure = chamber["pressure"]
        viscosity = chamber["viscosity"]

        # Eruption threshold depends on type
        threshold = 0.4 if vent["type"] == "hawaiian" else 0.6

        if pressure > threshold:
            eruption_intensity = (pressure - threshold) / (1.0 - threshold)
            eruption_intensity *= vent["strength"]

            vr, vc = vent["r"], vent["c"]

            # Emit lava at vent
            lava_output = vent["lava_rate"] * eruption_intensity * speed * (1.0 - viscosity * 0.5)
            if 0 <= vr < rows and 0 <= vc < cols:
                self.volcano_lava[vr][vc] = min(1.0, self.volcano_lava[vr][vc] + lava_output * 0.15)
                self.volcano_lava_temp[vr][vc] = min(1200.0, max(self.volcano_lava_temp[vr][vc], 1100.0))

            # Eject particles (bombs, tephra)
            n_ejecta = int(vent["eject_rate"] * eruption_intensity * 5 * speed)
            for _ in range(min(n_ejecta, 20)):
                angle = _rand.uniform(0, 2 * _math.pi)
                eject_speed = _rand.uniform(1, 4) * eruption_intensity
                self.volcano_particles.append({
                    "r": float(vr), "c": float(vc),
                    "vr": -_rand.uniform(0.5, 2.0) * eruption_intensity + _math.sin(angle) * eject_speed * 0.3,
                    "vc": _math.cos(angle) * eject_speed,
                    "life": _rand.randint(5, 25),
                    "size": _rand.uniform(0.3, 1.0),
                    "type": "bomb" if _rand.random() < 0.3 else "tephra",
                })

            # Generate ash
            ash_output = vent["eject_rate"] * eruption_intensity * speed
            if 0 <= vr < rows and 0 <= vc < cols:
                self.volcano_ash[vr][vc] = min(1.0, self.volcano_ash[vr][vc] + ash_output * 0.2)
                self.volcano_gas[vr][vc] = min(1.0, self.volcano_gas[vr][vc] + ash_output * 0.1)

            # Pyroclastic density current generation (for explosive types)
            if vent["type"] in ("plinian", "vulcanian") and eruption_intensity > 0.5:
                if _rand.random() < 0.15 * speed:
                    # Column collapse → pyroclastic flow
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            pr = vr + dr
                            pc = vc + dc
                            if 0 <= pr < rows and 0 <= pc < cols:
                                self.volcano_pyroclastic[pr][pc] = min(
                                    1.0, self.volcano_pyroclastic[pr][pc] + 0.3 * eruption_intensity)
                    if len(self.volcano_eruption_log) < 20:
                        self.volcano_eruption_log.append(f"T{self.volcano_tick}: Pyroclastic surge!")

            # Drain pressure from eruption
            drain = 0.01 * eruption_intensity * speed
            chamber["pressure"] = max(0.0, chamber["pressure"] - drain)
            chamber["magma_volume"] = max(0.0, chamber["magma_volume"] - drain * 0.005)

            # Log eruption events
            if eruption_intensity > 0.7 and self.volcano_tick % 20 == 0 and len(self.volcano_eruption_log) < 20:
                self.volcano_eruption_log.append(f"T{self.volcano_tick}: Major eruption! I={eruption_intensity:.1f}")

    # ── Lava flow physics (fluid over terrain, gravity-driven) ──
    new_lava = [row[:] for row in self.volcano_lava]
    new_temp = [row[:] for row in self.volcano_lava_temp]

    for r in range(rows):
        for c in range(cols):
            lava = self.volcano_lava[r][c]
            if lava < 0.01:
                continue
            temp = self.volcano_lava_temp[r][c]
            # Viscosity increases as lava cools
            temp_factor = max(0.05, min(1.0, (temp - 400) / 800.0))
            flow_rate = 0.08 * temp_factor * speed

            # Current effective elevation = terrain + rock + lava
            here_elev = self.volcano_terrain[r][c] + self.volcano_rock[r][c] + lava

            # Flow to lower neighbors (4-connected + diagonals)
            neighbors = []
            for dr, dc_off in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = r + dr, c + dc_off
                if 0 <= nr < rows and 0 <= nc < cols:
                    n_elev = self.volcano_terrain[nr][nc] + self.volcano_rock[nr][nc] + self.volcano_lava[nr][nc]
                    diff = here_elev - n_elev
                    if diff > 0:
                        # Diagonal flow is slower
                        weight = diff * (0.7 if abs(dr) + abs(dc_off) == 2 else 1.0)
                        neighbors.append((nr, nc, weight))

            if neighbors:
                total_weight = sum(w for _, _, w in neighbors)
                flow_amount = min(lava * flow_rate, lava * 0.5)
                for nr, nc, w in neighbors:
                    transfer = flow_amount * w / total_weight
                    new_lava[nr][nc] += transfer
                    new_lava[r][c] -= transfer
                    # Transfer heat with lava
                    new_temp[nr][nc] = max(new_temp[nr][nc], temp * 0.85)

    self.volcano_lava = new_lava
    self.volcano_lava_temp = new_temp

    # ── Lava cooling and solidification ──
    for r in range(rows):
        for c in range(cols):
            if self.volcano_lava_temp[r][c] > 0:
                # Radiative cooling
                cooling_rate = 3.0 * speed
                self.volcano_lava_temp[r][c] = max(0, self.volcano_lava_temp[r][c] - cooling_rate)

                # Solidification: lava below 500°C turns to rock
                if self.volcano_lava_temp[r][c] < 500 and self.volcano_lava[r][c] > 0.01:
                    solidify = min(self.volcano_lava[r][c], 0.02 * speed)
                    self.volcano_lava[r][c] -= solidify
                    self.volcano_rock[r][c] += solidify * 0.8
                    # Terrain deformation: cooled lava becomes new terrain
                    self.volcano_terrain[r][c] += solidify * 0.2

    # ── Pyroclastic density current flow (fast, hugs terrain) ──
    new_pyro = [row[:] for row in self.volcano_pyroclastic]
    for r in range(rows):
        for c in range(cols):
            pyro = self.volcano_pyroclastic[r][c]
            if pyro < 0.01:
                continue
            # PDCs flow fast downhill
            here_elev = self.volcano_terrain[r][c]
            flow_rate = 0.25 * speed
            best_drop = 0
            targets = []
            for dr, dc_off in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc_off
                if 0 <= nr < rows and 0 <= nc < cols:
                    n_elev = self.volcano_terrain[nr][nc]
                    drop = here_elev - n_elev
                    if drop > -0.05:  # PDCs can flow slightly uphill
                        targets.append((nr, nc, max(0.01, drop + 0.05)))
            if targets:
                total_w = sum(w for _, _, w in targets)
                flow = min(pyro * flow_rate, pyro * 0.6)
                for nr, nc, w in targets:
                    transfer = flow * w / total_w
                    new_pyro[nr][nc] += transfer
                    new_pyro[r][c] -= transfer
            # PDCs dissipate
            new_pyro[r][c] *= (0.96 if speed <= 1.0 else 0.96 ** speed)
            # Leave ash deposit
            if pyro > 0.1:
                self.volcano_ash[r][c] = min(1.0, self.volcano_ash[r][c] + pyro * 0.02 * speed)
    self.volcano_pyroclastic = new_pyro

    # ── Ash dispersion by wind ──
    new_ash = [row[:] for row in self.volcano_ash]
    wu = self.volcano_wind_u
    wv = self.volcano_wind_v
    for r in range(rows):
        for c in range(cols):
            ash = self.volcano_ash[r][c]
            if ash < 0.005:
                continue
            # Wind advection (semi-Lagrangian)
            src_r = r - wv * speed
            src_c = c - wu * speed
            sr, sc = int(src_r) % rows, int(src_c) % cols
            if 0 <= sr < rows and 0 <= sc < cols:
                new_ash[r][c] = self.volcano_ash[sr][sc] * 0.92
            # Diffusion
            diffuse = ash * 0.03 * speed
            for dr, dc_off in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc_off
                if 0 <= nr < rows and 0 <= nc < cols:
                    new_ash[nr][nc] += diffuse * 0.25
            new_ash[r][c] -= diffuse
            # Ash settles
            new_ash[r][c] *= 0.995
    # Clamp
    for r in range(rows):
        for c in range(cols):
            new_ash[r][c] = max(0.0, min(1.0, new_ash[r][c]))
    self.volcano_ash = new_ash

    # ── Gas dispersion ──
    new_gas = [row[:] for row in self.volcano_gas]
    for r in range(rows):
        for c in range(cols):
            gas = self.volcano_gas[r][c]
            if gas < 0.005:
                continue
            # Wind + buoyant rise (dissipation)
            diffuse = gas * 0.05 * speed
            for dr, dc_off in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = (r + dr) % rows, (c + dc_off) % cols
                new_gas[nr][nc] += diffuse * 0.25
            new_gas[r][c] -= diffuse
            new_gas[r][c] *= 0.98
    for r in range(rows):
        for c in range(cols):
            new_gas[r][c] = max(0.0, min(1.0, new_gas[r][c]))
    self.volcano_gas = new_gas

    # ── Ejecta particle update ──
    surviving = []
    for p in self.volcano_particles:
        p["r"] += p["vr"] * speed
        p["c"] += p["vc"] * speed
        p["vr"] += 0.15 * speed  # gravity
        p["vc"] += self.volcano_wind_u * 0.05 * speed
        p["life"] -= 1

        pr, pc = int(p["r"]), int(p["c"])
        if p["life"] > 0 and 0 <= pr < rows and 0 <= pc < cols:
            # Check if particle has landed (below terrain level analogy)
            if p["vr"] > 0 and p["life"] < 3:
                # Impact: deposit as rock or ash
                if p["type"] == "bomb":
                    self.volcano_rock[pr][pc] = min(1.0, self.volcano_rock[pr][pc] + p["size"] * 0.05)
                else:
                    self.volcano_ash[pr][pc] = min(1.0, self.volcano_ash[pr][pc] + p["size"] * 0.03)
            else:
                surviving.append(p)
        # Out of bounds particles just die
    self.volcano_particles = surviving[:200]  # cap particle count

    # ── Wind variation ──
    self.volcano_wind_u += _rand.uniform(-0.02, 0.02) * speed
    self.volcano_wind_v += _rand.uniform(-0.02, 0.02) * speed
    self.volcano_wind_u = max(-2.0, min(2.0, self.volcano_wind_u))
    self.volcano_wind_v = max(-2.0, min(2.0, self.volcano_wind_v))




def _handle_volcano_menu_key(self, key: int) -> bool:
    """Handle input in volcano preset menu."""
    import curses
    n = len(VOLCANO_PRESETS)
    if key == curses.KEY_DOWN or key == ord('j'):
        self.volcano_menu_sel = (self.volcano_menu_sel + 1) % n
    elif key == curses.KEY_UP or key == ord('k'):
        self.volcano_menu_sel = (self.volcano_menu_sel - 1) % n
    elif key in (10, 13, curses.KEY_ENTER):
        self._volcano_init(self.volcano_menu_sel)
    elif key == 27:
        self.volcano_menu = False
        self.volcano_mode = False
        self._flash("Volcanic Eruption cancelled")
    else:
        return True
    return True




def _handle_volcano_key(self, key: int) -> bool:
    """Handle input in active volcano simulation."""
    if key == -1:
        return True
    if key == ord(' '):
        self.volcano_running = not self.volcano_running
        self._flash("Paused" if not self.volcano_running else "Running")
    elif key == ord('+') or key == ord('='):
        self.volcano_speed_scale = min(5.0, self.volcano_speed_scale + 0.25)
        self._flash(f"Speed: {self.volcano_speed_scale:.1f}x")
    elif key == ord('-'):
        self.volcano_speed_scale = max(0.25, self.volcano_speed_scale - 0.25)
        self._flash(f"Speed: {self.volcano_speed_scale:.1f}x")
    elif key == ord('l') or key == ord('v'):
        layers = ["default", "terrain", "lava", "temperature", "ash", "pyroclastic"]
        idx = layers.index(self.volcano_layer) if self.volcano_layer in layers else 0
        self.volcano_layer = layers[(idx + 1) % len(layers)]
        self._flash(f"Layer: {self.volcano_layer}")
    elif key == ord('e'):
        # Force eruption: spike chamber pressure
        for ch in self.volcano_chambers:
            ch["pressure"] = ch["max_pressure"]
        self._flash("Forced eruption!")
    elif key == ord('?'):
        self.volcano_show_help = not self.volcano_show_help
    elif key == ord('r'):
        idx = next((i for i, (n, _, _) in enumerate(VOLCANO_PRESETS)
                     if n == self.volcano_preset_name), 0)
        self._volcano_init(idx)
    elif key == ord('m'):
        self.volcano_running = False
        self.volcano_menu = True
        self.volcano_menu_sel = 0
    elif key == 27:
        self._exit_volcano_mode()
    else:
        return True
    return True




def _draw_volcano_menu(self, max_y: int, max_x: int):
    """Draw volcano preset selection menu."""
    import curses
    title = "═══ Volcanic Eruption & Lava Flow ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(2))
        self.stdscr.addstr(3, 2, "Select an eruption scenario:",
                           curses.color_pair(4))
        for i, (name, desc, _) in enumerate(VOLCANO_PRESETS):
            y = 5 + i * 2
            if y >= max_y - 2:
                break
            marker = "▸ " if i == self.volcano_menu_sel else "  "
            attr = curses.A_BOLD | curses.color_pair(2) if i == self.volcano_menu_sel else curses.color_pair(4)
            self.stdscr.addstr(y, 3, f"{marker}{name}", attr)
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], curses.A_DIM)
        foot_y = min(5 + len(VOLCANO_PRESETS) * 2 + 1, max_y - 2)
        self.stdscr.addstr(foot_y, 3, "Enter=Select  Esc=Cancel",
                           curses.A_DIM | curses.color_pair(6))
    except curses.error:
        pass




def _volcano_terrain_color(self, elev: float) -> int:
    """Return curses color pair for terrain elevation."""
    import curses
    if elev > 0.8:
        return curses.color_pair(1) | curses.A_BOLD   # peak = white bold
    elif elev > 0.6:
        return curses.color_pair(4)                     # high = yellow
    elif elev > 0.35:
        return curses.color_pair(3)                     # mid = green
    elif elev > 0.15:
        return curses.color_pair(6)                     # low = brown/cyan
    else:
        return curses.A_DIM                             # flat




def _volcano_lava_color(self, temp: float, thickness: float) -> int:
    """Return curses color pair for lava based on temperature."""
    import curses
    if temp > 900:
        return curses.color_pair(4) | curses.A_BOLD    # incandescent = bright yellow
    elif temp > 700:
        return curses.color_pair(2) | curses.A_BOLD    # hot = bright red
    elif temp > 500:
        return curses.color_pair(2)                     # cooling = red
    elif temp > 300:
        return curses.color_pair(6)                     # dim = dark
    else:
        return curses.A_DIM




def _draw_volcano(self, max_y: int, max_x: int):
    """Render volcanic simulation as ASCII volcanic landscape."""
    import curses
    import math as _math
    rows, cols = self.volcano_rows, self.volcano_cols
    draw_rows = min(rows, max_y - 3)
    draw_cols = min(cols, max_x - 1)

    layer = self.volcano_layer

    for r in range(draw_rows):
        for c in range(draw_cols):
            try:
                if layer == "terrain":
                    elev = self.volcano_terrain[r][c] + self.volcano_rock[r][c]
                    idx = int(elev * 4)
                    idx = max(0, min(4, idx))
                    ch = TERRAIN_CHARS[idx]
                    attr = self._volcano_terrain_color(elev)
                    self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

                elif layer == "lava":
                    lava = self.volcano_lava[r][c]
                    if lava > 0.01:
                        idx = int(lava * 9)
                        idx = max(1, min(9, idx))
                        ch = LAVA_CHARS[idx]
                        attr = self._volcano_lava_color(self.volcano_lava_temp[r][c], lava)
                        self.stdscr.addch(r, c, ord(ch), attr)
                    else:
                        self.stdscr.addch(r, c, ord(' '), curses.A_DIM)

                elif layer == "temperature":
                    temp = self.volcano_lava_temp[r][c]
                    if temp > 10:
                        idx = int(temp / 1200 * 9)
                        idx = max(1, min(9, idx))
                        ch = LAVA_CHARS[idx]
                        if temp > 900:
                            attr = curses.color_pair(4) | curses.A_BOLD
                        elif temp > 600:
                            attr = curses.color_pair(2) | curses.A_BOLD
                        elif temp > 300:
                            attr = curses.color_pair(2)
                        else:
                            attr = curses.color_pair(6)
                        self.stdscr.addch(r, c, ord(ch), attr)
                    else:
                        self.stdscr.addch(r, c, ord(' '), curses.A_DIM)

                elif layer == "ash":
                    ash = self.volcano_ash[r][c]
                    idx = int(ash * 8)
                    idx = max(0, min(7, idx))
                    ch = ASH_CHARS[idx]
                    if ash > 0.5:
                        attr = curses.color_pair(1) | curses.A_BOLD
                    elif ash > 0.2:
                        attr = curses.color_pair(6)
                    else:
                        attr = curses.A_DIM
                    self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

                elif layer == "pyroclastic":
                    pyro = self.volcano_pyroclastic[r][c]
                    if pyro > 0.02:
                        idx = int(pyro * 9)
                        idx = max(1, min(9, idx))
                        ch = LAVA_CHARS[idx]
                        if pyro > 0.5:
                            attr = curses.color_pair(2) | curses.A_BOLD
                        elif pyro > 0.2:
                            attr = curses.color_pair(4)
                        else:
                            attr = curses.color_pair(6) | curses.A_DIM
                        self.stdscr.addch(r, c, ord(ch), attr)
                    else:
                        self.stdscr.addch(r, c, ord(' '), curses.A_DIM)

                else:  # default composite view
                    lava = self.volcano_lava[r][c]
                    temp = self.volcano_lava_temp[r][c]
                    pyro = self.volcano_pyroclastic[r][c]
                    ash = self.volcano_ash[r][c]
                    rock = self.volcano_rock[r][c]
                    terrain = self.volcano_terrain[r][c]

                    if pyro > 0.15:
                        # Pyroclastic current: deadly fast-moving cloud
                        idx = int(pyro * 8)
                        idx = max(1, min(8, idx))
                        ch = '░▒▓█████'[min(idx, 7)]
                        if pyro > 0.5:
                            attr = curses.color_pair(2) | curses.A_BOLD
                        else:
                            attr = curses.color_pair(4) | curses.A_DIM
                        self.stdscr.addch(r, c, ord(ch), attr)

                    elif lava > 0.02:
                        # Active lava flow
                        idx = int(lava * 9)
                        idx = max(1, min(9, idx))
                        ch = LAVA_CHARS[idx]
                        attr = self._volcano_lava_color(temp, lava)
                        self.stdscr.addch(r, c, ord(ch), attr)

                    elif ash > 0.15:
                        # Ash fall
                        idx = int(ash * 7)
                        idx = max(1, min(7, idx))
                        ch = ASH_CHARS[idx]
                        attr = curses.color_pair(6) | curses.A_DIM
                        self.stdscr.addch(r, c, ord(ch), attr)

                    elif rock > 0.03:
                        # Cooled rock deposits
                        idx = int(rock * 8)
                        idx = max(1, min(8, idx))
                        ch = ROCK_CHARS[min(idx, 8)]
                        attr = curses.color_pair(6)
                        self.stdscr.addch(r, c, ord(ch), attr)

                    else:
                        # Base terrain
                        elev = terrain
                        idx = int(elev * 4)
                        idx = max(0, min(4, idx))
                        ch = TERRAIN_CHARS[idx]
                        attr = self._volcano_terrain_color(elev)
                        self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

            except curses.error:
                pass

    # Draw ejecta particles
    for p in self.volcano_particles:
        pr, pc = int(p["r"]), int(p["c"])
        if 0 <= pr < draw_rows and 0 <= pc < draw_cols:
            try:
                ch = '*' if p["type"] == "bomb" else '·'
                attr = curses.color_pair(4) | curses.A_BOLD if p["type"] == "bomb" else curses.color_pair(2)
                self.stdscr.addch(pr, pc, ord(ch), attr)
            except curses.error:
                pass

    # Mark vents
    for vent in self.volcano_vents:
        vr, vc = vent["r"], vent["c"]
        if 0 <= vr < draw_rows and 0 <= vc < draw_cols:
            try:
                if vent["active"]:
                    # Check if erupting
                    erupting = any(ch["pressure"] > 0.4 for ch in self.volcano_chambers)
                    ch = '▲' if erupting else '△'
                    attr = curses.color_pair(2) | curses.A_BOLD if erupting else curses.color_pair(4)
                else:
                    ch = '△'
                    attr = curses.A_DIM
                self.stdscr.addch(vr, vc, ord(ch), attr)
            except curses.error:
                pass

    # Status bar
    status_y = min(draw_rows, max_y - 2)
    try:
        total_lava = sum(self.volcano_lava[r][c] for r in range(rows) for c in range(cols))
        total_ash = sum(self.volcano_ash[r][c] for r in range(rows) for c in range(cols))
        total_rock = sum(self.volcano_rock[r][c] for r in range(rows) for c in range(cols))
        max_pressure = max((ch["pressure"] for ch in self.volcano_chambers), default=0)
        n_particles = len(self.volcano_particles)

        status = (f" T{self.volcano_tick} │ "
                  f"Pressure: {max_pressure:.0%} │ "
                  f"Lava: {total_lava:.0f} │ "
                  f"Ash: {total_ash:.0f} │ "
                  f"Rock: {total_rock:.0f} │ "
                  f"Ejecta: {n_particles} │ "
                  f"Wind: {self.volcano_wind_u:.1f},{self.volcano_wind_v:.1f} │ "
                  f"Layer: {self.volcano_layer} │ "
                  f"Speed: {self.volcano_speed_scale:.1f}x ")
        self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                           curses.color_pair(0) | curses.A_REVERSE)
    except curses.error:
        pass

    # Legend bar
    try:
        legend = " ▲vent *bomb ·tephra ░▒ash #lava █pyro ░▓terrain "
        self.stdscr.addstr(status_y + 1, 0, legend[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    # Help overlay
    if self.volcano_show_help:
        help_lines = [
            "Controls:",
            " Space  Pause/Resume",
            " +/-    Speed up/down",
            " l/v    Cycle layers",
            "        (default/terrain/lava",
            "         /temperature/ash/",
            "         pyroclastic)",
            " e      Force eruption",
            " r      Restart scenario",
            " m      Preset menu",
            " ?      Toggle this help",
            " Esc    Exit mode",
        ]
        hx = max(0, max_x - 28)
        hy = 1
        try:
            for i, line in enumerate(help_lines):
                if hy + i >= max_y - 3:
                    break
                self.stdscr.addstr(hy + i, hx, line[:28],
                                   curses.A_DIM | curses.color_pair(6))
        except curses.error:
            pass


# Bind volcano methods to App class


def register(App):
    """Register volcano mode methods on the App class."""
    App._enter_volcano_mode = _enter_volcano_mode
    App._exit_volcano_mode = _exit_volcano_mode
    App._volcano_init = _volcano_init
    App._volcano_build_cone = _volcano_build_cone
    App._volcano_step = _volcano_step
    App._handle_volcano_menu_key = _handle_volcano_menu_key
    App._handle_volcano_key = _handle_volcano_key
    App._draw_volcano_menu = _draw_volcano_menu
    App._volcano_terrain_color = _volcano_terrain_color
    App._volcano_lava_color = _volcano_lava_color
    App._draw_volcano = _draw_volcano

