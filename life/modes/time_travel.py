"""Time Travel — records the active mode's state so you can rewind and scrub through it."""
import copy
import curses
import math
import pickle
import time

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


# Total byte budget for pickled snapshots held in ``tt_history``.
TT_BYTE_BUDGET = 64 * 1024 * 1024

# Average time per frame recording may take. Modes whose snapshot costs
# more (multi-MB state) are recorded every Nth generation instead of every
# one; cheap modes keep frame-by-frame history.
TT_FRAME_BUDGET = 0.002
TT_MAX_STRIDE = 10

_PICKLE_PROTO = pickle.HIGHEST_PROTOCOL


class _TTSnapshot:
    """Compact, immutable-ish snapshot of one mode's state.

    Picklable attributes are stored as a single ``pickle`` blob; attributes
    that cannot be pickled fall back to ``copy.deepcopy`` and live in
    ``extra``.  Behaves like a read-mostly mapping (``snap["attr"]``,
    ``in``, ``get``, ``items``) by unpickling on demand, so every access
    yields fresh, independent objects.
    """

    __slots__ = ("blob", "extra", "nbytes")

    def __init__(self, blob, extra, prefix):
        self.blob = blob
        self.extra = extra
        self.extra["_prefix"] = prefix
        self.nbytes = len(blob) if blob else 0

    @property
    def prefix(self):
        return self.extra.get("_prefix")

    def state(self):
        """Return a fresh dict of all captured attributes (no _prefix)."""
        out = pickle.loads(self.blob) if self.blob else {}
        for k, v in self.extra.items():
            if k != "_prefix":
                out[k] = copy.deepcopy(v)
        return out

    def _full(self):
        d = self.state()
        d["_prefix"] = self.prefix
        return d

    def __getitem__(self, key):
        if key == "_prefix":
            return self.prefix
        return self._full()[key]

    def __setitem__(self, key, value):
        self.extra[key] = value

    def __contains__(self, key):
        return key in self._full()

    def get(self, key, default=None):
        if key == "_prefix":
            return self.prefix
        return self._full().get(key, default)

    def keys(self):
        return self._full().keys()

    def items(self):
        return self._full().items()

    def __iter__(self):
        return iter(self._full())

    def __len__(self):
        return len(self._full())


def _tt_snapshot(self, prefix):
    """Capture the state of the mode with the given attribute prefix."""
    state = {}
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
        state[attr_name] = val
    try:
        blob = pickle.dumps(state, protocol=_PICKLE_PROTO)
        return _TTSnapshot(blob, {}, prefix)
    except Exception:
        pass
    # Slow path: pickle what we can, deepcopy the rest.
    good = {}
    extra = {}
    for k, v in state.items():
        try:
            pickle.dumps(v, protocol=_PICKLE_PROTO)
            good[k] = v
        except Exception:
            try:
                extra[k] = copy.deepcopy(v)
            except Exception:
                pass  # unsnapshottable; leave live value untouched on restore
    try:
        blob = pickle.dumps(good, protocol=_PICKLE_PROTO)
    except Exception:
        blob = pickle.dumps({}, protocol=_PICKLE_PROTO)
    return _TTSnapshot(blob, extra, prefix)


def _tt_restore(self, snapshot):
    """Restore mode state from a snapshot, using fresh objects each time."""
    if isinstance(snapshot, _TTSnapshot):
        items = snapshot.state()
    else:  # plain dict (legacy / tests)
        items = {k: copy.deepcopy(v) for k, v in snapshot.items()}
    for key, val in items.items():
        setattr(self, key, val)


def _tt_history_bytes(self):
    """Byte total of tt_history, kept as a running sum by _tt_push.

    Recomputed whenever the list was replaced or resized elsewhere
    (scrub truncation, clear on mode switch, ...).
    """
    hist = self.tt_history
    if getattr(self, "_tt_bytes_key", None) != (id(hist), len(hist)):
        self._tt_bytes = sum(getattr(h, "nbytes", 0) for h in hist)
    return self._tt_bytes


def _tt_push(self):
    """Append the current state to the history, trimming it to its limits."""
    prefix = self._tt_get_active_mode_prefix()
    if prefix is None:
        return

    # Recording from a scrubbed position drops the abandoned future.
    if self.tt_pos is not None:
        self.tt_history = self.tt_history[:self.tt_pos + 1]
        self.tt_pos = None

    total = _tt_history_bytes(self)
    snap = self._tt_snapshot(prefix)
    self.tt_history.append(snap)
    total += getattr(snap, "nbytes", 0)

    # Enforce the entry cap and the byte budget by dropping the oldest
    # entries (always keep the newest one).
    hist = self.tt_history
    drop = max(0, len(hist) - self.tt_max)
    total -= sum(getattr(h, "nbytes", 0) for h in hist[:drop])
    while total > TT_BYTE_BUDGET and drop < len(hist) - 1:
        total -= getattr(hist[drop], "nbytes", 0)
        drop += 1
    if drop:
        self.tt_history = hist[drop:]

    self._tt_bytes = total
    self._tt_bytes_key = (id(self.tt_history), len(self.tt_history))


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
    """Record a snapshot of the running mode, thinned by the adaptive stride.

    Called at the start of each main-loop iteration.  Skips frames where a
    mode's generation has not advanced.
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
    # Modes without a generation counter record every frame.

    # Detect mode switch — clear history if prefix changed
    if self.tt_history and self.tt_history[-1].get("_prefix") != prefix:
        self.tt_history.clear()
        self.tt_pos = None
        self._tt_last_gen = -1
        self._tt_stride = 1
        self._tt_skip = 0

    # Record every _tt_stride-th new generation (1 for cheap snapshots).
    if self.tt_history:
        self._tt_skip = (self._tt_skip or 0) + 1
        if self._tt_skip < (self._tt_stride or 1):
            return
    self._tt_skip = 0

    t0 = time.perf_counter()
    self._tt_push()
    cost = time.perf_counter() - t0
    self._tt_stride = max(1, min(TT_MAX_STRIDE, math.ceil(cost / TT_FRAME_BUDGET)))


def _tt_handle_key(self, key):
    """Handle the time-travel keys.  Return True if the key was consumed."""
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
        # Drop the future and resume from here.
        self.tt_history = self.tt_history[:self.tt_pos + 1]
        self.tt_pos = None
        running_attr = f"{prefix}_running"
        if hasattr(self, running_attr):
            setattr(self, running_attr, True)
        self._flash("Resumed from scrubbed position")
        return True

    return False


def _draw_tt_scrubber(self, max_y, max_x):
    """Draw the timeline bar on the bottom row."""
    prefix = self._tt_get_active_mode_prefix()
    if prefix is None:
        return  # GoL has its own timeline rendering

    hist_len = len(self.tt_history)
    if hist_len == 0:
        return

    bar_y = max_y - 1
    if bar_y <= 0:
        return

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
