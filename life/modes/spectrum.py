"""2D Spatial Frequency Spectrum overlay.

Performs a discrete Fourier transform on the current simulation grid and
displays the frequency-domain magnitude as a secondary panel, revealing
hidden periodic structures, symmetry, and standing waves in any running
simulation.

Toggle with 'y'.  Works universally across all 130+ modes via the same
_get_minimap_data() sampling interface used by the minimap overlay.
Pure Python — no external dependencies.
"""

import math
import curses

from life.colors import colormap_rgb

# ── DFT implementation ───────────────────────────────────────────────────

def _dft_2d(data, N):
    """Compute 2D DFT magnitude spectrum on an NxN real-valued grid.

    Returns NxN list of log-magnitude values, DC-centered (shifted so that
    the zero-frequency component is in the middle of the panel).

    Uses a separable approach: 1D DFT along rows, then 1D DFT along columns,
    for O(N^3) instead of O(N^4).
    """
    two_pi = 2.0 * math.pi

    # Pre-compute twiddle factors for size N
    cos_table = [0.0] * N
    sin_table = [0.0] * N
    for k in range(N):
        angle = two_pi * k / N
        cos_table[k] = math.cos(angle)
        sin_table[k] = math.sin(angle)

    # 1D DFT helper using pre-computed twiddles
    def dft_1d_rows(matrix):
        """Apply 1D DFT along each row, returning (real, imag) pair of 2D lists."""
        out_re = [[0.0] * N for _ in range(N)]
        out_im = [[0.0] * N for _ in range(N)]
        for r in range(N):
            row = matrix[r]
            for k in range(N):
                re = 0.0
                im = 0.0
                for n in range(N):
                    idx = (k * n) % N
                    val = row[n]
                    re += val * cos_table[idx]
                    im -= val * sin_table[idx]
                out_re[r][k] = re
                out_im[r][k] = im
        return out_re, out_im

    # Step 1: DFT along rows
    row_re, row_im = dft_1d_rows(data)

    # Step 2: DFT along columns (transpose, DFT rows, transpose back)
    # Transpose
    t_re = [[row_re[r][c] for r in range(N)] for c in range(N)]
    t_im = [[row_im[r][c] for r in range(N)] for c in range(N)]

    # DFT along what were columns (now rows of transposed)
    # We need to handle complex input this time
    mag = [[0.0] * N for _ in range(N)]

    for k_col in range(N):
        col_re_in = t_re[k_col]
        col_im_in = t_im[k_col]
        for k_row in range(N):
            re = 0.0
            im = 0.0
            for n in range(N):
                idx = (k_row * n) % N
                c_cos = cos_table[idx]
                c_sin = sin_table[idx]
                # (a + bi)(cos - i*sin) = a*cos + b*sin + i*(b*cos - a*sin)
                re += col_re_in[n] * c_cos + col_im_in[n] * c_sin
                im += col_im_in[n] * c_cos - col_re_in[n] * c_sin
            # Result goes to mag[k_row][k_col]
            mag[k_row][k_col] = math.sqrt(re * re + im * im)

    # DC-center shift: swap quadrants
    half = N // 2
    shifted = [[0.0] * N for _ in range(N)]
    for r in range(N):
        for c in range(N):
            sr = (r + half) % N
            sc = (c + half) % N
            shifted[sr][sc] = mag[r][c]

    # Log-scale for better visibility
    log_mag = [[0.0] * N for _ in range(N)]
    max_val = 0.0
    for r in range(N):
        for c in range(N):
            v = math.log1p(shifted[r][c])
            log_mag[r][c] = v
            if v > max_val:
                max_val = v

    # Normalise to [0, 1]
    if max_val > 0:
        inv = 1.0 / max_val
        for r in range(N):
            for c in range(N):
                log_mag[r][c] *= inv

    return log_mag


# ── State initialisation ─────────────────────────────────────────────────

def _spectrum_init(self):
    """Initialise spectrum overlay state variables."""
    self.spectrum_active = False
    self._spectrum_cache = None       # cached magnitude grid
    self._spectrum_frame = -1         # draw frame when cache was computed
    self._spectrum_size = 32          # DFT resolution (NxN)
    self._spectrum_colormap = "inferno"  # colormap for rendering


# ── Sampling ─────────────────────────────────────────────────────────────

def _spectrum_sample_grid(self, N):
    """Sample the current simulation into an NxN grid of floats [0,1].

    Reuses _get_minimap_data() for universal mode support.
    """
    data = self._get_minimap_data()
    if data is None:
        return None

    grid_rows, grid_cols, sample_fn = data[0], data[1], data[2]
    if grid_rows <= 0 or grid_cols <= 0:
        return None

    # Down/up-sample into NxN
    result = [[0.0] * N for _ in range(N)]
    for r in range(N):
        gr = int(r * grid_rows / N) % grid_rows
        for c in range(N):
            gc = int(c * grid_cols / N) % grid_cols
            try:
                result[r][c] = sample_fn(gr, gc)
            except Exception:
                result[r][c] = 0.0
    return result


# ── Compute spectrum ─────────────────────────────────────────────────────

