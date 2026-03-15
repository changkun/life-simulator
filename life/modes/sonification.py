"""Procedural Music / Generative Soundscape — cross-cutting sonification layer.

A horizontal feature that attaches to *any* running simulation and turns it into
a listenable composition in real-time. Maps:
  - Cell density   → harmony (chord voicings, root motion)
  - Spatial patterns → melody (column profiles become arpeggiated sequences)
  - Entropy        → rhythm (gate patterns, subdivisions, accents)
  - Rate of change → dynamics (volume swells, timbre shifts)
  - Symmetry       → stereo field & pulse-width modulation
  - Center of mass → pitch register & panning

Multi-voice synthesis engine with four layers:
  Bass   — deep root note following harmonic progression
  Melody — arpeggiated sequence extracted from spatial column profile
  Harmony — sustained chord pad from density & symmetry
  Rhythm — percussive noise bursts gated by entropy-driven patterns

Frame-to-frame state enables musical continuity: portamento between pitches,
smooth dynamic transitions, and evolving rhythmic patterns.
"""
import math
import random
import struct
import threading
import subprocess
import tempfile
import wave

from life.registry import MODE_REGISTRY, MODE_CATEGORIES

# ── Audio profiles per category ─────────────────────────────────────────────

# Maps category name → audio profile dict
# Each profile controls: base_freq, scale, waveform mix, tempo_mult, drone level,
# plus new: melody_mode, rhythm_feel, harmonic_character
_AUDIO_PROFILES = {
    "Classic CA": {
        "base_freq": 220.0,
        "scale": [0, 2, 4, 7, 9],  # pentatonic
        "wave_mix": (1.0, 0.0, 0.0),  # (sine, saw, pulse)
        "tempo_mult": 1.0,
        "drone": 0.0,
        "melody_mode": "arpeggio",
        "rhythm_feel": "pulse",
        "swing": 0.0,
    },
    "Particle & Swarm": {
        "base_freq": 330.0,
        "scale": [0, 2, 3, 5, 7, 10],  # minor pentatonic + b7
        "wave_mix": (0.3, 0.0, 0.7),  # percussive clicks
        "tempo_mult": 1.5,
        "drone": 0.0,
        "melody_mode": "scatter",
        "rhythm_feel": "staccato",
        "swing": 0.1,
    },
    "Physics & Waves": {
        "base_freq": 196.0,
        "scale": [0, 2, 4, 5, 7, 9, 11],  # major scale
        "wave_mix": (0.8, 0.2, 0.0),
        "tempo_mult": 0.8,
        "drone": 0.3,
        "melody_mode": "wave",
        "rhythm_feel": "legato",
        "swing": 0.0,
    },
    "Fluid Dynamics": {
        "base_freq": 110.0,
        "scale": [0, 2, 3, 7, 8],  # japanese (in-sen)
        "wave_mix": (0.6, 0.4, 0.0),  # flowing drones
        "tempo_mult": 0.6,
        "drone": 0.5,
        "melody_mode": "glide",
        "rhythm_feel": "ambient",
        "swing": 0.0,
    },
    "Chemical & Biological": {
        "base_freq": 261.6,
        "scale": [0, 1, 4, 5, 7, 8, 11],  # harmonic minor
        "wave_mix": (0.7, 0.3, 0.0),
        "tempo_mult": 0.9,
        "drone": 0.2,
        "melody_mode": "arpeggio",
        "rhythm_feel": "organic",
        "swing": 0.15,
    },
    "Game Theory & Social": {
        "base_freq": 293.7,
        "scale": [0, 2, 4, 7, 9],  # pentatonic
        "wave_mix": (0.5, 0.5, 0.0),
        "tempo_mult": 1.0,
        "drone": 0.1,
        "melody_mode": "call_response",
        "rhythm_feel": "pulse",
        "swing": 0.05,
    },
    "Fractals & Chaos": {
        "base_freq": 174.6,
        "scale": [0, 1, 3, 6, 7, 9, 10],  # whole-tone-ish
        "wave_mix": (0.4, 0.3, 0.3),  # evolving harmonics
        "tempo_mult": 0.7,
        "drone": 0.4,
        "melody_mode": "fractal",
        "rhythm_feel": "polyrhythm",
        "swing": 0.0,
    },
    "Procedural & Computational": {
        "base_freq": 246.9,
        "scale": [0, 2, 4, 6, 8, 10],  # whole tone
        "wave_mix": (0.5, 0.2, 0.3),
        "tempo_mult": 1.2,
        "drone": 0.1,
        "melody_mode": "sequence",
        "rhythm_feel": "grid",
        "swing": 0.0,
    },
    "Complex Simulations": {
        "base_freq": 220.0,
        "scale": [0, 3, 5, 7, 10],  # minor pentatonic
        "wave_mix": (0.6, 0.2, 0.2),
        "tempo_mult": 1.0,
        "drone": 0.2,
        "melody_mode": "arpeggio",
        "rhythm_feel": "organic",
        "swing": 0.1,
    },
    "Meta Modes": {
        "base_freq": 220.0,
        "scale": [0, 2, 4, 7, 9],  # pentatonic
        "wave_mix": (1.0, 0.0, 0.0),
        "tempo_mult": 1.0,
        "drone": 0.0,
        "melody_mode": "arpeggio",
        "rhythm_feel": "pulse",
        "swing": 0.0,
    },
    "Audio & Visual": {
        "base_freq": 196.0,
        "scale": [0, 4, 7, 11, 14],  # major 9th arpeggio
        "wave_mix": (0.7, 0.2, 0.1),
        "tempo_mult": 0.8,
        "drone": 0.3,
        "melody_mode": "wave",
        "rhythm_feel": "ambient",
        "swing": 0.0,
    },
    "Physics & Math": {
        "base_freq": 220.0,
        "scale": [0, 2, 4, 5, 7, 9, 11],
        "wave_mix": (0.6, 0.3, 0.1),
        "tempo_mult": 0.9,
        "drone": 0.2,
        "melody_mode": "wave",
        "rhythm_feel": "pulse",
        "swing": 0.0,
    },
}

