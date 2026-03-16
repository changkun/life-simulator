"""Mode: quake — Earthquake & Seismic Wave Propagation simulation.

Burridge-Knopoff spring-block fault model where tectonic stress accumulates
on a heterogeneous fault plane until stick-slip ruptures cascade as
earthquakes, radiating P-waves and S-waves through layered crust.

Emergent phenomena:
  - Gutenberg-Richter frequency-magnitude scaling (power-law statistics)
  - Omori's law aftershock clustering
  - Characteristic earthquake cycles
  - Self-organized criticality
"""
import curses
import math
import random
import time


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

QUAKE_PRESETS = [
    ("Strike-Slip Fault",
     "San Andreas-style lateral rupture on a planar fault",
     "strike_slip"),
    ("Subduction Zone",
     "Megathrust with deep coupling and wide rupture area",
     "subduction"),
    ("Swarm Seismicity",
     "Diffuse volcanic/geothermal earthquake cluster",
     "swarm"),
    ("Tsunami Generation",
     "Seafloor displacement drives shallow-water wave propagation",
     "tsunami"),
    ("Induced Seismicity",
     "Injection-triggered fault reactivation from fluid pressure",
     "induced"),
    ("Coulomb Stress Transfer",
     "One earthquake triggers the next via static stress changes",
     "coulomb"),
]


# ══════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════

def _quake_make_fault(self):
    """Create heterogeneous fault plane: 2D grid of spring-blocks.

    Each block has:
      stress   - accumulated shear stress
      strength - static friction threshold (heterogeneous)
      slip     - dynamic slip amount when rupture occurs
      failed   - True if currently slipping this step
    """
    rows = self.quake_rows
    cols = self.quake_cols
    base_strength = self.quake_base_strength
    heterogeneity = self.quake_heterogeneity
    rng = random.random

    stress = []
    strength = []
    slip = []
    failed = []
    for r in range(rows):
        sr, st, sl, fl = [], [], [], []
        for c in range(cols):
            sr.append(rng() * base_strength * 0.3)
            st.append(base_strength * (1.0 + heterogeneity * (rng() - 0.5)))
            sl.append(0.0)
            fl.append(False)
        stress.append(sr)
        strength.append(st)
        slip.append(sl)
        failed.append(fl)
    self.quake_stress = stress
    self.quake_strength = strength
    self.quake_slip = slip
    self.quake_failed = failed


def _quake_make_wave_field(self):
    """Create seismic wave propagation grid (P-wave and S-wave amplitudes)."""
    rows = self.quake_wrows
    cols = self.quake_wcols
    self.quake_pwave = [[0.0] * cols for _ in range(rows)]
    self.quake_swave = [[0.0] * cols for _ in range(rows)]
    self.quake_pwave_prev = [[0.0] * cols for _ in range(rows)]
    self.quake_swave_prev = [[0.0] * cols for _ in range(rows)]


def _quake_magnitude(self, n_blocks):
    """Convert number of ruptured blocks to approximate magnitude."""
    if n_blocks <= 0:
        return 0.0
    # M ~ (2/3) * log10(area) + const; scale so single block ~ M1
    return (2.0 / 3.0) * math.log10(n_blocks) + 1.0


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _enter_quake_mode(self):
    """Enter Earthquake mode — show preset menu."""
    self.quake_menu = True
    self.quake_menu_sel = 0
    self._flash("Earthquake & Seismic Waves — select a scenario")


def _exit_quake_mode(self):
    """Exit Earthquake mode."""
    self.quake_mode = False
    self.quake_menu = False
    self.quake_running = False
    self._flash("Earthquake mode OFF")


