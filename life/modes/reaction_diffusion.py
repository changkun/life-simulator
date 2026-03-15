"""Mode: rd — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS, SPEED_LABELS
from life.grid import Grid

def _enter_rd_mode(self):
    """Enter reaction-diffusion mode — show preset menu."""
    self.rd_menu = True
    self.rd_menu_sel = 0
    self._flash("Reaction-Diffusion — select a pattern type")



def _exit_rd_mode(self):
    """Exit reaction-diffusion mode."""
    self.rd_mode = False
    self.rd_menu = False
    self.rd_running = False
    self.rd_U = []
    self.rd_V = []
    self._flash("Reaction-Diffusion mode OFF")



def _rd_init(self, preset_idx: int | None = None):
    """Initialize the reaction-diffusion grid."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.rd_rows = max_y - 3
    self.rd_cols = (max_x - 1) // 2
    if self.rd_rows < 10:
        self.rd_rows = 10
    if self.rd_cols < 10:
        self.rd_cols = 10
    self.rd_generation = 0

    if preset_idx is not None and 0 <= preset_idx < len(self.RD_PRESETS):
        _, _, f, k = self.RD_PRESETS[preset_idx]
        self.rd_feed = f
        self.rd_kill = k
        self.rd_preset_name = self.RD_PRESETS[preset_idx][0]

    # Initialize U=1 everywhere, V=0 everywhere
    rows, cols = self.rd_rows, self.rd_cols
    self.rd_U = [[1.0] * cols for _ in range(rows)]
    self.rd_V = [[0.0] * cols for _ in range(rows)]

    # Seed V with random square patches to initiate pattern formation
    num_seeds = max(3, (rows * cols) // 800)
    for _ in range(num_seeds):
        sr = random.randint(rows // 4, 3 * rows // 4)
        sc = random.randint(cols // 4, 3 * cols // 4)
        sz = random.randint(2, max(3, min(rows, cols) // 12))
        for dr in range(-sz, sz + 1):
            for dc in range(-sz, sz + 1):
                r2, c2 = sr + dr, sc + dc
                if 0 <= r2 < rows and 0 <= c2 < cols:
                    self.rd_U[r2][c2] = 0.5 + random.random() * 0.05
                    self.rd_V[r2][c2] = 0.25 + random.random() * 0.05



def _rd_step(self):
    """Advance the Gray-Scott simulation by one time step."""
    rows, cols = self.rd_rows, self.rd_cols
    U, V = self.rd_U, self.rd_V
    Du, Dv = self.rd_Du, self.rd_Dv
    f, k = self.rd_feed, self.rd_kill
    dt = self.rd_dt

    # Compute new grids
    newU = [[0.0] * cols for _ in range(rows)]
    newV = [[0.0] * cols for _ in range(rows)]

    for r in range(rows):
        rp = r + 1 if r + 1 < rows else 0
        rm = r - 1  # Python handles negative indexing
        Ur = U[r]
        Vr = V[r]
        Uu = U[rm]
        Ud = U[rp]
        Vu = V[rm]
        Vd = V[rp]
        for c in range(cols):
            cp = c + 1 if c + 1 < cols else 0
            cm = c - 1  # wraps via Python negative indexing

            u = Ur[c]
            v = Vr[c]
            # 5-point discrete Laplacian
            lap_u = Uu[c] + Ud[c] + Ur[cm] + Ur[cp] - 4.0 * u
            lap_v = Vu[c] + Vd[c] + Vr[cm] + Vr[cp] - 4.0 * v

            uvv = u * v * v
            nu = u + dt * (Du * lap_u - uvv + f * (1.0 - u))
            nv = v + dt * (Dv * lap_v + uvv - (f + k) * v)

            # Clamp to [0, 1]
            if nu < 0.0:
                nu = 0.0
            elif nu > 1.0:
                nu = 1.0
            if nv < 0.0:
                nv = 0.0
            elif nv > 1.0:
                nv = 1.0

            newU[r][c] = nu
            newV[r][c] = nv

    self.rd_U = newU
    self.rd_V = newV
    self.rd_generation += 1



def _handle_rd_menu_key(self, key: int) -> bool:
    """Handle keys in the reaction-diffusion preset menu."""
    if key == -1:
        return True
    n = len(self.RD_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.rd_menu_sel = (self.rd_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.rd_menu_sel = (self.rd_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.rd_menu = False
        self._flash("Reaction-Diffusion cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self.rd_menu = False
        self.rd_mode = True
        self.rd_running = False
        self._rd_init(self.rd_menu_sel)
        name = self.RD_PRESETS[self.rd_menu_sel][0]
        self._flash(f"Reaction-Diffusion [{name}] — Space=play, f/k=adjust params, q=exit")
        return True
    return True



def _handle_rd_key(self, key: int) -> bool:
    """Handle keys while in reaction-diffusion mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_rd_mode()
        return True
    if key == ord(" "):
        self.rd_running = not self.rd_running
        self._flash("Playing" if self.rd_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.rd_running = False
        for _ in range(self.rd_steps_per_frame):
            self._rd_step()
        return True
    if key == ord("r"):
        self._rd_init()
        self._flash("Grid re-seeded")
        return True
    if key == ord("R") or key == ord("m"):
        self.rd_mode = False
        self.rd_running = False
        self.rd_menu = True
        self.rd_menu_sel = 0
        return True
    # Adjust feed rate
    if key == ord("f"):
        self.rd_feed = min(self.rd_feed + 0.001, 0.100)
        self._flash(f"Feed rate: {self.rd_feed:.4f}")
        return True
    if key == ord("F"):
        self.rd_feed = max(self.rd_feed - 0.001, 0.001)
        self._flash(f"Feed rate: {self.rd_feed:.4f}")
        return True
    # Adjust kill rate
    if key == ord("k"):
        self.rd_kill = min(self.rd_kill + 0.001, 0.100)
        self._flash(f"Kill rate: {self.rd_kill:.4f}")
        return True
    if key == ord("K"):
        self.rd_kill = max(self.rd_kill - 0.001, 0.001)
        self._flash(f"Kill rate: {self.rd_kill:.4f}")
        return True
    # Adjust simulation speed (steps per frame)
    if key == ord("+") or key == ord("="):
        self.rd_steps_per_frame = min(self.rd_steps_per_frame + 1, 20)
        self._flash(f"Steps/frame: {self.rd_steps_per_frame}")
        return True
    if key == ord("-"):
        self.rd_steps_per_frame = max(self.rd_steps_per_frame - 1, 1)
        self._flash(f"Steps/frame: {self.rd_steps_per_frame}")
        return True
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    return True



def _draw_rd_menu(self, max_y: int, max_x: int):
    """Draw the reaction-diffusion preset selection menu."""
    title = "── Reaction-Diffusion (Gray-Scott) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    subtitle = "Continuous two-chemical simulation producing organic patterns"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.RD_PRESETS)
    for i, (name, desc, f_val, k_val) in enumerate(self.RD_PRESETS):
        y = 5 + i
        if y >= max_y - 10:
            break
        line = f"  {name:<16s} f={f_val:.4f} k={k_val:.4f}  {desc}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.rd_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    info_y = 5 + min(n, max_y - 15) + 1
    info_lines = [
        "The Gray-Scott model simulates two chemicals (U and V) that",
        "diffuse and react: U + 2V → 3V. The feed rate (f) controls",
        "how fast U is replenished; the kill rate (k) controls how",
        "fast V decays. Small parameter changes produce very different",
        "self-organizing patterns: spots, stripes, coral, and more.",
    ]
    for i, info in enumerate(info_lines):
        y = info_y + i
        if y >= max_y - 2:
            break
        try:
            self.stdscr.addstr(y, 2, info[:max_x - 3], curses.color_pair(1))
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate [Enter]=select [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_rd(self, max_y: int, max_x: int):
    """Draw the reaction-diffusion simulation."""
    # Title bar
    title = (f" Reaction-Diffusion [{self.rd_preset_name}]"
             f"  Gen: {self.rd_generation}"
             f"  f={self.rd_feed:.4f}  k={self.rd_kill:.4f}")
    state = " PLAY" if self.rd_running else " PAUSE"
    title += f"  {state}  ({self.rd_steps_per_frame} steps/frame)"
    title = title[:max_x - 1]
    try:
        self.stdscr.addstr(0, 0, title, curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw grid — map V concentration to density glyphs with colour
    draw_start = 1
    draw_rows = min(max_y - 3, self.rd_rows)
    draw_cols = min((max_x - 1) // 2, self.rd_cols)
    density = self.RD_DENSITY

    # Colour pair lookup: 8 tiers (pairs 60-67)
    color_tiers = [60, 61, 62, 63, 64, 65, 66, 67]

    for y in range(draw_rows):
        screen_y = draw_start + y
        if screen_y >= max_y - 2:
            break
        Vrow = self.rd_V[y]
        for x in range(draw_cols):
            sx = x * 2
            if sx + 1 >= max_x:
                break
            v = Vrow[x]
            if v < 0.005:
                continue  # leave blank (already erased)
            # Map V to density glyph (1-4, skip 0=blank)
            di = int(v * 4.0)
            if di < 1:
                di = 1
            elif di > 4:
                di = 4
            ch = density[di]
            # Map V to colour tier (0-7)
            ci = int(v * 7.99)
            if ci > 7:
                ci = 7
            attr = curses.color_pair(color_tiers[ci])
            if v > 0.5:
                attr |= curses.A_BOLD
            try:
                self.stdscr.addstr(screen_y, sx, ch, attr)
            except curses.error:
                pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        # Compute some stats
        total = self.rd_rows * self.rd_cols
        v_sum = 0.0
        v_max = 0.0
        for row in self.rd_V:
            for v in row:
                v_sum += v
                if v > v_max:
                    v_max = v
        v_avg = v_sum / total if total > 0 else 0.0
        status = (f" Gen: {self.rd_generation}  |"
                  f"  V avg: {v_avg:.4f}  V max: {v_max:.4f}  |"
                  f"  Du={self.rd_Du}  Dv={self.rd_Dv}  |"
                  f"  Speed: {SPEED_LABELS[self.speed_idx]}")
        status = status[:max_x - 1]
        try:
            self.stdscr.addstr(status_y, 0, status, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [f/F]=feed± [k/K]=kill± [+/-]=steps/frame [r]=reseed [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register rd mode methods on the App class."""
    App._enter_rd_mode = _enter_rd_mode
    App._exit_rd_mode = _exit_rd_mode
    App._rd_init = _rd_init
    App._rd_step = _rd_step
    App._handle_rd_menu_key = _handle_rd_menu_key
    App._handle_rd_key = _handle_rd_key
    App._draw_rd_menu = _draw_rd_menu
    App._draw_rd = _draw_rd

