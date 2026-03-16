"""Mode: snowfall — simulation mode for the life package."""
import curses
import math
import random
import time

SNOWFALL_PRESETS = [
    ("Gentle Snowfall", "Light, peaceful snow drifting down on a calm winter night", "gentle"),
    ("Steady Winter Storm", "Moderate snowfall with consistent wind and steady accumulation", "steady"),
    ("Heavy Blizzard", "Intense whiteout conditions with powerful wind gusts and rapid drifting", "blizzard"),
    ("Arctic Whiteout", "Extreme polar storm — near-zero visibility, fierce horizontal snow", "whiteout"),
    ("Wet Spring Snow", "Large, heavy flakes falling slowly in mild temperatures", "wet"),
    ("Mountain Squall", "Sudden intense burst of fine snow with swirling updrafts", "squall"),
]


def _enter_snowfall_mode(self):
    """Enter Snowfall & Blizzard mode — show preset menu."""
    self.snowfall_menu = True
    self.snowfall_menu_sel = 0




def _exit_snowfall_mode(self):
    """Exit Snowfall & Blizzard mode."""
    self.snowfall_mode = False
    self.snowfall_menu = False
    self.snowfall_running = False
    self.snowfall_flakes = []
    self.snowfall_accumulation = []
    self.snowfall_drift_particles = []




