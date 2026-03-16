"""Mode: voronoi — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_voronoi_mode(self):
    """Enter Voronoi Crystal Growth mode — show preset menu."""
    self.voronoi_menu = True
    self.voronoi_menu_sel = 0
    self._flash("Voronoi Crystal Growth — select a scenario")



def _exit_voronoi_mode(self):
    """Exit Voronoi Crystal Growth mode."""
    self.voronoi_mode = False
    self.voronoi_menu = False
    self.voronoi_running = False
    self.voronoi_grid = []
    self.voronoi_seeds = []
    self.voronoi_angles = []
    self.voronoi_frontier = []
    self._flash("Voronoi Crystal Growth OFF")



def _voronoi_init(self, preset_idx: int):
    """Initialize voronoi simulation with selected preset."""
    name, _desc, num_seeds, aniso, seed_mode = self.VORONOI_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max_y - 2
    cols = (max_x - 1) // 2
    if rows < 5 or cols < 5:
        return

    self.voronoi_rows = rows
    self.voronoi_cols = cols
    self.voronoi_num_seeds = num_seeds
    self.voronoi_aniso = aniso
    self.voronoi_preset_name = name
    self.voronoi_generation = 0
    self.voronoi_grid = [[-1] * cols for _ in range(rows)]
    self.voronoi_seeds = []
    self.voronoi_angles = []
    self.voronoi_frontier = []

    # Place seeds based on mode
    if seed_mode == "edge":
        # Seeds along left edge
        for i in range(num_seeds):
            r = int((i + 0.5) * rows / num_seeds)
            c = 0
            self.voronoi_seeds.append((r, c))
            self.voronoi_angles.append(random.random() * math.pi * 2)
    elif seed_mode == "bicrystal":
        # Two seeds on opposite sides
        self.voronoi_seeds.append((rows // 2, cols // 4))
        self.voronoi_angles.append(0.0)
        self.voronoi_seeds.append((rows // 2, 3 * cols // 4))
        self.voronoi_angles.append(math.pi / 3)
    elif seed_mode == "center":
        # Seeds clustered near center
        cr, cc = rows // 2, cols // 2
        for _i in range(num_seeds):
            angle = random.random() * math.pi * 2
            dist = random.random() * min(rows, cols) * 0.15
            r = int(cr + dist * math.sin(angle))
            c = int(cc + dist * math.cos(angle))
            r = max(0, min(rows - 1, r))
            c = max(0, min(cols - 1, c))
            self.voronoi_seeds.append((r, c))
            self.voronoi_angles.append(random.random() * math.pi * 2)
    else:
        # Random placement
        for _i in range(num_seeds):
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            self.voronoi_seeds.append((r, c))
            self.voronoi_angles.append(random.random() * math.pi * 2)

    # Initialize seeds on grid and frontier
    for gid, (r, c) in enumerate(self.voronoi_seeds):
        self.voronoi_grid[r][c] = gid
        # Add neighbors to frontier
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and self.voronoi_grid[nr][nc] == -1:
                    self.voronoi_frontier.append((nr, nc, gid))

    self.voronoi_grain_count = len(self.voronoi_seeds)
    self.voronoi_steps_per_frame = getattr(self, 'voronoi_steps_per_frame', 8)
    self.voronoi_menu = False
    self.voronoi_mode = True
    self.voronoi_running = True



def _voronoi_step(self):
    """Advance voronoi crystal growth by one step."""
    if not self.voronoi_frontier:
        return

    rows = self.voronoi_rows
    cols = self.voronoi_cols
    grid = self.voronoi_grid
    aniso = self.voronoi_aniso

    # Process frontier in random order for natural growth
    random.shuffle(self.voronoi_frontier)

    new_frontier: list[tuple[int, int, int]] = []
    claimed_this_step: set[tuple[int, int]] = set()

    for r, c, gid in self.voronoi_frontier:
        if grid[r][c] != -1:
            continue  # already claimed

        # Anisotropic growth probability
        # Direction from seed to this cell
        sr, sc = self.voronoi_seeds[gid]
        dr = r - sr
        dc = c - sc
        if dr == 0 and dc == 0:
            prob = 1.0
        else:
            angle_to_cell = math.atan2(dr, dc)
            preferred = self.voronoi_angles[gid]
            # Angular difference — growth is faster along preferred direction
            diff = abs(angle_to_cell - preferred)
            if diff > math.pi:
                diff = 2 * math.pi - diff
            # Probability: 1.0 along preferred axis, reduced perpendicular
            prob = 1.0 - aniso * (diff / math.pi)
            prob = max(0.1, prob)

        if random.random() < prob:
            grid[r][c] = gid
            claimed_this_step.add((r, c))
            # Add unclaimed neighbors to frontier
            for ddr in (-1, 0, 1):
                for ddc in (-1, 0, 1):
                    if ddr == 0 and ddc == 0:
                        continue
                    nr, nc = r + ddr, c + ddc
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == -1:
                        if (nr, nc) not in claimed_this_step:
                            new_frontier.append((nr, nc, gid))
        else:
            # Keep in frontier for next step
            new_frontier.append((r, c, gid))

    self.voronoi_frontier = new_frontier
    self.voronoi_generation += 1



def _voronoi_is_boundary(self, r: int, c: int) -> bool:
    """Check if cell (r, c) is on a grain boundary."""
    grid = self.voronoi_grid
    gid = grid[r][c]
    if gid == -1:
        return False
    rows = self.voronoi_rows
    cols = self.voronoi_cols
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                ngid = grid[nr][nc]
                if ngid != -1 and ngid != gid:
                    return True
    return False



def _handle_voronoi_menu_key(self, key: int) -> bool:
    """Handle keys in voronoi preset menu."""
    if key == curses.KEY_UP:
        self.voronoi_menu_sel = (self.voronoi_menu_sel - 1) % len(self.VORONOI_PRESETS)
    elif key == curses.KEY_DOWN:
        self.voronoi_menu_sel = (self.voronoi_menu_sel + 1) % len(self.VORONOI_PRESETS)
    elif key in (curses.KEY_ENTER, 10, 13):
        self._voronoi_init(self.voronoi_menu_sel)
    elif key == 27 or key == ord("q") or key == ord("%"):
        self.voronoi_menu = False
        self._flash("Voronoi Crystal Growth cancelled")
    else:
        return True
    return True



def _handle_voronoi_key(self, key: int) -> bool:
    """Handle keys during voronoi simulation."""
    if key == ord(" "):
        self.voronoi_running = not self.voronoi_running
    elif key == ord("n"):
        self._voronoi_step()
    elif key == ord("+") or key == ord("="):
        self.voronoi_steps_per_frame = min(50, self.voronoi_steps_per_frame + 2)
        self._flash(f"Steps/frame: {self.voronoi_steps_per_frame}")
    elif key == ord("-"):
        self.voronoi_steps_per_frame = max(1, self.voronoi_steps_per_frame - 2)
        self._flash(f"Steps/frame: {self.voronoi_steps_per_frame}")
    elif key == ord("r"):
        # Reset with same preset
        idx = self.voronoi_menu_sel
        self._voronoi_init(idx)
    elif key == ord("R"):
        self.voronoi_mode = False
        self.voronoi_menu = True
        self.voronoi_running = False
    elif key == ord("q") or key == ord("%"):
        self._exit_voronoi_mode()
    elif key == ord("a"):
        # Increase anisotropy
        self.voronoi_aniso = min(0.9, self.voronoi_aniso + 0.05)
        self._flash(f"Anisotropy: {self.voronoi_aniso:.2f}")
    elif key == ord("A"):
        # Decrease anisotropy
        self.voronoi_aniso = max(0.0, self.voronoi_aniso - 0.05)
        self._flash(f"Anisotropy: {self.voronoi_aniso:.2f}")
    else:
        return True
    return True



def _draw_voronoi_menu(self, max_y: int, max_x: int):
    """Draw the voronoi preset selection menu."""
    self.stdscr.erase()
    title = "── Voronoi Crystal Growth ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.VORONOI_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.voronoi_menu_sel else "  "
        attr = curses.A_BOLD if i == self.voronoi_menu_sel else 0
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], curses.color_pair(7) | attr)
        except curses.error:
            pass
        if y + 1 < max_y - 1:
            try:
                self.stdscr.addstr(y + 1, 6, desc[:max_x - 7], curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    # Footer
    foot_y = max_y - 1
    if foot_y > 0:
        foot = " [↑/↓]=select  [Enter]=start  [q]=cancel"
        try:
            self.stdscr.addstr(foot_y, 0, foot[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_voronoi(self, max_y: int, max_x: int):
    """Draw the active voronoi crystal growth simulation."""
    self.stdscr.erase()
    rows = self.voronoi_rows
    cols = self.voronoi_cols
    grid = self.voronoi_grid
    gen = self.voronoi_generation
    frontier_count = len(self.voronoi_frontier)

    # Title bar
    status = "GROWING" if self.voronoi_running and frontier_count > 0 else ("COMPLETE" if frontier_count == 0 else "PAUSED")
    title = (f" Voronoi: {self.voronoi_preset_name}  |  step {gen}"
             f"  |  grains: {self.voronoi_grain_count}"
             f"  |  aniso: {self.voronoi_aniso:.2f}"
             f"  |  {status}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 2)
    view_cols = min(cols, (max_x - 1) // 2)

    num_grain_colors = 15  # pairs 100-114
    for r in range(view_rows):
        for c in range(view_cols):
            sy = r + 1
            sx = c * 2
            gid = grid[r][c]
            if gid == -1:
                # Unclaimed — empty space
                ch = "  "
                attr = 0
            elif self._voronoi_is_boundary(r, c):
                # Grain boundary
                ch = "▒▒"
                attr = curses.color_pair(115) | curses.A_DIM
            else:
                # Interior of grain — color based on grain ID
                color_idx = 100 + (gid % num_grain_colors)
                ch = "██"
                attr = curses.color_pair(color_idx)
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
            hint = " [Space]=play [n]=step [a/A]=aniso+/- [+/-]=steps/f [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


VORONOI_PRESETS = [
    # (name, description, num_seeds, anisotropy, seed_mode)
    ("Fine Microstructure",
     "Many small grains — dense polycrystalline texture",
     60, 0.20, "random"),
    ("Coarse Grains",
     "Few large crystals — visible anisotropic facets",
     12, 0.45, "random"),
    ("Columnar Growth",
     "Seeds along one edge — columnar crystal columns",
     25, 0.50, "edge"),
    ("Dendritic Arms",
     "High anisotropy — branching faceted domains",
     20, 0.70, "random"),
    ("Isotropic Foam",
     "No preferred direction — soap-bubble-like cells",
     35, 0.0, "random"),
    ("Sparse Nucleation",
     "Very few seeds — large irregular territories",
     6, 0.35, "random"),
    ("Bicrystal",
     "Two grains meeting — single grain boundary study",
     2, 0.40, "bicrystal"),
    ("Radial Burst",
     "Seeds from centre — radial competitive growth",
     20, 0.30, "center"),
]


def register(App):
    """Register voronoi mode methods on the App class."""
    App.VORONOI_PRESETS = VORONOI_PRESETS
    App._enter_voronoi_mode = _enter_voronoi_mode
    App._exit_voronoi_mode = _exit_voronoi_mode
    App._voronoi_init = _voronoi_init
    App._voronoi_step = _voronoi_step
    App._voronoi_is_boundary = _voronoi_is_boundary
    App._handle_voronoi_menu_key = _handle_voronoi_menu_key
    App._handle_voronoi_key = _handle_voronoi_key
    App._draw_voronoi_menu = _draw_voronoi_menu
    App._draw_voronoi = _draw_voronoi

