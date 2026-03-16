"""Braille-dot Sparkline Metrics HUD — real-time mini charts overlay.

Renders live sparkline charts for population, entropy, energy, and
diversity index using Unicode braille characters (U+2800–U+28FF) for
~2×4 sub-cell resolution per character.  Toggled with Ctrl+V across
all 135 modes.  Auto-scales axes per metric.
"""
from __future__ import annotations

import curses
import math
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from life.grid import Grid

# ── Braille rendering ─────────────────────────────────────────────────────
# Each braille character encodes a 2-wide × 4-tall dot matrix.
# Dot positions (col 0, col 1):
#   row 0: 0x01, 0x08
#   row 1: 0x02, 0x10
#   row 2: 0x04, 0x20
#   row 3: 0x40, 0x80
_BRAILLE_BASE = 0x2800
_DOT_MAP = [
    [0x01, 0x08],  # row 0 (top)
    [0x02, 0x10],  # row 1
    [0x04, 0x20],  # row 2
    [0x40, 0x80],  # row 3 (bottom)
]


def _braille_sparkline(data: list[float], width: int, height: int) -> list[str]:
    """Render *data* as a braille sparkline chart.

    Returns a list of *height* strings, each *width* characters wide.
    The chart auto-scales to the data range.

    Each character covers 2 data columns and 4 dot rows, giving
    ``width * 2`` data-point resolution and ``height * 4`` vertical
    resolution.
    """
    if not data or width <= 0 or height <= 0:
        return [" " * width] * height

    # Number of data columns we can represent
    n_cols = width * 2
    # Take the most recent n_cols points (or pad with first value)
    if len(data) >= n_cols:
        vals = data[-n_cols:]
    else:
        vals = data[:]

    lo = min(vals)
    hi = max(vals)
    span = hi - lo if hi != lo else 1.0

    total_rows = height * 4  # total dot rows

    # Map each value to a dot-row index (0 = bottom, total_rows-1 = top)
    scaled = []
    for v in vals:
        row_idx = (v - lo) / span * (total_rows - 1)
        scaled.append(max(0.0, min(float(total_rows - 1), row_idx)))

    # Build the braille grid
    # grid[char_row][char_col] = braille offset bits
    grid = [[0] * width for _ in range(height)]

    for di, sv in enumerate(scaled):
        # Which character column?
        char_col = di // 2
        if char_col >= width:
            break
        sub_col = di % 2  # 0 or 1 within the character

        # Fill from bottom up to the value level (bar chart style)
        dot_row_top = int(round(sv))
        for dot_row in range(dot_row_top + 1):
            # dot_row 0 = bottom of chart
            # Convert to character grid coordinates
            # Bottom of chart = char_row (height-1), sub_row 3
            actual_row = total_rows - 1 - dot_row
            char_row = actual_row // 4
            sub_row = actual_row % 4
            if 0 <= char_row < height:
                grid[char_row][char_col] |= _DOT_MAP[sub_row][sub_col]

    # Convert to strings
    lines = []
    for char_row in range(height):
        chars = []
        for char_col in range(width):
            chars.append(chr(_BRAILLE_BASE + grid[char_row][char_col]))
        lines.append("".join(chars))
    return lines


def _format_compact(value: float) -> str:
    """Format a number compactly for axis labels."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 1:
        return f"{value:.1f}"
    if abs(value) >= 0.01:
        return f"{value:.2f}"
    return f"{value:.3f}"


# ── Energy computation ─────────────────────────────────────────────────────

def _compute_energy(grid: "Grid") -> float:
    """Compute a simple activity/energy metric.

    Sum of all live cell values — for binary grids this equals population,
    for multi-state grids it captures total excitation energy.
    """
    total = 0.0
    for r in range(grid.rows):
        row = grid.cells[r]
        for c in range(grid.cols):
            v = row[c]
            if v > 0:
                total += v
    return total


def _compute_diversity(grid: "Grid") -> float:
    """Compute a Shannon diversity index over cell states.

    Returns the effective number of species (exp of Shannon entropy),
    normalized to [0, 1] range based on the number of distinct states.
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
    n_states = len(counts)
    if n_states <= 1:
        return 0.0
    entropy = 0.0
    for cnt in counts.values():
        if cnt > 0:
            p = cnt / total
            entropy -= p * math.log(p)
    # Normalize: max entropy = ln(n_states)
    max_ent = math.log(n_states)
    return entropy / max_ent if max_ent > 0 else 0.0


# ── Sparkline HUD State ───────────────────────────────────────────────────

class SparklineHUDState:
    """Holds all state for the braille sparkline metrics overlay."""

    def __init__(self):
        self.active: bool = False
        self.max_points: int = 120  # history depth
        self.pop_history: deque[float] = deque(maxlen=120)
        self.entropy_history: deque[float] = deque(maxlen=120)
        self.energy_history: deque[float] = deque(maxlen=120)
        self.diversity_history: deque[float] = deque(maxlen=120)
        self.update_counter: int = 0
        # Which charts are visible (all on by default)
        self.show_pop: bool = True
        self.show_entropy: bool = True
        self.show_energy: bool = True
        self.show_diversity: bool = True

    def reset(self):
        self.pop_history.clear()
        self.entropy_history.clear()
        self.energy_history.clear()
        self.diversity_history.clear()
        self.update_counter = 0

    def update(self, grid: "Grid", entropy: float):
        """Sample current metrics from the grid."""
        self.update_counter += 1
        self.pop_history.append(float(grid.population))
        self.entropy_history.append(entropy)

        # Energy and diversity are moderately expensive — sample every 2 frames
        if self.update_counter % 2 == 0 or len(self.energy_history) == 0:
            self.energy_history.append(_compute_energy(grid))
            self.diversity_history.append(_compute_diversity(grid))
        else:
            # Carry forward last value
            if self.energy_history:
                self.energy_history.append(self.energy_history[-1])
            if self.diversity_history:
                self.diversity_history.append(self.diversity_history[-1])


