"""Universal Time-Travel History Scrubber for all simulation modes.

Records N frames of state for the active mode, enabling rewind, fast-forward,
and frame-by-frame stepping through any simulation's timeline.
"""
import copy
import curses

from life.registry import MODE_REGISTRY


# Mode attrs that are GoL overlays / meta-modes not suitable for time-travel
_TT_EXCLUDED_ATTRS = frozenset({
    "hex_mode", "compare_mode", "race_mode",
    "heatmap_mode", "pattern_search_mode", "blueprint_mode", "iso_mode",
    "screensaver_mode", "pexplorer_mode", "ep_mode",
    "puzzle_mode", "evo_mode", "mp_mode",
})

# Attribute suffixes to skip when snapshotting (UI state, not sim state)
_SKIP_SUFFIXES = frozenset({
    "_mode", "_menu", "_menu_sel", "_running",
})


def _tt_get_active_mode_prefix(self):
    """Return the prefix of the currently active non-GoL mode, or None."""
    for entry in MODE_REGISTRY:
        attr = entry.get("attr")
        if not attr or attr in _TT_EXCLUDED_ATTRS:
            continue
        if getattr(self, attr, False):
            return attr.rsplit("_mode", 1)[0]
    return None


def _tt_snapshot(self, prefix):
    """Capture a deep-copy snapshot of all simulation state for the given mode prefix."""
    snapshot = {}
    attr_prefix = prefix + "_"
    for attr_name in list(vars(self)):
        if not attr_name.startswith(attr_prefix):
            continue
        suffix = attr_name[len(prefix):]
        if suffix in _SKIP_SUFFIXES:
            continue
        val = getattr(self, attr_name)
        if callable(val):
            continue
        snapshot[attr_name] = copy.deepcopy(val)
    return snapshot


def _tt_restore(self, snapshot):
    """Restore mode state from a snapshot dict."""
    for key, val in snapshot.items():
        setattr(self, key, copy.deepcopy(val))


def _tt_push(self):
    """Push current state to the time-travel history buffer."""
    prefix = self._tt_get_active_mode_prefix()
    if prefix is None:
        return

    # If scrubbed back, truncate future history before pushing
    if self.tt_pos is not None:
        self.tt_history = self.tt_history[:self.tt_pos + 1]
        self.tt_pos = None

    snapshot = self._tt_snapshot(prefix)
    snapshot["_prefix"] = prefix
    self.tt_history.append(snapshot)

    if len(self.tt_history) > self.tt_max:
        self.tt_history = self.tt_history[-self.tt_max:]


def _tt_rewind(self):
    """Step back one frame in the time-travel history."""
    if not self.tt_history:
        self._flash("No history to rewind")
        return

    if self.tt_pos is None:
        self.tt_pos = len(self.tt_history) - 1
    else:
        if self.tt_pos <= 0:
            self._flash("At oldest recorded state")
            return
        self.tt_pos -= 1

    self._tt_restore(self.tt_history[self.tt_pos])
    hist_len = len(self.tt_history)
    self._flash(f"Frame {self.tt_pos + 1}/{hist_len}")


def _tt_scrub_back(self, steps=10):
    """Scrub backward through the timeline by N steps."""
    if not self.tt_history:
        self._flash("No history to scrub")
        return
    if self.tt_pos is None:
        self.tt_pos = max(0, len(self.tt_history) - 1 - steps)
    else:
        self.tt_pos = max(0, self.tt_pos - steps)
    self._tt_restore(self.tt_history[self.tt_pos])
    self._flash(f"Frame {self.tt_pos + 1}/{len(self.tt_history)}")


def _tt_scrub_forward(self, steps=10):
    """Scrub forward through the timeline by N steps."""
    if self.tt_pos is None:
        self._flash("Already at latest state")
        return
    self.tt_pos += steps
    if self.tt_pos >= len(self.tt_history):
        self.tt_pos = None
        if self.tt_history:
            self._tt_restore(self.tt_history[-1])
        self._flash("Latest state (press Space to continue)")
    else:
        self._tt_restore(self.tt_history[self.tt_pos])
        self._flash(f"Frame {self.tt_pos + 1}/{len(self.tt_history)}")


def _tt_step_forward(self):
    """Step forward one frame in the time-travel history."""
    if self.tt_pos is None:
        self._flash("Already at latest state")
        return
    self.tt_pos += 1
    if self.tt_pos >= len(self.tt_history):
        self.tt_pos = None
        if self.tt_history:
            self._tt_restore(self.tt_history[-1])
        self._flash("Latest state (press Space to continue)")
    else:
        self._tt_restore(self.tt_history[self.tt_pos])
        self._flash(f"Frame {self.tt_pos + 1}/{len(self.tt_history)}")


