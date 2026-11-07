"""Recording & Export — capture terminal frames and save them as an asciinema .cast or a plain-text flipbook."""

import curses
import json
import os
import time

from life.constants import SAVE_DIR


# ── ANSI color mapping from curses color pairs / attributes ──

# curses colour constants → ANSI SGR codes.
_CURSES_TO_ANSI_FG = {
    curses.COLOR_BLACK: 30,
    curses.COLOR_RED: 31,
    curses.COLOR_GREEN: 32,
    curses.COLOR_YELLOW: 33,
    curses.COLOR_BLUE: 34,
    curses.COLOR_MAGENTA: 35,
    curses.COLOR_CYAN: 36,
    curses.COLOR_WHITE: 37,
}

_CURSES_TO_ANSI_BG = {
    curses.COLOR_BLACK: 40,
    curses.COLOR_RED: 41,
    curses.COLOR_GREEN: 42,
    curses.COLOR_YELLOW: 43,
    curses.COLOR_BLUE: 44,
    curses.COLOR_MAGENTA: 45,
    curses.COLOR_CYAN: 46,
    curses.COLOR_WHITE: 47,
}


def _attr_to_ansi(attr):
    """Convert a curses attribute bitmask to an ANSI escape prefix string."""
    codes = []
    if attr & curses.A_BOLD:
        codes.append("1")
    if attr & curses.A_DIM:
        codes.append("2")
    if attr & curses.A_REVERSE:
        codes.append("7")
    if attr & curses.A_UNDERLINE:
        codes.append("4")
    pair_num = curses.pair_number(attr)
    if pair_num > 0:
        try:
            fg, bg = curses.pair_content(pair_num)
            if fg in _CURSES_TO_ANSI_FG:
                codes.append(str(_CURSES_TO_ANSI_FG[fg]))
            if bg in _CURSES_TO_ANSI_BG and bg != curses.COLOR_BLACK:
                codes.append(str(_CURSES_TO_ANSI_BG[bg]))
        except curses.error:
            pass
    if codes:
        return "\033[" + ";".join(codes) + "m"
    return ""


def _capture_frame(stdscr):
    """Read the entire curses window and return a single string with ANSI escapes.

    Walks each cell of the window, groups runs of identical attributes,
    and emits ANSI escape sequences for color/bold/dim changes.
    """
    max_y, max_x = stdscr.getmaxyx()
    lines = []
    for y in range(max_y):
        line_parts = []
        prev_attr = None
        for x in range(max_x):
            try:
                ch_int = stdscr.inch(y, x)
            except curses.error:
                break
            ch = chr(ch_int & 0xFF)
            attr = ch_int & ~0xFF
            if attr != prev_attr:
                if prev_attr is not None:
                    line_parts.append("\033[0m")
                ansi = _attr_to_ansi(attr)
                if ansi:
                    line_parts.append(ansi)
                prev_attr = attr
            line_parts.append(ch)
        if prev_attr is not None and prev_attr != 0:
            line_parts.append("\033[0m")
        line = "".join(line_parts).rstrip()
        lines.append(line)
    # Remove trailing empty lines
    while lines and not lines[-1]:
        lines.pop()
    return "\r\n".join(lines)


def _capture_frame_plain(stdscr):
    """Read the entire curses window as plain text (no ANSI escapes)."""
    max_y, max_x = stdscr.getmaxyx()
    lines = []
    for y in range(max_y):
        line_parts = []
        for x in range(max_x):
            try:
                ch_int = stdscr.inch(y, x)
            except curses.error:
                break
            line_parts.append(chr(ch_int & 0xFF))
        lines.append("".join(line_parts).rstrip())
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


# ── Export functions ──

def _export_cast(frames, timestamps, width, height, filepath):
    """Write frames as asciinema v2 .cast file.

    Format spec: https://docs.asciinema.org/manual/asciicast/v2/
    Header line: JSON object with version, width, height, timestamp.
    Event lines: [elapsed_seconds, "o", data_string]
    """
    header = {
        "version": 2,
        "width": width,
        "height": height,
        "timestamp": int(timestamps[0]) if timestamps else int(time.time()),
        "env": {"TERM": os.environ.get("TERM", "xterm-256color")},
        "title": "life-simulator simulation recording",
    }
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(header) + "\n")
        t0 = timestamps[0] if timestamps else 0.0
        for i, frame in enumerate(frames):
            elapsed = timestamps[i] - t0 if i < len(timestamps) else 0.0
            # Clear screen + move cursor home, then draw frame
            data = "\033[2J\033[H" + frame
            event = json.dumps([round(elapsed, 6), "o", data])
            f.write(event + "\n")