_DEFAULT_PROFILE = _AUDIO_PROFILES["Classic CA"]

SAMPLE_RATE = 22050
MAX_POLYPHONY = 16

# Rhythm gate patterns: each is a list of 16 step weights (0.0-1.0)
# Higher entropy selects denser patterns
_RHYTHM_PATTERNS = [
    # Sparse (low entropy)
    [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],  # 4-on-floor
    [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],  # minimal
    # Medium
    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],  # 8ths
    [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1],  # tresillo
    [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1],  # clave
    # Dense (high entropy)
    [1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0],  # syncopated
    [1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1],  # busy
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # full
]

# Chord voicing intervals (semitones above root) by density
_CHORD_VOICINGS = {
    "fifth": [0, 7],                     # density < 0.1
    "triad": [0, 4, 7],                  # density < 0.25
    "seventh": [0, 4, 7, 11],            # density < 0.4
    "ninth": [0, 4, 7, 11, 14],          # density < 0.6
    "extended": [0, 2, 4, 7, 9, 11, 14], # density >= 0.6
}

# Root motion intervals for harmonic progression (in semitones)
_ROOT_MOTION = [0, 5, 7, -5, -7, 3, -3, 2, -2]


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
    """Extract rich visual/spatial metrics from the current frame.

    Returns dict with: density, activity, entropy, center_x, center_y,
    symmetry, delta, col_profile, quadrant_densities, cluster_estimate,
    edge_ratio, profile, rows, cols.
    Returns None if no suitable mode/data is found.
    """
    # Detect active mode
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

    # Determine data source
    raw_metrics = None
    if prefix:
        data = _extract_mode_data(self, prefix)
        if data:
            raw_metrics = data
        elif hasattr(self, 'grid') and self.grid:
            raw_metrics = _extract_grid_data(self.grid)
    elif hasattr(self, 'grid') and self.grid:
        raw_metrics = _extract_grid_data(self.grid)

    if raw_metrics is None:
        return None

    rows, cols, density, activity, cx, cy, entropy, symmetry, col_profile, \
        quadrant_densities, edge_ratio = raw_metrics

    # Compute delta (rate of change) from previous frame
    prev_density = getattr(self, '_sonify_prev_density', density)
    delta = abs(density - prev_density)
    self._sonify_prev_density = density

    # Estimate cluster count from column profile transitions
    cluster_est = 0
    if col_profile:
        in_cluster = False
        threshold = 0.05
        for v in col_profile:
            if v > threshold and not in_cluster:
                cluster_est += 1
                in_cluster = True
            elif v <= threshold:
                in_cluster = False

    return {
        "density": density,
        "activity": activity,
        "entropy": entropy,
        "center_x": cx,
        "center_y": cy,
        "symmetry": symmetry,
        "delta": delta,
        "col_profile": col_profile,
        "quadrant_densities": quadrant_densities,
        "cluster_estimate": cluster_est,
        "edge_ratio": edge_ratio,
        "profile": profile,
        "rows": rows,
        "cols": cols,
    }


