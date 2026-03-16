"""Mode: spinice — Spin Ice & Emergent Magnetic Monopoles simulation."""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

SPINICE_PRESETS = [
    # (name, description, preset_id)
    ("Equilibrium Ice",
     "Thermal fluctuations at ice-rule ground state — 2-in/2-out everywhere",
     "equilibrium"),
    ("Monopole Gas",
     "High-temperature Coulomb plasma of emergent monopoles",
     "monopole_gas"),
    ("Field Quench",
     "Sudden applied field drives monopole avalanche from ordered state",
     "field_quench"),
    ("Dirac Strings",
     "Track string tension between monopole-antimonopole pairs",
     "dirac_strings"),
    ("Kagome Ice",
     "Triangular frustrated variant with 2-in/1-out ice rules",
     "kagome"),
    ("Pauling Entropy",
     "Measure residual entropy of the ice manifold at low T",
     "pauling"),
]


# ══════════════════════════════════════════════════════════════════════
#  Square-ice lattice helpers
# ══════════════════════════════════════════════════════════════════════
# The lattice is a square grid of vertices. Each edge carries a spin (arrow).
# Horizontal edges: spinice_hedge[r][c] = +1 (right) or -1 (left)
#   Edge (r,c) connects vertex (r,c) to vertex (r,c+1)
# Vertical edges:   spinice_vedge[r][c] = +1 (down) or -1 (up)
#   Edge (r,c) connects vertex (r,c) to vertex (r+1,c)
#
# "2-in / 2-out" ice rule at vertex (r,c):
#   in-arrows = arrows pointing INTO the vertex
#   Horizontal: hedge[r][c-1]==+1 (right into vertex) and hedge[r][c]==-1 (left into vertex)
#   Vertical:   vedge[r-1][c]==+1 (down into vertex) and vedge[r][c]==-1 (up into vertex)
#   charge = (number of out-arrows) - (number of in-arrows)
#   Ice rule satisfied when charge == 0.
#   charge != 0 => monopole (positive if more out, negative if more in).


def _vertex_charge(self, r, c):
    """Compute vertex charge at (r, c). 0 = ice rule satisfied."""
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    hedge = self.spinice_hedge
    vedge = self.spinice_vedge
    # Count arrows pointing OUT of vertex (r, c)
    out_count = 0
    # Right edge from this vertex
    if c < cols - 1:
        if hedge[r][c] == +1:
            out_count += 1
    # Left edge into this vertex (from vertex at c-1)
    if c > 0:
        if hedge[r][c - 1] == -1:
            out_count += 1
    # Down edge from this vertex
    if r < rows - 1:
        if vedge[r][c] == +1:
            out_count += 1
    # Up edge into this vertex (from vertex at r-1)
    if r > 0:
        if vedge[r - 1][c] == -1:
            out_count += 1
    # For boundary vertices, count available edges
    total_edges = 0
    if c < cols - 1:
        total_edges += 1
    if c > 0:
        total_edges += 1
    if r < rows - 1:
        total_edges += 1
    if r > 0:
        total_edges += 1
    in_count = total_edges - out_count
    return out_count - in_count


def _spinice_count_monopoles(self):
    """Count monopoles and antimonopoles across the lattice."""
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    pos = 0
    neg = 0
    for r in range(rows):
        for c in range(cols):
            q = self._vertex_charge(r, c)
            if q > 0:
                pos += 1
            elif q < 0:
                neg += 1
    return pos, neg


def _spinice_ice_fraction(self):
    """Fraction of vertices satisfying ice rules."""
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    total = rows * cols
    satisfied = 0
    for r in range(rows):
        for c in range(cols):
            if self._vertex_charge(r, c) == 0:
                satisfied += 1
    return satisfied / max(1, total)


def _spinice_total_energy(self):
    """Compute total energy: J * sum over edges + Coulomb between monopoles + field coupling."""
    J = self.spinice_J
    h_field = self.spinice_field
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    hedge = self.spinice_hedge
    vedge = self.spinice_vedge
    energy = 0.0
    # Near-neighbor ice-rule energy: penalize ice-rule violations
    for r in range(rows):
        for c in range(cols):
            q = self._vertex_charge(r, c)
            energy += J * q * q
    # Field coupling: field favors all horizontal arrows pointing right
    if abs(h_field) > 1e-9:
        for r in range(rows):
            for c in range(cols - 1):
                energy -= h_field * hedge[r][c]
    return energy


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _enter_spinice_mode(self):
    """Enter Spin Ice mode — show preset menu."""
    self.spinice_menu = True
    self.spinice_menu_sel = 0
    self._flash("Spin Ice & Emergent Monopoles — select a scenario")


