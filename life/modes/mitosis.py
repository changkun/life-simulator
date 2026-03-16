"""Mode: mitosis — Mitosis & Cell Division Cycle simulation.

Models the eukaryotic cell cycle (G1→S→G2→M phases) across a 2D tissue grid.
Each cell maintains phase, cyclin/CDK levels, DNA replication progress,
chromosome condensation, spindle assembly, metaphase alignment, anaphase
separation, and cytokinesis.  Includes spindle assembly checkpoint (SAC)
enforcement, cyclin/CDK oscillator dynamics, contact inhibition, apoptosis
signaling, and pathological failure modes (checkpoint bypass → aneuploidy,
uncontrolled proliferation mimicking tumor growth).

Three views:
  1) Tissue grid — cell phase coloring with mitotic figure glyphs
  2) Single-cell detail — cyclin/CDK oscillator waveforms + chromosome diagram
  3) Time-series sparkline graphs — 10 population-level metrics

Six presets:
  Normal Tissue Homeostasis, Rapid Proliferation (Embryonic),
  Checkpoint Bypass (Tumor), Contact Inhibition Loss,
  Apoptosis Cascade, Spindle Poison (Drug Treatment)
"""
import curses
import math
import random


# ======================================================================
#  Presets
# ======================================================================

MITOSIS_PRESETS = [
    ("Normal Tissue Homeostasis",
     "Balanced proliferation & apoptosis — cells divide when growth signals exceed threshold, contact inhibition active",
     "normal"),
    ("Rapid Proliferation (Embryonic)",
     "Shortened G1 gap phase — fast cycling with minimal checkpoints, high growth factor field",
     "embryonic"),
    ("Checkpoint Bypass (Tumor)",
     "p53 loss + SAC defect — cells skip G1/M checkpoints, accumulate aneuploidy, uncontrolled growth",
     "tumor"),
    ("Contact Inhibition Loss",
     "Cells ignore neighbor density — pile up without growth arrest, mimicking transformed phenotype",
     "contact_loss"),
    ("Apoptosis Cascade",
     "Stressed tissue triggers caspase signaling wave — apoptotic cells release death ligands to neighbors",
     "apoptosis"),
    ("Spindle Poison (Drug Treatment)",
     "Microtubule-targeting agent arrests cells in M-phase — SAC fires indefinitely, mitotic catastrophe",
     "spindle_poison"),
]


# ======================================================================
#  Constants
# ======================================================================

_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]
_NEIGHBORS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]

# Cell cycle phase IDs
_PHASE_EMPTY = 0
_PHASE_G1 = 1
_PHASE_S = 2
_PHASE_G2 = 3
_PHASE_M_PROPHASE = 4
_PHASE_M_METAPHASE = 5
_PHASE_M_ANAPHASE = 6
_PHASE_M_TELOPHASE = 7
_PHASE_CYTOKINESIS = 8
_PHASE_QUIESCENT = 9   # G0
_PHASE_APOPTOTIC = 10

_PHASE_NAMES = {
    _PHASE_EMPTY: "empty", _PHASE_G1: "G1", _PHASE_S: "S",
    _PHASE_G2: "G2", _PHASE_M_PROPHASE: "Pro", _PHASE_M_METAPHASE: "Met",
    _PHASE_M_ANAPHASE: "Ana", _PHASE_M_TELOPHASE: "Tel",
    _PHASE_CYTOKINESIS: "Cyt", _PHASE_QUIESCENT: "G0",
    _PHASE_APOPTOTIC: "Apo",
}

# Duration of each phase (ticks) — baseline
_G1_DURATION = 40
_S_DURATION = 30
_G2_DURATION = 20
_PROPHASE_DURATION = 12
_METAPHASE_DURATION = 10
_ANAPHASE_DURATION = 8
_TELOPHASE_DURATION = 6
_CYTOKINESIS_DURATION = 4
_APOPTOSIS_DURATION = 15

# Cyclin/CDK thresholds
_CYCLIN_D_THRESHOLD = 0.6    # G1→S transition (restriction point)
_CYCLIN_B_THRESHOLD = 0.7    # G2→M transition
_APC_THRESHOLD = 0.65        # M exit (anaphase promoting complex)

# Cyclin oscillator rates
_CYCLIN_D_RATE = 0.025       # G1 cyclin accumulation
_CYCLIN_E_RATE = 0.04        # S-phase cyclin
_CYCLIN_A_RATE = 0.03        # S/G2 cyclin
_CYCLIN_B_RATE = 0.035       # mitotic cyclin
_CYCLIN_DEGRADE = 0.02       # base degradation rate

# Spindle assembly checkpoint
_SAC_ATTACHMENT_RATE = 0.12  # per-tick prob of kinetochore attachment
_SAC_THRESHOLD = 0.95        # fraction attached needed to pass SAC

# Contact inhibition
_CONTACT_INHIBIT_THRESHOLD = 6  # neighbors to trigger G0 arrest

# Growth factor field
_GF_DIFFUSION = 0.06
_GF_DECAY = 0.008
_GF_PRODUCTION = 0.02        # produced by living cells
_GF_THRESHOLD = 0.3          # needed to enter cycle from G0

# Apoptosis
_APOPTOSIS_SIGNAL_DIFFUSION = 0.10
_APOPTOSIS_SIGNAL_DECAY = 0.012
_APOPTOSIS_BASE_RATE = 0.001  # spontaneous apoptosis per tick
_APOPTOSIS_SIGNAL_RATE = 0.04  # death ligand induced

# Aneuploidy
_PLOIDY_NORMAL = 2
_PLOIDY_ERROR_THRESHOLD = 3  # aneuploidy above this

