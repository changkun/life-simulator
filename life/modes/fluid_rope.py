"""Mode: fluidrope — simulation mode for the life package."""
import curses
import math
import random
import time

FLUIDROPE_PRESETS = [
    ("Honey", "Thick golden honey coiling on a surface", "honey"),
    ("Chocolate", "Smooth melted chocolate with medium viscosity", "chocolate"),
    ("Shampoo", "Thin, fast-flowing shampoo with rapid coiling", "shampoo"),
    ("Lava", "Extremely viscous molten lava with slow, heavy coils", "lava"),
]

_FLUIDROPE_POOL_CHARS = "░▒▓█▓▒░█"
_FLUIDROPE_COIL_CHARS = "·∘○◎●◉"
_FLUIDROPE_SPLASH_CHARS = "·∘°~≈"


def _enter_fluidrope_mode(self):
    self.fluidrope_mode = True
    self.fluidrope_menu = True
    self.fluidrope_menu_sel = 0
    self.fluidrope_running = False




def _exit_fluidrope_mode(self):
    self.fluidrope_mode = False
    self.fluidrope_menu = False
    self.fluidrope_running = False
    self.fluidrope_rope_segments = []
    self.fluidrope_pool = []
    self.fluidrope_trail = []




def _fluidrope_init(self, preset_key):
    import math as _m
    rows, cols = self.stdscr.getmaxyx()
    self.fluidrope_rows = rows
    self.fluidrope_cols = cols
    self.fluidrope_menu = False
    self.fluidrope_running = True
    self.fluidrope_generation = 0
    self.fluidrope_time = 0.0
    self.fluidrope_show_info = False
    self.fluidrope_speed = 3
    self.fluidrope_coil_angle = 0.0
    self.fluidrope_surface_offset = 0.0
    self.fluidrope_trail = []

    # Pour point at top center
    self.fluidrope_pour_x = 0.5
    self.fluidrope_pour_y = 0.08

    if preset_key == "honey":
        self.fluidrope_preset_name = "Honey"
        self.fluidrope_viscosity = 1.0
        self.fluidrope_flow_rate = 1.0
        self.fluidrope_pour_height = 0.70
        self.fluidrope_coil_speed = 2.5
        self.fluidrope_coil_radius = 3.0
        self.fluidrope_surface_move = 0.0
    elif preset_key == "chocolate":
        self.fluidrope_preset_name = "Chocolate"
        self.fluidrope_viscosity = 0.7
        self.fluidrope_flow_rate = 1.3
        self.fluidrope_pour_height = 0.60
        self.fluidrope_coil_speed = 3.5
        self.fluidrope_coil_radius = 2.5
        self.fluidrope_surface_move = 0.0
    elif preset_key == "shampoo":
        self.fluidrope_preset_name = "Shampoo"
        self.fluidrope_viscosity = 0.5
        self.fluidrope_flow_rate = 1.5
        self.fluidrope_pour_height = 0.55
        self.fluidrope_coil_speed = 5.0
        self.fluidrope_coil_radius = 2.0
        self.fluidrope_surface_move = 0.0
    elif preset_key == "lava":
        self.fluidrope_preset_name = "Lava"
        self.fluidrope_viscosity = 2.0
        self.fluidrope_flow_rate = 0.6
        self.fluidrope_pour_height = 0.80
        self.fluidrope_coil_speed = 1.2
        self.fluidrope_coil_radius = 4.5
        self.fluidrope_surface_move = 0.0

    # Initialize pool (accumulated fluid per column)
    self.fluidrope_pool = [0.0] * cols

    # Initialize rope segments along the stream
    stream_top_y = int(self.fluidrope_pour_y * rows)
    surface_y = int((self.fluidrope_pour_y + self.fluidrope_pour_height) * rows)
    cx = int(self.fluidrope_pour_x * cols)
    num_segs = surface_y - stream_top_y
    self.fluidrope_rope_segments = []
    for i in range(max(1, num_segs)):
        y = stream_top_y + i
        frac = i / max(1, num_segs - 1)
        # acceleration under gravity — speed increases along stream
        speed = 0.5 + frac * 2.0
        self.fluidrope_rope_segments.append([float(cx), float(y), 0.0, speed])




