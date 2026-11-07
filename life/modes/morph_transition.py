"""Mode Morph Transitions — crossfade the previous mode's last frame into the new mode.

The outgoing screen is captured on mode exit and faded out over a set
number of frames while the new mode draws normally.  Hooks into
_exit_current_modes (capture) and _tc_refresh (blend).

Toggle with 'G' (Shift+G).  Adjust duration with '[' / ']'.
Cycle easing curve with ':'.
"""

import curses
import sys


# ── Easing functions ─────────────────────────────────────────────────────

def _ease_linear(t):
    return t

def _ease_smooth(t):
    """Smooth-step (ease-in-out cubic)."""
    return t * t * (3.0 - 2.0 * t)

def _ease_in_out(t):
    """Ease-in-out quintic for a more dramatic curve."""
    if t < 0.5:
        return 16.0 * t * t * t * t * t
    u = 1.0 - t
    return 1.0 - 16.0 * u * u * u * u * u

EASING_FUNCS = [
    ("linear", _ease_linear),
    ("smooth", _ease_smooth),
    ("ease-in-out", _ease_in_out),
]


# ── State initialisation ────────────────────────────────────────────────

def _morph_transition_init(self):
    """Initialise morph transition state variables."""
    self.morph_enabled = False          # global toggle for crossfade transitions
    self.morph_duration = 45            # frames for the crossfade (30-60 typical)
    self.morph_easing_idx = 1           # index into EASING_FUNCS (default: smooth)
    self._morph_active = False          # currently mid-transition?
    self._morph_progress = 0            # current frame counter (0..morph_duration)
    self._morph_old_frame = {}          # captured frame: (y,x) -> (char, r, g, b)
    self._morph_old_curses = {}         # captured curses-only cells: (y,x) -> char


# ── Frame capture ────────────────────────────────────────────────────────

def _morph_capture_frame(self):
    """Capture the truecolor and curses cells on screen as the outgoing frame."""
    my, mx = self.stdscr.getmaxyx()
    safe_mx = mx - 1
    frame = {}

    for y, x, text, r, g, b, _bold, _dim in self.tc_buf.cells:
        frame[(y, x)] = (text[:1] if text else " ", r, g, b)

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

    self._morph_old_frame = frame
    self._morph_progress = 0
    self._morph_active = True


# ── Crossfade rendering ─────────────────────────────────────────────────

def _morph_render_crossfade(self):
    """Overlay the captured frame, fading it out with the easing curve."""
    if not self._morph_active:
        return

    self._morph_progress += 1
    if self._morph_progress >= self.morph_duration:
        self._morph_active = False
        self._morph_old_frame.clear()
        return

    t = self._morph_progress / self.morph_duration
    _name, easing_fn = EASING_FUNCS[self.morph_easing_idx]
    alpha_old = 1.0 - easing_fn(t)

    if alpha_old <= 0.01:
        self._morph_active = False
        self._morph_old_frame.clear()
        return

    new_occupied = set()
    for y, x, _t, _r, _g, _b, _bo, _di in self.tc_buf.cells:
        new_occupied.add((y, x))

    my, mx = self.stdscr.getmaxyx()
    safe_mx = mx - 1

    # Render old frame cells with faded alpha
    parts = []
    for (y, x), (char, r, g, b) in self._morph_old_frame.items():
        if y >= my or x >= safe_mx:
            continue
        if (y, x) in new_occupied:
            continue  # the new mode's content takes priority

        if r is not None:
            dr = max(0, int(r * alpha_old))
            dg = max(0, int(g * alpha_old))
            db = max(0, int(b * alpha_old))
        else:  # curses-only cell has no RGB; use grey
            grey = max(0, int(180 * alpha_old))
            dr = dg = db = grey

        # Emit raw ANSI escapes: curses cannot draw 24-bit colour
        pos = f'\033[{y + 1};{x + 1}H'
        color = f'\033[38;2;{dr};{dg};{db}m'
        dim_attr = '\033[2m' if alpha_old < 0.5 else ''
        parts.append(f'{pos}{color}{dim_attr}{char}')

    if parts:
        parts.append('\033[0m')
        sys.stdout.write(''.join(parts))
        sys.stdout.flush()


# ── Indicator overlay ────────────────────────────────────────────────────

def _morph_draw_indicator(self):
    """Draw a compact status badge when morph transitions are enabled."""
    if not self.morph_enabled:
        return
    my, mx = self.stdscr.getmaxyx()
    easing_name = EASING_FUNCS[self.morph_easing_idx][0]
    if self._morph_active:
        pct = int(100 * self._morph_progress / max(1, self.morph_duration))
        label = f" MORPH:{self.morph_duration}f {easing_name} [{pct}%] "
    else:
        label = f" MORPH:{self.morph_duration}f {easing_name} "
    # Sit to the right of the ghost trail badge
    col = 1
    if self.ghost_trail_active:
        col += 22
    if col + len(label) >= mx:
        return
    try:
        self.stdscr.addstr(0, col, label, curses.color_pair(3) | curses.A_BOLD)
    except curses.error:
        pass
    self.stdscr.refresh()


# ── Key handling ─────────────────────────────────────────────────────────

def _morph_handle_key(self, key):
    """Handle morph transition keys.  Return True if the key was consumed."""
    # 'G' (Shift+G) — toggle morph transitions on/off
    if key == ord("G"):
        self.morph_enabled = not self.morph_enabled
        if not self.morph_enabled:
            self._morph_active = False
            self._morph_old_frame.clear()
        msg = "Mode Morphing ON" if self.morph_enabled else "Mode Morphing OFF"
        if self.morph_enabled:
            easing_name = EASING_FUNCS[self.morph_easing_idx][0]
            msg += f" ({self.morph_duration} frames, {easing_name})"
        self._flash(msg)
        return True

    if not self.morph_enabled:
        return False

    # '[' — decrease transition duration
    if key == ord("["):
        self.morph_duration = max(10, self.morph_duration - 5)
        self._flash(f"Morph duration: {self.morph_duration} frames")
        return True

    # ']' — increase transition duration
    if key == ord("]"):
        self.morph_duration = min(120, self.morph_duration + 5)
        self._flash(f"Morph duration: {self.morph_duration} frames")
        return True

    # ':' — cycle easing curve (Ctrl+T belongs to the phase bookmarks)
    if key == ord(":"):
        self.morph_easing_idx = (self.morph_easing_idx + 1) % len(EASING_FUNCS)
        easing_name = EASING_FUNCS[self.morph_easing_idx][0]
        self._flash(f"Morph easing: {easing_name}")
        return True

    return False


# ── Hooks ────────────────────────────────────────────────────────────────

def _morph_on_mode_exit(self):
    """Capture the outgoing screen when morphing is enabled."""
    if self.morph_enabled:
        _morph_capture_frame(self)


def _morph_on_refresh(self):
    """Draw the crossfade overlay.

    Call after stdscr.refresh() and tc_buf.render() so the fading remnants
    land on top of the new mode.
    """
    if self._morph_active:
        _morph_render_crossfade(self)


# ── Registration ─────────────────────────────────────────────────────────

def register(App):
    """Attach morph transition methods and state initialiser to App."""
    App._morph_transition_init = _morph_transition_init
    App._morph_capture_frame = _morph_capture_frame
    App._morph_render_crossfade = _morph_render_crossfade
    App._morph_draw_indicator = _morph_draw_indicator
    App._morph_handle_key = _morph_handle_key
    App._morph_on_mode_exit = _morph_on_mode_exit
    App._morph_on_refresh = _morph_on_refresh
