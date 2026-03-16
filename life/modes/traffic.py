"""Mode: traffic — Nagel-Schreckenberg cellular automaton with multi-lane
lane-changing, on-ramp merging, and a real-time fundamental diagram overlay.

Vehicles accelerate, brake for gaps, randomly dawdle, and optionally change
lanes.  Emergent phenomena include phantom traffic jams, stop-and-go waves,
flow–density phase transitions, and on-ramp bottleneck queuing.
"""
import curses
import math
import random
import time

# ══════════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════════
# (name, description, vmax, p_slow, density, lanes, kind)
# kind: "open"      — periodic ring road
#       "bottleneck" — reduced speed zone in the middle
#       "onramp"     — on-ramp merging from a slip road
#       "incident"   — stalled car blocking a lane mid-road

TRAFFIC_PRESETS = [
    ("Open Highway",
     "Free-flow ring road — watch phantom jams nucleate",
     5, 0.3, 0.15, 4, "open"),
    ("Moderate Flow",
     "Medium density — stop-and-go waves emerge",
     5, 0.3, 0.28, 4, "open"),
    ("Rush Hour",
     "High density — persistent jam clusters",
     5, 0.3, 0.42, 4, "open"),
    ("Gridlock",
     "Near-capacity — almost all cars stopped",
     5, 0.3, 0.60, 4, "open"),
    ("Bottleneck",
     "Speed drops to 2 in the centre third — flow breakdown",
     5, 0.3, 0.25, 4, "bottleneck"),
    ("On-Ramp Merge",
     "Slip road feeds into lane 0 — merging disrupts flow",
     5, 0.3, 0.22, 4, "onramp"),
    ("Incident",
     "Stalled vehicle blocks lane 1 — rubbernecking cascade",
     5, 0.3, 0.25, 4, "incident"),
    ("Cautious Drivers",
     "High dawdling probability — fragile flow",
     5, 0.50, 0.22, 4, "open"),
    ("Aggressive Drivers",
     "Low dawdling — smooth until a single brake cascades",
     5, 0.10, 0.30, 4, "open"),
    ("Wide Highway",
     "8 lanes of moderate traffic with lane-changing",
     5, 0.3, 0.25, 8, "open"),
]

# ── Car glyphs & colours ─────────────────────────────────────────────────
# Index by speed: 0 (stopped) → vmax (cruising)
_CAR_CHARS = ["█", "▓", "▒", "░", "◆", "►"]
# curses color pair: 1=red, 2=green, 3=yellow, 6=cyan
_SPEED_COLORS = [1, 1, 3, 3, 6, 2, 2]

# Sparkline bars for the fundamental diagram (8 levels)
_SPARK = " ▁▂▃▄▅▆▇█"


# ══════════════════════════════════════════════════════════════════════════
#  Lifecycle
# ══════════════════════════════════════════════════════════════════════════

def _enter_traffic_mode(self):
    self.traffic_menu = True
    self.traffic_menu_sel = 0
    self._flash("Traffic Flow (Nagel-Schreckenberg) — select a scenario")


def _exit_traffic_mode(self):
    self.traffic_mode = False
    self.traffic_menu = False
    self.traffic_running = False
    self.traffic_grid = []
    self._flash("Traffic Flow mode OFF")


