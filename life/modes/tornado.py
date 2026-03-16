"""Mode: tornado — simulation mode for the life package."""
import curses
import math
import random
import time

TORNADO_PRESETS = [
    ("EF3 Tornado", "Violent tornado with debris cloud and destruction path", "ef3"),
    ("Rope Tornado", "Thin, sinuous funnel with rapid rotation", "rope"),
    ("Outbreak", "Multiple vortices in a severe supercell storm", "outbreak"),
    ("Rain-wrapped", "Tornado hidden in heavy rain curtains", "rainwrap"),
    ("Night Storm", "Tornado at night — visible only by lightning flashes", "night"),
    ("Dust Devil", "Small, harmless whirlwind in dry conditions", "dustdevil"),
]

_TORNADO_DEBRIS_CHARS = "·∘°*×+#@%&"
_TORNADO_CLOUD_CHARS = "░▒▓█"
_TORNADO_FUNNEL_CHARS = "░▒▓█"
_TORNADO_RAIN_CHARS = "·:│║"


def _enter_tornado_mode(self):
    """Enter Tornado & Supercell Storm mode — show preset menu."""
    self.tornado_menu = True
    self.tornado_menu_sel = 0




def _exit_tornado_mode(self):
    """Exit Tornado & Supercell Storm mode."""
    self.tornado_mode = False
    self.tornado_menu = False
    self.tornado_running = False
    self.tornado_rain_particles = []
    self.tornado_debris = []
    self.tornado_lightning_segments = []
    self.tornado_destruction = []




