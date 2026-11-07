"""Self-Modifying Rules CA — a cellular automaton where each cell carries its own birth/survival rule."""
import curses
import math
import random

# ── Genome utilities ──────────────────────────────────────────────
# A genome is a pair of 9-bit ints: (birth_bits, survival_bits).

def _genome_to_bs(genome):
    """Convert a genome to (birth_set, surv_set)."""
    b, s = genome
    return (
        frozenset(i for i in range(9) if b & (1 << i)),
        frozenset(i for i in range(9) if s & (1 << i)),
    )


def _bs_to_genome(birth_set, surv_set):
    """Convert birth and survival sets to a genome."""
    b = 0
    for i in birth_set:
        b |= (1 << i)
    s = 0
    for i in surv_set:
        s |= (1 << i)
    return (b, s)


def _genome_label(genome):
    """Return the B/S label of a genome, such as "B3/S23"."""
    bs, ss = _genome_to_bs(genome)
    b_str = "".join(str(i) for i in sorted(bs)) if bs else ""
    s_str = "".join(str(i) for i in sorted(ss)) if ss else ""
    return f"B{b_str}/S{s_str}"


def _mutate_genome(genome, mutation_rate):
    """Flip each genome bit with the given probability."""
    b, s = genome
    for bit in range(9):
        if random.random() < mutation_rate:
            b ^= (1 << bit)
        if random.random() < mutation_rate:
            s ^= (1 << bit)
    return (b, s)


def _genome_color_hash(genome):
    """Map a genome to a species color index, 0-7."""
    h = (genome[0] * 31 + genome[1] * 17) & 0xFFFFFFFF
    return h % 8


# ── Presets ───────────────────────────────────────────────────────

SMR_PRESETS = [
    ("Life vs HighLife",
     "Two species: B3/S23 (Life) and B36/S23 (HighLife) compete",
     [_bs_to_genome({3}, {2, 3}), _bs_to_genome({3, 6}, {2, 3})],
     0.01, 0.3),
    ("Three Kingdoms",
     "Life, Day&Night, and Seeds in a 3-way battle",
     [_bs_to_genome({3}, {2, 3}), _bs_to_genome({3, 6, 7, 8}, {3, 4, 6, 7, 8}),
      _bs_to_genome({2}, set())],
     0.02, 0.25),
    ("Mutation Storm",
     "Start with Life but high mutation creates rapid speciation",
     [_bs_to_genome({3}, {2, 3})],
     0.08, 0.4),
    ("Sparse Ecology",
     "Low density, low mutation — fragile ecosystems form slowly",
     [_bs_to_genome({3}, {2, 3}), _bs_to_genome({3, 6}, {2, 3})],
     0.005, 0.15),
    ("Cambrian Explosion",
     "Many random seed species with moderate mutation",
     "random_8",
     0.03, 0.35),
    ("Arms Race",
     "Aggressive vs defensive rules with high mutation pressure",
     [_bs_to_genome({2, 3}, {3}), _bs_to_genome({3}, {1, 2, 3, 4, 5})],
     0.04, 0.3),
    ("Single Seed",
     "One species with moderate mutation — watch it diversify",
     [_bs_to_genome({3}, {2, 3})],
     0.03, 0.5),
    ("Blank Canvas",
     "Random cells with random genomes — pure emergence",
     "random_all",
     0.02, 0.3),
]

# ── Color pairs for species ───────────────────────────────────────
# Color pairs 160-175: 8 species colors, each with a young and an old shade.

_SPECIES_256_COLORS = [
    (33, 27),    # blue
    (196, 124),  # red
    (46, 22),    # green
    (226, 178),  # yellow
    (201, 129),  # magenta
    (51, 30),    # cyan
    (208, 130),  # orange
    (255, 245),  # white/gray
]

_SPECIES_8_COLORS = [
    curses.COLOR_BLUE,
    curses.COLOR_RED,
    curses.COLOR_GREEN,
    curses.COLOR_YELLOW,
    curses.COLOR_MAGENTA,
    curses.COLOR_CYAN,
    curses.COLOR_RED,
    curses.COLOR_WHITE,
]


