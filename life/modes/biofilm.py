"""Mode: biofilm — Bacterial Quorum Sensing & Biofilm Formation.

Bacteria swim freely as planktonic individuals at low density.  As population
grows they secrete and detect autoinducer (AI) signaling molecules — when local
concentration crosses a threshold each bacterium switches phenotype: stops
swimming, secretes extracellular polymeric substance (EPS), and assembles into
a structured biofilm with water channels, nutrient gradients, and persister
cells.

Three views:
  1) Spatial biofilm cross-section — EPS matrix, water channels, cell types
     (planktonic / biofilm / persister), nutrient & oxygen shading
  2) Autoinducer concentration heatmap — diffusible QS signal field
  3) Time-series sparkline graphs — 10 metrics

Six presets:
  Wound Infection, Dental Plaque, Catheter Colonization,
  Quorum Quenching Therapy, Nutrient-Rich Bloom, Antibiotic Pulse
"""
import curses
import math
import random


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

BIOFILM_PRESETS = [
    ("Wound Infection",
     "Bacteria colonize a wound surface — biofilm forms on tissue, resists immune clearance",
     "wound"),
    ("Dental Plaque",
     "Oral bacteria attach to tooth surface — layered multispecies biofilm with acid gradients",
     "dental"),
    ("Catheter Colonization",
     "Medical device surface — rapid biofilm formation in nutrient-rich fluid flow",
     "catheter"),
    ("Quorum Quenching Therapy",
     "Enzyme degrades autoinducers — bacteria cannot coordinate, biofilm formation blocked",
     "quench"),
    ("Nutrient-Rich Bloom",
     "Abundant nutrients drive explosive planktonic growth then sudden biofilm transition",
     "bloom"),
    ("Antibiotic Pulse",
     "Established biofilm challenged by antibiotic wash — planktonic cells die, biofilm persists",
     "antibiotic"),
]


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

_NEIGHBORS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]

# Autoinducer (AI)
_AI_SECRETE_RATE = 0.008     # per bacterium per tick
_AI_DIFFUSE = 0.15           # diffusion coefficient
_AI_DECAY = 0.003            # natural decay
_AI_THRESHOLD = 0.25         # intracellular threshold to switch phenotype
_AI_UPTAKE = 0.02            # intracellular accumulation rate from environment

# Quorum quenching
_QQ_DEGRADE_RATE = 0.06      # AI degradation per tick when enzyme present

# Nutrients
_NUTRIENT_DIFFUSE = 0.10
_NUTRIENT_CONSUME_PLANK = 0.012
_NUTRIENT_CONSUME_BIOFILM = 0.008
_NUTRIENT_REPLENISH = 0.02   # from bulk fluid (top of domain)
_NUTRIENT_CHANNEL_BOOST = 0.015  # extra delivery through water channels

# Oxygen
_O2_DIFFUSE = 0.12
_O2_CONSUME = 0.010
_O2_SURFACE = 1.0            # oxygen at bulk fluid surface

# EPS (extracellular polymeric substance)
_EPS_SECRETE_RATE = 0.015
_EPS_DIFFUSE = 0.03
_EPS_MAX = 1.0

# Biofilm architecture
_CHANNEL_PROB = 0.004        # probability of water channel forming
_TOWER_GROW_PROB = 0.02      # probability of mushroom tower extension

# Persister cells
_PERSISTER_O2_THRESH = 0.15  # low O2 triggers persister phenotype
_PERSISTER_NUTRIENT_THRESH = 0.10
_PERSISTER_PROB = 0.02       # probability of switching to persister

# Antibiotic
_ANTIBIOTIC_KILL_PLANK = 0.15   # kill probability per tick for planktonic
_ANTIBIOTIC_PENETRATE = 0.02    # diffusion through biofilm per tick
_ANTIBIOTIC_KILL_BIOFILM = 0.001  # kill probability per tick for biofilm cells
_ANTIBIOTIC_KILL_PERSISTER = 0.0002  # persisters nearly immune
_ANTIBIOTIC_DECAY = 0.005

# Bacteria
_DIVIDE_NUTRIENT_THRESH = 0.3
_DIVIDE_PROB = 0.03
_SWIM_SPEED = 1.0
_CHEMOTAXIS_STRENGTH = 0.7
_MAX_BACTERIA = 800
_DETACH_PROB = 0.002         # biofilm cell detaches back to planktonic


# ══════════════════════════════════════════════════════════════════════
#  Data classes
# ══════════════════════════════════════════════════════════════════════

class _Bacterium:
    """A single bacterial cell."""
    __slots__ = ('r', 'c', 'vr', 'vc', 'phenotype', 'ai_internal',
                 'energy', 'age', 'eps_produced')

    def __init__(self, r, c, phenotype='planktonic'):
        self.r = r
        self.c = c
        self.vr = random.uniform(-1, 1)
        self.vc = random.uniform(-1, 1)
        self.phenotype = phenotype  # planktonic | biofilm | persister
        self.ai_internal = 0.0
        self.energy = 0.5 + random.random() * 0.5
        self.age = 0
        self.eps_produced = 0.0


# ══════════════════════════════════════════════════════════════════════
#  Enter / Exit
# ══════════════════════════════════════════════════════════════════════

