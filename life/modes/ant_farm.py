"""Mode: antfarm — simulation mode for the life package."""
import curses
import math
import random
import time

ANTFARM_PRESETS = [
    ("Classic Colony", "Standard ant colony with balanced terrain", "classic"),
    ("Sandy Soil", "Loose sand — ants dig faster but tunnels are fragile", "sandy"),
    ("Rocky Ground", "Dense rocky soil — slow digging with obstacles", "rocky"),
    ("Deep Nest", "Extra-deep colony with multiple chamber layers", "deep"),
    ("Rainy Day", "Colony with rain that brings surface food and moisture", "rainy"),
]

# Cell type constants
_AF_AIR = 0
_AF_DIRT = 1
_AF_ROCK = 2
_AF_CLAY = 3
_AF_CHAMBER = 4
_AF_FOOD_STORE = 5
_AF_QUEEN_CELL = 6


def _enter_antfarm_mode(self):
    """Enter Ant Farm Simulation mode — show preset menu."""
    self.antfarm_menu = True
    self.antfarm_menu_sel = 0




def _exit_antfarm_mode(self):
    """Exit Ant Farm Simulation mode."""
    self.antfarm_mode = False
    self.antfarm_menu = False
    self.antfarm_running = False
    self.antfarm_ants = []
    self.antfarm_grid = []
    self.antfarm_pheromone_food = []
    self.antfarm_pheromone_home = []
    self.antfarm_food_surface = []
    self.antfarm_rain_drops = []




