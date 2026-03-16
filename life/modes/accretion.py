"""Mode: accretion — Planetary Accretion & Solar System Formation.

Simulates the birth of a solar system from a protoplanetary disk:
- Dust and gas particles coalesce into planetesimals via gravitational accretion
- Planetesimals clear their orbital lanes and undergo giant impacts/mergers
- Frost line determines rocky vs. icy composition
- Inner rocky planets and outer gas giants self-organize from chaos
- Orbital resonances and planetary migration
- Moon capture from giant impacts
- Late Heavy Bombardment phase

Three views:
  1) Top-down orbital disk map with particle density and forming protoplanets
  2) Cross-section showing disk thickness, temperature, frost line
  3) Time-series sparkline graphs for 10 metrics

Six presets:
  Calm Accretion, Jupiter Migration (Grand Tack), Giant Impact (Moon formation),
  Resonant Chain (TRAPPIST-1 analog), Hot Jupiter Inward Spiral,
  Late Heavy Bombardment
"""
import curses
import math
import random

# ======================================================================
#  Presets
# ======================================================================

ACCRETION_PRESETS = [
    ("Calm Accretion",
     "Steady protoplanetary disk — dust slowly coalesces into rocky and icy worlds",
     "calm"),
    ("Jupiter Migration (Grand Tack)",
     "Gas giant forms early, migrates inward scattering material, then reverses outward",
     "grand_tack"),
    ("Giant Impact (Moon Formation)",
     "Theia-sized body collides with proto-Earth — debris disk forms the Moon",
     "giant_impact"),
    ("Resonant Chain (TRAPPIST-1)",
     "Compact system — planets migrate into mean-motion resonance chain",
     "resonant"),
    ("Hot Jupiter Inward Spiral",
     "Gas giant spirals inward through disk, ejecting inner planets",
     "hot_jupiter"),
    ("Late Heavy Bombardment",
     "Mature system destabilized — outer body scattering bombards inner planets",
     "lhb"),
]

# ======================================================================
#  Physical constants
# ======================================================================

_GRAV_CONST = 0.5            # gravitational coupling strength
_DISK_INNER_AU = 0.3         # inner disk edge (AU)
_DISK_OUTER_AU = 40.0        # outer disk edge (AU)
_FROST_LINE_AU = 2.7         # frost line distance (AU)
_STAR_MASS = 100.0           # central star mass (arbitrary units)

# Accretion
_ACCRETION_RADIUS = 1.5      # Hill sphere factor for merging
_GAS_ACCRETION_THRESH = 10.0 # core mass to start runaway gas accretion
_GAS_ACCRETION_RATE = 0.08   # gas accretion rate per tick
_MAX_GAS_MASS = 300.0        # max gas giant mass

# Disk
_DISK_GAS_DECAY = 0.9997     # gas dissipation per tick
_DISK_DUST_DECAY = 0.9999    # dust dissipation per tick
_PARTICLE_DAMPING = 0.998    # orbital eccentricity damping from gas drag
_INITIAL_DUST_PARTICLES = 400
_INITIAL_PLANETESIMALS = 60

# Migration
_TYPE_I_MIGRATION = -0.0003  # inward migration rate for small bodies
_TYPE_II_MIGRATION = -0.0006 # inward migration rate for gap-opening giants
_MIGRATION_MASS_THRESH = 50.0 # mass threshold for Type II migration

# Dynamics
_EJECT_SPEED = 0.8           # ejection velocity threshold
_RESONANCE_LOCK_PROB = 0.02  # probability of locking into resonance per tick
_COLLISION_DEBRIS_FRAC = 0.1 # fraction of mass becoming debris on impact
_MOON_CAPTURE_PROB = 0.3     # probability of debris becoming a moon

# LHB
_LHB_SCATTER_PROB = 0.01     # probability of outer body perturbation per tick
_LHB_IMPULSE = 0.15          # velocity kick from scattering

_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]


# ======================================================================
#  Mode lifecycle
# ======================================================================

def _enter_accretion_mode(self):
    """Enter Planetary Accretion mode — show preset menu."""
    self.accretion_menu = True
    self.accretion_menu_sel = 0


def _exit_accretion_mode(self):
    """Exit Planetary Accretion mode."""
    self.accretion_mode = False
    self.accretion_menu = False
    self.accretion_running = False
    self.accretion_bodies = []
    self.accretion_dust = []
    self.accretion_debris = []
    self.accretion_history = {}


# ======================================================================
#  Initialization
# ======================================================================

