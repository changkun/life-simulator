"""Mode: portal — spatial gateways connecting two simulations at a boundary seam."""
import curses
import math
import random
import time

from life.constants import SPEEDS
from life.modes.mashup import MASHUP_SIMS, _ENGINES

_DENSITY = " ░▒▓█"

_SIM_BY_ID = {s["id"]: s for s in MASHUP_SIMS}

# ── Portal presets ─────────────────────────────────────────────────

PORTAL_PRESETS = [
    ("RD ↔ Particle Life", "rd", "boids", "vertical",
     "Reaction-Diffusion feeds energy into Boids at the seam"),
    ("Wave ↔ Forest Fire", "wave", "fire", "vertical",
     "Wave amplitude ignites fire; fire damps waves at the border"),
    ("Game of Life ↔ Ising", "gol", "ising", "vertical",
     "Life births polarize spins; spin alignment births life"),
    ("Physarum ↔ RPS", "physarum", "rps", "horizontal",
     "Slime trails guide invasion; invasions deposit pheromone"),
    ("Boids ↔ Wave", "boids", "wave", "horizontal",
     "Boids create ripples at boundary; waves steer boids"),
    ("Fire ↔ Game of Life", "fire", "gol", "vertical",
     "Fire clears life; life regrows and fuels fire across the seam"),
    ("Ising ↔ RD", "ising", "rd", "horizontal",
     "Spin domains modulate reaction feed rate at the interface"),
    ("RPS ↔ Wave", "rps", "wave", "vertical",
     "Cyclic invasion creates wave pulses; waves bias dominance"),
]

# Portal boundary visual character
_PORTAL_CHAR_V = "┃"
_PORTAL_CHAR_H = "━"


# ════════════════════════════════════════════════════════════════════
#  Mode entry / exit
# ════════════════════════════════════════════════════════════════════

def _enter_portal_mode(self):
    """Enter Portal mode — show selection menu."""
    self.portal_menu = True
    self.portal_menu_sel = 0
    self.portal_menu_phase = 0  # 0=presets, 1=pick sim A, 2=pick sim B, 3=pick orientation
    self._flash("Simulation Portal — pick a combo")


def _exit_portal_mode(self):
    """Exit Portal mode and clean up."""
    self.portal_mode = False
    self.portal_menu = False
    self.portal_running = False
    self.portal_sim_a = None
    self.portal_sim_b = None
    self._flash("Portal mode OFF")


# ════════════════════════════════════════════════════════════════════
#  Initialization
# ════════════════════════════════════════════════════════════════════

