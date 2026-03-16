"""Mode: simulation_archaeology — Reverse-engineer unknown CA rules from artifacts.

A puzzle game where you're presented with a mysterious end-state (or short
animation) and must deduce what rules and initial conditions produced it.
It's a detective game played in rule-space.

The mode generates puzzles by running random (or curated) rules forward,
then presenting the result. Players get clues (symmetry hints, entropy
readings, partial timeline fragments), form hypotheses, test candidate
rules against the evidence, and narrow down the answer.

Difficulty scales from easy (which well-known rule?) to hard (identify
birth/survival sets from a single frozen frame with minimal clues).

Keys (main puzzle view):
    SPC     Start/stop candidate simulation
    Enter   Submit guess (check answer)
    ←/→     Cycle through birth digits to toggle
    Tab     Switch between editing birth vs survival set
    +/-     Adjust initial density guess
    s       Cycle seed style guess
    c       Request a clue (costs points)
    n       New puzzle (skip current)
    d       Cycle difficulty (easy/medium/hard/expert)
    t       Toggle timeline fragment clue
    v       Cycle view mode (artifact / candidate / diff / side-by-side)
    r       Reset candidate to default
    h       Toggle hint overlay
    q       Quit mode
"""
import curses
import math
import random
import time

from life.analytics import (
    PeriodicityDetector,
    shannon_entropy,
    symmetry_score,
    classify_stability,
)
from life.constants import SPEEDS
from life.grid import Grid
from life.rules import rule_string, parse_rule_string, RULE_PRESETS

# ── Constants ────────────────────────────────────────────────────────

_SPARKLINE = "▁▂▃▄▅▆▇█"
_DENSITY_CHARS = ["  ", "░░", "▒▒", "▓▓", "██"]

_DIFFICULTIES = ["easy", "medium", "hard", "expert"]

# How many generations to run the source simulation for puzzle generation
_PUZZLE_GENS = {
    "easy": 40,
    "medium": 80,
    "hard": 120,
    "expert": 200,
}

# How many clues are initially revealed per difficulty
_INITIAL_CLUES = {
    "easy": 4,
    "medium": 2,
    "hard": 1,
    "expert": 0,
}

# Max score per puzzle (before clue penalties)
_MAX_SCORE = 100

# Score penalty per clue requested
_CLUE_COST = 15

# Well-known rules for easy difficulty
_EASY_RULES = [
    {"name": "Conway's Life", "birth": {3}, "survival": {2, 3}},
    {"name": "HighLife", "birth": {3, 6}, "survival": {2, 3}},
    {"name": "Day & Night", "birth": {3, 6, 7, 8}, "survival": {3, 4, 6, 7, 8}},
    {"name": "Seeds", "birth": {2}, "survival": set()},
    {"name": "Diamoeba", "birth": {3, 5, 6, 7, 8}, "survival": {5, 6, 7, 8}},
    {"name": "Morley", "birth": {3, 6, 8}, "survival": {2, 4, 5}},
    {"name": "Anneal", "birth": {4, 6, 7, 8}, "survival": {3, 5, 6, 7, 8}},
    {"name": "2x2", "birth": {3, 6}, "survival": {1, 2, 5}},
]

_SEED_STYLES = ["random", "symmetric", "clustered", "sparse", "central"]

# Clue types available
_CLUE_TYPES = [
    "entropy",          # Shannon entropy of the final state
    "symmetry",         # Symmetry scores (H/V/rot)
    "stability",        # Stability classification
    "population",       # Final population percentage
    "birth_count",      # How many digits in birth set
    "survival_count",   # How many digits in survival set
    "birth_hint",       # Reveal one birth digit
    "survival_hint",    # Reveal one survival digit
    "timeline",         # Show N frames from the timeline
    "density",          # Initial density used
    "periodicity",      # Period if oscillating
]


# ── Sparkline helper ─────────────────────────────────────────────────

