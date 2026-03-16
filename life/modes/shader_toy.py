"""Mode: shadertoy — simulation mode for the life package."""
import curses
import math
import random
import time


SHADERTOY_SHADE_CHARS = " .,:;=+*#%@\u2588"

SHADERTOY_PRESETS = [
    ("Plasma Waves", "Overlapping sine waves create flowing plasma"),
    ("Tunnel Zoom", "Infinite tunnel zoom with angular patterns"),
    ("Metaballs", "Soft organic blob shapes merging and splitting"),
    ("Moir\u00e9 Rings", "Interference rings creating moir\u00e9 patterns"),
    ("Fractal Flame", "Iterated function system fractal art"),
    ("Warp Grid", "Warped checkerboard grid"),
    ("Lava Lamp", "Floating blobs with smooth contours"),
    ("Matrix Rain", "Digital rain columns"),
    ("Kaleidoscope", "Mirror-symmetry kaleidoscope"),
    ("Spiral Galaxy", "Rotating spiral arms"),
]

SHADERTOY_COLOR_NAMES = ["Rainbow", "Fire", "Ocean", "Mono"]


def _shadertoy_eval(self, nx: float, ny: float, t: float) -> float:
    """Evaluate the current shader preset at normalized coords (nx, ny) and time t.
    Returns a value in [0, 1]."""
    preset = self.shadertoy_preset_idx
    a = self.shadertoy_param_a
    b = self.shadertoy_param_b
    sin = math.sin
    cos = math.cos
    sqrt = math.sqrt
    pi = math.pi

    if preset == 0:  # Plasma Waves
        v = sin(nx * 10.0 * a + t)
        v += sin((ny * 10.0 * b + t) * 0.7)
        v += sin((nx * 10.0 + ny * 10.0 + t) * 0.5)
        v += sin(sqrt(nx * nx * 100 + ny * ny * 100) * a + t)
        return (v / 4.0 + 1.0) * 0.5

    elif preset == 1:  # Tunnel Zoom
        dx = nx
        dy = ny
        r = sqrt(dx * dx + dy * dy) + 1e-6
        angle = math.atan2(dy, dx)
        v = sin(1.0 / (r * a) + t * 2.0) * cos(angle * 3.0 * b + t)
        return (v + 1.0) * 0.5

    elif preset == 2:  # Metaballs
        v = 0.0
        for i in range(5):
            cx = sin(t * (0.3 + i * 0.17) * a) * 0.5
            cy = cos(t * (0.4 + i * 0.13) * b) * 0.5
            dx = nx - cx
            dy = ny - cy
            v += 0.03 / (dx * dx + dy * dy + 0.01)
        return min(1.0, v * 0.15)

    elif preset == 3:  # Moiré Rings
        r1 = sqrt(nx * nx + ny * ny) * 20.0 * a
        ox = 0.3 * sin(t * 0.5)
        oy = 0.3 * cos(t * 0.7)
        r2 = sqrt((nx - ox) ** 2 + (ny - oy) ** 2) * 20.0 * b
        v = sin(r1 + t) + sin(r2 + t * 0.8)
        return (v / 2.0 + 1.0) * 0.5

    elif preset == 4:  # Fractal Flame
        zx, zy = nx * 2.0, ny * 2.0
        v = 0.0
        for i in range(8):
            r = sqrt(zx * zx + zy * zy)
            if r < 1e-6:
                r = 1e-6
            theta = math.atan2(zy, zx)
            zx_new = sin(theta * a + t * 0.3) * r * 0.9 + sin(t * 0.1 + i)
            zy = cos(theta * b + t * 0.2) * r * 0.9 + cos(t * 0.15 + i)
            zx = zx_new
            v += 1.0 / (1.0 + r * r)
        return min(1.0, v * 0.15)

    elif preset == 5:  # Warp Grid
        wx = nx + sin(ny * 6.0 * a + t) * 0.15
        wy = ny + sin(nx * 6.0 * b + t * 0.8) * 0.15
        gx = abs(sin(wx * pi * 8.0))
        gy = abs(sin(wy * pi * 8.0))
        v = min(gx, gy)
        return v ** 0.5

    elif preset == 6:  # Lava Lamp
        v = 0.0
        for i in range(4):
            cx = sin(t * (0.2 + i * 0.1) * a) * 0.4
            cy = sin(t * (0.15 + i * 0.12) * b + i * 1.5) * 0.6
            dx = nx - cx
            dy = ny - cy
            blob = max(0.0, 1.0 - sqrt(dx * dx + dy * dy) * 3.0)
            v += blob * blob
        return min(1.0, v)

    elif preset == 7:  # Matrix Rain
        col_idx = int((nx + 1.0) * 20.0 * a) % 13
        phase = col_idx * 0.7 + t * (1.5 + (col_idx % 5) * 0.3) * b
        drop = (sin(phase) + 1.0) * 0.5
        y_pos = ((ny + 1.0) * 0.5)
        v = max(0.0, drop - y_pos)
        return min(1.0, v * 2.5)

    elif preset == 8:  # Kaleidoscope
        angle = math.atan2(ny, nx + 1e-6)
        segments = max(3, int(6 * a))
        angle = abs((angle % (2 * pi / segments)) - pi / segments)
        r = sqrt(nx * nx + ny * ny)
        v = sin(r * 12.0 * b - t * 2.0) * cos(angle * 5.0 + t)
        return (v + 1.0) * 0.5

    elif preset == 9:  # Spiral Galaxy
        r = sqrt(nx * nx + ny * ny) + 1e-6
        angle = math.atan2(ny, nx)
        spiral = sin(angle * 2.0 * a - r * 10.0 * b + t * 1.5)
        arm = max(0.0, spiral) * max(0.0, 1.0 - r * 1.2)
        core = max(0.0, 0.3 - r) * 3.0
        v = arm + core
        v += sin(r * 30.0 - t * 3.0) * 0.1 * max(0.0, 1.0 - r * 2.0)
        return min(1.0, max(0.0, v))

    return 0.0



