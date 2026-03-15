"""Mode: evo — simulation mode for the life package."""
import curses
import math
import random
import time


from life.colors import color_for_age
from life.constants import CELL_CHAR, SPEEDS, SPEED_LABELS
from life.grid import Grid
from life.rules import rule_string

def _enter_evo_mode(self):
    """Open the evolution mode settings menu."""
    if self.compare_mode:
        self._exit_compare_mode()
    if self.race_mode:
        self._exit_race_mode()
    self.evo_menu = True
    self.evo_menu_sel = 0



def _exit_evo_mode(self):
    """Leave evolution mode entirely."""
    self.evo_mode = False
    self.evo_menu = False
    self.evo_phase = "idle"
    self.evo_grids.clear()
    self.evo_rules.clear()
    self.evo_fitness.clear()
    self.evo_pop_histories.clear()
    self.evo_generation = 0
    self.evo_sim_step = 0
    self.evo_sel = 0
    self.evo_history.clear()
    self.evo_best_ever = None
    self._flash("Evolution mode OFF")



def _evo_random_rule(self) -> tuple[set, set]:
    """Generate a random B/S ruleset."""
    birth = {d for d in range(9) if random.random() < 0.3}
    survival = {d for d in range(9) if random.random() < 0.3}
    # Ensure at least one birth and one survival digit
    if not birth:
        birth.add(random.randint(1, 5))
    if not survival:
        survival.add(random.randint(2, 4))
    return birth, survival



def _evo_mutate(self, birth: set, survival: set) -> tuple[set, set]:
    """Mutate a ruleset by flipping individual digits."""
    new_birth = set(birth)
    new_survival = set(survival)
    for d in range(9):
        if random.random() < self.evo_mutation_rate:
            if d in new_birth:
                new_birth.discard(d)
            else:
                new_birth.add(d)
        if random.random() < self.evo_mutation_rate:
            if d in new_survival:
                new_survival.discard(d)
            else:
                new_survival.add(d)
    # Ensure at least one birth digit
    if not new_birth:
        new_birth.add(random.randint(1, 5))
    return new_birth, new_survival



def _evo_crossover(self, parent1: tuple[set, set], parent2: tuple[set, set]) -> tuple[set, set]:
    """Single-point crossover between two rulesets."""
    b1, s1 = parent1
    b2, s2 = parent2
    # For each digit, pick from either parent
    child_birth = set()
    child_survival = set()
    for d in range(9):
        child_birth.add(d) if (d in (b1 if random.random() < 0.5 else b2)) else None
        child_survival.add(d) if (d in (s1 if random.random() < 0.5 else s2)) else None
    if not child_birth:
        child_birth.add(random.randint(1, 5))
    return child_birth, child_survival



def _evo_init_population(self):
    """Create initial random population and start simulation."""
    self.evo_grids = []
    self.evo_rules = []
    self.evo_fitness = []
    self.evo_pop_histories = []
    self.evo_sim_step = 0
    self.evo_generation += 1

    # If we have previous elite, breed from them; otherwise random
    if self.evo_history and len(self.evo_history[-1].get("elite_rules", [])) >= 2:
        elite_rules = self.evo_history[-1]["elite_rules"]
        new_rules = list(elite_rules)  # keep elites
        while len(new_rules) < self.evo_pop_size:
            # Crossover two random elites + mutate
            p1 = random.choice(elite_rules)
            p2 = random.choice(elite_rules)
            child = self._evo_crossover(p1, p2)
            child = self._evo_mutate(child[0], child[1])
            new_rules.append(child)
    else:
        new_rules = [self._evo_random_rule() for _ in range(self.evo_pop_size)]

    # Create a small grid for each individual with random initial state
    sub_rows = 30
    sub_cols = 40
    for birth, survival in new_rules:
        g = Grid(sub_rows, sub_cols)
        g.birth = set(birth)
        g.survival = set(survival)
        # Random 20% fill
        for r in range(sub_rows):
            for c in range(sub_cols):
                if random.random() < 0.2:
                    g.set_alive(r, c)
        self.evo_grids.append(g)
        self.evo_rules.append((set(birth), set(survival)))
        self.evo_pop_histories.append([g.population])
        self.evo_fitness.append({})

    self.evo_phase = "simulating"
    self.running = True



