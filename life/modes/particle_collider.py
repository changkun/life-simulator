"""Mode: collider — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_collider_mode(self):
    """Enter Particle Collider mode — show preset menu."""
    self.collider_mode = True
    self.collider_menu = True
    self.collider_menu_sel = 0
    self.collider_running = False




def _exit_collider_mode(self):
    """Exit Particle Collider mode and clean up."""
    self.collider_mode = False
    self.collider_menu = False
    self.collider_running = False
    self.collider_beams = []
    self.collider_showers = []
    self.collider_trails = []
    self.collider_detections = []
    self.collider_detector_log = []




def _collider_init(self, preset_key):
    """Initialize collider simulation from selected preset."""
    import random as rng
    import math
    rows, cols = self.stdscr.getmaxyx()
    self.collider_rows = rows
    self.collider_cols = cols
    self.collider_menu = False
    self.collider_running = True
    self.collider_generation = 0
    self.collider_time = 0.0
    self.collider_preset_name = preset_key
    self.collider_beams = []
    self.collider_showers = []
    self.collider_trails = []
    self.collider_detections = []
    self.collider_total_collisions = 0
    self.collider_detector_log = []
    self.collider_show_info = False

    # Ring geometry — elliptical to fit terminal aspect ratio
    self.collider_ring_cx = cols / 2.0
    self.collider_ring_cy = rows / 2.0 - 1
    self.collider_ring_rx = min(cols / 2.0 - 8, 45)
    self.collider_ring_ry = min(rows / 2.0 - 4, 18)

    # Set up 4 collision/interaction points at cardinal positions
    self.collider_collision_points = []
    for i in range(4):
        angle = i * math.pi / 2.0
        self.collider_collision_points.append({
            "angle": angle,
            "label": _COLLIDER_DETECTOR_LABELS[i],
            "flash": 0.0,
        })

    # Preset-specific parameters
    if preset_key == "lhc":
        self.collider_energy = 13.6
        num_beams = 12
        beam_speed = 0.08
        collision_rate = 0.03
    elif preset_key == "heavy_ion":
        self.collider_energy = 5.36
        num_beams = 8
        beam_speed = 0.06
        collision_rate = 0.06
    elif preset_key == "lepton":
        self.collider_energy = 0.209
        num_beams = 16
        beam_speed = 0.10
        collision_rate = 0.04
    else:  # discovery
        self.collider_energy = 14.0
        num_beams = 20
        beam_speed = 0.09
        collision_rate = 0.08

    self.collider_collision_rate = collision_rate

    # Spawn beam particles — half clockwise, half counter-clockwise
    for i in range(num_beams):
        angle = rng.uniform(0, 2 * math.pi)
        direction = 1 if i % 2 == 0 else -1
        speed_var = rng.uniform(0.8, 1.2)
        self.collider_beams.append({
            "angle": angle,
            "speed": beam_speed * speed_var * direction,
            "color": 4 if direction > 0 else 2,
            "trail": [],
        })




def _collider_spawn_shower(self, cx, cy, energy, preset_key):
    """Create a shower of decay products from a collision."""
    import random as rng
    import math

    # Determine how many particles to spawn
    if preset_key == "heavy_ion":
        num_particles = rng.randint(12, 25)
    elif preset_key == "lepton":
        num_particles = rng.randint(4, 8)
    else:
        num_particles = rng.randint(6, 16)

    shower_particles = []
    for _ in range(num_particles):
        angle = rng.uniform(0, 2 * math.pi)
        speed = rng.uniform(0.3, 1.5)
        lifetime = rng.randint(8, 30)
        char_idx = rng.randint(0, len(_COLLIDER_SHOWER_CHARS) - 1)
        color = rng.choice([2, 3, 4, 5, 6, 7, 10, 11, 13, 14])
        shower_particles.append({
            "x": cx, "y": cy,
            "vx": math.cos(angle) * speed * 1.8,  # wider in x for aspect ratio
            "vy": math.sin(angle) * speed,
            "life": lifetime,
            "max_life": lifetime,
            "char_idx": char_idx,
            "color": color,
        })

    self.collider_showers.append({
        "particles": shower_particles,
        "x": cx, "y": cy,
        "age": 0,
    })

    # Detect a particle
    if preset_key == "discovery":
        rare_chance = 0.4
    else:
        rare_chance = 0.15
    candidates = [p for p in _COLLIDER_PARTICLES if not p["rare"] or rng.random() < rare_chance]
    detected = rng.choice(candidates)
    mass_measured = detected["mass"] * rng.uniform(0.92, 1.08) if detected["mass"] > 0 else 0.0
    event = {
        "name": detected["name"],
        "symbol": detected["symbol"],
        "mass": mass_measured,
        "energy": energy * rng.uniform(0.3, 0.9),
        "color": detected["color"],
        "time": self.collider_time,
        "flash": 1.0,
    }
    self.collider_detections.append(event)

    # Add to log
    log_entry = f"  {detected['symbol']:>4s}  {detected['name']:<14s}  {mass_measured:>7.2f} GeV  E={event['energy']:.1f} TeV"
    self.collider_detector_log.append(log_entry)
    if len(self.collider_detector_log) > 50:
        self.collider_detector_log = self.collider_detector_log[-50:]




def _collider_step(self):
    """Advance the collider simulation by one step."""
    import random as rng
    import math

    self.collider_generation += 1
    self.collider_time += 0.05

    cx = self.collider_ring_cx
    cy = self.collider_ring_cy
    rx = self.collider_ring_rx
    ry = self.collider_ring_ry

    # Move beam particles around the ring
    for beam in self.collider_beams:
        beam["angle"] += beam["speed"]
        if beam["angle"] > 2 * math.pi:
            beam["angle"] -= 2 * math.pi
        if beam["angle"] < 0:
            beam["angle"] += 2 * math.pi

        # Record trail
        bx = cx + math.cos(beam["angle"]) * rx
        by = cy + math.sin(beam["angle"]) * ry
        beam["trail"].append((bx, by))
        if len(beam["trail"]) > 6:
            beam["trail"] = beam["trail"][-6:]

    # Check for collisions near interaction points
    for cp in self.collider_collision_points:
        cp["flash"] = max(0, cp["flash"] - 0.05)

        if rng.random() < self.collider_collision_rate:
            # Find if opposite-direction beams are near this point
            cw_near = []
            ccw_near = []
            for beam in self.collider_beams:
                angle_diff = abs(beam["angle"] - cp["angle"])
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                if angle_diff < 0.4:
                    if beam["speed"] > 0:
                        cw_near.append(beam)
                    else:
                        ccw_near.append(beam)

            if cw_near and ccw_near:
                # Collision!
                collision_x = cx + math.cos(cp["angle"]) * rx
                collision_y = cy + math.sin(cp["angle"]) * ry
                cp["flash"] = 1.0
                self.collider_total_collisions += 1
                self._collider_spawn_shower(
                    collision_x, collision_y,
                    self.collider_energy, self.collider_preset_name
                )

                # Add trail flash at collision point
                for _ in range(rng.randint(3, 8)):
                    tx = collision_x + rng.uniform(-2, 2)
                    ty = collision_y + rng.uniform(-1, 1)
                    self.collider_trails.append({
                        "x": tx, "y": ty, "life": rng.randint(5, 15),
                        "char": rng.choice(["✦", "✧", "⚡", "★", "⊕", "⊗"]),
                        "color": rng.choice([4, 6, 7, 14]),
                    })

    # Update shower particles
    for shower in self.collider_showers:
        shower["age"] += 1
        for p in shower["particles"]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= 0.96  # friction / deceleration
            p["vy"] *= 0.96
            p["life"] -= 1

        shower["particles"] = [p for p in shower["particles"] if p["life"] > 0]

    self.collider_showers = [s for s in self.collider_showers if s["particles"]]

    # Update trails
    for trail in self.collider_trails:
        trail["life"] -= 1
    self.collider_trails = [t for t in self.collider_trails if t["life"] > 0]

    # Decay detection flash
    for det in self.collider_detections:
        det["flash"] = max(0, det["flash"] - 0.02)
    # Keep only recent detections for display
    if len(self.collider_detections) > 20:
        self.collider_detections = self.collider_detections[-20:]




def _handle_collider_menu_key(self, key: int) -> bool:
    """Handle keys in the collider preset menu."""
    n = len(COLLIDER_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.collider_menu_sel = (self.collider_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.collider_menu_sel = (self.collider_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.collider_menu = False
        self.collider_mode = False
        self._exit_collider_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = COLLIDER_PRESETS[self.collider_menu_sel]
        self.collider_preset_name = preset[2]
        self._collider_init(preset[2])
    return True




def _handle_collider_key(self, key: int) -> bool:
    """Handle keys during collider simulation."""
    if key in (27, ord('q')):
        self._exit_collider_mode()
        return True
    elif key == ord(' '):
        self.collider_running = not self.collider_running
    elif key == ord('+') or key == ord('='):
        self.collider_speed = min(10, self.collider_speed + 1)
    elif key == ord('-') or key == ord('_'):
        self.collider_speed = max(1, self.collider_speed - 1)
    elif key == ord('r'):
        self._collider_init(self.collider_preset_name)
    elif key == ord('R'):
        self.collider_running = False
        self.collider_menu = True
        self.collider_menu_sel = 0
    elif key == ord('i') or key == ord('I'):
        self.collider_show_info = not self.collider_show_info
    elif key == ord('c') or key == ord('C'):
        # Force a collision at a random interaction point
        import random as rng
        import math
        cp = rng.choice(self.collider_collision_points)
        collision_x = self.collider_ring_cx + math.cos(cp["angle"]) * self.collider_ring_rx
        collision_y = self.collider_ring_cy + math.sin(cp["angle"]) * self.collider_ring_ry
        cp["flash"] = 1.0
        self.collider_total_collisions += 1
        self._collider_spawn_shower(collision_x, collision_y,
                                    self.collider_energy, self.collider_preset_name)
    return True




def _draw_collider_menu(self, max_y: int, max_x: int):
    """Draw the collider preset selection menu."""
    self.stdscr.erase()
    title = "⚛  Particle Collider / Hadron Collider  ⚛"
    subtitle = "CERN-inspired particle accelerator with collisions and decay showers"
    if max_x > len(title) + 2:
        try:
            self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                               curses.A_BOLD | curses.color_pair(6))
        except curses.error:
            pass
    if max_x > len(subtitle) + 2:
        try:
            self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(7))
        except curses.error:
            pass

    # Draw ASCII accelerator art
    art = [
        "        ╭──────────────╮",
        "   ╭────╯  ⚛  ⊕  ⊗    ╰────╮",
        "   │    →→→→→→→→→→→→→→→    │",
        "   │    ←←←←←←←←←←←←←←←    │",
        "   ╰────╮    ★  ✦  ⚡  ╭────╯",
        "        ╰──────────────╯",
    ]
    art_y = 4
    for i, line in enumerate(art):
        if art_y + i < max_y - 10 and len(line) + 2 < max_x:
            try:
                self.stdscr.addstr(art_y + i, max(0, (max_x - len(line)) // 2), line,
                                   curses.color_pair(4))
            except curses.error:
                pass

    y_start = art_y + len(art) + 2
    for i, (name, desc, _) in enumerate(COLLIDER_PRESETS):
        if y_start + i * 2 >= max_y - 3:
            break
        marker = " ▸ " if i == self.collider_menu_sel else "   "
        attr = curses.A_BOLD | curses.color_pair(6) if i == self.collider_menu_sel else curses.color_pair(7)
        try:
            self.stdscr.addstr(y_start + i * 2, 4, f"{marker}{name}", attr)
            if len(desc) + 8 < max_x:
                self.stdscr.addstr(y_start + i * 2 + 1, 8, desc,
                                   curses.color_pair(8) if i != self.collider_menu_sel else curses.color_pair(7))
        except curses.error:
            pass

    hint_y = min(y_start + len(COLLIDER_PRESETS) * 2 + 2, max_y - 2)
    hint = "↑/↓ select   Enter start   q quit"
    try:
        self.stdscr.addstr(hint_y, max(0, (max_x - len(hint)) // 2), hint, curses.color_pair(8))
    except curses.error:
        pass




def _draw_collider(self, max_y: int, max_x: int):
    """Draw the full collider simulation."""
    import math
    self.stdscr.erase()
    rows = max_y
    cols = max_x

    cx = self.collider_ring_cx
    cy = self.collider_ring_cy
    rx = self.collider_ring_rx
    ry = self.collider_ring_ry
    t = self.collider_time

    # ── Draw the accelerator ring ──
    num_points = int(2 * math.pi * max(rx, ry) * 1.5)
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        x = int(cx + math.cos(angle) * rx)
        y = int(cy + math.sin(angle) * ry)
        if 0 <= y < rows - 1 and 0 <= x < cols - 1:
            # Choose ring character based on angle
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            if abs(cos_a) > abs(sin_a) * 1.5:
                ch = "─"
            elif abs(sin_a) > abs(cos_a) * 1.5:
                ch = "│"
            elif cos_a > 0 and sin_a < 0:
                ch = "╮"
            elif cos_a < 0 and sin_a < 0:
                ch = "╭"
            elif cos_a < 0 and sin_a > 0:
                ch = "╰"
            else:
                ch = "╯"

            # Pulsing energy along the ring
            pulse = math.sin(angle * 8 + t * 4) * 0.5 + 0.5
            color = curses.color_pair(4) if pulse > 0.5 else curses.color_pair(12)
            try:
                self.stdscr.addstr(y, x, ch, color | curses.A_DIM)
            except curses.error:
                pass

    # ── Draw interaction points / detectors ──
    for cp in self.collider_collision_points:
        dx = int(cx + math.cos(cp["angle"]) * rx)
        dy = int(cy + math.sin(cp["angle"]) * ry)

        if 0 <= dy < rows - 1 and 0 <= dx < cols - 1:
            if cp["flash"] > 0.3:
                # Collision flash
                flash_chars = "████"
                flash_color = curses.color_pair(7) | curses.A_BOLD
                for fi, fc in enumerate(flash_chars):
                    fx = dx - 2 + fi
                    if 0 <= fx < cols - 1:
                        try:
                            self.stdscr.addstr(dy, fx, fc, flash_color)
                        except curses.error:
                            pass
            else:
                try:
                    self.stdscr.addstr(dy, dx, "◆", curses.color_pair(6) | curses.A_BOLD)
                except curses.error:
                    pass

        # Detector label
        label = cp["label"]
        lx = int(cx + math.cos(cp["angle"]) * (rx + 4))
        ly = int(cy + math.sin(cp["angle"]) * (ry + 2))
        if 0 <= ly < rows - 1 and 0 <= lx < cols - len(label) - 1:
            label_color = curses.color_pair(6) | curses.A_BOLD if cp["flash"] > 0 else curses.color_pair(8)
            try:
                self.stdscr.addstr(ly, lx, label, label_color)
            except curses.error:
                pass

    # ── Draw beam particles ──
    for beam in self.collider_beams:
        bx = int(cx + math.cos(beam["angle"]) * rx)
        by = int(cy + math.sin(beam["angle"]) * ry)

        # Draw trail
        for ti, (tx, ty) in enumerate(beam["trail"]):
            itx, ity = int(tx), int(ty)
            if 0 <= ity < rows - 1 and 0 <= itx < cols - 1:
                brightness = (ti + 1) / len(beam["trail"]) if beam["trail"] else 1
                trail_char = "·" if brightness < 0.5 else "•"
                try:
                    self.stdscr.addstr(ity, itx, trail_char,
                                       curses.color_pair(beam["color"]) | curses.A_DIM)
                except curses.error:
                    pass

        # Draw beam particle
        if 0 <= by < rows - 1 and 0 <= bx < cols - 1:
            beam_char = "●" if beam["speed"] > 0 else "○"
            try:
                self.stdscr.addstr(by, bx, beam_char,
                                   curses.color_pair(beam["color"]) | curses.A_BOLD)
            except curses.error:
                pass

    # ── Draw collision trails / sparks ──
    for trail in self.collider_trails:
        tx, ty = int(trail["x"]), int(trail["y"])
        if 0 <= ty < rows - 1 and 0 <= tx < cols - 1:
            intensity = trail["life"] / 15.0
            attr = curses.A_BOLD if intensity > 0.5 else curses.A_DIM
            try:
                self.stdscr.addstr(ty, tx, trail["char"],
                                   curses.color_pair(trail["color"]) | attr)
            except curses.error:
                pass

    # ── Draw shower particles ──
    for shower in self.collider_showers:
        for p in shower["particles"]:
            px, py = int(p["x"]), int(p["y"])
            if 0 <= py < rows - 1 and 0 <= px < cols - 1:
                life_frac = p["life"] / p["max_life"]
                char = _COLLIDER_SHOWER_CHARS[p["char_idx"]]
                attr = curses.A_BOLD if life_frac > 0.5 else curses.A_DIM
                try:
                    self.stdscr.addstr(py, px, char,
                                       curses.color_pair(p["color"]) | attr)
                except curses.error:
                    pass


def register(App):
    """Register collider mode methods on the App class."""
    App._enter_collider_mode = _enter_collider_mode
    App._exit_collider_mode = _exit_collider_mode
    App._collider_init = _collider_init
    App._collider_spawn_shower = _collider_spawn_shower
    App._collider_step = _collider_step
    App._handle_collider_menu_key = _handle_collider_menu_key
    App._handle_collider_key = _handle_collider_key
    App._draw_collider_menu = _draw_collider_menu
    App._draw_collider = _draw_collider

