"""Mode: dnahelix — simulation mode for the life package."""
import curses
import math
import random
import time

DNAHELIX_PRESETS = [
    ("Classic Binary GA", "Evolve a 32-bit genome to match a random target — standard genetic algorithm", "classic"),
    ("OneMax Challenge", "Maximize the number of 1-bits in a 64-bit genome — classic GA benchmark", "onemax"),
    ("Long Strand", "128-bit genome with low mutation — watch slow convergence on a tall helix", "long"),
    ("Hyper-Mutation", "High mutation rate (10%) causes chaotic exploration before convergence", "hyper"),
    ("Minimal Pop", "Tiny population of 10 with a 48-bit target — strong genetic drift", "minimal"),
    ("Royal Road", "64-bit genome with 8-bit schema blocks — fitness jumps when full blocks match", "royal"),
]


def _enter_dnahelix_mode(self):
    """Enter DNA Helix & Genetic Algorithm — show preset menu."""
    self.dnahelix_menu = True
    self.dnahelix_menu_sel = 0




def _exit_dnahelix_mode(self):
    """Exit DNA Helix & Genetic Algorithm."""
    self.dnahelix_mode = False
    self.dnahelix_menu = False
    self.dnahelix_running = False
    self.dnahelix_population = []
    self.dnahelix_target = []
    self.dnahelix_best_genome = []
    self.dnahelix_fitness_history = []
    self.dnahelix_solved = False




def _dnahelix_init(self, preset: str):
    """Initialize DNA helix + GA simulation from preset."""
    import random as _rnd
    rows, cols = self.grid.rows, self.grid.cols
    self.dnahelix_rows = rows
    self.dnahelix_cols = cols
    self.dnahelix_generation = 0
    self.dnahelix_phase = 0.0
    self.dnahelix_solved = False
    self.dnahelix_fitness_history = []

    if preset == "classic":
        self.dnahelix_genome_len = 32
        self.dnahelix_pop_size = 40
        self.dnahelix_mutation_rate = 0.02
        self.dnahelix_crossover_rate = 0.7
    elif preset == "onemax":
        self.dnahelix_genome_len = 64
        self.dnahelix_pop_size = 50
        self.dnahelix_mutation_rate = 0.015
        self.dnahelix_crossover_rate = 0.8
    elif preset == "long":
        self.dnahelix_genome_len = 128
        self.dnahelix_pop_size = 60
        self.dnahelix_mutation_rate = 0.005
        self.dnahelix_crossover_rate = 0.7
    elif preset == "hyper":
        self.dnahelix_genome_len = 32
        self.dnahelix_pop_size = 40
        self.dnahelix_mutation_rate = 0.10
        self.dnahelix_crossover_rate = 0.6
    elif preset == "minimal":
        self.dnahelix_genome_len = 48
        self.dnahelix_pop_size = 10
        self.dnahelix_mutation_rate = 0.03
        self.dnahelix_crossover_rate = 0.7
    elif preset == "royal":
        self.dnahelix_genome_len = 64
        self.dnahelix_pop_size = 50
        self.dnahelix_mutation_rate = 0.02
        self.dnahelix_crossover_rate = 0.75
    else:
        self.dnahelix_genome_len = 32
        self.dnahelix_pop_size = 40
        self.dnahelix_mutation_rate = 0.02
        self.dnahelix_crossover_rate = 0.7

    gl = self.dnahelix_genome_len
    # For onemax the target is all 1s; for royal road it's all 1s too
    if preset == "onemax" or preset == "royal":
        self.dnahelix_target = [1] * gl
    else:
        self.dnahelix_target = [_rnd.randint(0, 1) for _ in range(gl)]

    # Random initial population
    self.dnahelix_population = [
        [_rnd.randint(0, 1) for _ in range(gl)]
        for _ in range(self.dnahelix_pop_size)
    ]

    self.dnahelix_best_genome = self.dnahelix_population[0][:]
    self.dnahelix_best_fitness = 0.0
    self.dnahelix_avg_fitness = 0.0
    self._dnahelix_evaluate()




