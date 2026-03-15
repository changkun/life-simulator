"""Mode: ifs — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_ifs_mode(self):
    """Enter Chaos Game / IFS Fractal mode — show preset menu."""
    self.ifs_menu = True
    self.ifs_menu_sel = 0
    self._flash("Chaos Game / IFS Fractals — select a fractal")



def _exit_ifs_mode(self):
    """Exit Chaos Game / IFS Fractal mode."""
    self.ifs_mode = False
    self.ifs_menu = False
    self.ifs_running = False
    self.ifs_points = []
    self.ifs_color_field = []
    self._flash("IFS Fractal mode OFF")



def _ifs_init(self, preset_idx: int):
    """Initialize IFS fractal simulation with the given preset.

    Each transform is (a, b, c, d, e, f, prob) representing:
      x' = a*x + b*y + e
      y' = c*x + d*y + f
    with probability prob of being chosen.
    """
    name, _desc, preset_id = self.IFS_PRESETS[preset_idx]
    self.ifs_preset_name = name
    self.ifs_generation = 0
    self.ifs_running = False
    self.ifs_total_points = 0

    max_y, max_x = self.stdscr.getmaxyx()
    self.ifs_rows = max(10, max_y - 3)
    self.ifs_cols = max(10, max_x - 1)

    # Initialize density and color fields
    self.ifs_points = [[0] * self.ifs_cols for _ in range(self.ifs_rows)]
    self.ifs_color_field = [[-1] * self.ifs_cols for _ in range(self.ifs_rows)]

    self.ifs_steps_per_frame = 200
    self.ifs_colorize = True

    # Define IFS transforms: (a, b, c, d, e, f, probability)
    if preset_id == "sierpinski":
        # Sierpinski triangle: 3 contractions toward vertices
        self.ifs_transforms = [
            (0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 1.0 / 3),
            (0.5, 0.0, 0.0, 0.5, 0.5, 0.0, 1.0 / 3),
            (0.5, 0.0, 0.0, 0.5, 0.25, 0.5, 1.0 / 3),
        ]
        self.ifs_x = random.random()
        self.ifs_y = random.random()

    elif preset_id == "fern":
        # Barnsley fern — classic IFS
        self.ifs_transforms = [
            (0.0, 0.0, 0.0, 0.16, 0.0, 0.0, 0.01),
            (0.85, 0.04, -0.04, 0.85, 0.0, 1.6, 0.85),
            (0.20, -0.26, 0.23, 0.22, 0.0, 1.6, 0.07),
            (-0.15, 0.28, 0.26, 0.24, 0.0, 0.44, 0.07),
        ]
        self.ifs_x = 0.0
        self.ifs_y = 0.0

    elif preset_id == "vicsek":
        # Vicsek snowflake: 5 contractions (center + 4 corners)
        r = 1.0 / 3
        self.ifs_transforms = [
            (r, 0.0, 0.0, r, 0.0, 0.0, 0.2),
            (r, 0.0, 0.0, r, 2 * r, 0.0, 0.2),
            (r, 0.0, 0.0, r, 0.0, 2 * r, 0.2),
            (r, 0.0, 0.0, r, 2 * r, 2 * r, 0.2),
            (r, 0.0, 0.0, r, r, r, 0.2),
        ]
        self.ifs_x = 0.5
        self.ifs_y = 0.5

    elif preset_id == "carpet":
        # Sierpinski carpet: 8 contractions (all corners + edges, no center)
        r = 1.0 / 3
        positions = [
            (0, 0), (r, 0), (2 * r, 0),
            (0, r),         (2 * r, r),
            (0, 2 * r), (r, 2 * r), (2 * r, 2 * r),
        ]
        self.ifs_transforms = [
            (r, 0.0, 0.0, r, px, py, 1.0 / 8) for px, py in positions
        ]
        self.ifs_x = 0.5
        self.ifs_y = 0.5

    elif preset_id == "dragon":
        # Heighway dragon curve
        self.ifs_transforms = [
            (0.5, -0.5, 0.5, 0.5, 0.0, 0.0, 0.5),
            (-0.5, -0.5, 0.5, -0.5, 1.0, 0.0, 0.5),
        ]
        self.ifs_x = 0.5
        self.ifs_y = 0.5

    elif preset_id == "maple":
        # Maple leaf IFS
        self.ifs_transforms = [
            (0.14, 0.01, 0.0, 0.51, -0.08, -1.31, 0.10),
            (0.43, 0.52, -0.45, 0.50, 1.49, -0.75, 0.35),
            (0.45, -0.49, 0.47, 0.47, -1.62, -0.74, 0.35),
            (0.49, 0.0, 0.0, 0.51, 0.02, 1.62, 0.20),
        ]
        self.ifs_x = 0.0
        self.ifs_y = 0.0

    elif preset_id == "koch":
        # Koch snowflake via IFS
        import math
        s = 1.0 / 3
        cos60 = math.cos(math.pi / 3)
        sin60 = math.sin(math.pi / 3)
        self.ifs_transforms = [
            (s, 0.0, 0.0, s, 0.0, 0.0, 0.25),
            (s, 0.0, 0.0, s, 2 * s, 0.0, 0.25),
            (s * cos60, -s * sin60, s * sin60, s * cos60, s, 0.0, 0.25),
            (s * cos60, s * sin60, -s * sin60, s * cos60, 0.5, s * sin60, 0.25),
        ]
        self.ifs_x = 0.5
        self.ifs_y = 0.5

    elif preset_id == "crystal":
        # Symmetric crystal / snowflake pattern
        import math
        transforms = []
        n_arms = 6
        for i in range(n_arms):
            angle = 2 * math.pi * i / n_arms
            ca = math.cos(angle)
            sa = math.sin(angle)
            sc = 0.4
            transforms.append(
                (sc * ca, -sc * sa, sc * sa, sc * ca,
                 0.5 * ca, 0.5 * sa, 1.0 / (n_arms + 1))
            )
        # Central contraction
        transforms.append((0.3, 0.0, 0.0, 0.3, 0.0, 0.0, 1.0 / (n_arms + 1)))
        self.ifs_transforms = transforms
        self.ifs_x = 0.0
        self.ifs_y = 0.0

    # Skip initial transient
    for _ in range(50):
        self._ifs_iterate()

    self.ifs_menu = False
    self.ifs_mode = True
    self._flash(f"IFS Fractal: {name} — Space to start")



def _ifs_iterate(self):
    """Perform one iteration of the IFS chaos game."""
    # Choose transform by probability
    r = random.random()
    cumulative = 0.0
    chosen = 0
    for i, t in enumerate(self.ifs_transforms):
        cumulative += t[6]
        if r <= cumulative:
            chosen = i
            break
    a, b, c, d, e, f, _p = self.ifs_transforms[chosen]
    nx = a * self.ifs_x + b * self.ifs_y + e
    ny = c * self.ifs_x + d * self.ifs_y + f
    self.ifs_x = nx
    self.ifs_y = ny
    self.ifs_last_transform = chosen



def _ifs_step(self):
    """Advance IFS fractal by one point iteration and plot it."""
    self._ifs_iterate()

    # Map IFS coordinates to screen
    # We need to find the bounding box — use adaptive bounds
    rows = self.ifs_rows
    cols = self.ifs_cols

    # Compute bounds from all transforms' fixed points (approximate)
    # Use running min/max tracked across iterations
    if not hasattr(self, '_ifs_xmin') or self.ifs_total_points == 0:
        self._ifs_xmin = self.ifs_x - 0.1
        self._ifs_xmax = self.ifs_x + 0.1
        self._ifs_ymin = self.ifs_y - 0.1
        self._ifs_ymax = self.ifs_y + 0.1

    # Expand bounds if needed
    margin = 0.05
    if self.ifs_x < self._ifs_xmin:
        self._ifs_xmin = self.ifs_x - margin
    if self.ifs_x > self._ifs_xmax:
        self._ifs_xmax = self.ifs_x + margin
    if self.ifs_y < self._ifs_ymin:
        self._ifs_ymin = self.ifs_y - margin
    if self.ifs_y > self._ifs_ymax:
        self._ifs_ymax = self.ifs_y + margin

    xrange = self._ifs_xmax - self._ifs_xmin
    yrange = self._ifs_ymax - self._ifs_ymin
    if xrange < 1e-10:
        xrange = 1.0
    if yrange < 1e-10:
        yrange = 1.0

    # Map to screen with aspect ratio correction (chars are ~2x tall)
    # Scale to fit both dimensions
    sx = (self.ifs_x - self._ifs_xmin) / xrange
    sy = (self.ifs_y - self._ifs_ymin) / yrange

    col = int(sx * (cols - 1))
    row = int((1.0 - sy) * (rows - 1))  # flip y

    col = max(0, min(cols - 1, col))
    row = max(0, min(rows - 1, row))

    self.ifs_points[row][col] += 1
    self.ifs_color_field[row][col] = self.ifs_last_transform
    self.ifs_total_points += 1
    self.ifs_generation += 1



def _handle_ifs_menu_key(self, key: int) -> bool:
    """Handle keys in the IFS Fractal preset menu."""
    if key == -1:
        return True
    n = len(self.IFS_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.ifs_menu_sel = (self.ifs_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.ifs_menu_sel = (self.ifs_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.ifs_menu = False
        self._flash("IFS Fractal cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._ifs_init(self.ifs_menu_sel)
        return True
    return True



def _handle_ifs_key(self, key: int) -> bool:
    """Handle keys while in Chaos Game / IFS Fractal mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_ifs_mode()
        return True
    if key == ord(" "):
        self.ifs_running = not self.ifs_running
        self._flash("Playing" if self.ifs_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        for _ in range(self.ifs_steps_per_frame):
            self._ifs_step()
        return True
    if key == ord("c"):
        self.ifs_colorize = not self.ifs_colorize
        self._flash(f"Color by transform: {'ON' if self.ifs_colorize else 'OFF'}")
        return True
    if key == ord(">"):
        self.ifs_steps_per_frame = min(5000, self.ifs_steps_per_frame * 2)
        self._flash(f"Points/frame: {self.ifs_steps_per_frame}")
        return True
    if key == ord("<"):
        self.ifs_steps_per_frame = max(10, self.ifs_steps_per_frame // 2)
        self._flash(f"Points/frame: {self.ifs_steps_per_frame}")
        return True
    if key == ord("x"):
        # Clear the canvas and restart
        self.ifs_points = [[0] * self.ifs_cols for _ in range(self.ifs_rows)]
        self.ifs_color_field = [[-1] * self.ifs_cols for _ in range(self.ifs_rows)]
        self.ifs_total_points = 0
        self.ifs_generation = 0
        if hasattr(self, '_ifs_xmin'):
            del self._ifs_xmin
            del self._ifs_xmax
            del self._ifs_ymin
            del self._ifs_ymax
        self._flash("Canvas cleared")
        return True
    if key == ord("r"):
        self._ifs_init(self.ifs_menu_sel)
        self._flash("Reset")
        return True
    if key == ord("R"):
        self.ifs_mode = False
        self.ifs_running = False
        self.ifs_menu = True
        self.ifs_menu_sel = 0
        return True
    return True



def _draw_ifs_menu(self, max_y: int, max_x: int):
    """Draw the IFS Fractal preset selection menu."""
    self.stdscr.erase()
    title = "── Chaos Game / IFS Fractals ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Iterated Function System fractals built point-by-point"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.IFS_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.IFS_PRESETS):
        y = 5 + i
        if y >= max_y - 14:
            break
        line = f"  {name:<22s} {desc}"
        attr = curses.color_pair(6)
        if i == self.ifs_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_y = 5 + n + 1
    info_lines = [
        "The Chaos Game generates fractals by iteratively",
        "applying random affine transformations to a point.",
        "",
        "Unlike equation-based fractals (Mandelbrot/Julia),",
        "IFS fractals emerge point-by-point — watch the",
        "structure materialize from apparent randomness.",
        "",
        "Each color represents a different transform,",
        "revealing the fractal's recursive structure.",
    ]
    for i, line in enumerate(info_lines):
        y = info_y + i
        if y >= max_y - 3:
            break
        try:
            self.stdscr.addstr(y, max(1, (max_x - len(line)) // 2),
                               line[:max_x - 2], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    footer = "↑/↓ select · Enter confirm · q cancel"
    try:
        self.stdscr.addstr(max_y - 2, max(0, (max_x - len(footer)) // 2), footer,
                           curses.color_pair(7))
    except curses.error:
        pass



def _draw_ifs(self, max_y: int, max_x: int):
    """Draw the Chaos Game / IFS Fractal simulation."""
    import math
    self.stdscr.erase()
    rows = self.ifs_rows
    cols = self.ifs_cols

    # Find max density for normalization
    max_density = 1
    for r in range(rows):
        for ci in range(cols):
            if self.ifs_points[r][ci] > max_density:
                max_density = self.ifs_points[r][ci]

    # Use log scale for density display
    log_max = math.log1p(max_density)
    if log_max < 1e-10:
        log_max = 1.0

    # Character ramp from sparse to dense
    ramp = " ·∙:;+*#%@"

    # Color palette for transforms
    transform_colors = [
        curses.color_pair(3),                          # green
        curses.color_pair(4),                          # blue
        curses.color_pair(5),                          # magenta
        curses.color_pair(6),                          # cyan
        curses.color_pair(3) | curses.A_BOLD,          # bright green
        curses.color_pair(7),                          # yellow/white
        curses.color_pair(1) | curses.A_BOLD,          # bright red
        curses.color_pair(4) | curses.A_BOLD,          # bright blue
    ]

    # Render field
    draw_rows = min(rows, max_y - 2)
    draw_cols = min(cols, max_x - 1)
    for r in range(draw_rows):
        for ci in range(draw_cols):
            density = self.ifs_points[r][ci]
            if density == 0:
                continue  # leave blank for speed
            norm = math.log1p(density) / log_max
            norm = max(0.0, min(1.0, norm))
            idx = int(norm * (len(ramp) - 1))
            ch = ramp[idx]

            if self.ifs_colorize and self.ifs_color_field[r][ci] >= 0:
                tidx = self.ifs_color_field[r][ci] % len(transform_colors)
                color = transform_colors[tidx]
                # Brighten based on density
                if norm > 0.6:
                    color = color | curses.A_BOLD
            else:
                # Monochrome density coloring
                if norm < 0.2:
                    color = curses.color_pair(4) | curses.A_DIM
                elif norm < 0.4:
                    color = curses.color_pair(6) | curses.A_DIM
                elif norm < 0.6:
                    color = curses.color_pair(6)
                elif norm < 0.8:
                    color = curses.color_pair(7)
                else:
                    color = curses.color_pair(1) | curses.A_BOLD

            try:
                self.stdscr.addstr(r + 1, ci, ch, color)
            except curses.error:
                pass

    # Status bar
    status = (f" IFS: {self.ifs_preset_name}"
              f" │ Points: {self.ifs_total_points:,}"
              f" │ {'▶' if self.ifs_running else '⏸'}"
              f" │ Transforms: {len(self.ifs_transforms)}"
              f" │ Color: {'ON' if self.ifs_colorize else 'OFF'}"
              f" │ Rate: {self.ifs_steps_per_frame}/f")
    try:
        self.stdscr.addstr(0, 0, status[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Hint bar
    hint_y = max_y - 1
    now = time.monotonic()
    if self.message and now - self.message_time < 3.0:
        hint = f" {self.message}"
    else:
        hint = " Space=play  n=step  c=color  </>=rate  x=clear  r=reset  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register ifs mode methods on the App class."""
    App._enter_ifs_mode = _enter_ifs_mode
    App._exit_ifs_mode = _exit_ifs_mode
    App._ifs_init = _ifs_init
    App._ifs_iterate = _ifs_iterate
    App._ifs_step = _ifs_step
    App._handle_ifs_menu_key = _handle_ifs_menu_key
    App._handle_ifs_key = _handle_ifs_key
    App._draw_ifs_menu = _draw_ifs_menu
    App._draw_ifs = _draw_ifs