def _fluidrope_step(self):
    import math as _m
    import random as _r

    rows = self.fluidrope_rows
    cols = self.fluidrope_cols
    dt = self.fluidrope_dt
    self.fluidrope_time += dt
    self.fluidrope_generation += 1
    t = self.fluidrope_time

    # Surface movement (for serpentine/figure-eight patterns)
    if abs(self.fluidrope_surface_move) > 0.01:
        self.fluidrope_surface_offset += self.fluidrope_surface_move * dt

    # Pour point
    pour_px = int(self.fluidrope_pour_x * cols)
    stream_top = int(self.fluidrope_pour_y * rows)
    surface_y = int((self.fluidrope_pour_y + self.fluidrope_pour_height) * rows)
    surface_y = min(surface_y, rows - 3)

    # Update coiling angle
    self.fluidrope_coil_angle += self.fluidrope_coil_speed * dt
    coil_r = self.fluidrope_coil_radius

    # Compute landing position with coiling
    base_land_x = pour_px + self.fluidrope_surface_offset
    land_x = base_land_x + coil_r * _m.cos(self.fluidrope_coil_angle)
    land_x_int = int(land_x) % cols

    # Record trail for coil visualization
    self.fluidrope_trail.append((land_x_int, surface_y, t))
    # Keep last 80 trail entries
    max_trail = 80
    if len(self.fluidrope_trail) > max_trail:
        self.fluidrope_trail = self.fluidrope_trail[-max_trail:]

    # Update rope segments — they form the falling stream
    num_segs = max(1, surface_y - stream_top)
    if len(self.fluidrope_rope_segments) != num_segs:
        self.fluidrope_rope_segments = []
        for i in range(num_segs):
            y = stream_top + i
            self.fluidrope_rope_segments.append([float(pour_px), float(y), 0.0, 0.5 + (i / max(1, num_segs - 1)) * 2.0])

    for i, seg in enumerate(self.fluidrope_rope_segments):
        frac = i / max(1, num_segs - 1)
        # Near the top, the stream is straight; near bottom it bends toward coil point
        target_x = pour_px * (1.0 - frac ** 2) + land_x * (frac ** 2)
        # Add slight wobble from viscosity
        wobble = _m.sin(t * 3.0 + i * 0.5) * 0.3 * frac * self.fluidrope_viscosity
        seg[0] = target_x + wobble
        seg[1] = stream_top + i

    # Accumulate fluid at landing point
    spread = max(1, int(coil_r * 1.5))
    deposit = self.fluidrope_flow_rate * dt * 0.8
    for dx in range(-spread, spread + 1):
        col = (land_x_int + dx) % cols
        dist_factor = 1.0 - abs(dx) / (spread + 1)
        self.fluidrope_pool[col] += deposit * dist_factor * dist_factor

    # Spread/flatten pool (viscous spreading)
    spread_rate = 0.02 / max(0.3, self.fluidrope_viscosity)
    new_pool = list(self.fluidrope_pool)
    for c in range(cols):
        left = (c - 1) % cols
        right = (c + 1) % cols
        avg = (self.fluidrope_pool[left] + self.fluidrope_pool[right]) / 2.0
        diff = avg - self.fluidrope_pool[c]
        new_pool[c] += diff * spread_rate
    self.fluidrope_pool = new_pool

    # Cap pool height
    max_pool = rows * 0.35
    for c in range(cols):
        if self.fluidrope_pool[c] > max_pool:
            self.fluidrope_pool[c] = max_pool




def _handle_fluidrope_menu_key(self, key):
    n = len(FLUIDROPE_PRESETS)
    if key in (curses.KEY_UP, ord('k')):
        self.fluidrope_menu_sel = (self.fluidrope_menu_sel - 1) % n
    elif key in (curses.KEY_DOWN, ord('j')):
        self.fluidrope_menu_sel = (self.fluidrope_menu_sel + 1) % n
    elif key in (curses.KEY_ENTER, 10, 13):
        preset_key = FLUIDROPE_PRESETS[self.fluidrope_menu_sel][2]
        self._fluidrope_init(preset_key)
    elif key == ord('q'):
        self._exit_fluidrope_mode()
    return True




