"""Mode: ocean — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_ocean_mode(self):
    """Enter Ocean Currents mode — show preset menu."""
    self.ocean_menu = True
    self.ocean_menu_sel = 0
    self._flash("Ocean Currents — select a scenario")




def _exit_ocean_mode(self):
    """Exit Ocean Currents mode."""
    self.ocean_mode = False
    self.ocean_menu = False
    self.ocean_running = False
    self._flash("Ocean Currents mode OFF")




def _ocean_init(self, preset_idx: int):
    """Initialize ocean simulation from preset."""
    import random as _rand
    import math as _math

    name, desc, ptype = OCEAN_PRESETS[preset_idx]
    self.ocean_preset_name = name
    self.ocean_menu = False
    self.ocean_mode = True
    self.ocean_running = True
    self.ocean_generation = 0
    self.ocean_day = 0
    self.ocean_show_help = True
    self.ocean_speed_scale = 1.0
    self.ocean_layer = "default"

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max_y - 3
    cols = max_x - 1
    self.ocean_rows = rows
    self.ocean_cols = cols

    # Initialize grids
    self.ocean_temperature = [[15.0 for _ in range(cols)] for _ in range(rows)]
    self.ocean_salinity = [[35.0 for _ in range(cols)] for _ in range(rows)]
    self.ocean_density = [[1025.0 for _ in range(cols)] for _ in range(rows)]
    self.ocean_current_u = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.ocean_current_v = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.ocean_depth = [[0.5 for _ in range(cols)] for _ in range(rows)]
    self.ocean_upwelling = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.ocean_plankton = [[0.0 for _ in range(cols)] for _ in range(rows)]
    self.ocean_nutrient = [[0.2 for _ in range(cols)] for _ in range(rows)]
    self.ocean_gyres = []
    self.ocean_deep_formation = []

    mid_r = rows / 2.0

    # Latitude-based temperature gradient (warm equator, cold poles)
    for r in range(rows):
        lat_factor = 1.0 - abs(r - mid_r) / mid_r  # 0 at poles, 1 at equator
        base_temp = -2.0 + 30.0 * lat_factor
        base_salinity = 33.0 + 4.0 * lat_factor  # higher salinity in subtropics
        for c in range(cols):
            self.ocean_temperature[r][c] = base_temp + _rand.uniform(-1, 1)
            self.ocean_salinity[r][c] = base_salinity + _rand.uniform(-0.3, 0.3)
            self.ocean_nutrient[r][c] = 0.1 + 0.5 * (1.0 - lat_factor) + _rand.uniform(-0.05, 0.05)

    if ptype == "gulfstream":
        # Western boundary current: strong northward flow on west side
        gyre_r, gyre_c = rows // 2, cols // 3
        self.ocean_gyres.append({
            "r": gyre_r, "c": gyre_c, "radius": min(rows, cols) // 2,
            "strength": 2.5, "direction": 1,  # 1 = clockwise (NH subtropical)
            "vr": 0.0, "vc": 0.02,
        })
        # Warm current along western boundary
        for r in range(rows):
            for c in range(min(cols // 6, cols)):
                strength = 1.0 - c / (cols / 6.0)
                self.ocean_current_v[r][c] = -2.0 * strength  # northward (negative v)
                self.ocean_temperature[r][c] += 8.0 * strength
                self.ocean_salinity[r][c] += 1.0 * strength
        # Eddies along the stream
        for _ in range(3):
            er = _rand.randint(rows // 4, rows * 3 // 4)
            ec = _rand.randint(cols // 8, cols // 4)
            self.ocean_gyres.append({
                "r": er, "c": ec, "radius": _rand.randint(3, 8),
                "strength": _rand.uniform(0.5, 1.5),
                "direction": _rand.choice([-1, 1]),
                "vr": _rand.uniform(-0.1, 0.1), "vc": _rand.uniform(0.02, 0.1),
            })

    elif ptype == "pacificgyre":
        # Large subtropical gyre
        self.ocean_gyres.append({
            "r": rows // 2, "c": cols // 2, "radius": min(rows, cols) * 2 // 3,
            "strength": 1.8, "direction": 1,
            "vr": 0.0, "vc": 0.0,
        })
        # Kuroshio-like western intensification
        for r in range(rows // 4, rows * 3 // 4):
            for c in range(min(cols // 8, cols)):
                self.ocean_current_v[r][c] = -1.5
                self.ocean_temperature[r][c] += 5.0
        # Equatorial counter-current
        eq_r = int(rows * 0.55)
        for c in range(cols):
            for dr in range(-2, 3):
                rr = (eq_r + dr) % rows
                self.ocean_current_u[rr][c] = -0.8  # westward
                self.ocean_temperature[rr][c] += 3.0

    elif ptype == "antarctic":
        # Circumpolar current: strong eastward flow in southern rows
        belt_start = int(rows * 0.7)
        belt_end = int(rows * 0.9)
        for r in range(belt_start, min(belt_end, rows)):
            belt_factor = 1.0 - abs(r - (belt_start + belt_end) / 2.0) / ((belt_end - belt_start) / 2.0)
            for c in range(cols):
                self.ocean_current_u[r][c] = 3.0 * belt_factor
                self.ocean_temperature[r][c] = -1.0 + 2.0 * _rand.random()
                self.ocean_salinity[r][c] = 34.0 + _rand.uniform(-0.5, 0.5)
                self.ocean_nutrient[r][c] = 0.7 + _rand.uniform(-0.1, 0.1)
        # Deep water formation zone near Antarctic coast
        self.ocean_deep_formation.append({
            "r": rows - 3, "c": cols // 3, "radius": cols // 4,
            "strength": 1.5, "salinity_boost": 1.5,
        })
        self.ocean_deep_formation.append({
            "r": rows - 3, "c": cols * 2 // 3, "radius": cols // 4,
            "strength": 1.2, "salinity_boost": 1.2,
        })

    elif ptype == "elnino":
        # Weakened trade winds, warm pool spreads east
        # Normal state: warm west, cold east (equatorial Pacific)
        eq_band = range(max(0, int(rows * 0.4)), min(rows, int(rows * 0.6)))
        for r in eq_band:
            for c in range(cols):
                # El Niño: warm water shifts east
                warm_factor = c / float(cols)  # warmer toward east
                self.ocean_temperature[r][c] = 22.0 + 8.0 * warm_factor + _rand.uniform(-0.5, 0.5)
                self.ocean_salinity[r][c] = 34.5 + _rand.uniform(-0.3, 0.3)
                # Weakened easterly trade winds
                self.ocean_current_u[r][c] = 0.3  # weak eastward instead of strong westward
        # Reduced upwelling on eastern coast
        for r in eq_band:
            for c in range(cols * 3 // 4, cols):
                self.ocean_upwelling[r][c] = -0.1  # downwelling
                self.ocean_nutrient[r][c] = 0.05  # nutrient-poor
        # Kelvin wave propagation marker
        self.ocean_gyres.append({
            "r": rows // 2, "c": cols // 3, "radius": rows // 4,
            "strength": 0.8, "direction": 0,  # 0 = propagating wave, not gyre
            "vr": 0.0, "vc": 0.15,
        })

    elif ptype == "thermohaline":
        # Global thermohaline conveyor belt
        # Warm surface current flowing north
        for r in range(rows // 2):
            for c in range(cols // 3, cols * 2 // 3):
                factor = 1.0 - abs(c - cols // 2) / (cols / 6.0)
                factor = max(0, factor)
                self.ocean_current_v[r][c] = -1.0 * factor  # northward
                self.ocean_temperature[r][c] += 5.0 * factor
        # Deep water formation in the north (like North Atlantic)
        self.ocean_deep_formation.append({
            "r": 2, "c": cols // 2, "radius": cols // 5,
            "strength": 2.0, "salinity_boost": 2.0,
        })
        # Deep cold return flow (south, deeper)
        for r in range(rows // 2, rows):
            for c in range(cols // 4, cols * 3 // 4):
                factor = 0.5
                self.ocean_current_v[r][c] = 0.5 * factor  # southward deep return
                self.ocean_temperature[r][c] -= 3.0
                self.ocean_salinity[r][c] += 0.8
        # Upwelling in southern ocean
        self.ocean_deep_formation.append({
            "r": rows - 4, "c": cols // 2, "radius": cols // 3,
            "strength": -1.5, "salinity_boost": -0.5,  # negative = upwelling zone
        })
        # Antarctic bottom water
        for c in range(cols):
            for dr in range(min(4, rows)):
                r = rows - 1 - dr
                self.ocean_temperature[r][c] = -1.5 + _rand.uniform(-0.3, 0.3)
                self.ocean_salinity[r][c] = 34.7 + _rand.uniform(-0.1, 0.1)

    else:  # random
        n_gyres = _rand.randint(2, 5)
        for _ in range(n_gyres):
            self.ocean_gyres.append({
                "r": _rand.randint(3, rows - 4), "c": _rand.randint(3, cols - 4),
                "radius": _rand.randint(min(rows, cols) // 6, min(rows, cols) // 3),
                "strength": _rand.uniform(0.5, 2.5),
                "direction": _rand.choice([-1, 1]),
                "vr": _rand.uniform(-0.05, 0.05), "vc": _rand.uniform(-0.05, 0.05),
            })
        if _rand.random() < 0.7:
            self.ocean_deep_formation.append({
                "r": _rand.randint(2, rows // 4),
                "c": _rand.randint(cols // 4, cols * 3 // 4),
                "radius": _rand.randint(cols // 8, cols // 4),
                "strength": _rand.uniform(1.0, 2.0),
                "salinity_boost": _rand.uniform(0.5, 2.0),
            })

    # Apply gyres to current field
    _ocean_apply_gyres(self)
    # Compute density from T and S
    _ocean_compute_density(self)
    # Compute upwelling from current divergence
    _ocean_compute_upwelling(self)
    # Seed initial plankton in nutrient-rich areas
    for r in range(rows):
        for c in range(cols):
            if self.ocean_nutrient[r][c] > 0.4 and self.ocean_upwelling[r][c] > 0.05:
                self.ocean_plankton[r][c] = _rand.uniform(0.1, 0.4)

    self._flash(f"Ocean Currents: {self.ocean_preset_name}")




def _ocean_apply_gyres(self):
    """Apply gyre circulation patterns to current field."""
    import math as _math
    rows, cols = self.ocean_rows, self.ocean_cols

    for gyre in self.ocean_gyres:
        gr, gc = gyre["r"], gyre["c"]
        radius = max(1, gyre["radius"])
        strength = gyre["strength"]
        direction = gyre.get("direction", 1)
        if direction == 0:
            continue  # wave, not a gyre
        for r in range(rows):
            for c in range(cols):
                dr = r - gr
                dc = c - gc
                dist = _math.sqrt(dr * dr + dc * dc)
                if dist < 1:
                    continue
                if dist > radius * 1.5:
                    continue
                # Tangential flow: perpendicular to radius vector
                falloff = _math.exp(-dist * dist / (2.0 * radius * radius))
                # Scale by distance from center (strongest at ~radius/2)
                radial_scale = dist / radius * _math.exp(0.5 - dist / radius)
                mag = strength * radial_scale * falloff * direction
                # Tangent: rotate radius vector 90 degrees
                nx = -dr / dist
                ny = dc / dist
                self.ocean_current_u[r][c] += mag * ny
                self.ocean_current_v[r][c] += mag * nx




def _ocean_compute_density(self):
    """Compute seawater density from temperature and salinity (simplified UNESCO)."""
    rows, cols = self.ocean_rows, self.ocean_cols
    for r in range(rows):
        for c in range(cols):
            t = self.ocean_temperature[r][c]
            s = self.ocean_salinity[r][c]
            # Simplified equation of state
            self.ocean_density[r][c] = (1000.0
                + 0.8 * s
                - 0.003 * (t - 4.0) * (t - 4.0)
                + 0.01 * s * (35.0 - s))




def _ocean_compute_upwelling(self):
    """Compute vertical velocity from horizontal current divergence."""
    rows, cols = self.ocean_rows, self.ocean_cols
    for r in range(rows):
        for c in range(cols):
            ce = (c + 1) % cols
            cw = (c - 1) % cols
            rn = (r - 1) % rows
            rs = (r + 1) % rows
            div_u = (self.ocean_current_u[r][ce] - self.ocean_current_u[r][cw]) / 2.0
            div_v = (self.ocean_current_v[rs][c] - self.ocean_current_v[rn][c]) / 2.0
            divergence = div_u + div_v
            # Positive divergence → upwelling (water rises to replace)
            self.ocean_upwelling[r][c] = self.ocean_upwelling[r][c] * 0.7 + divergence * 0.3




def _ocean_step(self):
    """Advance ocean simulation by one time step."""
    import random as _rand
    import math as _math

    self.ocean_generation += 1
    self.ocean_day += 1
    rows, cols = self.ocean_rows, self.ocean_cols
    speed = self.ocean_speed_scale

    # Move gyres slowly
    for gyre in self.ocean_gyres:
        gyre["r"] += gyre.get("vr", 0) * speed
        gyre["c"] += gyre.get("vc", 0) * speed
        gyre["r"] = gyre["r"] % rows
        gyre["c"] = gyre["c"] % cols
        # Strength fluctuation
        gyre["strength"] += _rand.uniform(-0.03, 0.03) * speed
        gyre["strength"] = max(0.2, min(3.5, gyre["strength"]))

    # Rebuild current field from gyres
    # Fade existing currents slightly
    for r in range(rows):
        for c in range(cols):
            self.ocean_current_u[r][c] *= 0.92
            self.ocean_current_v[r][c] *= 0.92
    _ocean_apply_gyres(self)

    # Coriolis effect on currents
    mid_r = rows / 2.0
    coriolis = 0.1
    for r in range(rows):
        lat_sign = 1.0 if r < mid_r else -1.0
        cf = coriolis * lat_sign
        for c in range(cols):
            u = self.ocean_current_u[r][c]
            v = self.ocean_current_v[r][c]
            self.ocean_current_u[r][c] = u + cf * v * 0.1 * speed
            self.ocean_current_v[r][c] = v - cf * u * 0.1 * speed
            # Clamp
            self.ocean_current_u[r][c] = max(-5.0, min(5.0, self.ocean_current_u[r][c]))
            self.ocean_current_v[r][c] = max(-5.0, min(5.0, self.ocean_current_v[r][c]))

    # Deep water formation: cold salty water sinks, drives circulation
    for dwf in self.ocean_deep_formation:
        dr_center = int(dwf["r"]) % rows
        dc_center = int(dwf["c"]) % cols
        radius = max(1, dwf["radius"])
        strength = dwf["strength"]
        s_boost = dwf["salinity_boost"]
        for r in range(max(0, dr_center - radius), min(rows, dr_center + radius + 1)):
            for c in range(max(0, dc_center - radius), min(cols, dc_center + radius + 1)):
                dr = r - dr_center
                dc = c - dc_center
                dist = _math.sqrt(dr * dr + dc * dc)
                if dist > radius:
                    continue
                falloff = 1.0 - dist / radius
                if strength > 0:
                    # Sinking zone: cool, increase salinity, downwelling
                    self.ocean_temperature[r][c] -= 0.1 * falloff * speed * strength
                    self.ocean_salinity[r][c] += 0.02 * falloff * speed * s_boost
                    self.ocean_upwelling[r][c] -= 0.05 * falloff * speed * strength
                    # Drive outward flow at depth (simplified as surface divergence)
                    if dist > 1:
                        self.ocean_current_u[r][c] += 0.1 * (dc / dist) * falloff * speed * strength
                        self.ocean_current_v[r][c] += 0.1 * (dr / dist) * falloff * speed * strength
                else:
                    # Upwelling zone: bring cold nutrient-rich water up
                    abs_str = abs(strength)
                    self.ocean_temperature[r][c] -= 0.05 * falloff * speed * abs_str
                    self.ocean_nutrient[r][c] += 0.03 * falloff * speed * abs_str
                    self.ocean_nutrient[r][c] = min(1.0, self.ocean_nutrient[r][c])
                    self.ocean_upwelling[r][c] += 0.08 * falloff * speed * abs_str

    # Advect temperature and salinity by currents
    new_temp = [row[:] for row in self.ocean_temperature]
    new_sal = [row[:] for row in self.ocean_salinity]
    new_nutrient = [row[:] for row in self.ocean_nutrient]
    new_plankton = [row[:] for row in self.ocean_plankton]

    for r in range(rows):
        for c in range(cols):
            u = self.ocean_current_u[r][c]
            v = self.ocean_current_v[r][c]
            # Semi-Lagrangian advection
            src_r = (r - v * 0.25 * speed) % rows
            src_c = (c - u * 0.25 * speed) % cols
            r0 = int(src_r) % rows
            c0 = int(src_c) % cols
            r1 = (r0 + 1) % rows
            c1 = (c0 + 1) % cols
            fr = src_r - int(src_r)
            fc = src_c - int(src_c)

            # Bilinear interpolation for temperature
            new_temp[r][c] = (self.ocean_temperature[r0][c0] * (1 - fr) * (1 - fc) +
                              self.ocean_temperature[r1][c0] * fr * (1 - fc) +
                              self.ocean_temperature[r0][c1] * (1 - fr) * fc +
                              self.ocean_temperature[r1][c1] * fr * fc)

            # Salinity
            new_sal[r][c] = (self.ocean_salinity[r0][c0] * (1 - fr) * (1 - fc) +
                             self.ocean_salinity[r1][c0] * fr * (1 - fc) +
                             self.ocean_salinity[r0][c1] * (1 - fr) * fc +
                             self.ocean_salinity[r1][c1] * fr * fc)

            # Nutrients
            new_nutrient[r][c] = (self.ocean_nutrient[r0][c0] * (1 - fr) * (1 - fc) +
                                  self.ocean_nutrient[r1][c0] * fr * (1 - fc) +
                                  self.ocean_nutrient[r0][c1] * (1 - fr) * fc +
                                  self.ocean_nutrient[r1][c1] * fr * fc)

            # Plankton (advected + growth/decay)
            new_plankton[r][c] = (self.ocean_plankton[r0][c0] * (1 - fr) * (1 - fc) +
                                  self.ocean_plankton[r1][c0] * fr * (1 - fc) +
                                  self.ocean_plankton[r0][c1] * (1 - fr) * fc +
                                  self.ocean_plankton[r1][c1] * fr * fc)

    self.ocean_temperature = new_temp
    self.ocean_salinity = new_sal
    self.ocean_nutrient = new_nutrient
    self.ocean_plankton = new_plankton

    # Thermal relaxation toward latitude-based equilibrium
    mid_r = rows / 2.0
    for r in range(rows):
        lat_factor = 1.0 - abs(r - mid_r) / mid_r
        eq_temp = -2.0 + 30.0 * lat_factor
        for c in range(cols):
            self.ocean_temperature[r][c] += (eq_temp - self.ocean_temperature[r][c]) * 0.005 * speed
            # Salinity: evaporation in warm subtropics, freshening at poles
            eq_sal = 33.0 + 4.0 * lat_factor
            self.ocean_salinity[r][c] += (eq_sal - self.ocean_salinity[r][c]) * 0.003 * speed
            self.ocean_salinity[r][c] = max(30.0, min(40.0, self.ocean_salinity[r][c]))

    # Compute upwelling from divergence
    _ocean_compute_upwelling(self)

    # Upwelling brings nutrients
    for r in range(rows):
        for c in range(cols):
            if self.ocean_upwelling[r][c] > 0.02:
                self.ocean_nutrient[r][c] += 0.02 * self.ocean_upwelling[r][c] * speed
                self.ocean_nutrient[r][c] = min(1.0, self.ocean_nutrient[r][c])

    # Plankton dynamics: growth where nutrients + light, decay otherwise
    for r in range(rows):
        lat_factor = 1.0 - abs(r - mid_r) / mid_r
        light = 0.3 + 0.7 * lat_factor  # more light near equator
        for c in range(cols):
            nutrient = self.ocean_nutrient[r][c]
            plankton = self.ocean_plankton[r][c]
            temp = self.ocean_temperature[r][c]

            # Growth: nutrients * light * temperature factor
            temp_factor = max(0, min(1, (temp + 2) / 30.0))
            growth = 0.04 * nutrient * light * temp_factor * speed
            # Logistic cap
            growth *= (1.0 - plankton)
            # Decay
            decay = 0.015 * plankton * speed
            # Grazing pressure (density-dependent)
            grazing = 0.02 * plankton * plankton * speed

            self.ocean_plankton[r][c] = max(0.0, min(1.0, plankton + growth - decay - grazing))
            # Plankton consumes nutrients
            self.ocean_nutrient[r][c] = max(0.0, self.ocean_nutrient[r][c] - growth * 0.5)
            # Dead plankton recycles some nutrients
            self.ocean_nutrient[r][c] = min(1.0, self.ocean_nutrient[r][c] + decay * 0.3)

    # Update density
    _ocean_compute_density(self)

    # Density-driven pressure gradient currents (thermohaline component)
    for r in range(1, rows - 1):
        for c in range(cols):
            cw = (c - 1) % cols
            ce = (c + 1) % cols
            d_dr = (self.ocean_density[r + 1][c] - self.ocean_density[r - 1][c]) / 2.0
            d_dc = (self.ocean_density[r][ce] - self.ocean_density[r][cw]) / 2.0
            # Flow from high density to low density (baroclinic)
            self.ocean_current_u[r][c] -= d_dc * 0.0005 * speed
            self.ocean_current_v[r][c] -= d_dr * 0.0005 * speed

    # Occasional eddy spawning
    if _rand.random() < 0.008 * speed and len(self.ocean_gyres) < 10:
        self.ocean_gyres.append({
            "r": _rand.randint(3, rows - 4), "c": _rand.randint(3, cols - 4),
            "radius": _rand.randint(3, min(rows, cols) // 6),
            "strength": _rand.uniform(0.3, 1.2),
            "direction": _rand.choice([-1, 1]),
            "vr": _rand.uniform(-0.08, 0.08), "vc": _rand.uniform(-0.05, 0.1),
        })

    # Remove weak gyres
    self.ocean_gyres = [g for g in self.ocean_gyres if g["strength"] > 0.15]




def _ocean_current_arrow(self, u: float, v: float) -> str:
    """Convert current (u, v) to directional arrow."""
    speed = (u * u + v * v) ** 0.5
    if speed < 0.3:
        return '·'
    import math
    angle = math.atan2(v, u)
    sector = int((angle + math.pi) / (math.pi / 4) + 0.5) % 8
    arrows = ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙']
    return arrows[sector]




def _ocean_temp_color(self, temp: float) -> int:
    """Return curses color pair for sea surface temperature."""
    import curses
    if temp < 0:
        return curses.color_pair(1) | curses.A_BOLD   # freezing = white bold
    elif temp < 5:
        return curses.color_pair(5) | curses.A_BOLD    # very cold = magenta
    elif temp < 10:
        return curses.color_pair(5)                     # cold = blue
    elif temp < 18:
        return curses.color_pair(7)                     # cool = cyan
    elif temp < 24:
        return curses.color_pair(3)                     # warm = green
    elif temp < 28:
        return curses.color_pair(4)                     # hot = yellow
    else:
        return curses.color_pair(2) | curses.A_BOLD     # tropical = red




def _ocean_density_color(self, d: float) -> int:
    """Return curses color pair for density."""
    import curses
    if d < 1024:
        return curses.color_pair(2) | curses.A_BOLD  # light = red
    elif d < 1025:
        return curses.color_pair(4)                   # yellow
    elif d < 1026:
        return curses.color_pair(3)                   # green
    elif d < 1027:
        return curses.color_pair(7)                   # cyan
    else:
        return curses.color_pair(5) | curses.A_BOLD   # dense = blue




def _handle_ocean_menu_key(self, key: int) -> bool:
    """Handle input in ocean preset menu."""
    import curses
    n = len(OCEAN_PRESETS)
    if key == curses.KEY_DOWN or key == ord('j'):
        self.ocean_menu_sel = (self.ocean_menu_sel + 1) % n
    elif key == curses.KEY_UP or key == ord('k'):
        self.ocean_menu_sel = (self.ocean_menu_sel - 1) % n
    elif key in (10, 13, curses.KEY_ENTER):
        self._ocean_init(self.ocean_menu_sel)
    elif key == 27:
        self.ocean_menu = False
        self.ocean_mode = False
        self._flash("Ocean Currents cancelled")
    else:
        return True
    return True




def _handle_ocean_key(self, key: int) -> bool:
    """Handle input in active ocean simulation."""
    if key == -1:
        return True
    if key == ord(' '):
        self.ocean_running = not self.ocean_running
        self._flash("Paused" if not self.ocean_running else "Running")
    elif key == ord('+') or key == ord('='):
        self.ocean_speed_scale = min(5.0, self.ocean_speed_scale + 0.25)
        self._flash(f"Speed: {self.ocean_speed_scale:.1f}x")
    elif key == ord('-'):
        self.ocean_speed_scale = max(0.25, self.ocean_speed_scale - 0.25)
        self._flash(f"Speed: {self.ocean_speed_scale:.1f}x")
    elif key == ord('l') or key == ord('v'):
        layers = ["default", "temp", "salinity", "density", "currents", "plankton"]
        idx = layers.index(self.ocean_layer) if self.ocean_layer in layers else 0
        self.ocean_layer = layers[(idx + 1) % len(layers)]
        self._flash(f"Layer: {self.ocean_layer}")
    elif key == ord('?'):
        self.ocean_show_help = not self.ocean_show_help
    elif key == ord('r'):
        idx = next((i for i, (n, _, _) in enumerate(OCEAN_PRESETS)
                     if n == self.ocean_preset_name), 0)
        self._ocean_init(idx)
    elif key == ord('m'):
        self.ocean_running = False
        self.ocean_menu = True
        self.ocean_menu_sel = 0
    elif key == 27:
        self._exit_ocean_mode()
    else:
        return True
    return True




def _draw_ocean_menu(self, max_y: int, max_x: int):
    """Draw ocean preset selection menu."""
    import curses
    title = "═══ Ocean Currents & Thermohaline Circulation ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(7))
        self.stdscr.addstr(3, 2, "Select an ocean scenario:",
                           curses.color_pair(3))
        for i, (name, desc, _) in enumerate(OCEAN_PRESETS):
            y = 5 + i * 2
            if y >= max_y - 2:
                break
            marker = "▸ " if i == self.ocean_menu_sel else "  "
            attr = curses.A_BOLD | curses.color_pair(7) if i == self.ocean_menu_sel else curses.color_pair(3)
            self.stdscr.addstr(y, 3, f"{marker}{name}", attr)
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], curses.A_DIM)
        foot_y = min(5 + len(OCEAN_PRESETS) * 2 + 1, max_y - 2)
        self.stdscr.addstr(foot_y, 3, "Enter=Select  Esc=Cancel",
                           curses.A_DIM | curses.color_pair(6))
    except curses.error:
        pass




def _draw_ocean(self, max_y: int, max_x: int):
    """Render ocean simulation as ASCII oceanographic map."""
    import curses
    import math as _math
    rows, cols = self.ocean_rows, self.ocean_cols
    draw_rows = min(rows, max_y - 3)
    draw_cols = min(cols, max_x - 1)

    layer = self.ocean_layer

    for r in range(draw_rows):
        for c in range(draw_cols):
            try:
                if layer == "temp":
                    temp = self.ocean_temperature[r][c]
                    idx = int((temp + 5) / 35 * 8)
                    idx = max(0, min(7, idx))
                    ch = OCEAN_CHARS[idx]
                    attr = self._ocean_temp_color(temp)
                    self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

                elif layer == "salinity":
                    s = self.ocean_salinity[r][c]
                    idx = int((s - 30) / 10 * 8)
                    idx = max(0, min(7, idx))
                    ch = OCEAN_CHARS[idx]
                    if s > 37:
                        attr = curses.color_pair(2) | curses.A_BOLD
                    elif s > 35:
                        attr = curses.color_pair(4)
                    elif s > 33:
                        attr = curses.color_pair(7)
                    else:
                        attr = curses.color_pair(5)
                    self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

                elif layer == "density":
                    d = self.ocean_density[r][c]
                    idx = int((d - 1022) / 8 * 8)
                    idx = max(0, min(7, idx))
                    ch = OCEAN_CHARS[idx]
                    attr = self._ocean_density_color(d)
                    self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

                elif layer == "currents":
                    u = self.ocean_current_u[r][c]
                    v = self.ocean_current_v[r][c]
                    ch = self._ocean_current_arrow(u, v)
                    speed = (u * u + v * v) ** 0.5
                    if speed > 2.0:
                        attr = curses.color_pair(2) | curses.A_BOLD
                    elif speed > 1.0:
                        attr = curses.color_pair(4) | curses.A_BOLD
                    elif speed > 0.3:
                        attr = curses.color_pair(7)
                    else:
                        attr = curses.A_DIM
                    self.stdscr.addch(r, c, ord(ch), attr)

                elif layer == "plankton":
                    p = self.ocean_plankton[r][c]
                    idx = int(p * 8)
                    idx = max(0, min(7, idx))
                    ch = PLANKTON_CHARS[idx]
                    if p > 0.6:
                        attr = curses.color_pair(3) | curses.A_BOLD  # dense bloom = bright green
                    elif p > 0.3:
                        attr = curses.color_pair(3)                  # moderate = green
                    elif p > 0.1:
                        attr = curses.color_pair(7)                  # sparse = cyan
                    else:
                        attr = curses.A_DIM
                    self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

                else:  # default composite view
                    plankton = self.ocean_plankton[r][c]
                    upwell = self.ocean_upwelling[r][c]
                    temp = self.ocean_temperature[r][c]
                    u = self.ocean_current_u[r][c]
                    v = self.ocean_current_v[r][c]
                    speed = (u * u + v * v) ** 0.5

                    if plankton > 0.25:
                        # Show plankton bloom
                        idx = int(plankton * 8)
                        idx = max(1, min(7, idx))
                        ch = PLANKTON_CHARS[idx]
                        if plankton > 0.5:
                            attr = curses.color_pair(3) | curses.A_BOLD
                        else:
                            attr = curses.color_pair(3)
                        self.stdscr.addch(r, c, ord(ch), attr)

                    elif upwell > 0.15:
                        # Show upwelling zones
                        ch = '⤊' if upwell > 0.3 else '↑'
                        attr = curses.color_pair(7) | curses.A_BOLD
                        self.stdscr.addch(r, c, ord(ch), attr)

                    elif speed > 0.5:
                        # Show currents with temperature coloring
                        ch = self._ocean_current_arrow(u, v)
                        attr = self._ocean_temp_color(temp)
                        self.stdscr.addch(r, c, ord(ch), attr)

                    else:
                        # Calm water, show temperature
                        idx = int((temp + 5) / 35 * 7)
                        idx = max(0, min(6, idx))
                        calm_chars = ' ·~≈≋∿⌇'
                        ch = calm_chars[idx]
                        attr = self._ocean_temp_color(temp) | curses.A_DIM
                        self.stdscr.addch(r, c, ord(ch) if ch != ' ' else ord(' '), attr)

            except curses.error:
                pass

    # Mark gyre centers
    for gyre in self.ocean_gyres:
        gr = int(gyre["r"]) % rows
        gc = int(gyre["c"]) % cols
        if gr < draw_rows and gc < draw_cols:
            try:
                d = gyre.get("direction", 1)
                label = '◎' if d != 0 else '◆'
                attr = curses.color_pair(4) | curses.A_BOLD
                self.stdscr.addch(gr, gc, ord(label), attr)
            except curses.error:
                pass

    # Mark deep water formation zones
    for dwf in self.ocean_deep_formation:
        dr = int(dwf["r"]) % rows
        dc = int(dwf["c"]) % cols
        if dr < draw_rows and dc < draw_cols:
            try:
                label = '▽' if dwf["strength"] > 0 else '△'
                attr = curses.color_pair(5) | curses.A_BOLD
                self.stdscr.addch(dr, dc, ord(label), attr)
            except curses.error:
                pass

    # Status bar
    status_y = min(draw_rows, max_y - 2)
    try:
        flat_t = [self.ocean_temperature[r][c] for r in range(rows) for c in range(cols)]
        avg_t = sum(flat_t) / len(flat_t)
        flat_s = [self.ocean_salinity[r][c] for r in range(rows) for c in range(cols)]
        avg_s = sum(flat_s) / len(flat_s)
        plankton_cells = sum(1 for r in range(rows) for c in range(cols) if self.ocean_plankton[r][c] > 0.15)
        bloom_pct = plankton_cells / (rows * cols) * 100
        upwell_cells = sum(1 for r in range(rows) for c in range(cols) if self.ocean_upwelling[r][c] > 0.1)

        status = (f" Day {self.ocean_day} │ "
                  f"SST: {avg_t:.1f}°C │ "
                  f"Sal: {avg_s:.1f} PSU │ "
                  f"Bloom: {bloom_pct:.0f}% │ "
                  f"Upwelling: {upwell_cells} │ "
                  f"Gyres: {len(self.ocean_gyres)} │ "
                  f"Layer: {self.ocean_layer} │ "
                  f"Speed: {self.ocean_speed_scale:.1f}x ")
        self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                           curses.color_pair(0) | curses.A_REVERSE)
    except curses.error:
        pass

    # Legend bar
    try:
        legend = " ·calm →current ↑upwell .:;bloom ◎gyre ▽sink △rise "
        self.stdscr.addstr(status_y + 1, 0, legend[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    # Help overlay
    if self.ocean_show_help:
        help_lines = [
            "Controls:",
            " Space  Pause/Resume",
            " +/-    Speed up/down",
            " l/v    Cycle layers",
            "        (default/temp/salinity",
            "         /density/currents/",
            "         plankton)",
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


# Bind ocean methods to App class
# ══════════════════════════════════════════════════════════════════════════════
# Volcanic Eruption & Lava Flow Simulation
# ══════════════════════════════════════════════════════════════════════════════

VOLCANO_PRESETS = [
    ("Strombolian", "Mild, rhythmic eruptions with lava fountains and slow flows", "strombolian"),
    ("Plinian", "Catastrophic explosive eruption with massive ash column", "plinian"),
    ("Hawaiian", "Effusive shield volcano with fluid lava rivers", "hawaiian"),
    ("Vulcanian", "Viscous magma with violent bursts and pyroclastic surges", "vulcanian"),
    ("Caldera Collapse", "Mega-eruption draining a magma chamber into caldera", "caldera"),
    ("Fissure Eruption", "Curtain of fire along a rift with lava flooding a plain", "fissure"),
]

# ASCII characters for volcanic visualization
LAVA_CHARS = ' .·:;+*#@█'         # cool to incandescent
TERRAIN_CHARS = ' ░▒▓█'            # flat to peak
ASH_CHARS = ' .,:;░▒▓█'            # thin to thick ash
ROCK_CHARS = ' .:;oO0@#'           # thin deposit to thick cooled rock





def register(App):
    """Register ocean mode methods on the App class."""
    App._enter_ocean_mode = _enter_ocean_mode
    App._exit_ocean_mode = _exit_ocean_mode
    App._ocean_init = _ocean_init
    App._ocean_apply_gyres = _ocean_apply_gyres
    App._ocean_compute_density = _ocean_compute_density
    App._ocean_compute_upwelling = _ocean_compute_upwelling
    App._ocean_step = _ocean_step
    App._ocean_current_arrow = _ocean_current_arrow
    App._ocean_temp_color = _ocean_temp_color
    App._ocean_density_color = _ocean_density_color
    App._handle_ocean_menu_key = _handle_ocean_menu_key
    App._handle_ocean_key = _handle_ocean_key
    App._draw_ocean_menu = _draw_ocean_menu
    App._draw_ocean = _draw_ocean

