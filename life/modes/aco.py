"""Mode: aco — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_aco_mode(self):
    """Enter ACO mode — show preset menu."""
    self.aco_menu = True
    self.aco_menu_sel = 0
    self._flash("Ant Colony — select a configuration")



def _exit_aco_mode(self):
    """Exit ACO mode."""
    self.aco_mode = False
    self.aco_menu = False
    self.aco_running = False
    self.aco_pheromone = []
    self.aco_ants = []
    self.aco_food = []
    self._flash("Ant Colony mode OFF")



def _aco_init(self, preset_idx: int):
    """Initialize ACO simulation with the given preset."""
    name, _desc, evap, dep, diff, ratio, num_food, food_r = self.ACO_PRESETS[preset_idx]
    self.aco_preset_name = name
    self.aco_evaporation = evap
    self.aco_deposit_strength = dep
    self.aco_diffusion = diff
    self.aco_generation = 0
    self.aco_running = False
    self.aco_food_collected = 0

    max_y, max_x = self.stdscr.getmaxyx()
    self.aco_rows = max(10, max_y - 3)
    self.aco_cols = max(10, (max_x - 1) // 2)
    rows, cols = self.aco_rows, self.aco_cols

    # Initialize pheromone grid
    self.aco_pheromone = [[0.0] * cols for _ in range(rows)]

    # Place nest at centre
    self.aco_nest = (rows // 2, cols // 2)

    # Place food sources randomly (away from nest)
    self.aco_food = []
    nr, nc = self.aco_nest
    for _ in range(num_food):
        for _attempt in range(50):
            fr = random.randint(food_r, rows - food_r - 1)
            fc = random.randint(food_r, cols - food_r - 1)
            dist = math.sqrt((fr - nr) ** 2 + (fc - nc) ** 2)
            if dist > min(rows, cols) * 0.25:
                self.aco_food.append([fr, fc, float(food_r * food_r * 4)])
                break

    # Spawn ants at nest
    self.aco_num_ants = max(20, int(rows * cols * ratio))
    self.aco_ants = []
    for _ in range(self.aco_num_ants):
        heading = random.random() * 2 * math.pi
        self.aco_ants.append([float(nr), float(nc), heading, 0.0])  # r, c, heading, has_food

    self.aco_menu = False
    self.aco_mode = True
    self._flash(f"Ant Colony: {name} — Space to start")



def _aco_step(self):
    """Advance ACO simulation by one step."""
    rows, cols = self.aco_rows, self.aco_cols
    pher = self.aco_pheromone
    nr, nc = self.aco_nest
    food_list = self.aco_food

    for ant in self.aco_ants:
        ar, ac, heading, has_food = ant[0], ant[1], ant[2], ant[3]
        ri, ci = int(ar) % rows, int(ac) % cols

        if has_food > 0.5:
            # Returning to nest — deposit pheromone, head towards nest
            pher[ri][ci] = min(1.0, pher[ri][ci] + self.aco_deposit_strength)
            # Steer towards nest
            dr = nr - ar
            dc = nc - ac
            target_angle = math.atan2(dr, dc)
            diff = target_angle - heading
            # Normalize angle diff to [-pi, pi]
            while diff > math.pi:
                diff -= 2 * math.pi
            while diff < -math.pi:
                diff += 2 * math.pi
            heading += diff * 0.3 + random.uniform(-0.2, 0.2)
            # Check if reached nest
            if abs(dr) < 2.0 and abs(dc) < 2.0:
                ant[3] = 0.0  # drop food
                self.aco_food_collected += 1
                heading = random.random() * 2 * math.pi  # turn around
        else:
            # Searching for food — follow pheromone or wander
            # Sense pheromone in three directions
            sense_dist = 3.0
            sense_angle = 0.5
            fl = self._aco_sense(ar, ac, heading + sense_angle, sense_dist)
            fc = self._aco_sense(ar, ac, heading, sense_dist)
            fr = self._aco_sense(ar, ac, heading - sense_angle, sense_dist)

            if fc >= fl and fc >= fr:
                heading += random.uniform(-0.1, 0.1)  # mostly straight
            elif fl > fr:
                heading += 0.3 + random.uniform(-0.1, 0.1)
            else:
                heading -= 0.3 + random.uniform(-0.1, 0.1)

            # Random wandering
            heading += random.uniform(-0.15, 0.15)

            # Check if near any food source
            for food in food_list:
                fdr = food[0] - ar
                fdc = food[1] - ac
                if abs(fdr) < 2.5 and abs(fdc) < 2.5 and food[2] > 0:
                    ant[3] = 1.0  # pick up food
                    food[2] -= 1.0
                    heading = math.atan2(nr - ar, nc - ac) + random.uniform(-0.3, 0.3)
                    break

        # Move forward
        move_speed = 1.0
        new_r = ar + math.sin(heading) * move_speed
        new_c = ac + math.cos(heading) * move_speed
        new_r = new_r % rows
        new_c = new_c % cols
        ant[0] = new_r
        ant[1] = new_c
        ant[2] = heading

    # Evaporate and diffuse pheromone
    evap = self.aco_evaporation
    diff_rate = self.aco_diffusion
    new_pher = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        rp = (r - 1) % rows
        rn = (r + 1) % rows
        for c in range(cols):
            cp = (c - 1) % cols
            cn = (c + 1) % cols
            # Diffusion: blend with neighbours
            avg = (
                pher[rp][cp] + pher[rp][c] + pher[rp][cn] +
                pher[r][cp] + pher[r][c] + pher[r][cn] +
                pher[rn][cp] + pher[rn][c] + pher[rn][cn]
            ) / 9.0
            blended = pher[r][c] * (1.0 - diff_rate) + avg * diff_rate
            new_pher[r][c] = max(0.0, blended - evap)
    self.aco_pheromone = new_pher

    # Remove depleted food sources
    self.aco_food = [f for f in food_list if f[2] > 0]

    self.aco_generation += 1



def _aco_sense(self, ar: float, ac: float, heading: float, dist: float) -> float:
    """Sense pheromone at a point ahead of the ant."""
    rows, cols = self.aco_rows, self.aco_cols
    sr = int(ar + math.sin(heading) * dist) % rows
    sc = int(ac + math.cos(heading) * dist) % cols
    return self.aco_pheromone[sr][sc]



def _handle_aco_menu_key(self, key: int) -> bool:
    """Handle input in ACO preset menu."""
    n = len(self.ACO_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.aco_menu_sel = (self.aco_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.aco_menu_sel = (self.aco_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._aco_init(self.aco_menu_sel)
    elif key in (ord("q"), 27):
        self.aco_menu = False
        self._flash("Ant Colony cancelled")
    return True



def _handle_aco_key(self, key: int) -> bool:
    """Handle input in active ACO simulation."""
    if key == ord(" "):
        self.aco_running = not self.aco_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.aco_steps_per_frame):
            self._aco_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.ACO_PRESETS)
                    if p[0] == self.aco_preset_name), 0)
        self._aco_init(idx)
        self.aco_running = False
    elif key == ord("R"):
        self.aco_mode = False
        self.aco_running = False
        self.aco_menu = True
        self.aco_menu_sel = 0
    elif key == ord("e"):
        self.aco_evaporation = min(0.2, self.aco_evaporation + 0.005)
        self._flash(f"Evaporation: {self.aco_evaporation:.3f}")
    elif key == ord("E"):
        self.aco_evaporation = max(0.001, self.aco_evaporation - 0.005)
        self._flash(f"Evaporation: {self.aco_evaporation:.3f}")
    elif key == ord("d"):
        self.aco_deposit_strength = min(1.0, self.aco_deposit_strength + 0.05)
        self._flash(f"Deposit: {self.aco_deposit_strength:.2f}")
    elif key == ord("D"):
        self.aco_deposit_strength = max(0.05, self.aco_deposit_strength - 0.05)
        self._flash(f"Deposit: {self.aco_deposit_strength:.2f}")
    elif key == ord("s"):
        self.aco_steps_per_frame = min(10, self.aco_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.aco_steps_per_frame}")
    elif key == ord("S"):
        self.aco_steps_per_frame = max(1, self.aco_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.aco_steps_per_frame}")
    elif key in (ord("q"), 27):
        self._exit_aco_mode()
    return True



def _draw_aco_menu(self, max_y: int, max_x: int):
    """Draw the ACO preset selection menu."""
    self.stdscr.erase()
    title = "── Ant Colony Optimization — Select Preset ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    for i, (name, desc, *_) in enumerate(self.ACO_PRESETS):
        y = 3 + i
        if y >= max_y - 1:
            break
        marker = "▶ " if i == self.aco_menu_sel else "  "
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.aco_menu_sel else curses.color_pair(6)
        line = f"{marker}{name:12s} — {desc}"
        try:
            self.stdscr.addstr(y, 4, line[:max_x - 5], attr)
        except curses.error:
            pass
    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_aco(self, max_y: int, max_x: int):
    """Draw the active ACO simulation."""
    self.stdscr.erase()
    pher = self.aco_pheromone
    rows, cols = self.aco_rows, self.aco_cols
    density = self.ACO_DENSITY
    state = "▶ RUNNING" if self.aco_running else "⏸ PAUSED"

    title = (f" Ant Colony: {self.aco_preset_name}  |  gen {self.aco_generation}"
             f"  |  evap={self.aco_evaporation:.3f}  dep={self.aco_deposit_strength:.2f}"
             f"  |  food={len(self.aco_food)}  collected={self.aco_food_collected}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Build a set of ant positions and food positions for overlay
    ant_positions: dict[tuple[int, int], bool] = {}
    for ant in self.aco_ants:
        ar, ac = int(ant[0]) % rows, int(ant[1]) % cols
        ant_positions[(ar, ac)] = ant[3] > 0.5  # True if carrying food

    food_cells: set[tuple[int, int]] = set()
    for food in self.aco_food:
        fr, fc = int(food[0]), int(food[1])
        rad = max(1, int(math.sqrt(food[2]) * 0.5))
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                if dr * dr + dc * dc <= rad * rad:
                    food_cells.add(((fr + dr) % rows, (fc + dc) % cols))

    nr, nc = self.aco_nest

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)
    for r in range(view_rows):
        for c in range(view_cols):
            # Check for special cells
            if abs(r - nr) <= 1 and abs(c - nc) <= 1:
                # Nest
                try:
                    self.stdscr.addstr(1 + r, c * 2, "🏠" if c == nc and r == nr else "▓▓",
                                       curses.color_pair(3) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            if (r, c) in food_cells:
                # Food source
                try:
                    self.stdscr.addstr(1 + r, c * 2, "██",
                                       curses.color_pair(2) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            if (r, c) in ant_positions:
                # Ant
                carrying = ant_positions[(r, c)]
                ch = "••"
                attr = curses.color_pair(4) | curses.A_BOLD if carrying else curses.color_pair(1) | curses.A_BOLD
                try:
                    self.stdscr.addstr(1 + r, c * 2, ch, attr)
                except curses.error:
                    pass
                continue
            # Pheromone trail
            v = pher[r][c]
            di = int(v * 4.99)
            di = max(0, min(4, di))
            ch = density[di]
            ci = int(v * 7.99)
            ci = max(0, min(7, ci))
            attr = curses.color_pair(80 + ci)
            if v > 0.5:
                attr |= curses.A_BOLD
            try:
                self.stdscr.addstr(1 + r, c * 2, ch, attr)
            except curses.error:
                pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        total_pher = sum(pher[r][c] for r in range(rows) for c in range(cols))
        avg_pher = total_pher / (rows * cols) if rows * cols > 0 else 0
        info = (f" Gen {self.aco_generation}  |  ants={self.aco_num_ants}"
                f"  |  food sources={len(self.aco_food)}  collected={self.aco_food_collected}"
                f"  |  avg pheromone={avg_pher:.4f}"
                f"  |  steps/f={self.aco_steps_per_frame}")
        try:
            self.stdscr.addstr(status_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [e/E]=evap+/- [d/D]=deposit+/- [s/S]=speed+/- [r]=reseed [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register aco mode methods on the App class."""
    App._enter_aco_mode = _enter_aco_mode
    App._exit_aco_mode = _exit_aco_mode
    App._aco_init = _aco_init
    App._aco_step = _aco_step
    App._aco_sense = _aco_sense
    App._handle_aco_menu_key = _handle_aco_menu_key
    App._handle_aco_key = _handle_aco_key
    App._draw_aco_menu = _draw_aco_menu
    App._draw_aco = _draw_aco

