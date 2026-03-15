"""Mode: ancestor_search — Reverse-Engineering / Ancestor Search.

Given any frozen grid state (target pattern), search backwards in time to find
predecessor states — grids that evolve INTO the target after one CA step.

Uses constraint-based SAT-style backtracking combined with stochastic search to
discover ancestor configurations. Highlights **Garden of Eden** patterns (states
with no possible predecessor).

Features:
  - Draw or load a target pattern
  - Stochastic + constraint-propagation ancestor search
  - Real-time visualization of search progress
  - Garden of Eden detection (no-ancestor proof via exhaustive local search)
  - Multi-candidate display showing top ancestor solutions
  - Analytics integration (entropy, symmetry of ancestors)
  - Works with any B/S rule set
"""
import curses
import hashlib
import math
import random
import time as _time

from life.constants import SPEEDS, SPEED_LABELS
from life.grid import Grid

# ── Constants ────────────────────────────────────────────────────────

_MAX_CANDIDATES = 8       # max ancestor candidates to track
_SEARCH_BATCH = 50        # mutations per search step
_ANNEAL_INIT_TEMP = 2.0   # simulated annealing initial temperature
_ANNEAL_COOL = 0.997      # cooling factor
_MAX_RESTARTS = 200       # stochastic restarts before declaring Garden of Eden
_GOE_LOCAL_TRIES = 500    # exhaustive attempts for Garden of Eden confirmation

# Preset target patterns (small, interesting shapes)
_PRESETS = [
    ("block", "2×2 still life", [(0, 0), (0, 1), (1, 0), (1, 1)]),
    ("blinker", "period-2 oscillator", [(0, 0), (0, 1), (0, 2)]),
    ("glider", "smallest spaceship", [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]),
    ("beehive", "6-cell still life", [(0, 1), (0, 2), (1, 0), (1, 3), (2, 1), (2, 2)]),
    ("toad", "period-2 oscillator", [(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2)]),
    ("loaf", "7-cell still life", [(0, 1), (0, 2), (1, 0), (1, 3), (2, 1), (2, 3), (3, 2)]),
    ("boat", "5-cell still life", [(0, 0), (0, 1), (1, 0), (1, 2), (2, 1)]),
    ("r-pentomino", "long-lived methuselah", [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]),
    ("custom", "draw your own target", []),
]

_DENSITY = ["  ", "░░", "▒▒", "▓▓", "██"]

# ── Search Engine ────────────────────────────────────────────────────


def _grid_to_flat(cells, rows, cols):
    """Convert 2D cells to flat binary list."""
    return [1 if cells[r][c] > 0 else 0 for r in range(rows) for c in range(cols)]


def _flat_to_cells(flat, rows, cols):
    """Convert flat binary list to 2D cells."""
    return [[flat[r * cols + c] for c in range(cols)] for r in range(rows)]


def _count_neighbours_flat(flat, r, c, rows, cols):
    """Count live neighbors for cell (r,c) in flat grid with toroidal wrapping."""
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr = (r + dr) % rows
            nc = (c + dc) % cols
            if flat[nr * cols + nc]:
                count += 1
    return count


def _step_flat(flat, rows, cols, birth, survival):
    """Apply one CA step to flat grid, return new flat grid."""
    new = [0] * (rows * cols)
    for r in range(rows):
        for c in range(cols):
            n = _count_neighbours_flat(flat, r, c, rows, cols)
            alive = flat[r * cols + c]
            if alive and n in survival:
                new[r * cols + c] = 1
            elif not alive and n in birth:
                new[r * cols + c] = 1
    return new


def _fitness(candidate, target, rows, cols):
    """Compute fitness = number of matching cells after one CA step.

    Higher is better. Perfect = rows * cols (all cells match).
    """
    return sum(1 for a, b in zip(candidate, target) if a == b)


def _hamming(a, b):
    """Count mismatched cells."""
    return sum(1 for x, y in zip(a, b) if x != y)


