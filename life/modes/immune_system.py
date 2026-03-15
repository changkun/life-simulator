"""Mode: immune_system — adaptive immune response simulation.

A 2D spatial simulation of innate and adaptive immunity.  Pathogens
(bacteria / viruses) invade and replicate.  Innate responders (macrophages,
neutrophils) rush to infection sites via chemotaxis on a cytokine gradient.
Adaptive immune cells (T-cells, B-cells) recognize antigen shapes,
proliferate on match, and form long-lived memory cells for faster secondary
responses.  Pathogens mutate over time, driving an evolutionary arms race.

Presets: Bacterial Invasion, Viral Outbreak, Vaccination, Autoimmune,
Cytokine Storm.
"""
import curses
import math
import random
import time

# ── Entity types ─────────────────────────────────────────────────────
ENT_EMPTY = 0
ENT_TISSUE = 1        # healthy tissue
ENT_INFECTED = 2      # infected tissue (viral)
ENT_BACTERIA = 3      # free bacterium
ENT_VIRUS = 4         # free virus particle
ENT_MACROPHAGE = 5    # innate — phagocyte
ENT_NEUTROPHIL = 6    # innate — fast responder
ENT_TCELL = 7         # adaptive — cytotoxic T cell
ENT_BCELL = 8         # adaptive — antibody-producing B cell
ENT_MEMORY = 9        # memory cell (T or B)
ENT_ANTIBODY = 10     # free antibody
ENT_DEBRIS = 11       # dead cell debris

ENT_NAMES = {
    ENT_EMPTY: "empty", ENT_TISSUE: "tissue", ENT_INFECTED: "infected",
    ENT_BACTERIA: "bact", ENT_VIRUS: "virus", ENT_MACROPHAGE: "macro",
    ENT_NEUTROPHIL: "neut", ENT_TCELL: "Tcell", ENT_BCELL: "Bcell",
    ENT_MEMORY: "mem", ENT_ANTIBODY: "Ab", ENT_DEBRIS: "debris",
}

ENT_CHARS = {
    ENT_EMPTY: "  ", ENT_TISSUE: "..", ENT_INFECTED: "xx",
    ENT_BACTERIA: "@@", ENT_VIRUS: "vv", ENT_MACROPHAGE: "MM",
    ENT_NEUTROPHIL: "NN", ENT_TCELL: "TT", ENT_BCELL: "BB",
    ENT_MEMORY: "**", ENT_ANTIBODY: "ab", ENT_DEBRIS: "::",
}

# Antigen is represented as an int 0..63 (6-bit shape)
ANTIGEN_BITS = 6
MAX_ANTIGEN = (1 << ANTIGEN_BITS) - 1


def _rand_antigen():
    return random.randint(0, MAX_ANTIGEN)


def _antigen_match(receptor, antigen):
    """Return match quality 0.0-1.0 (hamming similarity)."""
    xor = receptor ^ antigen
    diff = bin(xor).count("1")
    return 1.0 - diff / ANTIGEN_BITS


# ── Presets ───────────────────────────────────────────────────────────
# (name, desc, settings_dict)
IMMUNE_PRESETS = [
    ("Bacterial Invasion",
     "Bacteria flood in and replicate — innate immunity scrambles to contain",
     {"pathogen": "bacteria", "invasion_rate": 0.04, "replicate_rate": 0.06,
      "mutate_rate": 0.02, "innate_count": 40, "adaptive_count": 15,
      "tissue_density": 0.6, "cytokine_decay": 0.03,
      "autoimmune": False, "vaccination": None,
      "cytokine_storm": False}),

    ("Viral Outbreak",
     "Viruses infect tissue cells, hijack replication — adaptive response critical",
     {"pathogen": "virus", "invasion_rate": 0.03, "replicate_rate": 0.05,
      "mutate_rate": 0.03, "innate_count": 30, "adaptive_count": 20,
      "tissue_density": 0.7, "cytokine_decay": 0.025,
      "autoimmune": False, "vaccination": None,
      "cytokine_storm": False}),

    ("Vaccination",
     "Pre-exposed memory cells — watch the rapid secondary response",
     {"pathogen": "virus", "invasion_rate": 0.03, "replicate_rate": 0.05,
      "mutate_rate": 0.01, "innate_count": 25, "adaptive_count": 15,
      "tissue_density": 0.7, "cytokine_decay": 0.025,
      "autoimmune": False, "vaccination": True,
      "cytokine_storm": False}),

    ("Autoimmune",
     "Immune cells mistakenly attack healthy tissue — friendly fire",
     {"pathogen": "bacteria", "invasion_rate": 0.01, "replicate_rate": 0.03,
      "mutate_rate": 0.01, "innate_count": 50, "adaptive_count": 30,
      "tissue_density": 0.7, "cytokine_decay": 0.02,
      "autoimmune": True, "vaccination": None,
      "cytokine_storm": False}),

    ("Cytokine Storm",
     "Runaway positive feedback — immune overreaction causes collateral damage",
     {"pathogen": "virus", "invasion_rate": 0.05, "replicate_rate": 0.07,
      "mutate_rate": 0.02, "innate_count": 60, "adaptive_count": 40,
      "tissue_density": 0.65, "cytokine_decay": 0.005,
      "autoimmune": False, "vaccination": None,
      "cytokine_storm": True}),
]

