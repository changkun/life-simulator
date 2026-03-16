"""Mode: orrery — simulation mode for the life package."""
import curses
import math
import random
import time

_ORRERY_PLANETS = [
    {"name": "Mercury", "sym": "☿", "a": 0.387, "e": 0.2056, "T": 0.241, "color": 7, "char": "m"},
    {"name": "Venus",   "sym": "♀", "a": 0.723, "e": 0.0068, "T": 0.615, "color": 3, "char": "v"},
    {"name": "Earth",   "sym": "⊕", "a": 1.000, "e": 0.0167, "T": 1.000, "color": 6, "char": "E"},
    {"name": "Mars",    "sym": "♂", "a": 1.524, "e": 0.0934, "T": 1.881, "color": 1, "char": "M"},
    {"name": "Jupiter", "sym": "♃", "a": 5.203, "e": 0.0484, "T": 11.86, "color": 3, "char": "J"},
    {"name": "Saturn",  "sym": "♄", "a": 9.537, "e": 0.0539, "T": 29.46, "color": 3, "char": "S"},
    {"name": "Uranus",  "sym": "⛢", "a": 19.19, "e": 0.0473, "T": 84.01, "color": 6, "char": "U"},
    {"name": "Neptune", "sym": "♆", "a": 30.07, "e": 0.0086, "T": 164.8, "color": 4, "char": "N"},
]

ORRERY_PRESETS = [
    ("Full Solar System", "All 8 planets with asteroid belt and comets", "full"),
    ("Inner Planets", "Mercury through Mars — zoomed in view", "inner"),
    ("Outer Planets", "Jupiter through Neptune — zoomed out view", "outer"),
    ("Earth & Neighbors", "Venus, Earth, Mars with detailed orbital info", "neighbors"),
    ("Comet Flyby", "Long-period comet passing through inner solar system", "comet"),
    ("Grand Alignment", "All planets starting near alignment", "alignment"),
]


def _enter_orrery_mode(self):
    """Enter Solar System Orrery mode — show preset menu."""
    self.orrery_menu = True
    self.orrery_menu_sel = 0




def _exit_orrery_mode(self):
    """Exit Solar System Orrery mode."""
    self.orrery_mode = False
    self.orrery_menu = False
    self.orrery_running = False
    self.orrery_planets = []
    self.orrery_asteroids = []
    self.orrery_comets = []
    self.orrery_bg_stars = []




def _orrery_solve_kepler(M, e, tol=1e-6):
    """Solve Kepler's equation M = E - e*sin(E) for eccentric anomaly E."""
    import math
    E = M
    for _ in range(50):
        dE = (M - E + e * math.sin(E)) / (1.0 - e * math.cos(E))
        E += dE
        if abs(dE) < tol:
            break
    return E




