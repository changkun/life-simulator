"""Mode: morphogenesis — biological embryonic development from a single cell.

A single cell divides, differentiates, and self-organizes into a complex
multicellular organism using morphogen gradients, gene regulatory networks,
and local cell-cell signaling.  Each cell carries a genome controlling
division rules, differentiation responses, and morphogen production.

Watch a fertilized "egg" develop into organized tissues with distinct cell
types, boundaries, and emergent body plans — all in ASCII.
"""
import curses
import math
import random
import time


# ── Cell types ──────────────────────────────────────────────────────────
CELL_EMPTY = 0
CELL_STEM = 1          # undifferentiated stem / progenitor
CELL_ECTO = 2          # ectoderm  (skin / neural)
CELL_MESO = 3          # mesoderm  (muscle / bone)
CELL_ENDO = 4          # endoderm  (gut / organ)
CELL_NEURAL = 5        # neural crest
CELL_SIGNAL = 6        # organiser / signaling center
CELL_DEAD = 7          # apoptotic

CELL_NAMES = {
    CELL_EMPTY: "empty", CELL_STEM: "stem", CELL_ECTO: "ecto",
    CELL_MESO: "meso", CELL_ENDO: "endo", CELL_NEURAL: "neural",
    CELL_SIGNAL: "signal", CELL_DEAD: "dead",
}

CELL_CHARS = {
    CELL_EMPTY: "  ",
    CELL_STEM:  "@@",
    CELL_ECTO:  "##",
    CELL_MESO:  "%%",
    CELL_ENDO:  "&&",
    CELL_NEURAL: "**",
    CELL_SIGNAL: "<>",
    CELL_DEAD:  "..",
}


# ── Genome: per-cell heritable parameters ───────────────────────────────
def _make_genome():
    """Return a default genome dict."""
    return {
        "div_rate": 0.12,       # probability of division per step
        "div_nutrient": 0.3,    # nutrient threshold to divide
        "morph_A_prod": 0.0,    # morphogen-A production rate
        "morph_B_prod": 0.0,    # morphogen-B production rate
        "diff_thresh_A": 0.4,   # morphogen-A threshold for differentiation
        "diff_thresh_B": 0.4,   # morphogen-B threshold for differentiation
        "apoptosis": 0.002,     # background apoptosis rate
        "adhesion": 1.0,        # cell-cell adhesion preference
        "mutation_rate": 0.02,  # per-division genome mutation
    }


def _mutate_genome(g, rate=None):
    """Return a mutated copy of genome *g*."""
    ng = dict(g)
    mr = rate if rate is not None else g.get("mutation_rate", 0.02)
    for k in ("div_rate", "morph_A_prod", "morph_B_prod",
              "diff_thresh_A", "diff_thresh_B", "apoptosis", "adhesion"):
        if random.random() < mr:
            ng[k] = max(0.0, min(1.0, ng[k] + random.gauss(0, 0.05)))
    return ng


