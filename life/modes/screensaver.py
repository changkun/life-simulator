"""Mode: screensaver — auto-cycling demo reel that showcases all simulation modes."""
import curses
import math
import random
import time

from life.registry import MODE_REGISTRY


# ── Screensaver presets ──
SCREENSAVER_PRESETS = [
    ("All Modes — Sequential", "Cycle through every mode in category order", "all_sequential"),
    ("All Modes — Shuffle", "Random order through all modes", "all_shuffle"),
    ("Favorites Only — Sequential", "Cycle through your favorited modes", "fav_sequential"),
    ("Favorites Only — Shuffle", "Shuffle through your favorited modes", "fav_shuffle"),
    ("Category: Classic CA", "Only Classic CA modes", "cat_Classic CA"),
    ("Category: Particle & Swarm", "Only Particle & Swarm modes", "cat_Particle & Swarm"),
    ("Category: Physics & Waves", "Only Physics & Waves modes", "cat_Physics & Waves"),
    ("Category: Fluid Dynamics", "Only Fluid Dynamics modes", "cat_Fluid Dynamics"),
    ("Category: Chemical & Biological", "Only Chemical & Biological modes", "cat_Chemical & Biological"),
    ("Category: Fractals & Chaos", "Only Fractals & Chaos modes", "cat_Fractals & Chaos"),
    ("Category: Audio & Visual", "Only Audio & Visual modes", "cat_Audio & Visual"),
    ("Category: Complex Simulations", "Only Complex Simulations modes", "cat_Complex Simulations"),
]


def _enter_screensaver_mode(self):
    """Enter Screensaver / Demo Reel mode — show preset menu."""
    self.screensaver_menu = True
    self.screensaver_menu_sel = 0


def _exit_screensaver_mode(self):
    """Exit Screensaver mode — clean up and exit any active sub-mode."""
    # Exit whatever mode is currently running
    if self.screensaver_active_mode is not None:
        self._exit_current_modes()
    self.screensaver_mode = False
    self.screensaver_menu = False
    self.screensaver_running = False
    self.screensaver_playlist = []
    self.screensaver_active_mode = None
    self.screensaver_transition_buf = []


def _screensaver_build_playlist(self):
    """Build the playlist of mode entries based on preset."""
    preset = self.screensaver_preset_name
    favorites = set()
    try:
        from life.dashboard import _load_favorites
        favorites = _load_favorites()
    except Exception:
        pass

    # Filter modes — skip Game of Life (no enter fn) and the screensaver itself
    all_modes = [m for m in MODE_REGISTRY if m["enter"] is not None and m["attr"] != "screensaver_mode"]

    if preset == "all_sequential":
        playlist = list(all_modes)
    elif preset == "all_shuffle":
        playlist = list(all_modes)
        random.shuffle(playlist)
    elif preset == "fav_sequential":
        playlist = [m for m in all_modes if m["name"] in favorites]
    elif preset == "fav_shuffle":
        playlist = [m for m in all_modes if m["name"] in favorites]
        random.shuffle(playlist)
    elif preset.startswith("cat_"):
        cat = preset[4:]
        playlist = [m for m in all_modes if m["category"] == cat]
    else:
        playlist = list(all_modes)

    if not playlist:
        # Fallback to all modes if filter produced empty list
        playlist = list(all_modes)
        random.shuffle(playlist)

    return playlist


def _screensaver_init(self, preset: str):
    """Initialize screensaver from a preset key."""
    self.screensaver_preset_name = preset
    self.screensaver_menu = False
    self.screensaver_mode = True
    self.screensaver_running = True
    self.screensaver_generation = 0
    self.screensaver_time = 0.0
    self.screensaver_playlist = _screensaver_build_playlist(self)
    self.screensaver_playlist_idx = 0
    self.screensaver_mode_start_time = time.monotonic()
    self.screensaver_active_mode = None
    self.screensaver_transition_phase = 0.0  # 0 = not transitioning
    self.screensaver_transition_buf = []
    self.screensaver_overlay_alpha = 1.0  # overlay fade
    self.screensaver_paused = False

    # Launch first mode
    _screensaver_launch_current(self)


