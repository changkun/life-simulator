"""Mode: fourier — simulation mode for the life package."""
import curses
import math
import random
import time


def _fourier_dft(points):
    """Compute Discrete Fourier Transform on a list of (x, y) complex points.

    Returns list of (freq, amplitude, phase) sorted by amplitude descending.
    """
    N = len(points)
    if N == 0:
        return []
    coeffs = []
    for k in range(N):
        re, im = 0.0, 0.0
        for n in range(N):
            angle = 2.0 * _math.pi * k * n / N
            re += points[n][0] * _math.cos(angle) + points[n][1] * _math.sin(angle)
            im += points[n][1] * _math.cos(angle) - points[n][0] * _math.sin(angle)
        re /= N
        im /= N
        amp = _math.sqrt(re * re + im * im)
        phase = _math.atan2(im, re)
        coeffs.append((k, amp, phase, re, im))
    # Sort by amplitude descending so largest circles come first
    coeffs.sort(key=lambda c: -c[1])
    return coeffs




def _fourier_generate_preset_path(preset, cx, cy, scale):
    """Generate a list of (x,y) points for a given preset shape."""
    points = []
    steps = 128
    if preset == "circle":
        for i in range(steps):
            t = 2.0 * _math.pi * i / steps
            points.append((cx + scale * _math.cos(t), cy + scale * _math.sin(t)))
    elif preset == "square":
        side = steps // 4
        for i in range(side):
            f = i / side
            points.append((cx + scale, cy - scale + 2 * scale * f))
        for i in range(side):
            f = i / side
            points.append((cx + scale - 2 * scale * f, cy + scale))
        for i in range(side):
            f = i / side
            points.append((cx - scale, cy + scale - 2 * scale * f))
        for i in range(side):
            f = i / side
            points.append((cx - scale + 2 * scale * f, cy - scale))
    elif preset == "star":
        for i in range(steps):
            t = 2.0 * _math.pi * i / steps
            r = scale * (0.5 + 0.5 * (1.0 if (i * 10 // steps) % 2 == 0 else 0.4))
            points.append((cx + r * _math.cos(t - _math.pi / 2), cy + r * _math.sin(t - _math.pi / 2)))
    elif preset == "figure8":
        for i in range(steps):
            t = 2.0 * _math.pi * i / steps
            points.append((cx + scale * _math.sin(t), cy + scale * _math.sin(t) * _math.cos(t)))
    elif preset == "heart":
        for i in range(steps):
            t = 2.0 * _math.pi * i / steps
            hx = 16 * _math.sin(t) ** 3
            hy = -(13 * _math.cos(t) - 5 * _math.cos(2*t) - 2 * _math.cos(3*t) - _math.cos(4*t))
            points.append((cx + hx * scale / 18, cy + hy * scale / 18))
    elif preset == "spiralsquare":
        for i in range(steps):
            t = 2.0 * _math.pi * i / steps
            r = scale * (0.3 + 0.7 * abs(_math.cos(2 * t)))
            points.append((cx + r * _math.cos(t), cy + r * _math.sin(t)))
    else:
        # Default: circle
        for i in range(steps):
            t = 2.0 * _math.pi * i / steps
            points.append((cx + scale * _math.cos(t), cy + scale * _math.sin(t)))
    return points




def _enter_fourier_mode(self):
    """Enter Fourier Epicycle Drawing — show preset menu."""
    self.fourier_menu = True
    self.fourier_menu_sel = 0




def _exit_fourier_mode(self):
    """Exit Fourier Epicycle Drawing."""
    self.fourier_mode = False
    self.fourier_menu = False
    self.fourier_running = False
    self.fourier_phase = "menu"
    self.fourier_path = []
    self.fourier_coeffs = []
    self.fourier_trace = []




def _fourier_init(self, preset: str):
    """Initialize Fourier epicycle simulation from preset."""
    rows, cols = self.grid.rows, self.grid.cols
    cx = cols / 2.0
    cy = rows / 2.0
    scale = min(rows, cols) * 0.3

    self.fourier_time = 0.0
    self.fourier_trace = []
    self.fourier_show_info = True
    self.fourier_show_circles = True
    self.fourier_speed = 1
    self.fourier_preset_name = preset

    if preset == "freedraw":
        # Enter drawing phase
        self.fourier_phase = "drawing"
        self.fourier_path = []
        self.fourier_coeffs = []
        self.fourier_cursor_x = int(cx)
        self.fourier_cursor_y = int(cy)
        self.fourier_drawing = False
        self.fourier_running = False
        self.fourier_mode = True
        self.fourier_menu = False
        return

    # Generate preset path and compute DFT
    self.fourier_path = _fourier_generate_preset_path(preset, cx, cy, scale)
    self.fourier_coeffs = _fourier_dft(self.fourier_path)
    self.fourier_num_circles = len(self.fourier_coeffs)
    self.fourier_max_circles = self.fourier_num_circles
    N = len(self.fourier_path)
    self.fourier_dt = 2.0 * _math.pi / N if N > 0 else 0.01
    self.fourier_time = 0.0
    self.fourier_trace = []
    self.fourier_phase = "playing"
    self.fourier_running = True
    self.fourier_mode = True
    self.fourier_menu = False




def _fourier_start_playback(self):
    """Compute DFT from drawn path and start playback."""
    if len(self.fourier_path) < 3:
        return
    self.fourier_coeffs = _fourier_dft(self.fourier_path)
    self.fourier_num_circles = len(self.fourier_coeffs)
    self.fourier_max_circles = self.fourier_num_circles
    N = len(self.fourier_path)
    self.fourier_dt = 2.0 * _math.pi / N if N > 0 else 0.01
    self.fourier_time = 0.0
    self.fourier_trace = []
    self.fourier_phase = "playing"
    self.fourier_running = True




def _fourier_step(self):
    """Advance the epicycle animation by one time step."""
    if not self.fourier_coeffs:
        return
    N = len(self.fourier_path)
    if N == 0:
        return

    # Compute the tip position by summing epicycles
    x, y = 0.0, 0.0
    limit = min(self.fourier_num_circles, len(self.fourier_coeffs))
    for i in range(limit):
        freq, amp, phase, _re, _im = self.fourier_coeffs[i]
        angle = freq * self.fourier_time + phase
        x += amp * _math.cos(angle)
        y += amp * _math.sin(angle)

    self.fourier_trace.append((x, y))
    # Keep trace from getting too long (2 full cycles)
    max_trace = N * 2
    if len(self.fourier_trace) > max_trace:
        self.fourier_trace = self.fourier_trace[-max_trace:]

    self.fourier_time += self.fourier_dt




def _handle_fourier_menu_key(self, key: int) -> bool:
    """Handle keys in the Fourier Epicycle preset menu."""
    n = len(FOURIER_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.fourier_menu_sel = (self.fourier_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.fourier_menu_sel = (self.fourier_menu_sel - 1) % n
    elif key in (curses.KEY_ENTER, 10, 13, ord('\n')):
        preset = FOURIER_PRESETS[self.fourier_menu_sel]
        self._fourier_init(preset[2])
    elif key in (27, ord('q')):
        self.fourier_menu = False
    else:
        return True
    return True




def _handle_fourier_key(self, key: int) -> bool:
    """Handle keys during Fourier epicycle simulation."""
    if self.fourier_phase == "drawing":
        return _handle_fourier_drawing_key(self, key)

    # Playing phase
    if key in (27, ord('q')):
        self._exit_fourier_mode()
        return True
    elif key == ord(' '):
        self.fourier_running = not self.fourier_running
    elif key in (ord('n'), ord('.')):
        self._fourier_step()
    elif key == ord('r'):
        # Reset playback
        self.fourier_time = 0.0
        self.fourier_trace = []
        self.fourier_running = True
    elif key in (ord('R'), ord('m')):
        # Return to menu
        self.fourier_mode = False
        self.fourier_running = False
        self.fourier_menu = True
        self.fourier_menu_sel = 0
    elif key == ord('+') or key == ord('='):
        self.fourier_speed = min(self.fourier_speed + 1, 20)
    elif key == ord('-') or key == ord('_'):
        self.fourier_speed = max(self.fourier_speed - 1, 1)
    elif key == ord('i'):
        self.fourier_show_info = not self.fourier_show_info
    elif key == ord('c'):
        self.fourier_show_circles = not self.fourier_show_circles
    elif key == ord('['):
        # Decrease number of circles
        self.fourier_num_circles = max(1, self.fourier_num_circles - 1)
        self.fourier_trace = []
        self.fourier_time = 0.0
    elif key == ord(']'):
        # Increase number of circles
        self.fourier_num_circles = min(self.fourier_max_circles, self.fourier_num_circles + 1)
        self.fourier_trace = []
        self.fourier_time = 0.0
    else:
        return True
    return True




def _handle_fourier_drawing_key(self, key: int) -> bool:
    """Handle keys during the free-draw phase."""
    if key in (27, ord('q')):
        self._exit_fourier_mode()
        return True
    elif key in (curses.KEY_ENTER, 10, 13, ord('\n')):
        # Finish drawing, start playback
        self._fourier_start_playback()
    elif key == curses.KEY_UP or key == ord('k'):
        self.fourier_cursor_y = max(1, self.fourier_cursor_y - 1)
        if self.fourier_drawing:
            self.fourier_path.append((float(self.fourier_cursor_x), float(self.fourier_cursor_y)))
    elif key == curses.KEY_DOWN or key == ord('j'):
        self.fourier_cursor_y = min(self.grid.rows - 2, self.fourier_cursor_y + 1)
        if self.fourier_drawing:
            self.fourier_path.append((float(self.fourier_cursor_x), float(self.fourier_cursor_y)))
    elif key == curses.KEY_LEFT or key == ord('h'):
        self.fourier_cursor_x = max(1, self.fourier_cursor_x - 1)
        if self.fourier_drawing:
            self.fourier_path.append((float(self.fourier_cursor_x), float(self.fourier_cursor_y)))
    elif key == curses.KEY_RIGHT or key == ord('l'):
        self.fourier_cursor_x = min(self.grid.cols - 2, self.fourier_cursor_x + 1)
        if self.fourier_drawing:
            self.fourier_path.append((float(self.fourier_cursor_x), float(self.fourier_cursor_y)))
    elif key == ord('d'):
        # Toggle pen down/up
        self.fourier_drawing = not self.fourier_drawing
        if self.fourier_drawing:
            self.fourier_path.append((float(self.fourier_cursor_x), float(self.fourier_cursor_y)))
    elif key == ord('x'):
        # Clear drawing
        self.fourier_path = []
        self.fourier_drawing = False
    elif key in (ord('R'), ord('m')):
        self.fourier_mode = False
        self.fourier_running = False
        self.fourier_menu = True
        self.fourier_menu_sel = 0
    else:
        return True
    return True




def _draw_fourier_menu(self, max_y: int, max_x: int):
    """Draw the Fourier Epicycle preset selection menu."""
    self.stdscr.erase()
    title = "═══ Fourier Epicycle Drawing ═══"
    if max_x > len(title) + 2:
        try:
            self.stdscr.addstr(1, (max_x - len(title)) // 2, title, curses.A_BOLD)
        except curses.error:
            pass

    subtitle = "Select a shape or draw your own"
    if max_x > len(subtitle) + 2:
        try:
            self.stdscr.addstr(2, (max_x - len(subtitle)) // 2, subtitle, curses.A_DIM)
        except curses.error:
            pass

    start_y = 4
    for idx, (name, desc, _key) in enumerate(FOURIER_PRESETS):
        if start_y + idx >= max_y - 3:
            break
        marker = "▸ " if idx == self.fourier_menu_sel else "  "
        attr = curses.A_REVERSE if idx == self.fourier_menu_sel else 0
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(start_y + idx * 2, 4, line[:max_x - 6], attr)
            if max_x > 10:
                self.stdscr.addstr(start_y + idx * 2 + 1, 6, desc[:max_x - 8], curses.A_DIM)
        except curses.error:
            pass

    help_y = max_y - 2
    help_text = "↑↓ Navigate  Enter Select  q Quit"
    if help_y > 0 and max_x > len(help_text) + 2:
        try:
            self.stdscr.addstr(help_y, (max_x - len(help_text)) // 2, help_text, curses.A_DIM)
        except curses.error:
            pass




def _draw_fourier(self, max_y: int, max_x: int):
    """Draw the Fourier epicycle simulation."""
    self.stdscr.erase()

    if self.fourier_phase == "drawing":
        _draw_fourier_drawing(self, max_y, max_x)
        return

    # ── Playing phase: render epicycles and trace ──
    if not self.fourier_coeffs:
        return

    N = len(self.fourier_path)
    limit = min(self.fourier_num_circles, len(self.fourier_coeffs))

    # Compute epicycle chain for current time
    chain = []  # list of (cx, cy) center points of each circle
    x, y = 0.0, 0.0
    chain.append((x, y))
    for i in range(limit):
        freq, amp, phase, _re, _im = self.fourier_coeffs[i]
        angle = freq * self.fourier_time + phase
        x += amp * _math.cos(angle)
        y += amp * _math.sin(angle)
        chain.append((x, y))

    # Find bounding box of path + chain for auto-scaling
    all_pts = list(self.fourier_path) + list(self.fourier_trace) + chain
    if not all_pts:
        return
    min_x = min(p[0] for p in all_pts)
    max_px = max(p[0] for p in all_pts)
    min_py = min(p[1] for p in all_pts)
    max_py = max(p[1] for p in all_pts)

    range_x = max_px - min_x if max_px > min_x else 1.0
    range_y = max_py - min_py if max_py > min_py else 1.0

    # Map to screen coords with margin
    margin = 3
    scr_w = max_x - 2 * margin
    scr_h = max_y - 2 * margin - 2  # leave room for info
    if scr_w < 10 or scr_h < 5:
        return

    # Uniform scaling (chars are ~2x taller than wide)
    scale_x = scr_w / range_x if range_x > 0 else 1.0
    scale_y = scr_h / range_y if range_y > 0 else 1.0
    scale = min(scale_x, scale_y * 2.0)  # *2 accounts for char aspect ratio

    def to_screen(px, py):
        sx = int(margin + (px - min_x) * scale)
        sy = int(margin + (py - min_py) * scale / 2.0)
        return sx, sy

    # Draw original path as dim dots
    for px, py in self.fourier_path:
        sx, sy = to_screen(px, py)
        if 0 <= sy < max_y and 0 <= sx < max_x - 1:
            try:
                self.stdscr.addch(sy, sx, ord('·'), curses.A_DIM)
            except curses.error:
                pass

    # Draw reconstructed trace
    trace_chars = "░▒▓█"
    n_trace = len(self.fourier_trace)
    for idx, (px, py) in enumerate(self.fourier_trace):
        sx, sy = to_screen(px, py)
        if 0 <= sy < max_y and 0 <= sx < max_x - 1:
            # Fade: older points dimmer
            brightness = idx / max(n_trace, 1)
            ch_idx = min(int(brightness * len(trace_chars)), len(trace_chars) - 1)
            try:
                attr = curses.A_BOLD if brightness > 0.8 else 0
                self.stdscr.addch(sy, sx, ord(trace_chars[ch_idx]), attr)
            except curses.error:
                pass

    # Draw epicycle circles (if enabled)
    if self.fourier_show_circles and len(chain) > 1:
        for i in range(len(chain) - 1):
            cx_s, cy_s = to_screen(chain[i][0], chain[i][1])
            nx_s, ny_s = to_screen(chain[i + 1][0], chain[i + 1][1])
            # Draw radius line from center to next center
            _draw_line_ascii(self, cx_s, cy_s, nx_s, ny_s, max_y, max_x)
            # Draw small circle indicator at center
            if i < limit and 0 <= cy_s < max_y and 0 <= cx_s < max_x - 1:
                try:
                    self.stdscr.addch(cy_s, cx_s, ord('○'), curses.A_DIM)
                except curses.error:
                    pass

        # Mark the tip
        tip_sx, tip_sy = to_screen(chain[-1][0], chain[-1][1])
        if 0 <= tip_sy < max_y and 0 <= tip_sx < max_x - 1:
            try:
                self.stdscr.addch(tip_sy, tip_sx, ord('●'), curses.A_BOLD)
            except curses.error:
                pass

    # Info panel
    if self.fourier_show_info:
        info_y = 0
        cycle_pct = (self.fourier_time / (2.0 * _math.pi)) * 100.0 if N > 0 else 0
        info_lines = [
            f"Fourier Epicycles: {self.fourier_num_circles}/{self.fourier_max_circles} circles",
            f"Points: {N}  Trace: {len(self.fourier_trace)}  Cycle: {cycle_pct:.0f}%",
            f"Speed: {self.fourier_speed}x  {'▶ Playing' if self.fourier_running else '⏸ Paused'}",
        ]
        for il, line in enumerate(info_lines):
            if info_y + il < max_y and max_x > len(line) + 2:
                try:
                    self.stdscr.addstr(info_y + il, max_x - len(line) - 2, line, curses.A_DIM)
                except curses.error:
                    pass

    # Help bar
    help_y = max_y - 1
    help_text = "SPC Pause  [/] ±Circles  c Circles  i Info  +/- Speed  r Reset  m Menu  q Quit"
    if help_y > 0 and max_x > 10:
        try:
            self.stdscr.addstr(help_y, 1, help_text[:max_x - 3], curses.A_DIM)
        except curses.error:
            pass




def _draw_fourier_drawing(self, max_y: int, max_x: int):
    """Draw the free-draw phase UI."""
    # Draw existing path
    for px, py in self.fourier_path:
        ix, iy = int(px), int(py)
        if 0 <= iy < max_y and 0 <= ix < max_x - 1:
            try:
                self.stdscr.addch(iy, ix, ord('█'))
            except curses.error:
                pass

    # Draw cursor
    cy, cx = self.fourier_cursor_y, self.fourier_cursor_x
    if 0 <= cy < max_y and 0 <= cx < max_x - 1:
        try:
            ch = ord('╋') if self.fourier_drawing else ord('┼')
            self.stdscr.addch(cy, cx, ch, curses.A_BOLD)
        except curses.error:
            pass

    # Title and help
    title = "═══ Free Draw Mode ═══"
    if max_x > len(title) + 2:
        try:
            self.stdscr.addstr(0, (max_x - len(title)) // 2, title, curses.A_BOLD)
        except curses.error:
            pass

    status = f"Pen: {'DOWN (drawing)' if self.fourier_drawing else 'UP'}  Points: {len(self.fourier_path)}"
    if max_x > len(status) + 2:
        try:
            self.stdscr.addstr(1, (max_x - len(status)) // 2, status, curses.A_DIM)
        except curses.error:
            pass

    help_text = "Arrows/hjkl Move  d Pen↕  Enter Play  x Clear  m Menu  q Quit"
    if max_y > 2 and max_x > len(help_text) + 2:
        try:
            self.stdscr.addstr(max_y - 1, 1, help_text[:max_x - 3], curses.A_DIM)
        except curses.error:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Snowfall & Blizzard
# ═══════════════════════════════════════════════════════════════════════════════

SNOWFALL_PRESETS = [
    ("Gentle Snowfall", "Light, peaceful snow drifting down on a calm winter night", "gentle"),
    ("Steady Winter Storm", "Moderate snowfall with consistent wind and steady accumulation", "steady"),
    ("Heavy Blizzard", "Intense whiteout conditions with powerful wind gusts and rapid drifting", "blizzard"),
    ("Arctic Whiteout", "Extreme polar storm — near-zero visibility, fierce horizontal snow", "whiteout"),
    ("Wet Spring Snow", "Large, heavy flakes falling slowly in mild temperatures", "wet"),
    ("Mountain Squall", "Sudden intense burst of fine snow with swirling updrafts", "squall"),
]

_SNOWFLAKE_CHARS_SMALL = "·.,:;'"
_SNOWFLAKE_CHARS_MED = "°∘○◦*+~"
_SNOWFLAKE_CHARS_LARGE = "❄❅❆✻✼◎"
_SNOW_GROUND_CHARS = "▁▂▃▄▅▆▇█"
_SNOW_DRIFT_CHARS = "·∘°~≈"





def register(App):
    """Register fourier mode methods on the App class."""
    App._fourier_dft = _fourier_dft
    App._fourier_generate_preset_path = _fourier_generate_preset_path
    App._enter_fourier_mode = _enter_fourier_mode
    App._exit_fourier_mode = _exit_fourier_mode
    App._fourier_init = _fourier_init
    App._fourier_start_playback = _fourier_start_playback
    App._fourier_step = _fourier_step
    App._handle_fourier_menu_key = _handle_fourier_menu_key
    App._handle_fourier_key = _handle_fourier_key
    App._handle_fourier_drawing_key = _handle_fourier_drawing_key
    App._draw_fourier_menu = _draw_fourier_menu
    App._draw_fourier = _draw_fourier
    App._draw_fourier_drawing = _draw_fourier_drawing

