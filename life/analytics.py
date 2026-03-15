"""Real-Time Simulation Analytics Overlay — quantitative metrics HUD.

Provides live population sparkline, Shannon entropy, periodicity detection,
rate of change with trend arrows, symmetry scoring, and stability classification.
Toggled with Ctrl+K across all 103+ modes.
"""
from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .grid import Grid

SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"

# ── Metric helpers ──────────────────────────────────────────────────────────


def _sparkline(data: list[int] | list[float], width: int) -> str:
    """Render a sparkline string of *width* characters from *data*."""
    if not data or width <= 0:
        return ""
    # Take the last `width` points (or fewer if not enough data)
    vals = list(data[-width:])
    lo, hi = min(vals), max(vals)
    span = hi - lo if hi != lo else 1
    out: list[str] = []
    for v in vals:
        idx = int((v - lo) / span * (len(SPARKLINE_CHARS) - 1))
        idx = max(0, min(idx, len(SPARKLINE_CHARS) - 1))
        out.append(SPARKLINE_CHARS[idx])
    return "".join(out)


def shannon_entropy(grid: Grid) -> float:
    """Shannon entropy of cell states (0 = uniform, higher = more disorder).

    Treats each distinct cell value as a symbol.
    """
    rows, cols = grid.rows, grid.cols
    total = rows * cols
    if total == 0:
        return 0.0
    counts: dict[int, int] = {}
    for r in range(rows):
        row = grid.cells[r]
        for c in range(cols):
            v = row[c]
            counts[v] = counts.get(v, 0) + 1
    entropy = 0.0
    for cnt in counts.values():
        if cnt > 0:
            p = cnt / total
            entropy -= p * math.log2(p)
    return entropy


def rate_of_change(pop_history: list[int], window: int = 5) -> tuple[float, str]:
    """Return (avg delta per tick, trend arrow) over the last *window* ticks."""
    if len(pop_history) < 2:
        return 0.0, "─"
    recent = pop_history[-min(window + 1, len(pop_history)):]
    deltas = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    avg = sum(deltas) / len(deltas)
    if avg > 2:
        arrow = "↑" if avg < 20 else "⇑"
    elif avg < -2:
        arrow = "↓" if avg > -20 else "⇓"
    else:
        arrow = "─"
    return avg, arrow


def symmetry_score(grid: Grid) -> dict[str, float]:
    """Compute horizontal, vertical, and 180° rotational symmetry (0.0–1.0)."""
    rows, cols = grid.rows, grid.cols
    if rows == 0 or cols == 0:
        return {"horiz": 0.0, "vert": 0.0, "rot180": 0.0}
    cells = grid.cells
    h_match = v_match = r_match = 0
    total_h = total_v = total_r = 0

    # Horizontal symmetry (left-right mirror)
    half_c = cols // 2
    for r in range(rows):
        row = cells[r]
        for c in range(half_c):
            a = 1 if row[c] > 0 else 0
            b = 1 if row[cols - 1 - c] > 0 else 0
            if a == b:
                h_match += 1
            total_h += 1

    # Vertical symmetry (top-bottom mirror)
    half_r = rows // 2
    for r in range(half_r):
        row_top = cells[r]
        row_bot = cells[rows - 1 - r]
        for c in range(cols):
            a = 1 if row_top[c] > 0 else 0
            b = 1 if row_bot[c] > 0 else 0
            if a == b:
                v_match += 1
            total_v += 1

    # 180° rotational symmetry
    half_total = (rows * cols) // 2
    for r in range(rows):
        for c in range(cols):
            rr, rc = rows - 1 - r, cols - 1 - c
            if r * cols + c >= rr * cols + rc:
                break  # only check half
            a = 1 if cells[r][c] > 0 else 0
            b = 1 if cells[rr][rc] > 0 else 0
            if a == b:
                r_match += 1
            total_r += 1

    return {
        "horiz": h_match / total_h if total_h else 0.0,
        "vert": v_match / total_v if total_v else 0.0,
        "rot180": r_match / total_r if total_r else 0.0,
    }


