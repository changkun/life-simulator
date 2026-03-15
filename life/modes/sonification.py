"""Simulation Sonification Layer — maps any running simulation's visual state to procedural audio.

A horizontal feature (like time-travel) that analyzes each frame's state and maps
metrics (density, activity, entropy, center of mass, symmetry) to audio parameters
(pitch, tempo, harmonics, stereo panning). Different simulation categories get
tailored audio profiles for a synesthetic experience across all modes.
"""
import math
import struct
import threading
import subprocess
import tempfile
import wave

from life.registry import MODE_REGISTRY, MODE_CATEGORIES

# ── Audio profiles per category ─────────────────────────────────────────────

# Maps category name → audio profile dict
# Each profile controls: base_freq, scale, waveform mix, tempo_mult, drone level
_AUDIO_PROFILES = {
    "Classic CA": {
        "base_freq": 220.0,
        "scale": [0, 2, 4, 7, 9],  # pentatonic
        "wave_mix": (1.0, 0.0, 0.0),  # (sine, saw, pulse)
        "tempo_mult": 1.0,
        "drone": 0.0,
    },
    "Particle & Swarm": {
        "base_freq": 330.0,
        "scale": [0, 2, 3, 5, 7, 10],  # minor pentatonic + b7
        "wave_mix": (0.3, 0.0, 0.7),  # percussive clicks
        "tempo_mult": 1.5,
        "drone": 0.0,
    },
    "Physics & Waves": {
        "base_freq": 196.0,
        "scale": [0, 2, 4, 5, 7, 9, 11],  # major scale
        "wave_mix": (0.8, 0.2, 0.0),
        "tempo_mult": 0.8,
        "drone": 0.3,
    },
    "Fluid Dynamics": {
        "base_freq": 110.0,
        "scale": [0, 2, 3, 7, 8],  # japanese (in-sen)
        "wave_mix": (0.6, 0.4, 0.0),  # flowing drones
        "tempo_mult": 0.6,
        "drone": 0.5,
    },
    "Chemical & Biological": {
        "base_freq": 261.6,
        "scale": [0, 1, 4, 5, 7, 8, 11],  # harmonic minor
        "wave_mix": (0.7, 0.3, 0.0),
        "tempo_mult": 0.9,
        "drone": 0.2,
    },
    "Game Theory & Social": {
        "base_freq": 293.7,
        "scale": [0, 2, 4, 7, 9],  # pentatonic
        "wave_mix": (0.5, 0.5, 0.0),
        "tempo_mult": 1.0,
        "drone": 0.1,
    },
    "Fractals & Chaos": {
        "base_freq": 174.6,
        "scale": [0, 1, 3, 6, 7, 9, 10],  # whole-tone-ish
        "wave_mix": (0.4, 0.3, 0.3),  # evolving harmonics
        "tempo_mult": 0.7,
        "drone": 0.4,
    },
    "Procedural & Computational": {
        "base_freq": 246.9,
        "scale": [0, 2, 4, 6, 8, 10],  # whole tone
        "wave_mix": (0.5, 0.2, 0.3),
        "tempo_mult": 1.2,
        "drone": 0.1,
    },
    "Complex Simulations": {
        "base_freq": 220.0,
        "scale": [0, 3, 5, 7, 10],  # minor pentatonic
        "wave_mix": (0.6, 0.2, 0.2),
        "tempo_mult": 1.0,
        "drone": 0.2,
    },
    "Meta Modes": {
        "base_freq": 220.0,
        "scale": [0, 2, 4, 7, 9],  # pentatonic
        "wave_mix": (1.0, 0.0, 0.0),
        "tempo_mult": 1.0,
        "drone": 0.0,
    },
    "Audio & Visual": {
        "base_freq": 196.0,
        "scale": [0, 4, 7, 11, 14],  # major 9th arpeggio
        "wave_mix": (0.7, 0.2, 0.1),
        "tempo_mult": 0.8,
        "drone": 0.3,
    },
    "Physics & Math": {
        "base_freq": 220.0,
        "scale": [0, 2, 4, 5, 7, 9, 11],
        "wave_mix": (0.6, 0.3, 0.1),
        "tempo_mult": 0.9,
        "drone": 0.2,
    },
}

