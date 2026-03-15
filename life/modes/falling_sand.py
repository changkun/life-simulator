"""Mode: sand — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS, SPEED_LABELS
from life.grid import Grid

def _sand_build_preset(self, name: str) -> dict[tuple[int, int], tuple[int, int]]:
    """Build a preset scene for falling sand."""
    grid: dict[tuple[int, int], tuple[int, int]] = {}
    mid_r = self.sand_rows // 2
    mid_c = self.sand_cols // 2

    if name == "hourglass":
        # Stone walls forming an hourglass shape
        for c in range(mid_c - 12, mid_c + 13):
            grid[(2, c)] = (self.SAND_STONE, 0)
            grid[(self.sand_rows - 3, c)] = (self.SAND_STONE, 0)
        for r in range(2, self.sand_rows - 2):
            grid[(r, mid_c - 12)] = (self.SAND_STONE, 0)
            grid[(r, mid_c + 12)] = (self.SAND_STONE, 0)
        # Narrow gap in the middle
        gap_r = mid_r
        for c in range(mid_c - 12, mid_c - 1):
            grid[(gap_r, c)] = (self.SAND_STONE, 0)
        for c in range(mid_c + 2, mid_c + 13):
            grid[(gap_r, c)] = (self.SAND_STONE, 0)
        # Fill top half with sand
        for r in range(3, gap_r):
            for c in range(mid_c - 11, mid_c + 12):
                grid[(r, c)] = (self.SAND_SAND, 0)

    elif name == "rainfall":
        # Stone platforms
        for c in range(mid_c - 10, mid_c - 2):
            grid[(mid_r, c)] = (self.SAND_STONE, 0)
        for c in range(mid_c + 3, mid_c + 11):
            grid[(mid_r, c)] = (self.SAND_STONE, 0)
        for c in range(mid_c - 6, mid_c + 7):
            grid[(mid_r + 8, c)] = (self.SAND_STONE, 0)
        # Water at top
        for r in range(2, 5):
            for c in range(mid_c - 8, mid_c + 9):
                grid[(r, c)] = (self.SAND_WATER, 0)

    elif name == "bonfire":
        # Ground
        for c in range(mid_c - 15, mid_c + 16):
            grid[(self.sand_rows - 4, c)] = (self.SAND_STONE, 0)
        # Plant forest
        for r in range(mid_r, self.sand_rows - 4):
            for c in range(mid_c - 12, mid_c + 13):
                if random.random() < 0.6:
                    grid[(r, c)] = (self.SAND_PLANT, 0)
        # Fire at bottom center
        for r in range(self.sand_rows - 7, self.sand_rows - 4):
            for c in range(mid_c - 2, mid_c + 3):
                grid[(r, c)] = (self.SAND_FIRE, 0)

    elif name == "lavalamp":
        # Walls
        for r in range(2, self.sand_rows - 2):
            grid[(r, mid_c - 8)] = (self.SAND_STONE, 0)
            grid[(r, mid_c + 8)] = (self.SAND_STONE, 0)
        for c in range(mid_c - 8, mid_c + 9):
            grid[(self.sand_rows - 3, c)] = (self.SAND_STONE, 0)
        # Alternating layers of sand and water
        for r in range(self.sand_rows - 10, self.sand_rows - 3):
            for c in range(mid_c - 7, mid_c + 8):
                if (r // 2) % 2 == 0:
                    grid[(r, c)] = (self.SAND_SAND, 0)
                else:
                    grid[(r, c)] = (self.SAND_WATER, 0)

    elif name == "forest":
        # Ground
        for c in range(mid_c - 15, mid_c + 16):
            grid[(self.sand_rows - 4, c)] = (self.SAND_STONE, 0)
        # Dense plant growth
        for r in range(mid_r, self.sand_rows - 4):
            for c in range(mid_c - 12, mid_c + 13):
                if random.random() < 0.6:
                    grid[(r, c)] = (self.SAND_PLANT, 0)
        # Fire ignition points
        for r in range(self.sand_rows - 7, self.sand_rows - 4):
            for c in range(mid_c - 2, mid_c + 3):
                grid[(r, c)] = (self.SAND_FIRE, 0)

    elif name == "oilrig":
        # Container walls
        for r in range(2, self.sand_rows - 2):
            grid[(r, mid_c - 12)] = (self.SAND_STONE, 0)
            grid[(r, mid_c + 12)] = (self.SAND_STONE, 0)
        for c in range(mid_c - 12, mid_c + 13):
            grid[(self.sand_rows - 3, c)] = (self.SAND_STONE, 0)
        # Water layer at bottom
        for r in range(self.sand_rows - 8, self.sand_rows - 3):
            for c in range(mid_c - 11, mid_c + 12):
                grid[(r, c)] = (self.SAND_WATER, 0)
        # Oil layer floating on water
        for r in range(self.sand_rows - 12, self.sand_rows - 8):
            for c in range(mid_c - 11, mid_c + 12):
                grid[(r, c)] = (self.SAND_OIL, 0)
        # Fire source at one end
        for r in range(self.sand_rows - 13, self.sand_rows - 11):
            grid[(r, mid_c - 10)] = (self.SAND_FIRE, 0)

    elif name == "waterfall":
        # Stone cliff
        for r in range(mid_r - 5, mid_r + 8):
            for dc in range(3):
                grid[(r, mid_c - 3 + dc)] = (self.SAND_STONE, 0)
        # Ledges
        for c in range(mid_c, mid_c + 10):
            grid[(mid_r - 5, c)] = (self.SAND_STONE, 0)
        for c in range(mid_c - 10, mid_c - 3):
            grid[(mid_r + 1, c)] = (self.SAND_STONE, 0)
        # Pool bottom
        for c in range(mid_c - 12, mid_c + 13):
            grid[(mid_r + 8, c)] = (self.SAND_STONE, 0)
        # Water source at top
        for r in range(mid_r - 8, mid_r - 5):
            for c in range(mid_c, mid_c + 5):
                grid[(r, c)] = (self.SAND_WATER, 0)

    return grid



def _sand_init(self, preset: str | None = None):
    """Initialize the falling sand grid."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.sand_rows = max_y - 3
    self.sand_cols = (max_x - 1) // 2
    if self.sand_rows < 10:
        self.sand_rows = 10
    if self.sand_cols < 10:
        self.sand_cols = 10
    self.sand_grid = {}
    self.sand_generation = 0
    self.sand_cursor_r = self.sand_rows // 2
    self.sand_cursor_c = self.sand_cols // 2
    if preset and preset != "empty":
        self.sand_grid = self._sand_build_preset(preset)



