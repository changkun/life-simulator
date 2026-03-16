"""Mode: fire — simulation mode for the life package."""
import curses
import math
import random
import time


from life.utils import sparkline

def _enter_fire_mode(self):
    """Enter Forest Fire mode — show preset menu."""
    self.fire_menu = True
    self.fire_menu_sel = 0
    self._flash("Forest Fire — select a scenario")



def _exit_fire_mode(self):
    """Exit Forest Fire mode."""
    self.fire_mode = False
    self.fire_menu = False
    self.fire_running = False
    self.fire_grid = []
    self.fire_counts = []
    self._flash("Forest Fire mode OFF")



def _fire_init(self, preset_idx: int):
    """Initialize forest fire simulation with the given preset."""
    (name, _desc, density, p_grow, p_light, ash_decay) = self.FIRE_PRESETS[preset_idx]
    self.fire_preset_name = name
    self.fire_generation = 0
    self.fire_running = False
    self.fire_p_grow = p_grow
    self.fire_p_lightning = p_light
    self.fire_initial_density = density
    self.fire_ash_decay = ash_decay
    self.fire_counts = []

    max_y, max_x = self.stdscr.getmaxyx()
    self.fire_rows = max(10, max_y - 4)
    self.fire_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.fire_rows, self.fire_cols

    # 0=empty, 1=tree, 2=burning, 3=ash, 4=ember
    self.fire_grid = [
        [1 if random.random() < density else 0 for _ in range(cols)]
        for _ in range(rows)
    ]

    self.fire_menu = False
    self.fire_mode = True
    self._flash(f"Forest Fire: {name} — Space to start")



def _fire_step(self):
    """Advance the forest fire CA by one generation.

    States: 0=empty, 1=tree, 2=burning(flame), 3=ash, 4=ember
    Transitions: tree->burning (neighbor fire or lightning),
                 burning->ember, ember->ash, ash->empty (decay),
                 empty->tree (growth)
    """
    rows, cols = self.fire_rows, self.fire_cols
    grid = self.fire_grid
    p_grow = self.fire_p_grow
    p_light = self.fire_p_lightning
    ash_decay = self.fire_ash_decay

    new_grid = [[0] * cols for _ in range(rows)]
    n_tree = n_fire = n_ash = n_empty = 0

    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            if cell == 2:
                # Burning -> ember
                new_grid[r][c] = 4
                n_fire += 1
            elif cell == 4:
                # Ember -> ash
                new_grid[r][c] = 3
                n_ash += 1
            elif cell == 3:
                # Ash -> empty (with probability)
                if random.random() < ash_decay:
                    new_grid[r][c] = 0
                    n_empty += 1
                else:
                    new_grid[r][c] = 3
                    n_ash += 1
            elif cell == 1:
                # Tree: check if any neighbor is burning or ember
                burning_neighbor = False
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] in (2, 4):
                            burning_neighbor = True
                            break
                    if burning_neighbor:
                        break
                if burning_neighbor:
                    new_grid[r][c] = 2  # catch fire
                    n_fire += 1
                elif random.random() < p_light:
                    new_grid[r][c] = 2  # lightning strike
                    n_fire += 1
                else:
                    new_grid[r][c] = 1  # stay tree
                    n_tree += 1
            else:
                # Empty: grow tree with probability p
                if random.random() < p_grow:
                    new_grid[r][c] = 1
                    n_tree += 1
                else:
                    new_grid[r][c] = 0
                    n_empty += 1

    self.fire_grid = new_grid
    self.fire_generation += 1
    self.fire_counts.append((n_tree, n_fire, n_ash, n_empty))
    # Keep last 200 data points for the density sparkline
    if len(self.fire_counts) > 200:
        self.fire_counts = self.fire_counts[-200:]



def _handle_fire_menu_key(self, key: int) -> bool:
    """Handle input in Forest Fire preset menu."""
    n = len(self.FIRE_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.fire_menu_sel = (self.fire_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.fire_menu_sel = (self.fire_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._fire_init(self.fire_menu_sel)
    elif key in (ord("q"), 27):
        self.fire_menu = False
        self._flash("Forest Fire cancelled")
    return True



def _handle_fire_key(self, key: int) -> bool:
    """Handle input in active Forest Fire simulation."""
    if key == ord(" "):
        self.fire_running = not self.fire_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.fire_steps_per_frame):
            self._fire_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.FIRE_PRESETS)
                    if p[0] == self.fire_preset_name), 0)
        self._fire_init(idx)
    elif key in (ord("R"), ord("m")):
        self.fire_mode = False
        self.fire_menu = True
    elif key == ord("p"):
        self.fire_p_grow = min(1.0, self.fire_p_grow + 0.005)
        self._flash(f"Growth prob: {self.fire_p_grow:.3f}")
    elif key == ord("P"):
        self.fire_p_grow = max(0.001, self.fire_p_grow - 0.005)
        self._flash(f"Growth prob: {self.fire_p_grow:.3f}")
    elif key == ord("l"):
        self.fire_p_lightning = min(0.1, self.fire_p_lightning + 0.0005)
        self._flash(f"Lightning prob: {self.fire_p_lightning:.4f}")
    elif key == ord("L"):
        self.fire_p_lightning = max(0.0001, self.fire_p_lightning - 0.0005)
        self._flash(f"Lightning prob: {self.fire_p_lightning:.4f}")
    elif key == ord("a"):
        self.fire_ash_decay = min(1.0, self.fire_ash_decay + 0.01)
        self._flash(f"Ash decay: {self.fire_ash_decay:.2f}")
    elif key == ord("A"):
        self.fire_ash_decay = max(0.01, self.fire_ash_decay - 0.01)
        self._flash(f"Ash decay: {self.fire_ash_decay:.2f}")
    elif key == ord("+") or key == ord("="):
        self.fire_steps_per_frame = min(20, self.fire_steps_per_frame + 1)
    elif key == ord("-"):
        self.fire_steps_per_frame = max(1, self.fire_steps_per_frame - 1)
    elif key in (ord("q"), 27):
        self._exit_fire_mode()
    else:
        return True
    return True



