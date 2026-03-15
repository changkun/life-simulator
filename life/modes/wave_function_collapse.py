"""Mode: wfc — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_wfc_mode(self):
    """Enter WFC mode — show preset menu."""
    self.wfc_menu = True
    self.wfc_menu_sel = 0
    self._flash("Wave Function Collapse — select a configuration")



def _exit_wfc_mode(self):
    """Exit WFC mode."""
    self.wfc_mode = False
    self.wfc_menu = False
    self.wfc_running = False
    self.wfc_grid = []
    self.wfc_collapsed = []
    self._flash("WFC mode OFF")



def _wfc_init(self, preset_idx: int):
    """Initialize WFC simulation with the given preset."""
    import random as _rng
    name, _desc, num_tiles, _tile_names, adj_rules = self.WFC_PRESETS[preset_idx]

    self.wfc_preset_name = name
    self.wfc_num_tiles = num_tiles
    self.wfc_preset_idx = preset_idx

    # Make adjacency bidirectional/symmetric
    opposites = {"N": "S", "S": "N", "E": "W", "W": "E"}
    self.wfc_adjacency = {}
    for t in range(num_tiles):
        self.wfc_adjacency[t] = {}
        for d in ("N", "S", "E", "W"):
            self.wfc_adjacency[t][d] = set(adj_rules.get(t, {}).get(d, set()))

    # Enforce symmetry: if tile A allows tile B to its North,
    # then tile B must allow tile A to its South
    for t in range(num_tiles):
        for d in ("N", "S", "E", "W"):
            od = opposites[d]
            for neighbor in list(self.wfc_adjacency[t][d]):
                self.wfc_adjacency[neighbor][od].add(t)

    max_y, max_x = self.stdscr.getmaxyx()
    self.wfc_rows = max(5, max_y - 3)
    self.wfc_cols = max(5, (max_x - 1) // 2)

    rows, cols = self.wfc_rows, self.wfc_cols
    all_tiles = set(range(num_tiles))

    # Initialize every cell with all possibilities
    self.wfc_grid = [[set(all_tiles) for _ in range(cols)] for _ in range(rows)]
    self.wfc_collapsed = [[-1] * cols for _ in range(rows)]

    self.wfc_generation = 0
    self.wfc_contradiction = False
    self.wfc_complete = False
    self.wfc_running = False

    self.wfc_menu = False
    self.wfc_mode = True
    self._flash(f"WFC: {name} — Space to auto-run, n to step")



def _wfc_step(self):
    """Perform one WFC collapse step: pick lowest-entropy cell, collapse, propagate."""
    import random as _rng

    if self.wfc_complete or self.wfc_contradiction:
        return

    rows, cols = self.wfc_rows, self.wfc_cols
    grid = self.wfc_grid
    collapsed = self.wfc_collapsed

    # Find the uncollapsed cell with lowest entropy (smallest number of possibilities)
    min_entropy = self.wfc_num_tiles + 1
    candidates = []
    for r in range(rows):
        for c in range(cols):
            if collapsed[r][c] == -1:
                e = len(grid[r][c])
                if e == 0:
                    # Contradiction — no valid tiles for this cell
                    self.wfc_contradiction = True
                    self._flash("Contradiction! No valid tile. Press r to restart.")
                    return
                if e < min_entropy:
                    min_entropy = e
                    candidates = [(r, c)]
                elif e == min_entropy:
                    candidates.append((r, c))

    if not candidates:
        # All cells collapsed
        self.wfc_complete = True
        self.wfc_running = False
        self._flash("WFC complete! All cells collapsed.")
        return

    # Pick a random cell among lowest-entropy candidates
    cr, cc = _rng.choice(candidates)

    # Collapse: pick a random tile from possibilities
    tile = _rng.choice(list(grid[cr][cc]))
    grid[cr][cc] = {tile}
    collapsed[cr][cc] = tile

    # Propagate constraints
    self._wfc_propagate(cr, cc)

    self.wfc_generation += 1



def _wfc_propagate(self, start_r: int, start_c: int):
    """Propagate constraints from a collapsed cell using BFS."""
    rows, cols = self.wfc_rows, self.wfc_cols
    grid = self.wfc_grid
    collapsed = self.wfc_collapsed
    adjacency = self.wfc_adjacency

    # Direction offsets: (dr, dc, direction_name)
    dirs = [(-1, 0, "N"), (1, 0, "S"), (0, 1, "E"), (0, -1, "W")]
    opposites = {"N": "S", "S": "N", "E": "W", "W": "E"}

    stack = [(start_r, start_c)]

    while stack:
        r, c = stack.pop()
        current_tiles = grid[r][c]

        for dr, dc, d in dirs:
            nr, nc = r + dr, c + dc
            if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                continue
            if collapsed[nr][nc] != -1:
                continue  # already collapsed, skip

            # Compute what tiles are allowed in neighbor based on current cell
            allowed = set()
            for t in current_tiles:
                allowed |= adjacency[t][d]

            # Intersect with neighbor's current possibilities
            neighbor_before = len(grid[nr][nc])
            grid[nr][nc] &= allowed

            if len(grid[nr][nc]) == 0:
                self.wfc_contradiction = True
                return

            # If we reduced possibilities, propagate further
            if len(grid[nr][nc]) < neighbor_before:
                # Auto-collapse if only one option left
                if len(grid[nr][nc]) == 1:
                    collapsed[nr][nc] = next(iter(grid[nr][nc]))
                stack.append((nr, nc))



def _handle_wfc_menu_key(self, key: int) -> bool:
    """Handle input in WFC preset menu."""
    n = len(self.WFC_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.wfc_menu_sel = (self.wfc_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.wfc_menu_sel = (self.wfc_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._wfc_init(self.wfc_menu_sel)
    elif key in (ord("q"), 27):
        self.wfc_menu = False
        self._flash("WFC cancelled")
    return True



def _handle_wfc_key(self, key: int) -> bool:
    """Handle input in active WFC simulation."""
    if key == ord(" "):
        if self.wfc_complete or self.wfc_contradiction:
            return True
        self.wfc_running = not self.wfc_running
        self._flash("Running" if self.wfc_running else "Paused")
    elif key in (ord("n"), ord(".")):
        self._wfc_step()
    elif key == ord("r"):
        # Restart with same preset
        self._wfc_init(self.wfc_preset_idx)
    elif key == ord("s") or key == ord("S"):
        # Adjust steps per frame
        if key == ord("s"):
            self.wfc_steps_per_frame = min(50, self.wfc_steps_per_frame + 1)
        else:
            self.wfc_steps_per_frame = max(1, self.wfc_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.wfc_steps_per_frame}")
    elif key in (ord("q"), 27):
        self._exit_wfc_mode()
    else:
        return True
    return True



def _draw_wfc_menu(self, max_y: int, max_x: int):
    """Draw the WFC preset selection menu."""
    self.stdscr.erase()
    title = "── Wave Function Collapse ── Select Configuration ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, num_tiles, tile_names, _adj) in enumerate(self.WFC_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        tiles_str = ", ".join(tile_names[:4])
        if len(tile_names) > 4:
            tiles_str += ", ..."
        line = f"  {name:<14s}  {desc}  [{tiles_str}]"
        attr = curses.color_pair(6)
        if i == self.wfc_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_wfc(self, max_y: int, max_x: int):
    """Draw the active WFC simulation."""
    self.stdscr.erase()
    rows, cols = self.wfc_rows, self.wfc_cols
    collapsed = self.wfc_collapsed
    grid = self.wfc_grid
    preset_tiles = self.WFC_PRESET_TILES[self.wfc_preset_idx]

    # Count collapsed cells
    num_collapsed = sum(1 for r in range(rows) for c in range(cols) if collapsed[r][c] != -1)
    total = rows * cols
    pct = num_collapsed * 100 // total if total > 0 else 0

    # Title bar
    if self.wfc_contradiction:
        state = "✗ CONTRADICTION"
    elif self.wfc_complete:
        state = "✓ COMPLETE"
    elif self.wfc_running:
        state = "▶ RUNNING"
    else:
        state = "⏸ PAUSED"

    title = (f" WFC: {self.wfc_preset_name}  |  step {self.wfc_generation}"
             f"  |  {pct}% collapsed  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    for r in range(view_rows):
        for c in range(view_cols):
            tile_idx = collapsed[r][c]
            if tile_idx != -1:
                # Collapsed cell — render the tile
                display_idx = preset_tiles[tile_idx] if tile_idx < len(preset_tiles) else 0
                if display_idx < len(self.WFC_TILE_CHARS):
                    ch, color = self.WFC_TILE_CHARS[display_idx]
                else:
                    ch, color = "??", 1
                attr = curses.color_pair(color)
                try:
                    self.stdscr.addstr(1 + r, c * 2, ch, attr)
                except curses.error:
                    pass
            else:
                # Uncollapsed — show entropy as brightness
                entropy = len(grid[r][c])
                if entropy <= 1:
                    ch = "!!"
                    attr = curses.color_pair(1) | curses.A_BOLD
                elif entropy <= 2:
                    ch = "░░"
                    attr = curses.color_pair(5) | curses.A_BOLD
                elif entropy <= 3:
                    ch = "▒▒"
                    attr = curses.color_pair(5)
                else:
                    ch = "▓▓"
                    attr = curses.color_pair(5) | curses.A_DIM
                try:
                    self.stdscr.addstr(1 + r, c * 2, ch, attr)
                except curses.error:
                    pass

    # Bottom hint bar
    hint = " [Space]=run  [n]=step  [r]=restart  [s/S]=speed  [q]=quit"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════
#  Lightning / Dielectric Breakdown — Mode ^
# ══════════════════════════════════════════════════════════════════════

# Each preset: (name, description, eta, source)
# eta = field exponent controlling branching (lower = more branching)
# source = where discharge originates: "top", "center", "point"
LIGHTNING_PRESETS = [
    ("Classic Lightning",
     "Top-to-bottom bolt — natural branching",
     2.0, "top"),
    ("Sparse Bolt",
     "High eta — fewer branches, straighter path",
     4.0, "top"),
    ("Dense Branching",
     "Low eta — heavily branched discharge",
     1.0, "top"),
    ("Lichtenberg Figure",
     "Center-outward — radial fractal pattern",
     1.5, "center"),
    ("Point Discharge",
     "Single point source — star-like pattern",
     2.0, "point"),
    ("Feathery Discharge",
     "Very low eta — maximum branching",
     0.5, "center"),
    ("Minimal Tree",
     "Moderate branching from top edge",
     3.0, "top"),
    ("Ball Lightning",
     "Center discharge — sparse and radial",
     3.5, "center"),
]




def register(App):
    """Register wfc mode methods on the App class."""
    App._enter_wfc_mode = _enter_wfc_mode
    App._exit_wfc_mode = _exit_wfc_mode
    App._wfc_init = _wfc_init
    App._wfc_step = _wfc_step
    App._wfc_propagate = _wfc_propagate
    App._handle_wfc_menu_key = _handle_wfc_menu_key
    App._handle_wfc_key = _handle_wfc_key
    App._draw_wfc_menu = _draw_wfc_menu
    App._draw_wfc = _draw_wfc