def _accretion_init(self, preset):
    """Initialize accretion simulation from preset."""
    rows, cols = self.grid.rows, self.grid.cols
    self.accretion_rows = rows
    self.accretion_cols = cols
    self.accretion_generation = 0
    self.accretion_time = 0.0
    self.accretion_speed_scale = 1.0
    self.accretion_view = "disk"  # "disk", "cross", "graphs"
    self.accretion_running = True
    self.accretion_paused = False
    self.accretion_preset = preset
    self.accretion_show_orbits = True
    self.accretion_show_labels = True
    self.accretion_selected = -1
    self.accretion_zoom = 1.0
    self.accretion_lhb_active = False
    self.accretion_lhb_timer = 0

    # Disk properties
    self.accretion_gas_remaining = 1.0   # normalized gas fraction
    self.accretion_dust_remaining = 1.0  # normalized dust fraction

    # History for sparklines
    self.accretion_history = {
        "planet_count": [], "largest_mass": [], "disk_mass": [],
        "mean_ecc": [], "collision_rate": [], "total_mass": [],
        "gas_giants": [], "rocky_count": [], "mean_a": [],
        "moon_count": [],
    }
    self.accretion_collisions_this_tick = 0
    self.accretion_total_collisions = 0

    # Background stars
    self.accretion_bg_stars = []
    for _ in range(min(60, rows * cols // 40)):
        self.accretion_bg_stars.append((random.randint(0, rows - 1),
                                        random.randint(0, cols - 1)))

    # Initialize bodies based on preset
    self.accretion_bodies = []
    self.accretion_dust = []
    self.accretion_debris = []

    if preset == "calm":
        _init_calm(self)
    elif preset == "grand_tack":
        _init_grand_tack(self)
    elif preset == "giant_impact":
        _init_giant_impact(self)
    elif preset == "resonant":
        _init_resonant(self)
    elif preset == "hot_jupiter":
        _init_hot_jupiter(self)
    elif preset == "lhb":
        _init_lhb(self)


def _make_body(a, mass, ecc=0.0, composition="rocky", name=None):
    """Create a protoplanetary body."""
    angle = random.uniform(0, 2 * math.pi)
    return {
        "a": a,             # semi-major axis (AU)
        "angle": angle,     # current orbital angle
        "ecc": ecc,         # eccentricity
        "mass": mass,       # mass (arbitrary units)
        "composition": composition,  # "rocky", "icy", "gas_giant"
        "name": name,
        "moons": 0,
        "trail": [],
        "age": 0,
        "migrating": False,
        "resonance": None,  # locked period ratio if any
        "color": 0,
    }


def _make_dust(a):
    """Create a dust/small particle."""
    angle = random.uniform(0, 2 * math.pi)
    icy = a > _FROST_LINE_AU
    return {
        "a": a,
        "angle": angle,
        "mass": random.uniform(0.01, 0.1) * (3.0 if icy else 1.0),
        "icy": icy,
    }


def _init_calm(self):
    """Standard protoplanetary disk — even distribution."""
    for _ in range(_INITIAL_DUST_PARTICLES):
        a = random.uniform(_DISK_INNER_AU, _DISK_OUTER_AU)
        self.accretion_dust.append(_make_dust(a))
    for _ in range(_INITIAL_PLANETESIMALS):
        a = random.uniform(_DISK_INNER_AU, _DISK_OUTER_AU * 0.8)
        mass = random.uniform(0.3, 2.0)
        if a > _FROST_LINE_AU:
            mass *= 3.0  # icy cores are bigger
        comp = "icy" if a > _FROST_LINE_AU else "rocky"
        self.accretion_bodies.append(_make_body(a, mass, ecc=random.uniform(0.0, 0.08), composition=comp))


def _init_grand_tack(self):
    """Jupiter forms early beyond frost line, begins migrating inward."""
    # Scattered disk
    for _ in range(_INITIAL_DUST_PARTICLES):
        a = random.uniform(_DISK_INNER_AU, _DISK_OUTER_AU)
        self.accretion_dust.append(_make_dust(a))
    # Inner rocky embryos
    for _ in range(25):
        a = random.uniform(0.5, 4.0)
        mass = random.uniform(0.5, 3.0)
        self.accretion_bodies.append(_make_body(a, mass, ecc=random.uniform(0.0, 0.06)))
    # Proto-Jupiter — already massive, migrating inward
    jup = _make_body(5.0, 80.0, ecc=0.02, composition="gas_giant", name="Proto-Jupiter")
    jup["migrating"] = True
    jup["color"] = 3
    self.accretion_bodies.append(jup)
    # Proto-Saturn forming
    sat = _make_body(8.0, 20.0, ecc=0.03, composition="icy", name="Proto-Saturn")
    self.accretion_bodies.append(sat)
    # Outer icy bodies
    for _ in range(20):
        a = random.uniform(10.0, 35.0)
        mass = random.uniform(0.5, 4.0)
        self.accretion_bodies.append(_make_body(a, mass, ecc=random.uniform(0.0, 0.1), composition="icy"))


def _init_giant_impact(self):
    """Proto-Earth and Theia on near-crossing orbits."""
    for _ in range(200):
        a = random.uniform(_DISK_INNER_AU, 15.0)
        self.accretion_dust.append(_make_dust(a))
    # Proto-Earth
    earth = _make_body(1.0, 15.0, ecc=0.01, composition="rocky", name="Proto-Earth")
    earth["color"] = 6
    self.accretion_bodies.append(earth)
    # Theia — Mars-sized impactor on slightly eccentric crossing orbit
    theia = _make_body(1.05, 5.0, ecc=0.08, composition="rocky", name="Theia")
    theia["color"] = 1
    theia["angle"] = earth["angle"] + 1.05  # L4/L5 Trojan-like start
    self.accretion_bodies.append(theia)
    # Other inner embryos
    for _ in range(15):
        a = random.uniform(0.4, 3.5)
        mass = random.uniform(0.3, 3.0)
        self.accretion_bodies.append(_make_body(a, mass, ecc=random.uniform(0.0, 0.05)))
    # Outer giants
    self.accretion_bodies.append(_make_body(5.2, 100.0, ecc=0.04, composition="gas_giant", name="Jupiter"))
    self.accretion_bodies.append(_make_body(9.5, 60.0, ecc=0.05, composition="gas_giant", name="Saturn"))
    self.accretion_gas_remaining = 0.3  # late stage, most gas gone


def _init_resonant(self):
    """Compact system — bodies migrate into resonance chain (TRAPPIST-1 analog)."""
    for _ in range(300):
        a = random.uniform(0.01, 5.0)
        self.accretion_dust.append(_make_dust(a))
    # Small star → closer frost line
    # 7 embryos migrating inward
    base_a = [0.8, 1.2, 1.6, 2.1, 2.7, 3.4, 4.2]
    for i, a in enumerate(base_a):
        mass = random.uniform(1.5, 4.0)
        comp = "icy" if a > 1.5 else "rocky"
        body = _make_body(a, mass, ecc=random.uniform(0.0, 0.03), composition=comp,
                         name=f"Planet-{chr(98 + i)}")
        body["migrating"] = True
        self.accretion_bodies.append(body)
    self.accretion_zoom = 3.0  # zoom in for compact system


def _init_hot_jupiter(self):
    """Gas giant forming far out, spiraling inward through disk."""
    for _ in range(_INITIAL_DUST_PARTICLES):
        a = random.uniform(_DISK_INNER_AU, _DISK_OUTER_AU)
        self.accretion_dust.append(_make_dust(a))
    # Inner rocky embryos that will get ejected
    for _ in range(20):
        a = random.uniform(0.5, 5.0)
        mass = random.uniform(0.5, 3.0)
        self.accretion_bodies.append(_make_body(a, mass, ecc=random.uniform(0.0, 0.05)))
    # Hot Jupiter progenitor — massive, migrating
    hj = _make_body(8.0, 120.0, ecc=0.01, composition="gas_giant", name="Hot Jupiter")
    hj["migrating"] = True
    hj["color"] = 1
    self.accretion_bodies.append(hj)


def _init_lhb(self):
    """Mature system destabilized by outer planet migration."""
    self.accretion_gas_remaining = 0.05  # almost no gas left
    self.accretion_dust_remaining = 0.2
    # Formed inner planets
    inner_planets = [
        ("Mercury", 0.39, 1.0, 0.02, "rocky"),
        ("Venus", 0.72, 8.0, 0.01, "rocky"),
        ("Earth", 1.0, 10.0, 0.02, "rocky"),
        ("Mars", 1.52, 2.0, 0.05, "rocky"),
    ]
    for name, a, mass, ecc, comp in inner_planets:
        body = _make_body(a, mass, ecc=ecc, composition=comp, name=name)
        self.accretion_bodies.append(body)
    # Outer giants
    self.accretion_bodies.append(_make_body(5.2, 150.0, ecc=0.04, composition="gas_giant", name="Jupiter"))
    self.accretion_bodies.append(_make_body(8.5, 80.0, ecc=0.05, composition="gas_giant", name="Saturn"))
    self.accretion_bodies.append(_make_body(14.0, 20.0, ecc=0.06, composition="icy", name="Uranus"))
    self.accretion_bodies.append(_make_body(20.0, 22.0, ecc=0.05, composition="icy", name="Neptune"))
    # Kuiper belt objects — will get scattered
    for _ in range(40):
        a = random.uniform(22.0, 40.0)
        mass = random.uniform(0.05, 0.5)
        self.accretion_bodies.append(_make_body(a, mass, ecc=random.uniform(0.0, 0.1), composition="icy"))
    # Residual dust
    for _ in range(100):
        a = random.uniform(20.0, 45.0)
        self.accretion_dust.append(_make_dust(a))
    self.accretion_lhb_active = True
    self.accretion_lhb_timer = 200  # ticks until bombardment begins


# ======================================================================
#  Simulation step
# ======================================================================

def _accretion_step(self):
    """Advance the accretion simulation by one tick."""
    self.accretion_generation += 1
    dt = 0.01 * self.accretion_speed_scale
    self.accretion_time += dt
    self.accretion_collisions_this_tick = 0
    bodies = self.accretion_bodies
    dust = self.accretion_dust

    # --- Orbital motion ---
    for b in bodies:
        # Keplerian angular velocity: omega ~ a^(-3/2)
        if b["a"] > 0.05:
            omega = math.sqrt(_STAR_MASS / (b["a"] ** 3))
            b["angle"] = (b["angle"] + omega * dt) % (2 * math.pi)
            b["age"] += 1

            # Eccentricity damping from gas drag (stronger for small bodies)
            if self.accretion_gas_remaining > 0.01 and b["mass"] < 50.0:
                drag = _PARTICLE_DAMPING ** (1.0 / max(b["mass"], 0.1))
                b["ecc"] *= drag

            # Migration
            if b["migrating"] and self.accretion_gas_remaining > 0.05:
                if b["mass"] >= _MIGRATION_MASS_THRESH:
                    b["a"] += _TYPE_II_MIGRATION * dt * 50
                else:
                    b["a"] += _TYPE_I_MIGRATION * dt * 50
                b["a"] = max(0.02, b["a"])

            # Gas accretion for massive cores beyond frost line
            if (b["mass"] >= _GAS_ACCRETION_THRESH and
                    self.accretion_gas_remaining > 0.05 and
                    b["composition"] != "gas_giant"):
                accreted = _GAS_ACCRETION_RATE * self.accretion_gas_remaining * dt
                b["mass"] += accreted
                self.accretion_gas_remaining -= accreted * 0.01
                if b["mass"] >= _GAS_ACCRETION_THRESH * 3:
                    b["composition"] = "gas_giant"
            elif b["composition"] == "gas_giant" and self.accretion_gas_remaining > 0.02:
                if b["mass"] < _MAX_GAS_MASS:
                    accreted = _GAS_ACCRETION_RATE * 0.5 * self.accretion_gas_remaining * dt
                    b["mass"] += accreted
                    self.accretion_gas_remaining -= accreted * 0.005

            # Trail
            b["trail"].append((b["a"], b["angle"]))
            if len(b["trail"]) > 40:
                b["trail"].pop(0)

    # --- Dust orbital motion ---
    for d in dust:
        if d["a"] > 0.05:
            omega = math.sqrt(_STAR_MASS / (d["a"] ** 3))
            d["angle"] = (d["angle"] + omega * dt) % (2 * math.pi)

    # --- Dust accretion onto bodies ---
    new_dust = []
    for d in dust:
        accreted = False
        for b in bodies:
            da = abs(d["a"] - b["a"])
            # Hill sphere radius
            r_hill = b["a"] * (b["mass"] / (3 * _STAR_MASS)) ** (1 / 3)
            if da < max(r_hill * _ACCRETION_RADIUS, 0.3):
                # Angular proximity check
                dangle = abs(d["angle"] - b["angle"])
                dangle = min(dangle, 2 * math.pi - dangle)
                if dangle < 0.5 or da < r_hill:
                    b["mass"] += d["mass"]
                    accreted = True
                    break
        if not accreted:
            new_dust.append(d)
    self.accretion_dust = new_dust

    # --- Body-body interactions and mergers ---
    merged = set()
    new_debris = []
    n = len(bodies)
    for i in range(n):
        if i in merged:
            continue
        for j in range(i + 1, n):
            if j in merged:
                continue
            bi, bj = bodies[i], bodies[j]
            da = abs(bi["a"] - bj["a"])
            # Hill sphere of larger body
            larger = bi if bi["mass"] >= bj["mass"] else bj
            r_hill = larger["a"] * (larger["mass"] / (3 * _STAR_MASS)) ** (1 / 3)
            merge_dist = max(r_hill * _ACCRETION_RADIUS, 0.15)

            if da < merge_dist:
                # Angular proximity
                dangle = abs(bi["angle"] - bj["angle"])
                dangle = min(dangle, 2 * math.pi - dangle)
                if dangle < 0.4 or da < r_hill * 0.5:
                    # Merge!
                    self.accretion_collisions_this_tick += 1
                    self.accretion_total_collisions += 1

                    if bi["mass"] >= bj["mass"]:
                        primary, secondary = bi, bj
                        merged.add(j)
                    else:
                        primary, secondary = bj, bi
                        merged.add(i)

                    # Mass ratio determines if it's accretion or giant impact
                    ratio = secondary["mass"] / max(primary["mass"], 0.01)
                    debris_mass = secondary["mass"] * _COLLISION_DEBRIS_FRAC * ratio

                    primary["mass"] += secondary["mass"] - debris_mass
                    # Eccentricity kick from impact
                    primary["ecc"] = min(0.5, primary["ecc"] + ratio * 0.05)
                    # Weighted average semi-major axis
                    total_m = primary["mass"] + secondary["mass"]
                    primary["a"] = (primary["a"] * primary["mass"] +
                                   secondary["a"] * secondary["mass"]) / total_m

                    # Moon capture from giant impacts
                    if ratio > 0.1 and random.random() < _MOON_CAPTURE_PROB:
                        primary["moons"] += 1

                    # Debris
                    if debris_mass > 0.01:
                        for _ in range(min(3, int(debris_mass * 5))):
                            da_off = random.uniform(-0.5, 0.5)
                            new_debris.append({
                                "a": max(0.1, primary["a"] + da_off),
                                "angle": primary["angle"] + random.uniform(-0.3, 0.3),
                                "mass": debris_mass / 3,
                                "age": 0,
                            })

                    # Inherit name
                    if secondary["name"] and not primary["name"]:
                        primary["name"] = secondary["name"]
                    # Update composition
                    if primary["composition"] != "gas_giant" and secondary["composition"] == "gas_giant":
                        primary["composition"] = "gas_giant"
                    break  # move to next i

    # Remove merged bodies
    self.accretion_bodies = [b for idx, b in enumerate(bodies) if idx not in merged]
    bodies = self.accretion_bodies

    # Add debris as dust
    for d in new_debris:
        self.accretion_dust.append({
            "a": d["a"], "angle": d["angle"], "mass": d["mass"],
            "icy": d["a"] > _FROST_LINE_AU,
        })

    # --- Gravitational scattering between nearby bodies ---
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            bi, bj = bodies[i], bodies[j]
            da = abs(bi["a"] - bj["a"])
            if da < 2.0:
                # Mutual perturbation
                force = _GRAV_CONST * bi["mass"] * bj["mass"] / max(da ** 2, 0.01)
                kick_i = force / max(bi["mass"], 0.1) * 0.0001
                kick_j = force / max(bj["mass"], 0.1) * 0.0001
                bi["ecc"] = min(0.9, bi["ecc"] + kick_i)
                bj["ecc"] = min(0.9, bj["ecc"] + kick_j)
                # Orbital repulsion/attraction
                if bi["a"] < bj["a"]:
                    bi["a"] -= kick_i * 0.01
                    bj["a"] += kick_j * 0.01
                else:
                    bi["a"] += kick_i * 0.01
                    bj["a"] -= kick_j * 0.01

    # --- Resonance locking ---
    for i in range(len(bodies)):
        if bodies[i]["resonance"]:
            continue
        for j in range(len(bodies)):
            if i == j or not bodies[j]["mass"] > bodies[i]["mass"] * 5:
                continue
            bi, bj = bodies[i], bodies[j]
            if bi["a"] > 0 and bj["a"] > 0:
                period_ratio = (bi["a"] / bj["a"]) ** 1.5
                # Check common resonances: 2:1, 3:2, 4:3, 5:3
                for p, q in [(2, 1), (3, 2), (4, 3), (5, 3)]:
                    target = p / q
                    if abs(period_ratio - target) < 0.08:
                        if random.random() < _RESONANCE_LOCK_PROB:
                            bi["resonance"] = f"{p}:{q}"
                            # Lock semi-major axis
                            bi["a"] = bj["a"] * target ** (2 / 3)
                            bi["ecc"] *= 0.5  # resonance damps eccentricity

    # --- Late Heavy Bombardment ---
    if self.accretion_lhb_active:
        if self.accretion_lhb_timer > 0:
            self.accretion_lhb_timer -= 1
        else:
            # Scatter outer bodies inward
            for b in bodies:
                if b["a"] > 15.0 and b["mass"] < 5.0:
                    if random.random() < _LHB_SCATTER_PROB:
                        b["ecc"] = min(0.95, b["ecc"] + _LHB_IMPULSE)
                        b["a"] *= random.uniform(0.3, 0.9)  # flung inward

    # --- Ejection of high-eccentricity bodies ---
    self.accretion_bodies = [b for b in bodies if b["ecc"] < _EJECT_SPEED and b["a"] > 0.01 and b["a"] < 100.0]

    # --- Disk dissipation ---
    self.accretion_gas_remaining *= _DISK_GAS_DECAY
    self.accretion_dust_remaining *= _DISK_DUST_DECAY

    # --- Record history ---
    h = self.accretion_history
    planets = [b for b in self.accretion_bodies if b["mass"] > 1.0]
    gas_giants = [b for b in self.accretion_bodies if b["composition"] == "gas_giant"]
    rocky = [b for b in planets if b["composition"] == "rocky"]

    h["planet_count"].append(len(planets))
    h["largest_mass"].append(max((b["mass"] for b in self.accretion_bodies), default=0))
    h["disk_mass"].append(self.accretion_gas_remaining + self.accretion_dust_remaining * 0.5 +
                          sum(d["mass"] for d in self.accretion_dust))
    h["mean_ecc"].append(sum(b["ecc"] for b in self.accretion_bodies) / max(len(self.accretion_bodies), 1))
    h["collision_rate"].append(self.accretion_collisions_this_tick)
    h["total_mass"].append(sum(b["mass"] for b in self.accretion_bodies))
    h["gas_giants"].append(len(gas_giants))
    h["rocky_count"].append(len(rocky))
    h["mean_a"].append(sum(b["a"] for b in planets) / max(len(planets), 1))
    h["moon_count"].append(sum(b["moons"] for b in self.accretion_bodies))

    # Trim history
    max_hist = 200
    for key in h:
        if len(h[key]) > max_hist:
            h[key] = h[key][-max_hist:]


# ======================================================================
#  Key handling
# ======================================================================

def _handle_accretion_menu_key(self, key):
    """Handle keys in the accretion preset menu."""
    n = len(ACCRETION_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.accretion_menu_sel = (self.accretion_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.accretion_menu_sel = (self.accretion_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.accretion_menu = False
        self.accretion_mode = False
        self._exit_accretion_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = ACCRETION_PRESETS[self.accretion_menu_sel]
        self.accretion_preset_name = preset[0]
        self._accretion_init(preset[2])
        self.accretion_menu = False
        self.accretion_mode = True
        self.accretion_running = True
    else:
        return False
    return True


def _handle_accretion_key(self, key):
    """Handle keys during accretion simulation."""
    if key == -1:
        return True
    if key in (27, ord('q')):
        self._exit_accretion_mode()
        return True
    elif key == ord(' '):
        self.accretion_running = not self.accretion_running
    elif key in (ord('n'), ord('.')):
        _accretion_step(self)
    elif key == ord('v'):
        views = ["disk", "cross", "graphs"]
        idx = views.index(self.accretion_view)
        self.accretion_view = views[(idx + 1) % len(views)]
    elif key == ord('r'):
        for p in ACCRETION_PRESETS:
            if p[0] == self.accretion_preset_name:
                self._accretion_init(p[2])
                break
    elif key in (ord('R'), ord('m')):
        self.accretion_running = False
        self.accretion_menu = True
        self.accretion_menu_sel = 0
    elif key == ord('+') or key == ord('='):
        self.accretion_speed_scale = min(self.accretion_speed_scale * 1.5, 10.0)
    elif key == ord('-') or key == ord('_'):
        self.accretion_speed_scale = max(self.accretion_speed_scale / 1.5, 0.1)
    elif key == ord('z'):
        self.accretion_zoom = min(self.accretion_zoom * 1.5, 10.0)
    elif key == ord('Z'):
        self.accretion_zoom = max(self.accretion_zoom / 1.5, 0.3)
    elif key == ord('o'):
        self.accretion_show_orbits = not self.accretion_show_orbits
    elif key == ord('l'):
        self.accretion_show_labels = not self.accretion_show_labels
    elif key == ord('\t'):
        nb = len(self.accretion_bodies)
        if nb > 0:
            self.accretion_selected = (self.accretion_selected + 1) % nb
    elif key == ord('u'):
        self.accretion_selected = -1
    else:
        return False
    return True


# ======================================================================
#  Coordinate helpers
# ======================================================================

def _accretion_to_screen(self, a, angle):
    """Convert orbital coords (a, angle) to screen (col, row)."""
    rows = self.accretion_rows
    cols = self.accretion_cols
    cx = cols / 2.0
    cy = rows / 2.0
    half = min(rows / 2.0 - 2, cols / 4.0 - 2)
    max_au = _DISK_OUTER_AU / self.accretion_zoom
    scale = half / max_au
    x_au = a * math.cos(angle)
    y_au = a * math.sin(angle)
    sc = cx + x_au * scale
    sr = cy + y_au * scale * 0.5
    return int(round(sc)), int(round(sr))


# ======================================================================
#  Drawing — Menu
# ======================================================================

def _draw_accretion_menu(self, max_y, max_x):
    """Draw the accretion preset selection menu."""
    self.stdscr.erase()
    title = "═══ Planetary Accretion & Solar System Formation ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(3))
        self.stdscr.addstr(3, 2, "Select a formation scenario:",
                           curses.color_pair(6))
        for i, (name, desc, _) in enumerate(ACCRETION_PRESETS):
            y = 5 + i * 2
            if y >= max_y - 2:
                break
            marker = "▸ " if i == self.accretion_menu_sel else "  "
            attr = (curses.A_BOLD | curses.color_pair(3)) if i == self.accretion_menu_sel else curses.color_pair(6)
            self.stdscr.addstr(y, 3, f"{marker}{name}", attr)
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], curses.A_DIM)
        foot_y = min(5 + len(ACCRETION_PRESETS) * 2 + 1, max_y - 2)
        self.stdscr.addstr(foot_y, 3, "Enter=Select  Esc=Cancel",
                           curses.A_DIM | curses.color_pair(6))
    except curses.error:
        pass


# ======================================================================
#  Drawing — View Dispatch
# ======================================================================

def _draw_accretion(self, max_y, max_x):
    """Draw the accretion simulation — dispatch to active view."""
    if self.accretion_view == "disk":
        _draw_disk_view(self, max_y, max_x)
    elif self.accretion_view == "cross":
        _draw_cross_view(self, max_y, max_x)
    elif self.accretion_view == "graphs":
        _draw_graphs_view(self, max_y, max_x)


# ======================================================================
#  Drawing — Top-Down Disk View
# ======================================================================

def _draw_disk_view(self, max_y, max_x):
    """Top-down view of protoplanetary disk with bodies and density."""
    self.stdscr.erase()
    rows = min(self.accretion_rows, max_y - 2)
    cols = min(self.accretion_cols, max_x)
    if rows < 5 or cols < 10:
        return

    buf = [[' '] * cols for _ in range(rows)]
    cbuf = [[0] * cols for _ in range(rows)]

    # Background stars
    for sr, sc in self.accretion_bg_stars:
        if 0 <= sr < rows and 0 <= sc < cols:
            buf[sr][sc] = '.'
            cbuf[sr][sc] = 8

    cx = cols / 2.0
    cy = rows / 2.0
    half = min(rows / 2.0 - 2, cols / 4.0 - 2)
    max_au = _DISK_OUTER_AU / self.accretion_zoom
    scale = half / max_au

    # Draw frost line circle
    frost_r_screen = _FROST_LINE_AU * scale
    steps = max(60, int(frost_r_screen * 6))
    for s in range(steps):
        theta = 2 * math.pi * s / steps
        sc_p = int(round(cx + frost_r_screen * math.cos(theta)))
        sr_p = int(round(cy + frost_r_screen * math.sin(theta) * 0.5))
        if 0 <= sr_p < rows and 0 <= sc_p < cols and buf[sr_p][sc_p] == ' ':
            buf[sr_p][sc_p] = '·'
            cbuf[sr_p][sc_p] = 6  # cyan for frost line

    # Draw disk dust as faint background density
    if self.accretion_gas_remaining > 0.01:
        for d in self.accretion_dust:
            x = d["a"] * math.cos(d["angle"])
            y = d["a"] * math.sin(d["angle"])
            sc_p = int(round(cx + x * scale))
            sr_p = int(round(cy + y * scale * 0.5))
            if 0 <= sr_p < rows and 0 <= sc_p < cols:
                if buf[sr_p][sc_p] == ' ':
                    buf[sr_p][sc_p] = '·' if d["icy"] else ','
                    cbuf[sr_p][sc_p] = 4 if d["icy"] else 7  # blue for icy, white for rocky

    # Draw orbit paths for significant bodies
    if self.accretion_show_orbits:
        for b in self.accretion_bodies:
            if b["mass"] < 2.0:
                continue
            a_screen = b["a"] * scale
            if a_screen < 1 or a_screen > half * 2:
                continue
            orbit_steps = max(30, int(a_screen * 4))
            for s in range(0, orbit_steps, 2):
                theta = 2 * math.pi * s / orbit_steps
                ecc = b["ecc"]
                r = b["a"] * (1 - ecc ** 2) / max(1 + ecc * math.cos(theta), 0.01)
                ox = r * math.cos(theta)
                oy = r * math.sin(theta)
                osc = int(round(cx + ox * scale))
                osr = int(round(cy + oy * scale * 0.5))
                if 0 <= osr < rows and 0 <= osc < cols and buf[osr][osc] == ' ':
                    buf[osr][osc] = '·'
                    cbuf[osr][osc] = 8

    # Draw central star
    sun_c = int(round(cx))
    sun_r = int(round(cy))
    for ch, dr, dc in [('@', 0, 0), ('*', 0, -1), ('*', 0, 1), ('*', -1, 0), ('*', 1, 0)]:
        sr_p = sun_r + dr
        sc_p = sun_c + dc
        if 0 <= sr_p < rows and 0 <= sc_p < cols:
            buf[sr_p][sc_p] = ch
            cbuf[sr_p][sc_p] = 3  # yellow

    # Draw bodies
    for bi, b in enumerate(self.accretion_bodies):
        x = b["a"] * math.cos(b["angle"])
        y = b["a"] * math.sin(b["angle"])
        sc_p = int(round(cx + x * scale))
        sr_p = int(round(cy + y * scale * 0.5))
        if 0 <= sr_p < rows and 0 <= sc_p < cols:
            # Size/char based on mass
            if b["mass"] > 100:
                ch = 'O'
            elif b["mass"] > 30:
                ch = 'O'
            elif b["mass"] > 10:
                ch = 'o'
            elif b["mass"] > 3:
                ch = '*'
            elif b["mass"] > 1:
                ch = '+'
            else:
                ch = '.'
            if bi == self.accretion_selected:
                ch = '#'
            buf[sr_p][sc_p] = ch
            # Color based on composition
            if b["composition"] == "gas_giant":
                cbuf[sr_p][sc_p] = 3  # yellow
            elif b["composition"] == "icy":
                cbuf[sr_p][sc_p] = 6  # cyan
            else:
                cbuf[sr_p][sc_p] = 1  # red for rocky
            if b.get("color"):
                cbuf[sr_p][sc_p] = b["color"]

            # Label
            if self.accretion_show_labels and b["name"] and sc_p + 2 < cols:
                label = b["name"][:8]
                for li, lc in enumerate(label):
                    if sc_p + 2 + li < cols:
                        buf[sr_p][sc_p + 2 + li] = lc
                        cbuf[sr_p][sc_p + 2 + li] = cbuf[sr_p][sc_p]

    # Render buffer to screen
    _render_buf(self, buf, cbuf, rows, cols)

    # Info panel for selected body
    if 0 <= self.accretion_selected < len(self.accretion_bodies):
        b = self.accretion_bodies[self.accretion_selected]
        info = [
            f" {b['name'] or 'Body'} ",
            f" mass={b['mass']:.1f}  a={b['a']:.2f} AU",
            f" ecc={b['ecc']:.3f}  type={b['composition']}",
            f" moons={b['moons']}  age={b['age']}",
        ]
        if b["resonance"]:
            info.append(f" resonance={b['resonance']}")
        iy = 1
        for il in info:
            if iy < rows - 3:
                try:
                    self.stdscr.addstr(iy, 1, il[:max_x - 3], curses.A_REVERSE)
                except curses.error:
                    pass
                iy += 1

    # Status bar
    status_y = min(rows, max_y - 2)
    n_bodies = len(self.accretion_bodies)
    n_dust = len(self.accretion_dust)
    status = (f" Gen:{self.accretion_generation} | {self.accretion_preset_name} | "
              f"t={self.accretion_time:.2f} Myr | bodies={n_bodies} dust={n_dust} | "
              f"gas={self.accretion_gas_remaining:.1%} | "
              f"speed={self.accretion_speed_scale:.1f}x zoom={self.accretion_zoom:.1f}x ")
    try:
        self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass
    hint = " Space=play n=step v=view z/Z=zoom o=orbits l=labels Tab=select +/-=speed r=reset m=menu q=exit"
    try:
        self.stdscr.addstr(status_y + 1, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


# ======================================================================
#  Drawing — Cross-Section View
# ======================================================================

def _draw_cross_view(self, max_y, max_x):
    """Cross-section showing disk thickness, temperature, frost line."""
    self.stdscr.erase()
    rows = min(self.accretion_rows, max_y - 2)
    cols = min(self.accretion_cols, max_x)
    if rows < 5 or cols < 10:
        return

    buf = [[' '] * cols for _ in range(rows)]
    cbuf = [[0] * cols for _ in range(rows)]

    mid_y = rows // 2
    max_au = _DISK_OUTER_AU / self.accretion_zoom
    au_per_col = max_au / max(cols - 4, 1)

    # Temperature profile: T ~ r^(-0.5), hotter near star
    # Disk thickness: H ~ r^(1.25), thicker farther out but thins as gas depletes
    gas_factor = self.accretion_gas_remaining

    # Draw disk cross-section
    for c in range(2, cols - 2):
        r_au = (c - 2) * au_per_col + 0.1
        # Temperature: hot near star, cool far out
        temp = min(1.0, 2.0 / max(r_au, 0.3) ** 0.5)
        # Disk half-thickness in rows
        thickness = min(mid_y - 1, int(3 + r_au ** 0.8 * 1.5 * gas_factor * self.accretion_zoom))

        for dr in range(-thickness, thickness + 1):
            sr = mid_y + dr
            if 0 <= sr < rows:
                # Density falls off from midplane
                dens = 1.0 - abs(dr) / max(thickness, 1)
                dens *= gas_factor
                if dens > 0.6:
                    ch = '#'
                elif dens > 0.3:
                    ch = '='
                elif dens > 0.1:
                    ch = '-'
                else:
                    ch = '.'

                # Color by temperature
                if temp > 0.7:
                    color = 1  # red (hot)
                elif temp > 0.4:
                    color = 3  # yellow (warm)
                elif r_au < _FROST_LINE_AU:
                    color = 7  # white (temperate)
                else:
                    color = 4  # blue (cold, beyond frost line)

                if buf[sr][c] == ' ':
                    buf[sr][c] = ch
                    cbuf[sr][c] = color

        # Frost line marker
        if abs(r_au - _FROST_LINE_AU) < au_per_col * 1.5:
            for sr in range(0, rows):
                if buf[sr][c] == ' ':
                    buf[sr][c] = '|'
                    cbuf[sr][c] = 6

    # Draw star at left edge
    for dr in range(-1, 2):
        sr = mid_y + dr
        if 0 <= sr < rows:
            buf[sr][1] = '@'
            cbuf[sr][1] = 3

    # Draw bodies as dots in cross-section (projected by semi-major axis)
    for b in self.accretion_bodies:
        c = int(2 + b["a"] / au_per_col)
        # Vertical scatter from eccentricity
        scatter = int(b["ecc"] * 5)
        sr = mid_y + random.randint(-scatter, scatter)
        if 0 <= sr < rows and 0 <= c < cols:
            if b["mass"] > 30:
                ch = 'O'
            elif b["mass"] > 5:
                ch = 'o'
            elif b["mass"] > 1:
                ch = '*'
            else:
                ch = '.'
            buf[sr][c] = ch
            if b["composition"] == "gas_giant":
                cbuf[sr][c] = 3
            elif b["composition"] == "icy":
                cbuf[sr][c] = 6
            else:
                cbuf[sr][c] = 1

    # Axis labels
    try:
        self.stdscr.addstr(0, 2, "Star", curses.A_BOLD | curses.color_pair(3))
        frost_col = int(2 + _FROST_LINE_AU / au_per_col)
        if frost_col < cols - 10:
            self.stdscr.addstr(0, frost_col, "Frost Line", curses.color_pair(6))
        self.stdscr.addstr(0, cols - 15, f"← {max_au:.0f} AU →", curses.A_DIM)
        self.stdscr.addstr(mid_y, cols - 10, "midplane", curses.A_DIM)
    except curses.error:
        pass

    # Render
    _render_buf(self, buf, cbuf, rows, cols)

    # Status bar
    status_y = min(rows, max_y - 2)
    status = (f" Gen:{self.accretion_generation} | Cross-Section | "
              f"gas={self.accretion_gas_remaining:.1%} | frost={_FROST_LINE_AU} AU | "
              f"bodies={len(self.accretion_bodies)} ")
    try:
        self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass
    hint = " v=view  Space=play  n=step  z/Z=zoom  +/-=speed  m=menu  q=exit"
    try:
        self.stdscr.addstr(status_y + 1, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


# ======================================================================
#  Drawing — Sparkline Graphs View
# ======================================================================

def _draw_graphs_view(self, max_y, max_x):
    """Time-series sparkline graphs for 10 metrics."""
    self.stdscr.erase()
    h = self.accretion_history
    metrics = [
        ("Planets", "planet_count", 2),
        ("Largest Mass", "largest_mass", 3),
        ("Disk Mass", "disk_mass", 4),
        ("Mean Ecc", "mean_ecc", 6),
        ("Collisions/tick", "collision_rate", 1),
        ("Total Mass", "total_mass", 7),
        ("Gas Giants", "gas_giants", 3),
        ("Rocky Planets", "rocky_count", 1),
        ("Mean SMA (AU)", "mean_a", 2),
        ("Moon Count", "moon_count", 5),
    ]

    spark_chars = " ▁▂▃▄▅▆▇█"
    y = 1
    graph_width = min(max_x - 22, 80)

    try:
        title = f"═══ Accretion Metrics — Gen {self.accretion_generation} ═══"
        self.stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(3))
    except curses.error:
        pass

    for label, key, color in metrics:
        if y >= max_y - 3:
            break
        data = h.get(key, [])
        if not data:
            y += 2
            continue
        # Build sparkline
        visible = data[-graph_width:]
        lo = min(visible) if visible else 0
        hi = max(visible) if visible else 1
        rng = hi - lo if hi > lo else 1
        spark = ""
        for val in visible:
            idx = int((val - lo) / rng * (len(spark_chars) - 1))
            idx = max(0, min(len(spark_chars) - 1, idx))
            spark += spark_chars[idx]

        cur_val = data[-1] if data else 0
        try:
            self.stdscr.addstr(y, 1, f"{label:>16s}", curses.A_BOLD)
            self.stdscr.addstr(y, 18, f" {cur_val:>8.1f} ", curses.color_pair(color))
        except curses.error:
            pass
        try:
            self.stdscr.addstr(y + 1, 18, spark[:graph_width], curses.color_pair(color))
        except curses.error:
            pass
        y += 2

    # Status bar
    status_y = min(max_y - 2, y + 1)
    try:
        hint = " v=view  Space=play  n=step  +/-=speed  m=menu  q=exit"
        self.stdscr.addstr(status_y, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


# ======================================================================
#  Rendering helper
# ======================================================================

def _render_buf(self, buf, cbuf, rows, cols):
    """Render character+color buffers to curses screen."""
    for r in range(rows):
        line = ''.join(buf[r])
        try:
            self.stdscr.addstr(r, 0, line[:cols])
        except curses.error:
            pass
        c = 0
        while c < cols:
            cp = cbuf[r][c]
            if cp != 0:
                run = 1
                while c + run < cols and cbuf[r][c + run] == cp:
                    run += 1
                try:
                    pair = cp if cp <= 7 else 0
                    attr = curses.color_pair(pair)
                    if cp == 8:
                        attr = curses.A_DIM
                    if cp == 3:
                        attr |= curses.A_BOLD
                    self.stdscr.chgat(r, c, run, attr)
                except curses.error:
                    pass
                c += run
            else:
                c += 1


# ======================================================================
#  Registration
# ======================================================================

def register(App):
    """Register accretion mode methods on the App class."""
    App._enter_accretion_mode = _enter_accretion_mode
    App._exit_accretion_mode = _exit_accretion_mode
    App._accretion_init = _accretion_init
    App._accretion_to_screen = _accretion_to_screen
    App._accretion_step = _accretion_step
    App._handle_accretion_menu_key = _handle_accretion_menu_key
    App._handle_accretion_key = _handle_accretion_key
    App._draw_accretion_menu = _draw_accretion_menu
    App._draw_accretion = _draw_accretion
