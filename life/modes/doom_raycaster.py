"""Doom Raycaster — a first-person walk through ASCII mazes drawn by raycasting."""
import curses
import math

DOOMRC_PRESETS = [
    ("Dungeon", "Dark stone corridors with twisting passages", "dungeon"),
    ("Office", "Cubicle maze — corporate labyrinth", "office"),
    ("Outdoor Ruins", "Crumbling walls in an open field", "ruins"),
    ("Arena", "Large open room with pillars", "arena"),
    ("Maze", "Dense procedurally-generated maze", "maze"),
    ("Fortress", "Thick-walled castle with rooms and hallways", "fortress"),
]

DOOMRC_MAPS = {
    "dungeon": [
        "################",
        "#..............#",
        "#..####..####..#",
        "#..#........#..#",
        "#..#..####..#..#",
        "#..#..#..#..#..#",
        "#.....#..#.....#",
        "###...#..#...###",
        "#.....#..#.....#",
        "#..#..####..#..#",
        "#..#........#..#",
        "#..####..####..#",
        "#..............#",
        "#...###..###...#",
        "#..............#",
        "################",
    ],
    "office": [
        "################",
        "#..#..#..#..#..#",
        "#..#..#..#..#..#",
        "#..............#",
        "####..####..####",
        "#..............#",
        "#..##......##..#",
        "#..#........#..#",
        "#..#........#..#",
        "#..##......##..#",
        "#..............#",
        "####..####..####",
        "#..............#",
        "#..#..#..#..#..#",
        "#..#..#..#..#..#",
        "################",
    ],
    "ruins": [
        "################",
        "#..............#",
        "#..##....##..#.#",
        "#...........#..#",
        "#....##........#",
        "#..............#",
        "#.#....##....#.#",
        "#..............#",
        "#........##....#",
        "#..#...........#",
        "#..............#",
        "#....#....#....#",
        "#..............#",
        "#.#..........#.#",
        "#..............#",
        "################",
    ],
    "arena": [
        "################",
        "#..............#",
        "#..............#",
        "#...##..##...#.#",
        "#..............#",
        "#.....##.......#",
        "#..............#",
        "#..##....##..#.#",
        "#..##....##....#",
        "#..............#",
        "#......##......#",
        "#..............#",
        "#...##..##.....#",
        "#..............#",
        "#..............#",
        "################",
    ],
    "maze": [
        "################",
        "#.#....#.....#.#",
        "#.#.##.#.###.#.#",
        "#.#..#.#.#.....#",
        "#.##.#.#.#.###.#",
        "#....#.#.#.#...#",
        "#.####.#.#.#.#.#",
        "#......#...#.#.#",
        "#.######.###.#.#",
        "#.#......#...#.#",
        "#.#.######.###.#",
        "#.#........#...#",
        "#.########.#.#.#",
        "#..........#.#.#",
        "#.############.#",
        "################",
    ],
    "fortress": [
        "################",
        "#..............#",
        "#.####..####.#.#",
        "#.#..#..#..#...#",
        "#.#..#..#..#.#.#",
        "#.####..####...#",
        "#..............#",
        "###..######..###",
        "#..............#",
        "#.####..####...#",
        "#.#..#..#..#.#.#",
        "#.#..#..#..#...#",
        "#.####..####.#.#",
        "#..............#",
        "#......##......#",
        "################",
    ],
}

DOOMRC_SHADE_WALL = "\u2588\u2593\u2592\u2591\u00b7"
DOOMRC_SHADE_FLOOR = "#x=-.  "


def _enter_doomrc_mode(self):
    """Enter Doom Raycaster mode — show preset menu."""
    self.doomrc_menu = True
    self.doomrc_menu_sel = 0
    self._flash("Doom Raycaster — select a map")



def _exit_doomrc_mode(self):
    """Exit Doom Raycaster mode."""
    self.doomrc_mode = False
    self.doomrc_menu = False
    self.doomrc_running = False
    self._flash("Doom Raycaster mode OFF")