def _enter_biofilm_mode(self):
    """Enter biofilm mode — show preset menu."""
    self.biofilm_mode = True
    self.biofilm_menu = True
    self.biofilm_menu_sel = 0


def _exit_biofilm_mode(self):
    """Exit biofilm mode."""
    self.biofilm_mode = False
    self.biofilm_menu = False
    self.biofilm_running = False
    for attr in list(vars(self)):
        if attr.startswith('biofilm_') and attr not in ('biofilm_mode',):
            try:
                delattr(self, attr)
            except AttributeError:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _biofilm_init(self, preset_idx: int):
    """Initialize simulation for the chosen preset."""
    name, _desc, pid = BIOFILM_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(20, max_x - 2)

    self.biofilm_menu = False
    self.biofilm_running = False
    self.biofilm_preset_name = name
    self.biofilm_preset_id = pid
    self.biofilm_rows = rows
    self.biofilm_cols = cols
    self.biofilm_generation = 0
    self.biofilm_speed = 1
    self.biofilm_view = "spatial"  # spatial | heatmap | graphs

    # Scalar fields  (row 0 = top/bulk fluid, row max = surface/substrate)
    self.biofilm_nutrients = [[0.5] * cols for _ in range(rows)]
    self.biofilm_oxygen = [[0.5] * cols for _ in range(rows)]
    self.biofilm_ai = [[0.0] * cols for _ in range(rows)]       # autoinducer
    self.biofilm_eps = [[0.0] * cols for _ in range(rows)]       # EPS matrix
    self.biofilm_antibiotic = [[0.0] * cols for _ in range(rows)]
    self.biofilm_channels = [[False] * cols for _ in range(rows)] # water channels

    # Bacteria
    self.biofilm_bacteria = []

    # Toggles
    self.biofilm_antibiotic_active = False
    self.biofilm_qq_active = False  # quorum quenching

    # History for sparklines
    self.biofilm_history = {
        'population': [],
        'planktonic': [],
        'biofilm_cells': [],
        'persister': [],
        'avg_ai': [],
        'eps_coverage': [],
        'nutrient_avg': [],
        'o2_avg': [],
        'antibiotic_avg': [],
        'biofilm_height': [],
    }

    # Set up initial conditions per preset
    _biofilm_setup_preset(self, pid, rows, cols)
    self._flash(f"Biofilm: {name}")


