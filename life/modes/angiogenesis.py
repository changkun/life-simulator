"""Mode: angio — Blood Vessel Network & Angiogenesis.

A pulsing vascular network that grows through angiogenesis — vessel tip cells
sprout toward VEGF gradients secreted by oxygen-starved tissue, branching and
anastomosing into a self-organizing capillary network.  Pulsatile blood flow
driven by a heartbeat pressure wave delivers oxygen to surrounding tissue;
vessels remodel by Murray's law (high-flow widen, unused regress).  A
toggleable tumor mode lets a growing tumor hijack the vasculature.

Three views:
  1) Living vessel network — flowing red blood cells, pulsing arteries,
     sprouting tip cells, optional tumor mass
  2) Oxygen / VEGF heatmap — tissue perfusion and hypoxic zones
  3) Time-series sparkline graphs — perfusion, density, flow, O2, VEGF, tumor

Six presets:
  Healthy Tissue Growth, Wound Healing, Tumor Angiogenesis,
  Anti-Angiogenic Drug Therapy, Retinal Vasculature, Exercise Capillarization
"""
import curses
import math
import random


# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

ANGIO_PRESETS = [
    ("Healthy Tissue Growth",
     "Normal angiogenesis — balanced VEGF, orderly branching, efficient perfusion",
     "healthy"),
    ("Wound Healing",
     "Tissue damage triggers VEGF burst — rapid neovascularization into wound bed",
     "wound"),
    ("Tumor Angiogenesis",
     "Growing tumor floods VEGF — chaotic tortuous vasculature with poor perfusion",
     "tumor"),
    ("Anti-Angiogenic Drug Therapy",
     "Tumor present but anti-VEGF drug suppresses sprouting — vessel normalization",
     "antiangio"),
    ("Retinal Vasculature",
     "Radial vascular tree growing from optic disc across retinal surface",
     "retinal"),
    ("Exercise-Induced Capillarization",
     "Muscle tissue with elevated O2 demand drives capillary bed densification",
     "exercise"),
]


# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

_NEIGHBORS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_NEIGHBORS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                (0, 1), (1, -1), (1, 0), (1, 1)]

# Murray's law exponent (cube law for branching)
_MURRAY_EXP = 3.0

# Heartbeat
_HEART_PERIOD = 30       # ticks per heartbeat cycle
_SYSTOLE_FRAC = 0.35     # fraction of cycle that is systole

# Oxygen diffusion
_O2_DIFFUSE = 0.12       # per-tick diffusion coefficient
_O2_CONSUME = 0.015      # tissue oxygen consumption rate
_O2_SUPPLY = 0.25        # O2 delivered per unit flow through vessel

# VEGF
_VEGF_SECRETE_THRESH = 0.3  # tissue O2 below this → secrete VEGF
_VEGF_SECRETE_RATE = 0.06
_VEGF_DECAY = 0.01
_VEGF_DIFFUSE = 0.08

# Sprouting
_SPROUT_VEGF_THRESH = 0.15  # VEGF level for tip cell activation
_SPROUT_PROB = 0.08
_BRANCH_PROB = 0.03
_ANASTOMOSE_RADIUS = 2.5    # merge distance for tip meeting vessel

# Vessel remodeling
_REGRESS_FLOW_THRESH = 0.01
_REGRESS_PROB = 0.004
_WIDEN_RATE = 0.002
_NARROW_RATE = 0.001
_MIN_RADIUS = 0.3
_MAX_RADIUS = 3.0


# ══════════════════════════════════════════════════════════════════════
#  Data classes
# ══════════════════════════════════════════════════════════════════════

class _VesselNode:
    """A junction in the vascular network."""
    __slots__ = ('r', 'c', 'pressure', 'oxygen', 'is_source', 'is_tip',
                 'neighbors', 'flow_out')

    def __init__(self, r, c, is_source=False):
        self.r = r
        self.c = c
        self.pressure = 0.0
        self.oxygen = 1.0
        self.is_source = is_source
        self.is_tip = False
        self.neighbors = []   # indices into vessel_edges
        self.flow_out = 0.0


class _VesselEdge:
    """A vessel segment connecting two nodes."""
    __slots__ = ('n1', 'n2', 'radius', 'flow', 'length', 'age',
                 'rbc_phase', 'wall_shear')

    def __init__(self, n1, n2, radius=0.8):
        self.n1 = n1
        self.n2 = n2
        self.radius = radius
        self.flow = 0.0
        self.length = 1.0
        self.age = 0
        self.rbc_phase = random.random() * 2 * math.pi
        self.wall_shear = 0.0


class _TipCell:
    """An active sprouting front guided by VEGF gradient."""
    __slots__ = ('r', 'c', 'node_idx', 'heading', 'speed', 'age',
                 'parent_edge')

    def __init__(self, r, c, node_idx, heading):
        self.r = r
        self.c = c
        self.node_idx = node_idx
        self.heading = heading
        self.speed = 0.5
        self.age = 0
        self.parent_edge = -1


class _Tumor:
    """A growing tumor mass."""
    __slots__ = ('r', 'c', 'radius', 'growth_rate', 'vegf_boost',
                 'cells')

    def __init__(self, r, c, radius=2.0):
        self.r = r
        self.c = c
        self.radius = radius
        self.growth_rate = 0.015
        self.vegf_boost = 0.3
        self.cells = set()  # (r, c) positions


class _RBCParticle:
    """Visual red blood cell particle flowing through vessel."""
    __slots__ = ('edge_idx', 'progress', 'forward')

    def __init__(self, edge_idx, progress=0.0, forward=True):
        self.edge_idx = edge_idx
        self.progress = progress
        self.forward = forward


