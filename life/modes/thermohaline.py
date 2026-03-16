"""Mode: thermohaline — Ocean Thermohaline Circulation & Global Current System.

Simulates a 2D global ocean with:
- Thermohaline circulation driven by temperature and salinity density gradients
  (cold salty water sinking at poles, warm surface return flow)
- Wind-driven surface currents with Ekman transport and western boundary
  intensification (Gulf Stream / Kuroshio analog) and subtropical gyres
- Deep water formation zones: NADW (North Atlantic) and AABW (Antarctic)
- Coastal & equatorial upwelling bringing nutrients to surface
- ENSO oscillation: El Nino / La Nina Pacific thermocline seesaw
- Freshwater hosing / AMOC shutdown from ice sheet meltwater

Three views:
  1) Global current map with temperature/salinity overlay + current arrows
  2) Ocean cross-section depth profile showing conveyor belt circulation
  3) Time-series sparkline graphs — 10 metrics

Six presets:
  Stable Modern Circulation, Gulf Stream Intensification, ENSO El Nino Event,
  Glacial Meltwater Hosing / AMOC Shutdown, Anoxic Ocean Stratification,
  Snowball Earth Frozen Ocean
"""
import curses
import math
import random

# ======================================================================
#  Presets
# ======================================================================

THERMOHALINE_PRESETS = [
    ("Stable Modern Circulation",
     "Balanced thermohaline conveyor — NADW sinking, Antarctic upwelling, steady gyres",
     "modern"),
    ("Gulf Stream Intensification",
     "Enhanced western boundary current — strong NADW formation driving rapid poleward heat transport",
     "gulfstream"),
    ("ENSO El Nino Event",
     "Weakened Walker circulation — warm pool spreading east, thermocline flattening, upwelling collapse",
     "elnino"),
    ("Glacial Meltwater Hosing / AMOC Shutdown",
     "Freshwater pulse shutting down NADW — conveyor collapse, rapid northern cooling",
     "hosing"),
    ("Anoxic Ocean Stratification",
     "Strong density stratification blocking vertical mixing — stagnant deep water, surface nutrient depletion",
     "anoxic"),
    ("Snowball Earth Frozen Ocean",
     "Near-global ice cover — suppressed circulation, geothermal-only deep heating, sub-ice brine currents",
     "snowball"),
]

# ======================================================================
#  Physical constants
# ======================================================================

_DT = 0.2                   # integration timestep
_TEMP_DIFF = 0.04            # thermal diffusion coefficient
_SAL_DIFF = 0.02             # salinity diffusion (slower than heat)
_WIND_STRESS = 0.06          # wind stress coupling to surface currents
_CORIOLIS_SCALE = 0.12       # Coriolis parameter scaling
_EKMAN_DEPTH = 3             # depth layers affected by Ekman transport
_DENSITY_TEMP_COEFF = -0.15  # temperature effect on density (warmer = lighter)
_DENSITY_SAL_COEFF = 0.20    # salinity effect on density (saltier = heavier)
_GRAVITY_ACCEL = 0.10        # gravitational acceleration (scaled)
_WESTERN_BOUNDARY = 0.08     # western boundary intensification factor
_UPWELLING_RATE = 0.03       # base upwelling velocity
_DEEP_WATER_SINK = 0.05      # sinking rate for dense water formation
_SURFACE_HEAT_FLUX = 0.03    # atmosphere-ocean heat exchange rate
_EVAP_RATE = 0.002           # evaporation salinity increase rate
_PRECIP_RATE = 0.001         # precipitation freshening rate
_ICE_FORM_TEMP = 0.12        # temperature below which ice forms
_ICE_MELT_TEMP = 0.18        # temperature above which ice melts
_ICE_BRINE_REJECT = 0.008    # salinity increase when ice forms (brine rejection)
_ENSO_PERIOD = 120           # ENSO oscillation period in ticks
_ENSO_AMPLITUDE = 0.15       # ENSO thermocline displacement amplitude
_NUTRIENT_UPWELL = 0.04      # nutrient supply from upwelling
_NUTRIENT_DECAY = 0.005      # surface nutrient consumption rate
_GEOTHERMAL_FLUX = 0.001     # deep ocean geothermal heating
_MAX_DEPTH_LAYERS = 8        # vertical depth layers for cross-section

_NEIGHBORS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


# ======================================================================
#  Helper functions
# ======================================================================

def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _wrap_col(c, cols):
    """Cylindrical wrapping in longitude."""
    return c % cols


def _lat_fraction(r, rows):
    """0 = north pole, 0.5 = equator, 1.0 = south pole."""
    return r / max(1, rows - 1)


def _coriolis(lat_frac):
    """Coriolis parameter f = scale * sin(lat)."""
    lat_rad = math.pi * (lat_frac - 0.5)
    return _CORIOLIS_SCALE * math.sin(lat_rad)


def _density(temp, sal):
    """Seawater density from temperature and salinity (higher = denser)."""
    return 1.0 + _DENSITY_TEMP_COEFF * temp + _DENSITY_SAL_COEFF * sal


def _insolation(lat_frac):
    """Solar heating of surface ocean as function of latitude."""
    return max(0.0, math.cos(math.pi * (lat_frac - 0.5)))


# ======================================================================
#  Enter / Exit
# ======================================================================

def _enter_thermohaline_mode(self):
    """Enter thermohaline circulation mode — show preset menu."""
    self.thermohaline_mode = True
    self.thermohaline_menu = True
    self.thermohaline_menu_sel = 0


def _exit_thermohaline_mode(self):
    """Exit thermohaline circulation mode."""
    self.thermohaline_mode = False
    self.thermohaline_menu = False
    self.thermohaline_running = False
    for attr in list(vars(self)):
        if attr.startswith('thermohaline_') and attr not in ('thermohaline_mode',):
            try:
                delattr(self, attr)
            except AttributeError:
                pass