# ── Presets ──────────────────────────────────────────────────────────────
# (name, desc, morphA_diff, morphB_diff, morphA_decay, morphB_decay,
#  nutrient_rate, symmetry, extra_settings_dict)
MORPHOGENESIS_PRESETS = [
    ("Radial Embryo",
     "Single egg — radial symmetry, layered germ layers",
     0.08, 0.06, 0.02, 0.015, 0.5, "radial",
     {"organiser": True, "apoptosis_sculpt": False}),

    ("Bilateral Body Plan",
     "Left-right symmetry axis with dorsal organiser",
     0.07, 0.05, 0.018, 0.012, 0.45, "bilateral",
     {"organiser": True, "apoptosis_sculpt": True}),

    ("Gastrulation",
     "Invagination — cells fold inward to form gut tube",
     0.09, 0.07, 0.025, 0.02, 0.55, "radial",
     {"organiser": True, "invagination": True, "apoptosis_sculpt": False}),

    ("Neural Tube Formation",
     "Dorsal ectoderm folds to create neural crest",
     0.06, 0.08, 0.015, 0.025, 0.5, "bilateral",
     {"organiser": True, "neural_induction": True, "apoptosis_sculpt": True}),

    ("Limb Bud Outgrowth",
     "Outgrowth from a body wall with ZPA signaling",
     0.10, 0.04, 0.02, 0.01, 0.6, "bilateral",
     {"organiser": True, "limb_bud": True, "apoptosis_sculpt": True}),

    ("Regeneration",
     "Cut in half — watch it regrow missing tissue",
     0.07, 0.06, 0.02, 0.015, 0.55, "radial",
     {"organiser": True, "regeneration": True, "apoptosis_sculpt": False}),

    ("Somitogenesis",
     "Segmented body plan via oscillating morphogen clock",
     0.08, 0.09, 0.03, 0.02, 0.5, "bilateral",
     {"organiser": True, "somite_clock": True, "apoptosis_sculpt": False}),

    ("Minimal Egg",
     "Bare-bones: one cell, no organiser, pure emergence",
     0.05, 0.05, 0.01, 0.01, 0.4, "none",
     {"organiser": False, "apoptosis_sculpt": False}),
]


# ── Helpers ──────────────────────────────────────────────────────────────
_NBRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NBRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _count_neighbors(grid, r, c, rows, cols):
    """Count non-empty neighbors (8-connected)."""
    n = 0
    for dr, dc in _NBRS8:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != CELL_EMPTY:
            n += 1
    return n


def _empty_neighbors(grid, r, c, rows, cols):
    """Return list of empty neighbor positions (4-connected)."""
    out = []
    for dr, dc in _NBRS4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == CELL_EMPTY:
            out.append((nr, nc))
    return out


def _neighbor_types(grid, r, c, rows, cols):
    """Return dict of cell-type -> count for 8-neighbors."""
    counts = {}
    for dr, dc in _NBRS8:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            t = grid[nr][nc]
            if t != CELL_EMPTY:
                counts[t] = counts.get(t, 0) + 1
    return counts


# ════════════════════════════════════════════════════════════════════════
#  Core mode functions
# ════════════════════════════════════════════════════════════════════════

def _enter_morpho_mode(self):
    """Enter Morphogenesis mode — show preset menu."""
    self.morpho_menu = True
    self.morpho_menu_sel = 0
    self._flash("Morphogenesis — select an embryo scenario")


def _exit_morpho_mode(self):
    """Exit Morphogenesis mode."""
    self.morpho_mode = False
    self.morpho_menu = False
    self.morpho_running = False
    self.morpho_cells = []
    self.morpho_genome_map = []
    self.morpho_morph_A = []
    self.morpho_morph_B = []
    self.morpho_nutrient = []
    self.morpho_age = []
    self._flash("Morphogenesis mode OFF")


