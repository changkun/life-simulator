"""Mode: doomrc — simulation mode for the life package."""
import curses
import math
import random
import time


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
    """Find first open floor tile to spawn the player."""
    for r in range(self.doomrc_map_h):
        for c in range(self.doomrc_map_w):
            if self.doomrc_map[r][c] == '.':
                return (c + 0.5, r + 0.5)
    return (1.5, 1.5)



def _doomrc_init(self, preset_idx: int):
    """Initialize raycaster with chosen map preset."""
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
    """Check if map position (x,y) is a wall."""
    ix = int(x)
    iy = int(y)
    if ix < 0 or iy < 0 or iy >= self.doomrc_map_h or ix >= self.doomrc_map_w:
        return True
    return self.doomrc_map[iy][ix] == '#'



def _doomrc_move(self, dx: float, dy: float):
    """Try to move player by (dx,dy) with collision detection and wall sliding."""
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
    """Advance one frame."""
    self.doomrc_generation += 1



def _handle_doomrc_menu_key(self, key: int) -> bool:
    """Handle input in doom raycaster preset menu."""
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
    """Handle input in active doom raycaster simulation."""
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
    """Draw the doom raycaster preset selection menu."""
    self.stdscr.erase()
    title = "╔══ DOOM RAYCASTER ══╗"
    subtitle = "Select a map to explore"
    try:
        cy = max(1, max_y // 2 - len(self.DOOMRC_PRESETS) // 2 - 3)
        cx = max(0, (max_x - len(title)) // 2)
        self.stdscr.addstr(cy, cx, title, curses.A_BOLD | curses.color_pair(4))
        self.stdscr.addstr(cy + 1, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(5))
        for i, (name, desc, _key) in enumerate(self.DOOMRC_PRESETS):
            y = cy + 3 + i
            if y >= max_y - 2:
                break
            marker = "▸ " if i == self.doomrc_menu_sel else "  "
            attr = curses.A_BOLD | curses.color_pair(4) if i == self.doomrc_menu_sel else curses.color_pair(3)
            line = f"{marker}{name:<18s}  {desc}"
            self.stdscr.addstr(y, max(0, cx - 2), line[:max_x - 1], attr)
        nav = "↑/↓ navigate · Enter select · Esc cancel"
        ny = cy + 3 + len(self.DOOMRC_PRESETS) + 1
        if ny < max_y - 1:
            self.stdscr.addstr(ny, max(0, (max_x - len(nav)) // 2), nav, curses.A_DIM)
    except curses.error:
        pass



def _draw_doomrc(self, max_y: int, max_x: int):
    """Render doom-style first-person view via raycasting."""
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

    # Cast a ray for each column
    for x in range(screen_w):
        # Ray angle for this column
        ray_a = (pa - fov / 2.0) + (x / float(screen_w)) * fov
        cos_r = math.cos(ray_a)
        sin_r = math.sin(ray_a)

        # DDA raycasting
        dist = 0.0
        hit = False
        step_size = 0.02
        max_steps = int(depth / step_size)

        # Use a faster stepping approach
        ray_x = px
        ray_y = py
        for _s in range(max_steps):
            dist += step_size
            ray_x = px + cos_r * dist
            ray_y = py + sin_r * dist
            ix = int(ray_x)
            iy = int(ray_y)
            if ix < 0 or iy < 0 or iy >= map_h or ix >= map_w:
                hit = True
                break
            if map_data[iy][ix] == '#':
                hit = True
                break

        # Correct for fisheye
        dist *= math.cos(ray_a - pa)
        if dist < 0.01:
            dist = 0.01

        # Calculate wall height
        wall_h = int(screen_h / dist) if dist > 0 else screen_h
        ceiling = int((screen_h - wall_h) / 2.0)
        floor = ceiling + wall_h

        for y in range(screen_h):
            try:
                if y < ceiling:
                    # Ceiling
                    self.stdscr.addstr(y, x, " ")
                elif y <= floor:
                    # Wall — shade by distance
                    t = dist / depth
                    idx = min(int(t * n_wall), n_wall - 1)
                    ch = shade_wall[idx]
                    # Color walls by distance
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
                    # Floor — shade by distance from bottom
                    b = 1.0 - (y - screen_h / 2.0) / (screen_h / 2.0)
                    if b < 0.01:
                        b = 0.01
                    idx = min(int(b * n_floor), n_floor - 1)
                    ch = shade_floor[idx]
                    self.stdscr.addstr(y, x, ch, curses.A_DIM)
            except curses.error:
                pass


def register(App):
    """Register doomrc mode methods on the App class."""
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

