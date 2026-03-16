"""Mode: lissajous — simulation mode for the life package."""
import curses
import math
import math as _math
import random
import time

LISSAJOUS_PRESETS = [
    ("Classic 3:2", "Classic Lissajous figure with frequency ratio 3:2", "classic_3_2"),
    ("Figure Eight", "Simple 2:1 figure-eight pattern", "figure_eight"),
    ("Star", "Five-lobed star with 5:4 ratio", "star"),
    ("Harmonograph", "Damped pendulum harmonograph with near-integer ratios", "harmonograph"),
    ("Lateral", "Two-pendulum lateral harmonograph with secondary oscillators", "lateral"),
    ("Rose Curve", "Rose-petal pattern with 7:4 ratio", "rose"),
    ("Decay Spiral", "High-frequency spiral with strong damping", "decay_spiral"),
    ("Knot", "Complex knot pattern with 5:3 ratio and light damping", "knot"),
]

LISSAJOUS_CHARS = " ·.,:;+=*#@"


def _enter_lissajous_mode(self):
    """Enter Lissajous / Harmonograph mode — show preset menu."""
    self.lissajous_mode = True
    self.lissajous_menu = True
    self.lissajous_menu_sel = 0
    self.lissajous_running = False




def _exit_lissajous_mode(self):
    """Exit Lissajous mode and clean up."""
    self.lissajous_mode = False
    self.lissajous_menu = False
    self.lissajous_running = False
    self.lissajous_trail = []
    self.lissajous_canvas = {}




def _lissajous_init(self, preset_key):
    """Initialize Lissajous mode from selected preset."""
    rows, cols = self.stdscr.getmaxyx()
    self.lissajous_rows = rows
    self.lissajous_cols = cols
    self.lissajous_menu = False
    self.lissajous_running = True
    self.lissajous_generation = 0
    self.lissajous_time = 0.0
    self.lissajous_trail = []
    self.lissajous_canvas = {}
    self.lissajous_preset_name = preset_key
    self.lissajous_dt = 0.02
    self.lissajous_speed = 2
    self.lissajous_max_trail = 4000

    # Default: no harmonograph oscillators
    self.lissajous_freq_c = 0.0
    self.lissajous_freq_d = 0.0
    self.lissajous_phase2 = 0.0
    self.lissajous_damping = 0.0
    self.lissajous_amp_x = 0.9
    self.lissajous_amp_y = 0.9

    if preset_key == "classic_3_2":
        self.lissajous_freq_a = 3.0
        self.lissajous_freq_b = 2.0
        self.lissajous_phase = _math.pi / 4
    elif preset_key == "figure_eight":
        self.lissajous_freq_a = 2.0
        self.lissajous_freq_b = 1.0
        self.lissajous_phase = _math.pi / 2
    elif preset_key == "star":
        self.lissajous_freq_a = 5.0
        self.lissajous_freq_b = 4.0
        self.lissajous_phase = _math.pi / 4
    elif preset_key == "harmonograph":
        self.lissajous_freq_a = 2.01
        self.lissajous_freq_b = 3.0
        self.lissajous_phase = _math.pi / 6
        self.lissajous_damping = 0.003
        self.lissajous_max_trail = 8000
    elif preset_key == "lateral":
        self.lissajous_freq_a = 2.0
        self.lissajous_freq_b = 3.0
        self.lissajous_phase = _math.pi / 4
        self.lissajous_freq_c = 2.005
        self.lissajous_freq_d = 3.003
        self.lissajous_phase2 = _math.pi / 3
        self.lissajous_damping = 0.002
        self.lissajous_max_trail = 10000
    elif preset_key == "rose":
        self.lissajous_freq_a = 7.0
        self.lissajous_freq_b = 4.0
        self.lissajous_phase = 0.0
    elif preset_key == "decay_spiral":
        self.lissajous_freq_a = 10.0
        self.lissajous_freq_b = 9.0
        self.lissajous_phase = _math.pi / 3
        self.lissajous_damping = 0.008
        self.lissajous_max_trail = 6000
    elif preset_key == "knot":
        self.lissajous_freq_a = 5.0
        self.lissajous_freq_b = 3.0
        self.lissajous_phase = _math.pi / 7
        self.lissajous_damping = 0.001
        self.lissajous_max_trail = 8000




