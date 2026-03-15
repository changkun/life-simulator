"""Mode: flythrough — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_flythrough_mode(self):
    """Enter 3D Terrain Flythrough mode — show preset menu."""
    self.flythrough_menu = True
    self.flythrough_menu_sel = 0
    self._flash("3D Terrain Flythrough — select a landscape")



def _exit_flythrough_mode(self):
    """Exit 3D Terrain Flythrough mode."""
    self.flythrough_mode = False
    self.flythrough_menu = False
    self.flythrough_running = False
    self.flythrough_heightmap = []
    self._flash("Flythrough mode OFF")



def _flythrough_generate(self, size: int, terrain_type: str):
    """Generate a heightmap for flythrough using layered noise."""
    hmap = [[0.0] * size for _ in range(size)]

    def _noise_layer(freq: float, amp: float):
        sr = max(2, int(size / freq))
        sc = max(2, int(size / freq))
        sparse_r = max(2, size // sr + 2)
        sparse_c = max(2, size // sc + 2)
        sparse = [[random.random() for _ in range(sparse_c)] for _ in range(sparse_r)]
        for r in range(size):
            for c in range(size):
                gr = r / sr
                gc = c / sc
                r0 = int(gr) % sparse_r
                r1 = (r0 + 1) % sparse_r
                c0 = int(gc) % sparse_c
                c1 = (c0 + 1) % sparse_c
                fr = gr - int(gr)
                fc = gc - int(gc)
                # Smooth interpolation (cosine)
                fr = (1 - math.cos(fr * math.pi)) * 0.5
                fc = (1 - math.cos(fc * math.pi)) * 0.5
                top = sparse[r0][c0] * (1 - fc) + sparse[r0][c1] * fc
                bot = sparse[r1][c0] * (1 - fc) + sparse[r1][c1] * fc
                hmap[r][c] += (top * (1 - fr) + bot * fr) * amp

    if terrain_type == "hills":
        _noise_layer(4, 0.4)
        _noise_layer(8, 0.3)
        _noise_layer(16, 0.15)
        _noise_layer(32, 0.08)
    elif terrain_type == "mountains":
        _noise_layer(3, 0.5)
        _noise_layer(6, 0.3)
        _noise_layer(12, 0.15)
        _noise_layer(24, 0.05)
        # Sharpen peaks
        for r in range(size):
            for c in range(size):
                hmap[r][c] = hmap[r][c] ** 1.5
    elif terrain_type == "canyon":
        _noise_layer(4, 0.35)
        _noise_layer(8, 0.2)
        _noise_layer(16, 0.1)
        # Carve canyon along center
        for r in range(size):
            for c in range(size):
                dist = abs(c - size // 2) / size
                canyon = 0.4 * max(0, 1.0 - dist * 10)
                hmap[r][c] -= canyon
                # Mesa flat tops
                if hmap[r][c] > 0.5:
                    hmap[r][c] = 0.5 + (hmap[r][c] - 0.5) * 0.3
    elif terrain_type == "islands":
        _noise_layer(5, 0.3)
        _noise_layer(10, 0.2)
        _noise_layer(20, 0.1)
        # Mostly ocean with island peaks
        for r in range(size):
            for c in range(size):
                hmap[r][c] -= 0.25
        n_islands = random.randint(5, 10)
        for _ in range(n_islands):
            ir = random.randint(size // 6, size * 5 // 6)
            ic = random.randint(size // 6, size * 5 // 6)
            rad = random.uniform(0.06, 0.15) * size
            peak = random.uniform(0.5, 0.9)
            for r in range(size):
                for c in range(size):
                    d = math.sqrt((r - ir) ** 2 + (c - ic) ** 2)
                    hmap[r][c] += peak * max(0, 1.0 - (d / rad) ** 2)
    elif terrain_type == "glacial":
        _noise_layer(3, 0.45)
        _noise_layer(7, 0.3)
        _noise_layer(14, 0.15)
        # U-shaped valley
        mid = size // 2
        for r in range(size):
            for c in range(size):
                dist = abs(c - mid) / (size * 0.5)
                valley = 0.3 * max(0, 1.0 - dist ** 2 * 4)
                hmap[r][c] -= valley
                hmap[r][c] += 0.15  # raise baseline
    elif terrain_type == "alien":
        _noise_layer(3, 0.4)
        _noise_layer(6, 0.25)
        _noise_layer(12, 0.2)
        _noise_layer(24, 0.15)
        # Weird transformations
        for r in range(size):
            for c in range(size):
                h = hmap[r][c]
                hmap[r][c] = math.sin(h * math.pi * 2) * 0.3 + h * 0.5

    # Normalize to [0, 1]
    min_h = min(hmap[r][c] for r in range(size) for c in range(size))
    max_h = max(hmap[r][c] for r in range(size) for c in range(size))
    rng = max_h - min_h if max_h > min_h else 1.0
    for r in range(size):
        for c in range(size):
            hmap[r][c] = (hmap[r][c] - min_h) / rng
    return hmap



def _flythrough_get_height(self, x: float, z: float) -> float:
    """Get interpolated terrain height at world position (x, z)."""
    hmap = self.flythrough_heightmap
    size = self.flythrough_map_size
    if not hmap:
        return 0.0
    # Wrap coordinates
    gx = x % size
    gz = z % size
    ix = int(gx)
    iz = int(gz)
    fx = gx - ix
    fz = gz - iz
    ix0 = ix % size
    ix1 = (ix + 1) % size
    iz0 = iz % size
    iz1 = (iz + 1) % size
    # Bilinear interpolation
    h00 = hmap[iz0][ix0]
    h10 = hmap[iz0][ix1]
    h01 = hmap[iz1][ix0]
    h11 = hmap[iz1][ix1]
    top = h00 * (1 - fx) + h10 * fx
    bot = h01 * (1 - fx) + h11 * fx
    return top * (1 - fz) + bot * fz



def _flythrough_init(self, preset_idx: int):
    """Initialize 3D flythrough with chosen preset."""
    name, _desc, ttype = self.FLYTHROUGH_PRESETS[preset_idx]
    self.flythrough_preset_name = name
    self.flythrough_generation = 0
    self.flythrough_running = True
    self.flythrough_time = 0.3  # start near morning
    self.flythrough_auto_time = True
    self.flythrough_time_speed = 0.002
    self.flythrough_cam_speed = 0.5
    self.flythrough_cam_pitch = -0.2
    self.flythrough_cam_yaw = 0.0
    self.flythrough_fov = 1.2

    size = 256
    self.flythrough_map_size = size
    self.flythrough_heightmap = self._flythrough_generate(size, ttype)

    # Place camera at center, above terrain
    cx, cz = size // 2, size // 2
    ch = self._flythrough_get_height(cx, cz)
    self.flythrough_cam_x = float(cx)
    self.flythrough_cam_z = float(cz)
    self.flythrough_cam_y = ch + 8.0  # altitude above terrain

    self.flythrough_menu = False
    self.flythrough_mode = True
    self._flash(f"Flythrough: {name} — WASD to fly, arrows to look")



def _flythrough_step(self):
    """Advance one frame: move camera forward along view direction."""
    spd = self.flythrough_cam_speed
    yaw = self.flythrough_cam_yaw
    pitch = self.flythrough_cam_pitch

    # Move forward in the direction the camera is facing (horizontal plane)
    dx = math.cos(yaw) * spd
    dz = math.sin(yaw) * spd

    self.flythrough_cam_x += dx
    self.flythrough_cam_z += dz

    # Ensure minimum altitude above terrain
    ground = self._flythrough_get_height(self.flythrough_cam_x, self.flythrough_cam_z)
    min_alt = ground + 2.0
    if self.flythrough_cam_y < min_alt:
        self.flythrough_cam_y = min_alt

    # Day/night cycle
    if self.flythrough_auto_time:
        self.flythrough_time = (self.flythrough_time + self.flythrough_time_speed) % 1.0

    self.flythrough_generation += 1



def _flythrough_get_sky_color(self) -> int:
    """Get color pair for sky based on time of day."""
    t = self.flythrough_time
    # 0.0=midnight, 0.25=dawn, 0.5=noon, 0.75=dusk
    if 0.2 < t < 0.3:  # dawn
        return curses.color_pair(3) | curses.A_DIM  # yellow dawn
    elif 0.3 <= t <= 0.7:  # day
        return curses.color_pair(2)  # cyan sky
    elif 0.7 < t < 0.8:  # dusk
        return curses.color_pair(1) | curses.A_DIM  # orange/red dusk
    else:  # night
        return curses.color_pair(6) | curses.A_DIM  # dark



def _flythrough_terrain_char_and_color(self, h: float, dist: float) -> tuple:
    """Get character and color for a terrain point based on height and distance."""
    t = self.flythrough_time
    is_night = t < 0.2 or t > 0.8

    # Altitude zones
    if h < 0.15:
        # Deep water
        ch = "≈" if dist < 30 else "~"
        attr = curses.color_pair(2) | curses.A_BOLD  # bright cyan
    elif h < 0.25:
        # Shallow water
        ch = "~"
        attr = curses.color_pair(2)  # cyan
    elif h < 0.3:
        # Beach/sand
        ch = "░"
        attr = curses.color_pair(3)  # yellow
    elif h < 0.5:
        # Grass/lowlands
        ch = "▒" if dist < 40 else ":"
        attr = curses.color_pair(1) | curses.A_BOLD  # bright green
    elif h < 0.65:
        # Forest
        ch = "▓" if dist < 30 else "#"
        attr = curses.color_pair(1)  # green
    elif h < 0.8:
        # Rock/mountain
        ch = "▓" if dist < 25 else "^"
        attr = curses.color_pair(6)  # gray
    elif h < 0.9:
        # High mountain
        ch = "█" if dist < 20 else "A"
        attr = curses.color_pair(6) | curses.A_BOLD  # bright gray
    else:
        # Snow caps
        ch = "█" if dist < 20 else "*"
        attr = curses.color_pair(0) | curses.A_BOLD  # bright white

    # Night dimming
    if is_night:
        attr = (attr & ~curses.A_BOLD) | curses.A_DIM

    # Distance fog
    if dist > 50:
        attr = curses.color_pair(6) | curses.A_DIM
        ch = "·" if dist < 70 else "."

    return ch, attr



def _flythrough_time_label(self) -> str:
    """Return label for current time of day."""
    t = self.flythrough_time
    hour = int(t * 24) % 24
    minute = int((t * 24 - hour) * 60) % 60
    if 0.2 < t < 0.3:
        phase = "Dawn"
    elif 0.3 <= t < 0.45:
        phase = "Morning"
    elif 0.45 <= t < 0.55:
        phase = "Noon"
    elif 0.55 <= t < 0.7:
        phase = "Afternoon"
    elif 0.7 <= t < 0.8:
        phase = "Dusk"
    else:
        phase = "Night"
    return f"{hour:02d}:{minute:02d} ({phase})"



def _handle_flythrough_menu_key(self, key: int) -> bool:
    """Handle input in flythrough preset menu."""
    n = len(self.FLYTHROUGH_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.flythrough_menu_sel = (self.flythrough_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.flythrough_menu_sel = (self.flythrough_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._flythrough_init(self.flythrough_menu_sel)
    elif key in (ord("q"), 27):
        self.flythrough_menu = False
        self._flash("Flythrough cancelled")
    return True



def _handle_flythrough_key(self, key: int) -> bool:
    """Handle input in active flythrough simulation."""
    cam_turn = 0.08  # radians per keypress
    alt_step = 1.0

    if key == ord(" "):
        self.flythrough_running = not self.flythrough_running
    # Camera orientation — arrow keys
    elif key == curses.KEY_LEFT:
        self.flythrough_cam_yaw -= cam_turn
    elif key == curses.KEY_RIGHT:
        self.flythrough_cam_yaw += cam_turn
    elif key == curses.KEY_UP:
        self.flythrough_cam_pitch = max(-1.2, self.flythrough_cam_pitch - cam_turn)
    elif key == curses.KEY_DOWN:
        self.flythrough_cam_pitch = min(0.6, self.flythrough_cam_pitch + cam_turn)
    # WASD movement
    elif key == ord("w"):
        yaw = self.flythrough_cam_yaw
        self.flythrough_cam_x += math.cos(yaw) * 2.0
        self.flythrough_cam_z += math.sin(yaw) * 2.0
    elif key == ord("s"):
        yaw = self.flythrough_cam_yaw
        self.flythrough_cam_x -= math.cos(yaw) * 2.0
        self.flythrough_cam_z -= math.sin(yaw) * 2.0
    elif key == ord("a"):
        yaw = self.flythrough_cam_yaw - math.pi / 2
        self.flythrough_cam_x += math.cos(yaw) * 2.0
        self.flythrough_cam_z += math.sin(yaw) * 2.0
    elif key == ord("d"):
        yaw = self.flythrough_cam_yaw + math.pi / 2
        self.flythrough_cam_x += math.cos(yaw) * 2.0
        self.flythrough_cam_z += math.sin(yaw) * 2.0
    # Altitude
    elif key == ord("e"):
        self.flythrough_cam_y += alt_step
    elif key == ord("c"):
        ground = self._flythrough_get_height(self.flythrough_cam_x, self.flythrough_cam_z)
        self.flythrough_cam_y = max(ground + 2.0, self.flythrough_cam_y - alt_step)
    # Speed
    elif key == ord("+") or key == ord("="):
        self.flythrough_cam_speed = min(5.0, self.flythrough_cam_speed + 0.1)
        self._flash(f"Speed: {self.flythrough_cam_speed:.1f}")
    elif key == ord("-"):
        self.flythrough_cam_speed = max(0.1, self.flythrough_cam_speed - 0.1)
        self._flash(f"Speed: {self.flythrough_cam_speed:.1f}")
    # Day/night
    elif key == ord("t"):
        self.flythrough_auto_time = not self.flythrough_auto_time
        self._flash(f"Auto time: {'ON' if self.flythrough_auto_time else 'OFF'}")
    elif key == ord("T"):
        self.flythrough_time = (self.flythrough_time + 0.05) % 1.0
    # FOV
    elif key == ord("f"):
        self.flythrough_fov = min(2.0, self.flythrough_fov + 0.1)
        self._flash(f"FOV: {math.degrees(self.flythrough_fov):.0f}°")
    elif key == ord("F"):
        self.flythrough_fov = max(0.5, self.flythrough_fov - 0.1)
        self._flash(f"FOV: {math.degrees(self.flythrough_fov):.0f}°")
    # Reset
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.FLYTHROUGH_PRESETS)
                    if p[0] == self.flythrough_preset_name), 0)
        self._flythrough_init(idx)
    elif key in (ord("R"), ord("m")):
        self.flythrough_mode = False
        self.flythrough_running = False
        self.flythrough_menu = True
        self.flythrough_menu_sel = 0
    elif key in (ord("q"), 27):
        self._exit_flythrough_mode()
    else:
        return True
    return True



def _draw_flythrough_menu(self, max_y: int, max_x: int):
    """Draw the flythrough preset selection menu."""
    self.stdscr.erase()
    title = "── 3D Terrain Flythrough ── Select Landscape ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "First-person 3D perspective flight over procedural terrain"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc, _ttype) in enumerate(self.FLYTHROUGH_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<24s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.flythrough_menu_sel:
            attr = curses.color_pair(3) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_flythrough(self, max_y: int, max_x: int):
    """Render 3D first-person terrain flythrough using perspective projection."""
    self.stdscr.erase()

    view_h = max_y - 3  # rows for 3D viewport
    view_w = max_x - 1  # columns for 3D viewport
    if view_h < 5 or view_w < 10:
        return

    cam_x = self.flythrough_cam_x
    cam_y = self.flythrough_cam_y
    cam_z = self.flythrough_cam_z
    yaw = self.flythrough_cam_yaw
    pitch = self.flythrough_cam_pitch
    fov = self.flythrough_fov
    t = self.flythrough_time

    # Sky color based on time
    sky_attr = self._flythrough_get_sky_color()

    # Determine horizon position based on pitch
    # pitch=0 means horizon at center, negative pitch (looking down) raises horizon
    horizon_row = int(view_h * 0.4 - pitch * view_h * 0.5)
    horizon_row = max(0, min(view_h - 1, horizon_row))

    # Draw sky above horizon
    is_night = t < 0.2 or t > 0.8
    sky_chars = " " if not is_night else "."
    for row in range(min(horizon_row, view_h)):
        sky_line = sky_chars * view_w
        # Add stars at night
        if is_night:
            line_arr = list(" " * view_w)
            for _ in range(view_w // 20):
                sx = random.randint(0, view_w - 1)
                line_arr[sx] = random.choice(["·", ".", "*", "✦"])
            sky_line = "".join(line_arr)
        try:
            self.stdscr.addstr(1 + row, 0, sky_line[:view_w], sky_attr)
        except curses.error:
            pass

    # Sun/moon indicator
    if 0.2 < t < 0.8:
        sun_col = int((t - 0.2) / 0.6 * view_w * 0.8 + view_w * 0.1)
        sun_row = max(1, horizon_row - int(math.sin((t - 0.2) / 0.6 * math.pi) * horizon_row * 0.7))
        if 0 <= sun_col < view_w and 1 <= sun_row < horizon_row:
            try:
                self.stdscr.addstr(sun_row, sun_col, "☀",
                                   curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass
    elif is_night:
        moon_col = int(view_w * 0.7)
        moon_row = max(1, 3)
        if moon_col < view_w:
            try:
                self.stdscr.addstr(moon_row, moon_col, "☾",
                                   curses.color_pair(0) | curses.A_BOLD)
            except curses.error:
                pass

    # Raycasting: for each column, cast a ray and for each row below horizon,
    # determine what terrain point it hits
    # We use a simple perspective projection approach
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)

    # Precompute column angles
    col_angles = []
    for col in range(view_w):
        angle_offset = (col / view_w - 0.5) * fov
        ray_yaw = yaw + angle_offset
        col_angles.append((math.cos(ray_yaw), math.sin(ray_yaw)))

    # For each screen row below horizon, compute the ground distance
    # Using perspective: row below horizon maps to distance
    max_dist = 80.0
    min_dist = 1.0

    for row in range(max(horizon_row, 0), view_h):
        rows_below_horizon = row - horizon_row
        if rows_below_horizon <= 0:
            continue

        # Distance calculation: farther for rows closer to horizon
        # perspective factor: screen_row proportional to 1/distance
        frac = rows_below_horizon / max(1, view_h - horizon_row)
        # Non-linear depth mapping for better perspective
        dist = min_dist + (max_dist - min_dist) * (1.0 - frac) ** 0.5
        if frac < 0.02:
            dist = max_dist

        # Adjust distance based on pitch
        pitch_factor = max(0.3, 1.0 + pitch * 0.5)
        dist *= pitch_factor

        # Height at this distance: camera_y - terrain_height determines visibility
        # The projected Y on screen depends on height difference and distance

        for col in range(0, view_w, 1):
            ray_cos, ray_sin = col_angles[min(col, len(col_angles) - 1)]
            world_x = cam_x + ray_cos * dist
            world_z = cam_z + ray_sin * dist
            terrain_h = self._flythrough_get_height(world_x, world_z)

            # Perspective height check: would this terrain be visible at this screen row?
            height_diff = cam_y - terrain_h
            if height_diff < 0:
                height_diff = 0

            ch, attr = self._flythrough_terrain_char_and_color(terrain_h, dist)

            try:
                self.stdscr.addstr(1 + row, col, ch, attr)
            except curses.error:
                pass

    # Draw crosshair at center
    cx_col = view_w // 2
    cx_row = 1 + view_h // 2
    if 0 < cx_col < view_w and 0 < cx_row < max_y - 2:
        try:
            self.stdscr.addstr(cx_row, cx_col, "+", curses.color_pair(0) | curses.A_BOLD)
        except curses.error:
            pass

    # HUD - title bar
    state = "▶ FLYING" if self.flythrough_running else "⏸ PAUSED"
    ground = self._flythrough_get_height(cam_x, cam_z)
    alt = cam_y - ground
    heading_deg = int(math.degrees(yaw)) % 360
    compass = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    compass_dir = compass[int((heading_deg + 22.5) / 45) % 8]

    title = (f" {self.flythrough_preset_name}"
             f"  |  {state}"
             f"  |  Alt: {alt:.1f}"
             f"  |  Hdg: {heading_deg}° {compass_dir}"
             f"  |  Spd: {self.flythrough_cam_speed:.1f}"
             f"  |  {self._flythrough_time_label()}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Bottom help bar
    help_text = (" WASD=move  ←→↑↓=look  e/c=alt  +/-=speed"
                 "  t=auto-time  T=advance  f/F=FOV  r=reset  q=quit")
    try:
        self.stdscr.addstr(max_y - 1, 0, help_text[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    # Mini compass
    compass_y = max_y - 2
    compass_str = f" ◈ {heading_deg:03d}° {compass_dir} | Pitch: {int(math.degrees(pitch))}°"
    try:
        self.stdscr.addstr(compass_y, 0, compass_str[:max_x - 1],
                           curses.color_pair(6))
    except curses.error:
        pass


def register(App):
    """Register flythrough mode methods on the App class."""
    App._enter_flythrough_mode = _enter_flythrough_mode
    App._exit_flythrough_mode = _exit_flythrough_mode
    App._flythrough_generate = _flythrough_generate
    App._flythrough_get_height = _flythrough_get_height
    App._flythrough_init = _flythrough_init
    App._flythrough_step = _flythrough_step
    App._flythrough_get_sky_color = _flythrough_get_sky_color
    App._flythrough_terrain_char_and_color = _flythrough_terrain_char_and_color
    App._flythrough_time_label = _flythrough_time_label
    App._handle_flythrough_menu_key = _handle_flythrough_menu_key
    App._handle_flythrough_key = _handle_flythrough_key
    App._draw_flythrough_menu = _draw_flythrough_menu
    App._draw_flythrough = _draw_flythrough