# ── Helpers ───────────────────────────────────────────────────────────
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


def _move_toward_gradient(grid, cytokine, r, c, rows, cols):
    """Return best adjacent position following cytokine gradient, or None."""
    best_pos = None
    best_val = cytokine[r][c]
    candidates = []
    for dr, dc in _NBRS4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            v = cytokine[nr][nc]
            if v > best_val and grid[nr][nc] in (ENT_EMPTY, ENT_DEBRIS):
                best_val = v
                candidates.append((nr, nc, v))
    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        return (candidates[0][0], candidates[0][1])
    return None


# ══════════════════════════════════════════════════════════════════════
#  Core mode functions
# ══════════════════════════════════════════════════════════════════════

def _enter_immune_mode(self):
    """Enter Immune System mode — show preset menu."""
    self.immune_menu = True
    self.immune_menu_sel = 0
    self._flash("Immune System Simulation — select a scenario")


def _exit_immune_mode(self):
    """Exit Immune System mode."""
    self.immune_mode = False
    self.immune_menu = False
    self.immune_running = False
    self.immune_grid = []
    self.immune_cytokine = []
    self.immune_antigen_map = []
    self.immune_receptor_map = []
    self._flash("Immune System mode OFF")


def _immune_init(self, preset_idx: int):
    """Initialize the Immune System simulation with the given preset."""
    name, _desc, settings = self.IMMUNE_PRESETS[preset_idx]

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
    self.immune_view = "cells"  # cells / cytokine / antigen

    # Statistics
    self.immune_stats = {
        "pathogens_killed": 0, "tissue_lost": 0,
        "immune_deaths": 0, "antibodies_made": 0,
        "peak_pathogen": 0, "peak_immune": 0,
    }

    # Grids
    self.immune_grid = [[ENT_EMPTY] * cols for _ in range(rows)]
    self.immune_cytokine = [[0.0] * cols for _ in range(rows)]
    # Per-cell antigen (for pathogens/infected) or receptor (for immune cells)
    self.immune_antigen_map = [[0] * cols for _ in range(rows)]
    self.immune_receptor_map = [[0] * cols for _ in range(rows)]
    # Age per cell
    self.immune_age = [[0] * cols for _ in range(rows)]

    # Dominant pathogen antigen for this run
    self.immune_pathogen_antigen = _rand_antigen()

    # Place tissue
    tissue_density = settings["tissue_density"]
    for r in range(rows):
        for c in range(cols):
            if random.random() < tissue_density:
                self.immune_grid[r][c] = ENT_TISSUE
                self.immune_antigen_map[r][c] = 0  # self-antigen = 0

    # Place initial pathogens along edges
    invasion = settings["invasion_rate"]
    pathogen_type = ENT_BACTERIA if settings["pathogen"] == "bacteria" else ENT_VIRUS
    for r in range(rows):
        for c in range(cols):
            if (r < 3 or r >= rows - 3 or c < 3 or c >= cols - 3):
                if random.random() < invasion:
                    self.immune_grid[r][c] = pathogen_type
                    ag = self.immune_pathogen_antigen
                    # Small initial mutation
                    if random.random() < 0.1:
                        bit = random.randint(0, ANTIGEN_BITS - 1)
                        ag ^= (1 << bit)
                    self.immune_antigen_map[r][c] = ag
                    self.immune_cytokine[r][c] = 0.3

    # Place innate immune cells (scattered)
    innate_count = settings["innate_count"]
    for _ in range(innate_count):
        r, c = random.randint(5, rows - 6), random.randint(5, cols - 6)
        if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
            etype = ENT_MACROPHAGE if random.random() < 0.5 else ENT_NEUTROPHIL
            self.immune_grid[r][c] = etype
            self.immune_receptor_map[r][c] = 0  # innate = non-specific

    # Place adaptive immune cells (near center = lymph node area)
    adaptive_count = settings["adaptive_count"]
    cr, cc = rows // 2, cols // 2
    for _ in range(adaptive_count):
        r = cr + random.randint(-8, 8)
        c = cc + random.randint(-8, 8)
        r = max(0, min(rows - 1, r))
        c = max(0, min(cols - 1, c))
        if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
            etype = ENT_TCELL if random.random() < 0.5 else ENT_BCELL
            self.immune_grid[r][c] = etype
            # Random receptor — some may match pathogen by luck
            self.immune_receptor_map[r][c] = _rand_antigen()

    # Vaccination: pre-seed memory cells with matching receptors
    if settings.get("vaccination"):
        for _ in range(20):
            r = cr + random.randint(-5, 5)
            c = cc + random.randint(-5, 5)
            r = max(0, min(rows - 1, r))
            c = max(0, min(cols - 1, c))
            if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
                self.immune_grid[r][c] = ENT_MEMORY
                # Memory cells have near-perfect receptor match
                receptor = self.immune_pathogen_antigen
                if random.random() < 0.2:
                    bit = random.randint(0, ANTIGEN_BITS - 1)
                    receptor ^= (1 << bit)
                self.immune_receptor_map[r][c] = receptor

    self.immune_mode = True
    self.immune_menu = False
    self.immune_running = False
    self._flash(f"Immune System: {name} — Space to start")


