"""Mode: bz — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_bz_mode(self):
    """Enter BZ Reaction mode — show preset menu."""
    self.bz_menu = True
    self.bz_menu_sel = 0
    self._flash("Belousov-Zhabotinsky Reaction — select a scenario")



def _exit_bz_mode(self):
    """Exit BZ Reaction mode."""
    self.bz_mode = False
    self.bz_menu = False
    self.bz_running = False
    self.bz_a = []
    self.bz_b = []
    self.bz_c = []
    self._flash("BZ Reaction mode OFF")



def _bz_init(self, preset_idx: int):
    """Initialize the BZ Reaction simulation with the given preset."""
    name, _desc, alpha, beta, gamma, diffusion, init_type = self.BZ_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.bz_rows = rows
    self.bz_cols = cols
    self.bz_alpha = alpha
    self.bz_beta = beta
    self.bz_gamma = gamma
    self.bz_diffusion = diffusion
    self.bz_preset_name = name
    self.bz_generation = 0
    self.bz_steps_per_frame = 1

    # Initialize grids: a=activator, b=inhibitor, c=recovery
    self.bz_a = [[0.0] * cols for _ in range(rows)]
    self.bz_b = [[0.0] * cols for _ in range(rows)]
    self.bz_c = [[0.0] * cols for _ in range(rows)]

    cr, cc = rows // 2, cols // 2

    if init_type == "spiral_seed":
        # Create an asymmetric initial condition for spiral formation
        # A broken wave front creates a free end that curls into a spiral
        for r in range(rows):
            for c2 in range(cols):
                # Vertical wavefront on left half
                if c2 < cc and abs(r - cr) < rows // 4:
                    self.bz_a[r][c2] = 1.0
                # Break the wavefront — only top half gets the recovery
                if c2 < cc and r < cr:
                    self.bz_c[r][c2] = 0.5
    elif init_type == "center_seed":
        # Gaussian blob in center — produces expanding rings
        for r in range(rows):
            for c2 in range(cols):
                dx = (c2 - cc) / max(cols, 1) * 6
                dy = (r - cr) / max(rows, 1) * 6
                d2 = dx * dx + dy * dy
                self.bz_a[r][c2] = math.exp(-d2 * 2.0)
    elif init_type == "random_seeds":
        # Scattered small excitation patches
        num_seeds = max(8, (rows * cols) // 300)
        for _ in range(num_seeds):
            sr = random.randint(3, rows - 4)
            sc = random.randint(3, cols - 4)
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    nr, nc = sr + dr, sc + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        d = math.sqrt(dr * dr + dc * dc)
                        self.bz_a[nr][nc] = max(self.bz_a[nr][nc],
                                                 math.exp(-d * d * 0.5))
    elif init_type == "random_noise":
        # Random low-level noise everywhere
        for r in range(rows):
            for c2 in range(cols):
                self.bz_a[r][c2] = random.uniform(0.0, 0.3)
                self.bz_b[r][c2] = random.uniform(0.0, 0.3)
                self.bz_c[r][c2] = random.uniform(0.0, 0.3)
    elif init_type == "multi_spiral":
        # Multiple offset broken wavefronts for multiple spirals
        offsets = [
            (cr // 2, cc // 2),
            (cr // 2, cc + cc // 2),
            (cr + cr // 2, cc // 2),
            (cr + cr // 2, cc + cc // 2),
        ]
        for (or_, oc) in offsets:
            radius = min(rows, cols) // 8
            angle_offset = random.uniform(0, 2 * math.pi)
            for r in range(max(0, or_ - radius), min(rows, or_ + radius)):
                for c2 in range(max(0, oc - radius), min(cols, oc + radius)):
                    dy = r - or_
                    dx = c2 - oc
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < radius:
                        angle = math.atan2(dy, dx) + angle_offset
                        # Half-plane excitation for spiral seeding
                        if angle % (2 * math.pi) < math.pi:
                            self.bz_a[r][c2] = max(self.bz_a[r][c2],
                                                     math.exp(-((d - radius * 0.5) ** 2) * 0.05))

    self.bz_mode = True
    self.bz_menu = False
    self.bz_running = False
    self._flash(f"BZ Reaction: {name} — Space to start")



def _bz_step(self):
    """Advance the BZ Reaction by one time step.

    Uses the Oregonator-inspired 3-variable model:
        a' = a(alpha - a - c) + D*∇²a       (activator: autocatalytic, inhibited by recovery)
        b' = a - b                            (inhibitor: tracks activator with delay)
        c' = gamma*(a - c)                    (recovery: slowly follows activator)

    This produces the characteristic spiral waves seen in the
    Belousov-Zhabotinsky chemical reaction.
    """
    a = self.bz_a
    b = self.bz_b
    c = self.bz_c
    rows, cols = self.bz_rows, self.bz_cols
    alpha = self.bz_alpha
    beta = self.bz_beta
    gamma = self.bz_gamma
    diff = self.bz_diffusion
    dt = 0.05

    new_a = [[0.0] * cols for _ in range(rows)]
    new_b = [[0.0] * cols for _ in range(rows)]
    new_c = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        a_r = a[r]
        b_r = b[r]
        c_r = c[r]
        for col in range(cols):
            av = a_r[col]
            bv = b_r[col]
            cv = c_r[col]

            # Laplacian of activator (5-point stencil, wrapping)
            up = a[(r - 1) % rows][col]
            dn = a[(r + 1) % rows][col]
            lt = a_r[(col - 1) % cols]
            rt = a_r[(col + 1) % cols]
            lap_a = up + dn + lt + rt - 4.0 * av

            # Reaction dynamics
            # Activator: autocatalytic growth, saturated by itself and suppressed by recovery
            da = av * (alpha - av - beta * cv) + diff * lap_a
            # Inhibitor: slowly tracks activator
            db = av - bv
            # Recovery: driven by activator, decays
            dc = gamma * (av - cv)

            # Euler step
            na = av + dt * da
            nb = bv + dt * db
            nc = cv + dt * dc

            # Clamp to [0, 1]
            new_a[r][col] = max(0.0, min(1.0, na))
            new_b[r][col] = max(0.0, min(1.0, nb))
            new_c[r][col] = max(0.0, min(1.0, nc))

    self.bz_a = new_a
    self.bz_b = new_b
    self.bz_c = new_c
    self.bz_generation += 1



def _handle_bz_menu_key(self, key: int) -> bool:
    """Handle input in BZ Reaction preset menu."""
    presets = self.BZ_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.bz_menu_sel = (self.bz_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.bz_menu_sel = (self.bz_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._bz_init(self.bz_menu_sel)
    elif key == ord("q") or key == 27:
        self.bz_menu = False
        self._flash("BZ Reaction cancelled")
    return True



def _handle_bz_key(self, key: int) -> bool:
    """Handle input in active BZ Reaction simulation."""
    if key == ord("q") or key == 27:
        self._exit_bz_mode()
        return True
    if key == ord(" "):
        self.bz_running = not self.bz_running
        return True
    if key == ord("n") or key == ord("."):
        self._bz_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.BZ_PRESETS) if p[0] == self.bz_preset_name),
            0,
        )
        self._bz_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.bz_mode = False
        self.bz_running = False
        self.bz_menu = True
        self.bz_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.bz_steps_per_frame) if self.bz_steps_per_frame in choices else 0
        self.bz_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.bz_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.bz_steps_per_frame) if self.bz_steps_per_frame in choices else 0
        self.bz_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.bz_steps_per_frame} steps/frame")
        return True
    # Alpha (activator rate): a/A
    if key == ord("a"):
        self.bz_alpha = max(0.1, self.bz_alpha - 0.1)
        self._flash(f"Alpha (activator): {self.bz_alpha:.1f}")
        return True
    if key == ord("A"):
        self.bz_alpha = min(3.0, self.bz_alpha + 0.1)
        self._flash(f"Alpha (activator): {self.bz_alpha:.1f}")
        return True
    # Gamma (recovery rate): g/G
    if key == ord("g"):
        self.bz_gamma = max(0.1, self.bz_gamma - 0.1)
        self._flash(f"Gamma (recovery): {self.bz_gamma:.1f}")
        return True
    if key == ord("G"):
        self.bz_gamma = min(3.0, self.bz_gamma + 0.1)
        self._flash(f"Gamma (recovery): {self.bz_gamma:.1f}")
        return True
    # Diffusion: d/D
    if key == ord("d"):
        self.bz_diffusion = max(0.01, self.bz_diffusion - 0.02)
        self._flash(f"Diffusion: {self.bz_diffusion:.2f}")
        return True
    if key == ord("D"):
        self.bz_diffusion = min(1.0, self.bz_diffusion + 0.02)
        self._flash(f"Diffusion: {self.bz_diffusion:.2f}")
        return True
    # Perturb: p — add random excitation patch
    if key == ord("p"):
        rows, cols = self.bz_rows, self.bz_cols
        pr = random.randint(3, rows - 4)
        pc = random.randint(3, cols - 4)
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    d = math.sqrt(dr * dr + dc * dc)
                    self.bz_a[nr][nc] = min(1.0, self.bz_a[nr][nc] +
                                             math.exp(-d * d * 0.3))
        self._flash("Perturbed!")
        return True
    # Mouse click to add excitation
    if key == curses.KEY_MOUSE:
        try:
            _, mx, my, _, _ = curses.getmouse()
            r = my - 1
            c = mx // 2
            rows, cols = self.bz_rows, self.bz_cols
            if 0 <= r < rows and 0 <= c < cols:
                for rr in range(-3, 4):
                    for rc in range(-3, 4):
                        nr, nc = r + rr, c + rc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            d = math.sqrt(rr * rr + rc * rc)
                            self.bz_a[nr][nc] = min(1.0, self.bz_a[nr][nc] +
                                                     math.exp(-d * d * 0.3))
        except curses.error:
            pass
        return True
    return True



def _draw_bz_menu(self, max_y: int, max_x: int):
    """Draw the BZ Reaction preset selection menu."""
    self.stdscr.erase()
    title = "── Belousov-Zhabotinsky Reaction ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, alpha, beta, gamma, diff, init) in enumerate(self.BZ_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.bz_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.bz_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:20s} α={alpha:<4.1f} β={beta:<4.1f} γ={gamma:<4.1f} D={diff:<5.2f}  {desc}"
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



def _draw_bz(self, max_y: int, max_x: int):
    """Draw the active BZ Reaction simulation.

    Maps the activator concentration to colorful characters that
    evoke the vibrant chemical oscillation patterns:
    - High activator: bright warm colors (yellow/white)
    - Medium: transitional (cyan/green)
    - Low/recovering: cool colors (blue/magenta)
    - Quiescent: dark
    """
    self.stdscr.erase()
    a = self.bz_a
    c = self.bz_c
    rows, cols = self.bz_rows, self.bz_cols
    state = "▶ RUNNING" if self.bz_running else "⏸ PAUSED"

    # Title bar
    title = (f" ⚗ BZ Reaction: {self.bz_preset_name}  |  step {self.bz_generation}"
             f"  |  α={self.bz_alpha:.1f} β={self.bz_beta:.1f} γ={self.bz_gamma:.1f}"
             f"  D={self.bz_diffusion:.2f}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    for r in range(view_rows):
        sy = 1 + r
        a_r = a[r]
        c_r = c[r]
        for col in range(view_cols):
            sx = col * 2
            av = a_r[col]
            cv = c_r[col]

            # Combine activator and recovery for phase-based coloring
            # This creates the classic BZ color wheel effect
            if av < 0.05 and cv < 0.05:
                # Quiescent — dark
                continue
            elif av > 0.7:
                # Excited — bright wavefront
                ch = "██"
                attr = curses.color_pair(3) | curses.A_BOLD  # bright yellow
            elif av > 0.4:
                # Active — medium excitation
                ch = "▓▓"
                if cv > 0.3:
                    attr = curses.color_pair(1) | curses.A_BOLD  # red (recovering)
                else:
                    attr = curses.color_pair(6) | curses.A_BOLD  # cyan-ish
            elif av > 0.2:
                # Transitional
                ch = "▒▒"
                if cv > av:
                    attr = curses.color_pair(5)  # magenta (refractory)
                else:
                    attr = curses.color_pair(2)  # green (rising)
            elif av > 0.08:
                # Low activity
                ch = "░░"
                if cv > 0.15:
                    attr = curses.color_pair(4) | curses.A_DIM  # blue (deep refractory)
                else:
                    attr = curses.color_pair(1) | curses.A_DIM  # dim green
            else:
                # Very faint
                ch = "··"
                attr = curses.color_pair(4) | curses.A_DIM

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [a/A]=alpha [g/G]=gamma [d/D]=diffusion [p]=perturb [+/-]=steps/f [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Chemotaxis & Bacterial Colony Growth — Mode {
# ══════════════════════════════════════════════════════════════════════

CHEMOTAXIS_PRESETS = [
    # (name, description, growth_rate, nutrient_diff, motility, chemotaxis,
    #  signal_prod, signal_decay, consumption, init_type)
    ("Eden Cluster", "Dense compact colony — nutrient-rich, low motility",
     0.8, 0.05, 0.01, 0.0, 0.0, 0.1, 0.3, "center_seed"),
    ("DLA Tendrils", "Diffusion-limited branching — starved environment",
     0.5, 0.08, 0.005, 0.3, 0.2, 0.05, 0.6, "center_seed"),
    ("Dense Branching", "Branchy morphology with moderate nutrients",
     0.6, 0.06, 0.02, 0.15, 0.1, 0.08, 0.4, "center_seed"),
    ("Concentric Rings", "Ring formation via chemotactic waves",
     0.4, 0.04, 0.03, 0.5, 0.4, 0.02, 0.5, "center_seed"),
    ("Swarming Colony", "Highly motile — rapid spreading",
     0.7, 0.05, 0.08, 0.4, 0.3, 0.06, 0.3, "center_seed"),
    ("Multi-Colony", "Multiple competing colonies",
     0.6, 0.05, 0.02, 0.2, 0.15, 0.08, 0.4, "multi_seed"),
    ("Nutrient Gradient", "Colony expanding along nutrient gradient",
     0.5, 0.06, 0.015, 0.25, 0.2, 0.06, 0.4, "gradient_seed"),
    ("Quorum Sensing", "Density-dependent collective behavior",
     0.5, 0.05, 0.01, 0.6, 0.5, 0.03, 0.35, "center_seed"),
]




def register(App):
    """Register bz mode methods on the App class."""
    from life.modes.spiking_neural import BZ_PRESETS
    App.BZ_PRESETS = BZ_PRESETS
    App._enter_bz_mode = _enter_bz_mode
    App._exit_bz_mode = _exit_bz_mode
    App._bz_init = _bz_init
    App._bz_step = _bz_step
    App._handle_bz_menu_key = _handle_bz_menu_key
    App._handle_bz_key = _handle_bz_key
    App._draw_bz_menu = _draw_bz_menu
    App._draw_bz = _draw_bz

