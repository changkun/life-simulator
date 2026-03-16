"""Mode: pwave — simulation mode for the life package."""
import curses
import math
import random
import time

PWAVE_PRESETS = [
    ("Classic Wave", "15 pendulums — elegant snake and convergence patterns", "classic"),
    ("Dense Array", "24 pendulums — rich interference and fine wave structure", "dense"),
    ("Wide Spread", "12 pendulums with large length differences — dramatic phase shifts", "wide"),
    ("Quick Cycle", "Fast realignment — watch the full cycle in seconds", "quick"),
    ("Slow Meditation", "Gentle, slow-evolving patterns for contemplation", "slow"),
    ("Grand Ensemble", "32 pendulums — maximum complexity and beauty", "grand"),
]


def _enter_pwave_mode(self):
    """Enter Pendulum Wave mode — show preset menu."""
    self.pwave_menu = True
    self.pwave_menu_sel = 0




def _exit_pwave_mode(self):
    """Exit Pendulum Wave mode."""
    self.pwave_mode = False
    self.pwave_menu = False
    self.pwave_running = False
    self.pwave_lengths = []
    self.pwave_angles = []
    self.pwave_trail = []




def _pwave_init(self, preset: str):
    """Initialize pendulum wave simulation from preset."""
    import math

    rows, cols = self.grid.rows, self.grid.cols
    self.pwave_rows = rows
    self.pwave_cols = cols
    self.pwave_generation = 0
    self.pwave_time = 0.0
    self.pwave_show_info = False
    self.pwave_trail = []

    if preset == "classic":
        self.pwave_n_pendulums = 15
        self.pwave_base_length = 1.0
        self.pwave_realign_time = 60.0
        self.pwave_g = 9.81
        self.pwave_dt = 0.02
        self.pwave_speed = 3
    elif preset == "dense":
        self.pwave_n_pendulums = 24
        self.pwave_base_length = 0.8
        self.pwave_realign_time = 60.0
        self.pwave_g = 9.81
        self.pwave_dt = 0.02
        self.pwave_speed = 3
    elif preset == "wide":
        self.pwave_n_pendulums = 12
        self.pwave_base_length = 0.6
        self.pwave_realign_time = 40.0
        self.pwave_g = 9.81
        self.pwave_dt = 0.02
        self.pwave_speed = 3
    elif preset == "quick":
        self.pwave_n_pendulums = 15
        self.pwave_base_length = 0.5
        self.pwave_realign_time = 20.0
        self.pwave_g = 9.81
        self.pwave_dt = 0.02
        self.pwave_speed = 5
    elif preset == "slow":
        self.pwave_n_pendulums = 18
        self.pwave_base_length = 1.5
        self.pwave_realign_time = 120.0
        self.pwave_g = 9.81
        self.pwave_dt = 0.02
        self.pwave_speed = 2
    elif preset == "grand":
        self.pwave_n_pendulums = 32
        self.pwave_base_length = 0.7
        self.pwave_realign_time = 60.0
        self.pwave_g = 9.81
        self.pwave_dt = 0.02
        self.pwave_speed = 3
    else:
        self.pwave_n_pendulums = 15
        self.pwave_base_length = 1.0
        self.pwave_realign_time = 60.0
        self.pwave_g = 9.81
        self.pwave_dt = 0.02
        self.pwave_speed = 3

    # Calculate pendulum lengths so that pendulum i completes (N_base + i)
    # oscillations in realign_time T. For SHM: period = 2*pi*sqrt(L/g)
    # We want period_i = T / (N_base + i), so L_i = g * (T / (2*pi*(N_base + i)))^2
    n = self.pwave_n_pendulums
    N_base = 51  # base number of oscillations for the longest pendulum
    self.pwave_lengths = []
    for i in range(n):
        period_i = self.pwave_realign_time / (N_base + i)
        L_i = self.pwave_g * (period_i / (2 * math.pi)) ** 2
        self.pwave_lengths.append(L_i)

    # All pendulums start at the same angle (max displacement)
    start_angle = 0.4  # ~23 degrees
    self.pwave_angles = [start_angle] * n

    # Initialize trail storage
    self.pwave_trail = [[] for _ in range(n)]

    self.pwave_running = True




def _pwave_step(self):
    """Advance pendulum wave by one timestep using exact SHM solution."""
    import math

    self.pwave_generation += 1
    self.pwave_time += self.pwave_dt

    t = self.pwave_time
    start_angle = 0.4
    g = self.pwave_g

    for i in range(self.pwave_n_pendulums):
        L = self.pwave_lengths[i]
        omega = math.sqrt(g / L)
        # Exact SHM: theta(t) = A * cos(omega * t)
        self.pwave_angles[i] = start_angle * math.cos(omega * t)




