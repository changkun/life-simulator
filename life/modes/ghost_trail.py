"""Ghost Trail / Temporal Echo rendering layer.

Captures frame snapshots and overlays fading afterimages from previous frames
onto any simulation mode.  Particles leave streaks, wavefronts show propagation
paths, cellular automata reveal their evolution.

Toggle with 'g'.  Adjust trail length with '<' / '>'.  Cycle decay curve
(linear / exponential) with Ctrl+G.  Works with all 125+ modes via the
truecolor pipeline without modifying any mode logic.
"""

import curses

from life.colors import colormap_rgb

# Ghost glyph sequence: newer echoes are more solid, older ones dissolve
_GHOST_GLYPHS = ["\u2593", "\u2592", "\u2591", "\u00b7"]  # ▓ ▒ ░ ·


# ── state initialisation ─────────────────────────────────────────────────

def _ghost_trail_init(self):
    """Initialise ghost trail state variables (called from App.__init__)."""
    self.ghost_trail_active = False
    self.ghost_trail_depth = 6          # number of echo frames to retain
    self.ghost_trail_decay = "exp"      # "linear" or "exp"
    self._ghost_frames: list[dict] = [] # ring buffer of frame snapshots
    self._ghost_frame_done = False       # flag: already processed this draw cycle


# ── capture ──────────────────────────────────────────────────────────────

def _ghost_trail_capture(self):
    """Snapshot the current frame's visible content.

    Stores a dict mapping (y, x) -> (char, r, g, b) for every occupied cell.
    Truecolor cells keep their original RGB; curses-only cells store None RGB
    and will be coloured by the active colormap when rendered as echoes.
    """
    my, mx = self.stdscr.getmaxyx()
    safe_mx = mx - 1

    frame: dict[tuple[int, int], tuple[str, int | None, int | None, int | None]] = {}

    # 1) Truecolor cells (full RGB)
    for y, x, text, r, g, b, _bold, _dim in self.tc_buf.cells:
        # Only store the first character for single-char ghost glyphs
        frame[(y, x)] = (text[:1] if text else " ", r, g, b)

    # 2) Curses screen cells (occupancy check via inch)
    for y in range(my):
        for x in range(safe_mx):
            if (y, x) in frame:
                continue
            try:
                ch = self.stdscr.inch(y, x)
                c = ch & 0xFF
                if c != ord(" ") and c != 0:
                    frame[(y, x)] = (chr(c), None, None, None)
            except curses.error:
                pass

    self._ghost_frames.append(frame)
    # Trim ring buffer (keep depth + 1: depth echoes + current frame)
    max_keep = self.ghost_trail_depth + 1
    if len(self._ghost_frames) > max_keep:
        self._ghost_frames = self._ghost_frames[-max_keep:]


# ── inject echoes ────────────────────────────────────────────────────────

def _ghost_trail_inject(self):
    """Render faded afterimages from previous frames into tc_buf.

    Iterates stored frames from newest to oldest.  For each cell that was
    occupied in a past frame but is *not* occupied in the current frame (and
    hasn't been claimed by a newer echo), a dimmed truecolor glyph is emitted.
    """
    n = len(self._ghost_frames)
    if n < 2:
        return

    # Build set of currently-occupied positions
    current = self._ghost_frames[-1]
    occupied = set(current.keys())
    # Also include any tc_buf cells queued by the current draw pass
    for y, x, _t, _r, _g, _b, _bo, _di in self.tc_buf.cells:
        occupied.add((y, x))

    placed: set[tuple[int, int]] = set()
    echo_count = min(self.ghost_trail_depth, n - 1)

    for i in range(1, echo_count + 1):
        frame = self._ghost_frames[n - 1 - i]
        # age 1 = most recent echo, echo_count = oldest
        age = i

        # Decay factor
        if self.ghost_trail_decay == "exp":
            factor = 0.65 ** age
        else:
            factor = max(0.08, 1.0 - age / (echo_count + 1))

        glyph_idx = min(age - 1, len(_GHOST_GLYPHS) - 1)
        glyph = _GHOST_GLYPHS[glyph_idx]

        for (y, x), (_char, r, g, b) in frame.items():
            if (y, x) in occupied or (y, x) in placed:
                continue
            placed.add((y, x))

            if r is not None:
                # Original RGB available — decay it
                dr = max(0, int(r * factor))
                dg = max(0, int(g * factor))
                db = max(0, int(b * factor))
            else:
                # Curses-only cell — derive colour from the active colormap
                cr, cg, cb = colormap_rgb(self.tc_colormap, max(0.15, factor))
                dr = max(0, int(cr * factor))
                dg = max(0, int(cg * factor))
                db = max(0, int(cb * factor))

            self.tc_buf.put(y, x, glyph, dr, dg, db, dim=True)


