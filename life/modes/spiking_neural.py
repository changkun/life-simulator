"""Mode: snn — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_snn_mode(self):
    """Enter Spiking Neural Network mode — show preset menu."""
    self.snn_menu = True
    self.snn_menu_sel = 0
    self._flash("Spiking Neural Network — select a scenario")



def _exit_snn_mode(self):
    """Exit Spiking Neural Network mode."""
    self.snn_mode = False
    self.snn_menu = False
    self.snn_running = False
    self.snn_v = []
    self.snn_u = []
    self.snn_fired = []
    self.snn_fire_history = []
    self._flash("Spiking Neural Network OFF")



def _snn_init(self, preset_idx: int):
    """Initialize the Spiking Neural Network with the given preset."""
    name, _desc, excit_ratio, weight, noise, dt, init_type = self.SNN_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.snn_rows = rows
    self.snn_cols = cols
    self.snn_weight = weight
    self.snn_noise_amp = noise
    self.snn_dt = dt
    self.snn_preset_name = name
    self.snn_generation = 0
    self.snn_steps_per_frame = 1

    # Initialize Izhikevich parameters per neuron
    # Excitatory: (a=0.02, b=0.2, c=-65, d=8) — regular spiking
    # Inhibitory: (a=0.1, b=0.2, c=-65, d=2) — fast spiking
    self.snn_v = [[-65.0] * cols for _ in range(rows)]
    self.snn_u = [[-65.0 * 0.2] * cols for _ in range(rows)]
    self.snn_fired = [[False] * cols for _ in range(rows)]
    self.snn_fire_history = [[0.0] * cols for _ in range(rows)]

    self.snn_a = [[0.0] * cols for _ in range(rows)]
    self.snn_b = [[0.0] * cols for _ in range(rows)]
    self.snn_c_param = [[0.0] * cols for _ in range(rows)]
    self.snn_d = [[0.0] * cols for _ in range(rows)]
    self.snn_is_excitatory = [[True] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            is_exc = random.random() < excit_ratio
            self.snn_is_excitatory[r][c] = is_exc

            if init_type == "chattering":
                if is_exc:
                    # Chattering neurons
                    self.snn_a[r][c] = 0.02
                    self.snn_b[r][c] = 0.2
                    self.snn_c_param[r][c] = -50.0
                    self.snn_d[r][c] = 2.0
                else:
                    self.snn_a[r][c] = 0.1
                    self.snn_b[r][c] = 0.2
                    self.snn_c_param[r][c] = -65.0
                    self.snn_d[r][c] = 2.0
            elif init_type == "cortical":
                if is_exc:
                    # Regular spiking with variation
                    re = random.random()
                    self.snn_a[r][c] = 0.02
                    self.snn_b[r][c] = 0.2
                    self.snn_c_param[r][c] = -65.0 + 15.0 * re * re
                    self.snn_d[r][c] = 8.0 - 6.0 * re * re
                else:
                    ri = random.random()
                    self.snn_a[r][c] = 0.02 + 0.08 * ri
                    self.snn_b[r][c] = 0.25 - 0.05 * ri
                    self.snn_c_param[r][c] = -65.0
                    self.snn_d[r][c] = 2.0
            else:
                if is_exc:
                    self.snn_a[r][c] = 0.02
                    self.snn_b[r][c] = 0.2
                    self.snn_c_param[r][c] = -65.0
                    self.snn_d[r][c] = 8.0
                else:
                    self.snn_a[r][c] = 0.1
                    self.snn_b[r][c] = 0.2
                    self.snn_c_param[r][c] = -65.0
                    self.snn_d[r][c] = 2.0

            # Randomize initial membrane potential slightly
            self.snn_v[r][c] = -65.0 + random.uniform(-5.0, 5.0)
            self.snn_u[r][c] = self.snn_b[r][c] * self.snn_v[r][c]

    # Apply init_type-specific initial stimulation
    if init_type == "wave_seed":
        # Stimulate left column to create a traveling wave
        for r in range(rows):
            self.snn_v[r][0] = 30.0
            self.snn_v[r][1] = 30.0
    elif init_type == "spiral_seed":
        # Create two offset stimulation points for spiral formation
        cr, cc = rows // 2, cols // 2
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    self.snn_v[nr][nc] = 30.0
        # Second stimulation offset to create rotation
        for dr in range(-2, 3):
            for dc in range(0, 8):
                nr, nc = cr + dr + 5, cc + dc + 5
                if 0 <= nr < rows and 0 <= nc < cols:
                    self.snn_v[nr][nc] = 30.0
    elif init_type == "center_seed":
        # Stimulate a central patch
        cr, cc = rows // 2, cols // 2
        for dr in range(-4, 5):
            for dc in range(-4, 5):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    self.snn_v[nr][nc] = 30.0
    elif init_type == "two_cluster":
        # Two separate clusters with different initial conditions
        for r in range(rows):
            for c in range(cols // 4, cols // 4 + 5):
                if 0 <= c < cols:
                    self.snn_v[r][c] = 30.0
        for r in range(rows // 4, rows // 4 + 5):
            for c in range(cols):
                self.snn_v[r][c] = 30.0

    self.snn_mode = True
    self.snn_menu = False
    self.snn_running = False
    self._flash(f"SNN: {name} — Space to start, w/W=weight")



def _snn_step(self):
    """Advance the Izhikevich spiking neural network by one time step.

    Izhikevich model:
        v' = 0.04v² + 5v + 140 - u + I
        u' = a(bv - u)
        if v >= 30mV: v = c, u = u + d  (spike & reset)

    Synaptic input I comes from neighboring neurons that fired,
    weighted by excitatory (+) or inhibitory (-) connections.
    """
    v = self.snn_v
    u = self.snn_u
    a_grid = self.snn_a
    b_grid = self.snn_b
    c_grid = self.snn_c_param
    d_grid = self.snn_d
    is_exc = self.snn_is_excitatory
    rows, cols = self.snn_rows, self.snn_cols
    weight = self.snn_weight
    noise_amp = self.snn_noise_amp
    dt = self.snn_dt
    fired = self.snn_fired
    history = self.snn_fire_history

    # Build new fired map and compute synaptic input
    new_v = [[0.0] * cols for _ in range(rows)]
    new_u = [[0.0] * cols for _ in range(rows)]
    new_fired = [[False] * cols for _ in range(rows)]

    for r in range(rows):
        v_r = v[r]
        u_r = u[r]
        a_r = a_grid[r]
        b_r = b_grid[r]
        c_r = c_grid[r]
        d_r = d_grid[r]
        for c in range(cols):
            # Compute synaptic input from 8 neighbors (Moore neighborhood)
            syn_input = 0.0
            for dr in (-1, 0, 1):
                nr = r + dr
                if nr < 0 or nr >= rows:
                    continue
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nc = c + dc
                    if nc < 0 or nc >= cols:
                        continue
                    if fired[nr][nc]:
                        if is_exc[nr][nc]:
                            syn_input += weight
                        else:
                            syn_input -= weight

            # Background noise (thalamic input)
            I = syn_input + noise_amp * random.gauss(0.0, 1.0)

            vv = v_r[c]
            uu = u_r[c]

            # Izhikevich step (Euler, possibly with smaller sub-steps for stability)
            for _ in range(int(1.0 / dt)):
                if vv >= 30.0:
                    break
                dvdt = 0.04 * vv * vv + 5.0 * vv + 140.0 - uu + I
                dudt = a_r[c] * (b_r[c] * vv - uu)
                vv += dt * dvdt
                uu += dt * dudt

            # Spike check
            if vv >= 30.0:
                new_v[r][c] = c_r[c]
                new_u[r][c] = uu + d_r[c]
                new_fired[r][c] = True
            else:
                new_v[r][c] = vv
                new_u[r][c] = uu
                new_fired[r][c] = False

    # Update fire history (exponential decay for glow effect)
    for r in range(rows):
        hist_r = history[r]
        for c in range(cols):
            if new_fired[r][c]:
                hist_r[c] = 1.0
            else:
                hist_r[c] *= 0.85  # decay

    self.snn_v = new_v
    self.snn_u = new_u
    self.snn_fired = new_fired
    self.snn_generation += 1



def _handle_snn_menu_key(self, key: int) -> bool:
    """Handle input in SNN preset menu."""
    presets = self.SNN_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.snn_menu_sel = (self.snn_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.snn_menu_sel = (self.snn_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._snn_init(self.snn_menu_sel)
    elif key == ord("q") or key == 27:
        self.snn_menu = False
        self._flash("Spiking Neural Network cancelled")
    return True



def _handle_snn_key(self, key: int) -> bool:
    """Handle input in active SNN simulation."""
    if key == ord("q") or key == 27:
        self._exit_snn_mode()
        return True
    if key == ord(" "):
        self.snn_running = not self.snn_running
        return True
    if key == ord("n") or key == ord("."):
        self._snn_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.SNN_PRESETS) if p[0] == self.snn_preset_name),
            0,
        )
        self._snn_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.snn_mode = False
        self.snn_running = False
        self.snn_menu = True
        self.snn_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.snn_steps_per_frame) if self.snn_steps_per_frame in choices else 0
        self.snn_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.snn_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.snn_steps_per_frame) if self.snn_steps_per_frame in choices else 0
        self.snn_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.snn_steps_per_frame} steps/frame")
        return True
    # Synaptic weight: w/W
    if key == ord("w"):
        self.snn_weight = max(0.0, self.snn_weight - 1.0)
        self._flash(f"Synaptic weight: {self.snn_weight:.1f}")
        return True
    if key == ord("W"):
        self.snn_weight = min(50.0, self.snn_weight + 1.0)
        self._flash(f"Synaptic weight: {self.snn_weight:.1f}")
        return True
    # Noise: v/V
    if key == ord("v"):
        self.snn_noise_amp = max(0.0, self.snn_noise_amp - 0.5)
        self._flash(f"Noise: {self.snn_noise_amp:.1f}")
        return True
    if key == ord("V"):
        self.snn_noise_amp = min(30.0, self.snn_noise_amp + 0.5)
        self._flash(f"Noise: {self.snn_noise_amp:.1f}")
        return True
    # Stimulate random patch: p
    if key == ord("p"):
        rows, cols = self.snn_rows, self.snn_cols
        pr = random.randint(2, rows - 3)
        pc = random.randint(2, cols - 3)
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    self.snn_v[nr][nc] = 30.0
        self._flash("Stimulated!")
        return True
    return True



def _draw_snn_menu(self, max_y: int, max_x: int):
    """Draw the SNN preset selection menu."""
    self.stdscr.erase()
    title = "── Spiking Neural Network (Izhikevich) ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, excit, wt, noise, dt, init) in enumerate(self.SNN_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.snn_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.snn_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:24s} w={wt:<5.1f} noise={noise:<5.1f} exc={excit:<4.0%}  {desc}"
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



def _draw_snn(self, max_y: int, max_x: int):
    """Draw the active Spiking Neural Network simulation.

    Neurons are visualized by their state:
    - Firing neurons: bright white/yellow flash
    - Recently fired: decaying warm glow (red/orange)
    - Resting: dim based on membrane potential
    - Inhibitory neurons shown in blue tones when firing
    """
    self.stdscr.erase()
    rows, cols = self.snn_rows, self.snn_cols
    state = "▶ RUNNING" if self.snn_running else "⏸ PAUSED"
    fire_rate = self._snn_fire_rate()

    # Title bar
    title = (f" ⚡ SNN: {self.snn_preset_name}  |  step {self.snn_generation}"
             f"  |  w={self.snn_weight:.1f}  noise={self.snn_noise_amp:.1f}"
             f"  |  fire={fire_rate:.1%}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    history = self.snn_fire_history
    fired = self.snn_fired
    is_exc = self.snn_is_excitatory
    v = self.snn_v

    for r in range(view_rows):
        sy = 1 + r
        hist_r = history[r]
        fired_r = fired[r]
        exc_r = is_exc[r]
        v_r = v[r]
        for c in range(view_cols):
            sx = c * 2
            glow = hist_r[c]

            if fired_r[c]:
                # Currently firing — bright flash
                if exc_r[c]:
                    ch = "██"
                    attr = curses.color_pair(3) | curses.A_BOLD  # bright yellow
                else:
                    ch = "██"
                    attr = curses.color_pair(4) | curses.A_BOLD  # bright cyan (inhibitory)
            elif glow > 0.6:
                # Recent fire — bright afterglow
                ch = "▓▓"
                attr = curses.color_pair(1) | curses.A_BOLD  # bright red
            elif glow > 0.35:
                # Fading glow
                ch = "▒▒"
                attr = curses.color_pair(1)  # red
            elif glow > 0.15:
                # Dim glow
                ch = "░░"
                attr = curses.color_pair(5)  # magenta dim
            else:
                # Resting — show subthreshold activity faintly
                membrane = v_r[c]
                if membrane > -50.0:
                    ch = "░░"
                    attr = curses.color_pair(6) | curses.A_DIM
                else:
                    ch = "  "
                    attr = curses.color_pair(0)

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Fire rate bar
    bar_y = max_y - 2
    if bar_y > 1:
        bar_width = min(40, max_x - 25)
        filled = int(min(fire_rate * 10.0, 1.0) * bar_width)  # scale: 10% = full bar
        bar = "█" * filled + "░" * (bar_width - filled)
        label = f" fire rate {fire_rate:.1%} [{bar}]"
        try:
            rate_color = curses.color_pair(1) if fire_rate > 0.05 else curses.color_pair(2)
            self.stdscr.addstr(bar_y, 0, label[:max_x - 1], rate_color | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [w/W]=weight [v/V]=noise [p]=stimulate [+/-]=steps/f [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Belousov-Zhabotinsky (BZ) Reaction — Mode `
# ══════════════════════════════════════════════════════════════════════

BZ_PRESETS = [
    # (name, description, alpha, beta, gamma, diffusion, init_type)
    # alpha: activator self-amplification
    # beta: inhibitor feedback strength
    # gamma: recovery/decay rate
    # diffusion: spatial diffusion coefficient
    ("Classic Spirals", "Self-organizing spiral wavefronts",
     1.0, 1.0, 1.0, 0.2, "spiral_seed"),
    ("Dense Spirals", "Many small tightly-wound spirals",
     1.2, 1.0, 0.8, 0.15, "random_seeds"),
    ("Slow Waves", "Large slow-moving circular waves",
     0.7, 0.8, 0.6, 0.3, "center_seed"),
    ("Turbulent", "Chaotic spiral breakup and turbulence",
     1.4, 1.2, 1.0, 0.1, "random_noise"),
    ("Target Waves", "Concentric ring patterns from center",
     0.9, 1.0, 0.9, 0.25, "center_seed"),
    ("Multi-Spiral", "Multiple competing spiral centers",
     1.0, 1.0, 1.0, 0.2, "multi_spiral"),
    ("Gentle Ripples", "Soft low-contrast undulations",
     0.6, 0.7, 0.5, 0.35, "random_noise"),
    ("Fast Chaos", "Rapid evolution with spiral fragments",
     1.3, 0.9, 1.2, 0.12, "random_seeds"),
]




def register(App):
    """Register snn mode methods on the App class."""
    App._enter_snn_mode = _enter_snn_mode
    App._exit_snn_mode = _exit_snn_mode
    App._snn_init = _snn_init
    App._snn_step = _snn_step
    App._handle_snn_menu_key = _handle_snn_menu_key
    App._handle_snn_key = _handle_snn_key
    App._draw_snn_menu = _draw_snn_menu
    App._draw_snn = _draw_snn

