"""Mode: observatory — tiled split-screen running 4-9 simulations simultaneously."""
import curses
import math
import random
import time

from life.constants import SPEEDS

# Reuse the mini-simulation engines from mashup mode
from life.modes.mashup import MASHUP_SIMS, _ENGINES

_DENSITY = " ░▒▓█"

# ── Layout definitions ──────────────────────────────────────────────

LAYOUTS = [
    {"name": "2×1 (Side by Side)", "rows": 1, "cols": 2, "count": 2},
    {"name": "2×2 (Quad)", "rows": 2, "cols": 2, "count": 4},
    {"name": "3×2 (Wide)", "rows": 2, "cols": 3, "count": 6},
    {"name": "3×3 (Full Grid)", "rows": 3, "cols": 3, "count": 9},
]

# ── Curated presets ─────────────────────────────────────────────────

OBSERVATORY_PRESETS = [
    {
        "name": "Fluid Trio",
        "desc": "Wave Equation, Reaction-Diffusion, Physarum Slime",
        "sims": ["wave", "rd", "physarum"],
        "layout": 2,  # index into LAYOUTS → 3×2 reduced to 1×3
    },
    {
        "name": "Chaos Theory",
        "desc": "Game of Life, Rock-Paper-Scissors, Ising Model, Forest Fire",
        "sims": ["gol", "rps", "ising", "fire"],
        "layout": 1,  # 2×2
    },
    {
        "name": "Micro vs Macro",
        "desc": "Boids, Physarum, Game of Life, Wave Equation",
        "sims": ["boids", "physarum", "gol", "wave"],
        "layout": 1,
    },
    {
        "name": "Nature's Patterns",
        "desc": "Reaction-Diffusion, Forest Fire, Physarum, Rock-Paper-Scissors",
        "sims": ["rd", "fire", "physarum", "rps"],
        "layout": 1,
    },
    {
        "name": "Everything",
        "desc": "All 8 simulation engines at once plus a duplicate",
        "sims": ["gol", "wave", "rd", "fire", "boids", "ising", "rps", "physarum", "gol"],
        "layout": 3,  # 3×3
    },
]

# Color pairs for each viewport (cycling through available pairs)
_VIEWPORT_COLORS = [6, 1, 2, 3, 4, 5, 7, 6, 1]

_SIM_BY_ID = {s["id"]: s for s in MASHUP_SIMS}


# ════════════════════════════════════════════════════════════════════
#  Mode entry / exit
# ════════════════════════════════════════════════════════════════════

def _enter_observatory_mode(self):
    """Enter Observatory mode — show layout/preset selection menu."""
    self.obs_menu = True
    self.obs_menu_sel = 0
    self.obs_menu_phase = 0  # 0=presets, 1=layout, 2=pick sims
    self.obs_pick_layout = None
    self.obs_pick_sims = []
    self._flash("Simulation Observatory — pick a preset or build your own")


def _exit_observatory_mode(self):
    """Exit Observatory mode and clean up."""
    self.obs_mode = False
    self.obs_menu = False
    self.obs_running = False
    self.obs_viewports = []
    self.obs_focus = -1
    self._flash("Observatory OFF")


# ════════════════════════════════════════════════════════════════════
#  Initialization
# ════════════════════════════════════════════════════════════════════