def _doomrc_find_spawn(self) -> tuple:
    """Return the first open floor tile as the player spawn point."""
    for r in range(self.doomrc_map_h):
        for c in range(self.doomrc_map_w):
            if self.doomrc_map[r][c] == '.':
                return (c + 0.5, r + 0.5)
    return (1.5, 1.5)



def _doomrc_init(self, preset_idx: int):
    """Start the raycaster on the chosen map."""
    name, _desc, key = self.DOOMRC_PRESETS[preset_idx]
    self.doomrc_preset_name = name
    self.doomrc_map = list(self.DOOMRC_MAPS[key])
    self.doomrc_map_h = len(self.doomrc_map)
    self.doomrc_map_w = len(self.doomrc_map[0]) if self.doomrc_map else 0
    sx, sy = self._doomrc_find_spawn()
    self.doomrc_px = sx
    self.doomrc_py = sy
    self.doomrc_pa = 0.0
    self.doomrc_generation = 0
    self.doomrc_running = True
    self.doomrc_show_map = True
    self.doomrc_show_help = True
    self.doomrc_menu = False
    self.doomrc_mode = True
    self._flash(f"Doom Raycaster: {name} — WASD to move, Q/E to turn")



def _doomrc_is_wall(self, x: float, y: float) -> bool:
    """Return True if map position (x, y) is a wall or off the map."""
    ix = int(x)
    iy = int(y)
    if ix < 0 or iy < 0 or iy >= self.doomrc_map_h or ix >= self.doomrc_map_w:
        return True
    return self.doomrc_map[iy][ix] == '#'



def _doomrc_move(self, dx: float, dy: float):
    """Move the player by (dx, dy), sliding along walls on collision."""
    margin = 0.2
    nx = self.doomrc_px + dx
    ny = self.doomrc_py + dy
    # Try full movement
    if not self._doomrc_is_wall(nx, ny):
        # Also check corners for the player radius
        if (not self._doomrc_is_wall(nx - margin, ny - margin) and
            not self._doomrc_is_wall(nx + margin, ny - margin) and
            not self._doomrc_is_wall(nx - margin, ny + margin) and
            not self._doomrc_is_wall(nx + margin, ny + margin)):
            self.doomrc_px = nx
            self.doomrc_py = ny
            return
    # Wall sliding — try x only
    if not self._doomrc_is_wall(self.doomrc_px + dx, self.doomrc_py):
        if (not self._doomrc_is_wall(self.doomrc_px + dx - margin, self.doomrc_py - margin) and
            not self._doomrc_is_wall(self.doomrc_px + dx + margin, self.doomrc_py + margin)):
            self.doomrc_px += dx
            return
    # Wall sliding — try y only
    if not self._doomrc_is_wall(self.doomrc_px, self.doomrc_py + dy):
        if (not self._doomrc_is_wall(self.doomrc_px - margin, self.doomrc_py + dy - margin) and
            not self._doomrc_is_wall(self.doomrc_px + margin, self.doomrc_py + dy + margin)):
            self.doomrc_py += dy



def _doomrc_step(self):
    """Count one frame."""
    self.doomrc_generation += 1