def _tt_pause_active_mode(self):
    """Pause the currently active mode's simulation."""
    prefix = self._tt_get_active_mode_prefix()
    if prefix is None:
        self.running = False
    else:
        running_attr = f"{prefix}_running"
        if hasattr(self, running_attr):
            setattr(self, running_attr, False)


def _tt_auto_record(self):
    """Auto-record state each frame if the active mode is running.

    Called at the start of each main-loop iteration.
    """
    prefix = self._tt_get_active_mode_prefix()
    if prefix is None:
        return  # GoL uses its own history system

    # Don't record while scrubbing
    if self.tt_pos is not None:
        return

    running_attr = f"{prefix}_running"
    if not getattr(self, running_attr, False):
        return

    # Check if generation advanced since last recording
    gen_attr = f"{prefix}_generation"
    current_gen = getattr(self, gen_attr, None)
    if current_gen is not None:
        if current_gen == self._tt_last_gen:
            return  # No change
        self._tt_last_gen = current_gen
    else:
        # Fallback: record every frame for modes without generation counter
        pass

    # Detect mode switch — clear history if prefix changed
    if self.tt_history and self.tt_history[-1].get("_prefix") != prefix:
        self.tt_history.clear()
        self.tt_pos = None
        self._tt_last_gen = -1

    self._tt_push()


def _tt_handle_key(self, key):
    """Handle universal time-travel keys. Returns True if handled."""
    prefix = self._tt_get_active_mode_prefix()
    if prefix is None:
        return False  # GoL uses its own history/timeline system

    if key == ord("u"):
        self._tt_pause_active_mode()
        self._tt_rewind()
        return True

    if key == ord("["):
        self._tt_pause_active_mode()
        self._tt_scrub_back(10)
        return True

    if key == ord("]"):
        self._tt_pause_active_mode()
        self._tt_scrub_forward(10)
        return True

    # When scrubbing, 'n' steps forward in history instead of sim
    if key == ord("n") and self.tt_pos is not None:
        self._tt_step_forward()
        return True

    # When scrubbing, Space resumes from current position
    if key == ord(" ") and self.tt_pos is not None:
        # Truncate future, resume from current
        self.tt_history = self.tt_history[:self.tt_pos + 1]
        self.tt_pos = None
        running_attr = f"{prefix}_running"
        if hasattr(self, running_attr):
            setattr(self, running_attr, True)
        self._flash("Resumed from scrubbed position")
        return True

    return False


def _draw_tt_scrubber(self, max_y, max_x):
    """Draw the time-travel scrubber bar overlay at the bottom of the screen."""
    prefix = self._tt_get_active_mode_prefix()
    if prefix is None:
        return  # GoL has its own timeline rendering

    hist_len = len(self.tt_history)
    if hist_len == 0:
        return

    bar_y = max_y - 1
    if bar_y <= 0:
        return

    # Build label and position info
    if self.tt_pos is not None:
        gen_attr = f"{prefix}_generation"
        gen = getattr(self, gen_attr, "?")
        pos_label = f" Gen {gen} ({self.tt_pos + 1}/{hist_len}) [SCRUBBING] u/[=back n/]=fwd "
    else:
        pos_label = f" LIVE ({hist_len} saved) u=rewind [/]=scrub "

    bar_label = " Timeline: "
    bar_width = max_x - len(bar_label) - len(pos_label) - 1
    if bar_width < 3:
        return

    if self.tt_pos is not None:
        filled = max(1, int((self.tt_pos + 1) / hist_len * bar_width))
        empty = bar_width - filled
        bar_str = "\u2588" * filled + "\u2591" * empty
    else:
        bar_str = "\u2588" * bar_width

    try:
        self.stdscr.addstr(bar_y, 0, bar_label, curses.color_pair(6) | curses.A_DIM)
        self.stdscr.addstr(bar_y, len(bar_label), bar_str, curses.color_pair(7))
        self.stdscr.addstr(bar_y, len(bar_label) + len(bar_str), pos_label,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register time-travel methods on the App class."""
    App._tt_get_active_mode_prefix = _tt_get_active_mode_prefix
    App._tt_snapshot = _tt_snapshot
    App._tt_restore = _tt_restore
    App._tt_push = _tt_push
    App._tt_rewind = _tt_rewind
    App._tt_scrub_back = _tt_scrub_back
    App._tt_scrub_forward = _tt_scrub_forward
    App._tt_step_forward = _tt_step_forward
    App._tt_pause_active_mode = _tt_pause_active_mode
    App._tt_auto_record = _tt_auto_record
    App._tt_handle_key = _tt_handle_key
    App._draw_tt_scrubber = _draw_tt_scrubber