def _init_smr_colors():
    """Initialize the species color pairs."""
    if curses.COLORS >= 256:
        for si in range(8):
            curses.init_pair(160 + si * 2, _SPECIES_256_COLORS[si][0], -1)
            curses.init_pair(160 + si * 2 + 1, _SPECIES_256_COLORS[si][1], -1)
    else:
        for si in range(8):
            curses.init_pair(160 + si * 2, _SPECIES_8_COLORS[si], -1)
            curses.init_pair(160 + si * 2 + 1, _SPECIES_8_COLORS[si], -1)


def _species_attr(genome, age):
    """Return the curses attribute for a cell from its genome and age."""
    ci = _genome_color_hash(genome)
    bright = 0 if age <= 3 else 1
    return curses.color_pair(160 + ci * 2 + bright)


# ── Grid simulation ──────────────────────────────────────────────

def _smr_build_grid(rows, cols, seed_genomes, density):
    """Create the initial grid with seed species placed in radial sectors."""
    # alive[r][c] is a genome tuple, or None for a dead cell.
    alive = [[None] * cols for _ in range(rows)]
    age = [[0] * cols for _ in range(rows)]

    if isinstance(seed_genomes, str) and seed_genomes == "random_8":
        genomes = []
        for _ in range(8):
            b = random.randint(1, 511)
            s = random.randint(0, 511)
            genomes.append((b, s))
        seed_genomes = genomes
    elif isinstance(seed_genomes, str) and seed_genomes == "random_all":
        # Every cell gets a random genome
        for r in range(rows):
            for c in range(cols):
                if random.random() < density:
                    b = random.randint(1, 511)
                    s = random.randint(0, 511)
                    alive[r][c] = (b, s)
                    age[r][c] = 1
        return alive, age

    n_species = len(seed_genomes)
    if n_species == 0:
        return alive, age

    cr, cc = rows // 2, cols // 2
    radius = min(rows, cols) // 3

    for r in range(rows):
        for c in range(cols):
            dr = r - cr
            dc = c - cc
            dist = math.sqrt(dr * dr + dc * dc)
            if dist > radius:
                continue
            if random.random() > density:
                continue
            angle = math.atan2(dr, dc) + math.pi  # 0 to 2*pi
            sector = int(angle / (2 * math.pi) * n_species) % n_species
            alive[r][c] = seed_genomes[sector]
            age[r][c] = 1

    return alive, age


def _smr_step_fn(alive, age, rows, cols, mutation_rate):
    """Advance one generation. Return (new_alive, new_age, stats)."""
    new_alive = [[None] * cols for _ in range(rows)]
    new_age = [[0] * cols for _ in range(rows)]

    species_count = {}
    births = 0
    deaths = 0
    mutations = 0
    total_alive = 0

    for r in range(rows):
        for c in range(cols):
            neighbor_genomes = []
            live_count = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    if alive[nr][nc] is not None:
                        live_count += 1
                        neighbor_genomes.append(alive[nr][nc])

            current = alive[r][c]

            if current is not None:
                # A live cell survives by its own rule.
                _, surv_set = _genome_to_bs(current)
                if live_count in surv_set:
                    new_alive[r][c] = current
                    new_age[r][c] = age[r][c] + 1
                    total_alive += 1
                    g_key = current
                    species_count[g_key] = species_count.get(g_key, 0) + 1
                else:
                    deaths += 1
            else:
                # A dead cell is born by the majority rule of its neighbors.
                if neighbor_genomes:
                    majority = _majority_genome(neighbor_genomes)
                    birth_set, _ = _genome_to_bs(majority)
                    if live_count in birth_set:
                        child = majority
                        if random.random() < mutation_rate:
                            child = _mutate_genome(child, 0.15)
                            if child != majority:
                                mutations += 1
                        new_alive[r][c] = child
                        new_age[r][c] = 1
                        births += 1
                        total_alive += 1
                        g_key = child
                        species_count[g_key] = species_count.get(g_key, 0) + 1

    return new_alive, new_age, {
        "species_count": species_count,
        "births": births,
        "deaths": deaths,
        "mutations": mutations,
        "total_alive": total_alive,
    }