def _morpho_init(self, preset_idx: int):
    """Initialize the Morphogenesis simulation with the given preset."""
    (name, _desc, mA_diff, mB_diff, mA_dec, mB_dec,
     nutr_rate, symmetry, extras) = self.MORPHOGENESIS_PRESETS[preset_idx]

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(30, max_y - 4)
    cols = max(30, (max_x - 1) // 2)
    self.morpho_rows = rows
    self.morpho_cols = cols
    self.morpho_preset_name = name
    self.morpho_generation = 0
    self.morpho_steps_per_frame = 1
    self.morpho_mA_diff = mA_diff
    self.morpho_mB_diff = mB_diff
    self.morpho_mA_decay = mA_dec
    self.morpho_mB_decay = mB_dec
    self.morpho_nutr_rate = nutr_rate
    self.morpho_symmetry = symmetry
    self.morpho_extras = dict(extras)
    self.morpho_total_cells = 1
    self.morpho_total_divisions = 0
    self.morpho_total_deaths = 0
    self.morpho_max_cells = 0
    self.morpho_view = "cells"  # cells / morphA / morphB / nutrient

    # Grids
    self.morpho_cells = [[CELL_EMPTY] * cols for _ in range(rows)]
    self.morpho_genome_map = [[None] * cols for _ in range(rows)]
    self.morpho_morph_A = [[0.0] * cols for _ in range(rows)]
    self.morpho_morph_B = [[0.0] * cols for _ in range(rows)]
    self.morpho_nutrient = [[1.0] * cols for _ in range(rows)]
    self.morpho_age = [[0] * cols for _ in range(rows)]
    self.morpho_clock = [[0.0] * cols for _ in range(rows)]

    cr, cc = rows // 2, cols // 2

    # Place the zygote (single fertilized egg)
    g = _make_genome()
    g["morph_A_prod"] = 0.3
    g["morph_B_prod"] = 0.1
    g["div_rate"] = 0.18
    self.morpho_cells[cr][cc] = CELL_STEM
    self.morpho_genome_map[cr][cc] = g
    self.morpho_age[cr][cc] = 0

    # Place organiser if requested
    if extras.get("organiser"):
        if symmetry == "bilateral":
            # Dorsal organiser above the egg
            or_ = max(0, cr - 3)
            og = _make_genome()
            og["morph_A_prod"] = 0.8
            og["morph_B_prod"] = 0.05
            og["div_rate"] = 0.05
            self.morpho_cells[or_][cc] = CELL_SIGNAL
            self.morpho_genome_map[or_][cc] = og
            self.morpho_morph_A[or_][cc] = 0.9
        else:
            # Radial organiser ring
            og = _make_genome()
            og["morph_A_prod"] = 0.7
            og["morph_B_prod"] = 0.3
            og["div_rate"] = 0.03
            for dr, dc in _NBRS4:
                nr, nc = cr + dr * 2, cc + dc * 2
                if 0 <= nr < rows and 0 <= nc < cols:
                    self.morpho_cells[nr][nc] = CELL_SIGNAL
                    self.morpho_genome_map[nr][nc] = _mutate_genome(og, 0.01)
                    self.morpho_morph_A[nr][nc] = 0.6

    self.morpho_mode = True
    self.morpho_menu = False
    self.morpho_running = False
    self._flash(f"Morphogenesis: {name} — Space to start")


def _morpho_step(self):
    """Advance the morphogenesis simulation by one step."""
    cells = self.morpho_cells
    genomes = self.morpho_genome_map
    mA = self.morpho_morph_A
    mB = self.morpho_morph_B
    nutr = self.morpho_nutrient
    age = self.morpho_age
    rows, cols = self.morpho_rows, self.morpho_cols
    mA_diff = self.morpho_mA_diff
    mB_diff = self.morpho_mB_diff
    mA_dec = self.morpho_mA_decay
    mB_dec = self.morpho_mB_decay
    nutr_rate = self.morpho_nutr_rate
    symmetry = self.morpho_symmetry
    extras = self.morpho_extras
    gen = self.morpho_generation
    dt = 0.15

    # ── 1. Diffuse morphogens & nutrients ───────────────────────────
    new_mA = [[0.0] * cols for _ in range(rows)]
    new_mB = [[0.0] * cols for _ in range(rows)]
    new_nutr = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            # Laplacians
            rn = min(r + 1, rows - 1)
            rs = max(r - 1, 0)
            ce = min(c + 1, cols - 1)
            cw = max(c - 1, 0)

            a = mA[r][c]
            b = mB[r][c]
            n = nutr[r][c]

            lap_a = mA[rn][c] + mA[rs][c] + mA[r][ce] + mA[r][cw] - 4.0 * a
            lap_b = mB[rn][c] + mB[rs][c] + mB[r][ce] + mB[r][cw] - 4.0 * b
            lap_n = nutr[rn][c] + nutr[rs][c] + nutr[r][ce] + nutr[r][cw] - 4.0 * n

            # Production by living cells
            prod_a = 0.0
            prod_b = 0.0
            consume = 0.0
            ct = cells[r][c]
            if ct != CELL_EMPTY and ct != CELL_DEAD:
                g = genomes[r][c]
                if g:
                    prod_a = g["morph_A_prod"]
                    prod_b = g["morph_B_prod"]
                # Signal cells produce extra morphogen-A
                if ct == CELL_SIGNAL:
                    prod_a += 0.3
                # Living cells consume nutrients
                consume = 0.1

            na = a + dt * (mA_diff * lap_a + prod_a - mA_dec * a)
            nb = b + dt * (mB_diff * lap_b + prod_b - mB_dec * b)
            nn = n + dt * (0.02 * lap_n - consume + nutr_rate * (1.0 - n) * 0.05)

            new_mA[r][c] = max(0.0, min(1.0, na))
            new_mB[r][c] = max(0.0, min(1.0, nb))
            new_nutr[r][c] = max(0.0, min(1.0, nn))

    self.morpho_morph_A = new_mA
    self.morpho_morph_B = new_mB
    self.morpho_nutrient = new_nutr
    mA = new_mA
    mB = new_mB
    nutr = new_nutr

    # ── 2. Cell behaviors: division, differentiation, apoptosis ─────
    # Build action list first, apply afterward for synchronous update
    divisions = []   # (parent_r, parent_c, child_r, child_c, child_type, child_genome)
    deaths = []      # (r, c)
    diffs = []       # (r, c, new_type)

    # Somite clock phase
    clock_period = 12.0
    clock_phase = math.sin(2.0 * math.pi * gen / clock_period)

    cr, cc_center = rows // 2, cols // 2

    for r in range(rows):
        for c in range(cols):
            ct = cells[r][c]
            if ct == CELL_EMPTY or ct == CELL_DEAD:
                continue

            g = genomes[r][c]
            if not g:
                continue

            age[r][c] += 1
            cell_age = age[r][c]
            a_val = mA[r][c]
            b_val = mB[r][c]
            n_val = nutr[r][c]
            nn_count = _count_neighbors(cells, r, c, rows, cols)

            # ── Apoptosis (programmed cell death) ──
            apop = g["apoptosis"]
            # Increased apoptosis when too crowded or nutrient-starved
            if nn_count >= 7:
                apop += 0.05
            if n_val < 0.1:
                apop += 0.04
            # Sculpting apoptosis for limb/body shaping
            if extras.get("apoptosis_sculpt") and cell_age > 40:
                dist = math.sqrt((r - cr) ** 2 + (c - cc_center) ** 2)
                if dist > min(rows, cols) * 0.4:
                    apop += 0.03
            if random.random() < apop:
                deaths.append((r, c))
                continue

            # ── Differentiation ──
            if ct == CELL_STEM:
                # Morphogen-A gradient drives ecto vs endo
                if a_val > g["diff_thresh_A"] and b_val < g["diff_thresh_B"]:
                    diffs.append((r, c, CELL_ECTO))
                elif b_val > g["diff_thresh_B"] and a_val < g["diff_thresh_A"]:
                    diffs.append((r, c, CELL_ENDO))
                elif a_val > g["diff_thresh_A"] * 0.7 and b_val > g["diff_thresh_B"] * 0.7:
                    diffs.append((r, c, CELL_MESO))

                # Neural induction
                if extras.get("neural_induction"):
                    if a_val > 0.6 and b_val < 0.2 and cell_age > 15:
                        ntypes = _neighbor_types(cells, r, c, rows, cols)
                        if ntypes.get(CELL_ECTO, 0) >= 2:
                            diffs.append((r, c, CELL_NEURAL))

            # ── Division ──
            if nn_count < 6 and n_val > g["div_nutrient"]:
                div_prob = g["div_rate"]
                # Stem cells divide faster
                if ct == CELL_STEM:
                    div_prob *= 1.4
                # Signal cells rarely divide
                if ct == CELL_SIGNAL:
                    div_prob *= 0.2
                # Reduce division as organism grows
                total = self.morpho_total_cells
                if total > 50:
                    div_prob *= max(0.2, 1.0 - total / 800.0)

                if random.random() < div_prob:
                    empties = _empty_neighbors(cells, r, c, rows, cols)
                    if empties:
                        # Prefer dividing toward higher nutrient
                        empties.sort(key=lambda p: nutr[p[0]][p[1]], reverse=True)
                        # For bilateral symmetry, also bias toward midline early on
                        if symmetry == "bilateral" and gen < 80:
                            empties.sort(
                                key=lambda p: abs(p[1] - cc_center) + 0.5 * nutr[p[0]][p[1]],
                            )
                        nr, nc = empties[0]
                        child_genome = _mutate_genome(g)
                        # Child type: usually same as parent, sometimes stem
                        child_type = ct
                        if ct != CELL_STEM and random.random() < 0.15:
                            child_type = CELL_STEM  # de-differentiation
                        divisions.append((r, c, nr, nc, child_type, child_genome))

            # ── Somite clock ──
            if extras.get("somite_clock") and ct in (CELL_MESO, CELL_STEM):
                # Oscillating clock drives segmental identity
                self.morpho_clock[r][c] += 0.1
                if (math.sin(self.morpho_clock[r][c]) > 0.9
                        and a_val > 0.3 and cell_age > 8):
                    if ct == CELL_STEM:
                        diffs.append((r, c, CELL_MESO))

    # ── 3. Apply changes ────────────────────────────────────────────
    for r, c in deaths:
        cells[r][c] = CELL_DEAD
        self.morpho_total_cells -= 1
        self.morpho_total_deaths += 1

    for r, c, new_t in diffs:
        if cells[r][c] != CELL_DEAD:  # don't overwrite death
            cells[r][c] = new_t

    for pr, pc, cr_, cc_, child_type, child_genome in divisions:
        if cells[cr_][cc_] == CELL_EMPTY:
            cells[cr_][cc_] = child_type
            genomes[cr_][cc_] = child_genome
            age[cr_][cc_] = 0
            self.morpho_total_cells += 1
            self.morpho_total_divisions += 1

    # ── Clean up dead cells after some time ─────────────────────────
    if gen % 10 == 0:
        for r in range(rows):
            for c in range(cols):
                if cells[r][c] == CELL_DEAD and age[r][c] > 5:
                    cells[r][c] = CELL_EMPTY
                    genomes[r][c] = None

    # ── Regeneration: if enabled and past gen 100, cut and regrow ──
    if (extras.get("regeneration") and gen == 100):
        # Cut right half
        for r in range(rows):
            for c in range(cc_center, cols):
                if cells[r][c] != CELL_EMPTY:
                    cells[r][c] = CELL_EMPTY
                    genomes[r][c] = None
                    self.morpho_total_cells -= 1

    # ── Limb bud outgrowth ──
    if extras.get("limb_bud") and gen == 60:
        # Place a ZPA signaling center at the flank
        lr, lc = cr, cc_center + 8
        if 0 <= lr < rows and 0 <= lc < cols and cells[lr][lc] == CELL_EMPTY:
            zpa_g = _make_genome()
            zpa_g["morph_B_prod"] = 0.9
            zpa_g["morph_A_prod"] = 0.1
            zpa_g["div_rate"] = 0.08
            cells[lr][lc] = CELL_SIGNAL
            genomes[lr][lc] = zpa_g
            self.morpho_total_cells += 1

    self.morpho_max_cells = max(self.morpho_max_cells, self.morpho_total_cells)
    self.morpho_generation += 1


# ════════════════════════════════════════════════════════════════════════
#  Input handling
# ════════════════════════════════════════════════════════════════════════

def _handle_morpho_menu_key(self, key: int) -> bool:
    """Handle input in Morphogenesis preset menu."""
    presets = self.MORPHOGENESIS_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.morpho_menu_sel = (self.morpho_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.morpho_menu_sel = (self.morpho_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._morpho_init(self.morpho_menu_sel)
    elif key == ord("q") or key == 27:
        self.morpho_menu = False
        self._flash("Morphogenesis cancelled")
    return True


def _handle_morpho_key(self, key: int) -> bool:
    """Handle input in active Morphogenesis simulation."""
    if key == ord("q") or key == 27:
        self._exit_morpho_mode()
        return True
    if key == ord(" "):
        self.morpho_running = not self.morpho_running
        return True
    if key == ord("n") or key == ord("."):
        self._morpho_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.MORPHOGENESIS_PRESETS)
             if p[0] == self.morpho_preset_name), 0)
        self._morpho_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.morpho_mode = False
        self.morpho_running = False
        self.morpho_menu = True
        self.morpho_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20]
        idx = choices.index(self.morpho_steps_per_frame) if self.morpho_steps_per_frame in choices else 0
        self.morpho_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.morpho_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20]
        idx = choices.index(self.morpho_steps_per_frame) if self.morpho_steps_per_frame in choices else 0
        self.morpho_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.morpho_steps_per_frame} steps/frame")
        return True
    if key == ord("v"):
        views = ["cells", "morphA", "morphB", "nutrient"]
        idx = views.index(self.morpho_view) if self.morpho_view in views else 0
        self.morpho_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.morpho_view}")
        return True
    # Mutation rate: u/U
    if key == ord("u"):
        # Decrease all genome mutation rates
        for r in range(self.morpho_rows):
            for c in range(self.morpho_cols):
                g = self.morpho_genome_map[r][c]
                if g:
                    g["mutation_rate"] = max(0.0, g["mutation_rate"] - 0.005)
        self._flash("Mutation rate decreased")
        return True
    if key == ord("U"):
        for r in range(self.morpho_rows):
            for c in range(self.morpho_cols):
                g = self.morpho_genome_map[r][c]
                if g:
                    g["mutation_rate"] = min(0.2, g["mutation_rate"] + 0.005)
        self._flash("Mutation rate increased")
        return True
    # Nutrient rate: f/F
    if key == ord("f"):
        self.morpho_nutr_rate = max(0.05, self.morpho_nutr_rate - 0.05)
        self._flash(f"Nutrient rate: {self.morpho_nutr_rate:.2f}")
        return True
    if key == ord("F"):
        self.morpho_nutr_rate = min(1.0, self.morpho_nutr_rate + 0.05)
        self._flash(f"Nutrient rate: {self.morpho_nutr_rate:.2f}")
        return True
    # Place stem cell at mouse click
    if key == curses.KEY_MOUSE:
        try:
            _, mx, my, _, _ = curses.getmouse()
            r = my - 1
            c = mx // 2
            rows, cols = self.morpho_rows, self.morpho_cols
            if 0 <= r < rows and 0 <= c < cols and self.morpho_cells[r][c] == CELL_EMPTY:
                self.morpho_cells[r][c] = CELL_STEM
                self.morpho_genome_map[r][c] = _make_genome()
                self.morpho_age[r][c] = 0
                self.morpho_total_cells += 1
                self._flash("Placed stem cell")
        except curses.error:
            pass
        return True
    return True