def _sparkline(data, width):
    """Render a sparkline string from numerical data."""
    if not data:
        return ""
    lo = min(data)
    hi = max(data)
    span = hi - lo if hi > lo else 1
    n = len(_SPARKLINE) - 1
    out = []
    step = max(1, len(data) // width)
    for i in range(0, min(len(data), width * step), step):
        idx = int((data[i] - lo) / span * n)
        out.append(_SPARKLINE[min(idx, n)])
    return "".join(out)


# ── Puzzle generation ────────────────────────────────────────────────

def _generate_puzzle(self):
    """Generate a new puzzle: run a random rule forward and capture artifact."""
    difficulty = self.archaeo_difficulty
    rows, cols = self.archaeo_sim_rows, self.archaeo_sim_cols

    # Pick a rule based on difficulty
    if difficulty == "easy":
        rule_info = random.choice(_EASY_RULES)
        birth = set(rule_info["birth"])
        survival = set(rule_info["survival"])
    elif difficulty == "medium":
        # Mix of known rules and slight mutations
        if random.random() < 0.5:
            rule_info = random.choice(_EASY_RULES)
            birth = set(rule_info["birth"])
            survival = set(rule_info["survival"])
            # Mutate one digit
            if random.random() < 0.5 and birth:
                d = random.randint(0, 8)
                birth.symmetric_difference_update({d})
                if not birth:
                    birth.add(3)
            else:
                d = random.randint(0, 8)
                survival.symmetric_difference_update({d})
        else:
            birth = {d for d in range(9) if random.random() < 0.25}
            survival = {d for d in range(9) if random.random() < 0.3}
            if not birth:
                birth.add(random.randint(1, 5))
            if not survival:
                survival.add(random.randint(2, 4))
    else:
        # Hard/expert: fully random rules
        birth = {d for d in range(9) if random.random() < 0.3}
        survival = {d for d in range(9) if random.random() < 0.3}
        if not birth:
            birth.add(random.randint(1, 5))
        if not survival:
            survival.add(random.randint(2, 4))

    # Pick seed style and density
    density = random.uniform(0.1, 0.45)
    seed_style = random.choice(_SEED_STYLES)

    # Create source grid and seed it
    src = Grid(rows, cols)
    src.birth = birth
    src.survival = survival
    _seed_grid(src, density, seed_style)

    # Capture initial state
    initial_cells = [[src.cells[r][c] for c in range(cols)] for r in range(rows)]

    # Run forward, capturing timeline snapshots
    gens = _PUZZLE_GENS[difficulty]
    timeline = []
    pop_history = [src.population]
    period_det = PeriodicityDetector()

    snapshot_interval = max(1, gens // 8)
    for g in range(gens):
        src.step()
        pop_history.append(src.population)
        period_det.update(src)
        if (g + 1) % snapshot_interval == 0:
            snap = [[1 if src.cells[r][c] > 0 else 0
                      for c in range(cols)] for r in range(rows)]
            timeline.append(snap)

    # If the sim died completely, retry
    if src.population == 0:
        return _generate_puzzle(self)

    # Capture final state as the artifact
    artifact = [[1 if src.cells[r][c] > 0 else 0
                  for c in range(cols)] for r in range(rows)]

    # Compute analytical clues about the artifact
    entropy = shannon_entropy(src)
    sym = symmetry_score(src)
    stability = classify_stability(pop_history, period_det.period)
    pop_pct = src.population / (rows * cols) * 100

    # Store puzzle data
    self.archaeo_answer_birth = birth
    self.archaeo_answer_survival = survival
    self.archaeo_answer_density = density
    self.archaeo_answer_seed_style = seed_style
    self.archaeo_answer_rule_str = rule_string(birth, survival)
    self.archaeo_artifact = artifact
    self.archaeo_initial_cells = initial_cells
    self.archaeo_timeline = timeline
    self.archaeo_pop_history = pop_history
    self.archaeo_artifact_entropy = entropy
    self.archaeo_artifact_symmetry = sym
    self.archaeo_artifact_stability = stability
    self.archaeo_artifact_pop_pct = pop_pct
    self.archaeo_artifact_period = period_det.period
    self.archaeo_artifact_gens = gens

    # Determine which clues are revealed
    self.archaeo_revealed_clues = set()
    self.archaeo_clues_used = 0

    # Auto-reveal some clues based on difficulty
    initial = _INITIAL_CLUES[difficulty]
    available = list(_CLUE_TYPES)
    random.shuffle(available)
    for i in range(min(initial, len(available))):
        self.archaeo_revealed_clues.add(available[i])

    # Reset candidate guess
    self.archaeo_guess_birth = {3}  # default starting guess
    self.archaeo_guess_survival = {2, 3}
    self.archaeo_guess_density = 0.25
    self.archaeo_guess_seed_style = "random"
    self.archaeo_editing_birth = True
    self.archaeo_edit_cursor = 0

    # Reset candidate simulation
    self.archaeo_candidate_grid = None
    self.archaeo_candidate_running = False
    self.archaeo_candidate_artifact = None

    self.archaeo_puzzle_num += 1
    self.archaeo_solved = False
    self.archaeo_show_answer = False
    self.archaeo_timeline_frame = 0
    self.archaeo_show_timeline = False


def _seed_grid(grid, density, style):
    """Seed a grid with initial conditions based on style."""
    rows, cols = grid.rows, grid.cols
    if style == "random":
        for r in range(rows):
            for c in range(cols):
                if random.random() < density:
                    grid.set_alive(r, c)
    elif style == "symmetric":
        # Horizontally symmetric
        for r in range(rows):
            for c in range(cols // 2 + 1):
                if random.random() < density:
                    grid.set_alive(r, c)
                    grid.set_alive(r, cols - 1 - c)
    elif style == "clustered":
        # Place several random clusters
        n_clusters = random.randint(3, 8)
        for _ in range(n_clusters):
            cr = random.randint(0, rows - 1)
            cc = random.randint(0, cols - 1)
            radius = random.randint(2, min(rows, cols) // 4)
            for r in range(max(0, cr - radius), min(rows, cr + radius)):
                for c in range(max(0, cc - radius), min(cols, cc + radius)):
                    dist = abs(r - cr) + abs(c - cc)
                    if dist <= radius and random.random() < density * 1.5:
                        grid.set_alive(r, c)
    elif style == "sparse":
        for r in range(rows):
            for c in range(cols):
                if random.random() < density * 0.4:
                    grid.set_alive(r, c)
    elif style == "central":
        # Dense center, sparse edges
        mr, mc = rows // 2, cols // 2
        for r in range(rows):
            for c in range(cols):
                dist = math.sqrt((r - mr) ** 2 + (c - mc) ** 2)
                max_dist = math.sqrt(mr ** 2 + mc ** 2)
                local_density = density * max(0, 1 - dist / max_dist)
                if random.random() < local_density:
                    grid.set_alive(r, c)
    else:
        # Fallback: random
        for r in range(rows):
            for c in range(cols):
                if random.random() < density:
                    grid.set_alive(r, c)


def _run_candidate(self):
    """Run the candidate guess forward and capture its artifact."""
    rows, cols = self.archaeo_sim_rows, self.archaeo_sim_cols
    gens = self.archaeo_artifact_gens

    g = Grid(rows, cols)
    g.birth = set(self.archaeo_guess_birth)
    g.survival = set(self.archaeo_guess_survival)
    _seed_grid(g, self.archaeo_guess_density, self.archaeo_guess_seed_style)

    for _ in range(gens):
        g.step()

    self.archaeo_candidate_grid = g
    self.archaeo_candidate_artifact = [
        [1 if g.cells[r][c] > 0 else 0 for c in range(cols)]
        for r in range(rows)
    ]


def _check_answer(self):
    """Score the player's guess against the true answer."""
    birth_match = self.archaeo_guess_birth == self.archaeo_answer_birth
    survival_match = self.archaeo_guess_survival == self.archaeo_answer_survival

    if birth_match and survival_match:
        # Perfect rule match
        clue_penalty = self.archaeo_clues_used * _CLUE_COST
        score = max(10, _MAX_SCORE - clue_penalty)
        self.archaeo_total_score += score
        self.archaeo_solved = True
        self.archaeo_puzzles_solved += 1
        self.archaeo_last_result = f"CORRECT! +{score}pts"
        return True
    else:
        # Partial credit based on digit overlap
        b_overlap = len(self.archaeo_guess_birth & self.archaeo_answer_birth)
        b_total = len(self.archaeo_answer_birth | self.archaeo_guess_birth)
        s_overlap = len(self.archaeo_guess_survival & self.archaeo_answer_survival)
        s_total = len(self.archaeo_answer_survival | self.archaeo_guess_survival)

        b_score = b_overlap / b_total if b_total else 0
        s_score = s_overlap / s_total if s_total else 0
        similarity = (b_score + s_score) / 2

        if similarity > 0.8:
            self.archaeo_last_result = f"Very close! ({similarity:.0%} match)"
        elif similarity > 0.5:
            self.archaeo_last_result = f"Getting warm ({similarity:.0%} match)"
        elif similarity > 0.2:
            self.archaeo_last_result = f"Some overlap ({similarity:.0%} match)"
        else:
            self.archaeo_last_result = f"Not quite ({similarity:.0%} match)"
        return False


def _reveal_clue(self):
    """Reveal the next unrevealed clue."""
    unrevealed = [c for c in _CLUE_TYPES if c not in self.archaeo_revealed_clues]
    if not unrevealed:
        self.archaeo_last_result = "All clues revealed!"
        return
    # Prioritize less-powerful clues first
    clue = unrevealed[0]
    self.archaeo_revealed_clues.add(clue)
    self.archaeo_clues_used += 1
    self.archaeo_last_result = f"Clue revealed: {clue} (-{_CLUE_COST}pts)"


# ── Entry / Exit ─────────────────────────────────────────────────────

def _enter_archaeo_mode(self):
    """Enter Simulation Archaeology mode."""
    self.archaeo_mode = True
    self.archaeo_menu = True
    self._flash("Simulation Archaeology — reverse-engineer unknown CA rules")


def _exit_archaeo_mode(self):
    """Exit Simulation Archaeology mode."""
    self.archaeo_mode = False
    self.archaeo_menu = False
    self.archaeo_running = False
    self.archaeo_candidate_running = False
    self._flash("Simulation Archaeology OFF")


# ── Key handling ─────────────────────────────────────────────────────

def _handle_archaeo_key(self, key):
    """Handle keys in the main puzzle view."""
    if key == ord('q') or key == 27:
        _exit_archaeo_mode(self)
        return True

    if self.archaeo_menu:
        return _handle_archaeo_menu_key(self, key)

    if self.archaeo_show_answer:
        # Any key after showing answer goes to next puzzle
        if key == ord('n') or key == ord(' ') or key == 10:
            _generate_puzzle(self)
        return True

    if key == ord(' '):
        # Run candidate simulation
        _run_candidate(self)
        self.archaeo_last_result = "Candidate simulated"
        return True

    if key == 10:  # Enter
        _run_candidate(self)
        solved = _check_answer(self)
        if solved:
            self.archaeo_show_answer = True
        return True

    if key == ord('\t'):
        # Toggle birth/survival editing
        self.archaeo_editing_birth = not self.archaeo_editing_birth
        self.archaeo_edit_cursor = 0
        return True

    if key == curses.KEY_LEFT:
        self.archaeo_edit_cursor = max(0, self.archaeo_edit_cursor - 1)
        return True

    if key == curses.KEY_RIGHT:
        self.archaeo_edit_cursor = min(8, self.archaeo_edit_cursor + 1)
        return True

    # Toggle digit at cursor
    if ord('0') <= key <= ord('8'):
        digit = key - ord('0')
        if self.archaeo_editing_birth:
            self.archaeo_guess_birth.symmetric_difference_update({digit})
            if not self.archaeo_guess_birth:
                self.archaeo_guess_birth.add(3)
        else:
            self.archaeo_guess_survival.symmetric_difference_update({digit})
        return True

    if key == ord('+') or key == ord('='):
        self.archaeo_guess_density = min(0.8, self.archaeo_guess_density + 0.05)
        return True

    if key == ord('-') or key == ord('_'):
        self.archaeo_guess_density = max(0.02, self.archaeo_guess_density - 0.05)
        return True

    if key == ord('s'):
        # Cycle seed style
        styles = _SEED_STYLES
        idx = styles.index(self.archaeo_guess_seed_style) if self.archaeo_guess_seed_style in styles else 0
        self.archaeo_guess_seed_style = styles[(idx + 1) % len(styles)]
        return True

    if key == ord('c'):
        _reveal_clue(self)
        return True

    if key == ord('n'):
        _generate_puzzle(self)
        return True

    if key == ord('d'):
        # Cycle difficulty
        idx = _DIFFICULTIES.index(self.archaeo_difficulty)
        self.archaeo_difficulty = _DIFFICULTIES[(idx + 1) % len(_DIFFICULTIES)]
        self.archaeo_last_result = f"Difficulty: {self.archaeo_difficulty}"
        return True

    if key == ord('t'):
        self.archaeo_show_timeline = not self.archaeo_show_timeline
        self.archaeo_timeline_frame = 0
        return True

    if key == ord('v'):
        # Cycle view mode
        views = ["artifact", "candidate", "diff", "side_by_side"]
        idx = views.index(self.archaeo_view_mode) if self.archaeo_view_mode in views else 0
        self.archaeo_view_mode = views[(idx + 1) % len(views)]
        return True

    if key == ord('r'):
        # Reset candidate
        self.archaeo_guess_birth = {3}
        self.archaeo_guess_survival = {2, 3}
        self.archaeo_guess_density = 0.25
        self.archaeo_guess_seed_style = "random"
        self.archaeo_candidate_grid = None
        self.archaeo_candidate_artifact = None
        self.archaeo_last_result = "Candidate reset"
        return True

    if key == ord('h'):
        self.archaeo_show_hints = not self.archaeo_show_hints
        return True

    if key == ord('a'):
        # Give up and show answer
        self.archaeo_show_answer = True
        self.archaeo_last_result = f"Answer: {self.archaeo_answer_rule_str}"
        return True

    return False


def _handle_archaeo_menu_key(self, key):
    """Handle keys in the menu/splash screen."""
    if key == ord('q') or key == 27:
        _exit_archaeo_mode(self)
        return True

    if key == curses.KEY_UP:
        self.archaeo_menu_sel = max(0, self.archaeo_menu_sel - 1)
        return True

    if key == curses.KEY_DOWN:
        self.archaeo_menu_sel = min(len(_DIFFICULTIES) - 1, self.archaeo_menu_sel + 1)
        return True

    if key == 10 or key == ord(' '):
        # Start game with selected difficulty
        self.archaeo_difficulty = _DIFFICULTIES[self.archaeo_menu_sel]
        self.archaeo_menu = False
        _generate_puzzle(self)
        return True

    return False


# ── Stepping ─────────────────────────────────────────────────────────

def _archaeo_step(self):
    """Auto-step: animate timeline if showing."""
    if self.archaeo_show_timeline and self.archaeo_timeline:
        self.archaeo_timeline_tick += 1
        if self.archaeo_timeline_tick % 8 == 0:
            self.archaeo_timeline_frame = (
                (self.archaeo_timeline_frame + 1) % len(self.archaeo_timeline)
            )


def _is_archaeo_auto_stepping(self):
    """Return True when mode should auto-step."""
    return self.archaeo_mode and not self.archaeo_menu


# ── Drawing ──────────────────────────────────────────────────────────

def _draw_archaeo(self):
    """Main draw function."""
    self.stdscr.erase()
    try:
        max_y, max_x = self.stdscr.getmaxyx()
    except Exception:
        return

    if self.archaeo_menu:
        _draw_archaeo_splash(self, max_y, max_x)
        return

    try:
        # Title bar
        title = f" ◆ Simulation Archaeology — Puzzle #{self.archaeo_puzzle_num} "
        self.stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)

        # Score display
        score_str = f"Score: {self.archaeo_total_score}  Solved: {self.archaeo_puzzles_solved}"
        if len(score_str) < max_x:
            self.stdscr.addstr(0, max_x - len(score_str) - 2, score_str, curses.A_DIM)

        # Layout: artifact on left, controls on right
        panel_w = min(40, max_x // 2 - 2)
        grid_area_w = max_x - panel_w - 3

        # Draw the artifact / candidate based on view mode
        grid_y = 2
        _draw_grid_view(self, grid_y, 1, grid_area_w, max_y - 4, max_x)

        # Right panel: controls and clues
        px = max_x - panel_w
        _draw_control_panel(self, px, panel_w, max_y, max_x)

        # Status bar
        _draw_status_bar(self, max_y, max_x)

    except curses.error:
        pass


def _draw_archaeo_menu(self):
    """Alias for menu draw."""
    _draw_archaeo(self)


def _draw_archaeo_splash(self, max_y, max_x):
    """Draw the difficulty selection splash screen."""
    try:
        title = "═══ Simulation Archaeology ═══"
        self.stdscr.addstr(2, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)

        subtitle = "Reverse-engineer unknown CA rules from their artifacts"
        self.stdscr.addstr(4, max(0, (max_x - len(subtitle)) // 2), subtitle, curses.A_DIM)

        # Description
        desc_lines = [
            "You'll be shown the end-state of an unknown cellular automaton.",
            "Your mission: deduce the birth/survival rules that created it.",
            "",
            "Use clues like entropy, symmetry, and timeline fragments",
            "to narrow down your hypothesis. Test candidates and compare.",
            "",
            "Select difficulty:",
        ]
        for i, line in enumerate(desc_lines):
            y = 6 + i
            if y < max_y - 6:
                self.stdscr.addstr(y, max(0, (max_x - len(line)) // 2), line)

        # Difficulty options
        diff_descs = {
            "easy": "Well-known rules (Life, HighLife, etc.) + 4 free clues",
            "medium": "Known rules + mutations, 2 free clues",
            "hard": "Random rules, 1 free clue",
            "expert": "Random rules, no free clues, larger grids",
        }
        base_y = 14
        for i, diff in enumerate(_DIFFICULTIES):
            y = base_y + i * 2
            if y >= max_y - 3:
                break
            is_sel = (i == self.archaeo_menu_sel)
            marker = "▸ " if is_sel else "  "
            attr = curses.A_BOLD | curses.A_REVERSE if is_sel else 0
            label = f"{marker}{diff.upper()}: {diff_descs[diff]}"
            self.stdscr.addstr(y, 4, label[:max_x - 6], attr)

        # Stats
        stats_y = base_y + len(_DIFFICULTIES) * 2 + 1
        if stats_y < max_y - 2:
            stats = f"Total score: {self.archaeo_total_score}  Puzzles solved: {self.archaeo_puzzles_solved}"
            self.stdscr.addstr(stats_y, 4, stats, curses.A_DIM)

        # Help
        help_y = max_y - 1
        help_text = " ↑/↓:select  Enter:start  q:quit "
        self.stdscr.addstr(help_y, 0, help_text[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass


def _draw_grid_view(self, start_y, start_x, width, height, max_x):
    """Draw the artifact and/or candidate grid."""
    rows = self.archaeo_sim_rows
    cols = self.archaeo_sim_cols

    # Scale to fit
    scale_r = max(1, rows // max(1, height - 2))
    scale_c = max(1, (cols * 2) // max(1, width - 1))
    disp_rows = min(rows, height - 2)
    disp_cols = min(cols, (width - 1) // 2)

    view = self.archaeo_view_mode

    if view == "side_by_side" and self.archaeo_candidate_artifact:
        half_w = (width - 3) // 2
        disp_cols_half = min(cols, half_w // 2)
        # Artifact on left
        try:
            self.stdscr.addstr(start_y, start_x, "Artifact:", curses.A_BOLD)
        except curses.error:
            pass
        _render_cells(self, self.archaeo_artifact, start_y + 1, start_x,
                      disp_rows, disp_cols_half, scale_r, scale_c, 3)
        # Candidate on right
        cx = start_x + half_w + 2
        try:
            self.stdscr.addstr(start_y, cx, "Candidate:", curses.A_BOLD)
        except curses.error:
            pass
        _render_cells(self, self.archaeo_candidate_artifact, start_y + 1, cx,
                      disp_rows, disp_cols_half, scale_r, scale_c, 2)
        return

    if view == "diff" and self.archaeo_candidate_artifact:
        try:
            self.stdscr.addstr(start_y, start_x, "Difference (red=mismatch):", curses.A_BOLD)
        except curses.error:
            pass
        _render_diff(self, start_y + 1, start_x, disp_rows, disp_cols, scale_r, scale_c)
        return

    if view == "candidate" and self.archaeo_candidate_artifact:
        try:
            self.stdscr.addstr(start_y, start_x, "Candidate result:", curses.A_BOLD)
        except curses.error:
            pass
        cells = self.archaeo_candidate_artifact
    elif self.archaeo_show_timeline and self.archaeo_timeline:
        frame = self.archaeo_timeline_frame % len(self.archaeo_timeline)
        try:
            self.stdscr.addstr(
                start_y, start_x,
                f"Timeline frame {frame + 1}/{len(self.archaeo_timeline)}:", curses.A_BOLD)
        except curses.error:
            pass
        cells = self.archaeo_timeline[frame]
    else:
        try:
            label = "ARTIFACT" if not self.archaeo_solved else "SOLVED!"
            self.stdscr.addstr(start_y, start_x, f"{label}:", curses.A_BOLD)
        except curses.error:
            pass
        cells = self.archaeo_artifact

    if cells:
        _render_cells(self, cells, start_y + 1, start_x,
                      disp_rows, disp_cols, scale_r, scale_c, 3)


def _render_cells(self, cells, y, x, disp_rows, disp_cols, scale_r, scale_c, color_pair):
    """Render a 2D cell array to screen."""
    if not cells:
        return
    rows = len(cells)
    cols = len(cells[0]) if rows else 0
    for dr in range(disp_rows):
        sr = dr * scale_r
        if sr >= rows:
            break
        for dc in range(disp_cols):
            sc = dc * scale_c
            if sc >= cols:
                break
            py = y + dr
            ppx = x + dc * 2
            try:
                if cells[sr][sc]:
                    attr = curses.color_pair(color_pair) if curses.has_colors() else curses.A_BOLD
                    self.stdscr.addstr(py, ppx, "██", attr)
                else:
                    self.stdscr.addstr(py, ppx, "  ")
            except curses.error:
                pass


def _render_diff(self, y, x, disp_rows, disp_cols, scale_r, scale_c):
    """Render diff between artifact and candidate."""
    art = self.archaeo_artifact
    cand = self.archaeo_candidate_artifact
    if not art or not cand:
        return
    rows = len(art)
    cols = len(art[0]) if rows else 0
    for dr in range(disp_rows):
        sr = dr * scale_r
        if sr >= rows:
            break
        for dc in range(disp_cols):
            sc = dc * scale_c
            if sc >= cols:
                break
            py = y + dr
            ppx = x + dc * 2
            try:
                a = art[sr][sc]
                c = cand[sr][sc] if sr < len(cand) and sc < len(cand[0]) else 0
                if a == c:
                    if a:
                        attr = curses.color_pair(3) if curses.has_colors() else curses.A_BOLD
                        self.stdscr.addstr(py, ppx, "██", attr)
                    else:
                        self.stdscr.addstr(py, ppx, "  ")
                else:
                    # Mismatch: red
                    attr = curses.color_pair(1) if curses.has_colors() else curses.A_REVERSE
                    self.stdscr.addstr(py, ppx, "▓▓", attr)
            except curses.error:
                pass


def _draw_control_panel(self, px, panel_w, max_y, max_x):
    """Draw the right-side control panel with clues and guess editor."""
    py = 2
    pw = panel_w - 2

    try:
        # Difficulty & puzzle info
        diff_str = self.archaeo_difficulty.upper()
        self.stdscr.addstr(py, px, f"Difficulty: {diff_str}", curses.A_BOLD)
        py += 1
        self.stdscr.addstr(py, px, f"Target: {self.archaeo_artifact_gens} gens", curses.A_DIM)
        py += 2

        # ── Guess Editor ──
        self.stdscr.addstr(py, px, "── Your Guess ──", curses.A_BOLD)
        py += 1

        # Birth set editor
        b_label = "Birth:    "
        b_active = self.archaeo_editing_birth
        b_attr = curses.A_BOLD if b_active else curses.A_DIM
        self.stdscr.addstr(py, px, b_label, b_attr)
        for d in range(9):
            is_on = d in self.archaeo_guess_birth
            ch = str(d)
            if b_active and d == self.archaeo_edit_cursor:
                da = curses.A_REVERSE | curses.A_BOLD
            elif is_on:
                da = curses.A_BOLD
                if curses.has_colors():
                    da |= curses.color_pair(3)
            else:
                da = curses.A_DIM
            self.stdscr.addstr(py, px + len(b_label) + d * 2, ch, da)
            self.stdscr.addstr(py, px + len(b_label) + d * 2 + 1, " ", curses.A_DIM)
        py += 1

        # Survival set editor
        s_label = "Survival: "
        s_active = not self.archaeo_editing_birth
        s_attr = curses.A_BOLD if s_active else curses.A_DIM
        self.stdscr.addstr(py, px, s_label, s_attr)
        for d in range(9):
            is_on = d in self.archaeo_guess_survival
            ch = str(d)
            if s_active and d == self.archaeo_edit_cursor:
                da = curses.A_REVERSE | curses.A_BOLD
            elif is_on:
                da = curses.A_BOLD
                if curses.has_colors():
                    da |= curses.color_pair(3)
            else:
                da = curses.A_DIM
            self.stdscr.addstr(py, px + len(s_label) + d * 2, ch, da)
            self.stdscr.addstr(py, px + len(s_label) + d * 2 + 1, " ", curses.A_DIM)
        py += 1

        guess_rule = rule_string(self.archaeo_guess_birth, self.archaeo_guess_survival)
        self.stdscr.addstr(py, px, f"Rule: {guess_rule}", curses.A_DIM)
        py += 1

        self.stdscr.addstr(py, px, f"Density: {self.archaeo_guess_density:.0%}")
        py += 1
        self.stdscr.addstr(py, px, f"Seed: {self.archaeo_guess_seed_style}")
        py += 2

        # ── Revealed Clues ──
        self.stdscr.addstr(py, px, "── Clues ──", curses.A_BOLD)
        py += 1

        clue_count = len(self.archaeo_revealed_clues)
        total_clues = len(_CLUE_TYPES)
        self.stdscr.addstr(py, px, f"Revealed: {clue_count}/{total_clues}", curses.A_DIM)
        py += 1

        if "entropy" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, f"Entropy: {self.archaeo_artifact_entropy:.3f}"[:pw])
            py += 1

        if "symmetry" in self.archaeo_revealed_clues:
            sym = self.archaeo_artifact_symmetry
            self.stdscr.addstr(py, px, f"Sym H:{sym['horiz']:.2f} V:{sym['vert']:.2f} R:{sym['rot180']:.2f}"[:pw])
            py += 1

        if "stability" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, f"Stability: {self.archaeo_artifact_stability}"[:pw])
            py += 1

        if "population" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, f"Final pop: {self.archaeo_artifact_pop_pct:.1f}%"[:pw])
            py += 1

        if "birth_count" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, f"Birth digits: {len(self.archaeo_answer_birth)}"[:pw])
            py += 1

        if "survival_count" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, f"Survival digits: {len(self.archaeo_answer_survival)}"[:pw])
            py += 1

        if "birth_hint" in self.archaeo_revealed_clues:
            # Show one random birth digit
            if self.archaeo_answer_birth:
                hint_d = min(self.archaeo_answer_birth)
                self.stdscr.addstr(py, px, f"Birth contains: {hint_d}"[:pw])
                py += 1

        if "survival_hint" in self.archaeo_revealed_clues:
            if self.archaeo_answer_survival:
                hint_d = min(self.archaeo_answer_survival)
                self.stdscr.addstr(py, px, f"Survival contains: {hint_d}"[:pw])
                py += 1

        if "density" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, f"Init density: ~{self.archaeo_answer_density:.0%}"[:pw])
            py += 1

        if "periodicity" in self.archaeo_revealed_clues:
            p = self.archaeo_artifact_period
            if p:
                self.stdscr.addstr(py, px, f"Period: {p}"[:pw])
            else:
                self.stdscr.addstr(py, px, "Period: none detected"[:pw])
            py += 1

        if "timeline" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, "Timeline: [t] to view"[:pw])
            py += 1

        py += 1

        # Population sparkline
        if self.archaeo_pop_history and "population" in self.archaeo_revealed_clues:
            self.stdscr.addstr(py, px, "── Pop History ──", curses.A_BOLD)
            py += 1
            spark = _sparkline(self.archaeo_pop_history, pw)
            self.stdscr.addstr(py, px, spark[:pw], curses.A_DIM)
            py += 2

        # Result message
        if self.archaeo_last_result:
            py = min(py, max_y - 4)
            result_attr = curses.A_BOLD
            if "CORRECT" in self.archaeo_last_result:
                if curses.has_colors():
                    result_attr |= curses.color_pair(3)
            self.stdscr.addstr(py, px, self.archaeo_last_result[:pw], result_attr)
            py += 1

        # Show answer if revealed
        if self.archaeo_show_answer:
            py = min(py + 1, max_y - 3)
            self.stdscr.addstr(py, px, f"Answer: {self.archaeo_answer_rule_str}", curses.A_BOLD)
            py += 1
            self.stdscr.addstr(py, px, "Press n/Enter for next puzzle", curses.A_DIM)

    except curses.error:
        pass


def _draw_status_bar(self, max_y, max_x):
    """Draw the bottom status bar."""
    try:
        bar = (" SPC:simulate Enter:submit c:clue v:view t:timeline "
               "d:diff n:new r:reset a:answer q:quit ")
        self.stdscr.addstr(max_y - 1, 0, bar[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass


# ── State initialization ─────────────────────────────────────────────

def _archaeo_init_state(self):
    """Initialize all state variables for Simulation Archaeology mode."""
    self.archaeo_mode = False
    self.archaeo_menu = False
    self.archaeo_menu_sel = 0
    self.archaeo_running = False
    self.archaeo_difficulty = "easy"

    # Simulation grid size
    self.archaeo_sim_rows = 32
    self.archaeo_sim_cols = 32

    # Puzzle state
    self.archaeo_puzzle_num = 0
    self.archaeo_artifact = None
    self.archaeo_initial_cells = None
    self.archaeo_timeline = []
    self.archaeo_pop_history = []
    self.archaeo_artifact_entropy = 0.0
    self.archaeo_artifact_symmetry = {"horiz": 0, "vert": 0, "rot180": 0}
    self.archaeo_artifact_stability = ""
    self.archaeo_artifact_pop_pct = 0.0
    self.archaeo_artifact_period = None
    self.archaeo_artifact_gens = 40

    # Answer
    self.archaeo_answer_birth = set()
    self.archaeo_answer_survival = set()
    self.archaeo_answer_density = 0.25
    self.archaeo_answer_seed_style = "random"
    self.archaeo_answer_rule_str = ""

    # Clues
    self.archaeo_revealed_clues = set()
    self.archaeo_clues_used = 0

    # Candidate guess
    self.archaeo_guess_birth = {3}
    self.archaeo_guess_survival = {2, 3}
    self.archaeo_guess_density = 0.25
    self.archaeo_guess_seed_style = "random"
    self.archaeo_editing_birth = True
    self.archaeo_edit_cursor = 0
    self.archaeo_candidate_grid = None
    self.archaeo_candidate_running = False
    self.archaeo_candidate_artifact = None

    # View state
    self.archaeo_view_mode = "artifact"  # artifact, candidate, diff, side_by_side
    self.archaeo_show_timeline = False
    self.archaeo_timeline_frame = 0
    self.archaeo_timeline_tick = 0
    self.archaeo_show_hints = True
    self.archaeo_show_answer = False
    self.archaeo_solved = False

    # Scoring
    self.archaeo_total_score = 0
    self.archaeo_puzzles_solved = 0
    self.archaeo_last_result = ""


# ── Registration ─────────────────────────────────────────────────────

def register(App):
    """Register Simulation Archaeology mode methods on the App class."""
    _archaeo_init_state(App)

    App._enter_archaeo_mode = _enter_archaeo_mode
    App._exit_archaeo_mode = _exit_archaeo_mode
    App._handle_archaeo_key = _handle_archaeo_key
    App._handle_archaeo_menu_key = _handle_archaeo_menu_key
    App._draw_archaeo = _draw_archaeo
    App._draw_archaeo_menu = _draw_archaeo_menu
    App._archaeo_step = _archaeo_step
    App._is_archaeo_auto_stepping = _is_archaeo_auto_stepping