def _dnahelix_fitness(self, genome: list[int]) -> float:
    """Compute fitness of a genome against the target. Returns 0.0-1.0."""
    gl = self.dnahelix_genome_len
    target = self.dnahelix_target
    preset = self.dnahelix_preset_name

    if preset == "royal":
        # Royal Road: fitness = number of complete 8-bit blocks matching target
        block_size = 8
        n_blocks = gl // block_size
        matched = 0
        for b in range(n_blocks):
            start = b * block_size
            if genome[start:start + block_size] == target[start:start + block_size]:
                matched += 1
        return matched / max(1, n_blocks)
    else:
        # Standard: fraction of bits matching target
        matching = sum(1 for i in range(gl) if genome[i] == target[i])
        return matching / gl




def _dnahelix_evaluate(self):
    """Evaluate fitness of entire population and update best/avg."""
    best_f = 0.0
    best_g = None
    total_f = 0.0
    for genome in self.dnahelix_population:
        f = self._dnahelix_fitness(genome)
        total_f += f
        if f > best_f:
            best_f = f
            best_g = genome
    self.dnahelix_best_fitness = best_f
    self.dnahelix_avg_fitness = total_f / max(1, len(self.dnahelix_population))
    if best_g is not None:
        self.dnahelix_best_genome = best_g[:]
    self.dnahelix_fitness_history.append(best_f)
    if best_f >= 1.0:
        self.dnahelix_solved = True




def _dnahelix_step(self):
    """Run one generation of the genetic algorithm."""
    import random as _rnd
    if self.dnahelix_solved:
        return

    pop = self.dnahelix_population
    pop_size = self.dnahelix_pop_size
    gl = self.dnahelix_genome_len
    mr = self.dnahelix_mutation_rate
    cr = self.dnahelix_crossover_rate

    # Compute fitness for selection
    fits = [self._dnahelix_fitness(g) for g in pop]

    # Tournament selection (size 3)
    def select():
        candidates = _rnd.sample(range(len(pop)), min(3, len(pop)))
        best = max(candidates, key=lambda i: fits[i])
        return pop[best][:]

    new_pop = []
    # Elitism: keep best
    best_idx = max(range(len(pop)), key=lambda i: fits[i])
    new_pop.append(pop[best_idx][:])

    while len(new_pop) < pop_size:
        p1 = select()
        p2 = select()

        # Crossover
        if _rnd.random() < cr:
            cx = _rnd.randint(1, gl - 1)
            child = p1[:cx] + p2[cx:]
        else:
            child = p1[:]

        # Mutation
        for i in range(gl):
            if _rnd.random() < mr:
                child[i] = 1 - child[i]

        new_pop.append(child)

    self.dnahelix_population = new_pop
    self.dnahelix_generation += 1
    self.dnahelix_phase += 0.15
    self._dnahelix_evaluate()