def _sand_step(self):
    """Advance the falling-sand simulation by one tick."""
    new_grid: dict[tuple[int, int], tuple[int, int]] = {}
    # Copy all static elements first (stone)
    for (r, c), (elem, age) in self.sand_grid.items():
        if elem == self.SAND_STONE:
            new_grid[(r, c)] = (elem, age)

    # Track which cells are occupied in new_grid as we go
    # Process from bottom to top so falling works correctly
    moved: set[tuple[int, int]] = set()

    # Process rows bottom-to-top for gravity elements
    for r in range(self.sand_rows - 1, -1, -1):
        # Randomize left-right processing to avoid bias
        cols = list(range(self.sand_cols))
        random.shuffle(cols)
        for c in cols:
            if (r, c) in moved:
                continue
            cell = self.sand_grid.get((r, c))
            if cell is None:
                continue
            elem, age = cell

            if elem == self.SAND_STONE:
                continue  # already copied

            if elem == self.SAND_SAND:
                # Sand: fall down, try diagonals, sink through water
                nr = r + 1
                if nr < self.sand_rows:
                    below = new_grid.get((nr, c))
                    below_orig = self.sand_grid.get((nr, c))
                    if below is None and (below_orig is None or (nr, c) in moved):
                        new_grid[(nr, c)] = (elem, age + 1)
                        moved.add((nr, c))
                        continue
                    # Swap with water/oil below (sand sinks through liquids)
                    if below is not None and below[0] in (self.SAND_WATER, self.SAND_OIL):
                        new_grid[(nr, c)] = (elem, age + 1)
                        new_grid[(r, c)] = (below[0], below[1])
                        moved.add((nr, c))
                        moved.add((r, c))
                        continue
                    # Try diagonal
                    dirs = [-1, 1]
                    random.shuffle(dirs)
                    fell = False
                    for dc in dirs:
                        nc = c + dc
                        if 0 <= nc < self.sand_cols and nr < self.sand_rows:
                            diag = new_grid.get((nr, nc))
                            diag_orig = self.sand_grid.get((nr, nc))
                            if diag is None and (diag_orig is None or (nr, nc) in moved):
                                new_grid[(nr, nc)] = (elem, age + 1)
                                moved.add((nr, nc))
                                fell = True
                                break
                    if fell:
                        continue
                # Stay in place
                new_grid[(r, c)] = (elem, age)
                moved.add((r, c))

            elif elem == self.SAND_WATER:
                # Water: fall down, sink below oil, then flow sideways
                nr = r + 1
                if nr < self.sand_rows:
                    below = new_grid.get((nr, c))
                    below_orig = self.sand_grid.get((nr, c))
                    if below is None and (below_orig is None or (nr, c) in moved):
                        new_grid[(nr, c)] = (elem, age + 1)
                        moved.add((nr, c))
                        continue
                    # Water sinks below oil
                    if below is not None and below[0] == self.SAND_OIL:
                        new_grid[(nr, c)] = (elem, age + 1)
                        new_grid[(r, c)] = (self.SAND_OIL, below[1])
                        moved.add((nr, c))
                        moved.add((r, c))
                        continue
                    # Try diagonal down
                    dirs = [-1, 1]
                    random.shuffle(dirs)
                    fell = False
                    for dc in dirs:
                        nc = c + dc
                        if 0 <= nc < self.sand_cols:
                            diag = new_grid.get((nr, nc))
                            diag_orig = self.sand_grid.get((nr, nc))
                            if diag is None and (diag_orig is None or (nr, nc) in moved):
                                new_grid[(nr, nc)] = (elem, age + 1)
                                moved.add((nr, nc))
                                fell = True
                                break
                    if fell:
                        continue
                # Try flowing sideways
                dirs = [-1, 1]
                random.shuffle(dirs)
                flowed = False
                for dc in dirs:
                    nc = c + dc
                    if 0 <= nc < self.sand_cols:
                        side = new_grid.get((r, nc))
                        side_orig = self.sand_grid.get((r, nc))
                        if side is None and (side_orig is None or (r, nc) in moved):
                            new_grid[(r, nc)] = (elem, age + 1)
                            moved.add((r, nc))
                            flowed = True
                            break
                if flowed:
                    continue
                # Stay in place
                new_grid[(r, c)] = (elem, age)
                moved.add((r, c))

            elif elem == self.SAND_FIRE:
                # Fire: rises upward, has limited lifetime, random flicker
                if age > 12 + random.randint(0, 8):
                    # Fire dies out — chance to produce steam
                    if random.random() < 0.2:
                        new_grid[(r, c)] = (self.SAND_STEAM, 0)
                        moved.add((r, c))
                    continue
                # Ignite adjacent plants and oil; evaporate water
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    ar, ac = r + dr, c + dc
                    if 0 <= ar < self.sand_rows and 0 <= ac < self.sand_cols:
                        adj = self.sand_grid.get((ar, ac))
                        if adj and adj[0] == self.SAND_PLANT:
                            if random.random() < 0.4:
                                new_grid[(ar, ac)] = (self.SAND_FIRE, 0)
                                moved.add((ar, ac))
                        elif adj and adj[0] == self.SAND_OIL:
                            if random.random() < 0.5:
                                new_grid[(ar, ac)] = (self.SAND_FIRE, 0)
                                moved.add((ar, ac))
                        elif adj and adj[0] == self.SAND_WATER:
                            if random.random() < 0.08:
                                new_grid[(ar, ac)] = (self.SAND_STEAM, 0)
                                moved.add((ar, ac))
                # Try to rise
                nr = r - 1
                if nr >= 0 and random.random() < 0.7:
                    dc = random.choice([-1, 0, 0, 1])
                    nc = c + dc
                    if 0 <= nc < self.sand_cols:
                        above = new_grid.get((nr, nc))
                        above_orig = self.sand_grid.get((nr, nc))
                        if above is None and (above_orig is None or (nr, nc) in moved):
                            new_grid[(nr, nc)] = (elem, age + 1)
                            moved.add((nr, nc))
                            continue
                # Stay or flicker
                new_grid[(r, c)] = (elem, age + 1)
                moved.add((r, c))

            elif elem == self.SAND_PLANT:
                # Plant: grows when adjacent to water, burns near fire
                # Check for fire neighbors (already handled by fire spreading)
                # Grow into empty adjacent cells if water is nearby
                has_water = False
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ar, ac = r + dr, c + dc
                    if 0 <= ar < self.sand_rows and 0 <= ac < self.sand_cols:
                        adj = self.sand_grid.get((ar, ac))
                        if adj and adj[0] == self.SAND_WATER:
                            has_water = True
                            break
                if has_water and random.random() < 0.05:
                    # Try to grow in a random direction (prefer upward)
                    grow_dirs = [(-1, 0), (-1, -1), (-1, 1), (0, -1), (0, 1)]
                    random.shuffle(grow_dirs)
                    for dr, dc in grow_dirs:
                        gr, gc = r + dr, c + dc
                        if 0 <= gr < self.sand_rows and 0 <= gc < self.sand_cols:
                            if (gr, gc) not in new_grid and (gr, gc) not in self.sand_grid:
                                new_grid[(gr, gc)] = (self.SAND_PLANT, 0)
                                moved.add((gr, gc))
                                break
                # Stay in place
                if (r, c) not in new_grid:
                    new_grid[(r, c)] = (elem, age + 1)
                    moved.add((r, c))

            elif elem == self.SAND_OIL:
                # Oil: liquid that floats on water, flammable
                nr = r + 1
                if nr < self.sand_rows:
                    below = new_grid.get((nr, c))
                    below_orig = self.sand_grid.get((nr, c))
                    if below is None and (below_orig is None or (nr, c) in moved):
                        new_grid[(nr, c)] = (elem, age + 1)
                        moved.add((nr, c))
                        continue
                    # Oil floats above water — swap if water is below
                    # (water sinks, oil rises handled by water not displacing oil upward)
                    # Try diagonal down
                    dirs = [-1, 1]
                    random.shuffle(dirs)
                    fell = False
                    for dc in dirs:
                        nc = c + dc
                        if 0 <= nc < self.sand_cols:
                            diag = new_grid.get((nr, nc))
                            diag_orig = self.sand_grid.get((nr, nc))
                            if diag is None and (diag_orig is None or (nr, nc) in moved):
                                new_grid[(nr, nc)] = (elem, age + 1)
                                moved.add((nr, nc))
                                fell = True
                                break
                    if fell:
                        continue
                # Try flowing sideways
                dirs = [-1, 1]
                random.shuffle(dirs)
                flowed = False
                for dc in dirs:
                    nc = c + dc
                    if 0 <= nc < self.sand_cols:
                        side = new_grid.get((r, nc))
                        side_orig = self.sand_grid.get((r, nc))
                        if side is None and (side_orig is None or (r, nc) in moved):
                            new_grid[(r, nc)] = (elem, age + 1)
                            moved.add((r, nc))
                            flowed = True
                            break
                if flowed:
                    continue
                # Stay in place
                new_grid[(r, c)] = (elem, age)
                moved.add((r, c))

            elif elem == self.SAND_STEAM:
                # Steam: rises upward, drifts, eventually condenses back to water
                if age > 15 + random.randint(0, 10):
                    # Condense back to water or vanish
                    if random.random() < 0.4:
                        new_grid[(r, c)] = (self.SAND_WATER, 0)
                        moved.add((r, c))
                    continue
                # Try to rise
                nr = r - 1
                if nr >= 0:
                    dc = random.choice([-1, 0, 0, 1])
                    nc = c + dc
                    if 0 <= nc < self.sand_cols:
                        above = new_grid.get((nr, nc))
                        above_orig = self.sand_grid.get((nr, nc))
                        if above is None and (above_orig is None or (nr, nc) in moved):
                            new_grid[(nr, nc)] = (elem, age + 1)
                            moved.add((nr, nc))
                            continue
                # Stay or drift sideways
                dc = random.choice([-1, 1])
                nc = c + dc
                if 0 <= nc < self.sand_cols:
                    side = new_grid.get((r, nc))
                    side_orig = self.sand_grid.get((r, nc))
                    if side is None and (side_orig is None or (r, nc) in moved):
                        new_grid[(r, nc)] = (elem, age + 1)
                        moved.add((r, nc))
                        continue
                new_grid[(r, c)] = (elem, age + 1)
                moved.add((r, c))

    self.sand_grid = new_grid
    self.sand_generation += 1