def _screensaver_launch_current(self):
    """Launch the current playlist entry."""
    if not self.screensaver_playlist:
        return

    idx = self.screensaver_playlist_idx % len(self.screensaver_playlist)
    entry = self.screensaver_playlist[idx]

    # Save screensaver state before _exit_current_modes (which clears all mode flags)
    ss_state = {
        "mode": self.screensaver_mode,
        "running": self.screensaver_running,
        "playlist": self.screensaver_playlist,
        "playlist_idx": self.screensaver_playlist_idx,
        "preset_name": self.screensaver_preset_name,
        "interval": self.screensaver_interval,
        "generation": self.screensaver_generation,
        "paused": self.screensaver_paused,
        "show_overlay": self.screensaver_show_overlay,
    }

    # Exit any current sub-mode
    self._exit_current_modes()

    # Restore screensaver state
    self.screensaver_mode = ss_state["mode"]
    self.screensaver_running = ss_state["running"]
    self.screensaver_playlist = ss_state["playlist"]
    self.screensaver_playlist_idx = ss_state["playlist_idx"]
    self.screensaver_preset_name = ss_state["preset_name"]
    self.screensaver_interval = ss_state["interval"]
    self.screensaver_generation = ss_state["generation"]
    self.screensaver_paused = ss_state["paused"]
    self.screensaver_show_overlay = ss_state["show_overlay"]

    # Enter the new mode
    enter_fn = getattr(self, entry["enter"], None)
    if enter_fn:
        enter_fn()

    # If mode opened a menu, try to auto-select first preset
    _screensaver_auto_select_preset(self, entry)

    self.screensaver_active_mode = entry
    self.screensaver_mode_start_time = time.monotonic()
    self.screensaver_transition_phase = 1.0  # start fade-in
    self.screensaver_overlay_alpha = 1.0


def _screensaver_auto_select_preset(self, entry):
    """Auto-select first preset for a mode's menu to skip manual selection."""
    attr_base = entry["attr"]
    if attr_base is None:
        return
    # Most modes use PREFIX_menu and have a _PREFIX_init method
    # The prefix is the attr without the _mode suffix
    prefix = attr_base.replace("_mode", "")

    menu_attr = f"{prefix}_menu"
    init_method = f"_{prefix}_init"

    # Check if we landed in a menu state
    if getattr(self, menu_attr, False):
        init_fn = getattr(self, init_method, None)
        if init_fn:
            # Try to call init with first preset
            # Different modes use different preset names — try common ones
            for preset_name in ["classic", "default", "gentle", "standard", "basic",
                                "normal", "simple", "small", "medium", "earth"]:
                try:
                    init_fn(preset_name)
                    setattr(self, menu_attr, False)
                    return
                except Exception:
                    continue
            # If none worked, try calling with index-based approaches
            # or just simulate pressing Enter on first item
            try:
                # Many modes have a PRESETS list — try to get first entry
                import importlib
                # Simulate pressing Enter (key 10) on the menu
                handler = getattr(self, f"_handle_{prefix}_menu_key", None)
                if handler:
                    handler(10)  # Enter key
                return
            except Exception:
                pass


def _screensaver_advance(self):
    """Advance to the next mode in the playlist."""
    self.screensaver_playlist_idx += 1
    if self.screensaver_playlist_idx >= len(self.screensaver_playlist):
        # Loop or reshuffle
        if "shuffle" in self.screensaver_preset_name:
            random.shuffle(self.screensaver_playlist)
        self.screensaver_playlist_idx = 0
    _screensaver_launch_current(self)