def _majority_genome(genomes):
    """Return the most common genome in the list, with random tiebreak."""
    counts = {}
    for g in genomes:
        counts[g] = counts.get(g, 0) + 1
    max_count = max(counts.values())
    winners = [g for g, c in counts.items() if c == max_count]
    return random.choice(winners)


# ── Mode functions ────────────────────────────────────────────────

def _enter_smr_mode(self):
    """Show the preset menu."""
    self.smr_menu = True
    self.smr_menu_sel = 0
    self._flash("Self-Modifying Rules — select a preset")


def _exit_smr_mode(self):
    """Leave Self-Modifying Rules mode."""
    self.smr_mode = False
    self.smr_menu = False
    self.smr_running = False
    self._flash("Self-Modifying Rules mode OFF")


def _smr_reset_stats(self):
    """Clear the history and recount the species on the current grid."""
    species = {}
    total = 0
    for row in self.smr_alive:
        for g in row:
            if g is not None:
                species[g] = species.get(g, 0) + 1
                total += 1
    self.smr_stats = {
        "species_count": species,
        "births": 0,
        "deaths": 0,
        "mutations": 0,
        "total_alive": total,
    }
    self.smr_total_mutations = 0
    self.smr_peak_species = len(species)
    self.smr_species_history = []
    self.smr_pop_history = []


