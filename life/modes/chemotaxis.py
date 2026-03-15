"""Mode: chemo — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_chemo_mode(self):
    """Enter Chemotaxis & Bacterial Colony Growth mode — show preset menu."""
    self.chemo_menu = True
    self.chemo_menu_sel = 0
    self._flash("Chemotaxis & Bacterial Colony Growth — select a scenario")



def _exit_chemo_mode(self):
    """Exit Chemotaxis mode."""
    self.chemo_mode = False
    self.chemo_menu = False
    self.chemo_running = False
    self.chemo_bacteria = []
    self.chemo_nutrient = []
    self.chemo_signal = []
    self._flash("Chemotaxis mode OFF")



def _chemo_init(self, preset_idx: int):
    """Initialize the Chemotaxis simulation with the given preset."""
    (name, _desc, growth, ndiff, motility, chemotaxis,
     sig_prod, sig_decay, consumption, init_type) = self.CHEMOTAXIS_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.chemo_rows = rows
    self.chemo_cols = cols
    self.chemo_growth_rate = growth
    self.chemo_nutrient_diff = ndiff
    self.chemo_motility = motility
    self.chemo_chemotaxis = chemotaxis
    self.chemo_signal_prod = sig_prod
    self.chemo_signal_decay = sig_decay
    self.chemo_consumption = consumption
    self.chemo_preset_name = name
    self.chemo_generation = 0
    self.chemo_steps_per_frame = 1

    # Initialize grids
    self.chemo_bacteria = [[0.0] * cols for _ in range(rows)]
    self.chemo_nutrient = [[1.0] * cols for _ in range(rows)]
    self.chemo_signal = [[0.0] * cols for _ in range(rows)]

    cr, cc = rows // 2, cols // 2

    if init_type == "center_seed":
        # Small inoculation in center
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    d = math.sqrt(dr * dr + dc * dc)
                    self.chemo_bacteria[nr][nc] = max(0.0, 0.8 * math.exp(-d * d * 0.5))
    elif init_type == "multi_seed":
        # Multiple colonies
        offsets = [
            (cr // 2, cc // 2),
            (cr // 2, cc + cc // 2),
            (cr + cr // 2, cc // 2),
            (cr + cr // 2, cc + cc // 2),
            (cr, cc),
        ]
        for (or_, oc) in offsets:
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    nr, nc = or_ + dr, oc + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        d = math.sqrt(dr * dr + dc * dc)
                        self.chemo_bacteria[nr][nc] = max(
                            self.chemo_bacteria[nr][nc],
                            0.7 * math.exp(-d * d * 0.5))
    elif init_type == "gradient_seed":
        # Center seed with nutrient gradient (more nutrients on right)
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    d = math.sqrt(dr * dr + dc * dc)
                    self.chemo_bacteria[nr][nc] = max(0.0, 0.8 * math.exp(-d * d * 0.5))
        # Nutrient gradient: low on left, high on right
        for r in range(rows):
            for c2 in range(cols):
                self.chemo_nutrient[r][c2] = 0.2 + 0.8 * (c2 / max(1, cols - 1))

    self.chemo_mode = True
    self.chemo_menu = False
    self.chemo_running = False
    self._flash(f"Chemotaxis: {name} — Space to start")



def _chemo_step(self):
    """Advance the Chemotaxis simulation by one time step.

    The model couples three fields:
    1. Bacteria: grow where nutrients exist, move up signal gradients, diffuse randomly
    2. Nutrients: diffuse and are consumed by bacteria
    3. Signal (chemoattractant): produced by bacteria, diffuses, and decays

    This produces the fractal-like colony morphologies seen in real
    petri dish experiments (Eden clusters, DLA tendrils, concentric rings).
    """
    bact = self.chemo_bacteria
    nutr = self.chemo_nutrient
    sig = self.chemo_signal
    rows, cols = self.chemo_rows, self.chemo_cols
    growth = self.chemo_growth_rate
    ndiff = self.chemo_nutrient_diff
    motility = self.chemo_motility
    chemotaxis = self.chemo_chemotaxis
    sig_prod = self.chemo_signal_prod
    sig_decay = self.chemo_signal_decay
    consumption = self.chemo_consumption
    dt = 0.1

    new_bact = [[0.0] * cols for _ in range(rows)]
    new_nutr = [[0.0] * cols for _ in range(rows)]
    new_sig = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        bact_r = bact[r]
        nutr_r = nutr[r]
        sig_r = sig[r]
        for c in range(cols):
            bv = bact_r[c]
            nv = nutr_r[c]
            sv = sig_r[c]

            # Laplacians (5-point stencil, zero-flux boundary)
            rn = min(r + 1, rows - 1)
            rs = max(r - 1, 0)
            ce = min(c + 1, cols - 1)
            cw = max(c - 1, 0)

            lap_b = bact[rn][c] + bact[rs][c] + bact_r[ce] + bact_r[cw] - 4.0 * bv
            lap_n = nutr[rn][c] + nutr[rs][c] + nutr_r[ce] + nutr_r[cw] - 4.0 * nv
            lap_s = sig[rn][c] + sig[rs][c] + sig_r[ce] + sig_r[cw] - 4.0 * sv

            # Signal gradient for chemotaxis (central differences)
            grad_sr = (sig[rn][c] - sig[rs][c]) * 0.5
            grad_sc = (sig_r[ce] - sig_r[cw]) * 0.5

            # Chemotactic flux divergence: -div(bacteria * chi * grad(signal))
            # Approximate: bacteria moves up gradient
            # Use upwind scheme for stability
            chemo_flux = 0.0
            if chemotaxis > 0 and bv > 0.001:
                # Flux of bacteria toward higher signal
                bact_n = bact[rn][c]
                bact_s = bact[rs][c]
                bact_e = bact_r[ce]
                bact_w = bact_r[cw]
                sig_n = sig[rn][c]
                sig_s = sig[rs][c]
                sig_e = sig_r[ce]
                sig_w = sig_r[cw]
                # Net chemotactic flux into cell
                flux_in = 0.0
                # From each neighbor: if signal here > signal there, bacteria flows in
                flux_in += bact_n * max(0.0, sv - sig_n)
                flux_in += bact_s * max(0.0, sv - sig_s)
                flux_in += bact_e * max(0.0, sv - sig_e)
                flux_in += bact_w * max(0.0, sv - sig_w)
                # From this cell: bacteria flows out to higher-signal neighbors
                flux_out = 0.0
                flux_out += bv * max(0.0, sig_n - sv)
                flux_out += bv * max(0.0, sig_s - sv)
                flux_out += bv * max(0.0, sig_e - sv)
                flux_out += bv * max(0.0, sig_w - sv)
                chemo_flux = chemotaxis * (flux_in - flux_out)

            # Bacterial dynamics
            # Growth: logistic with nutrient limitation
            db = (growth * bv * nv * (1.0 - bv)    # logistic growth
                  + motility * lap_b                 # random motility
                  + chemo_flux)                      # chemotactic movement

            # Nutrient dynamics
            dn = ndiff * lap_n - consumption * bv * nv  # diffusion - consumption

            # Signal dynamics
            ds = sig_prod * bv - sig_decay * sv + 0.1 * lap_s  # production - decay + diffusion

            # Euler step
            nb = bv + dt * db
            nn = nv + dt * dn
            ns = sv + dt * ds

            new_bact[r][c] = max(0.0, min(1.0, nb))
            new_nutr[r][c] = max(0.0, min(1.0, nn))
            new_sig[r][c] = max(0.0, min(1.0, ns))

    self.chemo_bacteria = new_bact
    self.chemo_nutrient = new_nutr
    self.chemo_signal = new_sig
    self.chemo_generation += 1



def _handle_chemo_menu_key(self, key: int) -> bool:
    """Handle input in Chemotaxis preset menu."""
    presets = self.CHEMOTAXIS_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.chemo_menu_sel = (self.chemo_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.chemo_menu_sel = (self.chemo_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._chemo_init(self.chemo_menu_sel)
    elif key == ord("q") or key == 27:
        self.chemo_menu = False
        self._flash("Chemotaxis cancelled")
    return True



def _handle_chemo_key(self, key: int) -> bool:
    """Handle input in active Chemotaxis simulation."""
    if key == ord("q") or key == 27:
        self._exit_chemo_mode()
        return True
    if key == ord(" "):
        self.chemo_running = not self.chemo_running
        return True
    if key == ord("n") or key == ord("."):
        self._chemo_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.CHEMOTAXIS_PRESETS) if p[0] == self.chemo_preset_name),
            0,
        )
        self._chemo_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.chemo_mode = False
        self.chemo_running = False
        self.chemo_menu = True
        self.chemo_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.chemo_steps_per_frame) if self.chemo_steps_per_frame in choices else 0
        self.chemo_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.chemo_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.chemo_steps_per_frame) if self.chemo_steps_per_frame in choices else 0
        self.chemo_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.chemo_steps_per_frame} steps/frame")
        return True
    # Growth rate: g/G
    if key == ord("g"):
        self.chemo_growth_rate = max(0.1, self.chemo_growth_rate - 0.05)
        self._flash(f"Growth rate: {self.chemo_growth_rate:.2f}")
        return True
    if key == ord("G"):
        self.chemo_growth_rate = min(2.0, self.chemo_growth_rate + 0.05)
        self._flash(f"Growth rate: {self.chemo_growth_rate:.2f}")
        return True
    # Chemotaxis strength: c/C
    if key == ord("c"):
        self.chemo_chemotaxis = max(0.0, self.chemo_chemotaxis - 0.05)
        self._flash(f"Chemotaxis: {self.chemo_chemotaxis:.2f}")
        return True
    if key == ord("C"):
        self.chemo_chemotaxis = min(2.0, self.chemo_chemotaxis + 0.05)
        self._flash(f"Chemotaxis: {self.chemo_chemotaxis:.2f}")
        return True
    # Motility: d/D
    if key == ord("d"):
        self.chemo_motility = max(0.0, self.chemo_motility - 0.005)
        self._flash(f"Motility: {self.chemo_motility:.3f}")
        return True
    if key == ord("D"):
        self.chemo_motility = min(0.5, self.chemo_motility + 0.005)
        self._flash(f"Motility: {self.chemo_motility:.3f}")
        return True
    # Consumption: a/A
    if key == ord("a"):
        self.chemo_consumption = max(0.05, self.chemo_consumption - 0.05)
        self._flash(f"Consumption: {self.chemo_consumption:.2f}")
        return True
    if key == ord("A"):
        self.chemo_consumption = min(2.0, self.chemo_consumption + 0.05)
        self._flash(f"Consumption: {self.chemo_consumption:.2f}")
        return True
    # Perturb: p — add bacteria at random location
    if key == ord("p"):
        rows, cols = self.chemo_rows, self.chemo_cols
        pr = random.randint(3, rows - 4)
        pc = random.randint(3, cols - 4)
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = pr + dr, pc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    d = math.sqrt(dr * dr + dc * dc)
                    self.chemo_bacteria[nr][nc] = min(
                        1.0, self.chemo_bacteria[nr][nc] + 0.6 * math.exp(-d * d * 0.5))
        self._flash("Inoculated!")
        return True
    # Mouse click to inoculate
    if key == curses.KEY_MOUSE:
        try:
            _, mx, my, _, _ = curses.getmouse()
            r = my - 1
            c = mx // 2
            rows, cols = self.chemo_rows, self.chemo_cols
            if 0 <= r < rows and 0 <= c < cols:
                for rr in range(-2, 3):
                    for rc in range(-2, 3):
                        nr, nc = r + rr, c + rc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            d = math.sqrt(rr * rr + rc * rc)
                            self.chemo_bacteria[nr][nc] = min(
                                1.0, self.chemo_bacteria[nr][nc] + 0.6 * math.exp(-d * d * 0.5))
        except curses.error:
            pass
        return True
    # Toggle view: v — cycle through bacteria/nutrient/signal views
    if key == ord("v"):
        views = ["bacteria", "nutrient", "signal"]
        cur = getattr(self, '_chemo_view', 'bacteria')
        idx = views.index(cur) if cur in views else 0
        self._chemo_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self._chemo_view}")
        return True
    return True



def _draw_chemo_menu(self, max_y: int, max_x: int):
    """Draw the Chemotaxis preset selection menu."""
    self.stdscr.erase()
    title = "── Chemotaxis & Bacterial Colony Growth ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, growth, ndiff, motil, chemo, sprod, sdec, cons, init) in enumerate(self.CHEMOTAXIS_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.chemo_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.chemo_menu_sel else curses.color_pair(7)
        line = f"{marker}{name:20s} g={growth:<4.1f} m={motil:<5.3f} χ={chemo:<4.2f} cons={cons:<4.2f}  {desc}"
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



def _draw_chemo(self, max_y: int, max_x: int):
    """Draw the active Chemotaxis simulation.

    Default view shows bacteria as colony morphology:
    - Dense bacteria: bright green/yellow (colony mass)
    - Medium: green characters
    - Low/frontier: dim green dots
    - Nutrient-depleted zones: dark blue
    - Signal hotspots: shown as magenta overlay when in signal view
    """
    self.stdscr.erase()
    bact = self.chemo_bacteria
    nutr = self.chemo_nutrient
    sig = self.chemo_signal
    rows, cols = self.chemo_rows, self.chemo_cols
    state = "▶ RUNNING" if self.chemo_running else "⏸ PAUSED"
    view = getattr(self, '_chemo_view', 'bacteria')

    # Title bar
    title = (f" 🦠 Chemotaxis: {self.chemo_preset_name}  |  step {self.chemo_generation}"
             f"  |  g={self.chemo_growth_rate:.2f} χ={self.chemo_chemotaxis:.2f}"
             f"  m={self.chemo_motility:.3f}  |  view={view}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    for r in range(view_rows):
        sy = 1 + r
        bact_r = bact[r]
        nutr_r = nutr[r]
        sig_r = sig[r]
        for col in range(view_cols):
            sx = col * 2

            if view == "bacteria":
                bv = bact_r[col]
                nv = nutr_r[col]
                if bv > 0.7:
                    ch = "██"
                    attr = curses.color_pair(3) | curses.A_BOLD  # bright yellow — dense colony
                elif bv > 0.4:
                    ch = "▓▓"
                    attr = curses.color_pair(1) | curses.A_BOLD  # bright green
                elif bv > 0.2:
                    ch = "▒▒"
                    attr = curses.color_pair(2)  # green
                elif bv > 0.08:
                    ch = "░░"
                    attr = curses.color_pair(1) | curses.A_DIM  # dim green — frontier
                elif bv > 0.02:
                    ch = "··"
                    attr = curses.color_pair(2) | curses.A_DIM
                elif nv < 0.3:
                    # Nutrient-depleted zone (no bacteria, low nutrients)
                    ch = "░░"
                    attr = curses.color_pair(4) | curses.A_DIM  # dark blue
                else:
                    continue  # empty — skip
            elif view == "nutrient":
                nv = nutr_r[col]
                if nv > 0.8:
                    ch = "██"
                    attr = curses.color_pair(6) | curses.A_BOLD  # bright cyan
                elif nv > 0.6:
                    ch = "▓▓"
                    attr = curses.color_pair(6)
                elif nv > 0.4:
                    ch = "▒▒"
                    attr = curses.color_pair(4)  # blue
                elif nv > 0.2:
                    ch = "░░"
                    attr = curses.color_pair(4) | curses.A_DIM
                elif nv > 0.05:
                    ch = "··"
                    attr = curses.color_pair(4) | curses.A_DIM
                else:
                    continue
            else:  # signal view
                sv = sig_r[col]
                if sv > 0.5:
                    ch = "██"
                    attr = curses.color_pair(5) | curses.A_BOLD  # bright magenta
                elif sv > 0.3:
                    ch = "▓▓"
                    attr = curses.color_pair(5)
                elif sv > 0.15:
                    ch = "▒▒"
                    attr = curses.color_pair(1)  # red
                elif sv > 0.05:
                    ch = "░░"
                    attr = curses.color_pair(1) | curses.A_DIM
                elif sv > 0.01:
                    ch = "··"
                    attr = curses.color_pair(1) | curses.A_DIM
                else:
                    continue

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
            hint = " [Space]=play [n]=step [g/G]=growth [c/C]=chemotaxis [d/D]=motility [a/A]=consumption [v]=view [p]=inoculate [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Magnetohydrodynamics (MHD) Plasma — Mode }
# ══════════════════════════════════════════════════════════════════════

MHD_PRESETS = [
    # (name, description, resistivity, viscosity, pressure, init_type)
    ("Harris Current Sheet", "Classic reconnection setup — anti-parallel B fields",
     0.008, 0.005, 1.0, "harris"),
    ("Orszag-Tang Vortex", "MHD turbulence from colliding vortices",
     0.005, 0.005, 0.8, "orszag_tang"),
    ("Magnetic Island", "Tearing-mode instability in a pinch",
     0.01, 0.008, 1.0, "island"),
    ("Blast Wave", "Explosion in a magnetized medium",
     0.005, 0.005, 1.2, "blast"),
    ("Kelvin-Helmholtz", "Shear flow instability with magnetic field",
     0.008, 0.01, 1.0, "kh"),
    ("Double Current Sheet", "Two reconnection sites — complex dynamics",
     0.01, 0.005, 1.0, "double_harris"),
    ("Magnetic Flux Rope", "Twisted magnetic structure relaxation",
     0.006, 0.006, 0.9, "flux_rope"),
    ("Random Turbulence", "Decaying MHD turbulence from random fields",
     0.008, 0.008, 1.0, "random"),
]




def register(App):
    """Register chemo mode methods on the App class."""
    App._enter_chemo_mode = _enter_chemo_mode
    App._exit_chemo_mode = _exit_chemo_mode
    App._chemo_init = _chemo_init
    App._chemo_step = _chemo_step
    App._handle_chemo_menu_key = _handle_chemo_menu_key
    App._handle_chemo_key = _handle_chemo_key
    App._draw_chemo_menu = _draw_chemo_menu
    App._draw_chemo = _draw_chemo

