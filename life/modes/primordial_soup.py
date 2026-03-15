"""Mode: primordial_soup — Primordial Soup / Origin of Life abiogenesis simulation.

Simple molecules form near hydrothermal vents, spontaneously polymerize into
chains (RNA-world style), lipid membranes self-assemble into vesicles, primitive
metabolism emerges from autocatalytic cycles, and competing protocells
undergo Darwinian selection — the transition from chemistry to biology.

Features energy gradients (hydrothermal vents), monomer→polymer assembly,
lipid bilayer self-organization, RNA-world replication with mutation,
protocell division, resource competition, and emergent life.

Presets: Hydrothermal Vent Field, Warm Little Pond, Volcanic Tidepool,
Deep Ocean Seep, Frozen Comet Lake, Chemical Garden.
"""
import curses
import math
import random
import time

# ── Cell types ───────────────────────────────────────────────────────
CELL_WATER = 0
CELL_ROCK = 1             # mineral substrate
CELL_VENT = 2             # hydrothermal vent (energy source)
CELL_MINERAL = 3          # dissolved minerals / nutrients
CELL_MONOMER = 4          # simple organic molecule (amino acid, nucleotide)
CELL_POLYMER = 5          # short polymer chain (proto-RNA / peptide)
CELL_REPLICATOR = 6       # self-replicating polymer (ribozyme-like)
CELL_LIPID = 7            # amphiphilic lipid molecule
CELL_VESICLE = 8          # lipid vesicle / membrane bubble
CELL_PROTOCELL = 9        # protocell (membrane + replicator + metabolism)
CELL_DEAD = 10            # dead organic matter / detritus
CELL_ICE = 11             # ice (concentrates molecules)

CELL_CHARS = {
    CELL_WATER: "  ", CELL_ROCK: "##", CELL_VENT: "/\\",
    CELL_MINERAL: "::", CELL_MONOMER: "..", CELL_POLYMER: "~~",
    CELL_REPLICATOR: "rr", CELL_LIPID: "oo", CELL_VESICLE: "()",
    CELL_PROTOCELL: "@@", CELL_DEAD: ",,", CELL_ICE: "**",
}

# ── Presets ───────────────────────────────────────────────────────────
PRIMSOUP_PRESETS = [
    ("Hydrothermal Vent Field",
     "Black smoker chimneys pour energy and minerals into the deep — classic abiogenesis",
     {"vents": 6, "vent_energy": 1.0, "mineral_density": 0.12,
      "monomer_density": 0.04, "lipid_density": 0.02, "temperature": 90.0,
      "uv_level": 0.0, "rock_density": 0.10, "ice_density": 0.0,
      "polymerize_rate": 0.04, "replicate_rate": 0.03,
      "lipid_assemble_rate": 0.03, "mutation_rate": 0.05}),

    ("Warm Little Pond",
     "Darwin's warm little pond — shallow, UV-irradiated, wet-dry cycling",
     {"vents": 2, "vent_energy": 0.4, "mineral_density": 0.10,
      "monomer_density": 0.06, "lipid_density": 0.03, "temperature": 45.0,
      "uv_level": 0.7, "rock_density": 0.08, "ice_density": 0.0,
      "polymerize_rate": 0.05, "replicate_rate": 0.04,
      "lipid_assemble_rate": 0.04, "mutation_rate": 0.06}),

    ("Volcanic Tidepool",
     "Geothermally heated tidepool with mineral-rich volcanic rock and UV exposure",
     {"vents": 4, "vent_energy": 0.8, "mineral_density": 0.15,
      "monomer_density": 0.05, "lipid_density": 0.02, "temperature": 65.0,
      "uv_level": 0.5, "rock_density": 0.15, "ice_density": 0.0,
      "polymerize_rate": 0.045, "replicate_rate": 0.035,
      "lipid_assemble_rate": 0.035, "mutation_rate": 0.07}),

    ("Deep Ocean Seep",
     "Cold methane seep on the abyssal plain — slow, steady chemistry",
     {"vents": 3, "vent_energy": 0.3, "mineral_density": 0.08,
      "monomer_density": 0.03, "lipid_density": 0.01, "temperature": 4.0,
      "uv_level": 0.0, "rock_density": 0.06, "ice_density": 0.0,
      "polymerize_rate": 0.02, "replicate_rate": 0.015,
      "lipid_assemble_rate": 0.02, "mutation_rate": 0.03}),

    ("Frozen Comet Lake",
     "Ice-covered lake with freeze-thaw cycles concentrating organics in eutectic veins",
     {"vents": 1, "vent_energy": 0.2, "mineral_density": 0.06,
      "monomer_density": 0.07, "lipid_density": 0.03, "temperature": -5.0,
      "uv_level": 0.1, "rock_density": 0.05, "ice_density": 0.25,
      "polymerize_rate": 0.06, "replicate_rate": 0.04,
      "lipid_assemble_rate": 0.05, "mutation_rate": 0.04}),

    ("Chemical Garden",
     "Semipermeable mineral chimneys with strong pH gradients — proton-motive abiogenesis",
     {"vents": 8, "vent_energy": 0.6, "mineral_density": 0.20,
      "monomer_density": 0.03, "lipid_density": 0.01, "temperature": 70.0,
      "uv_level": 0.0, "rock_density": 0.18, "ice_density": 0.0,
      "polymerize_rate": 0.035, "replicate_rate": 0.025,
      "lipid_assemble_rate": 0.025, "mutation_rate": 0.04}),
]