def _draw_fire_menu(self, max_y: int, max_x: int):
    """Draw the Forest Fire preset selection menu."""
    self.stdscr.erase()
    title = "── Forest Fire ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, *_rest) in enumerate(self.FIRE_PRESETS):
        y = 3 + i
        if y >= max_y - 2:
            break
        selected = "▶" if i == self.fire_menu_sel else " "
        line = f" {selected} {name:20} {desc}"
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.fire_menu_sel else curses.color_pair(6)
        try:
            self.stdscr.addstr(y, 0, line[:max_x - 1], attr)
        except curses.error:
            pass

    # Footer
    foot_y = min(3 + len(self.FIRE_PRESETS) + 1, max_y - 1)
    if foot_y < max_y:
        try:
            self.stdscr.addstr(foot_y, 2, "[j/k]=navigate  [Enter]=select  [q]=cancel",
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_fire(self, max_y: int, max_x: int):
    """Draw the active Forest Fire simulation."""
    self.stdscr.erase()
    grid = self.fire_grid
    rows, cols = self.fire_rows, self.fire_cols
    state = "▶ RUNNING" if self.fire_running else "⏸ PAUSED"

    # Count cells
    n_tree = n_fire = n_ash = n_empty = 0
    for r in range(rows):
        for c in range(cols):
            v = grid[r][c]
            if v == 1:
                n_tree += 1
            elif v in (2, 4):
                n_fire += 1
            elif v == 3:
                n_ash += 1
            else:
                n_empty += 1

    total = rows * cols
    pct_tree = 100.0 * n_tree / total if total else 0

    # Title bar
    title = (f" Forest Fire: {self.fire_preset_name}  |  gen {self.fire_generation}"
             f"  |  trees={n_tree} fire={n_fire} ash={n_ash} empty={n_empty}"
             f"  |  density={pct_tree:.1f}%  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    view_rows = max_y - 4
    view_cols = (max_x - 1) // 2

    # Draw grid
    for r in range(min(rows, view_rows)):
        for c in range(min(cols, view_cols)):
            val = grid[r][c]
            sx = c * 2
            sy = 1 + r
            if val == 0:
                # Empty — dark
                continue
            elif val == 1:
                # Tree — green
                ch = "██"
                attr = curses.color_pair(2)
            elif val == 2:
                # Burning — bright yellow/red bold
                ch = "▓▓"
                attr = curses.color_pair(3) | curses.A_BOLD
            elif val == 4:
                # Ember — dim red
                ch = "░░"
                attr = curses.color_pair(3)
            elif val == 3:
                # Ash/char — dim gray
                ch = "░░"
                attr = curses.color_pair(8) if curses.COLORS >= 8 else curses.color_pair(6)
            else:
                continue
            try:
                self.stdscr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Density sparkline (tree density over time)
    if self.fire_counts and max_x > 60:
        spark_chars = "▁▂▃▄▅▆▇█"
        spark_width = min(40, len(self.fire_counts))
        recent = self.fire_counts[-spark_width:]
        max_trees = max((c[0] for c in recent), default=1) or 1
        spark = ""
        for t, f, a, e in recent:
            idx = min(len(spark_chars) - 1, int(t / max_trees * (len(spark_chars) - 1)))
            spark += spark_chars[idx]
        spark_y = max_y - 3
        if spark_y > 1:
            label = f" density: {spark}"
            try:
                self.stdscr.addstr(spark_y, 0, label[:max_x - 1], curses.color_pair(2))
            except curses.error:
                pass

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = (f" Gen {self.fire_generation}  |  grow={self.fire_p_grow:.3f}"
                f"  |  lightning={self.fire_p_lightning:.4f}"
                f"  |  ash_decay={self.fire_ash_decay:.2f}"
                f"  |  steps/f={self.fire_steps_per_frame}")
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [p/P]=grow+/- [l/L]=lightning+/- [a/A]=ash+/- [+/-]=speed [r]=reset [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

def register(App):
    """Register fire mode methods on the App class."""
    App._enter_fire_mode = _enter_fire_mode
    App._exit_fire_mode = _exit_fire_mode
    App._fire_init = _fire_init
    App._fire_step = _fire_step
    App._handle_fire_menu_key = _handle_fire_menu_key
    App._handle_fire_key = _handle_fire_key
    App._draw_fire_menu = _draw_fire_menu
    App._draw_fire = _draw_fire

