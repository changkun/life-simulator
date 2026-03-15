"""Mode: graph_ca — Game of Life on arbitrary network topologies.

Runs CA rules on non-grid structures: small-world networks, scale-free
(Barabasi-Albert) networks, random (Erdos-Renyi) graphs, ring lattices,
star graphs, and trees. Visualize with a force-directed ASCII layout where
nodes are colored by cell state/age. Includes presets for different network
types and sizes, live topology switching, and real-time metrics (alive ratio,
clustering coefficient, average path length).
"""
import curses
import math
import random
import time

# ── Network topology generators ──────────────────────────────────

GRAPH_TOPOLOGIES = [
    ("Ring Lattice", "Regular ring where each node connects to K nearest neighbors", "ring"),
    ("Small-World (WS)", "Watts-Strogatz: ring lattice with random rewiring (p=0.3)", "smallworld"),
    ("Scale-Free (BA)", "Barabasi-Albert preferential attachment network", "scalefree"),
    ("Random (ER)", "Erdos-Renyi random graph with edge probability p", "random"),
    ("Star Graph", "Central hub connected to all other nodes", "star"),
    ("Binary Tree", "Complete binary tree structure", "tree"),
    ("Grid 2D", "Standard 2D lattice graph (for comparison)", "grid2d"),
    ("Caveman Graph", "Clusters of cliques with inter-cluster links", "caveman"),
]

GRAPH_RULES = [
    ("B3/S23 (Life)", "Classic Conway's Game of Life rules", {3}, {2, 3}),
    ("B2/S34 (Pulse)", "Pulsing growth for high-degree nodes", {2}, {3, 4}),
    ("B3/S234 (Coral)", "Slow coral-like growth", {3}, {2, 3, 4}),
    ("B23/S3 (Sparse)", "Sparse dynamics — hard to sustain", {2, 3}, {3}),
    ("B1/S12 (Dense)", "Very active — suited for low-degree graphs", {1}, {1, 2}),
    ("B2/S23 (Spread)", "Fast spreading with moderate survival", {2}, {2, 3}),
    ("B34/S345 (Hardy)", "Tough survivors on high-connectivity nets", {3, 4}, {3, 4, 5}),
    ("B2/S (Seeds)", "Explosive — no survival, pure birth", {2}, set()),
]


