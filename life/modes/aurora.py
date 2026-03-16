"""Mode: aurora — simulation mode for the life package."""
import curses
import math
import random
import time

AURORA_PRESETS = [
    ("Quiet Arc", "Gentle green arc across the sky — calm geomagnetic conditions", "quiet"),
    ("Substorm Breakup", "Explosive brightening with rapid curtain movement and folds", "substorm"),
    ("Pulsating Aurora", "Rhythmic patches of light flickering on and off", "pulsating"),
    ("Coronal Mass Ejection", "Intense multi-color display from a major solar storm", "cme"),
]

_AURORA_BANDS = [
    ("N2_purple", 0.05, 0.20, 5, "░▒"),
    ("O_green",   0.15, 0.55, 2, "░▒▓█"),
    ("O_red",     0.08, 0.25, 1, "░▒"),
    ("N2_blue",   0.40, 0.70, 4, "░▒▓"),
]


def _enter_aurora_mode(self):
    """Enter Aurora Borealis mode — show preset menu."""
    self.aurora_menu = True
    self.aurora_menu_sel = 0




def _exit_aurora_mode(self):
    """Exit Aurora Borealis mode."""
    self.aurora_mode = False
    self.aurora_menu = False
    self.aurora_running = False
    self.aurora_curtains = []
    self.aurora_particles = []
    self.aurora_stars = []




