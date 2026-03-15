"""Mode: snowflake — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_snowflake_mode(self):
    """Enter Snowflake Growth mode — show preset menu."""
    self.snowflake_menu = True
    self.snowflake_menu_sel = 0
    self._flash("Snowflake Growth (Reiter Crystal) — select a scenario")



def _exit_snowflake_mode(self):
    """Exit Snowflake Growth mode."""
    self.snowflake_mode = False
    self.snowflake_menu = False
    self.snowflake_running = False
    self.snowflake_frozen = []
    self.snowflake_vapor = []
    self._flash("Snowflake Growth mode OFF")



def _snowflake_hex_neighbors(self, r: int, c: int) -> list[tuple[int, int]]:
    """Return the 6 hex neighbors using offset coordinates (even-r)."""
    if r % 2 == 0:
        return [
            (r - 1, c - 1), (r - 1, c),
            (r, c - 1), (r, c + 1),
            (r + 1, c - 1), (r + 1, c),
        ]
    else:
        return [
            (r - 1, c), (r - 1, c + 1),
            (r, c - 1), (r, c + 1),
            (r + 1, c), (r + 1, c + 1),
        ]



def _snowflake_init(self, preset_idx: int):
    """Initialize Snowflake Growth with the given preset."""
    name, _desc, alpha, beta, gamma, mu, symmetric = self.SNOWFLAKE_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.snowflake_rows = rows
    self.snowflake_cols = cols
    self.snowflake_alpha = alpha
    self.snowflake_beta = beta
    self.snowflake_gamma = gamma
    self.snowflake_mu = mu
    self.snowflake_symmetric = symmetric
    self.snowflake_preset_name = name
    self.snowflake_generation = 0
    self.snowflake_steps_per_frame = 1

    # Initialize vapor field to uniform beta, no frozen cells
    self.snowflake_frozen = [[False] * cols for _ in range(rows)]
    self.snowflake_vapor = [[beta] * cols for _ in range(rows)]

    # Seed: freeze the center cell
    cr, cc = rows // 2, cols // 2
    self.snowflake_frozen[cr][cc] = True
    self.snowflake_vapor[cr][cc] = 0.0
    self.snowflake_frozen_count = 1

    self.snowflake_mode = True
    self.snowflake_menu = False
    self.snowflake_running = False
    sym_label = "6-fold symmetric" if symmetric else "asymmetric"
    self._flash(f"Snowflake: {name} ({sym_label}) — Space to start")



def _snowflake_hex_to_axial(self, r: int, c: int) -> tuple[int, int]:
    """Convert offset (even-r) coordinates to axial (q, s) for symmetry ops."""
    q = c - (r - (r & 1)) // 2
    s = r
    return q, s



def _snowflake_axial_to_offset(self, q: int, s: int) -> tuple[int, int]:
    """Convert axial (q, s) coordinates back to offset (even-r)."""
    r = s
    c = q + (s - (s & 1)) // 2
    return r, c



def _snowflake_symmetric_points(self, r: int, c: int) -> list[tuple[int, int]]:
    """Return all 12 symmetric images of (r, c) under 6-fold symmetry + mirror.

    Uses hex axial coordinates centered on the grid center for rotation,
    then converts back to offset coords.
    """
    rows, cols = self.snowflake_rows, self.snowflake_cols
    cr, cc = rows // 2, cols // 2

    # Get axial coords relative to center
    q0, s0 = self._snowflake_hex_to_axial(r, c)
    qc, sc = self._snowflake_hex_to_axial(cr, cc)
    dq = q0 - qc
    ds = s0 - sc

    # In cube coordinates: x=dq, z=ds, y=-dq-ds
    x, z = dq, ds
    y = -x - z

    # All 6 rotations × 2 reflections = 12 symmetric points
    transforms = [
        (x, y, z), (-y, -z, -x), (z, x, y),
        (-x, -y, -z), (y, z, x), (-z, -x, -y),
        # Mirror (reflect across one axis)
        (x, z, y), (-y, -x, -z), (z, y, x),
        (-x, -z, -y), (y, x, z), (-z, -y, -x),
    ]

    points = []
    seen = set()
    for tx, ty, tz in transforms:
        aq = tx + qc
        asval = tz + sc
        or_, oc = self._snowflake_axial_to_offset(aq, asval)
        if 0 <= or_ < rows and 0 <= oc < cols and (or_, oc) not in seen:
            seen.add((or_, oc))
            points.append((or_, oc))
    return points



def _snowflake_step(self):
    """Advance the Reiter snowflake model by one step.

    Algorithm (Reiter 2005):
    1. Identify receptive cells (non-frozen neighbors of frozen cells).
    2. Add alpha to receptive cells (vapor deposition).
    3. Diffuse vapor among non-frozen cells on the hex lattice.
    4. Freeze any receptive cell with vapor >= 1.0.
    5. If symmetric mode: enforce 6-fold symmetry on newly frozen cells.
    """
    frozen = self.snowflake_frozen
    vapor = self.snowflake_vapor
    rows, cols = self.snowflake_rows, self.snowflake_cols
    alpha = self.snowflake_alpha
    gamma = self.snowflake_gamma
    mu = self.snowflake_mu

    # Step 1: identify receptive cells
    receptive = [[False] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if frozen[r][c]:
                continue
            for nr, nc in self._snowflake_hex_neighbors(r, c):
                if 0 <= nr < rows and 0 <= nc < cols and frozen[nr][nc]:
                    receptive[r][c] = True
                    break

    # Step 2: add deposition to receptive cells
    for r in range(rows):
        for c in range(cols):
            if receptive[r][c]:
                vapor[r][c] += alpha
                if gamma > 0:
                    vapor[r][c] += random.uniform(-gamma, gamma)

    # Step 3: diffuse vapor among non-receptive, non-frozen cells
    # mu controls how much of the cell's vapor is exchanged with neighbors
    new_vapor = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if frozen[r][c] or receptive[r][c]:
                new_vapor[r][c] = vapor[r][c]
                continue
            # Weighted average: (1-mu)*self + mu*(avg of diffusible neighbors)
            neighbor_total = 0.0
            neighbor_count = 0
            for nr, nc in self._snowflake_hex_neighbors(r, c):
                if 0 <= nr < rows and 0 <= nc < cols:
                    if not frozen[nr][nc] and not receptive[nr][nc]:
                        neighbor_total += vapor[nr][nc]
                        neighbor_count += 1
            if neighbor_count > 0:
                avg_neighbor = neighbor_total / neighbor_count
                new_vapor[r][c] = (1.0 - mu) * vapor[r][c] + mu * avg_neighbor
            else:
                new_vapor[r][c] = vapor[r][c]

    # Step 4: freeze receptive cells that reached threshold
    newly_frozen = []
    for r in range(rows):
        for c in range(cols):
            if receptive[r][c] and new_vapor[r][c] >= 1.0:
                newly_frozen.append((r, c))

    # Step 5: apply freezing — with optional 6-fold symmetry enforcement
    if self.snowflake_symmetric and newly_frozen:
        # For each newly frozen cell, also freeze all its symmetric images
        all_to_freeze = set()
        for r, c in newly_frozen:
            for sr, sc in self._snowflake_symmetric_points(r, c):
                all_to_freeze.add((sr, sc))
        for fr, fc in all_to_freeze:
            if not frozen[fr][fc]:
                frozen[fr][fc] = True
                new_vapor[fr][fc] = 0.0
                self.snowflake_frozen_count += 1
    else:
        for r, c in newly_frozen:
            frozen[r][c] = True
            new_vapor[r][c] = 0.0
            self.snowflake_frozen_count += 1

    self.snowflake_vapor = new_vapor
    self.snowflake_generation += 1



def _handle_snowflake_menu_key(self, key: int) -> bool:
    """Handle input in Snowflake Growth preset menu."""
    presets = self.SNOWFLAKE_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.snowflake_menu_sel = (self.snowflake_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.snowflake_menu_sel = (self.snowflake_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._snowflake_init(self.snowflake_menu_sel)
    elif key == ord("q") or key == 27:
        self.snowflake_menu = False
        self._flash("Snowflake Growth cancelled")
    return True



def _handle_snowflake_key(self, key: int) -> bool:
    """Handle input in active Snowflake Growth simulation."""
    if key == ord("q") or key == 27:
        self._exit_snowflake_mode()
        return True
    if key == ord(" "):
        self.snowflake_running = not self.snowflake_running
        return True
    if key == ord("n") or key == ord("."):
        self._snowflake_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.SNOWFLAKE_PRESETS) if p[0] == self.snowflake_preset_name),
            0,
        )
        self._snowflake_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.snowflake_mode = False
        self.snowflake_running = False
        self.snowflake_menu = True
        self.snowflake_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.snowflake_steps_per_frame) if self.snowflake_steps_per_frame in choices else 0
        self.snowflake_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.snowflake_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.snowflake_steps_per_frame) if self.snowflake_steps_per_frame in choices else 0
        self.snowflake_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.snowflake_steps_per_frame} steps/frame")
        return True
    # Alpha controls: a/A to decrease/increase deposition rate
    if key == ord("a"):
        self.snowflake_alpha = max(0.01, self.snowflake_alpha - 0.05)
        self._flash(f"Alpha (deposition): {self.snowflake_alpha:.2f}")
        return True
    if key == ord("A"):
        self.snowflake_alpha = min(1.0, self.snowflake_alpha + 0.05)
        self._flash(f"Alpha (deposition): {self.snowflake_alpha:.2f}")
        return True
    # Diffusion rate controls: d/D
    if key == ord("d"):
        self.snowflake_mu = max(0.05, self.snowflake_mu - 0.05)
        self._flash(f"Diffusion rate (μ): {self.snowflake_mu:.2f}")
        return True
    if key == ord("D"):
        self.snowflake_mu = min(1.0, self.snowflake_mu + 0.05)
        self._flash(f"Diffusion rate (μ): {self.snowflake_mu:.2f}")
        return True
    # Toggle 6-fold symmetry: s
    if key == ord("s"):
        self.snowflake_symmetric = not self.snowflake_symmetric
        label = "ON" if self.snowflake_symmetric else "OFF"
        self._flash(f"6-fold symmetry: {label}")
        return True
    return True



def _draw_snowflake_menu(self, max_y: int, max_x: int):
    """Draw the Snowflake Growth preset selection menu."""
    self.stdscr.erase()
    title = "── Snowflake Growth (Reiter Crystal) ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, alpha, beta, gamma, mu, sym) in enumerate(self.SNOWFLAKE_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.snowflake_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.snowflake_menu_sel else curses.color_pair(7)
        sym_tag = "❄" if sym else "~"
        line = f"{marker}{name:22s} α={alpha:<5.2f} β={beta:<5.2f} μ={mu:<4.2f} {sym_tag}  {desc}"
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



def _draw_snowflake(self, max_y: int, max_x: int):
    """Draw the active Snowflake Growth simulation."""
    self.stdscr.erase()
    frozen = self.snowflake_frozen
    vapor = self.snowflake_vapor
    rows, cols = self.snowflake_rows, self.snowflake_cols
    state = "▶ RUNNING" if self.snowflake_running else "⏸ PAUSED"
    sym_label = "❄ 6-fold" if self.snowflake_symmetric else "~ free"

    # Title bar
    title = (f" ❄ Snowflake: {self.snowflake_preset_name}  |  step {self.snowflake_generation}"
             f"  |  {sym_label}  |  frozen={self.snowflake_frozen_count}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    # Precompute frozen-neighbor counts for crystal edge rendering
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            sx = c * 2
            sy = 1 + r
            if frozen[r][c]:
                # Count frozen neighbors to determine crystal interior vs edge
                fn = 0
                for nr, nc in self._snowflake_hex_neighbors(r, c):
                    if 0 <= nr < rows and 0 <= nc < cols and frozen[nr][nc]:
                        fn += 1
                if fn >= 5:
                    # Deep interior — solid bright white
                    ch = "██"
                    attr = curses.color_pair(7) | curses.A_BOLD
                elif fn >= 3:
                    # Interior — bright cyan
                    ch = "██"
                    attr = curses.color_pair(6) | curses.A_BOLD
                else:
                    # Crystal edge / tip — highlighted
                    ch = "▓▓"
                    attr = curses.color_pair(4) | curses.A_BOLD
                try:
                    self.stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass
            else:
                v = vapor[r][c]
                if v >= 0.8:
                    try:
                        self.stdscr.addstr(sy, sx, "░░", curses.color_pair(4))
                    except curses.error:
                        pass
                elif v >= 0.5:
                    try:
                        self.stdscr.addstr(sy, sx, "··", curses.color_pair(4) | curses.A_DIM)
                    except curses.error:
                        pass
                elif v >= 0.3:
                    try:
                        self.stdscr.addstr(sy, sx, "  ", curses.color_pair(4) | curses.A_DIM)
                    except curses.error:
                        pass
                # Very low vapor: leave blank (dark background)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Step {self.snowflake_generation}  |  α={self.snowflake_alpha:.2f}"
                f"  β={self.snowflake_beta:.2f}  μ={self.snowflake_mu:.2f}"
                f"  γ={self.snowflake_gamma:.4f}"
                f"  |  frozen={self.snowflake_frozen_count}"
                f"  |  steps/f={self.snowflake_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [a/A]=α-/+ [d/D]=μ-/+ [s]=symmetry [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Predator-Prey (Lotka-Volterra) Ecosystem — Mode J
# ══════════════════════════════════════════════════════════════════════

LV_PRESETS = [
    # (name, description, grass_regrow, prey_gain, pred_gain,
    #  prey_breed, pred_breed, prey_init_e, pred_init_e,
    #  prey_density, pred_density)
    ("Classic Oscillation",
     "Balanced ecosystem with clear population cycles",
     5, 4, 8, 6, 10, 4, 8, 0.25, 0.08),
    ("Predator Boom",
     "Many predators — prey crash then predator starvation",
     4, 4, 10, 6, 12, 4, 10, 0.20, 0.15),
    ("Prey Paradise",
     "Few predators, abundant grass — prey explosion",
     3, 5, 8, 5, 10, 5, 8, 0.30, 0.03),
    ("Fast Dynamics",
     "Quick breed cycles — rapid oscillations",
     2, 3, 6, 4, 7, 3, 6, 0.25, 0.10),
    ("Sparse Savanna",
     "Slow grass regrowth — fragile ecosystem",
     12, 6, 10, 8, 14, 5, 10, 0.15, 0.05),
    ("Dense Jungle",
     "Fast grass, many creatures — chaotic dynamics",
     2, 4, 7, 5, 8, 4, 7, 0.35, 0.12),
    ("Extinction Edge",
     "Predators barely viable — boom-bust extinction risk",
     6, 4, 6, 6, 14, 4, 6, 0.20, 0.06),
    ("Stable Coexistence",
     "Tuned for long-term stable oscillations",
     4, 5, 9, 7, 12, 5, 9, 0.22, 0.07),
]




def register(App):
    """Register snowflake mode methods on the App class."""
    App._enter_snowflake_mode = _enter_snowflake_mode
    App._exit_snowflake_mode = _exit_snowflake_mode
    App._snowflake_hex_neighbors = _snowflake_hex_neighbors
    App._snowflake_init = _snowflake_init
    App._snowflake_hex_to_axial = _snowflake_hex_to_axial
    App._snowflake_axial_to_offset = _snowflake_axial_to_offset
    App._snowflake_symmetric_points = _snowflake_symmetric_points
    App._snowflake_step = _snowflake_step
    App._handle_snowflake_menu_key = _handle_snowflake_menu_key
    App._handle_snowflake_key = _handle_snowflake_key
    App._draw_snowflake_menu = _draw_snowflake_menu
    App._draw_snowflake = _draw_snowflake