def _handle_pwave_menu_key(self, key: int) -> bool:
    """Handle keys in the pendulum wave preset menu."""
    n = len(PWAVE_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.pwave_menu_sel = (self.pwave_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.pwave_menu_sel = (self.pwave_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.pwave_menu = False
        self.pwave_mode = False
        self._exit_pwave_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = PWAVE_PRESETS[self.pwave_menu_sel]
        self.pwave_preset_name = preset[0]
        self._pwave_init(preset[2])
        self.pwave_menu = False
        self.pwave_mode = True
        self.pwave_running = True
    else:
        return False
    return True




def _handle_pwave_key(self, key: int) -> bool:
    """Handle keys during pendulum wave simulation."""
    if key in (27, ord('q')):
        self._exit_pwave_mode()
        return True
    elif key == ord(' '):
        self.pwave_running = not self.pwave_running
    elif key in (ord('n'), ord('.')):
        self._pwave_step()
    elif key == ord('r'):
        for p in PWAVE_PRESETS:
            if p[0] == self.pwave_preset_name:
                self._pwave_init(p[2])
                break
    elif key in (ord('R'), ord('m')):
        self.pwave_running = False
        self.pwave_menu = True
    elif key == ord('i'):
        self.pwave_show_info = not self.pwave_show_info
    elif key == ord('+') or key == ord('='):
        self.pwave_speed = min(10, self.pwave_speed + 1)
    elif key == ord('-') or key == ord('_'):
        self.pwave_speed = max(1, self.pwave_speed - 1)
    else:
        return False
    return True




def _draw_pwave_menu(self, max_y: int, max_x: int):
    """Draw the pendulum wave preset selection menu."""
    self.stdscr.erase()
    title = "── Pendulum Wave ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Uncoupled pendulums with incremental lengths produce mesmerizing wave patterns"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass

    y = 4
    for i, (name, desc, _key) in enumerate(PWAVE_PRESETS):
        if y >= max_y - 6:
            break
        attr = curses.A_REVERSE if i == self.pwave_menu_sel else 0
        try:
            label = f"  {name:<20s} {desc}"
            self.stdscr.addstr(y, 2, label[:max_x - 4], attr)
        except curses.error:
            pass
        y += 1

    y += 1
    info_lines = [
        "Controls during simulation:",
        "  Space=play/pause  n=step  +/-=speed  i=info  r=reset  R=menu  q=exit",
        "",
        "Physics: Each pendulum has a slightly different length, so they oscillate",
        "at slightly different frequencies. They start in sync and gradually create",
        "traveling waves, standing waves, and chaotic-looking patterns before",
        "eventually realigning — a beautiful demonstration of simple harmonic motion.",
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




def _draw_pwave(self, max_y: int, max_x: int):
    """Draw the Pendulum Wave simulation."""
    import math

    self.stdscr.erase()
    rows = min(self.pwave_rows, max_y - 2)
    cols = min(self.pwave_cols, max_x)
    if rows < 10 or cols < 20:
        return

    n = self.pwave_n_pendulums
    t = self.pwave_time

    # Layout: pendulums hang from the top
    pivot_y = 2  # row of the support bar
    # Maximum visual pendulum length (in rows)
    max_vis_len = rows - 6  # leave room for status bars and pivot
    # The longest pendulum length (first one) sets the scale
    L_max = self.pwave_lengths[0] if self.pwave_lengths else 1.0

    # Spacing between pendulums
    margin = max(2, cols // (n + 2))
    total_width = margin * (n - 1) if n > 1 else 0
    start_x = (cols - total_width) // 2

    # Draw support bar
    bar_x1 = max(0, start_x - 2)
    bar_x2 = min(cols - 1, start_x + total_width + 2)
    bar_str = "═" * (bar_x2 - bar_x1 + 1)
    try:
        self.stdscr.addstr(pivot_y, bar_x1, bar_str[:cols - bar_x1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw each pendulum
    bob_positions = []
    for i in range(n):
        px = start_x + i * margin
        if px < 0 or px >= cols:
            continue

        L = self.pwave_lengths[i]
        theta = self.pwave_angles[i]

        # Visual length proportional to actual length
        vis_len = max(3, int(max_vis_len * L / L_max))

        # Bob position: x offset = L*sin(theta), y offset = L*cos(theta)
        # Scale to visual coordinates
        bob_dx = vis_len * math.sin(theta)
        bob_dy = vis_len * math.cos(theta)

        bob_x = int(round(px + bob_dx))
        bob_y = int(round(pivot_y + bob_dy))

        bob_positions.append((bob_x, bob_y, i))

        # Draw string from pivot to bob using Bresenham-like approach
        x0, y0 = px, pivot_y + 1
        x1, y1 = bob_x, bob_y
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1

        if dy == 0:
            continue

        cx, cy = x0, y0
        err = dx - dy
        steps = 0
        max_steps = dx + dy + 1
        while steps < max_steps:
            if 0 <= cy < rows and 0 <= cx < cols and (cx, cy) != (bob_x, bob_y):
                # Choose string character based on angle
                if abs(theta) < 0.05:
                    ch = '│'
                elif abs(bob_dx) > abs(bob_dy) * 0.5:
                    ch = '╲' if theta > 0 else '╱'
                else:
                    ch = '│'
                try:
                    self.stdscr.addch(cy, cx, ch, curses.A_DIM)
                except curses.error:
                    pass
            if cx == x1 and cy == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy
            steps += 1

        # Store trail
        if i < len(self.pwave_trail):
            self.pwave_trail[i].append((bob_x, bob_y))
            if len(self.pwave_trail[i]) > self.pwave_max_trail:
                self.pwave_trail[i] = self.pwave_trail[i][-self.pwave_max_trail:]

    # Draw trails (fading)
    for i in range(min(n, len(self.pwave_trail))):
        trail = self.pwave_trail[i]
        tlen = len(trail)
        for ti, (tx, ty) in enumerate(trail):
            if 0 <= ty < rows and 0 <= tx < cols:
                age_frac = ti / max(tlen, 1)
                if age_frac < 0.3:
                    ch = '·'
                elif age_frac < 0.7:
                    ch = '∘'
                else:
                    ch = '•'
                try:
                    attr = curses.A_DIM if age_frac < 0.5 else 0
                    color = curses.color_pair((i % 6) + 1)
                    self.stdscr.addch(ty, tx, ch, color | attr)
                except curses.error:
                    pass

    # Draw bobs on top of everything
    for bob_x, bob_y, i in bob_positions:
        if 0 <= bob_y < rows and 0 <= bob_x < cols:
            color = curses.color_pair((i % 6) + 1)
            try:
                self.stdscr.addch(bob_y, bob_x, 'O', color | curses.A_BOLD)
            except curses.error:
                pass
        # Draw pivot point
        ppx = start_x + i * margin
        if 0 <= ppx < cols:
            try:
                self.stdscr.addch(pivot_y, ppx, '╤', curses.color_pair(7))
            except curses.error:
                pass

    # Draw a "wave curve" at the bottom showing the bob x-offsets
    wave_y = min(rows - 1, max_y - 4)
    if wave_y > pivot_y + 5:
        for i in range(n):
            wx = start_x + i * margin
            theta = self.pwave_angles[i]
            # Map angle to a visual offset for the wave indicator
            indicator_h = 2
            wy = wave_y - int(round(theta / 0.4 * indicator_h))
            if 0 <= wy < rows and 0 <= wx < cols:
                color = curses.color_pair((i % 6) + 1)
                try:
                    self.stdscr.addch(wy, wx, '●', color | curses.A_BOLD)
                except curses.error:
                    pass
        # Wave baseline
        for i in range(n):
            wx = start_x + i * margin
            if 0 <= wx < cols and 0 <= wave_y < rows:
                try:
                    self.stdscr.addch(wave_y, wx, '─', curses.A_DIM)
                except curses.error:
                    pass

    # Info panel
    if self.pwave_show_info:
        info_lines = [
            f" Pendulum Wave — {self.pwave_preset_name} ",
            f" Pendulums: {n}  Base oscillations: 51",
            f" Realign time: {self.pwave_realign_time:.0f}s",
            f" Lengths: {self.pwave_lengths[0]:.3f}m .. {self.pwave_lengths[-1]:.3f}m",
            f" Time: {self.pwave_time:.1f}s / {self.pwave_realign_time:.0f}s",
            f" Phase: {(self.pwave_time % self.pwave_realign_time) / self.pwave_realign_time * 100:.0f}% of cycle",
        ]
        iy = pivot_y + 1
        for il in info_lines:
            if iy < rows - 3:
                try:
                    self.stdscr.addstr(iy, 1, il[:max_x - 3], curses.A_REVERSE)
                except curses.error:
                    pass
                iy += 1

    # Status bar
    status_y = min(rows, max_y - 2)
    cycle_pct = (self.pwave_time % self.pwave_realign_time) / self.pwave_realign_time * 100
    status = (f" Gen:{self.pwave_generation} | {self.pwave_preset_name} | "
              f"t={self.pwave_time:.1f}s | cycle={cycle_pct:.0f}% | speed=x{self.pwave_speed} ")
    try:
        self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.A_REVERSE)
    except curses.error:
        pass

    # Hint bar
    hint = " Space=play n=step +/-=speed i=info r=reset R=menu q=exit"
    try:
        self.stdscr.addstr(status_y + 1, 0, hint[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register pwave mode methods on the App class."""
    App._enter_pwave_mode = _enter_pwave_mode
    App._exit_pwave_mode = _exit_pwave_mode
    App._pwave_init = _pwave_init
    App._pwave_step = _pwave_step
    App._handle_pwave_menu_key = _handle_pwave_menu_key
    App._handle_pwave_key = _handle_pwave_key
    App._draw_pwave_menu = _draw_pwave_menu
    App._draw_pwave = _draw_pwave

