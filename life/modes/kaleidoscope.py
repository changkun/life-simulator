"""Kaleidoscope / Symmetry Patterns — animated or hand-painted shapes mirrored across N-fold symmetry axes."""
import curses
import math
import random

KALEIDO_PRESETS = [
    ("Snowflake", "6-fold crystal symmetry with ice-blue palette", "snowflake"),
    ("Mandala", "8-fold sacred geometry patterns", "mandala"),
    ("Diamond", "4-fold diamond/square symmetry", "diamond"),
    ("Starburst", "12-fold radial burst patterns", "starburst"),
    ("Flower", "6-fold floral petal patterns", "flower"),
    ("Vortex", "8-fold spiral vortex animation", "vortex"),
    ("Hypnotic", "4-fold concentric pulsing rings", "hypnotic"),
    ("Paint Mode", "6-fold interactive painting canvas", "paint"),
]

KALEIDO_PALETTES = [
    ("Jewel Tones", [1, 2, 3, 4, 5, 6]),
    ("Ice", [4, 5, 6, 7, 5, 4]),
    ("Fire", [1, 2, 3, 2, 1, 3]),
    ("Forest", [2, 3, 6, 3, 2, 6]),
    ("Neon", [1, 4, 5, 6, 4, 1]),
    ("Monochrome", [7, 7, 7, 7, 7, 7]),
]

KALEIDO_CHARS = " ·.:;+=*#%@"

def _enter_kaleido_mode(self):
    """Enter Kaleidoscope mode and show the preset menu."""
    self.kaleido_mode = True
    self.kaleido_menu = True
    self.kaleido_menu_sel = 0
    self.kaleido_running = False


def _exit_kaleido_mode(self):
    """Exit Kaleidoscope mode and clear its state."""
    self.kaleido_mode = False
    self.kaleido_menu = False
    self.kaleido_running = False
    self.kaleido_canvas = {}
    self.kaleido_seeds = []


def _kaleido_init(self, preset_key):
    """Initialize the kaleidoscope from the selected preset."""
    rows, cols = self.stdscr.getmaxyx()
    self.kaleido_rows = rows
    self.kaleido_cols = cols
    self.kaleido_menu = False
    self.kaleido_running = True
    self.kaleido_generation = 0
    self.kaleido_time = 0.0
    self.kaleido_canvas = {}
    self.kaleido_seeds = []
    self.kaleido_preset_name = preset_key
    self.kaleido_speed = 2
    self.kaleido_show_info = False
    self.kaleido_palette_idx = 0
    self.kaleido_color_shift = 0.0
    self.kaleido_painting = False
    self.kaleido_auto_mode = True
    self.kaleido_brush_size = 1
    self.kaleido_fade = True
    self.kaleido_cursor_r = rows // 2
    self.kaleido_cursor_c = cols // 2

    if preset_key == "snowflake":
        self.kaleido_symmetry = 6
        self.kaleido_palette_idx = 1  # Ice
        self._kaleido_spawn_seeds(8, "crystal")
    elif preset_key == "mandala":
        self.kaleido_symmetry = 8
        self.kaleido_palette_idx = 0  # Jewel Tones
        self._kaleido_spawn_seeds(6, "wave")
    elif preset_key == "diamond":
        self.kaleido_symmetry = 4
        self.kaleido_palette_idx = 0
        self._kaleido_spawn_seeds(5, "line")
    elif preset_key == "starburst":
        self.kaleido_symmetry = 12
        self.kaleido_palette_idx = 4  # Neon
        self._kaleido_spawn_seeds(10, "burst")
    elif preset_key == "flower":
        self.kaleido_symmetry = 6
        self.kaleido_palette_idx = 3  # Forest
        self._kaleido_spawn_seeds(6, "petal")
    elif preset_key == "vortex":
        self.kaleido_symmetry = 8
        self.kaleido_palette_idx = 2  # Fire
        self._kaleido_spawn_seeds(8, "spiral")
    elif preset_key == "hypnotic":
        self.kaleido_symmetry = 4
        self.kaleido_palette_idx = 5  # Monochrome
        self._kaleido_spawn_seeds(4, "ring")
    elif preset_key == "paint":
        self.kaleido_symmetry = 6
        self.kaleido_palette_idx = 0
        self.kaleido_auto_mode = False
        self.kaleido_painting = True
        self.kaleido_fade = False


