"""Persistent Terrarium Mode — a long-running simulation that lives between sessions.

Saves state automatically on exit, resumes where it left off on next launch.
Optionally fast-forwards through elapsed generations while "away," and maintains
a chronicle log of notable events (phase transitions, population records,
extinction events) with real-world timestamps.
"""

import datetime
import json
import os
import time

from life.constants import SAVE_DIR

TERRARIUM_DIR = os.path.join(SAVE_DIR, "terrarium")
TERRARIUM_STATE_FILE = os.path.join(TERRARIUM_DIR, "state.json")
TERRARIUM_CHRONICLE_FILE = os.path.join(TERRARIUM_DIR, "chronicle.json")

# How many generations per real-world second during fast-forward catch-up
CATCHUP_GENS_PER_SEC = 10.0
# Maximum generations to fast-forward when away (cap to avoid huge delays)
MAX_CATCHUP_GENS = 50000
# How often to sample the simulation for events during fast-forward
CATCHUP_SAMPLE_INTERVAL = 50


def _terrarium_init(self):
    """Initialize terrarium mode state."""
    self.terrarium_mode = False
    self.terrarium_chronicle: list[dict] = []
    self.terrarium_session_start = 0.0
    self.terrarium_last_save = 0.0
    self.terrarium_save_interval = 60.0  # auto-save every 60s
    self.terrarium_peak_pop = 0
    self.terrarium_peak_pop_gen = 0
    self.terrarium_total_sessions = 0
    self.terrarium_total_generations = 0
    self.terrarium_first_started = 0.0
    self.terrarium_catchup_summary: list[str] = []
    self.terrarium_show_summary = False
    self.terrarium_summary_scroll = 0
    self.terrarium_away_gens = 0


def _enter_terrarium_mode(self):
    """Activate terrarium mode — load saved state or start fresh."""
    self.terrarium_mode = True
    self.terrarium_session_start = time.time()
    self.terrarium_last_save = time.time()
    self.terrarium_catchup_summary = []
    self.terrarium_show_summary = False
    self.terrarium_summary_scroll = 0
    self.terrarium_away_gens = 0

    loaded = _terrarium_load_state(self)
    if loaded:
        self._flash("Terrarium resumed — press Enter to see what happened while you were away")
    else:
        # Fresh terrarium
        self.terrarium_chronicle = []
        self.terrarium_peak_pop = self.grid.population
        self.terrarium_peak_pop_gen = self.grid.generation
        self.terrarium_total_sessions = 1
        self.terrarium_total_generations = 0
        self.terrarium_first_started = time.time()
        _terrarium_chronicle_add(self, "terrarium_created", "Terrarium created — a new world begins")
        self._flash("Terrarium created! Your simulation now persists between sessions")


def _exit_terrarium_mode(self):
    """Deactivate terrarium mode — save state before leaving."""
    if self.terrarium_mode:
        _terrarium_save_state(self)
        _terrarium_chronicle_add(self, "session_end", "Session ended")
        _terrarium_save_chronicle(self)
    self.terrarium_mode = False
    self.terrarium_show_summary = False


def _terrarium_quit(self):
    """Called when user presses 'q' while in terrarium mode — save and exit."""
    _terrarium_save_state(self)
    _terrarium_chronicle_add(self, "session_end",
                             f"Session ended (gen {self.grid.generation}, pop {self.grid.population})")
    _terrarium_save_chronicle(self)


def _terrarium_chronicle_add(self, kind: str, detail: str):
    """Add an entry to the terrarium chronicle with a real-world timestamp."""
    entry = {
        "timestamp": time.time(),
        "iso_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generation": self.grid.generation,
        "population": self.grid.population,
        "kind": kind,
        "detail": detail,
    }
    self.terrarium_chronicle.append(entry)
    # Keep chronicle bounded
    if len(self.terrarium_chronicle) > 5000:
        self.terrarium_chronicle = self.terrarium_chronicle[-4000:]