def _observatory_init(self, sim_ids, layout_idx):
    """Initialize all viewports with the given simulations and layout."""
    max_y, max_x = self.stdscr.getmaxyx()
    layout = LAYOUTS[layout_idx]

    # Adjust layout to fit the number of sims
    count = len(sim_ids)
    # Find best fitting layout
    if count <= 2:
        grid_r, grid_c = 1, 2
    elif count <= 4:
        grid_r, grid_c = 2, 2
    elif count <= 6:
        grid_r, grid_c = 2, 3
    else:
        grid_r, grid_c = 3, 3

    self.obs_grid_rows = grid_r
    self.obs_grid_cols = grid_c

    # Calculate viewport dimensions (leave room for header/footer)
    avail_y = max(10, max_y - 3)  # header + footer
    avail_x = max(20, max_x - 1)

    vp_h = max(5, avail_y // grid_r - 1)  # -1 for border between viewports
    vp_w = max(10, avail_x // grid_c - 1)

    self.obs_vp_h = vp_h
    self.obs_vp_w = vp_w

    # Simulation grid dimensions per viewport (in cells, not chars)
    sim_rows = max(4, vp_h - 2)  # -2 for viewport title bar + padding
    sim_cols = max(4, (vp_w - 1) // 2)  # each cell = 2 chars wide

    # Initialize viewports
    self.obs_viewports = []
    for i, sid in enumerate(sim_ids):
        init_fn, _, dens_fn = _ENGINES[sid]
        state = init_fn(sim_rows, sim_cols)
        density = dens_fn(state)
        self.obs_viewports.append({
            "sim_id": sid,
            "name": _SIM_BY_ID[sid]["name"],
            "state": state,
            "density": density,
            "sim_rows": sim_rows,
            "sim_cols": sim_cols,
        })

    self.obs_generation = 0
    self.obs_running = False
    self.obs_focus = -1  # -1 = no focus, 0..N-1 = focused viewport
    self.obs_menu = False
    self.obs_mode = True
    self._flash(f"Observatory: {len(sim_ids)} viewports — Space to start")


# ════════════════════════════════════════════════════════════════════
#  Simulation step
# ════════════════════════════════════════════════════════════════════

def _observatory_step(self):
    """Advance all viewports by one generation (independent, no coupling)."""
    for vp in self.obs_viewports:
        _, step_fn, dens_fn = _ENGINES[vp["sim_id"]]
        step_fn(vp["state"], None, 0.0)  # independent: no coupling
        vp["density"] = dens_fn(vp["state"])
    self.obs_generation += 1


# ════════════════════════════════════════════════════════════════════
#  Menu drawing
# ════════════════════════════════════════════════════════════════════

def _draw_observatory_menu(self, max_y, max_x):
    """Draw the observatory mode selection menu."""
    self.stdscr.erase()
    phase = self.obs_menu_phase

    title = "── Simulation Observatory ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if phase == 0:
        # ── Preset selection ──
        subtitle = "Choose a curated combo or build your own:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass

        for i, preset in enumerate(OBSERVATORY_PRESETS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.obs_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            line = f"{marker}{preset['name']}"
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            except curses.error:
                pass
            if sel:
                try:
                    self.stdscr.addstr(y, 2 + len(line) + 2,
                                       preset["desc"][:max_x - len(line) - 6],
                                       curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass

        # Custom option
        ci = len(OBSERVATORY_PRESETS)
        y = 5 + ci
        if y < max_y - 3:
            sel = self.obs_menu_sel == ci
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(3)
            try:
                self.stdscr.addstr(y, 2, f"{marker}Custom Observatory..."[:max_x - 4], attr)
            except curses.error:
                pass

    elif phase == 1:
        # ── Pick layout ──
        subtitle = "Select a layout:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass
        for i, layout in enumerate(LAYOUTS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.obs_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2,
                                   f"{marker}{layout['name']} ({layout['count']} viewports)"[:max_x - 4],
                                   attr)
            except curses.error:
                pass

    elif phase == 2:
        # ── Pick simulations for each slot ──
        picked = len(self.obs_pick_sims)
        total = LAYOUTS[self.obs_pick_layout]["count"]
        subtitle = f"Select simulation {picked + 1} of {total}:"
        if self.obs_pick_sims:
            names = ", ".join(_SIM_BY_ID[s]["name"] for s in self.obs_pick_sims)
            subtitle += f"  (picked: {names})"
        try:
            self.stdscr.addstr(3, max(0, 2), subtitle[:max_x - 4],
                               curses.color_pair(6))
        except curses.error:
            pass
        for i, sim in enumerate(MASHUP_SIMS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.obs_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
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

def _handle_observatory_menu_key(self, key):
    """Handle input in the observatory selection menu."""
    if key == -1:
        return True
    phase = self.obs_menu_phase

    if phase == 0:
        n = len(OBSERVATORY_PRESETS) + 1
    elif phase == 1:
        n = len(LAYOUTS)
    else:
        n = len(MASHUP_SIMS)

    if key == curses.KEY_UP or key == ord("k"):
        self.obs_menu_sel = (self.obs_menu_sel - 1) % max(1, n)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.obs_menu_sel = (self.obs_menu_sel + 1) % max(1, n)
        return True
    if key == 27:  # Esc
        if phase > 0:
            self.obs_menu_phase = phase - 1
            self.obs_menu_sel = 0
            if phase == 2:
                self.obs_pick_sims = []
        else:
            self.obs_menu = False
            self._flash("Observatory cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if phase == 0:
            sel = self.obs_menu_sel
            if sel < len(OBSERVATORY_PRESETS):
                preset = OBSERVATORY_PRESETS[sel]
                self._observatory_init(preset["sims"], preset["layout"])
            else:
                self.obs_menu_phase = 1
                self.obs_menu_sel = 0
        elif phase == 1:
            self.obs_pick_layout = self.obs_menu_sel
            self.obs_pick_sims = []
            self.obs_menu_phase = 2
            self.obs_menu_sel = 0
        elif phase == 2:
            sim_id = MASHUP_SIMS[self.obs_menu_sel]["id"]
            self.obs_pick_sims.append(sim_id)
            total = LAYOUTS[self.obs_pick_layout]["count"]
            if len(self.obs_pick_sims) >= total:
                self._observatory_init(self.obs_pick_sims, self.obs_pick_layout)
            # stay on same phase for next pick
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Main simulation drawing
# ════════════════════════════════════════════════════════════════════

def _draw_observatory(self, max_y, max_x):
    """Draw the tiled observatory view."""
    self.stdscr.erase()

    # If a viewport is focused, draw it full-screen
    if self.obs_focus >= 0 and self.obs_focus < len(self.obs_viewports):
        _draw_focused_viewport(self, max_y, max_x)
        return

    # ── Title bar ──
    state = "▶ RUNNING" if self.obs_running else "⏸ PAUSED"
    n = len(self.obs_viewports)
    title = (f" OBSERVATORY: {n} viewports"
             f"  |  gen {self.obs_generation}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # ── Draw viewport grid ──
    grid_r = self.obs_grid_rows
    grid_c = self.obs_grid_cols

    avail_y = max(10, max_y - 3)
    avail_x = max(20, max_x - 1)

    vp_h = max(5, avail_y // grid_r)
    vp_w = max(10, avail_x // grid_c)

    for idx, vp in enumerate(self.obs_viewports):
        gr = idx // grid_c
        gc = idx % grid_c
        # Viewport origin (in screen coords)
        oy = 1 + gr * vp_h
        ox = gc * vp_w

        _draw_single_viewport(self, vp, idx, oy, ox, vp_h, vp_w, max_y, max_x)

    # ── Hint bar ──
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [1-9]=focus [0]=unfocus [R]=menu [q]=exit [>/<]=speed"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_single_viewport(self, vp, idx, oy, ox, vp_h, vp_w, max_y, max_x):
    """Draw a single viewport tile at (oy, ox) with size (vp_h, vp_w)."""
    color = _VIEWPORT_COLORS[idx % len(_VIEWPORT_COLORS)]

    # Viewport title
    label = f" [{idx + 1}] {vp['name']} "
    if oy < max_y:
        try:
            self.stdscr.addstr(oy, ox, label[:vp_w],
                               curses.color_pair(color) | curses.A_BOLD)
            # Fill rest of title bar with thin line
            remaining = vp_w - len(label)
            if remaining > 0:
                self.stdscr.addstr(oy, ox + len(label),
                                   "─" * remaining,
                                   curses.color_pair(color) | curses.A_DIM)
        except curses.error:
            pass

    # Viewport density grid
    density = vp["density"]
    sim_rows = vp["sim_rows"]
    sim_cols = vp["sim_cols"]
    view_rows = min(sim_rows, vp_h - 1)  # -1 for title
    view_cols = min(sim_cols, (vp_w - 1) // 2)

    for r in range(view_rows):
        sy = oy + 1 + r
        if sy >= max_y - 1:
            break
        d_row = density[r] if r < len(density) else []
        for c in range(view_cols):
            sx = ox + c * 2
            if sx + 1 >= max_x:
                break
            val = d_row[c] if c < len(d_row) else 0.0
            if val < 0.01:
                continue
            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]
            if val > 0.7:
                attr = curses.color_pair(color) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(color)
            else:
                attr = curses.color_pair(color) | curses.A_DIM
            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass


def _draw_focused_viewport(self, max_y, max_x):
    """Draw a single viewport expanded to full screen."""
    vp = self.obs_viewports[self.obs_focus]
    color = _VIEWPORT_COLORS[self.obs_focus % len(_VIEWPORT_COLORS)]

    # Title bar
    state = "▶ RUNNING" if self.obs_running else "⏸ PAUSED"
    title = (f" OBSERVATORY [{self.obs_focus + 1}] {vp['name']}"
             f"  |  gen {self.obs_generation}"
             f"  |  {state}"
             f"  |  [0]=unfocus")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(color) | curses.A_BOLD)
    except curses.error:
        pass

    # Re-render density at full resolution for focused view
    density = vp["density"]
    sim_rows = vp["sim_rows"]
    sim_cols = vp["sim_cols"]
    view_rows = min(sim_rows, max_y - 4)
    view_cols = min(sim_cols, (max_x - 1) // 2)

    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 2:
            break
        d_row = density[r] if r < len(density) else []
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            val = d_row[c] if c < len(d_row) else 0.0
            if val < 0.01:
                continue
            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]
            if val > 0.7:
                attr = curses.color_pair(color) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(color)
            else:
                attr = curses.color_pair(color) | curses.A_DIM
            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [0]=unfocus [1-9]=switch [q]=exit [>/<]=speed"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Simulation key handling
# ════════════════════════════════════════════════════════════════════

def _handle_observatory_key(self, key):
    """Handle input during active observatory simulation."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_observatory_mode()
        return True
    if key == ord(" "):
        self.obs_running = not self.obs_running
        self._flash("Playing" if self.obs_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.obs_running = False
        self._observatory_step()
        return True
    # Focus: 1-9 to zoom into viewport, 0 to unfocus
    if ord("1") <= key <= ord("9"):
        idx = key - ord("1")
        if idx < len(self.obs_viewports):
            self.obs_focus = idx
            self._flash(f"Focused: [{idx + 1}] {self.obs_viewports[idx]['name']}")
        return True
    if key == ord("0"):
        if self.obs_focus >= 0:
            self.obs_focus = -1
            self._flash("Unfocused — showing all viewports")
        return True
    if key == ord("r"):
        # Reset all viewports
        sims = [vp["sim_id"] for vp in self.obs_viewports]
        layout_idx = 0
        count = len(sims)
        if count <= 2:
            layout_idx = 0
        elif count <= 4:
            layout_idx = 1
        elif count <= 6:
            layout_idx = 2
        else:
            layout_idx = 3
        self._observatory_init(sims, layout_idx)
        self._flash("Reset!")
        return True
    if key == ord("R"):
        self.obs_mode = False
        self.obs_running = False
        self.obs_menu = True
        self.obs_menu_phase = 0
        self.obs_menu_sel = 0
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
    """Register observatory mode methods on the App class."""
    App._enter_observatory_mode = _enter_observatory_mode
    App._exit_observatory_mode = _exit_observatory_mode
    App._observatory_init = _observatory_init
    App._observatory_step = _observatory_step
    App._handle_observatory_menu_key = _handle_observatory_menu_key
    App._handle_observatory_key = _handle_observatory_key
    App._draw_observatory_menu = _draw_observatory_menu
    App._draw_observatory = _draw_observatory
