"""Mode: immune_system — Immune System Response & Pathogen Defense.

Simulates innate and adaptive immunity as a 2D tissue cross-section.
Pathogen particles invade through a wound breach, neutrophil first-responders
rush via chemotaxis toward cytokine gradients, macrophage phagocytosis with
antigen presentation, T-cell activation cascade (naive → helper/killer with
clonal expansion), B-cell antibody production creating diffusible antibody
fields that opsonize pathogens, complement system membrane attack,
inflammatory cytokine signaling (TNF-α, IL-6) with positive feedback and
tissue damage from excessive inflammation, fever mechanic boosting immune
kinetics but risking tissue at high levels, and memory cell formation for
faster secondary response.

Three views:
  1) Tissue map — immune cell glyphs + pathogen spread + wound site
  2) Cytokine/antibody heatmap overlay
  3) Time-series sparkline graphs (pathogen load, immune cells,
     inflammation, antibody titer, tissue damage, fever, etc.)

Six presets:
  Normal Bacterial Infection, Viral Invasion, Cytokine Storm,
  Immunodeficiency, Allergic Hypersensitivity, Vaccination & Re-exposure
"""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Entity types
# ══════════════════════════════════════════════════════════════════════

ENT_EMPTY = 0
ENT_TISSUE = 1         # healthy tissue
ENT_INFECTED = 2       # infected tissue (viral)
ENT_BACTERIA = 3       # free bacterium
ENT_VIRUS = 4          # free virus particle
ENT_MACROPHAGE = 5     # innate — phagocyte + antigen presenter
ENT_NEUTROPHIL = 6     # innate — fast first responder
ENT_NAIVE_T = 7        # naive T cell (uncommitted)
ENT_HELPER_T = 8       # helper T cell (CD4+ — orchestrates response)
ENT_KILLER_T = 9       # killer T cell (CD8+ — cytotoxic)
ENT_BCELL = 10         # B cell — antibody producer
ENT_MEMORY = 11        # memory cell (T or B lineage)
ENT_DEBRIS = 12        # dead cell debris
ENT_MAST = 13          # mast cell (allergic response)
ENT_DENDRITIC = 14     # dendritic cell — antigen presenter to T cells

ENT_NAMES = {
    ENT_EMPTY: "empty", ENT_TISSUE: "tissue", ENT_INFECTED: "infected",
    ENT_BACTERIA: "bact", ENT_VIRUS: "virus", ENT_MACROPHAGE: "macro",
    ENT_NEUTROPHIL: "neut", ENT_NAIVE_T: "naiveT", ENT_HELPER_T: "helpT",
    ENT_KILLER_T: "killT", ENT_BCELL: "Bcell", ENT_MEMORY: "mem",
    ENT_DEBRIS: "debris", ENT_MAST: "mast", ENT_DENDRITIC: "DC",
}

ENT_CHARS = {
    ENT_EMPTY: "  ", ENT_TISSUE: "..", ENT_INFECTED: "xx",
    ENT_BACTERIA: "@@", ENT_VIRUS: "vv", ENT_MACROPHAGE: "MM",
    ENT_NEUTROPHIL: "NN", ENT_NAIVE_T: "Tn", ENT_HELPER_T: "Th",
    ENT_KILLER_T: "Tk", ENT_BCELL: "BB", ENT_MEMORY: "**",
    ENT_DEBRIS: "::", ENT_MAST: "!!", ENT_DENDRITIC: "DC",
}

# Antigen representation: 6-bit shape for receptor matching
ANTIGEN_BITS = 6
MAX_ANTIGEN = (1 << ANTIGEN_BITS) - 1


def _rand_antigen():
    return random.randint(0, MAX_ANTIGEN)


def _antigen_match(receptor, antigen):
    """Return match quality 0.0-1.0 (hamming similarity)."""
    xor = receptor ^ antigen
    diff = bin(xor).count("1")
    return 1.0 - diff / ANTIGEN_BITS


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

IMMUNE_PRESETS = [
    ("Normal Bacterial Infection",
     "Bacteria invade through wound — innate response then adaptive cascade clears infection",
     {"pathogen": "bacteria", "invasion_rate": 0.04, "replicate_rate": 0.05,
      "mutate_rate": 0.02, "innate_count": 35, "adaptive_count": 20,
      "tissue_density": 0.65, "tnf_decay": 0.03, "il6_decay": 0.03,
      "wound_size": 6, "fever_enabled": True, "complement_enabled": True,
      "immunodeficient": False, "allergic": False,
      "vaccination_antigen": None, "cytokine_storm": False}),

    ("Viral Invasion",
     "Viruses breach wound, infect tissue cells, replicate intracellularly — killer T-cells critical",
     {"pathogen": "virus", "invasion_rate": 0.03, "replicate_rate": 0.04,
      "mutate_rate": 0.03, "innate_count": 30, "adaptive_count": 20,
      "tissue_density": 0.70, "tnf_decay": 0.025, "il6_decay": 0.025,
      "wound_size": 5, "fever_enabled": True, "complement_enabled": True,
      "immunodeficient": False, "allergic": False,
      "vaccination_antigen": None, "cytokine_storm": False}),

    ("Cytokine Storm",
     "Runaway inflammatory feedback — TNF-α/IL-6 cascade causes more damage than pathogens",
     {"pathogen": "virus", "invasion_rate": 0.05, "replicate_rate": 0.06,
      "mutate_rate": 0.02, "innate_count": 55, "adaptive_count": 40,
      "tissue_density": 0.65, "tnf_decay": 0.005, "il6_decay": 0.005,
      "wound_size": 8, "fever_enabled": True, "complement_enabled": True,
      "immunodeficient": False, "allergic": False,
      "vaccination_antigen": None, "cytokine_storm": True}),

    ("Immunodeficiency",
     "Depleted T-cell population — pathogens spread with minimal adaptive defense",
     {"pathogen": "bacteria", "invasion_rate": 0.04, "replicate_rate": 0.05,
      "mutate_rate": 0.02, "innate_count": 25, "adaptive_count": 4,
      "tissue_density": 0.65, "tnf_decay": 0.03, "il6_decay": 0.03,
      "wound_size": 6, "fever_enabled": True, "complement_enabled": True,
      "immunodeficient": True, "allergic": False,
      "vaccination_antigen": None, "cytokine_storm": False}),

    ("Allergic Hypersensitivity",
     "Mast cells degranulate on harmless antigen — histamine flood, excessive inflammation",
     {"pathogen": "bacteria", "invasion_rate": 0.01, "replicate_rate": 0.03,
      "mutate_rate": 0.01, "innate_count": 30, "adaptive_count": 20,
      "tissue_density": 0.70, "tnf_decay": 0.02, "il6_decay": 0.02,
      "wound_size": 4, "fever_enabled": True, "complement_enabled": True,
      "immunodeficient": False, "allergic": True,
      "vaccination_antigen": None, "cytokine_storm": False}),

    ("Vaccination & Re-exposure",
     "Pre-seeded memory cells — watch the rapid secondary response clear pathogens fast",
     {"pathogen": "virus", "invasion_rate": 0.03, "replicate_rate": 0.04,
      "mutate_rate": 0.01, "innate_count": 25, "adaptive_count": 15,
      "tissue_density": 0.70, "tnf_decay": 0.025, "il6_decay": 0.025,
      "wound_size": 5, "fever_enabled": True, "complement_enabled": True,
      "immunodeficient": False, "allergic": False,
      "vaccination_antigen": True, "cytokine_storm": False}),
]