def _terrarium_record_event(self):
    """Hook into the simulation step to record notable events for the chronicle."""
    if not self.terrarium_mode:
        return

    pop = self.grid.population
    gen = self.grid.generation

    # Track population records
    if pop > self.terrarium_peak_pop:
        old_peak = self.terrarium_peak_pop
        self.terrarium_peak_pop = pop
        self.terrarium_peak_pop_gen = gen
        # Only log significant new records (>10% increase)
        if old_peak > 0 and (pop - old_peak) / old_peak > 0.1:
            _terrarium_chronicle_add(self, "population_record",
                                     f"New population record: {pop} (was {old_peak})")

    # Extinction
    if pop == 0:
        _terrarium_chronicle_add(self, "extinction",
                                 f"Extinction at generation {gen} — all cells dead")

    # Phase transitions (piggyback on existing detector)
    if hasattr(self, 'phase_transition_log') and self.phase_transition_log:
        last_pt = self.phase_transition_log[-1]
        # Check if this is a new transition we haven't chronicled
        if not hasattr(self, '_terrarium_last_pt_gen'):
            self._terrarium_last_pt_gen = -1
        if last_pt.generation > self._terrarium_last_pt_gen:
            self._terrarium_last_pt_gen = last_pt.generation
            _terrarium_chronicle_add(self, f"phase_{last_pt.kind}",
                                     f"{last_pt.label} at gen {last_pt.generation}")

    # Periodic auto-save
    now = time.time()
    if now - self.terrarium_last_save >= self.terrarium_save_interval:
        self.terrarium_last_save = now
        _terrarium_save_state(self)


def _terrarium_save_state(self):
    """Save the complete terrarium state to disk."""
    os.makedirs(TERRARIUM_DIR, exist_ok=True)

    mode_attr = self._snapshot_detect_mode()
    # If we're in terrarium but the detected mode is terrarium itself,
    # save the underlying simulation (base Game of Life)
    underlying_mode = mode_attr if mode_attr != "terrarium_mode" else None

    state = {
        "version": 1,
        "save_time": time.time(),
        "save_iso": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "grid": self.grid.to_dict(),
        "hex_mode": self.grid.hex_mode,
        "topology": self.grid.topology,
        "underlying_mode": underlying_mode,
        "viewport": {
            "view_r": self.view_r,
            "view_c": self.view_c,
            "cursor_r": self.cursor_r,
            "cursor_c": self.cursor_c,
            "zoom_level": self.zoom_level,
        },
        "speed_idx": self.speed_idx,
        "colormap": self.tc_colormap,
        "colormap_idx": self.tc_colormap_idx,
        "heatmap_mode": self.heatmap_mode,
        "running": self.running,
        "mode_params": self._snapshot_collect_mode_params(underlying_mode),
        # Terrarium-specific metadata
        "terrarium": {
            "peak_pop": self.terrarium_peak_pop,
            "peak_pop_gen": self.terrarium_peak_pop_gen,
            "total_sessions": self.terrarium_total_sessions,
            "total_generations": self.terrarium_total_generations + self.grid.generation,
            "first_started": self.terrarium_first_started,
            "session_start": self.terrarium_session_start,
        },
    }

    try:
        # Write atomically via temp file
        tmp_path = TERRARIUM_STATE_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, TERRARIUM_STATE_FILE)
    except OSError:
        pass

    _terrarium_save_chronicle(self)


def _terrarium_save_chronicle(self):
    """Persist the chronicle log to disk."""
    os.makedirs(TERRARIUM_DIR, exist_ok=True)
    try:
        tmp_path = TERRARIUM_CHRONICLE_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(self.terrarium_chronicle, f, indent=2)
        os.replace(tmp_path, TERRARIUM_CHRONICLE_FILE)
    except OSError:
        pass


