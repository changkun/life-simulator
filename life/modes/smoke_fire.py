"""Mode: smokefire — simulation mode for the life package."""
import curses
import math
import random
import time


def _smokefire_build_preset(self, name: str):
    """Set up a smoke-fire preset scene."""
    rows, cols = self.smokefire_rows, self.smokefire_cols
    self.smokefire_temp = [[0.0] * cols for _ in range(rows)]
    self.smokefire_smoke = [[0.0] * cols for _ in range(rows)]
    self.smokefire_fuel = [[0.0] * cols for _ in range(rows)]
    self.smokefire_vx = [[0.0] * cols for _ in range(rows)]
    self.smokefire_vy = [[0.0] * cols for _ in range(rows)]
    self.smokefire_sources = []

    if name == "campfire":
        self.smokefire_buoyancy = 0.15
        self.smokefire_turbulence = 0.04
        self.smokefire_cooling = 0.012
        self.smokefire_smoke_rate = 0.3
        self.smokefire_wind = 0.0
        mid = cols // 2
        base_r = rows - 3
        # fuel logs
        for c in range(mid - 4, mid + 5):
            for r in range(base_r - 1, base_r + 1):
                if 0 <= r < rows and 0 <= c < cols:
                    self.smokefire_fuel[r][c] = 0.9
        # fire sources
        for c in range(mid - 3, mid + 4):
            self.smokefire_sources.append((base_r - 2, c, 0.7 + random.random() * 0.3))

    elif name == "wildfire":
        self.smokefire_buoyancy = 0.12
        self.smokefire_turbulence = 0.06
        self.smokefire_cooling = 0.008
        self.smokefire_smoke_rate = 0.4
        self.smokefire_wind = 0.02
        # scatter fuel across the ground
        for r in range(rows * 2 // 3, rows - 1):
            for c in range(cols):
                if random.random() < 0.7:
                    self.smokefire_fuel[r][c] = 0.3 + random.random() * 0.7
        # ignition points on the left
        for r in range(rows * 2 // 3, rows - 1, 3):
            self.smokefire_sources.append((r, 2, 0.9))
            self.smokefire_temp[r][2] = 1.0

    elif name == "explosion":
        self.smokefire_buoyancy = 0.25
        self.smokefire_turbulence = 0.12
        self.smokefire_cooling = 0.02
        self.smokefire_smoke_rate = 0.6
        self.smokefire_wind = 0.0
        mid_r, mid_c = rows * 2 // 3, cols // 2
        # central blast zone
        for dr in range(-5, 6):
            for dc in range(-5, 6):
                r, c = mid_r + dr, mid_c + dc
                if 0 <= r < rows and 0 <= c < cols:
                    dist = (dr * dr + dc * dc) ** 0.5
                    if dist < 6:
                        intensity = max(0.0, 1.0 - dist / 6.0)
                        self.smokefire_temp[r][c] = intensity
                        self.smokefire_fuel[r][c] = intensity * 0.5
                        # radial velocity
                        if dist > 0:
                            self.smokefire_vx[r][c] = dc / dist * 0.3
                            self.smokefire_vy[r][c] = dr / dist * 0.3 - 0.2
        self.smokefire_sources.append((mid_r, mid_c, 1.0))

    elif name == "candles":
        self.smokefire_buoyancy = 0.1
        self.smokefire_turbulence = 0.02
        self.smokefire_cooling = 0.018
        self.smokefire_smoke_rate = 0.15
        self.smokefire_wind = 0.0
        base_r = rows - 3
        spacing = max(3, cols // 7)
        for i in range(6):
            c = spacing + i * spacing
            if c < cols:
                self.smokefire_sources.append((base_r - 2, c, 0.5 + random.random() * 0.3))
                self.smokefire_fuel[base_r - 1][c] = 0.6
                self.smokefire_fuel[base_r][c] = 0.6

    elif name == "inferno":
        self.smokefire_buoyancy = 0.2
        self.smokefire_turbulence = 0.08
        self.smokefire_cooling = 0.006
        self.smokefire_smoke_rate = 0.5
        self.smokefire_wind = 0.01
        base_r = rows - 3
        for c in range(2, cols - 2):
            self.smokefire_fuel[base_r][c] = 0.8 + random.random() * 0.2
            self.smokefire_fuel[base_r - 1][c] = 0.5 + random.random() * 0.3
            if random.random() < 0.3:
                self.smokefire_sources.append((base_r - 2, c, 0.8 + random.random() * 0.2))

    elif name == "smokestack":
        self.smokefire_buoyancy = 0.18
        self.smokefire_turbulence = 0.05
        self.smokefire_cooling = 0.01
        self.smokefire_smoke_rate = 0.5
        self.smokefire_wind = 0.03
        mid = cols // 2
        base_r = rows - 2
        # chimney outline (fuel as structure marker)
        for r in range(base_r - 10, base_r + 1):
            for dc in [-2, -1, 2, 3]:
                c = mid + dc
                if 0 <= c < cols and 0 <= r < rows:
                    self.smokefire_fuel[r][c] = 0.05  # structural, won't really burn
        # smoke/fire source at chimney top
        for dc in range(0, 2):
            c = mid + dc
            if 0 <= c < cols:
                self.smokefire_sources.append((base_r - 11, c, 0.6))



def _smokefire_init(self, preset: str):
    """Initialize the smoke-fire grid."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.smokefire_rows = max_y - 3
    self.smokefire_cols = (max_x - 1) // 2
    if self.smokefire_rows < 10:
        self.smokefire_rows = 10
    if self.smokefire_cols < 10:
        self.smokefire_cols = 10
    self.smokefire_generation = 0
    self.smokefire_cursor_r = self.smokefire_rows // 2
    self.smokefire_cursor_c = self.smokefire_cols // 2
    self._smokefire_build_preset(preset)



def _smokefire_step(self):
    """Advance the smoke-fire simulation by one tick."""
    rows = self.smokefire_rows
    cols = self.smokefire_cols
    temp = self.smokefire_temp
    smoke = self.smokefire_smoke
    fuel = self.smokefire_fuel
    vx = self.smokefire_vx
    vy = self.smokefire_vy

    # New grids
    nt = [[0.0] * cols for _ in range(rows)]
    ns = [[0.0] * cols for _ in range(rows)]
    nf = [[fuel[r][c] for c in range(cols)] for r in range(rows)]
    nvx = [[0.0] * cols for _ in range(rows)]
    nvy = [[0.0] * cols for _ in range(rows)]

    buoy = self.smokefire_buoyancy
    turb = self.smokefire_turbulence
    cool = self.smokefire_cooling
    srate = self.smokefire_smoke_rate
    wind = self.smokefire_wind

    for r in range(rows):
        for c in range(cols):
            t = temp[r][c]
            s = smoke[r][c]
            f = fuel[r][c]
            cur_vx = vx[r][c]
            cur_vy = vy[r][c]

            # Buoyancy: heat rises
            cur_vy -= buoy * t
            # Wind
            cur_vx += wind
            # Turbulence
            cur_vx += (random.random() - 0.5) * turb * (1.0 + t * 2.0)
            cur_vy += (random.random() - 0.5) * turb * 0.5

            # Damping
            cur_vx *= 0.85
            cur_vy *= 0.85

            # Combustion: fuel burns if hot enough
            if t > 0.2 and f > 0.01:
                burn = min(f, 0.05 * t)
                nf[r][c] -= burn
                t += burn * 3.0  # heat from combustion

            # Spread fire to neighbors if hot
            if t > 0.4:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if fuel[nr][nc] > 0.1 and temp[nr][nc] < 0.3:
                            nf[nr][nc] -= 0.002
                            nt[nr][nc] += 0.05 * t

            # Smoke production from heat
            smoke_add = t * srate * 0.3
            s += smoke_add

            # Cooling
            t -= cool * (1.0 + (rows - 1 - r) / rows * 0.5)

            # Smoke dissipation
            s *= 0.985
            s -= 0.003

            t = max(0.0, min(1.0, t))
            s = max(0.0, min(1.0, s))

            # Advection: move temperature and smoke by velocity
            src_r = r - cur_vy
            src_c = c - cur_vx
            # Bilinear sample from source
            sr0 = int(src_r)
            sc0 = int(src_c)
            fr = src_r - sr0
            fc = src_c - sc0
            sr1 = sr0 + 1
            sc1 = sc0 + 1

            sampled_t = 0.0
            sampled_s = 0.0
            total_w = 0.0
            for (sr, wr) in [(sr0, 1.0 - fr), (sr1, fr)]:
                for (sc, wc) in [(sc0, 1.0 - fc), (sc1, fc)]:
                    if 0 <= sr < rows and 0 <= sc < cols:
                        w = wr * wc
                        sampled_t += temp[sr][sc] * w
                        sampled_s += smoke[sr][sc] * w
                        total_w += w

            if total_w > 0:
                blend = 0.6
                t = t * (1.0 - blend) + (sampled_t / total_w) * blend
                s = s * (1.0 - blend) + (sampled_s / total_w) * blend

            # Diffusion with neighbors
            diff_t = 0.0
            diff_s = 0.0
            n_count = 0
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    diff_t += temp[nr][nc]
                    diff_s += smoke[nr][nc]
                    n_count += 1
            if n_count > 0:
                t = t * 0.8 + (diff_t / n_count) * 0.2
                s = s * 0.85 + (diff_s / n_count) * 0.15

            nt[r][c] += t
            nt[r][c] = max(0.0, min(1.0, nt[r][c]))
            ns[r][c] += s
            ns[r][c] = max(0.0, min(1.0, ns[r][c]))
            nvx[r][c] = cur_vx
            nvy[r][c] = cur_vy

    # Apply fire sources
    for (sr, sc, intensity) in self.smokefire_sources:
        if 0 <= sr < rows and 0 <= sc < cols:
            flicker = 0.7 + random.random() * 0.3
            nt[sr][sc] = min(1.0, nt[sr][sc] + intensity * flicker)
            # Also add slight heat to neighbors for wider flames
            for dr, dc in [(-1, 0), (0, -1), (0, 1)]:
                nr, nc = sr + dr, sc + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    nt[nr][nc] = min(1.0, nt[nr][nc] + intensity * flicker * 0.3)

    self.smokefire_temp = nt
    self.smokefire_smoke = ns
    self.smokefire_fuel = nf
    self.smokefire_vx = nvx
    self.smokefire_vy = nvy
    self.smokefire_generation += 1



def _enter_smokefire_mode(self):
    """Enter smoke-fire mode — show preset menu."""
    self.smokefire_menu = True
    self.smokefire_menu_sel = 0
    self._flash("Smoke & Fire — select a scene")



def _exit_smokefire_mode(self):
    """Exit smoke-fire mode."""
    self.smokefire_mode = False
    self.smokefire_menu = False
    self.smokefire_running = False
    self.smokefire_temp = []
    self.smokefire_smoke = []
    self.smokefire_fuel = []
    self.smokefire_vx = []
    self.smokefire_vy = []
    self.smokefire_sources = []
    self._flash("Smoke & Fire mode OFF")



def _handle_smokefire_menu_key(self, key: int) -> bool:
    """Handle keys in the smoke-fire preset menu."""
    if key == -1:
        return True
    n = len(self.SMOKEFIRE_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.smokefire_menu_sel = (self.smokefire_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.smokefire_menu_sel = (self.smokefire_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.smokefire_menu = False
        self._flash("Smoke & Fire cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        name, _desc, preset_id = self.SMOKEFIRE_PRESETS[self.smokefire_menu_sel]
        self.smokefire_menu = False
        self.smokefire_mode = True
        self.smokefire_running = False
        self.smokefire_preset_name = name
        self._smokefire_init(preset_id)
        self._flash(f"Smoke & Fire [{name}] — Space=play, arrows=cursor, f=add fire, q=exit")
        return True
    return True



def _handle_smokefire_key(self, key: int) -> bool:
    """Handle keys while in smoke-fire mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_smokefire_mode()
        return True
    if key == ord(" "):
        self.smokefire_running = not self.smokefire_running
        self._flash("Playing" if self.smokefire_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self._smokefire_step()
        return True
    if key == ord("R"):
        self.smokefire_mode = False
        self.smokefire_menu = True
        self.smokefire_menu_sel = 0
        self._flash("Smoke & Fire — select a scene")
        return True
    # Cursor movement
    if key == curses.KEY_UP or key == ord("k"):
        self.smokefire_cursor_r = max(0, self.smokefire_cursor_r - 1)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.smokefire_cursor_r = min(self.smokefire_rows - 1, self.smokefire_cursor_r + 1)
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        self.smokefire_cursor_c = max(0, self.smokefire_cursor_c - 1)
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        self.smokefire_cursor_c = min(self.smokefire_cols - 1, self.smokefire_cursor_c + 1)
        return True
    # Add/remove fire source at cursor
    if key == ord("f") or key in (10, 13, curses.KEY_ENTER):
        r, c = self.smokefire_cursor_r, self.smokefire_cursor_c
        # Check if source already exists nearby
        removed = False
        for i, (sr, sc, _si) in enumerate(self.smokefire_sources):
            if abs(sr - r) <= 1 and abs(sc - c) <= 1:
                self.smokefire_sources.pop(i)
                self._flash("Fire source removed")
                removed = True
                break
        if not removed:
            self.smokefire_sources.append((r, c, 0.8))
            self._flash("Fire source added")
        return True
    # Add fuel at cursor
    if key == ord("F"):
        r, c = self.smokefire_cursor_r, self.smokefire_cursor_c
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.smokefire_rows and 0 <= nc < self.smokefire_cols:
                    self.smokefire_fuel[nr][nc] = min(1.0, self.smokefire_fuel[nr][nc] + 0.5)
        self._flash("Fuel added")
        return True
    # Adjust parameters
    if key == ord("b"):
        self.smokefire_buoyancy = min(0.5, self.smokefire_buoyancy + 0.02)
        self._flash(f"Buoyancy: {self.smokefire_buoyancy:.2f}")
        return True
    if key == ord("B"):
        self.smokefire_buoyancy = max(0.0, self.smokefire_buoyancy - 0.02)
        self._flash(f"Buoyancy: {self.smokefire_buoyancy:.2f}")
        return True
    if key == ord("t"):
        self.smokefire_turbulence = min(0.3, self.smokefire_turbulence + 0.01)
        self._flash(f"Turbulence: {self.smokefire_turbulence:.2f}")
        return True
    if key == ord("T"):
        self.smokefire_turbulence = max(0.0, self.smokefire_turbulence - 0.01)
        self._flash(f"Turbulence: {self.smokefire_turbulence:.2f}")
        return True
    if key == ord("w"):
        self.smokefire_wind += 0.01
        self._flash(f"Wind: {self.smokefire_wind:.2f}")
        return True
    if key == ord("W"):
        self.smokefire_wind -= 0.01
        self._flash(f"Wind: {self.smokefire_wind:.2f}")
        return True
    if key == ord("c"):
        self.smokefire_cooling = min(0.1, self.smokefire_cooling + 0.002)
        self._flash(f"Cooling: {self.smokefire_cooling:.3f}")
        return True
    if key == ord("C"):
        self.smokefire_cooling = max(0.0, self.smokefire_cooling - 0.002)
        self._flash(f"Cooling: {self.smokefire_cooling:.3f}")
        return True
    # Speed
    if key == ord(">"):
        self.smokefire_steps_per_frame = min(10, self.smokefire_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.smokefire_steps_per_frame}")
        return True
    if key == ord("<"):
        self.smokefire_steps_per_frame = max(1, self.smokefire_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.smokefire_steps_per_frame}")
        return True
    return True



def _draw_smokefire_menu(self, max_y: int, max_x: int):
    """Draw the smoke-fire preset selection menu."""
    self.stdscr.erase()
    title = "── Smoke & Fire ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Particle-based fire and smoke simulation with buoyant flow"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.SMOKEFIRE_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.SMOKEFIRE_PRESETS):
        y = 5 + i
        if y >= max_y - 12:
            break
        line = f"  {name:<18s} {desc}"
        attr = curses.color_pair(6)
        if i == self.smokefire_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_lines = [
        "",
        "Flames burn at source points, heat rises with buoyancy,",
        "smoke billows upward while cooling and dispersing.",
        "Temperature-mapped colors: white-hot \u2192 yellow \u2192 orange \u2192 red \u2192 dark smoke \u2192 gray",
        "",
        "Controls: f=add/remove fire, F=add fuel, b/B=buoyancy, t/T=turbulence,",
        "          w/W=wind, c/C=cooling, >/<=speed, R=preset menu, q=exit",
    ]
    base_y = 5 + n + 1
    for i, line in enumerate(info_lines):
        y = base_y + i
        if y >= max_y - 2:
            break
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 3], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    footer = "↑/↓ select · Enter confirm · q cancel"
    try:
        self.stdscr.addstr(max_y - 2, max(0, (max_x - len(footer)) // 2), footer,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_smokefire(self, max_y: int, max_x: int):
    """Draw the smoke-fire simulation."""
    self.stdscr.erase()
    rows = self.smokefire_rows
    cols = self.smokefire_cols
    temp = self.smokefire_temp
    smoke_grid = self.smokefire_smoke
    fuel = self.smokefire_fuel

    # Fire/smoke color chars — temperature-mapped
    # white-hot > yellow > orange > red > dark smoke > fading gray
    fire_chars = [
        " ",       # 0: empty
        "\u2591",  # 1: light shade (faint smoke)
        "\u2592",  # 2: medium shade (smoke)
        "\u2593",  # 3: dark shade (thick smoke)
        "\u2588",  # 4: full block (fire glow)
    ]

    for r in range(min(rows, max_y - 3)):
        for c in range(min(cols, (max_x - 1) // 2)):
            t = temp[r][c] if r < len(temp) and c < len(temp[0]) else 0.0
            s = smoke_grid[r][c] if r < len(smoke_grid) and c < len(smoke_grid[0]) else 0.0
            f = fuel[r][c] if r < len(fuel) and c < len(fuel[0]) else 0.0

            sx = c * 2

            # Determine what to draw
            if t > 0.7:
                # White-hot / bright yellow
                ch = fire_chars[4] * 2
                attr = curses.color_pair(3) | curses.A_BOLD  # bright yellow
                if t > 0.9:
                    attr = curses.color_pair(8) | curses.A_BOLD  # white-hot
            elif t > 0.5:
                # Orange/yellow
                ch = fire_chars[4] * 2
                attr = curses.color_pair(3)  # yellow
            elif t > 0.3:
                # Red/orange
                ch = fire_chars[4] * 2
                attr = curses.color_pair(2)  # red
            elif t > 0.15:
                # Dark red ember
                ch = fire_chars[3] * 2
                attr = curses.color_pair(2) | curses.A_DIM
            elif s > 0.3:
                # Thick smoke
                ch = fire_chars[3] * 2
                attr = curses.color_pair(8) | curses.A_DIM
            elif s > 0.15:
                # Medium smoke
                ch = fire_chars[2] * 2
                attr = curses.color_pair(8) | curses.A_DIM
            elif s > 0.05:
                # Light smoke
                ch = fire_chars[1] * 2
                attr = curses.color_pair(8) | curses.A_DIM
            elif f > 0.3:
                # Fuel on ground (unburnt)
                ch = fire_chars[2] * 2
                attr = curses.color_pair(4) | curses.A_DIM  # green = vegetation/fuel
            elif f > 0.01:
                ch = fire_chars[1] * 2
                attr = curses.color_pair(4) | curses.A_DIM
            else:
                continue  # empty, skip

            # Cursor highlight
            if r == self.smokefire_cursor_r and c == self.smokefire_cursor_c:
                attr = attr | curses.A_REVERSE

            try:
                self.stdscr.addstr(r + 1, sx, ch, attr)
            except curses.error:
                pass

    # Draw cursor if on empty cell
    cr, cc = self.smokefire_cursor_r, self.smokefire_cursor_c
    t_cur = temp[cr][cc] if 0 <= cr < rows and 0 <= cc < cols else 0.0
    s_cur = smoke_grid[cr][cc] if 0 <= cr < rows and 0 <= cc < cols else 0.0
    f_cur = fuel[cr][cc] if 0 <= cr < rows and 0 <= cc < cols else 0.0
    if t_cur < 0.05 and s_cur < 0.05 and f_cur < 0.01:
        try:
            self.stdscr.addstr(cr + 1, cc * 2, "++", curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Status bar
    hint_y = max_y - 2
    status = (f" [{self.smokefire_preset_name}] Gen:{self.smokefire_generation}"
              f" Buoy:{self.smokefire_buoyancy:.2f} Turb:{self.smokefire_turbulence:.2f}"
              f" Cool:{self.smokefire_cooling:.3f} Wind:{self.smokefire_wind:.2f}"
              f" Sources:{len(self.smokefire_sources)}"
              f" {'▶ PLAY' if self.smokefire_running else '⏸ PAUSE'}")
    try:
        self.stdscr.addstr(0, 0, status[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if self.message and time.time() - self.message_time < 3.0:
        hint = f" {self.message}"
    else:
        hint = " [Space]=play [n]=step [f]=fire [F]=fuel [b/B]=buoy [t/T]=turb [w/W]=wind [c/C]=cool [R]=menu [q]=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register smokefire mode methods on the App class."""
    App._smokefire_build_preset = _smokefire_build_preset
    App._smokefire_init = _smokefire_init
    App._smokefire_step = _smokefire_step
    App._enter_smokefire_mode = _enter_smokefire_mode
    App._exit_smokefire_mode = _exit_smokefire_mode
    App._handle_smokefire_menu_key = _handle_smokefire_menu_key
    App._handle_smokefire_key = _handle_smokefire_key
    App._draw_smokefire_menu = _draw_smokefire_menu
    App._draw_smokefire = _draw_smokefire