def _extract_grid_data(grid):
    """Extract rich metrics from a standard Grid object."""
    rows = grid.rows
    cols = grid.cols
    cells = grid.cells
    total = rows * cols
    if total == 0:
        return rows, cols, 0, 0, 0.5, 0.5, 0, 0.5, [], [0, 0, 0, 0], 0

    alive = 0
    sum_x = 0.0
    sum_y = 0.0
    col_counts = [0] * cols
    row_counts = [0] * rows
    # Quadrants: TL, TR, BL, BR
    quad = [0, 0, 0, 0]
    half_r = rows // 2
    half_c = cols // 2
    edge_cells = 0

    for r in range(rows):
        for c in range(cols):
            if cells[r][c] > 0:
                alive += 1
                sum_x += c
                sum_y += r
                col_counts[c] += 1
                row_counts[r] += 1
                # Quadrant
                qi = (0 if r < half_r else 2) + (0 if c < half_c else 1)
                quad[qi] += 1
                # Edge detection: cell alive but has at least one dead neighbor
                has_dead = False
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if cells[nr][nc] == 0:
                            has_dead = True
                            break
                    else:
                        has_dead = True
                        break
                if has_dead:
                    edge_cells += 1

    density = alive / total
    edge_ratio = edge_cells / alive if alive > 0 else 0

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
        entropy = entropy / max_entropy

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

    activity = min(1.0, density * 4)

    # Column profile (normalized density per column)
    col_profile = [cc / rows for cc in col_counts] if rows > 0 else []

    # Quadrant densities (normalized)
    q_total = half_r * half_c if half_r > 0 and half_c > 0 else 1
    quadrant_densities = [q / q_total for q in quad]

    return rows, cols, density, activity, cx, cy, entropy, symmetry, \
        col_profile, quadrant_densities, edge_ratio


def _extract_mode_data(self, prefix):
    """Try to extract metrics from a mode's internal state."""
    rows_attr = f"{prefix}_rows"
    cols_attr = f"{prefix}_cols"

    r = getattr(self, rows_attr, 0)
    c = getattr(self, cols_attr, 0)

    if not r or not c:
        if hasattr(self, 'grid') and self.grid:
            return _extract_grid_data(self.grid)
        return None

    total = r * c
    if total == 0:
        return r, c, 0, 0, 0.5, 0.5, 0, 0.5, [], [0, 0, 0, 0], 0

    cells = None
    for suffix in ("_cells", "_grid", "_state", "_field", "_data"):
        cells = getattr(self, f"{prefix}{suffix}", None)
        if cells is not None:
            break

    particles = getattr(self, f"{prefix}_particles", None)

    if cells is not None and isinstance(cells, list) and len(cells) > 0:
        return _analyze_2d_array(cells, r, c)
    elif particles is not None and isinstance(particles, list):
        return _analyze_particles(particles, r, c)

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
    col_counts = [0] * cols
    quad = [0, 0, 0, 0]
    half_r = rows // 2
    half_c = cols // 2

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
                col_counts[c] += 1
                qi = (0 if r < half_r else 2) + (0 if c < half_c else 1)
                quad[qi] += 1

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
    symmetry = 0.5

    col_profile = [cc / rows for cc in col_counts] if rows > 0 else []
    q_total = half_r * half_c if half_r > 0 and half_c > 0 else 1
    quadrant_densities = [q / q_total for q in quad]
    edge_ratio = 0.5  # approximate for non-grid modes

    return rows, cols, density, activity, cx, cy, entropy, symmetry, \
        col_profile, quadrant_densities, edge_ratio


