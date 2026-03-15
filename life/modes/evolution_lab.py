"""Mode: evolution_lab — Interactive Rule Evolution Lab.

A genetic algorithm that breeds cellular automata rules to discover novel
emergent behaviors.  A population of CA rulesets runs in parallel in a tiled
view, with fitness scored automatically by analytics metrics (entropy,
periodicity, symmetry, population stability).  Each generation the top
performers reproduce with crossover and mutation; users can manually
"favorite" organisms to protect them from culling.

Connects three existing systems: analytics metrics, rule parsing/genomes,
and tiled multi-sim views.
"""
import curses
import json
import math
import os
import random
import time

from life.analytics import (
    PeriodicityDetector,
    classify_stability,
    rate_of_change,
    shannon_entropy,
    symmetry_score,
)
from life.constants import SAVE_DIR, SPEEDS, SPEED_LABELS
from life.grid import Grid
from life.rules import rule_string, parse_rule_string

# ── Constants ────────────────────────────────────────────────────────

_DENSITY = ["  ", "░░", "▒▒", "▓▓", "██"]

_SAVED_FILE = os.path.join(SAVE_DIR, "evolution_lab.json")

# Fitness presets — each maps metric names to weights
_FITNESS_PRESETS = {
    "balanced":    {"entropy": 1.0, "symmetry": 1.0, "stability": 1.0, "longevity": 1.0, "diversity": 1.0},
    "beauty":      {"entropy": 0.5, "symmetry": 3.0, "stability": 1.0, "longevity": 0.5, "diversity": 1.0},
    "chaos":       {"entropy": 3.0, "symmetry": 0.2, "stability": 0.3, "longevity": 1.0, "diversity": 2.0},
    "complexity":  {"entropy": 2.0, "symmetry": 1.0, "stability": 0.5, "longevity": 1.5, "diversity": 2.0},
    "stability":   {"entropy": 0.5, "symmetry": 1.0, "stability": 3.0, "longevity": 2.0, "diversity": 0.5},
}

_NEIGHBORHOODS = ["moore", "von_neumann"]
_NH_LABELS = {"moore": "M8", "von_neumann": "VN4"}

