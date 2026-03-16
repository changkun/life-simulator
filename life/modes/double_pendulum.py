"""Mode: dpend — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_dpend_mode(self):
    """Enter Double Pendulum mode — show preset menu."""
    self.dpend_menu = True
    self.dpend_menu_sel = 0
    self._flash("Double Pendulum Chaos — select a configuration")



def _exit_dpend_mode(self):
    """Exit Double Pendulum mode."""
    self.dpend_mode = False
    self.dpend_menu = False
    self.dpend_running = False
    self.dpend_trail1 = []
    self.dpend_trail2 = []
    self._flash("Double Pendulum mode OFF")



def _dpend_init(self, preset_idx: int):
    """Initialize double pendulum simulation with the given preset."""
    import math
    name, _desc, preset_id = self.DPEND_PRESETS[preset_idx]
    self.dpend_preset_name = name
    self.dpend_generation = 0
    self.dpend_running = False
    self.dpend_trail1 = []
    self.dpend_trail2 = []

    max_y, max_x = self.stdscr.getmaxyx()
    self.dpend_rows = max(10, max_y - 3)
    self.dpend_cols = max(10, max_x - 1)

    # Default parameters
    self.dpend_m1 = 1.0
    self.dpend_m2 = 1.0
    self.dpend_l1 = 1.0
    self.dpend_l2 = 1.0
    self.dpend_g = 9.81
    self.dpend_dt = 0.005
    self.dpend_dual = True
    self.dpend_perturb = 0.001
    self.dpend_max_trail = 500

    if preset_id == "classic":
        self.dpend_p1 = [math.pi * 0.75, math.pi * 0.75, 0.0, 0.0]
        self.dpend_perturb = 0.001
    elif preset_id == "gentle":
        self.dpend_p1 = [math.pi * 0.15, math.pi * 0.15, 0.0, 0.0]
        self.dpend_perturb = 0.01
    elif preset_id == "heavy_lower":
        self.dpend_m1 = 1.0
        self.dpend_m2 = 3.0
        self.dpend_p1 = [math.pi * 0.6, math.pi * 0.8, 0.0, 0.0]
        self.dpend_perturb = 0.001
    elif preset_id == "heavy_upper":
        self.dpend_m1 = 3.0
        self.dpend_m2 = 1.0
        self.dpend_p1 = [math.pi * 0.6, math.pi * 0.8, 0.0, 0.0]
        self.dpend_perturb = 0.001
    elif preset_id == "max_chaos":
        self.dpend_m1 = 1.5
        self.dpend_m2 = 1.0
        self.dpend_l1 = 1.0
        self.dpend_l2 = 1.3
        self.dpend_p1 = [math.pi * 0.99, math.pi * 0.99, 0.0, 0.0]
        self.dpend_perturb = 0.0001
    elif preset_id == "near_identical":
        self.dpend_p1 = [math.pi * 0.5, math.pi * 0.75, 0.0, 0.0]
        self.dpend_perturb = math.radians(0.001)
    elif preset_id == "butterfly":
        self.dpend_p1 = [math.pi * 0.85, math.pi * 0.5, 0.0, 0.0]
        self.dpend_perturb = 1e-6
        self.dpend_max_trail = 800
    elif preset_id == "long_arms":
        self.dpend_l1 = 0.8
        self.dpend_l2 = 1.5
        self.dpend_p1 = [math.pi * 0.7, math.pi * 0.6, 0.0, 0.0]
        self.dpend_perturb = 0.001

    # Set up pendulum 2 with slight perturbation
    self.dpend_p2 = [
        self.dpend_p1[0] + self.dpend_perturb,
        self.dpend_p1[1],
        self.dpend_p1[2],
        self.dpend_p1[3],
    ]

    self.dpend_menu = False
    self.dpend_mode = True
    self._flash(f"Double Pendulum: {name} — Space to start")



def _dpend_derivs(self, state: list[float]) -> list[float]:
    """Compute derivatives for double pendulum equations of motion."""
    import math
    t1, t2, w1, w2 = state
    m1, m2 = self.dpend_m1, self.dpend_m2
    l1, l2 = self.dpend_l1, self.dpend_l2
    g = self.dpend_g

    delta = t1 - t2
    sin_d = math.sin(delta)
    cos_d = math.cos(delta)
    M = m1 + m2

    # Denominator: l1 * (2*m1 + m2 - m2*cos(2*delta))
    # which equals l1 * (2*M - m2*(1 + cos(2*delta)))
    # Guard against division by zero
    denom_factor = 2.0 * M - m2 * (1.0 + math.cos(2.0 * delta))
    if abs(denom_factor) < 1e-12:
        denom_factor = 1e-12 if denom_factor >= 0 else -1e-12

    dw1 = (-g * (2.0 * m1 + m2) * math.sin(t1)
           - m2 * g * math.sin(t1 - 2.0 * t2)
           - 2.0 * sin_d * m2 * (w2 * w2 * l2 + w1 * w1 * l1 * cos_d)
           ) / (l1 * denom_factor)

    dw2 = (2.0 * sin_d * (
        w1 * w1 * l1 * M
        + g * M * math.cos(t1)
        + w2 * w2 * l2 * m2 * cos_d)
           ) / (l2 * denom_factor)

    return [w1, w2, dw1, dw2]



def _dpend_rk4_step(self, state: list[float]) -> list[float]:
    """Advance state by one RK4 step."""
    dt = self.dpend_dt
    k1 = self._dpend_derivs(state)
    s2 = [state[i] + 0.5 * dt * k1[i] for i in range(4)]
    k2 = self._dpend_derivs(s2)
    s3 = [state[i] + 0.5 * dt * k2[i] for i in range(4)]
    k3 = self._dpend_derivs(s3)
    s4 = [state[i] + dt * k3[i] for i in range(4)]
    k4 = self._dpend_derivs(s4)
    return [state[i] + (dt / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])
            for i in range(4)]



def _dpend_tip_pos(self, state: list[float]) -> tuple[float, float]:
    """Get (x, y) position of the lower bob tip."""
    import math
    t1, t2 = state[0], state[1]
    l1, l2 = self.dpend_l1, self.dpend_l2
    x = l1 * math.sin(t1) + l2 * math.sin(t2)
    y = l1 * math.cos(t1) + l2 * math.cos(t2)
    return (x, y)



def _dpend_step(self):
    """Advance double pendulum by one timestep."""
    self.dpend_p1 = self._dpend_rk4_step(self.dpend_p1)
    tip1 = self._dpend_tip_pos(self.dpend_p1)
    self.dpend_trail1.append(tip1)
    if len(self.dpend_trail1) > self.dpend_max_trail:
        self.dpend_trail1 = self.dpend_trail1[-self.dpend_max_trail:]

    if self.dpend_dual:
        self.dpend_p2 = self._dpend_rk4_step(self.dpend_p2)
        tip2 = self._dpend_tip_pos(self.dpend_p2)
        self.dpend_trail2.append(tip2)
        if len(self.dpend_trail2) > self.dpend_max_trail:
            self.dpend_trail2 = self.dpend_trail2[-self.dpend_max_trail:]

    self.dpend_generation += 1



def _handle_dpend_menu_key(self, key: int) -> bool:
    """Handle keys in the Double Pendulum preset menu."""
    if key == -1:
        return True
    n = len(self.DPEND_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.dpend_menu_sel = (self.dpend_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.dpend_menu_sel = (self.dpend_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.dpend_menu = False
        self._flash("Double Pendulum cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._dpend_init(self.dpend_menu_sel)
        return True
    return True



def _handle_dpend_key(self, key: int) -> bool:
    """Handle keys while in Double Pendulum mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_dpend_mode()
        return True
    if key == ord(" "):
        self.dpend_running = not self.dpend_running
        self._flash("Playing" if self.dpend_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self._dpend_step()
        return True
    if key == ord("R"):
        self.dpend_mode = False
        self.dpend_menu = True
        self.dpend_menu_sel = 0
        self._flash("Double Pendulum — select a configuration")
        return True
    if key == ord("r"):
        # Reset current preset
        idx = self.dpend_menu_sel
        self._dpend_init(idx)
        self._flash("Reset")
        return True
    if key == ord("d"):
        self.dpend_dual = not self.dpend_dual
        self._flash("Dual mode: " + ("ON" if self.dpend_dual else "OFF"))
        return True
    if key == ord("c"):
        self.dpend_trail1 = []
        self.dpend_trail2 = []
        self._flash("Trails cleared")
        return True
    # Speed controls
    if key == ord(">"):
        self.dpend_steps_per_frame = min(50, self.dpend_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.dpend_steps_per_frame}")
        return True
    if key == ord("<"):
        self.dpend_steps_per_frame = max(1, self.dpend_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.dpend_steps_per_frame}")
        return True
    # Trail length
    if key == ord("]"):
        self.dpend_max_trail = min(2000, self.dpend_max_trail + 100)
        self._flash(f"Max trail: {self.dpend_max_trail}")
        return True
    if key == ord("["):
        self.dpend_max_trail = max(50, self.dpend_max_trail - 100)
        self._flash(f"Max trail: {self.dpend_max_trail}")
        return True
    # Gravity adjustment
    if key == ord("g"):
        self.dpend_g = max(1.0, self.dpend_g - 1.0)
        self._flash(f"Gravity: {self.dpend_g:.1f}")
        return True
    if key == ord("G"):
        self.dpend_g = min(30.0, self.dpend_g + 1.0)
        self._flash(f"Gravity: {self.dpend_g:.1f}")
        return True
    # Timestep adjustment
    if key == ord("+") or key == ord("="):
        self.dpend_dt = min(0.02, self.dpend_dt * 1.5)
        self._flash(f"dt: {self.dpend_dt:.4f}")
        return True
    if key == ord("-"):
        self.dpend_dt = max(0.001, self.dpend_dt / 1.5)
        self._flash(f"dt: {self.dpend_dt:.4f}")
        return True
    return True



def _draw_dpend_menu(self, max_y: int, max_x: int):
    """Draw the Double Pendulum preset selection menu."""
    self.stdscr.erase()
    title = "── Double Pendulum Chaos ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Classic chaos theory: sensitive dependence on initial conditions"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.DPEND_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.DPEND_PRESETS):
        y = 5 + i
        if y >= max_y - 14:
            break
        line = f"  {name:<20s} {desc}"
        attr = curses.color_pair(6)
        if i == self.dpend_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_lines = [
        "",
        "A double pendulum is a pendulum with another pendulum attached to its end.",
        "Despite simple rules, the system is chaotic: tiny changes in starting",
        "conditions lead to wildly different trajectories over time.",
        "",
        "Two pendulums are shown side-by-side with nearly identical initial angles",
        "to dramatically visualize the butterfly effect.",
        "",
        "Controls: Space=play/pause  n=step  d=toggle dual  c=clear trails",
        "          g/G=gravity  +/-=timestep  [/]=trail length  >/<=speed",
        "          r=reset  R=menu  q=exit",
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
                           curses.color_pair(7))
    except curses.error:
        pass