_DEFAULT_PROFILE = _AUDIO_PROFILES["Classic CA"]

SAMPLE_RATE = 22050
MAX_POLYPHONY = 16


# ── Build category lookup from registry ──────────────────────────────────────

def _build_category_map():
    """Map mode attr → category name."""
    m = {}
    for entry in MODE_REGISTRY:
        attr = entry.get("attr")
        cat = entry.get("category")
        if attr and cat:
            m[attr] = cat
    return m

_CATEGORY_MAP = _build_category_map()


# ── Frame metrics extraction ─────────────────────────────────────────────────

def _extract_metrics(self):
    """Extract visual metrics from the current frame of the active mode.

    Returns dict with: density, activity, entropy, center_x, center_y,
    symmetry, profile (audio profile dict), rows, cols.
    Returns None if no suitable mode/data is found.
    """
    # Try to detect active mode
    prefix = None
    mode_attr = None
    for entry in MODE_REGISTRY:
        attr = entry.get("attr")
        if not attr:
            continue
        if getattr(self, attr, False):
            prefix = attr.rsplit("_mode", 1)[0]
            mode_attr = attr
            break

    category = _CATEGORY_MAP.get(mode_attr, "Classic CA") if mode_attr else "Classic CA"
    profile = _AUDIO_PROFILES.get(category, _DEFAULT_PROFILE)

    # Determine the data source — try mode-specific state, fall back to grid
    rows = cols = 0
    density = 0.0
    activity = 0.0
    cx = cy = 0.5
    entropy = 0.0
    symmetry = 0.5

    if prefix:
        # Try mode-specific grid/state arrays
        data = _extract_mode_data(self, prefix)
        if data:
            rows, cols, density, activity, cx, cy, entropy, symmetry = data
        elif hasattr(self, 'grid') and self.grid:
            rows, cols, density, activity, cx, cy, entropy, symmetry = _extract_grid_data(self.grid)
        else:
            return None
    elif hasattr(self, 'grid') and self.grid:
        # Base GoL mode
        rows, cols, density, activity, cx, cy, entropy, symmetry = _extract_grid_data(self.grid)
    else:
        return None

    return {
        "density": density,
        "activity": activity,
        "entropy": entropy,
        "center_x": cx,
        "center_y": cy,
        "symmetry": symmetry,
        "profile": profile,
        "rows": rows,
        "cols": cols,
    }


def _extract_grid_data(grid):
    """Extract metrics from a standard Grid object."""
    rows = grid.rows
    cols = grid.cols
    cells = grid.cells
    total = rows * cols
    if total == 0:
        return rows, cols, 0, 0, 0.5, 0.5, 0, 0.5

    alive = 0
    sum_x = 0.0
    sum_y = 0.0
    col_counts = [0] * cols
    row_counts = [0] * rows

    for r in range(rows):
        for c in range(cols):
            if cells[r][c] > 0:
                alive += 1
                sum_x += c
                sum_y += r
                col_counts[c] += 1
                row_counts[r] += 1

    density = alive / total if total > 0 else 0

    # Center of mass (normalized 0-1)
    if alive > 0:
        cx = (sum_x / alive) / cols
        cy = (sum_y / alive) / rows
    else:
        cx = cy = 0.5

    # Spatial entropy (row distribution)
    entropy = 0.0
    if alive > 0:
        for rc in row_counts:
            if rc > 0:
                p = rc / alive
                entropy -= p * math.log2(p)
        max_entropy = math.log2(rows) if rows > 1 else 1.0
        entropy = entropy / max_entropy  # normalize to 0-1

    # Horizontal symmetry score
    sym_match = 0
    sym_total = 0
    half = cols // 2
    for r in range(rows):
        for c in range(half):
            sym_total += 1
            a = 1 if cells[r][c] > 0 else 0
            b = 1 if cells[r][cols - 1 - c] > 0 else 0
            if a == b:
                sym_match += 1
    symmetry = sym_match / sym_total if sym_total > 0 else 0.5

    # Activity: estimate from density variation (proxy)
    activity = min(1.0, density * 4)  # more alive = more active

    return rows, cols, density, activity, cx, cy, entropy, symmetry