# ══════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════

_NBRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NBRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
           (0, 1), (1, -1), (1, 0), (1, 1)]


def _empty_adj(grid, r, c, rows, cols, include_tissue=False):
    """Return list of adjacent empty (or tissue if allowed) positions."""
    out = []
    for dr, dc in _NBRS4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            if grid[nr][nc] == ENT_EMPTY:
                out.append((nr, nc))
            elif include_tissue and grid[nr][nc] == ENT_TISSUE:
                out.append((nr, nc))
    return out


def _move_toward_gradient(grid, field, r, c, rows, cols):
    """Return best adjacent position following a diffusible field gradient."""
    best_val = field[r][c]
    candidates = []
    for dr, dc in _NBRS4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            v = field[nr][nc]
            if v > best_val and grid[nr][nc] in (ENT_EMPTY, ENT_DEBRIS):
                best_val = v
                candidates.append((nr, nc, v))
    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        return (candidates[0][0], candidates[0][1])
    return None


def _diffuse_field(field, rows, cols, diff_rate, decay_rate, cap=2.0):
    """Diffuse and decay a 2D scalar field via 4-neighbor Laplacian."""
    new = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        rn = min(r + 1, rows - 1)
        rs = max(r - 1, 0)
        for c in range(cols):
            ce = min(c + 1, cols - 1)
            cw = max(c - 1, 0)
            v = field[r][c]
            lap = field[rn][c] + field[rs][c] + field[r][ce] + field[r][cw] - 4.0 * v
            nv = v + diff_rate * lap - decay_rate * v
            new[r][c] = max(0.0, min(cap, nv))
    return new


# ══════════════════════════════════════════════════════════════════════
#  Enter / Exit
# ══════════════════════════════════════════════════════════════════════

def _enter_immune_mode(self):
    """Enter Immune System mode — show preset menu."""
    self.immune_menu = True
    self.immune_menu_sel = 0
    self._flash("Immune System Response & Pathogen Defense — select scenario")


