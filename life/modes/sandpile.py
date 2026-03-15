"""Mode: sandpile — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_sandpile_mode(self):
    """Enter Abelian Sandpile mode — show preset menu."""
    self.sandpile_menu = True
    self.sandpile_menu_sel = 0
    self._flash("Abelian Sandpile — select a scenario")



def _exit_sandpile_mode(self):
    """Exit Abelian Sandpile mode."""
    self.sandpile_mode = False
    self.sandpile_menu = False
    self.sandpile_running = False
    self.sandpile_grid = []
    self._flash("Sandpile mode OFF")



def _sandpile_init(self, preset_idx: int):
    """Initialize sandpile simulation with the given preset."""
    (name, _desc, drop_mode, drop_amount,
     initial_pile, spf) = self.SANDPILE_PRESETS[preset_idx]
    self.sandpile_preset_name = name
    self.sandpile_generation = 0
    self.sandpile_running = False
    self.sandpile_drop_mode = drop_mode
    self.sandpile_drop_amount = drop_amount
    self.sandpile_auto_drop = drop_amount > 0
    self.sandpile_steps_per_frame = spf
    self.sandpile_topples = 0
    self.sandpile_total_grains = 0

    max_y, max_x = self.stdscr.getmaxyx()
    self.sandpile_rows = max(10, max_y - 4)
    self.sandpile_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.sandpile_rows, self.sandpile_cols

    self.sandpile_grid = [[0] * cols for _ in range(rows)]
    self.sandpile_cursor_r = rows // 2
    self.sandpile_cursor_c = cols // 2

    cr, cc = rows // 2, cols // 2

    if drop_mode == "center" and initial_pile > 0:
        self.sandpile_grid[cr][cc] = initial_pile
        self.sandpile_total_grains = initial_pile
        self.sandpile_auto_drop = False
    elif drop_mode == "corners":
        pass  # auto-drop handles it
    elif drop_mode == "diamond":
        # Create a diamond seed of 3-grain cells
        radius = min(rows, cols) // 6
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if abs(dr) + abs(dc) <= radius:
                    r, c = cr + dr, cc + dc
                    if 0 <= r < rows and 0 <= c < cols:
                        self.sandpile_grid[r][c] = 3
                        self.sandpile_total_grains += 3
    elif drop_mode == "checkerboard":
        for r in range(rows):
            for c in range(cols):
                if (r + c) % 2 == 0:
                    self.sandpile_grid[r][c] = 3
                    self.sandpile_total_grains += 3
    elif drop_mode == "max_stable":
        for r in range(rows):
            for c in range(cols):
                self.sandpile_grid[r][c] = 3
                self.sandpile_total_grains += 3
        # Perturb center to start avalanche
        self.sandpile_grid[cr][cc] = 4
        self.sandpile_total_grains += 1
    elif drop_mode == "identity":
        # Identity element of the Abelian Sandpile group.
        # Computed as: identity = topple(2·max_stable - topple(2·max_stable))
        # i.e. fill with 6, topple to get E, then identity = topple(6-E each cell).
        from collections import deque
        def _topple_to_stable(g: list[list[int]], rs: int, cs: int) -> None:
            q: deque[tuple[int, int]] = deque()
            for r in range(rs):
                for c in range(cs):
                    if g[r][c] >= 4:
                        q.append((r, c))
            while q:
                r, c = q.popleft()
                while g[r][c] >= 4:
                    spill = g[r][c] // 4
                    g[r][c] %= 4
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rs and 0 <= nc < cs:
                            g[nr][nc] += spill
                            if g[nr][nc] >= 4:
                                q.append((nr, nc))

        tmp = [[6] * cols for _ in range(rows)]
        _topple_to_stable(tmp, rows, cols)
        # Identity = topple(6 - E) for each cell
        for r in range(rows):
            for c in range(cols):
                self.sandpile_grid[r][c] = 6 - tmp[r][c]
        _topple_to_stable(self.sandpile_grid, rows, cols)
        self.sandpile_total_grains = sum(
            self.sandpile_grid[r][c] for r in range(rows) for c in range(cols)
        )
        self.sandpile_auto_drop = False
    elif drop_mode == "random_fill":
        import random as _rng
        for r in range(rows):
            for c in range(cols):
                v = _rng.randint(0, 3)
                self.sandpile_grid[r][c] = v
                self.sandpile_total_grains += v
        # Perturb center to trigger avalanches
        old_val = self.sandpile_grid[cr][cc]
        self.sandpile_grid[cr][cc] = 4
        self.sandpile_total_grains += 4 - old_val

    self.sandpile_menu = False
    self.sandpile_mode = True
    self._flash(f"Sandpile: {name} — Space to start")



def _sandpile_drop(self):
    """Drop grains according to drop mode."""
    rows, cols = self.sandpile_rows, self.sandpile_cols
    grid = self.sandpile_grid
    cr, cc = rows // 2, cols // 2

    if self.sandpile_drop_mode == "center":
        grid[cr][cc] += self.sandpile_drop_amount
        self.sandpile_total_grains += self.sandpile_drop_amount
    elif self.sandpile_drop_mode == "random":
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        grid[r][c] += self.sandpile_drop_amount
        self.sandpile_total_grains += self.sandpile_drop_amount
    elif self.sandpile_drop_mode == "corners":
        margin = min(rows, cols) // 4
        corners = [
            (margin, margin), (margin, cols - 1 - margin),
            (rows - 1 - margin, margin), (rows - 1 - margin, cols - 1 - margin),
        ]
        for r, c in corners:
            grid[r][c] += self.sandpile_drop_amount
            self.sandpile_total_grains += self.sandpile_drop_amount
    elif self.sandpile_drop_mode == "cursor":
        r, c = self.sandpile_cursor_r, self.sandpile_cursor_c
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] += self.sandpile_drop_amount
            self.sandpile_total_grains += self.sandpile_drop_amount



def _sandpile_step(self):
    """Advance one step: optionally drop, then topple until stable."""
    if self.sandpile_auto_drop:
        self._sandpile_drop()

    # Topple all unstable cells (parallel update)
    rows, cols = self.sandpile_rows, self.sandpile_cols
    grid = self.sandpile_grid
    topples = 0

    # Keep toppling until stable
    changed = True
    iterations = 0
    max_iterations = 1000  # prevent infinite loop in huge avalanches
    while changed and iterations < max_iterations:
        changed = False
        iterations += 1
        topple_list: list[tuple[int, int]] = []
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] >= 4:
                    topple_list.append((r, c))

        if not topple_list:
            break

        changed = True
        topples += len(topple_list)

        # Apply all topples simultaneously
        for r, c in topple_list:
            grid[r][c] -= 4
            # Distribute to 4 neighbors (grains fall off edges)
            if r > 0:
                grid[r - 1][c] += 1
            if r < rows - 1:
                grid[r + 1][c] += 1
            if c > 0:
                grid[r][c - 1] += 1
            if c < cols - 1:
                grid[r][c + 1] += 1
            # Grains at edges are lost
            lost = 0
            if r == 0:
                lost += 1
            if r == rows - 1:
                lost += 1
            if c == 0:
                lost += 1
            if c == cols - 1:
                lost += 1
            self.sandpile_total_grains -= lost

    self.sandpile_topples = topples
    self.sandpile_generation += 1



def _handle_sandpile_menu_key(self, key: int) -> bool:
    """Handle input in sandpile preset menu."""
    n = len(self.SANDPILE_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.sandpile_menu_sel = (self.sandpile_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.sandpile_menu_sel = (self.sandpile_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._sandpile_init(self.sandpile_menu_sel)
    elif key in (ord("q"), 27):
        self.sandpile_menu = False
        self._flash("Sandpile cancelled")
    return True



def _handle_sandpile_key(self, key: int) -> bool:
    """Handle input in active sandpile simulation."""
    if key == ord(" "):
        self.sandpile_running = not self.sandpile_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.sandpile_steps_per_frame):
            self._sandpile_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.SANDPILE_PRESETS)
                    if p[0] == self.sandpile_preset_name), 0)
        self._sandpile_init(idx)
        self.sandpile_running = False
    elif key in (ord("R"), ord("m")):
        self.sandpile_mode = False
        self.sandpile_running = False
        self.sandpile_menu = True
        self.sandpile_menu_sel = 0
    elif key == ord("a"):
        # Add a big pile at center
        cr, cc = self.sandpile_rows // 2, self.sandpile_cols // 2
        self.sandpile_grid[cr][cc] += 100
        self.sandpile_total_grains += 100
        self._flash("Added 100 grains at center")
    elif key == ord("A"):
        cr, cc = self.sandpile_rows // 2, self.sandpile_cols // 2
        self.sandpile_grid[cr][cc] += 1000
        self.sandpile_total_grains += 1000
        self._flash("Added 1000 grains at center")
    elif key == ord("d"):
        # Toggle drop mode
        modes = ["center", "random", "cursor"]
        try:
            idx = modes.index(self.sandpile_drop_mode)
        except ValueError:
            idx = 0
        self.sandpile_drop_mode = modes[(idx + 1) % len(modes)]
        self.sandpile_auto_drop = True
        self.sandpile_drop_amount = 1
        self._flash(f"Drop mode: {self.sandpile_drop_mode}")
    elif key == ord("+") or key == ord("="):
        self.sandpile_steps_per_frame = min(50, self.sandpile_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.sandpile_steps_per_frame}")
    elif key == ord("-"):
        self.sandpile_steps_per_frame = max(1, self.sandpile_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.sandpile_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    # Cursor movement for cursor-drop mode
    elif key in (ord("h"), curses.KEY_LEFT):
        self.sandpile_cursor_c = max(0, self.sandpile_cursor_c - 1)
    elif key in (ord("l"), curses.KEY_RIGHT):
        self.sandpile_cursor_c = min(self.sandpile_cols - 1, self.sandpile_cursor_c + 1)
    elif key in (ord("k"), curses.KEY_UP):
        self.sandpile_cursor_r = max(0, self.sandpile_cursor_r - 1)
    elif key in (ord("j"), curses.KEY_DOWN):
        self.sandpile_cursor_r = min(self.sandpile_rows - 1, self.sandpile_cursor_r + 1)
    elif key == ord("e"):
        # Drop grain at cursor
        r, c = self.sandpile_cursor_r, self.sandpile_cursor_c
        self.sandpile_grid[r][c] += 1
        self.sandpile_total_grains += 1
    elif key in (ord("q"), 27):
        self._exit_sandpile_mode()
    else:
        return True
    return True



def _draw_sandpile_menu(self, max_y: int, max_x: int):
    """Draw the sandpile preset selection menu."""
    self.stdscr.erase()
    title = "── Abelian Sandpile ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.SANDPILE_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<20s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.sandpile_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_sandpile(self, max_y: int, max_x: int):
    """Draw the active sandpile simulation."""
    self.stdscr.erase()
    grid = self.sandpile_grid
    rows, cols = self.sandpile_rows, self.sandpile_cols
    state = "▶ RUNNING" if self.sandpile_running else "⏸ PAUSED"
    gen = self.sandpile_generation

    # Find max grain count for stats
    max_grains = 0
    for row in grid:
        for v in row:
            if v > max_grains:
                max_grains = v

    # Title bar
    title = (f" Sandpile: {self.sandpile_preset_name}  |  step {gen}"
             f"  |  grains={self.sandpile_total_grains}"
             f"  |  topples={self.sandpile_topples}"
             f"  |  max={max_grains}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 3
    view_cols = (max_x - 1) // 2

    # Draw grid
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            sx = c * 2
            sy = 1 + r

            if val == 0:
                continue  # empty
            elif val >= 4:
                ch, cp = self.SANDPILE_OVERFLOW_CHAR
                attr = curses.color_pair(cp) | curses.A_BOLD
            elif val in self.SANDPILE_CHARS:
                ch, cp = self.SANDPILE_CHARS[val]
                if ch == " ":
                    continue
                attr = curses.color_pair(cp)
            else:
                ch, cp = "██", 3
                attr = curses.color_pair(cp)

            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Draw cursor marker in cursor-drop mode
    if self.sandpile_drop_mode == "cursor":
        cy = 1 + self.sandpile_cursor_r
        cx = self.sandpile_cursor_c * 2
        if 0 < cy < max_y - 2 and 0 <= cx < max_x - 2:
            try:
                self.stdscr.addstr(cy, cx, "╬╬", curses.color_pair(7) | curses.A_BOLD)
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Step {gen}  |  drop={self.sandpile_drop_mode}"
                f"  |  grains={self.sandpile_total_grains}"
                f"  |  steps/f={self.sandpile_steps_per_frame}")
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
            hint = " [Space]=play [n]=step [d]=drop-mode [a/A]=+100/+1000 [e]=drop@cursor [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ══════════════════════════════════════════════════════════════════════
#  Forest Fire — Mode O
# ══════════════════════════════════════════════════════════════════════

FIRE_PRESETS = [
    # (name, description, density, p_grow, p_lightning, ash_decay)
    ("Classic", "Balanced growth and lightning", 0.55, 0.03, 0.0005, 0.08),
    ("Dense Forest", "Thick canopy, rare lightning", 0.85, 0.05, 0.0002, 0.06),
    ("Dry Season", "Sparse trees, frequent lightning", 0.3, 0.01, 0.003, 0.12),
    ("Regrowth", "Fast regrowth after fire", 0.4, 0.08, 0.001, 0.15),
    ("Tinderbox", "High density, high lightning", 0.7, 0.02, 0.005, 0.10),
    ("Savanna", "Very sparse, steady fires", 0.15, 0.02, 0.002, 0.20),
    ("Rainforest", "Very dense, very rare fire", 0.95, 0.06, 0.0001, 0.04),
    ("Firestorm", "Maximum chaos", 0.5, 0.04, 0.01, 0.05),
    ("Critical Density", "Self-organized criticality demo", 0.60, 0.02, 0.0003, 0.10),
    ("Slow Burn", "Long-lived embers, slow spread", 0.65, 0.03, 0.0004, 0.03),
]




def register(App):
    """Register sandpile mode methods on the App class."""
    App._enter_sandpile_mode = _enter_sandpile_mode
    App._exit_sandpile_mode = _exit_sandpile_mode
    App._sandpile_init = _sandpile_init
    App._sandpile_drop = _sandpile_drop
    App._sandpile_step = _sandpile_step
    App._handle_sandpile_menu_key = _handle_sandpile_menu_key
    App._handle_sandpile_key = _handle_sandpile_key
    App._draw_sandpile_menu = _draw_sandpile_menu
    App._draw_sandpile = _draw_sandpile