def _handle_dnahelix_menu_key(self, key: int) -> bool:
    """Handle keys in the DNA helix preset menu."""
    n = len(DNAHELIX_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.dnahelix_menu_sel = (self.dnahelix_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.dnahelix_menu_sel = (self.dnahelix_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.dnahelix_menu = False
        self.dnahelix_mode = False
        self._exit_dnahelix_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = DNAHELIX_PRESETS[self.dnahelix_menu_sel]
        self.dnahelix_preset_name = preset[2]
        self._dnahelix_init(preset[2])
        self.dnahelix_menu = False
        self.dnahelix_mode = True
        self.dnahelix_running = True
    else:
        return True
    return True




def _handle_dnahelix_key(self, key: int) -> bool:
    """Handle keys during DNA helix simulation."""
    if key in (27, ord('q')):
        self._exit_dnahelix_mode()
        return True
    elif key == ord(' '):
        self.dnahelix_running = not self.dnahelix_running
    elif key in (ord('n'), ord('.')):
        self._dnahelix_step()
    elif key == ord('r'):
        self._dnahelix_init(self.dnahelix_preset_name)
    elif key in (ord('R'), ord('m')):
        self.dnahelix_menu = True
        self.dnahelix_running = False
    elif key == ord('+'):
        self.dnahelix_speed = min(20, self.dnahelix_speed + 1)
    elif key == ord('-'):
        self.dnahelix_speed = max(1, self.dnahelix_speed - 1)
    elif key == ord('i'):
        self.dnahelix_show_info = not self.dnahelix_show_info
    else:
        return True
    return True




def _draw_dnahelix_menu(self, max_y: int, max_x: int):
    """Draw the DNA helix preset selection menu."""
    self.stdscr.erase()
    title = "── DNA Helix & Genetic Algorithm ──"
    if max_x > len(title) + 2:
        self.stdscr.addstr(1, (max_x - len(title)) // 2, title, curses.A_BOLD)

    subtitle = "Rotating double helix visualizing a live genetic algorithm"
    if max_y > 3 and max_x > len(subtitle) + 2:
        self.stdscr.addstr(2, (max_x - len(subtitle)) // 2, subtitle, curses.A_DIM)

    # ASCII art helix
    art = [
        r"      .  \    /  .      ",
        r"       '. \  / .'       ",
        r"    ──── ·····  ────    ",
        r"       .' /  \ '.      ",
        r"      '  /    \  '     ",
        r"       '. \  / .'      ",
        r"    ──── ·····  ────   ",
        r"       .' /  \ '.     ",
        r"      '  /    \  '    ",
    ]
    art_start = 4
    for i, line in enumerate(art):
        y = art_start + i
        if y >= max_y - len(DNAHELIX_PRESETS) - 6:
            break
        x = (max_x - len(line)) // 2
        if x > 0 and y < max_y:
            try:
                self.stdscr.addstr(y, x, line, curses.A_DIM)
            except curses.error:
                pass

    menu_y = max(art_start + len(art) + 1, max_y // 2 - len(DNAHELIX_PRESETS) // 2)
    header = "Select a GA preset:"
    if menu_y - 1 > 0 and max_x > len(header) + 4:
        try:
            self.stdscr.addstr(menu_y - 1, 3, header, curses.A_BOLD)
        except curses.error:
            pass

    for i, (name, desc, _key) in enumerate(DNAHELIX_PRESETS):
        y = menu_y + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.dnahelix_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.dnahelix_menu_sel else 0
        line = f"{marker}{name:<22s} {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    footer = " ↑↓=select  Enter=start  q=back "
    try:
        self.stdscr.addstr(max_y - 1, 0, footer[:max_x - 1], curses.A_DIM | curses.A_REVERSE)
    except curses.error:
        pass




def _draw_dnahelix(self, max_y: int, max_x: int):
    """Draw the DNA Helix & Genetic Algorithm visualization."""
    import math
    self.stdscr.erase()
    rows = min(max_y, self.dnahelix_rows)
    cols = min(max_x, self.dnahelix_cols)
    if rows < 10 or cols < 30:
        try:
            self.stdscr.addstr(0, 0, "Terminal too small")
        except curses.error:
            pass
        return

    try:
        has_color = curses.has_colors()
    except curses.error:
        has_color = False
    genome = self.dnahelix_best_genome
    gl = self.dnahelix_genome_len
    target = self.dnahelix_target

    # Layout: left side = helix, right side = GA stats & population
    helix_width = min(cols // 2, 40)
    stats_x = helix_width + 2

    # ── Draw rotating double helix ──
    helix_top = 2
    helix_bottom = rows - 3
    helix_h = helix_bottom - helix_top
    if helix_h < 4:
        return

    helix_cx = helix_width // 2
    amplitude = max(3, helix_width // 3)
    phase = self.dnahelix_phase

    base_pair_chars = "ATCG"
    for row_i in range(helix_h):
        y = helix_top + row_i
        t = phase + row_i * 0.3
        # Two strands offset by pi
        x1 = helix_cx + int(amplitude * math.sin(t))
        x2 = helix_cx + int(amplitude * math.sin(t + math.pi))

        # Draw backbone strands
        for sx in (x1, x2):
            if 0 <= y < rows and 0 <= sx < cols - 1:
                try:
                    ch = '(' if sx == x1 else ')'
                    self.stdscr.addstr(y, sx, ch, curses.A_BOLD)
                except curses.error:
                    pass

        # Draw base pair rungs when strands are near-horizontal crossing
        depth = math.cos(t)
        if abs(depth) < 0.5 and abs(x1 - x2) > 2:
            lx, rx = min(x1, x2), max(x1, x2)
            gene_idx = row_i % gl
            bp_char = base_pair_chars[genome[gene_idx] * 2 + target[gene_idx]] if gene_idx < gl else '-'
            for bx in range(lx + 1, rx):
                if 0 <= y < rows and 0 <= bx < cols - 1:
                    try:
                        ch = bp_char if bx == (lx + rx) // 2 else '-'
                        attr = curses.A_DIM
                        if gene_idx < gl and genome[gene_idx] == target[gene_idx]:
                            attr = curses.A_BOLD
                        self.stdscr.addstr(y, bx, ch, attr)
                    except curses.error:
                        pass

    # ── Title ──
    title = "DNA Helix & Genetic Algorithm"
    if self.dnahelix_solved:
        title += " — SOLVED"
    try:
        self.stdscr.addstr(0, (cols - len(title)) // 2, title, curses.A_BOLD)
    except curses.error:
        pass

    # ── GA stats on right side ──
    if stats_x < cols - 10:
        info_lines = [
            f"Generation: {self.dnahelix_generation}",
            f"Genome len: {gl}",
            f"Population: {self.dnahelix_pop_size}",
            f"Best fit:   {self.dnahelix_best_fitness:.3f}",
            f"Avg fit:    {self.dnahelix_avg_fitness:.3f}",
            f"Mutation:   {self.dnahelix_mutation_rate:.3f}",
            f"Crossover:  {self.dnahelix_crossover_rate:.2f}",
        ]
        for il, line in enumerate(info_lines):
            iy = 2 + il
            if iy < rows - 2 and stats_x + len(line) < cols:
                try:
                    self.stdscr.addstr(iy, stats_x, line, curses.A_DIM)
                except curses.error:
                    pass

        # Fitness sparkline
        hist = self.dnahelix_fitness_history[-min(30, cols - stats_x - 2):]
        if hist:
            spark_y = 2 + len(info_lines) + 1
            spark_chars = " ▁▂▃▄▅▆▇█"
            if spark_y < rows - 2:
                spark = ""
                for fv in hist:
                    idx = min(int(fv * (len(spark_chars) - 1)), len(spark_chars) - 1)
                    spark += spark_chars[idx]
                try:
                    self.stdscr.addstr(spark_y, stats_x, f"Fit: {spark}", curses.A_DIM)
                except curses.error:
                    pass

    # ── Status bar ──
    state = "SOLVED" if self.dnahelix_solved else ("▶ RUN" if self.dnahelix_running else "⏸ PAUSED")
    status = f" Gen {self.dnahelix_generation}  {state}  best={self.dnahelix_best_fitness:.3f}"
    status_y = rows - 2
    try:
        self.stdscr.addstr(status_y, 0, status[:cols - 1], curses.A_REVERSE)
        pad = cols - 1 - len(status)
        if pad > 0:
            self.stdscr.addstr(status_y, len(status), " " * pad, curses.A_REVERSE)
    except curses.error:
        pass

    hint = " Space=play n=step +/-=speed i=info r=reset R=menu q=exit"
    if status_y + 1 < rows:
        try:
            self.stdscr.addstr(status_y + 1, 0, hint[:cols - 1], curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register dnahelix mode methods on the App class."""
    App._enter_dnahelix_mode = _enter_dnahelix_mode
    App._exit_dnahelix_mode = _exit_dnahelix_mode
    App._dnahelix_init = _dnahelix_init
    App._dnahelix_fitness = _dnahelix_fitness
    App._dnahelix_evaluate = _dnahelix_evaluate
    App._dnahelix_step = _dnahelix_step
    App._handle_dnahelix_menu_key = _handle_dnahelix_menu_key
    App._handle_dnahelix_key = _handle_dnahelix_key
    App._draw_dnahelix_menu = _draw_dnahelix_menu
    App._draw_dnahelix = _draw_dnahelix

