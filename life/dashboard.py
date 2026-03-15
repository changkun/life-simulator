"""TUI Dashboard — polished landing screen with live preview, categories, and favorites."""
import curses
import json
import math
import os
import random
import time

from life.constants import SAVE_DIR
from life.registry import MODE_CATEGORIES, MODE_REGISTRY

FAVORITES_FILE = os.path.join(SAVE_DIR, "favorites.json")

# ── Mini-preview simulations ──
# Each preview is a simple self-contained animation that gives a flavor of the mode.
# They operate on a small buffer and return a list of (row, col, char, color_pair) tuples.


def _preview_gol(tick, h, w):
    """Game of Life mini preview."""
    cells = set()
    if tick == 0:
        # Seed with an R-pentomino in center
        cr, cc = h // 2, w // 2
        for dr, dc in [(0, 0), (0, 1), (1, -1), (1, 0), (-1, 0)]:
            cells.add((cr + dr, cc + dc))
        return cells, []
    return None, []


def _preview_static(name, tick, h, w):
    """Generate a static/animated ASCII art preview for a mode."""
    out = []
    t = tick * 0.15

    if "wave" in name.lower() or "oscillat" in name.lower():
        for r in range(h):
            for c in range(w):
                v = math.sin(c * 0.4 + t) * math.cos(r * 0.3 + t * 0.7)
                idx = int((v + 1) * 2.5)
                chars = " ░▒▓█"
                ch = chars[max(0, min(4, idx))]
                cp = 5 if v > 0.3 else 4 if v > -0.3 else 6
                out.append((r, c, ch, cp))

    elif "sand" in name.lower() or "falling" in name.lower():
        for c in range(w):
            pile_h = int((math.sin(c * 0.3) + 1) * h * 0.3) + int(tick * 0.5) % 3
            for r in range(h - pile_h, h):
                if r >= 0:
                    out.append((r, c, "░" if r == h - pile_h else "▓", 3))
        # Falling particles
        for i in range(5):
            pr = (tick * 2 + i * 7) % h
            pc = (w // 2 + int(math.sin(tick * 0.3 + i) * 3)) % w
            out.append((pr, pc, "●", 3))

    elif "boid" in name.lower() or "flock" in name.lower():
        for i in range(12):
            angle = t * 0.8 + i * 0.5
            r = int(h / 2 + math.sin(angle + i * 0.3) * h * 0.35)
            c = int(w / 2 + math.cos(angle * 0.7 + i * 0.5) * w * 0.35)
            if 0 <= r < h and 0 <= c < w:
                out.append((r, c, ">" if math.cos(angle) > 0 else "<", 2))

    elif "fluid" in name.lower() or "navier" in name.lower() or "boltzmann" in name.lower():
        for r in range(h):
            for c in range(w):
                v = math.sin(c * 0.2 + t * 1.5) * math.cos(r * 0.15 + t * 0.5)
                v += math.sin((c + r) * 0.1 + t * 0.8) * 0.5
                idx = int((v + 1.5) * 1.5)
                chars = " ·~≈▒"
                ch = chars[max(0, min(4, idx))]
                cp = 4 if v > 0.5 else 6 if v > -0.2 else 5
                out.append((r, c, ch, cp))

    elif "fire" in name.lower() or "smoke" in name.lower() or "volcano" in name.lower():
        for r in range(h):
            for c in range(w):
                heat = max(0, 1.0 - r / h) * (0.7 + 0.3 * math.sin(c * 0.5 + t * 2))
                heat *= (0.8 + 0.2 * math.sin(t * 3 + c * 0.7 + r * 0.4))
                if heat > 0.7:
                    out.append((r, c, "█", 1))
                elif heat > 0.5:
                    out.append((r, c, "▓", 3))
                elif heat > 0.3:
                    out.append((r, c, "░", 3))

    elif "fractal" in name.lower() or "mandel" in name.lower():
        chars = " .·:;+*#█"
        for r in range(h):
            for c in range(w):
                zr = (c - w / 2) / (w * 0.3) + math.sin(t * 0.1) * 0.1
                zi = (r - h / 2) / (h * 0.5)
                cr2, ci = -0.7 + math.sin(t * 0.05) * 0.1, 0.27
                x, y, i = 0.0, 0.0, 0
                while x * x + y * y < 4 and i < 8:
                    x, y = x * x - y * y + cr2 + zr * 0.3, 2 * x * y + ci + zi * 0.3
                    i += 1
                out.append((r, c, chars[i], 5 if i > 5 else 4 if i > 2 else 6))

    elif "maze" in name.lower():
        random.seed(42)
        for r in range(h):
            for c in range(w):
                if r == 0 or c == 0 or r == h - 1 or c == w - 1:
                    out.append((r, c, "█", 7))
                elif (r % 2 == 0 and random.random() < 0.5) or (c % 2 == 0 and random.random() < 0.3):
                    out.append((r, c, "█", 7))
        # Animated cursor
        cr = int(1 + (tick * 0.5) % max(1, h - 2))
        cc = int(1 + (tick * 0.3) % max(1, w - 2))
        out.append((min(cr, h - 1), min(cc, w - 1), "●", 2))

    elif "matrix" in name.lower() or "digital rain" in name.lower():
        for c in range(w):
            speed = 1 + (c * 7 + 3) % 3
            for r in range(h):
                pos = (r - int(t * speed * 2) + c * 5) % (h + 5)
                if pos < 0:
                    continue
                if pos == 0:
                    out.append((r, c, chr(random.randint(0x30, 0x5A)), 2))
                elif pos < 6:
                    brightness = max(0, 5 - pos)
                    if brightness > 2:
                        out.append((r, c, chr(random.randint(0x30, 0x5A)), 2))

    elif "galaxy" in name.lower() or "n-body" in name.lower() or "orrery" in name.lower():
        cx, cy = w / 2, h / 2
        for i in range(20):
            angle = t * (0.3 + i * 0.02) + i * 0.31
            dist = 2 + i * 0.5
            r = int(cy + math.sin(angle) * dist * 0.8)
            c = int(cx + math.cos(angle) * dist)
            if 0 <= r < h and 0 <= c < w:
                ch = "★" if i < 3 else "·" if i > 15 else "*"
                out.append((r, c, ch, 3 if i < 5 else 7))

    elif "lightning" in name.lower() or "aurora" in name.lower():
        # Zigzag bolt
        c = w // 2
        for r in range(h):
            c += random.choice([-1, 0, 0, 1])
            c = max(0, min(w - 1, c))
            if (tick + r) % 8 < 5:
                out.append((r, c, "│", 3))
                if c > 0:
                    out.append((r, c - 1, "░", 6))
                if c < w - 1:
                    out.append((r, c + 1, "░", 6))

    elif "pendulum" in name.lower() or "double" in name.lower():
        cx, cy = w // 2, 1
        l1, l2 = min(h, w) * 0.3, min(h, w) * 0.25
        a1 = math.sin(t * 1.3) * 1.2
        a2 = math.sin(t * 2.1 + 1) * 1.5
        x1 = int(cx + l1 * math.sin(a1))
        y1 = int(cy + l1 * math.cos(a1) * 0.6)
        x2 = int(x1 + l2 * math.sin(a2))
        y2 = int(y1 + l2 * math.cos(a2) * 0.6)
        if 0 <= y1 < h and 0 <= x1 < w:
            out.append((y1, x1, "●", 2))
        if 0 <= y2 < h and 0 <= x2 < w:
            out.append((y2, x2, "●", 1))

    elif "sort" in name.lower():
        n_bars = min(w, 15)
        heights = list(range(1, n_bars + 1))
        # Simple animated swap
        si = tick % n_bars
        if si < n_bars - 1 and heights[si] > heights[si + 1]:
            heights[si], heights[si + 1] = heights[si + 1], heights[si]
        for i, bh in enumerate(heights):
            bar_h = int(bh * h / (n_bars + 1))
            for r in range(h - bar_h, h):
                c = i * (w // n_bars)
                if 0 <= c < w:
                    out.append((r, c, "█", 2 if i == si else 4))

    elif "aquarium" in name.lower() or "fish" in name.lower():
        # Seaweed
        for i in range(3):
            bc = 2 + i * (w // 3)
            for r in range(h - 4, h):
                sc = bc + int(math.sin(t * 2 + r * 0.5 + i) * 1)
                if 0 <= sc < w:
                    out.append((r, sc, "}", 2))
        # Fish
        for i in range(4):
            fr = 1 + (i * 3) % max(1, h - 2)
            fc = int((t * 3 + i * 11) % (w + 4)) - 2
            if 0 <= fr < h:
                if 0 <= fc < w:
                    out.append((fr, fc, "><", 6 if i % 2 == 0 else 3))
                if 0 <= fc + 1 < w:
                    out.append((fr, fc + 1, ">", 6 if i % 2 == 0 else 3))
        # Bubbles
        for i in range(3):
            br = int((h - (t * 1.5 + i * 5) % h)) % h
            bc = w // 4 + i * (w // 3)
            if 0 <= bc < w:
                out.append((br, bc, "°", 4))

    elif "snow" in name.lower() or "blizzard" in name.lower():
        for i in range(20):
            r = int((t * (1 + i % 3) + i * 3.7) % h)
            c = int((i * 7.3 + math.sin(t + i) * 2) % w)
            if 0 <= r < h and 0 <= c < w:
                out.append((r, c, "❄" if i % 5 == 0 else "*" if i % 3 == 0 else "·", 7))

    elif "kaleidoscope" in name.lower() or "symmetry" in name.lower():
        cx, cy = w // 2, h // 2
        for i in range(6):
            angle = t * 0.5 + i * math.pi / 3
            for d in range(1, min(cx, cy)):
                r = int(cy + math.sin(angle) * d * 0.8)
                c = int(cx + math.cos(angle) * d)
                if 0 <= r < h and 0 <= c < w:
                    chars = "·*+#█"
                    ci = min(4, d % 5)
                    out.append((r, c, chars[ci], 1 + (i % 6) + 1))

    elif "dna" in name.lower() or "helix" in name.lower():
        for r in range(h):
            phase = r * 0.4 + t * 2
            c1 = int(w / 2 + math.sin(phase) * w * 0.3)
            c2 = int(w / 2 - math.sin(phase) * w * 0.3)
            if 0 <= c1 < w:
                out.append((r, c1, "●", 1))
            if 0 <= c2 < w:
                out.append((r, c2, "●", 4))
            if abs(math.sin(phase)) < 0.3 and 0 <= min(c1, c2) and max(c1, c2) < w:
                mc = (c1 + c2) // 2
                if 0 <= mc < w:
                    out.append((r, mc, "─", 2))

    elif "collider" in name.lower() or "hadron" in name.lower():
        cx, cy = w // 2, h // 2
        radius = min(cx - 1, cy - 1, 8)
        for angle_i in range(max(1, int(radius * 6))):
            a = angle_i * 2 * math.pi / (radius * 6)
            r = int(cy + math.sin(a) * radius * 0.8)
            c = int(cx + math.cos(a) * radius)
            if 0 <= r < h and 0 <= c < w:
                out.append((r, c, "·", 7))
        # Particles orbiting
        for i in range(2):
            a = t * (3 + i) + i * math.pi
            r = int(cy + math.sin(a) * radius * 0.8)
            c = int(cx + math.cos(a) * radius)
            if 0 <= r < h and 0 <= c < w:
                out.append((r, c, "●", 1 if i == 0 else 4))

    else:
        # Default: Game of Life glider animation
        glider_frames = [
            [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)],
            [(0, 2), (1, 0), (1, 2), (2, 1), (2, 2)],
            [(0, 1), (1, 2), (1, 3), (2, 1), (2, 2)],  # shifted
        ]
        frame = glider_frames[tick % len(glider_frames)]
        offset_r = (tick // 3) % max(1, h - 4)
        offset_c = (tick // 3) % max(1, w - 4)
        for dr, dc in frame:
            r, c = (offset_r + dr) % h, (offset_c + dc) % w
            out.append((r, c, "██"[:1], 2))
        # Add some static cells for atmosphere
        random.seed(123)
        for _ in range(15):
            r, c = random.randint(0, h - 1), random.randint(0, w - 1)
            if random.random() < 0.5:
                out.append((r, c, "·", 7))

    return out


# ── Favorites persistence ──

def _load_favorites():
    """Load favorite mode names from disk."""
    try:
        with open(FAVORITES_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return set()


def _save_favorites(favorites):
    """Save favorite mode names to disk."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    try:
        with open(FAVORITES_FILE, "w") as f:
            json.dump(sorted(favorites), f)
    except OSError:
        pass


# ── ASCII art banner ──

BANNER = [
    "╔═══════════════════════════════════════════════════════════╗",
    "║   ██╗     ██╗███████╗███████╗    ███████╗██╗███╗   ███╗  ║",
    "║   ██║     ██║██╔════╝██╔════╝    ██╔════╝██║████╗ ████║  ║",
    "║   ██║     ██║█████╗  █████╗      ███████╗██║██╔████╔██║  ║",
    "║   ██║     ██║██╔══╝  ██╔══╝      ╚════██║██║██║╚██╔╝██║  ║",
    "║   ███████╗██║██║     ███████╗    ███████║██║██║ ╚═╝ ██║  ║",
    "║   ╚══════╝╚═╝╚═╝     ╚══════╝    ╚══════╝╚═╝╚═╝     ╚═╝  ║",
    "╚═══════════════════════════════════════════════════════════╝",
]

BANNER_SMALL = [
    "┌─────────────────────────────────┐",
    "│  L I F E   S I M U L A T O R   │",
    "└─────────────────────────────────┘",
]

# Category icons for visual flair
CATEGORY_ICONS = {
    "Classic CA": "⬡",
    "Particle & Swarm": "◎",
    "Physics & Waves": "〜",
    "Fluid Dynamics": "≈",
    "Chemical & Biological": "◉",
    "Game Theory & Social": "⚖",
    "Fractals & Chaos": "❋",
    "Procedural & Computational": "⚙",
    "Complex Simulations": "◈",
    "Meta Modes": "◇",
    "Audio & Visual": "♫",
    "Physics & Math": "∑",
}


def register(App):
    """Register dashboard methods on the App class."""
    App._dashboard_init = _dashboard_init
    App._handle_dashboard_key = _handle_dashboard_key
    App._draw_dashboard = _draw_dashboard
    App._dashboard_get_visible_items = _dashboard_get_visible_items
    App._dashboard_toggle_favorite = _dashboard_toggle_favorite
    App._dashboard_launch_selected = _dashboard_launch_selected


def _dashboard_init(self):
    """Initialize dashboard state."""
    self.dashboard = True
    self.dashboard_sel = 0
    self.dashboard_scroll = 0
    self.dashboard_search = ""
    self.dashboard_category_filter = None  # None = all, str = specific category
    self.dashboard_favorites = _load_favorites()
    self.dashboard_show_favorites_only = False
    self.dashboard_preview_tick = 0
    self.dashboard_last_preview_time = 0.0
    self.dashboard_tab = 0  # 0=browse, 1=favorites


def _dashboard_get_visible_items(self):
    """Get filtered/sorted list of modes for current view."""
    items = list(MODE_REGISTRY)

    # Favorites-only filter
    if self.dashboard_show_favorites_only:
        items = [m for m in items if m["name"] in self.dashboard_favorites]

    # Category filter
    if self.dashboard_category_filter:
        items = [m for m in items if m["category"] == self.dashboard_category_filter]

    # Search filter
    if self.dashboard_search:
        q = self.dashboard_search.lower()
        items = [
            m for m in items
            if q in m["name"].lower() or q in m["desc"].lower() or q in m["category"].lower()
        ]

    return items


def _dashboard_toggle_favorite(self):
    """Toggle favorite status of the currently selected mode."""
    items = self._dashboard_get_visible_items()
    if not items or self.dashboard_sel >= len(items):
        return
    name = items[self.dashboard_sel]["name"]
    if name in self.dashboard_favorites:
        self.dashboard_favorites.discard(name)
    else:
        self.dashboard_favorites.add(name)
    _save_favorites(self.dashboard_favorites)


def _dashboard_launch_selected(self):
    """Launch the currently selected mode from the dashboard."""
    items = self._dashboard_get_visible_items()
    if not items or self.dashboard_sel >= len(items):
        return
    entry = items[self.dashboard_sel]
    self.dashboard = False
    self._exit_current_modes()
    if entry["enter"] is not None:
        enter_fn = getattr(self, entry["enter"], None)
        if enter_fn:
            enter_fn()
    else:
        self._flash("Game of Life (default mode)")


def _handle_dashboard_key(self, key):
    """Handle input on the dashboard screen. Returns True if consumed."""
    if key == -1:
        return True

    items = self._dashboard_get_visible_items()
    n = len(items)

    # Navigation
    nav_up = key == curses.KEY_UP or (key == ord("k") and not self.dashboard_search)
    nav_down = key == curses.KEY_DOWN or (key == ord("j") and not self.dashboard_search)

    if nav_up:
        if n > 0:
            self.dashboard_sel = (self.dashboard_sel - 1) % n
        return True
    if nav_down:
        if n > 0:
            self.dashboard_sel = (self.dashboard_sel + 1) % n
        return True

    if key == curses.KEY_PPAGE:
        if n > 0:
            self.dashboard_sel = max(0, self.dashboard_sel - 10)
        return True
    if key == curses.KEY_NPAGE:
        if n > 0:
            self.dashboard_sel = min(n - 1, self.dashboard_sel + 10)
        return True
    if key == curses.KEY_HOME:
        self.dashboard_sel = 0
        return True
    if key == curses.KEY_END:
        if n > 0:
            self.dashboard_sel = n - 1
        return True

    # Enter = launch
    if key in (10, 13, curses.KEY_ENTER):
        self._dashboard_launch_selected()
        return True

    # F = toggle favorite
    if key == ord("f") and not self.dashboard_search:
        self._dashboard_toggle_favorite()
        return True

    # Tab = toggle favorites-only view
    if key == 9:  # Tab
        self.dashboard_show_favorites_only = not self.dashboard_show_favorites_only
        self.dashboard_sel = 0
        self.dashboard_scroll = 0
        return True

    # Ctrl+A = cycle category filter
    if key == 1:  # Ctrl+A
        cats = [None] + list(dict.fromkeys(m["category"] for m in MODE_REGISTRY))
        if self.dashboard_category_filter in cats:
            idx = cats.index(self.dashboard_category_filter)
            self.dashboard_category_filter = cats[(idx + 1) % len(cats)]
        else:
            self.dashboard_category_filter = None
        self.dashboard_sel = 0
        self.dashboard_scroll = 0
        return True

    # Escape clears search first, then exits dashboard
    if key == 27:
        if self.dashboard_search:
            self.dashboard_search = ""
            self.dashboard_sel = 0
            self.dashboard_scroll = 0
            return True
        if self.dashboard_show_favorites_only:
            self.dashboard_show_favorites_only = False
            self.dashboard_sel = 0
            self.dashboard_scroll = 0
            return True
        if self.dashboard_category_filter:
            self.dashboard_category_filter = None
            self.dashboard_sel = 0
            self.dashboard_scroll = 0
            return True
        # Exit dashboard to default Game of Life
        self.dashboard = False
        self._flash("Game of Life (default mode)")
        return True

    # M opens old mode browser (hidden shortcut)
    if key == ord("M") and not self.dashboard_search:
        self.dashboard = False
        self.mode_browser = True
        self.mode_browser_search = ""
        self.mode_browser_sel = 0
        self.mode_browser_scroll = 0
        self.mode_browser_filtered = list(MODE_REGISTRY)
        return True

    # Backspace
    if key in (curses.KEY_BACKSPACE, 127, 8):
        if self.dashboard_search:
            self.dashboard_search = self.dashboard_search[:-1]
            self.dashboard_sel = 0
            self.dashboard_scroll = 0
        return True

    # ? = help
    if key == ord("?") and not self.dashboard_search:
        self.dashboard = False
        self.show_help = True
        return True

    # q = quit
    if key == ord("q") and not self.dashboard_search:
        raise KeyboardInterrupt

    # Printable → search
    if 32 <= key <= 126:
        self.dashboard_search += chr(key)
        self.dashboard_sel = 0
        self.dashboard_scroll = 0
        return True

    return True


def _draw_dashboard(self, max_y, max_x):
    """Draw the full dashboard screen."""
    now = time.monotonic()
    # Animate preview at ~10fps
    if now - self.dashboard_last_preview_time > 0.1:
        self.dashboard_preview_tick += 1
        self.dashboard_last_preview_time = now

    items = self._dashboard_get_visible_items()
    n = len(items)

    # Clamp selection
    if n > 0:
        self.dashboard_sel = min(self.dashboard_sel, n - 1)
    else:
        self.dashboard_sel = 0

    # ── Layout ──
    # Use full width. Left panel: mode list. Right panel: preview + info.
    preview_w = min(max(20, max_x // 3), 40)
    list_w = max_x - preview_w - 1  # 1 for divider

    # ── Banner ──
    banner = BANNER if max_x >= 65 else BANNER_SMALL
    banner_y = 0
    for i, line in enumerate(banner):
        y = banner_y + i
        if y >= max_y:
            break
        text = line[:max_x - 1]
        try:
            self.stdscr.addstr(y, max(0, (list_w - len(line)) // 2), text,
                               curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass

    content_y = len(banner) + 1

    # ── Subtitle / stats ──
    total_modes = len(MODE_REGISTRY)
    n_favorites = len(self.dashboard_favorites)
    n_categories = len(set(m["category"] for m in MODE_REGISTRY))
    subtitle = f" {total_modes} simulation modes │ {n_categories} categories │ {n_favorites} favorites"
    if content_y < max_y:
        try:
            self.stdscr.addstr(content_y, max(0, (list_w - len(subtitle)) // 2),
                               subtitle[:list_w], curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass
    content_y += 1

    # ── Search bar ──
    if self.dashboard_search:
        search_text = f" 🔍 {self.dashboard_search}█"
    else:
        search_text = " Type to search..."
    if content_y < max_y:
        search_attr = curses.color_pair(6) if self.dashboard_search else curses.color_pair(7) | curses.A_DIM
        try:
            bar = f"┌{'─' * (list_w - 3)}┐"
            self.stdscr.addstr(content_y, 1, bar[:list_w - 1], curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass
        content_y += 1
        if content_y < max_y:
            try:
                inner = search_text[:list_w - 5].ljust(list_w - 4)
                self.stdscr.addstr(content_y, 1, f"│{inner}│", search_attr)
            except curses.error:
                pass
        content_y += 1
        if content_y < max_y:
            try:
                bar = f"└{'─' * (list_w - 3)}┘"
                self.stdscr.addstr(content_y, 1, bar[:list_w - 1], curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass
        content_y += 1

    # ── Filter status line ──
    filter_parts = []
    if self.dashboard_show_favorites_only:
        filter_parts.append("★ Favorites")
    if self.dashboard_category_filter:
        icon = CATEGORY_ICONS.get(self.dashboard_category_filter, "")
        filter_parts.append(f"{icon} {self.dashboard_category_filter}")
    if filter_parts:
        filter_line = " │ ".join(filter_parts) + f"  ({n} modes)"
        if content_y < max_y:
            try:
                self.stdscr.addstr(content_y, 2, filter_line[:list_w - 3],
                                   curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass
            content_y += 1

    # ── Mode list (left panel) ──
    list_start_y = content_y
    list_h = max_y - list_start_y - 2  # 2 for footer

    if n == 0:
        if list_start_y < max_y:
            try:
                self.stdscr.addstr(list_start_y + 1, 4, "No matching modes.",
                                   curses.color_pair(1) | curses.A_DIM)
            except curses.error:
                pass
    else:
        # Build display lines with category headers
        lines = []  # (text, color_pair, is_header, entry_index_or_none)
        current_cat = ""
        entry_idx = 0
        for entry in items:
            if entry["category"] != current_cat:
                current_cat = entry["category"]
                if lines:
                    lines.append(("", 0, True, None))
                icon = CATEGORY_ICONS.get(current_cat, "•")
                lines.append((f"  {icon} {current_cat}", 7, True, None))
            is_fav = "★" if entry["name"] in self.dashboard_favorites else " "
            line = f"  {is_fav} {entry['name']}"
            lines.append((line, 6, False, entry_idx))
            entry_idx += 1

        # Map selection to line index
        selectable = [(i, eidx) for i, (_, _, hdr, eidx) in enumerate(lines) if not hdr and eidx is not None]
        sel_line_idx = -1
        for li, eidx in selectable:
            if eidx == self.dashboard_sel:
                sel_line_idx = li
                break

        # Scroll to keep selection visible
        if list_h > 0:
            if sel_line_idx >= 0:
                if sel_line_idx < self.dashboard_scroll:
                    self.dashboard_scroll = sel_line_idx
                elif sel_line_idx >= self.dashboard_scroll + list_h:
                    self.dashboard_scroll = sel_line_idx - list_h + 1
            self.dashboard_scroll = max(0, min(self.dashboard_scroll, max(0, len(lines) - list_h)))

            for vi in range(list_h):
                li = self.dashboard_scroll + vi
                if li >= len(lines):
                    break
                text, cpair, is_header, eidx = lines[li]
                y = list_start_y + vi
                if y >= max_y - 2:
                    break
                if li == sel_line_idx:
                    attr = curses.color_pair(2) | curses.A_REVERSE | curses.A_BOLD
                elif is_header:
                    attr = curses.color_pair(cpair) | curses.A_BOLD if cpair else curses.A_BOLD
                else:
                    attr = curses.color_pair(cpair) if cpair else 0
                try:
                    display_text = text[:list_w - 1].ljust(list_w - 1)
                    self.stdscr.addstr(y, 0, display_text, attr)
                except curses.error:
                    pass

            # Scrollbar
            if len(lines) > list_h:
                sb_frac = self.dashboard_scroll / max(1, len(lines) - list_h)
                sb_pos = list_start_y + int(sb_frac * (list_h - 1))
                try:
                    self.stdscr.addstr(min(sb_pos, max_y - 3), list_w - 1, "█",
                                       curses.color_pair(7))
                except curses.error:
                    pass

    # ── Vertical divider ──
    div_x = list_w
    for y in range(content_y, max_y - 1):
        try:
            self.stdscr.addstr(y, div_x, "│", curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass

    # ── Right panel: Preview + Info ──
    panel_x = div_x + 1
    panel_w = max_x - panel_x - 1
    if panel_w < 5:
        # Terminal too narrow for preview
        pass
    elif n > 0 and self.dashboard_sel < n:
        entry = items[self.dashboard_sel]
        # Mode name
        py = content_y
        if py < max_y - 1:
            name_text = entry["name"][:panel_w]
            try:
                self.stdscr.addstr(py, panel_x + 1, name_text,
                                   curses.color_pair(2) | curses.A_BOLD)
            except curses.error:
                pass
            py += 1

        # Category
        if py < max_y - 1:
            icon = CATEGORY_ICONS.get(entry["category"], "")
            cat_text = f"{icon} {entry['category']}"[:panel_w]
            try:
                self.stdscr.addstr(py, panel_x + 1, cat_text,
                                   curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass
            py += 1

        # Description (word-wrapped)
        if py < max_y - 1:
            desc = entry["desc"]
            wrap_w = panel_w - 2
            if wrap_w > 5:
                words = desc.split()
                line = ""
                for word in words:
                    if len(line) + len(word) + 1 > wrap_w:
                        if py < max_y - 1:
                            try:
                                self.stdscr.addstr(py, panel_x + 1, line,
                                                   curses.color_pair(6))
                            except curses.error:
                                pass
                            py += 1
                        line = word
                    else:
                        line = f"{line} {word}" if line else word
                if line and py < max_y - 1:
                    try:
                        self.stdscr.addstr(py, panel_x + 1, line[:panel_w],
                                           curses.color_pair(6))
                    except curses.error:
                        pass
                    py += 1

        # Hotkey
        py += 1
        if py < max_y - 1 and entry["key"] != "—":
            key_text = f"Hotkey: [{entry['key']}]"
            try:
                self.stdscr.addstr(py, panel_x + 1, key_text[:panel_w],
                                   curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass
            py += 1

        # Favorite status
        if py < max_y - 1:
            fav_text = "★ Favorite" if entry["name"] in self.dashboard_favorites else "  Press 'f' to favorite"
            fav_attr = curses.color_pair(3) | curses.A_BOLD if entry["name"] in self.dashboard_favorites else curses.color_pair(7) | curses.A_DIM
            try:
                self.stdscr.addstr(py, panel_x + 1, fav_text[:panel_w], fav_attr)
            except curses.error:
                pass
            py += 1

        # ── Live Preview ──
        py += 1
        preview_top = py
        preview_label = "─ Preview ─"
        if py < max_y - 1:
            try:
                self.stdscr.addstr(py, panel_x + 1, preview_label[:panel_w],
                                   curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass
            py += 1

        preview_h = max(3, max_y - py - 3)
        preview_w_actual = max(3, panel_w - 2)

        # Draw preview border
        if py < max_y - 1:
            try:
                border_top = "┌" + "─" * min(preview_w_actual, panel_w - 2) + "┐"
                self.stdscr.addstr(py, panel_x, border_top[:panel_w],
                                   curses.color_pair(7) | curses.A_DIM)
            except curses.error:
                pass
            py += 1

        preview_start_y = py
        preview_end_y = min(py + preview_h, max_y - 3)
        actual_preview_h = preview_end_y - preview_start_y

        # Draw preview content
        if actual_preview_h > 0 and preview_w_actual > 0:
            # Clear preview area with side borders
            for row in range(preview_start_y, preview_end_y):
                if row >= max_y - 1:
                    break
                try:
                    line_content = "│" + " " * min(preview_w_actual, panel_w - 2) + "│"
                    self.stdscr.addstr(row, panel_x, line_content[:panel_w],
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

            # Generate and render preview
            preview_pixels = _preview_static(entry["name"], self.dashboard_preview_tick,
                                             actual_preview_h, preview_w_actual)
            for pr, pc, ch, cp in preview_pixels:
                screen_y = preview_start_y + pr
                screen_x = panel_x + 1 + pc
                if preview_start_y <= screen_y < preview_end_y and panel_x < screen_x < panel_x + panel_w - 1:
                    try:
                        self.stdscr.addstr(screen_y, screen_x, ch[:1],
                                           curses.color_pair(cp))
                    except curses.error:
                        pass

            # Bottom border
            bottom_y = preview_end_y
            if bottom_y < max_y - 1:
                try:
                    border_bot = "└" + "─" * min(preview_w_actual, panel_w - 2) + "┘"
                    self.stdscr.addstr(bottom_y, panel_x, border_bot[:panel_w],
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

    # ── Footer ──
    footer_parts = [
        "↑↓ Navigate",
        "Enter Launch",
        "f Favorite",
        "Tab Favs",
        "Ctrl+A Category",
        "? Help",
        "Esc Exit",
    ]
    footer = " │ ".join(footer_parts)
    if max_y > 1:
        try:
            self.stdscr.addstr(max_y - 1, 0, footer[:max_x - 1].ljust(max_x - 1),
                               curses.color_pair(6) | curses.A_REVERSE)
        except curses.error:
            pass
