"""Mode: weather — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_weather_mode(self):
    """Enter Atmospheric Weather mode — show preset menu."""
    self.weather_menu = True
    self.weather_menu_sel = 0
    self._flash("Atmospheric Weather — select a scenario")




def _exit_weather_mode(self):
    """Exit Atmospheric Weather mode."""
    self.weather_mode = False
    self.weather_menu = False
    self.weather_running = False
    self._flash("Atmospheric Weather mode OFF")




def _weather_init(self, preset_idx: int):
    """Initialize weather simulation from preset."""
    import random as _rand
    import math as _math

    name, desc, ptype = WEATHER_PRESETS[preset_idx]
    self.weather_preset_name = name
    self.weather_menu = False
    self.weather_mode = True
    self.weather_running = True
    self.weather_generation = 0
    self.weather_hour = 0
    self.weather_show_help = True
    self.weather_speed_scale = 1.0
    self.weather_layer = "default"

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max_y - 3
    cols = max_x - 1
    self.weather_rows = rows
    self.weather_cols = cols

    # Initialize grids
    self.weather_pressure = [[1013.25 for _ in range(cols)] for _ in range(rows)]
    self.weather_temperature = [[15.0 for _ in range(cols)] for _ in range(rows)]
    self.weather_humidity = [[0.5 for _ in range(cols)] for _ in range(rows)]
    self.weather_wind_u = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.weather_wind_v = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.weather_cloud = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.weather_precip = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.weather_precip_type = [[0 for _ in range(cols)] for _ in range(rows)]
    self.weather_centers = []
    self.weather_fronts = []

    # Latitude-based temperature gradient (warmer at center row, cooler at edges)
    mid_r = rows / 2.0
    for r in range(rows):
        lat_factor = 1.0 - abs(r - mid_r) / mid_r  # 0 at poles, 1 at equator
        base_temp = -20.0 + 50.0 * lat_factor  # -20°C poles to +30°C equator
        for c in range(cols):
            self.weather_temperature[r][c] = base_temp + _rand.uniform(-2, 2)
            self.weather_humidity[r][c] = 0.3 + 0.4 * lat_factor + _rand.uniform(-0.05, 0.05)

    if ptype == "cyclone":
        # Intense low-pressure center with high moisture
        cr, cc = rows // 2, cols // 2
        self.weather_centers.append({
            "r": cr, "c": cc, "pressure": 960.0, "radius": min(rows, cols) // 3,
            "type": "low", "vr": 0.1, "vc": 0.3, "intensity": 1.0,
        })
        # Set warm moist air around cyclone
        for r in range(rows):
            for c in range(cols):
                dr = r - cr
                dc = c - cc
                dist = _math.sqrt(dr * dr + dc * dc)
                if dist < min(rows, cols) // 3:
                    self.weather_temperature[r][c] = max(self.weather_temperature[r][c], 25.0)
                    self.weather_humidity[r][c] = min(1.0, 0.8 + 0.2 * (1 - dist / (min(rows, cols) // 3)))
        # High pressure to the east
        self.weather_centers.append({
            "r": rows // 3, "c": cols * 3 // 4, "pressure": 1035.0, "radius": min(rows, cols) // 4,
            "type": "high", "vr": -0.05, "vc": 0.2, "intensity": 0.6,
        })

    elif ptype == "fronts":
        # Cold air mass in the north, warm in south, front in the middle
        self.weather_centers.append({
            "r": rows // 4, "c": cols // 3, "pressure": 1025.0, "radius": min(rows, cols) // 3,
            "type": "high", "vr": 0.15, "vc": 0.2, "intensity": 0.7,
        })
        self.weather_centers.append({
            "r": rows * 3 // 4, "c": cols * 2 // 3, "pressure": 1000.0, "radius": min(rows, cols) // 3,
            "type": "low", "vr": 0.1, "vc": 0.25, "intensity": 0.8,
        })
        # Cold front line
        self.weather_fronts.append({
            "type": "cold", "points": [(rows // 2, c) for c in range(0, cols, 3)],
            "vc": 0.3, "vr": 0.1, "strength": 1.0,
        })
        # Warm front ahead
        self.weather_fronts.append({
            "type": "warm", "points": [(rows // 2 + 3, c) for c in range(cols // 3, cols * 2 // 3, 3)],
            "vc": 0.15, "vr": 0.05, "strength": 0.7,
        })
        # Enhanced temperature contrast
        for r in range(rows // 2):
            for c in range(cols):
                self.weather_temperature[r][c] -= 10.0

    elif ptype == "highpressure":
        # Large high pressure dome with clear skies
        self.weather_centers.append({
            "r": rows // 2, "c": cols // 2, "pressure": 1040.0, "radius": min(rows, cols) // 2,
            "type": "high", "vr": 0.0, "vc": 0.1, "intensity": 0.9,
        })
        # Small low to the west for contrast
        self.weather_centers.append({
            "r": rows // 2, "c": cols // 6, "pressure": 1005.0, "radius": min(rows, cols) // 5,
            "type": "low", "vr": 0.05, "vc": 0.15, "intensity": 0.5,
        })
        # Dry air mass
        for r in range(rows):
            for c in range(cols):
                self.weather_humidity[r][c] *= 0.6

    elif ptype == "monsoon":
        # Strong moisture gradient, warm ocean to the south
        for r in range(rows):
            for c in range(cols):
                lat_factor = r / float(rows)
                self.weather_humidity[r][c] = min(1.0, 0.3 + 0.7 * lat_factor)
                self.weather_temperature[r][c] = 15.0 + 20.0 * lat_factor
        # Deep thermal low over land (north)
        self.weather_centers.append({
            "r": rows // 4, "c": cols // 2, "pressure": 995.0, "radius": min(rows, cols) // 3,
            "type": "low", "vr": 0.0, "vc": 0.1, "intensity": 0.9,
        })
        # Oceanic high to the south
        self.weather_centers.append({
            "r": rows * 3 // 4, "c": cols // 2, "pressure": 1030.0, "radius": min(rows, cols) // 3,
            "type": "high", "vr": 0.0, "vc": 0.1, "intensity": 0.7,
        })

    elif ptype == "arctic":
        # Cold polar high pushing south
        self.weather_centers.append({
            "r": 2, "c": cols // 2, "pressure": 1045.0, "radius": min(rows, cols) // 3,
            "type": "high", "vr": 0.2, "vc": 0.05, "intensity": 0.9,
        })
        # Warm low to the south
        self.weather_centers.append({
            "r": rows * 3 // 4, "c": cols // 2, "pressure": 1000.0, "radius": min(rows, cols) // 3,
            "type": "low", "vr": -0.05, "vc": 0.1, "intensity": 0.6,
        })
        # Cold front
        self.weather_fronts.append({
            "type": "cold", "points": [(rows // 3, c) for c in range(0, cols, 3)],
            "vc": 0.1, "vr": 0.25, "strength": 1.2,
        })
        # Very cold north
        for r in range(rows // 2):
            for c in range(cols):
                self.weather_temperature[r][c] = -25.0 + 15.0 * (r / (rows / 2.0)) + _rand.uniform(-2, 2)
                self.weather_humidity[r][c] = 0.4 + _rand.uniform(-0.05, 0.05)

    else:  # random
        n_centers = _rand.randint(3, 6)
        for _ in range(n_centers):
            ctype = _rand.choice(["high", "low"])
            p = _rand.uniform(1030, 1050) if ctype == "high" else _rand.uniform(975, 1005)
            self.weather_centers.append({
                "r": _rand.randint(2, rows - 3), "c": _rand.randint(2, cols - 3),
                "pressure": p, "radius": _rand.randint(min(rows, cols) // 6, min(rows, cols) // 3),
                "type": ctype,
                "vr": _rand.uniform(-0.2, 0.2), "vc": _rand.uniform(0.05, 0.3),
                "intensity": _rand.uniform(0.4, 1.0),
            })
        if _rand.random() < 0.6:
            fr = _rand.randint(rows // 4, rows * 3 // 4)
            self.weather_fronts.append({
                "type": _rand.choice(["cold", "warm"]),
                "points": [(fr, c) for c in range(0, cols, 3)],
                "vc": _rand.uniform(0.1, 0.3), "vr": _rand.uniform(-0.1, 0.2),
                "strength": _rand.uniform(0.5, 1.2),
            })

    # Apply pressure centers to grid
    _weather_apply_pressure_centers(self)
    # Derive initial wind from pressure gradient
    _weather_compute_wind(self)
    # Initial cloud formation
    _weather_update_clouds(self)

    self._flash(f"Atmospheric Weather: {self.weather_preset_name}")




def _weather_apply_pressure_centers(self):
    """Apply pressure centers to the pressure grid using Gaussian falloff."""
    import math as _math
    rows, cols = self.weather_rows, self.weather_cols
    # Reset to base
    for r in range(rows):
        for c in range(cols):
            self.weather_pressure[r][c] = 1013.25
    # Apply each center
    for ctr in self.weather_centers:
        cr, cc = ctr["r"], ctr["c"]
        radius = max(1, ctr["radius"])
        dp = ctr["pressure"] - 1013.25
        intensity = ctr["intensity"]
        for r in range(rows):
            for c in range(cols):
                dr = r - cr
                dc = c - cc
                dist_sq = dr * dr + dc * dc
                influence = dp * intensity * _math.exp(-dist_sq / (2.0 * radius * radius))
                self.weather_pressure[r][c] += influence




def _weather_compute_wind(self):
    """Compute wind vectors from pressure gradient + Coriolis deflection."""
    rows, cols = self.weather_rows, self.weather_cols
    pressure = self.weather_pressure
    coriolis = self.weather_coriolis
    mid_r = rows / 2.0

    for r in range(rows):
        for c in range(cols):
            # Pressure gradient (finite differences)
            rn = (r - 1) % rows
            rs = (r + 1) % rows
            cw = (c - 1) % cols
            ce = (c + 1) % cols

            dp_dr = (pressure[rs][c] - pressure[rn][c]) / 2.0
            dp_dc = (pressure[r][ce] - pressure[r][cw]) / 2.0

            # Wind blows from high to low pressure (negative gradient)
            u = -dp_dc * 0.5  # east-west
            v = -dp_dr * 0.5  # north-south

            # Coriolis deflection (NH deflects right, SH deflects left)
            lat_sign = 1.0 if r < mid_r else -1.0
            cf = coriolis * lat_sign
            # Geostrophic-like rotation
            u_new = u + cf * v
            v_new = v - cf * u

            self.weather_wind_u[r][c] = max(-15.0, min(15.0, u_new))
            self.weather_wind_v[r][c] = max(-15.0, min(15.0, v_new))




def _weather_update_clouds(self):
    """Update cloud density from humidity, temperature, and vertical motion."""
    rows, cols = self.weather_rows, self.weather_cols
    for r in range(rows):
        for c in range(cols):
            humidity = self.weather_humidity[r][c]
            temp = self.weather_temperature[r][c]
            pressure = self.weather_pressure[r][c]

            # Rising air (low pressure) → cloud formation
            # Sinking air (high pressure) → cloud dissipation
            lift = (1013.25 - pressure) / 50.0  # positive = rising

            # Dew point approximation: clouds form when humidity is high and air is lifted
            cloud_tendency = humidity * 0.6 + lift * 0.3 - 0.3

            # Cold air holds less moisture → easier saturation
            if temp < 0:
                cloud_tendency += 0.15
            elif temp > 25:
                cloud_tendency -= 0.1

            # Wind convergence enhances clouds
            rn = (r - 1) % rows
            rs = (r + 1) % rows
            cw = (c - 1) % cols
            ce = (c + 1) % cols
            div = ((self.weather_wind_u[r][ce] - self.weather_wind_u[r][cw]) / 2.0 +
                   (self.weather_wind_v[rs][c] - self.weather_wind_v[rn][c]) / 2.0)
            # Negative divergence (convergence) = more clouds
            cloud_tendency -= div * 0.1

            # Blend toward target
            target = max(0.0, min(1.0, cloud_tendency))
            self.weather_cloud[r][c] = self.weather_cloud[r][c] * 0.8 + target * 0.2

            # Precipitation: needs thick clouds and high humidity
            cloud_val = self.weather_cloud[r][c]
            if cloud_val > 0.6 and humidity > 0.65:
                precip_rate = (cloud_val - 0.5) * humidity * 2.0
                self.weather_precip[r][c] = min(1.0, precip_rate)
                self.weather_precip_type[r][c] = 2 if temp < 2.0 else 1
            else:
                self.weather_precip[r][c] *= 0.5  # dissipate
                if self.weather_precip[r][c] < 0.05:
                    self.weather_precip[r][c] = 0.0
                    self.weather_precip_type[r][c] = 0




def _weather_step(self):
    """Advance weather simulation by one time step."""
    import random as _rand
    import math as _math

    self.weather_generation += 1
    self.weather_hour += 1
    rows, cols = self.weather_rows, self.weather_cols
    speed = self.weather_speed_scale

    # Move pressure centers
    for ctr in self.weather_centers:
        ctr["r"] += ctr["vr"] * speed
        ctr["c"] += ctr["vc"] * speed
        # Wrap around
        ctr["r"] = ctr["r"] % rows
        ctr["c"] = ctr["c"] % cols
        # Intensity fluctuation
        ctr["intensity"] += _rand.uniform(-0.02, 0.02) * speed
        ctr["intensity"] = max(0.2, min(1.2, ctr["intensity"]))
        # Slight pressure wandering
        if ctr["type"] == "low":
            ctr["pressure"] += _rand.uniform(-1.0, 0.8) * speed
            ctr["pressure"] = max(950, min(1010, ctr["pressure"]))
        else:
            ctr["pressure"] += _rand.uniform(-0.8, 1.0) * speed
            ctr["pressure"] = max(1015, min(1055, ctr["pressure"]))

    # Move fronts
    for front in self.weather_fronts:
        new_pts = []
        for pr, pc in front["points"]:
            nr = pr + front["vr"] * speed
            nc = pc + front["vc"] * speed
            new_pts.append((nr % rows, nc % cols))
        front["points"] = new_pts
        front["strength"] += _rand.uniform(-0.03, 0.02) * speed
        front["strength"] = max(0.1, min(1.5, front["strength"]))

    # Apply pressure field
    _weather_apply_pressure_centers(self)

    # Frontal effects: temperature contrast and enhanced precipitation along fronts
    for front in self.weather_fronts:
        for pr, pc in front["points"]:
            ir, ic = int(pr) % rows, int(pc) % cols
            strength = front["strength"]
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    fr = (ir + dr) % rows
                    fc = (ic + dc) % cols
                    dist = abs(dr) + abs(dc)
                    if dist > 3:
                        continue
                    factor = strength * (1.0 - dist / 4.0)
                    if front["type"] == "cold":
                        self.weather_temperature[fr][fc] -= 0.5 * factor * speed
                        self.weather_humidity[fr][fc] = min(1.0, self.weather_humidity[fr][fc] + 0.05 * factor * speed)
                        # Pressure drops along front
                        self.weather_pressure[fr][fc] -= 2.0 * factor * speed
                    else:
                        self.weather_temperature[fr][fc] += 0.3 * factor * speed
                        self.weather_humidity[fr][fc] = min(1.0, self.weather_humidity[fr][fc] + 0.08 * factor * speed)
                        self.weather_pressure[fr][fc] -= 1.5 * factor * speed

    # Compute wind from updated pressure
    _weather_compute_wind(self)

    # Advect temperature and humidity by wind
    new_temp = [row[:] for row in self.weather_temperature]
    new_humid = [row[:] for row in self.weather_humidity]
    for r in range(rows):
        for c in range(cols):
            u = self.weather_wind_u[r][c]
            v = self.weather_wind_v[r][c]
            # Semi-Lagrangian advection: trace back
            src_r = (r - v * 0.3 * speed) % rows
            src_c = (c - u * 0.3 * speed) % cols
            # Bilinear interpolation
            r0 = int(src_r) % rows
            c0 = int(src_c) % cols
            r1 = (r0 + 1) % rows
            c1 = (c0 + 1) % cols
            fr = src_r - int(src_r)
            fc = src_c - int(src_c)

            t00 = self.weather_temperature[r0][c0]
            t10 = self.weather_temperature[r1][c0]
            t01 = self.weather_temperature[r0][c1]
            t11 = self.weather_temperature[r1][c1]
            new_temp[r][c] = (t00 * (1 - fr) * (1 - fc) + t10 * fr * (1 - fc) +
                              t01 * (1 - fr) * fc + t11 * fr * fc)

            h00 = self.weather_humidity[r0][c0]
            h10 = self.weather_humidity[r1][c0]
            h01 = self.weather_humidity[r0][c1]
            h11 = self.weather_humidity[r1][c1]
            new_humid[r][c] = max(0.0, min(1.0,
                h00 * (1 - fr) * (1 - fc) + h10 * fr * (1 - fc) +
                h01 * (1 - fr) * fc + h11 * fr * fc))

    self.weather_temperature = new_temp
    self.weather_humidity = new_humid

    # Precipitation depletes humidity
    for r in range(rows):
        for c in range(cols):
            if self.weather_precip[r][c] > 0.1:
                self.weather_humidity[r][c] -= 0.02 * self.weather_precip[r][c] * speed
                self.weather_humidity[r][c] = max(0.1, self.weather_humidity[r][c])

    # Update clouds and precipitation
    _weather_update_clouds(self)

    # Occasional new center spawning
    if _rand.random() < 0.005 * speed and len(self.weather_centers) < 8:
        ctype = _rand.choice(["high", "low"])
        p = _rand.uniform(1025, 1045) if ctype == "high" else _rand.uniform(985, 1010)
        self.weather_centers.append({
            "r": _rand.randint(2, rows - 3), "c": _rand.randint(2, cols - 3),
            "pressure": p, "radius": _rand.randint(min(rows, cols) // 6, min(rows, cols) // 4),
            "type": ctype,
            "vr": _rand.uniform(-0.15, 0.15), "vc": _rand.uniform(0.05, 0.25),
            "intensity": _rand.uniform(0.3, 0.8),
        })

    # Remove weak/off-screen centers to keep things manageable
    self.weather_centers = [c for c in self.weather_centers if c["intensity"] > 0.15]

    # Dissipate old fronts
    self.weather_fronts = [f for f in self.weather_fronts if f["strength"] > 0.1]




def _weather_wind_arrow(self, u: float, v: float) -> str:
    """Convert wind (u, v) components to a directional arrow character."""
    speed = (u * u + v * v) ** 0.5
    if speed < 0.5:
        return '·'
    # Quantize to 8 directions
    import math
    angle = math.atan2(v, u)  # v=south, u=east
    # Map to 8 sectors
    sector = int((angle + math.pi) / (math.pi / 4) + 0.5) % 8
    arrows = ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙']
    return arrows[sector]




def _weather_temp_color(self, temp: float) -> int:
    """Return curses color pair for temperature."""
    import curses
    if temp < -15:
        return curses.color_pair(5) | curses.A_BOLD  # deep blue/magenta
    elif temp < 0:
        return curses.color_pair(5)       # blue
    elif temp < 10:
        return curses.color_pair(7)       # cyan
    elif temp < 20:
        return curses.color_pair(3)       # green
    elif temp < 30:
        return curses.color_pair(4)       # yellow
    else:
        return curses.color_pair(2) | curses.A_BOLD  # red/hot




def _weather_pressure_color(self, p: float) -> int:
    """Return curses color pair for pressure."""
    import curses
    if p < 990:
        return curses.color_pair(2) | curses.A_BOLD  # deep low = red
    elif p < 1005:
        return curses.color_pair(2)       # low
    elif p < 1015:
        return curses.color_pair(3)       # normal = green
    elif p < 1030:
        return curses.color_pair(7)       # high = cyan
    else:
        return curses.color_pair(5) | curses.A_BOLD  # strong high = blue




def _handle_weather_menu_key(self, key: int) -> bool:
    """Handle input in weather preset menu."""
    import curses
    n = len(WEATHER_PRESETS)
    if key == curses.KEY_DOWN or key == ord('j'):
        self.weather_menu_sel = (self.weather_menu_sel + 1) % n
    elif key == curses.KEY_UP or key == ord('k'):
        self.weather_menu_sel = (self.weather_menu_sel - 1) % n
    elif key in (10, 13, curses.KEY_ENTER):
        self._weather_init(self.weather_menu_sel)
    elif key == 27:
        self.weather_menu = False
        self.weather_mode = False
        self._flash("Atmospheric Weather cancelled")
    else:
        return True
    return True




def _handle_weather_key(self, key: int) -> bool:
    """Handle input in active weather simulation."""
    if key == -1:
        return True
    if key == ord(' '):
        self.weather_running = not self.weather_running
        self._flash("Paused" if not self.weather_running else "Running")
    elif key == ord('+') or key == ord('='):
        self.weather_speed_scale = min(5.0, self.weather_speed_scale + 0.25)
        self._flash(f"Speed: {self.weather_speed_scale:.1f}x")
    elif key == ord('-'):
        self.weather_speed_scale = max(0.25, self.weather_speed_scale - 0.25)
        self._flash(f"Speed: {self.weather_speed_scale:.1f}x")
    elif key == ord('l') or key == ord('v'):
        # Cycle through display layers
        layers = ["default", "pressure", "temp", "wind", "humidity"]
        idx = layers.index(self.weather_layer) if self.weather_layer in layers else 0
        self.weather_layer = layers[(idx + 1) % len(layers)]
        self._flash(f"Layer: {self.weather_layer}")
    elif key == ord('?'):
        self.weather_show_help = not self.weather_show_help
    elif key == ord('r'):
        idx = next((i for i, (n, _, _) in enumerate(WEATHER_PRESETS)
                     if n == self.weather_preset_name), 0)
        self._weather_init(idx)
    elif key == ord('m'):
        self.weather_running = False
        self.weather_menu = True
        self.weather_menu_sel = 0
    elif key == 27:
        self._exit_weather_mode()
    else:
        return True
    return True




def _draw_weather_menu(self, max_y: int, max_x: int):
    """Draw weather preset selection menu."""
    import curses
    title = "═══ Atmospheric Weather ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(7))
        self.stdscr.addstr(3, 2, "Select a weather scenario:",
                           curses.color_pair(3))
        for i, (name, desc, _) in enumerate(WEATHER_PRESETS):
            y = 5 + i * 2
            if y >= max_y - 2:
                break
            marker = "▸ " if i == self.weather_menu_sel else "  "
            attr = curses.A_BOLD | curses.color_pair(7) if i == self.weather_menu_sel else curses.color_pair(3)
            self.stdscr.addstr(y, 3, f"{marker}{name}", attr)
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], curses.A_DIM)
        foot_y = min(5 + len(WEATHER_PRESETS) * 2 + 1, max_y - 2)
        self.stdscr.addstr(foot_y, 3, "Enter=Select  Esc=Cancel",
                           curses.A_DIM | curses.color_pair(6))
    except curses.error:
        pass




def _draw_weather(self, max_y: int, max_x: int):
    """Render weather simulation as ASCII atmospheric map."""
    import curses
    import math as _math
    rows, cols = self.weather_rows, self.weather_cols
    draw_rows = min(rows, max_y - 3)
    draw_cols = min(cols, max_x - 1)

    layer = self.weather_layer

    # Build front cell set for rendering frontal symbols
    front_cells = {}
    for front in self.weather_fronts:
        sym = '▼' if front["type"] == "cold" else '▲'
        for pr, pc in front["points"]:
            ir, ic = int(pr) % rows, int(pc) % cols
            if ir < draw_rows and ic < draw_cols:
                front_cells[(ir, ic)] = (sym, front["type"])

    for r in range(draw_rows):
        for c in range(draw_cols):
            try:
                # Check for frontal boundary
                if (r, c) in front_cells:
                    sym, ftype = front_cells[(r, c)]
                    color = curses.color_pair(5) | curses.A_BOLD if ftype == "cold" else curses.color_pair(2) | curses.A_BOLD
                    self.stdscr.addch(r, c, ord(sym), color)
                    continue

                if layer == "pressure":
                    p = self.weather_pressure[r][c]
                    # Map pressure to character
                    idx = int((p - 950) / (1060 - 950) * 9)
                    idx = max(0, min(8, idx))
                    ch = "▁▂▃▄▅▆▇█▉"[idx]
                    attr = self._weather_pressure_color(p)
                    self.stdscr.addch(r, c, ord(ch), attr)

                elif layer == "temp":
                    temp = self.weather_temperature[r][c]
                    # Map temp to character gradient
                    idx = int((temp + 30) / 60 * 9)
                    idx = max(0, min(9, idx))
                    ch = "▁▂▃▄▅▆▇█▉●"[idx]
                    attr = self._weather_temp_color(temp)
                    self.stdscr.addch(r, c, ord(ch), attr)

                elif layer == "wind":
                    u = self.weather_wind_u[r][c]
                    v = self.weather_wind_v[r][c]
                    ch = self._weather_wind_arrow(u, v)
                    speed = (u * u + v * v) ** 0.5
                    if speed > 8:
                        attr = curses.color_pair(2) | curses.A_BOLD  # strong wind = red
                    elif speed > 4:
                        attr = curses.color_pair(4) | curses.A_BOLD  # moderate = yellow
                    elif speed > 1:
                        attr = curses.color_pair(3)                  # light = green
                    else:
                        attr = curses.A_DIM
                    self.stdscr.addch(r, c, ord(ch), attr)

                elif layer == "humidity":
                    h = self.weather_humidity[r][c]
                    idx = int(h * 8)
                    idx = max(0, min(7, idx))
                    ch = CLOUD_CHARS[idx]
                    if h > 0.8:
                        attr = curses.color_pair(5) | curses.A_BOLD
                    elif h > 0.5:
                        attr = curses.color_pair(7)
                    else:
                        attr = curses.A_DIM
                    self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

                else:  # default composite view
                    precip = self.weather_precip[r][c]
                    cloud = self.weather_cloud[r][c]

                    if precip > 0.3:
                        # Show precipitation
                        ptype = self.weather_precip_type[r][c]
                        if ptype == 2:
                            ch = '*'
                            attr = curses.color_pair(1) | curses.A_BOLD  # snow = white
                        else:
                            ch = '│' if precip > 0.6 else ':'
                            attr = curses.color_pair(5)  # rain = blue
                        self.stdscr.addch(r, c, ord(ch), attr)

                    elif cloud > 0.15:
                        # Show clouds
                        idx = int(cloud * 7)
                        idx = max(0, min(7, idx))
                        ch = CLOUD_CHARS[idx + 1] if idx < 7 else CLOUD_CHARS[7]
                        attr = curses.color_pair(1) if cloud > 0.5 else curses.A_DIM
                        self.stdscr.addch(r, c, ord(ch), attr)

                    else:
                        # Show wind with temperature coloring
                        u = self.weather_wind_u[r][c]
                        v = self.weather_wind_v[r][c]
                        speed = (u * u + v * v) ** 0.5
                        if speed > 2.0:
                            ch = self._weather_wind_arrow(u, v)
                            attr = self._weather_temp_color(self.weather_temperature[r][c])
                        else:
                            ch = '·'
                            attr = curses.A_DIM
                        self.stdscr.addch(r, c, ord(ch), attr)

            except curses.error:
                pass

    # Pressure center markers
    for ctr in self.weather_centers:
        cr = int(ctr["r"]) % rows
        cc = int(ctr["c"]) % cols
        if cr < draw_rows and cc < draw_cols:
            try:
                label = 'L' if ctr["type"] == "low" else 'H'
                color = curses.color_pair(2) | curses.A_BOLD if ctr["type"] == "low" else curses.color_pair(5) | curses.A_BOLD
                self.stdscr.addch(cr, cc, ord(label), color)
            except curses.error:
                pass

    # Status bar
    status_y = min(draw_rows, max_y - 2)
    try:
        flat_p = [self.weather_pressure[r][c] for r in range(rows) for c in range(cols)]
        min_p = min(flat_p)
        max_p = max(flat_p)
        flat_t = [self.weather_temperature[r][c] for r in range(rows) for c in range(cols)]
        avg_t = sum(flat_t) / len(flat_t)
        precip_cells = sum(1 for r in range(rows) for c in range(cols) if self.weather_precip[r][c] > 0.2)
        precip_pct = precip_cells / (rows * cols) * 100

        day = self.weather_hour // 24
        hour = self.weather_hour % 24
        status = (f" Day {day} {hour:02d}:00 │ "
                  f"P: {min_p:.0f}-{max_p:.0f} hPa │ "
                  f"Avg T: {avg_t:.1f}°C │ "
                  f"Precip: {precip_pct:.0f}% │ "
                  f"Centers: {len(self.weather_centers)} │ "
                  f"Layer: {self.weather_layer} │ "
                  f"Speed: {self.weather_speed_scale:.1f}x ")
        self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                           curses.color_pair(0) | curses.A_REVERSE)
    except curses.error:
        pass

    # Legend bar
    try:
        legend = " ·calm →wind ░▒▓cloud │rain *snow ▼cold▲warm L=low H=high "
        self.stdscr.addstr(status_y + 1, 0, legend[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    # Help overlay
    if self.weather_show_help:
        help_lines = [
            "Controls:",
            " Space  Pause/Resume",
            " +/-    Speed up/down",
            " l/v    Cycle layers",
            "        (default/pressure/",
            "         temp/wind/humidity)",
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


# Bind weather methods to App class
# ══════════════════════════════════════════════════════════════════════════════
# Ocean Currents & Thermohaline Circulation
# ══════════════════════════════════════════════════════════════════════════════

OCEAN_PRESETS = [
    ("Gulf Stream", "Warm western boundary current with eddies and meanders", "gulfstream"),
    ("Pacific Gyre", "Large-scale subtropical gyre with Kuroshio Current", "pacificgyre"),
    ("Antarctic Circumpolar", "Strongest current on Earth circling Antarctica", "antarctic"),
    ("El Niño", "Weakened trade winds with warm water spreading east", "elnino"),
    ("Thermohaline Conveyor", "Global deep water formation driving the great ocean conveyor", "thermohaline"),
    ("Random Ocean", "Randomly generated ocean basin with currents and blooms", "random"),
]

# ASCII characters for ocean visualization
OCEAN_CHARS = ' ·~≈≋∿⌇█'         # calm to turbulent
CURRENT_ARROWS = '·←↙↓↘→↗↑↖'      # indexed by 8-direction + calm
PLANKTON_CHARS = ' .,:;+*#@'       # sparse to dense bloom





def register(App):
    """Register weather mode methods on the App class."""
    App._enter_weather_mode = _enter_weather_mode
    App._exit_weather_mode = _exit_weather_mode
    App._weather_init = _weather_init
    App._weather_apply_pressure_centers = _weather_apply_pressure_centers
    App._weather_compute_wind = _weather_compute_wind
    App._weather_update_clouds = _weather_update_clouds
    App._weather_step = _weather_step
    App._weather_wind_arrow = _weather_wind_arrow
    App._weather_temp_color = _weather_temp_color
    App._weather_pressure_color = _weather_pressure_color
    App._handle_weather_menu_key = _handle_weather_menu_key
    App._handle_weather_key = _handle_weather_key
    App._draw_weather_menu = _draw_weather_menu
    App._draw_weather = _draw_weather

