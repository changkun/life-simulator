"""Mode: rps — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_rps_mode(self):
    """Enter Spatial Rock-Paper-Scissors mode — show preset menu."""
    self.rps_menu = True
    self.rps_menu_sel = 0
    self._flash("Rock-Paper-Scissors — select a scenario")



def _exit_rps_mode(self):
    """Exit Spatial Rock-Paper-Scissors mode."""
    self.rps_mode = False
    self.rps_menu = False
    self.rps_running = False
    self.rps_grid = []
    self._flash("Rock-Paper-Scissors OFF")



def _rps_init(self, preset_idx: int):
    """Initialize RPS simulation with selected preset."""
    name, _desc, num_species, swap_rate, layout = self.RPS_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max_y - 2
    cols = (max_x - 1) // 2
    if rows < 5 or cols < 5:
        return

    self.rps_rows = rows
    self.rps_cols = cols
    self.rps_num_species = num_species
    self.rps_swap_rate = swap_rate
    self.rps_preset_name = name
    self.rps_generation = 0

    if layout == "blocks":
        # Vertical stripes of each species
        self.rps_grid = [[0] * cols for _ in range(rows)]
        stripe_w = cols // num_species
        for r in range(rows):
            for c in range(cols):
                self.rps_grid[r][c] = min(c // stripe_w, num_species - 1)
    elif layout == "seeds":
        # Fill with species 0, place small circular clusters of 1 and 2
        self.rps_grid = [[0] * cols for _ in range(rows)]
        num_clusters = max(3, (rows * cols) // 400)
        for _ in range(num_clusters):
            species = random.randint(1, num_species - 1)
            cr = random.randint(2, rows - 3)
            cc = random.randint(2, cols - 3)
            radius = random.randint(2, 4)
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if dr * dr + dc * dc <= radius * radius:
                        nr = (cr + dr) % rows
                        nc = (cc + dc) % cols
                        self.rps_grid[nr][nc] = species
    else:
        # Random uniform
        self.rps_grid = [
            [random.randint(0, num_species - 1) for _ in range(cols)]
            for _ in range(rows)
        ]

    self.rps_menu = False
    self.rps_mode = True
    self.rps_running = True



def _rps_step(self):
    """Advance RPS simulation by one generation.

    Each cell picks a random neighbor. If the cell beats the neighbor
    (cyclic dominance: i beats (i-1) mod N), nothing happens.
    If the neighbor beats the cell, the cell is replaced by the
    neighbor's species.
    """
    rows = self.rps_rows
    cols = self.rps_cols
    grid = self.rps_grid
    ns = self.rps_num_species
    # Number of interactions per step — proportional to grid size
    interactions = int(rows * cols * self.rps_swap_rate)

    for _ in range(interactions):
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        # Pick a random von Neumann neighbor (4-connected, wrapping)
        direction = random.randint(0, 3)
        if direction == 0:
            nr = (r - 1) % rows
            nc = c
        elif direction == 1:
            nr = (r + 1) % rows
            nc = c
        elif direction == 2:
            nr = r
            nc = (c - 1) % cols
        else:
            nr = r
            nc = (c + 1) % cols

        attacker = grid[nr][nc]
        defender = grid[r][c]
        # Cyclic dominance: attacker beats defender if
        # defender == (attacker - 1) % ns
        if defender == (attacker - 1) % ns:
            grid[r][c] = attacker

    self.rps_generation += 1



def _rps_counts(self) -> list[int]:
    """Count population of each species."""
    counts = [0] * self.rps_num_species
    for row in self.rps_grid:
        for cell in row:
            counts[cell] += 1
    return counts



def _handle_rps_menu_key(self, key: int) -> bool:
    """Handle keys in RPS preset menu."""
    if key == curses.KEY_UP:
        self.rps_menu_sel = (self.rps_menu_sel - 1) % len(self.RPS_PRESETS)
    elif key == curses.KEY_DOWN:
        self.rps_menu_sel = (self.rps_menu_sel + 1) % len(self.RPS_PRESETS)
    elif key in (curses.KEY_ENTER, 10, 13):
        self._rps_init(self.rps_menu_sel)
    elif key == 27 or key == ord("q") or key == ord("&"):
        self.rps_menu = False
        self._flash("Rock-Paper-Scissors cancelled")
    else:
        return True
    return True



def _handle_rps_key(self, key: int) -> bool:
    """Handle keys during RPS simulation."""
    if key == ord(" "):
        self.rps_running = not self.rps_running
    elif key == ord("n"):
        self._rps_step()
    elif key == ord("+") or key == ord("="):
        self.rps_steps_per_frame = min(20, self.rps_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.rps_steps_per_frame}")
    elif key == ord("-"):
        self.rps_steps_per_frame = max(1, self.rps_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.rps_steps_per_frame}")
    elif key == ord("r"):
        self._rps_init(self.rps_menu_sel)
    elif key == ord("R"):
        self.rps_mode = False
        self.rps_menu = True
        self.rps_running = False
    elif key == ord("q") or key == ord("&"):
        self._exit_rps_mode()
    elif key == ord("s"):
        # Adjust swap rate up
        self.rps_swap_rate = min(1.0, self.rps_swap_rate + 0.05)
        self._flash(f"Swap rate: {self.rps_swap_rate:.2f}")
    elif key == ord("S"):
        # Adjust swap rate down
        self.rps_swap_rate = max(0.05, self.rps_swap_rate - 0.05)
        self._flash(f"Swap rate: {self.rps_swap_rate:.2f}")
    else:
        return True
    return True



def _draw_rps_menu(self, max_y: int, max_x: int):
    """Draw the RPS preset selection menu."""
    self.stdscr.erase()
    title = "── Rock-Paper-Scissors ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.RPS_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.rps_menu_sel else "  "
        attr = curses.A_BOLD if i == self.rps_menu_sel else 0
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], curses.color_pair(7) | attr)
        except curses.error:
            pass
        if y + 1 < max_y - 1:
            try:
                self.stdscr.addstr(y + 1, 6, desc[:max_x - 7], curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    # Footer
    foot_y = max_y - 1
    if foot_y > 0:
        foot = " [↑/↓]=select  [Enter]=start  [q]=cancel"
        try:
            self.stdscr.addstr(foot_y, 0, foot[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_rps(self, max_y: int, max_x: int):
    """Draw the active RPS simulation."""
    self.stdscr.erase()
    rows = self.rps_rows
    cols = self.rps_cols
    grid = self.rps_grid
    gen = self.rps_generation
    ns = self.rps_num_species

    counts = self._rps_counts()
    total = sum(counts)

    # Species names and symbols
    if ns == 5:
        species_names = ["Rock", "Paper", "Scissors", "Lizard", "Spock"]
        species_sym = ["✊", "✋", "✌", "🦎", "🖖"]
    else:
        species_names = ["Rock", "Paper", "Scissors"]
        species_sym = ["✊", "✋", "✌"]

    # Title bar
    status = "RUNNING" if self.rps_running else "PAUSED"
    pcts = "  ".join(f"{species_names[i]}: {counts[i]*100//max(total,1)}%" for i in range(ns))
    title = f" RPS: {self.rps_preset_name}  |  gen {gen}  |  {status}  |  {pcts}"
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 2)
    view_cols = min(cols, (max_x - 1) // 2)

    # Color pairs for species:
    # 0=Rock → color_pair 5 (red)
    # 1=Paper → color_pair 2 (green)
    # 2=Scissors → color_pair 4 (blue/cyan)
    # 3=Lizard → color_pair 3 (yellow)
    # 4=Spock → color_pair 1 (white/magenta)
    species_colors = [5, 2, 4, 3, 1]

    for r in range(view_rows):
        for c in range(view_cols):
            sy = r + 1
            sx = c * 2
            species = grid[r][c]
            cp = species_colors[species % len(species_colors)]
            ch = "██"
            try:
                self.stdscr.addstr(sy, sx, ch, curses.color_pair(cp))
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [s/S]=rate+/- [+/-]=steps/f [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  2D Wave Equation — Mode !
# ══════════════════════════════════════════════════════════════════════

WAVE_PRESETS = [
    # (name, description, c, damping, boundary, init_type)
    # c = wave speed (Courant number, keep <= 0.5 for stability)
    # damping = per-step damping (1.0 = no damping)
    # boundary = reflect | absorb | wrap
    # init_type = center_drop | double_slit | corner_pulse | random_drops | ring | cross
    ("Center Drop", "Single drop in center — watch circular ripples", 0.45, 0.999, "reflect", "center_drop"),
    ("Reflecting Pool", "Drop with reflective walls — standing waves form", 0.40, 0.9995, "reflect", "center_drop"),
    ("Absorbing Edges", "Drop with absorbing boundaries — no reflections", 0.45, 0.999, "absorb", "center_drop"),
    ("Wraparound Torus", "Drop on toroidal surface — waves wrap around", 0.40, 0.999, "wrap", "center_drop"),
    ("Double Slit", "Plane wave through two slits — diffraction pattern", 0.35, 0.9995, "absorb", "double_slit"),
    ("Corner Pulse", "Pulse from corner — diagonal wave front", 0.45, 0.999, "reflect", "corner_pulse"),
    ("Rain Drops", "Random drops — chaotic interference patterns", 0.40, 0.999, "reflect", "random_drops"),
    ("Ring Wave", "Expanding ring — inward and outward propagation", 0.40, 0.999, "reflect", "ring"),
    ("Cross Pattern", "Cross-shaped initial disturbance", 0.40, 0.999, "reflect", "cross"),
    ("Undamped Pool", "No damping — energy conserved forever", 0.40, 1.0, "reflect", "center_drop"),
    ("Slow Ripple", "Very slow wave speed — watch propagation clearly", 0.20, 0.999, "reflect", "center_drop"),
    ("Fast Chaos", "Fast waves, random drops — turbulent surface", 0.48, 0.998, "wrap", "random_drops"),
]




def register(App):
    """Register rps mode methods on the App class."""
    App._enter_rps_mode = _enter_rps_mode
    App._exit_rps_mode = _exit_rps_mode
    App._rps_init = _rps_init
    App._rps_step = _rps_step
    App._rps_counts = _rps_counts
    App._handle_rps_menu_key = _handle_rps_menu_key
    App._handle_rps_key = _handle_rps_key
    App._draw_rps_menu = _draw_rps_menu
    App._draw_rps = _draw_rps