# ── Helpers ───────────────────────────────────────────────────────────
_NBRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NBRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
           (0, 1), (1, -1), (1, 0), (1, 1)]


def _count_neighbors(grid, r, c, rows, cols, cell_types):
    """Count neighbors of given cell types in 8-neighborhood."""
    count = 0
    for dr, dc in _NBRS8:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            if grid[nr][nc] in cell_types:
                count += 1
    return count


def _adj_cells(grid, r, c, rows, cols, allowed):
    """Return list of adjacent positions with cell types in allowed set."""
    out = []
    for dr, dc in _NBRS4:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            if grid[nr][nc] in allowed:
                out.append((nr, nc))
    return out


def _energy_at(r, c, rows, cols, vents, vent_energy, temperature):
    """Energy available at position — high near vents, decays with distance."""
    base = max(0.01, (temperature + 20.0) / 120.0) * 0.1
    for vr, vc in vents:
        dist = math.sqrt((r - vr) ** 2 + (c - vc) ** 2)
        if dist < 1:
            dist = 1
        base += vent_energy / (1.0 + dist * 0.3)
    return min(1.0, base)


# ══════════════════════════════════════════════════════════════════════
#  Core mode functions
# ══════════════════════════════════════════════════════════════════════

def _enter_psoup_mode(self):
    """Enter Primordial Soup / Origin of Life mode — show preset menu."""
    self.psoup_menu = True
    self.psoup_menu_sel = 0
    self._flash("Primordial Soup / Origin of Life — select a scenario")


def _exit_psoup_mode(self):
    """Exit Primordial Soup mode."""
    self.psoup_mode = False
    self.psoup_menu = False
    self.psoup_running = False
    self.psoup_grid = []
    self.psoup_energy_grid = []
    self.psoup_protocells = []
    self._flash("Primordial Soup mode OFF")


