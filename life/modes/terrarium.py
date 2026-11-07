"""Terrarium — a persistent world that resumes where you left off and catches up on the time you were away.

A chronicle log records notable events (phase transitions, population records,
extinctions) with real-world timestamps.
"""

import datetime
import json
import os
import time

from life.analytics import PHASE_LABELS
from life.constants import SAVE_DIR

TERRARIUM_DIR = os.path.join(SAVE_DIR, "terrarium")
TERRARIUM_STATE_FILE = os.path.join(TERRARIUM_DIR, "state.json")
TERRARIUM_CHRONICLE_FILE = os.path.join(TERRARIUM_DIR, "chronicle.json")

# Maximum generations to fast-forward when away (cap to avoid huge delays)
MAX_CATCHUP_GENS = 50000
# How often to sample the simulation for events during fast-forward
CATCHUP_SAMPLE_INTERVAL = 50
# Maximum events listed in the welcome-back summary
MAX_SUMMARY_EVENTS = 200


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
    self._terrarium_chronicle_view = False  # chronicle viewer open over the summary
    self._terrarium_last_pt_gen = -1        # newest phase transition already chronicled


def _enter_terrarium_mode(self):
    """Start Terrarium mode: resume the saved world or create a new one."""
    self.terrarium_mode = True
    self.terrarium_session_start = time.time()
    self.terrarium_last_save = time.time()
    self.terrarium_catchup_summary = []
    self.terrarium_show_summary = False
    self.terrarium_summary_scroll = 0
    self.terrarium_away_gens = 0
    self._terrarium_chronicle_view = False
    self._terrarium_last_pt_gen = -1

    loaded = _terrarium_load_state(self)
    if loaded:
        self._flash("Terrarium resumed — press Enter to see what happened while you were away")
    else:
        self.terrarium_chronicle = []
        self.terrarium_peak_pop = self.grid.population
        self.terrarium_peak_pop_gen = self.grid.generation
        self.terrarium_total_sessions = 1
        self.terrarium_total_generations = 0
        self.terrarium_first_started = time.time()
        _terrarium_chronicle_add(self, "terrarium_created", "Terrarium created — a new world begins")
        self._flash("Terrarium created! Your simulation now persists between sessions")


def _exit_terrarium_mode(self):
    """Save the world and leave Terrarium mode."""
    if self.terrarium_mode:
        _terrarium_save_state(self)
        _terrarium_chronicle_add(self, "session_end", "Session ended")
        _terrarium_save_chronicle(self)
    self.terrarium_mode = False
    self.terrarium_show_summary = False


def _terrarium_quit(self):
    """Save the world and log the end of the session when the app quits."""
    _terrarium_save_state(self)
    _terrarium_chronicle_add(self, "session_end",
                             f"Session ended (gen {self.grid.generation}, pop {self.grid.population})")
    _terrarium_save_chronicle(self)


def _terrarium_chronicle_add(self, kind: str, detail: str):
    """Append a timestamped entry to the chronicle."""
    entry = {
        "timestamp": time.time(),
        "iso_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generation": self.grid.generation,
        "population": self.grid.population,
        "kind": kind,
        "detail": detail,
    }
    self.terrarium_chronicle.append(entry)
    if len(self.terrarium_chronicle) > 5000:
        self.terrarium_chronicle = self.terrarium_chronicle[-4000:]


def _terrarium_record_event(self):
    """Log population records, extinctions and phase transitions after a step."""
    if not self.terrarium_mode:
        return

    pop = self.grid.population
    gen = self.grid.generation

    if pop > self.terrarium_peak_pop:
        old_peak = self.terrarium_peak_pop
        self.terrarium_peak_pop = pop
        self.terrarium_peak_pop_gen = gen
        # Log only records more than 10% above the old peak.
        if old_peak > 0 and (pop - old_peak) / old_peak > 0.1:
            _terrarium_chronicle_add(self, "population_record",
                                     f"New population record: {pop} (was {old_peak})")

    if pop == 0:
        _terrarium_chronicle_add(self, "extinction",
                                 f"Extinction at generation {gen} — all cells dead")

    # Phase transitions come from the shared phase detector.
    if hasattr(self, 'phase_transition_log') and self.phase_transition_log:
        last_pt = self.phase_transition_log[-1]
        if last_pt.generation > self._terrarium_last_pt_gen:
            self._terrarium_last_pt_gen = last_pt.generation
            _terrarium_chronicle_add(self, f"phase_{last_pt.kind}",
                                     f"{last_pt.label} at gen {last_pt.generation}")

    now = time.time()
    if now - self.terrarium_last_save >= self.terrarium_save_interval:
        self.terrarium_last_save = now
        _terrarium_save_state(self)