def _evo_step_sim(self):
    """Advance all evolution grids by one step."""
    if self.evo_phase != "simulating":
        return
    self.evo_sim_step += 1
    for i, g in enumerate(self.evo_grids):
        g.step()
        self.evo_pop_histories[i].append(g.population)

    if self.evo_sim_step >= self.evo_grid_gens:
        self._evo_score_all()



def _evo_score_all(self):
    """Compute fitness for all individuals."""
    self.evo_phase = "scored"
    self.running = False
    for i, g in enumerate(self.evo_grids):
        hist = self.evo_pop_histories[i]
        self.evo_fitness[i] = self._evo_compute_fitness(g, hist)

    # Sort by fitness score (best first)
    order = sorted(range(len(self.evo_fitness)),
                   key=lambda i: self.evo_fitness[i].get("total", 0), reverse=True)
    self.evo_grids = [self.evo_grids[i] for i in order]
    self.evo_rules = [self.evo_rules[i] for i in order]
    self.evo_fitness = [self.evo_fitness[i] for i in order]
    self.evo_pop_histories = [self.evo_pop_histories[i] for i in order]

    # Track best ever
    best = self.evo_fitness[0]
    if self.evo_best_ever is None or best.get("total", 0) > self.evo_best_ever.get("total", 0):
        self.evo_best_ever = dict(best)
        self.evo_best_ever["rule"] = rule_string(self.evo_rules[0][0], self.evo_rules[0][1])
        self.evo_best_ever["gen"] = self.evo_generation

    # Record elite rules for next generation
    elite_count = min(self.evo_elite_count, len(self.evo_rules))
    elite_rules = [self.evo_rules[i] for i in range(elite_count)]
    self.evo_history.append({
        "generation": self.evo_generation,
        "best_score": best.get("total", 0),
        "best_rule": rule_string(self.evo_rules[0][0], self.evo_rules[0][1]),
        "avg_score": sum(f.get("total", 0) for f in self.evo_fitness) / max(1, len(self.evo_fitness)),
        "elite_rules": elite_rules,
    })
    self.evo_sel = 0
    self._flash(f"Gen {self.evo_generation} scored! Best: {rule_string(self.evo_rules[0][0], self.evo_rules[0][1])} ({best.get('total', 0):.0f}pts)")



def _evo_compute_fitness(self, g: Grid, hist: list[int]) -> dict:
    """Compute fitness score for a single individual."""
    if not hist:
        return {"total": 0, "longevity": 0, "stability": 0, "diversity": 0, "population": 0}

    # Longevity: how many gens stayed alive (non-zero population)
    alive_gens = sum(1 for p in hist if p > 0)
    longevity = alive_gens

    # Population score: average population (normalized)
    avg_pop = sum(hist) / len(hist) if hist else 0
    pop_score = min(avg_pop, 200)  # cap at 200

    # Stability: low variance = more stable
    if len(hist) > 1 and avg_pop > 0:
        variance = sum((p - avg_pop) ** 2 for p in hist) / len(hist)
        std = variance ** 0.5
        # Low std relative to mean = more stable
        cv = std / max(avg_pop, 1)  # coefficient of variation
        stability = max(0, 100 - cv * 100)
    else:
        stability = 0

    # Diversity: count distinct population values (pattern richness)
    unique_pops = len(set(hist[-100:]))  # last 100 gens
    diversity = min(unique_pops * 2, 100)

    # Weight based on fitness mode
    if self.evo_fitness_mode == "longevity":
        total = longevity * 3 + pop_score * 0.5 + stability * 0.5 + diversity * 0.5
    elif self.evo_fitness_mode == "diversity":
        total = diversity * 3 + longevity * 0.5 + pop_score * 0.5 + stability * 0.5
    elif self.evo_fitness_mode == "population":
        total = pop_score * 3 + longevity * 0.5 + stability * 0.5 + diversity * 0.5
    else:  # balanced
        total = longevity + pop_score + stability + diversity

    return {
        "total": total,
        "longevity": longevity,
        "stability": stability,
        "diversity": diversity,
        "population": pop_score,
    }