def _extract_mode_data(self, prefix):
    """Try to extract metrics from a mode's internal state.

    Looks for common attribute patterns across modes.
    Returns (rows, cols, density, activity, cx, cy, entropy, symmetry) or None.
    """
    # Try to find grid-like data in the mode's state
    rows_attr = f"{prefix}_rows"
    cols_attr = f"{prefix}_cols"

    r = getattr(self, rows_attr, 0)
    c = getattr(self, cols_attr, 0)

    if not r or not c:
        # Fall back to grid if mode doesn't store dimensions
        if hasattr(self, 'grid') and self.grid:
            return _extract_grid_data(self.grid)
        return None

    total = r * c
    if total == 0:
        return r, c, 0, 0, 0.5, 0.5, 0, 0.5

    # Look for a cells/grid/state array
    cells = None
    for suffix in ("_cells", "_grid", "_state", "_field", "_data"):
        cells = getattr(self, f"{prefix}{suffix}", None)
        if cells is not None:
            break

    # Check for particle-based modes
    particles = getattr(self, f"{prefix}_particles", None)

    if cells is not None and isinstance(cells, list) and len(cells) > 0:
        return _analyze_2d_array(cells, r, c)
    elif particles is not None and isinstance(particles, list):
        return _analyze_particles(particles, r, c)

    # Fall back to grid
    if hasattr(self, 'grid') and self.grid:
        return _extract_grid_data(self.grid)
    return None


def _analyze_2d_array(cells, rows, cols):
    """Analyze a 2D list-of-lists for audio metrics."""
    total = rows * cols
    alive = 0
    sum_x = 0.0
    sum_y = 0.0
    row_counts = [0] * rows

    actual_rows = min(rows, len(cells))
    for r in range(actual_rows):
        if not isinstance(cells[r], (list, tuple)):
            continue
        actual_cols = min(cols, len(cells[r]))
        for c in range(actual_cols):
            val = cells[r][c]
            if isinstance(val, (int, float)) and val > 0:
                alive += 1
                sum_x += c
                sum_y += r
                row_counts[r] += 1

    density = alive / total if total > 0 else 0
    if alive > 0:
        cx = (sum_x / alive) / cols
        cy = (sum_y / alive) / rows
    else:
        cx = cy = 0.5

    entropy = 0.0
    if alive > 0:
        for rc in row_counts:
            if rc > 0:
                p = rc / alive
                entropy -= p * math.log2(p)
        max_e = math.log2(rows) if rows > 1 else 1.0
        entropy = entropy / max_e

    activity = min(1.0, density * 4)
    symmetry = 0.5  # simplified for non-grid modes
    return rows, cols, density, activity, cx, cy, entropy, symmetry


def _analyze_particles(particles, rows, cols):
    """Analyze a particle list for audio metrics."""
    n = len(particles)
    if n == 0:
        return rows, cols, 0, 0, 0.5, 0.5, 0, 0.5

    density = min(1.0, n / (rows * cols)) if rows * cols > 0 else 0
    sum_x = 0.0
    sum_y = 0.0
    sum_vx = 0.0
    sum_vy = 0.0

    for p in particles:
        if isinstance(p, dict):
            sum_x += p.get("x", 0)
            sum_y += p.get("y", 0)
            sum_vx += abs(p.get("vx", 0))
            sum_vy += abs(p.get("vy", 0))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            sum_x += p[0]
            sum_y += p[1]

    cx = (sum_x / n) / cols if cols > 0 else 0.5
    cy = (sum_y / n) / rows if rows > 0 else 0.5
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))

    # Activity from average velocity
    avg_v = (sum_vx + sum_vy) / (2 * n) if n > 0 else 0
    activity = min(1.0, avg_v * 0.5)

    entropy = 0.5  # approximate for particles
    symmetry = 0.5
    return rows, cols, density, activity, cx, cy, entropy, symmetry