def _export_txt(frames, timestamps, filepath):
    """Write frames as plain-text flipbook separated by form-feed characters."""
    with open(filepath, "w", encoding="utf-8") as f:
        t0 = timestamps[0] if timestamps else 0.0
        for i, frame in enumerate(frames):
            elapsed = timestamps[i] - t0 if i < len(timestamps) else 0.0
            f.write(f"--- Frame {i + 1}  t={elapsed:.3f}s ---\n")
            f.write(frame)
            f.write("\n\f\n")


# ── Methods bound to App ──

def _cast_rec_init(self):
    """Initialize recording state."""
    self.cast_recording = False
    self.cast_frames = []          # list of ANSI-encoded frame strings
    self.cast_frames_plain = []    # list of plain-text frame strings (for .txt export)
    self.cast_timestamps = []      # wall-clock timestamp per frame
    self.cast_start_time = 0.0
    self.cast_fps = 10             # max capture FPS (skip frames if simulation is faster)
    self.cast_max_frames = 3000    # safety cap
    self.cast_last_capture = 0.0   # time of last captured frame
    self.cast_export_menu = False  # show export format picker
    self.cast_export_sel = 0       # selected export format index
    self.cast_width = 80
    self.cast_height = 24


def _cast_rec_start(self):
    """Begin recording terminal frames."""
    self.cast_recording = True
    self.cast_frames = []
    self.cast_frames_plain = []
    self.cast_timestamps = []
    self.cast_start_time = time.time()
    self.cast_last_capture = 0.0
    max_y, max_x = self.stdscr.getmaxyx()
    self.cast_width = max_x
    self.cast_height = max_y
    self._flash("REC started (Ctrl+X to stop)")


def _cast_rec_stop(self):
    """Stop recording and show export menu."""
    self.cast_recording = False
    n = len(self.cast_frames)
    if n == 0:
        self._flash("Recording cancelled (no frames captured)")
        return
    self.cast_export_menu = True
    self.cast_export_sel = 0
    self._flash(f"Recording stopped — {n} frames captured")


def _cast_rec_toggle(self):
    """Toggle recording on/off via hotkey."""
    if self.cast_recording:
        self._cast_rec_stop()
    elif self.cast_export_menu:
        pass  # Finish or discard the pending export first.
    else:
        self._cast_rec_start()


def _cast_rec_capture(self):
    """Capture current frame if recording is active and FPS budget allows."""
    if not self.cast_recording:
        return
    now = time.time()
    min_interval = 1.0 / self.cast_fps if self.cast_fps > 0 else 0.0
    if now - self.cast_last_capture < min_interval:
        return
    if len(self.cast_frames) >= self.cast_max_frames:
        self._cast_rec_stop()
        self._flash(f"Recording auto-stopped (max {self.cast_max_frames} frames)")
        return
    self.cast_last_capture = now
    self.cast_timestamps.append(now)
    self.cast_frames.append(_capture_frame(self.stdscr))
    self.cast_frames_plain.append(_capture_frame_plain(self.stdscr))


def _cast_rec_export(self, fmt):
    """Export captured frames in the given format ('cast' or 'txt').

    On a write error the frames are kept so the user can retry or pick another format.
    """
    if fmt not in ("cast", "txt"):
        self._flash(f"Unknown format: {fmt}")
        return
    n = len(self.cast_frames)
    filename = f"recording_{int(time.time())}.{fmt}"
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        filepath = os.path.join(SAVE_DIR, filename)
        if fmt == "cast":
            _export_cast(self.cast_frames, self.cast_timestamps,
                         self.cast_width, self.cast_height, filepath)
        else:
            _export_txt(self.cast_frames_plain, self.cast_timestamps, filepath)
    except OSError as e:
        self._flash(f"Export failed: {e.strerror or e}")
        return
    self._flash(f"Saved: {filename} ({n} frames)")
    _cast_rec_clear(self)


def _cast_rec_clear(self):
    """Drop captured frames and close the export menu."""
    self.cast_frames = []
    self.cast_frames_plain = []
    self.cast_timestamps = []
    self.cast_export_menu = False


def _cast_rec_discard(self):
    """Discard captured frames without exporting."""
    _cast_rec_clear(self)
    self._flash("Recording discarded")