# ── main hook ────────────────────────────────────────────────────────────

def _ghost_trail_process(self):
    """Capture current frame and inject echoes.  Called once per draw cycle."""
    if not self.ghost_trail_active or self._ghost_frame_done:
        return
    self._ghost_frame_done = True
    _ghost_trail_capture(self)
    _ghost_trail_inject(self)


# ── indicator overlay ────────────────────────────────────────────────────

def _ghost_trail_draw_indicator(self):
    """Draw a compact status badge when ghost trail is active."""
    if not self.ghost_trail_active:
        return
    my, mx = self.stdscr.getmaxyx()
    decay_tag = "EXP" if self.ghost_trail_decay == "exp" else "LIN"
    label = f" GHOST:{self.ghost_trail_depth}f {decay_tag} "
    col = 1
    if col + len(label) >= mx:
        return
    try:
        self.stdscr.addstr(0, col, label, curses.color_pair(3) | curses.A_BOLD)
    except curses.error:
        pass
    self.stdscr.refresh()


# ── key handling ─────────────────────────────────────────────────────────

def _ghost_trail_handle_key(self, key):
    """Handle ghost trail key bindings.  Returns True if key was consumed."""
    # 'g' — toggle ghost trail on/off
    if key == ord("g"):
        self.ghost_trail_active = not self.ghost_trail_active
        if not self.ghost_trail_active:
            self._ghost_frames.clear()
        msg = "Ghost Trail ON" if self.ghost_trail_active else "Ghost Trail OFF"
        if self.ghost_trail_active:
            decay_tag = "exponential" if self.ghost_trail_decay == "exp" else "linear"
            msg += f" ({self.ghost_trail_depth} frames, {decay_tag} decay)"
        self._flash(msg)
        return True

    if not self.ghost_trail_active:
        return False

    # '<' / ',' — decrease trail depth
    if key == ord("<") or key == ord(","):
        self.ghost_trail_depth = max(1, self.ghost_trail_depth - 1)
        max_keep = self.ghost_trail_depth + 1
        if len(self._ghost_frames) > max_keep:
            self._ghost_frames = self._ghost_frames[-max_keep:]
        self._flash(f"Ghost Trail: {self.ghost_trail_depth} frames")
        return True

    # '>' / '.' — increase trail depth
    if key == ord(">") or key == ord("."):
        self.ghost_trail_depth = min(20, self.ghost_trail_depth + 1)
        self._flash(f"Ghost Trail: {self.ghost_trail_depth} frames")
        return True

    # Ctrl+G (7) — cycle decay curve
    if key == 7:
        if self.ghost_trail_decay == "exp":
            self.ghost_trail_decay = "linear"
        else:
            self.ghost_trail_decay = "exp"
        decay_tag = "exponential" if self.ghost_trail_decay == "exp" else "linear"
        self._flash(f"Ghost Trail decay: {decay_tag}")
        return True

    return False


# ── registration ─────────────────────────────────────────────────────────

def register(App):
    """Attach ghost trail methods and state initialiser to App."""
    App._ghost_trail_init = _ghost_trail_init
    App._ghost_trail_process = _ghost_trail_process
    App._ghost_trail_draw_indicator = _ghost_trail_draw_indicator
    App._ghost_trail_handle_key = _ghost_trail_handle_key