def _spectrum_compute(self):
    """Compute the 2D DFT spectrum, with caching per generation."""
    # Recompute every 3 draw frames to keep responsive without lagging
    frame = getattr(self, 'pp_frame_count', 0)
    if self._spectrum_cache is not None and (frame - self._spectrum_frame) < 3:
        return self._spectrum_cache

    N = self._spectrum_size
    grid = _spectrum_sample_grid(self, N)
    if grid is None:
        return None

    self._spectrum_cache = _dft_2d(grid, N)
    self._spectrum_frame = frame
    return self._spectrum_cache


# ── Draw spectrum panel ──────────────────────────────────────────────────

def _spectrum_draw_panel(self):
    """Draw the frequency spectrum as a panel in the bottom-left corner."""
    if not self.spectrum_active:
        return

    mag = _spectrum_compute(self)
    if mag is None:
        return

    my, mx = self.stdscr.getmaxyx()
    N = len(mag)

    # Panel size: fit into bottom-left, max 1/3 screen
    panel_h = min(N, max(6, my // 3))
    panel_w = min(N * 2, max(12, mx // 3))  # 2 chars per cell
    cell_w = 2

    # Position: bottom-left with 1 row/col margin
    start_y = my - panel_h - 2
    start_x = 1

    if start_y < 2 or start_x + panel_w + 2 >= mx:
        return

    # Draw border
    title = " SPECTRUM (2D DFT) "
    border_w = panel_w + 2
    try:
        # Top border
        top = "\u250c" + title + "\u2500" * max(0, border_w - 2 - len(title)) + "\u2510"
        self.stdscr.addstr(start_y - 1, start_x - 1, top[:mx - start_x],
                           curses.color_pair(0) | curses.A_DIM)
        # Bottom border
        bot = "\u2514" + "\u2500" * (border_w - 2) + "\u2518"
        self.stdscr.addstr(start_y + panel_h, start_x - 1, bot[:mx - start_x],
                           curses.color_pair(0) | curses.A_DIM)
        # Side borders
        for dy in range(panel_h):
            self.stdscr.addstr(start_y + dy, start_x - 1, "\u2502",
                               curses.color_pair(0) | curses.A_DIM)
            rx = start_x + panel_w
            if rx < mx - 1:
                self.stdscr.addstr(start_y + dy, rx, "\u2502",
                                   curses.color_pair(0) | curses.A_DIM)
    except curses.error:
        pass

    # Render spectrum cells
    cells_h = panel_h
    cells_w = panel_w // cell_w
    cmap = self._spectrum_colormap

    for dy in range(cells_h):
        # Map panel row to spectrum row
        sr = int(dy * N / cells_h) % N
        py = start_y + dy
        if py >= my - 1:
            break
        for dx in range(cells_w):
            sc = int(dx * N / cells_w) % N
            px = start_x + dx * cell_w
            if px + cell_w > mx - 2:
                break

            val = mag[sr][sc]
            r, g, b = colormap_rgb(cmap, val)
            self.tc_buf.put(py, px, "\u2588\u2588", r, g, b)


# ── Indicator badge ──────────────────────────────────────────────────────

def _spectrum_draw_indicator(self):
    """Draw a compact status badge when spectrum overlay is active."""
    if not self.spectrum_active:
        return
    my, mx = self.stdscr.getmaxyx()
    label = f" SPECTRUM {self._spectrum_size}x{self._spectrum_size} "
    # Position after ghost trail badge area
    col = max(1, mx - len(label) - 2)
    row = 0
    if col + len(label) >= mx:
        return
    try:
        self.stdscr.addstr(row, col, label,
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass


# ── Key handling ─────────────────────────────────────────────────────────

def _spectrum_handle_key(self, key):
    """Handle spectrum overlay key bindings.  Returns True if consumed."""
    # 'y' — toggle spectrum on/off
    if key == ord("y"):
        self.spectrum_active = not self.spectrum_active
        if not self.spectrum_active:
            self._spectrum_cache = None
        msg = "Spectrum Overlay ON" if self.spectrum_active else "Spectrum Overlay OFF"
        if self.spectrum_active:
            msg += f" ({self._spectrum_size}x{self._spectrum_size} DFT)"
        self._flash(msg)
        return True

    if not self.spectrum_active:
        return False

    # '[' / ']' when spectrum active — adjust DFT resolution
    # (These don't conflict since we only capture them when spectrum is on)
    if key == ord("{"):
        old = self._spectrum_size
        self._spectrum_size = max(8, self._spectrum_size // 2)
        if self._spectrum_size != old:
            self._spectrum_cache = None
        self._flash(f"Spectrum resolution: {self._spectrum_size}x{self._spectrum_size}")
        return True
    if key == ord("}"):
        old = self._spectrum_size
        self._spectrum_size = min(64, self._spectrum_size * 2)
        if self._spectrum_size != old:
            self._spectrum_cache = None
        self._flash(f"Spectrum resolution: {self._spectrum_size}x{self._spectrum_size}")
        return True

    return False


# ── Registration ─────────────────────────────────────────────────────────

def register(App):
    """Attach spectrum overlay methods and state initialiser to App."""
    App._spectrum_init = _spectrum_init
    App._spectrum_draw_panel = _spectrum_draw_panel
    App._spectrum_draw_indicator = _spectrum_draw_indicator
    App._spectrum_handle_key = _spectrum_handle_key