def _screensaver_step(self):
    """Advance the screensaver — handle timing and transitions."""
    now = time.monotonic()
    self.screensaver_generation += 1
    self.screensaver_time = now

    # Fade-in overlay (decreases from 1.0 to 0.0 over ~1 second)
    if self.screensaver_transition_phase > 0:
        self.screensaver_transition_phase = max(0, self.screensaver_transition_phase - 0.05)

    # Overlay text fades after a few seconds
    elapsed = now - self.screensaver_mode_start_time
    if elapsed < 3.0:
        self.screensaver_overlay_alpha = 1.0
    elif elapsed < 4.0:
        self.screensaver_overlay_alpha = max(0, 1.0 - (elapsed - 3.0))
    else:
        self.screensaver_overlay_alpha = 0.0

    # Step the active sub-mode
    if self.screensaver_active_mode and not self.screensaver_paused:
        _screensaver_step_submode(self)

    # Check if it's time to advance
    if not self.screensaver_paused and elapsed > self.screensaver_interval:
        _screensaver_advance(self)


def _screensaver_step_submode(self):
    """Step the currently active sub-mode's simulation."""
    entry = self.screensaver_active_mode
    if entry is None:
        return
    prefix = entry["attr"].replace("_mode", "")
    step_fn = getattr(self, f"_{prefix}_step", None)
    running_attr = f"{prefix}_running"

    if step_fn and getattr(self, running_attr, False):
        speed_attr = f"{prefix}_speed"
        speed = getattr(self, speed_attr, 1)
        steps_attr = f"{prefix}_steps_per_frame"
        steps = getattr(self, steps_attr, speed)
        try:
            for _ in range(max(1, steps)):
                step_fn()
        except Exception:
            pass  # Some modes may error on step — just skip


def _handle_screensaver_menu_key(self, key):
    """Handle keys in the screensaver preset selection menu."""
    if key == -1:
        return True

    n = len(SCREENSAVER_PRESETS)

    if key in (curses.KEY_DOWN, ord("j")):
        self.screensaver_menu_sel = (self.screensaver_menu_sel + 1) % n
        return True
    if key in (curses.KEY_UP, ord("k")):
        self.screensaver_menu_sel = (self.screensaver_menu_sel - 1) % n
        return True
    if key in (curses.KEY_PPAGE,):
        self.screensaver_menu_sel = max(0, self.screensaver_menu_sel - 5)
        return True
    if key in (curses.KEY_NPAGE,):
        self.screensaver_menu_sel = min(n - 1, self.screensaver_menu_sel + 5)
        return True

    # +/- to adjust interval
    if key == ord("+") or key == ord("="):
        self.screensaver_interval = min(120, self.screensaver_interval + 5)
        return True
    if key == ord("-") or key == ord("_"):
        self.screensaver_interval = max(5, self.screensaver_interval - 5)
        return True

    if key in (27, ord("q")):
        self.screensaver_menu = False
        self.screensaver_mode = False
        return True

    if key in (10, 13, curses.KEY_ENTER):
        preset_key = SCREENSAVER_PRESETS[self.screensaver_menu_sel][2]
        _screensaver_init(self, preset_key)
        return True

    return True


def _handle_screensaver_key(self, key):
    """Handle keys during screensaver playback."""
    if key == -1:
        return True

    # Escape / q = exit screensaver
    if key == 27 or key == ord("q"):
        _exit_screensaver_mode(self)
        self._dashboard_init()
        return True

    # Space = pause/resume cycling
    if key == ord(" "):
        self.screensaver_paused = not self.screensaver_paused
        return True

    # n / Right = skip to next mode
    if key == ord("n") or key == curses.KEY_RIGHT:
        _screensaver_advance(self)
        return True

    # p / Left = go to previous mode
    if key == ord("p") or key == curses.KEY_LEFT:
        self.screensaver_playlist_idx = max(0, self.screensaver_playlist_idx - 2)
        _screensaver_advance(self)
        return True

    # +/- adjust interval
    if key == ord("+") or key == ord("="):
        self.screensaver_interval = min(120, self.screensaver_interval + 5)
        return True
    if key == ord("-") or key == ord("_"):
        self.screensaver_interval = max(5, self.screensaver_interval - 5)
        return True

    # i = toggle info overlay
    if key == ord("i"):
        self.screensaver_show_overlay = not self.screensaver_show_overlay
        return True

    return True