def _quake_init(self, preset_idx: int):
    """Initialize earthquake simulation with the given preset."""
    name, _desc, preset_id = self.QUAKE_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()

    # Fault grid dimensions
    cols = max(8, (max_x - 2) // 2)
    rows = max(6, (max_y - 5) // 2)
    self.quake_rows = rows
    self.quake_cols = cols

    # Wave field matches display area
    self.quake_wrows = max_y - 3
    self.quake_wcols = max_x - 1

    self.quake_preset_name = name
    self.quake_preset_id = preset_id
    self.quake_generation = 0
    self.quake_running = False
    self.quake_steps_per_frame = 1

    # Physics parameters (defaults)
    self.quake_tectonic_rate = 0.02     # stress loading rate per step
    self.quake_base_strength = 1.0      # mean static friction threshold
    self.quake_heterogeneity = 0.4      # strength variation factor
    self.quake_coupling = 0.15          # neighbor spring coupling
    self.quake_dynamic_drop = 0.85      # fraction of stress dropped on slip
    self.quake_damping = 0.96           # wave damping per step
    self.quake_p_speed = 1.5            # P-wave speed (cells/step)
    self.quake_s_speed = 0.9            # S-wave speed (cells/step)

    # Display mode: "fault" or "waves"
    self.quake_view = "fault"

    # Statistics
    self.quake_total_events = 0
    self.quake_largest_mag = 0.0
    self.quake_last_mag = 0.0
    self.quake_event_sizes = []       # for GR statistics
    self.quake_recent_events = []     # (generation, magnitude) for Omori
    self.quake_aftershock_count = 0

    # Tsunami-specific state
    self.quake_tsunami_h = None
    self.quake_tsunami_v = None

    # Preset-specific tuning
    if preset_id == "strike_slip":
        self.quake_tectonic_rate = 0.02
        self.quake_coupling = 0.15
        self.quake_heterogeneity = 0.4
    elif preset_id == "subduction":
        self.quake_tectonic_rate = 0.012
        self.quake_coupling = 0.25
        self.quake_base_strength = 1.4
        self.quake_heterogeneity = 0.3
    elif preset_id == "swarm":
        self.quake_tectonic_rate = 0.035
        self.quake_coupling = 0.08
        self.quake_base_strength = 0.7
        self.quake_heterogeneity = 0.6
    elif preset_id == "tsunami":
        self.quake_tectonic_rate = 0.015
        self.quake_coupling = 0.22
        self.quake_base_strength = 1.3
        self.quake_view = "waves"
        # Initialize shallow-water tsunami field
        wr = self.quake_wrows
        wc = self.quake_wcols
        self.quake_tsunami_h = [[0.0] * wc for _ in range(wr)]
        self.quake_tsunami_v = [[0.0] * wc for _ in range(wr)]
    elif preset_id == "induced":
        self.quake_tectonic_rate = 0.005
        self.quake_coupling = 0.12
        self.quake_base_strength = 1.1
        self.quake_heterogeneity = 0.3
        self.quake_injection_rate = 0.008
        self.quake_injection_r = rows // 2
        self.quake_injection_c = cols // 2
        self.quake_injection_radius = max(2, min(rows, cols) // 5)
    elif preset_id == "coulomb":
        self.quake_tectonic_rate = 0.018
        self.quake_coupling = 0.20
        self.quake_heterogeneity = 0.35
        self.quake_coulomb_transfer = 0.12

    # Build fault and wave grids
    self._quake_make_fault()
    self._quake_make_wave_field()

    self.quake_mode = True
    self.quake_menu = False
    self._flash(f"Earthquake: {name} — Space to start")


# ══════════════════════════════════════════════════════════════════════
#  Physics step
# ══════════════════════════════════════════════════════════════════════

def _quake_step(self):
    """Advance simulation by one time step."""
    rows = self.quake_rows
    cols = self.quake_cols
    stress = self.quake_stress
    strength = self.quake_strength
    failed = self.quake_failed
    slip = self.quake_slip
    coupling = self.quake_coupling
    drop = self.quake_dynamic_drop
    preset_id = self.quake_preset_id
    rand = random.random

    # ── 1. Tectonic loading: add stress uniformly ──
    rate = self.quake_tectonic_rate
    for r in range(rows):
        for c in range(cols):
            stress[r][c] += rate
            failed[r][c] = False
            slip[r][c] = 0.0

    # ── 1b. Induced seismicity: pore pressure reduces effective strength ──
    if preset_id == "induced":
        inj_r = self.quake_injection_r
        inj_c = self.quake_injection_c
        inj_rad = self.quake_injection_radius
        inj_rate = self.quake_injection_rate
        for r in range(max(0, inj_r - inj_rad), min(rows, inj_r + inj_rad + 1)):
            for c in range(max(0, inj_c - inj_rad), min(cols, inj_c + inj_rad + 1)):
                dist = math.sqrt((r - inj_r) ** 2 + (c - inj_c) ** 2)
                if dist <= inj_rad:
                    pressure = inj_rate * (1.0 - dist / (inj_rad + 1))
                    stress[r][c] += pressure

    # ── 2. Check for failures and cascade ──
    total_ruptured = 0
    rupture_r_sum = 0.0
    rupture_c_sum = 0.0
    cascade = True
    iteration = 0
    max_iterations = 50

    while cascade and iteration < max_iterations:
        cascade = False
        iteration += 1
        for r in range(rows):
            for c in range(cols):
                if stress[r][c] >= strength[r][c] and not failed[r][c]:
                    # Block ruptures: stick-slip
                    failed[r][c] = True
                    cascade = True
                    total_ruptured += 1
                    rupture_r_sum += r
                    rupture_c_sum += c

                    # Stress drop
                    released = stress[r][c] * drop
                    slip[r][c] = released
                    stress[r][c] -= released

                    # Transfer stress to neighbors (spring coupling)
                    transfer = released * coupling
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            stress[nr][nc] += transfer

                    # Reset strength with some randomness (healing)
                    strength[r][c] = self.quake_base_strength * (
                        1.0 + self.quake_heterogeneity * (rand() - 0.5)
                    )

    # ── 2b. Coulomb stress transfer for that preset ──
    if preset_id == "coulomb" and total_ruptured > 0:
        ct = getattr(self, 'quake_coulomb_transfer', 0.12)
        center_r = rupture_r_sum / total_ruptured
        center_c = rupture_c_sum / total_ruptured
        mag = self._quake_magnitude(total_ruptured)
        radius = max(2, int(mag * 2))
        for r in range(max(0, int(center_r) - radius),
                       min(rows, int(center_r) + radius + 1)):
            for c in range(max(0, int(center_c) - radius),
                           min(cols, int(center_c) + radius + 1)):
                if not failed[r][c]:
                    dist = math.sqrt((r - center_r) ** 2 + (c - center_c) ** 2)
                    if dist > 0:
                        # Coulomb lobe pattern: positive along strike, negative off-fault
                        angle = math.atan2(r - center_r, c - center_c)
                        lobe = math.cos(2.0 * angle)
                        delta = ct * mag * lobe / (1.0 + dist)
                        stress[r][c] += delta

    # ── 3. Record event statistics ──
    if total_ruptured > 0:
        mag = self._quake_magnitude(total_ruptured)
        self.quake_total_events += 1
        self.quake_last_mag = mag
        if mag > self.quake_largest_mag:
            self.quake_largest_mag = mag
        self.quake_event_sizes.append(total_ruptured)
        self.quake_recent_events.append((self.quake_generation, mag))
        # Trim history
        if len(self.quake_event_sizes) > 500:
            self.quake_event_sizes = self.quake_event_sizes[-500:]
        if len(self.quake_recent_events) > 200:
            self.quake_recent_events = self.quake_recent_events[-200:]

        # ── 4. Inject seismic waves from rupture ──
        _quake_inject_waves(self, total_ruptured, rupture_r_sum, rupture_c_sum)

        # ── 4b. Tsunami generation ──
        if preset_id == "tsunami" and self.quake_tsunami_h is not None:
            cr = rupture_r_sum / total_ruptured
            cc = rupture_c_sum / total_ruptured
            amp = min(5.0, mag * 0.8)
            wr = self.quake_wrows
            wc = self.quake_wcols
            # Map fault coords to wave coords
            sy = int(cr * wr / max(1, rows))
            sx = int(cc * wc / max(1, cols))
            rad = max(2, int(mag))
            for dr in range(-rad, rad + 1):
                for dc in range(-rad, rad + 1):
                    wy, wx = sy + dr, sx + dc
                    if 0 <= wy < wr and 0 <= wx < wc:
                        dist = math.sqrt(dr * dr + dc * dc)
                        if dist <= rad:
                            self.quake_tsunami_h[wy][wx] += amp * (1.0 - dist / (rad + 1))

    # ── 5. Propagate seismic waves ──
    _quake_propagate_waves(self)

    # ── 5b. Propagate tsunami ──
    if preset_id == "tsunami" and self.quake_tsunami_h is not None:
        _quake_propagate_tsunami(self)

    # ── 6. Count aftershocks (Omori) ──
    gen = self.quake_generation
    self.quake_aftershock_count = sum(
        1 for g, m in self.quake_recent_events
        if gen - g < 30 and gen - g > 0
    )

    self.quake_generation += 1


def _quake_inject_waves(self, n_ruptured, r_sum, c_sum):
    """Inject P-wave and S-wave energy at rupture centroid."""
    if n_ruptured == 0:
        return
    cr = r_sum / n_ruptured
    cc = c_sum / n_ruptured
    rows = self.quake_rows
    cols = self.quake_cols
    wr = self.quake_wrows
    wc = self.quake_wcols
    pwave = self.quake_pwave
    swave = self.quake_swave

    mag = self._quake_magnitude(n_ruptured)
    p_amp = min(8.0, mag * 1.5)
    s_amp = min(6.0, mag * 1.0)

    # Map fault centroid to wave grid
    sy = int(cr * wr / max(1, rows))
    sx = int(cc * wc / max(1, cols))
    rad = max(1, int(mag * 0.8))

    for dr in range(-rad, rad + 1):
        for dc in range(-rad, rad + 1):
            wy, wx = sy + dr, sx + dc
            if 0 <= wy < wr and 0 <= wx < wc:
                dist = math.sqrt(dr * dr + dc * dc)
                if dist <= rad:
                    frac = 1.0 - dist / (rad + 1)
                    pwave[wy][wx] += p_amp * frac
                    swave[wy][wx] += s_amp * frac * 0.7


def _quake_propagate_waves(self):
    """Propagate P-waves and S-waves using simple wave equation on grid."""
    wr = self.quake_wrows
    wc = self.quake_wcols
    damping = self.quake_damping
    c_p = self.quake_p_speed
    c_s = self.quake_s_speed

    # P-wave propagation
    pw = self.quake_pwave
    pw_prev = self.quake_pwave_prev
    pw_new = [[0.0] * wc for _ in range(wr)]
    cp2 = c_p * c_p
    for r in range(1, wr - 1):
        for c in range(1, wc - 1):
            laplacian = (pw[r - 1][c] + pw[r + 1][c] +
                         pw[r][c - 1] + pw[r][c + 1] - 4.0 * pw[r][c])
            pw_new[r][c] = (2.0 * pw[r][c] - pw_prev[r][c] +
                            cp2 * laplacian) * damping
    self.quake_pwave_prev = pw
    self.quake_pwave = pw_new

    # S-wave propagation
    sw = self.quake_swave
    sw_prev = self.quake_swave_prev
    sw_new = [[0.0] * wc for _ in range(wr)]
    cs2 = c_s * c_s
    for r in range(1, wr - 1):
        for c in range(1, wc - 1):
            laplacian = (sw[r - 1][c] + sw[r + 1][c] +
                         sw[r][c - 1] + sw[r][c + 1] - 4.0 * sw[r][c])
            sw_new[r][c] = (2.0 * sw[r][c] - sw_prev[r][c] +
                            cs2 * laplacian) * damping
    self.quake_swave_prev = sw
    self.quake_swave = sw_new


def _quake_propagate_tsunami(self):
    """Simple shallow-water wave propagation for tsunami preset."""
    wr = self.quake_wrows
    wc = self.quake_wcols
    h = self.quake_tsunami_h
    v = self.quake_tsunami_v
    c2 = 0.4  # shallow-water wave speed squared
    damp = 0.995

    h_new = [[0.0] * wc for _ in range(wr)]
    for r in range(1, wr - 1):
        for c in range(1, wc - 1):
            laplacian = (h[r - 1][c] + h[r + 1][c] +
                         h[r][c - 1] + h[r][c + 1] - 4.0 * h[r][c])
            h_new[r][c] = (2.0 * h[r][c] - v[r][c] + c2 * laplacian) * damp
    self.quake_tsunami_v = h
    self.quake_tsunami_h = h_new


# ══════════════════════════════════════════════════════════════════════
#  Key handling
# ══════════════════════════════════════════════════════════════════════

def _handle_quake_menu_key(self, key: int) -> bool:
    """Handle input in Earthquake preset menu."""
    presets = self.QUAKE_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.quake_menu_sel = (self.quake_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.quake_menu_sel = (self.quake_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._quake_init(self.quake_menu_sel)
    elif key == ord("q") or key == 27:
        self.quake_menu = False
        self._flash("Earthquake mode cancelled")
    return True


def _handle_quake_key(self, key: int) -> bool:
    """Handle input in active Earthquake simulation."""
    if key == ord("q") or key == 27:
        self._exit_quake_mode()
        return True
    if key == ord(" "):
        self.quake_running = not self.quake_running
        return True
    if key == ord("n") or key == ord("."):
        self._quake_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.QUAKE_PRESETS)
             if p[0] == self.quake_preset_name), 0)
        self._quake_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.quake_mode = False
        self.quake_running = False
        self.quake_menu = True
        self.quake_menu_sel = 0
        return True
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.quake_steps_per_frame) if self.quake_steps_per_frame in choices else 0
        self.quake_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.quake_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.quake_steps_per_frame) if self.quake_steps_per_frame in choices else 0
        self.quake_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.quake_steps_per_frame} steps/frame")
        return True
    # Tectonic loading rate controls
    if key == ord("t"):
        self.quake_tectonic_rate = max(0.001, self.quake_tectonic_rate - 0.005)
        self._flash(f"Tectonic rate: {self.quake_tectonic_rate:.3f}")
        return True
    if key == ord("T"):
        self.quake_tectonic_rate = min(0.1, self.quake_tectonic_rate + 0.005)
        self._flash(f"Tectonic rate: {self.quake_tectonic_rate:.3f}")
        return True
    # Coupling controls
    if key == ord("c"):
        self.quake_coupling = max(0.01, self.quake_coupling - 0.02)
        self._flash(f"Coupling: {self.quake_coupling:.2f}")
        return True
    if key == ord("C"):
        self.quake_coupling = min(0.5, self.quake_coupling + 0.02)
        self._flash(f"Coupling: {self.quake_coupling:.2f}")
        return True
    # Toggle view
    if key == ord("v") or key == ord("V"):
        self.quake_view = "waves" if self.quake_view == "fault" else "fault"
        self._flash(f"View: {self.quake_view}")
        return True
    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing
# ══════════════════════════════════════════════════════════════════════

def _draw_quake_menu(self, max_y: int, max_x: int):
    """Draw the Earthquake preset selection menu."""
    self.stdscr.erase()
    title = "── Earthquake & Seismic Wave Propagation ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(self.QUAKE_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 6:
            break
        marker = "▸ " if i == self.quake_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.quake_menu_sel else curses.color_pair(7)
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(y, 3, line[:max_x - 4], attr)
        except curses.error:
            pass
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Legend
    legend_y = max_y - 5
    if legend_y > 0:
        lines = [
            "Burridge-Knopoff spring-block fault model with stick-slip rupture cascades.",
            "Emergent Gutenberg-Richter scaling, Omori aftershock decay, and earthquake cycles.",
            "Self-organized criticality: simple local rules produce complex power-law statistics.",
        ]
        for i, line in enumerate(lines):
            try:
                self.stdscr.addstr(legend_y + i, 3, line[:max_x - 4],
                                   curses.color_pair(6))
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


def _draw_quake(self, max_y: int, max_x: int):
    """Draw the active Earthquake simulation."""
    self.stdscr.erase()
    state = "▶ RUNNING" if self.quake_running else "⏸ PAUSED"

    # Title bar
    title = (f" Earthquake: {self.quake_preset_name}  |  t={self.quake_generation}"
             f"  events={self.quake_total_events}"
             f"  last M={self.quake_last_mag:.1f}"
             f"  max M={self.quake_largest_mag:.1f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if self.quake_view == "fault":
        _draw_quake_fault(self, max_y, max_x)
    else:
        _draw_quake_waves(self, max_y, max_x)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        gr_text = ""
        if len(self.quake_event_sizes) >= 10:
            # Compute approximate b-value for GR scaling
            sizes = self.quake_event_sizes[-200:]
            mean_log = sum(math.log10(max(1, s)) for s in sizes) / len(sizes)
            b_val = 1.0 / max(0.01, mean_log) if mean_log > 0 else 0.0
            gr_text = f"  b≈{b_val:.2f}"
        info = (f" t={self.quake_generation}"
                f"  rate={self.quake_tectonic_rate:.3f}"
                f"  coupling={self.quake_coupling:.2f}"
                f"  events={self.quake_total_events}"
                f"  aftershocks(30)={self.quake_aftershock_count}"
                f"{gr_text}"
                f"  view={self.quake_view}"
                f"  spf={self.quake_steps_per_frame}")
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [t/T]=rate [c/C]=coupling [v]=view [+/-]=speed [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_quake_fault(self, max_y: int, max_x: int):
    """Draw the fault plane stress/rupture view."""
    rows = self.quake_rows
    cols = self.quake_cols
    stress = self.quake_stress
    strength = self.quake_strength
    failed = self.quake_failed

    # Fit fault into display area
    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    # Stress visualization characters
    stress_chars = " .:-=+*#%@"

    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break
        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols:
                break
            if sx >= max_x - 1:
                break

            s = stress[r][c]
            th = strength[r][c]
            ratio = min(1.0, s / max(0.01, th))

            if failed[r][c]:
                # Active rupture: bright red
                ch = "█"
                attr = curses.color_pair(1) | curses.A_BOLD
            elif ratio > 0.9:
                # Near failure: yellow
                ch = stress_chars[min(9, int(ratio * 9))]
                attr = curses.color_pair(3) | curses.A_BOLD
            elif ratio > 0.6:
                # Moderate stress: orange/yellow
                ch = stress_chars[min(9, int(ratio * 9))]
                attr = curses.color_pair(3)
            elif ratio > 0.3:
                # Low-moderate stress: green
                ch = stress_chars[min(9, int(ratio * 9))]
                attr = curses.color_pair(2)
            else:
                # Low stress: dim
                ch = stress_chars[min(9, int(ratio * 9))]
                attr = curses.color_pair(6) | curses.A_DIM

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass

    # Draw injection point for induced seismicity
    if self.quake_preset_id == "induced":
        inj_sy = 1 + self.quake_injection_r // max(1, row_scale)
        inj_sx = self.quake_injection_c // max(1, col_scale)
        if 1 <= inj_sy < max_y - 2 and 0 <= inj_sx < max_x - 1:
            try:
                self.stdscr.addstr(inj_sy, inj_sx, "◉",
                                   curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass


def _draw_quake_waves(self, max_y: int, max_x: int):
    """Draw the seismic wave / tsunami propagation view."""
    wr = self.quake_wrows
    wc = self.quake_wcols
    pw = self.quake_pwave
    sw = self.quake_swave
    tsunami = self.quake_tsunami_h

    disp_rows = min(max_y - 4, wr)
    disp_cols = min(max_x - 1, wc)

    wave_chars = " .·:~≈∿≋░▒"

    for sy in range(disp_rows):
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break
        for sx in range(disp_cols):
            if sx >= max_x - 1:
                break
            p_val = abs(pw[sy][sx]) if sy < wr and sx < wc else 0.0
            s_val = abs(sw[sy][sx]) if sy < wr and sx < wc else 0.0
            t_val = abs(tsunami[sy][sx]) if tsunami and sy < wr and sx < wc else 0.0

            total = p_val + s_val + t_val
            if total < 0.05:
                continue

            idx = min(9, int(total * 3))
            ch = wave_chars[idx]

            # Color: P-wave = blue, S-wave = green, tsunami = cyan
            if t_val > p_val and t_val > s_val:
                attr = curses.color_pair(6) | curses.A_BOLD
            elif p_val > s_val:
                attr = curses.color_pair(4)
                if p_val > 1.5:
                    attr |= curses.A_BOLD
            else:
                attr = curses.color_pair(2)
                if s_val > 1.5:
                    attr |= curses.A_BOLD

            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register earthquake mode methods on the App class."""
    App.QUAKE_PRESETS = QUAKE_PRESETS
    App._enter_quake_mode = _enter_quake_mode
    App._exit_quake_mode = _exit_quake_mode
    App._quake_init = _quake_init
    App._quake_make_fault = _quake_make_fault
    App._quake_make_wave_field = _quake_make_wave_field
    App._quake_magnitude = _quake_magnitude
    App._quake_step = _quake_step
    App._quake_inject_waves = _quake_inject_waves
    App._quake_propagate_waves = _quake_propagate_waves
    App._quake_propagate_tsunami = _quake_propagate_tsunami
    App._handle_quake_menu_key = _handle_quake_menu_key
    App._handle_quake_key = _handle_quake_key
    App._draw_quake_menu = _draw_quake_menu
    App._draw_quake = _draw_quake
    App._draw_quake_fault = _draw_quake_fault
    App._draw_quake_waves = _draw_quake_waves