def _kaleido_spawn_seeds(self, count, style):
    """Spawn the procedural seeds that drive the animation."""
    self.kaleido_seeds = []
    for i in range(count):
        seed = {
            "style": style,
            "phase": random.uniform(0, 2 * math.pi),
            "speed": random.uniform(0.02, 0.08),
            "radius": random.uniform(0.15, 0.45),
            "amplitude": random.uniform(0.3, 1.0),
            "freq": random.uniform(0.5, 3.0),
            "color_offset": i,
        }
        self.kaleido_seeds.append(seed)


def _kaleido_step(self):
    """Advance the animation by one step."""
    self.kaleido_generation += 1
    self.kaleido_time += 0.05
    self.kaleido_color_shift += 0.01

    if self.kaleido_fade:
        to_remove = []
        for key, (intensity, col_idx) in self.kaleido_canvas.items():
            new_intensity = intensity - 0.04
            if new_intensity <= 0:
                to_remove.append(key)
            else:
                self.kaleido_canvas[key] = (new_intensity, col_idx)
        for key in to_remove:
            del self.kaleido_canvas[key]

    if not self.kaleido_auto_mode:
        return

    rows = self.kaleido_rows
    cols = self.kaleido_cols
    cy = rows / 2.0
    cx = cols / 2.0
    aspect = 2.0  # terminal chars are ~2x taller than wide

    for seed in self.kaleido_seeds:
        t = self.kaleido_time * seed["speed"] * 20
        phase = seed["phase"]
        r = seed["radius"]
        amp = seed["amplitude"]
        freq = seed["freq"]
        style = seed["style"]

        if style == "crystal":
            # Radial line segments
            base_angle = t * 0.3 + phase
            length = r * min(cy, cx / aspect) * (0.5 + 0.5 * math.sin(t * freq))
            for step in range(int(length)):
                frac = step / max(1, length)
                angle = base_angle + frac * 0.3 * math.sin(t * 0.5)
                pr = step
                py_off = pr * math.sin(angle)
                px_off = pr * math.cos(angle) * aspect
                intensity = amp * (1.0 - frac * 0.5)
                self._kaleido_plot_symmetric(cy + py_off, cx + px_off, intensity, seed["color_offset"])
        elif style == "wave":
            # Sinusoidal radial waves
            for angle_step in range(0, 60, 2):
                a = angle_step / 60.0 * math.pi * 2 / self.kaleido_symmetry
                for rd in range(1, int(min(cy, cx / aspect) * r)):
                    wave = amp * math.sin(rd * 0.2 * freq - t * 2 + phase)
                    if wave > 0.2:
                        py_off = rd * math.sin(a)
                        px_off = rd * math.cos(a) * aspect
                        self._kaleido_plot_symmetric(cy + py_off, cx + px_off, wave, seed["color_offset"])
        elif style == "line":
            # Rotating line
            angle = t * 0.5 + phase
            length = min(cy, cx / aspect) * r
            for step in range(int(length)):
                py_off = step * math.sin(angle)
                px_off = step * math.cos(angle) * aspect
                intensity = amp * (0.6 + 0.4 * math.sin(step * 0.3 + t))
                self._kaleido_plot_symmetric(cy + py_off, cx + px_off, intensity, seed["color_offset"])
        elif style == "burst":
            # Expanding/contracting bursts
            pulse = (1 + math.sin(t * freq + phase)) * 0.5
            max_r = min(cy, cx / aspect) * r * pulse
            for rd in range(1, max(2, int(max_r))):
                a = phase + rd * 0.15
                py_off = rd * math.sin(a)
                px_off = rd * math.cos(a) * aspect
                intensity = amp * (1.0 - rd / max(1, max_r))
                self._kaleido_plot_symmetric(cy + py_off, cx + px_off, intensity, seed["color_offset"])
        elif style == "petal":
            # Rose-curve inspired petals
            for angle_step in range(0, 120, 1):
                a = angle_step / 120.0 * math.pi * 2 / self.kaleido_symmetry
                petal_r = min(cy, cx / aspect) * r * abs(math.sin(freq * a + t * 0.5 + phase))
                if petal_r > 1:
                    py_off = petal_r * math.sin(a)
                    px_off = petal_r * math.cos(a) * aspect
                    intensity = amp * petal_r / (min(cy, cx / aspect) * r + 0.01)
                    self._kaleido_plot_symmetric(cy + py_off, cx + px_off, intensity, seed["color_offset"])
        elif style == "spiral":
            # Archimedean spiral arm
            for step in range(200):
                tt = step * 0.05
                spiral_r = tt * r * 3
                if spiral_r > min(cy, cx / aspect):
                    break
                a = tt * freq + t * 1.5 + phase
                py_off = spiral_r * math.sin(a)
                px_off = spiral_r * math.cos(a) * aspect
                intensity = amp * (1.0 - spiral_r / min(cy, cx / aspect))
                self._kaleido_plot_symmetric(cy + py_off, cx + px_off, intensity, seed["color_offset"])
        elif style == "ring":
            # Concentric pulsing rings
            for ring_idx in range(1, 8):
                ring_r = ring_idx * min(cy, cx / aspect) * r / 8
                pulse = math.sin(t * freq + ring_idx * 0.5 + phase)
                if pulse > -0.3:
                    intensity = amp * (0.3 + pulse * 0.7)
                    for angle_step in range(0, 80, 1):
                        a = angle_step / 80.0 * math.pi * 2 / self.kaleido_symmetry
                        py_off = ring_r * math.sin(a)
                        px_off = ring_r * math.cos(a) * aspect
                        self._kaleido_plot_symmetric(cy + py_off, cx + px_off, intensity, seed["color_offset"])