def _psoup_init(self, preset_idx: int):
    """Initialize the Primordial Soup simulation with the given preset."""
    name, _desc, settings = self.PRIMSOUP_PRESETS[preset_idx]

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(30, max_y - 4)
    cols = max(40, (max_x - 1) // 2)

    self.psoup_rows = rows
    self.psoup_cols = cols
    self.psoup_preset_name = name
    self.psoup_preset_idx = preset_idx
    self.psoup_generation = 0
    self.psoup_steps_per_frame = 1
    self.psoup_settings = dict(settings)
    self.psoup_view = "soup"  # soup / energy / density

    # Environment state
    self.psoup_temperature = settings["temperature"]
    self.psoup_uv = settings["uv_level"]

    # Statistics
    self.psoup_stats = {
        "monomers": 0, "polymers": 0, "replicators": 0,
        "lipids": 0, "vesicles": 0, "protocells": 0,
        "peak_protocells": 0, "total_divisions": 0,
        "generation_max": 0,
    }

    # ── Place vents ──
    vent_positions = []
    for _ in range(settings["vents"]):
        vr = random.randint(int(rows * 0.5), rows - 3)
        vc = random.randint(3, cols - 4)
        vent_positions.append((vr, vc))
    self.psoup_vents = vent_positions

    # ── Build grid ──
    grid = [[CELL_WATER] * cols for _ in range(rows)]

    # Place rock substrate (bottom portion + scattered)
    for r in range(int(rows * 0.85), rows):
        for c in range(cols):
            if random.random() < 0.6:
                grid[r][c] = CELL_ROCK

    for r in range(int(rows * 0.3), int(rows * 0.85)):
        for c in range(cols):
            if random.random() < settings["rock_density"] * 0.3:
                grid[r][c] = CELL_ROCK

    # Place vents on rock
    for vr, vc in vent_positions:
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                nr, nc = vr + dr, vc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    grid[nr][nc] = CELL_VENT

    # Place ice (for frozen scenarios)
    if settings["ice_density"] > 0:
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == CELL_WATER and random.random() < settings["ice_density"]:
                    # Ice more common at surface
                    depth_frac = r / max(1, rows - 1)
                    if random.random() > depth_frac * 0.8:
                        grid[r][c] = CELL_ICE

    # Scatter minerals near vents
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != CELL_WATER:
                continue
            energy = _energy_at(r, c, rows, cols, vent_positions,
                                settings["vent_energy"], settings["temperature"])
            if random.random() < settings["mineral_density"] * energy:
                grid[r][c] = CELL_MINERAL

    # Scatter initial monomers
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != CELL_WATER:
                continue
            if random.random() < settings["monomer_density"]:
                grid[r][c] = CELL_MONOMER
            elif random.random() < settings["lipid_density"]:
                grid[r][c] = CELL_LIPID

    self.psoup_grid = grid

    # Energy grid (precomputed per-cell energy availability)
    self.psoup_energy_grid = [
        [_energy_at(r, c, rows, cols, vent_positions,
                    settings["vent_energy"], settings["temperature"])
         for c in range(cols)]
        for r in range(rows)
    ]

    # Protocell list: each is a dict with genome, fitness, age, position, energy
    self.psoup_protocells = []

    self.psoup_mode = True
    self.psoup_menu = False
    self.psoup_running = False
    self._flash(f"Primordial Soup: {name} — Space to start")


def _psoup_step(self):
    """Advance the primordial soup simulation by one step."""
    grid = self.psoup_grid
    rows, cols = self.psoup_rows, self.psoup_cols
    settings = self.psoup_settings
    energy_grid = self.psoup_energy_grid
    stats = self.psoup_stats
    vents = self.psoup_vents
    protocells = self.psoup_protocells
    gen = self.psoup_generation

    temperature = self.psoup_temperature
    uv = self.psoup_uv

    polymerize_rate = settings["polymerize_rate"]
    replicate_rate = settings["replicate_rate"]
    lipid_assemble_rate = settings["lipid_assemble_rate"]
    mutation_rate = settings["mutation_rate"]

    # Temperature-dependent rate modifier
    if temperature < 0:
        temp_mod = 0.3  # ice slows but concentrates
    elif temperature < 30:
        temp_mod = 0.5 + temperature / 60.0
    elif temperature < 80:
        temp_mod = 1.0
    else:
        temp_mod = max(0.3, 1.0 - (temperature - 80) / 100.0)

    # ── 0. Vent activity: produce minerals and energy ──
    for vr, vc in vents:
        for dr, dc in _NBRS8:
            nr, nc = vr + dr, vc + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] == CELL_WATER and random.random() < 0.15:
                    grid[nr][nc] = CELL_MINERAL
                # Occasional monomer synthesis at vents
                if grid[nr][nc] == CELL_MINERAL and random.random() < 0.05 * temp_mod:
                    grid[nr][nc] = CELL_MONOMER

    # ── 1. Chemical reactions across the grid ──
    new_grid = [row[:] for row in grid]

    for r in range(rows):
        for c in range(cols):
            ct = grid[r][c]
            energy = energy_grid[r][c]

            if ct == CELL_MINERAL:
                # Minerals can be converted to monomers near energy sources
                if energy > 0.3 and random.random() < 0.02 * temp_mod * energy:
                    new_grid[r][c] = CELL_MONOMER

            elif ct == CELL_MONOMER:
                # UV can create monomers from water (photochemistry) but also destroy
                if uv > 0 and random.random() < uv * 0.01:
                    new_grid[r][c] = CELL_WATER
                    continue

                # Polymerization: monomers near other monomers + energy → polymer
                monomer_nbrs = _count_neighbors(grid, r, c, rows, cols, {CELL_MONOMER})
                mineral_nbrs = _count_neighbors(grid, r, c, rows, cols, {CELL_MINERAL})

                if monomer_nbrs >= 2 and energy > 0.2:
                    if random.random() < polymerize_rate * temp_mod * energy:
                        new_grid[r][c] = CELL_POLYMER
                        # Consume one adjacent monomer
                        adj = _adj_cells(grid, r, c, rows, cols, {CELL_MONOMER})
                        if adj:
                            ar, ac = random.choice(adj)
                            new_grid[ar][ac] = CELL_WATER

                # Monomers can also become lipids (with mineral catalyst)
                elif mineral_nbrs >= 1 and random.random() < 0.008 * temp_mod:
                    new_grid[r][c] = CELL_LIPID

                # Ice concentration effect — monomers near ice polymerize faster
                if ct == CELL_MONOMER and new_grid[r][c] == CELL_MONOMER:
                    ice_nbrs = _count_neighbors(grid, r, c, rows, cols, {CELL_ICE})
                    if ice_nbrs >= 2 and monomer_nbrs >= 1:
                        if random.random() < polymerize_rate * 1.5:
                            new_grid[r][c] = CELL_POLYMER

            elif ct == CELL_POLYMER:
                # Polymers can become replicators (autocatalysis)
                polymer_nbrs = _count_neighbors(grid, r, c, rows, cols, {CELL_POLYMER, CELL_REPLICATOR})
                if polymer_nbrs >= 1 and energy > 0.3:
                    if random.random() < replicate_rate * 0.3 * temp_mod * energy:
                        new_grid[r][c] = CELL_REPLICATOR

                # Polymers degrade slowly
                if random.random() < 0.005:
                    new_grid[r][c] = CELL_MONOMER

                # UV damages polymers
                if uv > 0 and random.random() < uv * 0.015:
                    new_grid[r][c] = CELL_MONOMER

            elif ct == CELL_REPLICATOR:
                # Self-replication: copy to adjacent water if monomers available
                if energy > 0.2:
                    monomer_nbrs = _count_neighbors(grid, r, c, rows, cols, {CELL_MONOMER})
                    if monomer_nbrs >= 2 and random.random() < replicate_rate * temp_mod:
                        adj_water = _adj_cells(grid, r, c, rows, cols, {CELL_WATER})
                        adj_mono = _adj_cells(grid, r, c, rows, cols, {CELL_MONOMER})
                        if adj_water and adj_mono:
                            wr, wc = random.choice(adj_water)
                            mr, mc = random.choice(adj_mono)
                            new_grid[wr][wc] = CELL_REPLICATOR
                            new_grid[mr][mc] = CELL_WATER

                # Replicators degrade faster without energy
                if energy < 0.15 and random.random() < 0.02:
                    new_grid[r][c] = CELL_POLYMER

                # UV damages replicators
                if uv > 0 and random.random() < uv * 0.02:
                    if random.random() < 0.5:
                        new_grid[r][c] = CELL_POLYMER
                    else:
                        new_grid[r][c] = CELL_MONOMER

            elif ct == CELL_LIPID:
                # Lipids self-assemble into vesicles near other lipids
                lipid_nbrs = _count_neighbors(grid, r, c, rows, cols, {CELL_LIPID})
                if lipid_nbrs >= 3:
                    if random.random() < lipid_assemble_rate * temp_mod:
                        new_grid[r][c] = CELL_VESICLE
                        # Consume some adjacent lipids
                        adj = _adj_cells(grid, r, c, rows, cols, {CELL_LIPID})
                        consumed = 0
                        for ar, ac in adj:
                            if consumed >= 2:
                                break
                            new_grid[ar][ac] = CELL_WATER
                            consumed += 1

                # Lipids slowly degrade
                if random.random() < 0.003:
                    new_grid[r][c] = CELL_DEAD

            elif ct == CELL_VESICLE:
                # Vesicles that capture replicators become protocells!
                repl_nbrs = _count_neighbors(grid, r, c, rows, cols, {CELL_REPLICATOR})
                if repl_nbrs >= 1 and random.random() < 0.08 * temp_mod:
                    new_grid[r][c] = CELL_PROTOCELL
                    # Consume the replicator
                    adj = _adj_cells(grid, r, c, rows, cols, {CELL_REPLICATOR})
                    if adj:
                        ar, ac = random.choice(adj)
                        new_grid[ar][ac] = CELL_WATER
                    # Create protocell entity
                    protocells.append({
                        "r": r, "c": c,
                        "energy": 50 + int(energy * 50),
                        "fitness": random.uniform(0.5, 1.0),
                        "age": 0,
                        "generation": 0,
                        "genome_len": random.randint(3, 8),
                        "mutations": 0,
                    })

                # Vesicles slowly degrade
                if random.random() < 0.008:
                    new_grid[r][c] = CELL_LIPID

                # Vesicles drift (random walk)
                if random.random() < 0.1:
                    adj = _adj_cells(grid, r, c, rows, cols, {CELL_WATER})
                    if adj:
                        nr2, nc2 = random.choice(adj)
                        new_grid[r][c] = CELL_WATER
                        new_grid[nr2][nc2] = CELL_VESICLE

            elif ct == CELL_DEAD:
                # Dead matter slowly recycles back to minerals/monomers
                if random.random() < 0.02:
                    if random.random() < 0.5:
                        new_grid[r][c] = CELL_MINERAL
                    else:
                        new_grid[r][c] = CELL_MONOMER

            elif ct == CELL_ICE:
                # Ice melts at high temperature
                if temperature > 5 and random.random() < 0.01 * (temperature / 50.0):
                    new_grid[r][c] = CELL_WATER
                # Freeze-thaw cycling creates concentration
                if random.random() < 0.005:
                    adj = _adj_cells(grid, r, c, rows, cols, {CELL_WATER})
                    if adj:
                        nr2, nc2 = random.choice(adj)
                        new_grid[nr2][nc2] = CELL_ICE

    # ── 2. Protocell dynamics ──
    alive_protocells = []
    for pc in protocells:
        pr, pcc = pc["r"], pc["c"]
        if not (0 <= pr < rows and 0 <= pcc < cols):
            continue
        if new_grid[pr][pcc] != CELL_PROTOCELL:
            continue

        energy = energy_grid[pr][pcc]
        pc["age"] += 1

        # Metabolism: consume nearby monomers/minerals for energy
        food = _adj_cells(new_grid, pr, pcc, rows, cols,
                          {CELL_MONOMER, CELL_MINERAL, CELL_DEAD})
        if food:
            fr, fc = random.choice(food)
            pc["energy"] += 15
            new_grid[fr][fc] = CELL_WATER

        # Energy cost of living
        pc["energy"] -= 2
        # Fitness affects efficiency
        pc["energy"] += int(pc["fitness"] * energy * 5)

        # Death from starvation
        if pc["energy"] <= 0:
            new_grid[pr][pcc] = CELL_DEAD
            continue

        # Division: protocell splits when energy is high enough
        if pc["energy"] > 120 and pc["age"] > 10:
            adj_water = _adj_cells(new_grid, pr, pcc, rows, cols, {CELL_WATER})
            if adj_water:
                nr2, nc2 = random.choice(adj_water)
                new_grid[nr2][nc2] = CELL_PROTOCELL
                # Daughter cell
                daughter_fitness = pc["fitness"]
                daughter_genome = pc["genome_len"]
                daughter_mutations = pc["mutations"]
                # Mutation during replication
                if random.random() < mutation_rate:
                    daughter_fitness += random.uniform(-0.15, 0.2)
                    daughter_fitness = max(0.1, min(2.0, daughter_fitness))
                    daughter_genome += random.choice([-1, 0, 1])
                    daughter_genome = max(1, min(20, daughter_genome))
                    daughter_mutations += 1

                half_energy = pc["energy"] // 2
                pc["energy"] = half_energy
                alive_protocells.append({
                    "r": nr2, "c": nc2,
                    "energy": half_energy,
                    "fitness": daughter_fitness,
                    "age": 0,
                    "generation": pc["generation"] + 1,
                    "genome_len": daughter_genome,
                    "mutations": daughter_mutations,
                })
                stats["total_divisions"] += 1
                stats["generation_max"] = max(stats["generation_max"],
                                               pc["generation"] + 1)

        # Movement: drift toward energy
        if random.random() < 0.15:
            best_adj = None
            best_energy = -1
            for dr, dc in _NBRS4:
                nr2, nc2 = pr + dr, pcc + dc
                if 0 <= nr2 < rows and 0 <= nc2 < cols:
                    if new_grid[nr2][nc2] == CELL_WATER:
                        e = energy_grid[nr2][nc2]
                        if e > best_energy:
                            best_energy = e
                            best_adj = (nr2, nc2)
            if best_adj and best_energy > energy * 0.8:
                nr2, nc2 = best_adj
                new_grid[pr][pcc] = CELL_WATER
                new_grid[nr2][nc2] = CELL_PROTOCELL
                pc["r"], pc["c"] = nr2, nc2

        alive_protocells.append(pc)

    self.psoup_protocells = alive_protocells
    self.psoup_grid = new_grid

    # ── 3. UV photochemistry: create some monomers from water near surface ──
    if uv > 0:
        for c in range(cols):
            for r in range(min(5, rows)):
                if new_grid[r][c] == CELL_WATER and random.random() < uv * 0.008:
                    new_grid[r][c] = CELL_MONOMER

    # ── 4. Update statistics ──
    mono_n = poly_n = repl_n = lip_n = ves_n = proto_n = 0
    for r in range(rows):
        for c in range(cols):
            ct = new_grid[r][c]
            if ct == CELL_MONOMER:
                mono_n += 1
            elif ct == CELL_POLYMER:
                poly_n += 1
            elif ct == CELL_REPLICATOR:
                repl_n += 1
            elif ct == CELL_LIPID:
                lip_n += 1
            elif ct == CELL_VESICLE:
                ves_n += 1
            elif ct == CELL_PROTOCELL:
                proto_n += 1

    stats["monomers"] = mono_n
    stats["polymers"] = poly_n
    stats["replicators"] = repl_n
    stats["lipids"] = lip_n
    stats["vesicles"] = ves_n
    stats["protocells"] = proto_n
    stats["peak_protocells"] = max(stats["peak_protocells"], proto_n)

    self.psoup_generation += 1