# ======================================================================
#  Initialization
# ======================================================================

def _thermohaline_init(self, preset_idx: int):
    """Initialize ocean thermohaline simulation for chosen preset."""
    name, _desc, pid = THERMOHALINE_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(40, max_x - 2)
    depth = _MAX_DEPTH_LAYERS

    self.thermohaline_menu = False
    self.thermohaline_running = False
    self.thermohaline_preset_name = name
    self.thermohaline_preset_id = pid
    self.thermohaline_rows = rows
    self.thermohaline_cols = cols
    self.thermohaline_depth = depth
    self.thermohaline_generation = 0
    self.thermohaline_view = "currents"  # currents | crosssection | graphs

    # --- Land mask: 0=ocean, 1=land ---
    land = [[0] * cols for _ in range(rows)]
    _generate_land(land, rows, cols, pid)
    self.thermohaline_land = land

    # --- Surface temperature [0, 1] ---
    self.thermohaline_temp = [[0.0] * cols for _ in range(rows)]

    # --- Surface salinity [0, 1] (0.5 = normal, >0.5 = salty, <0.5 = fresh) ---
    self.thermohaline_salinity = [[0.5] * cols for _ in range(rows)]

    # --- Surface current velocity (u = east-west, v = north-south) ---
    self.thermohaline_u = [[0.0] * cols for _ in range(rows)]
    self.thermohaline_v = [[0.0] * cols for _ in range(rows)]

    # --- Deep temperature and salinity (by depth layer) ---
    self.thermohaline_deep_temp = [[[0.0] * cols for _ in range(rows)] for _ in range(depth)]
    self.thermohaline_deep_sal = [[[0.5] * cols for _ in range(rows)] for _ in range(depth)]

    # --- Vertical velocity field (positive = upwelling) ---
    self.thermohaline_w = [[0.0] * cols for _ in range(rows)]

    # --- Ice coverage [0, 1] ---
    self.thermohaline_ice = [[0.0] * cols for _ in range(rows)]

    # --- Surface nutrient concentration [0, 1] ---
    self.thermohaline_nutrients = [[0.0] * cols for _ in range(rows)]

    # --- Density field (derived) ---
    self.thermohaline_density = [[1.0] * cols for _ in range(rows)]

    # --- ENSO state ---
    self.thermohaline_enso_phase = 0.0       # oscillator phase
    self.thermohaline_enso_amplitude = 0.0   # current amplitude

    # --- AMOC strength (0 = collapsed, 1 = vigorous) ---
    self.thermohaline_amoc_strength = 1.0

    # --- Freshwater hosing rate ---
    self.thermohaline_hosing_rate = 0.0

    # --- Cross-section latitude for depth view ---
    self.thermohaline_xsec_row = rows // 3  # roughly North Atlantic latitude

    # --- Metrics history ---
    self.thermohaline_history = {
        'amoc_strength': [],
        'mean_sst': [],
        'mean_salinity': [],
        'enso_index': [],
        'ice_area': [],
        'upwelling': [],
        'deep_temp': [],
        'nutrient_level': [],
        'max_current': [],
        'density_contrast': [],
    }

    # Apply preset
    _apply_preset(self, pid, rows, cols, depth)
    self._flash(f"Ocean Thermohaline: {name}")


