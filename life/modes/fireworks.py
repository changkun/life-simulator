"""Mode: fireworks — simulation mode for the life package."""
import curses
import math
import random
import time


def _fireworks_init(self, preset: str):
    """Initialize fireworks simulation."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.fireworks_rows = max(20, max_y - 3)
    self.fireworks_cols = max(20, max_x - 1)
    self.fireworks_generation = 0
    self.fireworks_particles = []
    self.fireworks_rockets = []
    self.fireworks_total_launched = 0
    self.fireworks_total_bursts = 0

    if preset == "finale":
        self.fireworks_gravity = 0.05
        self.fireworks_launch_rate = 0.18
        self.fireworks_wind = 0.0
        self.fireworks_auto_launch = True
    elif preset == "gentle":
        self.fireworks_gravity = 0.04
        self.fireworks_launch_rate = 0.04
        self.fireworks_wind = 0.005
        self.fireworks_auto_launch = True
    elif preset == "crossette":
        self.fireworks_gravity = 0.05
        self.fireworks_launch_rate = 0.07
        self.fireworks_wind = 0.0
        self.fireworks_auto_launch = True
    elif preset == "willow":
        self.fireworks_gravity = 0.06
        self.fireworks_launch_rate = 0.06
        self.fireworks_wind = 0.003
        self.fireworks_auto_launch = True
    elif preset == "ring":
        self.fireworks_gravity = 0.05
        self.fireworks_launch_rate = 0.07
        self.fireworks_wind = 0.0
        self.fireworks_auto_launch = True
    else:  # random
        self.fireworks_gravity = 0.05
        self.fireworks_launch_rate = 0.08
        self.fireworks_wind = 0.0
        self.fireworks_auto_launch = True

    # Launch a few initial rockets
    for _ in range(3):
        self._fireworks_launch(preset)



def _fireworks_launch(self, preset: str | None = None):
    """Launch a single rocket from the bottom."""
    cols = self.fireworks_cols
    rows = self.fireworks_rows
    # Random launch position along the bottom
    c = random.randint(cols // 6, cols * 5 // 6)
    r = float(rows - 1)
    # Upward velocity with slight horizontal variance
    vr = -(random.uniform(1.2, 2.0))
    vc = random.uniform(-0.3, 0.3) + self.fireworks_wind
    # Fuse = how high before exploding (fraction of screen)
    fuse = random.randint(rows // 4, rows * 2 // 3)
    color = random.choice(self.FIREWORKS_COLORS)

    if preset == "crossette":
        pattern = "crossette"
    elif preset == "willow":
        pattern = "willow"
    elif preset == "ring":
        pattern = "ring"
    elif preset == "finale":
        pattern = random.choice(self.FIREWORKS_PATTERNS)
    elif preset == "gentle":
        pattern = random.choice(["spherical", "willow"])
    else:
        pattern = random.choice(self.FIREWORKS_PATTERNS)

    # rocket: [r, c, vr, vc, fuse, color, pattern]
    self.fireworks_rockets.append([r, c, vr, vc, fuse, color, pattern])
    self.fireworks_total_launched += 1



def _fireworks_explode(self, r: float, c: float, color: int, pattern: str):
    """Create an explosion burst at (r, c) with the given pattern."""
    particles = self.fireworks_particles
    self.fireworks_total_bursts += 1

    if pattern == "spherical":
        n_sparks = random.randint(30, 60)
        for _ in range(n_sparks):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.3, 1.2)
            vr = math.sin(angle) * speed
            vc = math.cos(angle) * speed
            life = random.randint(15, 35)
            spark_color = color if random.random() < 0.7 else random.choice(self.FIREWORKS_COLORS)
            # [r, c, vr, vc, life, max_life, color, kind, trail_positions]
            particles.append([r, c, vr, vc, life, life, spark_color, "spark", []])

    elif pattern == "ring":
        n_sparks = random.randint(24, 40)
        speed = random.uniform(0.7, 1.1)
        for i in range(n_sparks):
            angle = 2 * math.pi * i / n_sparks
            vr = math.sin(angle) * speed
            vc = math.cos(angle) * speed
            life = random.randint(18, 30)
            particles.append([r, c, vr, vc, life, life, color, "spark", []])
        # Inner ring
        if random.random() < 0.5:
            inner_speed = speed * 0.5
            color2 = random.choice(self.FIREWORKS_COLORS)
            for i in range(n_sparks // 2):
                angle = 2 * math.pi * i / (n_sparks // 2)
                vr = math.sin(angle) * inner_speed
                vc = math.cos(angle) * inner_speed
                life = random.randint(12, 22)
                particles.append([r, c, vr, vc, life, life, color2, "spark", []])

    elif pattern == "willow":
        n_sparks = random.randint(40, 70)
        for _ in range(n_sparks):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.2, 0.9)
            vr = math.sin(angle) * speed
            vc = math.cos(angle) * speed
            life = random.randint(30, 55)  # longer life for drooping effect
            particles.append([r, c, vr, vc, life, life, color, "willow", []])

    elif pattern == "crossette":
        # Initial burst into 4-6 sub-rockets
        n_sub = random.randint(4, 6)
        for i in range(n_sub):
            angle = 2 * math.pi * i / n_sub + random.uniform(-0.2, 0.2)
            speed = random.uniform(0.6, 1.0)
            vr = math.sin(angle) * speed
            vc = math.cos(angle) * speed
            life = random.randint(10, 16)
            # crossette sub-rockets explode again when they die
            particles.append([r, c, vr, vc, life, life, color, "crossette", []])



def _fireworks_step(self):
    """Advance the fireworks simulation by one tick."""
    gravity = self.fireworks_gravity
    wind = self.fireworks_wind
    rows = self.fireworks_rows
    cols = self.fireworks_cols

    # Auto-launch new rockets
    if self.fireworks_auto_launch and random.random() < self.fireworks_launch_rate:
        self._fireworks_launch(self.fireworks_preset_name.lower().replace(" ", "")
                               if self.fireworks_preset_name else None)

    # Update rockets
    new_rockets = []
    for rocket in self.fireworks_rockets:
        r, c, vr, vc, fuse, color, pattern = rocket
        # Apply gravity (slows the upward motion)
        vr += gravity
        vc += wind
        r += vr
        c += vc
        fuse -= 1

        if fuse <= 0 or vr >= 0:
            # Explode!
            self._fireworks_explode(r, c, color, pattern)
        elif 0 <= r < rows and 0 <= c < cols:
            rocket[0] = r
            rocket[1] = c
            rocket[2] = vr
            rocket[3] = vc
            rocket[4] = fuse
            new_rockets.append(rocket)
    self.fireworks_rockets = new_rockets

    # Update particles
    new_particles = []
    for p in self.fireworks_particles:
        r, c, vr, vc, life, max_life, color, kind, trail = p
        life -= 1
        if life <= 0:
            # Crossette sub-rockets create secondary bursts
            if kind == "crossette":
                sub_color = random.choice(self.FIREWORKS_COLORS)
                self._fireworks_explode(r, c, sub_color, "spherical")
            continue

        # Store trail position
        trail.append((r, c))
        if len(trail) > 6:
            trail.pop(0)

        # Apply gravity
        vr += gravity * (1.5 if kind == "willow" else 0.8)
        vc += wind

        # Add slight random jitter
        vr += random.uniform(-0.02, 0.02)
        vc += random.uniform(-0.02, 0.02)

        # Drag
        drag = 0.97 if kind == "willow" else 0.985
        vr *= drag
        vc *= drag

        r += vr
        c += vc

        if 0 <= r < rows and 0 <= c < cols:
            p[0] = r
            p[1] = c
            p[2] = vr
            p[3] = vc
            p[4] = life
            new_particles.append(p)
    self.fireworks_particles = new_particles
    self.fireworks_generation += 1



def _enter_fireworks_mode(self):
    """Enter fireworks mode — show preset menu."""
    self.fireworks_menu = True
    self.fireworks_menu_sel = 0
    self._flash("Fireworks — select a show")



def _exit_fireworks_mode(self):
    """Exit fireworks mode."""
    self.fireworks_mode = False
    self.fireworks_menu = False
    self.fireworks_running = False
    self.fireworks_particles = []
    self.fireworks_rockets = []
    self._flash("Fireworks mode OFF")



def _handle_fireworks_menu_key(self, key: int) -> bool:
    """Handle keys in the fireworks preset menu."""
    if key == -1:
        return True
    n = len(self.FIREWORKS_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.fireworks_menu_sel = (self.fireworks_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.fireworks_menu_sel = (self.fireworks_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.fireworks_menu = False
        self._flash("Fireworks cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        name, _desc, preset_id = self.FIREWORKS_PRESETS[self.fireworks_menu_sel]
        self.fireworks_menu = False
        self.fireworks_mode = True
        self.fireworks_running = True
        self.fireworks_preset_name = name
        self._fireworks_init(preset_id)
        self._flash(f"Fireworks [{name}] — Space=pause, f=launch, g/G=gravity, q=exit")
        return True
    return True



def _handle_fireworks_key(self, key: int) -> bool:
    """Handle keys while in fireworks mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_fireworks_mode()
        return True
    if key == ord(" "):
        self.fireworks_running = not self.fireworks_running
        self._flash("Playing" if self.fireworks_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self._fireworks_step()
        return True
    if key == ord("R"):
        self.fireworks_mode = False
        self.fireworks_menu = True
        self.fireworks_menu_sel = 0
        self._flash("Fireworks — select a show")
        return True
    if key == ord("r"):
        preset_id = ""
        for name, _desc, pid in self.FIREWORKS_PRESETS:
            if name == self.fireworks_preset_name:
                preset_id = pid
                break
        self._fireworks_init(preset_id or "random")
        self._flash("Reset!")
        return True
    # Manual launch
    if key == ord("f") or key in (10, 13, curses.KEY_ENTER):
        preset_map = {name: pid for name, _desc, pid in self.FIREWORKS_PRESETS}
        pid = preset_map.get(self.fireworks_preset_name, "random")
        self._fireworks_launch(pid)
        return True
    # Toggle auto-launch
    if key == ord("a"):
        self.fireworks_auto_launch = not self.fireworks_auto_launch
        self._flash(f"Auto-launch: {'ON' if self.fireworks_auto_launch else 'OFF'}")
        return True
    # Gravity
    if key == ord("g"):
        self.fireworks_gravity = min(0.2, self.fireworks_gravity + 0.01)
        self._flash(f"Gravity: {self.fireworks_gravity:.2f}")
        return True
    if key == ord("G"):
        self.fireworks_gravity = max(0.01, self.fireworks_gravity - 0.01)
        self._flash(f"Gravity: {self.fireworks_gravity:.2f}")
        return True
    # Wind
    if key == ord("w"):
        self.fireworks_wind += 0.005
        self._flash(f"Wind: {self.fireworks_wind:.3f}")
        return True
    if key == ord("W"):
        self.fireworks_wind -= 0.005
        self._flash(f"Wind: {self.fireworks_wind:.3f}")
        return True
    # Launch rate
    if key == ord("l"):
        self.fireworks_launch_rate = min(0.5, self.fireworks_launch_rate + 0.02)
        self._flash(f"Launch rate: {self.fireworks_launch_rate:.2f}")
        return True
    if key == ord("L"):
        self.fireworks_launch_rate = max(0.01, self.fireworks_launch_rate - 0.02)
        self._flash(f"Launch rate: {self.fireworks_launch_rate:.2f}")
        return True
    # Speed
    if key == ord(">") or key == ord("+") or key == ord("="):
        self.fireworks_steps_per_frame = min(10, self.fireworks_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.fireworks_steps_per_frame}")
        return True
    if key == ord("<") or key == ord("-") or key == ord("_"):
        self.fireworks_steps_per_frame = max(1, self.fireworks_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.fireworks_steps_per_frame}")
        return True
    return True



def _draw_fireworks_menu(self, max_y: int, max_x: int):
    """Draw the fireworks preset selection menu."""
    self.stdscr.erase()
    title = "── Fireworks ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Particle-based fireworks with gravity, bursts, and trailing sparks"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.FIREWORKS_PRESETS)
    for i, (name, desc, _pid) in enumerate(self.FIREWORKS_PRESETS):
        y = 5 + i
        if y >= max_y - 12:
            break
        line = f"  {name:<18s} {desc}"
        attr = curses.color_pair(6)
        if i == self.fireworks_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_lines = [
        "",
        "Rockets launch upward with gravity, explode into colorful bursts",
        "with randomized patterns (spherical, ring, willow, crossette),",
        "then fade with trailing sparks.",
        "",
        "Controls: f=launch, a=auto-launch, g/G=gravity, w/W=wind,",
        "          l/L=launch rate, >/<=speed, r=reset, R=menu, q=exit",
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



def _draw_fireworks(self, max_y: int, max_x: int):
    """Draw the fireworks simulation."""
    self.stdscr.erase()
    rows = self.fireworks_rows
    cols = self.fireworks_cols
    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, max_x - 1)

    # Draw particle trails first (dimmer)
    for p in self.fireworks_particles:
        r, c, vr, vc, life, max_life, color, kind, trail = p
        trail_chars = self.FIREWORKS_CHARS["trail"]
        for ti, (tr, tc) in enumerate(trail):
            sr = int(tr)
            sc = int(tc)
            if 0 <= sr < view_rows and 0 <= sc < view_cols:
                fade_idx = min(len(trail_chars) - 1, len(trail) - 1 - ti)
                ch = trail_chars[fade_idx]
                attr = curses.color_pair(color) | curses.A_DIM
                try:
                    self.stdscr.addstr(sr + 1, sc, ch, attr)
                except curses.error:
                    pass

    # Draw active particles
    for p in self.fireworks_particles:
        r, c, vr, vc, life, max_life, color, kind, trail = p
        sr = int(r)
        sc = int(c)
        if 0 <= sr < view_rows and 0 <= sc < view_cols:
            life_frac = life / max_life if max_life > 0 else 0
            spark_chars = self.FIREWORKS_CHARS["spark"]
            if life_frac > 0.7:
                ch = spark_chars[min(4, len(spark_chars) - 1)]
                attr = curses.color_pair(color) | curses.A_BOLD
            elif life_frac > 0.4:
                ch = spark_chars[min(3, len(spark_chars) - 1)]
                attr = curses.color_pair(color)
            elif life_frac > 0.15:
                ch = spark_chars[min(1, len(spark_chars) - 1)]
                attr = curses.color_pair(color) | curses.A_DIM
            else:
                ch = spark_chars[0]
                attr = curses.color_pair(color) | curses.A_DIM

            # Crossette sub-rockets are brighter
            if kind == "crossette":
                ch = "✦"
                attr = curses.color_pair(color) | curses.A_BOLD

            try:
                self.stdscr.addstr(sr + 1, sc, ch, attr)
            except curses.error:
                pass

    # Draw rockets (ascending)
    rocket_chars = self.FIREWORKS_CHARS["rocket"]
    for rocket in self.fireworks_rockets:
        r, c, vr, vc, fuse, color, pattern = rocket
        sr = int(r)
        sc = int(c)
        if 0 <= sr < view_rows and 0 <= sc < view_cols:
            ch = rocket_chars[self.fireworks_generation % len(rocket_chars)]
            attr = curses.color_pair(color) | curses.A_BOLD
            try:
                self.stdscr.addstr(sr + 1, sc, ch, attr)
            except curses.error:
                pass
            # Rocket trail (a few chars below)
            for ti in range(1, 4):
                tr = sr + ti
                if 0 <= tr < view_rows:
                    trail_ch = self.FIREWORKS_CHARS["trail"][min(ti - 1, len(self.FIREWORKS_CHARS["trail"]) - 1)]
                    try:
                        self.stdscr.addstr(tr + 1, sc, trail_ch, curses.color_pair(3) | curses.A_DIM)
                    except curses.error:
                        pass

    # Title bar
    n_particles = len(self.fireworks_particles)
    n_rockets = len(self.fireworks_rockets)
    status = (f" Fireworks [{self.fireworks_preset_name}]"
              f"  Gen:{self.fireworks_generation}"
              f"  Rockets:{n_rockets}  Sparks:{n_particles}"
              f"  Launched:{self.fireworks_total_launched}"
              f"  Bursts:{self.fireworks_total_bursts}"
              f"  {'▶ PLAY' if self.fireworks_running else '⏸ PAUSE'}")
    try:
        self.stdscr.addstr(0, 0, status[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Info bar
    info_y = max_y - 2
    info = (f" grav={self.fireworks_gravity:.2f}"
            f"  wind={self.fireworks_wind:.3f}"
            f"  rate={self.fireworks_launch_rate:.2f}"
            f"  auto={'ON' if self.fireworks_auto_launch else 'OFF'}"
            f"  steps/f={self.fireworks_steps_per_frame}")
    try:
        self.stdscr.addstr(info_y, 0, info[:max_x - 1], curses.color_pair(6))
    except curses.error:
        pass

    # Hint bar
    hint_y = max_y - 1
    now = time.monotonic()
    if self.message and now - self.message_time < 3.0:
        hint = f" {self.message}"
    else:
        hint = " [Space]=play [f]=launch [a]=auto [g/G]=grav [w/W]=wind [l/L]=rate [R]=menu [q]=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register fireworks mode methods on the App class."""
    App._fireworks_init = _fireworks_init
    App._fireworks_launch = _fireworks_launch
    App._fireworks_explode = _fireworks_explode
    App._fireworks_step = _fireworks_step
    App._enter_fireworks_mode = _enter_fireworks_mode
    App._exit_fireworks_mode = _exit_fireworks_mode
    App._handle_fireworks_menu_key = _handle_fireworks_menu_key
    App._handle_fireworks_key = _handle_fireworks_key
    App._draw_fireworks_menu = _draw_fireworks_menu
    App._draw_fireworks = _draw_fireworks