def _kaleido_plot_symmetric(self, y, x, intensity, color_offset):
    """Plot a point reflected across all symmetry axes."""
    rows = self.kaleido_rows
    cols = self.kaleido_cols
    cy = rows / 2.0
    cx = cols / 2.0
    n = self.kaleido_symmetry
    aspect = 2.0

    # Convert to polar relative to center
    dy = y - cy
    dx = (x - cx) / aspect
    r = math.sqrt(dy * dy + dx * dx)
    if r < 0.01:
        r = 0.01
    theta = math.atan2(dy, dx)

    for k in range(n):
        angle = theta + k * (2 * math.pi / n)
        # Also add reflection for each sector
        for reflected in (angle, -angle + 2 * k * (2 * math.pi / n) / n):
            py = int(cy + r * math.sin(reflected))
            px = int(cx + r * math.cos(reflected) * aspect)
            if 0 <= py < rows and 0 <= px < cols:
                key = (py, px)
                old = self.kaleido_canvas.get(key)
                col_idx = int((color_offset + self.kaleido_color_shift * 10) % 6)
                if old is None or intensity > old[0]:
                    self.kaleido_canvas[key] = (intensity, col_idx)


def _kaleido_paint_at(self, r, c):
    """Paint at cursor position, mirroring across all axes."""
    brush = self.kaleido_brush_size
    for dr in range(-brush + 1, brush):
        for dc in range(-brush + 1, brush):
            pr = r + dr
            pc = c + dc
            if 0 <= pr < self.kaleido_rows and 0 <= pc < self.kaleido_cols:
                intensity = 1.0 - 0.3 * math.sqrt(dr * dr + dc * dc) / max(1, brush)
                col_idx = int(self.kaleido_palette_idx)
                self._kaleido_plot_symmetric(pr, pc, max(0.3, intensity), col_idx)


def _handle_kaleido_menu_key(self, key: int) -> bool:
    """Handle keys in the preset menu."""
    if key == 27:  # ESC
        self.kaleido_mode = False
        self.kaleido_menu = False
        return True
    if key == curses.KEY_UP:
        self.kaleido_menu_sel = (self.kaleido_menu_sel - 1) % len(KALEIDO_PRESETS)
        return True
    if key == curses.KEY_DOWN:
        self.kaleido_menu_sel = (self.kaleido_menu_sel + 1) % len(KALEIDO_PRESETS)
        return True
    if key in (curses.KEY_ENTER, 10, 13):
        _name, _desc, preset_key = KALEIDO_PRESETS[self.kaleido_menu_sel]
        self._kaleido_init(preset_key)
        return True
    return False


