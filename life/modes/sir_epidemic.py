"""Mode: sir — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

SIR_PRESETS = [
    # (name, description, density, n_infected, radius, trans_prob, recovery, mortality, reinfection)
    ("Seasonal Flu", "Moderate spread, no deaths, full grid", 1.0, 3, 1.5, 0.25, 25, 0.0, False),
    ("COVID-like", "High transmission, low mortality", 0.8, 5, 2.0, 0.35, 30, 0.02, False),
    ("Deadly Plague", "High mortality, slow recovery", 0.7, 2, 1.5, 0.4, 40, 0.15, False),
    ("Measles", "Very high transmission, fast recovery", 1.0, 1, 3.0, 0.6, 15, 0.01, False),
    ("Reinfection Wave", "Recovered lose immunity over time", 0.9, 4, 1.5, 0.3, 20, 0.0, True),
    ("Sparse Rural", "Low density, slow spread", 0.3, 2, 2.0, 0.2, 25, 0.05, False),
    ("Superspreader", "Few initial cases, huge radius", 0.8, 1, 5.0, 0.15, 20, 0.01, False),
    ("Fast Burn", "Rapid infection and recovery", 1.0, 10, 2.0, 0.5, 8, 0.0, False),
]

# S=susceptible(green), I=infected(red), R=recovered(blue), D=dead(dim)
SIR_CHARS = {0: "██", 1: "██", 2: "██", 3: "░░"}


def _enter_sir_mode(self):
    """Enter SIR epidemic mode — show preset menu."""
    self.sir_menu = True
    self.sir_menu_sel = 0
    self._flash("Epidemic / SIR — select a scenario")



def _exit_sir_mode(self):
    """Exit SIR epidemic mode."""
    self.sir_mode = False
    self.sir_menu = False
    self.sir_running = False
    self.sir_grid = []
    self.sir_infection_timer = []
    self.sir_counts = []
    self._flash("Epidemic mode OFF")



def _sir_init(self, preset_idx: int):
    """Initialize SIR simulation with the given preset."""
    (name, _desc, density, n_infected, radius,
     trans_prob, recovery, mortality, reinfection) = self.SIR_PRESETS[preset_idx]
    self.sir_preset_name = name
    self.sir_generation = 0
    self.sir_running = False
    self.sir_infection_radius = radius
    self.sir_transmission_prob = trans_prob
    self.sir_recovery_time = recovery
    self.sir_mortality_rate = mortality
    self.sir_initial_infected = n_infected
    self.sir_population_density = density
    self.sir_reinfection = reinfection
    self.sir_counts = []

    max_y, max_x = self.stdscr.getmaxyx()
    self.sir_rows = max(10, max_y - 4)
    self.sir_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.sir_rows, self.sir_cols

    # Initialize grid: -1=empty, 0=S, 1=I, 2=R, 3=dead
    self.sir_grid = [[-1] * cols for _ in range(rows)]
    self.sir_infection_timer = [[0] * cols for _ in range(rows)]

    # Place population
    for r in range(rows):
        for c in range(cols):
            if random.random() < density:
                self.sir_grid[r][c] = 0  # susceptible

    # Seed initial infections randomly among susceptible
    susceptible = [(r, c) for r in range(rows) for c in range(cols)
                   if self.sir_grid[r][c] == 0]
    if susceptible:
        chosen = random.sample(susceptible, min(n_infected, len(susceptible)))
        for r, c in chosen:
            self.sir_grid[r][c] = 1
            self.sir_infection_timer[r][c] = recovery

    self._sir_record_counts()
    self.sir_menu = False
    self.sir_mode = True
    self._flash(f"Epidemic: {name} — Space to start")



def _sir_record_counts(self):
    """Count S, I, R, D populations and append to history."""
    s = i = r_count = d = 0
    for row in self.sir_grid:
        for cell in row:
            if cell == 0:
                s += 1
            elif cell == 1:
                i += 1
            elif cell == 2:
                r_count += 1
            elif cell == 3:
                d += 1
    self.sir_counts.append((s, i, r_count, d))



def _sir_step(self):
    """Advance the SIR simulation by one step."""
    rows, cols = self.sir_rows, self.sir_cols
    grid = self.sir_grid
    timers = self.sir_infection_timer
    radius = self.sir_infection_radius
    trans_p = self.sir_transmission_prob
    mort = self.sir_mortality_rate
    ir = int(math.ceil(radius))

    # Phase 1: Collect new infections
    new_infections: list[tuple[int, int]] = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != 1:
                continue
            # This infected cell tries to spread
            for dr in range(-ir, ir + 1):
                for dc in range(-ir, ir + 1):
                    if dr == 0 and dc == 0:
                        continue
                    dist = math.sqrt(dr * dr + dc * dc)
                    if dist > radius:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
                        # Distance-weighted probability
                        p = trans_p * (1.0 - dist / (radius + 1.0))
                        if random.random() < p:
                            new_infections.append((nr, nc))

    # Phase 2: Apply infections
    for r, c in new_infections:
        if grid[r][c] == 0:
            grid[r][c] = 1
            timers[r][c] = self.sir_recovery_time

    # Phase 3: Update infected (recovery / death)
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != 1:
                continue
            timers[r][c] -= 1
            if timers[r][c] <= 0:
                if mort > 0 and random.random() < mort:
                    grid[r][c] = 3  # dead
                else:
                    grid[r][c] = 2  # recovered

    # Phase 4: Optional reinfection (recovered -> susceptible with low prob)
    if self.sir_reinfection:
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 2 and random.random() < 0.005:
                    grid[r][c] = 0  # lose immunity

    self.sir_generation += 1
    self._sir_record_counts()



def _handle_sir_menu_key(self, key: int) -> bool:
    """Handle input in SIR preset menu."""
    n = len(self.SIR_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.sir_menu_sel = (self.sir_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.sir_menu_sel = (self.sir_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._sir_init(self.sir_menu_sel)
    elif key in (ord("q"), 27):
        self.sir_menu = False
        self._flash("Epidemic cancelled")
    return True



def _handle_sir_key(self, key: int) -> bool:
    """Handle input in active SIR simulation."""
    if key == ord(" "):
        self.sir_running = not self.sir_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.sir_steps_per_frame):
            self._sir_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.SIR_PRESETS)
                    if p[0] == self.sir_preset_name), 0)
        self._sir_init(idx)
        self.sir_running = False
    elif key in (ord("R"), ord("m")):
        self.sir_mode = False
        self.sir_running = False
        self.sir_menu = True
        self.sir_menu_sel = 0
    elif key == ord("t") or key == ord("T"):
        delta = 0.05 if key == ord("t") else -0.05
        self.sir_transmission_prob = max(0.01, min(1.0, self.sir_transmission_prob + delta))
        self._flash(f"Transmission: {self.sir_transmission_prob:.2f}")
    elif key == ord("v") or key == ord("V"):
        delta = 5 if key == ord("v") else -5
        self.sir_recovery_time = max(3, min(100, self.sir_recovery_time + delta))
        self._flash(f"Recovery time: {self.sir_recovery_time}")
    elif key == ord("d") or key == ord("D"):
        delta = 0.02 if key == ord("d") else -0.02
        self.sir_mortality_rate = max(0.0, min(1.0, self.sir_mortality_rate + delta))
        self._flash(f"Mortality: {self.sir_mortality_rate:.2f}")
    elif key == ord("+") or key == ord("="):
        self.sir_steps_per_frame = min(20, self.sir_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.sir_steps_per_frame}")
    elif key == ord("-"):
        self.sir_steps_per_frame = max(1, self.sir_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.sir_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_sir_mode()
    else:
        return True
    return True



def _draw_sir_menu(self, max_y: int, max_x: int):
    """Draw the SIR preset selection menu."""
    self.stdscr.erase()
    title = "── Epidemic / SIR Disease Spread ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.SIR_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<20s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.sir_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_sir(self, max_y: int, max_x: int):
    """Draw the active SIR simulation."""
    self.stdscr.erase()
    grid = self.sir_grid
    rows, cols = self.sir_rows, self.sir_cols
    state = "▶ RUNNING" if self.sir_running else "⏸ PAUSED"
    gen = self.sir_generation

    # Current counts
    if self.sir_counts:
        s, i, r_c, d = self.sir_counts[-1]
    else:
        s = i = r_c = d = 0

    # Title bar
    title = (f" Epidemic: {self.sir_preset_name}  |  day {gen}"
             f"  |  S={s} I={i} R={r_c}"
             + (f" D={d}" if self.sir_mortality_rate > 0 else "")
             + f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    # Draw grid
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            if val == -1:
                continue  # empty
            sx = c * 2
            sy = 1 + r
            if val == 0:
                # Susceptible — green
                cp = 2
                attr = curses.color_pair(cp)
                ch = "██"
            elif val == 1:
                # Infected — red/bold
                cp = 1
                attr = curses.color_pair(cp) | curses.A_BOLD
                ch = "██"
            elif val == 2:
                # Recovered — blue
                cp = 4
                attr = curses.color_pair(cp)
                ch = "██"
            else:
                # Dead — dim
                cp = 6
                attr = curses.color_pair(cp) | curses.A_DIM
                ch = "░░"
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Mini epidemic curve (text-based bar chart) in status area
    status_y = max_y - 3
    if status_y > 1 and self.sir_counts:
        total = s + i + r_c + d
        if total > 0:
            bar_w = min(40, max_x - 30)
            s_w = int(bar_w * s / total)
            i_w = int(bar_w * i / total)
            r_w = int(bar_w * r_c / total)
            d_w = bar_w - s_w - i_w - r_w
            bx = 2
            try:
                self.stdscr.addstr(status_y, bx, "█" * s_w, curses.color_pair(2))
                bx += s_w
                self.stdscr.addstr(status_y, bx, "█" * i_w, curses.color_pair(1) | curses.A_BOLD)
                bx += i_w
                self.stdscr.addstr(status_y, bx, "█" * r_w, curses.color_pair(4))
                bx += r_w
                if d_w > 0:
                    self.stdscr.addstr(status_y, bx, "░" * d_w, curses.color_pair(6) | curses.A_DIM)
                bx += d_w
                legend = f"  S:{s} I:{i} R:{r_c}"
                if d > 0:
                    legend += f" D:{d}"
                self.stdscr.addstr(status_y, bx + 1, legend[:max_x - bx - 2],
                                   curses.color_pair(6))
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Day {gen}  |  trans={self.sir_transmission_prob:.2f}"
                f"  |  radius={self.sir_infection_radius:.1f}"
                f"  |  recovery={self.sir_recovery_time}"
                f"  |  mortality={self.sir_mortality_rate:.2f}"
                f"  |  steps/f={self.sir_steps_per_frame}")
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [t/T]=trans+/- [v/V]=recovery+/- [d]=mortality+ [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

def register(App):
    """Register sir mode methods on the App class."""
    App.SIR_PRESETS = SIR_PRESETS
    App._enter_sir_mode = _enter_sir_mode
    App._exit_sir_mode = _exit_sir_mode
    App._sir_init = _sir_init
    App._sir_record_counts = _sir_record_counts
    App._sir_step = _sir_step
    App._handle_sir_menu_key = _handle_sir_menu_key
    App._handle_sir_key = _handle_sir_key
    App._draw_sir_menu = _draw_sir_menu
    App._draw_sir = _draw_sir