class PeriodicityDetector:
    """Detect when the simulation enters a repeating cycle."""

    def __init__(self, max_history: int = 500):
        self.hashes: dict[str, int] = {}  # hash -> generation
        self.period: int | None = None
        self.detected_at: int | None = None
        self.max_history = max_history

    def reset(self):
        self.hashes.clear()
        self.period = None
        self.detected_at = None

    def update(self, grid: Grid) -> int | None:
        """Feed a grid state. Returns period if cycle detected, else None."""
        h = grid.state_hash()
        gen = grid.generation
        if h in self.hashes:
            self.period = gen - self.hashes[h]
            self.detected_at = gen
            return self.period
        self.hashes[h] = gen
        # Prune old entries to bound memory
        if len(self.hashes) > self.max_history:
            cutoff = gen - self.max_history
            self.hashes = {k: v for k, v in self.hashes.items() if v >= cutoff}
        return None


def classify_stability(pop_history: list[int], cycle_period: int | None) -> str:
    """Classify the simulation state into a stability category."""
    if len(pop_history) < 3:
        return "starting"

    recent = pop_history[-30:]
    pop = recent[-1]

    # Extinction
    if pop == 0:
        return "extinct"

    # Check if cycle was detected
    if cycle_period is not None:
        if cycle_period == 1:
            return "static"
        return "oscillating"

    # Compute recent trend
    if len(recent) >= 10:
        first_half = sum(recent[:len(recent) // 2]) / (len(recent) // 2)
        second_half = sum(recent[len(recent) // 2:]) / (len(recent) - len(recent) // 2)
        ratio = second_half / first_half if first_half > 0 else 1.0

        if ratio > 1.15:
            return "growing"
        if ratio < 0.85:
            return "dying"

    # Check variance for chaos vs. stable
    if len(recent) >= 5:
        mean = sum(recent) / len(recent)
        if mean > 0:
            variance = sum((x - mean) ** 2 for x in recent) / len(recent)
            cv = math.sqrt(variance) / mean  # coefficient of variation
            if cv > 0.15:
                return "chaotic"

    return "stable"


class AnalyticsState:
    """Holds all analytics overlay state for the App."""

    def __init__(self):
        self.enabled: bool = False
        self.periodicity = PeriodicityDetector()
        self.pop_sparkline: deque[int] = deque(maxlen=60)
        self.entropy_history: deque[float] = deque(maxlen=60)
        self.last_entropy: float = 0.0
        self.last_symmetry: dict[str, float] = {"horiz": 0.0, "vert": 0.0, "rot180": 0.0}
        self.last_delta: float = 0.0
        self.last_trend: str = "─"
        self.last_stability: str = "starting"
        self.update_counter: int = 0
        # Expensive metrics computed every N frames
        self.symmetry_interval: int = 5
        self.entropy_interval: int = 2

    def reset(self):
        """Reset analytics state (e.g. on grid clear)."""
        self.periodicity.reset()
        self.pop_sparkline.clear()
        self.entropy_history.clear()
        self.last_entropy = 0.0
        self.last_symmetry = {"horiz": 0.0, "vert": 0.0, "rot180": 0.0}
        self.last_delta = 0.0
        self.last_trend = "─"
        self.last_stability = "starting"
        self.update_counter = 0

    def update(self, grid: Grid, pop_history: list[int]):
        """Recompute metrics for the current frame."""
        self.update_counter += 1
        pop = grid.population
        self.pop_sparkline.append(pop)

        # Rate of change
        self.last_delta, self.last_trend = rate_of_change(pop_history)

        # Shannon entropy (every N frames — moderately expensive)
        if self.update_counter % self.entropy_interval == 0:
            self.last_entropy = shannon_entropy(grid)
            self.entropy_history.append(self.last_entropy)

        # Periodicity
        self.periodicity.update(grid)

        # Symmetry (every N frames — expensive)
        if self.update_counter % self.symmetry_interval == 0:
            self.last_symmetry = symmetry_score(grid)

        # Stability classification
        self.last_stability = classify_stability(
            pop_history, self.periodicity.period
        )