# ════════════════════════════════════════════════════════════════════════
#  Drawing
# ════════════════════════════════════════════════════════════════════════

def _draw_morpho_menu(self, max_y: int, max_x: int):
    """Draw the Morphogenesis preset selection menu."""
    self.stdscr.erase()
    title = "── Morphogenesis: Embryonic Development ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.MORPHOGENESIS_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.morpho_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.morpho_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:28s} {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], attr)
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


def _draw_morpho(self, max_y: int, max_x: int):
    """Draw the active Morphogenesis simulation."""
    self.stdscr.erase()
    cells = self.morpho_cells
    mA = self.morpho_morph_A
    mB = self.morpho_morph_B
    nutr = self.morpho_nutrient
    rows, cols = self.morpho_rows, self.morpho_cols
    state = "▶ RUNNING" if self.morpho_running else "⏸ PAUSED"
    view = self.morpho_view

    # Count cell types
    type_counts = {}
    for r in range(rows):
        for c in range(cols):
            ct = cells[r][c]
            if ct != CELL_EMPTY:
                type_counts[ct] = type_counts.get(ct, 0) + 1

    # Title bar
    counts_str = " ".join(f"{CELL_NAMES.get(k, '?')}={v}" for k, v in sorted(type_counts.items()))
    title = (f" Morphogenesis: {self.morpho_preset_name}  |  gen {self.morpho_generation}"
             f"  |  cells={self.morpho_total_cells}  div={self.morpho_total_divisions}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Color mapping for cell types
    # color_pair assignments: 1=green, 2=yellow, 3=yellow/bold, 4=blue, 5=magenta, 6=cyan, 7=white
    cell_colors = {
        CELL_STEM: curses.color_pair(3) | curses.A_BOLD,    # bright yellow
        CELL_ECTO: curses.color_pair(6) | curses.A_BOLD,    # cyan
        CELL_MESO: curses.color_pair(1) | curses.A_BOLD,    # green
        CELL_ENDO: curses.color_pair(2),                     # yellow
        CELL_NEURAL: curses.color_pair(5) | curses.A_BOLD,  # magenta
        CELL_SIGNAL: curses.color_pair(7) | curses.A_BOLD,  # white bold
        CELL_DEAD: curses.color_pair(7) | curses.A_DIM,     # dim
    }

    for r in range(view_rows):
        sy = 1 + r
        for c in range(view_cols):
            sx = c * 2

            if view == "cells":
                ct = cells[r][c]
                if ct == CELL_EMPTY:
                    continue
                ch = CELL_CHARS.get(ct, "??")
                attr = cell_colors.get(ct, curses.color_pair(7))
            elif view == "morphA":
                v = mA[r][c]
                if v > 0.7:
                    ch, attr = "██", curses.color_pair(1) | curses.A_BOLD
                elif v > 0.4:
                    ch, attr = "▓▓", curses.color_pair(1)
                elif v > 0.2:
                    ch, attr = "▒▒", curses.color_pair(2)
                elif v > 0.05:
                    ch, attr = "░░", curses.color_pair(2) | curses.A_DIM
                else:
                    continue
            elif view == "morphB":
                v = mB[r][c]
                if v > 0.7:
                    ch, attr = "██", curses.color_pair(5) | curses.A_BOLD
                elif v > 0.4:
                    ch, attr = "▓▓", curses.color_pair(5)
                elif v > 0.2:
                    ch, attr = "▒▒", curses.color_pair(4)
                elif v > 0.05:
                    ch, attr = "░░", curses.color_pair(4) | curses.A_DIM
                else:
                    continue
            else:  # nutrient
                v = nutr[r][c]
                if v > 0.8:
                    ch, attr = "██", curses.color_pair(6) | curses.A_BOLD
                elif v > 0.6:
                    ch, attr = "▓▓", curses.color_pair(6)
                elif v > 0.4:
                    ch, attr = "▒▒", curses.color_pair(4)
                elif v > 0.2:
                    ch, attr = "░░", curses.color_pair(4) | curses.A_DIM
                else:
                    continue

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Stats line
    stats_y = max_y - 2
    if stats_y > 1:
        stats = f" {counts_str}  |  max={self.morpho_max_cells}  deaths={self.morpho_total_deaths}"
        try:
            self.stdscr.addstr(stats_y, 0, stats[:max_x - 1], curses.color_pair(7))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [u/U]=mutation [f/F]=nutrient [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════════
#  Registration
# ════════════════════════════════════════════════════════════════════════

def register(App):
    """Register morphogenesis mode methods on the App class."""
    App._enter_morpho_mode = _enter_morpho_mode
    App._exit_morpho_mode = _exit_morpho_mode
    App._morpho_init = _morpho_init
    App._morpho_step = _morpho_step
    App._handle_morpho_menu_key = _handle_morpho_menu_key
    App._handle_morpho_key = _handle_morpho_key
    App._draw_morpho_menu = _draw_morpho_menu
    App._draw_morpho = _draw_morpho
    App.MORPHOGENESIS_PRESETS = MORPHOGENESIS_PRESETS