def _enter_sand_mode(self):
    """Enter falling-sand mode — show preset menu."""
    self.sand_menu = True
    self.sand_menu_sel = 0
    self._flash("Falling Sand — select a scene")



def _exit_sand_mode(self):
    """Exit falling-sand mode."""
    self.sand_mode = False
    self.sand_menu = False
    self.sand_running = False
    self.sand_grid = {}
    self._flash("Falling Sand mode OFF")



def _handle_sand_menu_key(self, key: int) -> bool:
    """Handle keys in the falling-sand preset menu."""
    if key == -1:
        return True
    n = len(self.SAND_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.sand_menu_sel = (self.sand_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.sand_menu_sel = (self.sand_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.sand_menu = False
        self._flash("Falling Sand cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        name, desc, preset_id = self.SAND_PRESETS[self.sand_menu_sel]
        self.sand_menu = False
        self.sand_mode = True
        self.sand_running = False
        self._sand_init(preset_id)
        self._flash(f"Falling Sand [{name}] — Space=play, arrows=move, 1-7=brush, Enter=place, q=exit")
        return True
    return True



def _handle_sand_key(self, key: int) -> bool:
    """Handle keys while in falling-sand mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_sand_mode()
        return True
    if key == ord(" "):
        self.sand_running = not self.sand_running
        self._flash("Playing" if self.sand_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.sand_running = False
        self._sand_step()
        return True
    if key == ord("r"):
        self._sand_init()
        self._flash("Grid cleared")
        return True
    if key == ord("R") or key == ord("m"):
        self.sand_mode = False
        self.sand_running = False
        self.sand_menu = True
        self.sand_menu_sel = 0
        return True
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
    # Brush selection
    if key == ord("1"):
        self.sand_brush = self.SAND_SAND
        self._flash("Brush: sand")
        return True
    if key == ord("2"):
        self.sand_brush = self.SAND_WATER
        self._flash("Brush: water")
        return True
    if key == ord("3"):
        self.sand_brush = self.SAND_FIRE
        self._flash("Brush: fire")
        return True
    if key == ord("4"):
        self.sand_brush = self.SAND_STONE
        self._flash("Brush: stone")
        return True
    if key == ord("5"):
        self.sand_brush = self.SAND_PLANT
        self._flash("Brush: plant")
        return True
    if key == ord("6"):
        self.sand_brush = self.SAND_OIL
        self._flash("Brush: oil")
        return True
    if key == ord("7"):
        self.sand_brush = self.SAND_STEAM
        self._flash("Brush: steam")
        return True
    if key == ord("0"):
        self.sand_brush = self.SAND_EMPTY
        self._flash("Brush: eraser")
        return True
    # Brush size
    if key == ord("+") or key == ord("="):
        self.sand_brush_size = min(self.sand_brush_size + 1, 5)
        self._flash(f"Brush size: {self.sand_brush_size}")
        return True
    if key == ord("-"):
        self.sand_brush_size = max(self.sand_brush_size - 1, 1)
        self._flash(f"Brush size: {self.sand_brush_size}")
        return True
    # Cursor movement
    if key == curses.KEY_UP or key == ord("k"):
        self.sand_cursor_r = max(0, self.sand_cursor_r - 1)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.sand_cursor_r = min(self.sand_rows - 1, self.sand_cursor_r + 1)
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        self.sand_cursor_c = max(0, self.sand_cursor_c - 1)
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        self.sand_cursor_c = min(self.sand_cols - 1, self.sand_cursor_c + 1)
        return True
    # Place element at cursor
    if key == 10 or key == 13 or key == curses.KEY_ENTER:
        self._sand_paint()
        return True
    # Draw mode: d to paint while moving
    if key == ord("d"):
        self._sand_paint()
        self._flash("Painted — use arrows + Enter to draw more")
        return True
    return True



def _sand_paint(self):
    """Paint the current brush at cursor position with brush size."""
    sz = self.sand_brush_size
    for dr in range(-sz + 1, sz):
        for dc in range(-sz + 1, sz):
            pr, pc = self.sand_cursor_r + dr, self.sand_cursor_c + dc
            if 0 <= pr < self.sand_rows and 0 <= pc < self.sand_cols:
                if self.sand_brush == self.SAND_EMPTY:
                    self.sand_grid.pop((pr, pc), None)
                else:
                    self.sand_grid[(pr, pc)] = (self.sand_brush, 0)



def _draw_sand_menu(self, max_y: int, max_x: int):
    """Draw the falling-sand preset selection menu."""
    title = "── Falling Sand ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    subtitle = "Gravity-based particle simulation with interacting elements"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.SAND_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.SAND_PRESETS):
        y = 5 + i
        if y >= max_y - 10:
            break
        line = f"  {name:<14s} {desc}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.sand_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    info_y = 5 + min(n, max_y - 15) + 1
    info_lines = [
        "Elements: sand (falls, piles), water (flows), fire (rises, burns),",
        "          stone (static walls), plant (grows near water, burns),",
        "          oil (floats on water, highly flammable), steam (rises, condenses)",
        "",
        "Sand sinks through water/oil. Fire ignites plants and oil.",
        "Water evaporates to steam near fire. Oil floats above water.",
    ]
    for i, info in enumerate(info_lines):
        y = info_y + i
        if y >= max_y - 2:
            break
        try:
            self.stdscr.addstr(y, 2, info[:max_x - 3], curses.color_pair(1))
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate [Enter]=select [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_sand(self, max_y: int, max_x: int):
    """Draw the falling-sand simulation."""
    # Count elements
    counts: dict[int, int] = {}
    for (_, _), (elem, _) in self.sand_grid.items():
        counts[elem] = counts.get(elem, 0) + 1

    # Title bar
    brush_name = self.SAND_ELEM_NAMES.get(self.sand_brush, "?")
    title = f" Falling Sand  Tick: {self.sand_generation}  Particles: {len(self.sand_grid)}"
    state = " PLAY" if self.sand_running else f" PAUSE  Brush: {brush_name} (sz:{self.sand_brush_size})"
    title += f"  {state}"
    title = title[:max_x - 1]
    try:
        self.stdscr.addstr(0, 0, title, curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw grid
    draw_start = 1
    draw_rows = max_y - 3
    draw_cols = (max_x - 1) // 2
    if draw_rows < 1:
        draw_rows = 1

    for y in range(draw_rows):
        if y >= self.sand_rows:
            break
        screen_y = draw_start + y
        if screen_y >= max_y - 2:
            break
        for x in range(draw_cols):
            if x >= self.sand_cols:
                break
            sx = x * 2
            if sx + 1 >= max_x:
                break
            cell = self.sand_grid.get((y, x))
            is_cursor = (y == self.sand_cursor_r and x == self.sand_cursor_c)

            if is_cursor and not self.sand_running:
                if cell is None:
                    ch = "[]"
                else:
                    ch = "\u2588\u2588"
                try:
                    self.stdscr.addstr(screen_y, sx, ch,
                                       curses.color_pair(7) | curses.A_BOLD)
                except curses.error:
                    pass
            elif cell is not None:
                elem, age = cell
                color = self.SAND_ELEM_COLORS.get(elem, 1)
                ch = self.SAND_ELEM_CHARS.get(elem, "\u2588\u2588")
                attr = curses.color_pair(color)
                # Fire flickers
                if elem == self.SAND_FIRE:
                    if age > 10:
                        attr = curses.color_pair(3)  # yellow as it dies
                    if random.random() < 0.3:
                        attr |= curses.A_BOLD
                # Plant gets brighter with age
                elif elem == self.SAND_PLANT and age > 5:
                    attr |= curses.A_BOLD
                # Oil is dim
                elif elem == self.SAND_OIL:
                    attr |= curses.A_DIM
                # Steam fades as it ages
                elif elem == self.SAND_STEAM:
                    attr |= curses.A_DIM
                try:
                    self.stdscr.addstr(screen_y, sx, ch, attr)
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        parts = []
        for eid, ename in sorted(self.SAND_ELEM_NAMES.items()):
            if eid == 0:
                continue
            cnt = counts.get(eid, 0)
            if cnt > 0:
                parts.append(f"{ename}:{cnt}")
        status = f" Tick: {self.sand_generation}  |  {' '.join(parts)}  |  Speed: {SPEED_LABELS[self.speed_idx]}"
        status = status[:max_x - 1]
        try:
            self.stdscr.addstr(status_y, 0, status, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [1-7]=element [0]=erase [+/-]=size [Enter]=place [r]=clear [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register sand mode methods on the App class."""
    App._sand_build_preset = _sand_build_preset
    App._sand_init = _sand_init
    App._sand_step = _sand_step
    App._enter_sand_mode = _enter_sand_mode
    App._exit_sand_mode = _exit_sand_mode
    App._handle_sand_menu_key = _handle_sand_menu_key
    App._handle_sand_key = _handle_sand_key
    App._sand_paint = _sand_paint
    App._draw_sand_menu = _draw_sand_menu
    App._draw_sand = _draw_sand

