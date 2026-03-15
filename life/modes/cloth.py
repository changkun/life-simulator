"""Mode: cloth — simulation mode for the life package."""
import curses
import math
import random
import time


def _cloth_build_points(self, preset: str):
    """Set up cloth point mass grid and constraints for a preset."""
    rows, cols = self.cloth_rows, self.cloth_cols
    # Determine grid dimensions to fit display
    gw = min(cols, 50)
    gh = min(rows - 4, 30)
    self.cloth_grid_w = gw
    self.cloth_grid_h = gh
    self.cloth_spacing = 1.0
    self.cloth_points = []
    self.cloth_constraints = []
    self.cloth_tear_threshold = 3.0

    # Offset to center the cloth in the display
    ox = (cols - gw) / 2.0
    oy = 2.0

    # Create point masses: [x, y, old_x, old_y, pinned(0/1)]
    for r in range(gh):
        for c in range(gw):
            x = ox + c * self.cloth_spacing
            y = oy + r * self.cloth_spacing
            self.cloth_points.append([x, y, x, y, 0.0])

    # Create constraints (structural springs)
    sp = self.cloth_spacing
    for r in range(gh):
        for c in range(gw):
            idx = r * gw + c
            # Horizontal
            if c < gw - 1:
                self.cloth_constraints.append([idx, idx + 1, sp])
            # Vertical
            if r < gh - 1:
                self.cloth_constraints.append([idx, idx + gw, sp])

    # Apply preset-specific pinning and parameters
    if preset == "hanging":
        self.cloth_gravity = 0.5
        self.cloth_wind = 0.0
        self.cloth_damping = 0.99
        # Pin entire top row
        for c in range(gw):
            self.cloth_points[c][4] = 1.0
    elif preset == "curtain":
        self.cloth_gravity = 0.4
        self.cloth_wind = 0.05
        self.cloth_damping = 0.98
        # Pin two points at top
        self.cloth_points[0][4] = 1.0
        self.cloth_points[gw - 1][4] = 1.0
    elif preset == "flag":
        self.cloth_gravity = 0.15
        self.cloth_wind = 0.3
        self.cloth_damping = 0.97
        # Pin left edge
        for r in range(gh):
            self.cloth_points[r * gw][4] = 1.0
    elif preset == "hammock":
        self.cloth_gravity = 0.6
        self.cloth_wind = 0.0
        self.cloth_damping = 0.99
        # Pin four corners
        self.cloth_points[0][4] = 1.0
        self.cloth_points[gw - 1][4] = 1.0
        self.cloth_points[(gh - 1) * gw][4] = 1.0
        self.cloth_points[(gh - 1) * gw + gw - 1][4] = 1.0
    elif preset == "net":
        self.cloth_gravity = 0.4
        self.cloth_wind = 0.0
        self.cloth_damping = 0.99
        self.cloth_spacing = 2.0
        self.cloth_tear_threshold = 5.0
        # Rebuild with wider spacing
        self.cloth_points = []
        self.cloth_constraints = []
        gw = min(cols // 2, 25)
        gh = min((rows - 4) // 2, 15)
        self.cloth_grid_w = gw
        self.cloth_grid_h = gh
        ox = (cols - gw * 2) / 2.0
        oy = 2.0
        for r in range(gh):
            for c in range(gw):
                x = ox + c * 2.0
                y = oy + r * 2.0
                self.cloth_points.append([x, y, x, y, 0.0])
        for r in range(gh):
            for c in range(gw):
                idx = r * gw + c
                if c < gw - 1:
                    self.cloth_constraints.append([idx, idx + 1, 2.0])
                if r < gh - 1:
                    self.cloth_constraints.append([idx, idx + gw, 2.0])
        # Pin top row
        for c in range(gw):
            self.cloth_points[c][4] = 1.0
    elif preset == "silk":
        self.cloth_gravity = 0.3
        self.cloth_wind = 0.02
        self.cloth_damping = 0.96
        self.cloth_constraint_iters = 8
        self.cloth_tear_threshold = 2.5
        # Pin top row
        for c in range(gw):
            self.cloth_points[c][4] = 1.0



def _cloth_init(self, preset: str):
    """Initialize cloth simulation for a given preset."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.cloth_rows = max_y - 3
    self.cloth_cols = (max_x - 1) // 2
    if self.cloth_rows < 10:
        self.cloth_rows = 10
    if self.cloth_cols < 10:
        self.cloth_cols = 10
    self.cloth_generation = 0
    self.cloth_cursor_r = 0
    self.cloth_cursor_c = 0
    self.cloth_constraint_iters = 5
    self._cloth_build_points(preset)



def _cloth_step(self):
    """Advance cloth simulation by one timestep using Verlet integration."""
    points = self.cloth_points
    grav = self.cloth_gravity
    wind = self.cloth_wind
    damp = self.cloth_damping

    # Verlet integration for each point
    for p in points:
        if p[4] > 0.5:  # pinned
            continue
        # Current velocity from position difference
        vx = (p[0] - p[2]) * damp
        vy = (p[1] - p[3]) * damp

        # Add wind (horizontal force with slight randomness)
        wx = wind
        if wind != 0:
            wx += (random.random() - 0.5) * abs(wind) * 0.5

        # Store old position
        p[2] = p[0]
        p[3] = p[1]

        # Update position
        p[0] += vx + wx
        p[1] += vy + grav

    # Satisfy constraints (iterative relaxation)
    to_remove = []
    for _iter in range(self.cloth_constraint_iters):
        for ci, con in enumerate(self.cloth_constraints):
            p1 = points[con[0]]
            p2 = points[con[1]]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 0.0001:
                continue

            # Tear if stretched too far
            if dist > con[2] * self.cloth_tear_threshold:
                if ci not in to_remove:
                    to_remove.append(ci)
                continue

            diff = (con[2] - dist) / dist
            ox = dx * 0.5 * diff
            oy = dy * 0.5 * diff

            if p1[4] < 0.5 and p2[4] < 0.5:
                p1[0] -= ox
                p1[1] -= oy
                p2[0] += ox
                p2[1] += oy
            elif p1[4] > 0.5:
                p2[0] += ox * 2
                p2[1] += oy * 2
            elif p2[4] > 0.5:
                p1[0] -= ox * 2
                p1[1] -= oy * 2

    # Remove torn constraints (reverse order to keep indices valid)
    for ci in sorted(to_remove, reverse=True):
        self.cloth_constraints.pop(ci)

    # Boundary constraints
    max_x = float(self.cloth_cols - 1)
    max_y = float(self.cloth_rows - 1)
    for p in points:
        if p[4] > 0.5:
            continue
        if p[0] < 0:
            p[0] = 0.0
        if p[0] > max_x:
            p[0] = max_x
        if p[1] < 0:
            p[1] = 0.0
        if p[1] > max_y:
            p[1] = max_y

    self.cloth_generation += 1



def _enter_cloth_mode(self):
    """Enter cloth simulation mode."""
    self.cloth_menu = True
    self.cloth_menu_sel = 0



def _exit_cloth_mode(self):
    """Exit cloth simulation mode and clean up."""
    self.cloth_mode = False
    self.cloth_menu = False
    self.cloth_running = False
    self.cloth_points = []
    self.cloth_constraints = []



def _handle_cloth_menu_key(self, key: int) -> bool:
    """Handle input in cloth preset menu."""
    n = len(self.CLOTH_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.cloth_menu_sel = (self.cloth_menu_sel - 1) % n
    elif key == curses.KEY_DOWN or key == ord("j"):
        self.cloth_menu_sel = (self.cloth_menu_sel + 1) % n
    elif key == ord("q") or key == 27:
        self.cloth_menu = False
        return True
    elif key in (ord("\n"), ord("\r"), curses.KEY_ENTER):
        name, _desc, preset_id = self.CLOTH_PRESETS[self.cloth_menu_sel]
        self.cloth_menu = False
        self.cloth_mode = True
        self.cloth_running = False
        self.cloth_preset_name = name
        self._cloth_init(preset_id)
    return True



def _handle_cloth_key(self, key: int) -> bool:
    """Handle input during cloth simulation."""
    if key == ord("q") or key == 27:
        self._exit_cloth_mode()
        return True
    if key == ord(" "):
        self.cloth_running = not self.cloth_running
        self._flash("Playing" if self.cloth_running else "Paused")
    elif key == ord("n"):
        self._cloth_step()
    elif key == ord("R") or key == ord("m"):
        self.cloth_mode = False
        self.cloth_menu = True
        self.cloth_menu_sel = 0
    elif key == curses.KEY_UP or key == ord("k"):
        self.cloth_cursor_r = max(0, self.cloth_cursor_r - 1)
    elif key == curses.KEY_DOWN or key == ord("j"):
        self.cloth_cursor_r = min(self.cloth_grid_h - 1, self.cloth_cursor_r + 1)
    elif key == curses.KEY_LEFT or key == ord("h"):
        self.cloth_cursor_c = max(0, self.cloth_cursor_c - 1)
    elif key == curses.KEY_RIGHT or key == ord("l"):
        self.cloth_cursor_c = min(self.cloth_grid_w - 1, self.cloth_cursor_c + 1)
    elif key == ord("p"):
        # Toggle pin at cursor
        idx = self.cloth_cursor_r * self.cloth_grid_w + self.cloth_cursor_c
        if 0 <= idx < len(self.cloth_points):
            pt = self.cloth_points[idx]
            pt[4] = 0.0 if pt[4] > 0.5 else 1.0
            self._flash("Pinned" if pt[4] > 0.5 else "Unpinned")
    elif key == ord("x"):
        # Tear constraints around cursor point
        idx = self.cloth_cursor_r * self.cloth_grid_w + self.cloth_cursor_c
        before = len(self.cloth_constraints)
        self.cloth_constraints = [c for c in self.cloth_constraints
                                  if c[0] != idx and c[1] != idx]
        torn = before - len(self.cloth_constraints)
        self._flash(f"Torn {torn} constraints")
    elif key == ord("r"):
        # Reset with same preset
        for _n, _d, pid in self.CLOTH_PRESETS:
            if _n == self.cloth_preset_name:
                self._cloth_init(pid)
                self._flash("Reset")
                break
    elif key == ord("g"):
        self.cloth_gravity = min(2.0, self.cloth_gravity + 0.05)
        self._flash(f"Gravity: {self.cloth_gravity:.2f}")
    elif key == ord("G"):
        self.cloth_gravity = max(0.0, self.cloth_gravity - 0.05)
        self._flash(f"Gravity: {self.cloth_gravity:.2f}")
    elif key == ord("w"):
        self.cloth_wind += 0.05
        self._flash(f"Wind: {self.cloth_wind:.2f}")
    elif key == ord("W"):
        self.cloth_wind -= 0.05
        self._flash(f"Wind: {self.cloth_wind:.2f}")
    elif key == ord("d"):
        self.cloth_damping = min(1.0, self.cloth_damping + 0.005)
        self._flash(f"Damping: {self.cloth_damping:.3f}")
    elif key == ord("D"):
        self.cloth_damping = max(0.9, self.cloth_damping - 0.005)
        self._flash(f"Damping: {self.cloth_damping:.3f}")
    elif key == ord("t"):
        self.cloth_tear_threshold = min(10.0, self.cloth_tear_threshold + 0.5)
        self._flash(f"Tear threshold: {self.cloth_tear_threshold:.1f}")
    elif key == ord("T"):
        self.cloth_tear_threshold = max(1.5, self.cloth_tear_threshold - 0.5)
        self._flash(f"Tear threshold: {self.cloth_tear_threshold:.1f}")
    elif key == ord("+") or key == ord("="):
        self.cloth_steps_per_frame = min(10, self.cloth_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.cloth_steps_per_frame}")
    elif key == ord("-") or key == ord("_"):
        self.cloth_steps_per_frame = max(1, self.cloth_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.cloth_steps_per_frame}")
    return True



def _draw_cloth_menu(self, max_y: int, max_x: int):
    """Draw the cloth simulation preset selection menu."""
    self.stdscr.erase()
    title = "── Cloth Simulation ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Gravity-driven fabric with spring constraints and Verlet integration"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.CLOTH_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.CLOTH_PRESETS):
        y = 5 + i
        if y >= max_y - 12:
            break
        line = f"  {name:<18s} {desc}"
        attr = curses.color_pair(6)
        if i == self.cloth_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_lines = [
        "",
        "Point masses connected by spring constraints simulate fabric.",
        "Gravity pulls the cloth down, wind pushes it sideways.",
        "Pin/unpin points and tear the fabric interactively.",
        "",
        "Controls: p=pin/unpin, x=tear, g/G=gravity, w/W=wind,",
        "          d/D=damping, t/T=tear threshold, r=reset, q=exit",
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



def _draw_cloth(self, max_y: int, max_x: int):
    """Draw the cloth simulation."""
    self.stdscr.erase()
    points = self.cloth_points
    gw = self.cloth_grid_w
    gh = self.cloth_grid_h

    # Build a screen buffer
    # Draw constraints as lines between points
    drawn = set()
    for con in self.cloth_constraints:
        p1 = points[con[0]]
        p2 = points[con[1]]
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]

        # Bresenham-like: draw chars along the constraint
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        steps = max(1, int(dist * 1.5))
        for s in range(steps + 1):
            t = s / max(steps, 1)
            px = x1 + (x2 - x1) * t
            py = y1 + (y2 - y1) * t
            sr = int(round(py))
            sc = int(round(px))
            if 1 <= sr < max_y - 2 and 0 <= sc * 2 < max_x - 2:
                if (sr, sc) not in drawn:
                    drawn.add((sr, sc))

                    # Choose character based on constraint direction
                    dx = x2 - x1
                    dy = y2 - y1
                    if abs(dx) > abs(dy) * 2:
                        ch = "──"
                    elif abs(dy) > abs(dx) * 2:
                        ch = "│ "
                    elif dx * dy > 0:
                        ch = "╲ "
                    else:
                        ch = "╱ "

                    # Color based on stretch (tension)
                    stretch = dist / max(con[2], 0.001)
                    if stretch > 2.0:
                        attr = curses.color_pair(2) | curses.A_BOLD  # red = high tension
                    elif stretch > 1.5:
                        attr = curses.color_pair(2)  # red
                    elif stretch > 1.2:
                        attr = curses.color_pair(3)  # yellow = moderate
                    else:
                        attr = curses.color_pair(8)  # white/normal

                    try:
                        self.stdscr.addstr(sr, sc * 2, ch, attr)
                    except curses.error:
                        pass

    # Draw point masses on top
    for r in range(gh):
        for c in range(gw):
            idx = r * gw + c
            if idx >= len(points):
                continue
            p = points[idx]
            sr = int(round(p[1]))
            sc = int(round(p[0]))
            if 1 <= sr < max_y - 2 and 0 <= sc * 2 < max_x - 2:
                is_cursor = (r == self.cloth_cursor_r and c == self.cloth_cursor_c)
                if p[4] > 0.5:
                    # Pinned point
                    ch = "◆ "
                    attr = curses.color_pair(2) | curses.A_BOLD  # red = pinned
                else:
                    ch = "● "
                    attr = curses.color_pair(5)  # cyan

                if is_cursor:
                    attr = attr | curses.A_REVERSE

                try:
                    self.stdscr.addstr(sr, sc * 2, ch, attr)
                except curses.error:
                    pass

    # Draw cursor if point is off-screen
    cidx = self.cloth_cursor_r * gw + self.cloth_cursor_c
    if 0 <= cidx < len(points):
        cp = points[cidx]
        csr = int(round(cp[1]))
        csc = int(round(cp[0]))
        if not (1 <= csr < max_y - 2 and 0 <= csc * 2 < max_x - 2):
            try:
                self.stdscr.addstr(1, 0, "++ cursor off-screen",
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    # Status bar
    n_pinned = sum(1 for p in points if p[4] > 0.5)
    status = (f" [{self.cloth_preset_name}] Gen:{self.cloth_generation}"
              f" Pts:{len(points)} Cons:{len(self.cloth_constraints)}"
              f" Pinned:{n_pinned}"
              f" Grav:{self.cloth_gravity:.2f} Wind:{self.cloth_wind:.2f}"
              f" Damp:{self.cloth_damping:.3f}"
              f" {'▶ PLAY' if self.cloth_running else '⏸ PAUSE'}")
    try:
        self.stdscr.addstr(0, 0, status[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if self.message and time.time() - self.message_time < 3.0:
        hint = f" {self.message}"
    else:
        hint = " [Space]=play [n]=step [p]=pin [x]=tear [g/G]=grav [w/W]=wind [d/D]=damp [t/T]=tear [R]=menu [q]=exit"
    hint_y = max_y - 2
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register cloth mode methods on the App class."""
    App._cloth_build_points = _cloth_build_points
    App._cloth_init = _cloth_init
    App._cloth_step = _cloth_step
    App._enter_cloth_mode = _enter_cloth_mode
    App._exit_cloth_mode = _exit_cloth_mode
    App._handle_cloth_menu_key = _handle_cloth_menu_key
    App._handle_cloth_key = _handle_cloth_key
    App._draw_cloth_menu = _draw_cloth_menu
    App._draw_cloth = _draw_cloth