def _smr_init(self, preset_idx):
    """Start the simulation from a preset."""
    _init_smr_colors()

    name, desc, seed_genomes, mutation_rate, density = SMR_PRESETS[preset_idx]

    max_y, max_x = self.stdscr.getmaxyx()
    self.smr_rows = max(10, max_y - 4)
    self.smr_cols = max(10, (max_x - 30) // 2)

    self.smr_alive, self.smr_age = _smr_build_grid(
        self.smr_rows, self.smr_cols, seed_genomes, density
    )

    self.smr_generation = 0
    self.smr_mutation_rate = mutation_rate
    self.smr_density = density
    self.smr_running = False
    _smr_reset_stats(self)
    self.smr_speed_mult = 1
    self.smr_preset_name = name

    self.smr_menu = False
    self.smr_mode = True


def _smr_step(self):
    """Advance the simulation by one generation."""
    self.smr_alive, self.smr_age, self.smr_stats = _smr_step_fn(
        self.smr_alive, self.smr_age,
        self.smr_rows, self.smr_cols,
        self.smr_mutation_rate,
    )
    self.smr_generation += 1
    self.smr_total_mutations += self.smr_stats["mutations"]
    n_species = len(self.smr_stats["species_count"])
    if n_species > self.smr_peak_species:
        self.smr_peak_species = n_species
    self.smr_species_history.append(n_species)
    if len(self.smr_species_history) > 200:
        self.smr_species_history.pop(0)
    self.smr_pop_history.append(self.smr_stats["total_alive"])
    if len(self.smr_pop_history) > 200:
        self.smr_pop_history.pop(0)


def _smr_randomize(self):
    """Replace the grid with random species at the current density."""
    genomes = []
    for _ in range(random.randint(2, 6)):
        b = random.randint(1, 511)
        s = random.randint(0, 511)
        genomes.append((b, s))
    self.smr_alive, self.smr_age = _smr_build_grid(
        self.smr_rows, self.smr_cols, genomes, self.smr_density
    )
    self.smr_generation = 0
    _smr_reset_stats(self)


def _handle_smr_menu_key(self, key):
    """Handle keys in the preset menu."""
    n = len(SMR_PRESETS)
    if key == ord("q") or key == 27:
        self.smr_menu = False
        self._flash("Self-Modifying Rules cancelled")
        return True
    if key == ord("j") or key == curses.KEY_DOWN:
        self.smr_menu_sel = (self.smr_menu_sel + 1) % n
        return True
    if key == ord("k") or key == curses.KEY_UP:
        self.smr_menu_sel = (self.smr_menu_sel - 1) % n
        return True
    if key in (ord("\n"), ord(" "), curses.KEY_ENTER, 10, 13):
        _smr_init(self, self.smr_menu_sel)
        return True
    return True


def _handle_smr_key(self, key):
    """Handle keys while the simulation runs."""
    if key == ord("q") or key == 27:
        _exit_smr_mode(self)
        return True
    if key == ord(" "):
        self.smr_running = not self.smr_running
        self._flash("Running" if self.smr_running else "Paused")
        return True
    if key == ord("n"):
        _smr_step(self)
        return True
    if key == ord("r"):
        _smr_randomize(self)
        self._flash("Randomized")
        return True
    if key == ord("+") or key == ord("="):
        self.smr_mutation_rate = min(0.5, self.smr_mutation_rate + 0.005)
        self._flash(f"Mutation rate: {self.smr_mutation_rate:.3f}")
        return True
    if key == ord("-") or key == ord("_"):
        self.smr_mutation_rate = max(0.0, self.smr_mutation_rate - 0.005)
        self._flash(f"Mutation rate: {self.smr_mutation_rate:.3f}")
        return True
    if key == ord("]"):
        self.smr_speed_mult = min(20, self.smr_speed_mult + 1)
        self._flash(f"Steps/frame: {self.smr_speed_mult}")
        return True
    if key == ord("["):
        self.smr_speed_mult = max(1, self.smr_speed_mult - 1)
        self._flash(f"Steps/frame: {self.smr_speed_mult}")
        return True
    return True


def _draw_smr_menu(self, max_y, max_x):
    """Draw the preset menu."""
    self.stdscr.erase()
    y = 1
    try:
        title = "═══ Self-Modifying Rules CA ═══"
        self.stdscr.addstr(y, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD)
        y += 2
        subtitle = "Each cell carries its own rule DNA that mutates and competes"
        self.stdscr.addstr(y, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.A_DIM)
        y += 2

        for i, (name, desc, _, mrate, dens) in enumerate(SMR_PRESETS):
            if y >= max_y - 3:
                break
            prefix = "▸ " if i == self.smr_menu_sel else "  "
            attr = curses.A_BOLD | curses.A_REVERSE if i == self.smr_menu_sel else 0
            line = f"{prefix}{name}"
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            y += 1
            if i == self.smr_menu_sel and y < max_y - 3:
                detail = f"  {desc}"
                self.stdscr.addstr(y, 2, detail[:max_x - 4], curses.A_DIM)
                y += 1
                params = f"  Mutation: {mrate:.3f}  Density: {dens:.0%}"
                self.stdscr.addstr(y, 2, params[:max_x - 4], curses.A_DIM)
                y += 1

        y = max_y - 2
        if y > 0:
            help_text = "↑/↓ or j/k: navigate  Enter: select  q: cancel"
            self.stdscr.addstr(y, 2, help_text[:max_x - 4], curses.A_DIM)
    except curses.error:
        pass


def _draw_smr(self, max_y, max_x):
    """Draw the grid, info panel and status bar."""
    self.stdscr.erase()

    stats = self.smr_stats
    species = stats.get("species_count", {})
    n_species = len(species)

    grid_x_start = 0
    grid_y_start = 0
    panel_x = max_x - 28 if max_x > 60 else max_x

    for r in range(min(self.smr_rows, max_y - 1)):
        for c in range(min(self.smr_cols, panel_x // 2)):
            g = self.smr_alive[r][c]
            sx = grid_x_start + c * 2
            sy = grid_y_start + r
            if sy >= max_y - 1 or sx + 1 >= max_x:
                continue
            try:
                if g is not None:
                    attr = _species_attr(g, self.smr_age[r][c])
                    self.stdscr.addstr(sy, sx, "██", attr)
            except curses.error:
                pass

    if max_x > 60:
        px = max_x - 27
        py = 1
        try:
            self.stdscr.addstr(py, px, "Self-Modifying Rules", curses.A_BOLD)
            py += 1
            self.stdscr.addstr(py, px, f"Preset: {self.smr_preset_name}"[:26], curses.A_DIM)
            py += 2

            self.stdscr.addstr(py, px, f"Gen: {self.smr_generation}", curses.A_BOLD)
            py += 1
            self.stdscr.addstr(py, px, f"Alive: {stats.get('total_alive', 0)}")
            py += 1
            self.stdscr.addstr(py, px, f"Species: {n_species}")
            py += 1
            self.stdscr.addstr(py, px, f"Peak species: {self.smr_peak_species}")
            py += 1
            self.stdscr.addstr(py, px, f"Births: {stats.get('births', 0)}")
            py += 1
            self.stdscr.addstr(py, px, f"Deaths: {stats.get('deaths', 0)}")
            py += 1
            self.stdscr.addstr(py, px, f"Mutations: {self.smr_total_mutations}")
            py += 1
            self.stdscr.addstr(py, px, f"Mut rate: {self.smr_mutation_rate:.3f}")
            py += 1
            self.stdscr.addstr(py, px, f"Steps/frame: {self.smr_speed_mult}")
            py += 2

            # Top species
            self.stdscr.addstr(py, px, "── Top Species ──", curses.A_BOLD)
            py += 1
            if species:
                top = sorted(species.items(), key=lambda x: -x[1])[:8]
                for genome, count in top:
                    if py >= max_y - 4:
                        break
                    label = _genome_label(genome)
                    ci = _genome_color_hash(genome)
                    attr = curses.color_pair(160 + ci * 2)
                    line = f"██ {label}: {count}"
                    self.stdscr.addstr(py, px, line[:26], attr)
                    py += 1

            # Species diversity sparkline
            py += 1
            if py < max_y - 4 and self.smr_species_history:
                self.stdscr.addstr(py, px, "── Diversity ──", curses.A_BOLD)
                py += 1
                _draw_sparkline(self.stdscr, py, px, 24, self.smr_species_history, max_y)
                py += 2

            # Population sparkline
            if py < max_y - 4 and self.smr_pop_history:
                self.stdscr.addstr(py, px, "── Population ──", curses.A_BOLD)
                py += 1
                _draw_sparkline(self.stdscr, py, px, 24, self.smr_pop_history, max_y)
                py += 2

        except curses.error:
            pass

    # Status bar
    try:
        status_y = max_y - 1
        state = "▶ RUNNING" if self.smr_running else "⏸ PAUSED"
        bar = f" {state} │ SPC:play/pause n:step r:rand +/-:mutation [/]:speed q:quit "
        self.stdscr.addstr(status_y, 0, bar[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass


def _draw_sparkline(stdscr, y, x, width, data, max_y):
    """Draw a sparkline of the last `width` values."""
    if y >= max_y - 1:
        return
    sparks = "▁▂▃▄▅▆▇█"
    segment = data[-width:]
    if not segment:
        return
    mn = min(segment)
    mx = max(segment)
    rng = mx - mn if mx > mn else 1
    line = ""
    for v in segment:
        idx = int((v - mn) / rng * (len(sparks) - 1))
        idx = max(0, min(len(sparks) - 1, idx))
        line += sparks[idx]
    try:
        stdscr.addstr(y, x, line[:width], curses.A_DIM)
    except curses.error:
        pass


# ── Registration ──────────────────────────────────────────────────

def register(App):
    """Register Self-Modifying Rules mode methods on the App class."""
    App._enter_smr_mode = _enter_smr_mode
    App._exit_smr_mode = _exit_smr_mode
    App._smr_init = _smr_init
    App._smr_step = _smr_step
    App._smr_randomize = _smr_randomize
    App._handle_smr_menu_key = _handle_smr_menu_key
    App._handle_smr_key = _handle_smr_key
    App._draw_smr_menu = _draw_smr_menu
    App._draw_smr = _draw_smr