def _traffic_init(self, preset_idx: int):
    name, _desc, vmax, p_slow, density, lanes, kind = self.TRAFFIC_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = min(lanes, max(2, max_y - 6))
    cols = max(40, max_x - 2)

    self.traffic_rows = rows
    self.traffic_cols = cols
    self.traffic_vmax = vmax
    self.traffic_p_slow = p_slow
    self.traffic_density = density
    self.traffic_preset_name = name
    self.traffic_kind = kind
    self.traffic_generation = 0
    self.traffic_steps_per_frame = 1
    self.traffic_lane_change = True
    self.traffic_show_diagram = True
    self.traffic_view = 0  # 0=road, 1=space-time

    # Fundamental-diagram history: list of (density, flow) samples
    self.traffic_fd_history = []
    self.traffic_fd_max = 300  # keep last N samples

    # Space-time diagram ring buffer (rows = time, cols = road position)
    # Stores average speed across lanes at each position per step
    self.traffic_st_height = max(10, max_y - 6)
    self.traffic_st_buf = []  # list of rows, each row = list of float speeds (or -1)

    # On-ramp state
    self.traffic_onramp_start = cols // 3
    self.traffic_onramp_end = cols // 3 + cols // 6
    self.traffic_onramp_rate = 0.08  # probability of car appearing per step

    # Bottleneck zone
    self.traffic_bn_start = cols // 3
    self.traffic_bn_end = 2 * cols // 3
    self.traffic_bn_vmax = 2

    # Incident position (lane, col)
    self.traffic_incident_lane = min(1, rows - 1)
    self.traffic_incident_col = cols // 2

    # Initialize grid: -1 = empty, 0..vmax = car with that speed
    grid = [[-1] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if random.random() < density:
                grid[r][c] = random.randint(0, vmax)
    # For incident: place a permanent obstacle (speed = -2)
    if kind == "incident":
        grid[self.traffic_incident_lane][self.traffic_incident_col] = -2

    self.traffic_grid = grid
    self._traffic_compute_stats()

    self.traffic_mode = True
    self.traffic_menu = False
    self.traffic_running = False
    self._flash(f"Traffic: {name} — Space to start, v=view, f=diagram")


# ══════════════════════════════════════════════════════════════════════════
#  Statistics
# ══════════════════════════════════════════════════════════════════════════

def _traffic_compute_stats(self):
    grid = self.traffic_grid
    rows, cols = self.traffic_rows, self.traffic_cols
    total_speed = 0
    car_count = 0
    for r in range(rows):
        for c in range(cols):
            v = grid[r][c]
            if v > 0:
                total_speed += v
                car_count += 1
            elif v == 0:
                car_count += 1
    total_cells = rows * cols
    if car_count > 0:
        self.traffic_avg_speed = total_speed / car_count
        self.traffic_flow = total_speed / total_cells
        self.traffic_measured_density = car_count / total_cells
    else:
        self.traffic_avg_speed = 0.0
        self.traffic_flow = 0.0
        self.traffic_measured_density = 0.0

    # Record fundamental-diagram sample
    fd = self.traffic_fd_history
    fd.append((self.traffic_measured_density, self.traffic_flow))
    if len(fd) > self.traffic_fd_max:
        del fd[: len(fd) - self.traffic_fd_max]

    # Record space-time row (average speed per column)
    st_row = []
    for c in range(cols):
        sv = 0.0
        sc = 0
        for r in range(rows):
            v = grid[r][c]
            if v >= 0:
                sv += v
                sc += 1
        st_row.append(sv / sc if sc > 0 else -1.0)
    self.traffic_st_buf.append(st_row)
    if len(self.traffic_st_buf) > self.traffic_st_height:
        del self.traffic_st_buf[: len(self.traffic_st_buf) - self.traffic_st_height]


# ══════════════════════════════════════════════════════════════════════════
#  Simulation step
# ══════════════════════════════════════════════════════════════════════════

def _traffic_gap(grid, r, c, cols):
    """Distance to next car ahead on lane r from position c (periodic)."""
    for d in range(1, cols):
        nc = (c + d) % cols
        v = grid[r][nc]
        if v >= 0 or v == -2:  # car or incident obstacle
            return d - 1
    return cols - 1


def _traffic_gap_back(grid, r, c, cols):
    """Distance to nearest car *behind* on lane r from position c (periodic)."""
    for d in range(1, cols):
        nc = (c - d) % cols
        v = grid[r][nc]
        if v >= 0 or v == -2:
            return d - 1
    return cols - 1


def _traffic_step(self):
    grid = self.traffic_grid
    rows, cols = self.traffic_rows, self.traffic_cols
    vmax = self.traffic_vmax
    p_slow = self.traffic_p_slow
    kind = self.traffic_kind
    rand = random.random

    # Effective vmax per cell (bottleneck reduces it)
    def eff_vmax(r, c):
        if kind == "bottleneck" and self.traffic_bn_start <= c < self.traffic_bn_end:
            return self.traffic_bn_vmax
        return vmax

    # ── Lane-changing phase (STCA symmetric rule) ─────────────────────
    if self.traffic_lane_change and rows > 1:
        for r in range(rows):
            for c in range(cols):
                v = grid[r][c]
                if v < 0:
                    continue  # empty or obstacle
                gap_cur = _traffic_gap(grid, r, c, cols)
                if gap_cur >= v + 1:
                    continue  # enough room, no need to change

                # Try a random adjacent lane
                dr = random.choice([-1, 1])
                nr = r + dr
                if nr < 0 or nr >= rows:
                    continue

                # Target lane must be empty at c
                if grid[nr][c] >= 0 or grid[nr][c] == -2:
                    continue

                gap_new = _traffic_gap(grid, nr, c, cols)
                if gap_new <= gap_cur:
                    continue  # not better

                gap_back = _traffic_gap_back(grid, nr, c, cols)
                if gap_back < vmax:
                    continue  # would cut off car behind

                # Execute lane change
                grid[nr][c] = v
                grid[r][c] = -1

    # ── On-ramp injection ─────────────────────────────────────────────
    if kind == "onramp":
        if rand() < self.traffic_onramp_rate:
            # Try to inject a car at a random position in the ramp zone, lane 0
            ramp_c = random.randint(self.traffic_onramp_start, self.traffic_onramp_end - 1)
            if grid[0][ramp_c] == -1:
                grid[0][ramp_c] = random.randint(0, max(1, vmax - 2))

    # ── NaSch update (parallel) ───────────────────────────────────────
    new_grid = [[-1] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            v = grid[r][c]
            if v == -2:
                # Incident obstacle: stays in place
                new_grid[r][c] = -2
                continue
            if v < 0:
                continue

            vm = eff_vmax(r, c)

            # 1. Acceleration
            v = min(v + 1, vm)

            # 2. Braking (gap)
            gap = _traffic_gap(grid, r, c, cols)
            v = min(v, gap)

            # 3. Random dawdling
            if v > 0 and rand() < p_slow:
                v -= 1

            # 4. Movement
            new_c = (c + v) % cols
            if new_grid[r][new_c] == -1:
                new_grid[r][new_c] = v
            else:
                # Collision avoidance fallback: stay put
                if new_grid[r][c] == -1:
                    new_grid[r][c] = 0
                else:
                    # Very rare edge case: find nearest empty
                    for off in range(1, 4):
                        fc = (c + off) % cols
                        if new_grid[r][fc] == -1:
                            new_grid[r][fc] = 0
                            break

    self.traffic_grid = new_grid
    self.traffic_generation += 1
    self._traffic_compute_stats()


# ══════════════════════════════════════════════════════════════════════════
#  Key handling
# ══════════════════════════════════════════════════════════════════════════

def _handle_traffic_menu_key(self, key: int) -> bool:
    presets = self.TRAFFIC_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.traffic_menu_sel = (self.traffic_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.traffic_menu_sel = (self.traffic_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._traffic_init(self.traffic_menu_sel)
    elif key == ord("q") or key == 27:
        self.traffic_menu = False
        self._flash("Traffic Flow cancelled")
    return True


def _handle_traffic_key(self, key: int) -> bool:
    if key == ord("q") or key == 27:
        self._exit_traffic_mode()
        return True
    if key == ord(" "):
        self.traffic_running = not self.traffic_running
        return True
    if key == ord("n") or key == ord("."):
        self._traffic_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.TRAFFIC_PRESETS) if p[0] == self.traffic_preset_name), 0)
        self._traffic_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.traffic_mode = False
        self.traffic_running = False
        self.traffic_menu = True
        self.traffic_menu_sel = 0
        return True
    # View toggle
    if key == ord("v"):
        self.traffic_view = (self.traffic_view + 1) % 2
        labels = ["Road View", "Space-Time Diagram"]
        self._flash(f"View: {labels[self.traffic_view]}")
        return True
    # Fundamental diagram toggle
    if key == ord("f"):
        self.traffic_show_diagram = not self.traffic_show_diagram
        self._flash("Fundamental diagram " + ("ON" if self.traffic_show_diagram else "OFF"))
        return True
    # Lane-change toggle
    if key == ord("l"):
        self.traffic_lane_change = not self.traffic_lane_change
        self._flash("Lane-changing " + ("ON" if self.traffic_lane_change else "OFF"))
        return True
    # Speed controls
    if key == ord("+") or key == ord("="):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.traffic_steps_per_frame) if self.traffic_steps_per_frame in choices else 0
        self.traffic_steps_per_frame = choices[min(idx + 1, len(choices) - 1)]
        self._flash(f"Speed: {self.traffic_steps_per_frame} steps/frame")
        return True
    if key == ord("-") or key == ord("_"):
        choices = [1, 2, 3, 5, 10, 20, 50]
        idx = choices.index(self.traffic_steps_per_frame) if self.traffic_steps_per_frame in choices else 0
        self.traffic_steps_per_frame = choices[max(idx - 1, 0)]
        self._flash(f"Speed: {self.traffic_steps_per_frame} steps/frame")
        return True
    # Density
    if key == ord("d"):
        self.traffic_density = max(0.01, self.traffic_density - 0.05)
        self._flash(f"Density: {self.traffic_density:.2f}")
        return True
    if key == ord("D"):
        self.traffic_density = min(0.95, self.traffic_density + 0.05)
        self._flash(f"Density: {self.traffic_density:.2f}")
        return True
    # Slowdown probability
    if key == ord("p"):
        self.traffic_p_slow = max(0.0, self.traffic_p_slow - 0.05)
        self._flash(f"P(slow): {self.traffic_p_slow:.2f}")
        return True
    if key == ord("P"):
        self.traffic_p_slow = min(1.0, self.traffic_p_slow + 0.05)
        self._flash(f"P(slow): {self.traffic_p_slow:.2f}")
        return True
    return True