def _terrarium_save_state(self):
    """Write the world and the chronicle to disk."""
    os.makedirs(TERRARIUM_DIR, exist_ok=True)

    mode_attr = self._snapshot_detect_mode()
    # The detected mode is terrarium itself when no other simulation is active.
    # Save None then, which means plain Game of Life.
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
        # Write to a temp file first so a crash cannot leave a half-written save.
        tmp_path = TERRARIUM_STATE_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, TERRARIUM_STATE_FILE)
    except OSError:
        pass

    _terrarium_save_chronicle(self)


def _terrarium_save_chronicle(self):
    """Write the chronicle to disk."""
    os.makedirs(TERRARIUM_DIR, exist_ok=True)
    try:
        tmp_path = TERRARIUM_CHRONICLE_FILE + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(self.terrarium_chronicle, f, indent=2)
        os.replace(tmp_path, TERRARIUM_CHRONICLE_FILE)
    except OSError:
        pass


def _terrarium_load_state(self) -> bool:
    """Load the saved world. Return True if a usable save was found."""
    if not os.path.isfile(TERRARIUM_STATE_FILE):
        return False

    try:
        with open(TERRARIUM_STATE_FILE) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    grid_data = state.get("grid") if isinstance(state, dict) else None
    if not isinstance(grid_data, dict) or not {"rows", "cols", "generation", "cells"} <= grid_data.keys():
        return False  # damaged save: start a fresh terrarium instead of crashing

    self.grid.load_dict(state["grid"])
    self.grid.hex_mode = state.get("hex_mode", False)
    self.grid.topology = state.get("topology", "torus")

    vp = state.get("viewport", {})
    self.view_r = vp.get("view_r", 0)
    self.view_c = vp.get("view_c", 0)
    self.cursor_r = vp.get("cursor_r", self.grid.rows // 2)
    self.cursor_c = vp.get("cursor_c", self.grid.cols // 2)
    self.zoom_level = vp.get("zoom_level", 1)

    from life.colors import COLORMAP_NAMES
    self.speed_idx = _clamp_speed_idx(state.get("speed_idx", 2))
    cmap = state.get("colormap", "viridis")
    if cmap in COLORMAP_NAMES:
        self.tc_colormap = cmap
        self.tc_colormap_idx = COLORMAP_NAMES.index(cmap)
    self.heatmap_mode = state.get("heatmap_mode", False)

    tmeta = state.get("terrarium", {})
    self.terrarium_peak_pop = tmeta.get("peak_pop", 0)
    self.terrarium_peak_pop_gen = tmeta.get("peak_pop_gen", 0)
    self.terrarium_total_sessions = tmeta.get("total_sessions", 0) + 1
    # The saved total already counts the grid's current generation, and the grid
    # keeps counting from it, so keep only the generations from earlier worlds.
    self.terrarium_total_generations = max(
        0, tmeta.get("total_generations", 0) - self.grid.generation)
    self.terrarium_first_started = tmeta.get("first_started", time.time())

    if os.path.isfile(TERRARIUM_CHRONICLE_FILE):
        try:
            with open(TERRARIUM_CHRONICLE_FILE) as f:
                self.terrarium_chronicle = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.terrarium_chronicle = []
    else:
        self.terrarium_chronicle = []

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

    # Analysis state from before the save no longer applies.
    self.pop_history.clear()
    self._record_pop()
    self._reset_cycle_detection()
    self.history.clear()
    self.timeline_pos = None
    self.running = False

    self.analytics.phase_detector.enabled = True
    self.analytics.phase_detector.reset()

    self.terrarium_show_summary = True
    self.terrarium_summary_scroll = 0

    return True


def _clamp_speed_idx(idx) -> int:
    """Return idx as a valid index into SPEEDS."""
    from life.constants import SPEEDS
    if not isinstance(idx, int):
        return 2
    return max(0, min(idx, len(SPEEDS) - 1))


def _terrarium_catchup(self, elapsed_seconds: float, state: dict):
    """Fast-forward the world through the time spent away and build the summary."""
    # Run as many generations as the saved speed setting would have run live.
    from life.constants import SPEEDS
    speed_idx = _clamp_speed_idx(state.get("speed_idx", 2))
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
    omitted = 0

    def note(text: str):
        # Keep the summary readable when a rule dies out again and again.
        nonlocal omitted
        if len(events) < MAX_SUMMARY_EVENTS:
            events.append(text)
        else:
            omitted += 1

    for i in range(target_gens):
        self.grid.step()

        pop = self.grid.population
        gen = self.grid.generation

        if pop > peak_pop:
            peak_pop = pop
            peak_gen = gen
        if pop < min_pop:
            min_pop = pop
            min_gen = gen

        if pop == 0:
            extinctions += 1
            note(f"  Extinction at gen {gen}")
            _terrarium_chronicle_add(self, "extinction",
                                     f"Extinction during catch-up at gen {gen}")
            # Re-seed so the world stays alive.
            import random
            for _ in range(max(20, self.grid.rows * self.grid.cols // 50)):
                r = random.randint(0, self.grid.rows - 1)
                c = random.randint(0, self.grid.cols - 1)
                self.grid.set_alive(r, c)
            note(f"  Life re-seeded at gen {gen}")
            _terrarium_chronicle_add(self, "reseed",
                                     f"Life re-seeded after extinction at gen {gen}")

        # Run analytics only at intervals to keep catch-up fast.
        if i > 0 and i % CATCHUP_SAMPLE_INTERVAL == 0:
            self.pop_history.append(pop)
            if len(self.pop_history) > 200:
                self.pop_history = self.pop_history[-200:]
            if self.analytics.phase_detector.enabled:
                self.analytics.update(self.grid, self.pop_history)
                new_transitions = self.analytics.phase_detector.drain_pending()
                for t in new_transitions:
                    self.phase_transition_log.append(t)
                    note(f"  {t.label} at gen {t.generation}")
                    _terrarium_chronicle_add(self, f"phase_{t.kind}",
                                             f"{t.label} at gen {t.generation} (during catch-up)")

    end_pop = self.grid.population
    end_gen = self.grid.generation

    if peak_pop > self.terrarium_peak_pop:
        self.terrarium_peak_pop = peak_pop
        self.terrarium_peak_pop_gen = peak_gen
        note(f"  New all-time population record: {peak_pop}")
        _terrarium_chronicle_add(self, "population_record",
                                 f"New all-time record: {peak_pop} at gen {peak_gen} (during catch-up)")

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
        if omitted:
            summary.append(f"  ... and {omitted:,} more")
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
    """Format seconds as a short duration such as "2h 5m"."""
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
    """Draw the welcome-back summary."""
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
    scroll = min(self.terrarium_summary_scroll, max(0, len(lines) - visible))
    self.terrarium_summary_scroll = scroll

    for i, line in enumerate(lines[scroll:scroll + visible]):
        y = 3 + i
        if y >= max_y - 2:
            break
        attr = curses.color_pair(6)
        if line.startswith("  "):
            if "extinction" in line.lower() or "Extinction" in line:
                attr = curses.color_pair(2)  # red
            elif "record" in line.lower():
                attr = curses.color_pair(3)  # green
            elif "phase" in line.lower() or any(label in line for label in PHASE_LABELS.values()):
                attr = curses.color_pair(5)  # cyan
        elif line.startswith("Away for") or line.startswith("Fast-forward"):
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    footer = "Enter=continue  ↑↓=scroll  c=chronicle"
    try:
        self.stdscr.addstr(max_y - 1, max(0, (max_x - len(footer)) // 2),
                           footer[:max_x - 2], curses.color_pair(7))
    except curses.error:
        pass

    self._tc_refresh()


def _draw_terrarium_chronicle_view(self, max_y: int, max_x: int):
    """Draw the chronicle viewer, newest entry first."""
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
        entries = list(reversed(chronicle))
        scroll = min(self.terrarium_summary_scroll, max(0, len(entries) - visible))
        self.terrarium_summary_scroll = scroll
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

    footer = "Esc/q=back  ↑↓=scroll"
    try:
        self.stdscr.addstr(max_y - 1, max(0, (max_x - len(footer)) // 2),
                           footer[:max_x - 2], curses.color_pair(7))
    except curses.error:
        pass

    self._tc_refresh()


def _draw_terrarium_indicator(self, max_y: int, max_x: int):
    """Draw the age, generation and population in the top-right corner."""
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
    """Handle keys in the summary and chronicle screens. Return True if consumed."""
    import curses
    if not self.terrarium_mode:
        return False

    if self.terrarium_show_summary:
        if key in (10, 13, curses.KEY_ENTER, 27):  # Enter or Esc
            if self._terrarium_chronicle_view:
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
            if self._terrarium_chronicle_view:
                self._terrarium_chronicle_view = False
            else:
                self._terrarium_chronicle_view = True
            self.terrarium_summary_scroll = 0
            return True
        if key == ord('q'):
            if self._terrarium_chronicle_view:
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
    """Record terrarium events after a simulation step."""
    _terrarium_record_event(self)


def _terrarium_delete(self):
    """Delete the saved world and reset the counters."""
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
    """Bind the Terrarium methods to App."""
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