def _evo_next_generation(self):
    """Breed the next generation from current elite."""
    self._evo_init_population()



def _evo_adopt_rule(self):
    """Adopt the selected evolved ruleset into the main simulator."""
    if not self.evo_rules:
        return
    idx = self.evo_sel
    birth, survival = self.evo_rules[idx]
    self.grid.birth = set(birth)
    self.grid.survival = set(survival)
    rs = rule_string(birth, survival)
    self._exit_evo_mode()
    self._flash(f"Adopted evolved rule: {rs}")



def _handle_evo_menu_key(self, key: int) -> bool:
    """Handle input in the evolution settings menu."""
    if key == -1:
        return True
    if key == 27 or key == ord("q"):
        self.evo_menu = False
        return True
    menu_items = ["pop_size", "grid_gens", "mutation_rate", "elite_count", "fitness_mode", "start"]
    if key in (curses.KEY_UP, ord("k")):
        self.evo_menu_sel = (self.evo_menu_sel - 1) % len(menu_items)
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.evo_menu_sel = (self.evo_menu_sel + 1) % len(menu_items)
        return True
    if key in (10, 13, curses.KEY_ENTER, ord(" ")):
        item = menu_items[self.evo_menu_sel]
        if item == "start":
            self.evo_menu = False
            self.evo_mode = True
            self.evo_generation = 0
            self.evo_history.clear()
            self.evo_best_ever = None
            self._evo_init_population()
            return True
        if item == "pop_size":
            val = self._prompt_text(f"Population size (current: {self.evo_pop_size})")
            if val:
                try:
                    n = int(val)
                    if 4 <= n <= 24:
                        self.evo_pop_size = n
                    else:
                        self._flash("Must be 4-24")
                except ValueError:
                    self._flash("Invalid number")
        elif item == "grid_gens":
            val = self._prompt_text(f"Simulation generations (current: {self.evo_grid_gens})")
            if val:
                try:
                    n = int(val)
                    if 50 <= n <= 2000:
                        self.evo_grid_gens = n
                    else:
                        self._flash("Must be 50-2000")
                except ValueError:
                    self._flash("Invalid number")
        elif item == "mutation_rate":
            val = self._prompt_text(f"Mutation rate 0-100% (current: {int(self.evo_mutation_rate * 100)}%)")
            if val:
                try:
                    n = int(val.replace("%", ""))
                    if 0 <= n <= 100:
                        self.evo_mutation_rate = n / 100.0
                    else:
                        self._flash("Must be 0-100")
                except ValueError:
                    self._flash("Invalid number")
        elif item == "elite_count":
            val = self._prompt_text(f"Elite survivors (current: {self.evo_elite_count})")
            if val:
                try:
                    n = int(val)
                    if 2 <= n <= self.evo_pop_size // 2:
                        self.evo_elite_count = n
                    else:
                        self._flash(f"Must be 2-{self.evo_pop_size // 2}")
                except ValueError:
                    self._flash("Invalid number")
        elif item == "fitness_mode":
            modes = ["balanced", "longevity", "diversity", "population"]
            idx = modes.index(self.evo_fitness_mode)
            self.evo_fitness_mode = modes[(idx + 1) % len(modes)]
        return True
    return True