def _build_ring(n, k=4):
    """Ring lattice: each node connected to K/2 neighbors on each side."""
    adj = {i: [] for i in range(n)}
    half_k = max(1, k // 2)
    for i in range(n):
        for j in range(1, half_k + 1):
            right = (i + j) % n
            left = (i - j) % n
            if right not in adj[i]:
                adj[i].append(right)
            if i not in adj[right]:
                adj[right].append(i)
            if left not in adj[i]:
                adj[i].append(left)
            if i not in adj[left]:
                adj[left].append(i)
    return n, adj


def _build_smallworld(n, k=4, p=0.3):
    """Watts-Strogatz small-world: start with ring, rewire with probability p."""
    n, adj = _build_ring(n, k)
    half_k = max(1, k // 2)
    for i in range(n):
        for j in range(1, half_k + 1):
            if random.random() < p:
                old = (i + j) % n
                # Remove old edge
                if old in adj[i]:
                    adj[i].remove(old)
                if i in adj[old]:
                    adj[old].remove(i)
                # Pick new target (not self, not already connected)
                attempts = 0
                while attempts < 20:
                    new_target = random.randint(0, n - 1)
                    if new_target != i and new_target not in adj[i]:
                        adj[i].append(new_target)
                        adj[new_target].append(i)
                        break
                    attempts += 1
                else:
                    # Restore if we couldn't rewire
                    if old not in adj[i]:
                        adj[i].append(old)
                    if i not in adj[old]:
                        adj[old].append(i)
    return n, adj


def _build_scalefree(n, m=2):
    """Barabasi-Albert scale-free network via preferential attachment."""
    adj = {i: [] for i in range(n)}
    # Start with a small complete graph of m+1 nodes
    init = min(m + 1, n)
    for i in range(init):
        for j in range(i + 1, init):
            adj[i].append(j)
            adj[j].append(i)

    # Degree list for preferential attachment (each edge adds both endpoints)
    degree_list = []
    for i in range(init):
        for _ in range(len(adj[i])):
            degree_list.append(i)

    for new_node in range(init, n):
        targets = set()
        if not degree_list:
            # Connect to node 0 if degree_list is empty
            targets.add(0)
        else:
            attempts = 0
            while len(targets) < min(m, new_node) and attempts < 100:
                pick = degree_list[random.randint(0, len(degree_list) - 1)]
                if pick != new_node:
                    targets.add(pick)
                attempts += 1
        for t in targets:
            adj[new_node].append(t)
            adj[t].append(new_node)
            degree_list.append(new_node)
            degree_list.append(t)

    return n, adj


def _build_random(n, p=0.08):
    """Erdos-Renyi random graph: each edge exists with probability p."""
    adj = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if random.random() < p:
                adj[i].append(j)
                adj[j].append(i)
    return n, adj


def _build_star(n):
    """Star graph: node 0 is the hub, all others connect only to it."""
    adj = {i: [] for i in range(n)}
    for i in range(1, n):
        adj[0].append(i)
        adj[i].append(0)
    return n, adj


def _build_tree(n):
    """Complete binary tree."""
    adj = {i: [] for i in range(n)}
    for i in range(n):
        left = 2 * i + 1
        right = 2 * i + 2
        if left < n:
            adj[i].append(left)
            adj[left].append(i)
        if right < n:
            adj[i].append(right)
            adj[right].append(i)
    return n, adj


def _build_grid2d(n):
    """2D grid graph (closest square)."""
    side = max(2, int(math.sqrt(n)))
    actual_n = side * side
    adj = {i: [] for i in range(actual_n)}
    for r in range(side):
        for c in range(side):
            idx = r * side + c
            if c + 1 < side:
                nb = r * side + (c + 1)
                adj[idx].append(nb)
                adj[nb].append(idx)
            if r + 1 < side:
                nb = (r + 1) * side + c
                adj[idx].append(nb)
                adj[nb].append(idx)
    return actual_n, adj


def _build_caveman(n, clique_size=5):
    """Caveman graph: k cliques connected in a ring."""
    num_cliques = max(2, n // clique_size)
    actual_n = num_cliques * clique_size
    adj = {i: [] for i in range(actual_n)}
    # Build internal clique edges
    for c in range(num_cliques):
        base = c * clique_size
        for i in range(clique_size):
            for j in range(i + 1, clique_size):
                adj[base + i].append(base + j)
                adj[base + j].append(base + i)
    # Connect adjacent cliques with one inter-link
    for c in range(num_cliques):
        a = c * clique_size
        b = ((c + 1) % num_cliques) * clique_size
        if b not in adj[a]:
            adj[a].append(b)
            adj[b].append(a)
    return actual_n, adj


_TOPOLOGY_BUILDERS = {
    "ring": lambda n: _build_ring(n, 4),
    "smallworld": lambda n: _build_smallworld(n, 4, 0.3),
    "scalefree": lambda n: _build_scalefree(n, 2),
    "random": lambda n: _build_random(n, 0.08),
    "star": _build_star,
    "tree": _build_tree,
    "grid2d": _build_grid2d,
    "caveman": lambda n: _build_caveman(n, 5),
}


# ── Force-directed layout ────────────────────────────────────────

def _force_layout(n, adj, width, height, iterations=80):
    """Simple force-directed layout returning (x, y) positions in [0,1]x[0,1]."""
    # Initialize positions in a circle
    pos_x = [0.0] * n
    pos_y = [0.0] * n
    for i in range(n):
        angle = 2.0 * math.pi * i / max(n, 1)
        pos_x[i] = 0.5 + 0.35 * math.cos(angle)
        pos_y[i] = 0.5 + 0.35 * math.sin(angle)

    if n <= 1:
        return pos_x, pos_y

    k = math.sqrt(1.0 / max(n, 1))  # optimal distance
    temp = 0.1

    for _it in range(iterations):
        dx = [0.0] * n
        dy = [0.0] * n

        # Repulsive forces (O(n^2) but n is small for terminal)
        for i in range(n):
            for j in range(i + 1, n):
                diffx = pos_x[i] - pos_x[j]
                diffy = pos_y[i] - pos_y[j]
                dist = math.sqrt(diffx * diffx + diffy * diffy) + 1e-6
                rep = (k * k) / dist
                fx = (diffx / dist) * rep
                fy = (diffy / dist) * rep
                dx[i] += fx
                dy[i] += fy
                dx[j] -= fx
                dy[j] -= fy

        # Attractive forces along edges
        for i in range(n):
            for j in adj.get(i, []):
                if j > i:
                    diffx = pos_x[i] - pos_x[j]
                    diffy = pos_y[i] - pos_y[j]
                    dist = math.sqrt(diffx * diffx + diffy * diffy) + 1e-6
                    att = (dist * dist) / k
                    fx = (diffx / dist) * att
                    fy = (diffy / dist) * att
                    dx[i] -= fx
                    dy[i] -= fy
                    dx[j] += fx
                    dy[j] += fy

        # Apply displacement with temperature limit
        for i in range(n):
            disp = math.sqrt(dx[i] * dx[i] + dy[i] * dy[i]) + 1e-6
            scale = min(disp, temp) / disp
            pos_x[i] += dx[i] * scale
            pos_y[i] += dy[i] * scale
            # Keep in bounds
            pos_x[i] = max(0.02, min(0.98, pos_x[i]))
            pos_y[i] = max(0.02, min(0.98, pos_y[i]))

        temp *= 0.95  # cool down

    return pos_x, pos_y


# ── Graph metrics ─────────────────────────────────────────────────

def _clustering_coefficient(n, adj):
    """Average local clustering coefficient."""
    if n == 0:
        return 0.0
    total = 0.0
    count = 0
    for i in range(n):
        neighbors = adj.get(i, [])
        ki = len(neighbors)
        if ki < 2:
            continue
        # Count edges between neighbors
        triangles = 0
        nb_set = set(neighbors)
        for a in neighbors:
            for b in adj.get(a, []):
                if b in nb_set and b > a:
                    triangles += 1
        possible = ki * (ki - 1) / 2
        total += triangles / possible if possible > 0 else 0.0
        count += 1
    return total / count if count > 0 else 0.0


def _avg_path_length_sample(n, adj, samples=50):
    """Estimate average shortest path length via BFS from random sample nodes."""
    if n < 2:
        return 0.0
    total_dist = 0
    total_pairs = 0
    sample_nodes = random.sample(range(n), min(samples, n))
    for src in sample_nodes:
        visited = {src: 0}
        queue = [src]
        qi = 0
        while qi < len(queue):
            curr = queue[qi]
            qi += 1
            for nb in adj.get(curr, []):
                if nb not in visited:
                    visited[nb] = visited[curr] + 1
                    queue.append(nb)
                    total_dist += visited[nb]
                    total_pairs += 1
    return total_dist / total_pairs if total_pairs > 0 else 0.0


def _degree_stats(n, adj):
    """Return (avg_degree, max_degree)."""
    if n == 0:
        return 0.0, 0
    degrees = [len(adj.get(i, [])) for i in range(n)]
    return sum(degrees) / n, max(degrees)


# ── Edge drawing helpers ──────────────────────────────────────────

_EDGE_CHARS = {
    (0, 1): "-", (0, -1): "-",
    (1, 0): "|", (-1, 0): "|",
    (1, 1): "\\", (-1, -1): "\\",
    (1, -1): "/", (-1, 1): "/",
}


def _draw_edge_line(scr, r1, c1, r2, c2, max_y, max_x, attr):
    """Draw an ASCII edge between two screen positions using Bresenham."""
    dr = r2 - r1
    dc = c2 - c1
    steps = max(abs(dr), abs(dc))
    if steps == 0:
        return
    # Only draw a subset of points for long edges to avoid clutter
    step_inc = max(1, steps // 12)
    for s in range(1, steps, step_inc):
        t = s / steps
        r = int(round(r1 + dr * t))
        c = int(round(c1 + dc * t))
        if 0 <= r < max_y - 2 and 0 <= c < max_x - 1:
            try:
                scr.addstr(r, c, ".", attr)
            except curses.error:
                pass


# ── Mode functions ────────────────────────────────────────────────

def _enter_gca_mode(self):
    """Enter Graph CA mode — show topology selection menu."""
    self.gca_menu = True
    self.gca_menu_phase = "topology"
    self.gca_menu_sel = 0
    self.gca_rule_sel = 0
    self._flash("Graph Cellular Automata — select a network topology")


def _exit_gca_mode(self):
    """Exit Graph CA mode."""
    self.gca_mode = False
    self.gca_menu = False
    self.gca_running = False
    self.gca_n = 0
    self.gca_adj = {}
    self.gca_states = []
    self.gca_ages = []
    self.gca_pos_x = []
    self.gca_pos_y = []
    self._flash("Graph CA OFF")


def _gca_init(self, topo_idx, rule_idx, node_count=None):
    """Initialize the graph and seed cells."""
    name, _desc, topo_key = GRAPH_TOPOLOGIES[topo_idx]
    rname, _rdesc, birth, survive = GRAPH_RULES[rule_idx]

    self.gca_topo_name = name
    self.gca_topo_key = topo_key
    self.gca_topo_idx = topo_idx
    self.gca_rule_name = rname
    self.gca_rule_idx = rule_idx
    self.gca_birth = birth
    self.gca_survive = survive
    self.gca_generation = 0
    self.gca_population = 0
    self.gca_show_edges = True
    self.gca_show_metrics = True

    # Determine node count based on terminal size
    if node_count is None:
        max_y, max_x = self.stdscr.getmaxyx()
        area = max_y * max_x
        node_count = min(120, max(30, area // 40))

    self.gca_node_count = node_count
    builder = _TOPOLOGY_BUILDERS[topo_key]
    self.gca_n, self.gca_adj = builder(node_count)
    n = self.gca_n
    self.gca_states = [False] * n
    self.gca_ages = [0] * n

    # Compute layout
    max_y, max_x = self.stdscr.getmaxyx()
    self.gca_pos_x, self.gca_pos_y = _force_layout(
        n, self.gca_adj, max_x, max_y,
        iterations=min(120, max(40, n))
    )

    # Compute metrics
    self.gca_clustering = _clustering_coefficient(n, self.gca_adj)
    self.gca_avg_path = _avg_path_length_sample(n, self.gca_adj)
    self.gca_avg_deg, self.gca_max_deg = _degree_stats(n, self.gca_adj)

    # Seed: randomly activate ~30% of nodes
    pop = 0
    for i in range(n):
        if random.random() < 0.3:
            self.gca_states[i] = True
            self.gca_ages[i] = 1
            pop += 1
    self.gca_population = pop

    self.gca_running = True
    self.gca_menu = False
    self.gca_mode = True
    self.gca_speed_mult = 1
    self.gca_pop_history = [pop]
    self._flash(f"Graph CA: {name} / {rname} — {n} nodes, space=pause, q=quit")


def _gca_step(self):
    """Advance one generation of the graph CA."""
    n = self.gca_n
    new_states = [False] * n
    new_ages = [0] * n
    pop = 0

    for i in range(n):
        live_nb = 0
        for ni in self.gca_adj.get(i, []):
            if self.gca_states[ni]:
                live_nb += 1

        if self.gca_states[i]:
            if live_nb in self.gca_survive:
                new_states[i] = True
                new_ages[i] = self.gca_ages[i] + 1
                pop += 1
        else:
            if live_nb in self.gca_birth:
                new_states[i] = True
                new_ages[i] = 1
                pop += 1

    self.gca_states = new_states
    self.gca_ages = new_ages
    self.gca_generation += 1
    self.gca_population = pop
    self.gca_pop_history.append(pop)
    if len(self.gca_pop_history) > 100:
        self.gca_pop_history = self.gca_pop_history[-100:]


def _gca_randomize(self, density=0.3):
    """Randomize cell states."""
    n = self.gca_n
    pop = 0
    for i in range(n):
        if random.random() < density:
            self.gca_states[i] = True
            self.gca_ages[i] = 1
            pop += 1
        else:
            self.gca_states[i] = False
            self.gca_ages[i] = 0
    self.gca_population = pop
    self.gca_generation = 0
    self.gca_pop_history = [pop]


def _gca_clear(self):
    """Clear all cells."""
    n = self.gca_n
    self.gca_states = [False] * n
    self.gca_ages = [0] * n
    self.gca_population = 0
    self.gca_generation = 0
    self.gca_pop_history = [0]


# ── Key handling ──────────────────────────────────────────────────

def _handle_gca_menu_key(self, key):
    """Handle keys in the topology/rule selection menu."""
    if key == 27:  # ESC
        self.gca_menu = False
        return True

    if self.gca_menu_phase == "topology":
        n_items = len(GRAPH_TOPOLOGIES)
        if key == curses.KEY_UP:
            self.gca_menu_sel = (self.gca_menu_sel - 1) % n_items
        elif key == curses.KEY_DOWN:
            self.gca_menu_sel = (self.gca_menu_sel + 1) % n_items
        elif key in (10, 13, curses.KEY_ENTER):
            self.gca_menu_phase = "rule"
            self.gca_rule_sel = 0
        elif key == ord("q"):
            self.gca_menu = False
        return True
    elif self.gca_menu_phase == "rule":
        n_items = len(GRAPH_RULES)
        if key == curses.KEY_UP:
            self.gca_rule_sel = (self.gca_rule_sel - 1) % n_items
        elif key == curses.KEY_DOWN:
            self.gca_rule_sel = (self.gca_rule_sel + 1) % n_items
        elif key in (10, 13, curses.KEY_ENTER):
            self._gca_init(self.gca_menu_sel, self.gca_rule_sel)
        elif key == ord("q") or key == 27:
            self.gca_menu_phase = "topology"
        return True

    return True


def _handle_gca_key(self, key):
    """Handle keys during graph CA simulation."""
    if key == ord("q") or key == 27:
        self._exit_gca_mode()
        return True
    if key == ord(" "):
        self.gca_running = not self.gca_running
        return True
    if key == ord("r"):
        self._gca_randomize()
        return True
    if key == ord("c"):
        self._gca_clear()
        return True
    if key == ord("s"):
        self._gca_step()
        return True
    if key == ord("e"):
        self.gca_show_edges = not self.gca_show_edges
        self._flash("Edges " + ("ON" if self.gca_show_edges else "OFF"))
        return True
    if key == ord("m"):
        self.gca_show_metrics = not self.gca_show_metrics
        return True
    if key == ord("n"):
        # Cycle to next rule
        idx = (self.gca_rule_idx + 1) % len(GRAPH_RULES)
        rname, _, birth, survive = GRAPH_RULES[idx]
        self.gca_birth = birth
        self.gca_survive = survive
        self.gca_rule_name = rname
        self.gca_rule_idx = idx
        self._flash(f"Rule: {rname}")
        return True
    if key == ord("t"):
        # Cycle to next topology (rebuild)
        idx = (self.gca_topo_idx + 1) % len(GRAPH_TOPOLOGIES)
        self._gca_init(idx, self.gca_rule_idx, self.gca_node_count)
        return True
    if key in (ord("+"), ord("=")):
        self.gca_node_count = min(200, self.gca_node_count + 10)
        self._gca_init(self.gca_topo_idx, self.gca_rule_idx, self.gca_node_count)
        return True
    if key in (ord("-"), ord("_")):
        self.gca_node_count = max(10, self.gca_node_count - 10)
        self._gca_init(self.gca_topo_idx, self.gca_rule_idx, self.gca_node_count)
        return True
    if key == ord("l"):
        # Re-layout
        max_y, max_x = self.stdscr.getmaxyx()
        self.gca_pos_x, self.gca_pos_y = _force_layout(
            self.gca_n, self.gca_adj, max_x, max_y,
            iterations=min(120, max(40, self.gca_n))
        )
        self._flash("Layout recalculated")
        return True

    return True


# ── Drawing ───────────────────────────────────────────────────────

def _draw_gca_menu(self, max_y, max_x):
    """Draw the topology/rule selection menu."""
    self.stdscr.erase()
    title = "╔══════════════════════════════════════════════╗"
    mid =   "║      GRAPH-BASED CELLULAR AUTOMATA           ║"
    sub =   "║      Game of Life on Network Topologies      ║"
    bot =   "╚══════════════════════════════════════════════╝"

    cy = max_y // 2
    cx = max_x // 2

    for i, line in enumerate([title, mid, sub, bot]):
        r = cy - 12 + i
        c = cx - len(line) // 2
        if 0 <= r < max_y:
            try:
                self.stdscr.addstr(r, max(0, c), line[:max_x - 1],
                                   curses.A_BOLD | curses.color_pair(4))
            except curses.error:
                pass

    if self.gca_menu_phase == "topology":
        hdr = "Select Network Topology (Up/Down, Enter):"
        r = cy - 7
        try:
            self.stdscr.addstr(r, cx - len(hdr) // 2, hdr,
                               curses.A_BOLD | curses.color_pair(3))
        except curses.error:
            pass

        for i, (name, desc, _key) in enumerate(GRAPH_TOPOLOGIES):
            r = cy - 5 + i * 2
            if r >= max_y - 1:
                break
            sel = ">" if i == self.gca_menu_sel else " "
            attr = curses.A_BOLD | curses.color_pair(2) if i == self.gca_menu_sel else curses.A_DIM
            line = f" {sel} {name}"
            try:
                self.stdscr.addstr(r, cx - 24, line[:max_x - 1], attr)
                self.stdscr.addstr(r + 1, cx - 22, desc[:max_x - 1],
                                   curses.A_DIM | curses.color_pair(6))
            except curses.error:
                pass

        # Draw a mini preview of the selected topology
        _draw_mini_graph(self.stdscr, cx + 20, cy - 2,
                         GRAPH_TOPOLOGIES[self.gca_menu_sel][2],
                         max_y, max_x)

    elif self.gca_menu_phase == "rule":
        hdr = "Select CA Rule (Up/Down, Enter):"
        r = cy - 5
        try:
            self.stdscr.addstr(r, cx - len(hdr) // 2, hdr,
                               curses.A_BOLD | curses.color_pair(3))
        except curses.error:
            pass

        for i, (name, desc, _, _) in enumerate(GRAPH_RULES):
            r = cy - 3 + i * 2
            if r >= max_y - 1:
                break
            sel = ">" if i == self.gca_rule_sel else " "
            attr = curses.A_BOLD | curses.color_pair(2) if i == self.gca_rule_sel else curses.A_DIM
            line = f" {sel} {name}"
            try:
                self.stdscr.addstr(r, cx - 20, line[:max_x - 1], attr)
                self.stdscr.addstr(r + 1, cx - 18, desc[:max_x - 1],
                                   curses.A_DIM | curses.color_pair(6))
            except curses.error:
                pass

    foot = "[ESC] back  [q] cancel"
    try:
        self.stdscr.addstr(max_y - 1, cx - len(foot) // 2, foot[:max_x - 1],
                           curses.A_DIM)
    except curses.error:
        pass


def _draw_mini_graph(scr, cx, cy, topo_key, max_y, max_x):
    """Draw a tiny preview of the graph topology."""
    n = 12
    builder = _TOPOLOGY_BUILDERS.get(topo_key, _TOPOLOGY_BUILDERS["ring"])
    actual_n, adj = builder(n)
    radius = 6

    # Simple circular layout for preview
    for i in range(actual_n):
        angle = 2.0 * math.pi * i / actual_n
        px = cx + int(round(radius * math.cos(angle)))
        py = cy + int(round(radius * 0.5 * math.sin(angle)))
        if 0 <= py < max_y and 0 <= px < max_x - 1:
            try:
                scr.addstr(py, px, "O", curses.A_BOLD | curses.color_pair(3))
            except curses.error:
                pass

    # Draw a few edges
    drawn = 0
    for i in range(actual_n):
        a1 = 2.0 * math.pi * i / actual_n
        x1 = cx + radius * math.cos(a1)
        y1 = cy + radius * 0.5 * math.sin(a1)
        for j in adj.get(i, []):
            if j > i and drawn < 20:
                a2 = 2.0 * math.pi * j / actual_n
                x2 = cx + radius * math.cos(a2)
                y2 = cy + radius * 0.5 * math.sin(a2)
                # Draw midpoint
                mx = int(round((x1 + x2) / 2))
                my = int(round((y1 + y2) / 2))
                if 0 <= my < max_y and 0 <= mx < max_x - 1:
                    try:
                        scr.addstr(my, mx, ".", curses.A_DIM)
                    except curses.error:
                        pass
                drawn += 1


def _draw_gca(self, max_y, max_x):
    """Draw the graph CA visualization."""
    self.stdscr.erase()

    n = self.gca_n
    draw_h = max_y - 4  # Leave room for status bars
    draw_w = max_x - 2

    # Metrics panel width
    metrics_w = 30 if self.gca_show_metrics and max_x > 70 else 0
    graph_w = draw_w - metrics_w

    # Map normalized positions to screen coordinates
    screen_r = [0] * n
    screen_c = [0] * n
    for i in range(n):
        screen_c[i] = int(1 + self.gca_pos_x[i] * (graph_w - 2))
        screen_r[i] = int(1 + self.gca_pos_y[i] * (draw_h - 2))

    # Draw edges first (underneath nodes)
    if self.gca_show_edges:
        edge_attr = curses.A_DIM
        drawn_edges = set()
        for i in range(n):
            for j in self.gca_adj.get(i, []):
                edge_key = (min(i, j), max(i, j))
                if edge_key in drawn_edges:
                    continue
                drawn_edges.add(edge_key)
                r1, c1 = screen_r[i], screen_c[i]
                r2, c2 = screen_r[j], screen_c[j]
                _draw_edge_line(self.stdscr, r1, c1, r2, c2,
                                max_y - 2, graph_w, edge_attr)

    # Draw nodes
    for i in range(n):
        r = screen_r[i]
        c = screen_c[i]
        if not (0 <= r < max_y - 2 and 0 <= c < max_x - 1):
            continue

        alive = self.gca_states[i]
        age = self.gca_ages[i]
        degree = len(self.gca_adj.get(i, []))

        if alive:
            # Node character based on degree (hubs are bigger)
            if degree >= 8:
                ch = "@"
            elif degree >= 5:
                ch = "#"
            elif degree >= 3:
                ch = "O"
            else:
                ch = "o"
            color_idx = min(age, 6) if age > 0 else 1
            attr = curses.A_BOLD | curses.color_pair(color_idx)
        else:
            # Dead node — show structure faintly
            if degree >= 5:
                ch = "+"
            else:
                ch = "."
            attr = curses.A_DIM

        try:
            self.stdscr.addstr(r, c, ch, attr)
        except curses.error:
            pass

    # Draw metrics panel on the right
    if self.gca_show_metrics and metrics_w > 0:
        mx = graph_w + 2
        mr = 1
        try:
            self.stdscr.addstr(mr, mx, "--- Metrics ---",
                               curses.A_BOLD | curses.color_pair(4))
            mr += 2
            alive_ratio = self.gca_population / max(n, 1)
            self.stdscr.addstr(mr, mx, f"Alive: {self.gca_population}/{n}",
                               curses.color_pair(2))
            mr += 1
            self.stdscr.addstr(mr, mx, f"Ratio: {alive_ratio:.1%}",
                               curses.color_pair(2))
            mr += 2
            self.stdscr.addstr(mr, mx, f"Clustering: {self.gca_clustering:.3f}",
                               curses.color_pair(3))
            mr += 1
            self.stdscr.addstr(mr, mx, f"Avg Path:   {self.gca_avg_path:.2f}",
                               curses.color_pair(3))
            mr += 1
            self.stdscr.addstr(mr, mx, f"Avg Degree: {self.gca_avg_deg:.1f}",
                               curses.color_pair(3))
            mr += 1
            self.stdscr.addstr(mr, mx, f"Max Degree: {self.gca_max_deg}",
                               curses.color_pair(3))
            mr += 2

            # Population sparkline
            self.stdscr.addstr(mr, mx, "Population History:",
                               curses.A_BOLD | curses.color_pair(6))
            mr += 1
            hist = self.gca_pop_history
            if len(hist) > 1:
                spark_w = min(metrics_w - 2, len(hist))
                # Sample history to fit
                if len(hist) > spark_w:
                    step = len(hist) / spark_w
                    sampled = [hist[int(i * step)] for i in range(spark_w)]
                else:
                    sampled = hist[-spark_w:]
                mn = min(sampled)
                mx_val = max(sampled)
                rng = mx_val - mn if mx_val > mn else 1
                spark_chars = " _.-~*#@"
                spark = ""
                for v in sampled:
                    idx = int((v - mn) / rng * (len(spark_chars) - 1))
                    spark += spark_chars[idx]
                self.stdscr.addstr(mr, graph_w + 2, spark[:metrics_w - 2],
                                   curses.color_pair(2))

            mr += 2
            # Degree distribution mini-histogram
            self.stdscr.addstr(mr, graph_w + 2, "Degree Distribution:",
                               curses.A_BOLD | curses.color_pair(6))
            mr += 1
            degrees = [len(self.gca_adj.get(i, [])) for i in range(n)]
            if degrees:
                max_d = max(degrees)
                bins = {}
                for d in degrees:
                    bins[d] = bins.get(d, 0) + 1
                # Show top few degree bins
                for d in sorted(bins.keys())[:6]:
                    if mr >= max_y - 3:
                        break
                    bar_len = int(bins[d] / max(max(bins.values()), 1) * (metrics_w - 10))
                    bar = "|" * bar_len
                    self.stdscr.addstr(mr, graph_w + 2, f"d={d:2d}: {bar}",
                                       curses.A_DIM | curses.color_pair(6))
                    mr += 1
        except curses.error:
            pass

    # Status bar
    status_parts = [
        f" {self.gca_topo_name}",
        f"Rule: {self.gca_rule_name}",
        f"Gen: {self.gca_generation}",
        f"Pop: {self.gca_population}/{n}",
        f"Nodes: {n}",
        "PAUSED" if not self.gca_running else "RUNNING",
    ]
    status = "  |  ".join(status_parts)
    try:
        self.stdscr.addstr(max_y - 2, 0, status[:max_x - 1],
                           curses.A_BOLD | curses.color_pair(4))
    except curses.error:
        pass

    # Help bar
    help_text = " [space]pause [r]andom [c]lear [s]tep [n]rule [t]opology [e]dges [m]etrics [l]ayout [+/-]nodes [q]uit"
    try:
        self.stdscr.addstr(max_y - 1, 0, help_text[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


# ── Registration ──────────────────────────────────────────────────

def register(App):
    """Register Graph CA mode methods on the App class."""
    App._enter_gca_mode = _enter_gca_mode
    App._exit_gca_mode = _exit_gca_mode
    App._gca_init = _gca_init
    App._gca_step = _gca_step
    App._gca_randomize = _gca_randomize
    App._gca_clear = _gca_clear
    App._handle_gca_menu_key = _handle_gca_menu_key
    App._handle_gca_key = _handle_gca_key
    App._draw_gca_menu = _draw_gca_menu
    App._draw_gca = _draw_gca