def _handle_fluidrope_key(self, key):
    if key == ord(' '):
        self.fluidrope_running = not self.fluidrope_running
    elif key == ord('n'):
        self._fluidrope_step()
    elif key == ord('+') or key == ord('='):
        self.fluidrope_speed = min(10, self.fluidrope_speed + 1)
    elif key == ord('-'):
        self.fluidrope_speed = max(1, self.fluidrope_speed - 1)
    elif key == ord('h'):
        # Increase pour height
        self.fluidrope_pour_height = min(0.85, self.fluidrope_pour_height + 0.05)
    elif key == ord('H'):
        # Decrease pour height
        self.fluidrope_pour_height = max(0.3, self.fluidrope_pour_height - 0.05)
    elif key == ord('f'):
        self.fluidrope_flow_rate = min(3.0, self.fluidrope_flow_rate + 0.1)
    elif key == ord('F'):
        self.fluidrope_flow_rate = max(0.1, self.fluidrope_flow_rate - 0.1)
    elif key == ord('v'):
        self.fluidrope_viscosity = min(3.0, self.fluidrope_viscosity + 0.1)
    elif key == ord('V'):
        self.fluidrope_viscosity = max(0.1, self.fluidrope_viscosity - 0.1)
    elif key == ord('s'):
        self.fluidrope_surface_move += 0.5
    elif key == ord('S'):
        self.fluidrope_surface_move -= 0.5
    elif key == ord('0'):
        self.fluidrope_surface_move = 0.0
        self.fluidrope_surface_offset = 0.0
    elif key == ord('i'):
        self.fluidrope_show_info = not self.fluidrope_show_info
    elif key == ord('r'):
        preset_key = None
        for name, desc, pk in FLUIDROPE_PRESETS:
            if name == self.fluidrope_preset_name:
                preset_key = pk
                break
        if preset_key:
            self._fluidrope_init(preset_key)
    elif key in (ord('R'), ord('m')):
        self.fluidrope_menu = True
        self.fluidrope_running = False
    elif key == ord('q'):
        self._exit_fluidrope_mode()
    return True