# Spindle poison
_POISON_DIFFUSION = 0.07
_POISON_DECAY = 0.004


# ======================================================================
#  Enter / Exit
# ======================================================================

def _enter_mitosis_mode(self):
    """Enter mitosis & cell division cycle mode — show preset menu."""
    self.mitosis_mode = True
    self.mitosis_menu = True
    self.mitosis_menu_sel = 0


def _exit_mitosis_mode(self):
    """Exit mitosis mode."""
    self.mitosis_mode = False
    self.mitosis_menu = False
    self.mitosis_running = False
    for attr in list(vars(self)):
        if attr.startswith('mitosis_') and attr not in ('mitosis_mode',):
            try:
                delattr(self, attr)
            except AttributeError:
                pass


# ======================================================================
#  Cell helper
# ======================================================================

def _make_cell(phase=_PHASE_G1, ploidy=2):
    """Create a new cell dict."""
    return {
        'phase': phase,
        'phase_tick': 0,
        'cyclin_d': random.uniform(0.0, 0.15),
        'cyclin_e': 0.0,
        'cyclin_a': 0.0,
        'cyclin_b': 0.0,
        'apc': 0.0,
        'dna_replicated': 0.0,       # 0→1 during S phase
        'condensation': 0.0,          # 0→1 during prophase
        'spindle_attached': 0.0,      # fraction of kinetochores attached
        'aligned': False,              # metaphase plate alignment
        'separated': False,            # anaphase chromatid separation
        'sac_active': True,            # spindle assembly checkpoint
        'checkpoint_g1': True,         # G1/S checkpoint (p53)
        'checkpoint_m': True,          # SAC functional
        'ploidy': ploidy,
        'aneuploid': False,
        'contact_inhibited': False,
        'apoptosis_timer': 0,
        'generation': 0,
    }


# ======================================================================
#  Initialization
# ======================================================================

def _mitosis_init(self, preset_idx: int):
    """Initialize mitosis simulation for chosen preset."""
    name, _desc, pid = MITOSIS_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(16, max_y - 4)
    cols = max(30, max_x - 2)

    self.mitosis_menu = False
    self.mitosis_running = False
    self.mitosis_preset_name = name
    self.mitosis_preset_id = pid
    self.mitosis_rows = rows
    self.mitosis_cols = cols
    self.mitosis_generation = 0
    self.mitosis_speed = 1
    self.mitosis_view = "tissue"  # tissue | detail | graphs

    # Cell grid: None = empty, dict = cell
    self.mitosis_cells = [[None] * cols for _ in range(rows)]

    # Growth factor field
    self.mitosis_gf = [[0.0] * cols for _ in range(rows)]

    # Apoptosis signal field
    self.mitosis_apo_signal = [[0.0] * cols for _ in range(rows)]

    # Spindle poison field
    self.mitosis_poison = [[0.0] * cols for _ in range(rows)]

    # Selected cell for detail view
    self.mitosis_sel_r = rows // 2
    self.mitosis_sel_c = cols // 2

    # Metrics history
    self.mitosis_history = {
        'total_cells': [],
        'dividing': [],
        'g1_frac': [],
        's_frac': [],
        'g2m_frac': [],
        'apoptotic': [],
        'aneuploid_frac': [],
        'mean_cyclin_b': [],
        'growth_factor': [],
        'quiescent_frac': [],
    }

    # Apply preset
    _mitosis_apply_preset(self, pid, rows, cols)
    self._flash(f"Mitosis: {name}")