def _tornado_init(self, preset: str):
    """Initialize tornado simulation from preset."""
    rows, cols = self.grid.rows, self.grid.cols
    self.tornado_rows = rows
    self.tornado_cols = cols
    self.tornado_time = 0.0
    self.tornado_generation = 0
    self.tornado_cloud_angle = 0.0
    self.tornado_lightning_active = False
    self.tornado_lightning_timer = 0.0
    self.tornado_lightning_flash = 0
    self.tornado_lightning_segments = []
    self.tornado_destruction = []
    self.tornado_wobble_phase = 0.0

    cx, cy = cols // 2, rows // 2
    self.tornado_vortex_x = float(cx)
    self.tornado_vortex_y = float(cy)

    if preset == "ef3":
        self.tornado_vortex_radius = 4.0
        self.tornado_vortex_max_radius = 10.0
        self.tornado_vortex_height = float(rows // 2 - 4)
        self.tornado_rotation_speed = 2.5
        self.tornado_touch_ground = True
        self.tornado_wobble_amp = 2.0
        self.tornado_storm_radius = min(30.0, cols * 0.4)
        self.tornado_max_debris = 80
        self.tornado_max_rain = 250
        self.tornado_lightning_interval = 2.5
        self.tornado_cloud_radius = min(18.0, cols * 0.35)
        self.tornado_updraft_strength = 1.5
        self.tornado_downdraft_strength = 0.7
    elif preset == "rope":
        self.tornado_vortex_radius = 1.5
        self.tornado_vortex_max_radius = 3.0
        self.tornado_vortex_height = float(rows // 2 - 3)
        self.tornado_rotation_speed = 4.0
        self.tornado_touch_ground = True
        self.tornado_wobble_amp = 3.0
        self.tornado_storm_radius = min(22.0, cols * 0.3)
        self.tornado_max_debris = 30
        self.tornado_max_rain = 150
        self.tornado_lightning_interval = 4.0
        self.tornado_cloud_radius = min(12.0, cols * 0.25)
        self.tornado_updraft_strength = 1.0
        self.tornado_downdraft_strength = 0.4
    elif preset == "outbreak":
        self.tornado_vortex_radius = 3.0
        self.tornado_vortex_max_radius = 7.0
        self.tornado_vortex_height = float(rows // 2 - 4)
        self.tornado_rotation_speed = 3.0
        self.tornado_touch_ground = True
        self.tornado_wobble_amp = 2.5
        self.tornado_storm_radius = min(35.0, cols * 0.45)
        self.tornado_max_debris = 100
        self.tornado_max_rain = 300
        self.tornado_lightning_interval = 1.5
        self.tornado_cloud_radius = min(22.0, cols * 0.4)
        self.tornado_updraft_strength = 2.0
        self.tornado_downdraft_strength = 1.0
    elif preset == "rainwrap":
        self.tornado_vortex_radius = 3.5
        self.tornado_vortex_max_radius = 8.0
        self.tornado_vortex_height = float(rows // 2 - 3)
        self.tornado_rotation_speed = 2.0
        self.tornado_touch_ground = True
        self.tornado_wobble_amp = 1.5
        self.tornado_storm_radius = min(28.0, cols * 0.4)
        self.tornado_max_debris = 40
        self.tornado_max_rain = 500
        self.tornado_lightning_interval = 3.0
        self.tornado_cloud_radius = min(16.0, cols * 0.3)
        self.tornado_updraft_strength = 1.2
        self.tornado_downdraft_strength = 0.8
    elif preset == "night":
        self.tornado_vortex_radius = 3.0
        self.tornado_vortex_max_radius = 8.0
        self.tornado_vortex_height = float(rows // 2 - 4)
        self.tornado_rotation_speed = 2.5
        self.tornado_touch_ground = True
        self.tornado_wobble_amp = 2.0
        self.tornado_storm_radius = min(28.0, cols * 0.35)
        self.tornado_max_debris = 50
        self.tornado_max_rain = 200
        self.tornado_lightning_interval = 2.0
        self.tornado_cloud_radius = min(16.0, cols * 0.3)
        self.tornado_updraft_strength = 1.3
        self.tornado_downdraft_strength = 0.6
    elif preset == "dustdevil":
        self.tornado_vortex_radius = 1.0
        self.tornado_vortex_max_radius = 2.5
        self.tornado_vortex_height = float(rows // 4)
        self.tornado_rotation_speed = 6.0
        self.tornado_touch_ground = True
        self.tornado_wobble_amp = 4.0
        self.tornado_storm_radius = min(10.0, cols * 0.15)
        self.tornado_max_debris = 40
        self.tornado_max_rain = 0
        self.tornado_lightning_interval = 999.0
        self.tornado_cloud_radius = min(6.0, cols * 0.1)
        self.tornado_updraft_strength = 0.6
        self.tornado_downdraft_strength = 0.2

    # Initialize rain particles: [x, y, vx, vy]
    self.tornado_rain_particles = []
    for _ in range(self.tornado_max_rain):
        rx = self.tornado_vortex_x + random.uniform(-self.tornado_storm_radius, self.tornado_storm_radius)
        ry = random.uniform(0, rows * 0.3)
        self.tornado_rain_particles.append([rx, ry, random.uniform(-0.3, 0.3), random.uniform(0.5, 1.5)])

    # Initialize debris: [x, y, vx, vy, char_idx, life]
    self.tornado_debris = []

    self.tornado_running = True




def _tornado_step(self):
    """Advance tornado simulation by one timestep."""
    self.tornado_generation += 1
    self.tornado_time += self.tornado_dt
    t = self.tornado_time
    rows = self.tornado_rows
    cols = self.tornado_cols

    # ── Vortex motion: slow drift + wobble ──
    self.tornado_wobble_phase += self.tornado_dt * 1.2
    drift_x = math.sin(t * 0.15) * 0.08
    drift_y = math.cos(t * 0.1) * 0.03
    wobble_x = math.sin(self.tornado_wobble_phase) * self.tornado_wobble_amp * 0.05
    self.tornado_vortex_x += drift_x + wobble_x
    self.tornado_vortex_y += drift_y

    # Keep vortex on screen
    margin = 10
    self.tornado_vortex_x = max(margin, min(cols - margin, self.tornado_vortex_x))
    self.tornado_vortex_y = max(rows * 0.3, min(rows * 0.7, self.tornado_vortex_y))

    # Pulsating vortex radius
    base_r = self.tornado_vortex_radius
    pulse = 0.3 * math.sin(t * 1.5)
    eff_radius = max(1.0, base_r + pulse)

    # ── Mesocyclone cloud rotation ──
    self.tornado_cloud_angle += self.tornado_rotation_speed * self.tornado_dt

    # ── Update rain particles ──
    vx_center = self.tornado_vortex_x
    vy_center = self.tornado_vortex_y
    for p in self.tornado_rain_particles:
        dx = p[0] - vx_center
        dy = p[1] - (rows * 0.3)
        dist = math.sqrt(dx * dx + dy * dy) + 0.1
        # Inward spiral near vortex
        if dist < self.tornado_storm_radius:
            strength = (1.0 - dist / self.tornado_storm_radius) * 0.3
            p[2] += (-dx / dist * strength + -dy / dist * 0.02)
            p[3] += 0.05
        p[0] += p[2]
        p[1] += p[3]
        # Reset rain that falls off screen
        if p[1] > rows - 2 or p[0] < 0 or p[0] >= cols:
            p[0] = vx_center + random.uniform(-self.tornado_storm_radius, self.tornado_storm_radius)
            p[1] = random.uniform(0, 3)
            p[2] = random.uniform(-0.3, 0.3)
            p[3] = random.uniform(0.5, 1.5)

    # ── Spawn and update debris ──
    ground_y = rows - 3
    if self.tornado_touch_ground and len(self.tornado_debris) < self.tornado_max_debris:
        if random.random() < 0.3:
            spawn_x = self.tornado_vortex_x + random.uniform(-eff_radius * 2, eff_radius * 2)
            self.tornado_debris.append([
                spawn_x, float(ground_y),
                random.uniform(-1.0, 1.0), random.uniform(-1.5, -0.5),
                random.randint(0, len(_TORNADO_DEBRIS_CHARS) - 1),
                random.uniform(40, 120)
            ])

    new_debris = []
    for d in self.tornado_debris:
        dx = d[0] - self.tornado_vortex_x
        dy = d[1] - (ground_y - self.tornado_vortex_height * 0.5)
        dist = math.sqrt(dx * dx + dy * dy) + 0.1
        # Rotational + inward force
        if dist < eff_radius * 4:
            f = min(1.0, eff_radius * 2 / dist)
            # Tangential (rotation)
            d[2] += (-dy / dist) * f * self.tornado_rotation_speed * 0.15
            d[3] += (dx / dist) * f * self.tornado_rotation_speed * 0.15
            # Inward pull
            d[2] -= (dx / dist) * f * 0.2
            d[3] -= (dy / dist) * f * 0.1
            # Updraft
            d[3] -= self.tornado_updraft_strength * f * 0.15
        # Gravity
        d[3] += 0.04
        # Drag
        d[2] *= 0.97
        d[3] *= 0.97
        d[0] += d[2]
        d[1] += d[3]
        d[5] -= 1.0
        # Keep on screen and alive
        if 0 <= d[0] < cols and 0 <= d[1] < rows and d[5] > 0:
            new_debris.append(d)
    self.tornado_debris = new_debris

    # ── Destruction path ──
    if self.tornado_touch_ground:
        gx = int(self.tornado_vortex_x)
        gy = ground_y
        for ox in range(int(-eff_radius), int(eff_radius) + 1):
            px = gx + ox
            if 0 <= px < cols:
                pt = (px, gy)
                if pt not in self.tornado_destruction:
                    self.tornado_destruction.append(pt)
        if len(self.tornado_destruction) > self.tornado_max_destruction:
            self.tornado_destruction = self.tornado_destruction[-self.tornado_max_destruction:]

    # ── Lightning ──
    self.tornado_lightning_timer += self.tornado_dt
    if self.tornado_lightning_flash > 0:
        self.tornado_lightning_flash -= 1
    if self.tornado_lightning_timer >= self.tornado_lightning_interval:
        self.tornado_lightning_timer = 0.0
        if random.random() < 0.7:
            self.tornado_lightning_active = True
            self.tornado_lightning_flash = 3
            self._tornado_generate_lightning()
        else:
            self.tornado_lightning_active = False
            self.tornado_lightning_segments = []
    elif self.tornado_lightning_timer > 0.2:
        self.tornado_lightning_active = False




def _tornado_generate_lightning(self):
    """Generate a branching lightning bolt from cloud to ground."""
    rows = self.tornado_rows
    cols = self.tornado_cols
    segments = []
    # Start from a random point in the cloud layer
    sx = int(self.tornado_vortex_x + random.uniform(-self.tornado_cloud_radius * 0.5, self.tornado_cloud_radius * 0.5))
    sy = 3
    cx, cy = sx, sy
    ground = rows - 3
    while cy < ground:
        nx = cx + random.randint(-2, 2)
        ny = cy + random.randint(1, 3)
        nx = max(1, min(cols - 2, nx))
        ny = min(ground, ny)
        segments.append((cx, cy, nx, ny))
        cx, cy = nx, ny
        # Branch with small probability
        if random.random() < 0.2 and len(segments) < 30:
            bx = cx + random.randint(-3, 3)
            by = cy + random.randint(2, 5)
            bx = max(1, min(cols - 2, bx))
            by = min(ground, by)
            segments.append((cx, cy, bx, by))
    self.tornado_lightning_segments = segments




def _handle_tornado_menu_key(self, key: int) -> bool:
    """Handle keys in the tornado preset menu."""
    n = len(TORNADO_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.tornado_menu_sel = (self.tornado_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.tornado_menu_sel = (self.tornado_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.tornado_menu = False
        self.tornado_mode = False
        self._exit_tornado_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = TORNADO_PRESETS[self.tornado_menu_sel]
        self.tornado_preset_name = preset[2]
        self._tornado_init(preset[2])
        self.tornado_menu = False
        self.tornado_mode = True
        self.tornado_running = True
    else:
        return True
    return True




def _handle_tornado_key(self, key: int) -> bool:
    """Handle keys during tornado simulation."""
    if key in (27, ord('q')):
        self._exit_tornado_mode()
        return True
    elif key == ord(' '):
        self.tornado_running = not self.tornado_running
    elif key in (ord('n'), ord('.')):
        self._tornado_step()
    elif key == ord('r'):
        self._tornado_init(self.tornado_preset_name)
    elif key in (ord('R'), ord('m')):
        self.tornado_menu = True
        self.tornado_running = False
    elif key == ord('+'):
        self.tornado_speed = min(10, self.tornado_speed + 1)
    elif key == ord('-'):
        self.tornado_speed = max(1, self.tornado_speed - 1)
    elif key == ord('i'):
        self.tornado_show_info = not self.tornado_show_info
    elif key == ord('l'):
        # Force a lightning strike
        self.tornado_lightning_active = True
        self.tornado_lightning_flash = 3
        self._tornado_generate_lightning()
    else:
        return True
    return True




def _draw_tornado_menu(self, max_y: int, max_x: int):
    """Draw the tornado preset selection menu."""
    self.stdscr.erase()
    title = "── Tornado & Supercell Storm ──"
    if max_x > len(title) + 2:
        self.stdscr.addstr(1, (max_x - len(title)) // 2, title, curses.A_BOLD)

    subtitle = "Rotating supercell thunderstorm with descending tornado vortex"
    if max_y > 3 and max_x > len(subtitle) + 2:
        self.stdscr.addstr(2, (max_x - len(subtitle)) // 2, subtitle, curses.A_DIM)

    # ASCII art tornado
    art = [
        "        ░▒▓████████▓▒░",
        "       ░▒▓██████████▓▒░",
        "         ▒▓████████▓▒",
        "          ▒▓██████▓▒",
        "           ░▓████▓░",
        "            ▒████▒",
        "             ▓██▓",
        "              ██",
        "              ▓▒",
        "              ░·",
        "         ·∘°*×+#@%&·∘°",
    ]
    art_start = 4
    for i, line in enumerate(art):
        y = art_start + i
        if y >= max_y - len(TORNADO_PRESETS) - 6:
            break
        x = (max_x - len(line)) // 2
        if x > 0 and y < max_y:
            try:
                self.stdscr.addstr(y, x, line, curses.A_DIM)
            except curses.error:
                pass

    menu_y = max(art_start + len(art) + 1, max_y // 2 - len(TORNADO_PRESETS) // 2)
    header = "Select a storm scenario:"
    if menu_y - 1 > 0 and max_x > len(header) + 4:
        try:
            self.stdscr.addstr(menu_y - 1, 3, header, curses.A_BOLD)
        except curses.error:
            pass

    for i, (name, desc, _key) in enumerate(TORNADO_PRESETS):
        y = menu_y + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.tornado_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.tornado_menu_sel else 0
        line = f"{marker}{name:<24s} {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    footer = " ↑↓=select  Enter=start  q=back "
    try:
        self.stdscr.addstr(max_y - 1, 0, footer[:max_x - 1], curses.A_DIM | curses.A_REVERSE)
    except curses.error:
        pass




def _draw_tornado(self, max_y: int, max_x: int):
    """Draw the Tornado & Supercell Storm simulation."""
    self.stdscr.erase()
    rows = min(max_y, self.tornado_rows)
    cols = min(max_x, self.tornado_cols)
    if rows < 10 or cols < 20:
        try:
            self.stdscr.addstr(0, 0, "Terminal too small")
        except curses.error:
            pass
        return

    t = self.tornado_time
    vx = self.tornado_vortex_x
    ground_y = rows - 3
    is_night = (self.tornado_preset_name == "night")
    is_dustdevil = (self.tornado_preset_name == "dustdevil")
    flash = self.tornado_lightning_flash > 0

    # ── Background: sky gradient ──
    cloud_top = 4
    for y in range(0, min(cloud_top, rows)):
        for x in range(cols):
            try:
                if is_night and not flash:
                    self.stdscr.addch(y, x, ' ')
                else:
                    # Cloud layer
                    dx = x - vx
                    dy = y - 1
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < self.tornado_cloud_radius:
                        # Rotating cloud texture
                        angle = math.atan2(dy, dx) + self.tornado_cloud_angle
                        noise = math.sin(angle * 3 + dist * 0.5) * 0.5 + 0.5
                        ci = min(3, int(noise * 4))
                        ch = _TORNADO_CLOUD_CHARS[ci]
                        color = curses.color_pair(5) if flash else curses.A_DIM
                        self.stdscr.addch(y, x, ch, color)
                    elif not is_night:
                        self.stdscr.addch(y, x, '░', curses.A_DIM)
            except curses.error:
                pass

    # ── Mesocyclone rotation indicator at cloud base ──
    cloud_base_y = cloud_top
    if cloud_base_y < rows:
        for angle_offset in range(12):
            a = self.tornado_cloud_angle + angle_offset * math.pi / 6
            r = self.tornado_cloud_radius * 0.6
            cx = int(vx + math.cos(a) * r)
            cy = int(cloud_base_y + math.sin(a) * r * 0.3)
            if 0 <= cx < cols and 0 <= cy < rows:
                spiral_char = "~≈≋"[angle_offset % 3]
                try:
                    attr = curses.color_pair(5) if flash else curses.A_DIM
                    self.stdscr.addch(cy, cx, spiral_char, attr)
                except curses.error:
                    pass

    # ── Funnel cloud / tornado vortex ──
    funnel_top = cloud_top + 1
    funnel_bot = ground_y if self.tornado_touch_ground else int(ground_y - self.tornado_vortex_height * 0.3)
    top_radius = self.tornado_vortex_max_radius
    bot_radius = max(0.5, self.tornado_vortex_radius * 0.3) if self.tornado_touch_ground else self.tornado_vortex_radius

    for y in range(funnel_top, min(funnel_bot + 1, rows)):
        frac = (y - funnel_top) / max(1, funnel_bot - funnel_top)
        # Radius narrows from top to bottom
        r = top_radius * (1 - frac) + bot_radius * frac
        # Wobble
        wobble = math.sin(self.tornado_wobble_phase + frac * 3) * self.tornado_wobble_amp * frac
        center_x = vx + wobble

        for dx_i in range(int(-r - 1), int(r + 2)):
            px = int(center_x + dx_i)
            if 0 <= px < cols and 0 <= y < rows:
                d = abs(dx_i) / max(0.5, r)
                if d <= 1.0:
                    # Density based on distance from edge
                    rotation_phase = math.sin(self.tornado_cloud_angle * 2 + y * 0.5 + dx_i * 0.3)
                    density = (1.0 - d * 0.7) * (0.7 + 0.3 * rotation_phase)
                    ci = min(3, max(0, int(density * 4)))
                    ch = _TORNADO_FUNNEL_CHARS[ci]
                    if is_night and not flash:
                        attr = curses.A_DIM
                    else:
                        attr = curses.color_pair(7) if d < 0.4 else curses.A_BOLD
                    try:
                        self.stdscr.addch(y, px, ch, attr)
                    except curses.error:
                        pass

    # ── Rain curtains ──
    if not is_dustdevil:
        for p in self.tornado_rain_particles:
            rx, ry = int(p[0]), int(p[1])
            if 0 <= rx < cols and cloud_top <= ry < ground_y:
                speed = abs(p[3])
                ci = min(3, int(speed * 2))
                ch = _TORNADO_RAIN_CHARS[ci]
                try:
                    if is_night and not flash:
                        self.stdscr.addch(ry, rx, ch, curses.A_DIM)
                    else:
                        self.stdscr.addch(ry, rx, ch, curses.color_pair(4))
                except curses.error:
                    pass

    # ── Debris ──
    for d in self.tornado_debris:
        dx, dy = int(d[0]), int(d[1])
        if 0 <= dx < cols and 0 <= dy < rows - 1:
            ci = int(d[4]) % len(_TORNADO_DEBRIS_CHARS)
            ch = _TORNADO_DEBRIS_CHARS[ci]
            age = d[5]
            attr = curses.A_BOLD if age > 60 else curses.A_DIM
            try:
                color = curses.color_pair(3) if age > 40 else curses.color_pair(1)
                self.stdscr.addch(dy, dx, ch, attr | color)
            except curses.error:
                pass


def register(App):
    """Register tornado mode methods on the App class."""
    App._enter_tornado_mode = _enter_tornado_mode
    App._exit_tornado_mode = _exit_tornado_mode
    App._tornado_init = _tornado_init
    App._tornado_step = _tornado_step
    App._tornado_generate_lightning = _tornado_generate_lightning
    App._handle_tornado_menu_key = _handle_tornado_menu_key
    App._handle_tornado_key = _handle_tornado_key
    App._draw_tornado_menu = _draw_tornado_menu
    App._draw_tornado = _draw_tornado