# ══════════════════════════════════════════════════════════════════════
#  Enter / Exit
# ══════════════════════════════════════════════════════════════════════

def _enter_angio_mode(self):
    """Enter angiogenesis mode — show preset menu."""
    self.angio_mode = True
    self.angio_menu = True
    self.angio_menu_sel = 0


def _exit_angio_mode(self):
    """Exit angiogenesis mode."""
    self.angio_mode = False
    self.angio_menu = False
    self.angio_running = False
    for attr in list(vars(self)):
        if attr.startswith('angio_') and attr not in ('angio_mode',):
            try:
                delattr(self, attr)
            except AttributeError:
                pass


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _angio_init(self, preset_idx: int):
    """Initialize simulation for the chosen preset."""
    name, _desc, pid = ANGIO_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(20, max_x - 2)

    self.angio_menu = False
    self.angio_running = False
    self.angio_preset_name = name
    self.angio_preset_id = pid
    self.angio_rows = rows
    self.angio_cols = cols
    self.angio_generation = 0
    self.angio_speed = 1
    self.angio_view = "vessel"    # vessel | heatmap | graphs

    # Heartbeat
    self.angio_heart_phase = 0.0
    self.angio_heart_rate = _HEART_PERIOD

    # Scalar fields
    self.angio_oxygen = [[0.5] * cols for _ in range(rows)]
    self.angio_vegf = [[0.0] * cols for _ in range(rows)]
    self.angio_tissue_alive = [[True] * cols for _ in range(rows)]

    # Vascular network
    self.angio_nodes = []
    self.angio_edges = []
    self.angio_tips = []
    self.angio_rbc = []
    self.angio_node_grid = {}  # (r,c) -> node_idx for fast lookup

    # Tumor (may be None)
    self.angio_tumor = None
    self.angio_drug_active = False
    self.angio_drug_strength = 0.0

    # History for sparklines
    self.angio_history = {
        'perfusion': [],
        'vessel_density': [],
        'mean_flow': [],
        'o2_coverage': [],
        'vegf_level': [],
        'tumor_size': [],
        'tip_count': [],
        'heart_pressure': [],
        'vessel_count': [],
        'regression_events': [],
    }

    # Preset-specific setup
    _angio_setup_preset(self, pid, rows, cols)
    self._flash(f"Angiogenesis: {name}")


