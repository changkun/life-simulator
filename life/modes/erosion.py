"""Mode: erosion — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_erosion_mode(self):
    """Enter Hydraulic Erosion mode — show preset menu."""
    self.erosion_menu = True
    self.erosion_menu_sel = 0
    self._flash("Hydraulic Erosion — select a scenario")



def _exit_erosion_mode(self):
    """Exit Hydraulic Erosion mode."""
    self.erosion_mode = False
    self.erosion_menu = False
    self.erosion_running = False
    self.erosion_terrain = []
    self.erosion_water = []
    self.erosion_sediment = []
    self._flash("Erosion mode OFF")



def _erosion_generate_terrain(self, rows: int, cols: int, terrain_type: str) -> list:
    """Generate a heightmap using layered noise (diamond-square inspired)."""
    terrain = [[0.0] * cols for _ in range(rows)]

    # Use multiple octaves of random smooth noise
    def _smooth_noise(freq: float, amp: float):
        # Generate sparse random grid then interpolate
        sr = max(2, int(rows / freq))
        sc = max(2, int(cols / freq))
        sparse_r = max(2, rows // sr + 2)
        sparse_c = max(2, cols // sc + 2)
        sparse = [[random.random() for _ in range(sparse_c)] for _ in range(sparse_r)]
        for r in range(rows):
            for c in range(cols):
                gr = r / sr
                gc = c / sc
                r0 = int(gr) % sparse_r
                r1 = (r0 + 1) % sparse_r
                c0 = int(gc) % sparse_c
                c1 = (c0 + 1) % sparse_c
                fr = gr - int(gr)
                fc = gc - int(gc)
                # Bilinear interpolation
                top = sparse[r0][c0] * (1 - fc) + sparse[r0][c1] * fc
                bot = sparse[r1][c0] * (1 - fc) + sparse[r1][c1] * fc
                val = top * (1 - fr) + bot * fr
                terrain[r][c] += val * amp

    if terrain_type == "gentle":
        _smooth_noise(4, 0.5)
        _smooth_noise(8, 0.3)
        _smooth_noise(16, 0.15)
    elif terrain_type == "steep":
        _smooth_noise(3, 0.6)
        _smooth_noise(6, 0.3)
        _smooth_noise(12, 0.1)
        # Add ridge line
        mid_c = cols // 2
        for r in range(rows):
            for c in range(cols):
                dist = abs(c - mid_c) / max(1, cols)
                terrain[r][c] += 0.3 * max(0, 1.0 - dist * 3)
    elif terrain_type == "plateau":
        _smooth_noise(5, 0.3)
        _smooth_noise(10, 0.15)
        # Flat top with cliff edges
        for r in range(rows):
            for c in range(cols):
                edge_dist = min(r, rows - 1 - r, c, cols - 1 - c) / max(1, min(rows, cols) * 0.3)
                terrain[r][c] += 0.4 * min(1.0, edge_dist)
    elif terrain_type == "rough":
        _smooth_noise(3, 0.35)
        _smooth_noise(6, 0.25)
        _smooth_noise(12, 0.2)
        _smooth_noise(24, 0.15)
    elif terrain_type == "alpine":
        _smooth_noise(3, 0.5)
        _smooth_noise(6, 0.3)
        _smooth_noise(12, 0.15)
        # Exaggerate peaks
        for r in range(rows):
            for c in range(cols):
                terrain[r][c] = terrain[r][c] ** 1.3
    elif terrain_type == "hills":
        _smooth_noise(5, 0.4)
        _smooth_noise(10, 0.3)
        _smooth_noise(20, 0.1)
    elif terrain_type == "mesa":
        _smooth_noise(4, 0.3)
        _smooth_noise(8, 0.2)
        # Quantize heights for layered look
        for r in range(rows):
            for c in range(cols):
                terrain[r][c] = int(terrain[r][c] * 6) / 6.0
    elif terrain_type == "volcano":
        _smooth_noise(6, 0.2)
        _smooth_noise(12, 0.1)
        # Central peak
        cr_center, cc_center = rows // 2, cols // 2
        max_dist = math.sqrt(cr_center ** 2 + cc_center ** 2)
        for r in range(rows):
            for c in range(cols):
                dist = math.sqrt((r - cr_center) ** 2 + (c - cc_center) ** 2)
                terrain[r][c] += 0.6 * max(0, 1.0 - dist / (max_dist * 0.6))

    # Normalize to [0, 1]
    min_h = min(terrain[r][c] for r in range(rows) for c in range(cols))
    max_h = max(terrain[r][c] for r in range(rows) for c in range(cols))
    rng = max_h - min_h if max_h > min_h else 1.0
    for r in range(rows):
        for c in range(cols):
            terrain[r][c] = (terrain[r][c] - min_h) / rng
    return terrain



def _erosion_init(self, preset_idx: int):
    """Initialize hydraulic erosion simulation with the given preset."""
    (name, _desc, rain, evap, sol, dep, ttype) = self.EROSION_PRESETS[preset_idx]
    self.erosion_preset_name = name
    self.erosion_generation = 0
    self.erosion_running = False
    self.erosion_rain_rate = rain
    self.erosion_evap_rate = evap
    self.erosion_solubility = sol
    self.erosion_deposition = dep
    self.erosion_total_eroded = 0.0

    max_y, max_x = self.stdscr.getmaxyx()
    self.erosion_rows = max(10, max_y - 4)
    self.erosion_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.erosion_rows, self.erosion_cols

    self.erosion_terrain = self._erosion_generate_terrain(rows, cols, ttype)
    self.erosion_water = [[0.0] * cols for _ in range(rows)]
    self.erosion_sediment = [[0.0] * cols for _ in range(rows)]

    self.erosion_menu = False
    self.erosion_mode = True
    self._flash(f"Erosion: {name} — Space to start")



def _erosion_step(self):
    """Advance hydraulic erosion by one step.

    Simplified shallow-water erosion model:
    1. Rain — add water uniformly (with slight randomness)
    2. Flow — water flows to lowest neighbor(s), carrying sediment
    3. Erode — flowing water picks up sediment proportional to flow speed
    4. Deposit — sediment drops when water slows or pools
    5. Evaporate — water evaporates, depositing remaining sediment
    """
    terrain = self.erosion_terrain
    water = self.erosion_water
    sediment = self.erosion_sediment
    rows, cols = self.erosion_rows, self.erosion_cols
    rain = self.erosion_rain_rate
    evap = self.erosion_evap_rate
    sol = self.erosion_solubility
    dep = self.erosion_deposition

    # 1. Rainfall — add water everywhere with some spatial variation
    for r in range(rows):
        for c in range(cols):
            water[r][c] += rain * (0.8 + 0.4 * random.random())

    # 2–4. Flow, erosion, deposition
    new_water = [[0.0] * cols for _ in range(rows)]
    new_sediment = [[0.0] * cols for _ in range(rows)]
    total_eroded = 0.0

    for r in range(rows):
        for c in range(cols):
            h = terrain[r][c] + water[r][c]  # effective height (terrain + water)
            w = water[r][c]
            s = sediment[r][c]

            if w < 1e-6:
                new_water[r][c] += w
                new_sediment[r][c] += s
                continue

            # Find neighbors and height differences
            neighbors = []
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    nh = terrain[nr][nc] + water[nr][nc]
                    if nh < h:
                        neighbors.append((nr, nc, h - nh))

            if not neighbors:
                # No downhill — water pools here
                new_water[r][c] += w
                # Deposit sediment when pooling
                deposit_amt = min(s, dep * w)
                terrain[r][c] += deposit_amt
                new_sediment[r][c] += s - deposit_amt
                continue

            # Distribute water to lower neighbors proportional to height diff
            total_diff = sum(d for _, _, d in neighbors)
            flow_out = min(w, total_diff * 0.5)  # limit flow to available water

            for nr, nc, diff in neighbors:
                frac = diff / total_diff
                flow = flow_out * frac
                # Erosion: proportional to flow velocity (slope * flow)
                velocity = diff * flow
                erode_amt = sol * velocity
                erode_amt = min(erode_amt, terrain[r][c] * 0.1)  # cap erosion
                terrain[r][c] -= erode_amt
                total_eroded += erode_amt

                # Move water and sediment (existing + newly eroded) to neighbor
                sed_flow = (s * frac * flow_out / max(w, 1e-9)) + erode_amt
                new_water[nr][nc] += flow
                new_sediment[nr][nc] += sed_flow

            # Keep remaining water and sediment at current cell
            remaining_w = w - flow_out
            remaining_s = s * (1.0 - flow_out / max(w, 1e-9))
            remaining_s = max(0.0, remaining_s)
            new_water[r][c] += remaining_w
            new_sediment[r][c] += remaining_s

    # 5. Evaporation and final deposition
    for r in range(rows):
        for c in range(cols):
            w = new_water[r][c]
            s = new_sediment[r][c]
            # Evaporate
            evap_amt = min(w, evap)
            w -= evap_amt
            # Deposit sediment from evaporating water
            if w < 1e-6 and s > 0:
                terrain[r][c] += s
                s = 0.0
            elif s > dep * 2:
                # Excess sediment deposits
                deposit = min(s - dep, dep * 0.5)
                terrain[r][c] += deposit
                s -= deposit
            new_water[r][c] = max(0.0, w)
            new_sediment[r][c] = max(0.0, s)

    self.erosion_water = new_water
    self.erosion_sediment = new_sediment
    self.erosion_total_eroded += total_eroded
    self.erosion_generation += 1

    # Water exits at boundaries (drain off edges)
    for r in range(rows):
        for c in (0, cols - 1):
            self.erosion_water[r][c] *= 0.5
            self.erosion_sediment[r][c] *= 0.5
    for c in range(cols):
        for r in (0, rows - 1):
            self.erosion_water[r][c] *= 0.5
            self.erosion_sediment[r][c] *= 0.5



def _handle_erosion_menu_key(self, key: int) -> bool:
    """Handle input in erosion preset menu."""
    n = len(self.EROSION_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.erosion_menu_sel = (self.erosion_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.erosion_menu_sel = (self.erosion_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._erosion_init(self.erosion_menu_sel)
    elif key in (ord("q"), 27):
        self.erosion_menu = False
        self._flash("Erosion cancelled")
    return True



def _handle_erosion_key(self, key: int) -> bool:
    """Handle input in active erosion simulation."""
    if key == ord(" "):
        self.erosion_running = not self.erosion_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.erosion_steps_per_frame):
            self._erosion_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.EROSION_PRESETS)
                    if p[0] == self.erosion_preset_name), 0)
        self._erosion_init(idx)
        self.erosion_running = False
    elif key in (ord("R"), ord("m")):
        self.erosion_mode = False
        self.erosion_running = False
        self.erosion_menu = True
        self.erosion_menu_sel = 0
    elif key == ord("w") or key == ord("W"):
        delta = 0.002 if key == ord("w") else -0.002
        self.erosion_rain_rate = max(0.001, min(0.05, self.erosion_rain_rate + delta))
        self._flash(f"Rain rate = {self.erosion_rain_rate:.3f}")
    elif key == ord("e") or key == ord("E"):
        delta = 0.002 if key == ord("e") else -0.002
        self.erosion_solubility = max(0.001, min(0.05, self.erosion_solubility + delta))
        self._flash(f"Solubility = {self.erosion_solubility:.3f}")
    elif key == ord("+") or key == ord("="):
        self.erosion_steps_per_frame = min(20, self.erosion_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.erosion_steps_per_frame}")
    elif key == ord("-"):
        self.erosion_steps_per_frame = max(1, self.erosion_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.erosion_steps_per_frame}")
    elif key == ord("<") or key == ord(","):
        self.speed_idx = max(0, self.speed_idx - 1)
    elif key == ord(">"):
        self.speed_idx = min(len(SPEEDS) - 1, self.speed_idx + 1)
    elif key in (ord("q"), 27):
        self._exit_erosion_mode()
    else:
        return True
    return True



def _draw_erosion_menu(self, max_y: int, max_x: int):
    """Draw the erosion preset selection menu."""
    self.stdscr.erase()
    title = "── Hydraulic Erosion ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.EROSION_PRESETS):
        y = 3 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<24s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.erosion_menu_sel:
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



def _draw_erosion(self, max_y: int, max_x: int):
    """Draw the active Hydraulic Erosion simulation."""
    self.stdscr.erase()
    terrain = self.erosion_terrain
    water = self.erosion_water
    rows, cols = self.erosion_rows, self.erosion_cols
    gen = self.erosion_generation
    state = "▶ RUNNING" if self.erosion_running else "⏸ PAUSED"

    # Title bar
    title = (f" Erosion: {self.erosion_preset_name}  |  step {gen}"
             f"  |  eroded: {self.erosion_total_eroded:.2f}"
             f"  |  rain={self.erosion_rain_rate:.3f}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 3
    view_cols = (max_x - 1) // 2

    # Terrain height-based color gradient + water overlay
    # Color pairs: 90=deep, 91-96=terrain gradient, 97=peak, 98=shallow water, 99=deep water
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            sx = c * 2
            sy = 1 + r
            h = terrain[r][c]
            w = water[r][c]

            if w > 0.02:
                # Water cell — blue tones based on depth
                if w > 0.08:
                    attr = curses.color_pair(99) | curses.A_BOLD
                    ch = "██"
                elif w > 0.04:
                    attr = curses.color_pair(98) | curses.A_BOLD
                    ch = "▓▓"
                else:
                    attr = curses.color_pair(98)
                    ch = "░░"
            else:
                # Terrain cell — color by height
                if h < 0.12:
                    attr = curses.color_pair(90)
                    ch = "░░"
                elif h < 0.25:
                    attr = curses.color_pair(91)
                    ch = "░░"
                elif h < 0.38:
                    attr = curses.color_pair(92)
                    ch = "▒▒"
                elif h < 0.50:
                    attr = curses.color_pair(93)
                    ch = "▒▒"
                elif h < 0.62:
                    attr = curses.color_pair(94)
                    ch = "▓▓"
                elif h < 0.75:
                    attr = curses.color_pair(95)
                    ch = "▓▓"
                elif h < 0.88:
                    attr = curses.color_pair(96) | curses.A_BOLD
                    ch = "██"
                else:
                    attr = curses.color_pair(97) | curses.A_BOLD
                    ch = "██"
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [w/W]=rain+/- [e/E]=erosion+/- [+/-]=steps/f [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register erosion mode methods on the App class."""
    App._enter_erosion_mode = _enter_erosion_mode
    App._exit_erosion_mode = _exit_erosion_mode
    App._erosion_generate_terrain = _erosion_generate_terrain
    App._erosion_init = _erosion_init
    App._erosion_step = _erosion_step
    App._handle_erosion_menu_key = _handle_erosion_menu_key
    App._handle_erosion_key = _handle_erosion_key
    App._draw_erosion_menu = _draw_erosion_menu
    App._draw_erosion = _draw_erosion