def _immune_step(self):
    """Advance the immune simulation by one step."""
    grid = self.immune_grid
    cyto = self.immune_cytokine
    ag_map = self.immune_antigen_map
    rec_map = self.immune_receptor_map
    age = self.immune_age
    rows, cols = self.immune_rows, self.immune_cols
    settings = self.immune_settings
    gen = self.immune_generation
    stats = self.immune_stats

    replicate_rate = settings["replicate_rate"]
    mutate_rate = settings["mutate_rate"]
    cyto_decay = settings["cytokine_decay"]
    autoimmune = settings["autoimmune"]
    cytokine_storm = settings["cytokine_storm"]

    # ── 1. Diffuse and decay cytokines ────────────────────────────
    new_cyto = [[0.0] * cols for _ in range(rows)]
    diff_rate = 0.08
    for r in range(rows):
        for c in range(cols):
            rn = min(r + 1, rows - 1)
            rs = max(r - 1, 0)
            ce = min(c + 1, cols - 1)
            cw = max(c - 1, 0)
            v = cyto[r][c]
            lap = cyto[rn][c] + cyto[rs][c] + cyto[r][ce] + cyto[r][cw] - 4.0 * v
            nv = v + diff_rate * lap - cyto_decay * v
            # Cytokine storm: reduced decay means runaway accumulation
            new_cyto[r][c] = max(0.0, min(2.0, nv))
    self.immune_cytokine = new_cyto
    cyto = new_cyto

    # ── 2. Build action lists (synchronous update) ────────────────
    moves = []       # (r, c, nr, nc)  — move entity
    kills = []       # (r, c)  — entity dies
    spawns = []      # (r, c, etype, antigen, receptor)
    infections = []  # (r, c)  — tissue becomes infected

    # Count entities for stats
    pathogen_count = 0
    immune_count = 0

    for r in range(rows):
        for c in range(cols):
            et = grid[r][c]
            if et == ENT_EMPTY or et == ENT_TISSUE or et == ENT_DEBRIS:
                # Debris decays
                if et == ENT_DEBRIS:
                    age[r][c] += 1
                    if age[r][c] > 8:
                        kills.append((r, c))
                continue

            age[r][c] += 1
            cell_age = age[r][c]

            # ── PATHOGENS: bacteria / virus ──
            if et == ENT_BACTERIA:
                pathogen_count += 1
                # Emit cytokine (danger signal)
                cyto[r][c] = min(2.0, cyto[r][c] + 0.15)

                # Replicate
                if random.random() < replicate_rate:
                    targets = _empty_adj(grid, r, c, rows, cols, include_tissue=True)
                    if targets:
                        nr, nc = random.choice(targets)
                        new_ag = ag_map[r][c]
                        # Mutation
                        if random.random() < mutate_rate:
                            bit = random.randint(0, ANTIGEN_BITS - 1)
                            new_ag ^= (1 << bit)
                        if grid[nr][nc] == ENT_TISSUE:
                            stats["tissue_lost"] += 1
                        spawns.append((nr, nc, ENT_BACTERIA, new_ag, 0))

                # Random walk
                elif random.random() < 0.3:
                    adj = _empty_adj(grid, r, c, rows, cols, include_tissue=True)
                    if adj:
                        nr, nc = random.choice(adj)
                        if grid[nr][nc] == ENT_TISSUE:
                            stats["tissue_lost"] += 1
                        moves.append((r, c, nr, nc))

            elif et == ENT_VIRUS:
                pathogen_count += 1
                cyto[r][c] = min(2.0, cyto[r][c] + 0.1)

                # Viruses infect adjacent tissue
                if random.random() < replicate_rate:
                    adj = _empty_adj(grid, r, c, rows, cols, include_tissue=True)
                    tissue_adj = [(nr, nc) for nr, nc in adj
                                  if grid[nr][nc] == ENT_TISSUE]
                    if tissue_adj:
                        nr, nc = random.choice(tissue_adj)
                        infections.append((nr, nc))
                        ag_map[nr][nc] = ag_map[r][c]
                        kills.append((r, c))  # virus consumed on infection
                    else:
                        # Drift
                        empty_adj = [(nr, nc) for nr, nc in adj
                                     if grid[nr][nc] == ENT_EMPTY]
                        if empty_adj:
                            nr, nc = random.choice(empty_adj)
                            moves.append((r, c, nr, nc))

            elif et == ENT_INFECTED:
                pathogen_count += 1
                cyto[r][c] = min(2.0, cyto[r][c] + 0.2)

                # Produce new virus particles
                if cell_age > 5 and random.random() < replicate_rate * 0.8:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        new_ag = ag_map[r][c]
                        if random.random() < mutate_rate:
                            bit = random.randint(0, ANTIGEN_BITS - 1)
                            new_ag ^= (1 << bit)
                        spawns.append((nr, nc, ENT_VIRUS, new_ag, 0))

                # Infected cells die after a while (lysis)
                if cell_age > 20:
                    kills.append((r, c))
                    stats["tissue_lost"] += 1

            # ── INNATE IMMUNE CELLS ──
            elif et == ENT_MACROPHAGE:
                immune_count += 1
                # Chemotaxis toward cytokine
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)

                # Check adjacent for pathogens to phagocytose
                ate = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED, ENT_DEBRIS):
                            kills.append((nr, nc))
                            stats["pathogens_killed"] += 1
                            ate = True
                            # Present antigen — boost nearby cytokine
                            cyto[r][c] = min(2.0, cyto[r][c] + 0.3)
                            break
                        # Autoimmune: sometimes attack tissue
                        if autoimmune and nt == ENT_TISSUE and random.random() < 0.02:
                            kills.append((nr, nc))
                            stats["tissue_lost"] += 1
                            ate = True
                            break

                if not ate and target:
                    moves.append((r, c, target[0], target[1]))
                elif not ate and random.random() < 0.2:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                # Macrophages have long lifespan but can die
                if cell_age > 200 and random.random() < 0.01:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            elif et == ENT_NEUTROPHIL:
                immune_count += 1
                # Fast but short-lived
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)

                # Kill adjacent pathogens (more aggressive)
                killed_any = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                            kills.append((nr, nc))
                            stats["pathogens_killed"] += 1
                            killed_any = True
                            # Neutrophil burst — also damages area
                            if cytokine_storm and cyto[r][c] > 1.0:
                                for dr2, dc2 in _NBRS4:
                                    nr2, nc2 = r + dr2, c + dc2
                                    if (0 <= nr2 < rows and 0 <= nc2 < cols
                                            and grid[nr2][nc2] == ENT_TISSUE):
                                        if random.random() < 0.15:
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
                if cell_age > 60 or (killed_any and random.random() < 0.3):
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            # ── ADAPTIVE IMMUNE CELLS ──
            elif et == ENT_TCELL:
                immune_count += 1
                receptor = rec_map[r][c]

                # Chemotaxis
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)

                # Check for antigen-presenting targets
                activated = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                            match = _antigen_match(receptor, ag_map[nr][nc])
                            if match > 0.7:
                                kills.append((nr, nc))
                                stats["pathogens_killed"] += 1
                                activated = True
                                cyto[r][c] = min(2.0, cyto[r][c] + 0.4)
                                break
                        # Autoimmune: T-cells attack tissue
                        if autoimmune and nt == ENT_TISSUE:
                            if _antigen_match(receptor, 0) > 0.8 and random.random() < 0.03:
                                kills.append((nr, nc))
                                stats["tissue_lost"] += 1
                                activated = True
                                break

                # Clonal expansion on activation
                if activated and random.random() < 0.4:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        spawns.append((nr, nc, ENT_TCELL, 0, receptor))

                # Become memory cell after long survival with activation
                if activated and cell_age > 30 and random.random() < 0.05:
                    # Convert to memory
                    grid[r][c] = ENT_MEMORY
                    age[r][c] = 0

                if not activated and target:
                    moves.append((r, c, target[0], target[1]))
                elif not activated and random.random() < 0.2:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                if cell_age > 150 and random.random() < 0.02:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            elif et == ENT_BCELL:
                immune_count += 1
                receptor = rec_map[r][c]

                # B cells produce antibodies when activated
                activated = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS):
                            match = _antigen_match(receptor, ag_map[nr][nc])
                            if match > 0.65:
                                activated = True
                                break

                if activated:
                    # Produce antibodies in empty adjacent cells
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj and random.random() < 0.5:
                        nr, nc = random.choice(adj)
                        spawns.append((nr, nc, ENT_ANTIBODY, 0, receptor))
                        stats["antibodies_made"] += 1
                    # Clonal expansion
                    if random.random() < 0.3:
                        adj2 = _empty_adj(grid, r, c, rows, cols)
                        if adj2:
                            nr, nc = random.choice(adj2)
                            spawns.append((nr, nc, ENT_BCELL, 0, receptor))

                    # Memory formation
                    if cell_age > 25 and random.random() < 0.05:
                        grid[r][c] = ENT_MEMORY
                        age[r][c] = 0

                # Move
                target = _move_toward_gradient(grid, cyto, r, c, rows, cols)
                if not activated and target:
                    moves.append((r, c, target[0], target[1]))
                elif not activated and random.random() < 0.15:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                if cell_age > 120 and random.random() < 0.02:
                    kills.append((r, c))
                    stats["immune_deaths"] += 1

            elif et == ENT_MEMORY:
                immune_count += 1
                receptor = rec_map[r][c]

                # Memory cells are dormant until they detect matching antigen
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                            match = _antigen_match(receptor, ag_map[nr][nc])
                            if match > 0.6:
                                # Rapid reactivation — spawn T and B cells
                                adj = _empty_adj(grid, r, c, rows, cols)
                                for pos in adj[:3]:
                                    etype = ENT_TCELL if random.random() < 0.5 else ENT_BCELL
                                    spawns.append((pos[0], pos[1], etype, 0, receptor))
                                cyto[r][c] = min(2.0, cyto[r][c] + 0.5)
                                break

                # Slow random walk
                if random.random() < 0.05:
                    adj = _empty_adj(grid, r, c, rows, cols)
                    if adj:
                        nr, nc = random.choice(adj)
                        moves.append((r, c, nr, nc))

                # Memory cells are very long-lived (no natural death in sim)

            elif et == ENT_ANTIBODY:
                # Antibodies drift and neutralize matching pathogens
                receptor = rec_map[r][c]
                neutralized = False
                for dr, dc in _NBRS8:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nt = grid[nr][nc]
                        if nt in (ENT_BACTERIA, ENT_VIRUS):
                            match = _antigen_match(receptor, ag_map[nr][nc])
                            if match > 0.6:
                                kills.append((nr, nc))
                                kills.append((r, c))  # antibody consumed
                                stats["pathogens_killed"] += 1
                                neutralized = True
                                break

                if not neutralized:
                    if random.random() < 0.5:
                        adj = _empty_adj(grid, r, c, rows, cols)
                        if adj:
                            nr, nc = random.choice(adj)
                            moves.append((r, c, nr, nc))
                    # Antibodies decay
                    if cell_age > 40 and random.random() < 0.05:
                        kills.append((r, c))

    # ── 3. Apply changes ──────────────────────────────────────────
    # Process kills first
    killed_set = set()
    for r, c in kills:
        if (r, c) not in killed_set:
            killed_set.add((r, c))
            old = grid[r][c]
            if old in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED,
                       ENT_MACROPHAGE, ENT_NEUTROPHIL, ENT_TCELL, ENT_BCELL):
                grid[r][c] = ENT_DEBRIS
                age[r][c] = 0
            else:
                grid[r][c] = ENT_EMPTY
                age[r][c] = 0
            ag_map[r][c] = 0
            rec_map[r][c] = 0

    # Process moves
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
        grid[r][c] = ENT_EMPTY
        ag_map[r][c] = 0
        rec_map[r][c] = 0
        age[r][c] = 0
        moved_from.add((r, c))
        moved_to.add((nr, nc))

    # Process spawns
    for r, c, etype, antigen, receptor in spawns:
        if grid[r][c] in (ENT_EMPTY, ENT_DEBRIS) and (r, c) not in moved_to:
            grid[r][c] = etype
            ag_map[r][c] = antigen
            rec_map[r][c] = receptor
            age[r][c] = 0

    # Process infections
    for r, c in infections:
        if grid[r][c] == ENT_TISSUE:
            grid[r][c] = ENT_INFECTED
            age[r][c] = 0

    # ── 4. Ongoing invasion (pathogens keep arriving at edges) ────
    if gen % 5 == 0 and gen < 300:
        invasion_rate = settings["invasion_rate"] * max(0.2, 1.0 - gen / 400.0)
        pathogen_type = ENT_BACTERIA if settings["pathogen"] == "bacteria" else ENT_VIRUS
        for _ in range(max(1, int(invasion_rate * (rows + cols)))):
            edge = random.randint(0, 3)
            if edge == 0:
                r, c = 0, random.randint(0, cols - 1)
            elif edge == 1:
                r, c = rows - 1, random.randint(0, cols - 1)
            elif edge == 2:
                r, c = random.randint(0, rows - 1), 0
            else:
                r, c = random.randint(0, rows - 1), cols - 1
            if grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
                if grid[r][c] == ENT_TISSUE:
                    stats["tissue_lost"] += 1
                grid[r][c] = pathogen_type
                ag = self.immune_pathogen_antigen
                if random.random() < mutate_rate:
                    bit = random.randint(0, ANTIGEN_BITS - 1)
                    ag ^= (1 << bit)
                ag_map[r][c] = ag
                age[r][c] = 0

    # ── 5. Innate reinforcements from bone marrow ─────────────────
    if gen % 15 == 0:
        cr, cc = rows // 2, cols // 2
        # Check if there's active infection (high cytokine)
        max_cyto = max(cyto[r][c] for r in range(rows) for c in range(cols))
        if max_cyto > 0.3:
            for _ in range(3):
                r = cr + random.randint(-5, 5)
                c = cc + random.randint(-5, 5)
                r = max(0, min(rows - 1, r))
                c = max(0, min(cols - 1, c))
                if grid[r][c] in (ENT_EMPTY, ENT_DEBRIS):
                    etype = ENT_MACROPHAGE if random.random() < 0.4 else ENT_NEUTROPHIL
                    grid[r][c] = etype
                    rec_map[r][c] = 0
                    age[r][c] = 0

    # Update peak stats
    stats["peak_pathogen"] = max(stats["peak_pathogen"], pathogen_count)
    stats["peak_immune"] = max(stats["peak_immune"], immune_count)

    self.immune_generation += 1


