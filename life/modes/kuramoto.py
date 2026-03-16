"""Mode: kuramoto — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_kuramoto_mode(self):
    """Enter Kuramoto Coupled Oscillators mode — show preset menu."""
    self.kuramoto_menu = True
    self.kuramoto_menu_sel = 0
    self._flash("Kuramoto Coupled Oscillators — select a scenario")



def _exit_kuramoto_mode(self):
    """Exit Kuramoto mode."""
    self.kuramoto_mode = False
    self.kuramoto_menu = False
    self.kuramoto_running = False
    self.kuramoto_phases = []
    self.kuramoto_nat_freq = []
    self._flash("Kuramoto Oscillators mode OFF")



def _kuramoto_init(self, preset_idx: int):
    """Initialize the Kuramoto simulation with the given preset."""
    name, _desc, coupling, freq_spread, dt, noise, init_type = self.KURAMOTO_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.kuramoto_rows = rows
    self.kuramoto_cols = cols
    self.kuramoto_coupling = coupling
    self.kuramoto_freq_spread = freq_spread
    self.kuramoto_dt = dt
    self.kuramoto_noise = noise
    self.kuramoto_preset_name = name
    self.kuramoto_generation = 0
    self.kuramoto_steps_per_frame = 1

    TWO_PI = 2.0 * math.pi

    # Initialize natural frequencies (drawn from normal distribution centered at 0)
    self.kuramoto_nat_freq = [
        [random.gauss(0.0, freq_spread) for _ in range(cols)]
        for _ in range(rows)
    ]

    # Initialize phases based on init_type
    if init_type == "gradient":
        # Linear phase gradient across the grid
        self.kuramoto_phases = [
            [(c / max(cols - 1, 1)) * TWO_PI for c in range(cols)]
            for r in range(rows)
        ]
    elif init_type == "spiral":
        # Spiral phase pattern around center
        cr, cc = rows // 2, cols // 2
        self.kuramoto_phases = [
            [math.atan2(r - cr, c - cc) % TWO_PI for c in range(cols)]
            for r in range(rows)
        ]
    elif init_type == "chimera":
        # Left half synchronized, right half random
        self.kuramoto_phases = []
        for r in range(rows):
            row = []
            for c in range(cols):
                if c < cols // 2:
                    row.append(0.0)  # synchronized
                else:
                    row.append(random.uniform(0.0, TWO_PI))
            self.kuramoto_phases.append(row)
        # Also give the two halves different frequency distributions
        for r in range(rows):
            for c in range(cols):
                if c < cols // 2:
                    self.kuramoto_nat_freq[r][c] = random.gauss(0.0, freq_spread * 0.3)
                else:
                    self.kuramoto_nat_freq[r][c] = random.gauss(0.0, freq_spread * 1.5)
    else:  # random
        self.kuramoto_phases = [
            [random.uniform(0.0, TWO_PI) for _ in range(cols)]
            for _ in range(rows)
        ]

    self.kuramoto_mode = True
    self.kuramoto_menu = False
    self.kuramoto_running = False
    self._flash(f"Kuramoto: {name} — Space to start, K/k=coupling")



def _kuramoto_step(self):
    """Advance the Kuramoto coupled oscillator system by one time step.

    Each oscillator i has:
        dθ_i/dt = ω_i + (K/N_neighbors) * Σ sin(θ_j - θ_i) + noise

    where ω_i is the natural frequency, K is coupling strength,
    and the sum is over the 4 nearest neighbors (von Neumann).
    """
    phases = self.kuramoto_phases
    nat_freq = self.kuramoto_nat_freq
    rows, cols = self.kuramoto_rows, self.kuramoto_cols
    K = self.kuramoto_coupling
    dt = self.kuramoto_dt
    noise_amp = self.kuramoto_noise
    TWO_PI = 2.0 * math.pi
    sin = math.sin

    new_phases = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        phases_r = phases[r]
        nat_freq_r = nat_freq[r]
        new_r = new_phases[r]
        for c in range(cols):
            theta = phases_r[c]

            # Sum of sin(θ_neighbor - θ) for 4 neighbors (wrap)
            coupling_sum = (
                sin(phases[(r - 1) % rows][c] - theta)
                + sin(phases[(r + 1) % rows][c] - theta)
                + sin(phases_r[(c - 1) % cols] - theta)
                + sin(phases_r[(c + 1) % cols] - theta)
            )

            dtheta = nat_freq_r[c] + (K / 4.0) * coupling_sum
            if noise_amp > 0.0:
                dtheta += noise_amp * random.gauss(0.0, 1.0)

            new_r[c] = (theta + dt * dtheta) % TWO_PI

    self.kuramoto_phases = new_phases
    self.kuramoto_generation += 1



def _kuramoto_order_parameter(self) -> float:
    """Compute the Kuramoto order parameter r ∈ [0,1].

    r = |1/N Σ exp(iθ_j)|
    r ≈ 0 means incoherence, r ≈ 1 means full synchronization.
    """
    cos = math.cos
    sin = math.sin
    sum_cos = 0.0
    sum_sin = 0.0
    n = 0
    for row in self.kuramoto_phases:
        for theta in row:
            sum_cos += cos(theta)
            sum_sin += sin(theta)
            n += 1
    if n == 0:
        return 0.0
    return math.sqrt(sum_cos * sum_cos + sum_sin * sum_sin) / n



def _handle_kuramoto_menu_key(self, key: int) -> bool:
    """Handle input in Kuramoto preset menu."""
    presets = self.KURAMOTO_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.kuramoto_menu_sel = (self.kuramoto_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.kuramoto_menu_sel = (self.kuramoto_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._kuramoto_init(self.kuramoto_menu_sel)
    elif key == ord("q") or key == 27:
        self.kuramoto_menu = False
        self._flash("Kuramoto Oscillators cancelled")
    return True



def _handle_kuramoto_key(self, key: int) -> bool:
    """Handle input in active Kuramoto simulation."""
    if key == ord("q") or key == 27:
        self._exit_kuramoto_mode()
        return True
    if key == ord(" "):
        self.kuramoto_running = not self.kuramoto_running
        return True
    if key == ord("n") or key == ord("."):
        self._kuramoto_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.KURAMOTO_PRESETS) if p[0] == self.kuramoto_preset_name),
            0,
        )
        self._kuramoto_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.kuramoto_mode = False
        self.kuramoto_running = False
        self.kuramoto_menu = True
        self.kuramoto_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.kuramoto_steps_per_frame) if self.kuramoto_steps_per_frame in choices else 0
        self.kuramoto_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.kuramoto_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.kuramoto_steps_per_frame) if self.kuramoto_steps_per_frame in choices else 0
        self.kuramoto_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.kuramoto_steps_per_frame} steps/frame")
        return True
    # Coupling strength: k/K
    if key == ord("c"):
        self.kuramoto_coupling = max(0.0, self.kuramoto_coupling - 0.1)
        self._flash(f"Coupling K: {self.kuramoto_coupling:.1f}")
        return True
    if key == ord("C"):
        self.kuramoto_coupling = min(10.0, self.kuramoto_coupling + 0.1)
        self._flash(f"Coupling K: {self.kuramoto_coupling:.1f}")
        return True
    # Noise: v/V
    if key == ord("v"):
        self.kuramoto_noise = max(0.0, self.kuramoto_noise - 0.05)
        self._flash(f"Noise: {self.kuramoto_noise:.2f}")
        return True
    if key == ord("V"):
        self.kuramoto_noise = min(5.0, self.kuramoto_noise + 0.05)
        self._flash(f"Noise: {self.kuramoto_noise:.2f}")
        return True
    # Time step: d/D
    if key == ord("d"):
        self.kuramoto_dt = max(0.01, self.kuramoto_dt - 0.01)
        self._flash(f"dt: {self.kuramoto_dt:.2f}")
        return True
    if key == ord("D"):
        self.kuramoto_dt = min(0.5, self.kuramoto_dt + 0.01)
        self._flash(f"dt: {self.kuramoto_dt:.2f}")
        return True
    # Perturb: p — randomize a small patch
    if key == ord("p"):
        rows, cols = self.kuramoto_rows, self.kuramoto_cols
        pr = random.randint(2, rows - 3)
        pc = random.randint(2, cols - 3)
        TWO_PI = 2.0 * math.pi
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    self.kuramoto_phases[nr][nc] = random.uniform(0.0, TWO_PI)
        self._flash("Perturbed!")
        return True
    return True



def _draw_kuramoto_menu(self, max_y: int, max_x: int):
    """Draw the Kuramoto preset selection menu."""
    self.stdscr.erase()
    title = "── Kuramoto Coupled Oscillators ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, coupling, freq_sp, dt, noise, init) in enumerate(self.KURAMOTO_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.kuramoto_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.kuramoto_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:22s} K={coupling:<5.1f} ω-spread={freq_sp:<4.1f} dt={dt:<4.2f} noise={noise:<4.2f}  {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], attr)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_kuramoto(self, max_y: int, max_x: int):
    """Draw the active Kuramoto oscillator simulation.

    Phase is mapped to hue (rainbow), producing flowing color patterns.
    """
    self.stdscr.erase()
    phases = self.kuramoto_phases
    rows, cols = self.kuramoto_rows, self.kuramoto_cols
    state = "▶ RUNNING" if self.kuramoto_running else "⏸ PAUSED"
    order_r = self._kuramoto_order_parameter()

    # Title bar
    title = (f" ∿ Kuramoto: {self.kuramoto_preset_name}  |  step {self.kuramoto_generation}"
             f"  |  K={self.kuramoto_coupling:.1f}  dt={self.kuramoto_dt:.2f}"
             f"  |  r={order_r:.3f}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    TWO_PI = 2.0 * math.pi

    # Map phase [0, 2π) to color pairs for a rainbow effect
    # We use the available 7 color pairs to create a phase wheel:
    # pair 1=red, 2=green, 3=yellow, 4=cyan, 5=magenta, 6=blue(ish), 7=white
    # Phase sectors: divide [0, 2π) into segments
    phase_colors = [1, 3, 2, 6, 4, 5]  # red, yellow, green, blue-ish, cyan, magenta
    n_colors = len(phase_colors)
    sector_size = TWO_PI / n_colors

    # Block characters based on phase within sector (for sub-sector shading)
    blocks = ["░░", "▒▒", "▓▓", "██", "▓▓", "▒▒"]
    n_blocks = len(blocks)

    for r in range(view_rows):
        phases_r = phases[r]
        sy = 1 + r
        for c in range(view_cols):
            theta = phases_r[c]
            sx = c * 2

            # Determine color sector
            sector_idx = int(theta / sector_size) % n_colors
            # Position within sector [0, 1)
            within = (theta - sector_idx * sector_size) / sector_size
            block_idx = int(within * n_blocks) % n_blocks

            cp = phase_colors[sector_idx]
            ch = blocks[block_idx]

            # Add boldness for mid-sector (brighter)
            attr = curses.color_pair(cp)
            if block_idx >= 2 and block_idx <= 3:
                attr |= curses.A_BOLD

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Order parameter bar (visual sync indicator)
    bar_y = max_y - 2
    if bar_y > 1:
        bar_width = min(40, max_x - 20)
        filled = int(order_r * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        label = f" sync r={order_r:.3f} [{bar}]"
        try:
            sync_color = curses.color_pair(2) if order_r > 0.5 else curses.color_pair(1)
            self.stdscr.addstr(bar_y, 0, label[:max_x - 1], sync_color | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [c/C]=coupling [d/D]=dt [v/V]=noise [p]=perturb [+/-]=steps/f [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Spiking Neural Network (Izhikevich) — Mode )
# ══════════════════════════════════════════════════════════════════════

SNN_PRESETS = [
    # (name, description, excit_ratio, weight, noise, dt, init_type)
    ("Sparse Random Firing", "Low noise — occasional spontaneous spikes",
     0.8, 8.0, 3.0, 0.5, "random"),
    ("Synchronized Bursting", "Strong coupling — rhythmic population bursts",
     0.8, 18.0, 5.0, 0.5, "random"),
    ("Traveling Waves", "Directional wave front propagating across the network",
     0.9, 12.0, 1.0, 0.5, "wave_seed"),
    ("Spiral Activity", "Rotating spiral waves of neural activation",
     0.85, 14.0, 1.5, 0.5, "spiral_seed"),
    ("Excitation Cascade", "Dense excitatory network — avalanche dynamics",
     0.95, 15.0, 4.0, 0.5, "center_seed"),
    ("Inhibition-Dominated", "Strong inhibition creates sparse patterns",
     0.5, 12.0, 6.0, 0.5, "random"),
    ("Chattering Network", "Fast rhythmic bursting with chattering neurons",
     0.8, 10.0, 4.0, 0.5, "chattering"),
    ("Cortical Column", "Mixed regular spiking & fast spiking neurons",
     0.8, 10.0, 5.0, 0.5, "cortical"),
    ("Noise-Driven", "High noise — stochastic firing patterns",
     0.8, 6.0, 12.0, 0.5, "random"),
    ("Two-Cluster Sync", "Two populations with different synchrony",
     0.8, 14.0, 3.0, 0.5, "two_cluster"),
]




def register(App):
    """Register kuramoto mode methods on the App class."""
    from life.modes.wave_equation import KURAMOTO_PRESETS
    App.KURAMOTO_PRESETS = KURAMOTO_PRESETS
    App._enter_kuramoto_mode = _enter_kuramoto_mode
    App._exit_kuramoto_mode = _exit_kuramoto_mode
    App._kuramoto_init = _kuramoto_init
    App._kuramoto_step = _kuramoto_step
    App._kuramoto_order_parameter = _kuramoto_order_parameter
    App._handle_kuramoto_menu_key = _handle_kuramoto_menu_key
    App._handle_kuramoto_key = _handle_kuramoto_key
    App._draw_kuramoto_menu = _draw_kuramoto_menu
    App._draw_kuramoto = _draw_kuramoto