def _shadertoy_color(self, val: float) -> int:
    """Map shader value [0,1] to a curses color pair based on current color mode."""
    mode = self.shadertoy_color_mode
    if mode == 0:  # Rainbow
        if val < 0.15:
            return curses.color_pair(6) | curses.A_DIM
        elif val < 0.3:
            return curses.color_pair(2)  # cyan
        elif val < 0.5:
            return curses.color_pair(1)  # green
        elif val < 0.7:
            return curses.color_pair(3)  # yellow/highlight
        elif val < 0.85:
            return curses.color_pair(4)  # red/magenta
        else:
            return curses.color_pair(7) | curses.A_BOLD
    elif mode == 1:  # Fire
        if val < 0.2:
            return curses.color_pair(0)
        elif val < 0.4:
            return curses.color_pair(4) | curses.A_DIM  # dark red
        elif val < 0.6:
            return curses.color_pair(4)  # red
        elif val < 0.8:
            return curses.color_pair(3)  # yellow
        else:
            return curses.color_pair(7) | curses.A_BOLD  # white
    elif mode == 2:  # Ocean
        if val < 0.2:
            return curses.color_pair(0)
        elif val < 0.4:
            return curses.color_pair(6) | curses.A_DIM
        elif val < 0.6:
            return curses.color_pair(2) | curses.A_DIM  # dark cyan
        elif val < 0.8:
            return curses.color_pair(2)  # cyan
        else:
            return curses.color_pair(7) | curses.A_BOLD
    else:  # Mono
        if val < 0.3:
            return curses.color_pair(0)
        elif val < 0.6:
            return curses.color_pair(6)
        elif val < 0.85:
            return curses.color_pair(7)
        else:
            return curses.color_pair(7) | curses.A_BOLD