def _mitosis_apply_preset(self, pid, rows, cols):
    """Configure preset-specific initial conditions."""
    cells = self.mitosis_cells
    gf = self.mitosis_gf

    if pid == "normal":
        # Scattered cells, ~40% density, contact inhibition on
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.40:
                    cell = _make_cell(_PHASE_G1 if random.random() < 0.6 else _PHASE_QUIESCENT)
                    cell['cyclin_d'] = random.uniform(0.0, 0.5)
                    cell['phase_tick'] = random.randint(0, _G1_DURATION // 2)
                    cells[r][c] = cell
                    gf[r][c] = random.uniform(0.25, 0.50)

    elif pid == "embryonic":
        # Dense, fast cycling, high growth factor
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.65:
                    phase = random.choice([_PHASE_G1, _PHASE_S, _PHASE_G2,
                                           _PHASE_M_PROPHASE])
                    cell = _make_cell(phase)
                    cell['cyclin_d'] = random.uniform(0.3, 0.8)
                    cell['cyclin_e'] = random.uniform(0.1, 0.5)
                    cell['phase_tick'] = random.randint(0, 10)
                    cells[r][c] = cell
                gf[r][c] = random.uniform(0.6, 0.95)

    elif pid == "tumor":
        # Cluster of checkpoint-defective cells + normal surround
        cr, cc = rows // 2, cols // 2
        radius = min(rows, cols) // 5
        for r in range(rows):
            for c in range(cols):
                dist = math.sqrt((r - cr) ** 2 + (c - cc) ** 2)
                if dist < radius:
                    cell = _make_cell(random.choice([_PHASE_G1, _PHASE_S]))
                    cell['checkpoint_g1'] = False
                    cell['checkpoint_m'] = False
                    cell['cyclin_d'] = random.uniform(0.4, 0.9)
                    cells[r][c] = cell
                    gf[r][c] = 0.7
                elif random.random() < 0.30:
                    cells[r][c] = _make_cell(_PHASE_QUIESCENT)
                    gf[r][c] = random.uniform(0.2, 0.4)

    elif pid == "contact_loss":
        # Very dense tissue, contact inhibition disabled
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.75:
                    cell = _make_cell(_PHASE_G1)
                    cell['contact_inhibited'] = False
                    cell['cyclin_d'] = random.uniform(0.2, 0.7)
                    cells[r][c] = cell
                gf[r][c] = random.uniform(0.5, 0.8)

    elif pid == "apoptosis":
        # Healthy tissue with apoptotic seed region
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.55:
                    cells[r][c] = _make_cell(_PHASE_G1)
                    cells[r][c]['cyclin_d'] = random.uniform(0.1, 0.4)
                gf[r][c] = random.uniform(0.3, 0.5)
        # Seed apoptosis in a corner
        for r in range(min(6, rows)):
            for c in range(min(6, cols)):
                if cells[r][c] is not None:
                    cells[r][c]['phase'] = _PHASE_APOPTOTIC
                    cells[r][c]['apoptosis_timer'] = random.randint(1, 8)
                self.mitosis_apo_signal[r][c] = 0.8

    elif pid == "spindle_poison":
        # Active tissue with drug flooding in
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.50:
                    phase = random.choice([_PHASE_G1, _PHASE_S, _PHASE_G2,
                                           _PHASE_M_PROPHASE, _PHASE_M_METAPHASE])
                    cell = _make_cell(phase)
                    cell['cyclin_d'] = random.uniform(0.2, 0.8)
                    if phase >= _PHASE_M_PROPHASE:
                        cell['cyclin_b'] = random.uniform(0.5, 0.9)
                    cells[r][c] = cell
                gf[r][c] = random.uniform(0.4, 0.6)
                self.mitosis_poison[r][c] = random.uniform(0.3, 0.8)


# ======================================================================
#  Simulation Step
# ======================================================================

def _mitosis_step(self):
    """One tick of mitosis & cell division simulation."""
    rows = self.mitosis_rows
    cols = self.mitosis_cols
    cells = self.mitosis_cells
    gf = self.mitosis_gf
    apo_sig = self.mitosis_apo_signal
    poison = self.mitosis_poison
    pid = self.mitosis_preset_id
    gen = self.mitosis_generation

    # --- Diffuse growth factor ---
    new_gf = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            g = gf[r][c]
            lap = 0.0
            for dr, dc in _NEIGHBORS_4:
                rr, cc2 = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc2 < cols:
                    lap += gf[rr][cc2] - g
            prod = _GF_PRODUCTION if cells[r][c] is not None else 0.0
            new_gf[r][c] = max(0.0, min(1.0, g + _GF_DIFFUSION * lap - _GF_DECAY * g + prod))
    self.mitosis_gf = new_gf
    gf = new_gf

    # --- Diffuse apoptosis signal ---
    new_apo = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            a = apo_sig[r][c]
            lap = 0.0
            for dr, dc in _NEIGHBORS_4:
                rr, cc2 = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc2 < cols:
                    lap += apo_sig[rr][cc2] - a
            # Apoptotic cells produce signal
            prod = 0.05 if (cells[r][c] is not None and cells[r][c]['phase'] == _PHASE_APOPTOTIC) else 0.0
            new_apo[r][c] = max(0.0, min(1.0, a + _APOPTOSIS_SIGNAL_DIFFUSION * lap
                                          - _APOPTOSIS_SIGNAL_DECAY * a + prod))
    self.mitosis_apo_signal = new_apo
    apo_sig = new_apo

    # --- Diffuse spindle poison ---
    if pid == "spindle_poison":
        new_poison = [[0.0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                p = poison[r][c]
                lap = 0.0
                for dr, dc in _NEIGHBORS_4:
                    rr, cc2 = r + dr, c + dc
                    if 0 <= rr < rows and 0 <= cc2 < cols:
                        lap += poison[rr][cc2] - p
                new_poison[r][c] = max(0.0, p + _POISON_DIFFUSION * lap - _POISON_DECAY * p)
        self.mitosis_poison = new_poison
        poison = new_poison

    # --- Process each cell ---
    # Collect division events to apply after iteration
    divisions = []  # (r, c, daughter_cell)
    removals = []   # (r, c)

    for r in range(rows):
        for c in range(cols):
            cell = cells[r][c]
            if cell is None:
                continue

            phase = cell['phase']
            cell['phase_tick'] += 1

            # --- Apoptosis check ---
            if phase != _PHASE_APOPTOTIC:
                apo_p = _APOPTOSIS_BASE_RATE
                if apo_sig[r][c] > 0.3:
                    apo_p += _APOPTOSIS_SIGNAL_RATE * apo_sig[r][c]
                if random.random() < apo_p:
                    cell['phase'] = _PHASE_APOPTOTIC
                    cell['apoptosis_timer'] = _APOPTOSIS_DURATION
                    continue

            # --- Contact inhibition ---
            if pid not in ("contact_loss", "tumor"):
                n_neighbors = 0
                for dr, dc in _NEIGHBORS_8:
                    rr, cc2 = r + dr, c + dc
                    if 0 <= rr < rows and 0 <= cc2 < cols and cells[rr][cc2] is not None:
                        n_neighbors += 1
                if n_neighbors >= _CONTACT_INHIBIT_THRESHOLD and phase in (_PHASE_G1, _PHASE_QUIESCENT):
                    cell['phase'] = _PHASE_QUIESCENT
                    cell['contact_inhibited'] = True
                    continue

            # --- Phase-specific logic ---
            if phase == _PHASE_QUIESCENT:
                # Check if growth factors allow re-entry
                if gf[r][c] > _GF_THRESHOLD:
                    # Check contact inhibition
                    n_neighbors = sum(
                        1 for dr, dc in _NEIGHBORS_8
                        if 0 <= r + dr < rows and 0 <= c + dc < cols
                        and cells[r + dr][c + dc] is not None
                    )
                    if pid in ("contact_loss", "tumor") or n_neighbors < _CONTACT_INHIBIT_THRESHOLD:
                        cell['phase'] = _PHASE_G1
                        cell['phase_tick'] = 0
                        cell['cyclin_d'] = 0.05
                        cell['contact_inhibited'] = False

            elif phase == _PHASE_G1:
                # Accumulate Cyclin D/CDK4,6
                growth_boost = gf[r][c] * 0.5
                cell['cyclin_d'] += (_CYCLIN_D_RATE + growth_boost * 0.02)
                cell['cyclin_d'] = min(1.0, cell['cyclin_d'])
                cell['cyclin_e'] += _CYCLIN_E_RATE * 0.3 * cell['cyclin_d']
                cell['cyclin_e'] = min(1.0, cell['cyclin_e'])

                # G1/S checkpoint (restriction point)
                g1_dur = _G1_DURATION
                if pid == "embryonic":
                    g1_dur = _G1_DURATION // 3  # shortened G1
                if cell['phase_tick'] >= g1_dur:
                    if cell['checkpoint_g1']:
                        if cell['cyclin_d'] >= _CYCLIN_D_THRESHOLD:
                            cell['phase'] = _PHASE_S
                            cell['phase_tick'] = 0
                        # else stay in G1
                    else:
                        # Checkpoint bypassed (tumor)
                        cell['phase'] = _PHASE_S
                        cell['phase_tick'] = 0

            elif phase == _PHASE_S:
                # DNA replication
                cell['dna_replicated'] += 1.0 / _S_DURATION
                cell['dna_replicated'] = min(1.0, cell['dna_replicated'])
                cell['cyclin_e'] += _CYCLIN_E_RATE
                cell['cyclin_e'] = min(1.0, cell['cyclin_e'])
                cell['cyclin_a'] += _CYCLIN_A_RATE * 0.5
                cell['cyclin_a'] = min(1.0, cell['cyclin_a'])

                # S→G2 transition
                if cell['dna_replicated'] >= 0.98:
                    cell['phase'] = _PHASE_G2
                    cell['phase_tick'] = 0

            elif phase == _PHASE_G2:
                # Accumulate Cyclin B/CDK1
                cell['cyclin_a'] += _CYCLIN_A_RATE
                cell['cyclin_a'] = min(1.0, cell['cyclin_a'])
                cell['cyclin_b'] += _CYCLIN_B_RATE
                cell['cyclin_b'] = min(1.0, cell['cyclin_b'])

                # G2→M checkpoint
                if cell['phase_tick'] >= _G2_DURATION:
                    if cell['cyclin_b'] >= _CYCLIN_B_THRESHOLD or not cell['checkpoint_g1']:
                        cell['phase'] = _PHASE_M_PROPHASE
                        cell['phase_tick'] = 0

            elif phase == _PHASE_M_PROPHASE:
                # Chromosome condensation
                cell['condensation'] += 1.0 / _PROPHASE_DURATION
                cell['condensation'] = min(1.0, cell['condensation'])
                cell['cyclin_b'] = min(1.0, cell['cyclin_b'] + 0.01)

                if cell['phase_tick'] >= _PROPHASE_DURATION:
                    cell['phase'] = _PHASE_M_METAPHASE
                    cell['phase_tick'] = 0
                    cell['spindle_attached'] = 0.0

            elif phase == _PHASE_M_METAPHASE:
                # Spindle assembly — kinetochore attachment
                local_poison = poison[r][c] if pid == "spindle_poison" else 0.0
                attach_rate = _SAC_ATTACHMENT_RATE * (1.0 - local_poison * 0.9)
                if random.random() < attach_rate:
                    cell['spindle_attached'] = min(1.0, cell['spindle_attached'] + 0.15)

                # Metaphase plate alignment
                if cell['spindle_attached'] > 0.8:
                    cell['aligned'] = True

                # Spindle assembly checkpoint
                if cell['checkpoint_m']:
                    if cell['spindle_attached'] >= _SAC_THRESHOLD:
                        cell['sac_active'] = False
                        cell['phase'] = _PHASE_M_ANAPHASE
                        cell['phase_tick'] = 0
                    elif cell['phase_tick'] > _METAPHASE_DURATION * 5:
                        # Prolonged arrest → mitotic catastrophe → apoptosis
                        if local_poison > 0.3:
                            cell['phase'] = _PHASE_APOPTOTIC
                            cell['apoptosis_timer'] = _APOPTOSIS_DURATION
                else:
                    # SAC bypassed — proceed even without full attachment
                    if cell['phase_tick'] >= _METAPHASE_DURATION:
                        cell['phase'] = _PHASE_M_ANAPHASE
                        cell['phase_tick'] = 0
                        # Risk of aneuploidy
                        if cell['spindle_attached'] < _SAC_THRESHOLD:
                            if random.random() < 0.6:
                                cell['ploidy'] += random.choice([-1, 1])
                                cell['aneuploid'] = True

            elif phase == _PHASE_M_ANAPHASE:
                # Chromatid separation
                cell['separated'] = True
                cell['apc'] += 0.1
                cell['apc'] = min(1.0, cell['apc'])
                cell['cyclin_b'] *= 0.85  # APC degrades cyclin B

                if cell['phase_tick'] >= _ANAPHASE_DURATION:
                    cell['phase'] = _PHASE_M_TELOPHASE
                    cell['phase_tick'] = 0

            elif phase == _PHASE_M_TELOPHASE:
                # Nuclear envelope reform, decondensation
                cell['condensation'] *= 0.9
                cell['cyclin_b'] *= 0.8
                cell['cyclin_a'] *= 0.8

                if cell['phase_tick'] >= _TELOPHASE_DURATION:
                    cell['phase'] = _PHASE_CYTOKINESIS
                    cell['phase_tick'] = 0

            elif phase == _PHASE_CYTOKINESIS:
                # Find empty neighbor for daughter cell
                if cell['phase_tick'] >= _CYTOKINESIS_DURATION:
                    empty_neighbors = []
                    for dr, dc in _NEIGHBORS_8:
                        rr, cc2 = r + dr, c + dc
                        if 0 <= rr < rows and 0 <= cc2 < cols and cells[rr][cc2] is None:
                            empty_neighbors.append((rr, cc2))

                    # Create daughter cell
                    daughter = _make_cell(_PHASE_G1, cell['ploidy'])
                    daughter['aneuploid'] = cell['aneuploid']
                    daughter['checkpoint_g1'] = cell['checkpoint_g1']
                    daughter['checkpoint_m'] = cell['checkpoint_m']
                    daughter['generation'] = cell['generation'] + 1

                    if empty_neighbors:
                        dr, dc2 = random.choice(empty_neighbors)
                        divisions.append((dr, dc2, daughter))

                    # Reset mother cell
                    cell['phase'] = _PHASE_G1
                    cell['phase_tick'] = 0
                    cell['cyclin_d'] = 0.05
                    cell['cyclin_e'] = 0.0
                    cell['cyclin_a'] = 0.0
                    cell['cyclin_b'] = 0.0
                    cell['apc'] = 0.0
                    cell['dna_replicated'] = 0.0
                    cell['condensation'] = 0.0
                    cell['spindle_attached'] = 0.0
                    cell['aligned'] = False
                    cell['separated'] = False
                    cell['sac_active'] = True
                    cell['generation'] += 1

            elif phase == _PHASE_APOPTOTIC:
                cell['apoptosis_timer'] -= 1
                if cell['apoptosis_timer'] <= 0:
                    removals.append((r, c))

    # --- Apply divisions ---
    for dr, dc, daughter in divisions:
        if cells[dr][dc] is None:
            cells[dr][dc] = daughter

    # --- Apply removals ---
    for rr, cc in removals:
        cells[rr][cc] = None

    # --- Collect metrics ---
    _mitosis_collect_metrics(self)
    self.mitosis_generation += 1


def _mitosis_collect_metrics(self):
    """Gather population-level statistics."""
    rows = self.mitosis_rows
    cols = self.mitosis_cols
    cells = self.mitosis_cells
    hist = self.mitosis_history

    total = 0
    dividing = 0
    g1_count = 0
    s_count = 0
    g2m_count = 0
    apo_count = 0
    aneuploid_count = 0
    cyclin_b_sum = 0.0
    gf_sum = 0.0
    quiescent_count = 0

    for r in range(rows):
        for c in range(cols):
            cell = cells[r][c]
            gf_sum += self.mitosis_gf[r][c]
            if cell is None:
                continue
            total += 1
            p = cell['phase']
            if p == _PHASE_G1:
                g1_count += 1
            elif p == _PHASE_S:
                s_count += 1
            elif _PHASE_G2 <= p <= _PHASE_CYTOKINESIS:
                g2m_count += 1
                if _PHASE_M_PROPHASE <= p <= _PHASE_CYTOKINESIS:
                    dividing += 1
            elif p == _PHASE_APOPTOTIC:
                apo_count += 1
            elif p == _PHASE_QUIESCENT:
                quiescent_count += 1
            if cell['aneuploid']:
                aneuploid_count += 1
            cyclin_b_sum += cell['cyclin_b']

    n = max(1, total)
    grid_size = rows * cols

    hist['total_cells'].append(total)
    hist['dividing'].append(dividing)
    hist['g1_frac'].append(g1_count / n * 100)
    hist['s_frac'].append(s_count / n * 100)
    hist['g2m_frac'].append(g2m_count / n * 100)
    hist['apoptotic'].append(apo_count)
    hist['aneuploid_frac'].append(aneuploid_count / n * 100 if total > 0 else 0)
    hist['mean_cyclin_b'].append(cyclin_b_sum / n if total > 0 else 0)
    hist['growth_factor'].append(gf_sum / grid_size)
    hist['quiescent_frac'].append(quiescent_count / n * 100 if total > 0 else 0)

    # Trim history
    max_hist = 500
    for key in hist:
        if len(hist[key]) > max_hist:
            hist[key] = hist[key][-max_hist:]


# ======================================================================
#  Key Handlers
# ======================================================================

def _handle_mitosis_menu_key(self, key: int) -> bool:
    """Handle keys in preset menu."""
    if key == curses.KEY_UP or key == ord('k'):
        self.mitosis_menu_sel = (self.mitosis_menu_sel - 1) % len(MITOSIS_PRESETS)
        return True
    if key == curses.KEY_DOWN or key == ord('j'):
        self.mitosis_menu_sel = (self.mitosis_menu_sel + 1) % len(MITOSIS_PRESETS)
        return True
    if key in (10, 13, curses.KEY_ENTER):
        _mitosis_init(self, self.mitosis_menu_sel)
        self.mitosis_running = True
        return True
    if key == ord('q') or key == 27:
        self._exit_mitosis_mode()
        return True
    return False


def _handle_mitosis_key(self, key: int) -> bool:
    """Handle keys during simulation."""
    if key == ord(' '):
        self.mitosis_running = not self.mitosis_running
        return True
    if key == ord('v'):
        views = ["tissue", "detail", "graphs"]
        idx = views.index(self.mitosis_view)
        self.mitosis_view = views[(idx + 1) % len(views)]
        return True
    if key == ord('n'):
        _mitosis_step(self)
        return True
    if key == ord('a'):
        # Trigger apoptosis at selected cell
        _mitosis_trigger_apoptosis(self)
        return True
    if key == ord('+') or key == ord('='):
        self.mitosis_speed = min(8, self.mitosis_speed + 1)
        return True
    if key == ord('-'):
        self.mitosis_speed = max(1, self.mitosis_speed - 1)
        return True
    if key == ord('r'):
        idx = next((i for i, p in enumerate(MITOSIS_PRESETS) if p[2] == self.mitosis_preset_id), 0)
        _mitosis_init(self, idx)
        self.mitosis_running = True
        return True
    if key == ord('R'):
        self.mitosis_menu = True
        self.mitosis_menu_sel = 0
        return True
    # Arrow keys move selection cursor in detail view
    if key == curses.KEY_UP:
        self.mitosis_sel_r = max(0, self.mitosis_sel_r - 1)
        return True
    if key == curses.KEY_DOWN:
        self.mitosis_sel_r = min(self.mitosis_rows - 1, self.mitosis_sel_r + 1)
        return True
    if key == curses.KEY_LEFT:
        self.mitosis_sel_c = max(0, self.mitosis_sel_c - 1)
        return True
    if key == curses.KEY_RIGHT:
        self.mitosis_sel_c = min(self.mitosis_cols - 1, self.mitosis_sel_c + 1)
        return True
    if key == ord('q'):
        self._exit_mitosis_mode()
        return True
    return False


def _mitosis_trigger_apoptosis(self):
    """Trigger apoptosis at selected cell position."""
    r, c = self.mitosis_sel_r, self.mitosis_sel_c
    cell = self.mitosis_cells[r][c]
    if cell is not None and cell['phase'] != _PHASE_APOPTOTIC:
        cell['phase'] = _PHASE_APOPTOTIC
        cell['apoptosis_timer'] = _APOPTOSIS_DURATION
        self.mitosis_apo_signal[r][c] = 1.0
        self._flash("Apoptosis triggered")


# ======================================================================
#  Drawing — Preset Menu
# ======================================================================

def _draw_mitosis_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    self.stdscr.erase()
    title = "Mitosis & Cell Division Cycle"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD | curses.color_pair(4))
    except curses.error:
        pass

    sub = "Select a cell cycle preset:"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(sub)) // 2), sub)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(MITOSIS_PRESETS):
        y = 5 + i * 3
        if y + 1 >= max_y:
            break
        marker = ">" if i == self.mitosis_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.mitosis_menu_sel else 0
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
#  Drawing — Tissue Grid View
# ======================================================================

def _draw_mitosis(self, max_y: int, max_x: int):
    """Dispatch to appropriate view drawer."""
    if self.mitosis_view == "tissue":
        _draw_mitosis_tissue(self, max_y, max_x)
    elif self.mitosis_view == "detail":
        _draw_mitosis_detail(self, max_y, max_x)
    elif self.mitosis_view == "graphs":
        _draw_mitosis_graphs(self, max_y, max_x)


def _draw_mitosis_tissue(self, max_y: int, max_x: int):
    """Render tissue grid with cell phase coloring and mitotic glyphs."""
    self.stdscr.erase()
    rows = self.mitosis_rows
    cols = self.mitosis_cols
    cells = self.mitosis_cells

    view_h = min(rows, max_y - 3)
    view_w = min(cols, max_x - 1)

    for r in range(view_h):
        for c in range(view_w):
            cell = cells[r][c]
            if cell is None:
                # Show growth factor faintly
                g = self.mitosis_gf[r][c]
                if g > 0.4:
                    ch = "."
                    cp = curses.color_pair(7) | curses.A_DIM
                else:
                    continue
            else:
                phase = cell['phase']
                ch, cp = _cell_glyph(cell, self.mitosis_poison[r][c])

            # Selected cell highlight
            if r == self.mitosis_sel_r and c == self.mitosis_sel_c:
                cp |= curses.A_UNDERLINE

            try:
                self.stdscr.addstr(1 + r, c, ch, cp)
            except curses.error:
                pass

    # Status bar
    hist = self.mitosis_history
    total = hist['total_cells'][-1] if hist['total_cells'] else 0
    div = hist['dividing'][-1] if hist['dividing'] else 0
    aneu = hist['aneuploid_frac'][-1] if hist['aneuploid_frac'] else 0

    status = (f" {self.mitosis_preset_name} | tick {self.mitosis_generation} | "
              f"cells:{total} | dividing:{div} | aneupl:{aneu:.1f}% | "
              f"[v]iew [a]popt [space]pause [r]estart [q]uit")
    try:
        self.stdscr.addstr(max_y - 2, 0, status[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    legend = "o:G1 O:S @:G2 *:Pro X:Met |:Ana %:Tel +:Cyt .:G0 x:Apo"
    try:
        self.stdscr.addstr(max_y - 1, 0, legend[:max_x - 1], curses.color_pair(7))
    except curses.error:
        pass


def _cell_glyph(cell, poison_level=0.0):
    """Return (char, curses_attr) for a cell based on its phase."""
    phase = cell['phase']

    if phase == _PHASE_G1:
        ch = "o"
        cp = curses.color_pair(2)  # green — growth
    elif phase == _PHASE_S:
        ch = "O"
        cp = curses.color_pair(4) | curses.A_BOLD  # blue — DNA replication
    elif phase == _PHASE_G2:
        ch = "@"
        cp = curses.color_pair(6)  # cyan — preparation
    elif phase == _PHASE_M_PROPHASE:
        ch = "*"
        cp = curses.color_pair(3) | curses.A_BOLD  # yellow — condensation
    elif phase == _PHASE_M_METAPHASE:
        ch = "X"
        cp = curses.color_pair(5) | curses.A_BOLD  # magenta — alignment
        if poison_level > 0.3:
            cp = curses.color_pair(1) | curses.A_BOLD  # red — arrested
    elif phase == _PHASE_M_ANAPHASE:
        ch = "|"
        cp = curses.color_pair(3)  # yellow — separation
    elif phase == _PHASE_M_TELOPHASE:
        ch = "%"
        cp = curses.color_pair(5)  # magenta — reform
    elif phase == _PHASE_CYTOKINESIS:
        ch = "+"
        cp = curses.color_pair(2) | curses.A_BOLD  # bright green — division!
    elif phase == _PHASE_QUIESCENT:
        ch = "."
        cp = curses.color_pair(7) | curses.A_DIM   # dim — resting
    elif phase == _PHASE_APOPTOTIC:
        ch = "x"
        cp = curses.color_pair(1)  # red — dying
    else:
        ch = "?"
        cp = curses.color_pair(7)

    # Aneuploidy marker
    if cell['aneuploid'] and phase not in (_PHASE_APOPTOTIC, _PHASE_QUIESCENT):
        cp |= curses.A_BLINK

    return ch, cp


# ======================================================================
#  Drawing — Single Cell Detail View
# ======================================================================

def _draw_mitosis_detail(self, max_y: int, max_x: int):
    """Render detail view of selected cell: cyclin oscillator + chromosome diagram."""
    self.stdscr.erase()
    sr, sc = self.mitosis_sel_r, self.mitosis_sel_c
    cell = self.mitosis_cells[sr][sc]

    title = f"Cell Detail ({sr},{sc}) -- {self.mitosis_preset_name} | tick {self.mitosis_generation}"
    try:
        self.stdscr.addstr(0, 2, title, curses.A_BOLD | curses.color_pair(4))
    except curses.error:
        pass

    if cell is None:
        try:
            self.stdscr.addstr(3, 4, "Empty position — use arrow keys to select a cell",
                               curses.color_pair(7))
        except curses.error:
            pass
        _draw_detail_status(self, max_y, max_x)
        return

    y = 2
    phase_name = _PHASE_NAMES.get(cell['phase'], '?')

    # Phase and basic info
    info_lines = [
        f"Phase: {phase_name}  (tick {cell['phase_tick']})",
        f"Ploidy: {cell['ploidy']}  {'ANEUPLOID' if cell['aneuploid'] else 'Normal'}",
        f"Generation: {cell['generation']}",
        f"Checkpoints: G1={'ON' if cell['checkpoint_g1'] else 'OFF'}  SAC={'ON' if cell['checkpoint_m'] else 'OFF'}",
        "",
    ]
    for line in info_lines:
        if y >= max_y - 4:
            break
        try:
            self.stdscr.addstr(y, 4, line[:max_x - 6], curses.color_pair(7))
        except curses.error:
            pass
        y += 1

    # Cyclin/CDK bars
    cyclins = [
        ("Cyclin D/CDK4,6", cell['cyclin_d'], 2, _CYCLIN_D_THRESHOLD),
        ("Cyclin E/CDK2  ", cell['cyclin_e'], 4, None),
        ("Cyclin A/CDK2  ", cell['cyclin_a'], 6, None),
        ("Cyclin B/CDK1  ", cell['cyclin_b'], 3, _CYCLIN_B_THRESHOLD),
        ("APC/C          ", cell['apc'], 1, _APC_THRESHOLD),
    ]
    bar_width = min(40, max_x - 30)

    for label, val, color, threshold in cyclins:
        if y >= max_y - 4:
            break
        filled = int(val * bar_width)
        bar = "|" * filled + "." * (bar_width - filled)
        try:
            self.stdscr.addstr(y, 4, f"{label} ", curses.color_pair(7))
            self.stdscr.addstr(y, 22, "[", curses.color_pair(7))
            self.stdscr.addstr(y, 23, bar[:filled],
                               curses.color_pair(color) | curses.A_BOLD)
            self.stdscr.addstr(y, 23 + filled, bar[filled:],
                               curses.color_pair(7) | curses.A_DIM)
            self.stdscr.addstr(y, 23 + bar_width, f"] {val:.2f}", curses.color_pair(7))
            # Threshold marker
            if threshold is not None:
                thresh_pos = int(threshold * bar_width)
                if thresh_pos < bar_width and 23 + thresh_pos < max_x - 2:
                    self.stdscr.addstr(y, 23 + thresh_pos, "^",
                                       curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        y += 1

    y += 1

    # Progress indicators
    progress_lines = [
        f"DNA Replication: {'=' * int(cell['dna_replicated'] * 20)}{'.' * (20 - int(cell['dna_replicated'] * 20))} {cell['dna_replicated']:.0%}",
        f"Condensation:    {'#' * int(cell['condensation'] * 20)}{'.' * (20 - int(cell['condensation'] * 20))} {cell['condensation']:.0%}",
        f"Spindle Attach:  {'|' * int(cell['spindle_attached'] * 20)}{'.' * (20 - int(cell['spindle_attached'] * 20))} {cell['spindle_attached']:.0%}",
        f"Aligned: {'Yes' if cell['aligned'] else 'No'}  Separated: {'Yes' if cell['separated'] else 'No'}",
    ]
    for line in progress_lines:
        if y >= max_y - 4:
            break
        try:
            self.stdscr.addstr(y, 4, line[:max_x - 6], curses.color_pair(7))
        except curses.error:
            pass
        y += 1

    y += 1
    # Chromosome diagram
    if y + 4 < max_y - 3:
        _draw_chromosome_diagram(self, y, 4, cell, max_x, max_y)

    _draw_detail_status(self, max_y, max_x)


def _draw_chromosome_diagram(self, y, x, cell, max_x, max_y):
    """Draw a simple ASCII chromosome state diagram."""
    phase = cell['phase']
    try:
        self.stdscr.addstr(y, x, "Chromosomes:", curses.A_BOLD | curses.color_pair(7))
    except curses.error:
        return

    y += 1
    if phase <= _PHASE_G1 or phase == _PHASE_QUIESCENT:
        # Decondensed — diffuse chromatin
        lines = [
            "  ~ ~ ~ ~  (decondensed chromatin)",
            "   ~ ~ ~   ",
        ]
    elif phase == _PHASE_S:
        pct = cell['dna_replicated']
        replicated = int(pct * 8)
        lines = [
            "  " + "==" * replicated + "~~" * (8 - replicated) + f"  (replicating {pct:.0%})",
        ]
    elif phase == _PHASE_G2:
        lines = [
            "  == == == == == == == ==  (replicated, sister chromatids joined)",
        ]
    elif phase == _PHASE_M_PROPHASE:
        cond = cell['condensation']
        if cond < 0.5:
            lines = ["  XX xx XX xx  (condensing...)"]
        else:
            lines = ["  XX XX XX XX  (condensed chromosomes)"]
    elif phase == _PHASE_M_METAPHASE:
        att = cell['spindle_attached']
        lines = [
            f"      |  spindle ({att:.0%} attached)",
            "  ----XX XX XX XX----  metaphase plate",
            "      |",
        ]
    elif phase == _PHASE_M_ANAPHASE:
        lines = [
            "  X X X X  >>>  <<<  X X X X",
            "     (chromatids separating → poles)",
        ]
    elif phase == _PHASE_M_TELOPHASE:
        lines = [
            "  [X X X X]    [X X X X]",
            "  (nuclear envelopes reforming)",
        ]
    elif phase == _PHASE_CYTOKINESIS:
        lines = [
            "  [~ ~ ~ ~] || [~ ~ ~ ~]",
            "        (cleavage furrow)",
        ]
    elif phase == _PHASE_APOPTOTIC:
        lines = [
            "  x . x . x  (DNA fragmenting)",
            "    . x .     (apoptotic bodies)",
        ]
    else:
        lines = ["  ..."]

    for line in lines:
        if y >= max_y - 3:
            break
        try:
            self.stdscr.addstr(y, x, line[:max_x - x - 1], curses.color_pair(7))
        except curses.error:
            pass
        y += 1


def _draw_detail_status(self, max_y, max_x):
    """Status bar for detail view."""
    status = "[v]iew [arrows]select [a]popt [space]pause [r]estart [q]uit"
    try:
        self.stdscr.addstr(max_y - 1, 2, status[:max_x - 3], curses.color_pair(7))
    except curses.error:
        pass


# ======================================================================
#  Drawing — Sparkline Graphs View
# ======================================================================

def _draw_mitosis_graphs(self, max_y: int, max_x: int):
    """Time-series sparkline graphs for cell population metrics."""
    self.stdscr.erase()
    hist = self.mitosis_history
    graph_w = min(200, max_x - 30)

    title = f"Cell Cycle Metrics -- {self.mitosis_preset_name} | tick {self.mitosis_generation}"
    try:
        self.stdscr.addstr(0, 2, title, curses.A_BOLD)
    except curses.error:
        pass

    labels = [
        ("Total Cells",     'total_cells',     2),
        ("Dividing (M)",    'dividing',        3),
        ("G1 %",            'g1_frac',         2),
        ("S %",             's_frac',          4),
        ("G2/M %",          'g2m_frac',        5),
        ("Apoptotic",       'apoptotic',       1),
        ("Aneuploid %",     'aneuploid_frac',  1),
        ("Mean Cyclin B",   'mean_cyclin_b',   3),
        ("Growth Factor",   'growth_factor',   6),
        ("Quiescent %",     'quiescent_frac',  7),
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
            for i, v in enumerate(visible):
                x = 26 + i
                if x >= max_x - 1:
                    break
                idx = int((v - mn) / rng * n_bars)
                idx = max(0, min(n_bars, idx))
                try:
                    self.stdscr.addstr(base_y, x, bars[idx], color)
                except curses.error:
                    pass

    status = "[v]iew [a]popt [space]pause [r]estart [q]uit"
    try:
        self.stdscr.addstr(max_y - 1, 2, status[:max_x - 3], curses.color_pair(7))
    except curses.error:
        pass


# ======================================================================
#  Registration
# ======================================================================

def register(App):
    """Register mitosis & cell division cycle mode methods on the App class."""
    App.MITOSIS_PRESETS = MITOSIS_PRESETS
    App._enter_mitosis_mode = _enter_mitosis_mode
    App._exit_mitosis_mode = _exit_mitosis_mode
    App._mitosis_init = _mitosis_init
    App._mitosis_step = _mitosis_step
    App._handle_mitosis_menu_key = _handle_mitosis_menu_key
    App._handle_mitosis_key = _handle_mitosis_key
    App._draw_mitosis_menu = _draw_mitosis_menu
    App._draw_mitosis = _draw_mitosis
