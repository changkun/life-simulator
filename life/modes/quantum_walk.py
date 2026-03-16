"""Mode: qwalk — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_qwalk_mode(self):
    """Enter Quantum Walk mode — show preset menu."""
    self.qwalk_menu = True
    self.qwalk_menu_sel = 0
    self._flash("Quantum Walk — select a configuration")



def _exit_qwalk_mode(self):
    """Exit Quantum Walk mode."""
    self.qwalk_mode = False
    self.qwalk_menu = False
    self.qwalk_running = False
    self.qwalk_amp_re = []
    self.qwalk_amp_im = []
    self.qwalk_prob = []
    self._flash("Quantum Walk mode OFF")



def _qwalk_init(self, preset_idx: int):
    """Initialize quantum walk with chosen preset."""
    name, _desc, coin, init_type, boundary = self.QWALK_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.qwalk_rows = rows
    self.qwalk_cols = cols
    self.qwalk_preset_name = name
    self.qwalk_generation = 0
    self.qwalk_steps_per_frame = 1
    self.qwalk_coin = coin
    self.qwalk_boundary = boundary
    self.qwalk_view = "probability"
    self.qwalk_decoherence = 0.02 if "decoherent" in init_type else 0.0

    # 4 internal directions: 0=up, 1=right, 2=down, 3=left
    # Each direction has a complex amplitude at each cell
    ndirs = 4
    self.qwalk_amp_re = [[[0.0] * cols for _ in range(rows)] for _ in range(ndirs)]
    self.qwalk_amp_im = [[[0.0] * cols for _ in range(rows)] for _ in range(ndirs)]

    cr, cc = rows // 2, cols // 2

    if init_type in ("single", "single_decoherent"):
        # Equal superposition of all 4 directions at center
        amp = 0.5  # 1/sqrt(4) = 0.5
        for d in range(4):
            self.qwalk_amp_re[d][cr][cc] = amp
    elif init_type == "gaussian":
        # Gaussian wave packet centered at (cr, cc)
        sigma = min(rows, cols) / 10.0
        total_sq = 0.0
        for r in range(rows):
            for c in range(cols):
                dr = r - cr
                dc = c - cc
                val = math.exp(-(dr * dr + dc * dc) / (2.0 * sigma * sigma))
                for d in range(4):
                    self.qwalk_amp_re[d][r][c] = val * 0.5
                total_sq += val * val
        # Normalize
        norm = math.sqrt(total_sq) if total_sq > 0 else 1.0
        for d in range(4):
            for r in range(rows):
                for c in range(cols):
                    self.qwalk_amp_re[d][r][c] /= norm
    elif init_type == "dual":
        # Two sources separated by 1/4 grid width
        offset = cols // 4
        amp = 0.5 / math.sqrt(2.0)
        for d in range(4):
            self.qwalk_amp_re[d][cr][cc - offset] = amp
            self.qwalk_amp_re[d][cr][cc + offset] = amp

    self._qwalk_update_prob()
    self.qwalk_mode = True
    self.qwalk_menu = False
    self.qwalk_running = False
    self._flash(f"Quantum Walk: {name} — Space to start")



def _qwalk_update_prob(self):
    """Recompute probability grid from amplitudes."""
    rows, cols = self.qwalk_rows, self.qwalk_cols
    prob = [[0.0] * cols for _ in range(rows)]
    max_p = 0.0
    for d in range(4):
        are = self.qwalk_amp_re[d]
        aim = self.qwalk_amp_im[d]
        for r in range(rows):
            for c in range(cols):
                p = are[r][c] ** 2 + aim[r][c] ** 2
                prob[r][c] += p
    for r in range(rows):
        for c in range(cols):
            if prob[r][c] > max_p:
                max_p = prob[r][c]
    self.qwalk_prob = prob
    self.qwalk_max_prob = max_p if max_p > 0 else 1.0



def _qwalk_step(self):
    """One discrete-time quantum walk step: Coin then Shift."""
    rows, cols = self.qwalk_rows, self.qwalk_cols
    are = self.qwalk_amp_re
    aim = self.qwalk_amp_im

    # ── Coin operation ──
    # Apply coin operator to internal state at each cell
    new_re = [[[0.0] * cols for _ in range(rows)] for _ in range(4)]
    new_im = [[[0.0] * cols for _ in range(rows)] for _ in range(4)]

    if self.qwalk_coin == "hadamard":
        # 4x4 Hadamard: H⊗H, entries are ±1/2
        # H⊗H[i][j] = (-1)^(bit_dot(i,j)) / 2
        h = [[0.5, 0.5, 0.5, 0.5],
             [0.5, -0.5, 0.5, -0.5],
             [0.5, 0.5, -0.5, -0.5],
             [0.5, -0.5, -0.5, 0.5]]
        for r in range(rows):
            for c in range(cols):
                for i in range(4):
                    s_re = 0.0
                    s_im = 0.0
                    for j in range(4):
                        s_re += h[i][j] * are[j][r][c]
                        s_im += h[i][j] * aim[j][r][c]
                    new_re[i][r][c] = s_re
                    new_im[i][r][c] = s_im

    elif self.qwalk_coin == "grover":
        # 4x4 Grover diffusion: G[i][j] = -delta(i,j) + 1/2
        for r in range(rows):
            for c in range(cols):
                sum_re = 0.0
                sum_im = 0.0
                for j in range(4):
                    sum_re += are[j][r][c]
                    sum_im += aim[j][r][c]
                avg_re = sum_re * 0.5
                avg_im = sum_im * 0.5
                for i in range(4):
                    new_re[i][r][c] = avg_re - are[i][r][c]
                    new_im[i][r][c] = avg_im - aim[i][r][c]

    elif self.qwalk_coin == "dft":
        # 4x4 DFT: F[j][k] = omega^(jk) / 2, omega = e^(i*pi/2) = i
        # omega^0=1, omega^1=i, omega^2=-1, omega^3=-i
        # Real parts of omega^n: [1, 0, -1, 0]
        # Imag parts of omega^n: [0, 1, 0, -1]
        wr = [1.0, 0.0, -1.0, 0.0]
        wi = [0.0, 1.0, 0.0, -1.0]
        for r in range(rows):
            for c in range(cols):
                for i in range(4):
                    s_re = 0.0
                    s_im = 0.0
                    for j in range(4):
                        exp = (i * j) % 4
                        # (wr[exp] + i*wi[exp]) * (are + i*aim)
                        s_re += wr[exp] * are[j][r][c] - wi[exp] * aim[j][r][c]
                        s_im += wr[exp] * aim[j][r][c] + wi[exp] * are[j][r][c]
                    new_re[i][r][c] = s_re * 0.5
                    new_im[i][r][c] = s_im * 0.5

    # ── Shift operation ──
    # Move each direction component one cell in its direction
    # 0=up (r-1), 1=right (c+1), 2=down (r+1), 3=left (c-1)
    dr = [-1, 0, 1, 0]
    dc = [0, 1, 0, -1]

    shifted_re = [[[0.0] * cols for _ in range(rows)] for _ in range(4)]
    shifted_im = [[[0.0] * cols for _ in range(rows)] for _ in range(4)]

    if self.qwalk_boundary == "periodic":
        for d in range(4):
            for r in range(rows):
                nr = (r + dr[d]) % rows
                for c in range(cols):
                    nc = (c + dc[d]) % cols
                    shifted_re[d][nr][nc] = new_re[d][r][c]
                    shifted_im[d][nr][nc] = new_im[d][r][c]
    else:  # absorbing
        for d in range(4):
            for r in range(rows):
                nr = r + dr[d]
                if nr < 0 or nr >= rows:
                    continue
                for c in range(cols):
                    nc = c + dc[d]
                    if nc < 0 or nc >= cols:
                        continue
                    shifted_re[d][nr][nc] = new_re[d][r][c]
                    shifted_im[d][nr][nc] = new_im[d][r][c]

    # ── Optional decoherence ──
    if self.qwalk_decoherence > 0:
        p = self.qwalk_decoherence
        for d in range(4):
            for r in range(rows):
                for c in range(cols):
                    if random.random() < p:
                        # Measure and collapse: pick random phase
                        mag = math.sqrt(shifted_re[d][r][c] ** 2 + shifted_im[d][r][c] ** 2)
                        angle = random.random() * 2.0 * math.pi
                        shifted_re[d][r][c] = mag * math.cos(angle)
                        shifted_im[d][r][c] = mag * math.sin(angle)

    self.qwalk_amp_re = shifted_re
    self.qwalk_amp_im = shifted_im
    self.qwalk_generation += 1
    self._qwalk_update_prob()



def _handle_qwalk_menu_key(self, key: int) -> bool:
    """Handle input in Quantum Walk preset menu."""
    n = len(self.QWALK_PRESETS)
    if key in (curses.KEY_UP, ord("k")):
        self.qwalk_menu_sel = (self.qwalk_menu_sel - 1) % n
    elif key in (curses.KEY_DOWN, ord("j")):
        self.qwalk_menu_sel = (self.qwalk_menu_sel + 1) % n
    elif key in (10, 13, curses.KEY_ENTER):
        self._qwalk_init(self.qwalk_menu_sel)
    elif key in (27, ord("q")):
        self.qwalk_menu = False
        self._flash("Quantum Walk cancelled")
    return True



def _handle_qwalk_key(self, key: int) -> bool:
    """Handle input in active Quantum Walk simulation."""
    if key == ord(" "):
        self.qwalk_running = not self.qwalk_running
        self._flash("Running" if self.qwalk_running else "Paused")
    elif key in (ord("n"), ord(".")):
        self.qwalk_running = False
        self._qwalk_step()
    elif key == ord("+") or key == ord("="):
        self.qwalk_steps_per_frame = min(20, self.qwalk_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.qwalk_steps_per_frame}")
    elif key == ord("-"):
        self.qwalk_steps_per_frame = max(1, self.qwalk_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.qwalk_steps_per_frame}")
    elif key == ord("v"):
        views = ["probability", "phase", "real", "imaginary"]
        idx = views.index(self.qwalk_view)
        self.qwalk_view = views[(idx + 1) % len(views)]
        self._flash(f"View: {self.qwalk_view}")
    elif key == ord("d"):
        self.qwalk_decoherence = min(1.0, self.qwalk_decoherence + 0.005)
        self._flash(f"Decoherence: {self.qwalk_decoherence:.3f}")
    elif key == ord("D"):
        self.qwalk_decoherence = max(0.0, self.qwalk_decoherence - 0.005)
        self._flash(f"Decoherence: {self.qwalk_decoherence:.3f}")
    elif key == ord("r"):
        self._qwalk_init(self.qwalk_menu_sel)
    elif key in (ord("R"), ord("m")):
        self.qwalk_mode = False
        self.qwalk_running = False
        self.qwalk_menu = True
        self.qwalk_menu_sel = 0
        self._flash("Quantum Walk — select a configuration")
    elif key in (27, ord("q")):
        self._exit_qwalk_mode()
    else:
        return True
    return True



def _draw_qwalk_menu(self, max_y: int, max_x: int):
    """Draw the Quantum Walk preset selection menu."""
    self.stdscr.erase()
    title = "── Quantum Walk ── Select Configuration ──"
    try:
        self.stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(6) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.QWALK_PRESETS):
        y = 2 + i * 2
        if y >= max_y - 2:
            break
        marker = "▶ " if i == self.qwalk_menu_sel else "  "
        attr = curses.A_BOLD if i == self.qwalk_menu_sel else 0
        try:
            self.stdscr.addstr(y, 2, f"{marker}{name}", curses.color_pair(3) | attr)
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate [Enter]=select [q]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_qwalk(self, max_y: int, max_x: int):
    """Draw the active Quantum Walk simulation."""
    self.stdscr.erase()
    rows, cols = self.qwalk_rows, self.qwalk_cols

    # Title bar
    state = "▶ RUNNING" if self.qwalk_running else "⏸ PAUSED"
    title = (f" Quantum Walk: {self.qwalk_preset_name}  │  "
             f"Gen {self.qwalk_generation}  │  {state}  │  "
             f"View: {self.qwalk_view}  │  "
             f"Decoherence: {self.qwalk_decoherence:.3f}")
    title = title[:max_x - 1]
    try:
        self.stdscr.addstr(0, 0, title, curses.color_pair(6) | curses.A_BOLD)
    except curses.error:
        pass

    # Render grid
    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)
    prob = self.qwalk_prob
    mp = self.qwalk_max_prob

    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 1:
            break
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break

            if self.qwalk_view == "probability":
                val = prob[r][c] / mp if mp > 0 else 0.0
                # Apply sqrt for better visual contrast
                val = math.sqrt(val) if val > 0 else 0.0
                ch, attr = self._qwalk_prob_char(val)
            elif self.qwalk_view == "phase":
                # Compute dominant phase angle
                total_re = 0.0
                total_im = 0.0
                for d in range(4):
                    total_re += self.qwalk_amp_re[d][r][c]
                    total_im += self.qwalk_amp_im[d][r][c]
                mag = math.sqrt(total_re ** 2 + total_im ** 2)
                if mag < 1e-10:
                    ch = "  "
                    attr = 0
                else:
                    phase = math.atan2(total_im, total_re)  # -pi to pi
                    intensity = math.sqrt(prob[r][c] / mp) if mp > 0 else 0.0
                    ch, attr = self._qwalk_phase_char(phase, intensity)
            elif self.qwalk_view == "real":
                total_re = 0.0
                for d in range(4):
                    total_re += self.qwalk_amp_re[d][r][c]
                val = total_re
                ch, attr = self._qwalk_signed_char(val, mp)
            else:  # imaginary
                total_im = 0.0
                for d in range(4):
                    total_im += self.qwalk_amp_im[d][r][c]
                val = total_im
                ch, attr = self._qwalk_signed_char(val, mp)

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
            hint = " [Space]=play [n]=step [v]=view [d/D]=decoherence [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _qwalk_prob_char(self, val: float) -> tuple:
    """Map probability value [0,1] to character and color."""
    if val > 0.85:
        return "██", curses.color_pair(3) | curses.A_BOLD   # bright yellow
    elif val > 0.65:
        return "▓▓", curses.color_pair(6) | curses.A_BOLD   # bright white
    elif val > 0.45:
        return "▒▒", curses.color_pair(5) | curses.A_BOLD   # magenta
    elif val > 0.28:
        return "░░", curses.color_pair(4) | curses.A_BOLD   # blue
    elif val > 0.12:
        return "··", curses.color_pair(4)                    # dim blue
    elif val > 0.02:
        return "· ", curses.color_pair(4) | curses.A_DIM     # very dim
    else:
        return "  ", 0



def _qwalk_phase_char(self, phase: float, intensity: float) -> tuple:
    """Map phase angle and intensity to character and color."""
    if intensity < 0.02:
        return "  ", 0
    # Map phase (-pi..pi) to 6 color regions
    # Normalize to 0..1
    p = (phase + math.pi) / (2.0 * math.pi)
    ch = "██" if intensity > 0.5 else ("▓▓" if intensity > 0.25 else "░░")
    if p < 0.167:
        return ch, curses.color_pair(1) | curses.A_BOLD   # red
    elif p < 0.333:
        return ch, curses.color_pair(3) | curses.A_BOLD   # yellow
    elif p < 0.5:
        return ch, curses.color_pair(2) | curses.A_BOLD   # green
    elif p < 0.667:
        return ch, curses.color_pair(4) | curses.A_BOLD   # blue (cyan-ish)
    elif p < 0.833:
        return ch, curses.color_pair(5) | curses.A_BOLD   # magenta
    else:
        return ch, curses.color_pair(1) | curses.A_BOLD   # red



def _qwalk_signed_char(self, val: float, max_p: float) -> tuple:
    """Map signed amplitude to character — green positive, red negative."""
    scale = math.sqrt(max_p) if max_p > 0 else 1.0
    nv = abs(val) / scale if scale > 0 else 0.0
    nv = min(1.0, nv)
    if nv < 0.02:
        return "  ", 0
    color = curses.color_pair(2) if val >= 0 else curses.color_pair(1)
    if nv > 0.7:
        return "██", color | curses.A_BOLD
    elif nv > 0.4:
        return "▓▓", color | curses.A_BOLD
    elif nv > 0.2:
        return "░░", color
    else:
        return "··", color | curses.A_DIM


def register(App):
    """Register qwalk mode methods on the App class."""
    from life.modes.strange_attractors import QWALK_PRESETS
    App.QWALK_PRESETS = QWALK_PRESETS
    App._enter_qwalk_mode = _enter_qwalk_mode
    App._exit_qwalk_mode = _exit_qwalk_mode
    App._qwalk_init = _qwalk_init
    App._qwalk_update_prob = _qwalk_update_prob
    App._qwalk_step = _qwalk_step
    App._handle_qwalk_menu_key = _handle_qwalk_menu_key
    App._handle_qwalk_key = _handle_qwalk_key
    App._draw_qwalk_menu = _draw_qwalk_menu
    App._draw_qwalk = _draw_qwalk
    App._qwalk_prob_char = _qwalk_prob_char
    App._qwalk_phase_char = _qwalk_phase_char
    App._qwalk_signed_char = _qwalk_signed_char