# ══════════════════════════════════════════════════════════════════════
#  Input handling
# ══════════════════════════════════════════════════════════════════════

def _handle_immune_menu_key(self, key: int) -> bool:
    """Handle input in Immune System preset menu."""
    presets = self.IMMUNE_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.immune_menu_sel = (self.immune_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.immune_menu_sel = (self.immune_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._immune_init(self.immune_menu_sel)
    elif key == ord("q") or key == 27:
        self.immune_menu = False
        self._flash("Immune System cancelled")
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
        self._immune_step()
        return True
    if key == ord("r"):
        self._immune_init(self.immune_preset_idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.immune_mode = False
        self.immune_running = False
        self.immune_menu = True
        self.immune_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20]
        idx = choices.index(self.immune_steps_per_frame) if self.immune_steps_per_frame in choices else 0
        self.immune_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.immune_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20]
        idx = choices.index(self.immune_steps_per_frame) if self.immune_steps_per_frame in choices else 0
        self.immune_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.immune_steps_per_frame} steps/frame")
        return True
    if key == ord("v"):
        views = ["cells", "cytokine", "antigen"]
        idx = views.index(self.immune_view) if self.immune_view in views else 0
        self.immune_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.immune_view}")
        return True
    # Inject pathogen wave
    if key == ord("p"):
        pathogen_type = ENT_BACTERIA if self.immune_settings["pathogen"] == "bacteria" else ENT_VIRUS
        rows, cols = self.immune_rows, self.immune_cols
        for _ in range(20):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            if self.immune_grid[r][c] in (ENT_EMPTY, ENT_TISSUE):
                self.immune_grid[r][c] = pathogen_type
                ag = self.immune_pathogen_antigen
                if random.random() < 0.15:
                    bit = random.randint(0, ANTIGEN_BITS - 1)
                    ag ^= (1 << bit)
                self.immune_antigen_map[r][c] = ag
        self._flash("Pathogen wave injected!")
        return True
    # Inject immune boost
    if key == ord("i"):
        rows, cols = self.immune_rows, self.immune_cols
        cr, cc = rows // 2, cols // 2
        for _ in range(15):
            r = cr + random.randint(-10, 10)
            c = cc + random.randint(-10, 10)
            r = max(0, min(rows - 1, r))
            c = max(0, min(cols - 1, c))
            if self.immune_grid[r][c] in (ENT_EMPTY, ENT_DEBRIS):
                etype = random.choice([ENT_TCELL, ENT_BCELL, ENT_MACROPHAGE, ENT_NEUTROPHIL])
                self.immune_grid[r][c] = etype
                self.immune_receptor_map[r][c] = _rand_antigen()
                self.immune_age[r][c] = 0
        self._flash("Immune boost deployed!")
        return True
    # Mutate pathogen antigen
    if key == ord("u"):
        bit = random.randint(0, ANTIGEN_BITS - 1)
        self.immune_pathogen_antigen ^= (1 << bit)
        self._flash(f"Pathogen mutated! Antigen: {self.immune_pathogen_antigen:06b}")
        return True
    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing
# ══════════════════════════════════════════════════════════════════════

def _draw_immune_menu(self, max_y: int, max_x: int):
    """Draw the Immune System preset selection menu."""
    self.stdscr.erase()
    title = "── Immune System Simulation ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _settings) in enumerate(self.IMMUNE_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        marker = ">" if i == self.immune_menu_sel else " "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.immune_menu_sel
                else curses.color_pair(7))
        line = f" {marker} {name:24s}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], attr)
        except curses.error:
            pass
        # Description on next line
        desc_attr = (curses.color_pair(6) if i == self.immune_menu_sel
                     else curses.color_pair(7) | curses.A_DIM)
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], desc_attr)
        except curses.error:
            pass

    # Legend
    legend_y = 3 + len(self.IMMUNE_PRESETS) * 2 + 1
    if legend_y < max_y - 3:
        legend_lines = [
            "Entities:  @@ bacteria  vv virus  xx infected  .. tissue",
            "           MM macrophage  NN neutrophil  TT T-cell  BB B-cell",
            "           ** memory cell  ab antibody  :: debris",
        ]
        for i, line in enumerate(legend_lines):
            if legend_y + i < max_y - 2:
                try:
                    self.stdscr.addstr(legend_y + i, 4, line[:max_x - 6],
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_immune(self, max_y: int, max_x: int):
    """Draw the active Immune System simulation."""
    self.stdscr.erase()
    grid = self.immune_grid
    cyto = self.immune_cytokine
    ag_map = self.immune_antigen_map
    rec_map = self.immune_receptor_map
    rows, cols = self.immune_rows, self.immune_cols
    state = "RUN" if self.immune_running else "PAUSED"
    view = self.immune_view
    stats = self.immune_stats

    # Count entities
    counts = {}
    for r in range(rows):
        for c in range(cols):
            et = grid[r][c]
            if et != ENT_EMPTY:
                counts[et] = counts.get(et, 0) + 1

    pathogen_n = counts.get(ENT_BACTERIA, 0) + counts.get(ENT_VIRUS, 0) + counts.get(ENT_INFECTED, 0)
    immune_n = (counts.get(ENT_MACROPHAGE, 0) + counts.get(ENT_NEUTROPHIL, 0)
                + counts.get(ENT_TCELL, 0) + counts.get(ENT_BCELL, 0)
                + counts.get(ENT_MEMORY, 0))

    # Title bar
    title = (f" Immune: {self.immune_preset_name}  |  gen {self.immune_generation}"
             f"  |  path={pathogen_n} imm={immune_n} tissue={counts.get(ENT_TISSUE, 0)}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Color mapping
    cell_colors = {
        ENT_TISSUE: curses.color_pair(1) | curses.A_DIM,          # dim green
        ENT_INFECTED: curses.color_pair(2) | curses.A_BOLD,       # bright yellow
        ENT_BACTERIA: curses.color_pair(1) | curses.A_BOLD,       # bright green
        ENT_VIRUS: curses.color_pair(5) | curses.A_BOLD,          # magenta
        ENT_MACROPHAGE: curses.color_pair(6) | curses.A_BOLD,     # cyan bold
        ENT_NEUTROPHIL: curses.color_pair(7) | curses.A_BOLD,     # white bold
        ENT_TCELL: curses.color_pair(4) | curses.A_BOLD,          # blue bold
        ENT_BCELL: curses.color_pair(3) | curses.A_BOLD,          # yellow bold
        ENT_MEMORY: curses.color_pair(5),                          # magenta
        ENT_ANTIBODY: curses.color_pair(6),                        # cyan
        ENT_DEBRIS: curses.color_pair(7) | curses.A_DIM,          # dim white
    }

    for r in range(view_rows):
        sy = 1 + r
        for c in range(view_cols):
            sx = c * 2
            if view == "cells":
                et = grid[r][c]
                if et == ENT_EMPTY:
                    continue
                ch = ENT_CHARS.get(et, "??")
                attr = cell_colors.get(et, curses.color_pair(7))
            elif view == "cytokine":
                v = cyto[r][c]
                if v > 1.0:
                    ch, attr = "##", curses.color_pair(1) | curses.A_BOLD
                elif v > 0.5:
                    ch, attr = "%%", curses.color_pair(2) | curses.A_BOLD
                elif v > 0.2:
                    ch, attr = "++", curses.color_pair(2)
                elif v > 0.05:
                    ch, attr = "..", curses.color_pair(2) | curses.A_DIM
                else:
                    continue
            else:  # antigen view
                et = grid[r][c]
                ag = ag_map[r][c]
                if et in (ENT_BACTERIA, ENT_VIRUS, ENT_INFECTED):
                    # Color by antigen value
                    hue = ag / MAX_ANTIGEN
                    if hue > 0.66:
                        ch, attr = "@@", curses.color_pair(1) | curses.A_BOLD
                    elif hue > 0.33:
                        ch, attr = "@@", curses.color_pair(2) | curses.A_BOLD
                    else:
                        ch, attr = "@@", curses.color_pair(5) | curses.A_BOLD
                elif et in (ENT_TCELL, ENT_BCELL, ENT_MEMORY):
                    rec = rec_map[r][c]
                    hue = rec / MAX_ANTIGEN
                    if hue > 0.66:
                        ch, attr = "**", curses.color_pair(4) | curses.A_BOLD
                    elif hue > 0.33:
                        ch, attr = "**", curses.color_pair(6) | curses.A_BOLD
                    else:
                        ch, attr = "**", curses.color_pair(3) | curses.A_BOLD
                else:
                    continue

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Stats line
    stats_y = max_y - 2
    if stats_y > 1:
        s = stats
        stat_line = (f" killed={s['pathogens_killed']} tissue_lost={s['tissue_lost']}"
                     f"  Ab={s['antibodies_made']}  mem={counts.get(ENT_MEMORY, 0)}"
                     f"  peak_path={s['peak_pathogen']} peak_imm={s['peak_immune']}")
        try:
            self.stdscr.addstr(stats_y, 0, stat_line[:max_x - 1], curses.color_pair(7))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [p]=pathogens [i]=immune [u]=mutate [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
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