def _snowfall_init(self, preset: str):
    """Initialize snowfall simulation from preset."""
    rows, cols = self.grid.rows, self.grid.cols
    self.snowfall_rows = rows
    self.snowfall_cols = cols
    self.snowfall_time = 0.0
    self.snowfall_generation = 0
    self.snowfall_wind_gust_phase = random.uniform(0, math.pi * 2)
    self.snowfall_drift_particles = []

    if preset == "gentle":
        self.snowfall_density = 80
        self.snowfall_wind_speed = 0.3
        self.snowfall_wind_dir = 1.0
        self.snowfall_temperature = -3.0
        self.snowfall_visibility = 1.0
        self.snowfall_max_accumulation = float(rows // 4)
    elif preset == "steady":
        self.snowfall_density = 180
        self.snowfall_wind_speed = 1.2
        self.snowfall_wind_dir = 1.0
        self.snowfall_temperature = -8.0
        self.snowfall_visibility = 0.75
        self.snowfall_max_accumulation = float(rows // 3)
    elif preset == "blizzard":
        self.snowfall_density = 400
        self.snowfall_wind_speed = 3.5
        self.snowfall_wind_dir = 1.0
        self.snowfall_temperature = -15.0
        self.snowfall_visibility = 0.35
        self.snowfall_max_accumulation = float(rows // 2)
    elif preset == "whiteout":
        self.snowfall_density = 600
        self.snowfall_wind_speed = 5.0
        self.snowfall_wind_dir = -1.0
        self.snowfall_temperature = -25.0
        self.snowfall_visibility = 0.15
        self.snowfall_max_accumulation = float(rows // 2)
    elif preset == "wet":
        self.snowfall_density = 120
        self.snowfall_wind_speed = 0.5
        self.snowfall_wind_dir = 1.0
        self.snowfall_temperature = 1.0
        self.snowfall_visibility = 0.85
        self.snowfall_max_accumulation = float(rows // 5)
    elif preset == "squall":
        self.snowfall_density = 350
        self.snowfall_wind_speed = 2.5
        self.snowfall_wind_dir = 1.0
        self.snowfall_temperature = -10.0
        self.snowfall_visibility = 0.45
        self.snowfall_max_accumulation = float(rows // 3)

    # Initialize accumulation array (height per column)
    self.snowfall_accumulation = [0.0] * cols

    # Initialize snowflakes: [x, y, vx, vy, size, wobble_phase]
    # size: 0=small, 1=medium, 2=large
    self.snowfall_flakes = []
    size_bias = 1 if self.snowfall_temperature > -2 else 0  # warmer = larger flakes
    for _ in range(self.snowfall_density):
        size = min(2, max(0, random.randint(0, 2) + size_bias))
        fall_speed = 0.2 + size * 0.15 + random.uniform(0, 0.3)
        self.snowfall_flakes.append([
            random.uniform(0, cols),
            random.uniform(0, rows),
            self.snowfall_wind_speed * self.snowfall_wind_dir * random.uniform(0.5, 1.0),
            fall_speed,
            size,
            random.uniform(0, math.pi * 2),
        ])

    self.snowfall_dt = 0.03
    self.snowfall_running = True




def _snowfall_step(self):
    """Advance snowfall simulation by one timestep."""
    self.snowfall_generation += 1
    self.snowfall_time += self.snowfall_dt
    t = self.snowfall_time
    rows = self.snowfall_rows
    cols = self.snowfall_cols

    # ── Wind gusts: sinusoidal variation ──
    self.snowfall_wind_gust_phase += self.snowfall_dt * 0.7
    gust = math.sin(self.snowfall_wind_gust_phase) * 0.4 + \
           math.sin(self.snowfall_wind_gust_phase * 2.3 + 1.0) * 0.2
    effective_wind = self.snowfall_wind_speed * self.snowfall_wind_dir + gust

    # ── Update snowflakes ──
    ground_base = rows - 2
    for f in self.snowfall_flakes:
        # Wobble (sinusoidal lateral drift)
        f[5] += self.snowfall_dt * (2.0 + f[4] * 0.5)
        wobble = math.sin(f[5]) * (0.15 + f[4] * 0.05)

        # Update velocity with wind influence
        target_vx = effective_wind * (0.6 + f[4] * 0.1)
        f[2] += (target_vx - f[2]) * 0.1  # smooth wind response
        f[2] += wobble * 0.1

        # Gravity — larger flakes fall faster
        base_fall = 0.3 + f[4] * 0.2
        f[3] = base_fall + random.uniform(-0.05, 0.05)

        # Temperature effect: warmer = slower melt-drag, colder = crisper fall
        if self.snowfall_temperature > 0:
            f[3] *= 0.8  # wet heavy snow falls slower

        f[0] += f[2]
        f[1] += f[3]

        # Check accumulation at this column
        col_idx = int(f[0]) % cols
        accum_height = self.snowfall_accumulation[col_idx] if 0 <= col_idx < cols else 0
        ground_level = ground_base - accum_height

        # Snowflake hits ground / accumulation
        if f[1] >= ground_level:
            # Add to accumulation
            if 0 <= col_idx < cols and self.snowfall_accumulation[col_idx] < self.snowfall_max_accumulation:
                self.snowfall_accumulation[col_idx] += 0.02 + f[4] * 0.01
            # Reset flake at top
            f[0] = random.uniform(0, cols)
            if effective_wind > 0:
                f[0] = random.uniform(-cols * 0.2, cols)
            elif effective_wind < 0:
                f[0] = random.uniform(0, cols * 1.2)
            f[1] = random.uniform(-3, 0)
            f[2] = effective_wind * random.uniform(0.5, 1.0)
            f[5] = random.uniform(0, math.pi * 2)

        # Wrap horizontally
        if f[0] < -5:
            f[0] = cols + random.uniform(0, 3)
            f[1] = random.uniform(0, rows * 0.5)
        elif f[0] > cols + 5:
            f[0] = random.uniform(-3, 0)
            f[1] = random.uniform(0, rows * 0.5)

    # ── Snow drifting: wind pushes accumulation ──
    if abs(effective_wind) > 0.5:
        drift_strength = abs(effective_wind) * 0.002
        drift_dir = 1 if effective_wind > 0 else -1
        new_accum = self.snowfall_accumulation[:]
        for i in range(cols):
            ni = i + drift_dir
            if 0 <= ni < cols:
                transfer = self.snowfall_accumulation[i] * drift_strength
                new_accum[i] -= transfer
                new_accum[ni] += transfer
        # Smooth accumulation slightly
        for i in range(1, cols - 1):
            new_accum[i] = new_accum[i] * 0.98 + (new_accum[i - 1] + new_accum[i + 1]) * 0.01
        self.snowfall_accumulation = [max(0, a) for a in new_accum]

    # ── Ground drift particles ──
    if abs(effective_wind) > 1.0 and random.random() < abs(effective_wind) * 0.15:
        # Spawn drift particle from top of a snow pile
        spawn_col = random.randint(0, cols - 1)
        if self.snowfall_accumulation[spawn_col] > 0.5:
            self.snowfall_drift_particles.append([
                float(spawn_col),
                float(ground_base - self.snowfall_accumulation[spawn_col]),
                effective_wind * random.uniform(0.5, 1.5),
                random.uniform(15, 40),
            ])

    new_drift = []
    for d in self.snowfall_drift_particles:
        d[0] += d[2] * 0.3
        d[1] += random.uniform(-0.3, 0.1)  # slight upward drift
        d[3] -= 1
        if 0 <= d[0] < cols and 0 <= d[1] < rows and d[3] > 0:
            new_drift.append(d)
    self.snowfall_drift_particles = new_drift




def _handle_snowfall_menu_key(self, key: int) -> bool:
    """Handle keys in the snowfall preset menu."""
    n = len(SNOWFALL_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.snowfall_menu_sel = (self.snowfall_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.snowfall_menu_sel = (self.snowfall_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.snowfall_menu = False
        self.snowfall_mode = False
        self._exit_snowfall_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = SNOWFALL_PRESETS[self.snowfall_menu_sel]
        self.snowfall_preset_name = preset[2]
        self._snowfall_init(preset[2])
        self.snowfall_menu = False
        self.snowfall_mode = True
        self.snowfall_running = True
    else:
        return True
    return True




def _handle_snowfall_key(self, key: int) -> bool:
    """Handle keys during snowfall simulation."""
    if key in (27, ord('q')):
        self._exit_snowfall_mode()
        return True
    elif key == ord(' '):
        self.snowfall_running = not self.snowfall_running
    elif key in (ord('n'), ord('.')):
        self._snowfall_step()
    elif key == ord('r'):
        self._snowfall_init(self.snowfall_preset_name)
    elif key in (ord('R'), ord('m')):
        self.snowfall_menu = True
        self.snowfall_running = False
    elif key == ord('+'):
        self.snowfall_speed = min(10, self.snowfall_speed + 1)
    elif key == ord('-'):
        self.snowfall_speed = max(1, self.snowfall_speed - 1)
    elif key == ord('i'):
        self.snowfall_show_info = not self.snowfall_show_info
    elif key == ord('w'):
        # Increase wind speed
        self.snowfall_wind_speed = min(6.0, self.snowfall_wind_speed + 0.3)
    elif key == ord('W'):
        # Decrease wind speed
        self.snowfall_wind_speed = max(0.0, self.snowfall_wind_speed - 0.3)
    elif key == ord('d'):
        # Flip wind direction
        self.snowfall_wind_dir *= -1
    elif key == ord('f'):
        # Increase snowfall density
        new_density = min(800, self.snowfall_density + 40)
        diff = new_density - self.snowfall_density
        cols = self.snowfall_cols
        rows = self.snowfall_rows
        for _ in range(diff):
            size = random.randint(0, 2)
            self.snowfall_flakes.append([
                random.uniform(0, cols),
                random.uniform(0, rows * 0.3),
                self.snowfall_wind_speed * self.snowfall_wind_dir * random.uniform(0.5, 1.0),
                0.2 + size * 0.15,
                size,
                random.uniform(0, math.pi * 2),
            ])
        self.snowfall_density = new_density
    elif key == ord('F'):
        # Decrease snowfall density
        new_density = max(20, self.snowfall_density - 40)
        self.snowfall_density = new_density
        if len(self.snowfall_flakes) > new_density:
            self.snowfall_flakes = self.snowfall_flakes[:new_density]
    elif key == ord('t'):
        # Warmer
        self.snowfall_temperature = min(3.0, self.snowfall_temperature + 1.0)
    elif key == ord('T'):
        # Colder
        self.snowfall_temperature = max(-30.0, self.snowfall_temperature - 1.0)
    else:
        return True
    return True




def _draw_snowfall_menu(self, max_y: int, max_x: int):
    """Draw the snowfall preset selection menu."""
    self.stdscr.erase()
    title = "── Snowfall & Blizzard ──"
    if max_x > len(title) + 2:
        self.stdscr.addstr(1, (max_x - len(title)) // 2, title, curses.A_BOLD)

    subtitle = "Realistic snowfall with wind, accumulation & blizzard dynamics"
    if max_y > 3 and max_x > len(subtitle) + 2:
        self.stdscr.addstr(2, (max_x - len(subtitle)) // 2, subtitle, curses.A_DIM)

    # ASCII art snowflake
    art = [
        "              *  .  *",
        "           .  *  .  *  .",
        "        *    ❄    ❅    *",
        "      .   *    ❆    *   .",
        "        ·  . * · * .  ·",
        "      *  ·  .  ❄  .  ·  *",
        "        ·  . * · * .  ·",
        "      .   *    ❆    *   .",
        "        *    ❅    ❄    *",
        "           .  *  .  *  .",
        "              *  .  *",
        "      ▁▂▃▄▅▆▅▄▃▂▁▂▃▄▅▆▅▄▃▂▁",
    ]
    art_start = 4
    for i, line in enumerate(art):
        y = art_start + i
        if y >= max_y - len(SNOWFALL_PRESETS) - 6:
            break
        x = (max_x - len(line)) // 2
        if x > 0 and y < max_y:
            try:
                self.stdscr.addstr(y, x, line, curses.A_DIM)
            except curses.error:
                pass

    menu_y = max(art_start + len(art) + 1, max_y // 2 - len(SNOWFALL_PRESETS) // 2)
    header = "Select a snow scenario:"
    if menu_y - 1 > 0 and max_x > len(header) + 4:
        try:
            self.stdscr.addstr(menu_y - 1, 3, header, curses.A_BOLD)
        except curses.error:
            pass

    for i, (name, desc, _key) in enumerate(SNOWFALL_PRESETS):
        y = menu_y + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.snowfall_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.snowfall_menu_sel else 0
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




def _draw_snowfall(self, max_y: int, max_x: int):
    """Draw the Snowfall & Blizzard simulation."""
    self.stdscr.erase()
    rows = min(max_y, self.snowfall_rows)
    cols = min(max_x, self.snowfall_cols)
    if rows < 10 or cols < 20:
        try:
            self.stdscr.addstr(0, 0, "Terminal too small")
        except curses.error:
            pass
        return

    t = self.snowfall_time
    ground_base = rows - 2
    vis = self.snowfall_visibility

    _SNOWFLAKE_CHARS_SMALL = "..,:;'"
    _SNOWFLAKE_CHARS_MED = "o*+~^%&"
    _SNOWFLAKE_CHARS_LARGE = "*#@OQ0"
    _SNOW_GROUND_CHARS = "_.=-~+#@"

    try:
        has_color = curses.has_colors()
    except curses.error:
        has_color = False

    # ── Draw snowflakes ──
    for f in self.snowfall_flakes:
        sx = int(f[0])
        sy = int(f[1])
        if 0 <= sy < rows - 1 and 0 <= sx < cols - 1:
            size = int(f[4])
            wobble_phase = f[5]
            try:
                if size == 0:
                    ci = int(wobble_phase * 2) % len(_SNOWFLAKE_CHARS_SMALL)
                    ch = _SNOWFLAKE_CHARS_SMALL[ci]
                    attr = curses.A_DIM
                elif size == 1:
                    ci = int(wobble_phase * 1.5) % len(_SNOWFLAKE_CHARS_MED)
                    ch = _SNOWFLAKE_CHARS_MED[ci]
                    attr = 0
                else:
                    ci = int(wobble_phase) % len(_SNOWFLAKE_CHARS_LARGE)
                    ch = _SNOWFLAKE_CHARS_LARGE[ci]
                    attr = curses.A_BOLD
                # Visibility fade: dimmer flakes at low visibility
                if vis < 0.5 and random.random() > vis * 2:
                    attr = curses.A_DIM
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # ── Draw snow accumulation ──
    for c in range(cols):
        accum = self.snowfall_accumulation[c] if c < len(self.snowfall_accumulation) else 0
        if accum > 0.1:
            height = int(accum)
            for h in range(height + 1):
                y = ground_base - h
                if 0 <= y < rows - 1 and 0 <= c < cols - 1:
                    ci = min(h, len(_SNOW_GROUND_CHARS) - 1)
                    try:
                        self.stdscr.addstr(y, c, _SNOW_GROUND_CHARS[ci], curses.A_BOLD)
                    except curses.error:
                        pass

    # ── Draw drift particles ──
    for d in self.snowfall_drift_particles:
        dx, dy = int(d[0]), int(d[1])
        if 0 <= dy < rows - 1 and 0 <= dx < cols - 1:
            try:
                self.stdscr.addstr(dy, dx, '~', curses.A_DIM)
            except curses.error:
                pass

    # ── Info panel ──
    if getattr(self, 'snowfall_show_info', False):
        total_accum = sum(self.snowfall_accumulation)
        info_lines = [
            f"Flakes: {len(self.snowfall_flakes)}",
            f"Wind: {self.snowfall_wind_speed:.1f} {'>' if self.snowfall_wind_dir > 0 else '<'}",
            f"Temp: {self.snowfall_temperature:.0f}C",
            f"Accum: {total_accum:.0f}",
            f"Vis: {self.snowfall_visibility:.0%}",
            f"Speed: {self.snowfall_speed}x",
        ]
        for il, line in enumerate(info_lines):
            iy = 1 + il
            if iy < rows - 2 and cols > len(line) + 4:
                try:
                    self.stdscr.addstr(iy, cols - len(line) - 3, f" {line} ", curses.A_REVERSE)
                except curses.error:
                    pass

    # ── Status bar ──
    gen_str = f"Gen {self.snowfall_generation}"
    state = "RUN" if self.snowfall_running else "PAUSED"
    status = f" {gen_str}  {state}  t={self.snowfall_time:.1f}s  spd={self.snowfall_speed}x"
    status_y = rows - 2
    try:
        self.stdscr.addstr(status_y, 0, status[:cols - 1], curses.A_REVERSE)
        pad = cols - 1 - len(status)
        if pad > 0:
            self.stdscr.addstr(status_y, len(status), " " * pad, curses.A_REVERSE)
    except curses.error:
        pass

    hint = " SPC=play n=step +/-=spd w/W=wind d=flip f/F=density t/T=temp i=info r=reset m=menu q=exit"
    if status_y + 1 < rows:
        try:
            self.stdscr.addstr(status_y + 1, 0, hint[:cols - 1], curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register snowfall mode methods on the App class."""
    App._enter_snowfall_mode = _enter_snowfall_mode
    App._exit_snowfall_mode = _exit_snowfall_mode
    App._snowfall_init = _snowfall_init
    App._snowfall_step = _snowfall_step
    App._handle_snowfall_menu_key = _handle_snowfall_menu_key
    App._handle_snowfall_key = _handle_snowfall_key
    App._draw_snowfall_menu = _draw_snowfall_menu
    App._draw_snowfall = _draw_snowfall