def _handle_doomrc_menu_key(self, key: int) -> bool:
    """Handle keys in the Doom Raycaster map menu."""
    n = len(self.DOOMRC_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.doomrc_menu_sel = (self.doomrc_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.doomrc_menu_sel = (self.doomrc_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._doomrc_init(self.doomrc_menu_sel)
    elif key == 27:  # Escape
        self.doomrc_menu = False
        self.doomrc_mode = False
    else:
        return False
    return True



def _handle_doomrc_key(self, key: int) -> bool:
    """Handle keys while walking the map."""
    spd = self.doomrc_speed
    rspd = self.doomrc_rot_speed
    cos_a = math.cos(self.doomrc_pa)
    sin_a = math.sin(self.doomrc_pa)

    if key in (ord('w'), ord('W'), curses.KEY_UP):
        self._doomrc_move(cos_a * spd, sin_a * spd)
    elif key in (ord('s'), ord('S'), curses.KEY_DOWN):
        self._doomrc_move(-cos_a * spd, -sin_a * spd)
    elif key in (ord('a'), ord('A')):
        # Strafe left
        self._doomrc_move(sin_a * spd, -cos_a * spd)
    elif key in (ord('d'), ord('D')):
        # Strafe right
        self._doomrc_move(-sin_a * spd, cos_a * spd)
    elif key in (ord('q'), ord('Q'), curses.KEY_LEFT):
        self.doomrc_pa -= rspd
    elif key in (ord('e'), ord('E'), curses.KEY_RIGHT):
        self.doomrc_pa += rspd
    elif key == ord(' '):
        self.doomrc_running = not self.doomrc_running
    elif key == ord('m'):
        self.doomrc_show_map = not self.doomrc_show_map
    elif key == ord('?'):
        self.doomrc_show_help = not self.doomrc_show_help
    elif key == 27:  # Escape
        self.doomrc_mode = False
        self.doomrc_running = False
        self._flash("Doom Raycaster mode OFF")
    else:
        return True  # consume all keys while in mode
    return True



def _draw_doomrc_menu(self, max_y: int, max_x: int):
    """Draw the Doom Raycaster map menu."""
    self.stdscr.erase()
    title = "╔══ DOOM RAYCASTER ══╗"
    subtitle = "Select a map to explore"
    try:
        cy = max(1, max_y // 2 - len(self.DOOMRC_PRESETS) // 2 - 3)
        cx = max(0, (max_x - len(title)) // 2)
        self.stdscr.addstr(cy, cx, title, curses.A_BOLD | curses.color_pair(4))
        self.stdscr.addstr(cy + 1, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(5))
        # Centre the list as a block and clip each line at the right edge.
        width = max(22 + len(desc) for _n, desc, _k in self.DOOMRC_PRESETS)
        lx = max(0, (max_x - width) // 2)
        for i, (name, desc, _key) in enumerate(self.DOOMRC_PRESETS):
            y = cy + 3 + i
            if y >= max_y - 2:
                break
            marker = "▸ " if i == self.doomrc_menu_sel else "  "
            attr = curses.A_BOLD | curses.color_pair(4) if i == self.doomrc_menu_sel else curses.color_pair(3)
            line = f"{marker}{name:<18s}  {desc}"
            self.stdscr.addstr(y, lx, line[:max(0, max_x - 1 - lx)], attr)
        nav = "↑/↓ navigate · Enter select · Esc cancel"
        ny = cy + 3 + len(self.DOOMRC_PRESETS) + 1
        if ny < max_y - 1:
            self.stdscr.addstr(ny, max(0, (max_x - len(nav)) // 2), nav, curses.A_DIM)
    except curses.error:
        pass



def _draw_doomrc(self, max_y: int, max_x: int):
    """Draw the first-person view by casting one ray per screen column."""
    self.stdscr.erase()
    if max_y < 5 or max_x < 10:
        return

    screen_h = max_y - 1  # leave last line for HUD
    screen_w = max_x - 1
    pa = self.doomrc_pa
    fov = self.doomrc_fov
    depth = self.doomrc_depth
    px = self.doomrc_px
    py = self.doomrc_py
    map_data = self.doomrc_map
    map_h = self.doomrc_map_h
    map_w = self.doomrc_map_w

    shade_wall = self.DOOMRC_SHADE_WALL
    shade_floor = self.DOOMRC_SHADE_FLOOR
    n_wall = len(shade_wall)
    n_floor = len(shade_floor)

    for x in range(screen_w):
        ray_a = (pa - fov / 2.0) + (x / float(screen_w)) * fov
        cos_r = math.cos(ray_a)
        sin_r = math.sin(ray_a)

        # Fixed-step ray march.
        dist = 0.0
        step_size = 0.02
        max_steps = int(depth / step_size)

        for _s in range(max_steps):
            dist += step_size
            ray_x = px + cos_r * dist
            ray_y = py + sin_r * dist
            ix = int(ray_x)
            iy = int(ray_y)
            if ix < 0 or iy < 0 or iy >= map_h or ix >= map_w:
                break
            if map_data[iy][ix] == '#':
                break

        # Correct for fisheye
        dist *= math.cos(ray_a - pa)
        if dist < 0.01:
            dist = 0.01

        wall_h = int(screen_h / dist) if dist > 0 else screen_h
        ceiling = int((screen_h - wall_h) / 2.0)
        floor = ceiling + wall_h

        for y in range(screen_h):
            try:
                if y < ceiling:
                    self.stdscr.addstr(y, x, " ")
                elif y <= floor:
                    t = dist / depth
                    idx = min(int(t * n_wall), n_wall - 1)
                    ch = shade_wall[idx]
                    if dist < depth * 0.25:
                        attr = curses.color_pair(4) | curses.A_BOLD
                    elif dist < depth * 0.5:
                        attr = curses.color_pair(3)
                    elif dist < depth * 0.75:
                        attr = curses.color_pair(5)
                    else:
                        attr = curses.A_DIM
                    self.stdscr.addstr(y, x, ch, attr)
                else:
                    b = 1.0 - (y - screen_h / 2.0) / (screen_h / 2.0)
                    if b < 0.01:
                        b = 0.01
                    idx = min(int(b * n_floor), n_floor - 1)
                    ch = shade_floor[idx]
                    self.stdscr.addstr(y, x, ch, curses.A_DIM)
            except curses.error:
                pass

    if self.doomrc_show_map:
        _draw_doomrc_minimap(self, max_y, max_x)
    if self.doomrc_show_help:
        hint = " WASD/arrows=move  Q/E=turn  m=map  ?=hide hints  Esc=exit"
        try:
            self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.A_DIM)
        except curses.error:
            pass


def _draw_doomrc_minimap(self, max_y: int, max_x: int):
    """Overlay a top-down map with the player's position and heading."""
    if self.doomrc_map_h >= max_y - 1 or self.doomrc_map_w >= max_x - 1:
        return
    px, py = int(self.doomrc_px), int(self.doomrc_py)
    heading = ">v<^"[int((self.doomrc_pa % (2 * math.pi)) / (math.pi / 2) + 0.5) % 4]
    for r, row in enumerate(self.doomrc_map):
        for c, tile in enumerate(row):
            if (c, r) == (px, py):
                ch, attr = heading, curses.A_BOLD | curses.color_pair(4)
            else:
                ch, attr = tile, curses.A_DIM
            try:
                self.stdscr.addstr(r, c, ch, attr)
            except curses.error:
                pass


def register(App):
    """Register Doom Raycaster methods and constants on the App class."""
    App.DOOMRC_PRESETS = DOOMRC_PRESETS
    App.DOOMRC_MAPS = DOOMRC_MAPS
    App.DOOMRC_SHADE_WALL = DOOMRC_SHADE_WALL
    App.DOOMRC_SHADE_FLOOR = DOOMRC_SHADE_FLOOR
    App._enter_doomrc_mode = _enter_doomrc_mode
    App._exit_doomrc_mode = _exit_doomrc_mode
    App._doomrc_find_spawn = _doomrc_find_spawn
    App._doomrc_init = _doomrc_init
    App._doomrc_is_wall = _doomrc_is_wall
    App._doomrc_move = _doomrc_move
    App._doomrc_step = _doomrc_step
    App._handle_doomrc_menu_key = _handle_doomrc_menu_key
    App._handle_doomrc_key = _handle_doomrc_key
    App._draw_doomrc_menu = _draw_doomrc_menu
    App._draw_doomrc = _draw_doomrc

