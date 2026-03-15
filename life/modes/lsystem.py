"""Mode: lsystem — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS

def _enter_lsystem_mode(self) -> None:
    self.lsystem_menu = True
    self.lsystem_menu_sel = 0



def _exit_lsystem_mode(self) -> None:
    self.lsystem_mode = False
    self.lsystem_menu = False
    self.lsystem_running = False
    self.lsystem_plants = []
    self.lsystem_segments = []
    self.lsystem_leaves = []



def _handle_lsystem_menu_key(self, key: int) -> bool:
    n = len(self.LSYSTEM_PRESETS)
    if key in (curses.KEY_UP, ord("k")):
        self.lsystem_menu_sel = (self.lsystem_menu_sel - 1) % n
    elif key in (curses.KEY_DOWN, ord("j")):
        self.lsystem_menu_sel = (self.lsystem_menu_sel + 1) % n
    elif key in (ord("q"), 27):
        self.lsystem_menu = False
    elif key in (ord("\n"), ord("\r"), curses.KEY_ENTER):
        name, _desc, preset_id = self.LSYSTEM_PRESETS[self.lsystem_menu_sel]
        self.lsystem_menu = False
        self.lsystem_mode = True
        self.lsystem_running = False
        self.lsystem_preset_name = name
        self._lsystem_init(preset_id)
    return True



def _handle_lsystem_key(self, key: int) -> bool:
    if key in (ord("q"), 27):
        self._exit_lsystem_mode()
    elif key == ord(" "):
        self.lsystem_running = not self.lsystem_running
    elif key in (ord("n"), ord(".")):
        self._lsystem_step()
    elif key == ord("R"):
        self.lsystem_menu = True
        self.lsystem_menu_sel = 0
    elif key == ord("r"):
        # Reset current preset
        preset_id = ""
        for _n, _d, pid in self.LSYSTEM_PRESETS:
            if _n == self.lsystem_preset_name:
                preset_id = pid
                break
        if preset_id:
            self._lsystem_init(preset_id)
    elif key == ord("a"):
        # Decrease branching angle
        for p in self.lsystem_plants:
            p["angle"] = max(5.0, p["angle"] - 2.0)
        self.lsystem_angle = max(5.0, self.lsystem_angle - 2.0)
        self._lsystem_rebuild_all()
    elif key == ord("A"):
        # Increase branching angle
        for p in self.lsystem_plants:
            p["angle"] = min(90.0, p["angle"] + 2.0)
        self.lsystem_angle = min(90.0, self.lsystem_angle + 2.0)
        self._lsystem_rebuild_all()
    elif key == ord("g"):
        # Decrease growth rate
        self.lsystem_growth_rate = max(0.2, self.lsystem_growth_rate - 0.1)
    elif key == ord("G"):
        # Increase growth rate
        self.lsystem_growth_rate = min(3.0, self.lsystem_growth_rate + 0.1)
    elif key in (curses.KEY_LEFT,):
        # Shift light direction left
        self.lsystem_light_dir = (self.lsystem_light_dir - 10) % 360
        self._lsystem_rebuild_all()
    elif key in (curses.KEY_RIGHT,):
        # Shift light direction right
        self.lsystem_light_dir = (self.lsystem_light_dir + 10) % 360
        self._lsystem_rebuild_all()
    elif key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
    elif key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
    return True



def _lsystem_init(self, preset: str) -> None:
    max_y, max_x = self.stdscr.getmaxyx()
    self.lsystem_rows = max_y - 3
    self.lsystem_cols = max_x - 1
    self.lsystem_generation = 0
    self.lsystem_current_depth = 0
    self.lsystem_plants = []
    self.lsystem_segments = []
    self.lsystem_leaves = []
    self._lsystem_build_preset(preset)



def _lsystem_build_preset(self, preset: str) -> None:
    import math as _m
    cx = self.lsystem_cols // 2
    base_y = float(self.lsystem_rows - 1)

    if preset == "binary_tree":
        self.lsystem_max_depth = 8
        self.lsystem_angle = 30.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_plants = [{
            "x": float(cx), "y": base_y,
            "axiom": "F",
            "rules": {"F": "FF+[+F-F-F]-[-F+F+F]"},
            "angle": 30.0,
            "depth": 0,
            "string": "F",
            "length": float(self.lsystem_rows) / 5.0,
            "length_scale": 0.5,
        }]
    elif preset == "fern":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 22.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_plants = [{
            "x": float(cx), "y": base_y,
            "axiom": "X",
            "rules": {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"},
            "angle": 22.0,
            "depth": 0,
            "string": "X",
            "length": float(self.lsystem_rows) / 4.0,
            "length_scale": 0.5,
        }]
    elif preset == "bush":
        self.lsystem_max_depth = 6
        self.lsystem_angle = 25.7
        self.lsystem_growth_rate = 1.2
        self.lsystem_plants = [{
            "x": float(cx), "y": base_y,
            "axiom": "F",
            "rules": {"F": "F[+F]F[-F][F]"},
            "angle": 25.7,
            "depth": 0,
            "string": "F",
            "length": float(self.lsystem_rows) / 4.0,
            "length_scale": 0.5,
        }]
    elif preset == "seaweed":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 18.0
        self.lsystem_growth_rate = 0.8
        self.lsystem_plants = [{
            "x": float(cx), "y": base_y,
            "axiom": "F",
            "rules": {"F": "FF-[-F+F+F]+[+F-F-F]"},
            "angle": 18.0,
            "depth": 0,
            "string": "F",
            "length": float(self.lsystem_rows) / 3.5,
            "length_scale": 0.52,
        }]
    elif preset == "willow":
        self.lsystem_max_depth = 7
        self.lsystem_angle = 20.0
        self.lsystem_growth_rate = 0.9
        self.lsystem_plants = [{
            "x": float(cx), "y": base_y,
            "axiom": "F",
            "rules": {"F": "FF+[+F-F]-[-F+F+F]"},
            "angle": 20.0,
            "depth": 0,
            "string": "F",
            "length": float(self.lsystem_rows) / 4.0,
            "length_scale": 0.55,
        }]
    elif preset == "pine":
        self.lsystem_max_depth = 8
        self.lsystem_angle = 35.0
        self.lsystem_growth_rate = 1.0
        self.lsystem_plants = [{
            "x": float(cx), "y": base_y,
            "axiom": "F",
            "rules": {"F": "F[+F]F[-F]F"},
            "angle": 35.0,
            "depth": 0,
            "string": "F",
            "length": float(self.lsystem_rows) / 5.0,
            "length_scale": 0.45,
        }]
    elif preset == "garden":
        self.lsystem_max_depth = 6
        self.lsystem_angle = 25.0
        self.lsystem_growth_rate = 1.0
        spread = self.lsystem_cols // 5
        species = [
            ("F", {"F": "FF+[+F-F-F]-[-F+F+F]"}, 28.0),  # tree
            ("X", {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}, 22.0),  # fern
            ("F", {"F": "F[+F]F[-F][F]"}, 25.7),  # bush
        ]
        positions = [cx - spread, cx, cx + spread]
        for i, pos_x in enumerate(positions):
            ax, ru, ang = species[i % len(species)]
            self.lsystem_plants.append({
                "x": float(pos_x), "y": base_y,
                "axiom": ax,
                "rules": dict(ru),
                "angle": ang,
                "depth": 0,
                "string": ax,
                "length": float(self.lsystem_rows) / 5.0,
                "length_scale": 0.5,
            })

    self._lsystem_rebuild_all()



def _lsystem_expand(self, string: str, rules: dict[str, str]) -> str:
    result: list[str] = []
    for ch in string:
        result.append(rules.get(ch, ch))
    return "".join(result)



def _lsystem_interpret(self, plant: dict) -> tuple[list[tuple[float, float, float, float, int]], list[tuple[float, float]]]:
    """Interpret an L-system string into line segments and leaf positions."""
    import math
    string = plant["string"]
    angle_deg = plant["angle"]
    length = plant["length"]
    length_scale = plant["length_scale"]
    start_x = plant["x"]
    start_y = plant["y"]

    # Apply light direction bias
    light_bias = math.radians(self.lsystem_light_dir) * 0.15

    segments: list[tuple[float, float, float, float, int]] = []
    leaves: list[tuple[float, float]] = []
    stack: list[tuple[float, float, float, float]] = []  # x, y, heading, cur_len

    x = start_x
    y = start_y
    heading = -math.pi / 2 + light_bias  # start pointing up
    cur_len = length
    depth = 0

    for ch in string:
        if ch == "F":
            nx = x + cur_len * math.cos(heading)
            ny = y + cur_len * math.sin(heading)
            segments.append((x, y, nx, ny, depth))
            x, y = nx, ny
        elif ch == "f":
            x += cur_len * math.cos(heading)
            y += cur_len * math.sin(heading)
        elif ch == "+":
            heading += math.radians(angle_deg)
        elif ch == "-":
            heading -= math.radians(angle_deg)
        elif ch == "[":
            stack.append((x, y, heading, cur_len))
            cur_len *= length_scale
            depth += 1
        elif ch == "]":
            if stack:
                leaves.append((x, y))
                x, y, heading, cur_len = stack.pop()
                depth = max(0, depth - 1)
        elif ch == "X":
            pass  # placeholder for expansion

    return segments, leaves



def _lsystem_rebuild_all(self) -> None:
    """Rebuild all segments and leaves from current plant strings."""
    self.lsystem_segments = []
    self.lsystem_leaves = []
    for plant in self.lsystem_plants:
        segs, lvs = self._lsystem_interpret(plant)
        self.lsystem_segments.extend(segs)
        self.lsystem_leaves.extend(lvs)



def _lsystem_step(self) -> None:
    """Grow all plants by one L-system expansion step."""
    any_grew = False
    for plant in self.lsystem_plants:
        if plant["depth"] < self.lsystem_max_depth:
            plant["string"] = self._lsystem_expand(plant["string"], plant["rules"])
            plant["depth"] += 1
            any_grew = True
    if any_grew:
        self.lsystem_generation += 1
        self._lsystem_rebuild_all()



def _draw_lsystem_menu(self, max_y: int, max_x: int) -> None:
    self.stdscr.erase()
    title = "═══ L-System Plant Growth ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD)
    except curses.error:
        pass

    desc = "Grow fractal plants using Lindenmayer system grammars"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(desc)) // 2), desc, curses.A_DIM)
    except curses.error:
        pass

    start_y = 5
    for i, (name, description, _pid) in enumerate(self.LSYSTEM_PRESETS):
        if start_y + i >= max_y - 3:
            break
        marker = "▸ " if i == self.lsystem_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.lsystem_menu_sel else curses.A_NORMAL
        line = f"{marker}{name:<16s} {description}"
        try:
            self.stdscr.addstr(start_y + i, 4, line[:max_x - 6], attr)
        except curses.error:
            pass

    hint = " [↑↓]=select  [Enter]=start  [q]=back"
    try:
        self.stdscr.addstr(max_y - 2, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_lsystem(self, max_y: int, max_x: int) -> None:
    import math
    self.stdscr.erase()

    rows = self.lsystem_rows
    cols = self.lsystem_cols

    # Build a character grid
    grid: list[list[str]] = [[" "] * cols for _ in range(rows)]
    color_grid: list[list[int]] = [[0] * cols for _ in range(rows)]

    # Trunk/branch characters by depth
    trunk_chars = ["║", "│", "┃", "╎", "╏", "┊", "┆", "·"]
    branch_chars_right = ["╲", "\\", "╲", "\\", "╲", "·"]
    branch_chars_left = ["╱", "/", "╱", "/", "╱", "·"]

    # Draw segments
    for x1, y1, x2, y2, depth in self.lsystem_segments:
        # Bresenham-style line rasterization
        steps = max(int(max(abs(x2 - x1), abs(y2 - y1))), 1)
        for s in range(steps + 1):
            t = s / steps if steps > 0 else 0
            px = x1 + t * (x2 - x1)
            py = y1 + t * (y2 - y1)
            r = int(round(py))
            c = int(round(px))
            if 0 <= r < rows and 0 <= c < cols:
                dx = x2 - x1
                dy = y2 - y1
                angle = math.atan2(dy, dx) if (abs(dx) + abs(dy)) > 0.01 else -math.pi / 2
                adeg = math.degrees(angle) % 360

                # Choose character based on angle
                d_idx = min(depth, len(trunk_chars) - 1)
                if 60 < adeg < 120 or 240 < adeg < 300:
                    # Mostly horizontal
                    ch = "─" if depth < 3 else "╌" if depth < 5 else "·"
                elif (30 < adeg <= 60) or (210 < adeg <= 240):
                    ch = branch_chars_right[min(depth, len(branch_chars_right) - 1)]
                elif (120 <= adeg < 150) or (300 <= adeg < 330):
                    ch = branch_chars_left[min(depth, len(branch_chars_left) - 1)]
                else:
                    ch = trunk_chars[d_idx]

                # Color: deeper branches get dimmer/greener
                if depth == 0:
                    col = 4  # brown/dark
                elif depth <= 2:
                    col = 3  # yellow/wood
                else:
                    col = 2  # green

                if grid[r][c] == " " or color_grid[r][c] < col:
                    grid[r][c] = ch
                    color_grid[r][c] = col

    # Draw leaves
    leaf_chars = ["🌿", "♣", "✿", "❀", "♠", "●", "◆"]
    simple_leaf_chars = ["&", "*", "@", "#", "%", "o"]
    for lx, ly in self.lsystem_leaves:
        r = int(round(ly))
        c = int(round(lx))
        if 0 <= r < rows and 0 <= c < cols:
            if grid[r][c] == " " or color_grid[r][c] <= 2:
                grid[r][c] = simple_leaf_chars[hash((r, c)) % len(simple_leaf_chars)]
                color_grid[r][c] = 2  # green

    # Draw ground line
    for c in range(cols):
        if rows - 1 >= 0:
            if grid[rows - 1][c] == " ":
                grid[rows - 1][c] = "▓" if (c % 3 != 0) else "░"
                color_grid[rows - 1][c] = 3  # brown

    # Render grid to screen
    for r in range(min(rows, max_y - 2)):
        line_parts: list[tuple[str, int]] = []
        for c in range(min(cols, max_x - 1)):
            ch = grid[r][c]
            col = color_grid[r][c]
            try:
                attr = curses.color_pair(col)
                if col == 2:
                    attr |= curses.A_BOLD
                self.stdscr.addstr(r, c, ch, attr)
            except curses.error:
                pass

    # Status bar
    plant_depths = "/".join(str(p["depth"]) for p in self.lsystem_plants)
    status = (
        f" {self.lsystem_preset_name} │ "
        f"Gen {self.lsystem_generation} │ "
        f"Depth {plant_depths}/{self.lsystem_max_depth} │ "
        f"Angle {self.lsystem_angle:.0f}° │ "
        f"Growth {self.lsystem_growth_rate:.1f}x │ "
        f"Light {self.lsystem_light_dir:.0f}° │ "
        f"{'▶ RUN' if self.lsystem_running else '⏸ STOP'}"
    )
    try:
        self.stdscr.addstr(max_y - 3, 0, status[:max_x - 1], curses.color_pair(6) | curses.A_BOLD)
    except curses.error:
        pass

    if self.message and time.monotonic() - self.message_time < 2.0:
        hint = f" {self.message}"
    else:
        hint = " [Space]=play [n]=step [a/A]=angle [←→]=light [g/G]=growth [r]=reset [R]=menu [q]=exit"
    try:
        self.stdscr.addstr(max_y - 2, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register lsystem mode methods on the App class."""
    App._enter_lsystem_mode = _enter_lsystem_mode
    App._exit_lsystem_mode = _exit_lsystem_mode
    App._handle_lsystem_menu_key = _handle_lsystem_menu_key
    App._handle_lsystem_key = _handle_lsystem_key
    App._lsystem_init = _lsystem_init
    App._lsystem_build_preset = _lsystem_build_preset
    App._lsystem_expand = _lsystem_expand
    App._lsystem_interpret = _lsystem_interpret
    App._lsystem_rebuild_all = _lsystem_rebuild_all
    App._lsystem_step = _lsystem_step
    App._draw_lsystem_menu = _draw_lsystem_menu
    App._draw_lsystem = _draw_lsystem