def _exit_immune_mode(self):
    """Exit Immune System mode."""
    self.immune_mode = False
    self.immune_menu = False
    self.immune_running = False
    for attr in list(vars(self)):
        if attr.startswith('immune_') and attr not in ('immune_mode',):
            try:
                delattr(self, attr)
            except AttributeError:
                pass
    self._flash("Immune System mode OFF")


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _immune_init(self, preset_idx: int):
    """Initialize the Immune System simulation with the given preset."""
    name, _desc, settings = IMMUNE_PRESETS[preset_idx]

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(30, max_y - 4)
    cols = max(30, (max_x - 1) // 2)

    self.immune_rows = rows
    self.immune_cols = cols
    self.immune_preset_name = name
    self.immune_preset_idx = preset_idx
    self.immune_generation = 0
    self.immune_steps_per_frame = 1
    self.immune_settings = dict(settings)
    self.immune_view = "cells"  # cells | heatmap | graphs

    # Entity grid
    self.immune_grid = [[ENT_EMPTY] * cols for _ in range(rows)]
    # Per-cell antigen (pathogens/infected) or receptor (immune cells)
    self.immune_antigen_map = [[0] * cols for _ in range(rows)]
    self.immune_receptor_map = [[0] * cols for _ in range(rows)]
    # Cell age
    self.immune_age = [[0] * cols for _ in range(rows)]
    # Activation state for T cells (0=naive, 1=activated)
    self.immune_activated = [[0] * cols for _ in range(rows)]

    # Diffusible fields
    self.immune_cytokine = [[0.0] * cols for _ in range(rows)]   # TNF-α
    self.immune_il6 = [[0.0] * cols for _ in range(rows)]        # IL-6
    self.immune_antibody = [[0.0] * cols for _ in range(rows)]   # antibody concentration
    self.immune_complement = [[0.0] * cols for _ in range(rows)] # complement proteins

    # Dominant pathogen antigen
    self.immune_pathogen_antigen = _rand_antigen()

    # Wound breach location (center of one edge)
    wound_size = settings["wound_size"]
    self.immune_wound_r = rows // 2
    self.immune_wound_c = 0  # left edge
    self.immune_wound_size = wound_size

    # Fever state
    self.immune_fever = 37.0  # body temperature in °C
    self.immune_fever_enabled = settings["fever_enabled"]

    # Complement enabled
    self.immune_complement_enabled = settings["complement_enabled"]

    # Statistics
    self.immune_stats = {
        "pathogens_killed": 0, "tissue_lost": 0,
        "immune_deaths": 0, "antibodies_made": 0,
        "complement_kills": 0, "fever_damage": 0,
    }

    # Time-series history for sparkline graphs
    self.immune_history = {
        'pathogen_load': [], 'immune_cells': [], 'inflammation': [],
        'antibody_titer': [], 'tissue_damage': [], 'fever_temp': [],
        'neutrophils': [], 'tcells': [], 'bcells': [],
        'memory_cells': [],
    }

    # Place tissue
    tissue_density = settings["tissue_density"]
    for r in range(rows):
        for c in range(cols):
            if random.random() < tissue_density:
                self.immune_grid[r][c] = ENT_TISSUE

    # Carve wound breach (gap in tissue at left edge)
    wr = self.immune_wound_r
    for dr in range(-wound_size, wound_size + 1):
        for dc in range(0, wound_size):
            rr, cc = wr + dr, dc
            if 0 <= rr < rows and 0 <= cc < cols:
                self.immune_grid[rr][cc] = ENT_EMPTY

    # Place initial pathogens through the wound
    pathogen_type = ENT_BACTERIA if settings["pathogen"] == "bacteria" else ENT_VIRUS
    n_initial = max(5, int(settings["invasion_rate"] * wound_size * 8))
    for _ in range(n_initial):
        rr = wr + random.randint(-wound_size, wound_size)
        cc = random.randint(0, wound_size + 2)
        rr = max(0, min(rows - 1, rr))
        cc = max(0, min(cols - 1, cc))
        if self.immune_grid[rr][cc] in (ENT_EMPTY, ENT_TISSUE):
            if self.immune_grid[rr][cc] == ENT_TISSUE:
                self.immune_stats["tissue_lost"] += 1
            self.immune_grid[rr][cc] = pathogen_type
            ag = self.immune_pathogen_antigen
            if random.random() < 0.1:
                ag ^= (1 << random.randint(0, ANTIGEN_BITS - 1))
            self.immune_antigen_map[rr][cc] = ag
            self.immune_cytokine[rr][cc] = 0.3

    # Place innate immune cells (scattered in tissue)
    innate_count = settings["innate_count"]
    for _ in range(innate_count):
        r, c = random.randint(3, rows - 4), random.randint(wound_size + 3, cols - 4)
        if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
            roll = random.random()
            if roll < 0.35:
                etype = ENT_MACROPHAGE
            elif roll < 0.70:
                etype = ENT_NEUTROPHIL
            else:
                etype = ENT_DENDRITIC
            self.immune_grid[r][c] = etype
            self.immune_age[r][c] = 0

    # Place adaptive immune cells (near center — "lymph node" area)
    adaptive_count = settings["adaptive_count"]
    cr, cc_center = rows // 2, cols * 3 // 4  # lymph node region
    for _ in range(adaptive_count):
        r = cr + random.randint(-8, 8)
        c = cc_center + random.randint(-6, 6)
        r = max(0, min(rows - 1, r))
        c = max(0, min(cols - 1, c))
        if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
            roll = random.random()
            if roll < 0.5:
                etype = ENT_NAIVE_T
            else:
                etype = ENT_BCELL
            self.immune_grid[r][c] = etype
            self.immune_receptor_map[r][c] = _rand_antigen()
            self.immune_age[r][c] = 0

    # Immunodeficiency: cull most T cells
    if settings.get("immunodeficient"):
        for r in range(rows):
            for c in range(cols):
                if self.immune_grid[r][c] in (ENT_NAIVE_T, ENT_HELPER_T, ENT_KILLER_T):
                    if random.random() < 0.8:
                        self.immune_grid[r][c] = ENT_EMPTY
                        self.immune_age[r][c] = 0

    # Allergic hypersensitivity: add mast cells
    if settings.get("allergic"):
        for _ in range(25):
            r = random.randint(3, rows - 4)
            c = random.randint(3, cols - 4)
            if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
                self.immune_grid[r][c] = ENT_MAST
                # Mast cells are pre-sensitized — receptor matches pathogen
                self.immune_receptor_map[r][c] = self.immune_pathogen_antigen
                self.immune_age[r][c] = 0

    # Vaccination: pre-seed memory cells with matching receptors
    if settings.get("vaccination_antigen"):
        for _ in range(25):
            r = cr + random.randint(-6, 6)
            c = cc_center + random.randint(-6, 6)
            r = max(0, min(rows - 1, r))
            c = max(0, min(cols - 1, c))
            if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
                self.immune_grid[r][c] = ENT_MEMORY
                receptor = self.immune_pathogen_antigen
                if random.random() < 0.15:
                    receptor ^= (1 << random.randint(0, ANTIGEN_BITS - 1))
                self.immune_receptor_map[r][c] = receptor
                self.immune_age[r][c] = 0

    # Seed complement in blood (everywhere at low level)
    if self.immune_complement_enabled:
        for r in range(rows):
            for c in range(cols):
                self.immune_complement[r][c] = 0.1

    self.immune_mode = True
    self.immune_menu = False
    self.immune_running = False
    self._flash(f"Immune System: {name} — Space to start")


# ══════════════════════════════════════════════════════════════════════
#  Simulation Step
# ══════════════════════════════════════════════════════════════════════

def _immune_step(self):
    """Advance the immune simulation by one tick."""
    grid = self.immune_grid
    cyto = self.immune_cytokine
    il6 = self.immune_il6
    ab_field = self.immune_antibody
    comp = self.immune_complement
    ag_map = self.immune_antigen_map
    rec_map = self.immune_receptor_map
    age = self.immune_age
    activated = self.immune_activated
    rows, cols = self.immune_rows, self.immune_cols
    settings = self.immune_settings
    gen = self.immune_generation
    stats = self.immune_stats

    replicate_rate = settings["replicate_rate"]
    mutate_rate = settings["mutate_rate"]
    cytokine_storm = settings["cytokine_storm"]

    # Fever multiplier: boosts immune kinetics but damages tissue at high temp
    fever = self.immune_fever
    fever_mult = 1.0 + max(0.0, (fever - 37.0)) * 0.08  # ~1.24 at 40°C

    # ── 1. Diffuse and decay fields ─────────────────────────────────
    self.immune_cytokine = _diffuse_field(cyto, rows, cols, 0.08,
                                          settings["tnf_decay"])
    cyto = self.immune_cytokine
    self.immune_il6 = _diffuse_field(il6, rows, cols, 0.09,
                                     settings["il6_decay"])
    il6 = self.immune_il6
    self.immune_antibody = _diffuse_field(ab_field, rows, cols, 0.12, 0.008)
    ab_field = self.immune_antibody
    if self.immune_complement_enabled:
        self.immune_complement = _diffuse_field(comp, rows, cols, 0.10, 0.005,
                                                cap=1.5)
        comp = self.immune_complement

    # ── 2. Fever dynamics ───────────────────────────────────────────
    if self.immune_fever_enabled:
        # Total inflammation drives fever
        total_il6 = 0.0
        for r in range(rows):
            for c in range(cols):
                total_il6 += il6[r][c]
        norm_il6 = total_il6 / (rows * cols)
        # Fever rises toward target based on IL-6; decays toward 37
        target_temp = 37.0 + min(5.0, norm_il6 * 30.0)
        self.immune_fever += (target_temp - self.immune_fever) * 0.05
        self.immune_fever = max(36.0, min(42.0, self.immune_fever))
        fever = self.immune_fever
        fever_mult = 1.0 + max(0.0, (fever - 37.0)) * 0.08

        # High fever damages tissue
        if fever > 40.0:
            dmg_prob = (fever - 40.0) * 0.003
            for r in range(rows):
                for c in range(cols):
                    if grid[r][c] == ENT_TISSUE and random.random() < dmg_prob:
                        grid[r][c] = ENT_DEBRIS
                        age[r][c] = 0
                        stats["tissue_lost"] += 1
                        stats["fever_damage"] += 1

    # ── 3. Build action lists (synchronous update) ──────────────────
    moves = []
    kills = []
    spawns = []
    infections = []

    pathogen_count = 0
    immune_count = 0
    neut_count = 0
    tcell_count = 0
    bcell_count = 0
    memory_count = 0

    for r in range(rows):
        for c in range(cols):
            et = grid[r][c]
            if et == ENT_EMPTY or et == ENT_TISSUE:
                continue

            if et == ENT_DEBRIS:
                age[r][c] += 1
                if age[r][c] > 8:
                    kills.append((r, c))
                continue

            age[r][c] += 1
            cell_age = age[r][c]

            # ── PATHOGENS ──────────────────────────────────────
            if et == ENT_BACTERIA:
                pathogen_count += 1
                # Emit TNF-α (danger signal)
                cyto[r][c] = min(2.0, cyto[r][c] + 0.12)
                il6[r][c] = min(2.0, il6[r][c] + 0.06)

                # Opsonization check: antibody field marks for phagocytosis
                opsonized = ab_field[r][c] > 0.15

                # Complement membrane attack
                if self.immune_complement_enabled and comp[r][c] > 0.4:
                    if random.random() < 0.06 * comp[r][c] * fever_mult:
                        kills.append((r, c))
                        stats["complement_kills"] += 1
                        stats["pathogens_killed"] += 1
                        continue

                # Replicate (slowed if opsonized)
                rep_rate = replicate_rate * (0.4 if opsonized else 1.0)
                if random.random() < rep_rate:
                    targets = _empty_adj(grid, r, c, rows, cols,
                                         include_tissue=True)
                    if targets:
                        nr, nc = random.choice(targets)
                        new_ag = ag_map[r][c]
                        if random.random() < mutate_rate:
                            new_ag ^= (1 << random.randint(0,
                                                           ANTIGEN_BITS - 1))
                        if grid[nr][nc] == ENT_TISSUE:
                            stats["tissue_lost"] += 1
                        spawns.append((nr, nc, ENT_BACTERIA, new_ag, 0))
                elif random.random() < 0.3:
                    adj = _empty_adj(grid, r, c, rows, cols,
                                     include_tissue=True)
                    if adj:
                        nr, nc = random.choice(adj)
                        if grid[nr][nc] == ENT_TISSUE:
                            stats["tissue_lost"] += 1
                        moves.append((r, c, nr, nc))

            elif et == ENT_VIRUS:
                pathogen_count += 1
                cyto[r][c] = min(2.0, cyto[r][c] + 0.08)

                # Complement neutralization
                if self.immune_complement_enabled and comp[r][c] > 0.5:
                    if random.random() < 0.04 * comp[r][c]:
                        kills.append((r, c))
                        stats["complement_kills"] += 1
                        stats["pathogens_killed"] += 1
                        continue

                # Antibody neutralization (opsonization)
                if ab_field[r][c] > 0.3 and random.random() < 0.08:
                    kills.append((r, c))
                    stats["pathogens_killed"] += 1
                    continue

                # Infect adjacent tissue
                if random.random() < replicate_rate:
                    adj = _empty_adj(grid, r, c, rows, cols,
                                     include_tissue=True)
                    tissue_adj = [(nr, nc) for nr, nc in adj
                                  if grid[nr][nc] == ENT_TISSUE]
                    if tissue_adj:
                        nr, nc = random.choice(tissue_adj)
                        infections.append((nr, nc))
                        ag_map[nr][nc] = ag_map[r][c]
                        kills.append((r, c))
                    else:
                        empty_adj = [(nr, nc) for nr, nc in adj
                                     if grid[nr][nc] == ENT_EMPTY]
                        if empty_adj:
                            nr, nc = random.choice(empty_adj)
                            moves.append((r, c, nr, nc))

            elif et == ENT_INFECTED:
                pathogen_count += 1
                cyto[r][c] = min(2.0, cyto[r][c] + 0.18)
                il6[r][c] = min(2.0, il6[r][c] + 0.10)

                # Intracellular viral replication — burst release
                if cell_age > 5 and random.random() < replicate_rate * 0.7:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        new_ag = ag_map[r][c]
                        if random.random() < mutate_rate:
                            new_ag ^= (1 << random.randint(0,
                                                           ANTIGEN_BITS - 1))
                        spawns.append((nr, nc, ENT_VIRUS, new_ag, 0))

                # Lysis after incubation
                if cell_age > 18:
                    kills.append((r, c))
                    stats["tissue_lost"] += 1

            # ── INNATE IMMUNE CELLS ─────────────────────────────
            elif et == ENT_NEUTROPHIL:
                immune_count += 1
                neut_count += 1
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)

                killed_any = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                            # Enhanced kill if opsonized
                            kill_prob = 0.9 if ab_field[nr][nc] > 0.1 else 0.6
                            if random.random() < kill_prob * fever_mult:
                                kills.append((nr, nc))
                                stats["pathogens_killed"] += 1
                                killed_any = True
                                cyto[r][c] = min(2.0, cyto[r][c] + 0.25)
                                # Cytokine storm: collateral tissue damage
                                if cytokine_storm and cyto[r][c] > 1.0:
                                    for dr2, dc2 in _NBRS4:
                                        nr2, nc2 = r + dr2, c + dc2
                                        if (0 <= nr2 < rows and 0 <= nc2 < cols
                                                and grid[nr2][nc2] == ENT_TISSUE
                                                and random.random() < 0.12):
                                            kills.append((nr2, nc2))
                                            stats["tissue_lost"] += 1
                                break

                if not killed_any and target:
                    moves.append((r, c, target[0], target[1]))
                elif not killed_any and random.random() < 0.4:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                # Short lifespan
                if cell_age > 50 or (killed_any and random.random() < 0.25):
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            elif et == ENT_MACROPHAGE:
                immune_count += 1
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)

                ate = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED,
                                  ENT_DEBRIS):
                            kills.append((nr, nc))
                            if nt != ENT_DEBRIS:
                                stats["pathogens_killed"] += 1
                            ate = True
                            # Antigen presentation: boost cytokines to recruit
                            cyto[r][c] = min(2.0, cyto[r][c] + 0.35)
                            il6[r][c] = min(2.0, il6[r][c] + 0.20)
                            # Activate complement cascade near site
                            if self.immune_complement_enabled:
                                comp[r][c] = min(1.5, comp[r][c] + 0.15)
                            break

                if not ate and target:
                    moves.append((r, c, target[0], target[1]))
                elif not ate and random.random() < 0.2:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                if cell_age > 180 and random.random() < 0.01:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            elif et == ENT_DENDRITIC:
                immune_count += 1
                # Dendritic cells patrol, phagocytose, then migrate to
                # "lymph node" region to present antigen and activate T cells
                captured_antigen = ag_map[r][c]

                if captured_antigen == 0:
                    # Patrol: look for pathogens
                    for dr, dc in _NBRS8:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            nt = grid[nr][nc]
                            if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                                ag_map[r][c] = ag_map[nr][nc]
                                kills.append((nr, nc))
                                stats["pathogens_killed"] += 1
                                break
                    # Wander
                    if random.random() < 0.3:
                        target = _move_toward_gradient(grid, cyto, r, c,
                                                       rows, cols)
                        if target:
                            moves.append((r, c, target[0], target[1]))
                        else:
                            adj = _empty_adj(grid, r, c, rows, cols)
                            if adj:
                                nr, nc = random.choice(adj)
                                moves.append((r, c, nr, nc))
                else:
                    # Has antigen — migrate toward lymph node (right side)
                    # and activate nearby naive T cells
                    best = None
                    best_c_val = c
                    for dr, dc in _NBRS4:
                        nr, nc = r + dr, c + dc
                        if (0 <= nr < rows and 0 <= nc < cols
                                and grid[nr][nc] in (ENT_EMPTY, ENT_DEBRIS)):
                            if nc > best_c_val:
                                best = (nr, nc)
                                best_c_val = nc
                    if best:
                        moves.append((r, c, best[0], best[1]))

                    # Activate adjacent naive T cells
                    for dr, dc in _NBRS8:
                        nr, nc = r + dr, c + dc
                        if (0 <= nr < rows and 0 <= nc < cols
                                and grid[nr][nc] == ENT_NAIVE_T):
                            match = _antigen_match(rec_map[nr][nc],
                                                   captured_antigen)
                            if match > 0.55:
                                # Differentiate into helper or killer
                                if random.random() < 0.5:
                                    grid[nr][nc] = ENT_HELPER_T
                                else:
                                    grid[nr][nc] = ENT_KILLER_T
                                activated[nr][nc] = 1
                                age[nr][nc] = 0
                                cyto[nr][nc] = min(2.0,
                                                   cyto[nr][nc] + 0.3)

                if cell_age > 200 and random.random() < 0.01:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            # ── MAST CELLS (allergic) ───────────────────────────
            elif et == ENT_MAST:
                immune_count += 1
                # Degranulate when antigen is nearby
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS):
                            match = _antigen_match(rec_map[r][c],
                                                   ag_map[nr][nc])
                            if match > 0.5:
                                # Histamine release — massive cytokine burst
                                for dr2 in range(-2, 3):
                                    for dc2 in range(-2, 3):
                                        rr, cc2 = r + dr2, c + dc2
                                        if 0 <= rr < rows and 0 <= cc2 < cols:
                                            cyto[rr][cc2] = min(
                                                2.0, cyto[rr][cc2] + 0.4)
                                            il6[rr][cc2] = min(
                                                2.0, il6[rr][cc2] + 0.3)
                                # Tissue damage from allergic inflammation
                                if settings.get("allergic"):
                                    for dr2, dc2 in _NBRS4:
                                        rr, cc2 = r + dr2, c + dc2
                                        if (0 <= rr < rows
                                                and 0 <= cc2 < cols
                                                and grid[rr][cc2] == ENT_TISSUE
                                                and random.random() < 0.08):
                                            kills.append((rr, cc2))
                                            stats["tissue_lost"] += 1
                                break

            # ── ADAPTIVE: NAIVE T CELLS ─────────────────────────
            elif et == ENT_NAIVE_T:
                immune_count += 1
                tcell_count += 1
                # Naive T cells wander; dendritic cells activate them
                # But also can self-activate if they encounter antigen
                # with high cytokine costimulation
                receptor = rec_map[r][c]

                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if (nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED)
                                and cyto[r][c] > 0.5):
                            match = _antigen_match(receptor, ag_map[nr][nc])
                            if match > 0.65:
                                if random.random() < 0.5:
                                    grid[r][c] = ENT_HELPER_T
                                else:
                                    grid[r][c] = ENT_KILLER_T
                                activated[r][c] = 1
                                age[r][c] = 0
                                break

                if grid[r][c] == ENT_NAIVE_T:
                    if random.random() < 0.15:
                        adj = _empty_adj(grid, r, c, rows, cols)
                        if adj:
                            nr, nc = random.choice(adj)
                            moves.append((r, c, nr, nc))

                    if cell_age > 200 and random.random() < 0.01:
                        kills.append((r, c))
                        stats["immune_deaths"] += 1

            # ── ADAPTIVE: HELPER T CELLS ────────────────────────
            elif et == ENT_HELPER_T:
                immune_count += 1
                tcell_count += 1
                receptor = rec_map[r][c]

                # Helper T cells amplify the response:
                # - boost cytokines
                # - activate nearby B cells and naive T cells
                # - promote clonal expansion
                cyto[r][c] = min(2.0, cyto[r][c] + 0.08 * fever_mult)
                il6[r][c] = min(2.0, il6[r][c] + 0.05)

                # Activate nearby B cells and naive T cells
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt == ENT_NAIVE_T:
                            if _antigen_match(rec_map[nr][nc],
                                              receptor) > 0.5:
                                if random.random() < 0.15 * fever_mult:
                                    grid[nr][nc] = (ENT_KILLER_T
                                                    if random.random() < 0.6
                                                    else ENT_HELPER_T)
                                    activated[nr][nc] = 1
                                    age[nr][nc] = 0
                        elif nt == ENT_BCELL:
                            if _antigen_match(rec_map[nr][nc],
                                              receptor) > 0.5:
                                # Signal B cell to produce antibodies
                                activated[nr][nc] = 1

                # Clonal expansion
                if random.random() < 0.06 * fever_mult:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        spawns.append((nr, nc, ENT_HELPER_T, 0, receptor))

                # Memory formation
                if cell_age > 40 and random.random() < 0.03:
                    grid[r][c] = ENT_MEMORY
                    age[r][c] = 0

                # Move toward cytokines
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)
                if target:
                    moves.append((r, c, target[0], target[1]))
                elif random.random() < 0.15:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                if cell_age > 120 and random.random() < 0.02:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            # ── ADAPTIVE: KILLER T CELLS ────────────────────────
            elif et == ENT_KILLER_T:
                immune_count += 1
                tcell_count += 1
                receptor = rec_map[r][c]

                # Cytotoxic — kill matching infected/pathogen cells
                killed_target = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                            match = _antigen_match(receptor, ag_map[nr][nc])
                            if match > 0.6:
                                if random.random() < 0.7 * fever_mult:
                                    kills.append((nr, nc))
                                    stats["pathogens_killed"] += 1
                                    killed_target = True
                                    cyto[r][c] = min(2.0,
                                                     cyto[r][c] + 0.3)
                                    break

                # Clonal expansion on kill
                if killed_target and random.random() < 0.12 * fever_mult:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        spawns.append((nr, nc, ENT_KILLER_T, 0, receptor))

                # Memory formation
                if killed_target and cell_age > 30 and random.random() < 0.04:
                    grid[r][c] = ENT_MEMORY
                    age[r][c] = 0

                # Chemotaxis
                if not killed_target:
                    target = _move_toward_gradient(grid, cyto, r, c,
                                                   rows, cols)
                    if target:
                        moves.append((r, c, target[0], target[1]))
                    elif random.random() < 0.2:
                        adj = _empty_adj(grid, r, c, rows, cols)
                        if adj:
                            nr, nc = random.choice(adj)
                            moves.append((r, c, nr, nc))

                if cell_age > 100 and random.random() < 0.02:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            # ── ADAPTIVE: B CELLS ───────────────────────────────
            elif et == ENT_BCELL:
                immune_count += 1
                bcell_count += 1
                receptor = rec_map[r][c]
                is_activated = activated[r][c] > 0

                # Check for antigen in vicinity
                if not is_activated:
                    for dr, dc in _NBRS8:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            nt = grid[nr][nc]
                            if nt in (ENT_BACTERIA, ENT_VIRUS):
                                match = _antigen_match(receptor,
                                                       ag_map[nr][nc])
                                if match > 0.6:
                                    is_activated = True
                                    activated[r][c] = 1
                                    break

                if is_activated:
                    # Produce diffusible antibodies
                    if random.random() < 0.15 * fever_mult:
                        ab_field[r][c] = min(2.0, ab_field[r][c] + 0.25)
                        stats["antibodies_made"] += 1

                    # Clonal expansion
                    if random.random() < 0.08 * fever_mult:
                        adj = _empty_adj(grid, r, c, rows, cols)
                        if adj:
                            nr, nc = random.choice(adj)
                            spawns.append((nr, nc, ENT_BCELL, 0, receptor))

                    # Memory formation
                    if cell_age > 30 and random.random() < 0.04:
                        grid[r][c] = ENT_MEMORY
                        age[r][c] = 0

                # Move
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)
                if not is_activated and target:
                    moves.append((r, c, target[0], target[1]))
                elif not is_activated and random.random() < 0.12:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                if cell_age > 120 and random.random() < 0.02:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            # ── MEMORY CELLS ────────────────────────────────────
            elif et == ENT_MEMORY:
                immune_count += 1
                memory_count += 1
                receptor = rec_map[r][c]

                # Dormant until matching antigen detected — then rapid
                # reactivation with clonal burst (secondary response)
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                            match = _antigen_match(receptor, ag_map[nr][nc])
                            if match > 0.55:
                                # Rapid reactivation — spawn effectors
                                adj = _empty_adj(grid, r, c, rows, cols)
                                for pos in adj[:4]:
                                    roll = random.random()
                                    if roll < 0.4:
                                        etype = ENT_KILLER_T
                                    elif roll < 0.7:
                                        etype = ENT_HELPER_T
                                    else:
                                        etype = ENT_BCELL
                                    spawns.append((pos[0], pos[1], etype, 0,
                                                   receptor))
                                cyto[r][c] = min(2.0, cyto[r][c] + 0.5)
                                # Produce antibodies immediately
                                ab_field[r][c] = min(2.0,
                                                     ab_field[r][c] + 0.3)
                                break

                # Slow patrol
                if random.random() < 0.04:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

    # ── 4. Apply changes ────────────────────────────────────────────
    killed_set = set()
    for r, c in kills:
        if (r, c) not in killed_set:
            killed_set.add((r, c))
            old = grid[r][c]
            if old in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED,
                       ENT_MACROPHAGE, ENT_NEUTROPHIL, ENT_NAIVE_T,
                       ENT_HELPER_T, ENT_KILLER_T, ENT_BCELL, ENT_DENDRITIC):
                grid[r][c] = ENT_DEBRIS
                age[r][c] = 0
            else:
                grid[r][c] = ENT_EMPTY
                age[r][c] = 0
            ag_map[r][c] = 0
            rec_map[r][c] = 0
            activated[r][c] = 0

    moved_from = set()
    moved_to = set()
    for r, c, nr, nc in moves:
        if ((r, c) in killed_set or (r, c) in moved_from
                or (nr, nc) in moved_to or (nr, nc) in killed_set):
            continue
        if grid[nr][nc] not in (ENT_EMPTY, ENT_DEBRIS):
            continue
        grid[nr][nc] = grid[r][c]
        ag_map[nr][nc] = ag_map[r][c]
        rec_map[nr][nc] = rec_map[r][c]
        age[nr][nc] = age[r][c]
        activated[nr][nc] = activated[r][c]
        grid[r][c] = ENT_EMPTY
        ag_map[r][c] = 0
        rec_map[r][c] = 0
        age[r][c] = 0
        activated[r][c] = 0
        moved_from.add((r, c))
        moved_to.add((nr, nc))

    for r, c, etype, antigen, receptor in spawns:
        if grid[r][c] in (ENT_EMPTY, ENT_DEBRIS) and (r, c) not in moved_to:
            grid[r][c] = etype
            ag_map[r][c] = antigen
            rec_map[r][c] = receptor
            age[r][c] = 0
            activated[r][c] = 0

    for r, c in infections:
        if grid[r][c] == ENT_TISSUE:
            grid[r][c] = ENT_INFECTED
            age[r][c] = 0

    # ── 5. Ongoing pathogen invasion through wound ──────────────────
    if gen % 4 == 0 and gen < 400:
        inv_rate = settings["invasion_rate"] * max(0.15, 1.0 - gen / 500.0)
        pathogen_type = (ENT_BACTERIA
                         if settings["pathogen"] == "bacteria"
                         else ENT_VIRUS)
        wr = self.immune_wound_r
        ws = self.immune_wound_size
        n_invaders = max(1, int(inv_rate * ws * 3))
        for _ in range(n_invaders):
            rr = wr + random.randint(-ws, ws)
            cc = random.randint(0, max(1, ws // 2))
            rr = max(0, min(rows - 1, rr))
            cc = max(0, min(cols - 1, cc))
            if grid[rr][cc] in (ENT_EMPTY, ENT_TISSUE):
                if grid[rr][cc] == ENT_TISSUE:
                    stats["tissue_lost"] += 1
                grid[rr][cc] = pathogen_type
                ag = self.immune_pathogen_antigen
                if random.random() < mutate_rate:
                    ag ^= (1 << random.randint(0, ANTIGEN_BITS - 1))
                ag_map[rr][cc] = ag
                age[rr][cc] = 0

    # ── 6. Bone marrow reinforcements ───────────────────────────────
    if gen % 12 == 0:
        max_cyto_val = 0.0
        for r in range(rows):
            for c in range(cols):
                if cyto[r][c] > max_cyto_val:
                    max_cyto_val = cyto[r][c]
        if max_cyto_val > 0.2:
            cr_bm = rows // 2
            cc_bm = cols * 3 // 4
            n_reinforce = 2 if not settings.get("immunodeficient") else 1
            for _ in range(n_reinforce):
                r = cr_bm + random.randint(-6, 6)
                c = cc_bm + random.randint(-6, 6)
                r = max(0, min(rows - 1, r))
                c = max(0, min(cols - 1, c))
                if grid[r][c] in (ENT_EMPTY, ENT_DEBRIS):
                    roll = random.random()
                    if roll < 0.3:
                        etype = ENT_MACROPHAGE
                    elif roll < 0.55:
                        etype = ENT_NEUTROPHIL
                    elif roll < 0.7:
                        etype = ENT_DENDRITIC
                    else:
                        etype = ENT_NAIVE_T
                    grid[r][c] = etype
                    rec_map[r][c] = (_rand_antigen()
                                     if etype == ENT_NAIVE_T else 0)
                    age[r][c] = 0

    # ── 7. Complement replenishment ─────────────────────────────────
    if self.immune_complement_enabled and gen % 8 == 0:
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == ENT_TISSUE:
                    comp[r][c] = min(1.5, comp[r][c] + 0.02)

    # ── 8. Record metrics ───────────────────────────────────────────
    hist = self.immune_history
    hist['pathogen_load'].append(pathogen_count)
    hist['immune_cells'].append(immune_count)

    # Total inflammation = sum of TNF-α + IL-6
    total_inflam = 0.0
    total_ab = 0.0
    for r in range(rows):
        for c in range(cols):
            total_inflam += cyto[r][c] + il6[r][c]
            total_ab += ab_field[r][c]
    hist['inflammation'].append(total_inflam / max(1, rows * cols) * 10)
    hist['antibody_titer'].append(total_ab / max(1, rows * cols) * 10)
    hist['tissue_damage'].append(stats["tissue_lost"])
    hist['fever_temp'].append(self.immune_fever)
    hist['neutrophils'].append(neut_count)
    hist['tcells'].append(tcell_count)
    hist['bcells'].append(bcell_count)
    hist['memory_cells'].append(memory_count)

    # Trim histories
    max_hist = 500
    for key in hist:
        if len(hist[key]) > max_hist:
            hist[key] = hist[key][-max_hist:]

    self.immune_generation += 1


# ══════════════════════════════════════════════════════════════════════
#  Input Handling
# ══════════════════════════════════════════════════════════════════════

def _handle_immune_menu_key(self, key: int) -> bool:
    """Handle input in Immune System preset menu."""
    presets = IMMUNE_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.immune_menu_sel = (self.immune_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.immune_menu_sel = (self.immune_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        _immune_init(self, self.immune_menu_sel)
    elif key == ord("q") or key == 27:
        self.immune_menu = False
        self._exit_immune_mode()
    return True


def _handle_immune_key(self, key: int) -> bool:
    """Handle input in active Immune System simulation."""
    if key == ord("q") or key == 27:
        self._exit_immune_mode()
        return True
    if key == ord(" "):
        self.immune_running = not self.immune_running
        return True
    if key == ord("n") or key == ord("."):
        _immune_step(self)
        return True
    if key == ord("r"):
        _immune_init(self, self.immune_preset_idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.immune_mode = False
        self.immune_running = False
        self.immune_menu = True
        self.immune_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20]
        idx = (choices.index(self.immune_steps_per_frame)
               if self.immune_steps_per_frame in choices else 0)
        self.immune_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.immune_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20]
        idx = (choices.index(self.immune_steps_per_frame)
               if self.immune_steps_per_frame in choices else 0)
        self.immune_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.immune_steps_per_frame} steps/frame")
        return True
    if key == ord("v"):
        views = ["cells", "heatmap", "graphs"]
        idx = views.index(self.immune_view) if self.immune_view in views else 0
        self.immune_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.immune_view}")
        return True
    # Inject pathogen wave
    if key == ord("p"):
        pathogen_type = (ENT_BACTERIA
                         if self.immune_settings["pathogen"] == "bacteria"
                         else ENT_VIRUS)
        rows, cols = self.immune_rows, self.immune_cols
        wr = self.immune_wound_r
        ws = self.immune_wound_size
        for _ in range(20):
            rr = wr + random.randint(-ws - 3, ws + 3)
            cc = random.randint(0, ws + 4)
            rr = max(0, min(rows - 1, rr))
            cc = max(0, min(cols - 1, cc))
            if self.immune_grid[rr][cc] in (ENT_EMPTY, ENT_TISSUE):
                self.immune_grid[rr][cc] = pathogen_type
                ag = self.immune_pathogen_antigen
                if random.random() < 0.15:
                    ag ^= (1 << random.randint(0, ANTIGEN_BITS - 1))
                self.immune_antigen_map[rr][cc] = ag
        self._flash("Pathogen wave injected!")
        return True
    # Inject immune boost
    if key == ord("i"):
        rows, cols = self.immune_rows, self.immune_cols
        cr, cc2 = rows // 2, cols * 3 // 4
        for _ in range(12):
            r = cr + random.randint(-8, 8)
            c = cc2 + random.randint(-8, 8)
            r = max(0, min(rows - 1, r))
            c = max(0, min(cols - 1, c))
            if self.immune_grid[r][c] in (ENT_EMPTY, ENT_DEBRIS):
                roll = random.random()
                if roll < 0.3:
                    etype = ENT_KILLER_T
                elif roll < 0.5:
                    etype = ENT_HELPER_T
                elif roll < 0.7:
                    etype = ENT_BCELL
                else:
                    etype = ENT_NEUTROPHIL
                self.immune_grid[r][c] = etype
                self.immune_receptor_map[r][c] = _rand_antigen()
                self.immune_age[r][c] = 0
        self._flash("Immune boost deployed!")
        return True
    # Mutate pathogen
    if key == ord("u"):
        bit = random.randint(0, ANTIGEN_BITS - 1)
        self.immune_pathogen_antigen ^= (1 << bit)
        self._flash(
            f"Pathogen mutated! Antigen: {self.immune_pathogen_antigen:06b}")
        return True
    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Preset Menu
# ══════════════════════════════════════════════════════════════════════

def _draw_immune_menu(self, max_y: int, max_x: int):
    """Draw the Immune System preset selection menu."""
    self.stdscr.erase()
    title = "── Immune System Response & Pathogen Defense ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    sub = "Select a scenario:"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(sub)) // 2), sub)
    except curses.error:
        pass

    for i, (pname, desc, _s) in enumerate(IMMUNE_PRESETS):
        y = 5 + i * 3
        if y + 1 >= max_y - 2:
            break
        marker = ">" if i == self.immune_menu_sel else " "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.immune_menu_sel
                else curses.color_pair(7))
        try:
            self.stdscr.addstr(y, 4, f" {marker} {pname}", attr)
        except curses.error:
            pass
        desc_attr = (curses.color_pair(6) if i == self.immune_menu_sel
                     else curses.color_pair(7) | curses.A_DIM)
        try:
            self.stdscr.addstr(y + 1, 8, desc[:max_x - 10], desc_attr)
        except curses.error:
            pass

    legend_y = 5 + len(IMMUNE_PRESETS) * 3 + 1
    if legend_y + 2 < max_y - 2:
        legend_lines = [
            "@@ bacteria  vv virus  xx infected  .. tissue  :: debris",
            "MM macro  NN neutrophil  DC dendritic  !! mast  Tn/Th/Tk T-cells  BB B-cell  ** memory",
        ]
        for i, line in enumerate(legend_lines):
            if legend_y + i < max_y - 2:
                try:
                    self.stdscr.addstr(legend_y + i, 4, line[:max_x - 6],
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

    hint = "[j/k] select  [Enter] start  [q] back"
    try:
        self.stdscr.addstr(max_y - 1, max(0, (max_x - len(hint)) // 2), hint,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Main Dispatch
# ══════════════════════════════════════════════════════════════════════

def _draw_immune(self, max_y: int, max_x: int):
    """Dispatch to current view."""
    if self.immune_view == "cells":
        _draw_immune_cells(self, max_y, max_x)
    elif self.immune_view == "heatmap":
        _draw_immune_heatmap(self, max_y, max_x)
    elif self.immune_view == "graphs":
        _draw_immune_graphs(self, max_y, max_x)


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Tissue Map View
# ══════════════════════════════════════════════════════════════════════

def _draw_immune_cells(self, max_y: int, max_x: int):
    """Draw tissue map with immune cell glyphs, pathogens, wound site."""
    self.stdscr.erase()
    grid = self.immune_grid
    rows, cols = self.immune_rows, self.immune_cols
    stats = self.immune_stats

    # Count entities
    counts = {}
    for r in range(rows):
        for c in range(cols):
            et = grid[r][c]
            if et != ENT_EMPTY:
                counts[et] = counts.get(et, 0) + 1

    pathogen_n = (counts.get(ENT_BACTERIA, 0) + counts.get(ENT_VIRUS, 0)
                  + counts.get(ENT_INFECTED, 0))
    immune_n = (counts.get(ENT_MACROPHAGE, 0) + counts.get(ENT_NEUTROPHIL, 0)
                + counts.get(ENT_NAIVE_T, 0) + counts.get(ENT_HELPER_T, 0)
                + counts.get(ENT_KILLER_T, 0) + counts.get(ENT_BCELL, 0)
                + counts.get(ENT_MEMORY, 0) + counts.get(ENT_DENDRITIC, 0)
                + counts.get(ENT_MAST, 0))

    # Title bar
    fever_str = f"{self.immune_fever:.1f}C" if self.immune_fever_enabled else ""
    state = "RUN" if self.immune_running else "PAUSED"
    title = (f" {self.immune_preset_name} | gen {self.immune_generation}"
             f" | path={pathogen_n} imm={immune_n}"
             f" tissue={counts.get(ENT_TISSUE, 0)}"
             f" | {fever_str} | {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Color mapping
    cell_colors = {
        ENT_TISSUE: curses.color_pair(2) | curses.A_DIM,
        ENT_INFECTED: curses.color_pair(1) | curses.A_BOLD,
        ENT_BACTERIA: curses.color_pair(1) | curses.A_BOLD,
        ENT_VIRUS: curses.color_pair(5) | curses.A_BOLD,
        ENT_MACROPHAGE: curses.color_pair(6) | curses.A_BOLD,
        ENT_NEUTROPHIL: curses.color_pair(7) | curses.A_BOLD,
        ENT_NAIVE_T: curses.color_pair(4),
        ENT_HELPER_T: curses.color_pair(3) | curses.A_BOLD,
        ENT_KILLER_T: curses.color_pair(4) | curses.A_BOLD,
        ENT_BCELL: curses.color_pair(3) | curses.A_BOLD,
        ENT_MEMORY: curses.color_pair(5),
        ENT_DEBRIS: curses.color_pair(7) | curses.A_DIM,
        ENT_MAST: curses.color_pair(1) | curses.A_BOLD,
        ENT_DENDRITIC: curses.color_pair(6),
    }

    # Draw wound marker on left edge
    wr = self.immune_wound_r
    ws = self.immune_wound_size
    for dr in range(-ws, ws + 1):
        rr = wr + dr
        if 0 <= rr < view_rows:
            try:
                self.stdscr.addstr(1 + rr, 0, "W",
                                   curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

    for r in range(view_rows):
        sy = 1 + r
        for c in range(view_cols):
            sx = c * 2
            et = grid[r][c]
            if et == ENT_EMPTY:
                continue
            ch = ENT_CHARS.get(et, "??")
            attr = cell_colors.get(et, curses.color_pair(7))
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Stats line
    s = stats
    stat_line = (f" killed={s['pathogens_killed']} tissue_lost={s['tissue_lost']}"
                 f" Ab={s['antibodies_made']} comp={s['complement_kills']}"
                 f" mem={counts.get(ENT_MEMORY, 0)}"
                 f" fever_dmg={s['fever_damage']}")
    try:
        self.stdscr.addstr(max_y - 2, 0, stat_line[:max_x - 1],
                           curses.color_pair(7))
    except curses.error:
        pass

    # Hint bar
    now = time.monotonic()
    if hasattr(self, 'message') and self.message and now - self.message_time < 3.0:
        hint = f" {self.message}"
    else:
        hint = " [Space] [n]step [v]iew [p]athogen [i]mmune [u]mutate [+/-]speed [r]eset [R]menu [q]uit"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Cytokine/Antibody Heatmap
# ══════════════════════════════════════════════════════════════════════

def _draw_immune_heatmap(self, max_y: int, max_x: int):
    """Draw cytokine and antibody heatmap overlay."""
    self.stdscr.erase()
    cyto = self.immune_cytokine
    il6 = self.immune_il6
    ab_field = self.immune_antibody
    comp = self.immune_complement
    rows, cols = self.immune_rows, self.immune_cols

    title = (f" Heatmap: TNF-a(red) + IL-6(yellow) + Antibody(cyan)"
             f" + Complement(blue) | gen {self.immune_generation}"
             f" | fever {self.immune_fever:.1f}C")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    heat_chars = " .,:;+=*#@"

    for r in range(view_rows):
        sy = 1 + r
        for c in range(view_cols):
            sx = c * 2
            # Combine fields
            tnf_v = cyto[r][c]
            il6_v = il6[r][c]
            ab_v = ab_field[r][c]
            comp_v = comp[r][c] if self.immune_complement_enabled else 0.0

            # Pick dominant field for color
            vals = [tnf_v, il6_v, ab_v, comp_v]
            max_v = max(vals)
            if max_v < 0.03:
                continue

            idx = int(min(max_v, 2.0) / 2.0 * (len(heat_chars) - 1))
            idx = max(0, min(len(heat_chars) - 1, idx))
            ch = heat_chars[idx] * 2

            # Color by dominant
            dom = vals.index(max_v)
            if dom == 0:
                cp = curses.color_pair(1)  # red — TNF-α
            elif dom == 1:
                cp = curses.color_pair(3)  # yellow — IL-6
            elif dom == 2:
                cp = curses.color_pair(6)  # cyan — antibody
            else:
                cp = curses.color_pair(4)  # blue — complement

            if max_v > 1.0:
                cp |= curses.A_BOLD

            try:
                self.stdscr.addstr(sy, sx, ch, cp)
            except curses.error:
                pass

    hint = " [v]iew [Space]pause [q]uit"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Time-Series Sparkline Graphs
# ══════════════════════════════════════════════════════════════════════

def _draw_immune_graphs(self, max_y: int, max_x: int):
    """Time-series sparkline graphs for immune metrics."""
    self.stdscr.erase()
    hist = self.immune_history
    graph_w = min(200, max_x - 30)

    title = (f" Immune Metrics — {self.immune_preset_name}"
             f" | gen {self.immune_generation}")
    try:
        self.stdscr.addstr(0, 2, title, curses.A_BOLD)
    except curses.error:
        pass

    labels = [
        ("Pathogen Load",    'pathogen_load',   1),
        ("Immune Cells",     'immune_cells',    2),
        ("Inflammation",     'inflammation',    1),
        ("Antibody Titer",   'antibody_titer',  6),
        ("Tissue Damage",    'tissue_damage',   1),
        ("Fever (C)",        'fever_temp',      3),
        ("Neutrophils",      'neutrophils',     7),
        ("T-cells",          'tcells',          4),
        ("B-cells",          'bcells',          3),
        ("Memory Cells",     'memory_cells',    5),
    ]

    bars = "▁▂▃▄▅▆▇█"
    n_bars = len(bars)

    for gi, (label, key, cp) in enumerate(labels):
        base_y = 2 + gi * 2
        if base_y + 1 >= max_y - 2:
            break

        data = hist.get(key, [])
        cur_val = data[-1] if data else 0
        if isinstance(cur_val, float):
            lbl = f"{label}: {cur_val:.2f}"
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
                bar_idx = int((v - mn) / rng * (n_bars - 1))
                bar_idx = max(0, min(n_bars - 1, bar_idx))
                try:
                    self.stdscr.addstr(base_y, x, bars[bar_idx], color)
                except curses.error:
                    pass

    hint = " [v]iew [Space]pause [q]uit"
    try:
        self.stdscr.addstr(max_y - 1, 2, hint[:max_x - 3],
                           curses.color_pair(7))
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register immune system mode methods on the App class."""
    App._enter_immune_mode = _enter_immune_mode
    App._exit_immune_mode = _exit_immune_mode
    App._immune_init = _immune_init
    App._immune_step = _immune_step
    App._handle_immune_menu_key = _handle_immune_menu_key
    App._handle_immune_key = _handle_immune_key
    App._draw_immune_menu = _draw_immune_menu
    App._draw_immune = _draw_immune
    App.IMMUNE_PRESETS = IMMUNE_PRESETS