# ══════════════════════════════════════════════════════════════════════════
#  Drawing — Menu
# ══════════════════════════════════════════════════════════════════════════

def _draw_traffic_menu(self, max_y: int, max_x: int):
    self.stdscr.erase()
    title = "── Traffic Flow (Nagel-Schreckenberg) ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Description block
    desc_lines = [
        "Multi-lane cellular automaton: vehicles accelerate, brake for gaps,",
        "randomly dawdle, and change lanes.  Produces phantom jams, stop-and-go",
        "waves, and flow-density phase transitions with a fundamental diagram.",
    ]
    for i, dl in enumerate(desc_lines):
        try:
            self.stdscr.addstr(3 + i, 4, dl[:max_x - 6], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    y0 = 3 + len(desc_lines) + 1
    for i, (name, desc, vmax, p_slow, density, lanes, kind) in enumerate(self.TRAFFIC_PRESETS):
        y = y0 + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.traffic_menu_sel else "  "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.traffic_menu_sel else curses.color_pair(7)
        tag = f"[{kind}]"
        line = f"{marker}{name:22s} {tag:13s} v={vmax} p={p_slow:.1f} ρ={density:.2f} {lanes}L  {desc}"
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


# ══════════════════════════════════════════════════════════════════════════
#  Drawing — Fundamental Diagram (flow vs density scatter)
# ══════════════════════════════════════════════════════════════════════════

def _draw_traffic_fd(self, x0, y0, w, h, max_y, max_x):
    """Draw a small ASCII fundamental diagram at (y0, x0) with size w x h."""
    if h < 4 or w < 10:
        return
    fd = self.traffic_fd_history
    if not fd:
        return

    # Axes ranges
    max_rho = max(0.8, max(d for d, _ in fd) * 1.2) if fd else 1.0
    max_flow = max(0.05, max(f for _, f in fd) * 1.2) if fd else 0.5

    # Border
    try:
        self.stdscr.addstr(y0, x0, "Flow", curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass
    for dy in range(1, h):
        ry = y0 + dy
        if 0 <= ry < max_y and x0 < max_x:
            try:
                self.stdscr.addstr(ry, x0, "│", curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass
    # Bottom axis
    bot_y = y0 + h
    if 0 <= bot_y < max_y:
        axis = "└" + "─" * (w - 2) + " ρ"
        try:
            self.stdscr.addstr(bot_y, x0, axis[:max_x - x0 - 1], curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass

    # Plot points — use a grid of counts to decide intensity
    canvas: dict[tuple[int, int], int] = {}
    plot_w = w - 2
    plot_h = h - 1
    for rho, flow in fd:
        px = int(rho / max_rho * (plot_w - 1)) if max_rho > 0 else 0
        py = int((1.0 - flow / max_flow) * (plot_h - 1)) if max_flow > 0 else plot_h - 1
        px = max(0, min(plot_w - 1, px))
        py = max(0, min(plot_h - 1, py))
        canvas[(py, px)] = canvas.get((py, px), 0) + 1

    max_cnt = max(canvas.values()) if canvas else 1
    for (py, px), cnt in canvas.items():
        sy = y0 + 1 + py
        sx = x0 + 1 + px
        if 0 <= sy < max_y and 0 <= sx < max_x - 1:
            intensity = min(len(_SPARK) - 1, max(1, int(cnt / max_cnt * (len(_SPARK) - 1))))
            ch = _SPARK[intensity]
            # Recent points brighter
            cp = 2 if cnt > 1 else 6
            try:
                self.stdscr.addstr(sy, sx, ch, curses.color_pair(cp) | curses.A_BOLD)
            except curses.error:
                pass

    # Mark current point
    if fd:
        rho, flow = fd[-1]
        px = int(rho / max_rho * (plot_w - 1)) if max_rho > 0 else 0
        py = int((1.0 - flow / max_flow) * (plot_h - 1)) if max_flow > 0 else plot_h - 1
        px = max(0, min(plot_w - 1, px))
        py = max(0, min(plot_h - 1, py))
        sy = y0 + 1 + py
        sx = x0 + 1 + px
        if 0 <= sy < max_y and 0 <= sx < max_x - 1:
            try:
                self.stdscr.addstr(sy, sx, "●", curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass


# ══════════════════════════════════════════════════════════════════════════
#  Drawing — Space-Time Diagram
# ══════════════════════════════════════════════════════════════════════════

def _draw_traffic_spacetime(self, max_y: int, max_x: int):
    """Draw space-time diagram: x = position along road, y = time (newest at bottom)."""
    self.stdscr.erase()
    state = "▶ RUNNING" if self.traffic_running else "⏸ PAUSED"
    title = (f" Traffic Space-Time: {self.traffic_preset_name}  |  "
             f"step {self.traffic_generation}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    buf = self.traffic_st_buf
    vmax = self.traffic_vmax
    view_h = min(len(buf), max_y - 4)
    view_w = min(self.traffic_cols, max_x - 2)

    # Density chars: dark = jam, light = free flow
    density_ch = ["█", "▓", "▒", "░", "·", " "]

    start_idx = max(0, len(buf) - view_h)
    for ti in range(view_h):
        row = buf[start_idx + ti]
        sy = 1 + ti
        if sy >= max_y - 2:
            break
        for c in range(min(view_w, len(row))):
            v = row[c]
            if v < 0:
                ch = " "
                cp = 7
            else:
                frac = v / vmax if vmax > 0 else 0
                ci = min(len(density_ch) - 1, int((1.0 - frac) * (len(density_ch) - 0.01)))
                ch = density_ch[ci]
                if frac < 0.2:
                    cp = 1  # red = jam
                elif frac < 0.5:
                    cp = 3  # yellow
                elif frac < 0.8:
                    cp = 6  # cyan
                else:
                    cp = 2  # green = free
            try:
                self.stdscr.addstr(sy, c, ch, curses.color_pair(cp))
            except curses.error:
                pass

    # Legend
    leg_y = max_y - 2
    if leg_y > 1:
        legend = " ← time │ x → position │ dark=jam  light=free │ [v]=road view"
        try:
            self.stdscr.addstr(leg_y, 0, legend[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    _draw_traffic_hint(self, max_y, max_x)


# ══════════════════════════════════════════════════════════════════════════
#  Drawing — Road View (main)
# ══════════════════════════════════════════════════════════════════════════

def _draw_traffic_hint(self, max_y, max_x):
    """Draw hint bar at bottom."""
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            lc = "ON" if self.traffic_lane_change else "OFF"
            hint = (f" [Space]=play [n]=step [v]=view [f]=diagram [l]=lanes({lc})"
                    f" [d/D]=ρ [p/P]=brake [+/-]=speed [r]=reset [R]=menu [q]=exit")
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_traffic(self, max_y: int, max_x: int):
    # Dispatch to space-time view if selected
    if self.traffic_view == 1:
        _draw_traffic_spacetime(self, max_y, max_x)
        return

    self.stdscr.erase()
    grid = self.traffic_grid
    rows, cols = self.traffic_rows, self.traffic_cols
    kind = self.traffic_kind
    state = "▶ RUNNING" if self.traffic_running else "⏸ PAUSED"

    # Title bar
    lc_tag = "LC" if self.traffic_lane_change else "no-LC"
    title = (f" Traffic: {self.traffic_preset_name} [{kind}]  |  "
             f"step {self.traffic_generation}  |  "
             f"ρ={self.traffic_measured_density:.2f}  "
             f"v̄={self.traffic_avg_speed:.2f}  "
             f"J={self.traffic_flow:.3f}  |  {lc_tag}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Determine diagram size if shown (right side)
    fd_w = 0
    if self.traffic_show_diagram:
        fd_w = min(36, max(0, max_x - cols - 4))
        if fd_w < 12:
            fd_w = 0

    view_cols = min(cols, max_x - 2 - fd_w)

    # Draw road lanes
    for r in range(rows):
        sy = 2 + r * 2
        if sy >= max_y - 3:
            break

        # Lane separator above
        if r == 0 and sy - 1 >= 1:
            sep = "═" * view_cols
            try:
                self.stdscr.addstr(sy - 1, 0, sep[:max_x - 1], curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass

        # Draw cars
        for c in range(view_cols):
            v = grid[r][c]
            if v == -2:
                # Incident obstacle
                try:
                    self.stdscr.addstr(sy, c, "X", curses.color_pair(1) | curses.A_BOLD | curses.A_BLINK)
                except curses.error:
                    pass
            elif v >= 0:
                ci = min(v, len(_CAR_CHARS) - 1)
                ch = _CAR_CHARS[ci]
                color = _SPEED_COLORS[min(v, len(_SPEED_COLORS) - 1)]
                try:
                    self.stdscr.addstr(sy, c, ch, curses.color_pair(color) | curses.A_BOLD)
                except curses.error:
                    pass
            else:
                # Empty road
                # Mark special zones
                is_ramp = (kind == "onramp" and r == 0
                           and self.traffic_onramp_start <= c < self.traffic_onramp_end)
                is_bn = (kind == "bottleneck"
                         and self.traffic_bn_start <= c < self.traffic_bn_end)
                if is_ramp:
                    ch = "▪"
                    cp = 5  # magenta
                elif is_bn:
                    ch = "▫"
                    cp = 3  # yellow
                else:
                    ch = "·"
                    cp = 7
                try:
                    self.stdscr.addstr(sy, c, ch, curses.color_pair(cp) | curses.A_DIM)
                except curses.error:
                    pass

        # Lane separator below
        sep_y = sy + 1
        if sep_y < max_y - 3:
            sep_ch = "─"
            try:
                self.stdscr.addstr(sep_y, 0, sep_ch * view_cols, curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass

    # Fundamental diagram overlay (right side)
    if fd_w > 0 and self.traffic_show_diagram:
        fd_x = max_x - fd_w - 1
        road_end_y = 2 + rows * 2
        fd_h = max(5, min(max_y - 5, road_end_y - 2))
        _draw_traffic_fd(self, fd_x, 1, fd_w, fd_h, max_y, max_x)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        car_count = sum(1 for r in range(rows) for c in range(cols) if grid[r][c] >= 0)
        total = rows * cols
        info = (f" Step {self.traffic_generation}  |  {car_count} cars / {total} cells"
                f"  |  v̄={self.traffic_avg_speed:.2f}/{self.traffic_vmax}"
                f"  J={self.traffic_flow:.3f}"
                f"  ρ={self.traffic_measured_density:.2f}"
                f"  |  {self.traffic_steps_per_frame} st/f")
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    _draw_traffic_hint(self, max_y, max_x)


# ══════════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════════

def register(App):
    """Register Traffic Flow mode methods on the App class."""
    App.TRAFFIC_PRESETS = TRAFFIC_PRESETS
    App._enter_traffic_mode = _enter_traffic_mode
    App._exit_traffic_mode = _exit_traffic_mode
    App._traffic_init = _traffic_init
    App._traffic_compute_stats = _traffic_compute_stats
    App._traffic_step = _traffic_step
    App._handle_traffic_menu_key = _handle_traffic_menu_key
    App._handle_traffic_key = _handle_traffic_key
    App._draw_traffic_menu = _draw_traffic_menu
    App._draw_traffic = _draw_traffic
    App._draw_traffic_fd = _draw_traffic_fd
    App._draw_traffic_spacetime = _draw_traffic_spacetime