def _exit_spinice_mode(self):
    """Exit Spin Ice mode."""
    self.spinice_mode = False
    self.spinice_menu = False
    self.spinice_running = False
    self._flash("Spin Ice mode OFF")


def _spinice_init(self, preset_idx: int):
    """Initialize Spin Ice simulation with the given preset."""
    name, _desc, preset_id = self.SPINICE_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    # Each vertex takes ~3 cols and ~2 rows for display
    vcols = max(4, (max_x - 2) // 4)
    vrows = max(4, (max_y - 4) // 2)
    self.spinice_vrows = vrows
    self.spinice_vcols = vcols
    self.spinice_preset_name = name
    self.spinice_preset_id = preset_id
    self.spinice_generation = 0
    self.spinice_running = False
    self.spinice_steps_per_frame = 1
    self.spinice_show_strings = (preset_id == "dirac_strings")
    self.spinice_show_charges = True

    # Physics parameters
    self.spinice_J = 4.0       # ice-rule coupling
    self.spinice_field = 0.0   # applied field
    self.spinice_temperature = 1.0

    # Kagome variant flag
    self.spinice_kagome = (preset_id == "kagome")

    if preset_id == "equilibrium":
        self.spinice_temperature = 0.5
        self._spinice_init_ice_state()
    elif preset_id == "monopole_gas":
        self.spinice_temperature = 8.0
        self._spinice_init_random()
    elif preset_id == "field_quench":
        self.spinice_temperature = 1.0
        self.spinice_field = 0.0
        self._spinice_init_ice_state()
        # After a few steps, field will be applied via key or auto
        self.spinice_quench_step = 20
    elif preset_id == "dirac_strings":
        self.spinice_temperature = 1.5
        self._spinice_init_ice_state()
        # Inject a few monopole pairs
        self._spinice_inject_pairs(3)
    elif preset_id == "kagome":
        self.spinice_temperature = 1.0
        self._spinice_init_random()
    elif preset_id == "pauling":
        self.spinice_temperature = 0.01
        self._spinice_init_ice_state()
    else:
        self.spinice_temperature = 1.0
        self._spinice_init_random()

    # Compute initial stats
    self._spinice_compute_stats()

    self.spinice_mode = True
    self.spinice_menu = False
    self._flash(f"Spin Ice: {name} — Space to start")


def _spinice_init_random(self):
    """Initialize with random arrow orientations."""
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    self.spinice_hedge = [
        [random.choice((-1, 1)) for _ in range(cols - 1)]
        for _ in range(rows)
    ]
    self.spinice_vedge = [
        [random.choice((-1, 1)) for _ in range(cols)]
        for _ in range(rows - 1)
    ]


def _spinice_init_ice_state(self):
    """Initialize in a perfect ice-rule ground state (2-in/2-out everywhere).

    Uses a simple pattern: alternating rows of right/left arrows,
    with vertical arrows chosen to satisfy ice rules.
    """
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    # Horizontal: alternate direction by row
    self.spinice_hedge = []
    for r in range(rows):
        row_edges = []
        for c in range(cols - 1):
            if (r + c) % 2 == 0:
                row_edges.append(1)   # right
            else:
                row_edges.append(-1)  # left
        self.spinice_hedge.append(row_edges)
    # Vertical: choose to satisfy ice rules
    self.spinice_vedge = []
    for r in range(rows - 1):
        row_edges = []
        for c in range(cols):
            if (r + c) % 2 == 0:
                row_edges.append(1)   # down
            else:
                row_edges.append(-1)  # up
        self.spinice_vedge.append(row_edges)


def _spinice_inject_pairs(self, n_pairs):
    """Inject monopole-antimonopole pairs by flipping short edge chains."""
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    for _ in range(n_pairs):
        # Pick a random interior horizontal edge and flip it
        r = random.randint(1, rows - 2)
        c = random.randint(1, cols - 3)
        self.spinice_hedge[r][c] *= -1


# ══════════════════════════════════════════════════════════════════════
#  Physics step
# ══════════════════════════════════════════════════════════════════════

def _spinice_compute_stats(self):
    """Compute summary statistics."""
    pos, neg = self._spinice_count_monopoles()
    self.spinice_n_positive = pos
    self.spinice_n_negative = neg
    self.spinice_ice_frac = self._spinice_ice_fraction()
    self.spinice_energy = self._spinice_total_energy()


def _spinice_step(self):
    """Advance by one Monte Carlo sweep — attempt to flip each edge once."""
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    T = self.spinice_temperature
    J = self.spinice_J
    h_field = self.spinice_field
    hedge = self.spinice_hedge
    vedge = self.spinice_vedge
    rand = random.random

    if T > 0:
        inv_T = 1.0 / T
    else:
        inv_T = 1e10

    # Field quench: apply field after quench_step
    if self.spinice_preset_id == "field_quench":
        if self.spinice_generation == getattr(self, 'spinice_quench_step', 20):
            self.spinice_field = 3.0
            h_field = 3.0
            self._flash("Field quench applied! h=3.0")

    # Attempt to flip each horizontal edge
    n_hedge = rows * max(0, cols - 1)
    n_vedge = max(0, rows - 1) * cols
    n_total = n_hedge + n_vedge

    for _ in range(n_total):
        if rand() < n_hedge / max(1, n_total):
            # Pick random horizontal edge
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 2)
            # Compute energy change from flipping hedge[r][c]
            # Vertices affected: (r, c) and (r, c+1)
            q1_before = self._vertex_charge(r, c)
            q2_before = self._vertex_charge(r, c + 1)
            e_before = J * (q1_before * q1_before + q2_before * q2_before)
            e_before -= h_field * hedge[r][c]
            # Flip
            hedge[r][c] *= -1
            q1_after = self._vertex_charge(r, c)
            q2_after = self._vertex_charge(r, c + 1)
            e_after = J * (q1_after * q1_after + q2_after * q2_after)
            e_after -= h_field * hedge[r][c]
            dE = e_after - e_before
            if dE > 0 and rand() >= math.exp(-dE * inv_T):
                hedge[r][c] *= -1  # reject
        else:
            # Pick random vertical edge
            r = random.randint(0, rows - 2)
            c = random.randint(0, cols - 1)
            q1_before = self._vertex_charge(r, c)
            q2_before = self._vertex_charge(r + 1, c)
            e_before = J * (q1_before * q1_before + q2_before * q2_before)
            # Flip
            vedge[r][c] *= -1
            q1_after = self._vertex_charge(r, c)
            q2_after = self._vertex_charge(r + 1, c)
            e_after = J * (q1_after * q1_after + q2_after * q2_after)
            dE = e_after - e_before
            if dE > 0 and rand() >= math.exp(-dE * inv_T):
                vedge[r][c] *= -1  # reject

    self.spinice_generation += 1
    self._spinice_compute_stats()


# ══════════════════════════════════════════════════════════════════════
#  Key handling
# ══════════════════════════════════════════════════════════════════════

def _handle_spinice_menu_key(self, key: int) -> bool:
    """Handle input in Spin Ice preset menu."""
    presets = self.SPINICE_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.spinice_menu_sel = (self.spinice_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.spinice_menu_sel = (self.spinice_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._spinice_init(self.spinice_menu_sel)
    elif key == ord("q") or key == 27:
        self.spinice_menu = False
        self._flash("Spin Ice cancelled")
    return True


def _handle_spinice_key(self, key: int) -> bool:
    """Handle input in active Spin Ice simulation."""
    if key == ord("q") or key == 27:
        self._exit_spinice_mode()
        return True
    if key == ord(" "):
        self.spinice_running = not self.spinice_running
        return True
    if key == ord("n") or key == ord("."):
        self._spinice_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.SPINICE_PRESETS) if p[0] == self.spinice_preset_name),
            0,
        )
        self._spinice_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.spinice_mode = False
        self.spinice_running = False
        self.spinice_menu = True
        self.spinice_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.spinice_steps_per_frame) if self.spinice_steps_per_frame in choices else 0
        self.spinice_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.spinice_steps_per_frame} sweeps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.spinice_steps_per_frame) if self.spinice_steps_per_frame in choices else 0
        self.spinice_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.spinice_steps_per_frame} sweeps/frame")
        return True
    # Temperature controls
    if key == ord("t"):
        self.spinice_temperature = max(0.01, self.spinice_temperature - 0.2)
        self._flash(f"Temperature: {self.spinice_temperature:.2f}")
        return True
    if key == ord("T"):
        self.spinice_temperature = min(20.0, self.spinice_temperature + 0.2)
        self._flash(f"Temperature: {self.spinice_temperature:.2f}")
        return True
    # Field controls
    if key == ord("f"):
        self.spinice_field = max(-5.0, self.spinice_field - 0.2)
        self._flash(f"Applied field: {self.spinice_field:.2f}")
        return True
    if key == ord("F"):
        self.spinice_field = min(5.0, self.spinice_field + 0.2)
        self._flash(f"Applied field: {self.spinice_field:.2f}")
        return True
    # Toggle Dirac string display
    if key == ord("d") or key == ord("D"):
        self.spinice_show_strings = not self.spinice_show_strings
        self._flash(f"Dirac strings: {'ON' if self.spinice_show_strings else 'OFF'}")
        return True
    # Toggle charge display
    if key == ord("c") or key == ord("C"):
        self.spinice_show_charges = not self.spinice_show_charges
        self._flash(f"Charge display: {'ON' if self.spinice_show_charges else 'OFF'}")
        return True
    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing
# ══════════════════════════════════════════════════════════════════════

def _draw_spinice_menu(self, max_y: int, max_x: int):
    """Draw the Spin Ice preset selection menu."""
    self.stdscr.erase()
    title = "── Spin Ice & Emergent Magnetic Monopoles ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(self.SPINICE_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 4:
            break
        marker = "▸ " if i == self.spinice_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.spinice_menu_sel else curses.color_pair(7)
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(y, 3, line[:max_x - 4], attr)
        except curses.error:
            pass
        # Description on next line
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Legend
    legend_y = max_y - 3
    if legend_y > 0:
        legend = "Spin Ice: arrows on lattice edges obey 2-in/2-out ice rules."
        try:
            self.stdscr.addstr(legend_y, 3, legend[:max_x - 4], curses.color_pair(6))
        except curses.error:
            pass
        legend2 = "Violations = emergent magnetic monopoles connected by Dirac strings."
        try:
            self.stdscr.addstr(legend_y + 1, 3, legend2[:max_x - 4], curses.color_pair(6))
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_spinice(self, max_y: int, max_x: int):
    """Draw the active Spin Ice simulation."""
    self.stdscr.erase()
    rows = self.spinice_vrows
    cols = self.spinice_vcols
    hedge = self.spinice_hedge
    vedge = self.spinice_vedge
    state = "▶ RUNNING" if self.spinice_running else "⏸ PAUSED"

    # Title bar
    title = (f" Spin Ice: {self.spinice_preset_name}  |  sweep {self.spinice_generation}"
             f"  |  T={self.spinice_temperature:.2f}  h={self.spinice_field:.2f}"
             f"  |  +mono={self.spinice_n_positive} −mono={self.spinice_n_negative}"
             f"  |  ice={self.spinice_ice_frac:.1%}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Layout: each vertex gets a 4x2 cell
    # Vertex at screen position (1 + r*2, c*4)
    # Horizontal edge arrow at (1 + r*2, c*4 + 1) to (1 + r*2, c*4 + 3)
    # Vertical edge arrow at (1 + r*2 + 1, c*4)

    view_rows = min(rows, (max_y - 4) // 2)
    view_cols = min(cols, (max_x - 2) // 4)

    # Draw edges first (arrows)
    # Horizontal edges
    for r in range(view_rows):
        sy = 1 + r * 2
        if sy >= max_y - 2:
            break
        for c in range(min(view_cols - 1, cols - 1)):
            sx = c * 4 + 2
            if sx + 1 >= max_x - 1:
                break
            arrow = hedge[r][c]
            ch = "→" if arrow == 1 else "←"
            # Color: ice-rule edges in cyan, violation-adjacent in yellow
            attr = curses.color_pair(6)
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Vertical edges
    for r in range(min(view_rows - 1, rows - 1)):
        sy = 1 + r * 2 + 1
        if sy >= max_y - 2:
            break
        for c in range(view_cols):
            sx = c * 4
            if sx >= max_x - 1:
                break
            arrow = vedge[r][c]
            ch = "↓" if arrow == 1 else "↑"
            attr = curses.color_pair(6)
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Draw vertices with charge coloring
    if self.spinice_show_charges:
        for r in range(view_rows):
            sy = 1 + r * 2
            if sy >= max_y - 2:
                break
            for c in range(view_cols):
                sx = c * 4
                if sx >= max_x - 1:
                    break
                q = self._vertex_charge(r, c)
                if q == 0:
                    # Ice-rule satisfied — dim dot
                    ch = "·"
                    attr = curses.color_pair(7) | curses.A_DIM
                elif q > 0:
                    # Positive monopole — bright red
                    ch = "⊕"
                    attr = curses.color_pair(1) | curses.A_BOLD
                else:
                    # Negative monopole (antimonopole) — bright blue
                    ch = "⊖"
                    attr = curses.color_pair(4) | curses.A_BOLD
                try:
                    self.stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass

    # Draw Dirac strings between monopole pairs
    if self.spinice_show_strings:
        _draw_spinice_strings(self, max_y, max_x, view_rows, view_cols)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        pauling = math.log(3 / 2) / math.log(2) if self.spinice_ice_frac > 0.99 else 0.0
        info = (f" Sweep {self.spinice_generation}  |  T={self.spinice_temperature:.2f}"
                f"  h={self.spinice_field:.2f}"
                f"  |  +monopoles={self.spinice_n_positive}"
                f"  −monopoles={self.spinice_n_negative}"
                f"  |  ice={self.spinice_ice_frac:.1%}"
                f"  |  E={self.spinice_energy:.1f}"
                f"  |  sweeps/f={self.spinice_steps_per_frame}")
        if self.spinice_preset_id == "pauling" and self.spinice_ice_frac > 0.99:
            info += f"  S/kB≈{pauling:.4f}"
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
            hint = " [Space]=play [n]=step [t/T]=temp [f/F]=field [d]=strings [c]=charges [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_spinice_strings(self, max_y, max_x, view_rows, view_cols):
    """Draw Dirac strings connecting monopole-antimonopole pairs."""
    # Find all monopoles
    monopoles_pos = []
    monopoles_neg = []
    for r in range(view_rows):
        for c in range(view_cols):
            q = self._vertex_charge(r, c)
            if q > 0:
                monopoles_pos.append((r, c))
            elif q < 0:
                monopoles_neg.append((r, c))

    # Simple greedy pairing: connect nearest positive to negative
    used_neg = set()
    for pr, pc in monopoles_pos:
        best_dist = float('inf')
        best_idx = -1
        for idx, (nr, nc) in enumerate(monopoles_neg):
            if idx in used_neg:
                continue
            dist = abs(pr - nr) + abs(pc - nc)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        if best_idx >= 0:
            used_neg.add(best_idx)
            nr, nc = monopoles_neg[best_idx]
            # Draw string as dotted line between the two
            _draw_string_line(self, pr, pc, nr, nc, max_y, max_x)


def _draw_string_line(self, r1, c1, r2, c2, max_y, max_x):
    """Draw a dotted line between two vertex positions to represent a Dirac string."""
    steps = max(abs(r2 - r1), abs(c2 - c1))
    if steps == 0:
        return
    for i in range(1, steps):
        t = i / steps
        r = r1 + t * (r2 - r1)
        c = c1 + t * (c2 - c1)
        sy = 1 + int(round(r)) * 2
        sx = int(round(c)) * 4
        if 1 <= sy < max_y - 2 and 0 <= sx < max_x - 1:
            try:
                self.stdscr.addstr(sy, sx, "∙",
                                   curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register spin_ice mode methods on the App class."""
    App.SPINICE_PRESETS = SPINICE_PRESETS
    App._enter_spinice_mode = _enter_spinice_mode
    App._exit_spinice_mode = _exit_spinice_mode
    App._spinice_init = _spinice_init
    App._spinice_init_random = _spinice_init_random
    App._spinice_init_ice_state = _spinice_init_ice_state
    App._spinice_inject_pairs = _spinice_inject_pairs
    App._vertex_charge = _vertex_charge
    App._spinice_count_monopoles = _spinice_count_monopoles
    App._spinice_ice_fraction = _spinice_ice_fraction
    App._spinice_total_energy = _spinice_total_energy
    App._spinice_compute_stats = _spinice_compute_stats
    App._spinice_step = _spinice_step
    App._handle_spinice_menu_key = _handle_spinice_menu_key
    App._handle_spinice_key = _handle_spinice_key
    App._draw_spinice_menu = _draw_spinice_menu
    App._draw_spinice = _draw_spinice
    App._draw_spinice_strings = _draw_spinice_strings