def _terrarium_load_state(self) -> bool:
    """Load terrarium state from disk. Returns True if a save was found and loaded."""
    if not os.path.isfile(TERRARIUM_STATE_FILE):
        return False

    try:
        with open(TERRARIUM_STATE_FILE) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    # Restore grid
    self.grid.load_dict(state["grid"])
    self.grid.hex_mode = state.get("hex_mode", False)
    self.grid.topology = state.get("topology", "torus")

    # Restore viewport
    vp = state.get("viewport", {})
    self.view_r = vp.get("view_r", 0)
    self.view_c = vp.get("view_c", 0)
    self.cursor_r = vp.get("cursor_r", self.grid.rows // 2)
    self.cursor_c = vp.get("cursor_c", self.grid.cols // 2)
    self.zoom_level = vp.get("zoom_level", 1)

    # Restore display
    from life.colors import COLORMAP_NAMES
    self.speed_idx = state.get("speed_idx", 2)
    cmap = state.get("colormap", "viridis")
    if cmap in COLORMAP_NAMES:
        self.tc_colormap = cmap
        self.tc_colormap_idx = COLORMAP_NAMES.index(cmap)
    self.heatmap_mode = state.get("heatmap_mode", False)

    # Restore terrarium metadata
    tmeta = state.get("terrarium", {})
    self.terrarium_peak_pop = tmeta.get("peak_pop", 0)
    self.terrarium_peak_pop_gen = tmeta.get("peak_pop_gen", 0)
    self.terrarium_total_sessions = tmeta.get("total_sessions", 0) + 1
    self.terrarium_total_generations = tmeta.get("total_generations", 0)
    self.terrarium_first_started = tmeta.get("first_started", time.time())

    # Load chronicle
    if os.path.isfile(TERRARIUM_CHRONICLE_FILE):
        try:
            with open(TERRARIUM_CHRONICLE_FILE) as f:
                self.terrarium_chronicle = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.terrarium_chronicle = []
    else:
        self.terrarium_chronicle = []

    # Calculate time away and fast-forward
    save_time = state.get("save_time", time.time())
    elapsed_seconds = time.time() - save_time
    if elapsed_seconds > 5:
        _terrarium_catchup(self, elapsed_seconds, state)
    else:
        self.terrarium_catchup_summary = ["You were only away for a moment."]
        self.terrarium_away_gens = 0

    _terrarium_chronicle_add(self, "session_start",
                             f"Session #{self.terrarium_total_sessions} started "
                             f"(away for {_format_duration(elapsed_seconds)})")

    # Reset tracking
    self.pop_history.clear()
    self._record_pop()
    self._reset_cycle_detection()
    self.history.clear()
    self.timeline_pos = None
    self.running = False
    self._terrarium_last_pt_gen = -1

    # Enable phase detector for chronicle logging
    self.analytics.phase_detector.enabled = True
    self.analytics.phase_detector.reset()

    # Show welcome-back summary
    self.terrarium_show_summary = True
    self.terrarium_summary_scroll = 0

    return True


def _terrarium_catchup(self, elapsed_seconds: float, state: dict):
    """Fast-forward the simulation through elapsed real time."""
    # Calculate generations to simulate based on the speed setting
    from life.constants import SPEEDS
    speed_idx = state.get("speed_idx", 2)
    gens_per_sec = 1.0 / max(SPEEDS[speed_idx], 0.01)
    target_gens = int(elapsed_seconds * gens_per_sec)
    target_gens = min(target_gens, MAX_CATCHUP_GENS)

    if target_gens <= 0:
        self.terrarium_catchup_summary = [f"Away for {_format_duration(elapsed_seconds)}, no catch-up needed."]
        self.terrarium_away_gens = 0
        return

    summary = []
    summary.append(f"Away for {_format_duration(elapsed_seconds)}")
    summary.append(f"Fast-forwarding {target_gens:,} generations...")
    summary.append("")

    start_pop = self.grid.population
    start_gen = self.grid.generation
    peak_pop = start_pop
    peak_gen = start_gen
    min_pop = start_pop
    min_gen = start_gen
    extinctions = 0
    events: list[str] = []

    for i in range(target_gens):
        self.grid.step()

        pop = self.grid.population
        gen = self.grid.generation

        # Track extremes
        if pop > peak_pop:
            peak_pop = pop
            peak_gen = gen
        if pop < min_pop:
            min_pop = pop
            min_gen = gen

        # Detect extinction during catch-up
        if pop == 0:
            extinctions += 1
            events.append(f"  Extinction at gen {gen}")
            _terrarium_chronicle_add(self, "extinction",
                                     f"Extinction during catch-up at gen {gen}")
            # Re-seed with random cells to keep the terrarium alive
            import random
            for _ in range(max(20, self.grid.rows * self.grid.cols // 50)):
                r = random.randint(0, self.grid.rows - 1)
                c = random.randint(0, self.grid.cols - 1)
                self.grid.set_alive(r, c)
            events.append(f"  Life re-seeded at gen {gen}")
            _terrarium_chronicle_add(self, "reseed",
                                     f"Life re-seeded after extinction at gen {gen}")

        # Sample analytics periodically during catch-up
        if i > 0 and i % CATCHUP_SAMPLE_INTERVAL == 0:
            # Update analytics for phase detection
            self.pop_history.append(pop)
            if len(self.pop_history) > 200:
                self.pop_history = self.pop_history[-200:]
            if self.analytics.phase_detector.enabled:
                self.analytics.update(self.grid, self.pop_history)
                new_transitions = self.analytics.phase_detector.drain_pending()
                for t in new_transitions:
                    self.phase_transition_log.append(t)
                    events.append(f"  {t.label} at gen {t.generation}")
                    _terrarium_chronicle_add(self, f"phase_{t.kind}",
                                             f"{t.label} at gen {t.generation} (during catch-up)")

    end_pop = self.grid.population
    end_gen = self.grid.generation

    # Update peak tracking
    if peak_pop > self.terrarium_peak_pop:
        self.terrarium_peak_pop = peak_pop
        self.terrarium_peak_pop_gen = peak_gen
        events.append(f"  New all-time population record: {peak_pop}")
        _terrarium_chronicle_add(self, "population_record",
                                 f"New all-time record: {peak_pop} at gen {peak_gen} (during catch-up)")

    # Build summary
    summary.append(f"Generations simulated: {start_gen} -> {end_gen} (+{target_gens:,})")
    summary.append(f"Population: {start_pop} -> {end_pop}")
    summary.append(f"Peak population: {peak_pop:,} (gen {peak_gen})")
    summary.append(f"Minimum population: {min_pop:,} (gen {min_gen})")
    if extinctions:
        summary.append(f"Extinctions: {extinctions} (life was re-seeded each time)")
    summary.append("")

    if events:
        summary.append("Notable events while you were away:")
        summary.extend(events)
    else:
        summary.append("Nothing particularly dramatic happened while you were away.")

    summary.append("")
    summary.append(f"All-time peak population: {self.terrarium_peak_pop:,} (gen {self.terrarium_peak_pop_gen})")
    summary.append(f"Total sessions: {self.terrarium_total_sessions}")
    total_gens = self.terrarium_total_generations + end_gen
    summary.append(f"Total generations across all sessions: {total_gens:,}")
    age = time.time() - self.terrarium_first_started
    summary.append(f"Terrarium age: {_format_duration(age)}")

    self.terrarium_catchup_summary = summary
    self.terrarium_away_gens = target_gens


def _format_duration(seconds: float) -> str:
    """Format a duration in seconds into a human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}m {s}s"
    elif seconds < 86400:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"
    else:
        d = int(seconds // 86400)
        h = int((seconds % 86400) // 3600)
        return f"{d}d {h}h"


def _draw_terrarium_summary(self, max_y: int, max_x: int):
    """Draw the welcome-back summary screen."""
    import curses
    self.stdscr.erase()
    self.tc_buf.clear()

    title = "── Welcome Back to Your Terrarium ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    lines = self.terrarium_catchup_summary
    visible = max_y - 5
    scroll = self.terrarium_summary_scroll

    for i, line in enumerate(lines[scroll:scroll + visible]):
        y = 3 + i
        if y >= max_y - 2:
            break
        attr = curses.color_pair(6)
        if line.startswith("  "):
            # Event lines — highlight
            if "extinction" in line.lower() or "Extinction" in line:
                attr = curses.color_pair(2)  # red
            elif "record" in line.lower():
                attr = curses.color_pair(3)  # green
            elif "phase" in line.lower() or "⚡" in line or "∿" in line:
                attr = curses.color_pair(5)  # cyan
        elif line.startswith("Away for") or line.startswith("Fast-forward"):
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    # Footer
    footer = "Press Enter to continue  |  ↑/↓ scroll  |  c = view chronicle"
    try:
        self.stdscr.addstr(max_y - 1, max(0, (max_x - len(footer)) // 2),
                           footer[:max_x - 2], curses.color_pair(7))
    except curses.error:
        pass

    self._tc_refresh()


def _draw_terrarium_chronicle_view(self, max_y: int, max_x: int):
    """Draw the chronicle log viewer."""
    import curses
    self.stdscr.erase()
    self.tc_buf.clear()

    title = "── Terrarium Chronicle ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    chronicle = self.terrarium_chronicle
    if not chronicle:
        try:
            self.stdscr.addstr(3, 2, "No chronicle entries yet.", curses.color_pair(6))
        except curses.error:
            pass
    else:
        visible = max_y - 5
        scroll = self.terrarium_summary_scroll
        # Show newest first
        entries = list(reversed(chronicle))
        for i, entry in enumerate(entries[scroll:scroll + visible]):
            y = 3 + i
            if y >= max_y - 2:
                break
            ts = entry.get("iso_time", "?")
            gen = entry.get("generation", "?")
            detail = entry.get("detail", "")
            kind = entry.get("kind", "")
            line = f"[{ts}] gen {gen}: {detail}"
            attr = curses.color_pair(6)
            if "extinction" in kind:
                attr = curses.color_pair(2)
            elif "record" in kind or "created" in kind:
                attr = curses.color_pair(3)
            elif "phase" in kind:
                attr = curses.color_pair(5)
            elif "session" in kind:
                attr = curses.color_pair(7)
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            except curses.error:
                pass

        total_label = f" {min(scroll + visible, len(entries))}/{len(entries)} entries "
        try:
            self.stdscr.addstr(max_y - 2, max(0, (max_x - len(total_label)) // 2),
                               total_label, curses.color_pair(7))
        except curses.error:
            pass

    footer = "Press Esc/q to return  |  ↑/↓ scroll"
    try:
        self.stdscr.addstr(max_y - 1, max(0, (max_x - len(footer)) // 2),
                           footer[:max_x - 2], curses.color_pair(7))
    except curses.error:
        pass

    self._tc_refresh()


def _draw_terrarium_indicator(self, max_y: int, max_x: int):
    """Draw a small terrarium status indicator in the corner."""
    import curses
    age = time.time() - self.terrarium_first_started
    age_str = _format_duration(age)
    gen = self.grid.generation
    pop = self.grid.population
    label = f" TERRARIUM age:{age_str} gen:{gen} pop:{pop} "
    x = max(0, max_x - len(label) - 1)
    try:
        self.stdscr.addstr(0, x, label, curses.color_pair(3) | curses.A_BOLD)
    except curses.error:
        pass


def _handle_terrarium_summary_key(self, key: int) -> bool:
    """Handle keys in the terrarium summary/chronicle screens. Returns True if handled."""
    import curses
    if not self.terrarium_mode:
        return False

    if self.terrarium_show_summary:
        if key in (10, 13, curses.KEY_ENTER, 27):  # Enter or Esc
            if hasattr(self, '_terrarium_chronicle_view') and self._terrarium_chronicle_view:
                # Return from chronicle to summary
                self._terrarium_chronicle_view = False
                self.terrarium_summary_scroll = 0
                return True
            # Dismiss summary
            self.terrarium_show_summary = False
            self.running = True
            self._flash("Terrarium running — press q to save & exit")
            return True
        if key == ord('c'):
            # Toggle chronicle view
            if hasattr(self, '_terrarium_chronicle_view') and self._terrarium_chronicle_view:
                self._terrarium_chronicle_view = False
            else:
                self._terrarium_chronicle_view = True
            self.terrarium_summary_scroll = 0
            return True
        if key == ord('q'):
            if hasattr(self, '_terrarium_chronicle_view') and self._terrarium_chronicle_view:
                self._terrarium_chronicle_view = False
                self.terrarium_summary_scroll = 0
                return True
        if key in (curses.KEY_UP, ord('k')):
            self.terrarium_summary_scroll = max(0, self.terrarium_summary_scroll - 1)
            return True
        if key in (curses.KEY_DOWN, ord('j')):
            self.terrarium_summary_scroll += 1
            return True
        return True  # Consume all keys while summary is showing

    return False


def _terrarium_step(self):
    """Called each simulation step to record terrarium events."""
    _terrarium_record_event(self)


def _terrarium_delete(self):
    """Delete all terrarium save data (called from menu)."""
    import shutil
    if os.path.isdir(TERRARIUM_DIR):
        shutil.rmtree(TERRARIUM_DIR, ignore_errors=True)
    self.terrarium_chronicle = []
    self.terrarium_peak_pop = 0
    self.terrarium_peak_pop_gen = 0
    self.terrarium_total_sessions = 0
    self.terrarium_total_generations = 0
    self.terrarium_first_started = time.time()


def register(App):
    """Register terrarium mode methods on the App class."""
    App._terrarium_init = _terrarium_init
    App._enter_terrarium_mode = _enter_terrarium_mode
    App._exit_terrarium_mode = _exit_terrarium_mode
    App._terrarium_quit = _terrarium_quit
    App._terrarium_chronicle_add = _terrarium_chronicle_add
    App._terrarium_record_event = _terrarium_record_event
    App._terrarium_save_state = _terrarium_save_state
    App._terrarium_save_chronicle = _terrarium_save_chronicle
    App._terrarium_load_state = _terrarium_load_state
    App._terrarium_catchup = _terrarium_catchup
    App._draw_terrarium_summary = _draw_terrarium_summary
    App._draw_terrarium_chronicle_view = _draw_terrarium_chronicle_view
    App._draw_terrarium_indicator = _draw_terrarium_indicator
    App._handle_terrarium_summary_key = _handle_terrarium_summary_key
    App._terrarium_step = _terrarium_step
    App._terrarium_delete = _terrarium_delete