def _draw_screensaver_menu(self, max_y, max_x):
    """Draw the screensaver preset selection menu."""
    self.stdscr.erase()
    n = len(SCREENSAVER_PRESETS)

    # Title
    title = "━━━ SCREENSAVER / DEMO REEL ━━━"
    if max_y > 1:
        try:
            self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                               curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass

    subtitle = "Auto-cycle through simulation modes with smooth transitions"
    if max_y > 2:
        try:
            self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass

    # Interval setting
    interval_text = f"Interval: {self.screensaver_interval}s per mode  (+/- to adjust)"
    if max_y > 4:
        try:
            self.stdscr.addstr(4, max(0, (max_x - len(interval_text)) // 2), interval_text,
                               curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass

    # Preset list
    menu_y = 6
    for i in range(n):
        if menu_y + i >= max_y - 2:
            break
        name, desc, _ = SCREENSAVER_PRESETS[i]
        selected = i == self.screensaver_menu_sel
        marker = "▸ " if selected else "  "
        attr = curses.color_pair(2) | curses.A_REVERSE | curses.A_BOLD if selected else curses.color_pair(6)
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(menu_y + i * 2, 4, line[:max_x - 6], attr)
        except curses.error:
            pass
        # Description on next line
        if menu_y + i * 2 + 1 < max_y - 2:
            desc_attr = curses.color_pair(7) | curses.A_DIM
            try:
                self.stdscr.addstr(menu_y + i * 2 + 1, 8, desc[:max_x - 10], desc_attr)
            except curses.error:
                pass

    # Footer
    footer = " ↑↓ Select │ Enter Launch │ +/- Interval │ Esc Back "
    if max_y > 1:
        try:
            self.stdscr.addstr(max_y - 1, 0, footer[:max_x - 1].ljust(max_x - 1),
                               curses.color_pair(6) | curses.A_REVERSE)
        except curses.error:
            pass


def _draw_screensaver_overlay(self, max_y, max_x):
    """Draw the mode name/category overlay on top of current mode content."""
    entry = self.screensaver_active_mode
    if entry is None:
        return

    # Info overlay (shown at bottom)
    if not self.screensaver_show_overlay and self.screensaver_overlay_alpha <= 0:
        # Still show minimal status bar
        _draw_screensaver_status_bar(self, max_y, max_x)
        return

    alpha = self.screensaver_overlay_alpha if not self.screensaver_show_overlay else 1.0
    if alpha <= 0:
        _draw_screensaver_status_bar(self, max_y, max_x)
        return

    attr_bright = curses.color_pair(2) | curses.A_BOLD
    attr_dim = curses.color_pair(7) | curses.A_DIM
    if alpha < 0.5:
        attr_bright = curses.color_pair(7) | curses.A_DIM
        attr_dim = curses.color_pair(7) | curses.A_DIM

    # Mode name — top-left overlay
    name = entry["name"]
    cat = entry["category"]
    idx = self.screensaver_playlist_idx % len(self.screensaver_playlist) + 1
    total = len(self.screensaver_playlist)

    # Box overlay at top-left
    box_w = max(len(name), len(cat), 20) + 6
    box_h = 4
    bx, by = 2, 1

    if by + box_h < max_y and bx + box_w < max_x:
        try:
            # Semi-transparent box
            top_border = "┌" + "─" * (box_w - 2) + "┐"
            self.stdscr.addstr(by, bx, top_border[:max_x - bx - 1], attr_dim)
            name_line = f"│ {name}".ljust(box_w - 1) + "│"
            self.stdscr.addstr(by + 1, bx, name_line[:max_x - bx - 1], attr_bright)
            cat_line = f"│ {cat}  [{idx}/{total}]".ljust(box_w - 1) + "│"
            self.stdscr.addstr(by + 2, bx, cat_line[:max_x - bx - 1], attr_dim)
            bot_border = "└" + "─" * (box_w - 2) + "┘"
            self.stdscr.addstr(by + 3, bx, bot_border[:max_x - bx - 1], attr_dim)
        except curses.error:
            pass

    _draw_screensaver_status_bar(self, max_y, max_x)


def _draw_screensaver_status_bar(self, max_y, max_x):
    """Draw the thin status bar at the very bottom."""
    entry = self.screensaver_active_mode
    if entry is None:
        return

    now = time.monotonic()
    elapsed = now - self.screensaver_mode_start_time
    remaining = max(0, self.screensaver_interval - elapsed)

    idx = self.screensaver_playlist_idx % len(self.screensaver_playlist) + 1
    total = len(self.screensaver_playlist)
    name = entry["name"]
    paused_str = " ⏸ PAUSED" if self.screensaver_paused else ""

    bar = f" ▶ {name} │ {idx}/{total} │ Next: {int(remaining)}s │ {self.screensaver_interval}s/mode{paused_str} │ n/p Skip │ Space Pause │ i Info │ Esc Exit "

    if max_y > 0:
        try:
            self.stdscr.addstr(max_y - 1, 0, bar[:max_x - 1].ljust(max_x - 1),
                               curses.color_pair(6) | curses.A_REVERSE)
        except curses.error:
            pass


def _draw_screensaver_transition(self, max_y, max_x):
    """Draw fade-in transition effect."""
    if self.screensaver_transition_phase <= 0:
        return

    # Simple dissolve: draw random block characters over the screen
    density = self.screensaver_transition_phase
    chars = "░▒▓█"
    n_cells = int(max_y * max_x * density * 0.3)

    for _ in range(n_cells):
        r = random.randint(0, max_y - 2)
        c = random.randint(0, max_x - 2)
        ci = min(3, int(density * 4))
        try:
            self.stdscr.addstr(r, c, chars[ci], curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass


def _draw_screensaver(self, max_y, max_x):
    """Draw the screensaver — delegates to the active sub-mode then overlays."""
    # The sub-mode's own draw function gets called by the normal draw dispatch.
    # We just add our overlay and transition effects on top.
    # This function is called AFTER the sub-mode has drawn itself.

    # Draw transition dissolve effect
    _draw_screensaver_transition(self, max_y, max_x)

    # Draw mode name/category overlay
    _draw_screensaver_overlay(self, max_y, max_x)


def register(App):
    """Register screensaver mode methods on the App class."""
    App._enter_screensaver_mode = _enter_screensaver_mode
    App._exit_screensaver_mode = _exit_screensaver_mode
    App._screensaver_init = _screensaver_init
    App._screensaver_step = _screensaver_step
    App._screensaver_build_playlist = _screensaver_build_playlist
    App._screensaver_launch_current = _screensaver_launch_current
    App._screensaver_advance = _screensaver_advance
    App._screensaver_auto_select_preset = _screensaver_auto_select_preset
    App._screensaver_step_submode = _screensaver_step_submode
    App._handle_screensaver_menu_key = _handle_screensaver_menu_key
    App._handle_screensaver_key = _handle_screensaver_key
    App._draw_screensaver_menu = _draw_screensaver_menu
    App._draw_screensaver = _draw_screensaver
    App._draw_screensaver_overlay = _draw_screensaver_overlay
    App._draw_screensaver_status_bar = _draw_screensaver_status_bar
    App._draw_screensaver_transition = _draw_screensaver_transition