def _orrery_init(self, preset: str):
    """Initialize orrery simulation from preset."""
    import math
    import random as rng

    rows, cols = self.grid.rows, self.grid.cols
    self.orrery_rows = rows
    self.orrery_cols = cols
    self.orrery_generation = 0
    self.orrery_time = 0.0
    self.orrery_speed_scale = 1.0
    self.orrery_show_orbits = True
    self.orrery_show_labels = True
    self.orrery_show_info = False
    self.orrery_selected = -1

    # Determine which planets to include and zoom level
    if preset == "inner":
        planet_indices = [0, 1, 2, 3]
        self.orrery_zoom = "inner"
    elif preset == "outer":
        planet_indices = [4, 5, 6, 7]
        self.orrery_zoom = "outer"
    elif preset == "neighbors":
        planet_indices = [1, 2, 3]
        self.orrery_zoom = "inner"
        self.orrery_show_info = True
    elif preset == "comet":
        planet_indices = list(range(8))
        self.orrery_zoom = "full"
    elif preset == "alignment":
        planet_indices = list(range(8))
        self.orrery_zoom = "full"
    else:  # full
        planet_indices = list(range(8))
        self.orrery_zoom = "full"

    # Initialize planets
    self.orrery_planets = []
    for idx in planet_indices:
        pdata = _ORRERY_PLANETS[idx]
        # Random initial mean anomaly (unless alignment preset)
        if preset == "alignment":
            M0 = rng.uniform(-0.15, 0.15)  # near-aligned
        else:
            M0 = rng.uniform(0, 2 * math.pi)
        planet = {
            "name": pdata["name"],
            "sym": pdata["sym"],
            "char": pdata["char"],
            "a": pdata["a"],           # semi-major axis AU
            "e": pdata["e"],           # eccentricity
            "T": pdata["T"],           # orbital period years
            "color": pdata["color"],
            "M0": M0,                  # initial mean anomaly
            "trail": [],               # list of (x, y) screen positions
        }
        self.orrery_planets.append(planet)

    # Initialize asteroid belt (between Mars and Jupiter, ~2.2-3.3 AU)
    self.orrery_asteroids = []
    if preset not in ("inner", "neighbors"):
        for _ in range(min(120, cols)):
            a = rng.uniform(2.1, 3.3)
            e = rng.uniform(0.0, 0.25)
            T = a ** 1.5  # Kepler's third law
            M0 = rng.uniform(0, 2 * math.pi)
            self.orrery_asteroids.append({"a": a, "e": e, "T": T, "M0": M0})

    # Initialize comets
    self.orrery_comets = []
    if preset == "comet":
        # One prominent long-period comet
        self.orrery_comets.append({
            "a": 18.0, "e": 0.967, "T": 18.0 ** 1.5,
            "M0": math.pi * 0.98,  # start near perihelion approach
            "trail": [],
        })
    elif preset == "full":
        # A couple of short-period comets
        for _ in range(2):
            a = rng.uniform(5.0, 15.0)
            e = rng.uniform(0.85, 0.97)
            T = a ** 1.5
            M0 = rng.uniform(0, 2 * math.pi)
            self.orrery_comets.append({"a": a, "e": e, "T": T, "M0": M0, "trail": []})

    # Background stars
    self.orrery_bg_stars = []
    for _ in range(min(80, rows * cols // 30)):
        sr = rng.randint(0, rows - 1)
        sc = rng.randint(0, cols - 1)
        self.orrery_bg_stars.append((sr, sc))

    self.orrery_running = True




def _orrery_get_scale(self):
    """Return the AU-to-screen scale factor and center position."""
    rows, cols = self.orrery_rows, self.orrery_cols
    cx = cols / 2.0
    cy = rows / 2.0
    half = min(rows / 2.0 - 2, cols / 4.0 - 2)  # cols/4 because chars are ~2x tall
    if self.orrery_zoom == "inner":
        max_au = 2.0   # show out to ~2 AU
    elif self.orrery_zoom == "outer":
        max_au = 35.0   # show out to Neptune
    else:
        max_au = 35.0   # full system
    scale = half / max_au  # screen units per AU
    return cx, cy, scale




def _orrery_body_pos(self, body, t):
    """Compute screen position (col, row) for an orbiting body at time t."""
    import math
    a = body["a"]
    e = body["e"]
    T = body["T"]
    M0 = body["M0"]

    # Mean anomaly at time t
    n = 2.0 * math.pi / T  # mean motion
    M = M0 + n * t
    M = M % (2.0 * math.pi)

    # Solve Kepler's equation
    E = _orrery_solve_kepler(M, e)

    # True anomaly
    nu = 2.0 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2),
                           math.sqrt(1 - e) * math.cos(E / 2))

    # Radius
    r = a * (1 - e * math.cos(E))

    # 2D position in AU
    x_au = r * math.cos(nu)
    y_au = r * math.sin(nu)

    # Convert to screen coordinates
    cx, cy, scale = self._orrery_get_scale()
    sc = cx + x_au * scale
    sr = cy + y_au * scale * 0.5  # compress vertically for terminal aspect ratio

    return sc, sr, r, nu




def _orrery_step(self):
    """Advance the orrery simulation by one time step."""
    self.orrery_generation += 1
    dt = self.orrery_dt * self.orrery_speed_scale
    self.orrery_time += dt

    # Update planet trails
    for planet in self.orrery_planets:
        sc, sr, _r, _nu = self._orrery_body_pos(planet, self.orrery_time)
        trail = planet["trail"]
        trail.append((int(round(sc)), int(round(sr))))
        if len(trail) > self.orrery_trail_len:
            trail.pop(0)

    # Update comet trails
    for comet in self.orrery_comets:
        sc, sr, _r, _nu = self._orrery_body_pos(comet, self.orrery_time)
        trail = comet["trail"]
        trail.append((int(round(sc)), int(round(sr))))
        max_trail = self.orrery_trail_len * 3  # comets get longer tails
        if len(trail) > max_trail:
            trail.pop(0)