def _handle_kaleido_key(self, key: int) -> bool:
    """Handle keys while the kaleidoscope runs."""
    if key == 27:  # ESC — back to menu
        self.kaleido_running = False
        self.kaleido_canvas = {}
        self.kaleido_seeds = []
        self.kaleido_menu = True
        self.kaleido_menu_sel = 0
        return True
    if key == ord(' '):  # Toggle pause
        self.kaleido_running = not self.kaleido_running
        return True
    if key == ord('+') or key == ord('='):
        self.kaleido_speed = min(10, self.kaleido_speed + 1)
        return True
    if key == ord('-'):
        self.kaleido_speed = max(1, self.kaleido_speed - 1)
        return True
    if key == ord('s'):  # Cycle symmetry
        options = [4, 6, 8, 12]
        idx = options.index(self.kaleido_symmetry) if self.kaleido_symmetry in options else 0
        self.kaleido_symmetry = options[(idx + 1) % len(options)]
        return True
    if key == ord('c'):  # Cycle color palette
        self.kaleido_palette_idx = (self.kaleido_palette_idx + 1) % len(KALEIDO_PALETTES)
        return True
    if key == ord('f'):  # Toggle fade
        self.kaleido_fade = not self.kaleido_fade
        return True
    if key == ord('r'):  # Reset canvas
        self.kaleido_canvas = {}
        self.kaleido_time = 0.0
        self.kaleido_generation = 0
        return True
    if key == ord('i'):  # Toggle info
        self.kaleido_show_info = not self.kaleido_show_info
        return True
    if key == ord('p'):  # Toggle paint mode
        self.kaleido_painting = not self.kaleido_painting
        return True
    if key == ord('b'):  # Cycle brush size
        self.kaleido_brush_size = (self.kaleido_brush_size % 3) + 1
        return True
    # Paint mode cursor movement
    if self.kaleido_painting:
        moved = False
        if key == curses.KEY_UP:
            self.kaleido_cursor_r = max(0, self.kaleido_cursor_r - 1)
            moved = True
        elif key == curses.KEY_DOWN:
            self.kaleido_cursor_r = min(self.kaleido_rows - 1, self.kaleido_cursor_r + 1)
            moved = True
        elif key == curses.KEY_LEFT:
            self.kaleido_cursor_c = max(0, self.kaleido_cursor_c - 1)
            moved = True
        elif key == curses.KEY_RIGHT:
            self.kaleido_cursor_c = min(self.kaleido_cols - 1, self.kaleido_cursor_c + 1)
            moved = True
        if moved:
            self._kaleido_paint_at(self.kaleido_cursor_r, self.kaleido_cursor_c)
            return True
        if key in (curses.KEY_ENTER, 10, 13):
            self._kaleido_paint_at(self.kaleido_cursor_r, self.kaleido_cursor_c)
            return True
    return True