_HEX_EVEN = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]
_HEX_ODD = [(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]

# ── Genome ───────────────────────────────────────────────────────────


def _random_genome():
    """Generate a random CA genome."""
    birth = {d for d in range(9) if random.random() < 0.3}
    survival = {d for d in range(9) if random.random() < 0.3}
    if not birth:
        birth.add(random.randint(1, 5))
    if not survival:
        survival.add(random.randint(2, 4))
    neighborhood = random.choice(["moore", "moore", "moore", "von_neumann"])
    num_states = random.choice([2, 2, 2, 3, 4])
    return {
        "birth": birth,
        "survival": survival,
        "neighborhood": neighborhood,
        "num_states": num_states,
    }


def _crossover(g1, g2):
    """Uniform crossover between two genomes."""
    child_birth = set()
    child_survival = set()
    for d in range(9):
        src_b = g1 if random.random() < 0.5 else g2
        if d in src_b["birth"]:
            child_birth.add(d)
        src_s = g1 if random.random() < 0.5 else g2
        if d in src_s["survival"]:
            child_survival.add(d)
    if not child_birth:
        child_birth.add(random.randint(1, 5))
    neighborhood = g1["neighborhood"] if random.random() < 0.5 else g2["neighborhood"]
    num_states = g1["num_states"] if random.random() < 0.5 else g2["num_states"]
    return {
        "birth": child_birth,
        "survival": child_survival,
        "neighborhood": neighborhood,
        "num_states": num_states,
    }


def _mutate(genome, rate=0.15):
    """Mutate a genome and return a new copy."""
    g = {
        "birth": set(genome["birth"]),
        "survival": set(genome["survival"]),
        "neighborhood": genome["neighborhood"],
        "num_states": genome["num_states"],
    }
    for d in range(9):
        if random.random() < rate:
            g["birth"].symmetric_difference_update({d})
        if random.random() < rate:
            g["survival"].symmetric_difference_update({d})
    if not g["birth"]:
        g["birth"].add(random.randint(1, 5))
    if random.random() < rate * 0.5:
        g["neighborhood"] = random.choice(_NEIGHBORHOODS)
    if random.random() < rate * 0.5:
        g["num_states"] = random.choice([2, 3, 4, 5])
    return g


def _genome_label(genome):
    """Short human-readable label."""
    rs = rule_string(genome["birth"], genome["survival"])
    nh = _NH_LABELS.get(genome["neighborhood"], "M8")
    ns = genome["num_states"]
    if ns == 2 and nh == "M8":
        return rs
    return f"{rs} {nh} s{ns}"


# ── Mini-simulation ──────────────────────────────────────────────────


def _count_neighbors(cells, r, c, rows, cols, neighborhood):
    """Count live neighbors for a cell."""
    count = 0
    if neighborhood == "von_neumann":
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if cells[(r + dr) % rows][(c + dc) % cols] > 0:
                count += 1
    else:  # moore
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                if cells[(r + dr) % rows][(c + dc) % cols] > 0:
                    count += 1
    return count


def _create_sim(genome, rows, cols):
    """Create a mini Grid for a genome."""
    g = Grid(rows, cols)
    g.birth = set(genome["birth"])
    g.survival = set(genome["survival"])
    g._elab_nh = genome["neighborhood"]
    g._elab_ns = genome["num_states"]
    for r in range(rows):
        for c in range(cols):
            if random.random() < 0.2:
                g.set_alive(r, c)
    return g


def _step_sim(grid):
    """Step a mini simulation with custom neighborhoods and multi-state."""
    rows, cols = grid.rows, grid.cols
    nh = getattr(grid, '_elab_nh', 'moore')
    ns = getattr(grid, '_elab_ns', 2)
    cells = grid.cells

    new = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            n = _count_neighbors(cells, r, c, rows, cols, nh)
            alive = cells[r][c] > 0
            if alive and n in grid.survival:
                new[r][c] = min(cells[r][c] + 1, ns * 50)
            elif not alive and n in grid.birth:
                new[r][c] = 1
            else:
                if ns > 2 and cells[r][c] > 1:
                    new[r][c] = cells[r][c] - 1
                else:
                    new[r][c] = 0
    grid.cells = new
    grid.generation += 1
    grid.population = sum(1 for row in new for cell in row if cell > 0)


# ── Fitness scoring using analytics metrics ──────────────────────────


def _compute_fitness(grid, pop_history, weights):
    """Compute fitness score for an organism using analytics metrics."""
    if not pop_history or len(pop_history) < 5:
        return {"total": 0, "entropy": 0, "symmetry": 0, "stability": 0,
                "longevity": 0, "diversity": 0}

    # Entropy (0-1 range, higher = more interesting structure)
    ent = shannon_entropy(grid)
    # Normalize: binary entropy max is 1.0, but multi-state can be higher
    ent_score = min(ent, 1.0) * 100

    # Symmetry (average of horiz/vert/rot)
    sym = symmetry_score(grid)
    sym_score = (sym["horiz"] + sym["vert"] + sym["rot180"]) / 3.0 * 100

    # Stability classification score
    period_det = PeriodicityDetector(max_history=200)
    # Feed last states — approximate by checking pop pattern
    cycle_period = None
    # Use population variance as stability proxy
    recent = pop_history[-30:]
    avg_pop = sum(recent) / len(recent) if recent else 0
    if avg_pop > 0 and len(recent) > 5:
        variance = sum((p - avg_pop) ** 2 for p in recent) / len(recent)
        cv = math.sqrt(variance) / max(avg_pop, 1)
        # Sweet spot: not too stable (boring) not too chaotic (noise)
        # Peak at cv ~ 0.1-0.3
        if cv < 0.01:
            stab_score = 30  # static — somewhat boring
        elif cv < 0.3:
            stab_score = 100  # oscillating nicely
        elif cv < 0.6:
            stab_score = 70  # somewhat chaotic
        else:
            stab_score = 40  # very chaotic
    else:
        stab_score = 0

    # Longevity: fraction of time alive
    alive_gens = sum(1 for p in pop_history if p > 0)
    longevity_score = (alive_gens / len(pop_history)) * 100

    # Diversity: unique population values (pattern richness)
    unique_pops = len(set(pop_history[-100:]))
    diversity_score = min(unique_pops * 3, 100)

    # Penalize extinction
    if pop_history[-1] == 0:
        longevity_score *= 0.3
        stab_score *= 0.1

    # Penalize full saturation (boring)
    total_cells = grid.rows * grid.cols
    if total_cells > 0 and grid.population > total_cells * 0.9:
        ent_score *= 0.3
        diversity_score *= 0.3

    # Weighted total
    total = (
        ent_score * weights.get("entropy", 1.0) +
        sym_score * weights.get("symmetry", 1.0) +
        stab_score * weights.get("stability", 1.0) +
        longevity_score * weights.get("longevity", 1.0) +
        diversity_score * weights.get("diversity", 1.0)
    )

    return {
        "total": total,
        "entropy": ent_score,
        "symmetry": sym_score,
        "stability": stab_score,
        "longevity": longevity_score,
        "diversity": diversity_score,
    }


# ── Mode functions ───────────────────────────────────────────────────


def _enter_elab_mode(self):
    """Enter Evolution Lab mode — show settings menu."""
    self.elab_mode = False
    self.elab_menu = True
    self.elab_menu_sel = 0
    self._flash("Evolution Lab — automated rule discovery via genetic algorithm")


def _exit_elab_mode(self):
    """Exit Evolution Lab mode."""
    self.elab_mode = False
    self.elab_menu = False
    self.elab_running = False
    self.elab_sims = []
    self.elab_genomes = []
    self.elab_favorites = set()
    self.elab_fitness = []
    self.elab_pop_histories = []
    self.elab_generation = 0
    self._flash("Evolution Lab OFF")


def _elab_init(self, seed_genomes=None):
    """Initialize a population of organisms."""
    max_y, max_x = self.stdscr.getmaxyx()

    # Determine tile layout to fit screen
    usable_h = max_y - 5
    usable_w = max_x - 1

    pop_size = self.elab_pop_size

    # Find best grid arrangement
    best_r, best_c = 2, 4
    for gc in range(2, 8):
        gr = math.ceil(pop_size / gc)
        if gr <= 0:
            continue
        th = usable_h // gr
        tw = usable_w // gc
        if th >= 4 and tw >= 8:
            best_r, best_c = gr, gc
            if gr * gc >= pop_size:
                break

    self.elab_grid_rows = best_r
    self.elab_grid_cols = best_c
    actual_pop = min(pop_size, best_r * best_c)

    self.elab_tile_h = max(4, usable_h // best_r - 1)
    self.elab_tile_w = max(4, (usable_w // best_c - 1) // 2)

    sim_rows = max(3, self.elab_tile_h - 2)
    sim_cols = max(3, self.elab_tile_w)

    # Generate genomes
    if seed_genomes and len(seed_genomes) >= 2:
        genomes = []
        # Keep favorites/parents unchanged
        for sg in seed_genomes:
            genomes.append(dict(sg, birth=set(sg["birth"]), survival=set(sg["survival"])))
        # Fill rest via crossover + mutation
        while len(genomes) < actual_pop:
            p1 = random.choice(seed_genomes)
            p2 = random.choice(seed_genomes)
            child = _crossover(p1, p2)
            child = _mutate(child, self.elab_mutation_rate)
            genomes.append(child)
        genomes = genomes[:actual_pop]
    else:
        genomes = [_random_genome() for _ in range(actual_pop)]

    # Create simulations
    self.elab_sims = []
    self.elab_genomes = genomes
    self.elab_pop_histories = []
    self.elab_fitness = [{} for _ in range(len(genomes))]
    for genome in genomes:
        grid = _create_sim(genome, sim_rows, sim_cols)
        self.elab_sims.append(grid)
        self.elab_pop_histories.append([grid.population])

    self.elab_favorites = set()
    self.elab_cursor = 0
    self.elab_sim_step = 0
    self.elab_phase = "simulating"
    self.elab_mode = True
    self.elab_menu = False
    self.elab_running = True  # auto-start
    self.elab_generation += 1
    self.elab_auto_breed = self.elab_auto_advance

    n_parents = len(seed_genomes) if seed_genomes else 0
    if n_parents > 0:
        self._flash(f"Gen {self.elab_generation}: bred {actual_pop} from {n_parents} parents — running...")
    else:
        self._flash(f"Gen {self.elab_generation}: {actual_pop} random organisms — evolving...")


def _elab_step(self):
    """Advance all organisms by one simulation step."""
    if self.elab_phase != "simulating":
        return
    for i, grid in enumerate(self.elab_sims):
        _step_sim(grid)
        self.elab_pop_histories[i].append(grid.population)
    self.elab_sim_step += 1

    # Auto-score when enough steps have run
    if self.elab_sim_step >= self.elab_eval_gens:
        self._elab_score_all()


def _elab_score_all(self):
    """Compute fitness for all organisms and rank them."""
    weights = _FITNESS_PRESETS.get(self.elab_fitness_preset, _FITNESS_PRESETS["balanced"])
    self.elab_phase = "scored"

    for i, grid in enumerate(self.elab_sims):
        self.elab_fitness[i] = _compute_fitness(
            grid, self.elab_pop_histories[i], weights
        )

    # Sort by fitness (best first), but keep favorites at top
    indices = list(range(len(self.elab_sims)))
    indices.sort(key=lambda i: (
        0 if i in self.elab_favorites else 1,
        -self.elab_fitness[i].get("total", 0)
    ))

    self.elab_sims = [self.elab_sims[i] for i in indices]
    self.elab_genomes = [self.elab_genomes[i] for i in indices]
    self.elab_fitness = [self.elab_fitness[i] for i in indices]
    self.elab_pop_histories = [self.elab_pop_histories[i] for i in indices]

    # Remap favorites
    old_favs = self.elab_favorites
    new_favs = set()
    for new_idx, old_idx in enumerate(indices):
        if old_idx in old_favs:
            new_favs.add(new_idx)
    self.elab_favorites = new_favs

    best = self.elab_fitness[0]
    best_label = _genome_label(self.elab_genomes[0])

    # Track best ever
    if self.elab_best_ever is None or best.get("total", 0) > self.elab_best_ever.get("total", 0):
        self.elab_best_ever = dict(best)
        self.elab_best_ever["rule"] = best_label
        self.elab_best_ever["gen"] = self.elab_generation

    # Record history
    avg_score = sum(f.get("total", 0) for f in self.elab_fitness) / max(1, len(self.elab_fitness))
    self.elab_history.append({
        "generation": self.elab_generation,
        "best_score": best.get("total", 0),
        "best_rule": best_label,
        "avg_score": avg_score,
    })

    self._flash(f"Gen {self.elab_generation} scored! Best: {best_label} ({best.get('total', 0):.0f}pts)")

    if self.elab_auto_breed:
        self._elab_breed_next()


def _elab_breed_next(self):
    """Breed next generation from top performers + favorites."""
    n = len(self.elab_sims)
    if n < 2:
        return

    # Parents = top elite + all favorites
    elite_count = max(2, min(self.elab_elite_count, n // 2))
    parent_indices = set(range(elite_count))
    parent_indices |= self.elab_favorites
    parents = [self.elab_genomes[i] for i in sorted(parent_indices)]

    if len(parents) < 2:
        parents = self.elab_genomes[:2]

    self.elab_sim_step = 0
    self._elab_init(seed_genomes=parents)
    self.elab_running = True


def _elab_toggle_favorite(self, idx):
    """Toggle favorite status on an organism."""
    if idx in self.elab_favorites:
        self.elab_favorites.discard(idx)
        self._flash(f"Unfavorited #{idx + 1} — {len(self.elab_favorites)} favorites")
    else:
        self.elab_favorites.add(idx)
        self._flash(f"Favorited #{idx + 1} '{_genome_label(self.elab_genomes[idx])}' — protected from culling")


def _elab_save_organism(self, idx):
    """Save an organism to disk."""
    genome = self.elab_genomes[idx]
    fitness = self.elab_fitness[idx] if idx < len(self.elab_fitness) else {}
    entry = {
        "rule": rule_string(genome["birth"], genome["survival"]),
        "birth": sorted(genome["birth"]),
        "survival": sorted(genome["survival"]),
        "neighborhood": genome["neighborhood"],
        "num_states": genome["num_states"],
        "label": _genome_label(genome),
        "fitness": {k: round(v, 1) for k, v in fitness.items()},
        "generation": self.elab_generation,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    saved = []
    if os.path.isfile(_SAVED_FILE):
        try:
            with open(_SAVED_FILE, "r") as f:
                saved = json.load(f)
        except (json.JSONDecodeError, OSError):
            saved = []
    saved.append(entry)
    os.makedirs(SAVE_DIR, exist_ok=True)
    with open(_SAVED_FILE, "w") as f:
        json.dump(saved, f, indent=2)
    self._flash(f"Saved: {entry['label']} ({fitness.get('total', 0):.0f}pts)")


def _elab_adopt_rule(self, idx):
    """Adopt a genome's ruleset into the main Game of Life."""
    genome = self.elab_genomes[idx]
    self.grid.birth = set(genome["birth"])
    self.grid.survival = set(genome["survival"])
    label = _genome_label(genome)
    self._exit_elab_mode()
    self._flash(f"Adopted evolved rule: {label}")


def _elab_load_saved(self):
    """Load saved organisms as seed genomes."""
    if not os.path.isfile(_SAVED_FILE):
        return None
    try:
        with open(_SAVED_FILE, "r") as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not saved:
        return None
    genomes = []
    for entry in saved[-12:]:
        genomes.append({
            "birth": set(entry["birth"]),
            "survival": set(entry["survival"]),
            "neighborhood": entry.get("neighborhood", "moore"),
            "num_states": entry.get("num_states", 2),
        })
    return genomes


# ── Key handlers ─────────────────────────────────────────────────────


def _handle_elab_menu_key(self, key):
    """Handle keys in the Evolution Lab settings menu."""
    if key == -1:
        return True
    menu_items = ["pop_size", "eval_gens", "mutation_rate", "elite_count",
                  "fitness_preset", "auto_advance", "start_random", "start_saved"]
    n = len(menu_items)

    if key in (curses.KEY_UP, ord("k")):
        self.elab_menu_sel = (self.elab_menu_sel - 1) % n
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.elab_menu_sel = (self.elab_menu_sel + 1) % n
        return True
    if key == 27 or key == ord("q"):
        self.elab_menu = False
        self._flash("Evolution Lab cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER, ord(" ")):
        item = menu_items[self.elab_menu_sel]
        if item == "pop_size":
            val = self._prompt_text(f"Population size 4-20 (current: {self.elab_pop_size})")
            if val:
                try:
                    v = int(val)
                    if 4 <= v <= 20:
                        self.elab_pop_size = v
                except ValueError:
                    self._flash("Invalid number")
        elif item == "eval_gens":
            val = self._prompt_text(f"Eval generations 50-500 (current: {self.elab_eval_gens})")
            if val:
                try:
                    v = int(val)
                    if 50 <= v <= 500:
                        self.elab_eval_gens = v
                except ValueError:
                    self._flash("Invalid number")
        elif item == "mutation_rate":
            val = self._prompt_text(f"Mutation rate 0-100% (current: {int(self.elab_mutation_rate * 100)}%)")
            if val:
                try:
                    v = int(val.replace("%", ""))
                    if 0 <= v <= 100:
                        self.elab_mutation_rate = v / 100.0
                except ValueError:
                    self._flash("Invalid number")
        elif item == "elite_count":
            val = self._prompt_text(f"Elite survivors 2-{self.elab_pop_size // 2} (current: {self.elab_elite_count})")
            if val:
                try:
                    v = int(val)
                    if 2 <= v <= self.elab_pop_size // 2:
                        self.elab_elite_count = v
                except ValueError:
                    self._flash("Invalid number")
        elif item == "fitness_preset":
            presets = list(_FITNESS_PRESETS.keys())
            idx = presets.index(self.elab_fitness_preset) if self.elab_fitness_preset in presets else 0
            self.elab_fitness_preset = presets[(idx + 1) % len(presets)]
            self._flash(f"Fitness: {self.elab_fitness_preset}")
        elif item == "auto_advance":
            self.elab_auto_advance = not self.elab_auto_advance
            self._flash(f"Auto-advance: {'ON' if self.elab_auto_advance else 'OFF'}")
        elif item == "start_random":
            self.elab_generation = 0
            self.elab_history = []
            self.elab_best_ever = None
            self._elab_init()
        elif item == "start_saved":
            genomes = self._elab_load_saved()
            if genomes:
                self.elab_generation = 0
                self.elab_history = []
                self.elab_best_ever = None
                self._elab_init(seed_genomes=genomes)
            else:
                self._flash("No saved organisms — starting random")
                self.elab_generation = 0
                self.elab_history = []
                self.elab_best_ever = None
                self._elab_init()
        return True
    return True


def _handle_elab_key(self, key):
    """Handle keys during active Evolution Lab."""
    if key == -1:
        return True
    if key == 27 or key == ord("q"):
        self._exit_elab_mode()
        return True

    pop_size = len(self.elab_sims)
    gc = self.elab_grid_cols

    # Play/pause
    if key == ord(" "):
        self.elab_running = not self.elab_running
        if self.elab_phase == "scored" and self.elab_running:
            # Restart with breeding
            self._elab_breed_next()
        else:
            self._flash("Running" if self.elab_running else "Paused")
        return True

    # Single step
    if key == ord("."):
        self.elab_running = False
        self._elab_step()
        return True

    # Navigate cursor
    if key == curses.KEY_UP or key == ord("w"):
        self.elab_cursor = max(0, self.elab_cursor - gc)
        return True
    if key == curses.KEY_DOWN or key == ord("s"):
        self.elab_cursor = min(pop_size - 1, self.elab_cursor + gc)
        return True
    if key == curses.KEY_LEFT or key == ord("a"):
        self.elab_cursor = max(0, self.elab_cursor - 1)
        return True
    if key == curses.KEY_RIGHT or key == ord("d"):
        self.elab_cursor = min(pop_size - 1, self.elab_cursor + 1)
        return True

    # Toggle favorite (protect from culling)
    if key in (10, 13, curses.KEY_ENTER):
        if 0 <= self.elab_cursor < pop_size:
            self._elab_toggle_favorite(self.elab_cursor)
        return True

    # Favorite with 'f' key too
    if key == ord("f"):
        if 0 <= self.elab_cursor < pop_size:
            self._elab_toggle_favorite(self.elab_cursor)
        return True

    # Force breed now (skip remaining eval steps)
    if key == ord("b"):
        if self.elab_phase == "simulating":
            self._elab_score_all()
        elif self.elab_phase == "scored":
            self._elab_breed_next()
        return True

    # Skip to scoring
    if key == ord("S"):
        if self.elab_phase == "simulating":
            # Fast-forward remaining steps
            remaining = self.elab_eval_gens - self.elab_sim_step
            for _ in range(remaining):
                for i, grid in enumerate(self.elab_sims):
                    _step_sim(grid)
                    self.elab_pop_histories[i].append(grid.population)
                self.elab_sim_step += 1
            self._elab_score_all()
        return True

    # Toggle auto-advance
    if key == ord("A"):
        self.elab_auto_advance = not self.elab_auto_advance
        self.elab_auto_breed = self.elab_auto_advance
        self._flash(f"Auto-advance: {'ON' if self.elab_auto_advance else 'OFF'}")
        return True

    # Cycle fitness preset
    if key == ord("p"):
        presets = list(_FITNESS_PRESETS.keys())
        idx = presets.index(self.elab_fitness_preset) if self.elab_fitness_preset in presets else 0
        self.elab_fitness_preset = presets[(idx + 1) % len(presets)]
        self._flash(f"Fitness: {self.elab_fitness_preset}")
        return True

    # Save organism
    if key == ord("s"):
        if 0 <= self.elab_cursor < pop_size:
            self._elab_save_organism(self.elab_cursor)
        return True

    # Adopt rule
    if key == ord("a"):
        if 0 <= self.elab_cursor < pop_size:
            self._elab_adopt_rule(self.elab_cursor)
        return True

    # Randomize (new random population)
    if key == ord("r"):
        self.elab_generation = 0
        self.elab_history = []
        self.elab_best_ever = None
        self._elab_init()
        self._flash("New random population")
        return True

    # Speed controls
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        return True

    # Return to menu
    if key == ord("R"):
        self.elab_mode = False
        self.elab_running = False
        self.elab_menu = True
        self.elab_menu_sel = 0
        return True

    return True


# ── Drawing ──────────────────────────────────────────────────────────

_COLOR_TIERS = [
    (1, curses.A_DIM), (1, 0), (4, curses.A_DIM), (4, 0),
    (6, curses.A_DIM), (6, 0), (7, 0), (7, curses.A_BOLD),
]


def _draw_elab_menu(self, max_y, max_x):
    """Draw the Evolution Lab settings menu."""
    self.stdscr.erase()

    title = "── Evolution Lab: Automated Rule Discovery ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Genetic algorithm breeds CA rules scored by entropy, symmetry & stability"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    items = [
        ("Population Size", str(self.elab_pop_size), "Number of competing organisms (4-20)"),
        ("Eval Generations", str(self.elab_eval_gens), "Steps to simulate before scoring (50-500)"),
        ("Mutation Rate", f"{int(self.elab_mutation_rate * 100)}%", "Chance of mutating each rule digit"),
        ("Elite Survivors", str(self.elab_elite_count), "Top performers that reproduce"),
        ("Fitness Preset", self.elab_fitness_preset, "balanced / beauty / chaos / complexity / stability"),
        ("Auto-Advance", "ON" if self.elab_auto_advance else "OFF", "Automatically breed next generation"),
        (">>> START (Random) <<<", "", "Begin with random organisms"),
        (">>> START (From Saved) <<<", "", "Breed from previously saved organisms"),
    ]

    for i, (label, value, hint) in enumerate(items):
        y = 5 + i * 2
        if y >= max_y - 12:
            break
        if i >= 6:
            line = f"  {label}"
            attr = curses.color_pair(3) | curses.A_BOLD
            if i == self.elab_menu_sel:
                attr |= curses.A_REVERSE
        else:
            line = f"  {label:<20s} {value:<12s} {hint}"
            attr = curses.color_pair(6)
            if i == self.elab_menu_sel:
                attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    # Info box
    info_y = max(5 + len(items) * 2 + 1, max_y - 10)
    info_lines = [
        "HOW IT WORKS:",
        "  A population of CA rules runs in parallel on a tiled grid.",
        "  Each organism is scored by analytics: entropy, symmetry, stability.",
        "  Top performers breed (crossover + mutation); weak rules are culled.",
        "  Favorite (Enter) any organism to protect it from culling.",
        "  The GA discovers surprising patterns no human would design by hand.",
        "",
        "  You can pause, inspect, favorite, save, or adopt any discovered rule.",
    ]
    for i, line in enumerate(info_lines):
        iy = info_y + i
        if iy >= max_y - 2:
            break
        try:
            self.stdscr.addstr(iy, 2, line[:max_x - 3],
                               curses.color_pair(1) if i > 0 else curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter/Space]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_elab(self, max_y, max_x):
    """Draw the Evolution Lab tiled view."""
    self.stdscr.erase()

    gr = self.elab_grid_rows
    gc = self.elab_grid_cols
    pop_size = len(self.elab_sims)

    # Title bar
    state_ch = "▶" if self.elab_running else "‖"
    n_fav = len(self.elab_favorites)
    progress = f"{self.elab_sim_step}/{self.elab_eval_gens}"
    if self.elab_phase == "scored":
        progress = "SCORED"

    title = (f" {state_ch} EVOLUTION LAB"
             f"  |  Gen {self.elab_generation}"
             f"  |  {progress}"
             f"  |  {self.elab_fitness_preset}"
             f"  |  {n_fav} fav")
    if self.elab_best_ever:
        title += f"  |  Best: {self.elab_best_ever.get('rule', '?')} ({self.elab_best_ever.get('total', 0):.0f}pts gen {self.elab_best_ever.get('gen', '?')})"

    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Recalculate tile dimensions
    usable_h = max_y - 5
    usable_w = max_x - 1
    th = max(4, usable_h // gr - 1)
    tw_chars = max(8, usable_w // gc - 1)
    tw = tw_chars // 2  # cell columns

    draw_y_start = 2
    draw_x_start = 1

    for idx in range(pop_size):
        row = idx // gc
        col = idx % gc

        tile_y = draw_y_start + row * (th + 1)
        tile_x = draw_x_start + col * (tw * 2 + 1)

        if tile_y + th >= max_y - 2 or tile_x + tw * 2 >= max_x:
            continue

        grid = self.elab_sims[idx]
        genome = self.elab_genomes[idx]
        fitness = self.elab_fitness[idx] if idx < len(self.elab_fitness) else {}
        is_cursor = (idx == self.elab_cursor)
        is_fav = (idx in self.elab_favorites)

        # Border color
        if is_fav:
            border_attr = curses.color_pair(3) | curses.A_BOLD
        elif is_cursor:
            border_attr = curses.color_pair(7) | curses.A_BOLD
        else:
            border_attr = curses.color_pair(6) | curses.A_DIM

        # Header: label + score
        label = _genome_label(genome)
        if is_fav:
            label = "★ " + label
        score = fitness.get("total", 0)
        if score > 0:
            score_str = f" {score:.0f}"
        else:
            score_str = f" P:{grid.population}"
        header = label[:tw * 2 - len(score_str) - 1] + score_str
        header = header[:tw * 2]
        try:
            self.stdscr.addstr(tile_y, tile_x, header, border_attr)
        except curses.error:
            pass

        # Border line
        try:
            self.stdscr.addstr(tile_y + 1, tile_x, "─" * (tw * 2), border_attr)
        except curses.error:
            pass

        # Simulation content
        sim_rows = min(th - 2, grid.rows)
        sim_cols = min(tw, grid.cols)
        for sr in range(sim_rows):
            sy = tile_y + 2 + sr
            if sy >= max_y - 2:
                break
            for sc in range(sim_cols):
                sx = tile_x + sc * 2
                if sx + 1 >= max_x:
                    break
                age = grid.cells[sr][sc]
                if age > 0:
                    v = min(1.0, age / 20.0)
                    di = max(1, min(4, int(v * 4.0) + 1))
                    ch = _DENSITY[di]
                    ci = min(7, int(v * 7.99))
                    pair_idx, extra = _COLOR_TIERS[ci]
                    attr = curses.color_pair(pair_idx) | extra
                    if not is_cursor and not is_fav:
                        attr |= curses.A_DIM
                    try:
                        self.stdscr.addstr(sy, sx, ch, attr)
                    except curses.error:
                        pass

        # Bottom border
        by = tile_y + th
        if by < max_y - 2:
            try:
                self.stdscr.addstr(by, tile_x, "─" * (tw * 2), border_attr)
            except curses.error:
                pass

        # Cursor / favorite markers
        if is_cursor:
            try:
                self.stdscr.addstr(tile_y + 1, tile_x, "▸", curses.color_pair(7) | curses.A_BOLD)
            except curses.error:
                pass

        if is_fav:
            try:
                self.stdscr.addstr(tile_y + 1, tile_x, "★", curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass

    # ── Fitness detail for cursor ──
    status_y = max_y - 3
    if status_y > 0 and 0 <= self.elab_cursor < pop_size:
        genome = self.elab_genomes[self.elab_cursor]
        fitness = self.elab_fitness[self.elab_cursor] if self.elab_cursor < len(self.elab_fitness) else {}
        grid = self.elab_sims[self.elab_cursor]

        if fitness.get("total", 0) > 0:
            info = (f" #{self.elab_cursor + 1} {_genome_label(genome)}"
                    f"  |  Total:{fitness.get('total', 0):.0f}"
                    f"  Ent:{fitness.get('entropy', 0):.0f}"
                    f"  Sym:{fitness.get('symmetry', 0):.0f}"
                    f"  Stab:{fitness.get('stability', 0):.0f}"
                    f"  Long:{fitness.get('longevity', 0):.0f}"
                    f"  Div:{fitness.get('diversity', 0):.0f}")
        else:
            info = (f" #{self.elab_cursor + 1} {_genome_label(genome)}"
                    f"  |  Pop: {grid.population}"
                    f"  |  Step: {self.elab_sim_step}")
        try:
            self.stdscr.addstr(status_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # ── Generation history sparkline ──
    hist_y = max_y - 2
    if hist_y > 0 and self.elab_history:
        scores = [h["best_score"] for h in self.elab_history[-30:]]
        spark_chars = "▁▂▃▄▅▆▇█"
        if scores:
            lo, hi = min(scores), max(scores)
            span = hi - lo if hi != lo else 1
            sparkline = ""
            for sc in scores:
                si = int((sc - lo) / span * (len(spark_chars) - 1))
                si = max(0, min(si, len(spark_chars) - 1))
                sparkline += spark_chars[si]
            hist_info = f" Fitness trend: {sparkline}  avg:{self.elab_history[-1].get('avg_score', 0):.0f}"
            try:
                self.stdscr.addstr(hist_y, 0, hist_info[:max_x - 1],
                                   curses.color_pair(3))
            except curses.error:
                pass

    # ── Hint bar ──
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            if self.elab_phase == "scored" and not self.elab_auto_breed:
                hint = " [Space]=breed next [f/Enter]=favorite [s]=save [b]=breed [p]=fitness [A]=auto [R]=menu [q]=exit"
            else:
                hint = " [Space]=pause [↑↓←→]=navigate [f/Enter]=favorite [b]=score now [S]=skip [s]=save [p]=fitness [A]=auto [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ── Registration ─────────────────────────────────────────────────────


def register(App):
    """Register Evolution Lab methods on the App class."""
    App._enter_elab_mode = _enter_elab_mode
    App._exit_elab_mode = _exit_elab_mode
    App._elab_init = _elab_init
    App._elab_step = _elab_step
    App._elab_score_all = _elab_score_all
    App._elab_breed_next = _elab_breed_next
    App._elab_toggle_favorite = _elab_toggle_favorite
    App._elab_save_organism = _elab_save_organism
    App._elab_adopt_rule = _elab_adopt_rule
    App._elab_load_saved = _elab_load_saved
    App._handle_elab_menu_key = _handle_elab_menu_key
    App._handle_elab_key = _handle_elab_key
    App._draw_elab_menu = _draw_elab_menu
    App._draw_elab = _draw_elab