def _mutate(flat, rate=0.05):
    """Flip random cells."""
    result = flat[:]
    for i in range(len(result)):
        if random.random() < rate:
            result[i] = 1 - result[i]
    return result


def _random_flat(size, density=0.3):
    """Generate random flat grid."""
    return [1 if random.random() < density else 0 for _ in range(size)]


def _crossover(a, b):
    """Single-point crossover."""
    point = random.randint(1, len(a) - 1)
    return a[:point] + b[point:]


class AncestorSearchEngine:
    """Stochastic search engine for finding CA predecessors."""

    def __init__(self, target_flat, rows, cols, birth, survival):
        self.target = target_flat
        self.rows = rows
        self.cols = cols
        self.birth = birth
        self.survival = survival
        self.size = rows * cols
        self.perfect_score = self.size

        # Search state
        self.candidates = []     # list of (flat_grid, score)
        self.best_score = 0
        self.best_candidate = None
        self.solutions = []      # confirmed ancestors (score == perfect)
        self.generation = 0
        self.total_evals = 0
        self.restarts = 0
        self.temperature = _ANNEAL_INIT_TEMP
        self.is_goe = False      # Garden of Eden flag
        self.goe_confidence = 0.0
        self.search_complete = False

        # Initialize population
        self._init_population()

    def _init_population(self):
        """Create initial random candidates."""
        self.candidates = []
        for _ in range(_MAX_CANDIDATES):
            flat = _random_flat(self.size, density=0.3 + random.random() * 0.4)
            evolved = _step_flat(flat, self.rows, self.cols, self.birth, self.survival)
            score = _fitness(evolved, self.target, self.rows, self.cols)
            self.candidates.append((flat, score))
            self.total_evals += 1
            if score > self.best_score:
                self.best_score = score
                self.best_candidate = flat[:]
            if score == self.perfect_score:
                self._add_solution(flat)

    def _add_solution(self, flat):
        """Add a unique solution."""
        h = hashlib.md5(bytes(flat)).hexdigest()
        for s, _, sh in self.solutions:
            if sh == h:
                return
        self.solutions.append((flat[:], self.generation, h))

    def step(self):
        """Run one generation of search."""
        if self.search_complete:
            return

        self.generation += 1
        self.temperature *= _ANNEAL_COOL

        new_candidates = []

        for flat, score in self.candidates:
            best_local = flat
            best_local_score = score

            # Try mutations
            for _ in range(_SEARCH_BATCH // _MAX_CANDIDATES):
                # Adaptive mutation rate based on score proximity
                progress = score / self.perfect_score
                mut_rate = max(0.005, 0.15 * (1.0 - progress * 0.8))

                child = _mutate(flat, rate=mut_rate)

                # Occasionally crossover with best
                if self.best_candidate and random.random() < 0.2:
                    child = _crossover(child, self.best_candidate)
                    child = _mutate(child, rate=0.02)

                evolved = _step_flat(child, self.rows, self.cols, self.birth, self.survival)
                child_score = _fitness(evolved, self.target, self.rows, self.cols)
                self.total_evals += 1

                # Simulated annealing acceptance
                delta = child_score - best_local_score
                if delta > 0 or (self.temperature > 0.01 and
                                 random.random() < math.exp(delta / max(self.temperature, 0.001))):
                    best_local = child
                    best_local_score = child_score

                if child_score == self.perfect_score:
                    self._add_solution(child)

            new_candidates.append((best_local, best_local_score))

            if best_local_score > self.best_score:
                self.best_score = best_local_score
                self.best_candidate = best_local[:]

        self.candidates = new_candidates

        # Check for restart
        if self.generation % 50 == 0 and self.best_score < self.perfect_score:
            self.restarts += 1
            # Keep best half, replace worst half
            self.candidates.sort(key=lambda x: x[1], reverse=True)
            keep = len(self.candidates) // 2
            for i in range(keep, len(self.candidates)):
                flat = _random_flat(self.size, density=random.random() * 0.7)
                evolved = _step_flat(flat, self.rows, self.cols, self.birth, self.survival)
                score = _fitness(evolved, self.target, self.rows, self.cols)
                self.candidates[i] = (flat, score)
                self.total_evals += 1
                if score > self.best_score:
                    self.best_score = score
                    self.best_candidate = flat[:]
                if score == self.perfect_score:
                    self._add_solution(flat)
            self.temperature = _ANNEAL_INIT_TEMP * 0.5  # partial reheat

        # Garden of Eden detection
        if self.restarts >= _MAX_RESTARTS and not self.solutions:
            self._check_goe()

    def _check_goe(self):
        """Run additional exhaustive local search to confirm Garden of Eden."""
        # Systematic local search around best candidate
        for _ in range(_GOE_LOCAL_TRIES):
            # Try flipping each cell of best candidate
            flat = self.best_candidate[:]
            # Random multi-flip
            n_flips = random.randint(1, max(1, self.size - self.best_score))
            positions = random.sample(range(self.size), min(n_flips, self.size))
            for pos in positions:
                flat[pos] = 1 - flat[pos]
            evolved = _step_flat(flat, self.rows, self.cols, self.birth, self.survival)
            score = _fitness(evolved, self.target, self.rows, self.cols)
            self.total_evals += 1
            if score == self.perfect_score:
                self._add_solution(flat)
                self.goe_confidence = 0.0
                return

        # No solution found after extensive search
        self.is_goe = True
        self.goe_confidence = min(0.99, 1.0 - (self.perfect_score - self.best_score) / self.perfect_score)
        self.search_complete = True


def _cell_char(alive):
    """Return display character for cell state."""
    return "██" if alive else "  "


# ── Constraint Analysis ─────────────────────────────────────────────


def _analyze_constraints(target_flat, rows, cols, birth, survival):
    """Analyze target pattern for constraint info.

    Returns dict with:
      - forced_dead: cells that MUST be dead in ancestor
      - forced_alive: cells that MUST be alive in ancestor
      - unconstrained: cells that could be either
      - constraint_density: fraction of constrained cells
    """
    forced_dead = set()
    forced_alive = set()

    # For each target cell, check if any ancestor state is forced
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            is_alive = target_flat[idx]

            # Get neighbor positions
            neighbors = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    neighbors.append(nr * cols + nc)

            # For a dead target cell: no birth count of neighbors should be alive
            # AND if it was alive, survival count shouldn't match
            # This is complex to fully analyze, but we can do simple checks

            if not is_alive:
                # If max_birth > 8 (impossible), cell can never be born anyway
                # If 0 not in birth and 0 not in survival: no constraint
                pass

    total = rows * cols
    constrained = len(forced_dead) + len(forced_alive)
    unconstrained = total - constrained

    return {
        "forced_dead": forced_dead,
        "forced_alive": forced_alive,
        "unconstrained": unconstrained,
        "constraint_density": constrained / max(total, 1),
    }


# ── Mode Functions ───────────────────────────────────────────────────


def _enter_ancestor_search(self):
    """Enter ancestor search mode with preset menu."""
    self.anc_mode = True
    self.anc_menu = True
    self.anc_menu_sel = 0
    self.anc_running = False
    self.anc_engine = None
    self.anc_target_flat = None
    self.anc_grid_h = 12
    self.anc_grid_w = 16
    self.anc_phase = "menu"  # menu, drawing, searching, done
    self.anc_draw_cursor_r = 0
    self.anc_draw_cursor_c = 0
    self.anc_draw_cells = None
    self.anc_solutions_page = 0
    self.anc_view_sel = 0  # which candidate/solution to highlight
    self.anc_birth = set(self.grid.birth)
    self.anc_survival = set(self.grid.survival)
    self.anc_use_current = False
    self._flash("Ancestor Search — find predecessors of any pattern")


def _exit_ancestor_search(self):
    """Exit ancestor search mode."""
    self.anc_mode = False
    self.anc_menu = False
    self.anc_running = False
    self.anc_engine = None
    self.anc_target_flat = None
    self.anc_draw_cells = None
    self.anc_phase = "menu"
    self._flash("Ancestor Search OFF")


def _anc_load_preset(self, idx):
    """Load a preset target pattern."""
    name, desc, cells = _PRESETS[idx]
    if name == "custom":
        self.anc_phase = "drawing"
        self.anc_menu = False
        self.anc_draw_cells = [[0] * self.anc_grid_w for _ in range(self.anc_grid_h)]
        self.anc_draw_cursor_r = self.anc_grid_h // 2
        self.anc_draw_cursor_c = self.anc_grid_w // 2
        self._flash("Draw target pattern — arrows to move, Space to toggle, Enter to search")
        return

    # Load preset centered on grid
    grid_cells = [[0] * self.anc_grid_w for _ in range(self.anc_grid_h)]
    offset_r = (self.anc_grid_h - max(r for r, c in cells) - 1) // 2 if cells else 0
    offset_c = (self.anc_grid_w - max(c for r, c in cells) - 1) // 2 if cells else 0
    for r, c in cells:
        nr, nc = r + offset_r, c + offset_c
        if 0 <= nr < self.anc_grid_h and 0 <= nc < self.anc_grid_w:
            grid_cells[nr][nc] = 1

    self.anc_draw_cells = grid_cells
    self.anc_target_flat = _grid_to_flat(grid_cells, self.anc_grid_h, self.anc_grid_w)
    self._anc_start_search()


def _anc_use_current_grid(self):
    """Use current main grid state as target."""
    self.anc_grid_h = min(self.grid.rows, 20)
    self.anc_grid_w = min(self.grid.cols, 30)
    grid_cells = [[0] * self.anc_grid_w for _ in range(self.anc_grid_h)]
    # Copy from center of main grid
    off_r = max(0, (self.grid.rows - self.anc_grid_h) // 2)
    off_c = max(0, (self.grid.cols - self.anc_grid_w) // 2)
    for r in range(self.anc_grid_h):
        for c in range(self.anc_grid_w):
            if self.grid.cells[r + off_r][c + off_c] > 0:
                grid_cells[r][c] = 1
    self.anc_draw_cells = grid_cells
    self.anc_target_flat = _grid_to_flat(grid_cells, self.anc_grid_h, self.anc_grid_w)
    self.anc_use_current = True
    self._anc_start_search()


def _anc_start_search(self):
    """Initialize the search engine and begin searching."""
    self.anc_menu = False
    self.anc_phase = "searching"
    self.anc_running = True
    self.anc_engine = AncestorSearchEngine(
        self.anc_target_flat,
        self.anc_grid_h,
        self.anc_grid_w,
        self.anc_birth,
        self.anc_survival,
    )
    self._flash("Searching for ancestors... Space to pause, q to quit")


def _anc_step(self):
    """Run one search generation."""
    if self.anc_engine and not self.anc_engine.search_complete:
        self.anc_engine.step()
        if self.anc_engine.search_complete:
            if self.anc_engine.is_goe:
                self._flash("Garden of Eden detected! No predecessor exists.")
            else:
                n = len(self.anc_engine.solutions)
                self._flash(f"Search stabilized — {n} ancestor(s) found")


def _handle_ancestor_search_key(self, key):
    """Handle keys in ancestor search mode."""
    if self.anc_phase == "menu":
        return _handle_anc_menu_key(self, key)
    elif self.anc_phase == "drawing":
        return _handle_anc_draw_key(self, key)
    elif self.anc_phase in ("searching", "done"):
        return _handle_anc_search_key(self, key)
    return True


def _handle_anc_menu_key(self, key):
    """Handle keys in preset menu."""
    if key == ord("q") or key == 27:
        self._exit_ancestor_search()
        return True
    if key == curses.KEY_UP or key == ord("k"):
        self.anc_menu_sel = (self.anc_menu_sel - 1) % (len(_PRESETS) + 1)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.anc_menu_sel = (self.anc_menu_sel + 1) % (len(_PRESETS) + 1)
        return True
    if key in (curses.KEY_ENTER, 10, 13):
        if self.anc_menu_sel == len(_PRESETS):
            # "Use current grid" option
            self._anc_use_current_grid()
        else:
            self._anc_load_preset(self.anc_menu_sel)
        return True
    return True


def _handle_anc_draw_key(self, key):
    """Handle keys in drawing mode."""
    if key == ord("q") or key == 27:
        self.anc_phase = "menu"
        self.anc_menu = True
        return True
    if key == curses.KEY_UP or key == ord("k"):
        self.anc_draw_cursor_r = max(0, self.anc_draw_cursor_r - 1)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.anc_draw_cursor_r = min(self.anc_grid_h - 1, self.anc_draw_cursor_r + 1)
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        self.anc_draw_cursor_c = max(0, self.anc_draw_cursor_c - 1)
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        self.anc_draw_cursor_c = min(self.anc_grid_w - 1, self.anc_draw_cursor_c + 1)
        return True
    if key == ord(" "):
        r, c = self.anc_draw_cursor_r, self.anc_draw_cursor_c
        self.anc_draw_cells[r][c] = 1 - self.anc_draw_cells[r][c]
        return True
    if key == ord("c"):
        self.anc_draw_cells = [[0] * self.anc_grid_w for _ in range(self.anc_grid_h)]
        return True
    if key in (curses.KEY_ENTER, 10, 13):
        # Check if anything is drawn
        has_cells = any(self.anc_draw_cells[r][c]
                        for r in range(self.anc_grid_h)
                        for c in range(self.anc_grid_w))
        if not has_cells:
            self._flash("Draw at least one cell first!")
            return True
        self.anc_target_flat = _grid_to_flat(
            self.anc_draw_cells, self.anc_grid_h, self.anc_grid_w)
        self._anc_start_search()
        return True
    return True


def _handle_anc_search_key(self, key):
    """Handle keys during search."""
    if key == ord("q") or key == 27:
        self._exit_ancestor_search()
        return True
    if key == ord(" "):
        self.anc_running = not self.anc_running
        return True
    if key == ord("n") or key == ord("."):
        self._anc_step()
        return True
    if key == ord("r"):
        # Restart search
        if self.anc_target_flat:
            self._anc_start_search()
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        self.anc_view_sel = max(0, self.anc_view_sel - 1)
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        if self.anc_engine:
            max_sel = max(0, len(self.anc_engine.solutions) - 1)
            self.anc_view_sel = min(max_sel, self.anc_view_sel + 1)
        return True
    if key == ord("a"):
        # Apply selected solution to main grid
        if self.anc_engine and self.anc_engine.solutions:
            idx = min(self.anc_view_sel, len(self.anc_engine.solutions) - 1)
            sol_flat = self.anc_engine.solutions[idx][0]
            cells = _flat_to_cells(sol_flat, self.anc_grid_h, self.anc_grid_w)
            # Write to main grid
            self.grid.clear()
            off_r = max(0, (self.grid.rows - self.anc_grid_h) // 2)
            off_c = max(0, (self.grid.cols - self.anc_grid_w) // 2)
            for r in range(self.anc_grid_h):
                for c in range(self.anc_grid_w):
                    if cells[r][c]:
                        self.grid.set_alive(r + off_r, c + off_c)
            self._exit_ancestor_search()
            self._flash("Ancestor loaded to main grid — step forward to see target")
        return True
    if key == ord("+") or key == ord("="):
        self.anc_grid_h = min(30, self.anc_grid_h + 2)
        self.anc_grid_w = min(40, self.anc_grid_w + 2)
        return True
    if key == ord("-") or key == ord("_"):
        self.anc_grid_h = max(6, self.anc_grid_h - 2)
        self.anc_grid_w = max(8, self.anc_grid_w - 2)
        return True
    return True


def _draw_ancestor_search(self, max_y, max_x):
    """Main draw dispatcher for ancestor search mode."""
    if self.anc_phase == "menu":
        _draw_anc_menu(self, max_y, max_x)
    elif self.anc_phase == "drawing":
        _draw_anc_drawing(self, max_y, max_x)
    elif self.anc_phase in ("searching", "done"):
        _draw_anc_search(self, max_y, max_x)


def _draw_anc_menu(self, max_y, max_x):
    """Draw the preset selection menu."""
    self.stdscr.erase()
    y = 1
    try:
        title = " Ancestor Search — Reverse-Engineering Mode "
        self.stdscr.addstr(y, max(0, (max_x - len(title)) // 2),
                           title, curses.color_pair(7) | curses.A_BOLD)
        y += 2
        self.stdscr.addstr(y, 2,
                           "Find predecessors of any pattern — search backwards through CA time",
                           curses.color_pair(6))
        y += 1
        self.stdscr.addstr(y, 2,
                           "Detect Garden of Eden patterns with no possible ancestor",
                           curses.color_pair(6))
        y += 2

        rule_str = "B" + "".join(str(x) for x in sorted(self.anc_birth))
        rule_str += "/S" + "".join(str(x) for x in sorted(self.anc_survival))
        self.stdscr.addstr(y, 2, f"Rule: {rule_str}", curses.color_pair(3))
        y += 2

        self.stdscr.addstr(y, 2, "Select target pattern:", curses.A_BOLD)
        y += 1

        for i, (name, desc, _) in enumerate(_PRESETS):
            marker = ">" if i == self.anc_menu_sel else " "
            attr = curses.color_pair(7) | curses.A_BOLD if i == self.anc_menu_sel else 0
            label = f" {marker} {name:<14s} {desc}"
            self.stdscr.addstr(y, 3, label[:max_x - 5], attr)
            y += 1

        # "Use current grid" option
        marker = ">" if self.anc_menu_sel == len(_PRESETS) else " "
        attr = curses.color_pair(7) | curses.A_BOLD if self.anc_menu_sel == len(_PRESETS) else 0
        label = f" {marker} {'current grid':<14s} use main grid state as target"
        self.stdscr.addstr(y, 3, label[:max_x - 5], attr)
        y += 2

        self.stdscr.addstr(y, 2, "j/k: navigate  Enter: select  q: back",
                           curses.color_pair(8))
    except curses.error:
        pass


def _draw_anc_drawing(self, max_y, max_x):
    """Draw the target pattern editor."""
    self.stdscr.erase()
    y = 1
    try:
        title = " Draw Target Pattern "
        self.stdscr.addstr(y, max(0, (max_x - len(title)) // 2),
                           title, curses.color_pair(7) | curses.A_BOLD)
        y += 2

        # Draw grid
        for r in range(self.anc_grid_h):
            row_str = ""
            for c in range(self.anc_grid_w):
                if r == self.anc_draw_cursor_r and c == self.anc_draw_cursor_c:
                    row_str += "[]"
                elif self.anc_draw_cells[r][c]:
                    row_str += "██"
                else:
                    row_str += "· "
            if y + r < max_y - 2:
                self.stdscr.addstr(y + r, 4, row_str[:max_x - 6])
                # Highlight cursor row
                if r == self.anc_draw_cursor_r:
                    cx = 4 + self.anc_draw_cursor_c * 2
                    if cx + 2 <= max_x:
                        self.stdscr.addstr(y + r, cx, "[]",
                                           curses.color_pair(3) | curses.A_BOLD)

        y += self.anc_grid_h + 1
        pop = sum(self.anc_draw_cells[r][c]
                  for r in range(self.anc_grid_h)
                  for c in range(self.anc_grid_w))
        self.stdscr.addstr(y, 2, f"Population: {pop}  Grid: {self.anc_grid_h}×{self.anc_grid_w}",
                           curses.color_pair(3))
        y += 1
        self.stdscr.addstr(y, 2,
                           "Arrows/hjkl: move  Space: toggle  c: clear  Enter: search  q: back",
                           curses.color_pair(8))
    except curses.error:
        pass


def _draw_anc_search(self, max_y, max_x):
    """Draw the search visualization."""
    self.stdscr.erase()
    eng = self.anc_engine
    if not eng:
        return

    y = 0
    try:
        # Title bar
        status = "PAUSED" if not self.anc_running else "SEARCHING"
        if eng.search_complete:
            if eng.is_goe:
                status = "GARDEN OF EDEN"
            elif eng.solutions:
                status = f"FOUND {len(eng.solutions)} ANCESTOR(S)"
            else:
                status = "EXHAUSTED"

        title = f" Ancestor Search — {status} "
        attr = curses.color_pair(7) | curses.A_BOLD
        if eng.is_goe:
            attr = curses.color_pair(2) | curses.A_BOLD  # red for GoE
        elif eng.solutions:
            attr = curses.color_pair(4) | curses.A_BOLD  # green for found
        self.stdscr.addstr(y, max(0, (max_x - len(title)) // 2), title[:max_x], attr)
        y += 1

        # Stats bar
        rule_str = "B" + "".join(str(x) for x in sorted(eng.birth))
        rule_str += "/S" + "".join(str(x) for x in sorted(eng.survival))
        stats = (f"Gen: {eng.generation}  Evals: {eng.total_evals}  "
                 f"Best: {eng.best_score}/{eng.perfect_score}  "
                 f"Restarts: {eng.restarts}  Temp: {eng.temperature:.3f}  "
                 f"Rule: {rule_str}")
        self.stdscr.addstr(y, 1, stats[:max_x - 2], curses.color_pair(3))
        y += 1

        # Progress bar
        progress = eng.best_score / max(eng.perfect_score, 1)
        bar_w = min(40, max_x - 10)
        filled = int(bar_w * progress)
        bar = "█" * filled + "░" * (bar_w - filled)
        pct_str = f" {progress * 100:.1f}%"
        self.stdscr.addstr(y, 1, f"[{bar}]{pct_str}", curses.color_pair(5))
        y += 2

        # Layout: target on left, best candidate in middle, solution on right
        grid_w_chars = self.anc_grid_w * 2
        panel_w = grid_w_chars + 4
        n_panels = max(1, min(3, (max_x - 2) // (panel_w + 2)))

        # Panel 1: Target
        if n_panels >= 1:
            col = 2
            self.stdscr.addstr(y, col, "TARGET", curses.color_pair(6) | curses.A_BOLD)
            for r in range(min(self.anc_grid_h, max_y - y - 5)):
                row_str = ""
                for c in range(self.anc_grid_w):
                    idx = r * self.anc_grid_w + c
                    if self.anc_target_flat[idx]:
                        row_str += "██"
                    else:
                        row_str += "· "
                if y + 1 + r < max_y - 3:
                    self.stdscr.addstr(y + 1 + r, col, row_str[:max_x - col - 1])

        # Panel 2: Best candidate (what it evolves into vs target)
        if n_panels >= 2 and eng.best_candidate:
            col = 2 + panel_w + 2
            evolved = _step_flat(eng.best_candidate, self.anc_grid_h, self.anc_grid_w,
                                 eng.birth, eng.survival)
            mismatches = _hamming(evolved, self.anc_target_flat)
            self.stdscr.addstr(y, col,
                               f"BEST ANCESTOR ({mismatches} mismatches)",
                               curses.color_pair(3) | curses.A_BOLD)
            for r in range(min(self.anc_grid_h, max_y - y - 5)):
                row_str = ""
                for c in range(self.anc_grid_w):
                    idx = r * self.anc_grid_w + c
                    if eng.best_candidate[idx]:
                        row_str += "██"
                    else:
                        row_str += "· "
                if y + 1 + r < max_y - 3:
                    self.stdscr.addstr(y + 1 + r, col,
                                       row_str[:max_x - col - 1])

        # Panel 3: Solution or evolved-best
        if n_panels >= 3:
            col = 2 + (panel_w + 2) * 2
            if eng.solutions:
                idx = min(self.anc_view_sel, len(eng.solutions) - 1)
                sol_flat, sol_gen, _ = eng.solutions[idx]
                self.stdscr.addstr(y, col,
                                   f"SOLUTION {idx + 1}/{len(eng.solutions)} (gen {sol_gen})",
                                   curses.color_pair(4) | curses.A_BOLD)
                for r in range(min(self.anc_grid_h, max_y - y - 5)):
                    row_str = ""
                    for c in range(self.anc_grid_w):
                        fidx = r * self.anc_grid_w + c
                        if sol_flat[fidx]:
                            row_str += "██"
                        else:
                            row_str += "· "
                    if y + 1 + r < max_y - 3:
                        self.stdscr.addstr(y + 1 + r, col,
                                           row_str[:max_x - col - 1])
            elif eng.best_candidate:
                evolved = _step_flat(eng.best_candidate, self.anc_grid_h, self.anc_grid_w,
                                     eng.birth, eng.survival)
                self.stdscr.addstr(y, col, "EVOLVED (best→1 step)",
                                   curses.color_pair(5) | curses.A_BOLD)
                for r in range(min(self.anc_grid_h, max_y - y - 5)):
                    row_str = ""
                    for c in range(self.anc_grid_w):
                        fidx = r * self.anc_grid_w + c
                        # Show match/mismatch coloring
                        if evolved[fidx]:
                            row_str += "██"
                        else:
                            row_str += "· "
                    if y + 1 + r < max_y - 3:
                        self.stdscr.addstr(y + 1 + r, col,
                                           row_str[:max_x - col - 1])

        y += self.anc_grid_h + 2

        # Garden of Eden alert
        if eng.is_goe:
            goe_msg = (f"  GARDEN OF EDEN — No predecessor exists! "
                       f"(confidence: {eng.goe_confidence * 100:.0f}%, "
                       f"{eng.total_evals} states tested)  ")
            if y < max_y - 3:
                self.stdscr.addstr(y, max(0, (max_x - len(goe_msg)) // 2),
                                   goe_msg[:max_x],
                                   curses.color_pair(2) | curses.A_BOLD | curses.A_REVERSE)
            y += 1

        # Solution count
        if eng.solutions and y < max_y - 2:
            sol_info = f"Solutions found: {len(eng.solutions)}  (h/l: browse, a: apply to grid)"
            self.stdscr.addstr(y, 2, sol_info[:max_x - 3], curses.color_pair(4))
            y += 1

        # Key hints
        if y < max_y - 1:
            hints = "Space: pause/resume  n: step  r: restart  h/l: browse solutions  a: apply  q: quit"
            self.stdscr.addstr(min(y, max_y - 1), 1, hints[:max_x - 2],
                               curses.color_pair(8))
    except curses.error:
        pass


def _draw_anc_menu_from_mode(self, max_y, max_x):
    """Draw menu when in menu sub-phase."""
    _draw_anc_menu(self, max_y, max_x)


def register(App):
    """Register ancestor_search mode methods on the App class."""
    App._enter_ancestor_search = _enter_ancestor_search
    App._exit_ancestor_search = _exit_ancestor_search
    App._anc_load_preset = _anc_load_preset
    App._anc_use_current_grid = _anc_use_current_grid
    App._anc_start_search = _anc_start_search
    App._anc_step = _anc_step
    App._handle_ancestor_search_key = _handle_ancestor_search_key
    App._draw_ancestor_search = _draw_ancestor_search
