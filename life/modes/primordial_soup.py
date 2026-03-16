"""Mode: primordial_soup — Primordial Soup & Origin of Life abiogenesis simulation.

Model abiogenesis in a hydrothermal vent environment — simple molecules (H2, CO2,
NH3) catalyzed on mineral surfaces form amino acids and nucleotides, which
polymerize into self-replicating RNA strands (RNA World hypothesis), compete via
fitness-proportional replication with mutation/error catastrophe threshold,
encapsulate into lipid protocells that divide when they grow too large, and evolve
primitive metabolism (autocatalytic cycles).

Three visualization views:
  1. Molecular soup — vent plumes, mineral surfaces, floating protocells & polymer chains
  2. Phylogenetic tree — replicator lineage tree showing ancestor-descendant relationships
  3. Time-series graphs — molecular complexity, replicator diversity, protocell population,
     metabolic efficiency sparklines
"""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

PSOUP_PRESETS = [
    ("Black Smoker Vent",
     "Deep-sea hydrothermal chimneys pump energy & minerals — classic abiogenesis scenario",
     "black_smoker"),
    ("Warm Little Pond",
     "Darwin's shallow UV-irradiated pond with wet-dry cycling concentrating organics",
     "warm_pond"),
    ("RNA World Takeover",
     "Abundant nucleotides & high polymerization — watch RNA replicators dominate",
     "rna_world"),
    ("Error Catastrophe",
     "Sky-high mutation rate pushes replicators past the error threshold — information meltdown",
     "error_catastrophe"),
    ("Protocell Competition",
     "Pre-seeded protocells compete for resources — Darwinian selection in action",
     "protocell_comp"),
    ("LUCA Emergence",
     "Long-run scenario — watch chemistry bootstrap into the Last Universal Common Ancestor",
     "luca"),
]


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

# Molecule types (grid cells)
MOL_WATER   = 0
MOL_ROCK    = 1
MOL_VENT    = 2
MOL_H2      = 3   # hydrogen gas
MOL_CO2     = 4   # carbon dioxide
MOL_NH3     = 5   # ammonia
MOL_AMINO   = 6   # amino acid
MOL_NUCLEO  = 7   # nucleotide
MOL_LIPID   = 8   # amphiphilic lipid
MOL_MINERAL = 9   # mineral catalyst surface

MOL_NAMES = {
    MOL_WATER: "H2O", MOL_ROCK: "Rock", MOL_VENT: "Vent",
    MOL_H2: "H2", MOL_CO2: "CO2", MOL_NH3: "NH3",
    MOL_AMINO: "Amino", MOL_NUCLEO: "Nucleo", MOL_LIPID: "Lipid",
    MOL_MINERAL: "Mineral",
}

MOL_CHARS = {
    MOL_WATER: "  ", MOL_ROCK: "\u2593\u2593", MOL_VENT: "/\\",
    MOL_H2: "H\u2082", MOL_CO2: "CO", MOL_NH3: "NH",
    MOL_AMINO: "aa", MOL_NUCLEO: "nt", MOL_LIPID: "oo",
    MOL_MINERAL: "::",
}

# RNA bases
BASES = "AUCG"

# Views
VIEW_SOUP = "soup"
VIEW_TREE = "tree"
VIEW_GRAPH = "graph"
VIEWS = [VIEW_SOUP, VIEW_TREE, VIEW_GRAPH]

_NBRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NBRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
           (0, 1), (1, -1), (1, 0), (1, 1)]


# ══════════════════════════════════════════════════════════════════════
#  RNA Strand (replicator)
# ══════════════════════════════════════════════════════════════════════

class _RNAStrand:
    __slots__ = ("r", "c", "sequence", "fitness", "age", "energy",
                 "replication_count", "uid", "parent_uid", "generation",
                 "catalytic_efficiency")

    def __init__(self, r, c, sequence, uid, parent_uid=0, generation=0):
        self.r = r
        self.c = c
        self.sequence = sequence
        self.fitness = _compute_fitness(sequence)
        self.age = 0
        self.energy = 30.0
        self.replication_count = 0
        self.uid = uid
        self.parent_uid = parent_uid
        self.generation = generation
        self.catalytic_efficiency = _catalytic_score(sequence)


