"""Topology Mode — run grid simulations on non-Euclidean surfaces.

Ctrl+W cycles the grid's boundary conditions through plane, torus, Klein
bottle, Möbius strip and projective plane.

Supported topologies:
  plane            – hard edges, no wrapping (finite flat sheet)
  torus            – both axes wrap (default, the classic modulo behavior)
  klein_bottle     – columns wrap; rows wrap with a horizontal flip
  möbius_strip     – columns wrap with a vertical flip; rows have hard edges
  projective_plane – both axes wrap with opposite-axis flips
"""
import curses

from life.grid import Grid

# ── Topology metadata ───────────────────────────────────────────────────────

TOPOLOGY_INFO = {
    Grid.TOPO_PLANE: {
        "label": "Plane",
        "symbol": "▭",
        "desc": "Flat sheet with hard edges — no wrapping",
        "edges": {"top": "wall", "bottom": "wall", "left": "wall", "right": "wall"},
    },
    Grid.TOPO_TORUS: {
        "label": "Torus",
        "symbol": "◎",
        "desc": "Both axes wrap seamlessly — donut surface",
        "edges": {"top": "wrap-v", "bottom": "wrap-v", "left": "wrap-h", "right": "wrap-h"},
    },
    Grid.TOPO_KLEIN: {
        "label": "Klein Bottle",
        "symbol": "♾",
        "desc": "Rows wrap with horizontal flip — non-orientable",
        "edges": {"top": "twist-h", "bottom": "twist-h", "left": "wrap-h", "right": "wrap-h"},
    },
    Grid.TOPO_MOBIUS: {
        "label": "Möbius Strip",
        "symbol": "∞",
        "desc": "Columns wrap with vertical flip — one-sided surface",
        "edges": {"top": "wall", "bottom": "wall", "left": "twist-v", "right": "twist-v"},
    },
    Grid.TOPO_PROJECTIVE: {
        "label": "Projective Plane",
        "symbol": "⊕",
        "desc": "Both axes wrap with flips — fully non-orientable",
        "edges": {"top": "twist-h", "bottom": "twist-h", "left": "twist-v", "right": "twist-v"},
    },
}

# ── Topology cycling ────────────────────────────────────────────────────────


def _topology_cycle(self, direction=1):
    """Switch the grid to the next (or previous) topology."""
    topo_list = Grid.TOPOLOGIES
    grid = self.grid
    cur_idx = topo_list.index(grid.topology) if grid.topology in topo_list else 0
    new_idx = (cur_idx + direction) % len(topo_list)
    new_topo = topo_list[new_idx]
    grid.topology = new_topo

    info = TOPOLOGY_INFO[new_topo]
    self._flash(f"{info['symbol']} Topology: {info['label']} — {info['desc']}")


def _topology_set(self, topo_name):
    """Switch the grid to the named topology."""
    if topo_name in Grid.TOPOLOGIES:
        self.grid.topology = topo_name
        info = TOPOLOGY_INFO[topo_name]
        self._flash(f"{info['symbol']} Topology: {info['label']} — {info['desc']}")


# ── Key handling ────────────────────────────────────────────────────────────

def _topology_handle_key(self, key):
    """Handle topology keys. Return True if the key was consumed."""
    if key == 23:  # Ctrl+W
        _topology_cycle(self, 1)
        return True
    return False


# ── Visual indicators ───────────────────────────────────────────────────────

def _draw_topology_indicator(self, max_y, max_x):
    """Draw the topology name in the top-right corner."""
    topo = self.grid.topology
    if topo == Grid.TOPO_TORUS:
        return  # Torus is default — no indicator needed

    info = TOPOLOGY_INFO.get(topo)
    if not info:
        return

    label = f" {info['symbol']} {info['label']} "
    x = max(0, max_x - len(label) - 1)
    y = 0

    try:
        self.stdscr.addstr(y, x, label, curses.color_pair(5) | curses.A_BOLD)
    except curses.error:
        pass