def _draw_kaleido_menu(self, max_y: int, max_x: int):
    """Draw the preset menu."""
    self.stdscr.erase()
    title = "✦ KALEIDOSCOPE / SYMMETRY PATTERNS ✦"
    subtitle = "Select a pattern preset"

    row = max(0, max_y // 2 - len(KALEIDO_PRESETS) // 2 - 5)

    art_lines = [
        r"    *  .  *  .  *  .  *",
        r"  .  ╲ ╱ ╲ ╱ ╲ ╱  .",
        r"  *  ─ ◎ ─ ◎ ─ ◎ ─  *",
        r"  .  ╱ ╲ ╱ ╲ ╱ ╲  .",
        r"    *  .  *  .  *  .  *",
    ]
    for line in art_lines:
        if row < max_y:
            x = max(0, (max_x - len(line)) // 2)
            try:
                self.stdscr.addstr(row, x, line[:max_x - 1], curses.color_pair(6) | curses.A_BOLD)
            except curses.error:
                pass
            row += 1

    row += 1
    if row < max_y:
        x = max(0, (max_x - len(title)) // 2)
        try:
            self.stdscr.addstr(row, x, title[:max_x - 1], curses.A_BOLD | curses.color_pair(5))
        except curses.error:
            pass
        row += 1

    if row < max_y:
        x = max(0, (max_x - len(subtitle)) // 2)
        try:
            self.stdscr.addstr(row, x, subtitle[:max_x - 1], curses.color_pair(7))
        except curses.error:
            pass
        row += 2

    for idx, (name, desc, _key) in enumerate(KALEIDO_PRESETS):
        if row >= max_y:
            break
        prefix = " ▸ " if idx == self.kaleido_menu_sel else "   "
        attr = curses.A_REVERSE if idx == self.kaleido_menu_sel else 0
        label = f"{prefix}{name}"
        x = max(0, (max_x - 50) // 2)
        try:
            self.stdscr.addstr(row, x, label[:max_x - x - 1], attr | curses.A_BOLD)
        except curses.error:
            pass
        row += 1
        desc_x = x + 5
        if row < max_y and desc_x < max_x:
            try:
                self.stdscr.addstr(row, desc_x, desc[:max_x - desc_x - 1], curses.color_pair(7))
            except curses.error:
                pass
        row += 2

    row += 1
    hint = "↑/↓=select  Enter=start  Esc=back"
    if row < max_y:
        x = max(0, (max_x - len(hint)) // 2)
        try:
            self.stdscr.addstr(row, x, hint[:max_x - 1], curses.color_pair(4))
        except curses.error:
            pass


def _draw_kaleido(self, max_y: int, max_x: int):
    """Draw the canvas, paint cursor, status bar and info overlay."""
    self.stdscr.erase()

    # Track the live terminal size so resizes reach the animation.
    self.kaleido_rows = max_y
    self.kaleido_cols = max_x

    palette = KALEIDO_PALETTES[self.kaleido_palette_idx][1]

    for (r, c), val in self.kaleido_canvas.items():
        if r < 0 or r >= max_y or c < 0 or c >= max_x - 1:
            continue
        intensity, col_idx = val

        # Map intensity to character
        char_idx = min(len(KALEIDO_CHARS) - 1, max(0, int(intensity * (len(KALEIDO_CHARS) - 1))))
        ch = KALEIDO_CHARS[char_idx]
        if ch == ' ':
            continue

        # Apply color with shift
        shifted_idx = int((col_idx + self.kaleido_color_shift * 5) % len(palette))
        color = curses.color_pair(palette[shifted_idx])
        attrs = color
        if intensity > 0.8:
            attrs |= curses.A_BOLD
        try:
            self.stdscr.addstr(r, c, ch, attrs)
        except curses.error:
            pass

    if self.kaleido_painting:
        cr, cc = self.kaleido_cursor_r, self.kaleido_cursor_c
        if 0 <= cr < max_y and 0 <= cc < max_x - 1:
            try:
                self.stdscr.addstr(cr, cc, "+", curses.A_BOLD | curses.A_BLINK | curses.color_pair(3))
            except curses.error:
                pass

    # Status bar
    pal_name = KALEIDO_PALETTES[self.kaleido_palette_idx][0]
    state = "PAUSED" if not self.kaleido_running else "RUNNING"
    paint_str = " PAINT" if self.kaleido_painting else ""
    status = f" {state} | {self.kaleido_symmetry}-fold | {pal_name} | Gen {self.kaleido_generation} | Spd {self.kaleido_speed}{paint_str} "
    if max_y > 1:
        x = max(0, (max_x - len(status)) // 2)
        try:
            self.stdscr.addstr(max_y - 1, x, status[:max_x - 1], curses.A_REVERSE)
        except curses.error:
            pass

    # Info overlay
    if self.kaleido_show_info and max_y > 12:
        info_lines = [
            f"Preset: {self.kaleido_preset_name}",
            f"Symmetry: {self.kaleido_symmetry}-fold",
            f"Palette: {pal_name}",
            f"Generation: {self.kaleido_generation}",
            f"Speed: {self.kaleido_speed}",
            f"Fade: {'ON' if self.kaleido_fade else 'OFF'}",
            f"Brush: {self.kaleido_brush_size}",
            "",
            "Space=pause  s=symmetry  c=color",
            "f=fade  r=reset  i=info  b=brush",
            "+/-=speed  p=paint  Esc=menu",
            "Paint: arrows move and paint, Enter paints",
        ]
        for i, line in enumerate(info_lines):
            if i + 1 < max_y - 1 and len(line) < max_x:
                try:
                    self.stdscr.addstr(i + 1, 1, line, curses.color_pair(7))
                except curses.error:
                    pass


def register(App):
    """Register kaleido mode methods on the App class."""
    App._enter_kaleido_mode = _enter_kaleido_mode
    App._exit_kaleido_mode = _exit_kaleido_mode
    App._kaleido_init = _kaleido_init
    App._kaleido_spawn_seeds = _kaleido_spawn_seeds
    App._kaleido_step = _kaleido_step
    App._kaleido_plot_symmetric = _kaleido_plot_symmetric
    App._kaleido_paint_at = _kaleido_paint_at
    App._handle_kaleido_menu_key = _handle_kaleido_menu_key
    App._handle_kaleido_key = _handle_kaleido_key
    App._draw_kaleido_menu = _draw_kaleido_menu
    App._draw_kaleido = _draw_kaleido