def _handle_evo_key(self, key: int) -> bool:
    """Handle input during active evolution mode."""
    if key == -1:
        return True
    if key == 27 or key == ord("q"):
        self._exit_evo_mode()
        return True
    if key == ord(" "):
        if self.evo_phase == "scored":
            # Start next generation
            self._evo_next_generation()
        else:
            self.running = not self.running
            self._flash("Playing" if self.running else "Paused")
        return True
    if key == ord("n"):
        if self.evo_phase == "simulating":
            self.running = False
            self._evo_step_sim()
        elif self.evo_phase == "scored":
            self._evo_next_generation()
        return True
    if key == ord("a"):
        if self.evo_phase == "scored" and self.evo_rules:
            self._evo_adopt_rule()
        return True
    if key in (curses.KEY_UP, ord("k")):
        if self.evo_phase == "scored" and self.evo_rules:
            self.evo_sel = (self.evo_sel - 1) % len(self.evo_rules)
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        if self.evo_phase == "scored" and self.evo_rules:
            self.evo_sel = (self.evo_sel + 1) % len(self.evo_rules)
        return True
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == ord("f"):
        # Cycle fitness mode
        modes = ["balanced", "longevity", "diversity", "population"]
        idx = modes.index(self.evo_fitness_mode)
        self.evo_fitness_mode = modes[(idx + 1) % len(modes)]
        self._flash(f"Fitness: {self.evo_fitness_mode}")
        return True
    if key == ord("m"):
        # Adjust mutation rate interactively
        val = self._prompt_text(f"Mutation rate 0-100% (current: {int(self.evo_mutation_rate * 100)}%)")
        if val:
            try:
                n = int(val.replace("%", ""))
                if 0 <= n <= 100:
                    self.evo_mutation_rate = n / 100.0
                    self._flash(f"Mutation: {int(self.evo_mutation_rate * 100)}%")
            except ValueError:
                self._flash("Invalid number")
        return True
    if key == ord("s"):
        # Skip to end of simulation
        if self.evo_phase == "simulating":
            while self.evo_sim_step < self.evo_grid_gens:
                self.evo_sim_step += 1
                for i, g in enumerate(self.evo_grids):
                    g.step()
                    self.evo_pop_histories[i].append(g.population)
            self._evo_score_all()
        return True
    return True