def _draw_dpend(self, max_y: int, max_x: int):
    """Draw the Double Pendulum simulation."""
    import math
    self.stdscr.erase()
    rows = self.dpend_rows
    cols = self.dpend_cols

    total_len = self.dpend_l1 + self.dpend_l2
    # Scale factor: map pendulum coordinates to screen
    # Leave margins for status bars
    draw_h = rows - 1
    draw_w = cols - 1

    if self.dpend_dual:
        # Two pendulums side by side
        panel_w = draw_w // 2 - 1
        panels = [
            (self.dpend_p1, self.dpend_trail1, panel_w // 2, draw_h // 2 + 1, "Pendulum A", 3),
            (self.dpend_p2, self.dpend_trail2, panel_w + 2 + panel_w // 2, draw_h // 2 + 1, "Pendulum B", 5),
        ]
        # Draw dividing line
        div_x = panel_w + 1
        for r in range(1, draw_h + 1):
            try:
                self.stdscr.addstr(r, div_x, "│", curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass
    else:
        panel_w = draw_w
        panels = [
            (self.dpend_p1, self.dpend_trail1, panel_w // 2, draw_h // 2 + 1, "Pendulum", 3),
        ]

    scale = min(draw_h * 0.4, panel_w * 0.4) / total_len if total_len > 0 else 10.0

    for state, trail, cx, cy, label, trail_color in panels:
        t1, t2 = state[0], state[1]
        l1, l2 = self.dpend_l1, self.dpend_l2

        # Pivot position
        px, py = cx, cy - int(total_len * scale * 0.3)

        # First bob position
        x1 = px + int(l1 * math.sin(t1) * scale)
        y1 = py + int(l1 * math.cos(t1) * scale)

        # Second bob position
        x2 = x1 + int(l2 * math.sin(t2) * scale)
        y2 = y1 + int(l2 * math.cos(t2) * scale)

        # Draw trajectory trail with fading
        trail_len = len(trail)
        for i, (tx, ty) in enumerate(trail):
            sx = px + int(tx * scale)
            sy = py + int(ty * scale * 0.5)  # Compress vertical for terminal aspect ratio
            # Recalculate with proper pivot offset
            sx = px + int(tx * scale)
            sy = py + int(ty * scale)
            if 1 <= sy < draw_h + 1 and 0 <= sx < cols:
                # Fade based on age
                age = (trail_len - i) / max(trail_len, 1)
                if age < 0.2:
                    ch = "█"
                    attr = curses.color_pair(trail_color) | curses.A_BOLD
                elif age < 0.4:
                    ch = "▓"
                    attr = curses.color_pair(trail_color) | curses.A_BOLD
                elif age < 0.6:
                    ch = "▒"
                    attr = curses.color_pair(trail_color)
                elif age < 0.8:
                    ch = "░"
                    attr = curses.color_pair(trail_color)
                else:
                    ch = "·"
                    attr = curses.color_pair(trail_color) | curses.A_DIM
                try:
                    self.stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass

        # Draw upper arm (pivot to first bob)
        self._dpend_draw_line(px, py, x1, y1, "─", curses.color_pair(7), draw_h, cols)

        # Draw lower arm (first bob to second bob)
        self._dpend_draw_line(x1, y1, x2, y2, "─", curses.color_pair(6), draw_h, cols)

        # Draw pivot
        if 1 <= py < draw_h + 1 and 0 <= px < cols:
            try:
                self.stdscr.addstr(py, px, "◆", curses.color_pair(7) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw first bob
        if 1 <= y1 < draw_h + 1 and 0 <= x1 < cols:
            m1_ch = "●" if self.dpend_m1 <= 2.0 else "⬤"
            try:
                self.stdscr.addstr(y1, x1, m1_ch, curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass

        # Draw second bob
        if 1 <= y2 < draw_h + 1 and 0 <= x2 < cols:
            m2_ch = "●" if self.dpend_m2 <= 2.0 else "⬤"
            try:
                self.stdscr.addstr(y2, x2, m2_ch, curses.color_pair(trail_color) | curses.A_BOLD)
            except curses.error:
                pass

        # Label
        try:
            self.stdscr.addstr(1, max(0, cx - len(label) // 2), label,
                               curses.color_pair(trail_color) | curses.A_BOLD)
        except curses.error:
            pass

    # Compute angular divergence if dual
    divergence_str = ""
    if self.dpend_dual and self.dpend_generation > 0:
        import math
        d_theta1 = abs(self.dpend_p1[0] - self.dpend_p2[0])
        d_theta2 = abs(self.dpend_p1[1] - self.dpend_p2[1])
        divergence = math.degrees(d_theta1 + d_theta2)
        divergence_str = f" │ Divergence: {divergence:.3f}°"

    # Status bar
    status = (f" Double Pendulum: {self.dpend_preset_name}"
              f" │ Step: {self.dpend_generation}"
              f" │ {'▶' if self.dpend_running else '⏸'}"
              f" │ g={self.dpend_g:.1f}"
              f" │ dt={self.dpend_dt:.4f}"
              f"{divergence_str}")
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
        hint = " Space=play  n=step  d=dual  c=clear  g/G=gravity  +/-=dt  [/]=trail  >/<=speed  r=reset  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _dpend_draw_line(self, x0: int, y0: int, x1: int, y1: int,
                     ch: str, attr: int, max_row: int, max_col: int):
    """Draw a line between two points using Bresenham's algorithm."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    steps = 0
    max_steps = dx + dy + 1

    while steps < max_steps:
        if 1 <= y0 < max_row + 1 and 0 <= x0 < max_col:
            # Choose character based on direction
            if dx > dy * 2:
                line_ch = "─"
            elif dy > dx * 2:
                line_ch = "│"
            elif sx == sy:
                line_ch = "╲"
            else:
                line_ch = "╱"
            try:
                self.stdscr.addstr(y0, x0, line_ch, attr)
            except curses.error:
                pass
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
        steps += 1


def register(App):
    """Register dpend mode methods on the App class."""
    App._enter_dpend_mode = _enter_dpend_mode
    App._exit_dpend_mode = _exit_dpend_mode
    App._dpend_init = _dpend_init
    App._dpend_derivs = _dpend_derivs
    App._dpend_rk4_step = _dpend_rk4_step
    App._dpend_tip_pos = _dpend_tip_pos
    App._dpend_step = _dpend_step
    App._handle_dpend_menu_key = _handle_dpend_menu_key
    App._handle_dpend_key = _handle_dpend_key
    App._draw_dpend_menu = _draw_dpend_menu
    App._draw_dpend = _draw_dpend
    App._dpend_draw_line = _dpend_draw_line