def _handle_cast_export_key(self, key):
    """Handle input on the export format menu. Returns True if key was consumed."""
    if not self.cast_export_menu:
        return False
    if key == -1:
        return True
    export_options = ["cast", "txt", "both"]
    if key == curses.KEY_UP or key == ord("k"):
        self.cast_export_sel = (self.cast_export_sel - 1) % len(export_options)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.cast_export_sel = (self.cast_export_sel + 1) % len(export_options)
        return True
    if key in (10, 13, curses.KEY_ENTER):
        choice = export_options[self.cast_export_sel]
        if choice == "both":
            self._cast_rec_export_both()
        else:
            self._cast_rec_export(choice)
        return True
    if key == ord("1"):
        self._cast_rec_export("cast")
        return True
    if key == ord("2"):
        self._cast_rec_export("txt")
        return True
    if key == ord("3"):
        self._cast_rec_export_both()
        return True
    if key == 27 or key == ord("q"):  # ESC or q — discard
        self._cast_rec_discard()
        return True
    if key == ord("d"):
        self._cast_rec_discard()
        return True
    return True  # The menu swallows every key while open.


def _cast_rec_export_both(self):
    """Export as both .cast and .txt."""
    n = len(self.cast_frames)
    stem = f"recording_{int(time.time())}"
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        _export_cast(self.cast_frames, self.cast_timestamps,
                     self.cast_width, self.cast_height,
                     os.path.join(SAVE_DIR, stem + ".cast"))
        _export_txt(self.cast_frames_plain, self.cast_timestamps,
                    os.path.join(SAVE_DIR, stem + ".txt"))
    except OSError as e:
        self._flash(f"Export failed: {e.strerror or e}")
        return
    self._flash(f"Saved: {stem}.cast + {stem}.txt ({n} frames)")
    _cast_rec_clear(self)


def _draw_cast_export_menu(self, max_y, max_x):
    """Draw the export format selection menu."""
    n = len(self.cast_frames)
    duration = 0.0
    if self.cast_timestamps and len(self.cast_timestamps) > 1:
        duration = self.cast_timestamps[-1] - self.cast_timestamps[0]

    w = 46

    def row(text=""):
        return "║" + text.ljust(w)[:w] + "║"

    lines = [
        "╔" + "═" * w + "╗",
        row("       EXPORT RECORDING"),
        "╠" + "═" * w + "╣",
        row(f"  Frames: {n:<6d}  Duration: {duration:>6.1f}s"),
        row(f"  Size: {self.cast_width}x{self.cast_height}"),
        row(),
        row("  Select export format:"),
        row(),
    ]

    options = [
        ("1", "Asciinema .cast", "Terminal / web player"),
        ("2", "Plain-text .txt", "One plain frame/page"),
        ("3", "Both formats",    "Export .cast + .txt"),
    ]
    for i, (num, name, desc) in enumerate(options):
        marker = ">" if i == self.cast_export_sel else " "
        lines.append(row(f"  {marker} [{num}] {name:<16s} {desc}"))

    lines += [
        row(),
        row("  Enter=export  d=discard  Esc=cancel"),
        row("  Files saved to: ~/.life_saves/"),
        "╚" + "═" * w + "╝",
    ]

    start_y = max(0, (max_y - len(lines)) // 2)
    for i, line in enumerate(lines):
        y = start_y + i
        if y >= max_y:
            break
        x = max(0, (max_x - len(line)) // 2)
        attr = curses.color_pair(7)
        if i >= 8 and i < 8 + len(options):
            idx = i - 8
            if idx == self.cast_export_sel:
                attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, x, line, attr)
        except curses.error:
            pass
    self.stdscr.refresh()


def _draw_cast_indicator(self, max_y, max_x):
    """Draw a blinking REC indicator in the top-right corner."""
    if not self.cast_recording:
        return
    n = len(self.cast_frames)
    elapsed = time.time() - self.cast_start_time if self.cast_start_time else 0.0
    blink = "●" if int(elapsed * 2) % 2 == 0 else "○"
    label = f" {blink} REC {n}f {elapsed:.0f}s "
    y = 0
    x = max(0, max_x - len(label) - 1)
    try:
        self.stdscr.addstr(y, x, label, curses.color_pair(1) | curses.A_BOLD)
    except curses.error:
        pass


def _cast_handle_key(self, key):
    """Handle Ctrl+X for recording toggle. Returns True if consumed."""
    if key == 24:  # Ctrl+X
        self._cast_rec_toggle()
        return True
    return False


def register(App):
    """Attach recording methods to the App class."""
    App._cast_rec_init = _cast_rec_init
    App._cast_rec_start = _cast_rec_start
    App._cast_rec_stop = _cast_rec_stop
    App._cast_rec_toggle = _cast_rec_toggle
    App._cast_rec_capture = _cast_rec_capture
    App._cast_rec_export = _cast_rec_export
    App._cast_rec_discard = _cast_rec_discard
    App._cast_rec_export_both = _cast_rec_export_both
    App._handle_cast_export_key = _handle_cast_export_key
    App._draw_cast_export_menu = _draw_cast_export_menu
    App._draw_cast_indicator = _draw_cast_indicator
    App._cast_handle_key = _cast_handle_key