def _analyze_particles(particles, rows, cols):
    """Analyze a particle list for audio metrics."""
    n = len(particles)
    if n == 0:
        return rows, cols, 0, 0, 0.5, 0.5, 0, 0.5, [], [0, 0, 0, 0], 0

    density = min(1.0, n / (rows * cols)) if rows * cols > 0 else 0
    sum_x = 0.0
    sum_y = 0.0
    sum_vx = 0.0
    sum_vy = 0.0
    col_counts = [0] * cols
    quad = [0, 0, 0, 0]
    half_r = rows // 2
    half_c = cols // 2

    for p in particles:
        if isinstance(p, dict):
            px = p.get("x", 0)
            py = p.get("y", 0)
            sum_x += px
            sum_y += py
            sum_vx += abs(p.get("vx", 0))
            sum_vy += abs(p.get("vy", 0))
            ci = max(0, min(cols - 1, int(px)))
            col_counts[ci] += 1
            qi = (0 if py < half_r else 2) + (0 if px < half_c else 1)
            quad[qi] += 1
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            sum_x += p[0]
            sum_y += p[1]
            ci = max(0, min(cols - 1, int(p[0])))
            col_counts[ci] += 1

    cx = (sum_x / n) / cols if cols > 0 else 0.5
    cy = (sum_y / n) / rows if rows > 0 else 0.5
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))

    avg_v = (sum_vx + sum_vy) / (2 * n) if n > 0 else 0
    activity = min(1.0, avg_v * 0.5)

    entropy = 0.5
    symmetry = 0.5
    col_profile = [cc / max(1, n) for cc in col_counts]
    q_total = max(1, n // 4)
    quadrant_densities = [q / q_total for q in quad]

    return rows, cols, density, activity, cx, cy, entropy, symmetry, \
        col_profile, quadrant_densities, 0.5


# ── Musical structure generation ─────────────────────────────────────────────

def _select_chord_voicing(density):
    """Select chord intervals based on density (sparser = simpler harmony)."""
    if density < 0.05:
        return _CHORD_VOICINGS["fifth"]
    elif density < 0.15:
        return _CHORD_VOICINGS["triad"]
    elif density < 0.3:
        return _CHORD_VOICINGS["seventh"]
    elif density < 0.5:
        return _CHORD_VOICINGS["ninth"]
    else:
        return _CHORD_VOICINGS["extended"]


def _select_rhythm_pattern(entropy):
    """Select rhythm gate pattern based on entropy (more entropy = denser rhythm)."""
    idx = min(len(_RHYTHM_PATTERNS) - 1, int(entropy * len(_RHYTHM_PATTERNS)))
    return _RHYTHM_PATTERNS[idx]


def _extract_melody_notes(col_profile, scale, base_freq, n_notes=8):
    """Extract a melodic sequence from the column density profile.

    Picks the N columns with highest density and maps them to scale degrees,
    ordering by column position (left-to-right) for a spatial melody.
    """
    if not col_profile or not scale:
        return [base_freq]

    # Find peaks in column profile
    indexed = [(i, v) for i, v in enumerate(col_profile) if v > 0.01]
    if not indexed:
        return [base_freq]

    # Sort by density (descending), pick top n_notes
    indexed.sort(key=lambda x: x[1], reverse=True)
    peaks = indexed[:n_notes]
    # Re-sort by column position for spatial ordering
    peaks.sort(key=lambda x: x[0])

    notes = []
    n_cols = len(col_profile)
    for col_idx, col_val in peaks:
        # Map column position to scale degree
        pos = col_idx / n_cols  # 0-1
        degree_idx = int(pos * len(scale) * 2)  # span ~2 octaves
        octave, deg = divmod(degree_idx, len(scale))
        semitones = octave * 12 + scale[deg]
        freq = base_freq * (2.0 ** (semitones / 12.0))
        # Keep audible
        while freq < 120:
            freq *= 2
        while freq > 3000:
            freq /= 2
        notes.append(freq)

    return notes if notes else [base_freq]


def _compute_root_motion(delta, frame_count):
    """Determine root note shift based on rate of change and time.

    Large deltas trigger bigger harmonic jumps (4ths/5ths).
    Small deltas keep the root stable or move by steps.
    """
    if delta < 0.005:
        return 0  # stable
    # Use delta magnitude to index into root motion intervals
    motion_idx = min(len(_ROOT_MOTION) - 1, int(delta * 20))
    # Alternate direction based on frame count for variety
    interval = _ROOT_MOTION[motion_idx]
    if frame_count % 8 < 4:
        return interval
    return -interval


# ── Multi-voice synthesis ────────────────────────────────────────────────────

def _sonify_synthesize(metrics, duration, prev_state):
    """Synthesize multi-voice audio from frame metrics.

    Layers:
      1. Bass   — deep root following harmonic progression
      2. Melody — arpeggiated spatial sequence
      3. Harmony — sustained chord pad
      4. Rhythm — percussive noise gated by entropy pattern

    Returns (PCM bytes S16LE stereo, new_state dict).
    """
    profile = metrics["profile"]
    sine_w, saw_w, pulse_w = profile["wave_mix"]
    drone_level = profile["drone"]
    density = metrics["density"]
    activity = metrics["activity"]
    symmetry = metrics["symmetry"]
    entropy = metrics["entropy"]
    delta = metrics["delta"]
    cx = metrics["center_x"]
    cy = metrics["center_y"]
    col_profile = metrics["col_profile"]
    scale = profile["scale"]
    base_freq = profile["base_freq"]
    swing = profile.get("swing", 0.0)

    frame_count = prev_state.get("frame_count", 0)

    # ── Voice 1: Bass root ──
    root_shift = _compute_root_motion(delta, frame_count)
    prev_root_semi = prev_state.get("root_semitone", 0)
    # Smooth root changes: only apply if shift is non-zero
    new_root_semi = prev_root_semi + root_shift
    # Keep root within ±12 semitones of base
    new_root_semi = max(-12, min(12, new_root_semi))
    bass_freq = base_freq * 0.5 * (2.0 ** (new_root_semi / 12.0))
    # Portamento from previous bass frequency
    prev_bass = prev_state.get("bass_freq", bass_freq)

    # ── Voice 2: Melody (arpeggiated) ──
    n_melody = max(2, min(8, int(2 + activity * 6)))
    melody_notes = _extract_melody_notes(col_profile, scale, base_freq * (2.0 ** (new_root_semi / 12.0)), n_melody)
    # Pitch register follows center of mass Y
    register_shift = (0.5 - cy) * 12  # higher mass position = higher pitch
    melody_notes = [f * (2.0 ** (register_shift / 12.0)) for f in melody_notes]
    prev_melody = prev_state.get("melody_notes", melody_notes)

    # ── Voice 3: Harmony pad ──
    chord_intervals = _select_chord_voicing(density)
    chord_root = base_freq * (2.0 ** (new_root_semi / 12.0))
    harmony_freqs = [chord_root * (2.0 ** (iv / 12.0)) for iv in chord_intervals]

    # ── Voice 4: Rhythm ──
    rhythm_pattern = _select_rhythm_pattern(entropy)

    # ── Synthesis parameters ──
    n_samples = max(1, int(SAMPLE_RATE * duration))
    # Master volume: base level + density boost + delta surge
    master_vol = 0.08 + 0.4 * density + 0.2 * min(1.0, delta * 10)
    max_amp = 24000

    # Voice mix levels
    bass_level = 0.35 + drone_level * 0.15
    melody_level = 0.30 + activity * 0.15
    harmony_level = 0.20 + symmetry * 0.1
    rhythm_level = 0.15 + entropy * 0.15

    # Normalize levels
    total_level = bass_level + melody_level + harmony_level + rhythm_level
    if total_level > 0:
        bass_level /= total_level
        melody_level /= total_level
        harmony_level /= total_level
        rhythm_level /= total_level

    # Stereo panning from center of mass X
    pan = max(0.0, min(1.0, cx))
    left_gain = math.cos(pan * math.pi / 2)
    right_gain = math.sin(pan * math.pi / 2)

    # Melody note timing: divide duration into melody steps
    n_steps = len(melody_notes)
    samples_per_step = n_samples // n_steps if n_steps > 0 else n_samples

    # Rhythm: 16 subdivisions within the frame
    samples_per_sub = n_samples // 16

    # Pre-compute bass phase increment (with portamento)
    bass_inc_start = 2.0 * math.pi * prev_bass / SAMPLE_RATE
    bass_inc_end = 2.0 * math.pi * bass_freq / SAMPLE_RATE

    # Pre-compute harmony increments
    harmony_incs = [2.0 * math.pi * f / SAMPLE_RATE for f in harmony_freqs]

    # Envelope: soft attack/release (8ms ramp for smoother sound)
    ramp = min(int(0.008 * SAMPLE_RATE), n_samples // 2)

    # Vibrato parameters (subtle pitch wobble for organic feel)
    vibrato_rate = 5.0  # Hz
    vibrato_depth = 0.003  # ±0.3% pitch variation
    vibrato_inc = 2.0 * math.pi * vibrato_rate / SAMPLE_RATE

    # Simple noise state for rhythm
    noise_state = prev_state.get("noise_seed", 42)

    # Stereo buffer (interleaved L R)
    buf = bytearray(n_samples * 4)

    for i in range(n_samples):
        # Global envelope
        if i < ramp:
            env = i / ramp
        elif i > n_samples - ramp:
            env = (n_samples - i) / ramp
        else:
            env = 1.0

        # Vibrato modulator
        vib = 1.0 + vibrato_depth * math.sin(vibrato_inc * i)

        # ── Bass voice ──
        # Portamento: interpolate phase increment
        t = i / n_samples
        bass_inc = bass_inc_start + (bass_inc_end - bass_inc_start) * t
        bass_phase = (bass_inc * vib * i) % (2.0 * math.pi)
        # Bass uses sine + slight saw for warmth
        bass_val = 0.8 * math.sin(bass_phase) + 0.2 * (2.0 * (bass_phase / (2.0 * math.pi)) - 1.0)
        bass_val *= bass_level

        # ── Melody voice ──
        # Determine current melody note
        step_idx = min(n_steps - 1, i // samples_per_step) if samples_per_step > 0 else 0
        current_note = melody_notes[step_idx]
        # Smooth transition between melody notes (per-step mini-envelope)
        step_pos = (i % samples_per_step) / samples_per_step if samples_per_step > 0 else 0
        # Portamento between consecutive notes
        if step_idx > 0:
            prev_note = melody_notes[step_idx - 1]
            blend = min(1.0, step_pos * 4)  # fast glide in first 25% of step
            note_freq = prev_note + (current_note - prev_note) * blend
        else:
            # Blend from previous frame's last note
            if prev_melody:
                prev_note = prev_melody[-1]
                blend = min(1.0, step_pos * 4)
                note_freq = prev_note + (current_note - prev_note) * blend
            else:
                note_freq = current_note

        mel_inc = 2.0 * math.pi * note_freq * vib / SAMPLE_RATE
        mel_phase = (mel_inc * i) % (2.0 * math.pi)
        # Per-step envelope: gentle attack/decay for each note
        step_env = 1.0
        step_ramp = min(int(0.003 * SAMPLE_RATE), samples_per_step // 4) if samples_per_step > 4 else 1
        step_i = i % samples_per_step if samples_per_step > 0 else 0
        if step_i < step_ramp:
            step_env = step_i / step_ramp
        elif step_i > samples_per_step - step_ramp and samples_per_step > step_ramp:
            step_env = (samples_per_step - step_i) / step_ramp

        # Mix waveforms per profile
        mel_s = 0.0
        if sine_w > 0:
            mel_s += sine_w * math.sin(mel_phase)
        if saw_w > 0:
            mel_s += saw_w * (2.0 * (mel_phase / (2.0 * math.pi)) - 1.0)
        if pulse_w > 0:
            pw = 0.3 + 0.4 * symmetry  # pulse width from symmetry
            mel_s += pulse_w * (1.0 if mel_phase < math.pi * 2 * pw else -1.0)
        mel_val = mel_s * step_env * melody_level

        # ── Harmony pad voice ──
        harm_val = 0.0
        for h_inc in harmony_incs:
            h_phase = (h_inc * vib * i) % (2.0 * math.pi)
            # Soft sine pad
            harm_val += math.sin(h_phase)
        if harmony_incs:
            harm_val /= len(harmony_incs)
        harm_val *= harmony_level

        # ── Rhythm voice ──
        sub_idx = min(15, i // samples_per_sub) if samples_per_sub > 0 else 0
        gate = rhythm_pattern[sub_idx]

        rhythm_val = 0.0
        if gate > 0:
            # Noise burst with sharp envelope
            sub_pos = (i % samples_per_sub) / samples_per_sub if samples_per_sub > 0 else 0
            # Apply swing to even-numbered subdivisions
            burst_env = max(0.0, 1.0 - sub_pos * 4)  # fast decay
            burst_env *= gate
            # Simple noise via LCG
            noise_state = (noise_state * 1103515245 + 12345) & 0x7FFFFFFF
            noise_val = (noise_state / 0x7FFFFFFF) * 2.0 - 1.0
            # Filtered noise: blend with sine for tonal percussion
            perc_freq = base_freq * 4  # high pitched click
            perc_phase = (2.0 * math.pi * perc_freq / SAMPLE_RATE * i) % (2.0 * math.pi)
            rhythm_val = (0.6 * noise_val + 0.4 * math.sin(perc_phase)) * burst_env * rhythm_level

        # ── Mix all voices ──
        val = bass_val + mel_val + harm_val + rhythm_val
        val = val * max_amp * master_vol * env

        sample_val = max(-32767, min(32767, int(val)))

        # Stereo: melody slightly panned based on column, bass centered
        # Slight stereo widening for harmony
        mel_pan = pan
        bass_pan_l = 0.7  # bass mostly center
        bass_pan_r = 0.7

        left = int(sample_val * left_gain)
        right = int(sample_val * right_gain)
        left = max(-32767, min(32767, left))
        right = max(-32767, min(32767, right))
        struct.pack_into("<hh", buf, i * 4, left, right)

    new_state = {
        "frame_count": frame_count + 1,
        "root_semitone": new_root_semi,
        "bass_freq": bass_freq,
        "melody_notes": melody_notes,
        "noise_seed": noise_state,
        "prev_density": density,
    }

    return bytes(buf), new_state


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
    """Analyze current frame and play multi-voice sonified audio.

    Called each main-loop iteration. Generates a layered musical composition
    from the simulation's spatial state, with frame-to-frame continuity.
    """
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

    # Retrieve persistent synthesis state for musical continuity
    prev_state = getattr(self, '_sonify_state', {})

    samples, new_state = _sonify_synthesize(metrics, duration, prev_state)
    self._sonify_state = new_state

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
        self._sonify_state = {}  # reset musical state
    return self.sonify_enabled


def _draw_sonify_indicator(self, max_y, max_x):
    """Draw sonification status indicator with live musical info."""
    import curses
    if not self.sonify_enabled:
        return

    label = " ♫ SOUNDSCAPE "
    y = max_y - 2 if self.tt_history else max_y - 1
    if y <= 0:
        return

    # Show active category and musical state
    prefix = getattr(self, '_tt_get_active_mode_prefix', lambda: None)()
    mode_attr = f"{prefix}_mode" if prefix else None
    category = _CATEGORY_MAP.get(mode_attr, "Classic CA") if mode_attr else "Classic CA"
    profile_name = category[:16]

    # Show current musical info from state
    state = getattr(self, '_sonify_state', {})
    frame = state.get("frame_count", 0)
    root_semi = state.get("root_semitone", 0)
    n_melody = len(state.get("melody_notes", []))

    # Note name from root semitone
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    # Base freq 220 Hz = A3, so root_semitone=0 is A
    root_note = note_names[(9 + root_semi) % 12]  # A=9 in note_names

    indicator = f" {label}[{profile_name}] {root_note} mel:{n_melody} f:{frame} "
    x = max(0, max_x - len(indicator) - 1)

    try:
        self.stdscr.addstr(y, x, indicator, curses.color_pair(3) | curses.A_BOLD)
    except curses.error:
        pass


# ── Registration ─────────────────────────────────────────────────────────────

def register(App):
    """Register sonification methods on the App class."""
    App.sonify_play_cmd = _sonify_detect_player()

    App._sonify_frame = _sonify_frame
    App._sonify_toggle = _sonify_toggle
    App._draw_sonify_indicator = _draw_sonify_indicator
    App._sonify_extract_metrics = _extract_metrics