def _angio_setup_preset(self, pid, rows, cols):
    """Configure initial vasculature and conditions per preset."""
    cr, cc = rows // 2, cols // 2

    if pid == "healthy":
        # Central arteriole with a few branches
        _angio_create_tree(self, cr, cc // 4, rows, cols, branches=4, depth=3)
        _angio_create_tree(self, cr, 3 * cc // 2, rows, cols, branches=3, depth=3)

    elif pid == "wound":
        # Vessels on left side, wound (no vessels) on right
        _angio_create_tree(self, cr, cc // 3, rows, cols, branches=5, depth=3)
        # Create wound zone — clear O2 and add VEGF
        for r in range(rows // 4, 3 * rows // 4):
            for c in range(cols // 2, min(cols, cols // 2 + cols // 3)):
                self.angio_oxygen[r][c] = 0.1
                self.angio_vegf[r][c] = 0.2

    elif pid == "tumor":
        # Healthy vasculature plus tumor
        _angio_create_tree(self, cr, cc // 3, rows, cols, branches=4, depth=3)
        _angio_create_tree(self, cr, 3 * cc // 2, rows, cols, branches=3, depth=2)
        tumor = _Tumor(cr, cc + cc // 3, radius=3.0)
        tumor.growth_rate = 0.02
        tumor.vegf_boost = 0.4
        _tumor_update_cells(tumor, rows, cols)
        self.angio_tumor = tumor

    elif pid == "antiangio":
        # Tumor with drug suppression
        _angio_create_tree(self, cr, cc // 3, rows, cols, branches=4, depth=3)
        tumor = _Tumor(cr, cc + cc // 3, radius=3.0)
        tumor.growth_rate = 0.01
        tumor.vegf_boost = 0.35
        _tumor_update_cells(tumor, rows, cols)
        self.angio_tumor = tumor
        self.angio_drug_active = True
        self.angio_drug_strength = 0.7

    elif pid == "retinal":
        # Single source at center (optic disc), radial growth
        src_idx = _angio_add_node(self, cr, cc, is_source=True)
        # Radial spokes
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            prev = src_idx
            for dist in range(1, min(rows, cols) // 4):
                nr = int(cr + dist * 2 * math.sin(rad))
                nc = int(cc + dist * 2 * math.cos(rad))
                if 0 <= nr < rows and 0 <= nc < cols:
                    ni = _angio_add_node(self, nr, nc)
                    _angio_add_edge(self, prev, ni, radius=max(0.5, 1.5 - dist * 0.1))
                    prev = ni
            # Add tip at end
            er = int(cr + (min(rows, cols) // 4) * 2 * math.sin(rad))
            ec = int(cc + (min(rows, cols) // 4) * 2 * math.cos(rad))
            er = max(0, min(rows - 1, er))
            ec = max(0, min(cols - 1, ec))
            if prev != src_idx:
                tip = _TipCell(er, ec, prev, angle)
                self.angio_tips.append(tip)
        # Lower base O2 to drive growth
        for r in range(rows):
            for c in range(cols):
                d = math.hypot(r - cr, c - cc)
                self.angio_oxygen[r][c] = max(0.1, 0.8 - d * 0.02)

    elif pid == "exercise":
        # Dense capillary bed with increased O2 demand
        _angio_create_tree(self, cr, cc // 4, rows, cols, branches=5, depth=3)
        _angio_create_tree(self, cr, 3 * cc // 2, rows, cols, branches=5, depth=3)
        # Elevated consumption everywhere (simulated by lower starting O2)
        for r in range(rows):
            for c in range(cols):
                self.angio_oxygen[r][c] = 0.25


def _angio_create_tree(self, root_r, root_c, rows, cols, branches=4, depth=3):
    """Create a simple branching vascular tree from a root point."""
    root_r = max(0, min(rows - 1, root_r))
    root_c = max(0, min(cols - 1, root_c))
    src_idx = _angio_add_node(self, root_r, root_c, is_source=True)

    def _branch(parent_idx, pr, pc, angle, rad, d):
        if d <= 0 or rad < _MIN_RADIUS:
            # Add a tip cell at the end
            tip = _TipCell(pr, pc, parent_idx, angle)
            self.angio_tips.append(tip)
            return
        length = random.randint(3, 6)
        prev = parent_idx
        for step in range(length):
            nr = int(pr + (step + 1) * math.sin(math.radians(angle)))
            nc = int(pc + (step + 1) * math.cos(math.radians(angle)))
            nr = max(0, min(rows - 1, nr))
            nc = max(0, min(cols - 1, nc))
            ni = _angio_add_node(self, nr, nc)
            _angio_add_edge(self, prev, ni, radius=rad)
            prev = ni
        # Get final position
        fr = self.angio_nodes[prev].r
        fc = self.angio_nodes[prev].c
        # Branch
        n_sub = random.randint(1, min(3, branches))
        for _ in range(n_sub):
            new_angle = angle + random.uniform(-50, 50)
            child_rad = rad * (0.7 + random.random() * 0.15)
            _branch(prev, fr, fc, new_angle, child_rad, d - 1)

    # Initial branches
    for i in range(branches):
        angle = (360.0 / branches) * i + random.uniform(-20, 20)
        _branch(src_idx, root_r, root_c, angle, 1.2 + random.random() * 0.3, depth)


def _angio_add_node(self, r, c, is_source=False):
    """Add a node; reuse if one exists at (r,c)."""
    key = (r, c)
    if key in self.angio_node_grid:
        idx = self.angio_node_grid[key]
        if is_source:
            self.angio_nodes[idx].is_source = True
        return idx
    idx = len(self.angio_nodes)
    node = _VesselNode(r, c, is_source=is_source)
    self.angio_nodes.append(node)
    self.angio_node_grid[key] = idx
    return idx


def _angio_add_edge(self, n1, n2, radius=0.8):
    """Add a vessel edge between two nodes."""
    if n1 == n2:
        return -1
    # Check for duplicate
    for ei in self.angio_nodes[n1].neighbors:
        e = self.angio_edges[ei]
        if (e.n1 == n1 and e.n2 == n2) or (e.n1 == n2 and e.n2 == n1):
            return ei
    ei = len(self.angio_edges)
    nd1, nd2 = self.angio_nodes[n1], self.angio_nodes[n2]
    edge = _VesselEdge(n1, n2, radius=radius)
    edge.length = max(1.0, math.hypot(nd1.r - nd2.r, nd1.c - nd2.c))
    self.angio_edges.append(edge)
    self.angio_nodes[n1].neighbors.append(ei)
    self.angio_nodes[n2].neighbors.append(ei)
    # Spawn some RBCs
    for _ in range(max(1, int(edge.length / 3))):
        rbc = _RBCParticle(ei, random.random(), random.random() > 0.5)
        self.angio_rbc.append(rbc)
    return ei


def _tumor_update_cells(tumor, rows, cols):
    """Recompute the set of cells covered by tumor."""
    tumor.cells.clear()
    r0, c0 = tumor.r, tumor.c
    ir = int(tumor.radius) + 1
    for dr in range(-ir, ir + 1):
        for dc in range(-ir, ir + 1):
            if dr * dr + dc * dc <= tumor.radius * tumor.radius:
                rr, cc2 = r0 + dr, c0 + dc
                if 0 <= rr < rows and 0 <= cc2 < cols:
                    tumor.cells.add((rr, cc2))


# ══════════════════════════════════════════════════════════════════════
#  Simulation Step
# ══════════════════════════════════════════════════════════════════════

def _angio_step(self):
    """Advance one tick of the angiogenesis simulation."""
    rows = self.angio_rows
    cols = self.angio_cols

    for _ in range(self.angio_speed):
        self.angio_generation += 1

        # ── 1. Heartbeat ──
        self.angio_heart_phase = (self.angio_heart_phase + 1) % self.angio_heart_rate
        phase_frac = self.angio_heart_phase / self.angio_heart_rate
        if phase_frac < _SYSTOLE_FRAC:
            # Systole: rising pressure
            systole_frac = phase_frac / _SYSTOLE_FRAC
            base_pressure = 0.5 + 0.5 * math.sin(systole_frac * math.pi)
        else:
            # Diastole: declining pressure
            diast_frac = (phase_frac - _SYSTOLE_FRAC) / (1.0 - _SYSTOLE_FRAC)
            base_pressure = 0.5 * math.exp(-2.0 * diast_frac)

        # ── 2. Pressure propagation from source nodes ──
        for node in self.angio_nodes:
            if node.is_source:
                node.pressure = base_pressure
            else:
                node.pressure *= 0.5  # decay

        # Simple BFS-like pressure propagation (a few iterations)
        for _iteration in range(3):
            for edge in self.angio_edges:
                nd1 = self.angio_nodes[edge.n1]
                nd2 = self.angio_nodes[edge.n2]
                # Poiseuille: flow ∝ r^4 / length * ΔP
                conductance = (edge.radius ** 4) / max(0.5, edge.length)
                dp = nd1.pressure - nd2.pressure
                flow = conductance * dp * 0.3
                edge.flow = flow
                edge.wall_shear = abs(flow) / max(0.1, edge.radius ** 3)
                # Transfer pressure
                if abs(dp) > 0.001:
                    transfer = dp * 0.15 * min(1.0, conductance)
                    nd1.pressure -= transfer
                    nd2.pressure += transfer

        # ── 3. Oxygen delivery ──
        # Vessels supply O2 to nearby tissue
        vessel_cells = set()
        for edge in self.angio_edges:
            nd1 = self.angio_nodes[edge.n1]
            nd2 = self.angio_nodes[edge.n2]
            steps = max(1, int(edge.length))
            for s in range(steps + 1):
                t = s / max(1, steps)
                vr = int(nd1.r + t * (nd2.r - nd1.r))
                vc = int(nd1.c + t * (nd2.c - nd1.c))
                if 0 <= vr < rows and 0 <= vc < cols:
                    vessel_cells.add((vr, vc))
                    supply = _O2_SUPPLY * abs(edge.flow) * (edge.radius / 1.0)
                    self.angio_oxygen[vr][vc] = min(1.0,
                        self.angio_oxygen[vr][vc] + supply)

        # ── 4. Oxygen diffusion + consumption ──
        new_o2 = [row[:] for row in self.angio_oxygen]
        consume_rate = _O2_CONSUME
        # Exercise preset: higher consumption
        if self.angio_preset_id == "exercise":
            consume_rate = _O2_CONSUME * 2.0

        for r in range(rows):
            for c in range(cols):
                val = self.angio_oxygen[r][c]
                # Diffusion (average of neighbors)
                total = 0.0
                cnt = 0
                for dr, dc in _NEIGHBORS_4:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        total += self.angio_oxygen[nr][nc]
                        cnt += 1
                if cnt > 0:
                    avg = total / cnt
                    val += _O2_DIFFUSE * (avg - val)
                # Consumption
                val -= consume_rate
                # Tumor cells consume more
                if self.angio_tumor and (r, c) in self.angio_tumor.cells:
                    val -= consume_rate * 1.5
                new_o2[r][c] = max(0.0, min(1.0, val))
        self.angio_oxygen = new_o2

        # ── 5. VEGF secretion + diffusion ──
        new_vegf = [row[:] for row in self.angio_vegf]
        drug_factor = 1.0
        if self.angio_drug_active:
            drug_factor = max(0.1, 1.0 - self.angio_drug_strength)

        for r in range(rows):
            for c in range(cols):
                val = self.angio_vegf[r][c]
                # Hypoxic tissue secretes VEGF
                if self.angio_oxygen[r][c] < _VEGF_SECRETE_THRESH:
                    deficit = _VEGF_SECRETE_THRESH - self.angio_oxygen[r][c]
                    val += _VEGF_SECRETE_RATE * deficit * drug_factor
                # Tumor boost
                if self.angio_tumor and (r, c) in self.angio_tumor.cells:
                    val += self.angio_tumor.vegf_boost * 0.05 * drug_factor
                # Decay
                val -= _VEGF_DECAY
                # Diffusion
                total = 0.0
                cnt = 0
                for dr, dc in _NEIGHBORS_4:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        total += self.angio_vegf[nr][nc]
                        cnt += 1
                if cnt > 0:
                    avg = total / cnt
                    val += _VEGF_DIFFUSE * (avg - val)
                new_vegf[r][c] = max(0.0, min(1.0, val))
        self.angio_vegf = new_vegf

        # ── 6. Tip cell migration (chemotaxis toward VEGF) ──
        new_tips = []
        for tip in self.angio_tips:
            tip.age += 1
            if tip.age > 150:
                continue  # tip dies

            # Drug suppresses sprouting
            if self.angio_drug_active and random.random() < self.angio_drug_strength * 0.3:
                new_tips.append(tip)
                continue

            # Sense VEGF gradient
            best_vegf = 0.0
            best_dr, best_dc = 0, 0
            for dr, dc in _NEIGHBORS_8:
                nr, nc = int(tip.r + dr), int(tip.c + dc)
                if 0 <= nr < rows and 0 <= nc < cols:
                    v = self.angio_vegf[nr][nc]
                    if v > best_vegf:
                        best_vegf = v
                        best_dr, best_dc = dr, dc

            # Move toward VEGF gradient with some persistence
            if best_vegf > 0.01:
                grad_angle = math.degrees(math.atan2(best_dr, best_dc))
                # Blend with current heading
                tip.heading = tip.heading * 0.6 + grad_angle * 0.4
            else:
                tip.heading += random.uniform(-15, 15)

            rad = math.radians(tip.heading)
            new_r = tip.r + math.sin(rad) * tip.speed
            new_c = tip.c + math.cos(rad) * tip.speed
            new_r = max(0, min(rows - 1, new_r))
            new_c = max(0, min(cols - 1, new_c))

            # Check for anastomosis (merge with existing vessel)
            merged = False
            nr_int, nc_int = int(new_r), int(new_c)
            for dr in range(-2, 3):
                if merged:
                    break
                for dc in range(-2, 3):
                    check = (nr_int + dr, nc_int + dc)
                    if check in self.angio_node_grid:
                        other_idx = self.angio_node_grid[check]
                        if other_idx != tip.node_idx:
                            d = math.hypot(new_r - check[0], new_c - check[1])
                            if d < _ANASTOMOSE_RADIUS:
                                # Connect!
                                _angio_add_edge(self, tip.node_idx, other_idx,
                                                radius=0.5)
                                merged = True
                                break

            if merged:
                continue

            # Create new node at current position and edge from previous
            if abs(new_r - self.angio_nodes[tip.node_idx].r) >= 1.0 or \
               abs(new_c - self.angio_nodes[tip.node_idx].c) >= 1.0:
                ni = _angio_add_node(self, int(new_r), int(new_c))
                _angio_add_edge(self, tip.node_idx, ni, radius=0.5)
                tip.node_idx = ni

            tip.r = new_r
            tip.c = new_c

            # Branching
            if best_vegf > _SPROUT_VEGF_THRESH and random.random() < _BRANCH_PROB:
                branch_heading = tip.heading + random.choice([-60, 60]) + random.uniform(-10, 10)
                new_tip = _TipCell(tip.r, tip.c, tip.node_idx, branch_heading)
                new_tips.append(new_tip)

            new_tips.append(tip)

        # New sprouts from existing vessels
        if random.random() < _SPROUT_PROB * drug_factor:
            if self.angio_nodes:
                candidates = []
                for ni, node in enumerate(self.angio_nodes):
                    if not node.is_tip and not node.is_source:
                        r, c = node.r, node.c
                        if 0 <= r < rows and 0 <= c < cols:
                            if self.angio_vegf[r][c] > _SPROUT_VEGF_THRESH:
                                candidates.append(ni)
                if candidates:
                    chosen = random.choice(candidates)
                    nd = self.angio_nodes[chosen]
                    heading = random.uniform(0, 360)
                    tip = _TipCell(nd.r, nd.c, chosen, heading)
                    new_tips.append(tip)

        self.angio_tips = new_tips

        # ── 7. Vessel remodeling (Murray's law) ──
        regression_count = 0
        for edge in self.angio_edges:
            edge.age += 1
            # Murray's law: optimal radius ∝ flow^(1/3)
            if abs(edge.flow) > 0.001:
                optimal = min(_MAX_RADIUS, abs(edge.flow) ** (1.0 / _MURRAY_EXP) * 2.0)
                if edge.radius < optimal:
                    edge.radius = min(_MAX_RADIUS, edge.radius + _WIDEN_RATE)
                elif edge.radius > optimal * 1.2:
                    edge.radius = max(_MIN_RADIUS, edge.radius - _NARROW_RATE)
            # Regression of unused vessels
            if abs(edge.flow) < _REGRESS_FLOW_THRESH and edge.age > 50:
                if random.random() < _REGRESS_PROB:
                    edge.radius = max(0.0, edge.radius - 0.05)
                    regression_count += 1

        # Remove collapsed vessels
        keep_edges = []
        for i, edge in enumerate(self.angio_edges):
            if edge.radius > 0.05:
                keep_edges.append(edge)
        if len(keep_edges) < len(self.angio_edges):
            # Rebuild edge indices
            self.angio_edges = keep_edges
            for node in self.angio_nodes:
                node.neighbors.clear()
            for ei, edge in enumerate(self.angio_edges):
                self.angio_nodes[edge.n1].neighbors.append(ei)
                self.angio_nodes[edge.n2].neighbors.append(ei)
            # Fix RBC references
            self.angio_rbc = [p for p in self.angio_rbc
                              if p.edge_idx < len(self.angio_edges)]

        # ── 8. Tumor growth ──
        if self.angio_tumor:
            tumor = self.angio_tumor
            # Grow if oxygenated
            avg_o2 = 0.0
            if tumor.cells:
                for tr, tc in tumor.cells:
                    avg_o2 += self.angio_oxygen[tr][tc]
                avg_o2 /= len(tumor.cells)
            if avg_o2 > 0.1:
                tumor.radius += tumor.growth_rate * avg_o2
                _tumor_update_cells(tumor, rows, cols)

        # ── 9. RBC particle movement ──
        for rbc in self.angio_rbc:
            if rbc.edge_idx >= len(self.angio_edges):
                continue
            edge = self.angio_edges[rbc.edge_idx]
            speed = min(0.15, abs(edge.flow) * 0.5 + 0.02)
            if rbc.forward:
                rbc.progress += speed
                if rbc.progress >= 1.0:
                    # Move to connected edge
                    nd = self.angio_nodes[edge.n2]
                    if nd.neighbors:
                        new_ei = random.choice(nd.neighbors)
                        rbc.edge_idx = new_ei
                        rbc.progress = 0.0
                        new_e = self.angio_edges[new_ei]
                        rbc.forward = new_e.n1 == edge.n2
                    else:
                        rbc.forward = False
                        rbc.progress = 1.0
            else:
                rbc.progress -= speed
                if rbc.progress <= 0.0:
                    nd = self.angio_nodes[edge.n1]
                    if nd.neighbors:
                        new_ei = random.choice(nd.neighbors)
                        rbc.edge_idx = new_ei
                        rbc.progress = 1.0
                        new_e = self.angio_edges[new_ei]
                        rbc.forward = new_e.n1 == edge.n1
                    else:
                        rbc.forward = True
                        rbc.progress = 0.0

        # Maintain RBC count proportional to vessel count
        target_rbc = max(10, len(self.angio_edges) * 2)
        while len(self.angio_rbc) < target_rbc and self.angio_edges:
            ei = random.randint(0, len(self.angio_edges) - 1)
            self.angio_rbc.append(_RBCParticle(ei, random.random()))
        if len(self.angio_rbc) > target_rbc * 2:
            self.angio_rbc = self.angio_rbc[:target_rbc]

        # ── 10. Record history ──
        hist = self.angio_history
        # Perfusion: fraction of tissue with O2 > 0.3
        o2_ok = sum(1 for r in range(rows) for c in range(cols)
                     if self.angio_oxygen[r][c] > 0.3)
        total = rows * cols
        hist['perfusion'].append(o2_ok / max(1, total))
        hist['vessel_density'].append(len(self.angio_edges) / max(1, total) * 100)
        hist['mean_flow'].append(
            sum(abs(e.flow) for e in self.angio_edges) / max(1, len(self.angio_edges)))
        hist['o2_coverage'].append(
            sum(self.angio_oxygen[r][c] for r in range(rows) for c in range(cols)) / total)
        hist['vegf_level'].append(
            sum(self.angio_vegf[r][c] for r in range(rows) for c in range(cols)) / total)
        hist['tumor_size'].append(
            self.angio_tumor.radius if self.angio_tumor else 0.0)
        hist['tip_count'].append(len(self.angio_tips))
        hist['heart_pressure'].append(base_pressure)
        hist['vessel_count'].append(len(self.angio_edges))
        hist['regression_events'].append(regression_count)

        # Cap history
        for k in hist:
            if len(hist[k]) > 200:
                hist[k] = hist[k][-200:]


# ══════════════════════════════════════════════════════════════════════
#  Key Handlers
# ══════════════════════════════════════════════════════════════════════

def _handle_angio_menu_key(self, key: int) -> bool:
    """Handle key input in the preset selection menu."""
    n = len(ANGIO_PRESETS)
    if key == ord("q") or key == 27:
        self.angio_mode = False
        self.angio_menu = False
        return True
    if key == curses.KEY_UP or key == ord("k"):
        self.angio_menu_sel = (self.angio_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.angio_menu_sel = (self.angio_menu_sel + 1) % n
        return True
    if key in (10, 13, curses.KEY_ENTER):
        _angio_init(self, self.angio_menu_sel)
        return True
    return True


def _handle_angio_key(self, key: int) -> bool:
    """Handle key input during live simulation."""
    if key == ord(" "):
        self.angio_running = not self.angio_running
        self._flash("Running" if self.angio_running else "Paused")
        return True

    if key == ord("n") or key == ord("."):
        _angio_step(self)
        return True

    if key == ord("v"):
        views = ["vessel", "heatmap", "graphs"]
        cur = views.index(self.angio_view) if self.angio_view in views else 0
        self.angio_view = views[(cur + 1) % len(views)]
        self._flash(f"View: {self.angio_view}")
        return True

    if key == ord("+") or key == ord("="):
        self.angio_speed = min(20, self.angio_speed + 1)
        self._flash(f"Speed: {self.angio_speed}x")
        return True

    if key == ord("-") or key == ord("_"):
        self.angio_speed = max(1, self.angio_speed - 1)
        self._flash(f"Speed: {self.angio_speed}x")
        return True

    if key == ord("d"):
        # Toggle drug
        if self.angio_tumor:
            self.angio_drug_active = not self.angio_drug_active
            self._flash(f"Anti-VEGF Drug: {'ON' if self.angio_drug_active else 'OFF'}")
        return True

    if key == ord("t"):
        # Toggle tumor
        if self.angio_tumor is None:
            cr, cc = self.angio_rows // 2, self.angio_cols // 2
            self.angio_tumor = _Tumor(cr, cc + cc // 3, radius=2.0)
            _tumor_update_cells(self.angio_tumor, self.angio_rows, self.angio_cols)
            self._flash("Tumor added")
        else:
            self.angio_tumor = None
            self._flash("Tumor removed")
        return True

    if key == ord("r"):
        idx = next((i for i, p in enumerate(ANGIO_PRESETS)
                     if p[0] == self.angio_preset_name), 0)
        _angio_init(self, idx)
        return True

    if key == ord("R") or key == ord("m"):
        self.angio_running = False
        self.angio_menu = True
        self.angio_menu_sel = 0
        return True

    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Menu
# ══════════════════════════════════════════════════════════════════════

def _draw_angio_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    self.stdscr.erase()

    title = "── Blood Vessel Network & Angiogenesis ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2),
                           title[:max_x - 1],
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(ANGIO_PRESETS):
        y = 4 + i * 3
        if y >= max_y - 6:
            break
        marker = "▸ " if i == self.angio_menu_sel else "  "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.angio_menu_sel
                else curses.color_pair(7))
        try:
            self.stdscr.addstr(y, 3, f"{marker}{name}"[:max_x - 4], attr)
        except curses.error:
            pass
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hints = " [↑/↓] Navigate   [Enter] Select   [q/Esc] Back"
    hy = max_y - 2
    if 0 < hy < max_y:
        try:
            self.stdscr.addstr(hy, 2, hints[:max_x - 4],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Main Dispatcher
# ══════════════════════════════════════════════════════════════════════

def _draw_angio(self, max_y: int, max_x: int):
    """Draw the active simulation view."""
    self.stdscr.erase()

    # Title bar
    gen = self.angio_generation
    view_label = self.angio_view.replace("_", " ").title()
    status = "▶" if self.angio_running else "⏸"
    n_vessels = len(self.angio_edges)
    n_tips = len(self.angio_tips)

    # Heartbeat indicator
    phase_frac = self.angio_heart_phase / self.angio_heart_rate
    if phase_frac < _SYSTOLE_FRAC:
        heart_ch = "♥"
        heart_attr = curses.color_pair(1) | curses.A_BOLD
    else:
        heart_ch = "♡"
        heart_attr = curses.color_pair(1)

    title = f" {self.angio_preset_name} | t={gen} | {view_label} | {status} " \
            f"| Vessels={n_vessels} Tips={n_tips}"
    if self.angio_tumor:
        title += f" | Tumor r={self.angio_tumor.radius:.1f}"
    if self.angio_drug_active:
        title += " | Drug ON"

    try:
        self.stdscr.addstr(0, 0, title[:max_x - 3],
                           curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(0, min(len(title), max_x - 3), f" {heart_ch}",
                           heart_attr)
    except curses.error:
        pass

    if self.angio_view == "vessel":
        _draw_angio_vessel(self, max_y, max_x)
    elif self.angio_view == "heatmap":
        _draw_angio_heatmap(self, max_y, max_x)
    elif self.angio_view == "graphs":
        _draw_angio_graphs(self, max_y, max_x)

    # Bottom hints
    hints = " [Space]Run [v]View [n]Step [+/-]Speed [t]Tumor [d]Drug [r]Reset [m]Menu"
    hy = max_y - 1
    if 0 < hy < max_y:
        try:
            self.stdscr.addstr(hy, 0, hints[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Vessel Network View
# ══════════════════════════════════════════════════════════════════════

def _draw_angio_vessel(self, max_y: int, max_x: int):
    """Draw the living vessel network with flowing RBCs."""
    rows = self.angio_rows
    cols = self.angio_cols
    off_y = 1
    off_x = 1
    view_h = max_y - 3
    view_w = max_x - 2

    # Background tissue — light gray for healthy, dark for hypoxic
    for r in range(min(rows, view_h)):
        for c in range(min(cols, view_w)):
            o2 = self.angio_oxygen[r][c]
            ch = " "
            if o2 < 0.15:
                ch = "░"
                attr = curses.color_pair(5) | curses.A_DIM
            elif o2 < 0.3:
                ch = "·"
                attr = curses.color_pair(6) | curses.A_DIM
            else:
                attr = curses.color_pair(0)
            try:
                self.stdscr.addstr(off_y + r, off_x + c, ch, attr)
            except curses.error:
                pass

    # Tumor mass
    if self.angio_tumor:
        for (tr, tc) in self.angio_tumor.cells:
            if tr < view_h and tc < view_w:
                try:
                    self.stdscr.addstr(off_y + tr, off_x + tc, "▓",
                                       curses.color_pair(5) | curses.A_BOLD)
                except curses.error:
                    pass

    # Vessel edges
    phase_frac = self.angio_heart_phase / self.angio_heart_rate
    pulse_bright = 1.0 if phase_frac < _SYSTOLE_FRAC else 0.6

    for edge in self.angio_edges:
        nd1 = self.angio_nodes[edge.n1]
        nd2 = self.angio_nodes[edge.n2]
        steps = max(1, int(edge.length * 1.5))
        for s in range(steps + 1):
            t = s / max(1, steps)
            vr = int(nd1.r + t * (nd2.r - nd1.r))
            vc = int(nd1.c + t * (nd2.c - nd1.c))
            if 0 <= vr < view_h and 0 <= vc < view_w:
                # Vessel character based on radius
                if edge.radius >= 2.0:
                    ch = "█"
                elif edge.radius >= 1.2:
                    ch = "▓"
                elif edge.radius >= 0.7:
                    ch = "▒"
                else:
                    ch = "░"

                # Color: arteries red, larger=brighter
                if abs(edge.flow) > 0.05:
                    if pulse_bright > 0.8:
                        attr = curses.color_pair(1) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(1)
                else:
                    attr = curses.color_pair(5)  # low-flow: magenta/dim

                try:
                    self.stdscr.addstr(off_y + vr, off_x + vc, ch, attr)
                except curses.error:
                    pass

    # RBC particles
    for rbc in self.angio_rbc:
        if rbc.edge_idx >= len(self.angio_edges):
            continue
        edge = self.angio_edges[rbc.edge_idx]
        nd1 = self.angio_nodes[edge.n1]
        nd2 = self.angio_nodes[edge.n2]
        t = max(0.0, min(1.0, rbc.progress))
        vr = int(nd1.r + t * (nd2.r - nd1.r))
        vc = int(nd1.c + t * (nd2.c - nd1.c))
        if 0 <= vr < view_h and 0 <= vc < view_w:
            try:
                self.stdscr.addstr(off_y + vr, off_x + vc, "●",
                                   curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

    # Tip cells (sprouting fronts)
    for tip in self.angio_tips:
        tr, tc = int(tip.r), int(tip.c)
        if 0 <= tr < view_h and 0 <= tc < view_w:
            try:
                self.stdscr.addstr(off_y + tr, off_x + tc, "⌁",
                                   curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass

    # Source nodes (arteriole origins)
    for node in self.angio_nodes:
        if node.is_source:
            nr, nc = node.r, node.c
            if 0 <= nr < view_h and 0 <= nc < view_w:
                try:
                    self.stdscr.addstr(off_y + nr, off_x + nc, "♦",
                                       curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Oxygen / VEGF Heatmap View
# ══════════════════════════════════════════════════════════════════════

def _draw_angio_heatmap(self, max_y: int, max_x: int):
    """Draw oxygen and VEGF heatmap side by side or overlaid."""
    rows = self.angio_rows
    cols = self.angio_cols
    off_y = 1
    off_x = 1
    view_h = max_y - 3
    view_w = max_x - 2

    # Split: left half = O2, right half = VEGF
    half_w = view_w // 2 - 1

    heat_chars = " ·∙░▒▓█"
    n_heat = len(heat_chars)

    # O2 heatmap (left)
    try:
        self.stdscr.addstr(off_y, off_x, "── O₂ Perfusion ──"[:half_w],
                           curses.color_pair(4) | curses.A_BOLD)
    except curses.error:
        pass

    for r in range(min(rows, view_h - 1)):
        for c in range(min(cols, half_w)):
            o2 = self.angio_oxygen[r][c] if r < rows and c < cols else 0
            idx = int(o2 * (n_heat - 1))
            idx = max(0, min(n_heat - 1, idx))
            ch = heat_chars[idx]
            # Color gradient: blue(low) -> cyan -> green -> white(high)
            if o2 < 0.2:
                cp = 4   # blue
            elif o2 < 0.4:
                cp = 6   # cyan
            elif o2 < 0.6:
                cp = 2   # green
            elif o2 < 0.8:
                cp = 3   # yellow
            else:
                cp = 7   # white
            try:
                self.stdscr.addstr(off_y + 1 + r, off_x + c, ch,
                                   curses.color_pair(cp))
            except curses.error:
                pass

    # VEGF heatmap (right)
    rx = off_x + half_w + 2
    try:
        self.stdscr.addstr(off_y, rx, "── VEGF Gradient ──"[:half_w],
                           curses.color_pair(5) | curses.A_BOLD)
    except curses.error:
        pass

    for r in range(min(rows, view_h - 1)):
        for c in range(min(cols, half_w)):
            vegf = self.angio_vegf[r][c] if r < rows and c < cols else 0
            idx = int(vegf * (n_heat - 1) * 2)  # amplify for visibility
            idx = max(0, min(n_heat - 1, idx))
            ch = heat_chars[idx]
            # Magenta/red gradient for VEGF
            if vegf < 0.1:
                cp = 6   # dim
            elif vegf < 0.3:
                cp = 5   # magenta
            else:
                cp = 1   # red (high VEGF)
            bold = curses.A_BOLD if vegf > 0.2 else 0
            try:
                self.stdscr.addstr(off_y + 1 + r, rx + c, ch,
                                   curses.color_pair(cp) | bold)
            except curses.error:
                pass

    # Overlay vessel positions on O2 map
    for edge in self.angio_edges:
        nd1 = self.angio_nodes[edge.n1]
        nd2 = self.angio_nodes[edge.n2]
        steps = max(1, int(edge.length))
        for s in range(steps + 1):
            t = s / max(1, steps)
            vr = int(nd1.r + t * (nd2.r - nd1.r))
            vc = int(nd1.c + t * (nd2.c - nd1.c))
            if 0 <= vr < view_h - 1 and 0 <= vc < half_w:
                try:
                    self.stdscr.addstr(off_y + 1 + vr, off_x + vc, "─",
                                       curses.color_pair(1) | curses.A_DIM)
                except curses.error:
                    pass

    # Tumor overlay
    if self.angio_tumor:
        for (tr, tc) in self.angio_tumor.cells:
            if tr < view_h - 1 and tc < half_w:
                try:
                    self.stdscr.addstr(off_y + 1 + tr, off_x + tc, "T",
                                       curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass
            if tr < view_h - 1 and tc < half_w:
                try:
                    self.stdscr.addstr(off_y + 1 + tr, rx + tc, "T",
                                       curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass


# ══════════════════════════════════════════════════════════════════════
#  Drawing — Sparkline Graphs View
# ══════════════════════════════════════════════════════════════════════

def _draw_angio_graphs(self, max_y: int, max_x: int):
    """Time-series sparkline graphs for key metrics."""
    hist = self.angio_history
    graph_w = min(200, max_x - 30)

    labels = [
        ("Perfusion",       'perfusion',          2),
        ("Vessel Density",  'vessel_density',     3),
        ("Mean Flow",       'mean_flow',          1),
        ("O₂ Coverage",     'o2_coverage',        4),
        ("VEGF Level",      'vegf_level',         5),
        ("Tumor Size",      'tumor_size',         1),
        ("Tip Cells",       'tip_count',          3),
        ("Heart Pressure",  'heart_pressure',     1),
        ("Vessel Count",    'vessel_count',       7),
        ("Regressions",     'regression_events',  6),
    ]

    bars = "▁▂▃▄▅▆▇█"
    n_bars = len(bars)

    for gi, (label, key, cp) in enumerate(labels):
        base_y = 2 + gi * 2
        if base_y + 1 >= max_y - 2:
            break

        data = hist.get(key, [])
        # Label with current value
        cur_val = data[-1] if data else 0
        if isinstance(cur_val, float):
            lbl = f"{label}: {cur_val:.3f}"
        else:
            lbl = f"{label}: {cur_val}"
        try:
            self.stdscr.addstr(base_y, 2, lbl[:24],
                               curses.color_pair(cp) | curses.A_BOLD)
        except curses.error:
            pass

        # Sparkline
        if data:
            visible = data[-graph_w:]
            mn = min(visible)
            mx = max(visible)
            rng = mx - mn if mx > mn else 1.0
            color = curses.color_pair(cp)
            for i, v in enumerate(visible):
                x = 26 + i
                if x >= max_x - 1:
                    break
                idx = int((v - mn) / rng * (n_bars - 1))
                idx = max(0, min(n_bars - 1, idx))
                try:
                    self.stdscr.addstr(base_y, x, bars[idx], color)
                except curses.error:
                    pass


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register angiogenesis mode methods on the App class."""
    App.ANGIO_PRESETS = ANGIO_PRESETS
    App._enter_angio_mode = _enter_angio_mode
    App._exit_angio_mode = _exit_angio_mode
    App._angio_init = _angio_init
    App._angio_step = _angio_step
    App._handle_angio_menu_key = _handle_angio_menu_key
    App._handle_angio_key = _handle_angio_key
    App._draw_angio_menu = _draw_angio_menu
    App._draw_angio = _draw_angio