def _handle_orrery_menu_key(self, key: int) -> bool:
    """Handle keys in the orrery preset menu."""
    n = len(ORRERY_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.orrery_menu_sel = (self.orrery_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.orrery_menu_sel = (self.orrery_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.orrery_menu = False
        self.orrery_mode = False
        self._exit_orrery_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = ORRERY_PRESETS[self.orrery_menu_sel]
        self.orrery_preset_name = preset[0]
        self._orrery_init(preset[2])
        self.orrery_menu = False
        self.orrery_mode = True
        self.orrery_running = True
    else:
        return False
    return True




def _handle_orrery_key(self, key: int) -> bool:
    """Handle keys during orrery simulation."""
    if key in (27, ord('q')):
        self._exit_orrery_mode()
        return True
    elif key == ord(' '):
        self.orrery_running = not self.orrery_running
    elif key in (ord('n'), ord('.')):
        self._orrery_step()
    elif key == ord('r'):
        # Reset with same preset
        for p in ORRERY_PRESETS:
            if p[0] == self.orrery_preset_name:
                self._orrery_init(p[2])
                break
    elif key in (ord('R'), ord('m')):
        self.orrery_running = False
        self.orrery_menu = True
    elif key == ord('z'):
        # Cycle zoom: full -> inner -> outer -> full
        if self.orrery_zoom == "full":
            self.orrery_zoom = "inner"
        elif self.orrery_zoom == "inner":
            self.orrery_zoom = "outer"
        else:
            self.orrery_zoom = "full"
    elif key == ord('o'):
        self.orrery_show_orbits = not self.orrery_show_orbits
    elif key == ord('l'):
        self.orrery_show_labels = not self.orrery_show_labels
    elif key == ord('i'):
        self.orrery_show_info = not self.orrery_show_info
    elif key == ord('+') or key == ord('='):
        self.orrery_speed_scale = min(self.orrery_speed_scale * 1.5, 50.0)
    elif key == ord('-') or key == ord('_'):
        self.orrery_speed_scale = max(self.orrery_speed_scale / 1.5, 0.05)
    elif key == ord('\t'):
        # Cycle through planets for selection
        np = len(self.orrery_planets)
        if np > 0:
            self.orrery_selected = (self.orrery_selected + 1) % np
    elif key == ord('u'):
        self.orrery_selected = -1  # unselect
    else:
        return False
    return True




def _draw_orrery_menu(self, max_y: int, max_x: int):
    """Draw the orrery preset selection menu."""
    self.stdscr.erase()
    title = "── Solar System Orrery ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Keplerian orbital mechanics with all 8 planets"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle, curses.A_DIM)
    except curses.error:
        pass

    y = 4
    for i, (name, desc, _key) in enumerate(ORRERY_PRESETS):
        if y >= max_y - 6:
            break
        attr = curses.A_REVERSE if i == self.orrery_menu_sel else 0
        try:
            label = f"  {name:<24s} {desc}"
            self.stdscr.addstr(y, 2, label[:max_x - 4], attr)
        except curses.error:
            pass
        y += 1

    y += 1
    info_lines = [
        "Controls during simulation:",
        "  Space=play/pause  n=step  z=zoom  o=orbits  l=labels  i=info",
        "  Tab=select planet  u=unselect  +/-=speed  r=reset  R=menu  q=exit",
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




def _draw_orrery(self, max_y: int, max_x: int):
    """Draw the Solar System Orrery simulation."""
    import math

    self.stdscr.erase()
    rows = min(self.orrery_rows, max_y - 2)
    cols = min(self.orrery_cols, max_x)
    if rows < 5 or cols < 10:
        return

    # Build display buffer
    buf = [[' '] * cols for _ in range(rows)]
    color_buf = [[0] * cols for _ in range(rows)]

    # Background stars
    for sr, sc in self.orrery_bg_stars:
        if 0 <= sr < rows and 0 <= sc < cols:
            buf[sr][sc] = '.'
            color_buf[sr][sc] = 8  # dim

    cx, cy, scale = self._orrery_get_scale()

    # Draw orbit ellipses
    if self.orrery_show_orbits:
        for planet in self.orrery_planets:
            a = planet["a"]
            e = planet["e"]
            b = a * math.sqrt(1 - e * e)
            # Sample points along the ellipse
            steps = max(60, int(a * scale * 4))
            for s in range(steps):
                theta = 2.0 * math.pi * s / steps
                r_au = a * (1 - e * e) / (1 + e * math.cos(theta))
                ex = r_au * math.cos(theta)
                ey = r_au * math.sin(theta)
                sc_pos = int(round(cx + ex * scale))
                sr_pos = int(round(cy + ey * scale * 0.5))
                if 0 <= sr_pos < rows and 0 <= sc_pos < cols:
                    if buf[sr_pos][sc_pos] == ' ':
                        buf[sr_pos][sc_pos] = '·'
                        color_buf[sr_pos][sc_pos] = 8

    # Draw asteroid belt
    t = self.orrery_time
    for ast in self.orrery_asteroids:
        asc, asr, _r, _nu = self._orrery_body_pos(ast, t)
        ac, ar = int(round(asc)), int(round(asr))
        if 0 <= ar < rows and 0 <= ac < cols:
            if buf[ar][ac] == ' ' or buf[ar][ac] == '·':
                buf[ar][ac] = '·'
                color_buf[ar][ac] = 7  # white dim

    # Draw comet trails and comets
    for comet in self.orrery_comets:
        trail = comet["trail"]
        trail_chars = " .·:;=+*"
        for ti, (tc, tr) in enumerate(trail):
            if 0 <= tr < rows and 0 <= tc < cols:
                frac = ti / max(len(trail), 1)
                ci = int(frac * (len(trail_chars) - 1))
                if buf[tr][tc] == ' ':
                    buf[tr][tc] = trail_chars[ci]
                    color_buf[tr][tc] = 6  # cyan

        sc_pos, sr_pos, _r, _nu = self._orrery_body_pos(comet, t)
        cc, cr = int(round(sc_pos)), int(round(sr_pos))
        if 0 <= cr < rows and 0 <= cc < cols:
            buf[cr][cc] = '*'
            color_buf[cr][cc] = 6

    # Draw Sun
    sun_c = int(round(cx))
    sun_r = int(round(cy))
    sun_chars = [('@', 0, 0), ('*', 0, -1), ('*', 0, 1), ('*', -1, 0), ('*', 1, 0)]
    for ch, dr, dc in sun_chars:
        sr_pos = sun_r + dr
        sc_pos = sun_c + dc
        if 0 <= sr_pos < rows and 0 <= sc_pos < cols:
            buf[sr_pos][sc_pos] = ch
            color_buf[sr_pos][sc_pos] = 3  # yellow

    # Draw planet trails
    trail_ch = '·'
    for pi, planet in enumerate(self.orrery_planets):
        trail = planet["trail"]
        for ti, (tc, tr) in enumerate(trail[:-1] if trail else []):
            if 0 <= tr < rows and 0 <= tc < cols:
                if buf[tr][tc] in (' ', '·') and color_buf[tr][tc] in (0, 8):
                    buf[tr][tc] = trail_ch
                    color_buf[tr][tc] = planet["color"]

    # Draw planets
    planet_sizes = {"Jupiter": "O", "Saturn": "O", "Uranus": "o", "Neptune": "o"}
    for pi, planet in enumerate(self.orrery_planets):
        sc_pos, sr_pos, r_au, nu = self._orrery_body_pos(planet, t)
        pc, pr = int(round(sc_pos)), int(round(sr_pos))
        if 0 <= pr < rows and 0 <= pc < cols:
            ch = planet_sizes.get(planet["name"], "o")
            if pi == self.orrery_selected:
                ch = '#'  # highlight selected
            buf[pr][pc] = ch
            color_buf[pr][pc] = planet["color"]

            # Planet label
            if self.orrery_show_labels:
                label = planet["char"]
                lc = pc + 2
                if lc < cols - 1:
                    try:
                        buf[pr][lc] = label
                        color_buf[pr][lc] = planet["color"]
                    except IndexError:
                        pass

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
                    if cp == 3:  # yellow / Sun
                        attr |= curses.A_BOLD
                    self.stdscr.chgat(r, c, run, attr)
                except curses.error:
                    pass
                c += run
            else:
                c += 1

    # Info panel for selected planet
    if self.orrery_show_info and 0 <= self.orrery_selected < len(self.orrery_planets):
        planet = self.orrery_planets[self.orrery_selected]
        sc_pos, sr_pos, r_au, nu = self._orrery_body_pos(planet, self.orrery_time)
        info_lines = [
            f" {planet['name']} ",
            f" a={planet['a']:.3f} AU  e={planet['e']:.4f}",
            f" T={planet['T']:.3f} yr",
            f" r={r_au:.3f} AU",
            f" nu={math.degrees(nu):.1f} deg",
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
    zoom_label = {"full": "Full", "inner": "Inner", "outer": "Outer"}
    status = (f" Gen:{self.orrery_generation} | {self.orrery_preset_name} | "
              f"t={self.orrery_time:.2f}yr | zoom={zoom_label.get(self.orrery_zoom, self.orrery_zoom)} | "
              f"speed={self.orrery_speed_scale:.2f}x ")
    try:
        self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass

    # Hint bar
    hint = " Space=play n=step z=zoom o=orbits l=labels i=info Tab=planet u=unsel +/-=speed r=reset R=menu q=exit"
    try:
        self.stdscr.addstr(status_y + 1, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass




def register(App):
    """Register orrery mode methods on the App class."""
    App._enter_orrery_mode = _enter_orrery_mode
    App._exit_orrery_mode = _exit_orrery_mode
    App._orrery_solve_kepler = _orrery_solve_kepler
    App._orrery_init = _orrery_init
    App._orrery_get_scale = _orrery_get_scale
    App._orrery_body_pos = _orrery_body_pos
    App._orrery_step = _orrery_step
    App._handle_orrery_menu_key = _handle_orrery_menu_key
    App._handle_orrery_key = _handle_orrery_key
    App._draw_orrery_menu = _draw_orrery_menu
    App._draw_orrery = _draw_orrery

