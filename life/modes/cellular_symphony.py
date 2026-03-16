"""Cellular Symphony — real-time sonification that turns CA patterns into emergent music.

Scans the grid row-by-row as a sequencer: columns map to pitch, cell density
controls rhythm, neighbor counts shape timbre, and different CA rules produce
different musical textures — from minimalist pulses (Rule 90) to chaotic jazz
(Life).  Users paint cells and hear the pattern sing, creating a synesthetic
experience where you *see* and *hear* emergence simultaneously.

Controls:
    Space       Toggle play / pause sequencer
    Enter       Step one sequencer row
    p           Toggle cell painting mode
    s           Cycle scale (pentatonic / chromatic / blues / whole-tone)
    t           Cycle timbre (sine / saw / square / triangle)
    o           Cycle octave range (2 / 3 / 4 / 5)
    +/-         Adjust tempo (BPM)
    v/V         Volume up / down
    r           Randomize grid
    c           Clear grid
    Tab         Cycle CA rule preset
    m           Toggle mute
    h           Toggle help overlay
    q/Esc       Exit mode
"""

import math
import struct
import threading
import time
import curses

# ── Musical scales (semitone intervals from root) ──────────────────────────

SCALES = {
    "pentatonic": [0, 2, 4, 7, 9],
    "chromatic":  list(range(12)),
    "blues":      [0, 3, 5, 6, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
}
SCALE_NAMES = list(SCALES.keys())

# ── Timbre waveforms ───────────────────────────────────────────────────────

def _wave_sine(phase):
    return math.sin(phase)

def _wave_saw(phase):
    p = (phase % (2 * math.pi)) / (2 * math.pi)
    return 2.0 * p - 1.0

def _wave_square(phase):
    return 1.0 if math.sin(phase) >= 0 else -1.0

def _wave_triangle(phase):
    p = (phase % (2 * math.pi)) / (2 * math.pi)
    return 4.0 * abs(p - 0.5) - 1.0

TIMBRES = {
    "sine":     _wave_sine,
    "saw":      _wave_saw,
    "square":   _wave_square,
    "triangle": _wave_triangle,
}
TIMBRE_NAMES = list(TIMBRES.keys())

# ── CA rule presets with musical character descriptions ─────────────────────

RULE_PRESETS = [
    {"name": "Conway's Life", "b": {3}, "s": {2, 3}, "character": "chaotic jazz"},
    {"name": "Seeds", "b": {2}, "s": set(), "character": "staccato bursts"},
    {"name": "Day & Night", "b": {3, 6, 7, 8}, "s": {3, 4, 6, 7, 8}, "character": "dense chords"},
    {"name": "Diamoeba", "b": {3, 5, 6, 7, 8}, "s": {5, 6, 7, 8}, "character": "evolving drones"},
    {"name": "HighLife", "b": {3, 6}, "s": {2, 3}, "character": "melodic drift"},
    {"name": "Maze", "b": {3}, "s": {1, 2, 3, 4, 5}, "character": "thick clusters"},
    {"name": "Anneal", "b": {4, 6, 7, 8}, "s": {3, 5, 6, 7, 8}, "character": "ambient wash"},
]

BASE_FREQ = 130.81  # C3

SAMPLE_RATE = 22050
MAX_VOICES = 16

# ── Helpers ────────────────────────────────────────────────────────────────

def _col_to_freq(col, total_cols, scale, octave_range, base_freq=BASE_FREQ):
    """Map a column index to a musical frequency using the chosen scale."""
    intervals = SCALES[scale]
    num_notes = len(intervals) * octave_range
    if total_cols <= 1:
        idx = 0
    else:
        idx = int(col * num_notes / total_cols)
    octave, degree = divmod(idx, len(intervals))
    semitones = octave * 12 + intervals[degree]
    return base_freq * (2.0 ** (semitones / 12.0))


def _neighbor_count(cells, r, c, rows, cols):
    """Count live Moore neighbors for cell (r, c) with wrapping."""
    count = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr = (r + dr) % rows
            nc = (c + dc) % cols
            if cells[nr][nc] > 0:
                count += 1
    return count


def _synthesize_symphony(voices, duration, volume, timbre_name, sample_rate=SAMPLE_RATE):
    """Synthesize mixed audio from a list of (freq, amplitude, harmonics) voices.

    Each voice gets its timbre shaped by harmonics (derived from neighbor count).
    Returns raw S16LE mono PCM bytes.
    """
    n_samples = max(1, int(sample_rate * duration))
    if not voices:
        return b"\x00\x00" * n_samples

    wave_fn = TIMBRES.get(timbre_name, _wave_sine)
    max_amp = 26000
    per_voice = volume / len(voices) if voices else 0

    buf = bytearray(n_samples * 2)
    ramp = min(int(0.008 * sample_rate), n_samples // 2)

    # Pre-compute increments and harmonic info
    voice_data = []
    for freq, amp_scale, harmonic_richness in voices:
        inc = 2.0 * math.pi * freq / sample_rate
        voice_data.append((inc, amp_scale, harmonic_richness))

    for i in range(n_samples):
        # Envelope
        if i < ramp:
            env = i / ramp
        elif i > n_samples - ramp:
            env = (n_samples - i) / ramp
        else:
            env = 1.0

        val = 0.0
        for inc, amp_scale, harm in voice_data:
            phase = inc * i
            # Fundamental
            s = wave_fn(phase)
            # Add harmonics based on neighbor density
            if harm >= 3:
                s += 0.3 * wave_fn(phase * 2)  # octave
            if harm >= 5:
                s += 0.15 * wave_fn(phase * 3)  # fifth above octave
            if harm >= 7:
                s += 0.08 * wave_fn(phase * 4)
            val += s * amp_scale

        val = val * per_voice * max_amp * env
        sample = max(-32767, min(32767, int(val)))
        struct.pack_into("<h", buf, i * 2, sample)

    return bytes(buf)


# ── Mode state and handlers ───────────────────────────────────────────────

def _enter_symphony_mode(self):
    """Initialize Cellular Symphony mode."""
    self.symphony_mode = True
    self.symphony_running = False
    self.symphony_scan_row = 0
    self.symphony_scale_idx = 0
    self.symphony_timbre_idx = 0
    self.symphony_octave_range = 3
    self.symphony_bpm = 120
    self.symphony_volume = 0.7
    self.symphony_muted = False
    self.symphony_painting = False
    self.symphony_paint_state = 1  # 1 = draw alive, 0 = erase
    self.symphony_rule_idx = 0
    self.symphony_show_help = True
    self.symphony_last_step_time = 0.0
    self.symphony_last_voices = []
    self.symphony_gen_count = 0

    # Apply first rule preset
    preset = RULE_PRESETS[self.symphony_rule_idx]
    self.grid.birth = set(preset["b"])
    self.grid.survival = set(preset["s"])

    # Enable sound engine
    if hasattr(self, 'sound') and self.sound and not self.sound.enabled:
        self.sound.toggle()


def _exit_symphony_mode(self):
    """Clean up Cellular Symphony mode."""
    self.symphony_mode = False
    self.symphony_running = False


def _is_symphony_auto_stepping(self):
    return self.symphony_running


def _handle_symphony_key(self, key):
    """Handle key input for Cellular Symphony mode."""
    if key in (ord('q'), 27):  # q or Esc
        self._exit_symphony_mode()
        return True

    if key == ord(' '):
        self.symphony_running = not self.symphony_running
        self.symphony_last_step_time = time.time()
        return True

    if key in (10, 13):  # Enter — single step
        _symphony_advance_row(self)
        return True

    if key == ord('p'):
        self.symphony_painting = not self.symphony_painting
        return True

    if key == ord('s'):
        self.symphony_scale_idx = (self.symphony_scale_idx + 1) % len(SCALE_NAMES)
        return True

    if key == ord('t'):
        self.symphony_timbre_idx = (self.symphony_timbre_idx + 1) % len(TIMBRE_NAMES)
        return True

    if key == ord('o'):
        self.symphony_octave_range = (self.symphony_octave_range % 4) + 2  # cycles 2-5
        return True

    if key in (ord('+'), ord('=')):
        self.symphony_bpm = min(300, self.symphony_bpm + 10)
        return True

    if key == ord('-'):
        self.symphony_bpm = max(20, self.symphony_bpm - 10)
        return True

    if key == ord('v'):
        self.symphony_volume = min(1.0, self.symphony_volume + 0.1)
        return True

    if key == ord('V'):
        self.symphony_volume = max(0.0, self.symphony_volume - 0.1)
        return True

    if key == ord('r'):
        import random
        for r in range(self.grid.rows):
            for c in range(self.grid.cols):
                self.grid.cells[r][c] = 1 if random.random() < 0.3 else 0
        self.grid.population = sum(
            1 for r in range(self.grid.rows)
            for c in range(self.grid.cols) if self.grid.cells[r][c] > 0
        )
        return True

    if key == ord('c'):
        self.grid.clear()
        self.symphony_scan_row = 0
        return True

    if key == ord('\t'):
        self.symphony_rule_idx = (self.symphony_rule_idx + 1) % len(RULE_PRESETS)
        preset = RULE_PRESETS[self.symphony_rule_idx]
        self.grid.birth = set(preset["b"])
        self.grid.survival = set(preset["s"])
        return True

    if key == ord('m'):
        self.symphony_muted = not self.symphony_muted
        return True

    if key == ord('h'):
        self.symphony_show_help = not self.symphony_show_help
        return True

    # Painting with arrow keys or mouse — paint cells at cursor
    if self.symphony_painting:
        moved = False
        if key == curses.KEY_UP and hasattr(self, 'cursor_r'):
            self.cursor_r = max(0, self.cursor_r - 1)
            moved = True
        elif key == curses.KEY_DOWN and hasattr(self, 'cursor_r'):
            self.cursor_r = min(self.grid.rows - 1, self.cursor_r + 1)
            moved = True
        elif key == curses.KEY_LEFT and hasattr(self, 'cursor_c'):
            self.cursor_c = max(0, self.cursor_c - 1)
            moved = True
        elif key == curses.KEY_RIGHT and hasattr(self, 'cursor_c'):
            self.cursor_c = min(self.grid.cols - 1, self.cursor_c + 1)
            moved = True
        elif key == ord('x'):
            if hasattr(self, 'cursor_r') and hasattr(self, 'cursor_c'):
                r, c = self.cursor_r, self.cursor_c
                if self.grid.cells[r][c] > 0:
                    self.grid.set_dead(r, c)
                else:
                    self.grid.set_alive(r, c)
            return True

        if moved:
            return True

    return False


def _symphony_advance_row(self):
    """Advance the sequencer by one row, play the corresponding notes, then step CA."""
    grid = self.grid
    rows, cols = grid.rows, grid.cols
    cells = grid.cells

    if rows == 0 or cols == 0:
        return

    r = self.symphony_scan_row % rows
    scale = SCALE_NAMES[self.symphony_scale_idx]
    timbre = TIMBRE_NAMES[self.symphony_timbre_idx]

    # Build voices from alive cells in current scan row
    voices = []
    for c in range(cols):
        if cells[r][c] > 0:
            freq = _col_to_freq(c, cols, scale, self.symphony_octave_range)
            # Neighbor count shapes harmonic richness
            nbrs = _neighbor_count(cells, r, c, rows, cols)
            # Cell age shapes amplitude (older = louder, up to a cap)
            age = min(cells[r][c], 10)
            amp_scale = 0.4 + 0.6 * (age / 10.0)
            voices.append((freq, amp_scale, nbrs))

    self.symphony_last_voices = voices

    # Play audio
    if voices and not self.symphony_muted and hasattr(self, 'sound') and self.sound:
        beat_duration = 60.0 / self.symphony_bpm
        duration = max(0.05, min(beat_duration * 0.8, 2.0))

        samples = _synthesize_symphony(
            voices[:MAX_VOICES], duration, self.symphony_volume, timbre
        )

        sound = self.sound
        if sound._play_cmd and not (sound._play_thread and sound._play_thread.is_alive()):
            sound._stop_event.clear()
            sound._play_thread = threading.Thread(
                target=sound._play_samples, args=(samples,), daemon=True
            )
            sound._play_thread.start()

    # Advance scan row
    self.symphony_scan_row = (r + 1) % rows

    # Step the CA every full scan cycle
    if self.symphony_scan_row == 0:
        grid.step()
        self.symphony_gen_count += 1


def _symphony_step(self):
    """Auto-step: advance sequencer row at the BPM tempo."""
    now = time.time()
    beat_interval = 60.0 / self.symphony_bpm
    if now - self.symphony_last_step_time >= beat_interval:
        self.symphony_last_step_time = now
        _symphony_advance_row(self)


def _draw_symphony(self):
    """Render the Cellular Symphony display."""
    win = self.stdscr
    win.erase()
    max_h, max_w = win.getmaxyx()
    if max_h < 5 or max_w < 20:
        return

    grid = self.grid
    rows, cols = grid.rows, grid.cols
    cells = grid.cells
    scan_row = self.symphony_scan_row % rows if rows > 0 else 0
    scale = SCALE_NAMES[self.symphony_scale_idx]
    timbre = TIMBRE_NAMES[self.symphony_timbre_idx]
    preset = RULE_PRESETS[self.symphony_rule_idx]

    # ── Header ──
    status = "PLAYING" if self.symphony_running else "PAUSED"
    mute_str = " [MUTED]" if self.symphony_muted else ""
    header = f" Cellular Symphony  |  {status}{mute_str}  |  {preset['name']} ({preset['character']})"
    try:
        win.addnstr(0, 0, header, max_w - 1, curses.A_BOLD | curses.A_REVERSE)
        win.addnstr(0, len(header), " " * (max_w - len(header) - 1), max_w - len(header) - 1, curses.A_REVERSE)
    except curses.error:
        pass

    # ── Parameters bar ──
    params = (f" Scale: {scale}  Timbre: {timbre}  "
              f"Octaves: {self.symphony_octave_range}  "
              f"BPM: {self.symphony_bpm}  Vol: {int(self.symphony_volume * 100)}%  "
              f"Gen: {self.symphony_gen_count}")
    try:
        win.addnstr(1, 0, params, max_w - 1, curses.A_DIM)
    except curses.error:
        pass

    # ── Grid display area ──
    grid_top = 2
    grid_bottom = max_h - 2
    avail_rows = grid_bottom - grid_top
    avail_cols = (max_w - 1) // 2  # 2 chars per cell

    # Determine visible portion of grid
    vis_rows = min(rows, avail_rows)
    vis_cols = min(cols, avail_cols)

    # Center the scan row in view if grid is larger than screen
    if rows > avail_rows:
        start_r = max(0, min(scan_row - avail_rows // 2, rows - avail_rows))
    else:
        start_r = 0

    start_c = 0
    if cols > avail_cols:
        start_c = max(0, (cols - avail_cols) // 2)

    # Color pairs — use what's available
    try:
        curses.init_pair(60, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(61, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(62, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(63, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(64, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(65, curses.COLOR_BLACK, curses.COLOR_GREEN)   # scan row highlight
        curses.init_pair(66, curses.COLOR_WHITE, curses.COLOR_BLUE)    # scan row alive
        curses.init_pair(67, curses.COLOR_BLACK, curses.COLOR_WHITE)   # painting cursor
    except curses.error:
        pass

    age_colors = [
        curses.color_pair(60),  # green - newborn
        curses.color_pair(61),  # cyan - young
        curses.color_pair(62),  # yellow - mature
        curses.color_pair(63),  # magenta - old
        curses.color_pair(64),  # red - ancient
    ]

    for vi in range(vis_rows):
        r = start_r + vi
        y = grid_top + vi
        if y >= grid_bottom:
            break
        is_scan = (r == scan_row)

        for vc in range(vis_cols):
            c = start_c + vc
            x = vc * 2
            if x + 1 >= max_w:
                break

            alive = cells[r][c] > 0
            age = cells[r][c]

            # Determine character and color
            if is_scan:
                if alive:
                    ch = "██"
                    attr = curses.color_pair(66) | curses.A_BOLD
                else:
                    ch = "░░"
                    attr = curses.color_pair(65)
            elif alive:
                ch = "██"
                age_idx = min(age - 1, len(age_colors) - 1) if age > 0 else 0
                attr = age_colors[age_idx]
            else:
                ch = "  "
                attr = 0

            # Painting cursor overlay
            if (self.symphony_painting and hasattr(self, 'cursor_r')
                    and hasattr(self, 'cursor_c')
                    and r == self.cursor_r and c == self.cursor_c):
                ch = "▒▒"
                attr = curses.color_pair(67) | curses.A_BLINK

            try:
                win.addstr(y, x, ch, attr)
            except curses.error:
                pass

    # ── Sequencer position indicator (left margin) ──
    for vi in range(vis_rows):
        r = start_r + vi
        y = grid_top + vi
        if r == scan_row:
            try:
                win.addstr(y, max(0, vis_cols * 2), "◄", curses.A_BOLD)
            except curses.error:
                pass
            break

    # ── Voice activity meter (bottom) ──
    voice_count = len(self.symphony_last_voices)
    meter_chars = "▁▂▃▄▅▆▇█"
    bar = ""
    if voice_count > 0:
        level = min(voice_count, MAX_VOICES)
        filled = int(level * 16 / MAX_VOICES)
        for i in range(16):
            if i < filled:
                idx = min(i * len(meter_chars) // 16, len(meter_chars) - 1)
                bar += meter_chars[idx]
            else:
                bar += " "

    footer = f" Voices: {voice_count:2d}/{MAX_VOICES}  [{bar}]  Row: {scan_row}/{rows}"
    if self.symphony_painting:
        cr = getattr(self, 'cursor_r', 0)
        cc = getattr(self, 'cursor_c', 0)
        footer += f"  Paint@({cr},{cc})"
    try:
        win.addnstr(max_h - 2, 0, footer, max_w - 1)
    except curses.error:
        pass

    # ── Help overlay ──
    if self.symphony_show_help:
        help_lines = [
            "═══ Cellular Symphony ═══",
            "",
            " Space  Play/Pause     Enter  Step one row",
            " s      Cycle scale    t      Cycle timbre",
            " o      Cycle octaves  +/-    Adjust BPM",
            " v/V    Volume up/dn   m      Mute toggle",
            " Tab    Cycle CA rule  r      Randomize",
            " c      Clear grid     p      Paint mode",
            " h      Toggle help    q/Esc  Exit",
            "",
            " In paint mode: arrows move, x toggles cell",
        ]
        box_w = max(len(l) for l in help_lines) + 4
        box_h = len(help_lines) + 2
        box_y = max(0, (max_h - box_h) // 2)
        box_x = max(0, (max_w - box_w) // 2)

        for i in range(box_h):
            y = box_y + i
            if y >= max_h - 1:
                break
            line = ""
            if i == 0:
                line = "╔" + "═" * (box_w - 2) + "╗"
            elif i == box_h - 1:
                line = "╚" + "═" * (box_w - 2) + "╝"
            else:
                content = help_lines[i - 1] if i - 1 < len(help_lines) else ""
                line = "║ " + content.ljust(box_w - 4) + " ║"
            try:
                win.addnstr(y, box_x, line, max_w - box_x - 1, curses.A_BOLD)
            except curses.error:
                pass

    try:
        win.noutrefresh()
    except curses.error:
        pass


# ── Registration ───────────────────────────────────────────────────────────

def register(App):
    """Attach Cellular Symphony mode methods to the App class."""
    App._enter_symphony_mode = _enter_symphony_mode
    App._exit_symphony_mode = _exit_symphony_mode
    App._handle_symphony_key = _handle_symphony_key
    App._draw_symphony = _draw_symphony
    App._symphony_step = _symphony_step
    App._is_symphony_auto_stepping = _is_symphony_auto_stepping