def _draw_topology_edges(self, max_y, max_x):
    """Draw border characters that show how each edge wraps.

      wall   → thin line (─ │)
      wrap   → double line (═ ║)
      twist  → wavy line (≈ ┃), which flips the other axis
    """
    topo = self.grid.topology
    if topo == Grid.TOPO_TORUS:
        return  # Default — no special indicators

    info = TOPOLOGY_INFO.get(topo)
    if not info:
        return

    edges = info["edges"]
    if max_y < 3 or max_x < 4:
        return

    # The bottom two rows belong to the status and hint bars.
    draw_h = max_y - 2
    draw_w = max_x - 1

    # Color: walls=dim, wraps=cyan, twists=magenta
    try:
        wall_attr = curses.color_pair(0) | curses.A_DIM
        wrap_attr = curses.color_pair(6) | curses.A_DIM
        twist_attr = curses.color_pair(3) | curses.A_BOLD
    except Exception:
        wall_attr = curses.A_DIM
        wrap_attr = curses.A_DIM
        twist_attr = curses.A_BOLD

    def _edge_attr(edge_type):
        if edge_type == "wall":
            return wall_attr
        if edge_type.startswith("wrap"):
            return wrap_attr
        return twist_attr

    def _hchar(edge_type):
        if edge_type == "wall":
            return "─"
        if edge_type.startswith("wrap"):
            return "═"
        return "≈"

    def _vchar(edge_type):
        if edge_type == "wall":
            return "│"
        if edge_type.startswith("wrap"):
            return "║"
        return "┃"

    # Draw top edge
    top_type = edges["top"]
    hc = _hchar(top_type)
    attr = _edge_attr(top_type)
    for x in range(1, min(draw_w - 1, max_x - 1)):
        try:
            self.stdscr.addstr(0, x, hc, attr)
        except curses.error:
            pass

    # Draw bottom edge
    bot_type = edges["bottom"]
    hc = _hchar(bot_type)
    attr = _edge_attr(bot_type)
    bot_y = min(draw_h - 1, max_y - 2)
    if bot_y > 0:
        for x in range(1, min(draw_w - 1, max_x - 1)):
            try:
                self.stdscr.addstr(bot_y, x, hc, attr)
            except curses.error:
                pass

    # Draw left edge
    left_type = edges["left"]
    vc = _vchar(left_type)
    attr = _edge_attr(left_type)
    for y in range(1, min(draw_h - 1, max_y - 1)):
        try:
            self.stdscr.addstr(y, 0, vc, attr)
        except curses.error:
            pass

    # Draw right edge
    right_type = edges["right"]
    vc = _vchar(right_type)
    attr = _edge_attr(right_type)
    right_x = min(draw_w - 1, max_x - 2)
    if right_x > 0:
        for y in range(1, min(draw_h - 1, max_y - 1)):
            try:
                self.stdscr.addstr(y, right_x, vc, attr)
            except curses.error:
                pass

    # Draw corner indicators
    corners = [
        (0, 0),
        (0, min(draw_w - 1, max_x - 2)),
        (min(draw_h - 1, max_y - 2), 0),
        (min(draw_h - 1, max_y - 2), min(draw_w - 1, max_x - 2)),
    ]
    for cy, cx in corners:
        try:
            if cx >= 0 and cy >= 0:
                self.stdscr.addstr(cy, cx, "┼", twist_attr if "twist" in edges["top"] or "twist" in edges["left"] else wrap_attr)
        except curses.error:
            pass

    # Draw twist arrows at midpoints for twist edges
    mid_x = draw_w // 2
    mid_y = draw_h // 2

    if "twist" in top_type:
        try:
            self.stdscr.addstr(0, max(1, mid_x - 2), "⟵⟶", twist_attr)
        except curses.error:
            pass
    if "twist" in bot_type:
        try:
            self.stdscr.addstr(bot_y, max(1, mid_x - 2), "⟵⟶", twist_attr)
        except curses.error:
            pass
    if "twist" in left_type:
        try:
            self.stdscr.addstr(max(1, mid_y - 1), 0, "↕", twist_attr)
        except curses.error:
            pass
    if "twist" in right_type:
        try:
            self.stdscr.addstr(max(1, mid_y - 1), right_x, "↕", twist_attr)
        except curses.error:
            pass


# ── Registration ────────────────────────────────────────────────────────────

def register(App):
    """Register topology methods on the App class."""
    App._topology_cycle = _topology_cycle
    App._topology_set = _topology_set
    App._topology_handle_key = _topology_handle_key
    App._draw_topology_indicator = _draw_topology_indicator
    App._draw_topology_edges = _draw_topology_edges