def _compute_fitness(seq):
    """Fitness from sequence — longer sequences with GC content and
    complementary palindromes (hairpin potential) score higher."""
    if not seq:
        return 0.01
    length_score = min(1.0, len(seq) / 15.0)
    gc = sum(1 for b in seq if b in "GC") / len(seq)
    gc_score = 1.0 - abs(gc - 0.5) * 2.0  # optimal at 50% GC
    # Palindrome bonus (hairpin → ribozyme activity)
    comp = {"A": "U", "U": "A", "G": "C", "C": "G"}
    pal = 0
    n = len(seq)
    for i in range(n // 2):
        if seq[i] == comp.get(seq[n - 1 - i], ""):
            pal += 1
    pal_score = pal / max(1, n // 2)
    return max(0.01, 0.3 * length_score + 0.4 * gc_score + 0.3 * pal_score)


def _catalytic_score(seq):
    """Autocatalytic cycle efficiency — sequences with runs of
    complementary pairs can catalyze reactions."""
    if len(seq) < 4:
        return 0.1
    runs = 0
    for i in range(len(seq) - 1):
        pair = seq[i] + seq[i + 1]
        if pair in ("AU", "UA", "GC", "CG"):
            runs += 1
    return min(1.0, 0.2 + runs / max(1, len(seq) - 1))


def _mutate_sequence(seq, mutation_rate):
    """Mutate a sequence — point mutations, insertions, deletions."""
    result = list(seq)
    mutated = False
    for i in range(len(result)):
        if random.random() < mutation_rate:
            result[i] = random.choice(BASES)
            mutated = True
    # Insertion
    if random.random() < mutation_rate * 0.3 and len(result) < 25:
        pos = random.randint(0, len(result))
        result.insert(pos, random.choice(BASES))
        mutated = True
    # Deletion
    if random.random() < mutation_rate * 0.3 and len(result) > 2:
        pos = random.randint(0, len(result) - 1)
        result.pop(pos)
        mutated = True
    return "".join(result), mutated


# ══════════════════════════════════════════════════════════════════════
#  Protocell
# ══════════════════════════════════════════════════════════════════════

class _Protocell:
    __slots__ = ("r", "c", "energy", "size", "max_size", "age",
                 "rna_strands", "lipid_layers", "metabolic_rate",
                 "uid", "parent_uid", "generation", "divisions")

    def __init__(self, r, c, uid, parent_uid=0, generation=0):
        self.r = r
        self.c = c
        self.energy = 50.0
        self.size = 1.0
        self.max_size = 3.0 + random.uniform(0, 2.0)
        self.age = 0
        self.rna_strands = []    # list of _RNAStrand uids inside
        self.lipid_layers = 1
        self.metabolic_rate = 0.1
        self.uid = uid
        self.parent_uid = parent_uid
        self.generation = generation
        self.divisions = 0


# ══════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════

def _count_neighbors(grid, r, c, rows, cols, cell_types):
    count = 0
    for dr, dc in _NBRS8:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            if grid[nr][nc] in cell_types:
                count += 1
    return count


def _adj_cells(grid, r, c, rows, cols, allowed):
    out = []
    for dr, dc in _NBRS4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            if grid[nr][nc] in allowed:
                out.append((nr, nc))
    return out


def _energy_at(r, c, vents, vent_energy, temperature):
    base = max(0.01, (temperature + 20.0) / 120.0) * 0.1
    for vr, vc in vents:
        dist = math.hypot(r - vr, c - vc)
        if dist < 1:
            dist = 1
        base += vent_energy / (1.0 + dist * 0.3)
    return min(1.0, base)


def _sparkline(values, width):
    """Return a sparkline string of given width from a list of values."""
    if not values:
        return " " * width
    # Sample values to fit width
    n = len(values)
    if n > width:
        step = n / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values[-width:]
    lo = min(sampled) if sampled else 0
    hi = max(sampled) if sampled else 1
    rng = hi - lo if hi > lo else 1
    blocks = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    out = []
    for v in sampled:
        idx = int((v - lo) / rng * 7.99)
        idx = max(0, min(7, idx))
        out.append(blocks[idx])
    return "".join(out).ljust(width)


# ══════════════════════════════════════════════════════════════════════
#  Enter / Exit
# ══════════════════════════════════════════════════════════════════════

def _enter_psoup_mode(self):
    self.psoup_mode = True
    self.psoup_menu = True
    self.psoup_menu_sel = 0


def _exit_psoup_mode(self):
    self.psoup_mode = False
    self.psoup_menu = False
    self.psoup_running = False
    for attr in list(vars(self)):
        if attr.startswith("psoup_") and attr != "psoup_mode":
            try:
                delattr(self, attr)
            except AttributeError:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _psoup_init(self, preset_idx: int):
    name, desc, preset_id = PSOUP_PRESETS[preset_idx]
    self.psoup_preset_name = name
    self.psoup_preset_id = preset_id
    self.psoup_preset_idx = preset_idx

    max_y, max_x = self.stdscr.getmaxyx()
    self.psoup_rows = max(20, max_y - 4)
    self.psoup_cols = max(30, (max_x - 1) // 2)

    self.psoup_generation = 0
    self.psoup_view = VIEW_SOUP
    self.psoup_running = False
    self.psoup_menu = False
    self.psoup_next_uid = 1

    # Preset parameters
    params = _get_preset_params(preset_id)
    self.psoup_params = params

    # Build grid
    rows, cols = self.psoup_rows, self.psoup_cols
    grid = [[MOL_WATER] * cols for _ in range(rows)]

    # Rock substrate at bottom
    for r in range(int(rows * 0.82), rows):
        for c in range(cols):
            if random.random() < 0.65:
                grid[r][c] = MOL_ROCK

    # Mineral surfaces scattered on rock
    for r in range(int(rows * 0.5), rows):
        for c in range(cols):
            if grid[r][c] == MOL_ROCK and random.random() < params["mineral_density"]:
                grid[r][c] = MOL_MINERAL

    # Hydrothermal vents
    vent_positions = []
    for _ in range(params["n_vents"]):
        vr = random.randint(int(rows * 0.55), rows - 3)
        vc = random.randint(3, cols - 4)
        vent_positions.append((vr, vc))
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = vr + dr, vc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    grid[nr][nc] = MOL_VENT
    self.psoup_vents = vent_positions

    # Scatter simple molecules
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != MOL_WATER:
                continue
            roll = random.random()
            if roll < params["h2_density"]:
                grid[r][c] = MOL_H2
            elif roll < params["h2_density"] + params["co2_density"]:
                grid[r][c] = MOL_CO2
            elif roll < params["h2_density"] + params["co2_density"] + params["nh3_density"]:
                grid[r][c] = MOL_NH3
            elif roll < params["h2_density"] + params["co2_density"] + params["nh3_density"] + params["lipid_density"]:
                grid[r][c] = MOL_LIPID

    # Pre-seed amino acids and nucleotides for some presets
    if params.get("preseed_amino", 0) > 0:
        placed = 0
        while placed < params["preseed_amino"]:
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            if grid[r][c] == MOL_WATER:
                grid[r][c] = MOL_AMINO
                placed += 1

    if params.get("preseed_nucleo", 0) > 0:
        placed = 0
        while placed < params["preseed_nucleo"]:
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            if grid[r][c] == MOL_WATER:
                grid[r][c] = MOL_NUCLEO
                placed += 1

    self.psoup_grid = grid

    # Energy grid
    self.psoup_energy = [
        [_energy_at(r, c, vent_positions, params["vent_energy"], params["temperature"])
         for c in range(cols)]
        for r in range(rows)
    ]

    # RNA strands
    self.psoup_rna = []

    # Pre-seed RNA for some presets
    if params.get("preseed_rna", 0) > 0:
        for _ in range(params["preseed_rna"]):
            r = random.randint(2, rows - 5)
            c = random.randint(2, cols - 3)
            if grid[r][c] == MOL_WATER:
                seq = "".join(random.choice(BASES) for _ in range(random.randint(4, 10)))
                uid = self.psoup_next_uid
                self.psoup_next_uid += 1
                self.psoup_rna.append(_RNAStrand(r, c, seq, uid))

    # Protocells
    self.psoup_protocells = []

    # Pre-seed protocells for competition preset
    if params.get("preseed_protocells", 0) > 0:
        for _ in range(params["preseed_protocells"]):
            r = random.randint(2, rows - 5)
            c = random.randint(2, cols - 3)
            uid = self.psoup_next_uid
            self.psoup_next_uid += 1
            pc = _Protocell(r, c, uid)
            pc.energy = random.uniform(60, 120)
            pc.metabolic_rate = random.uniform(0.1, 0.5)
            pc.size = random.uniform(1.0, 2.0)
            self.psoup_protocells.append(pc)

    # Phylogenetic tree records: uid -> {parent_uid, generation, sequence, birth_gen, alive}
    self.psoup_phylo = {}

    # Time-series history
    self.psoup_history = {
        "molecules": [],     # total H2+CO2+NH3
        "amino": [],
        "nucleo": [],
        "rna_count": [],
        "rna_diversity": [],  # unique sequences
        "protocells": [],
        "avg_fitness": [],
        "avg_metabolic": [],
        "complexity": [],     # avg RNA length
        "error_rate": [],     # effective mutation count
    }
    self.psoup_max_history = 300


def _get_preset_params(preset_id):
    defaults = {
        "n_vents": 4, "vent_energy": 0.8, "temperature": 80.0,
        "mineral_density": 0.12,
        "h2_density": 0.03, "co2_density": 0.03, "nh3_density": 0.02,
        "lipid_density": 0.015,
        "uv_level": 0.0,
        "polymerize_rate": 0.035,
        "replicate_rate": 0.04,
        "mutation_rate": 0.05,
        "error_threshold": 0.15,  # Eigen error catastrophe threshold
        "lipid_assemble_rate": 0.03,
        "catalysis_boost": 1.0,
        "preseed_amino": 0, "preseed_nucleo": 0,
        "preseed_rna": 0, "preseed_protocells": 0,
    }
    overrides = {
        "black_smoker": {
            "n_vents": 5, "vent_energy": 1.0, "temperature": 95.0,
            "mineral_density": 0.15,
        },
        "warm_pond": {
            "n_vents": 2, "vent_energy": 0.3, "temperature": 40.0,
            "uv_level": 0.6, "mineral_density": 0.08,
            "h2_density": 0.02, "co2_density": 0.04, "nh3_density": 0.03,
            "lipid_density": 0.025,
        },
        "rna_world": {
            "n_vents": 3, "vent_energy": 0.7, "temperature": 70.0,
            "preseed_nucleo": 80,
            "polymerize_rate": 0.06, "replicate_rate": 0.07,
            "mutation_rate": 0.04,
        },
        "error_catastrophe": {
            "n_vents": 3, "vent_energy": 0.6, "temperature": 65.0,
            "preseed_rna": 30, "preseed_nucleo": 50,
            "mutation_rate": 0.25, "error_threshold": 0.12,
            "replicate_rate": 0.06,
        },
        "protocell_comp": {
            "n_vents": 4, "vent_energy": 0.7, "temperature": 60.0,
            "preseed_protocells": 15, "preseed_rna": 20,
            "preseed_nucleo": 40, "preseed_amino": 30,
            "lipid_density": 0.03, "lipid_assemble_rate": 0.05,
        },
        "luca": {
            "n_vents": 6, "vent_energy": 0.9, "temperature": 85.0,
            "mineral_density": 0.14,
            "catalysis_boost": 1.5,
            "h2_density": 0.04, "co2_density": 0.04, "nh3_density": 0.03,
        },
    }
    params = dict(defaults)
    if preset_id in overrides:
        params.update(overrides[preset_id])
    return params


# ══════════════════════════════════════════════════════════════════════
#  Simulation step
# ══════════════════════════════════════════════════════════════════════

def _psoup_step(self):
    grid = self.psoup_grid
    rows, cols = self.psoup_rows, self.psoup_cols
    params = self.psoup_params
    energy_grid = self.psoup_energy
    vents = self.psoup_vents
    rna_list = self.psoup_rna
    protocells = self.psoup_protocells
    gen = self.psoup_generation

    temperature = params["temperature"]
    uv = params["uv_level"]
    poly_rate = params["polymerize_rate"]
    repl_rate = params["replicate_rate"]
    mut_rate = params["mutation_rate"]
    err_thresh = params["error_threshold"]
    lipid_rate = params["lipid_assemble_rate"]
    cat_boost = params["catalysis_boost"]

    # Temperature-dependent rate modifier
    if temperature < 10:
        temp_mod = 0.3
    elif temperature < 40:
        temp_mod = 0.5 + temperature / 80.0
    elif temperature < 90:
        temp_mod = 1.0
    else:
        temp_mod = max(0.4, 1.0 - (temperature - 90) / 120.0)

    new_grid = [row[:] for row in grid]

    # ── 0. Vent activity: emit H2, CO2, minerals ──
    for vr, vc in vents:
        for dr, dc in _NBRS8:
            nr, nc = vr + dr, vc + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] == MOL_WATER:
                    roll = random.random()
                    if roll < 0.08:
                        new_grid[nr][nc] = MOL_H2
                    elif roll < 0.14:
                        new_grid[nr][nc] = MOL_CO2
                    elif roll < 0.17:
                        new_grid[nr][nc] = MOL_NH3
        # Plume: upward mineral/heat dispersal
        for i in range(1, random.randint(2, 5)):
            pr = vr - i
            pc2 = vc + random.randint(-1, 1)
            if 0 <= pr < rows and 0 <= pc2 < cols:
                if grid[pr][pc2] == MOL_WATER and random.random() < 0.06:
                    new_grid[pr][pc2] = random.choice([MOL_H2, MOL_CO2])

    # ── 1. Chemical reactions ──
    mutations_this_step = 0

    for r in range(rows):
        for c in range(cols):
            ct = grid[r][c]
            e = energy_grid[r][c]

            if ct == MOL_H2:
                # H2 + CO2 on mineral → amino acid (Fischer-Tropsch type)
                mineral_near = _count_neighbors(grid, r, c, rows, cols, {MOL_MINERAL})
                co2_near = _count_neighbors(grid, r, c, rows, cols, {MOL_CO2})
                if mineral_near >= 1 and co2_near >= 1 and e > 0.2:
                    if random.random() < 0.025 * temp_mod * e * cat_boost:
                        new_grid[r][c] = MOL_AMINO
                        # Consume a CO2
                        adj = _adj_cells(grid, r, c, rows, cols, {MOL_CO2})
                        if adj:
                            ar, ac = random.choice(adj)
                            new_grid[ar][ac] = MOL_WATER

                # H2 + NH3 on mineral → nucleotide base
                nh3_near = _count_neighbors(grid, r, c, rows, cols, {MOL_NH3})
                if mineral_near >= 1 and nh3_near >= 1 and e > 0.25:
                    if random.random() < 0.02 * temp_mod * e * cat_boost:
                        new_grid[r][c] = MOL_NUCLEO
                        adj = _adj_cells(grid, r, c, rows, cols, {MOL_NH3})
                        if adj:
                            ar, ac = random.choice(adj)
                            new_grid[ar][ac] = MOL_WATER

                # H2 slowly drifts upward
                if r > 0 and grid[r - 1][c] == MOL_WATER and random.random() < 0.05:
                    new_grid[r][c] = MOL_WATER
                    new_grid[r - 1][c] = MOL_H2

            elif ct == MOL_CO2:
                # CO2 dissolves / drifts
                if random.random() < 0.003:
                    new_grid[r][c] = MOL_WATER

            elif ct == MOL_NH3:
                # NH3 + CO2 near energy → nucleotide
                co2_near = _count_neighbors(grid, r, c, rows, cols, {MOL_CO2})
                if co2_near >= 1 and e > 0.3:
                    if random.random() < 0.015 * temp_mod * e * cat_boost:
                        new_grid[r][c] = MOL_NUCLEO
                        adj = _adj_cells(grid, r, c, rows, cols, {MOL_CO2})
                        if adj:
                            ar, ac = random.choice(adj)
                            new_grid[ar][ac] = MOL_WATER

            elif ct == MOL_AMINO:
                # Amino acids can become lipids (amphiphile formation)
                if _count_neighbors(grid, r, c, rows, cols, {MOL_MINERAL}) >= 1:
                    if random.random() < 0.008 * temp_mod:
                        new_grid[r][c] = MOL_LIPID
                # UV destroys amino acids
                if uv > 0 and r < rows // 4 and random.random() < uv * 0.01:
                    new_grid[r][c] = MOL_WATER

            elif ct == MOL_NUCLEO:
                # Nucleotides polymerize into RNA near mineral + other nucleotides
                nucleo_near = _count_neighbors(grid, r, c, rows, cols, {MOL_NUCLEO})
                mineral_near = _count_neighbors(grid, r, c, rows, cols, {MOL_MINERAL})
                if nucleo_near >= 2 and (mineral_near >= 1 or e > 0.4):
                    if random.random() < poly_rate * temp_mod * e * cat_boost:
                        # Create an RNA strand
                        seq_len = random.randint(3, 6)
                        seq = "".join(random.choice(BASES) for _ in range(seq_len))
                        uid = self.psoup_next_uid
                        self.psoup_next_uid += 1
                        rna = _RNAStrand(r, c, seq, uid)
                        rna_list.append(rna)
                        self.psoup_phylo[uid] = {
                            "parent": 0, "gen": 0, "seq": seq,
                            "birth": gen, "alive": True,
                        }
                        new_grid[r][c] = MOL_WATER
                        # Consume adjacent nucleotides
                        adj = _adj_cells(grid, r, c, rows, cols, {MOL_NUCLEO})
                        consumed = 0
                        for ar, ac in adj:
                            if consumed >= 2:
                                break
                            new_grid[ar][ac] = MOL_WATER
                            consumed += 1

                # UV damages nucleotides
                if uv > 0 and r < rows // 4 and random.random() < uv * 0.012:
                    new_grid[r][c] = MOL_WATER

            elif ct == MOL_LIPID:
                # Lipids self-assemble (handled in protocell formation below)
                # Slow degradation
                if random.random() < 0.002:
                    new_grid[r][c] = MOL_WATER

    # ── 2. RNA replication & mutation ──
    new_rna = []
    rna_positions = {}  # (r,c) -> rna for collision detection

    for rna in rna_list:
        rr, rc = rna.r, rna.c
        if not (0 <= rr < rows and 0 <= rc < cols):
            self.psoup_phylo.get(rna.uid, {})["alive"] = False
            continue

        rna.age += 1
        e = energy_grid[rr][rc]

        # Energy from environment
        rna.energy += e * 3.0
        rna.energy -= 1.0  # maintenance cost

        # Death from energy depletion or old age
        if rna.energy <= 0 or rna.age > 500:
            # RNA degrades back to nucleotides
            if new_grid[rr][rc] == MOL_WATER:
                new_grid[rr][rc] = MOL_NUCLEO
            self.psoup_phylo.get(rna.uid, {})["alive"] = False
            continue

        # Fitness-proportional replication
        nucleo_near = _count_neighbors(new_grid, rr, rc, rows, cols, {MOL_NUCLEO})
        if nucleo_near >= 1 and rna.energy > 15:
            # Replication probability proportional to fitness
            prob = repl_rate * rna.fitness * temp_mod * e * cat_boost
            if random.random() < prob:
                adj_water = _adj_cells(new_grid, rr, rc, rows, cols, {MOL_WATER})
                adj_nucleo = _adj_cells(new_grid, rr, rc, rows, cols, {MOL_NUCLEO})
                if adj_water and adj_nucleo:
                    wr, wc = random.choice(adj_water)
                    # Consume nucleotides
                    nr2, nc2 = random.choice(adj_nucleo)
                    new_grid[nr2][nc2] = MOL_WATER

                    # Mutate daughter
                    new_seq, did_mutate = _mutate_sequence(rna.sequence, mut_rate)
                    if did_mutate:
                        mutations_this_step += 1

                    # Error catastrophe check
                    if mut_rate > err_thresh and len(rna.sequence) > 3:
                        # Above error threshold — information degrades
                        if random.random() < (mut_rate - err_thresh) * 3:
                            new_seq = "".join(random.choice(BASES) for _ in range(len(new_seq)))

                    uid = self.psoup_next_uid
                    self.psoup_next_uid += 1
                    daughter = _RNAStrand(wr, wc, new_seq, uid,
                                          parent_uid=rna.uid,
                                          generation=rna.generation + 1)
                    daughter.energy = rna.energy * 0.4
                    rna.energy *= 0.6
                    rna.replication_count += 1
                    new_rna.append(daughter)

                    self.psoup_phylo[uid] = {
                        "parent": rna.uid, "gen": rna.generation + 1,
                        "seq": new_seq, "birth": gen, "alive": True,
                    }

        # Autocatalytic cycle: RNA near amino acids catalyzes more amino acid formation
        if rna.catalytic_efficiency > 0.3:
            h2_near = _count_neighbors(new_grid, rr, rc, rows, cols, {MOL_H2})
            co2_near = _count_neighbors(new_grid, rr, rc, rows, cols, {MOL_CO2})
            if h2_near >= 1 and co2_near >= 1:
                if random.random() < 0.03 * rna.catalytic_efficiency * cat_boost:
                    adj_h2 = _adj_cells(new_grid, rr, rc, rows, cols, {MOL_H2})
                    if adj_h2:
                        ar, ac = random.choice(adj_h2)
                        new_grid[ar][ac] = MOL_AMINO
                        rna.energy += 2.0  # catalysis provides energy

        # Movement: random walk, bias toward energy
        if random.random() < 0.12:
            best = None
            best_e = -1
            for dr, dc in _NBRS4:
                nr, nc = rr + dr, rc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if new_grid[nr][nc] == MOL_WATER:
                        ee = energy_grid[nr][nc]
                        if ee > best_e:
                            best_e = ee
                            best = (nr, nc)
            if best:
                rna.r, rna.c = best

        new_rna.append(rna)
        rna_positions[(rna.r, rna.c)] = rna

    self.psoup_rna = new_rna

    # ── 3. Lipid vesicle formation & Protocell encapsulation ──
    # Check for lipid clusters that form vesicles → protocells
    for r in range(rows):
        for c in range(cols):
            if new_grid[r][c] != MOL_LIPID:
                continue
            lipid_near = _count_neighbors(new_grid, r, c, rows, cols, {MOL_LIPID})
            if lipid_near >= 3 and random.random() < lipid_rate * temp_mod:
                # Vesicle formed — check if RNA nearby to make protocell
                nearby_rna = []
                for rna in self.psoup_rna:
                    dist = abs(rna.r - r) + abs(rna.c - c)
                    if dist <= 2:
                        nearby_rna.append(rna)
                if nearby_rna and random.random() < 0.15:
                    # Protocell formation!
                    uid = self.psoup_next_uid
                    self.psoup_next_uid += 1
                    pc = _Protocell(r, c, uid)
                    for rna in nearby_rna[:3]:
                        pc.rna_strands.append(rna.uid)
                        pc.metabolic_rate += rna.catalytic_efficiency * 0.2
                    pc.lipid_layers = min(3, lipid_near // 2)
                    protocells.append(pc)
                    # Consume lipids
                    new_grid[r][c] = MOL_WATER
                    adj = _adj_cells(new_grid, r, c, rows, cols, {MOL_LIPID})
                    for ar, ac in adj[:2]:
                        new_grid[ar][ac] = MOL_WATER

    # ── 4. Protocell dynamics ──
    alive_proto = []
    for pc in protocells:
        pr, pcc = pc.r, pc.c
        if not (0 <= pr < rows and 0 <= pcc < cols):
            continue
        pc.age += 1
        e = energy_grid[pr][pcc]

        # Metabolism: consume nearby molecules for energy
        food_types = {MOL_AMINO, MOL_NUCLEO, MOL_H2, MOL_CO2}
        food = _adj_cells(new_grid, pr, pcc, rows, cols, food_types)
        if food:
            fr, fc = random.choice(food)
            gain = 10 + pc.metabolic_rate * 15
            pc.energy += gain
            new_grid[fr][fc] = MOL_WATER

        # Autocatalytic metabolism boost
        pc.energy += pc.metabolic_rate * e * 5.0
        # Living cost
        pc.energy -= 2.0 + pc.size * 0.5

        # Growth
        if pc.energy > 40:
            pc.size += 0.02 * pc.metabolic_rate
            # Absorb lipids to grow membrane
            lip_adj = _adj_cells(new_grid, pr, pcc, rows, cols, {MOL_LIPID})
            if lip_adj and random.random() < 0.1:
                lr, lc = random.choice(lip_adj)
                new_grid[lr][lc] = MOL_WATER
                pc.lipid_layers = min(5, pc.lipid_layers + 1)
                pc.size += 0.1

        # Death
        if pc.energy <= 0 or pc.age > 800:
            # Release contents
            if 0 <= pr < rows and 0 <= pcc < cols:
                new_grid[pr][pcc] = MOL_LIPID  # membrane remnants
            continue

        # Division when too large
        if pc.size >= pc.max_size and pc.energy > 60:
            adj_water = _adj_cells(new_grid, pr, pcc, rows, cols, {MOL_WATER})
            if adj_water:
                wr, wc = random.choice(adj_water)
                uid = self.psoup_next_uid
                self.psoup_next_uid += 1
                daughter = _Protocell(wr, wc, uid, parent_uid=pc.uid,
                                      generation=pc.generation + 1)
                daughter.energy = pc.energy * 0.45
                pc.energy *= 0.55
                daughter.metabolic_rate = pc.metabolic_rate
                # Mutate metabolic rate slightly
                if random.random() < mut_rate:
                    daughter.metabolic_rate += random.uniform(-0.05, 0.08)
                    daughter.metabolic_rate = max(0.05, min(1.0, daughter.metabolic_rate))
                daughter.lipid_layers = max(1, pc.lipid_layers // 2)
                daughter.size = 1.0
                pc.size = 1.0
                pc.divisions += 1
                # Split RNA strands
                half = len(pc.rna_strands) // 2
                daughter.rna_strands = pc.rna_strands[half:]
                pc.rna_strands = pc.rna_strands[:half]
                alive_proto.append(daughter)

        # Movement
        if random.random() < 0.08:
            adj = _adj_cells(new_grid, pr, pcc, rows, cols, {MOL_WATER})
            if adj:
                best = max(adj, key=lambda p: energy_grid[p[0]][p[1]])
                pc.r, pc.c = best

        alive_proto.append(pc)

    self.psoup_protocells = alive_proto
    self.psoup_grid = new_grid

    # ── 5. UV photochemistry at surface ──
    if uv > 0:
        for c in range(cols):
            for r in range(min(4, rows)):
                if new_grid[r][c] == MOL_WATER and random.random() < uv * 0.006:
                    new_grid[r][c] = random.choice([MOL_H2, MOL_NH3])

    # ── 6. Statistics ──
    counts = {t: 0 for t in range(11)}
    for r in range(rows):
        for c in range(cols):
            ct = new_grid[r][c]
            if ct in counts:
                counts[ct] += 1

    h = self.psoup_history
    h["molecules"].append(counts[MOL_H2] + counts[MOL_CO2] + counts[MOL_NH3])
    h["amino"].append(counts[MOL_AMINO])
    h["nucleo"].append(counts[MOL_NUCLEO])
    h["rna_count"].append(len(self.psoup_rna))
    unique_seqs = len(set(rna.sequence for rna in self.psoup_rna)) if self.psoup_rna else 0
    h["rna_diversity"].append(unique_seqs)
    h["protocells"].append(len(self.psoup_protocells))
    avg_fit = (sum(rna.fitness for rna in self.psoup_rna) / len(self.psoup_rna)
               if self.psoup_rna else 0)
    h["avg_fitness"].append(avg_fit)
    avg_met = (sum(pc.metabolic_rate for pc in self.psoup_protocells) / len(self.psoup_protocells)
               if self.psoup_protocells else 0)
    h["avg_metabolic"].append(avg_met)
    avg_len = (sum(len(rna.sequence) for rna in self.psoup_rna) / len(self.psoup_rna)
               if self.psoup_rna else 0)
    h["complexity"].append(avg_len)
    h["error_rate"].append(mutations_this_step)

    # Trim history
    mx = self.psoup_max_history
    for k in h:
        if len(h[k]) > mx:
            h[k] = h[k][-mx:]

    self.psoup_generation += 1


# ══════════════════════════════════════════════════════════════════════
#  Input handling
# ══════════════════════════════════════════════════════════════════════

def _handle_psoup_menu_key(self, key):
    presets = PSOUP_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.psoup_menu_sel = (self.psoup_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.psoup_menu_sel = (self.psoup_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        _psoup_init(self, self.psoup_menu_sel)
    elif key == ord("q") or key == 27:
        self.psoup_menu = False
        _exit_psoup_mode(self)
    return True


def _handle_psoup_key(self, key):
    if key == ord("q") or key == 27:
        _exit_psoup_mode(self)
        return True
    if key == ord(" "):
        self.psoup_running = not self.psoup_running
        return True
    if key == ord("n") or key == ord("."):
        _psoup_step(self)
        return True
    if key == ord("r"):
        _psoup_init(self, self.psoup_preset_idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.psoup_running = False
        self.psoup_menu = True
        self.psoup_menu_sel = 0
        return True
    if key == ord("v"):
        idx = VIEWS.index(self.psoup_view) if self.psoup_view in VIEWS else 0
        self.psoup_view = VIEWS[(idx + 1) % len(VIEWS)]
        return True
    if key == ord("l"):
        # Lightning strike — create monomers
        rows, cols = self.psoup_rows, self.psoup_cols
        sr = random.randint(0, rows // 3)
        sc = random.randint(0, cols - 1)
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = sr + dr, sc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if self.psoup_grid[nr][nc] == MOL_WATER and random.random() < 0.5:
                        self.psoup_grid[nr][nc] = random.choice([MOL_H2, MOL_CO2, MOL_NH3])
        return True
    if key == ord("h"):
        self.psoup_params["temperature"] += 15
        return True
    if key == ord("c"):
        self.psoup_params["temperature"] -= 15
        return True
    if key == ord("u"):
        self.psoup_params["uv_level"] = 0.6 if self.psoup_params["uv_level"] == 0 else 0.0
        return True
    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Menu
# ══════════════════════════════════════════════════════════════════════

def _draw_psoup_menu(self, max_y, max_x):
    self.stdscr.erase()
    title = "\u2550\u2550 Primordial Soup & Origin of Life \u2550\u2550 Select Scenario \u2550\u2550"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(PSOUP_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        marker = "\u25b6" if i == self.psoup_menu_sel else " "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.psoup_menu_sel else curses.color_pair(7))
        try:
            self.stdscr.addstr(y, 2, f" {marker} {name:30s}"[:max_x - 3], attr)
        except curses.error:
            pass
        desc_attr = (curses.color_pair(6) if i == self.psoup_menu_sel
                     else curses.color_pair(7) | curses.A_DIM)
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], desc_attr)
        except curses.error:
            pass

    leg_y = 3 + len(PSOUP_PRESETS) * 2 + 1
    legend = [
        "Chemistry:  H\u2082 + CO\u2082 + NH\u2083 \u2192 amino acids + nucleotides (on mineral catalysts)",
        "RNA World:  nucleotides \u2192 RNA polymers \u2192 self-replicating ribozymes",
        "Protocells: lipid vesicles + RNA replicators \u2192 dividing protocells",
        "Evolution:  fitness-proportional replication, mutation, error catastrophe",
    ]
    for i, line in enumerate(legend):
        if leg_y + i < max_y - 2:
            try:
                self.stdscr.addstr(leg_y + i, 4, line[:max_x - 6],
                                   curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass

    if max_y - 1 > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Soup view
# ══════════════════════════════════════════════════════════════════════

def _draw_psoup_soup(self, max_y, max_x):
    grid = self.psoup_grid
    rows, cols = self.psoup_rows, self.psoup_cols
    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)
    gen = self.psoup_generation

    # Color map
    colors = {
        MOL_ROCK: curses.color_pair(7) | curses.A_DIM,
        MOL_VENT: curses.color_pair(1) | curses.A_BOLD,
        MOL_H2: curses.color_pair(4) | curses.A_DIM,
        MOL_CO2: curses.color_pair(7) | curses.A_DIM,
        MOL_NH3: curses.color_pair(6) | curses.A_DIM,
        MOL_AMINO: curses.color_pair(3),
        MOL_NUCLEO: curses.color_pair(6) | curses.A_BOLD,
        MOL_LIPID: curses.color_pair(2),
        MOL_MINERAL: curses.color_pair(2) | curses.A_DIM,
    }

    for r in range(view_rows):
        sy = 1 + r
        for c in range(view_cols):
            sx = c * 2
            ct = grid[r][c]
            if ct == MOL_WATER:
                # Depth shading for water
                depth = r / max(1, rows - 1)
                if depth > 0.6:
                    try:
                        self.stdscr.addstr(sy, sx, "\u2591\u2591", curses.color_pair(4) | curses.A_DIM)
                    except curses.error:
                        pass
                continue

            ch = MOL_CHARS.get(ct, "??")
            attr = colors.get(ct, curses.color_pair(7))

            # Vent plume animation
            if ct == MOL_VENT:
                phase = (gen + r + c) % 3
                ch = ["/\\", "\\/", "||"][phase]
                attr = curses.color_pair(1) | curses.A_BOLD

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Draw RNA strands as bright markers
    for rna in self.psoup_rna:
        sr, sc = rna.r, rna.c
        if 0 <= sr < view_rows and 0 <= sc < view_cols:
            sy = 1 + sr
            sx = sc * 2
            # Size indicator based on sequence length
            if len(rna.sequence) >= 10:
                ch = "RR"
                attr = curses.color_pair(1) | curses.A_BOLD
            elif len(rna.sequence) >= 6:
                ch = "Rr"
                attr = curses.color_pair(6) | curses.A_BOLD
            else:
                ch = "rr"
                attr = curses.color_pair(6)
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Draw protocells as prominent markers
    for pc in self.psoup_protocells:
        pr, pcc = pc.r, pc.c
        if 0 <= pr < view_rows and 0 <= pcc < view_cols:
            sy = 1 + pr
            sx = pcc * 2
            phase = (gen + pr + pcc) % 4
            if pc.size >= 2.5:
                ch = "@@"
            elif pc.size >= 1.5:
                ch = "()"
            else:
                ch = "<>"
            if phase < 2:
                attr = curses.color_pair(5) | curses.A_BOLD
            else:
                attr = curses.color_pair(3) | curses.A_BOLD
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Phylogenetic tree view
# ══════════════════════════════════════════════════════════════════════

def _draw_psoup_tree(self, max_y, max_x):
    phylo = self.psoup_phylo
    if not phylo:
        try:
            self.stdscr.addstr(max_y // 2, max(0, (max_x - 30) // 2),
                               "No replicator lineages yet...",
                               curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass
        return

    # Build tree: find roots and living tips
    children = {}
    for uid, info in phylo.items():
        p = info["parent"]
        if p not in children:
            children[p] = []
        children[p].append(uid)

    # Find roots (parent == 0)
    roots = children.get(0, [])
    if not roots:
        roots = [min(phylo.keys())]

    # BFS layout — allocate each node a column, generation gives row
    # Limit to most recent/active lineages
    alive_uids = {uid for uid, info in phylo.items() if info["alive"]}
    # Trace ancestry of alive nodes
    relevant = set()
    for uid in alive_uids:
        cur = uid
        while cur in phylo and cur not in relevant:
            relevant.add(cur)
            cur = phylo[cur]["parent"]

    # If too few relevant, include recent births
    if len(relevant) < 5:
        by_birth = sorted(phylo.keys(), key=lambda u: phylo[u]["birth"], reverse=True)
        for uid in by_birth[:20]:
            relevant.add(uid)
            cur = phylo[uid]["parent"]
            while cur in phylo:
                relevant.add(cur)
                cur = phylo[cur]["parent"]

    # Layout: DFS from roots, assign x positions
    avail_w = max_x - 4
    avail_h = max_y - 4
    if avail_w < 10 or avail_h < 5:
        return

    positions = {}  # uid -> (x, y)
    x_counter = [0]

    def _layout(uid, depth):
        if uid not in relevant or depth > avail_h:
            return
        kids = [k for k in children.get(uid, []) if k in relevant]
        if not kids:
            positions[uid] = (x_counter[0], depth)
            x_counter[0] += 1
        else:
            for kid in kids:
                _layout(kid, depth + 1)
            child_xs = [positions[k][0] for k in kids if k in positions]
            if child_xs:
                my_x = (min(child_xs) + max(child_xs)) / 2
            else:
                my_x = x_counter[0]
                x_counter[0] += 1
            positions[uid] = (my_x, depth)

    for root in roots:
        if root in relevant:
            _layout(root, 0)

    if not positions:
        return

    # Scale to screen
    min_x = min(p[0] for p in positions.values())
    max_x_pos = max(p[0] for p in positions.values())
    min_depth = min(p[1] for p in positions.values())
    max_depth = max(p[1] for p in positions.values())
    x_range = max(1, max_x_pos - min_x)
    d_range = max(1, max_depth - min_depth)

    for uid in positions:
        ox, od = positions[uid]
        sx = int(2 + (ox - min_x) / x_range * (avail_w - 2))
        sy = int(1 + (od - min_depth) / d_range * (avail_h - 1))
        positions[uid] = (sx, sy)

    # Draw edges
    for uid, info in phylo.items():
        if uid not in positions:
            continue
        par = info["parent"]
        if par in positions:
            px, py = positions[par]
            cx, cy = positions[uid]
            # Simple vertical + horizontal connector
            mid_y = (py + cy) // 2
            for y in range(min(py, cy) + 1, max(py, cy)):
                try:
                    self.stdscr.addstr(y, px, "\u2502", curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass
            if cx != px:
                y_line = min(cy, mid_y)
                x_start = min(px, cx)
                x_end = max(px, cx)
                for x in range(x_start, x_end + 1):
                    try:
                        self.stdscr.addstr(y_line, x, "\u2500", curses.color_pair(7) | curses.A_DIM)
                    except curses.error:
                        pass

    # Draw nodes
    for uid, (sx, sy) in positions.items():
        info = phylo[uid]
        if info["alive"]:
            ch = "\u25cf"  # filled circle
            attr = curses.color_pair(3) | curses.A_BOLD
        else:
            ch = "\u25cb"  # hollow circle
            attr = curses.color_pair(7) | curses.A_DIM
        try:
            self.stdscr.addstr(sy, sx, ch, attr)
        except curses.error:
            pass

    # Legend
    try:
        leg = f" Lineages: {len(roots)} roots, {len(alive_uids)} alive, {len(phylo)} total"
        self.stdscr.addstr(0, 2, leg[:max_x - 4], curses.color_pair(6))
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Time-series graph view
# ══════════════════════════════════════════════════════════════════════

def _draw_psoup_graph(self, max_y, max_x):
    h = self.psoup_history
    spark_w = max(10, max_x - 30)

    graphs = [
        ("Molecules (H\u2082+CO\u2082+NH\u2083)", "molecules", curses.color_pair(4)),
        ("Amino Acids",                "amino",     curses.color_pair(3)),
        ("Nucleotides",                "nucleo",    curses.color_pair(6)),
        ("RNA Replicators",            "rna_count", curses.color_pair(1) | curses.A_BOLD),
        ("Replicator Diversity",       "rna_diversity", curses.color_pair(6) | curses.A_BOLD),
        ("Protocells",                 "protocells", curses.color_pair(5) | curses.A_BOLD),
        ("Avg RNA Fitness",            "avg_fitness", curses.color_pair(3) | curses.A_BOLD),
        ("Avg Metabolic Efficiency",   "avg_metabolic", curses.color_pair(2)),
        ("Avg RNA Length (Complexity)", "complexity", curses.color_pair(6)),
        ("Mutations / Step",           "error_rate", curses.color_pair(1)),
    ]

    row = 1
    for label, key, attr in graphs:
        if row >= max_y - 2:
            break
        vals = h.get(key, [])
        current = vals[-1] if vals else 0
        spark = _sparkline(vals, spark_w)

        try:
            self.stdscr.addstr(row, 1, f"{label:>28s}", curses.color_pair(7))
        except curses.error:
            pass
        try:
            self.stdscr.addstr(row, 30, spark[:max_x - 40], attr)
        except curses.error:
            pass
        # Current value
        if isinstance(current, float):
            val_str = f" {current:.2f}"
        else:
            val_str = f" {current}"
        try:
            self.stdscr.addstr(row, min(max_x - 8, 30 + spark_w + 1),
                               val_str[:7], curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass
        row += 2


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Main dispatch
# ══════════════════════════════════════════════════════════════════════

def _draw_psoup(self, max_y, max_x):
    self.stdscr.erase()

    view = self.psoup_view
    h = self.psoup_history
    state = "RUN" if self.psoup_running else "PAUSED"

    rna_n = len(self.psoup_rna)
    proto_n = len(self.psoup_protocells)
    amino_n = h["amino"][-1] if h["amino"] else 0
    nucleo_n = h["nucleo"][-1] if h["nucleo"] else 0

    # Title bar
    title = (f" {self.psoup_preset_name}  gen={self.psoup_generation}"
             f"  RNA={rna_n} Proto={proto_n}"
             f"  amino={amino_n} nucl={nucleo_n}"
             f"  [{state}]  view={view}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if view == VIEW_SOUP:
        _draw_psoup_soup(self, max_y, max_x)
    elif view == VIEW_TREE:
        _draw_psoup_tree(self, max_y, max_x)
    else:
        _draw_psoup_graph(self, max_y, max_x)

    # Help bar
    if max_y - 1 > 0:
        hint = " [Space]=play [n]=step [v]=view [l]=lightning [h]=heat [c]=cool [u]=UV [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    App.PRIMSOUP_PRESETS = PSOUP_PRESETS
    App._enter_psoup_mode = _enter_psoup_mode
    App._exit_psoup_mode = _exit_psoup_mode
    App._psoup_init = _psoup_init
    App._psoup_step = _psoup_step
    App._handle_psoup_menu_key = _handle_psoup_menu_key
    App._handle_psoup_key = _handle_psoup_key
    App._draw_psoup_menu = _draw_psoup_menu
    App._draw_psoup = _draw_psoup
