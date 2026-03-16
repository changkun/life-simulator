"""Mode: iso — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEED_LABELS
from life.rules import rule_string

def _iso_pillar(self, age: int) -> list[str]:
    """Return pillar characters (bottom to top) for a given cell age."""
    for max_age, chars in self._ISO_HEIGHT_TIERS:
        if age <= max_age:
            return chars
    return self._ISO_ANCIENT[:self._ISO_MAX_HEIGHT]



def _draw_iso(self, max_y: int, max_x: int):
    """Draw the grid as a pseudo-3D isometric cityscape.

    Each living cell becomes a column whose height reflects the cell's age.
    The view uses a simple oblique projection: each grid row shifts right
    by 1 column and up by 1 row compared to the row behind it, creating
    an isometric illusion.  Taller pillars occlude shorter ones behind them.
    """
    # Reserve bottom rows for status/hint
    draw_h = max_y - 4
    draw_w = max_x - 1
    if draw_h < 5 or draw_w < 10:
        return

    # Determine how many grid cells we can fit.
    # In iso view, each cell occupies 2 screen columns.  Each successive
    # grid row shifts +1 col and -1 row on screen.  We work out a window
    # that fits in the available terminal space.
    #
    # visible grid rows  = R, visible grid cols = C
    # screen width needed  = 2*C + R   (the shift per row is +1 col)
    # screen height needed = R + max_pillar_height
    max_pillar = self._ISO_MAX_HEIGHT

    # Solve for R, C from available space
    vis_rows = min(self.grid.rows, draw_h - max_pillar)
    if vis_rows < 1:
        vis_rows = 1
    vis_cols = min(self.grid.cols, (draw_w - vis_rows) // 2)
    if vis_cols < 1:
        vis_cols = 1

    # Centre viewport on cursor
    start_r = self.cursor_r - vis_rows // 2
    start_c = self.cursor_c - vis_cols // 2

    # Build a z-buffer: screen[sy][sx] = (char, color_pair_idx, bold)
    # We'll use a dict for sparse storage
    zbuf: dict[tuple[int, int], tuple[str, int, bool]] = {}

    # We iterate grid back-to-front (painter's algorithm) so that closer
    # rows overwrite farther ones.
    for gy in range(vis_rows):
        gr = (start_r + gy) % self.grid.rows
        # Screen base position for this grid row:
        # row 0 (farthest) is at top-right; last row at bottom-left.
        base_sy = (vis_rows - 1 - gy) + max_pillar  # bottom of pillar footprint
        base_sx = gy  # iso shift: each row shifts right by 1

        for gx in range(vis_cols):
            gc = (start_c + gx) % self.grid.cols
            age = self.grid.cells[gr][gc]
            sx = base_sx + gx * 2
            is_cursor = (gr == self.cursor_r and gc == self.cursor_c)

            if age > 0:
                pillar = self._iso_pillar(age)
                height = len(pillar)
                # Determine color based on age
                if age <= 1:
                    cpair = 1   # green
                elif age <= 3:
                    cpair = 2   # cyan
                elif age <= 8:
                    cpair = 3   # yellow
                elif age <= 20:
                    cpair = 4   # magenta
                else:
                    cpair = 5   # red

                # Draw pillar from bottom to top
                for i, ch in enumerate(pillar):
                    sy = base_sy - i
                    if 0 <= sy < draw_h and 0 <= sx < draw_w - 1:
                        bold = is_cursor or (i == height - 1)
                        zbuf[(sy, sx)] = (ch + ch, cpair, bold)
                        # Right-face shade (1 col to the right of the 2-char cell)
                        shade_sx = sx + 2
                        shade_ch = self._ISO_SHADE_MAP.get(ch, " ")
                        if shade_ch != " " and 0 <= shade_sx < draw_w - 1:
                            # Only draw shade if nothing solid is there already
                            if (sy, shade_sx) not in zbuf:
                                zbuf[(sy, shade_sx)] = (shade_ch + " ", cpair, False)
            else:
                # Dead cell: draw ground marker
                if is_cursor:
                    sy = base_sy
                    if 0 <= sy < draw_h and 0 <= sx < draw_w - 1:
                        zbuf[(sy, sx)] = ("▒▒", 6, False)
                # else: leave empty (background)

    # Render the z-buffer to screen
    for (sy, sx), (chars, cpair, bold) in zbuf.items():
        attr = curses.color_pair(cpair)
        if bold:
            attr |= curses.A_BOLD
        try:
            self.stdscr.addstr(sy, sx, chars, attr)
        except curses.error:
            pass

    # Draw a ground line at the base
    ground_y = vis_rows + max_pillar
    if ground_y < draw_h:
        ground_str = "╌" * min(draw_w, 2 * vis_cols + vis_rows)
        try:
            self.stdscr.addstr(ground_y, 0, ground_str, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        state = "▶ PLAY" if self.running else "⏸ PAUSE"
        speed = SPEED_LABELS[self.speed_idx]
        rs = rule_string(self.grid.birth, self.grid.survival)
        mode = "  │  🏙 ISO-3D"
        if self.heatmap_mode:
            mode += "  │  🔥 HEATMAP"
        if self.sound_engine.enabled:
            mode += "  │  ♪ SOUND"
        if self.recording:
            mode += f"  │  ⏺ REC({len(self.recorded_frames)})"
        status = (
            f" Gen: {self.grid.generation}  │  "
            f"Pop: {self.grid.population}  │  "
            f"{state}  │  Speed: {speed}  │  "
            f"Rule: {rs}  │  "
            f"Cursor: ({self.cursor_r},{self.cursor_c}){mode}"
        )
        status = status[:max_x - 1]
        try:
            self.stdscr.addstr(status_y, 0, status, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [I]=exit 3D [arrows]=move cursor [H]=heatmap [M]=sound [+/-]=zoom [?]=help [q]=quit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

# ── Comparison mode ──




def register(App):
    """Register iso mode methods and constants on the App class."""
    # Class-level constants for isometric rendering
    App._ISO_HEIGHT_TIERS = [
        (1,  ["█"]),                              # newborn: 1 row
        (3,  ["█", "▓"]),                         # young: 2 rows
        (8,  ["█", "▓", "▒"]),                    # mature: 3 rows
        (20, ["█", "▓", "▒", "░"]),               # old: 4 rows
    ]
    App._ISO_MAX_HEIGHT = 5  # ancient: 5 rows
    App._ISO_ANCIENT = ["█", "▓", "▒", "░", "·"]
    App._ISO_SHADE_MAP = {"█": "▓", "▓": "▒", "▒": "░", "░": " ", "·": " "}
    # Methods
    App._iso_pillar = _iso_pillar
    App._draw_iso = _draw_iso