# ── Methods to register on App ─────────────────────────────────────────────

def _toggle_sparkline_hud(self):
    """Toggle the braille sparkline metrics HUD."""
    self.sparkline_hud.active = not self.sparkline_hud.active
    if self.sparkline_hud.active:
        # Seed with current data
        self.sparkline_hud.update(self.grid, self.analytics.last_entropy)
        self._flash("Sparkline HUD ON  (Ctrl+V)")
    else:
        self._flash("Sparkline HUD OFF")


def _sparkline_hud_update(self):
    """Update sparkline HUD metrics (call each frame when active)."""
    if self.sparkline_hud.active:
        self.sparkline_hud.update(self.grid, self.analytics.last_entropy)


def _draw_sparkline_hud(self, max_y: int, max_x: int):
    """Draw the braille sparkline charts panel."""
    hud = self.sparkline_hud
    if not hud.active:
        return

    # Determine which charts to show
    charts: list[tuple[str, deque, int]] = []  # (label, data, color_pair)
    if hud.show_pop:
        charts.append(("POP", hud.pop_history, 1))       # green
    if hud.show_entropy:
        charts.append(("ENTROPY", hud.entropy_history, 4))  # magenta
    if hud.show_energy:
        charts.append(("ENERGY", hud.energy_history, 3))   # yellow
    if hud.show_diversity:
        charts.append(("DIVERSITY", hud.diversity_history, 2))  # cyan

    if not charts:
        return

    chart_h = 3  # braille chars tall per chart (= 12 dot rows resolution)
    chart_w = min(30, max_x // 3)  # braille chars wide
    if chart_w < 8:
        return

    # Panel dimensions
    label_w = 10  # space for label + axis values
    panel_w = label_w + chart_w + 3  # margins
    n_charts = len(charts)
    panel_h = n_charts * (chart_h + 1) + 2  # +1 for label row, +2 for border

    if max_y < panel_h + 2 or max_x < panel_w + 2:
        return

    # Position: top-left area (below any top indicators)
    px = 1
    py = 2

    border_attr = curses.color_pair(7) | curses.A_DIM
    title_attr = curses.color_pair(7) | curses.A_BOLD
    dim_attr = curses.color_pair(6) | curses.A_DIM

    # Draw border
    title = " SPARKLINES "
    inner_w = panel_w - 2
    top_line = "\u250c" + title + "\u2500" * max(0, inner_w - len(title)) + "\u2510"
    bot_line = "\u2514" + "\u2500" * inner_w + "\u2518"
    try:
        self.stdscr.addstr(py, px, top_line[:panel_w], title_attr)
    except curses.error:
        pass
    for row_off in range(1, panel_h - 1):
        try:
            self.stdscr.addstr(py + row_off, px, "\u2502", border_attr)
            self.stdscr.addstr(py + row_off, px + panel_w - 1, "\u2502", border_attr)
            # Clear interior
            self.stdscr.addstr(py + row_off, px + 1, " " * inner_w)
        except curses.error:
            pass
    try:
        self.stdscr.addstr(py + panel_h - 1, px, bot_line[:panel_w], border_attr)
    except curses.error:
        pass

    # Draw each chart
    y = py + 1
    for label, data, color_idx in charts:
        data_list = list(data)
        chart_attr = curses.color_pair(color_idx) | curses.A_BOLD
        label_attr = curses.color_pair(color_idx)

        # Label row with current value and range
        if data_list:
            cur = data_list[-1]
            lo = min(data_list)
            hi = max(data_list)
            header = f" {label}: {_format_compact(cur)}"
            range_str = f"{_format_compact(lo)}-{_format_compact(hi)}"
            # Fit header + range in available space
            avail = inner_w - 1
            if len(header) + len(range_str) + 1 <= avail:
                header = header + " " * (avail - len(header) - len(range_str)) + range_str
            header = header[:avail]
        else:
            header = f" {label}: --"
            header = header[:inner_w - 1]

        try:
            self.stdscr.addstr(y, px + 1, header.ljust(inner_w)[:inner_w], label_attr)
        except curses.error:
            pass
        y += 1

        # Render braille chart
        lines = _braille_sparkline(data_list, chart_w, chart_h)
        for li, line in enumerate(lines):
            try:
                self.stdscr.addstr(y + li, px + 2, line[:chart_w], chart_attr)
            except curses.error:
                pass
        y += chart_h

    # Footer hint
    try:
        hint = " Ctrl+V=close"
        self.stdscr.addstr(py + panel_h - 1, px + 2, hint[:inner_w - 2], dim_attr)
    except curses.error:
        pass


def register(App):
    """Register sparkline HUD methods on the App class."""
    App._toggle_sparkline_hud = _toggle_sparkline_hud
    App._sparkline_hud_update = _sparkline_hud_update
    App._draw_sparkline_hud = _draw_sparkline_hud