def _lissajous_step(self):
    """Advance the Lissajous curve by one timestep."""
    t = self.lissajous_time
    rows = self.lissajous_rows
    cols = self.lissajous_cols

    decay = _math.exp(-self.lissajous_damping * t) if self.lissajous_damping > 0 else 1.0

    # Primary oscillators
    x = self.lissajous_amp_x * decay * _math.sin(self.lissajous_freq_a * t + self.lissajous_phase)
    y = self.lissajous_amp_y * decay * _math.sin(self.lissajous_freq_b * t)

    # Secondary oscillators (harmonograph)
    if self.lissajous_freq_c != 0.0:
        x += self.lissajous_amp_x * 0.5 * decay * _math.sin(self.lissajous_freq_c * t + self.lissajous_phase2)
    if self.lissajous_freq_d != 0.0:
        y += self.lissajous_amp_y * 0.5 * decay * _math.sin(self.lissajous_freq_d * t)

    # Normalize combined amplitudes
    max_amp_x = self.lissajous_amp_x * (1.5 if self.lissajous_freq_c != 0.0 else 1.0)
    max_amp_y = self.lissajous_amp_y * (1.5 if self.lissajous_freq_d != 0.0 else 1.0)

    # Map to screen coords — use 2:1 aspect ratio correction for terminal chars
    cx = cols / 2.0
    cy = rows / 2.0
    half_w = (cols - 4) / 2.0
    half_h = (rows - 4) / 2.0

    sx = cx + (x / max_amp_x) * half_w
    sy = cy + (y / max_amp_y) * half_h

    self.lissajous_pen_x = sx
    self.lissajous_pen_y = sy

    # Add to trail
    self.lissajous_trail.append((sy, sx, 1.0))
    if len(self.lissajous_trail) > self.lissajous_max_trail:
        self.lissajous_trail.pop(0)

    # Rasterize current point to canvas with intensity accumulation
    r = int(round(sy))
    c = int(round(sx))
    if 0 <= r < rows - 1 and 0 <= c < cols:
        self.lissajous_canvas[(r, c)] = min(1.0, self.lissajous_canvas.get((r, c), 0.0) + 0.15)

    # Also fill intermediate points for smoother lines
    if len(self.lissajous_trail) >= 2:
        prev_y, prev_x, _ = self.lissajous_trail[-2]
        dy = sy - prev_y
        dx = sx - prev_x
        dist = _math.sqrt(dy * dy + dx * dx)
        if dist > 1.0:
            steps = int(dist)
            for s in range(1, steps):
                frac = s / dist
                ir = int(round(prev_y + dy * frac))
                ic = int(round(prev_x + dx * frac))
                if 0 <= ir < rows - 1 and 0 <= ic < cols:
                    self.lissajous_canvas[(ir, ic)] = min(1.0, self.lissajous_canvas.get((ir, ic), 0.0) + 0.1)

    self.lissajous_time += self.lissajous_dt
    self.lissajous_generation += 1




def _handle_lissajous_menu_key(self, key):
    """Handle input in preset menu."""
    n = len(LISSAJOUS_PRESETS)
    if key in (curses.KEY_UP, ord('k')):
        self.lissajous_menu_sel = (self.lissajous_menu_sel - 1) % n
    elif key in (curses.KEY_DOWN, ord('j')):
        self.lissajous_menu_sel = (self.lissajous_menu_sel + 1) % n
    elif key in (curses.KEY_ENTER, 10, 13):
        preset_key = LISSAJOUS_PRESETS[self.lissajous_menu_sel][2]
        self._lissajous_init(preset_key)
    elif key == ord('q'):
        self._exit_lissajous_mode()
    return True




def _handle_lissajous_key(self, key):
    """Handle input during simulation."""
    if key == ord(' '):
        self.lissajous_running = not self.lissajous_running
    elif key == ord('n'):
        self._lissajous_step()
    elif key in (ord('+'), ord('=')):
        self.lissajous_speed = min(10, self.lissajous_speed + 1)
    elif key == ord('-'):
        self.lissajous_speed = max(1, self.lissajous_speed - 1)
    elif key == ord('a'):
        self.lissajous_freq_a = round(self.lissajous_freq_a + 0.1, 2)
    elif key == ord('A'):
        self.lissajous_freq_a = max(0.1, round(self.lissajous_freq_a - 0.1, 2))
    elif key == ord('b'):
        self.lissajous_freq_b = round(self.lissajous_freq_b + 0.1, 2)
    elif key == ord('B'):
        self.lissajous_freq_b = max(0.1, round(self.lissajous_freq_b - 0.1, 2))
    elif key == ord('p'):
        self.lissajous_phase += 0.1
    elif key == ord('P'):
        self.lissajous_phase -= 0.1
    elif key == ord('d'):
        self.lissajous_damping = round(min(0.1, self.lissajous_damping + 0.001), 4)
    elif key == ord('D'):
        self.lissajous_damping = round(max(0.0, self.lissajous_damping - 0.001), 4)
    elif key == ord('c'):
        # Clear canvas and trail, restart from current params
        self.lissajous_canvas = {}
        self.lissajous_trail = []
        self.lissajous_time = 0.0
        self.lissajous_generation = 0
    elif key == ord('i'):
        self.lissajous_show_info = not self.lissajous_show_info
    elif key == ord('r'):
        self._lissajous_init(self.lissajous_preset_name)
    elif key in (ord('R'), ord('m')):
        self.lissajous_menu = True
        self.lissajous_running = False
    elif key == ord('q'):
        self._exit_lissajous_mode()
    return True