def _enter_shadertoy_mode(self):
    """Enter Shader Toy mode — show preset menu."""
    self.shadertoy_menu = True
    self.shadertoy_menu_sel = 0
    self._flash("Shader Toy — select a shader")



def _exit_shadertoy_mode(self):
    """Exit Shader Toy mode."""
    self.shadertoy_mode = False
    self.shadertoy_menu = False
    self.shadertoy_running = False
    self._flash("Shader Toy mode OFF")



def _shadertoy_init(self, preset_idx: int):
    """Initialize shader toy with chosen preset."""
    name, _desc = self.SHADERTOY_PRESETS[preset_idx]
    self.shadertoy_preset_name = name
    self.shadertoy_preset_idx = preset_idx
    self.shadertoy_generation = 0
    self.shadertoy_time = 0.0
    self.shadertoy_speed = 1.0
    self.shadertoy_param_a = 1.0
    self.shadertoy_param_b = 1.0
    self.shadertoy_running = True
    self.shadertoy_menu = False
    self.shadertoy_mode = True
    self._flash(f"Shader: {name} — space=pause, c=color, n/N=next/prev")



def _shadertoy_step(self):
    """Advance one frame — increment time."""
    self.shadertoy_time += 0.05 * self.shadertoy_speed
    self.shadertoy_generation += 1