def _portal_init(self, id_a, id_b, orientation):
    """Initialize two simulations on separate halves of the screen."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.portal_orientation = orientation  # "vertical" or "horizontal"
    self.portal_sim_a_id = id_a
    self.portal_sim_b_id = id_b
    self.portal_sim_a_name = _SIM_BY_ID[id_a]["name"]
    self.portal_sim_b_name = _SIM_BY_ID[id_b]["name"]

    # Available rendering area (leave room for header + status + hint)
    avail_rows = max(10, max_y - 4)
    avail_cols = max(20, max_x - 1)

    if orientation == "vertical":
        # Side by side: A on left, B on right, portal line in middle
        half_cols = max(5, avail_cols // 4)  # each sim gets half the char width
        sim_cols = half_cols  # cell columns per sim
        sim_rows = max(5, avail_rows)
        self.portal_split = half_cols  # split position in cell coords
    else:
        # Top/bottom: A on top, B on bottom, portal line in middle
        half_rows = max(5, avail_rows // 2)
        sim_rows = half_rows
        sim_cols = max(5, avail_cols // 2)  # each cell = 2 chars wide
        self.portal_split = half_rows

    self.portal_sim_rows = sim_rows
    self.portal_sim_cols = sim_cols
    self.portal_avail_rows = avail_rows
    self.portal_avail_cols = avail_cols

    # Initialize both simulations
    init_a, _, dens_a = _ENGINES[id_a]
    init_b, _, dens_b = _ENGINES[id_b]
    self.portal_sim_a = init_a(sim_rows, sim_cols)
    self.portal_sim_b = init_b(sim_rows, sim_cols)

    self.portal_generation = 0
    self.portal_running = False
    self.portal_coupling = 0.5
    self.portal_bleed = 3  # how many cells deep the cross-talk extends

    # Compute initial density maps
    self.portal_density_a = dens_a(self.portal_sim_a)
    self.portal_density_b = dens_b(self.portal_sim_b)

    self.portal_menu = False
    self.portal_mode = True
    self._flash(f"Portal: {self.portal_sim_a_name} ↔ {self.portal_sim_b_name} — Space to start")


# ════════════════════════════════════════════════════════════════════
#  Boundary cross-talk
# ════════════════════════════════════════════════════════════════════

def _portal_build_boundary_influence(density, rows, cols, orientation, split, bleed):
    """Build a coupling density field from one sim's boundary edge.

    For a vertical split, we take the rightmost `bleed` columns of A
    and mirror them into a field the same size as B (and vice-versa).
    The influence fades linearly from the seam.
    """
    influence = [[0.0] * cols for _ in range(rows)]

    if orientation == "vertical":
        # Extract the edge columns near the split
        for r in range(rows):
            for d in range(bleed):
                # Source column: from the edge of the donor sim
                src_c = cols - 1 - d  # rightmost cols for A→B, leftmost for B→A
                if src_c < 0 or src_c >= cols:
                    continue
                fade = 1.0 - d / max(bleed, 1)
                # Place into target at the opposite edge
                tgt_c = d
                if tgt_c < cols:
                    val = density[r][src_c] if src_c < len(density[r]) else 0.0
                    influence[r][tgt_c] = val * fade
    else:
        # Horizontal: extract edge rows near the split
        for c in range(cols):
            for d in range(bleed):
                src_r = rows - 1 - d
                if src_r < 0 or src_r >= rows:
                    continue
                fade = 1.0 - d / max(bleed, 1)
                tgt_r = d
                if tgt_r < rows:
                    row_data = density[src_r] if src_r < len(density) else []
                    val = row_data[c] if c < len(row_data) else 0.0
                    influence[tgt_r][c] = val * fade

    return influence


# ════════════════════════════════════════════════════════════════════
#  Simulation step
# ════════════════════════════════════════════════════════════════════

def _portal_step(self):
    """Advance both simulations with boundary cross-talk at the seam."""
    _, step_a, density_a = _ENGINES[self.portal_sim_a_id]
    _, step_b, density_b = _ENGINES[self.portal_sim_b_id]

    rows = self.portal_sim_rows
    cols = self.portal_sim_cols
    bleed = self.portal_bleed
    orient = self.portal_orientation
    coupling = self.portal_coupling

    # Build boundary influence: A's edge feeds into B, and vice versa
    influence_a_to_b = _portal_build_boundary_influence(
        self.portal_density_a, rows, cols, orient, self.portal_split, bleed)
    influence_b_to_a = _portal_build_boundary_influence(
        self.portal_density_b, rows, cols, orient, self.portal_split, bleed)

    # For B→A influence, the source edge is the *left/top* edge of B
    # and it should appear at the *right/bottom* edge of A.
    # We need to flip the influence mapping.
    flipped_b_to_a = _portal_flip_influence(
        self.portal_density_b, rows, cols, orient, bleed)

    flipped_a_to_b = influence_a_to_b  # already correct: A's right → B's left

    # Step each sim with the other's boundary influence
    step_a(self.portal_sim_a, flipped_b_to_a, coupling)
    step_b(self.portal_sim_b, flipped_a_to_b, coupling)

    # Refresh density maps
    self.portal_density_a = density_a(self.portal_sim_a)
    self.portal_density_b = density_b(self.portal_sim_b)
    self.portal_generation += 1


def _portal_flip_influence(density, rows, cols, orientation, bleed):
    """Build influence from a sim's *near* edge into the other sim's *far* edge."""
    influence = [[0.0] * cols for _ in range(rows)]

    if orientation == "vertical":
        # B's leftmost cols → A's rightmost cols
        for r in range(rows):
            for d in range(bleed):
                src_c = d  # leftmost cols of B
                if src_c >= cols:
                    continue
                fade = 1.0 - d / max(bleed, 1)
                tgt_c = cols - 1 - d  # rightmost cols of A
                if 0 <= tgt_c < cols:
                    val = density[r][src_c] if src_c < len(density[r]) else 0.0
                    influence[r][tgt_c] = val * fade
    else:
        # B's topmost rows → A's bottommost rows
        for c in range(cols):
            for d in range(bleed):
                src_r = d
                if src_r >= rows:
                    continue
                fade = 1.0 - d / max(bleed, 1)
                tgt_r = rows - 1 - d
                if 0 <= tgt_r < rows:
                    row_data = density[src_r] if src_r < len(density) else []
                    val = row_data[c] if c < len(row_data) else 0.0
                    influence[tgt_r][c] = val * fade

    return influence


# ════════════════════════════════════════════════════════════════════
#  Menu drawing
# ════════════════════════════════════════════════════════════════════

def _draw_portal_menu(self, max_y, max_x):
    """Draw the portal mode selection menu."""
    self.stdscr.erase()
    phase = self.portal_menu_phase

    title = "── Simulation Portal ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if phase == 0:
        # ── Preset selection ──
        subtitle = "Choose a portal preset or build your own:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass

        for i, (name, _, _, orient, desc) in enumerate(PORTAL_PRESETS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.portal_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            orient_icon = "│" if orient == "vertical" else "─"
            line = f"{marker}{name} [{orient_icon}]"
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            except curses.error:
                pass
            if sel:
                try:
                    self.stdscr.addstr(y, 2 + len(line) + 2,
                                       desc[:max_x - len(line) - 6],
                                       curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass

        # Custom option
        ci = len(PORTAL_PRESETS)
        y = 5 + ci
        if y < max_y - 3:
            sel = self.portal_menu_sel == ci
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(3)
            try:
                self.stdscr.addstr(y, 2, f"{marker}Custom Portal..."[:max_x - 4], attr)
            except curses.error:
                pass

    elif phase == 1:
        # ── Pick Simulation A ──
        subtitle = "Select Simulation A (left/top side):"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass
        for i, sim in enumerate(MASHUP_SIMS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.portal_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    elif phase == 2:
        # ── Pick Simulation B ──
        subtitle = f"Sim A: {_SIM_BY_ID[self.portal_pick_a]['name']}  |  Select Simulation B (right/bottom side):"
        try:
            self.stdscr.addstr(3, max(0, 2), subtitle[:max_x - 4],
                               curses.color_pair(6))
        except curses.error:
            pass
        available = [s for s in MASHUP_SIMS if s["id"] != self.portal_pick_a]
        for idx, sim in enumerate(available):
            y = 5 + idx
            if y >= max_y - 3:
                break
            sel = idx == self.portal_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    elif phase == 3:
        # ── Pick orientation ──
        subtitle = (f"Sim A: {_SIM_BY_ID[self.portal_pick_a]['name']}  |  "
                    f"Sim B: {_SIM_BY_ID[self.portal_pick_b]['name']}  |  Select orientation:")
        try:
            self.stdscr.addstr(3, max(0, 2), subtitle[:max_x - 4],
                               curses.color_pair(6))
        except curses.error:
            pass
        orientations = [
            ("Vertical  │  (A left, B right)", "vertical"),
            ("Horizontal ── (A top, B bottom)", "horizontal"),
        ]
        for i, (label, _) in enumerate(orientations):
            y = 5 + i
            sel = i == self.portal_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{label}"[:max_x - 4], attr)
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [Up/Down]=navigate  [Enter]=select  [Esc]=back/exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Menu key handling
# ════════════════════════════════════════════════════════════════════

def _handle_portal_menu_key(self, key):
    """Handle input in the portal selection menu."""
    if key == -1:
        return True
    phase = self.portal_menu_phase

    if phase == 0:
        n = len(PORTAL_PRESETS) + 1
    elif phase == 1:
        n = len(MASHUP_SIMS)
    elif phase == 2:
        n = len([s for s in MASHUP_SIMS if s["id"] != self.portal_pick_a])
    else:
        n = 2  # vertical / horizontal

    if key == curses.KEY_UP or key == ord("k"):
        self.portal_menu_sel = (self.portal_menu_sel - 1) % max(1, n)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.portal_menu_sel = (self.portal_menu_sel + 1) % max(1, n)
        return True
    if key == 27:  # Esc
        if phase > 0:
            self.portal_menu_phase = phase - 1
            self.portal_menu_sel = 0
        else:
            self.portal_menu = False
            self._flash("Portal cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if phase == 0:
            sel = self.portal_menu_sel
            if sel < len(PORTAL_PRESETS):
                _, id_a, id_b, orient, _ = PORTAL_PRESETS[sel]
                self._portal_init(id_a, id_b, orient)
            else:
                self.portal_menu_phase = 1
                self.portal_menu_sel = 0
        elif phase == 1:
            self.portal_pick_a = MASHUP_SIMS[self.portal_menu_sel]["id"]
            self.portal_menu_phase = 2
            self.portal_menu_sel = 0
        elif phase == 2:
            available = [s for s in MASHUP_SIMS if s["id"] != self.portal_pick_a]
            self.portal_pick_b = available[self.portal_menu_sel]["id"]
            self.portal_menu_phase = 3
            self.portal_menu_sel = 0
        elif phase == 3:
            orientations = ["vertical", "horizontal"]
            orient = orientations[self.portal_menu_sel]
            self._portal_init(self.portal_pick_a, self.portal_pick_b, orient)
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Main simulation drawing
# ════════════════════════════════════════════════════════════════════

def _draw_portal(self, max_y, max_x):
    """Draw the split-screen portal view with boundary seam."""
    self.stdscr.erase()

    state = "▶ RUNNING" if self.portal_running else "⏸ PAUSED"
    orient_icon = "│" if self.portal_orientation == "vertical" else "─"
    title = (f" PORTAL: {self.portal_sim_a_name} [{orient_icon}] {self.portal_sim_b_name}"
             f"  |  gen {self.portal_generation}"
             f"  |  coupling={self.portal_coupling:.2f}"
             f"  |  bleed={self.portal_bleed}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    da = self.portal_density_a
    db = self.portal_density_b
    rows = self.portal_sim_rows
    cols = self.portal_sim_cols

    if self.portal_orientation == "vertical":
        _draw_portal_vertical(self, da, db, rows, cols, max_y, max_x)
    else:
        _draw_portal_horizontal(self, da, db, rows, cols, max_y, max_x)

    # ── Legend bar ──
    legend_y = max_y - 3
    if legend_y > 1:
        legend = (f" ■ {self.portal_sim_a_name}=cyan (left/top)"
                  f"  ■ {self.portal_sim_b_name}=red (right/bottom)"
                  f"  ┃ portal seam=yellow")
        try:
            self.stdscr.addstr(legend_y, 0, legend[:max_x - 1],
                               curses.color_pair(7))
        except curses.error:
            pass

    # ── Status bar ──
    status_y = max_y - 2
    if status_y > 1:
        sa = sb = 0.0
        cnt = max(1, rows * cols)
        for r in range(min(rows, len(da))):
            for c in range(min(cols, len(da[r]) if r < len(da) else 0)):
                sa += da[r][c]
            for c in range(min(cols, len(db[r]) if r < len(db) else 0)):
                sb += db[r][c]
        sa /= cnt
        sb /= cnt
        status = (f" gen {self.portal_generation}  |"
                  f"  A density={sa:.3f}  B density={sb:.3f}  |"
                  f"  coupling={self.portal_coupling:.2f}  bleed={self.portal_bleed}")
        try:
            self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # ── Hint bar ──
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [+/-]=coupling [b/B]=bleed [o]=orient [r]=reset [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_portal_vertical(self, da, db, rows, cols, max_y, max_x):
    """Draw vertical split: A on left, portal line, B on right."""
    view_rows = min(rows, max_y - 5)  # leave room for header/footer

    # Each sim's density is cols wide. We render side by side.
    # Left side uses cols_a characters, then portal line, then cols_b characters.
    # Each cell = 2 chars wide.
    half_w = min(cols, (max_x - 3) // 4)  # chars available for each side / 2
    portal_sx = half_w * 2  # screen x of portal line

    bleed = self.portal_bleed

    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 3:
            break

        # Draw sim A (left side)
        da_row = da[r] if r < len(da) else []
        for c in range(half_w):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            val = da_row[c] if c < len(da_row) else 0.0
            if val < 0.01:
                continue
            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]

            # Near-seam cells glow to show cross-talk
            dist_to_seam = cols - 1 - c
            if dist_to_seam < bleed and self.portal_coupling > 0:
                pair = 5  # magenta for bleed zone
            else:
                pair = 6  # cyan for sim A

            if val > 0.7:
                attr = curses.color_pair(pair) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(pair)
            else:
                attr = curses.color_pair(pair) | curses.A_DIM
            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass

        # Draw portal seam
        if portal_sx < max_x:
            try:
                self.stdscr.addstr(sy, portal_sx, _PORTAL_CHAR_V,
                                   curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw sim B (right side)
        db_row = db[r] if r < len(db) else []
        for c in range(half_w):
            sx = portal_sx + 1 + c * 2
            if sx + 1 >= max_x:
                break
            val = db_row[c] if c < len(db_row) else 0.0
            if val < 0.01:
                continue
            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]

            # Near-seam cells glow
            if c < bleed and self.portal_coupling > 0:
                pair = 5  # magenta for bleed zone
            else:
                pair = 1  # red for sim B

            if val > 0.7:
                attr = curses.color_pair(pair) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(pair)
            else:
                attr = curses.color_pair(pair) | curses.A_DIM
            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass


def _draw_portal_horizontal(self, da, db, rows, cols, max_y, max_x):
    """Draw horizontal split: A on top, portal line, B on bottom."""
    half_h = min(rows, (max_y - 5) // 2)  # rows available for each side
    view_cols = min(cols, (max_x - 1) // 2)
    portal_sy = 1 + half_h  # screen y of portal line

    bleed = self.portal_bleed

    # Draw sim A (top)
    for r in range(half_h):
        sy = 1 + r
        if sy >= max_y - 3:
            break
        da_row = da[r] if r < len(da) else []
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            val = da_row[c] if c < len(da_row) else 0.0
            if val < 0.01:
                continue
            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]

            dist_to_seam = rows - 1 - r
            if dist_to_seam < bleed and self.portal_coupling > 0:
                pair = 5
            else:
                pair = 6

            if val > 0.7:
                attr = curses.color_pair(pair) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(pair)
            else:
                attr = curses.color_pair(pair) | curses.A_DIM
            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass

    # Draw portal seam line
    if portal_sy < max_y - 3:
        seam_str = _PORTAL_CHAR_H * min(view_cols * 2, max_x - 1)
        try:
            self.stdscr.addstr(portal_sy, 0, seam_str,
                               curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass

    # Draw sim B (bottom)
    for r in range(half_h):
        sy = portal_sy + 1 + r
        if sy >= max_y - 3:
            break
        db_row = db[r] if r < len(db) else []
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            val = db_row[c] if c < len(db_row) else 0.0
            if val < 0.01:
                continue
            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]

            if r < bleed and self.portal_coupling > 0:
                pair = 5
            else:
                pair = 1

            if val > 0.7:
                attr = curses.color_pair(pair) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(pair)
            else:
                attr = curses.color_pair(pair) | curses.A_DIM
            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass


# ════════════════════════════════════════════════════════════════════
#  Simulation key handling
# ════════════════════════════════════════════════════════════════════

def _handle_portal_key(self, key):
    """Handle input during active portal simulation."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_portal_mode()
        return True
    if key == ord(" "):
        self.portal_running = not self.portal_running
        self._flash("Playing" if self.portal_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.portal_running = False
        self._portal_step()
        return True
    if key == ord("+") or key == ord("="):
        self.portal_coupling = min(1.0, self.portal_coupling + 0.05)
        self._flash(f"Coupling: {self.portal_coupling:.2f}")
        return True
    if key == ord("-") or key == ord("_"):
        self.portal_coupling = max(0.0, self.portal_coupling - 0.05)
        self._flash(f"Coupling: {self.portal_coupling:.2f}")
        return True
    if key == ord("b"):
        self.portal_bleed = min(20, self.portal_bleed + 1)
        self._flash(f"Bleed depth: {self.portal_bleed} cells")
        return True
    if key == ord("B"):
        self.portal_bleed = max(1, self.portal_bleed - 1)
        self._flash(f"Bleed depth: {self.portal_bleed} cells")
        return True
    if key == ord("o"):
        # Toggle orientation
        new_orient = "horizontal" if self.portal_orientation == "vertical" else "vertical"
        self._portal_init(self.portal_sim_a_id, self.portal_sim_b_id, new_orient)
        self._flash(f"Orientation: {new_orient}")
        return True
    if key == ord("0"):
        self.portal_coupling = 0.0
        self._flash("Coupling: OFF (independent)")
        return True
    if key == ord("5"):
        self.portal_coupling = 0.5
        self._flash("Coupling: 0.50 (default)")
        return True
    if key == ord("r"):
        self._portal_init(self.portal_sim_a_id, self.portal_sim_b_id,
                          self.portal_orientation)
        self._flash("Reset!")
        return True
    if key == ord("R"):
        self.portal_mode = False
        self.portal_running = False
        self.portal_menu = True
        self.portal_menu_phase = 0
        self.portal_menu_sel = 0
        return True
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Registration
# ════════════════════════════════════════════════════════════════════

def register(App):
    """Register portal mode methods on the App class."""
    App._enter_portal_mode = _enter_portal_mode
    App._exit_portal_mode = _exit_portal_mode
    App._portal_init = _portal_init
    App._portal_step = _portal_step
    App._handle_portal_menu_key = _handle_portal_menu_key
    App._handle_portal_key = _handle_portal_key
    App._draw_portal_menu = _draw_portal_menu
    App._draw_portal = _draw_portal