def _aurora_init(self, preset: str):
    """Initialize aurora simulation from preset."""
    import math
    import random as rng

    rows, cols = self.grid.rows, self.grid.cols
    self.aurora_rows = rows
    self.aurora_cols = cols
    self.aurora_generation = 0
    self.aurora_time = 0.0
    self.aurora_show_field = False
    self.aurora_show_info = False

    # Preset-specific parameters
    if preset == "quiet":
        self.aurora_intensity = 0.5
        self.aurora_wind_strength = 0.3
        n_curtains = 3
        curtain_speed = 0.4
        fold_intensity = 0.2
    elif preset == "substorm":
        self.aurora_intensity = 1.5
        self.aurora_wind_strength = 0.8
        n_curtains = 6
        curtain_speed = 1.2
        fold_intensity = 0.8
    elif preset == "pulsating":
        self.aurora_intensity = 0.8
        self.aurora_wind_strength = 0.4
        n_curtains = 5
        curtain_speed = 0.3
        fold_intensity = 0.4
    elif preset == "cme":
        self.aurora_intensity = 2.0
        self.aurora_wind_strength = 1.2
        n_curtains = 8
        curtain_speed = 1.5
        fold_intensity = 1.0
    else:
        self.aurora_intensity = 0.7
        self.aurora_wind_strength = 0.5
        n_curtains = 4
        curtain_speed = 0.6
        fold_intensity = 0.4

    # Initialize curtains — each is a vertical band that shimmers
    self.aurora_curtains = []
    for i in range(n_curtains):
        cx = rng.uniform(0, cols)
        width = rng.uniform(cols * 0.05, cols * 0.15)
        phase = rng.uniform(0, 2 * math.pi)
        # Each curtain has a series of control points for its wave shape
        n_points = rng.randint(5, 10)
        points = []
        for j in range(n_points):
            points.append({
                "offset": rng.uniform(-width * 0.5, width * 0.5),
                "phase": rng.uniform(0, 2 * math.pi),
                "freq": rng.uniform(0.3, 1.5),
                "amp": rng.uniform(1.0, 4.0) * fold_intensity,
            })
        curtain = {
            "cx": cx,
            "width": width,
            "phase": phase,
            "speed": curtain_speed * rng.uniform(0.5, 1.5),
            "drift": rng.uniform(-0.3, 0.3),
            "brightness": rng.uniform(0.5, 1.0),
            "points": points,
            "band_idx": rng.randint(0, len(_AURORA_BANDS) - 1),
            "pulse_phase": rng.uniform(0, 2 * math.pi),
            "pulse_freq": rng.uniform(0.5, 2.0) if preset == "pulsating" else 0.0,
        }
        self.aurora_curtains.append(curtain)

    # Solar wind particles (small dots drifting downward)
    self.aurora_particles = []
    for _ in range(min(60, cols // 3)):
        self.aurora_particles.append({
            "x": rng.uniform(0, cols),
            "y": rng.uniform(-rows, 0),
            "vx": rng.uniform(-0.5, 0.5),
            "vy": rng.uniform(0.3, 1.0) * self.aurora_wind_strength,
            "life": rng.uniform(0.5, 1.0),
        })

    # Background stars
    star_chars = ['.', '·', '*', '+', '✦']
    self.aurora_stars = []
    for _ in range(min(100, rows * cols // 40)):
        sr = rng.randint(0, rows - 1)
        sc = rng.randint(0, cols - 1)
        ch = rng.choice(star_chars)
        self.aurora_stars.append((sr, sc, ch))

    self.aurora_running = True




def _aurora_step(self):
    """Advance the aurora simulation by one time step."""
    import math
    import random as rng

    self.aurora_generation += 1
    dt = 0.05
    self.aurora_time += dt
    t = self.aurora_time
    rows = self.aurora_rows
    cols = self.aurora_cols

    # Drift curtains
    for curtain in self.aurora_curtains:
        curtain["cx"] += curtain["drift"] * dt * 10
        # Wrap around
        if curtain["cx"] < -curtain["width"]:
            curtain["cx"] = cols + curtain["width"] * 0.5
        elif curtain["cx"] > cols + curtain["width"]:
            curtain["cx"] = -curtain["width"] * 0.5

    # Update solar wind particles
    for p in self.aurora_particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        # Curve toward magnetic field lines (toward horizon center)
        mid_x = cols / 2.0
        p["vx"] += (mid_x - p["x"]) * 0.0005
        p["life"] -= dt * 0.1

        # Reset particles that fall off screen or die
        if p["y"] > rows * 0.4 or p["life"] <= 0 or p["x"] < -5 or p["x"] > cols + 5:
            p["x"] = rng.uniform(0, cols)
            p["y"] = rng.uniform(-rows * 0.3, -1)
            p["vx"] = rng.uniform(-0.5, 0.5)
            p["vy"] = rng.uniform(0.3, 1.0) * self.aurora_wind_strength
            p["life"] = rng.uniform(0.5, 1.0)

    # Occasionally add intensity fluctuations (substorm)
    if rng.random() < 0.02 * self.aurora_wind_strength:
        idx = rng.randint(0, len(self.aurora_curtains) - 1)
        self.aurora_curtains[idx]["brightness"] = min(1.5, self.aurora_curtains[idx]["brightness"] + rng.uniform(0.1, 0.3))

    # Decay brightness slowly
    for curtain in self.aurora_curtains:
        curtain["brightness"] = max(0.2, curtain["brightness"] - dt * 0.05)




def _handle_aurora_menu_key(self, key: int) -> bool:
    """Handle keys in the aurora preset menu."""
    n = len(AURORA_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.aurora_menu_sel = (self.aurora_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.aurora_menu_sel = (self.aurora_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.aurora_menu = False
        self.aurora_mode = False
        self._exit_aurora_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = AURORA_PRESETS[self.aurora_menu_sel]
        self.aurora_preset_name = preset[0]
        self._aurora_init(preset[2])
        self.aurora_menu = False
        self.aurora_mode = True
        self.aurora_running = True
    else:
        return False
    return True




def _handle_aurora_key(self, key: int) -> bool:
    """Handle keys during aurora simulation."""
    if key in (27, ord('q')):
        self._exit_aurora_mode()
        return True
    elif key == ord(' '):
        self.aurora_running = not self.aurora_running
    elif key in (ord('n'), ord('.')):
        self._aurora_step()
    elif key == ord('r'):
        # Reset with same preset
        for p in AURORA_PRESETS:
            if p[0] == self.aurora_preset_name:
                self._aurora_init(p[2])
                break
    elif key in (ord('R'), ord('m')):
        self.aurora_running = False
        self.aurora_menu = True
    elif key == ord('f'):
        self.aurora_show_field = not self.aurora_show_field
    elif key == ord('i'):
        self.aurora_show_info = not self.aurora_show_info
    elif key == ord('+') or key == ord('='):
        self.aurora_intensity = min(3.0, self.aurora_intensity + 0.2)
    elif key == ord('-') or key == ord('_'):
        self.aurora_intensity = max(0.1, self.aurora_intensity - 0.2)
    elif key == ord('w'):
        self.aurora_wind_strength = min(2.0, self.aurora_wind_strength + 0.1)
    elif key == ord('s'):
        self.aurora_wind_strength = max(0.1, self.aurora_wind_strength - 0.1)
    else:
        return False
    return True




def _draw_aurora_menu(self, max_y: int, max_x: int):
    """Draw the aurora preset selection menu."""
    self.stdscr.erase()
    title = "── Aurora Borealis (Northern Lights) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Solar wind particles exciting atmospheric gases along magnetic field lines"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle, curses.A_DIM)
    except curses.error:
        pass

    y = 4
    for i, (name, desc, _key) in enumerate(AURORA_PRESETS):
        if y >= max_y - 6:
            break
        attr = curses.A_REVERSE if i == self.aurora_menu_sel else 0
        try:
            label = f"  {name:<24s} {desc}"
            self.stdscr.addstr(y, 2, label[:max_x - 4], attr)
        except curses.error:
            pass
        y += 1

    y += 1
    info_lines = [
        "Controls during simulation:",
        "  Space=play/pause  n=step  +/-=intensity  w/s=wind  f=field lines",
        "  i=info  r=reset  R=menu  q=exit",
    ]
    for line in info_lines:
        if y < max_y - 2:
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4], curses.A_DIM)
            except curses.error:
                pass
            y += 1

    try:
        footer = " ↑↓=select  Enter=start  q=back "
        self.stdscr.addstr(max_y - 1, max(0, (max_x - len(footer)) // 2), footer[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass




def _draw_aurora(self, max_y: int, max_x: int):
    """Draw the Aurora Borealis simulation."""
    import math

    self.stdscr.erase()
    rows = min(self.aurora_rows, max_y - 2)
    cols = min(self.aurora_cols, max_x)
    if rows < 5 or cols < 10:
        return

    t = self.aurora_time

    # Build display buffer
    buf = [[' '] * cols for _ in range(rows)]
    color_buf = [[0] * cols for _ in range(rows)]
    bright_buf = [[0.0] * cols for _ in range(rows)]

    # Background: dark sky gradient
    for r in range(rows):
        frac = r / max(rows - 1, 1)
        # Lower part = ground/horizon (darker)
        if frac > 0.85:
            for c in range(cols):
                buf[r][c] = '▄' if frac > 0.92 else '░'
                color_buf[r][c] = 8  # dim
        elif frac > 0.75:
            # Horizon glow
            for c in range(cols):
                if (c + int(t * 2)) % 7 == 0:
                    buf[r][c] = '·'
                    color_buf[r][c] = 2  # faint green glow at horizon

    # Background stars (only in upper sky)
    for sr, sc, ch in self.aurora_stars:
        if 0 <= sr < int(rows * 0.80) and 0 <= sc < cols:
            if buf[sr][sc] == ' ':
                # Stars twinkle
                if math.sin(t * 3.0 + sr * 0.7 + sc * 0.3) > -0.3:
                    buf[sr][sc] = ch
                    color_buf[sr][sc] = 7  # white

    # Draw magnetic field lines if enabled
    if self.aurora_show_field:
        mid_x = cols / 2.0
        for line_i in range(5):
            spread = (line_i - 2) * cols * 0.12
            for r in range(int(rows * 0.05), int(rows * 0.7)):
                frac = r / max(rows - 1, 1)
                # Parabolic field line shape converging toward poles
                x = mid_x + spread * (1.0 - frac * 1.2)
                c = int(round(x))
                if 0 <= c < cols and buf[r][c] == ' ':
                    buf[r][c] = '│'
                    color_buf[r][c] = 8

    # Draw aurora curtains
    for curtain in self.aurora_curtains:
        band = _AURORA_BANDS[curtain["band_idx"]]
        band_top = int(rows * band[1])
        band_bot = int(rows * band[2])
        band_color = band[3]
        band_chars = band[4]

        cx = curtain["cx"]
        width = curtain["width"]
        speed = curtain["speed"]
        brightness = curtain["brightness"] * self.aurora_intensity

        # Pulsating effect
        if curtain["pulse_freq"] > 0:
            pulse = 0.5 + 0.5 * math.sin(t * curtain["pulse_freq"] * 2 * math.pi + curtain["pulse_phase"])
            brightness *= pulse

        if brightness < 0.1:
            continue

        for r in range(max(0, band_top), min(rows, band_bot)):
            # Vertical intensity falloff — strongest in the middle of the band
            band_frac = (r - band_top) / max(band_bot - band_top, 1)
            vert_intensity = math.sin(band_frac * math.pi)  # peak at center

            # Compute curtain wave at this row
            wave_offset = 0.0
            for pt in curtain["points"]:
                row_frac = band_frac
                wave_offset += pt["amp"] * math.sin(
                    row_frac * pt["freq"] * 6.0 + t * speed + pt["phase"]
                )

            center = cx + wave_offset
            hw = width * 0.5 * (0.6 + 0.4 * vert_intensity)

            for c in range(max(0, int(center - hw)), min(cols, int(center + hw))):
                dist = abs(c - center) / max(hw, 0.1)
                # Gaussian-like falloff from center
                h_intensity = math.exp(-dist * dist * 2.0)
                total = h_intensity * vert_intensity * brightness

                if total > bright_buf[r][c]:
                    bright_buf[r][c] = total
                    # Select character based on intensity
                    ci = min(int(total * len(band_chars)), len(band_chars) - 1)
                    ci = max(0, ci)
                    buf[r][c] = band_chars[ci]
                    color_buf[r][c] = band_color

    # Draw solar wind particles
    for p in self.aurora_particles:
        px, py = int(round(p["x"])), int(round(p["y"]))
        if 0 <= py < rows and 0 <= px < cols:
            if p["life"] > 0.3:
                buf[py][px] = '·'
                color_buf[py][px] = 7
            else:
                buf[py][px] = '.'
                color_buf[py][px] = 8

    # Render buffer to screen
    for r in range(rows):
        line = ''.join(buf[r])
        try:
            self.stdscr.addstr(r, 0, line[:cols])
        except curses.error:
            pass
        # Apply colors
        c = 0
        while c < cols:
            cp = color_buf[r][c]
            if cp != 0:
                run = 1
                while c + run < cols and color_buf[r][c + run] == cp:
                    run += 1
                try:
                    pair = cp if cp <= 7 else 0
                    attr = curses.color_pair(pair)
                    if cp == 8:
                        attr = curses.A_DIM
                    # Brighter aurora cells get BOLD
                    if cp in (1, 2, 4, 5) and bright_buf[r][c] > 0.6:
                        attr |= curses.A_BOLD
                    self.stdscr.chgat(r, c, run, attr)
                except curses.error:
                    pass
                c += run
            else:
                c += 1

    # Info panel
    if self.aurora_show_info:
        info_lines = [
            f" Aurora Borealis — {self.aurora_preset_name} ",
            f" Intensity: {self.aurora_intensity:.1f}  Wind: {self.aurora_wind_strength:.1f}",
            f" Curtains: {len(self.aurora_curtains)}  Particles: {len(self.aurora_particles)}",
            f" O(green)@100-200km  N₂(purple)@200-300km",
            f" O(red)@200-400km  N₂(blue)@80-120km",
        ]
        iy = 1
        for il in info_lines:
            if iy < rows - 3:
                try:
                    self.stdscr.addstr(iy, 1, il[:max_x - 3], curses.A_REVERSE)
                except curses.error:
                    pass
                iy += 1

    # Status bar
    status_y = min(rows, max_y - 2)
    status = (f" Gen:{self.aurora_generation} | {self.aurora_preset_name} | "
              f"intensity={self.aurora_intensity:.1f} | wind={self.aurora_wind_strength:.1f} ")
    try:
        self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass

    # Hint bar
    hint = " Space=play n=step +/-=intensity w/s=wind f=field i=info r=reset R=menu q=exit"
    try:
        self.stdscr.addstr(status_y + 1, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass




def register(App):
    """Register aurora mode methods on the App class."""
    App._enter_aurora_mode = _enter_aurora_mode
    App._exit_aurora_mode = _exit_aurora_mode
    App._aurora_init = _aurora_init
    App._aurora_step = _aurora_step
    App._handle_aurora_menu_key = _handle_aurora_menu_key
    App._handle_aurora_key = _handle_aurora_key
    App._draw_aurora_menu = _draw_aurora_menu
    App._draw_aurora = _draw_aurora

