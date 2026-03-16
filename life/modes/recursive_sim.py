"""Mode: recursive_sim — Sim-in-a-Cell recursive nested simulation.

Each cell in a macro-grid contains an independent micro-simulation.
The micro-simulation's aggregate density determines the macro cell's
alive/dead state, creating multi-scale emergence.  The user picks
any two of the 8 mashup engines (one for macro, one for micro),
enabling thousands of cross-scale combinations.  Navigation lets
you zoom between the macro overview and any individual cell's
inner world.
"""
import curses
import math
import random
import time

from life.constants import SPEEDS, SPEED_LABELS

# Reuse the mini-simulation engines from mashup mode
from life.modes.mashup import MASHUP_SIMS, _ENGINES

_DENSITY = " ░▒▓█"
_SIM_BY_ID = {s["id"]: s for s in MASHUP_SIMS}

# ── Presets ─────────────────────────────────────────────────────────
RECURSIVE_PRESETS = [
    ("GoL ← RD Cells", "gol", "rd",
     "Game of Life macro-grid; each cell runs Reaction-Diffusion"),
    ("GoL ← GoL Cells", "gol", "gol",
     "Classic recursive: Game of Life all the way down"),
    ("GoL ← Ising Cells", "gol", "ising",
     "Life grid driven by magnetic spin micro-worlds"),
    ("RD ← GoL Cells", "rd", "gol",
     "Reaction-Diffusion macro fed by Game of Life micro-cells"),
    ("Wave ← Fire Cells", "wave", "fire",
     "Wave propagation macro driven by forest fire micro-sims"),
    ("Ising ← RPS Cells", "ising", "rps",
     "Ising model macro with Rock-Paper-Scissors inside each cell"),
    ("Fire ← Physarum Cells", "fire", "physarum",
     "Forest fire macro fueled by slime mold micro-networks"),
    ("RPS ← Wave Cells", "rps", "wave",
     "Rock-Paper-Scissors macro with wave interference inside cells"),
]

# Cell size presets
CELL_SIZES = [
    (6,  "Tiny (6×6)"),
    (8,  "Small (8×8)"),
    (10, "Medium (10×10)"),
    (12, "Large (12×12)"),
]

# Density threshold: micro-sim density above this → macro cell alive
_ALIVE_THRESHOLD = 0.15


# ════════════════════════════════════════════════════════════════════
#  Mode entry / exit
# ════════════════════════════════════════════════════════════════════

def _enter_recursive_mode(self):
    """Enter recursive simulation mode — show selection menu."""
    self.rsim_menu = True
    self.rsim_menu_sel = 0
    self.rsim_menu_phase = 0  # 0=presets, 1=pick macro, 2=pick micro, 3=pick cell size
    self.rsim_pick_macro = None
    self.rsim_pick_micro = None
    self._flash("Sim-in-a-Cell — recursive nested simulation")


def _exit_recursive_mode(self):
    """Exit recursive simulation mode and clean up."""
    self.rsim_mode = False
    self.rsim_menu = False
    self.rsim_running = False
    self.rsim_cells = None
    self.rsim_macro_state = None
    self.rsim_zoom_cell = None
    self._flash("Recursive simulation OFF")


# ════════════════════════════════════════════════════════════════════
#  Initialization
# ════════════════════════════════════════════════════════════════════