def _handle_shadertoy_menu_key(self, key: int) -> bool:
    """Handle input in shader toy preset menu."""
    n = len(self.SHADERTOY_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.shadertoy_menu_sel = (self.shadertoy_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.shadertoy_menu_sel = (self.shadertoy_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._shadertoy_init(self.shadertoy_menu_sel)
    elif key in (ord("q"), 27):
        self.shadertoy_menu = False
        self._flash("Shader Toy cancelled")
    return True



def _handle_shadertoy_key(self, key: int) -> bool:
    """Handle input in active shader toy simulation."""
    if key == ord(" "):
        self.shadertoy_running = not self.shadertoy_running
    elif key == ord("n"):
        # Next shader
        n = len(self.SHADERTOY_PRESETS)
        self._shadertoy_init((self.shadertoy_preset_idx + 1) % n)
    elif key == ord("N"):
        # Prev shader
        n = len(self.SHADERTOY_PRESETS)
        self._shadertoy_init((self.shadertoy_preset_idx - 1) % n)
    elif key == ord("c"):
        n_colors = len(self.SHADERTOY_COLOR_NAMES)
        self.shadertoy_color_mode = (self.shadertoy_color_mode + 1) % n_colors
        self._flash(f"Color: {self.SHADERTOY_COLOR_NAMES[self.shadertoy_color_mode]}")
    elif key == ord("+") or key == ord("="):
        self.shadertoy_speed = min(5.0, self.shadertoy_speed + 0.25)
        self._flash(f"Speed: {self.shadertoy_speed:.2f}x")
    elif key == ord("-"):
        self.shadertoy_speed = max(0.1, self.shadertoy_speed - 0.25)
        self._flash(f"Speed: {self.shadertoy_speed:.2f}x")
    elif key == ord("a"):
        self.shadertoy_param_a = min(3.0, self.shadertoy_param_a + 0.1)
        self._flash(f"Param A: {self.shadertoy_param_a:.1f}")
    elif key == ord("A"):
        self.shadertoy_param_a = max(0.1, self.shadertoy_param_a - 0.1)
        self._flash(f"Param A: {self.shadertoy_param_a:.1f}")
    elif key == ord("b"):
        self.shadertoy_param_b = min(3.0, self.shadertoy_param_b + 0.1)
        self._flash(f"Param B: {self.shadertoy_param_b:.1f}")
    elif key == ord("B"):
        self.shadertoy_param_b = max(0.1, self.shadertoy_param_b - 0.1)
        self._flash(f"Param B: {self.shadertoy_param_b:.1f}")
    elif key == ord("r"):
        self._shadertoy_init(self.shadertoy_preset_idx)
    elif key in (ord("R"), ord("m")):
        self.shadertoy_mode = False
        self.shadertoy_running = False
        self.shadertoy_menu = True
        self.shadertoy_menu_sel = 0
    elif key in (ord("q"), 27):
        self._exit_shadertoy_mode()
    else:
        return True
    return True



def _draw_shadertoy_menu(self, max_y: int, max_x: int):
    """Draw the shader toy preset selection menu."""
    self.stdscr.erase()
    title = "── Shader Toy ── Select Shader ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Real-time programmable pixel shaders rendered in ASCII"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc) in enumerate(self.SHADERTOY_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<20s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.shadertoy_menu_sel:
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



def _draw_shadertoy(self, max_y: int, max_x: int):
    """Render the current shader to the terminal as ASCII art."""
    self.stdscr.erase()

    view_h = max_y - 3
    view_w = max_x - 1
    if view_h < 5 or view_w < 10:
        return

    shade = self.SHADERTOY_SHADE_CHARS
    n_shades = len(shade) - 1
    t = self.shadertoy_time
    shader_eval = self._shadertoy_eval
    shader_color = self._shadertoy_color

    # Aspect ratio correction (terminal chars ~2:1)
    aspect = (view_w / view_h) * 0.5

    for row in range(view_h):
        line_chars = []
        line_attrs = []
        # Normalized y: -1 to 1
        ny = (0.5 - row / view_h) * 2.0

        for col in range(view_w):
            # Normalized x: -1 to 1 (aspect-corrected)
            nx = (col / view_w - 0.5) * 2.0 * aspect

            val = shader_eval(nx, ny, t)
            val = max(0.0, min(1.0, val))

            idx = int(val * n_shades)
            ch = shade[idx]
            attr = shader_color(val)

            line_chars.append(ch)
            line_attrs.append(attr)

        # Write line to screen
        for col_i, (ch, attr) in enumerate(zip(line_chars, line_attrs)):
            try:
                self.stdscr.addstr(1 + row, col_i, ch, attr)
            except curses.error:
                pass

    # HUD
    state = "▶ RUNNING" if self.shadertoy_running else "⏸ PAUSED"
    color_name = self.SHADERTOY_COLOR_NAMES[self.shadertoy_color_mode]
    hud = (f" {self.shadertoy_preset_name}"
           f"  |  {state}"
           f"  |  t={self.shadertoy_time:.1f}"
           f"  |  Speed: {self.shadertoy_speed:.2f}x"
           f"  |  Color: {color_name}"
           f"  |  A={self.shadertoy_param_a:.1f} B={self.shadertoy_param_b:.1f}"
           f"  |  Frame: {self.shadertoy_generation}")
    try:
        self.stdscr.addstr(0, 0, hud[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    help_text = (" space=pause  n/N=next/prev  c=color  +/-=speed"
                 "  a/A=param-A  b/B=param-B  r=reset  m=menu  q=quit")
    try:
        self.stdscr.addstr(max_y - 1, 0, help_text[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register shadertoy mode methods and constants on the App class."""
    App.SHADERTOY_SHADE_CHARS = SHADERTOY_SHADE_CHARS
    App.SHADERTOY_PRESETS = SHADERTOY_PRESETS
    App.SHADERTOY_COLOR_NAMES = SHADERTOY_COLOR_NAMES
    App._shadertoy_eval = _shadertoy_eval
    App._shadertoy_color = _shadertoy_color
    App._enter_shadertoy_mode = _enter_shadertoy_mode
    App._exit_shadertoy_mode = _exit_shadertoy_mode
    App._shadertoy_init = _shadertoy_init
    App._shadertoy_step = _shadertoy_step
    App._handle_shadertoy_menu_key = _handle_shadertoy_menu_key
    App._handle_shadertoy_key = _handle_shadertoy_key
    App._draw_shadertoy_menu = _draw_shadertoy_menu
    App._draw_shadertoy = _draw_shadertoy