def _draw_lissajous_menu(self, max_y, max_x):
    """Draw preset selection menu."""
    self.stdscr.erase()
    rows, cols = max_y, max_x
    n = len(LISSAJOUS_PRESETS)

    # Title
    title = "╔═══ Lissajous Curve / Harmonograph ═══╗"
    if cols > len(title) + 2:
        cx = (cols - len(title)) // 2
        try:
            self.stdscr.addstr(1, cx, title, curses.A_BOLD)
        except curses.error:
            pass

    subtitle = "Select a pattern to explore"
    if cols > len(subtitle) + 2:
        try:
            self.stdscr.addstr(2, (cols - len(subtitle)) // 2, subtitle, curses.A_DIM)
        except curses.error:
            pass

    # Presets
    start_y = 4
    for idx, (name, desc, _key) in enumerate(LISSAJOUS_PRESETS):
        if start_y + idx >= rows - 6:
            break
        prefix = " ▸ " if idx == self.lissajous_menu_sel else "   "
        attr = curses.A_REVERSE if idx == self.lissajous_menu_sel else 0
        line = f"{prefix}{name:<28s}{desc}"
        try:
            self.stdscr.addstr(start_y + idx, 2, line[:cols - 4], attr)
        except curses.error:
            pass

    # Preview art
    preview_y = start_y + n + 2
    sel_key = LISSAJOUS_PRESETS[self.lissajous_menu_sel][2]
    art_lines = _lissajous_preview_art(sel_key)
    for i, line in enumerate(art_lines):
        if preview_y + i < rows - 2:
            cx = (cols - len(line)) // 2
            try:
                self.stdscr.addstr(preview_y + i, max(0, cx), line[:cols - 1], curses.A_DIM)
            except curses.error:
                pass

    # Hints
    hint = " ↑/↓=select  Enter=start  q=back"
    if rows > 2:
        try:
            self.stdscr.addstr(rows - 2, 2, hint[:cols - 4], curses.A_DIM)
        except curses.error:
            pass




def _lissajous_preview_art(preset_key):
    """Generate small ASCII art preview for a preset."""
    import math
    lines = []
    w, h = 30, 12
    canvas = {}
    fa, fb, phase, damp = 3.0, 2.0, _math.pi / 4, 0.0
    fc, fd, phase2 = 0.0, 0.0, 0.0

    if preset_key == "classic_3_2":
        fa, fb, phase = 3.0, 2.0, _math.pi / 4
    elif preset_key == "figure_eight":
        fa, fb, phase = 2.0, 1.0, _math.pi / 2
    elif preset_key == "star":
        fa, fb, phase = 5.0, 4.0, _math.pi / 4
    elif preset_key == "harmonograph":
        fa, fb, phase, damp = 2.01, 3.0, _math.pi / 6, 0.003
    elif preset_key == "lateral":
        fa, fb, phase, damp = 2.0, 3.0, _math.pi / 4, 0.002
        fc, fd, phase2 = 2.005, 3.003, _math.pi / 3
    elif preset_key == "rose":
        fa, fb, phase = 7.0, 4.0, 0.0
    elif preset_key == "decay_spiral":
        fa, fb, phase, damp = 10.0, 9.0, _math.pi / 3, 0.008
    elif preset_key == "knot":
        fa, fb, phase, damp = 5.0, 3.0, _math.pi / 7, 0.001

    for i in range(600):
        t = i * 0.04
        decay = math.exp(-damp * t) if damp > 0 else 1.0
        x = decay * math.sin(fa * t + phase)
        y = decay * math.sin(fb * t)
        if fc != 0.0:
            x += 0.5 * decay * math.sin(fc * t + phase2)
        if fd != 0.0:
            y += 0.5 * decay * math.sin(fd * t)
        max_a = 1.5 if fc != 0.0 else 1.0
        max_b = 1.5 if fd != 0.0 else 1.0
        cx = int(w / 2 + x / max_a * (w / 2 - 1))
        cy = int(h / 2 + y / max_b * (h / 2 - 1))
        cx = max(0, min(w - 1, cx))
        cy = max(0, min(h - 1, cy))
        canvas[(cy, cx)] = min(1.0, canvas.get((cy, cx), 0.0) + 0.05)

    chars = " .·:+*#"
    for r in range(h):
        row_str = ""
        for c in range(w):
            v = canvas.get((r, c), 0.0)
            idx = int(v * (len(chars) - 1))
            idx = min(len(chars) - 1, idx)
            row_str += chars[idx]
        lines.append(row_str)
    return lines




def _draw_lissajous(self, max_y, max_x):
    """Draw the Lissajous simulation."""
    self.stdscr.erase()
    rows, cols = max_y, max_x

    chars = LISSAJOUS_CHARS

    # Draw canvas
    for (r, c), intensity in self.lissajous_canvas.items():
        if 0 <= r < rows - 1 and 0 <= c < cols:
            idx = int(intensity * (len(chars) - 1))
            idx = max(0, min(len(chars) - 1, idx))
            if idx > 0:
                ch = chars[idx]
                try:
                    attr = curses.A_BOLD if intensity > 0.6 else 0
                    self.stdscr.addch(r, c, ch, attr)
                except curses.error:
                    pass

    # Draw current pen position as bright marker
    pr = int(round(self.lissajous_pen_y))
    pc = int(round(self.lissajous_pen_x))
    if 0 <= pr < rows - 1 and 0 <= pc < cols:
        try:
            self.stdscr.addch(pr, pc, '@', curses.A_BOLD)
        except curses.error:
            pass

    # Title
    title = f" Lissajous — {self.lissajous_preset_name} "
    state = "▶ RUNNING" if self.lissajous_running else "❚❚ PAUSED"
    header = f"{title}  [{state}]  gen={self.lissajous_generation}  speed={self.lissajous_speed}x"
    try:
        self.stdscr.addstr(0, 0, header[:cols - 1], curses.A_REVERSE)
    except curses.error:
        pass

    # Info overlay
    if self.lissajous_show_info:
        info_lines = [
            f"Freq A: {self.lissajous_freq_a:.2f}",
            f"Freq B: {self.lissajous_freq_b:.2f}",
            f"Phase: {self.lissajous_phase:.2f} rad",
            f"Damping: {self.lissajous_damping:.4f}",
            f"Amp X: {self.lissajous_amp_x:.2f}",
            f"Amp Y: {self.lissajous_amp_y:.2f}",
            f"Time: {self.lissajous_time:.1f}",
            f"Trail pts: {len(self.lissajous_trail)}",
        ]
        if self.lissajous_freq_c != 0.0:
            info_lines.append(f"Freq C: {self.lissajous_freq_c:.3f}")
        if self.lissajous_freq_d != 0.0:
            info_lines.append(f"Freq D: {self.lissajous_freq_d:.3f}")
        if self.lissajous_phase2 != 0.0:
            info_lines.append(f"Phase2: {self.lissajous_phase2:.2f}")
        ix = cols - 24
        iy = 2
        for line in info_lines:
            if iy < rows - 2 and ix > 0:
                try:
                    self.stdscr.addstr(iy, ix, f" {line:<21}", curses.A_DIM)
                except curses.error:
                    pass
                iy += 1

    # Hint bar
    hint = " Space=play n=step +/-=speed a/A=freqA b/B=freqB p/P=phase d/D=damping c=clear i=info r=reset R=menu q=exit"
    hint_y = rows - 1
    if 0 <= hint_y < rows:
        try:
            self.stdscr.addstr(hint_y, 0, hint[:cols - 1], curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register lissajous mode methods on the App class."""
    App._enter_lissajous_mode = _enter_lissajous_mode
    App._exit_lissajous_mode = _exit_lissajous_mode
    App._lissajous_init = _lissajous_init
    App._lissajous_step = _lissajous_step
    App._handle_lissajous_menu_key = _handle_lissajous_menu_key
    App._handle_lissajous_key = _handle_lissajous_key
    App._draw_lissajous_menu = _draw_lissajous_menu
    App._lissajous_preview_art = staticmethod(_lissajous_preview_art)
    App._draw_lissajous = _draw_lissajous