def _antfarm_init(self, preset: str):
    """Initialize ant farm from a preset."""
    self.antfarm_menu = False
    self.antfarm_mode = True
    self.antfarm_running = True
    self.antfarm_generation = 0
    self.antfarm_total_food = 0
    self.antfarm_eggs = 0
    self.antfarm_rain_active = preset == "rainy"

    try:
        max_y, max_x = self.stdscr.getmaxyx()
    except Exception:
        max_y, max_x = 40, 120

    self.antfarm_rows = max(20, max_y - 2)
    self.antfarm_cols = max(40, max_x - 1)
    rows, cols = self.antfarm_rows, self.antfarm_cols
    self.antfarm_sky_rows = max(3, rows // 8)
    self.antfarm_surface_row = self.antfarm_sky_rows
    self.antfarm_cursor_x = cols // 2

    sr = self.antfarm_surface_row

    # Initialize grid — sky is AIR, underground is DIRT with layers
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if r < sr:
                row.append(_AF_AIR)
            else:
                depth = r - sr
                if preset == "rocky" and random.random() < 0.12 + depth * 0.004:
                    row.append(_AF_ROCK)
                elif preset == "deep" and depth > rows * 0.6 and random.random() < 0.15:
                    row.append(_AF_ROCK)
                elif depth > 4 and random.random() < 0.05:
                    row.append(_AF_CLAY)
                elif depth > rows // 3 and random.random() < 0.08:
                    row.append(_AF_ROCK)
                else:
                    row.append(_AF_DIRT)
        grid.append(row)
    self.antfarm_grid = grid

    # Pheromone grids
    self.antfarm_pheromone_food = [[0.0] * cols for _ in range(rows)]
    self.antfarm_pheromone_home = [[0.0] * cols for _ in range(rows)]

    # Queen chamber — centered, a few rows below surface
    qr = sr + 4
    qc = cols // 2
    self.antfarm_queen_pos = (qr, qc)
    for dr in range(-1, 2):
        for dc in range(-2, 3):
            rr, cc = qr + dr, qc + dc
            if 0 <= rr < rows and 0 <= cc < cols:
                grid[rr][cc] = _AF_QUEEN_CELL

    # Dig a starter tunnel from surface to queen
    for r in range(sr, qr):
        if 0 <= r < rows and 0 <= qc < cols:
            grid[r][qc] = _AF_AIR

    # Scatter surface food
    self.antfarm_food_surface = []
    for _ in range(max(5, cols // 10)):
        fx = random.randint(1, cols - 2)
        self.antfarm_food_surface.append(fx)

    # Create initial ants
    num_ants = 15 if preset in ("classic", "rainy") else (20 if preset == "deep" else 12)
    self.antfarm_ants = []
    for i in range(num_ants):
        ant = {
            "r": qr,
            "c": qc + random.randint(-1, 1),
            "has_food": False,
            "state": "explore",  # explore, forage, return_food, dig
            "target_r": 0,
            "target_c": 0,
            "dig_strength": 2 if preset == "sandy" else 1,
            "age": 0,
            "energy": 100,
        }
        self.antfarm_ants.append(ant)

    self.antfarm_rain_drops = []

    # Preset-specific name
    for name, _desc, key in ANTFARM_PRESETS:
        if key == preset:
            self.antfarm_preset_name = name
            break




def _antfarm_step(self):
    """Advance the ant farm simulation by one tick."""
    self.antfarm_generation += 1
    rows = self.antfarm_rows
    cols = self.antfarm_cols
    grid = self.antfarm_grid
    p_food = self.antfarm_pheromone_food
    p_home = self.antfarm_pheromone_home
    sr = self.antfarm_surface_row
    qr, qc = self.antfarm_queen_pos

    # Decay pheromones
    for r in range(rows):
        for c in range(cols):
            p_food[r][c] *= 0.995
            p_home[r][c] *= 0.995
            if p_food[r][c] < 0.01:
                p_food[r][c] = 0.0
            if p_home[r][c] < 0.01:
                p_home[r][c] = 0.0

    # Rain
    if self.antfarm_rain_active:
        # Add new drops
        for _ in range(max(1, cols // 15)):
            rx = random.randint(0, cols - 1)
            self.antfarm_rain_drops.append([0, rx])
        # Move drops down
        new_drops = []
        for drop in self.antfarm_rain_drops:
            drop[0] += 1
            if drop[0] < sr:
                new_drops.append(drop)
            # Rain reaching surface can spawn food occasionally
            elif drop[0] == sr and random.random() < 0.002:
                self.antfarm_food_surface.append(drop[1])
        self.antfarm_rain_drops = new_drops

    # Move ants
    for ant in self.antfarm_ants:
        ant["age"] += 1
        r, c = ant["r"], ant["c"]

        if ant["state"] == "explore":
            # Wander around, prefer unexplored tunnels, occasionally dig
            neighbors = []
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    cell = grid[nr][nc]
                    if cell in (_AF_AIR, _AF_CHAMBER, _AF_QUEEN_CELL, _AF_FOOD_STORE):
                        neighbors.append((nr, nc, 1.0 + p_food[nr][nc] * 5.0))
                    elif cell == _AF_DIRT and nr > sr:
                        # Might dig
                        if random.random() < 0.08:
                            grid[nr][nc] = _AF_AIR
                            neighbors.append((nr, nc, 0.5))
                    elif cell == _AF_CLAY and nr > sr:
                        if random.random() < 0.02 * ant["dig_strength"]:
                            grid[nr][nc] = _AF_AIR
                            neighbors.append((nr, nc, 0.3))

            if neighbors:
                # Weighted random choice
                total = sum(w for _, _, w in neighbors)
                pick = random.random() * total
                cum = 0
                chosen = neighbors[0]
                for nr, nc, w in neighbors:
                    cum += w
                    if cum >= pick:
                        chosen = (nr, nc, w)
                        break
                ant["r"], ant["c"] = chosen[0], chosen[1]

                # Leave home pheromone
                p_home[ant["r"]][ant["c"]] = min(p_home[ant["r"]][ant["c"]] + 0.5, 10.0)

            # Check if at surface — switch to forage
            if ant["r"] <= sr + 1 and random.random() < 0.3:
                ant["state"] = "forage"

            # Occasionally switch to dig mode to create tunnels
            if ant["r"] > sr + 3 and random.random() < 0.02:
                ant["state"] = "dig"

        elif ant["state"] == "forage":
            # Move along surface looking for food
            if ant["r"] > sr:
                # Move up to surface
                ant["r"] = max(sr, ant["r"] - 1)
            else:
                # Walk along surface
                dc = random.choice([-1, 0, 1])
                nc = max(0, min(cols - 1, c + dc))
                ant["c"] = nc

                # Check for food
                if nc in self.antfarm_food_surface:
                    self.antfarm_food_surface.remove(nc)
                    ant["has_food"] = True
                    ant["state"] = "return_food"
                    self.antfarm_total_food += 1

                # Give up after a while
                if random.random() < 0.01:
                    ant["state"] = "explore"

        elif ant["state"] == "return_food":
            # Navigate back toward queen chamber using home pheromone
            best = None
            best_score = -1
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    cell = grid[nr][nc]
                    if cell in (_AF_AIR, _AF_CHAMBER, _AF_QUEEN_CELL, _AF_FOOD_STORE):
                        # Score: prefer toward queen, use home pheromone
                        dist = abs(nr - qr) + abs(nc - qc)
                        score = p_home[nr][nc] * 2.0 + max(0, 50 - dist)
                        if score > best_score:
                            best_score = score
                            best = (nr, nc)
                    elif cell == _AF_DIRT and nr > sr:
                        # Dig toward queen if needed
                        dist = abs(nr - qr) + abs(nc - qc)
                        if dist < abs(r - qr) + abs(c - qc) and random.random() < 0.15:
                            grid[nr][nc] = _AF_AIR
                            best = (nr, nc)
                            best_score = 999

            if best:
                ant["r"], ant["c"] = best
                # Leave food pheromone trail
                p_food[ant["r"]][ant["c"]] = min(p_food[ant["r"]][ant["c"]] + 1.0, 10.0)

            # Reached queen?
            if abs(ant["r"] - qr) <= 1 and abs(ant["c"] - qc) <= 2:
                ant["has_food"] = False
                ant["state"] = "explore"
                self.antfarm_eggs += 1
                # Spawn new ant occasionally
                if self.antfarm_eggs % 5 == 0 and len(self.antfarm_ants) < 60:
                    self.antfarm_ants.append({
                        "r": qr, "c": qc,
                        "has_food": False, "state": "explore",
                        "target_r": 0, "target_c": 0,
                        "dig_strength": 1, "age": 0, "energy": 100,
                    })

        elif ant["state"] == "dig":
            # Dig downward/sideways to create tunnels and chambers
            dig_dirs = [(1, 0), (1, -1), (1, 1), (0, -1), (0, 1)]
            random.shuffle(dig_dirs)
            dug = False
            for dr, dc in dig_dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and nr > sr:
                    cell = grid[nr][nc]
                    if cell == _AF_DIRT:
                        grid[nr][nc] = _AF_AIR
                        ant["r"], ant["c"] = nr, nc
                        p_home[nr][nc] = min(p_home[nr][nc] + 0.3, 10.0)
                        dug = True
                        break
                    elif cell == _AF_CLAY and random.random() < 0.1 * ant["dig_strength"]:
                        grid[nr][nc] = _AF_AIR
                        ant["r"], ant["c"] = nr, nc
                        dug = True
                        break
                    elif cell in (_AF_AIR, _AF_CHAMBER):
                        ant["r"], ant["c"] = nr, nc
                        dug = True
                        break

            if not dug or random.random() < 0.05:
                ant["state"] = "explore"

            # Create chambers at tunnel junctions
            if ant["r"] > sr + 5 and random.random() < 0.01:
                for dr2 in range(-1, 2):
                    for dc2 in range(-1, 2):
                        rr, cc = ant["r"] + dr2, ant["c"] + dc2
                        if 0 <= rr < rows and 0 <= cc < cols and grid[rr][cc] == _AF_DIRT:
                            grid[rr][cc] = _AF_CHAMBER

    # Occasionally spawn surface food
    if random.random() < 0.02 and len(self.antfarm_food_surface) < cols // 3:
        self.antfarm_food_surface.append(random.randint(1, cols - 2))




def _handle_antfarm_menu_key(self, key: int) -> bool:
    """Handle key presses in the ant farm preset selection menu."""
    if key == 27:  # Escape
        self.antfarm_menu = False
        self._exit_antfarm_mode()
        return True
    elif key == curses.KEY_UP:
        self.antfarm_menu_sel = (self.antfarm_menu_sel - 1) % len(ANTFARM_PRESETS)
        return True
    elif key == curses.KEY_DOWN:
        self.antfarm_menu_sel = (self.antfarm_menu_sel + 1) % len(ANTFARM_PRESETS)
        return True
    elif key in (10, 13, curses.KEY_ENTER):
        _name, _desc, preset_key = ANTFARM_PRESETS[self.antfarm_menu_sel]
        self._antfarm_init(preset_key)
        return True
    return True




def _handle_antfarm_key(self, key: int) -> bool:
    """Handle key presses during ant farm simulation."""
    if key == 27:  # Escape
        self._exit_antfarm_mode()
        return True
    elif key == ord(" "):
        self.antfarm_running = not self.antfarm_running
        return True
    elif key == ord("n"):
        self._antfarm_step()
        return True
    elif key == ord("r"):
        # Reset with same preset
        for _name, _desc, k in ANTFARM_PRESETS:
            if _name == self.antfarm_preset_name:
                self._antfarm_init(k)
                break
        return True
    elif key == ord("R") or key == ord("m"):
        # Return to preset menu
        self.antfarm_mode = False
        self.antfarm_menu = True
        self.antfarm_menu_sel = 0
        return True
    elif key == ord("+") or key == ord("="):
        self.antfarm_speed = min(10, self.antfarm_speed + 1)
        return True
    elif key == ord("-"):
        self.antfarm_speed = max(1, self.antfarm_speed - 1)
        return True
    elif key == ord("i"):
        self.antfarm_show_info = not self.antfarm_show_info
        return True
    elif key == ord("f"):
        # Drop food at cursor position
        self.antfarm_food_surface.append(self.antfarm_cursor_x)
        return True
    elif key == ord("w"):
        # Toggle rain
        self.antfarm_rain_active = not self.antfarm_rain_active
        if not self.antfarm_rain_active:
            self.antfarm_rain_drops = []
        return True
    elif key == ord("o"):
        # Place obstacle (rock) at cursor position, a few rows below surface
        sr = self.antfarm_surface_row
        obs_r = sr + 3
        cx = self.antfarm_cursor_x
        if 0 <= obs_r < self.antfarm_rows and 0 <= cx < self.antfarm_cols:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    rr, cc = obs_r + dr, cx + dc
                    if 0 <= rr < self.antfarm_rows and 0 <= cc < self.antfarm_cols:
                        self.antfarm_grid[rr][cc] = _AF_ROCK
        return True
    elif key == curses.KEY_LEFT:
        self.antfarm_cursor_x = max(0, self.antfarm_cursor_x - 1)
        return True
    elif key == curses.KEY_RIGHT:
        self.antfarm_cursor_x = min(self.antfarm_cols - 1, self.antfarm_cursor_x + 1)
        return True
    return True




def _draw_antfarm_menu(self, max_y: int, max_x: int):
    """Draw the ant farm preset selection menu."""
    self.stdscr.erase()
    try:
        title_lines = [
            "╔══════════════════════════════════════════╗",
            "║        ANT FARM SIMULATION               ║",
            "║   Side-view underground ant colony       ║",
            "╚══════════════════════════════════════════╝",
        ]
        start_y = max(0, max_y // 2 - len(ANTFARM_PRESETS) // 2 - 5)
        for i, line in enumerate(title_lines):
            y = start_y + i
            x = max(0, (max_x - len(line)) // 2)
            if y < max_y - 1:
                self.stdscr.addstr(y, x, line[:max_x - 1])

        y = start_y + len(title_lines) + 1
        hdr = "Select a Preset:"
        x = max(0, (max_x - len(hdr)) // 2)
        if y < max_y - 1:
            self.stdscr.addstr(y, x, hdr, curses.A_BOLD)
        y += 2

        for idx, (name, desc, _key) in enumerate(ANTFARM_PRESETS):
            if y >= max_y - 3:
                break
            prefix = " > " if idx == self.antfarm_menu_sel else "   "
            attr = curses.A_REVERSE if idx == self.antfarm_menu_sel else 0
            line = f"{prefix}{name}"
            x = max(0, (max_x - 50) // 2)
            self.stdscr.addstr(y, x, line[:max_x - 1], attr)
            y += 1
            desc_line = f"     {desc}"
            if y < max_y - 1:
                self.stdscr.addstr(y, x, desc_line[:max_x - 1], curses.A_DIM)
            y += 2

        footer = "[↑/↓] Navigate  [Enter] Select  [Esc] Back"
        fy = min(max_y - 2, y + 1)
        fx = max(0, (max_x - len(footer)) // 2)
        if fy > 0:
            self.stdscr.addstr(fy, fx, footer[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass




def _draw_antfarm(self, max_y: int, max_x: int):
    """Draw the ant farm simulation."""
    self.stdscr.erase()
    grid = self.antfarm_grid
    rows = self.antfarm_rows
    cols = self.antfarm_cols
    sr = self.antfarm_surface_row
    p_food = self.antfarm_pheromone_food
    p_home = self.antfarm_pheromone_home
    qr, qc = self.antfarm_queen_pos
    draw_rows = min(rows, max_y - 2)
    draw_cols = min(cols, max_x - 1)

    # Build character buffer
    buf = []
    attr_buf = []
    for r in range(draw_rows):
        row_chars = []
        row_attrs = []
        for c in range(draw_cols):
            if r < sr:
                # Sky
                ch = " "
                at = 0
                # Sun/clouds
                if r == 0 and c == draw_cols - 5:
                    ch = "O"
                    at = curses.A_BOLD
                elif r == 1 and 10 < c < 20:
                    ch = "~"
                    at = curses.A_DIM
            elif r == sr:
                # Ground surface
                ch = "="
                at = curses.A_BOLD
                if grid[r][c] == _AF_AIR:
                    ch = " "
                    at = 0
            else:
                # Underground
                cell = grid[r][c]
                if cell == _AF_AIR:
                    ch = " "
                    at = 0
                    # Show pheromones faintly
                    if p_food[r][c] > 0.5:
                        ch = "."
                        at = curses.A_DIM
                    elif p_home[r][c] > 0.5:
                        ch = ","
                        at = curses.A_DIM
                elif cell == _AF_DIRT:
                    depth = r - sr
                    if depth < 3:
                        ch = "."
                    elif depth < 8:
                        ch = ":"
                    else:
                        ch = "#"
                    at = 0
                elif cell == _AF_CLAY:
                    ch = "%"
                    at = curses.A_BOLD
                elif cell == _AF_ROCK:
                    ch = "@"
                    at = curses.A_BOLD
                elif cell == _AF_CHAMBER:
                    ch = " "
                    at = 0
                elif cell == _AF_FOOD_STORE:
                    ch = "o"
                    at = curses.A_BOLD
                elif cell == _AF_QUEEN_CELL:
                    ch = " "
                    at = 0

            row_chars.append(ch)
            row_attrs.append(at)
        buf.append(row_chars)
        attr_buf.append(row_attrs)

    # Draw surface food
    for fx in self.antfarm_food_surface:
        if 0 <= fx < draw_cols and sr > 0 and sr - 1 < draw_rows:
            buf[sr - 1][fx] = "*"
            attr_buf[sr - 1][fx] = curses.A_BOLD

    # Draw rain
    for drop in self.antfarm_rain_drops:
        dr, dc = drop
        if 0 <= dr < draw_rows and 0 <= dc < draw_cols:
            buf[dr][dc] = "|"
            attr_buf[dr][dc] = curses.A_DIM

    # Draw queen
    if 0 <= qr < draw_rows and 0 <= qc < draw_cols:
        buf[qr][qc] = "Q"
        attr_buf[qr][qc] = curses.A_BOLD

    # Draw ants
    for ant in self.antfarm_ants:
        ar, ac = ant["r"], ant["c"]
        if 0 <= ar < draw_rows and 0 <= ac < draw_cols:
            if ant["has_food"]:
                buf[ar][ac] = "&"
                attr_buf[ar][ac] = curses.A_BOLD
            else:
                buf[ar][ac] = "a"
                attr_buf[ar][ac] = 0

    # Draw cursor on surface
    cx = self.antfarm_cursor_x
    if 0 <= cx < draw_cols and sr > 0:
        cursor_r = max(0, sr - 2)
        if cursor_r < draw_rows:
            buf[cursor_r][cx] = "V"
            attr_buf[cursor_r][cx] = curses.A_BOLD

    # Render buffer
    try:
        for r in range(draw_rows):
            for c in range(draw_cols):
                if r < max_y - 1 and c < max_x - 1:
                    try:
                        self.stdscr.addch(r, c, buf[r][c], attr_buf[r][c])
                    except curses.error:
                        pass

        # Status bar
        status_y = min(draw_rows, max_y - 2)
        if status_y >= 0:
            paused = "PAUSED" if not self.antfarm_running else "RUNNING"
            status = (f" {self.antfarm_preset_name} | Gen:{self.antfarm_generation} "
                      f"| Ants:{len(self.antfarm_ants)} | Food:{self.antfarm_total_food} "
                      f"| Eggs:{self.antfarm_eggs} | Speed:{self.antfarm_speed}x "
                      f"| Rain:{'ON' if self.antfarm_rain_active else 'OFF'} "
                      f"| {paused}")
            self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.A_REVERSE)

        # Info overlay
        if self.antfarm_show_info:
            info_lines = [
                "Controls:",
                " Space: Pause/Play    n: Step     r: Reset",
                " R/m: Preset menu     +/-: Speed  i: Info",
                " f: Drop food   w: Toggle rain   o: Place rock",
                " ←/→: Move cursor     Esc: Exit",
                "",
                "Legend:",
                " a=ant  &=ant+food  Q=queen  *=food",
                " ./:/#=soil layers  %=clay  @=rock",
                " .=food trail  ,=home trail",
            ]
            info_y = 1
            info_x = max(0, draw_cols - 50)
            for i, line in enumerate(info_lines):
                y = info_y + i
                if y < max_y - 2 and info_x + len(line) < max_x:
                    try:
                        self.stdscr.addstr(y, info_x, line, curses.A_DIM)
                    except curses.error:
                        pass
    except curses.error:
        pass


def register(App):
    """Register antfarm mode methods on the App class."""
    App._enter_antfarm_mode = _enter_antfarm_mode
    App._exit_antfarm_mode = _exit_antfarm_mode
    App._antfarm_init = _antfarm_init
    App._antfarm_step = _antfarm_step
    App._handle_antfarm_menu_key = _handle_antfarm_menu_key
    App._handle_antfarm_key = _handle_antfarm_key
    App._draw_antfarm_menu = _draw_antfarm_menu
    App._draw_antfarm = _draw_antfarm