def _draw_fluidrope_menu(self, max_y, max_x):
    self.stdscr.erase()
    cols = max_x
    title = "═══ Fluid Rope / Honey Coiling ═══"
    if max_y < 5 or cols < 20:
        return
    y = 1
    try:
        self.stdscr.addstr(y, max(0, (cols - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    y += 2
    subtitle = "Select a fluid preset:"
    try:
        self.stdscr.addstr(y, max(0, (cols - len(subtitle)) // 2), subtitle, curses.A_DIM)
    except curses.error:
        pass

    y += 2
    for idx, (name, desc, _key) in enumerate(FLUIDROPE_PRESETS):
        if y >= max_y - 4:
            break
        marker = "▶ " if idx == self.fluidrope_menu_sel else "  "
        attr = curses.A_REVERSE if idx == self.fluidrope_menu_sel else curses.A_NORMAL
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(y, 4, line[:cols - 6], attr)
        except curses.error:
            pass
        y += 1
        if idx == self.fluidrope_menu_sel:
            try:
                self.stdscr.addstr(y, 6, desc[:cols - 8], curses.A_DIM)
            except curses.error:
                pass
            y += 1
        y += 1

    # ASCII art preview
    y += 1
    art = [
        "     ╷       ",
        "     │       ",
        "     │       ",
        "     ┃       ",
        "    ╱ ╲      ",
        "  ≈~≈~≈~≈    ",
        " ▃▄▅▆▆▅▄▃   ",
    ]
    for line in art:
        if y >= max_y - 2:
            break
        try:
            self.stdscr.addstr(y, max(0, (cols - len(line)) // 2), line, curses.A_DIM)
        except curses.error:
            pass
        y += 1

    hint = " ↑/↓=select  Enter=start  q=back"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:cols - 1], curses.A_DIM)
    except curses.error:
        pass




def _draw_fluidrope(self, max_y, max_x):
    import math as _m
    self.stdscr.erase()
    rows = max_y
    cols = max_x
    if rows < 5 or cols < 10:
        return

    stream_top = int(self.fluidrope_pour_y * rows)
    surface_y = int((self.fluidrope_pour_y + self.fluidrope_pour_height) * rows)
    surface_y = min(surface_y, rows - 3)

    # ── Draw pool / accumulated fluid ──
    for c in range(cols):
        h = self.fluidrope_pool[c] if c < len(self.fluidrope_pool) else 0.0
        if h < 0.05:
            continue
        max_pool = rows * 0.35
        bar_height = int(h / max_pool * len(_FLUIDROPE_POOL_CHARS))
        bar_height = min(bar_height, len(_FLUIDROPE_POOL_CHARS) - 1)
        ch = _FLUIDROPE_POOL_CHARS[bar_height]
        # Draw from surface downward
        pool_rows = max(1, int(h / max_pool * 6))
        for dr in range(pool_rows):
            py = surface_y + 1 + dr
            if 0 <= py < rows - 1 and 0 <= c < cols - 1:
                try:
                    self.stdscr.addch(py, c, ord(ch))
                except curses.error:
                    pass
        # Top of pool gets partial char
        top_py = surface_y + 1
        if 0 <= top_py < rows - 1 and 0 <= c < cols - 1:
            tidx = min(bar_height, len(_FLUIDROPE_POOL_CHARS) - 1)
            try:
                self.stdscr.addch(top_py, c, ord(_FLUIDROPE_POOL_CHARS[tidx]))
            except curses.error:
                pass

    # ── Draw coil trail at surface ──
    t_now = self.fluidrope_time
    for tx, ty, tt in self.fluidrope_trail:
        age = t_now - tt
        if age > 3.0:
            continue
        fade = 1.0 - age / 3.0
        if 0 <= ty < rows - 1 and 0 <= tx < cols - 1:
            cidx = int(fade * (len(_FLUIDROPE_COIL_CHARS) - 1))
            cidx = max(0, min(cidx, len(_FLUIDROPE_COIL_CHARS) - 1))
            ch = _FLUIDROPE_COIL_CHARS[cidx]
            attr = curses.A_BOLD if fade > 0.5 else curses.A_DIM
            try:
                self.stdscr.addch(ty, tx, ord(ch), attr)
            except curses.error:
                pass

    # ── Draw falling stream (rope segments) ──
    for i, seg in enumerate(self.fluidrope_rope_segments):
        sx = int(seg[0])
        sy = int(seg[1])
        if 0 <= sy < rows - 1 and 0 <= sx < cols - 1:
            frac = i / max(1, len(self.fluidrope_rope_segments) - 1)
            # Stream gets thicker near bottom
            if frac < 0.3:
                ch = '│'
            elif frac < 0.6:
                ch = '┃'
            else:
                ch = '║'
            attr = curses.A_BOLD if frac > 0.5 else curses.A_NORMAL
            try:
                self.stdscr.addch(sy, sx, ord(ch), attr)
            except curses.error:
                pass

    # ── Draw pour point (nozzle) ──
    nozzle_x = int(self.fluidrope_pour_x * cols)
    nozzle_y = max(0, stream_top - 1)
    if 0 <= nozzle_y < rows - 1 and 0 <= nozzle_x < cols - 1:
        try:
            self.stdscr.addstr(nozzle_y, max(0, nozzle_x - 1), "╺█╸", curses.A_BOLD)
        except curses.error:
            pass

    # ── Draw splash particles near landing zone ──
    land_x = int(self.fluidrope_pour_x * cols + self.fluidrope_surface_offset +
                 self.fluidrope_coil_radius * _m.cos(self.fluidrope_coil_angle))
    land_x = land_x % cols
    for dx in range(-2, 3):
        for dy in range(-1, 2):
            sx = (land_x + dx) % cols
            sy = surface_y + dy
            if 0 <= sy < rows - 1 and 0 <= sx < cols - 1 and (dx != 0 or dy != 0):
                if abs(dx) + abs(dy) <= 2:
                    cidx = (self.fluidrope_generation + dx + dy) % len(_FLUIDROPE_SPLASH_CHARS)
                    try:
                        self.stdscr.addch(sy, sx, ord(_FLUIDROPE_SPLASH_CHARS[cidx]), curses.A_DIM)
                    except curses.error:
                        pass


def register(App):
    """Register fluidrope mode methods on the App class."""
    App._enter_fluidrope_mode = _enter_fluidrope_mode
    App._exit_fluidrope_mode = _exit_fluidrope_mode
    App._fluidrope_init = _fluidrope_init
    App._fluidrope_step = _fluidrope_step
    App._handle_fluidrope_menu_key = _handle_fluidrope_menu_key
    App._handle_fluidrope_key = _handle_fluidrope_key
    App._draw_fluidrope_menu = _draw_fluidrope_menu
    App._draw_fluidrope = _draw_fluidrope