# ══════════════════════════════════════════════════════════════════════
#  Input handling
# ══════════════════════════════════════════════════════════════════════

def _handle_psoup_menu_key(self, key: int) -> bool:
    """Handle input in Primordial Soup preset menu."""
    presets = self.PRIMSOUP_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.psoup_menu_sel = (self.psoup_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.psoup_menu_sel = (self.psoup_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._psoup_init(self.psoup_menu_sel)
    elif key == ord("q") or key == 27:
        self.psoup_menu = False
        self._flash("Primordial Soup cancelled")
    return True


def _handle_psoup_key(self, key: int) -> bool:
    """Handle input in active Primordial Soup simulation."""
    if key == ord("q") or key == 27:
        self._exit_psoup_mode()
        return True
    if key == ord(" "):
        self.psoup_running = not self.psoup_running
        return True
    if key == ord("n") or key == ord("."):
        self._psoup_step()
        return True
    if key == ord("r"):
        self._psoup_init(self.psoup_preset_idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.psoup_mode = False
        self.psoup_running = False
        self.psoup_menu = True
        self.psoup_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20]
        idx = choices.index(self.psoup_steps_per_frame) if self.psoup_steps_per_frame in choices else 0
        self.psoup_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.psoup_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20]
        idx = choices.index(self.psoup_steps_per_frame) if self.psoup_steps_per_frame in choices else 0
        self.psoup_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.psoup_steps_per_frame} steps/frame")
        return True
    if key == ord("v"):
        views = ["soup", "energy", "density"]
        idx = views.index(self.psoup_view) if self.psoup_view in views else 0
        self.psoup_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.psoup_view}")
        return True
    # Heat burst
    if key == ord("h"):
        self.psoup_temperature += 15.0
        self._flash(f"Heat burst! Temp: {self.psoup_temperature:.0f}C")
        return True
    # Cool down
    if key == ord("c"):
        self.psoup_temperature -= 15.0
        self._flash(f"Cooling! Temp: {self.psoup_temperature:.0f}C")
        return True
    # Lightning strike — spawn monomers
    if key == ord("l"):
        rows, cols = self.psoup_rows, self.psoup_cols
        sr, sc = random.randint(0, rows // 3), random.randint(0, cols - 1)
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = sr + dr, sc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if self.psoup_grid[nr][nc] == CELL_WATER and random.random() < 0.5:
                        self.psoup_grid[nr][nc] = CELL_MONOMER
        self._flash("Lightning! Monomers created!")
        return True
    # Mineral injection
    if key == ord("M"):
        rows, cols = self.psoup_rows, self.psoup_cols
        for _ in range(30):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            if self.psoup_grid[r][c] == CELL_WATER:
                self.psoup_grid[r][c] = CELL_MINERAL
        self._flash("Mineral injection!")
        return True
    # UV toggle
    if key == ord("u"):
        if self.psoup_uv > 0:
            self.psoup_uv = 0.0
        else:
            self.psoup_uv = 0.7
        self._flash(f"UV: {'ON' if self.psoup_uv > 0 else 'OFF'}")
        return True
    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing
# ══════════════════════════════════════════════════════════════════════

def _draw_psoup_menu(self, max_y: int, max_x: int):
    """Draw the Primordial Soup preset selection menu."""
    self.stdscr.erase()
    title = "── Primordial Soup / Origin of Life ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _settings) in enumerate(self.PRIMSOUP_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        marker = ">" if i == self.psoup_menu_sel else " "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.psoup_menu_sel
                else curses.color_pair(7))
        line = f" {marker} {name:30s}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], attr)
        except curses.error:
            pass
        desc_attr = (curses.color_pair(6) if i == self.psoup_menu_sel
                     else curses.color_pair(7) | curses.A_DIM)
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], desc_attr)
        except curses.error:
            pass

    # Legend
    legend_y = 3 + len(self.PRIMSOUP_PRESETS) * 2 + 1
    if legend_y < max_y - 5:
        legend_lines = [
            "Cells:  /\\ vent  :: mineral  .. monomer  ~~ polymer  rr replicator",
            "        oo lipid  () vesicle  @@ protocell  ,, dead  ** ice  ## rock",
            "",
            "Chemistry → Biology:  mineral → monomer → polymer → replicator",
            "                      lipid → vesicle + replicator → PROTOCELL → division!",
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


def _draw_psoup(self, max_y: int, max_x: int):
    """Draw the active Primordial Soup simulation."""
    self.stdscr.erase()
    grid = self.psoup_grid
    rows, cols = self.psoup_rows, self.psoup_cols
    state = "RUN" if self.psoup_running else "PAUSED"
    view = self.psoup_view
    stats = self.psoup_stats

    # Title bar
    title = (f" Soup: {self.psoup_preset_name}  |  gen {self.psoup_generation}"
             f"  |  mono={stats['monomers']} poly={stats['polymers']}"
             f" repl={stats['replicators']} proto={stats['protocells']}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Color mapping
    cell_colors = {
        CELL_ROCK: curses.color_pair(7) | curses.A_DIM,
        CELL_VENT: curses.color_pair(1) | curses.A_BOLD,        # red/bold — hot vent
        CELL_MINERAL: curses.color_pair(2) | curses.A_DIM,      # dim yellow
        CELL_MONOMER: curses.color_pair(6) | curses.A_DIM,      # dim cyan
        CELL_POLYMER: curses.color_pair(6) | curses.A_BOLD,     # bright cyan
        CELL_REPLICATOR: curses.color_pair(1) | curses.A_BOLD,  # bright green (pair 1)
        CELL_LIPID: curses.color_pair(2),                        # yellow
        CELL_VESICLE: curses.color_pair(3) | curses.A_BOLD,     # bright yellow/orange
        CELL_PROTOCELL: curses.color_pair(5) | curses.A_BOLD,   # bright magenta — life!
        CELL_DEAD: curses.color_pair(7) | curses.A_DIM,         # dim gray
        CELL_ICE: curses.color_pair(7) | curses.A_BOLD,         # bright white
    }

    energy_grid = self.psoup_energy_grid

    for r in range(view_rows):
        sy = 1 + r
        for c in range(view_cols):
            sx = c * 2

            if view == "soup":
                ct = grid[r][c]
                if ct == CELL_WATER:
                    # Depth-based water tint
                    depth_frac = r / max(1, rows - 1)
                    if depth_frac > 0.7:
                        ch, attr = "~~", curses.color_pair(4) | curses.A_DIM
                    elif depth_frac > 0.3:
                        ch, attr = "  ", curses.color_pair(4)
                    else:
                        continue
                else:
                    ch = CELL_CHARS.get(ct, "??")
                    attr = cell_colors.get(ct, curses.color_pair(7))
                    # Protocells glow/pulse
                    if ct == CELL_PROTOCELL:
                        phase = (self.psoup_generation + r + c) % 4
                        if phase == 0:
                            attr = curses.color_pair(5) | curses.A_BOLD
                        elif phase == 1:
                            attr = curses.color_pair(3) | curses.A_BOLD
                        else:
                            attr = curses.color_pair(5)

            elif view == "energy":
                e = energy_grid[r][c] if r < len(energy_grid) and c < len(energy_grid[0]) else 0
                if e > 0.7:
                    ch, attr = "##", curses.color_pair(1) | curses.A_BOLD
                elif e > 0.4:
                    ch, attr = "%%", curses.color_pair(2) | curses.A_BOLD
                elif e > 0.2:
                    ch, attr = "..", curses.color_pair(2)
                elif e > 0.05:
                    ch, attr = "..", curses.color_pair(4) | curses.A_DIM
                else:
                    continue

            else:  # density view — show molecular complexity
                ct = grid[r][c]
                if ct == CELL_PROTOCELL:
                    ch, attr = "@@", curses.color_pair(5) | curses.A_BOLD
                elif ct == CELL_REPLICATOR:
                    ch, attr = "**", curses.color_pair(1) | curses.A_BOLD
                elif ct == CELL_VESICLE:
                    ch, attr = "()", curses.color_pair(3) | curses.A_BOLD
                elif ct == CELL_POLYMER:
                    ch, attr = "~~", curses.color_pair(6)
                elif ct == CELL_LIPID:
                    ch, attr = "oo", curses.color_pair(2)
                elif ct in (CELL_MONOMER, CELL_MINERAL):
                    ch, attr = "..", curses.color_pair(7) | curses.A_DIM
                else:
                    continue

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Environment status line
    env_y = max_y - 2
    if env_y > 1:
        avg_fitness = 0.0
        if self.psoup_protocells:
            avg_fitness = sum(p["fitness"] for p in self.psoup_protocells) / len(self.psoup_protocells)
        env_line = (f" Temp={self.psoup_temperature:.0f}C"
                    f"  UV={'ON' if self.psoup_uv > 0 else 'off'}"
                    f"  Vents={len(self.psoup_vents)}"
                    f"  Vesicles={stats['vesicles']}"
                    f"  Peak proto={stats['peak_protocells']}"
                    f"  Divisions={stats['total_divisions']}"
                    f"  MaxGen={stats['generation_max']}"
                    f"  Fitness={avg_fitness:.2f}")
        try:
            self.stdscr.addstr(env_y, 0, env_line[:max_x - 1], curses.color_pair(7))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=view [h]=heat [c]=cool [l]=lightning [M]=minerals [u]=UV [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register primordial soup mode methods on the App class."""
    App._enter_psoup_mode = _enter_psoup_mode
    App._exit_psoup_mode = _exit_psoup_mode
    App._psoup_init = _psoup_init
    App._psoup_step = _psoup_step
    App._handle_psoup_menu_key = _handle_psoup_menu_key
    App._handle_psoup_key = _handle_psoup_key
    App._draw_psoup_menu = _draw_psoup_menu
    App._draw_psoup = _draw_psoup
    App.PRIMSOUP_PRESETS = PRIMSOUP_PRESETS