def _rsim_init(self, macro_id, micro_id, cell_size=8):
    """Initialize the recursive grid: macro engine + micro engines per cell."""
    max_y, max_x = self.stdscr.getmaxyx()

    # Macro grid dimensions — fit in terminal
    # In overview mode each macro cell is rendered as cell_size rows tall
    # and cell_size*2 cols wide (each sim cell = 2 chars)
    # But in overview we show a compact view: 1 char per macro cell (2 cols wide)
    display_rows = max(5, max_y - 4)
    display_cols = max(5, (max_x - 1) // 2)

    # Macro grid can be at most display_rows × display_cols for compact view
    # but limit so micro sims aren't too many (perf)
    macro_rows = min(display_rows, 30)
    macro_cols = min(display_cols, 40)

    self.rsim_macro_id = macro_id
    self.rsim_micro_id = micro_id
    self.rsim_macro_name = _SIM_BY_ID[macro_id]["name"]
    self.rsim_micro_name = _SIM_BY_ID[micro_id]["name"]
    self.rsim_cell_size = cell_size
    self.rsim_macro_rows = macro_rows
    self.rsim_macro_cols = macro_cols

    # Initialize macro engine (using the mashup engine at macro scale)
    macro_init, _, _ = _ENGINES[macro_id]
    self.rsim_macro_state = macro_init(macro_rows, macro_cols)

    # Initialize one micro-simulation per macro cell
    micro_init, _, _ = _ENGINES[micro_id]
    cells = []
    for r in range(macro_rows):
        row = []
        for c in range(macro_cols):
            row.append(micro_init(cell_size, cell_size))
        cells.append(row)
    self.rsim_cells = cells

    # Density caches
    self.rsim_micro_densities = [[0.0] * macro_cols for _ in range(macro_rows)]
    self.rsim_macro_density = [[0.0] * macro_cols for _ in range(macro_rows)]
    # Compute initial densities
    _, _, micro_dens_fn = _ENGINES[micro_id]
    for r in range(macro_rows):
        for c in range(macro_cols):
            d = micro_dens_fn(cells[r][c])
            total = sum(sum(row) for row in d)
            self.rsim_micro_densities[r][c] = total / max(1, cell_size * cell_size)

    _, _, macro_dens_fn = _ENGINES[macro_id]
    md = macro_dens_fn(self.rsim_macro_state)
    self.rsim_macro_density = md

    self.rsim_generation = 0
    self.rsim_running = False
    self.rsim_coupling = 0.5
    self.rsim_zoom_cell = None  # None = overview, (r,c) = zoomed into cell
    self.rsim_zoom_cursor = [0, 0]  # cursor for selecting cell to zoom
    self.rsim_menu = False
    self.rsim_mode = True

    self._flash(f"Recursive: {self.rsim_macro_name} macro ← {self.rsim_micro_name} micro  |  "
                f"{macro_rows}×{macro_cols} grid, {cell_size}×{cell_size} cells")


# ════════════════════════════════════════════════════════════════════
#  Simulation step
# ════════════════════════════════════════════════════════════════════

def _rsim_step(self):
    """Advance all micro-simulations, then feed density up to macro, then step macro."""
    macro_rows = self.rsim_macro_rows
    macro_cols = self.rsim_macro_cols
    cell_size = self.rsim_cell_size
    coupling = self.rsim_coupling

    _, micro_step, micro_dens_fn = _ENGINES[self.rsim_micro_id]
    _, macro_step, macro_dens_fn = _ENGINES[self.rsim_macro_id]

    # Step 1: Step all micro-simulations
    # Feed macro cell's density as external influence to micro
    for r in range(macro_rows):
        for c in range(macro_cols):
            # Macro cell density as external signal to micro
            macro_val = self.rsim_macro_density[r][c] if r < len(self.rsim_macro_density) else 0.0
            if isinstance(macro_val, list):
                macro_val = 0.0
            # Build a uniform density field from macro value for the micro sim
            micro_external = [[macro_val * coupling] * cell_size for _ in range(cell_size)]
            micro_step(self.rsim_cells[r][c], micro_external, coupling)

    # Step 2: Compute micro densities → feed into macro
    for r in range(macro_rows):
        for c in range(macro_cols):
            d = micro_dens_fn(self.rsim_cells[r][c])
            total = sum(sum(row) for row in d)
            self.rsim_micro_densities[r][c] = total / max(1, cell_size * cell_size)

    # Step 3: Build density field from micro densities for macro engine coupling
    micro_dens_field = self.rsim_micro_densities

    # Step 4: Step the macro engine with micro density as external input
    macro_step(self.rsim_macro_state, micro_dens_field, coupling)

    # Step 5: Refresh macro density
    self.rsim_macro_density = macro_dens_fn(self.rsim_macro_state)

    self.rsim_generation += 1


# ════════════════════════════════════════════════════════════════════
#  Menu drawing
# ════════════════════════════════════════════════════════════════════

def _draw_rsim_menu(self, max_y, max_x):
    """Draw the recursive sim selection menu."""
    self.stdscr.erase()
    phase = self.rsim_menu_phase

    title = "── Sim-in-a-Cell: Recursive Nested Simulation ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    desc = "Each macro cell contains a living micro-simulation"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(desc)) // 2), desc[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    if phase == 0:
        # ── Preset selection ──
        subtitle = "Choose a preset or build your own:"
        try:
            self.stdscr.addstr(4, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass

        for i, (name, _, _, pdesc) in enumerate(RECURSIVE_PRESETS):
            y = 6 + i
            if y >= max_y - 3:
                break
            sel = i == self.rsim_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{name}"[:max_x - 4], attr)
            except curses.error:
                pass
            if sel:
                try:
                    self.stdscr.addstr(y + 0, 40, pdesc[:max_x - 42],
                                       curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass

        # Custom option
        ci = len(RECURSIVE_PRESETS)
        y = 6 + ci
        if y < max_y - 3:
            sel = self.rsim_menu_sel == ci
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(3)
            try:
                self.stdscr.addstr(y, 2, f"{marker}Custom Combination..."[:max_x - 4], attr)
            except curses.error:
                pass

    elif phase == 1:
        # ── Pick macro sim ──
        subtitle = "Select MACRO simulation (the big grid):"
        try:
            self.stdscr.addstr(4, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass
        for i, sim in enumerate(MASHUP_SIMS):
            y = 6 + i
            if y >= max_y - 3:
                break
            sel = i == self.rsim_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    elif phase == 2:
        # ── Pick micro sim ──
        subtitle = f"Macro: {_SIM_BY_ID[self.rsim_pick_macro]['name']}  |  Select MICRO simulation (inside each cell):"
        try:
            self.stdscr.addstr(4, 2, subtitle[:max_x - 4], curses.color_pair(6))
        except curses.error:
            pass
        for i, sim in enumerate(MASHUP_SIMS):
            y = 6 + i
            if y >= max_y - 3:
                break
            sel = i == self.rsim_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    elif phase == 3:
        # ── Pick cell size ──
        subtitle = (f"Macro: {_SIM_BY_ID[self.rsim_pick_macro]['name']}  |  "
                    f"Micro: {_SIM_BY_ID[self.rsim_pick_micro]['name']}  |  Select cell size:")
        try:
            self.stdscr.addstr(4, 2, subtitle[:max_x - 4], curses.color_pair(6))
        except curses.error:
            pass
        for i, (sz, label) in enumerate(CELL_SIZES):
            y = 6 + i
            if y >= max_y - 3:
                break
            sel = i == self.rsim_menu_sel
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

def _handle_rsim_menu_key(self, key):
    """Handle input in the recursive sim selection menu."""
    if key == -1:
        return True
    phase = self.rsim_menu_phase

    if phase == 0:
        n = len(RECURSIVE_PRESETS) + 1
    elif phase == 1:
        n = len(MASHUP_SIMS)
    elif phase == 2:
        n = len(MASHUP_SIMS)
    else:
        n = len(CELL_SIZES)

    if key == curses.KEY_UP or key == ord("k"):
        self.rsim_menu_sel = (self.rsim_menu_sel - 1) % max(1, n)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.rsim_menu_sel = (self.rsim_menu_sel + 1) % max(1, n)
        return True
    if key == 27:  # Esc
        if phase > 0:
            self.rsim_menu_phase = phase - 1
            self.rsim_menu_sel = 0
        else:
            self.rsim_menu = False
            self._flash("Recursive sim cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if phase == 0:
            sel = self.rsim_menu_sel
            if sel < len(RECURSIVE_PRESETS):
                _, macro_id, micro_id, _ = RECURSIVE_PRESETS[sel]
                self._rsim_init(macro_id, micro_id, 8)
            else:
                self.rsim_menu_phase = 1
                self.rsim_menu_sel = 0
        elif phase == 1:
            self.rsim_pick_macro = MASHUP_SIMS[self.rsim_menu_sel]["id"]
            self.rsim_menu_phase = 2
            self.rsim_menu_sel = 0
        elif phase == 2:
            self.rsim_pick_micro = MASHUP_SIMS[self.rsim_menu_sel]["id"]
            self.rsim_menu_phase = 3
            self.rsim_menu_sel = 0
        elif phase == 3:
            cell_size = CELL_SIZES[self.rsim_menu_sel][0]
            self._rsim_init(self.rsim_pick_macro, self.rsim_pick_micro, cell_size)
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Main drawing — overview (macro grid with density coloring)
# ════════════════════════════════════════════════════════════════════

def _draw_rsim_overview(self, max_y, max_x):
    """Draw the macro overview — each macro cell colored by micro density."""
    self.stdscr.erase()

    macro_rows = self.rsim_macro_rows
    macro_cols = self.rsim_macro_cols

    # Title bar
    state = "▶ RUNNING" if self.rsim_running else "⏸ PAUSED"
    title = (f" SIM-IN-A-CELL: {self.rsim_macro_name} ← {self.rsim_micro_name}"
             f"  |  gen {self.rsim_generation}"
             f"  |  coupling={self.rsim_coupling:.2f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Grid rendering — each macro cell as 2-char-wide block
    view_rows = min(macro_rows, max_y - 4)
    view_cols = min(macro_cols, (max_x - 1) // 2)

    cursor_r, cursor_c = self.rsim_zoom_cursor
    macro_dens = self.rsim_macro_density
    micro_dens = self.rsim_micro_densities

    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 3:
            break
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break

            # Get macro and micro densities for this cell
            m_val = macro_dens[r][c] if r < len(macro_dens) and c < len(macro_dens[r]) else 0.0
            if isinstance(m_val, list):
                m_val = 0.0
            u_val = micro_dens[r][c] if r < len(micro_dens) and c < len(micro_dens[r]) else 0.0

            # Combined visual: micro density drives glyph, macro density drives color
            combined = max(m_val, u_val)
            if combined < 0.01:
                # Check if cursor is here
                if r == cursor_r and c == cursor_c:
                    try:
                        self.stdscr.addstr(sy, sx, "[]",
                                           curses.color_pair(7) | curses.A_DIM)
                    except curses.error:
                        pass
                continue

            # Density glyph from micro
            di = max(1, min(4, int(u_val * 4.999)))
            ch = _DENSITY[di]

            # Color from macro alive state
            if m_val > 0.5:
                if u_val > 0.5:
                    pair = 5  # magenta: both active
                else:
                    pair = 6  # cyan: macro alive
            else:
                if u_val > 0.3:
                    pair = 3  # green: micro active
                else:
                    pair = 6  # cyan: dim

            # Brightness
            if combined > 0.7:
                attr = curses.color_pair(pair) | curses.A_BOLD
            elif combined > 0.3:
                attr = curses.color_pair(pair)
            else:
                attr = curses.color_pair(pair) | curses.A_DIM

            # Cursor highlight
            if r == cursor_r and c == cursor_c:
                attr = curses.color_pair(7) | curses.A_BOLD | curses.A_REVERSE

            try:
                self.stdscr.addstr(sy, sx, ch + ch, attr)
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 3
    if info_y > 1:
        cell_info = (f" Cursor: ({cursor_r},{cursor_c})"
                     f"  Micro density: {micro_dens[cursor_r][cursor_c]:.3f}"
                     f"  Macro density: "
                     f"{macro_dens[cursor_r][cursor_c] if cursor_r < len(macro_dens) and cursor_c < len(macro_dens[cursor_r]) else 0.0:.3f}"
                     f"  Grid: {macro_rows}×{macro_cols}"
                     f"  Cell: {self.rsim_cell_size}×{self.rsim_cell_size}")
        try:
            self.stdscr.addstr(info_y, 0, cell_info[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        status = (f" gen {self.rsim_generation}  |"
                  f"  coupling={self.rsim_coupling:.2f}  |"
                  f"  speed={SPEED_LABELS[self.speed_idx]}  |"
                  f"  [Enter]=zoom into cell  [arrows]=move cursor")
        try:
            self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                               curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [+/-]=coupling [>/<=speed [r]=reset [R]=menu [Enter]=zoom [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Zoom drawing — show a single cell's micro-simulation full-screen
# ════════════════════════════════════════════════════════════════════

def _draw_rsim_zoom(self, max_y, max_x):
    """Draw zoomed-in view of a single cell's micro-simulation."""
    self.stdscr.erase()
    zr, zc = self.rsim_zoom_cell
    cell_size = self.rsim_cell_size

    _, _, micro_dens_fn = _ENGINES[self.rsim_micro_id]
    micro_state = self.rsim_cells[zr][zc]
    dens = micro_dens_fn(micro_state)

    # Title
    state = "▶ RUNNING" if self.rsim_running else "⏸ PAUSED"
    macro_val = self.rsim_macro_density[zr][zc] if zr < len(self.rsim_macro_density) and zc < len(self.rsim_macro_density[zr]) else 0.0
    if isinstance(macro_val, list):
        macro_val = 0.0
    micro_val = self.rsim_micro_densities[zr][zc]
    title = (f" ZOOM: Cell ({zr},{zc})  |  {self.rsim_micro_name}"
             f"  |  gen {self.rsim_generation}"
             f"  |  micro={micro_val:.3f}  macro={macro_val:.3f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Compute scale factor to fill the screen
    avail_rows = max_y - 4
    avail_cols = (max_x - 1) // 2
    scale_r = max(1, avail_rows // cell_size)
    scale_c = max(1, avail_cols // cell_size)
    scale = min(scale_r, scale_c)

    # Draw the micro grid scaled up
    for mr in range(cell_size):
        for mc in range(cell_size):
            val = dens[mr][mc] if mr < len(dens) and mc < len(dens[mr]) else 0.0
            if val < 0.01:
                continue
            di = max(1, min(4, int(val * 4.999)))
            ch = _DENSITY[di]

            # Color based on intensity
            if val > 0.7:
                attr = curses.color_pair(6) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(6)
            else:
                attr = curses.color_pair(6) | curses.A_DIM

            # Draw scaled block
            for sr in range(scale):
                for sc in range(scale):
                    sy = 1 + mr * scale + sr
                    sx = (mc * scale + sc) * 2
                    if sy < max_y - 3 and sx + 1 < max_x:
                        try:
                            self.stdscr.addstr(sy, sx, ch + ch, attr)
                        except curses.error:
                            pass

    # Draw a mini-map of the macro grid in the corner
    minimap_w = min(self.rsim_macro_cols, 20)
    minimap_h = min(self.rsim_macro_rows, 10)
    mm_x = max_x - minimap_w * 2 - 2
    mm_y = 1
    if mm_x > 0 and minimap_h + mm_y < max_y - 4:
        # Border
        try:
            self.stdscr.addstr(mm_y, mm_x - 1, "┌" + "─" * (minimap_w * 2) + "┐",
                               curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass
        for mr in range(minimap_h):
            row_str = ""
            for mc in range(minimap_w):
                md = self.rsim_micro_densities[mr][mc] if mr < self.rsim_macro_rows and mc < self.rsim_macro_cols else 0.0
                if mr == zr and mc == zc:
                    row_str += "██"
                elif md > 0.3:
                    row_str += "▓▓"
                elif md > 0.1:
                    row_str += "░░"
                else:
                    row_str += "  "
            try:
                border_attr = curses.color_pair(7) | curses.A_DIM
                self.stdscr.addstr(mm_y + 1 + mr, mm_x - 1, "│", border_attr)
                self.stdscr.addstr(mm_y + 1 + mr, mm_x, row_str[:minimap_w * 2],
                                   curses.color_pair(3))
                self.stdscr.addstr(mm_y + 1 + mr, mm_x + minimap_w * 2, "│", border_attr)
            except curses.error:
                pass
        try:
            self.stdscr.addstr(mm_y + 1 + minimap_h, mm_x - 1,
                               "└" + "─" * (minimap_w * 2) + "┘",
                               curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass

    # Neighbor info
    info_y = max_y - 3
    if info_y > 1:
        # Show neighbor cells' densities
        neighbors = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr = (zr + dr) % self.rsim_macro_rows
                nc = (zc + dc) % self.rsim_macro_cols
                nd = self.rsim_micro_densities[nr][nc]
                neighbors.append(f"{nd:.2f}")
        info = f" Neighbors: [{', '.join(neighbors)}]  |  coupling={self.rsim_coupling:.2f}"
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
            hint = " [Esc/Backspace]=back to overview  [Space]=play  [n]=step  [arrows]=move to neighbor  [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Draw dispatcher
# ════════════════════════════════════════════════════════════════════

def _draw_rsim(self, max_y, max_x):
    """Main draw entry — delegates to overview or zoom."""
    if self.rsim_zoom_cell is not None:
        _draw_rsim_zoom(self, max_y, max_x)
    else:
        _draw_rsim_overview(self, max_y, max_x)


# ════════════════════════════════════════════════════════════════════
#  Key handling
# ════════════════════════════════════════════════════════════════════

def _handle_rsim_key(self, key):
    """Handle input during active recursive simulation."""
    if key == -1:
        return True

    # ── Quit ──
    if key == ord("q"):
        self._exit_recursive_mode()
        return True

    # ── Play/Pause ──
    if key == ord(" "):
        self.rsim_running = not self.rsim_running
        self._flash("Playing" if self.rsim_running else "Paused")
        return True

    # ── Single step ──
    if key == ord("n") or key == ord("."):
        self.rsim_running = False
        self._rsim_step()
        return True

    # ── Speed control ──
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
            self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
            self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True

    # ── Coupling control ──
    if key == ord("+") or key == ord("="):
        self.rsim_coupling = min(1.0, self.rsim_coupling + 0.05)
        self._flash(f"Coupling: {self.rsim_coupling:.2f}")
        return True
    if key == ord("-") or key == ord("_"):
        self.rsim_coupling = max(0.0, self.rsim_coupling - 0.05)
        self._flash(f"Coupling: {self.rsim_coupling:.2f}")
        return True
    if key == ord("0"):
        self.rsim_coupling = 0.0
        self._flash("Coupling: OFF (independent)")
        return True

    # ── Zoom mode handling ──
    if self.rsim_zoom_cell is not None:
        return _handle_rsim_zoom_key(self, key)
    else:
        return _handle_rsim_overview_key(self, key)


def _handle_rsim_overview_key(self, key):
    """Handle keys in overview mode."""
    # ── Cursor movement ──
    if key == curses.KEY_UP or key == ord("k"):
        self.rsim_zoom_cursor[0] = (self.rsim_zoom_cursor[0] - 1) % self.rsim_macro_rows
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.rsim_zoom_cursor[0] = (self.rsim_zoom_cursor[0] + 1) % self.rsim_macro_rows
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        self.rsim_zoom_cursor[1] = (self.rsim_zoom_cursor[1] - 1) % self.rsim_macro_cols
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        self.rsim_zoom_cursor[1] = (self.rsim_zoom_cursor[1] + 1) % self.rsim_macro_cols
        return True

    # ── Zoom into cell ──
    if key in (10, 13, curses.KEY_ENTER, ord("z")):
        r, c = self.rsim_zoom_cursor
        self.rsim_zoom_cell = (r, c)
        self._flash(f"Zoomed into cell ({r},{c}) — {self.rsim_micro_name}")
        return True

    # ── Reset ──
    if key == ord("r"):
        self._rsim_init(self.rsim_macro_id, self.rsim_micro_id, self.rsim_cell_size)
        self._flash("Reset!")
        return True

    # ── Back to menu ──
    if key == ord("R") or key == 27:
        self.rsim_mode = False
        self.rsim_running = False
        self.rsim_menu = True
        self.rsim_menu_phase = 0
        self.rsim_menu_sel = 0
        return True

    return True


def _handle_rsim_zoom_key(self, key):
    """Handle keys in zoomed-in cell view."""
    # ── Back to overview ──
    if key == 27 or key == curses.KEY_BACKSPACE or key == 127 or key == ord("z"):
        self.rsim_zoom_cell = None
        self._flash("Back to overview")
        return True

    # ── Navigate to neighbor cell ──
    if key == curses.KEY_UP or key == ord("k"):
        zr, zc = self.rsim_zoom_cell
        self.rsim_zoom_cell = ((zr - 1) % self.rsim_macro_rows, zc)
        self.rsim_zoom_cursor = [self.rsim_zoom_cell[0], self.rsim_zoom_cell[1]]
        self._flash(f"Cell ({self.rsim_zoom_cell[0]},{self.rsim_zoom_cell[1]})")
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        zr, zc = self.rsim_zoom_cell
        self.rsim_zoom_cell = ((zr + 1) % self.rsim_macro_rows, zc)
        self.rsim_zoom_cursor = [self.rsim_zoom_cell[0], self.rsim_zoom_cell[1]]
        self._flash(f"Cell ({self.rsim_zoom_cell[0]},{self.rsim_zoom_cell[1]})")
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        zr, zc = self.rsim_zoom_cell
        self.rsim_zoom_cell = (zr, (zc - 1) % self.rsim_macro_cols)
        self.rsim_zoom_cursor = [self.rsim_zoom_cell[0], self.rsim_zoom_cell[1]]
        self._flash(f"Cell ({self.rsim_zoom_cell[0]},{self.rsim_zoom_cell[1]})")
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        zr, zc = self.rsim_zoom_cell
        self.rsim_zoom_cell = (zr, (zc + 1) % self.rsim_macro_cols)
        self.rsim_zoom_cursor = [self.rsim_zoom_cell[0], self.rsim_zoom_cell[1]]
        self._flash(f"Cell ({self.rsim_zoom_cell[0]},{self.rsim_zoom_cell[1]})")
        return True

    # ── Back to menu ──
    if key == ord("R"):
        self.rsim_zoom_cell = None
        self.rsim_mode = False
        self.rsim_running = False
        self.rsim_menu = True
        self.rsim_menu_phase = 0
        self.rsim_menu_sel = 0
        return True

    return True


# ════════════════════════════════════════════════════════════════════
#  Registration
# ════════════════════════════════════════════════════════════════════

def register(App):
    """Register recursive sim mode methods on the App class."""
    App._enter_recursive_mode = _enter_recursive_mode
    App._exit_recursive_mode = _exit_recursive_mode
    App._rsim_init = _rsim_init
    App._rsim_step = _rsim_step
    App._handle_rsim_menu_key = _handle_rsim_menu_key
    App._handle_rsim_key = _handle_rsim_key
    App._draw_rsim_menu = _draw_rsim_menu
    App._draw_rsim = _draw_rsim