def _draw_evo_menu(self, max_y: int, max_x: int):
    """Draw the evolution mode settings menu."""
    title = "── Evolution Mode: Genetic Algorithm Settings ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    desc = "Breed Life-like rulesets through natural selection"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(desc)) // 2), desc,
                           curses.color_pair(6))
    except curses.error:
        pass

    items = [
        ("Population Size", str(self.evo_pop_size), "Number of competing rulesets (4-24)"),
        ("Sim Generations", str(self.evo_grid_gens), "Generations to simulate each ruleset (50-2000)"),
        ("Mutation Rate", f"{int(self.evo_mutation_rate * 100)}%", "Chance of flipping each rule digit"),
        ("Elite Survivors", str(self.evo_elite_count), "Top performers that reproduce"),
        ("Fitness Criteria", self.evo_fitness_mode, "balanced / longevity / diversity / population"),
        (">>> START EVOLUTION <<<", "", "Begin breeding rulesets!"),
    ]

    for i, (label, value, hint) in enumerate(items):
        y = 5 + i * 2
        if y >= max_y - 2:
            break
        if i == len(items) - 1:
            # Start button
            line = f"  {label}"
            attr = curses.color_pair(3) | curses.A_BOLD
            if i == self.evo_menu_sel:
                attr = curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE
        else:
            line = f"  {label:<20s} {value:<12s} {hint}"
            attr = curses.color_pair(6)
            if i == self.evo_menu_sel:
                attr = curses.color_pair(7) | curses.A_REVERSE
        line = line[:max_x - 2]
        try:
            self.stdscr.addstr(y, 2, line, attr)
        except curses.error:
            pass

    tip_y = max_y - 1
    if tip_y > 0:
        tip = " Up/Down=navigate │ Enter/Space=edit/toggle │ q/Esc=cancel"
        try:
            self.stdscr.addstr(tip_y, 0, tip[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_evo(self, max_y: int, max_x: int):
    """Draw the evolution mode view with tiled sub-grids and fitness scoreboard."""
    n = len(self.evo_grids)
    if n == 0:
        return

    # Compute tile layout: roughly square arrangement
    tile_cols = int(math.ceil(math.sqrt(n)))
    tile_rows = int(math.ceil(n / tile_cols))

    # Reserve space for scoreboard at bottom
    scoreboard_lines = min(n + 4, max_y // 3)
    grid_area_h = max_y - scoreboard_lines
    grid_area_w = max_x

    if grid_area_h < 4 or grid_area_w < 10:
        try:
            self.stdscr.addstr(0, 0, "Terminal too small for evolution mode", curses.color_pair(5))
        except curses.error:
            pass
        return

    tile_h = max(3, grid_area_h // tile_rows)
    tile_w = max(6, grid_area_w // tile_cols)

    # Draw each individual's grid tile
    for idx in range(n):
        tr = idx // tile_cols
        tc = idx % tile_cols
        origin_y = tr * tile_h
        origin_x = tc * tile_w

        if origin_y >= grid_area_h or origin_x >= grid_area_w:
            continue

        g = self.evo_grids[idx]
        birth, survival = self.evo_rules[idx]
        rs = rule_string(birth, survival)

        # Label bar
        label = f" {rs} P:{g.population}"
        if self.evo_phase == "scored":
            score = self.evo_fitness[idx].get("total", 0)
            label = f" {rs} {score:.0f}pts"
        label = label[:tile_w - 1]

        label_attr = curses.color_pair(6) | curses.A_BOLD
        if self.evo_phase == "scored" and idx == 0:
            label_attr = curses.color_pair(3) | curses.A_BOLD
        if self.evo_phase == "scored" and idx == self.evo_sel:
            label_attr = curses.color_pair(7) | curses.A_REVERSE | curses.A_BOLD
        try:
            self.stdscr.addstr(origin_y, origin_x, label, label_attr)
        except curses.error:
            pass

        # Draw cells using density rendering for small tiles
        cell_vis_rows = tile_h - 1
        cell_vis_cols = (tile_w - 1) // 2

        for sy in range(min(cell_vis_rows, g.rows)):
            for sx in range(min(cell_vis_cols, g.cols)):
                age = g.cells[sy][sx]
                px = origin_x + sx * 2
                py = origin_y + 1 + sy
                if py >= origin_y + tile_h or px + 1 >= origin_x + tile_w:
                    continue
                if py >= grid_area_h or px + 1 >= max_x:
                    continue
                if age > 0:
                    try:
                        self.stdscr.addstr(py, px, CELL_CHAR, color_for_age(age))
                    except curses.error:
                        pass

        # Tile borders
        if tc < tile_cols - 1:
            border_x = origin_x + tile_w - 1
            if border_x < max_x:
                for sy in range(tile_h):
                    py = origin_y + sy
                    if py < grid_area_h:
                        try:
                            self.stdscr.addstr(py, border_x, "│",
                                               curses.color_pair(6) | curses.A_DIM)
                        except curses.error:
                            pass


def register(App):
    """Register evo mode methods on the App class."""
    App._enter_evo_mode = _enter_evo_mode
    App._exit_evo_mode = _exit_evo_mode
    App._evo_random_rule = _evo_random_rule
    App._evo_mutate = _evo_mutate
    App._evo_crossover = _evo_crossover
    App._evo_init_population = _evo_init_population
    App._evo_step_sim = _evo_step_sim
    App._evo_score_all = _evo_score_all
    App._evo_compute_fitness = _evo_compute_fitness
    App._evo_next_generation = _evo_next_generation
    App._evo_adopt_rule = _evo_adopt_rule
    App._handle_evo_menu_key = _handle_evo_menu_key
    App._handle_evo_key = _handle_evo_key
    App._draw_evo_menu = _draw_evo_menu
    App._draw_evo = _draw_evo