# ── Synthesis ────────────────────────────────────────────────────────────────

def _metrics_to_freqs(metrics):
    """Convert frame metrics to a list of frequencies using the mode's audio profile."""
    profile = metrics["profile"]
    base = profile["base_freq"]
    scale = profile["scale"]
    density = metrics["density"]
    entropy = metrics["entropy"]
    symmetry = metrics["symmetry"]
    cy = metrics["center_y"]

    freqs = []

    # Base tone: pitch follows center of mass (higher when mass is at top)
    pitch_shift = (1.0 - cy) * 12  # up to 12 semitones up
    base_note = base * (2.0 ** (pitch_shift / 12.0))

    # Number of harmonics from entropy (more entropy = richer harmonics)
    n_voices = max(1, min(MAX_POLYPHONY, int(2 + entropy * 6 + density * 8)))

    for i in range(n_voices):
        octave, degree = divmod(i, len(scale))
        semitones = octave * 12 + scale[degree]
        freq = base_note * (2.0 ** (semitones / 12.0))
        # Keep in audible range
        if freq < 80:
            freq *= 2
        if freq > 4000:
            freq /= 2
        freqs.append(freq)

    return freqs


def _sonify_synthesize(metrics, duration):
    """Synthesize audio from frame metrics. Returns PCM bytes (S16LE stereo)."""
    profile = metrics["profile"]
    sine_w, saw_w, pulse_w = profile["wave_mix"]
    drone_level = profile["drone"]
    density = metrics["density"]
    activity = metrics["activity"]
    symmetry = metrics["symmetry"]
    cx = metrics["center_x"]

    freqs = _metrics_to_freqs(metrics)
    if not freqs:
        return b""

    n_samples = max(1, int(SAMPLE_RATE * duration))
    master_vol = 0.1 + 0.6 * density  # quieter than old sound engine
    amp_per_voice = master_vol / len(freqs)
    max_amp = 24000

    # Stereo panning from center of mass X
    pan = max(0.0, min(1.0, cx))  # 0=left, 1=right
    left_gain = math.cos(pan * math.pi / 2)
    right_gain = math.sin(pan * math.pi / 2)

    # Pre-compute phase increments
    increments = [2.0 * math.pi * f / SAMPLE_RATE for f in freqs]

    # Drone: low continuous tone
    drone_freq = profile["base_freq"] * 0.5
    drone_inc = 2.0 * math.pi * drone_freq / SAMPLE_RATE

    # Envelope: soft attack/release (5ms ramp)
    ramp = min(int(0.005 * SAMPLE_RATE), n_samples // 2)

    # Stereo buffer (interleaved L R)
    buf = bytearray(n_samples * 4)  # 2 bytes * 2 channels

    for i in range(n_samples):
        # Envelope
        if i < ramp:
            env = i / ramp
        elif i > n_samples - ramp:
            env = (n_samples - i) / ramp
        else:
            env = 1.0

        val = 0.0
        for inc in increments:
            phase = (inc * i) % (2.0 * math.pi)
            # Mix waveforms
            s = 0.0
            if sine_w > 0:
                s += sine_w * math.sin(phase)
            if saw_w > 0:
                s += saw_w * (2.0 * (phase / (2.0 * math.pi)) - 1.0)
            if pulse_w > 0:
                s += pulse_w * (1.0 if phase < math.pi * (0.3 + 0.4 * symmetry) else -1.0)
            val += s

        val *= amp_per_voice

        # Add drone
        if drone_level > 0:
            drone_val = drone_level * 0.5 * math.sin(drone_inc * i)
            val += drone_val

        val = val * max_amp * env
        sample_val = max(-32767, min(32767, int(val)))

        left = max(-32767, min(32767, int(sample_val * left_gain)))
        right = max(-32767, min(32767, int(sample_val * right_gain)))
        struct.pack_into("<hh", buf, i * 4, left, right)

    return bytes(buf)


# ── Playback ─────────────────────────────────────────────────────────────────

def _sonify_detect_player():
    """Find stereo-capable audio playback command."""
    import shutil
    for cmd, args in [
        ("paplay", ["paplay", "--raw", "--rate=22050", "--channels=2",
                     "--format=s16le"]),
        ("aplay", ["aplay", "-q", "-f", "S16_LE", "-r", "22050", "-c", "2"]),
        ("afplay", None),
    ]:
        if shutil.which(cmd):
            return args
    return None


def _sonify_play(samples, play_cmd, stop_event):
    """Play stereo PCM samples via detected player (runs in thread)."""
    if not play_cmd or not samples:
        return
    try:
        if play_cmd[0] == "afplay":
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
                with wave.open(tmp.name, "wb") as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(samples)
                subprocess.run(["afplay", tmp.name],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               timeout=5)
        else:
            proc = subprocess.Popen(
                play_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proc.communicate(input=samples, timeout=5)
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass


# ── Main sonification hook (called each frame) ──────────────────────────────

def _sonify_frame(self):
    """Analyze current frame and play sonified audio. Called each main-loop iteration."""
    if not self.sonify_enabled:
        return

    if self.sonify_play_cmd is None:
        return

    # Don't stack threads
    if self._sonify_thread and self._sonify_thread.is_alive():
        return

    # Check if any mode is actually running
    is_running = self.running  # GoL
    if not is_running:
        prefix = getattr(self, '_tt_get_active_mode_prefix', lambda: None)()
        if prefix:
            running_attr = f"{prefix}_running"
            is_running = getattr(self, running_attr, False)
    if not is_running:
        return

    metrics = _extract_metrics(self)
    if metrics is None:
        return

    # Duration: based on simulation speed
    from life.constants import SPEEDS
    delay = SPEEDS[self.speed_idx]
    tempo_mult = metrics["profile"]["tempo_mult"]
    duration = max(0.04, min(delay * 0.8 * tempo_mult, 1.5))

    samples = _sonify_synthesize(metrics, duration)
    if not samples:
        return

    self._sonify_stop.clear()
    self._sonify_thread = threading.Thread(
        target=_sonify_play,
        args=(samples, self.sonify_play_cmd, self._sonify_stop),
        daemon=True,
    )
    self._sonify_thread.start()


# ── Toggle & status ──────────────────────────────────────────────────────────

def _sonify_toggle(self):
    """Toggle sonification on/off. Returns new state."""
    self.sonify_enabled = not self.sonify_enabled
    if not self.sonify_enabled:
        self._sonify_stop.set()
    return self.sonify_enabled


def _draw_sonify_indicator(self, max_y, max_x):
    """Draw a small sonification status indicator at the bottom of the screen."""
    import curses
    if not self.sonify_enabled:
        return

    # Get current metrics for a mini-visualization
    label = " SONIFY "
    y = max_y - 2 if self.tt_history else max_y - 1
    if y <= 0:
        return

    # Show active category
    prefix = getattr(self, '_tt_get_active_mode_prefix', lambda: None)()
    mode_attr = f"{prefix}_mode" if prefix else None
    category = _CATEGORY_MAP.get(mode_attr, "Classic CA") if mode_attr else "Classic CA"
    profile_name = category[:20]

    indicator = f" {label} [{profile_name}] "
    x = max(0, max_x - len(indicator) - 1)

    try:
        self.stdscr.addstr(y, x, indicator, curses.color_pair(3) | curses.A_BOLD)
    except curses.error:
        pass


# ── Registration ─────────────────────────────────────────────────────────────

def register(App):
    """Register sonification methods on the App class."""
    # Class-level shared state (safe to share)
    App.sonify_play_cmd = _sonify_detect_player()

    # Methods
    App._sonify_frame = _sonify_frame
    App._sonify_toggle = _sonify_toggle
    App._draw_sonify_indicator = _draw_sonify_indicator
    App._sonify_extract_metrics = _extract_metrics
