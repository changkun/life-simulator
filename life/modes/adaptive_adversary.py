"""Mode: Adaptive Adversary — co-evolutionary Living Labyrinth where the dungeon
learns from how you play.

Fuses the Living Labyrinth (playable roguelike CA dungeon) with the Genesis
Protocol (evolutionary rule discovery).  After each level the dungeon evolves
its CA ruleset using crossover & mutation, with a fitness function that targets
the player's behavioral weaknesses.  A population of candidate rulesets competes
to be "most challenging but still solvable" — difficulty via co-evolution.

Keys:
  Arrow keys / WASD / hjkl — move player (@)
  Space                    — wait one turn
  f                        — use Freeze item
  v                        — use Reverse item
  m                        — use Mutate item
  +/-                      — adjust CA tick rate
  ?                        — toggle help overlay
  TAB                      — toggle Adversary Report
  q / Escape               — exit Adaptive Adversary
"""

import curses
import math
import random
import time
import copy

from life.rules import rule_string


# ── Constants ──────────────────────────────────────────────────────────

WALL = 1
FLOOR = 0

PLAYER_CHAR = "@"
EXIT_CHAR = "◈"
ITEM_FREEZE_CHAR = "❄"
ITEM_REVERSE_CHAR = "⊛"
ITEM_MUTATE_CHAR = "✦"
WALL_CHAR = "██"
FLOOR_CHAR = "··"

ITEM_FREEZE = "freeze"
ITEM_REVERSE = "reverse"
ITEM_MUTATE = "mutate"

ITEM_CHARS = {
    ITEM_FREEZE: ITEM_FREEZE_CHAR,
    ITEM_REVERSE: ITEM_REVERSE_CHAR,
    ITEM_MUTATE: ITEM_MUTATE_CHAR,
}

ITEMS_PER_DUNGEON = 12

# Population size for adversarial evolution
ADVERSARY_POP_SIZE = 8
# How many rulesets survive selection each round
ADVERSARY_ELITE = 3
# Mutation rate for adversary genomes
ADVERSARY_MUTATION_RATE = 0.18


# ── Maze generation ───────────────────────────────────────────────────