def _generate_land(land, rows, cols, pid):
    """Generate continent shapes for ocean basins."""
    if pid == "snowball":
        # Minimal land — small equatorial continent
        cr, cc = rows // 2, cols // 2
        size = max(3, min(rows, cols) // 8)
        for r in range(max(0, cr - size), min(rows, cr + size)):
            for c in range(cc - size, cc + size):
                wc = _wrap_col(c, cols)
                dist = math.sqrt((r - cr) ** 2 + (c - cc) ** 2)
                if dist < size * 0.6:
                    land[r][wc] = 1
        return

    # Earth-like ocean basins with continents
    n_continents = random.randint(3, 5)
    for _ in range(n_continents):
        cr = random.randint(rows // 6, rows * 5 // 6)
        cc = random.randint(0, cols - 1)
        size = random.randint(3, max(4, min(rows, cols) // 6))
        for r in range(max(0, cr - size), min(rows, cr + size)):
            for c in range(cc - size, cc + size):
                wc = _wrap_col(c, cols)
                dist = math.sqrt((r - cr) ** 2 + (c - cc) ** 2)
                if dist < size * (0.4 + 0.4 * random.random()):
                    land[r][wc] = 1

    # Polar land masses (small)
    for _ in range(2):
        cc = random.randint(0, cols - 1)
        size = random.randint(2, max(3, cols // 10))
        pole_r = random.choice([0, rows - 1])
        for r in range(max(0, pole_r - size), min(rows, pole_r + size + 1)):
            for c in range(cc - size, cc + size):
                wc = _wrap_col(c, cols)
                if random.random() < 0.4:
                    land[r][wc] = 1


def _apply_preset(self, pid, rows, cols, depth):
    """Configure preset-specific initial conditions."""
    temp = self.thermohaline_temp
    sal = self.thermohaline_salinity
    ice = self.thermohaline_ice
    land = self.thermohaline_land
    deep_temp = self.thermohaline_deep_temp
    deep_sal = self.thermohaline_deep_sal
    nutrients = self.thermohaline_nutrients

    # Base: latitude-dependent SST and salinity
    for r in range(rows):
        lat = _lat_fraction(r, rows)
        insol = _insolation(lat)
        for c in range(cols):
            if land[r][c]:
                continue
            base_t = insol * 0.6 + 0.1 + random.uniform(-0.02, 0.02)
            temp[r][c] = _clamp(base_t)

            # Salinity: higher in subtropics (evaporation), lower at equator/poles (precipitation/melt)
            eq_dist = abs(lat - 0.5)
            if eq_dist < 0.15:
                sal[r][c] = 0.45 + random.uniform(-0.01, 0.01)  # equatorial freshening
            elif eq_dist < 0.35:
                sal[r][c] = 0.58 + random.uniform(-0.01, 0.01)  # subtropical salty
            else:
                sal[r][c] = 0.48 + random.uniform(-0.01, 0.01)  # polar fresh-ish

            # Deep ocean: cold, slightly salty
            for d in range(depth):
                frac = (d + 1) / depth
                deep_temp[d][r][c] = temp[r][c] * (1.0 - frac * 0.8) + 0.05
                deep_sal[d][r][c] = sal[r][c] + frac * 0.05

    if pid == "modern":
        self.thermohaline_amoc_strength = 1.0
        self.thermohaline_enso_amplitude = 0.05  # weak background ENSO

    elif pid == "gulfstream":
        self.thermohaline_amoc_strength = 1.4  # enhanced
        # Warm up western boundary current zone (left side of basin, upper latitudes)
        for r in range(rows // 6, rows // 3):
            for c in range(cols // 8):
                wc = _wrap_col(c, cols)
                if not land[r][wc]:
                    temp[r][wc] = min(1.0, temp[r][wc] + 0.2)
                    sal[r][wc] = min(1.0, sal[r][wc] + 0.05)

    elif pid == "elnino":
        self.thermohaline_enso_phase = 0.0
        self.thermohaline_enso_amplitude = _ENSO_AMPLITUDE * 2.0  # strong El Nino
        # Warm the eastern equatorial Pacific
        eq_band = range(max(0, rows // 2 - rows // 8), min(rows, rows // 2 + rows // 8))
        for r in eq_band:
            for c in range(cols * 2 // 3, cols):
                wc = _wrap_col(c, cols)
                if not land[r][wc]:
                    temp[r][wc] = min(1.0, temp[r][wc] + 0.15)
                    nutrients[r][wc] = 0.05  # upwelling suppressed

    elif pid == "hosing":
        self.thermohaline_amoc_strength = 0.8  # starts weakened
        self.thermohaline_hosing_rate = 0.015   # continuous freshwater input
        # Freshen North Atlantic
        for r in range(rows // 8):
            for c in range(cols):
                if not land[r][c]:
                    sal[r][c] = max(0.0, sal[r][c] - 0.12)
                    temp[r][c] = max(0.0, temp[r][c] - 0.05)

    elif pid == "anoxic":
        self.thermohaline_amoc_strength = 0.3  # very weak circulation
        # Strong stratification: warm salty surface, cold fresh deep
        for r in range(rows):
            for c in range(cols):
                if not land[r][c]:
                    temp[r][c] = min(1.0, temp[r][c] + 0.1)
                    sal[r][c] = min(1.0, sal[r][c] + 0.08)
                    for d in range(depth):
                        deep_temp[d][r][c] = 0.08
                        deep_sal[d][r][c] = 0.42

    elif pid == "snowball":
        self.thermohaline_amoc_strength = 0.15
        for r in range(rows):
            for c in range(cols):
                if not land[r][c]:
                    temp[r][c] = 0.08 + random.uniform(-0.02, 0.02)
                    ice[r][c] = 0.7 + random.uniform(0, 0.3)
                    sal[r][c] = 0.55  # brine rejection from ice
                    for d in range(depth):
                        deep_temp[d][r][c] = 0.06 + _GEOTHERMAL_FLUX * (d + 1) * 5
                        deep_sal[d][r][c] = 0.55

    # Initialize nutrient field from upwelling zones
    for r in range(rows):
        lat = _lat_fraction(r, rows)
        for c in range(cols):
            if land[r][c]:
                continue
            # Equatorial and polar upwelling zones have more nutrients
            eq_dist = abs(lat - 0.5)
            pole_dist = min(lat, 1.0 - lat)
            if eq_dist < 0.08 or pole_dist < 0.15:
                nutrients[r][c] = max(nutrients[r][c], 0.4 + random.uniform(0, 0.2))
            else:
                nutrients[r][c] = max(nutrients[r][c], 0.1 + random.uniform(0, 0.1))


# ======================================================================
#  Simulation Step
# ======================================================================

def _thermohaline_step(self):
    """Advance ocean simulation by one tick."""
    rows = self.thermohaline_rows
    cols = self.thermohaline_cols
    depth = self.thermohaline_depth
    temp = self.thermohaline_temp
    sal = self.thermohaline_salinity
    u = self.thermohaline_u
    v = self.thermohaline_v
    w = self.thermohaline_w
    ice = self.thermohaline_ice
    land = self.thermohaline_land
    nutrients = self.thermohaline_nutrients
    deep_temp = self.thermohaline_deep_temp
    deep_sal = self.thermohaline_deep_sal
    pid = self.thermohaline_preset_id
    amoc = self.thermohaline_amoc_strength

    self.thermohaline_generation += 1
    gen = self.thermohaline_generation

    # --- ENSO oscillation ---
    self.thermohaline_enso_phase += 2.0 * math.pi / _ENSO_PERIOD
    if self.thermohaline_enso_phase > 2.0 * math.pi:
        self.thermohaline_enso_phase -= 2.0 * math.pi
    enso_idx = self.thermohaline_enso_amplitude * math.sin(self.thermohaline_enso_phase)

    # --- Freshwater hosing ---
    hosing = self.thermohaline_hosing_rate

    # New fields
    new_temp = [[0.0] * cols for _ in range(rows)]
    new_sal = [[0.5] * cols for _ in range(rows)]
    new_u = [[0.0] * cols for _ in range(rows)]
    new_v = [[0.0] * cols for _ in range(rows)]
    new_w = [[0.0] * cols for _ in range(rows)]
    new_ice = [[0.0] * cols for _ in range(rows)]
    new_nut = [[0.0] * cols for _ in range(rows)]

    max_current = 0.0
    total_upwelling = 0.0
    total_nut = 0.0
    n_ocean = 0

    for r in range(rows):
        lat = _lat_fraction(r, rows)
        f = _coriolis(lat)
        insol = _insolation(lat)
        pole_dist = min(lat, 1.0 - lat)
        eq_dist = abs(lat - 0.5)

        for c in range(cols):
            if land[r][c]:
                new_temp[r][c] = 0.0
                new_sal[r][c] = 0.0
                continue

            n_ocean += 1

            # --- Surface heat flux ---
            # Solar heating + atmospheric exchange
            heat_in = insol * _SURFACE_HEAT_FLUX * (1.0 - ice[r][c] * 0.8)
            heat_out = 0.01 * temp[r][c] ** 2
            # Ice insulation reduces heat loss
            if ice[r][c] > 0.3:
                heat_out *= (1.0 - ice[r][c] * 0.6)

            # --- Temperature diffusion ---
            t_lap = 0.0
            n_adj = 0
            for dr, dc in _NEIGHBORS_4:
                rr = r + dr
                cc = _wrap_col(c + dc, cols)
                if 0 <= rr < rows and not land[rr][cc]:
                    t_lap += temp[rr][cc] - temp[r][c]
                    n_adj += 1

            # --- Temperature advection ---
            t_adv = 0.0
            src_r = r - int(round(v[r][c] * 2))
            src_c = c - int(round(u[r][c] * 2))
            src_r = max(0, min(rows - 1, src_r))
            src_c = _wrap_col(src_c, cols)
            if not land[src_r][src_c]:
                t_adv = (temp[src_r][src_c] - temp[r][c]) * 0.12

            new_t = temp[r][c] + _DT * (heat_in - heat_out + _TEMP_DIFF * t_lap + t_adv)

            # ENSO: warm eastern equatorial Pacific during El Nino
            if eq_dist < 0.1 and c > cols * 2 // 3:
                new_t += enso_idx * 0.02

            # Deep water exchange: upwelling brings cold water, downwelling sends warm water down
            if w[r][c] > 0:
                # Upwelling: mix surface with cold deep water
                new_t -= w[r][c] * 0.3 * (new_t - deep_temp[0][r][c])
            else:
                # Downwelling
                new_t += w[r][c] * 0.1  # slight cooling from sinking

            new_temp[r][c] = _clamp(new_t, 0.0, 1.2)

            # --- Salinity ---
            s_lap = 0.0
            for dr, dc in _NEIGHBORS_4:
                rr = r + dr
                cc = _wrap_col(c + dc, cols)
                if 0 <= rr < rows and not land[rr][cc]:
                    s_lap += sal[rr][cc] - sal[r][c]

            # Evaporation increases salinity (subtropical), precipitation decreases it (equatorial/polar)
            evap_sal = 0.0
            if eq_dist > 0.12 and eq_dist < 0.35:
                evap_sal = _EVAP_RATE * (1.0 - ice[r][c])  # subtropical evaporation
            elif eq_dist < 0.12 or pole_dist < 0.15:
                evap_sal = -_PRECIP_RATE  # precipitation freshening

            # Hosing: freshwater input at high northern latitudes
            hosing_effect = 0.0
            if hosing > 0 and lat < 0.2:
                hosing_effect = -hosing * (1.0 - lat / 0.2)

            # Salinity advection
            s_adv = 0.0
            if not land[src_r][src_c]:
                s_adv = (sal[src_r][src_c] - sal[r][c]) * 0.10

            new_s = sal[r][c] + _DT * (_SAL_DIFF * s_lap + evap_sal + hosing_effect + s_adv)

            # Ice brine rejection
            if new_temp[r][c] < _ICE_FORM_TEMP and ice[r][c] < 1.0:
                new_s += _ICE_BRINE_REJECT * (1.0 - ice[r][c])

            new_sal[r][c] = _clamp(new_s, 0.0, 1.0)

            # --- Density ---
            dens = _density(new_temp[r][c], new_sal[r][c])
            self.thermohaline_density[r][c] = dens

            # --- Vertical velocity (upwelling/downwelling) ---
            # Dense water sinks, creating downwelling
            # Equatorial divergence and coastal effects drive upwelling
            vert_w = 0.0

            # Thermohaline-driven: dense polar water sinks
            if pole_dist < 0.2 and dens > 1.02:
                vert_w = -_DEEP_WATER_SINK * (dens - 1.0) * amoc  # downwelling (negative)
            # Equatorial upwelling from trade wind divergence
            if eq_dist < 0.08:
                vert_w = _UPWELLING_RATE * amoc
            # ENSO modulates equatorial upwelling
            if eq_dist < 0.08 and c > cols * 2 // 3:
                vert_w -= enso_idx * _UPWELLING_RATE  # El Nino suppresses upwelling

            # Coastal upwelling near western continent edges
            for dc in [-1, 1]:
                cc = _wrap_col(c + dc, cols)
                if 0 <= cc < cols and land[r][cc] and eq_dist < 0.3:
                    vert_w += _UPWELLING_RATE * 0.5

            new_w[r][c] = _clamp(vert_w, -0.2, 0.2)
            if vert_w > 0:
                total_upwelling += vert_w

            # --- Wind-driven surface currents ---
            # Trade winds: easterlies in tropics, westerlies in mid-latitudes
            wind_u = 0.0
            if eq_dist < 0.2:
                wind_u = -0.15  # easterly trades
            elif eq_dist < 0.4:
                wind_u = 0.2   # mid-latitude westerlies
            else:
                wind_u = -0.08  # polar easterlies

            # Pressure gradient force from density gradients
            dp_dx = 0.0
            dp_dy = 0.0
            cl = _wrap_col(c - 1, cols)
            cr_ = _wrap_col(c + 1, cols)
            if not land[r][cl] and not land[r][cr_]:
                dp_dx = (self.thermohaline_density[r][cr_] - self.thermohaline_density[r][cl]) * 0.5
            if r > 0 and r < rows - 1 and not land[r - 1][c] and not land[r + 1][c]:
                dp_dy = (self.thermohaline_density[r + 1][c] - self.thermohaline_density[r - 1][c]) * 0.5

            pgf_u = -dp_dx * _GRAVITY_ACCEL
            pgf_v = -dp_dy * _GRAVITY_ACCEL

            # Coriolis
            cor_u = f * v[r][c]
            cor_v = -f * u[r][c]

            # Western boundary intensification
            wb_boost = 0.0
            # Check if near western coast of a basin (land to the west)
            for dc in range(1, 4):
                wc = _wrap_col(c - dc, cols)
                if land[r][wc]:
                    wb_boost = _WESTERN_BOUNDARY * (1.0 - dc / 4.0) * abs(f)
                    break

            new_u[r][c] = u[r][c] + _DT * (
                _WIND_STRESS * wind_u + pgf_u + cor_u - 0.03 * u[r][c] + wb_boost * (1 if lat < 0.5 else -1)
            )
            new_v[r][c] = v[r][c] + _DT * (
                pgf_v + cor_v - 0.03 * v[r][c]
            )

            # Ekman transport: 90 degrees right (NH) / left (SH) of wind
            if eq_dist > 0.05:  # skip near equator where Coriolis vanishes
                ekman_v = _WIND_STRESS * wind_u * 0.3 * (1 if lat < 0.5 else -1)
                new_v[r][c] += _DT * ekman_v

            # Gyre circulation: subtropical convergence
            if 0.2 < eq_dist < 0.35:
                gyre_v = -0.02 * (1 if lat < 0.5 else -1)  # converge toward gyre center
                new_v[r][c] += _DT * gyre_v

            new_u[r][c] = _clamp(new_u[r][c], -0.8, 0.8)
            new_v[r][c] = _clamp(new_v[r][c], -0.5, 0.5)

            cs = math.sqrt(new_u[r][c] ** 2 + new_v[r][c] ** 2)
            if cs > max_current:
                max_current = cs

            # --- Ice dynamics ---
            ice_val = ice[r][c]
            if new_temp[r][c] < _ICE_FORM_TEMP:
                ice_val = min(1.0, ice_val + 0.004)
            elif new_temp[r][c] > _ICE_MELT_TEMP:
                ice_val = max(0.0, ice_val - 0.003)
            # Strong currents break up ice
            if cs > 0.3:
                ice_val = max(0.0, ice_val - 0.001 * cs)
            new_ice[r][c] = ice_val

            # --- Nutrients ---
            nut = nutrients[r][c]
            # Upwelling brings nutrients
            if new_w[r][c] > 0:
                nut += _NUTRIENT_UPWELL * new_w[r][c] * 10.0
            # Surface consumption (biological pump)
            nut -= _NUTRIENT_DECAY * nut
            # Advection
            if not land[src_r][src_c]:
                nut += (nutrients[src_r][src_c] - nut) * 0.05
            new_nut[r][c] = _clamp(nut, 0.0, 1.0)
            total_nut += new_nut[r][c]

    # Update surface fields
    self.thermohaline_temp = new_temp
    self.thermohaline_salinity = new_sal
    self.thermohaline_u = new_u
    self.thermohaline_v = new_v
    self.thermohaline_w = new_w
    self.thermohaline_ice = new_ice
    self.thermohaline_nutrients = new_nut

    # --- Update deep ocean ---
    for d in range(depth):
        frac = (d + 1) / depth
        for r in range(rows):
            for c in range(cols):
                if land[r][c]:
                    continue
                dt = deep_temp[d][r][c]
                ds = deep_sal[d][r][c]
                # Slow diffusion from above
                above_t = new_temp[r][c] if d == 0 else deep_temp[d - 1][r][c]
                above_s = new_sal[r][c] if d == 0 else deep_sal[d - 1][r][c]
                dt += 0.005 * (above_t - dt) * amoc
                ds += 0.003 * (above_s - ds) * amoc
                # Geothermal heating at bottom
                if d == depth - 1:
                    dt += _GEOTHERMAL_FLUX
                # Downwelling injects surface water into deep layers
                if new_w[r][c] < 0:
                    inject = -new_w[r][c] * 0.15
                    dt += inject * (new_temp[r][c] - dt)
                    ds += inject * (new_sal[r][c] - ds)
                deep_temp[d][r][c] = _clamp(dt, 0.0, 1.0)
                deep_sal[d][r][c] = _clamp(ds, 0.0, 1.0)

    # --- AMOC strength: driven by N-S density gradient ---
    # Average density at high northern latitudes vs tropics
    n_polar_dens = []
    n_tropic_dens = []
    for r in range(rows):
        lat = _lat_fraction(r, rows)
        for c in range(cols):
            if land[r][c]:
                continue
            d = self.thermohaline_density[r][c]
            if lat < 0.15:
                n_polar_dens.append(d)
            elif 0.35 < lat < 0.65:
                n_tropic_dens.append(d)

    if n_polar_dens and n_tropic_dens:
        polar_d = sum(n_polar_dens) / len(n_polar_dens)
        tropic_d = sum(n_tropic_dens) / len(n_tropic_dens)
        density_contrast = polar_d - tropic_d
        # AMOC strengthens when polar water is denser than tropical water
        target_amoc = _clamp(0.5 + density_contrast * 10.0, 0.0, 1.5)
        # Slow adjustment
        self.thermohaline_amoc_strength += 0.01 * (target_amoc - self.thermohaline_amoc_strength)
        self.thermohaline_amoc_strength = _clamp(self.thermohaline_amoc_strength, 0.0, 1.5)
    else:
        density_contrast = 0.0

    # --- Snowball: very slow geothermal warming from below ---
    if pid == "snowball" and gen % 50 == 0:
        for r in range(rows):
            for c in range(cols):
                if not land[r][c]:
                    new_temp[r][c] = min(1.0, new_temp[r][c] + 0.001)

    # --- Metrics ---
    if n_ocean == 0:
        n_ocean = 1
    avg_sst = sum(new_temp[r][c] for r in range(rows) for c in range(cols) if not land[r][c]) / n_ocean
    avg_sal = sum(new_sal[r][c] for r in range(rows) for c in range(cols) if not land[r][c]) / n_ocean
    ice_area = sum(1 for r in range(rows) for c in range(cols) if new_ice[r][c] > 0.3 and not land[r][c]) / max(1, n_ocean)
    avg_deep = sum(deep_temp[depth - 1][r][c] for r in range(rows) for c in range(cols) if not land[r][c]) / n_ocean

    hist = self.thermohaline_history
    _append_metric(hist, 'amoc_strength', self.thermohaline_amoc_strength)
    _append_metric(hist, 'mean_sst', avg_sst)
    _append_metric(hist, 'mean_salinity', avg_sal)
    _append_metric(hist, 'enso_index', enso_idx)
    _append_metric(hist, 'ice_area', ice_area)
    _append_metric(hist, 'upwelling', total_upwelling / n_ocean)
    _append_metric(hist, 'deep_temp', avg_deep)
    _append_metric(hist, 'nutrient_level', total_nut / n_ocean)
    _append_metric(hist, 'max_current', max_current)
    _append_metric(hist, 'density_contrast', density_contrast)


def _append_metric(hist, key, val):
    """Append to history, cap at 300 entries."""
    lst = hist[key]
    lst.append(val)
    if len(lst) > 300:
        del lst[0]


# ======================================================================
#  Key Handlers
# ======================================================================

def _handle_thermohaline_menu_key(self, key: int) -> bool:
    """Handle keys in preset menu."""
    if key == curses.KEY_UP or key == ord('k'):
        self.thermohaline_menu_sel = (self.thermohaline_menu_sel - 1) % len(THERMOHALINE_PRESETS)
        return True
    if key == curses.KEY_DOWN or key == ord('j'):
        self.thermohaline_menu_sel = (self.thermohaline_menu_sel + 1) % len(THERMOHALINE_PRESETS)
        return True
    if key in (10, 13, curses.KEY_ENTER):
        _thermohaline_init(self, self.thermohaline_menu_sel)
        self.thermohaline_running = True
        return True
    if key == ord('q') or key == 27:
        self._exit_thermohaline_mode()
        return True
    return False


def _handle_thermohaline_key(self, key: int) -> bool:
    """Handle keys during simulation."""
    if key == ord(' '):
        self.thermohaline_running = not self.thermohaline_running
        return True
    if key == ord('v'):
        views = ["currents", "crosssection", "graphs"]
        idx = views.index(self.thermohaline_view)
        self.thermohaline_view = views[(idx + 1) % len(views)]
        return True
    if key == ord('n'):
        _thermohaline_step(self)
        return True
    if key == ord('+') or key == ord('='):
        self.thermohaline_hosing_rate = min(0.05, self.thermohaline_hosing_rate + 0.005)
        self._flash(f"Hosing: {self.thermohaline_hosing_rate:.3f}")
        return True
    if key == ord('-'):
        self.thermohaline_hosing_rate = max(0.0, self.thermohaline_hosing_rate - 0.005)
        self._flash(f"Hosing: {self.thermohaline_hosing_rate:.3f}")
        return True
    if key == curses.KEY_UP:
        self.thermohaline_xsec_row = max(0, self.thermohaline_xsec_row - 1)
        return True
    if key == curses.KEY_DOWN:
        self.thermohaline_xsec_row = min(self.thermohaline_rows - 1, self.thermohaline_xsec_row + 1)
        return True
    if key == ord('r'):
        idx = next((i for i, p in enumerate(THERMOHALINE_PRESETS)
                     if p[2] == self.thermohaline_preset_id), 0)
        _thermohaline_init(self, idx)
        self.thermohaline_running = True
        return True
    if key == ord('R') or key == ord('m'):
        self.thermohaline_menu = True
        self.thermohaline_menu_sel = 0
        return True
    if key == ord('q'):
        self._exit_thermohaline_mode()
        return True
    return False


# ======================================================================
#  Drawing — Preset Menu
# ======================================================================

def _draw_thermohaline_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    self.stdscr.erase()
    title = "Ocean Thermohaline Circulation & Global Current System"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(4))
    except curses.error:
        pass

    sub = "Select an ocean circulation preset:"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(sub)) // 2), sub)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(THERMOHALINE_PRESETS):
        y = 5 + i * 3
        if y + 1 >= max_y:
            break
        marker = "> " if i == self.thermohaline_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.thermohaline_menu_sel else 0
        try:
            self.stdscr.addstr(y, 4, f"{marker}{name}", attr | curses.A_BOLD)
        except curses.error:
            pass
        try:
            self.stdscr.addstr(y + 1, 8, desc[:max_x - 10], curses.color_pair(7))
        except curses.error:
            pass

    hint = "[up/dn] select  [Enter] start  [q] back"
    try:
        self.stdscr.addstr(max_y - 2, max(0, (max_x - len(hint)) // 2), hint,
                           curses.color_pair(7))
    except curses.error:
        pass


# ======================================================================
#  Drawing — Main dispatch
# ======================================================================

def _draw_thermohaline(self, max_y: int, max_x: int):
    """Dispatch to appropriate view drawer."""
    if self.thermohaline_view == "currents":
        _draw_currents_view(self, max_y, max_x)
    elif self.thermohaline_view == "crosssection":
        _draw_crosssection_view(self, max_y, max_x)
    elif self.thermohaline_view == "graphs":
        _draw_graphs_view(self, max_y, max_x)


# ======================================================================
#  Drawing — Global Current Map
# ======================================================================

_CURRENT_ARROWS = {
    (0, 1): '\u2192', (0, -1): '\u2190',
    (1, 0): '\u2193', (-1, 0): '\u2191',
    (1, 1): '\u2198', (1, -1): '\u2199',
    (-1, 1): '\u2197', (-1, -1): '\u2196',
    (0, 0): '\u00b7',
}

_TEMP_GLYPHS = ' .,:;+=*#@'


def _draw_currents_view(self, max_y: int, max_x: int):
    """Render global current map with temperature/salinity overlay."""
    self.stdscr.erase()
    rows = self.thermohaline_rows
    cols = self.thermohaline_cols
    temp = self.thermohaline_temp
    sal = self.thermohaline_salinity
    u = self.thermohaline_u
    v = self.thermohaline_v
    w = self.thermohaline_w
    ice = self.thermohaline_ice
    land = self.thermohaline_land
    nutrients = self.thermohaline_nutrients

    draw_rows = min(rows, max_y - 3)
    draw_cols = min(cols, max_x - 1)

    for r in range(draw_rows):
        for c in range(draw_cols):
            if r >= rows or c >= cols:
                continue

            if land[r][c]:
                try:
                    self.stdscr.addstr(r, c, '#', curses.color_pair(3) | curses.A_DIM)
                except curses.error:
                    pass
                continue

            is_ice = ice[r][c] > 0.3
            t = temp[r][c]

            if is_ice:
                ch = '~'
                color_idx = 7
            elif r % 2 == 0 and c % 3 == 0:
                # Current arrow
                uu = u[r][c]
                vv = v[r][c]
                cs = math.sqrt(uu * uu + vv * vv)
                if cs > 0.03:
                    du = 1 if uu > 0.08 else (-1 if uu < -0.08 else 0)
                    dv = 1 if vv > 0.08 else (-1 if vv < -0.08 else 0)
                    ch = _CURRENT_ARROWS.get((dv, du), '.')
                    if cs > 0.4:
                        color_idx = 1  # red = strong current
                    elif cs > 0.2:
                        color_idx = 3  # yellow = moderate
                    else:
                        color_idx = 6  # cyan = weak
                else:
                    ch = '\u00b7'
                    color_idx = 7
            elif w[r][c] > 0.02:
                # Upwelling indicator
                ch = '^'
                color_idx = 2  # green = nutrient-rich upwelling
            elif w[r][c] < -0.02:
                # Downwelling indicator
                ch = 'v'
                color_idx = 5  # magenta = sinking
            else:
                # Temperature glyph
                ti = int(t / 0.8 * (len(_TEMP_GLYPHS) - 1))
                ti = max(0, min(len(_TEMP_GLYPHS) - 1, ti))
                ch = _TEMP_GLYPHS[ti]
                if t > 0.6:
                    color_idx = 1  # red = warm
                elif t > 0.4:
                    color_idx = 3  # yellow
                elif t > 0.25:
                    color_idx = 6  # cyan = cool
                else:
                    color_idx = 4  # blue = cold

            try:
                self.stdscr.addstr(r, c, ch, curses.color_pair(color_idx))
            except curses.error:
                pass

    # Status bar
    gen = self.thermohaline_generation
    amoc = self.thermohaline_amoc_strength
    enso = self.thermohaline_enso_amplitude * math.sin(self.thermohaline_enso_phase)
    state = "RUNNING" if self.thermohaline_running else "PAUSED"
    hosing = self.thermohaline_hosing_rate
    status = (f" {self.thermohaline_preset_name} | tick {gen} | {state} | "
              f"AMOC:{amoc:.2f} | ENSO:{enso:+.2f} | hosing:{hosing:.3f} | "
              f"[v]iew [+/-]hosing [space] [r]eset [q]uit")
    try:
        self.stdscr.addstr(max_y - 2, 0, status[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    legend = " #=land ~=ice ^=upwell v=sink  arrows=currents  cold(blue) cool(cyan) warm(yellow) hot(red)"
    try:
        self.stdscr.addstr(max_y - 1, 0, legend[:max_x - 1], curses.color_pair(7))
    except curses.error:
        pass


# ======================================================================
#  Drawing — Ocean Cross-Section Depth Profile
# ======================================================================

def _draw_crosssection_view(self, max_y: int, max_x: int):
    """Render ocean cross-section at selected latitude showing conveyor belt."""
    self.stdscr.erase()
    rows = self.thermohaline_rows
    cols = self.thermohaline_cols
    depth = self.thermohaline_depth
    xsec_r = self.thermohaline_xsec_row
    land = self.thermohaline_land
    temp = self.thermohaline_temp
    sal = self.thermohaline_salinity
    deep_temp = self.thermohaline_deep_temp
    deep_sal = self.thermohaline_deep_sal
    u = self.thermohaline_u
    w = self.thermohaline_w

    lat = _lat_fraction(xsec_r, rows)
    lat_deg = (0.5 - lat) * 180

    title = f"Ocean Cross-Section at {lat_deg:+.0f} lat (row {xsec_r}) | [up/dn] move slice"
    try:
        self.stdscr.addstr(0, 2, title, curses.A_BOLD | curses.color_pair(4))
    except curses.error:
        pass

    # Draw depth layers
    draw_cols = min(cols, max_x - 1)
    avail_rows = max_y - 5
    rows_per_layer = max(1, avail_rows // (depth + 1))

    # Surface layer (row 0 = surface)
    for layer in range(depth + 1):
        base_y = 2 + layer * rows_per_layer
        if base_y >= max_y - 3:
            break

        # Depth label
        if layer == 0:
            label = "Sfc"
        else:
            label = f"{layer * 500}m"
        try:
            self.stdscr.addstr(base_y, 0, label[:3], curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass

        for c in range(min(draw_cols - 4, cols)):
            x = c + 4
            if x >= max_x - 1:
                break

            if land[xsec_r][c]:
                ch = '#'
                color_idx = 3
            else:
                if layer == 0:
                    t = temp[xsec_r][c]
                    s = sal[xsec_r][c]
                    cu = u[xsec_r][c]
                    cw = w[xsec_r][c]
                else:
                    d_idx = min(layer - 1, depth - 1)
                    t = deep_temp[d_idx][xsec_r][c]
                    s = deep_sal[d_idx][xsec_r][c]
                    cu = u[xsec_r][c] * (1.0 - layer / (depth + 1))  # current weakens with depth
                    cw = w[xsec_r][c] * (1.0 - layer / (depth + 2))

                # Temperature coloring
                if t > 0.6:
                    color_idx = 1  # red
                elif t > 0.4:
                    color_idx = 3  # yellow
                elif t > 0.25:
                    color_idx = 6  # cyan
                else:
                    color_idx = 4  # blue

                # Glyph: show circulation direction
                if abs(cu) > 0.1 or abs(cw) > 0.02:
                    if cw > 0.02:
                        ch = '^'  # upwelling
                    elif cw < -0.02:
                        ch = 'v'  # downwelling
                    elif cu > 0.1:
                        ch = '>'  # eastward flow
                    elif cu < -0.1:
                        ch = '<'  # westward flow
                    else:
                        ch = '-'
                else:
                    # Density shading
                    dens = _density(t, s)
                    if dens > 1.05:
                        ch = '@'
                    elif dens > 1.02:
                        ch = '='
                    elif dens > 0.99:
                        ch = '-'
                    else:
                        ch = '.'

            for row_off in range(min(rows_per_layer, 2)):
                try:
                    self.stdscr.addstr(base_y + row_off, x, ch, curses.color_pair(color_idx))
                except curses.error:
                    pass

    # Status bar
    gen = self.thermohaline_generation
    amoc = self.thermohaline_amoc_strength
    state = "RUNNING" if self.thermohaline_running else "PAUSED"
    status = (f" Cross-Section | tick {gen} | {state} | AMOC:{amoc:.2f} | "
              f"[up/dn]latitude [v]iew [+/-]hosing [space] [r]eset [q]uit")
    try:
        self.stdscr.addstr(max_y - 2, 0, status[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    legend = " ^=upwell v=sink >/<=flow  #=land  cold(blue) cool(cyan) warm(yellow) hot(red)  @/=/-/.=density"
    try:
        self.stdscr.addstr(max_y - 1, 0, legend[:max_x - 1], curses.color_pair(7))
    except curses.error:
        pass


# ======================================================================
#  Drawing — Time-Series Sparkline Graphs
# ======================================================================

def _draw_graphs_view(self, max_y: int, max_x: int):
    """Time-series sparkline graphs for ocean metrics."""
    self.stdscr.erase()
    hist = self.thermohaline_history
    graph_w = min(200, max_x - 30)

    title = (f"Ocean Metrics -- {self.thermohaline_preset_name} | "
             f"tick {self.thermohaline_generation}")
    try:
        self.stdscr.addstr(0, 2, title, curses.A_BOLD)
    except curses.error:
        pass

    labels = [
        ("AMOC Strength",     'amoc_strength',    1),
        ("Mean SST",          'mean_sst',         1),
        ("Mean Salinity",     'mean_salinity',     6),
        ("ENSO Index",        'enso_index',        3),
        ("Ice Area %",        'ice_area',          7),
        ("Upwelling",         'upwelling',         2),
        ("Deep Ocean Temp",   'deep_temp',         4),
        ("Nutrient Level",    'nutrient_level',    2),
        ("Max Current Speed", 'max_current',       1),
        ("Density Contrast",  'density_contrast',  5),
    ]

    bars = " _.,:-=!#%@"
    n_bars = len(bars) - 1

    for gi, (label, key, cp) in enumerate(labels):
        base_y = 2 + gi * 2
        if base_y + 1 >= max_y - 2:
            break

        data = hist.get(key, [])
        cur_val = data[-1] if data else 0
        if isinstance(cur_val, float):
            lbl = f"{label}: {cur_val:.3f}"
        else:
            lbl = f"{label}: {cur_val}"
        try:
            self.stdscr.addstr(base_y, 2, lbl[:24],
                               curses.color_pair(cp) | curses.A_BOLD)
        except curses.error:
            pass

        if data:
            visible = data[-graph_w:]
            mn = min(visible)
            mx = max(visible)
            rng = mx - mn if mx > mn else 1.0
            color = curses.color_pair(cp)
            for i, val in enumerate(visible):
                x = 26 + i
                if x >= max_x - 1:
                    break
                idx = int((val - mn) / rng * n_bars)
                idx = max(0, min(n_bars, idx))
                try:
                    self.stdscr.addstr(base_y, x, bars[idx], color)
                except curses.error:
                    pass

    status = "[v]iew [+/-]hosing [space]pause [r]estart [q]uit"
    try:
        self.stdscr.addstr(max_y - 1, 2, status[:max_x - 3], curses.color_pair(7))
    except curses.error:
        pass


# ======================================================================
#  Registration
# ======================================================================

def register(App):
    """Register thermohaline circulation mode methods on the App class."""
    App.THERMOHALINE_PRESETS = THERMOHALINE_PRESETS
    App._enter_thermohaline_mode = _enter_thermohaline_mode
    App._exit_thermohaline_mode = _exit_thermohaline_mode
    App._thermohaline_init = _thermohaline_init
    App._thermohaline_step = _thermohaline_step
    App._handle_thermohaline_menu_key = _handle_thermohaline_menu_key
    App._handle_thermohaline_key = _handle_thermohaline_key
    App._draw_thermohaline_menu = _draw_thermohaline_menu
    App._draw_thermohaline = _draw_thermohaline
