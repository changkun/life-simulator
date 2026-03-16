"""Mode: aquarium — simulation mode for the life package."""
import curses
import math
import random
import time

AQUARIUM_PRESETS = [
    ("Goldfish Bowl", "Classic goldfish in a small bowl", "goldfish"),
    ("Tropical Reef", "Colorful tropical fish in a reef tank", "tropical"),
    ("Koi Pond", "Elegant koi swimming in a garden pond", "koi"),
    ("Deep Sea", "Mysterious deep-sea creatures in darkness", "deep"),
]

BUBBLE_CHARS = "·∘○◯"
SEAWEED_CHARS = ["}", "{", ")", "(", "]", "[", "|"]
SAND_CHARS = ["~", "≈", ".", ",", "'", "`", "·"]

FISH_SPECIES = [
    {"name": "Neon Tetra", "left": ["><>"], "right": ["<><"], "speed": (0.2, 0.5)},
    {"name": "Goldfish", "left": ["><))'>"], "right": ["<'((<>"], "speed": (0.15, 0.35)},
    {"name": "Angelfish", "left": [">{>"], "right": ["<}<"], "speed": (0.1, 0.3)},
    {"name": "Koi", "left": [">===>"], "right": ["<===<"], "speed": (0.1, 0.25)},
    {"name": "Guppy", "left": ["><>"], "right": ["<><"], "speed": (0.25, 0.6)},
    {"name": "Clownfish", "left": [">({>"], "right": ["<})>"], "speed": (0.15, 0.4)},
    {"name": "Pufferfish", "left": [">(O)>"], "right": ["<(O)<"], "speed": (0.1, 0.2)},
    {"name": "Anglerfish", "left": [">*-=>"], "right": ["<=--*<"], "speed": (0.05, 0.15)},
]


def _enter_aquarium_mode(self):
    """Enter Aquarium mode — show preset menu."""
    self.aquarium_mode = True
    self.aquarium_menu = True
    self.aquarium_menu_sel = 0
    self.aquarium_running = False




def _exit_aquarium_mode(self):
    """Exit Aquarium mode and clean up."""
    self.aquarium_mode = False
    self.aquarium_menu = False
    self.aquarium_running = False
    self.aquarium_fish = []
    self.aquarium_seaweed = []
    self.aquarium_bubbles = []
    self.aquarium_food = []
    self.aquarium_sand = []