def _generate_maze(rows, cols):
    """Generate a maze using recursive backtracker."""
    mr = rows if rows % 2 == 1 else rows - 1
    mc = cols if cols % 2 == 1 else cols - 1
    maze = [[WALL] * cols for _ in range(rows)]

    def neighbors(r, c):
        result = []
        for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            nr, nc = r + dr, c + dc
            if 1 <= nr < mr - 1 and 1 <= nc < mc - 1 and maze[nr][nc] == WALL:
                result.append((nr, nc, r + dr // 2, c + dc // 2))
        return result

    stack = [(1, 1)]
    maze[1][1] = FLOOR
    while stack:
        r, c = stack[-1]
        nbrs = neighbors(r, c)
        if nbrs:
            nr, nc, wr, wc = random.choice(nbrs)
            maze[wr][wc] = FLOOR
            maze[nr][nc] = FLOOR
            stack.append((nr, nc))
        else:
            stack.pop()

    for r in range(1, mr - 1):
        for c in range(1, mc - 1):
            if maze[r][c] == WALL:
                adj_floors = sum(
                    1 for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    if 0 <= r + dr < rows and 0 <= c + dc < cols
                    and maze[r + dr][c + dc] == FLOOR
                )
                if adj_floors >= 2 and random.random() < 0.3:
                    maze[r][c] = FLOOR
    return maze


def _find_open_cells(maze, rows, cols):
    return [(r, c) for r in range(rows) for c in range(cols) if maze[r][c] == FLOOR]


# ── CA step ────────────────────────────────────────────────────────────

def _adversary_ca_step(cells, rows, cols, birth, survival, frozen_mask=None):
    """One CA generation with optional freeze mask."""
    new = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if frozen_mask and frozen_mask[r][c] > 0:
                new[r][c] = cells[r][c]
                continue
            count = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    if cells[nr][nc] > 0:
                        count += 1
            alive = cells[r][c] > 0
            if alive:
                new[r][c] = cells[r][c] + 1 if count in survival else 0
            else:
                new[r][c] = 1 if count in birth else 0
    return new


# ── Adversary genome helpers ──────────────────────────────────────────

def _random_adversary_genome():
    """Generate a random adversary genome (CA ruleset)."""
    birth = {d for d in range(9) if random.random() < 0.3}
    survival = {d for d in range(9) if random.random() < 0.3}
    if not birth:
        birth.add(random.randint(1, 5))
    if not survival:
        survival.add(random.randint(2, 4))
    # Asymmetry bias: probability that the rule favors asymmetric corridor growth
    # Higher values produce corridors that collapse from one side
    asymmetry_bias = random.uniform(0.0, 0.5)
    # Wall growth speed modifier (multiplier on birth probability thresholds)
    wall_aggression = random.uniform(0.3, 1.0)
    return {
        "birth": birth,
        "survival": survival,
        "asymmetry_bias": asymmetry_bias,
        "wall_aggression": wall_aggression,
    }


def _crossover_adversary(g1, g2):
    """Uniform crossover between two adversary genomes."""
    child_birth = set()
    child_survival = set()
    for d in range(9):
        if d in (g1 if random.random() < 0.5 else g2)["birth"]:
            child_birth.add(d)
        if d in (g1 if random.random() < 0.5 else g2)["survival"]:
            child_survival.add(d)
    if not child_birth:
        child_birth.add(random.randint(1, 5))
    return {
        "birth": child_birth,
        "survival": child_survival,
        "asymmetry_bias": (g1["asymmetry_bias"] + g2["asymmetry_bias"]) / 2
                          + random.gauss(0, 0.05),
        "wall_aggression": max(0.1, min(1.5,
            (g1["wall_aggression"] + g2["wall_aggression"]) / 2
            + random.gauss(0, 0.05))),
    }


def _mutate_adversary(genome, rate=ADVERSARY_MUTATION_RATE):
    """Mutate an adversary genome."""
    g = {
        "birth": set(genome["birth"]),
        "survival": set(genome["survival"]),
        "asymmetry_bias": genome["asymmetry_bias"],
        "wall_aggression": genome["wall_aggression"],
    }
    for d in range(9):
        if random.random() < rate:
            g["birth"].symmetric_difference_update({d})
        if random.random() < rate:
            g["survival"].symmetric_difference_update({d})
    if not g["birth"]:
        g["birth"].add(random.randint(1, 5))
    if random.random() < rate:
        g["asymmetry_bias"] = max(0.0, min(1.0,
            g["asymmetry_bias"] + random.gauss(0, 0.1)))
    if random.random() < rate:
        g["wall_aggression"] = max(0.1, min(1.5,
            g["wall_aggression"] + random.gauss(0, 0.1)))
    return g


def _genome_rule_label(genome):
    """Short label for a genome."""
    return rule_string(genome["birth"], genome["survival"])


# ── Player behavior tracking ─────────────────────────────────────────

def _empty_player_profile():
    """Return a fresh player behavior profile."""
    return {
        # Movement direction counts
        "moves_up": 0,
        "moves_down": 0,
        "moves_left": 0,
        "moves_right": 0,
        "moves_wait": 0,
        "total_moves": 0,
        # Item usage counts
        "freeze_used": 0,
        "reverse_used": 0,
        "mutate_used": 0,
        # Outcome metrics
        "turns_to_exit": [],     # list of turn counts per completed level
        "deaths": 0,
        "wins": 0,
        # Path analysis
        "positions": [],         # (r, c) trail for directional bias
        "direction_changes": 0,  # how often the player reverses direction
        "last_dir": None,
    }


def _update_direction(profile, dr, dc):
    """Record a movement direction."""
    if dr == -1:
        profile["moves_up"] += 1
        d = "up"
    elif dr == 1:
        profile["moves_down"] += 1
        d = "down"
    elif dc == -1:
        profile["moves_left"] += 1
        d = "left"
    elif dc == 1:
        profile["moves_right"] += 1
        d = "right"
    else:
        profile["moves_wait"] += 1
        d = "wait"
    profile["total_moves"] += 1
    if profile["last_dir"] and profile["last_dir"] != d and d != "wait":
        profile["direction_changes"] += 1
    if d != "wait":
        profile["last_dir"] = d


def _analyze_player_weaknesses(profile):
    """Analyze the player profile and return a weakness report dict."""
    report = {
        "dominant_direction": None,
        "direction_bias": 0.0,
        "item_reliance": None,
        "item_reliance_score": 0.0,
        "avg_time_to_exit": 0.0,
        "hesitancy": 0.0,        # ratio of waits to total moves
        "path_predictability": 0.0,
        "adaptations": [],       # list of string descriptions
    }

    total = max(1, profile["total_moves"])

    # Direction bias
    dir_counts = {
        "right": profile["moves_right"],
        "left": profile["moves_left"],
        "down": profile["moves_down"],
        "up": profile["moves_up"],
    }
    dominant = max(dir_counts, key=dir_counts.get)
    bias = dir_counts[dominant] / total
    report["dominant_direction"] = dominant
    report["direction_bias"] = bias
    if bias > 0.35:
        report["adaptations"].append(
            f"Player favors {dominant} ({bias:.0%}) → evolving asymmetric collapse from {dominant}")

    # Item reliance
    item_counts = {
        "freeze": profile["freeze_used"],
        "reverse": profile["reverse_used"],
        "mutate": profile["mutate_used"],
    }
    total_items = sum(item_counts.values())
    if total_items > 0:
        top_item = max(item_counts, key=item_counts.get)
        reliance = item_counts[top_item] / max(1, total_items)
        report["item_reliance"] = top_item
        report["item_reliance_score"] = reliance
        if reliance > 0.5 and total_items >= 2:
            if top_item == "freeze":
                report["adaptations"].append(
                    "Freeze-dependent → evolving faster wall regrowth")
            elif top_item == "reverse":
                report["adaptations"].append(
                    "Reverse-dependent → evolving more volatile CA dynamics")
            elif top_item == "mutate":
                report["adaptations"].append(
                    "Mutate-dependent → evolving rules resilient to random flips")

    # Average time to exit
    if profile["turns_to_exit"]:
        report["avg_time_to_exit"] = sum(profile["turns_to_exit"]) / len(profile["turns_to_exit"])

    # Hesitancy
    report["hesitancy"] = profile["moves_wait"] / total
    if report["hesitancy"] > 0.2:
        report["adaptations"].append(
            f"Hesitant player ({report['hesitancy']:.0%} waits) → evolving aggressive wall encroachment")

    # Path predictability (low direction changes = predictable)
    if total > 5:
        change_rate = profile["direction_changes"] / total
        report["path_predictability"] = 1.0 - min(1.0, change_rate * 4)
        if report["path_predictability"] > 0.6:
            report["adaptations"].append(
                f"Predictable pathing ({report['path_predictability']:.0%}) → evolving corridor traps")

    if not report["adaptations"]:
        report["adaptations"].append("No strong patterns detected yet — exploring rule space broadly")

    return report


# ── Adversary fitness function ────────────────────────────────────────

def _adversary_fitness(genome, player_profile, level_result):
    """Score an adversary genome based on how well it challenged the player.

    Fitness = challenge_score × solvability_bonus
    - challenge_score rewards dungeons that exploit player weaknesses
    - solvability_bonus penalizes dungeons that are impossible or trivial
    """
    score = 50.0  # base score

    weaknesses = _analyze_player_weaknesses(player_profile)

    # Reward targeting the dominant direction with asymmetric rules
    if weaknesses["direction_bias"] > 0.3:
        # Genomes with higher asymmetry_bias get bonus when player is directionally biased
        score += genome["asymmetry_bias"] * weaknesses["direction_bias"] * 40

    # Reward wall aggression when player relies on freeze items
    if weaknesses["item_reliance"] == "freeze":
        score += genome["wall_aggression"] * weaknesses["item_reliance_score"] * 30

    # Reward volatile rules (many birth conditions) when player uses reverse
    if weaknesses["item_reliance"] == "reverse":
        birth_richness = len(genome["birth"]) / 9.0
        score += birth_richness * weaknesses["item_reliance_score"] * 25

    # Reward stable-but-tricky rules when player uses mutate
    if weaknesses["item_reliance"] == "mutate":
        survival_richness = len(genome["survival"]) / 9.0
        score += survival_richness * weaknesses["item_reliance_score"] * 25

    # Hesitancy: reward aggressive wall growth
    score += weaknesses["hesitancy"] * genome["wall_aggression"] * 20

    # Path predictability: reward asymmetric rulesets
    score += weaknesses["path_predictability"] * genome["asymmetry_bias"] * 20

    # Solvability constraint: ideal difficulty sweet spot
    if level_result == "won":
        # Player won — bonus for making it close (high turn count)
        turns = player_profile["turns_to_exit"][-1] if player_profile["turns_to_exit"] else 50
        # Sweet spot: 30-80 turns
        if 30 <= turns <= 80:
            score *= 1.3  # perfect difficulty
        elif turns < 15:
            score *= 0.5  # too easy
        elif turns > 150:
            score *= 0.7  # too tedious
    elif level_result == "died":
        # Player died — slight penalty (want challenging but solvable)
        score *= 0.85
    else:
        # Quit / unknown
        score *= 0.6

    return max(0.0, score)


# ── Adversary evolution engine ────────────────────────────────────────

def _evolve_adversary_population(population, fitnesses, player_profile):
    """Evolve the adversary population based on fitness scores.

    Returns a new population of ADVERSARY_POP_SIZE genomes.
    """
    # Sort by fitness descending
    ranked = sorted(zip(population, fitnesses), key=lambda x: x[1], reverse=True)

    # Elites survive
    new_pop = [copy.deepcopy(ranked[i][0]) for i in range(min(ADVERSARY_ELITE, len(ranked)))]

    # Breed children from top half
    parents = [g for g, _ in ranked[:max(2, len(ranked) // 2)]]
    while len(new_pop) < ADVERSARY_POP_SIZE - 1:
        p1, p2 = random.sample(parents, 2)
        child = _crossover_adversary(p1, p2)
        child = _mutate_adversary(child)
        new_pop.append(child)

    # One fully random genome for exploration
    new_pop.append(_random_adversary_genome())

    return new_pop[:ADVERSARY_POP_SIZE]


def _targeted_mutation(genome, weaknesses):
    """Apply targeted mutations based on player weaknesses."""
    g = copy.deepcopy(genome)

    # If player goes right a lot, bias birth rules toward higher counts
    # (denser walls on right side due to asymmetric growth)
    if weaknesses["dominant_direction"] in ("right", "down") and weaknesses["direction_bias"] > 0.35:
        g["asymmetry_bias"] = min(1.0, g["asymmetry_bias"] + 0.1)

    # If player relies on freeze, increase wall aggression
    if weaknesses["item_reliance"] == "freeze" and weaknesses["item_reliance_score"] > 0.5:
        g["wall_aggression"] = min(1.5, g["wall_aggression"] + 0.15)
        # Add more birth conditions to regrow walls faster
        if random.random() < 0.4:
            candidate = random.randint(2, 5)
            g["birth"].add(candidate)

    # If player relies on reverse, make rules more chaotic
    if weaknesses["item_reliance"] == "reverse" and weaknesses["item_reliance_score"] > 0.5:
        if random.random() < 0.3:
            g["birth"].add(random.randint(1, 6))
            if len(g["survival"]) > 2:
                g["survival"].discard(random.choice(list(g["survival"])))

    return g


# ── Solvability check ─────────────────────────────────────────────────

def _check_solvability(cells, rows, cols, start_r, start_c, exit_r, exit_c):
    """BFS to check if there's a path from start to exit on floor cells."""
    if cells[start_r][start_c] > 0 or cells[exit_r][exit_c] > 0:
        return False
    visited = set()
    queue = [(start_r, start_c)]
    visited.add((start_r, start_c))
    while queue:
        r, c = queue.pop(0)
        if r == exit_r and c == exit_c:
            return True
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited:
                if cells[nr][nc] == 0:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
    return False


# ── State initialization ──────────────────────────────────────────────

def _adversary_init(self):
    """Initialize Adaptive Adversary state variables."""
    self.adversary_mode = False
    self.adversary_running = False
    self.adversary_cells = None
    self.adversary_rows = 0
    self.adversary_cols = 0
    self.adversary_player_r = 1
    self.adversary_player_c = 1
    self.adversary_exit_r = 0
    self.adversary_exit_c = 0
    self.adversary_items = {}
    self.adversary_inventory = {ITEM_FREEZE: 0, ITEM_REVERSE: 0, ITEM_MUTATE: 0}
    self.adversary_frozen_mask = None
    self.adversary_birth = {3}
    self.adversary_survival = {1, 2, 3, 4, 5}
    self.adversary_ca_ticks = 1
    self.adversary_turn = 0
    self.adversary_score = 0
    self.adversary_level = 1
    self.adversary_wins = 0
    self.adversary_deaths = 0
    self.adversary_history = []
    self.adversary_max_history = 10
    self.adversary_show_help = False
    self.adversary_show_report = False
    self.adversary_msg = ""
    self.adversary_msg_time = 0.0
    self.adversary_game_over = False
    self.adversary_won = False
    self.adversary_fov_radius = 20

    # Adversary evolution state
    self.adversary_population = []       # list of adversary genomes
    self.adversary_fitnesses = []        # fitness scores per genome
    self.adversary_current_genome = None # genome used for current level
    self.adversary_current_genome_idx = 0
    self.adversary_player_profile = _empty_player_profile()
    self.adversary_weakness_report = None
    self.adversary_generation = 0        # evolution generation counter
    self.adversary_adaptation_log = []   # list of (level, adaptations) tuples
    self.adversary_level_results = []    # list of (genome, result, fitness)


def _adversary_generate(self):
    """Generate a new adversary dungeon using the current genome."""
    h, w = self.grid.rows, self.grid.cols
    self.adversary_rows = h
    self.adversary_cols = w

    # Generate base maze
    self.adversary_cells = _generate_maze(h, w)

    # Apply current genome's rules
    genome = self.adversary_current_genome
    self.adversary_birth = set(genome["birth"])
    self.adversary_survival = set(genome["survival"])

    # Apply asymmetry bias: selectively wall off one side more
    if genome["asymmetry_bias"] > 0.2:
        weaknesses = _analyze_player_weaknesses(self.adversary_player_profile)
        dom = weaknesses.get("dominant_direction", "right")
        bias = genome["asymmetry_bias"]
        for r in range(h):
            for c in range(w):
                if self.adversary_cells[r][c] == FLOOR:
                    # Add walls in the player's preferred direction
                    extra_wall_prob = 0.0
                    if dom == "right" and c > w * 0.6:
                        extra_wall_prob = bias * 0.15
                    elif dom == "left" and c < w * 0.4:
                        extra_wall_prob = bias * 0.15
                    elif dom == "down" and r > h * 0.6:
                        extra_wall_prob = bias * 0.15
                    elif dom == "up" and r < h * 0.4:
                        extra_wall_prob = bias * 0.15
                    if random.random() < extra_wall_prob:
                        self.adversary_cells[r][c] = WALL

    # Place player near top-left
    open_cells = _find_open_cells(self.adversary_cells, h, w)
    if not open_cells:
        for r in range(h // 4, 3 * h // 4):
            for c in range(w // 4, 3 * w // 4):
                self.adversary_cells[r][c] = FLOOR
        open_cells = _find_open_cells(self.adversary_cells, h, w)

    open_cells.sort(key=lambda rc: rc[0] + rc[1])
    self.adversary_player_r, self.adversary_player_c = open_cells[0]

    open_cells.sort(key=lambda rc: rc[0] + rc[1], reverse=True)
    self.adversary_exit_r, self.adversary_exit_c = open_cells[0]

    # Safety zones
    self.adversary_cells[self.adversary_player_r][self.adversary_player_c] = FLOOR
    self.adversary_cells[self.adversary_exit_r][self.adversary_exit_c] = FLOOR
    for cr, cc in [(self.adversary_player_r, self.adversary_player_c),
                   (self.adversary_exit_r, self.adversary_exit_c)]:
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < h and 0 <= nc < w:
                    self.adversary_cells[nr][nc] = FLOOR

    # Ensure solvability
    if not _check_solvability(self.adversary_cells, h, w,
                              self.adversary_player_r, self.adversary_player_c,
                              self.adversary_exit_r, self.adversary_exit_c):
        # Carve a guaranteed path
        r, c = self.adversary_player_r, self.adversary_player_c
        er, ec = self.adversary_exit_r, self.adversary_exit_c
        while r != er or c != ec:
            self.adversary_cells[r][c] = FLOOR
            if random.random() < 0.6:
                if r < er:
                    r += 1
                elif r > er:
                    r -= 1
            else:
                if c < ec:
                    c += 1
                elif c > ec:
                    c -= 1
        self.adversary_cells[er][ec] = FLOOR

    # Scatter items — adjust based on wall_aggression
    self.adversary_items = {}
    floor_cells = [
        (r, c) for r, c in _find_open_cells(self.adversary_cells, h, w)
        if (r, c) != (self.adversary_player_r, self.adversary_player_c)
        and (r, c) != (self.adversary_exit_r, self.adversary_exit_c)
    ]
    random.shuffle(floor_cells)
    # More aggressive dungeons get slightly more items (fairness)
    n_items = min(ITEMS_PER_DUNGEON + int(genome["wall_aggression"] * 3), len(floor_cells))
    item_types = [ITEM_FREEZE, ITEM_REVERSE, ITEM_MUTATE]
    for i in range(n_items):
        self.adversary_items[floor_cells[i]] = random.choice(item_types)

    # Reset level state
    self.adversary_frozen_mask = [[0] * w for _ in range(h)]
    self.adversary_history = []
    self.adversary_turn = 0
    self.adversary_game_over = False
    self.adversary_won = False
    self.adversary_inventory = {ITEM_FREEZE: 0, ITEM_REVERSE: 0, ITEM_MUTATE: 0}
    self.adversary_history.append([row[:] for row in self.adversary_cells])


def _adversary_flash(self, msg):
    self.adversary_msg = msg
    self.adversary_msg_time = time.time()


# ── Entry / exit ──────────────────────────────────────────────────────

def _enter_adversary_mode(self):
    """Enter Adaptive Adversary mode."""
    self.adversary_mode = True
    self.adversary_running = True
    self.adversary_level = 1
    self.adversary_wins = 0
    self.adversary_deaths = 0
    self.adversary_score = 0
    self.adversary_show_help = False
    self.adversary_show_report = False
    self.adversary_generation = 0
    self.adversary_player_profile = _empty_player_profile()
    self.adversary_weakness_report = None
    self.adversary_adaptation_log = []
    self.adversary_level_results = []

    # Initialize population with random genomes
    self.adversary_population = [_random_adversary_genome() for _ in range(ADVERSARY_POP_SIZE)]
    self.adversary_fitnesses = [0.0] * ADVERSARY_POP_SIZE
    # Pick the first genome for level 1
    self.adversary_current_genome_idx = 0
    self.adversary_current_genome = self.adversary_population[0]

    _adversary_generate(self)
    _adversary_flash(self, "The dungeon is watching you. It will learn. Reach ◈ to escape. Press ? for help.")


def _exit_adversary_mode(self):
    """Exit Adaptive Adversary mode."""
    self.adversary_mode = False
    self.adversary_running = False
    self.adversary_cells = None
    self.adversary_frozen_mask = None
    self.adversary_history = []
    self.adversary_items = {}


# ── CA tick ────────────────────────────────────────────────────────────

def _adversary_tick_ca(self):
    """Advance the CA one generation."""
    h, w = self.adversary_rows, self.adversary_cols

    if len(self.adversary_history) >= self.adversary_max_history:
        self.adversary_history.pop(0)
    self.adversary_history.append([row[:] for row in self.adversary_cells])

    self.adversary_cells = _adversary_ca_step(
        self.adversary_cells, h, w,
        self.adversary_birth, self.adversary_survival,
        self.adversary_frozen_mask,
    )

    self.adversary_cells[self.adversary_player_r][self.adversary_player_c] = FLOOR
    self.adversary_cells[self.adversary_exit_r][self.adversary_exit_c] = FLOOR

    for r in range(h):
        for c in range(w):
            if self.adversary_frozen_mask[r][c] > 0:
                self.adversary_frozen_mask[r][c] -= 1


# ── Item usage ─────────────────────────────────────────────────────────

def _adversary_use_freeze(self):
    if self.adversary_inventory[ITEM_FREEZE] <= 0:
        _adversary_flash(self, "No freeze items!")
        return
    self.adversary_inventory[ITEM_FREEZE] -= 1
    self.adversary_player_profile["freeze_used"] += 1
    radius = 5
    pr, pc = self.adversary_player_r, self.adversary_player_c
    h, w = self.adversary_rows, self.adversary_cols
    for r in range(max(0, pr - radius), min(h, pr + radius + 1)):
        for c in range(max(0, pc - radius), min(w, pc + radius + 1)):
            if (r - pr) ** 2 + (c - pc) ** 2 <= radius ** 2:
                self.adversary_frozen_mask[r][c] = 10
    _adversary_flash(self, "❄ Freeze! The dungeon notes your tactic...")


def _adversary_use_reverse(self):
    if self.adversary_inventory[ITEM_REVERSE] <= 0:
        _adversary_flash(self, "No reverse items!")
        return
    self.adversary_inventory[ITEM_REVERSE] -= 1
    self.adversary_player_profile["reverse_used"] += 1
    steps_back = min(5, len(self.adversary_history) - 1)
    if steps_back > 0:
        old = self.adversary_history[-(steps_back + 1)]
        radius = 6
        pr, pc = self.adversary_player_r, self.adversary_player_c
        h, w = self.adversary_rows, self.adversary_cols
        for r in range(max(0, pr - radius), min(h, pr + radius + 1)):
            for c in range(max(0, pc - radius), min(w, pc + radius + 1)):
                if (r - pr) ** 2 + (c - pc) ** 2 <= radius ** 2:
                    self.adversary_cells[r][c] = old[r][c]
        _adversary_flash(self, f"⊛ Reverse! Rewound {steps_back} steps. The dungeon remembers...")
    else:
        _adversary_flash(self, "Not enough history to rewind!")


def _adversary_use_mutate(self):
    if self.adversary_inventory[ITEM_MUTATE] <= 0:
        _adversary_flash(self, "No mutate items!")
        return
    self.adversary_inventory[ITEM_MUTATE] -= 1
    self.adversary_player_profile["mutate_used"] += 1
    radius = 7
    pr, pc = self.adversary_player_r, self.adversary_player_c
    h, w = self.adversary_rows, self.adversary_cols
    flipped = 0
    for r in range(max(0, pr - radius), min(h, pr + radius + 1)):
        for c in range(max(0, pc - radius), min(w, pc + radius + 1)):
            if (r - pr) ** 2 + (c - pc) ** 2 <= radius ** 2:
                if random.random() < 0.4:
                    self.adversary_cells[r][c] = FLOOR if self.adversary_cells[r][c] > 0 else WALL
                    flipped += 1
    _adversary_flash(self, f"✦ Mutate! Flipped {flipped} cells. The dungeon is adapting...")


# ── Player movement ───────────────────────────────────────────────────

def _adversary_move(self, dr, dc):
    """Try to move player."""
    if self.adversary_game_over:
        return False
    nr = self.adversary_player_r + dr
    nc = self.adversary_player_c + dc
    h, w = self.adversary_rows, self.adversary_cols

    if nr < 0 or nr >= h or nc < 0 or nc >= w:
        return False

    if self.adversary_cells[nr][nc] > 0:
        _adversary_flash(self, "Blocked by wall!")
        return False

    self.adversary_player_r = nr
    self.adversary_player_c = nc

    # Track position for behavior analysis
    self.adversary_player_profile["positions"].append((nr, nc))
    if len(self.adversary_player_profile["positions"]) > 200:
        self.adversary_player_profile["positions"] = \
            self.adversary_player_profile["positions"][-100:]

    # Pick up items
    pos = (nr, nc)
    if pos in self.adversary_items:
        item_type = self.adversary_items.pop(pos)
        self.adversary_inventory[item_type] += 1
        name = item_type.capitalize()
        _adversary_flash(self, f"Picked up {ITEM_CHARS[item_type]} {name}!")

    # Check win
    if nr == self.adversary_exit_r and nc == self.adversary_exit_c:
        self.adversary_won = True
        self.adversary_game_over = True
        self.adversary_wins += 1
        self.adversary_player_profile["wins"] += 1
        self.adversary_player_profile["turns_to_exit"].append(self.adversary_turn)
        bonus = max(0, 500 - self.adversary_turn * 2)
        level_bonus = self.adversary_level * 100
        self.adversary_score += bonus + level_bonus

        # Score the adversary genome and evolve
        _adversary_end_level(self, "won")
        _adversary_flash(self, f"Level {self.adversary_level} complete! The dungeon evolves...")

    return True


def _adversary_player_turn(self, dr, dc):
    """Execute a player turn: move, record behavior, tick CA."""
    # Record direction
    _update_direction(self.adversary_player_profile, dr, dc)

    _adversary_move(self, dr, dc)

    self.adversary_turn += 1
    for _ in range(self.adversary_ca_ticks):
        _adversary_tick_ca(self)

    # Check crush
    pr, pc = self.adversary_player_r, self.adversary_player_c
    if self.adversary_cells[pr][pc] > 0 and not self.adversary_game_over:
        self.adversary_game_over = True
        self.adversary_won = False
        self.adversary_deaths += 1
        self.adversary_player_profile["deaths"] += 1
        _adversary_end_level(self, "died")
        _adversary_flash(self, "Crushed! The dungeon learns from your defeat... Press 'n' to continue.")


# ── Level end: evolution trigger ──────────────────────────────────────

def _adversary_end_level(self, result):
    """Called when a level ends (win or death). Evolve the adversary."""
    genome = self.adversary_current_genome

    # Compute fitness for current genome
    fitness = _adversary_fitness(genome, self.adversary_player_profile, result)
    self.adversary_fitnesses[self.adversary_current_genome_idx] = fitness

    # Compute weakness report
    self.adversary_weakness_report = _analyze_player_weaknesses(self.adversary_player_profile)

    # Log adaptation
    self.adversary_adaptation_log.append(
        (self.adversary_level, list(self.adversary_weakness_report["adaptations"]))
    )
    # Keep log bounded
    if len(self.adversary_adaptation_log) > 20:
        self.adversary_adaptation_log = self.adversary_adaptation_log[-15:]

    self.adversary_level_results.append({
        "genome": _genome_rule_label(genome),
        "result": result,
        "fitness": fitness,
        "level": self.adversary_level,
    })


def _adversary_next_level(self):
    """Advance to the next level with evolved dungeon."""
    self.adversary_level += 1
    self.adversary_generation += 1

    weaknesses = _analyze_player_weaknesses(self.adversary_player_profile)

    # Evolve the population
    self.adversary_population = _evolve_adversary_population(
        self.adversary_population,
        self.adversary_fitnesses,
        self.adversary_player_profile,
    )

    # Apply targeted mutations to top genomes based on player weaknesses
    for i in range(min(ADVERSARY_ELITE, len(self.adversary_population))):
        self.adversary_population[i] = _targeted_mutation(
            self.adversary_population[i], weaknesses)

    # Reset fitnesses for new generation
    self.adversary_fitnesses = [0.0] * ADVERSARY_POP_SIZE

    # Select next genome: round-robin through population
    self.adversary_current_genome_idx = (self.adversary_level - 1) % ADVERSARY_POP_SIZE
    self.adversary_current_genome = self.adversary_population[self.adversary_current_genome_idx]

    _adversary_generate(self)
    rule_label = _genome_rule_label(self.adversary_current_genome)
    _adversary_flash(self, f"Level {self.adversary_level} — Dungeon evolved to {rule_label}")


# ── Key handler ────────────────────────────────────────────────────────

def _handle_adversary_key(self, key):
    """Handle keyboard input for Adaptive Adversary mode."""
    if key == ord('q') or key == 27:
        _exit_adversary_mode(self)
        return True

    if key == ord('?'):
        self.adversary_show_help = not self.adversary_show_help
        self.adversary_show_report = False
        return True

    if key == 9:  # TAB
        self.adversary_show_report = not self.adversary_show_report
        self.adversary_show_help = False
        return True

    if key == ord('n'):
        if self.adversary_game_over:
            _adversary_next_level(self)
        else:
            # Restart from level 1 with current population
            self.adversary_level = 0
            self.adversary_score = 0
            _adversary_next_level(self)
        return True

    if self.adversary_game_over and self.adversary_won:
        if key in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT,
                   ord('w'), ord('a'), ord('s'), ord('d'),
                   ord('h'), ord('j'), ord('k'), ord('l'), ord(' ')):
            _adversary_next_level(self)
            return True

    if self.adversary_game_over:
        return True

    # Movement
    if key == curses.KEY_UP or key == ord('w') or key == ord('k'):
        _adversary_player_turn(self, -1, 0)
        return True
    if key == curses.KEY_DOWN or key == ord('s') or key == ord('j'):
        _adversary_player_turn(self, 1, 0)
        return True
    if key == curses.KEY_LEFT or key == ord('a') or key == ord('h'):
        _adversary_player_turn(self, 0, -1)
        return True
    if key == curses.KEY_RIGHT or key == ord('d') or key == ord('l'):
        _adversary_player_turn(self, 0, 1)
        return True
    if key == ord(' '):
        _adversary_player_turn(self, 0, 0)
        return True

    # Items
    if key == ord('f'):
        _adversary_use_freeze(self)
        return True
    if key == ord('v'):
        _adversary_use_reverse(self)
        return True
    if key == ord('m'):
        _adversary_use_mutate(self)
        return True

    # CA tick rate
    if key == ord('+') or key == ord('='):
        self.adversary_ca_ticks = min(5, self.adversary_ca_ticks + 1)
        _adversary_flash(self, f"CA ticks per move: {self.adversary_ca_ticks}")
        return True
    if key == ord('-'):
        self.adversary_ca_ticks = max(1, self.adversary_ca_ticks - 1)
        _adversary_flash(self, f"CA ticks per move: {self.adversary_ca_ticks}")
        return True

    return True


# ── Drawing ────────────────────────────────────────────────────────────

def _draw_adversary(self, max_y=None, max_x=None):
    """Render the Adaptive Adversary dungeon."""
    scr = self.stdscr
    scr.erase()
    max_h, max_w = scr.getmaxyx()

    if self.adversary_cells is None:
        return

    h, w = self.adversary_rows, self.adversary_cols
    pr, pc = self.adversary_player_r, self.adversary_player_c
    er, ec = self.adversary_exit_r, self.adversary_exit_c

    # Viewport centered on player
    view_h = max_h - 4  # HUD + report hint
    view_w = max_w // 2
    half_h = view_h // 2
    half_w = view_w // 2
    cam_r = max(half_h, min(h - half_h - 1, pr))
    cam_c = max(half_w, min(w - half_w - 1, pc))
    start_r = cam_r - half_h
    start_c = cam_c - half_w

    # Color pairs
    try:
        curses.init_pair(200, curses.COLOR_WHITE, curses.COLOR_WHITE)
        curses.init_pair(201, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(202, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(203, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(204, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(205, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(206, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(207, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(208, curses.COLOR_RED, curses.COLOR_WHITE)
    except curses.error:
        pass

    for screen_r in range(view_h):
        grid_r = start_r + screen_r
        if grid_r < 0 or grid_r >= h:
            continue
        for screen_c in range(view_w):
            grid_c = start_c + screen_c
            if grid_c < 0 or grid_c >= w:
                continue
            sx = screen_c * 2
            sy = screen_r
            if sy >= max_h - 4 or sx + 1 >= max_w:
                continue

            pos = (grid_r, grid_c)
            ch = None
            attr = curses.A_NORMAL

            if grid_r == pr and grid_c == pc:
                ch = PLAYER_CHAR + " "
                attr = curses.color_pair(201) | curses.A_BOLD
            elif grid_r == er and grid_c == ec:
                ch = EXIT_CHAR + " "
                attr = curses.color_pair(203) | curses.A_BOLD
            elif pos in self.adversary_items:
                item_type = self.adversary_items[pos]
                ch = ITEM_CHARS[item_type] + " "
                if item_type == ITEM_FREEZE:
                    attr = curses.color_pair(202) | curses.A_BOLD
                elif item_type == ITEM_REVERSE:
                    attr = curses.color_pair(205) | curses.A_BOLD
                else:
                    attr = curses.color_pair(203) | curses.A_BOLD
            elif self.adversary_cells[grid_r][grid_c] > 0:
                age = self.adversary_cells[grid_r][grid_c]
                if self.adversary_frozen_mask[grid_r][grid_c] > 0:
                    ch = WALL_CHAR
                    attr = curses.color_pair(207)
                elif age <= 1:
                    ch = "░░"
                    attr = curses.color_pair(204)
                elif age <= 3:
                    ch = "▒▒"
                    attr = curses.color_pair(204)
                elif age <= 8:
                    ch = "▓▓"
                    attr = curses.color_pair(200)
                else:
                    ch = WALL_CHAR
                    attr = curses.color_pair(200)
            else:
                ch = FLOOR_CHAR
                attr = curses.color_pair(206) | curses.A_DIM

            try:
                scr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # ── HUD ──
    hud_y = max_h - 4
    genome = self.adversary_current_genome
    rule_label = _genome_rule_label(genome) if genome else "???"

    inv_str = (
        f"❄×{self.adversary_inventory[ITEM_FREEZE]} "
        f"⊛×{self.adversary_inventory[ITEM_REVERSE]} "
        f"✦×{self.adversary_inventory[ITEM_MUTATE]}"
    )
    status = (
        f" Lv {self.adversary_level} │ Turn {self.adversary_turn} │ "
        f"Score {self.adversary_score} │ {inv_str} │ "
        f"Rule: {rule_label} │ Gen {self.adversary_generation}"
    )
    try:
        scr.addstr(hud_y, 0, status[:max_w - 1], curses.A_REVERSE)
        remaining = max_w - 1 - len(status)
        if remaining > 0:
            scr.addstr(hud_y, len(status), " " * remaining, curses.A_REVERSE)
    except curses.error:
        pass

    # Stats line
    stats = (
        f" W:{self.adversary_wins} D:{self.adversary_deaths} │ "
        f"CA/move: {self.adversary_ca_ticks} │ "
        f"[?]Help [TAB]Report [f]Freeze [v]Rev [m]Mut [q]Quit"
    )
    try:
        scr.addstr(hud_y + 1, 0, stats[:max_w - 1], curses.A_DIM)
    except curses.error:
        pass

    # Adversary hint line
    if self.adversary_weakness_report:
        adaptations = self.adversary_weakness_report["adaptations"]
        hint = f" Dungeon adapting: {adaptations[0]}" if adaptations else ""
    else:
        hint = " The dungeon is studying your behavior..."
    try:
        scr.addstr(hud_y + 2, 0, hint[:max_w - 1],
                   curses.color_pair(204) | curses.A_DIM)
    except curses.error:
        pass

    # Flash message
    if self.adversary_msg and time.time() - self.adversary_msg_time < 3.0:
        msg = f" {self.adversary_msg} "
        msg_x = max(0, (max_w - len(msg)) // 2)
        try:
            scr.addstr(hud_y + 3, msg_x, msg[:max_w - 1],
                       curses.color_pair(203) | curses.A_BOLD)
        except curses.error:
            pass

    # Game over overlay
    if self.adversary_game_over:
        if self.adversary_won:
            msg = f"  ◈ LEVEL {self.adversary_level} COMPLETE! The dungeon evolves... Press any key.  "
            attr = curses.color_pair(201) | curses.A_BOLD
        else:
            msg = "  ☠ CRUSHED! The dungeon learned from your defeat. Press 'n'.  "
            attr = curses.color_pair(204) | curses.A_BOLD
        msg_x = max(0, (max_w - len(msg)) // 2)
        msg_y = max(0, view_h // 2)
        try:
            scr.addstr(msg_y, msg_x, msg, attr)
        except curses.error:
            pass

    # Help overlay
    if self.adversary_show_help:
        help_lines = [
            "╔═══════════════════════════════════════════╗",
            "║       ADAPTIVE ADVERSARY — HELP           ║",
            "╠═══════════════════════════════════════════╣",
            "║ Arrow/WASD/hjkl — Move player (@)         ║",
            "║ Space           — Wait (CA ticks)          ║",
            "║ f               — Use Freeze item          ║",
            "║ v               — Use Reverse item         ║",
            "║ m               — Use Mutate item          ║",
            "║ +/-             — CA ticks per move         ║",
            "║ TAB             — Toggle Adversary Report   ║",
            "║ n               — New dungeon               ║",
            "║ ?               — Toggle this help          ║",
            "║ q/Esc           — Exit mode                 ║",
            "╠═══════════════════════════════════════════╣",
            "║ The dungeon LEARNS from how you play.      ║",
            "║ It evolves CA rules to exploit your         ║",
            "║ weaknesses after each level.                ║",
            "║ Can you outthink an evolving adversary?     ║",
            "╚═══════════════════════════════════════════╝",
        ]
        hy = max(0, (view_h - len(help_lines)) // 2)
        hx = max(0, (max_w - 46) // 2)
        for i, line in enumerate(help_lines):
            try:
                scr.addstr(hy + i, hx, line, curses.A_BOLD)
            except curses.error:
                pass

    # Adversary Report overlay
    if self.adversary_show_report:
        _draw_adversary_report(self, scr, max_h, max_w, view_h)

    scr.nontimeout(True)
    scr.timeout(100)


def _draw_adversary_report(self, scr, max_h, max_w, view_h):
    """Draw the Adversary Report overlay."""
    profile = self.adversary_player_profile
    report = self.adversary_weakness_report or _analyze_player_weaknesses(profile)

    lines = []
    lines.append("╔═══════════════════════════════════════════════════╗")
    lines.append("║            ADVERSARY INTELLIGENCE REPORT          ║")
    lines.append("╠═══════════════════════════════════════════════════╣")

    # Player behavior summary
    total = max(1, profile["total_moves"])
    lines.append(f"║ Total moves: {total:>5}  │  Wins: {profile['wins']}  Deaths: {profile['deaths']:<5}  ║")
    lines.append("║                                                   ║")

    # Direction breakdown
    lines.append("║ ── Movement Analysis ──                            ║")
    dirs = {
        "↑": profile["moves_up"], "↓": profile["moves_down"],
        "←": profile["moves_left"], "→": profile["moves_right"],
        "○": profile["moves_wait"],
    }
    bar_max = max(dirs.values()) if max(dirs.values()) > 0 else 1
    for sym, cnt in dirs.items():
        bar_len = int(cnt / bar_max * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        pct = cnt / total * 100
        line = f"║  {sym} {bar} {cnt:>4} ({pct:4.1f}%)"
        lines.append(f"{line:<52}║")

    lines.append("║                                                   ║")

    # Item usage
    lines.append("║ ── Item Usage ──                                   ║")
    items = {
        "❄ Freeze": profile["freeze_used"],
        "⊛ Reverse": profile["reverse_used"],
        "✦ Mutate": profile["mutate_used"],
    }
    for name, cnt in items.items():
        line = f"║  {name}: {cnt}"
        lines.append(f"{line:<52}║")

    lines.append("║                                                   ║")

    # Detected weaknesses
    lines.append("║ ── Detected Patterns ──                            ║")
    for adaptation in report["adaptations"]:
        # Wrap long lines
        while len(adaptation) > 47:
            line = f"║  {adaptation[:47]}"
            lines.append(f"{line:<52}║")
            adaptation = adaptation[47:]
        line = f"║  • {adaptation}"
        lines.append(f"{line:<52}║")

    lines.append("║                                                   ║")

    # Evolution status
    lines.append("║ ── Evolution Status ──                             ║")
    line = f"║  Generation: {self.adversary_generation}  │  Population: {ADVERSARY_POP_SIZE} rulesets"
    lines.append(f"{line:<52}║")
    if self.adversary_current_genome:
        rule_label = _genome_rule_label(self.adversary_current_genome)
        asym = self.adversary_current_genome["asymmetry_bias"]
        aggr = self.adversary_current_genome["wall_aggression"]
        line = f"║  Current rule: {rule_label}"
        lines.append(f"{line:<52}║")
        line = f"║  Asymmetry: {asym:.2f}  │  Aggression: {aggr:.2f}"
        lines.append(f"{line:<52}║")

    lines.append("║                                                   ║")

    # Recent adaptation log
    if self.adversary_adaptation_log:
        lines.append("║ ── Recent Adaptations ──                          ║")
        for lvl, adaptations in self.adversary_adaptation_log[-5:]:
            for a in adaptations[:1]:  # show first adaptation per level
                text = a[:42]
                line = f"║  Lv{lvl:>2}: {text}"
                lines.append(f"{line:<52}║")

    lines.append("╚═══════════════════════════════════════════════════╝")

    hy = max(0, (view_h - len(lines)) // 2)
    hx = max(0, (max_w - 54) // 2)
    for i, line in enumerate(lines):
        if hy + i >= max_h:
            break
        try:
            scr.addstr(hy + i, hx, line[:max_w - 1],
                       curses.color_pair(205) | curses.A_BOLD)
        except curses.error:
            pass


# ── Step / auto-stepping ──────────────────────────────────────────────

def _adversary_step(self):
    """Auto-step: no-op since movement is turn-based."""
    pass


def _is_adversary_auto_stepping(self):
    """Turn-based, no auto-stepping."""
    return False


# ── Menu (no separate menu needed) ────────────────────────────────────

def _handle_adversary_menu_key(self, key):
    return _handle_adversary_key(self, key)


def _draw_adversary_menu(self):
    _draw_adversary(self)


# ── Registration ──────────────────────────────────────────────────────

def register(App):
    """Register Adaptive Adversary mode methods on App class."""
    App.adversary_mode = False
    App.adversary_running = False
    _adversary_init(App)

    App._enter_adversary_mode = _enter_adversary_mode
    App._exit_adversary_mode = _exit_adversary_mode
    App._handle_adversary_key = _handle_adversary_key
    App._handle_adversary_menu_key = _handle_adversary_menu_key
    App._draw_adversary = _draw_adversary
    App._draw_adversary_menu = _draw_adversary_menu
    App._adversary_step = _adversary_step
    App._is_adversary_auto_stepping = _is_adversary_auto_stepping