def _biofilm_setup_preset(self, pid, rows, cols):
    """Configure initial conditions per preset."""
    # Surface/substrate is at the bottom rows; bulk fluid is at top
    # Nutrient-rich fluid at top
    for r in range(rows):
        depth_frac = r / max(1, rows - 1)  # 0 at top, 1 at bottom
        for c in range(cols):
            self.biofilm_nutrients[r][c] = max(0.1, 1.0 - depth_frac * 0.3)
            self.biofilm_oxygen[r][c] = max(0.1, 1.0 - depth_frac * 0.2)

    if pid == "wound":
        # Moderate bacteria on wound surface (bottom)
        for _ in range(40):
            r = rows - 1 - random.randint(0, rows // 6)
            c = random.randint(2, cols - 3)
            self.biofilm_bacteria.append(_Bacterium(r, c))
        # Some planktonic in fluid
        for _ in range(20):
            r = random.randint(0, rows // 2)
            c = random.randint(2, cols - 3)
            self.biofilm_bacteria.append(_Bacterium(r, c))

    elif pid == "dental":
        # Bacteria attach to tooth surface (bottom row) in clumps
        for cluster in range(5):
            cc = random.randint(cols // 6, 5 * cols // 6)
            for _ in range(12):
                r = rows - 1 - random.randint(0, 2)
                c = cc + random.randint(-3, 3)
                c = max(1, min(cols - 2, c))
                b = _Bacterium(r, c)
                b.ai_internal = random.uniform(0.1, 0.2)
                self.biofilm_bacteria.append(b)

    elif pid == "catheter":
        # Nutrient-rich environment, bacteria colonizing surface
        for r in range(rows):
            for c in range(cols):
                self.biofilm_nutrients[r][c] = min(1.0,
                    self.biofilm_nutrients[r][c] * 1.5)
        for _ in range(50):
            r = rows - 1 - random.randint(0, rows // 8)
            c = random.randint(1, cols - 2)
            self.biofilm_bacteria.append(_Bacterium(r, c))
        for _ in range(30):
            r = random.randint(0, rows // 3)
            c = random.randint(1, cols - 2)
            self.biofilm_bacteria.append(_Bacterium(r, c))

    elif pid == "quench":
        # Same as wound but quorum quenching enzyme active
        for _ in range(50):
            r = rows - 1 - random.randint(0, rows // 5)
            c = random.randint(2, cols - 3)
            b = _Bacterium(r, c)
            b.ai_internal = random.uniform(0.0, 0.15)
            self.biofilm_bacteria.append(b)
        for _ in range(30):
            r = random.randint(0, rows // 2)
            c = random.randint(2, cols - 3)
            self.biofilm_bacteria.append(_Bacterium(r, c))
        self.biofilm_qq_active = True

    elif pid == "bloom":
        # Very high nutrients, few initial bacteria
        for r in range(rows):
            for c in range(cols):
                self.biofilm_nutrients[r][c] = 1.0
                self.biofilm_oxygen[r][c] = 0.9
        for _ in range(15):
            r = random.randint(rows // 4, 3 * rows // 4)
            c = random.randint(cols // 4, 3 * cols // 4)
            self.biofilm_bacteria.append(_Bacterium(r, c))

    elif pid == "antibiotic":
        # Pre-established biofilm, then antibiotic challenge starts
        # Build a biofilm at bottom
        for _ in range(80):
            r = rows - 1 - random.randint(0, rows // 4)
            c = random.randint(cols // 6, 5 * cols // 6)
            b = _Bacterium(r, c, phenotype='biofilm')
            b.ai_internal = 0.5
            b.energy = 0.8
            self.biofilm_bacteria.append(b)
        # EPS around biofilm cells
        for b in self.biofilm_bacteria:
            ri, ci = int(b.r), int(b.c)
            if 0 <= ri < rows and 0 <= ci < cols:
                self.biofilm_eps[ri][ci] = min(_EPS_MAX,
                    self.biofilm_eps[ri][ci] + 0.3)
                for dr, dc in _NEIGHBORS_4:
                    nr, nc = ri + dr, ci + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        self.biofilm_eps[nr][nc] = min(_EPS_MAX,
                            self.biofilm_eps[nr][nc] + 0.1)
        # Some planktonic
        for _ in range(25):
            r = random.randint(0, rows // 3)
            c = random.randint(1, cols - 2)
            self.biofilm_bacteria.append(_Bacterium(r, c))
        # Antibiotic starts after a short delay (will be toggled)
        self.biofilm_antibiotic_active = True
        # Seed antibiotic from top
        for c in range(cols):
            self.biofilm_antibiotic[0][c] = 0.8


# ══════════════════════════════════════════════════════════════════════
#  Simulation Step
# ══════════════════════════════════════════════════════════════════════

def _biofilm_step(self):
    """Advance one tick of the biofilm simulation."""
    rows = self.biofilm_rows
    cols = self.biofilm_cols

    for _ in range(self.biofilm_speed):
        self.biofilm_generation += 1
        bacteria = self.biofilm_bacteria

        # ── 1. Nutrient & oxygen replenishment from bulk fluid (top) ──
        for c in range(cols):
            self.biofilm_nutrients[0][c] = min(1.0,
                self.biofilm_nutrients[0][c] + _NUTRIENT_REPLENISH)
            self.biofilm_oxygen[0][c] = min(1.0,
                self.biofilm_oxygen[0][c] + _NUTRIENT_REPLENISH * 1.5)

        # ── 2. Diffuse nutrients, oxygen, autoinducer, antibiotic ──
        _diffuse_field(self.biofilm_nutrients, rows, cols, _NUTRIENT_DIFFUSE,
                       self.biofilm_channels, _NUTRIENT_CHANNEL_BOOST)
        _diffuse_field(self.biofilm_oxygen, rows, cols, _O2_DIFFUSE,
                       self.biofilm_channels, _NUTRIENT_CHANNEL_BOOST)
        _diffuse_field(self.biofilm_ai, rows, cols, _AI_DIFFUSE, None, 0)
        if self.biofilm_antibiotic_active:
            _diffuse_field_with_eps(self.biofilm_antibiotic, self.biofilm_eps,
                                    rows, cols, _ANTIBIOTIC_PENETRATE)

        # ── 3. AI decay (and quorum quenching) ──
        qq_active = self.biofilm_qq_active
        for r in range(rows):
            for c in range(cols):
                self.biofilm_ai[r][c] -= _AI_DECAY
                if qq_active:
                    self.biofilm_ai[r][c] -= _QQ_DEGRADE_RATE
                if self.biofilm_ai[r][c] < 0:
                    self.biofilm_ai[r][c] = 0.0

        # ── 4. Antibiotic source & decay ──
        if self.biofilm_antibiotic_active:
            for c in range(cols):
                self.biofilm_antibiotic[0][c] = min(1.0,
                    self.biofilm_antibiotic[0][c] + 0.03)
            for r in range(rows):
                for c in range(cols):
                    self.biofilm_antibiotic[r][c] = max(0.0,
                        self.biofilm_antibiotic[r][c] - _ANTIBIOTIC_DECAY)

        # ── 5. EPS diffusion (slow spread) ──
        _diffuse_field(self.biofilm_eps, rows, cols, _EPS_DIFFUSE, None, 0)

        # ── 6. Bacterial behavior ──
        new_bacteria = []
        dead_count = 0

        for b in bacteria:
            b.age += 1
            ri, ci = int(b.r), int(b.c)
            ri = max(0, min(rows - 1, ri))
            ci = max(0, min(cols - 1, ci))

            # Local environment
            local_nutrient = self.biofilm_nutrients[ri][ci]
            local_o2 = self.biofilm_oxygen[ri][ci]
            local_ai = self.biofilm_ai[ri][ci]
            local_abx = self.biofilm_antibiotic[ri][ci]
            local_eps = self.biofilm_eps[ri][ci]

            # Consume nutrients and oxygen
            if b.phenotype == 'planktonic':
                consume = _NUTRIENT_CONSUME_PLANK
            else:
                consume = _NUTRIENT_CONSUME_BIOFILM
            self.biofilm_nutrients[ri][ci] = max(0.0,
                local_nutrient - consume)
            self.biofilm_oxygen[ri][ci] = max(0.0, local_o2 - _O2_CONSUME)

            # Energy from nutrients
            b.energy += local_nutrient * 0.02
            b.energy = min(1.5, b.energy)
            b.energy -= 0.005  # basal metabolism

            # Secrete autoinducer
            self.biofilm_ai[ri][ci] = min(1.0,
                self.biofilm_ai[ri][ci] + _AI_SECRETE_RATE)

            # Uptake AI into intracellular pool
            b.ai_internal += _AI_UPTAKE * local_ai
            b.ai_internal *= 0.98  # intracellular decay

            # ── Phenotype switching ──
            if b.phenotype == 'planktonic':
                # Check quorum sensing threshold
                if b.ai_internal >= _AI_THRESHOLD and not qq_active:
                    # Switch to biofilm phenotype — attach!
                    b.phenotype = 'biofilm'
                    b.vr = 0.0
                    b.vc = 0.0

                # Chemotaxis toward nutrients
                best_n = local_nutrient
                best_dr, best_dc = 0.0, 0.0
                for dr, dc in _NEIGHBORS_8:
                    nr, nc = ri + dr, ci + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        n_val = self.biofilm_nutrients[nr][nc]
                        if n_val > best_n:
                            best_n = n_val
                            best_dr, best_dc = dr, dc

                if best_dr != 0 or best_dc != 0:
                    b.vr = b.vr * (1 - _CHEMOTAXIS_STRENGTH) + best_dr * _CHEMOTAXIS_STRENGTH
                    b.vc = b.vc * (1 - _CHEMOTAXIS_STRENGTH) + best_dc * _CHEMOTAXIS_STRENGTH
                else:
                    b.vr += random.uniform(-0.3, 0.3)
                    b.vc += random.uniform(-0.3, 0.3)

                # Normalize speed
                spd = math.hypot(b.vr, b.vc)
                if spd > _SWIM_SPEED:
                    b.vr = b.vr / spd * _SWIM_SPEED
                    b.vc = b.vc / spd * _SWIM_SPEED

                # Move
                b.r += b.vr
                b.c += b.vc
                b.r = max(0, min(rows - 1, b.r))
                b.c = max(0, min(cols - 1, b.c))

            elif b.phenotype == 'biofilm':
                # Secrete EPS
                self.biofilm_eps[ri][ci] = min(_EPS_MAX,
                    self.biofilm_eps[ri][ci] + _EPS_SECRETE_RATE)
                b.eps_produced += _EPS_SECRETE_RATE

                # Check for persister transition (low O2 / nutrients)
                if (local_o2 < _PERSISTER_O2_THRESH or
                        local_nutrient < _PERSISTER_NUTRIENT_THRESH):
                    if random.random() < _PERSISTER_PROB:
                        b.phenotype = 'persister'

                # Rare detachment back to planktonic
                if random.random() < _DETACH_PROB:
                    b.phenotype = 'planktonic'
                    b.vr = random.uniform(-0.5, 0.5)
                    b.vc = random.uniform(-0.5, -0.1)  # drift upward

            elif b.phenotype == 'persister':
                # Dormant — minimal metabolism
                b.energy -= 0.001  # very low
                # Can revert if conditions improve
                if local_o2 > 0.4 and local_nutrient > 0.4:
                    if random.random() < 0.01:
                        b.phenotype = 'biofilm'

            # ── Antibiotic killing ──
            if local_abx > 0.05:
                kill_prob = 0.0
                if b.phenotype == 'planktonic':
                    kill_prob = _ANTIBIOTIC_KILL_PLANK * local_abx
                elif b.phenotype == 'biofilm':
                    # EPS shields
                    shield = min(0.9, local_eps * 0.8)
                    kill_prob = _ANTIBIOTIC_KILL_BIOFILM * local_abx * (1 - shield)
                elif b.phenotype == 'persister':
                    kill_prob = _ANTIBIOTIC_KILL_PERSISTER * local_abx
                if random.random() < kill_prob:
                    b.energy = -1  # mark dead

            # ── Death from starvation ──
            if b.energy <= 0:
                dead_count += 1
                continue

            # ── Division ──
            if (b.energy > 0.8 and local_nutrient > _DIVIDE_NUTRIENT_THRESH
                    and random.random() < _DIVIDE_PROB
                    and len(bacteria) + len(new_bacteria) < _MAX_BACTERIA):
                # Daughter cell
                dr = random.uniform(-1, 1)
                dc = random.uniform(-1, 1)
                daughter = _Bacterium(
                    max(0, min(rows - 1, b.r + dr)),
                    max(0, min(cols - 1, b.c + dc)),
                    phenotype=b.phenotype
                )
                daughter.ai_internal = b.ai_internal * 0.5
                daughter.energy = b.energy * 0.5
                b.energy *= 0.5
                b.ai_internal *= 0.5
                new_bacteria.append(daughter)

            new_bacteria.append(b)

        self.biofilm_bacteria = new_bacteria

        # ── 7. Water channel formation ──
        # Channels form in gaps within biofilm where EPS is low
        for r in range(2, rows - 2):
            for c in range(2, cols - 2):
                if self.biofilm_eps[r][c] < 0.05:
                    # Check if surrounded by biofilm
                    eps_neighbors = sum(
                        1 for dr, dc in _NEIGHBORS_4
                        if 0 <= r + dr < rows and 0 <= c + dc < cols
                        and self.biofilm_eps[r + dr][c + dc] > 0.2
                    )
                    if eps_neighbors >= 3 and random.random() < _CHANNEL_PROB:
                        self.biofilm_channels[r][c] = True

        # ── 8. Mushroom tower growth ──
        # Biofilm cells at the top of biofilm clusters can grow upward
        for b in self.biofilm_bacteria:
            if b.phenotype != 'biofilm':
                continue
            ri, ci = int(b.r), int(b.c)
            if ri <= 0:
                continue
            # Check if cell is at top of a column of EPS
            if (self.biofilm_eps[ri][ci] > 0.3 and
                    ri > 0 and self.biofilm_eps[ri - 1][ci] < 0.1):
                if random.random() < _TOWER_GROW_PROB:
                    # Push cell upward slightly
                    b.r = max(0, b.r - 0.5)

        # ── 9. Record history ──
        hist = self.biofilm_history
        n_plank = sum(1 for b in self.biofilm_bacteria
                      if b.phenotype == 'planktonic')
        n_biofilm = sum(1 for b in self.biofilm_bacteria
                        if b.phenotype == 'biofilm')
        n_persister = sum(1 for b in self.biofilm_bacteria
                          if b.phenotype == 'persister')
        total_cells = rows * cols

        hist['population'].append(len(self.biofilm_bacteria))
        hist['planktonic'].append(n_plank)
        hist['biofilm_cells'].append(n_biofilm)
        hist['persister'].append(n_persister)

        ai_sum = sum(self.biofilm_ai[r][c]
                     for r in range(rows) for c in range(cols))
        hist['avg_ai'].append(ai_sum / total_cells)

        eps_count = sum(1 for r in range(rows) for c in range(cols)
                        if self.biofilm_eps[r][c] > 0.1)
        hist['eps_coverage'].append(eps_count / total_cells)

        nut_sum = sum(self.biofilm_nutrients[r][c]
                      for r in range(rows) for c in range(cols))
        hist['nutrient_avg'].append(nut_sum / total_cells)

        o2_sum = sum(self.biofilm_oxygen[r][c]
                     for r in range(rows) for c in range(cols))
        hist['o2_avg'].append(o2_sum / total_cells)

        abx_sum = sum(self.biofilm_antibiotic[r][c]
                      for r in range(rows) for c in range(cols))
        hist['antibiotic_avg'].append(abx_sum / total_cells)

        # Biofilm height: topmost row with EPS > 0.1
        max_height = 0
        for r in range(rows):
            for c in range(cols):
                if self.biofilm_eps[r][c] > 0.1:
                    max_height = max(max_height, rows - r)
                    break
            if max_height > 0:
                break
        hist['biofilm_height'].append(max_height)

        # Cap history
        for k in hist:
            if len(hist[k]) > 200:
                hist[k] = hist[k][-200:]


# ── Field diffusion helpers ──

def _diffuse_field(field, rows, cols, coeff, channels, channel_boost):
    """Diffuse a scalar field with optional channel boosting."""
    new = [row[:] for row in field]
    for r in range(rows):
        for c in range(cols):
            total = 0.0
            cnt = 0
            for dr, dc in _NEIGHBORS_4:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    total += field[nr][nc]
                    cnt += 1
            if cnt > 0:
                avg = total / cnt
                eff_coeff = coeff
                if channels and channels[r][c]:
                    eff_coeff += channel_boost
                new[r][c] += eff_coeff * (avg - new[r][c])
            new[r][c] = max(0.0, min(1.0, new[r][c]))
    # Copy back
    for r in range(rows):
        for c in range(cols):
            field[r][c] = new[r][c]


def _diffuse_field_with_eps(field, eps, rows, cols, base_coeff):
    """Diffuse antibiotic field; EPS slows penetration."""
    new = [row[:] for row in field]
    for r in range(rows):
        for c in range(cols):
            total = 0.0
            cnt = 0
            for dr, dc in _NEIGHBORS_4:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    total += field[nr][nc]
                    cnt += 1
            if cnt > 0:
                avg = total / cnt
                # EPS reduces diffusion dramatically
                eps_barrier = max(0.05, 1.0 - eps[r][c] * 0.9)
                eff_coeff = base_coeff * eps_barrier
                new[r][c] += eff_coeff * (avg - new[r][c])
            new[r][c] = max(0.0, min(1.0, new[r][c]))
    for r in range(rows):
        for c in range(cols):
            field[r][c] = new[r][c]


# ══════════════════════════════════════════════════════════════════════
#  Key Handlers
# ══════════════════════════════════════════════════════════════════════

def _handle_biofilm_menu_key(self, key: int) -> bool:
    """Handle key input in the preset selection menu."""
    n = len(BIOFILM_PRESETS)
    if key == ord("q") or key == 27:
        self.biofilm_mode = False
        self.biofilm_menu = False
        return True
    if key == curses.KEY_UP or key == ord("k"):
        self.biofilm_menu_sel = (self.biofilm_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.biofilm_menu_sel = (self.biofilm_menu_sel + 1) % n
        return True
    if key in (10, 13, curses.KEY_ENTER):
        _biofilm_init(self, self.biofilm_menu_sel)
        return True
    return True


def _handle_biofilm_key(self, key: int) -> bool:
    """Handle key input during live simulation."""
    if key == ord(" "):
        self.biofilm_running = not self.biofilm_running
        self._flash("Running" if self.biofilm_running else "Paused")
        return True

    if key == ord("n") or key == ord("."):
        _biofilm_step(self)
        return True

    if key == ord("v"):
        views = ["spatial", "heatmap", "graphs"]
        cur = views.index(self.biofilm_view) if self.biofilm_view in views else 0
        self.biofilm_view = views[(cur + 1) % len(views)]
        self._flash(f"View: {self.biofilm_view}")
        return True

    if key == ord("+") or key == ord("="):
        self.biofilm_speed = min(20, self.biofilm_speed + 1)
        self._flash(f"Speed: {self.biofilm_speed}x")
        return True

    if key == ord("-") or key == ord("_"):
        self.biofilm_speed = max(1, self.biofilm_speed - 1)
        self._flash(f"Speed: {self.biofilm_speed}x")
        return True

    if key == ord("a"):
        # Toggle antibiotic
        self.biofilm_antibiotic_active = not self.biofilm_antibiotic_active
        if not self.biofilm_antibiotic_active:
            # Clear antibiotic field
            for r in range(self.biofilm_rows):
                for c in range(self.biofilm_cols):
                    self.biofilm_antibiotic[r][c] = 0.0
        self._flash(f"Antibiotic: {'ON' if self.biofilm_antibiotic_active else 'OFF'}")
        return True

    if key == ord("q") and not self.biofilm_menu:
        # Back to menu on 'q' during sim if desired, but let's use 'Q'
        pass

    if key == ord("Q"):
        # Toggle quorum quenching
        self.biofilm_qq_active = not self.biofilm_qq_active
        self._flash(f"Quorum Quenching: {'ON' if self.biofilm_qq_active else 'OFF'}")
        return True

    if key == ord("r"):
        idx = next((i for i, p in enumerate(BIOFILM_PRESETS)
                     if p[0] == self.biofilm_preset_name), 0)
        _biofilm_init(self, idx)
        return True

    if key == ord("R") or key == ord("m"):
        self.biofilm_running = False
        self.biofilm_menu = True
        self.biofilm_menu_sel = 0
        return True

    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Menu
# ══════════════════════════════════════════════════════════════════════

def _draw_biofilm_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    self.stdscr.erase()

    title = "── Bacterial Quorum Sensing & Biofilm Formation ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title[:max_x - 1],
                           curses.A_BOLD)
    except curses.error:
        pass

    # Subtitle
    sub = "Bacteria sense density via autoinducers → collective biofilm phenotype switch"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(sub)) // 2), sub[:max_x - 1],
                           curses.A_DIM)
    except curses.error:
        pass

    y = 4
    for i, (name, desc, _pid) in enumerate(BIOFILM_PRESETS):
        if y + 2 >= max_y - 2:
            break
        sel = i == self.biofilm_menu_sel
        marker = "▸ " if sel else "  "
        attr = curses.A_REVERSE if sel else curses.A_NORMAL
        try:
            self.stdscr.addstr(y, 4, f"{marker}{name}"[:max_x - 5], attr | curses.A_BOLD)
            self.stdscr.addstr(y + 1, 8, desc[:max_x - 9], curses.A_DIM)
        except curses.error:
            pass
        y += 3

    # Controls
    controls = "↑/↓ select  ·  Enter start  ·  q quit"
    try:
        self.stdscr.addstr(max_y - 2, max(0, (max_x - len(controls)) // 2),
                           controls[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Live Simulation
# ══════════════════════════════════════════════════════════════════════

def _draw_biofilm(self, max_y: int, max_x: int):
    """Draw the active simulation."""
    self.stdscr.erase()
    view = self.biofilm_view

    if view == "spatial":
        _draw_biofilm_spatial(self, max_y, max_x)
    elif view == "heatmap":
        _draw_biofilm_heatmap(self, max_y, max_x)
    elif view == "graphs":
        _draw_biofilm_graphs(self, max_y, max_x)

    # Status bar
    n_bact = len(self.biofilm_bacteria)
    n_plank = sum(1 for b in self.biofilm_bacteria if b.phenotype == 'planktonic')
    n_bio = sum(1 for b in self.biofilm_bacteria if b.phenotype == 'biofilm')
    n_pers = sum(1 for b in self.biofilm_bacteria if b.phenotype == 'persister')

    status_parts = [
        f"Gen:{self.biofilm_generation}",
        f"Pop:{n_bact}",
        f"Plnk:{n_plank}",
        f"Bio:{n_bio}",
        f"Pers:{n_pers}",
        f"Spd:{self.biofilm_speed}x",
    ]
    if self.biofilm_antibiotic_active:
        status_parts.append("ABX:ON")
    if self.biofilm_qq_active:
        status_parts.append("QQ:ON")
    status_parts.append("▶" if self.biofilm_running else "⏸")

    status = "  ".join(status_parts)
    try:
        self.stdscr.addstr(max_y - 1, 0, status[:max_x - 1],
                           curses.A_BOLD)
    except curses.error:
        pass

    # Controls hint
    hint = "SP:⏯  v:view  a:antibiotic  Q:quorum-quench  +/-:speed  r:reset  m:menu"
    try:
        self.stdscr.addstr(0, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


def _draw_biofilm_spatial(self, max_y: int, max_x: int):
    """Draw spatial cross-section view: EPS, channels, bacteria by type."""
    rows = self.biofilm_rows
    cols = self.biofilm_cols
    draw_rows = min(rows, max_y - 3)
    draw_cols = min(cols, max_x - 1)

    # Build a character grid
    # Background: nutrient/oxygen gradient → dim shading
    for r in range(draw_rows):
        for c in range(draw_cols):
            eps_val = self.biofilm_eps[r][c]
            nut_val = self.biofilm_nutrients[r][c]
            o2_val = self.biofilm_oxygen[r][c]
            channel = self.biofilm_channels[r][c]
            abx_val = self.biofilm_antibiotic[r][c]

            ch = ' '
            attr = curses.A_DIM

            if channel:
                # Water channel — blue tilde
                ch = '~'
                try:
                    attr = curses.color_pair(4) | curses.A_BOLD  # blue
                except Exception:
                    attr = curses.A_BOLD
            elif eps_val > 0.5:
                # Dense EPS matrix
                ch = '▓'
                try:
                    attr = curses.color_pair(3)  # yellow/amber
                except Exception:
                    attr = curses.A_DIM
            elif eps_val > 0.2:
                ch = '░'
                try:
                    attr = curses.color_pair(3)
                except Exception:
                    attr = curses.A_DIM
            elif eps_val > 0.05:
                ch = '·'
                try:
                    attr = curses.color_pair(3) | curses.A_DIM
                except Exception:
                    attr = curses.A_DIM
            else:
                # Bulk fluid — shaded by nutrient level
                if nut_val > 0.6:
                    ch = ' '
                elif nut_val > 0.3:
                    ch = '·'
                    attr = curses.A_DIM
                else:
                    ch = '·'
                    try:
                        attr = curses.color_pair(1) | curses.A_DIM  # red = depleted
                    except Exception:
                        attr = curses.A_DIM

            # Antibiotic overlay
            if abx_val > 0.3:
                if ch == ' ':
                    ch = '×'
                try:
                    attr = curses.color_pair(5) | curses.A_BOLD  # magenta
                except Exception:
                    pass

            try:
                self.stdscr.addch(r + 1, c, ord(ch), attr)
            except curses.error:
                pass

    # Draw bacteria on top
    for b in self.biofilm_bacteria:
        br, bc = int(b.r), int(b.c)
        if br < 0 or br >= draw_rows or bc < 0 or bc >= draw_cols:
            continue

        if b.phenotype == 'planktonic':
            ch = 'o'
            try:
                attr = curses.color_pair(2) | curses.A_BOLD  # green
            except Exception:
                attr = curses.A_BOLD
        elif b.phenotype == 'biofilm':
            ch = '●'
            try:
                attr = curses.color_pair(3) | curses.A_BOLD  # yellow
            except Exception:
                attr = curses.A_BOLD
        elif b.phenotype == 'persister':
            ch = '◆'
            try:
                attr = curses.color_pair(6) | curses.A_BOLD  # cyan
            except Exception:
                attr = curses.A_BOLD
        else:
            ch = '?'
            attr = curses.A_NORMAL

        try:
            self.stdscr.addstr(br + 1, bc, ch, attr)
        except curses.error:
            pass

    # Surface label at bottom
    surf_label = "═══ SUBSTRATE ═══"
    try:
        sx = max(0, (draw_cols - len(surf_label)) // 2)
        self.stdscr.addstr(min(draw_rows, max_y - 3), sx,
                           surf_label[:draw_cols], curses.A_DIM)
    except curses.error:
        pass

    # Fluid label at top area
    fluid_label = "~~~ BULK FLUID ~~~"
    try:
        fx = max(0, (draw_cols - len(fluid_label)) // 2)
        self.stdscr.addstr(1, fx, fluid_label[:draw_cols],
                           curses.color_pair(4) | curses.A_DIM)
    except curses.error:
        pass


def _draw_biofilm_heatmap(self, max_y: int, max_x: int):
    """Draw autoinducer concentration heatmap with nutrient/O2 split."""
    rows = self.biofilm_rows
    cols = self.biofilm_cols
    draw_rows = min(rows, max_y - 3)
    # Split screen: left = autoinducer, right = nutrient
    half = min(cols, max_x - 1) // 2

    heat_chars = " ·∙░▒▓█"
    n_chars = len(heat_chars)

    # Left: autoinducer
    try:
        self.stdscr.addstr(1, max(0, half // 2 - 6), "AUTOINDUCER (AI)",
                           curses.A_BOLD)
    except curses.error:
        pass

    for r in range(min(draw_rows, max_y - 3)):
        for c in range(half - 1):
            if c >= cols:
                break
            val = self.biofilm_ai[r][c]
            idx = int(val * (n_chars - 1))
            idx = max(0, min(n_chars - 1, idx))
            ch = heat_chars[idx]
            # Color: dim → green → yellow → red as AI increases
            if val < 0.15:
                cp = curses.A_DIM
            elif val < _AI_THRESHOLD:
                try:
                    cp = curses.color_pair(2)  # green (below threshold)
                except Exception:
                    cp = curses.A_NORMAL
            elif val < 0.5:
                try:
                    cp = curses.color_pair(3) | curses.A_BOLD  # yellow
                except Exception:
                    cp = curses.A_BOLD
            else:
                try:
                    cp = curses.color_pair(1) | curses.A_BOLD  # red (high)
                except Exception:
                    cp = curses.A_BOLD

            try:
                self.stdscr.addstr(r + 2, c, ch, cp)
            except curses.error:
                pass

    # Divider
    for r in range(draw_rows + 1):
        try:
            self.stdscr.addstr(r + 1, half, "│", curses.A_DIM)
        except curses.error:
            pass

    # Right: nutrients + oxygen blend
    try:
        self.stdscr.addstr(1, half + max(0, half // 2 - 8),
                           "NUTRIENT / OXYGEN", curses.A_BOLD)
    except curses.error:
        pass

    for r in range(min(draw_rows, max_y - 3)):
        for c in range(half - 1):
            if c >= cols:
                break
            nut = self.biofilm_nutrients[r][c]
            o2 = self.biofilm_oxygen[r][c]
            val = (nut + o2) / 2.0
            idx = int(val * (n_chars - 1))
            idx = max(0, min(n_chars - 1, idx))
            ch = heat_chars[idx]

            if val > 0.6:
                try:
                    cp = curses.color_pair(4) | curses.A_BOLD  # blue (well-fed)
                except Exception:
                    cp = curses.A_BOLD
            elif val > 0.3:
                try:
                    cp = curses.color_pair(2)  # green
                except Exception:
                    cp = curses.A_NORMAL
            else:
                try:
                    cp = curses.color_pair(1) | curses.A_DIM  # red (depleted)
                except Exception:
                    cp = curses.A_DIM

            try:
                self.stdscr.addstr(r + 2, half + 1 + c, ch, cp)
            except curses.error:
                pass

    # Draw AI threshold line indicator
    thresh_label = f"QS threshold: {_AI_THRESHOLD:.2f}"
    try:
        self.stdscr.addstr(max_y - 3, 2, thresh_label[:max_x - 3],
                           curses.color_pair(3) | curses.A_DIM)
    except curses.error:
        pass


def _draw_biofilm_graphs(self, max_y: int, max_x: int):
    """Draw time-series sparkline graphs for biofilm metrics."""
    hist = self.biofilm_history
    graph_w = max(10, max_x - 30)

    labels = [
        ("Population",      'population',     7),
        ("Planktonic",       'planktonic',     2),
        ("Biofilm Cells",    'biofilm_cells',  3),
        ("Persister Cells",  'persister',      6),
        ("Avg Autoinducer",  'avg_ai',         3),
        ("EPS Coverage",     'eps_coverage',   3),
        ("Avg Nutrient",     'nutrient_avg',   4),
        ("Avg Oxygen",       'o2_avg',         4),
        ("Avg Antibiotic",   'antibiotic_avg', 5),
        ("Biofilm Height",   'biofilm_height', 1),
    ]

    bars = "▁▂▃▄▅▆▇█"
    n_bars = len(bars)

    for gi, (label, key, cp) in enumerate(labels):
        base_y = 2 + gi * 2
        if base_y + 1 >= max_y - 2:
            break

        data = hist.get(key, [])
        # Label with current value
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

        # Sparkline
        if data:
            visible = data[-graph_w:]
            mn = min(visible)
            mx = max(visible)
            rng = mx - mn if mx > mn else 1.0
            color = curses.color_pair(cp)
            for i, v in enumerate(visible):
                x = 26 + i
                if x >= max_x - 1:
                    break
                idx = int((v - mn) / rng * (n_bars - 1))
                idx = max(0, min(n_bars - 1, idx))
                try:
                    self.stdscr.addstr(base_y, x, bars[idx], color)
                except curses.error:
                    pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register biofilm mode methods on the App class."""
    App.BIOFILM_PRESETS = BIOFILM_PRESETS
    App._enter_biofilm_mode = _enter_biofilm_mode
    App._exit_biofilm_mode = _exit_biofilm_mode
    App._biofilm_init = _biofilm_init
    App._biofilm_step = _biofilm_step
    App._handle_biofilm_menu_key = _handle_biofilm_menu_key
    App._handle_biofilm_key = _handle_biofilm_key
    App._draw_biofilm_menu = _draw_biofilm_menu
    App._draw_biofilm = _draw_biofilm