def _aquarium_init(self, preset_key):
    """Initialize aquarium from selected preset."""
    import random as rng
    rows, cols = self.stdscr.getmaxyx()
    self.aquarium_rows = rows
    self.aquarium_cols = cols
    self.aquarium_menu = False
    self.aquarium_running = True
    self.aquarium_generation = 0
    self.aquarium_time = 0.0
    self.aquarium_startled = 0.0
    self.aquarium_caustic_phase = 0.0
    self.aquarium_fish = []
    self.aquarium_seaweed = []
    self.aquarium_bubbles = []
    self.aquarium_food = []
    self.aquarium_preset_name = preset_key

    sand_row = rows - 2
    # Generate sandy bottom
    self.aquarium_sand = []
    for c in range(cols):
        h = rng.choice([0, 0, 0, 1, 1, 2]) if rng.random() < 0.7 else 0
        self.aquarium_sand.append(h)

    # Spawn seaweed
    num_seaweed = max(3, cols // 8)
    for _ in range(num_seaweed):
        x = rng.randint(2, cols - 3)
        height = rng.randint(3, min(8, rows // 3))
        color = rng.choice([3, 11, 10])  # green variants
        phase = rng.uniform(0, 6.28)
        self.aquarium_seaweed.append({
            "x": x, "height": height, "color": color, "phase": phase,
            "speed": rng.uniform(0.5, 1.5),
        })

    # Spawn fish based on preset
    if preset_key == "tropical":
        species_pool = [0, 1, 2, 3, 4, 5]
        num_fish = rng.randint(10, 16)
    elif preset_key == "deep":
        species_pool = [5, 6, 7]
        num_fish = rng.randint(5, 8)
    elif preset_key == "koi":
        species_pool = [3, 4]
        num_fish = rng.randint(6, 10)
    else:  # goldfish
        species_pool = [1, 2]
        num_fish = rng.randint(4, 7)

    water_top = 2
    water_bottom = sand_row - 2
    for _ in range(num_fish):
        self._aquarium_spawn_fish(species_pool, water_top, water_bottom)

    # Initial bubble streams
    num_streams = rng.randint(1, 3)
    for _ in range(num_streams):
        bx = rng.randint(3, cols - 4)
        self.aquarium_bubbles.append({
            "x": float(bx), "y": float(sand_row - 1),
            "vx": 0.0, "vy": -rng.uniform(0.3, 0.8),
            "char_idx": 0, "age": 0,
            "stream_x": bx, "stream_delay": rng.randint(0, 20),
        })




def _aquarium_spawn_fish(self, species_pool, water_top, water_bottom):
    """Spawn a single fish in the tank."""
    import random as rng
    sp_idx = rng.choice(species_pool)
    sp = FISH_SPECIES[sp_idx]
    direction = rng.choice([-1, 1])  # -1 = left, 1 = right
    speed = rng.uniform(sp["speed"][0], sp["speed"][1])
    y = rng.uniform(water_top + 1, water_bottom)
    x = rng.uniform(5, self.aquarium_cols - 10)
    # Color: vary by species index
    colors = [2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14]
    color = rng.choice(colors)
    bob_phase = rng.uniform(0, 6.28)
    self.aquarium_fish.append({
        "species": sp_idx, "x": float(x), "y": float(y),
        "vx": speed * direction, "vy": 0.0,
        "color": color, "bob_phase": bob_phase,
        "bob_amp": rng.uniform(0.1, 0.4),
        "target_y": y,
    })




def _aquarium_step(self):
    """Advance aquarium simulation by one tick."""
    import random as rng
    import math
    self.aquarium_generation += 1
    self.aquarium_time += 0.1
    self.aquarium_caustic_phase += 0.05

    rows = self.aquarium_rows
    cols = self.aquarium_cols
    sand_row = rows - 2
    water_top = 2

    if self.aquarium_startled > 0:
        self.aquarium_startled -= 0.1

    # ── Move fish ──
    for fish in self.aquarium_fish:
        sp = FISH_SPECIES[fish["species"]]
        base_speed = rng.uniform(sp["speed"][0], sp["speed"][1])
        startle_mult = 2.5 if self.aquarium_startled > 0 else 1.0

        # Horizontal movement
        fish["x"] += fish["vx"] * startle_mult

        # Wrap around
        body = sp["left"] if fish["vx"] < 0 else sp["right"]
        body_len = len(body[0]) if body else 3
        if fish["vx"] > 0 and fish["x"] > cols + body_len:
            fish["x"] = -body_len - 1
        elif fish["vx"] < 0 and fish["x"] < -body_len - 1:
            fish["x"] = cols + body_len

        # Occasionally change direction
        if rng.random() < 0.005:
            fish["vx"] = -fish["vx"]

        # Vertical bobbing
        fish["bob_phase"] += 0.08
        bob = math.sin(fish["bob_phase"]) * fish["bob_amp"]
        fish["y"] = fish["target_y"] + bob

        # Occasionally change depth
        if rng.random() < 0.01:
            fish["target_y"] = rng.uniform(water_top + 1, sand_row - 3)

        # Clamp
        fish["y"] = max(water_top, min(sand_row - 2, fish["y"]))

        # Chase food
        if self.aquarium_food:
            nearest = min(self.aquarium_food,
                          key=lambda f: abs(f["x"] - fish["x"]) + abs(f["y"] - fish["y"]))
            dist = abs(nearest["x"] - fish["x"]) + abs(nearest["y"] - fish["y"])
            if dist < 15:
                if nearest["x"] > fish["x"]:
                    fish["vx"] = abs(fish["vx"])
                else:
                    fish["vx"] = -abs(fish["vx"])
                fish["target_y"] += (nearest["y"] - fish["y"]) * 0.1
            # Eat food
            if dist < 2:
                self.aquarium_food.remove(nearest)

    # ── Move bubbles ──
    new_bubbles = []
    for b in self.aquarium_bubbles:
        b["y"] += b["vy"]
        b["x"] += math.sin(b["age"] * 0.3) * 0.15  # gentle wobble
        b["age"] += 1
        # Grow bubble
        if b["age"] > 5:
            b["char_idx"] = min(b["char_idx"] + 1, len(BUBBLE_CHARS) - 1) if rng.random() < 0.05 else b["char_idx"]

        if b["y"] > water_top:
            new_bubbles.append(b)
        # Spawn new bubble in stream
        if b.get("stream_x") is not None and b["age"] % max(1, 8 - self.aquarium_speed) == 0:
            if rng.random() < 0.3:
                new_bubbles.append({
                    "x": float(b["stream_x"]) + rng.uniform(-0.5, 0.5),
                    "y": float(sand_row - 1),
                    "vx": 0.0, "vy": -rng.uniform(0.3, 0.8),
                    "char_idx": 0, "age": 0,
                    "stream_x": None, "stream_delay": 0,
                })
    self.aquarium_bubbles = new_bubbles

    # ── Move food ──
    for food in self.aquarium_food:
        food["y"] += 0.15  # sink slowly
        food["x"] += math.sin(food["age"] * 0.2) * 0.1
        food["age"] += 1
        if food["y"] > sand_row:
            food["y"] = float(sand_row)

    # Remove old food
    self.aquarium_food = [f for f in self.aquarium_food if f["age"] < 300]




def _handle_aquarium_menu_key(self, key: int) -> bool:
    """Handle keys in the aquarium preset menu."""
    if key == curses.KEY_UP:
        self.aquarium_menu_sel = (self.aquarium_menu_sel - 1) % len(AQUARIUM_PRESETS)
    elif key == curses.KEY_DOWN:
        self.aquarium_menu_sel = (self.aquarium_menu_sel + 1) % len(AQUARIUM_PRESETS)
    elif key in (curses.KEY_ENTER, 10, 13):
        _, _, preset_key = AQUARIUM_PRESETS[self.aquarium_menu_sel]
        self._aquarium_init(preset_key)
    elif key in (27, ord('q'), ord('Q')):
        self.aquarium_mode = False
        self.aquarium_menu = False
    else:
        return False
    return True




def _handle_aquarium_key(self, key: int) -> bool:
    """Handle keys during aquarium simulation."""
    import random as rng
    if key in (27,):  # ESC -> menu
        self.aquarium_running = False
        self.aquarium_menu = True
        self.aquarium_menu_sel = 0
        return True
    elif key in (ord('q'), ord('Q')):
        self.aquarium_mode = False
        self.aquarium_menu = False
        self.aquarium_running = False
        return True
    elif key == ord('R'):
        self.aquarium_running = False
        self.aquarium_menu = True
        self.aquarium_menu_sel = 0
        return True
    elif key == ord(' '):  # pause/resume
        self.aquarium_running = not self.aquarium_running
        return True
    elif key == ord('f') or key == ord('F'):
        # Feed fish — drop food from top
        cols = self.aquarium_cols
        for _ in range(rng.randint(3, 7)):
            self.aquarium_food.append({
                "x": rng.uniform(3, cols - 4),
                "y": 3.0,
                "age": 0,
            })
        return True
    elif key == ord('t') or key == ord('T'):
        # Tap glass — startle fish
        self.aquarium_startled = 3.0
        for fish in self.aquarium_fish:
            fish["vx"] = -fish["vx"] * 2.0
            sp = FISH_SPECIES[fish["species"]]
            max_spd = sp["speed"][1] * 2.5
            fish["vx"] = max(-max_spd, min(max_spd, fish["vx"]))
        return True
    elif key == ord('+') or key == ord('='):
        self.aquarium_speed = min(5, self.aquarium_speed + 1)
        return True
    elif key == ord('-') or key == ord('_'):
        self.aquarium_speed = max(1, self.aquarium_speed - 1)
        return True
    elif key == ord('a') or key == ord('A'):
        # Add a fish
        sand_row = self.aquarium_rows - 2
        if self.aquarium_preset_name == "tropical":
            pool = [0, 1, 2, 3, 4, 5]
        elif self.aquarium_preset_name == "deep":
            pool = [5, 6, 7]
        elif self.aquarium_preset_name == "koi":
            pool = [3, 4]
        else:
            pool = [1, 2]
        self._aquarium_spawn_fish(pool, 2, sand_row - 2)
        return True
    elif key == ord('d') or key == ord('D'):
        # Remove a fish
        if self.aquarium_fish:
            self.aquarium_fish.pop()
        return True
    elif key == ord('b') or key == ord('B'):
        # Add bubble stream
        import random as rng2
        cols = self.aquarium_cols
        sand_row = self.aquarium_rows - 2
        bx = rng2.randint(3, cols - 4)
        self.aquarium_bubbles.append({
            "x": float(bx), "y": float(sand_row - 1),
            "vx": 0.0, "vy": -rng2.uniform(0.3, 0.8),
            "char_idx": 0, "age": 0,
            "stream_x": bx, "stream_delay": 0,
        })
        return True
    elif key == ord('i') or key == ord('I'):
        self.aquarium_show_info = not self.aquarium_show_info
        return True
    return True  # consume all keys while in aquarium mode




def _draw_aquarium_menu(self, max_y: int, max_x: int):
    """Draw the aquarium preset selection menu."""
    self.stdscr.erase()
    title = "🐠  ASCII Aquarium / Fish Tank  🐠"
    subtitle = "A relaxing zen-mode aquarium with procedural ASCII fish"
    if max_x > len(title) + 2:
        try:
            self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title, curses.A_BOLD | curses.color_pair(4))
        except curses.error:
            pass
    if max_x > len(subtitle) + 2:
        try:
            self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle, curses.color_pair(7))
        except curses.error:
            pass

    y_start = 4
    for i, (name, desc, _) in enumerate(AQUARIUM_PRESETS):
        if y_start + i * 2 >= max_y - 3:
            break
        marker = " ▸ " if i == self.aquarium_menu_sel else "   "
        attr = curses.A_BOLD | curses.color_pair(4) if i == self.aquarium_menu_sel else curses.color_pair(7)
        try:
            self.stdscr.addstr(y_start + i * 2, 4, f"{marker}{name}", attr)
            if len(desc) + 8 < max_x:
                self.stdscr.addstr(y_start + i * 2 + 1, 8, desc, curses.color_pair(8) if i != self.aquarium_menu_sel else curses.color_pair(7))
        except curses.error:
            pass

    hint_y = min(y_start + len(AQUARIUM_PRESETS) * 2 + 2, max_y - 2)
    hint = "↑/↓ select   Enter start   q quit"
    try:
        self.stdscr.addstr(hint_y, max(0, (max_x - len(hint)) // 2), hint, curses.color_pair(8))
    except curses.error:
        pass




def _draw_aquarium(self, max_y: int, max_x: int):
    """Draw the full aquarium scene."""
    import math
    self.stdscr.erase()
    rows = max_y
    cols = max_x
    sand_row = rows - 2
    t = self.aquarium_time

    # ── Surface light ripples ──
    for c in range(min(cols - 1, self.aquarium_cols)):
        ripple = math.sin(c * 0.3 + t * 2.0) * 0.5 + math.sin(c * 0.7 + t * 1.3) * 0.3
        ch = "~" if ripple > 0.2 else "≈" if ripple > -0.2 else "~"
        try:
            color = curses.color_pair(4) if ripple > 0 else curses.color_pair(12)
            self.stdscr.addstr(1, c, ch, color)
        except curses.error:
            pass

    # ── Caustic light patterns on water ──
    for r in range(2, min(sand_row, rows - 1)):
        for c in range(0, min(cols - 1, self.aquarium_cols), 3):
            caustic = math.sin(c * 0.4 + r * 0.6 + self.aquarium_caustic_phase * 3) * \
                      math.cos(c * 0.3 - r * 0.4 + self.aquarium_caustic_phase * 2)
            if caustic > 0.7:
                try:
                    depth_fade = max(0, min(7, int((r - 2) / (sand_row - 2) * 6)))
                    if depth_fade < 3:
                        self.stdscr.addstr(r, c, "·", curses.color_pair(12) | curses.A_DIM)
                except curses.error:
                    pass

    # ── Draw sandy bottom ──
    for c in range(min(cols - 1, len(self.aquarium_sand))):
        h = self.aquarium_sand[c]
        for dh in range(h + 1):
            sr = sand_row - dh
            if 0 < sr < rows - 1:
                ch = SAND_CHARS[c % len(SAND_CHARS)]
                try:
                    self.stdscr.addstr(sr, c, ch, curses.color_pair(3) | curses.A_DIM)
                except curses.error:
                    pass

    # ── Draw seaweed ──
    for sw in self.aquarium_seaweed:
        bx = sw["x"]
        for seg in range(sw["height"]):
            sway = math.sin(t * sw["speed"] + sw["phase"] + seg * 0.5) * (1.0 + seg * 0.3)
            sx = int(bx + sway)
            sy = sand_row - seg - 1
            if 0 < sy < rows - 1 and 0 <= sx < cols - 1:
                ch = SEAWEED_CHARS[seg % len(SEAWEED_CHARS)]
                try:
                    self.stdscr.addstr(sy, sx, ch, curses.color_pair(sw["color"]))
                except curses.error:
                    pass

    # ── Draw bubbles ──
    for b in self.aquarium_bubbles:
        bx, by = int(b["x"]), int(b["y"])
        if 0 < by < rows - 1 and 0 <= bx < cols - 1:
            ch = BUBBLE_CHARS[min(b["char_idx"], len(BUBBLE_CHARS) - 1)]
            try:
                self.stdscr.addstr(by, bx, ch, curses.color_pair(12))
            except curses.error:
                pass

    # ── Draw food ──
    for food in self.aquarium_food:
        fx, fy = int(food["x"]), int(food["y"])
        if 0 < fy < rows - 1 and 0 <= fx < cols - 1:
            try:
                self.stdscr.addstr(fy, fx, "*", curses.color_pair(3))
            except curses.error:
                pass

    # ── Draw fish ──
    for fish in self.aquarium_fish:
        sp = FISH_SPECIES[fish["species"]]
        body = sp["left"] if fish["vx"] < 0 else sp["right"]
        body_str = body[0] if body else "><>"
        fx = int(fish["x"])
        fy = int(fish["y"])
        if 0 < fy < rows - 1:
            for ci, ch in enumerate(body_str):
                cx = fx + ci
                if 0 <= cx < cols - 1:
                    try:
                        attr = curses.color_pair(fish["color"]) | curses.A_BOLD
                        self.stdscr.addstr(fy, cx, ch, attr)
                    except curses.error:
                        pass

    # ── Title bar ──
    title = f" ASCII Aquarium — {self.aquarium_preset_name.title()} "
    if len(title) < cols:
        try:
            self.stdscr.addstr(0, 0, title.center(cols - 1), curses.A_REVERSE | curses.color_pair(4))
        except curses.error:
            pass

    # ── Bottom status ──
    status = f" Fish: {len(self.aquarium_fish)}  Speed: {self.aquarium_speed}x  Gen: {self.aquarium_generation} "
    controls = " f=feed  t=tap  a/d=add/remove fish  b=bubbles  +/-=speed  i=info  Space=pause  R=menu  q=quit "
    try:
        if len(status) < cols:
            self.stdscr.addstr(rows - 1, 0, status, curses.color_pair(7))
        remaining = cols - len(status) - 1
        if remaining > 10:
            self.stdscr.addstr(rows - 1, len(status), controls[:remaining], curses.color_pair(8))
    except curses.error:
        pass

    # ── Info overlay ──
    if self.aquarium_show_info:
        info_lines = [
            f"Preset: {self.aquarium_preset_name}",
            f"Fish: {len(self.aquarium_fish)}",
            f"Bubbles: {len(self.aquarium_bubbles)}",
            f"Seaweed: {len(self.aquarium_seaweed)}",
            f"Food: {len(self.aquarium_food)}",
            f"Generation: {self.aquarium_generation}",
            "",
            "f feed  t tap glass  a/d +/- fish",
            "b add bubbles  +/- speed  ESC menu",
        ]
        for i, line in enumerate(info_lines):
            if i + 1 < rows - 1 and len(line) + 2 < cols:
                try:
                    self.stdscr.addstr(i + 1, 1, line, curses.color_pair(7))
                except curses.error:
                    pass


def register(App):
    """Register aquarium mode methods on the App class."""
    App._enter_aquarium_mode = _enter_aquarium_mode
    App._exit_aquarium_mode = _exit_aquarium_mode
    App._aquarium_init = _aquarium_init
    App._aquarium_spawn_fish = _aquarium_spawn_fish
    App._aquarium_step = _aquarium_step
    App._handle_aquarium_menu_key = _handle_aquarium_menu_key
    App._handle_aquarium_key = _handle_aquarium_key
    App._draw_aquarium_menu = _draw_aquarium_menu
    App._draw_aquarium = _draw_aquarium

