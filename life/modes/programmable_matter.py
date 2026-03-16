"""Mode: programmable_matter — self-assembling programmable cells.

Each cell is a tiny state machine executing a local program.  Cells have
internal registers, read neighbors' states, and follow simple instruction
sets (move, bond, signal, replicate).  Distributed computation happens
spatially: swarms self-assemble into target shapes, self-repair when
damaged, and perform parallel computation — all from purely local rules.
"""

import curses
import math
import random
import time

# ══════════════════════════════════════════════════════════════════════════
#  Programmable Matter — self-assembling state-machine cells
# ══════════════════════════════════════════════════════════════════════════

# Cell states
ST_EMPTY = 0
ST_IDLE = 1
ST_MOVING = 2
ST_BONDED = 3
ST_SIGNALING = 4

STATE_NAMES = {ST_EMPTY: "empty", ST_IDLE: "idle", ST_MOVING: "moving",
               ST_BONDED: "bonded", ST_SIGNALING: "signal"}

# Instruction opcodes
OP_NOP = 0
OP_MOVE = 1        # move in direction stored in reg A (0-3: N/E/S/W)
OP_BOND = 2        # bond to adjacent cell with matching signal
OP_UNBOND = 3      # release all bonds
OP_SIGNAL = 4      # emit signal value from reg B
OP_READ = 5        # read neighbor count + avg signal into reg C
OP_IF_NBRS = 6     # skip next instr if neighbor count != operand
OP_IF_REG = 7      # skip next instr if reg A != operand
OP_SET_REG = 8     # set reg[operand & 3] = (operand >> 2)
OP_REPLICATE = 9   # spawn copy into empty neighbor
OP_TURN = 10       # reg A = (reg A + operand) % 4
OP_IF_BONDED = 11  # skip next if not bonded
OP_GOTO = 12       # set PC to operand
OP_IF_DIST = 13    # skip next if distance to centroid > operand
OP_INC_REG = 14    # reg[operand & 3] += 1

OP_NAMES = {
    OP_NOP: "NOP", OP_MOVE: "MOVE", OP_BOND: "BOND", OP_UNBOND: "UNBOND",
    OP_SIGNAL: "SIG", OP_READ: "READ", OP_IF_NBRS: "IF_N", OP_IF_REG: "IF_R",
    OP_SET_REG: "SET", OP_REPLICATE: "REPL", OP_TURN: "TURN",
    OP_IF_BONDED: "IF_B", OP_GOTO: "GOTO", OP_IF_DIST: "IF_D",
    OP_INC_REG: "INC",
}

# Directions: N, E, S, W
DR = [(-1, 0), (0, 1), (1, 0), (0, -1)]

# ── Target shape generators ─────────────────────────────────────────────

def _shape_circle(rows, cols, radius=None):
    """Return set of (r, c) for a filled circle at center."""
    cr, cc = rows // 2, cols // 2
    if radius is None:
        radius = min(rows, cols) // 4
    pts = set()
    for r in range(rows):
        for c in range(cols):
            if (r - cr) ** 2 + (c - cc) ** 2 <= radius ** 2:
                pts.add((r, c))
    return pts

def _shape_square(rows, cols, side=None):
    """Return set of (r, c) for a filled square at center."""
    if side is None:
        side = min(rows, cols) // 3
    cr, cc = rows // 2, cols // 2
    h = side // 2
    pts = set()
    for r in range(cr - h, cr + h + 1):
        for c in range(cc - h, cc + h + 1):
            if 0 <= r < rows and 0 <= c < cols:
                pts.add((r, c))
    return pts

def _shape_letter(rows, cols, letter="H"):
    """Return set of (r, c) for a blocky letter at center."""
    # 5x5 pixel font for a few letters
    fonts = {
        "H": [
            "X...X",
            "X...X",
            "XXXXX",
            "X...X",
            "X...X",
        ],
        "L": [
            "X....",
            "X....",
            "X....",
            "X....",
            "XXXXX",
        ],
        "T": [
            "XXXXX",
            "..X..",
            "..X..",
            "..X..",
            "..X..",
        ],
        "O": [
            ".XXX.",
            "X...X",
            "X...X",
            "X...X",
            ".XXX.",
        ],
        "C": [
            ".XXXX",
            "X....",
            "X....",
            "X....",
            ".XXXX",
        ],
    }
    glyph = fonts.get(letter, fonts["H"])
    # scale to fit
    scale = max(1, min(rows, cols) // 12)
    gh, gw = len(glyph), len(glyph[0])
    sr = rows // 2 - (gh * scale) // 2
    sc = cols // 2 - (gw * scale) // 2
    pts = set()
    for gr, row in enumerate(glyph):
        for gc, ch in enumerate(row):
            if ch == "X":
                for dr in range(scale):
                    for dc in range(scale):
                        r, c = sr + gr * scale + dr, sc + gc * scale + dc
                        if 0 <= r < rows and 0 <= c < cols:
                            pts.add((r, c))
    return pts

def _shape_diamond(rows, cols):
    """Return set of (r,c) for a diamond."""
    cr, cc = rows // 2, cols // 2
    radius = min(rows, cols) // 4
    pts = set()
    for r in range(rows):
        for c in range(cols):
            if abs(r - cr) + abs(c - cc) <= radius:
                pts.add((r, c))
    return pts

# ── Programs (instruction lists) ────────────────────────────────────────

def _prog_shape_assembly():
    """Program: cells move toward target shape positions via gradient."""
    return [
        (OP_READ, 0),       # 0: read neighbors
        (OP_IF_DIST, 2),    # 1: skip next if far from target centroid
        (OP_BOND, 0),       # 2: bond if close
        (OP_IF_BONDED, 0),  # 3: skip move if bonded
        (OP_MOVE, 0),       # 4: move toward target (dir computed by engine)
        (OP_SIGNAL, 0),     # 5: broadcast state
        (OP_GOTO, 0),       # 6: loop
    ]

def _prog_self_replicate():
    """Program: cells replicate when they have few neighbors."""
    return [
        (OP_READ, 0),       # 0: read neighbor info
        (OP_IF_NBRS, 3),    # 1: skip replication if 3+ neighbors
        (OP_REPLICATE, 0),  # 2: replicate into empty neighbor
        (OP_TURN, 1),       # 3: turn clockwise
        (OP_MOVE, 0),       # 4: move forward
        (OP_SIGNAL, 0),     # 5: signal
        (OP_GOTO, 0),       # 6: loop
    ]

def _prog_distributed_counter():
    """Program: cells collectively count — each increments and signals."""
    return [
        (OP_READ, 0),       # 0: read neighbors
        (OP_INC_REG, 2),    # 1: increment reg C (counter)
        (OP_SIGNAL, 0),     # 2: broadcast counter value
        (OP_IF_NBRS, 2),    # 3: skip bond if <2 neighbors
        (OP_BOND, 0),       # 4: bond to stabilize
        (OP_NOP, 0),        # 5: no-op
        (OP_GOTO, 0),       # 6: loop
    ]

def _prog_explorer():
    """Program: random walk, signal on discovery, bond on signal."""
    return [
        (OP_READ, 0),       # 0: read neighbors
        (OP_SET_REG, 0),    # 1: set reg A to random dir (engine handles)
        (OP_MOVE, 0),       # 2: move
        (OP_IF_NBRS, 1),    # 3: skip signal if alone
        (OP_SIGNAL, 0),     # 4: signal neighbors
        (OP_BOND, 0),       # 5: try to bond
        (OP_GOTO, 0),       # 6: loop
    ]

def _prog_line_formation():
    """Program: cells form a horizontal line through the center."""
    return [
        (OP_READ, 0),       # 0: read neighbors
        (OP_IF_DIST, 1),    # 1: skip next if close to target
        (OP_MOVE, 0),       # 2: move toward target
        (OP_BOND, 0),       # 3: bond
        (OP_SIGNAL, 0),     # 4: signal
        (OP_GOTO, 0),       # 5: loop
    ]

# ── Presets ──────────────────────────────────────────────────────────────

PM_PRESETS = [
    ("Circle Formation",
     "Cells self-assemble into a filled circle using gradient-following",
     "circle", _prog_shape_assembly, 80, False),
    ("Square Formation",
     "Cells self-assemble into a square through neighbor communication",
     "square", _prog_shape_assembly, 80, False),
    ("Letter 'H'",
     "Swarm forms the letter H — distributed shape recognition",
     "letter_H", _prog_shape_assembly, 100, False),
    ("Diamond Formation",
     "Cells converge into a diamond/rhombus shape",
     "diamond", _prog_shape_assembly, 80, False),
    ("Self-Replicating Cluster",
     "Cells replicate when sparse, forming an expanding colony",
     "replicate", _prog_self_replicate, 15, False),
    ("Distributed Counter",
     "Cells collectively count via signal propagation — watch values climb",
     "counter", _prog_distributed_counter, 40, True),
    ("Random Explorers",
     "Cells random-walk, signal on contact, and bond into clusters",
     "explorer", _prog_explorer, 50, False),
    ("Line Formation",
     "Cells form a horizontal line through the center",
     "line", _prog_line_formation, 60, False),
]

# ── Cell class ───────────────────────────────────────────────────────────

class _PMCell:
    """A programmable matter cell with registers and program counter."""
    __slots__ = ("state", "reg_a", "reg_b", "reg_c", "pc", "program",
                 "signal_val", "bonded", "age")

    def __init__(self, program):
        self.state = ST_IDLE
        self.reg_a = random.randint(0, 3)  # direction register
        self.reg_b = 0                      # signal register
        self.reg_c = 0                      # general / counter
        self.pc = 0
        self.program = program
        self.signal_val = 0
        self.bonded = False
        self.age = 0


# ── Simulation engine ───────────────────────────────────────────────────

def _progmatter_init(self, preset_idx: int):
    """Initialize the programmable matter simulation."""
    name, _desc, shape_key, prog_fn, n_cells, counter_mode = PM_PRESETS[preset_idx]
    self.pm_preset_name = name
    self.pm_preset_idx = preset_idx
    self.pm_generation = 0
    self.pm_running = False
    self.pm_counter_mode = counter_mode

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(16, max_y - 6)
    cols = max(16, (max_x - 30) // 2)
    self.pm_rows = rows
    self.pm_cols = cols

    # build target shape
    if shape_key == "circle":
        self.pm_target = _shape_circle(rows, cols)
    elif shape_key == "square":
        self.pm_target = _shape_square(rows, cols)
    elif shape_key.startswith("letter_"):
        self.pm_target = _shape_letter(rows, cols, shape_key[-1])
    elif shape_key == "diamond":
        self.pm_target = _shape_diamond(rows, cols)
    elif shape_key == "line":
        cr = rows // 2
        self.pm_target = {(cr, c) for c in range(cols // 4, 3 * cols // 4)}
    else:
        self.pm_target = set()

    # compute target centroid
    if self.pm_target:
        tr = sum(r for r, c in self.pm_target) / len(self.pm_target)
        tc = sum(c for r, c in self.pm_target) / len(self.pm_target)
        self.pm_target_centroid = (tr, tc)
    else:
        self.pm_target_centroid = (rows // 2, cols // 2)

    # program
    program = prog_fn()
    self.pm_program = program

    # grid: None or _PMCell
    self.pm_grid = [[None] * cols for _ in range(rows)]

    # place cells randomly
    positions = [(r, c) for r in range(rows) for c in range(cols)]
    random.shuffle(positions)
    n_cells = min(n_cells, len(positions))
    self.pm_cell_count = n_cells
    for i in range(n_cells):
        r, c = positions[i]
        self.pm_grid[r][c] = _PMCell(list(program))
        self.pm_grid[r][c].reg_a = random.randint(0, 3)

    # signal field (for visualization and READ)
    self.pm_signal = [[0.0] * cols for _ in range(rows)]
    # damage tracking for self-repair demo
    self.pm_damage_flash = 0
    # stats
    self.pm_bonded_count = 0
    self.pm_on_target = 0
    self.pm_max_signal = 0
    # viz mode: 0=cells, 1=signals, 2=target overlay
    self.pm_viz = 0
    self.pm_cursor_r = rows // 2
    self.pm_cursor_c = cols // 2
    self.pm_show_info = True
    self.pm_speed = 1  # steps per frame


def _progmatter_step(self):
    """Execute one generation of the programmable matter simulation."""
    rows, cols = self.pm_rows, self.pm_cols
    grid = self.pm_grid
    target = self.pm_target
    tc_r, tc_c = self.pm_target_centroid

    # Phase 1: execute programs for all cells
    moves = []  # (old_r, old_c, new_r, new_c)
    replications = []  # (r, c, nr, nc)

    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            if cell is None:
                continue

            cell.age += 1
            prog = cell.program
            if not prog:
                continue

            # execute up to 2 instructions per step
            for _ in range(2):
                if cell.pc >= len(prog):
                    cell.pc = 0
                op, operand = prog[cell.pc]
                cell.pc += 1
                if cell.pc >= len(prog):
                    cell.pc = 0

                if op == OP_NOP:
                    pass

                elif op == OP_MOVE:
                    d = cell.reg_a % 4
                    # if target exists, bias movement toward nearest target cell
                    if target:
                        best_d = _best_dir_to_target(r, c, target, rows, cols)
                        if best_d >= 0 and not cell.bonded:
                            d = best_d
                    nr, nc = r + DR[d][0], c + DR[d][1]
                    if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is None:
                        moves.append((r, c, nr, nc))
                    cell.state = ST_MOVING

                elif op == OP_BOND:
                    # bond if adjacent to another cell
                    for dr, dc in DR:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is not None:
                            cell.bonded = True
                            cell.state = ST_BONDED
                            grid[nr][nc].bonded = True
                            grid[nr][nc].state = ST_BONDED
                            break

                elif op == OP_UNBOND:
                    cell.bonded = False
                    cell.state = ST_IDLE

                elif op == OP_SIGNAL:
                    cell.signal_val = cell.reg_b if cell.reg_b else cell.reg_c
                    cell.state = ST_SIGNALING
                    self.pm_signal[r][c] = max(self.pm_signal[r][c],
                                               float(cell.signal_val) + 1.0)

                elif op == OP_READ:
                    nbr_count = 0
                    sig_sum = 0.0
                    for dr, dc in DR:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if grid[nr][nc] is not None:
                                nbr_count += 1
                                sig_sum += grid[nr][nc].signal_val
                    cell.reg_c = nbr_count
                    cell.reg_b = int(sig_sum / max(1, nbr_count))

                elif op == OP_IF_NBRS:
                    nbr_count = 0
                    for dr, dc in DR:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is not None:
                            nbr_count += 1
                    if nbr_count >= operand:
                        cell.pc += 1
                        if cell.pc >= len(prog):
                            cell.pc = 0

                elif op == OP_IF_REG:
                    if cell.reg_a != operand:
                        cell.pc += 1
                        if cell.pc >= len(prog):
                            cell.pc = 0

                elif op == OP_SET_REG:
                    reg_idx = operand & 3
                    val = (operand >> 2) if (operand >> 2) else random.randint(0, 3)
                    if reg_idx == 0:
                        cell.reg_a = val
                    elif reg_idx == 1:
                        cell.reg_b = val
                    else:
                        cell.reg_c = val

                elif op == OP_REPLICATE:
                    for d in range(4):
                        dr, dc = DR[d]
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is None:
                            replications.append((r, c, nr, nc))
                            break

                elif op == OP_TURN:
                    cell.reg_a = (cell.reg_a + operand) % 4

                elif op == OP_IF_BONDED:
                    if not cell.bonded:
                        cell.pc += 1
                        if cell.pc >= len(prog):
                            cell.pc = 0

                elif op == OP_GOTO:
                    cell.pc = operand % len(prog)

                elif op == OP_IF_DIST:
                    if target:
                        dist = _min_dist_to_target(r, c, target, rows, cols)
                        if dist > operand:
                            cell.pc += 1
                            if cell.pc >= len(prog):
                                cell.pc = 0

                elif op == OP_INC_REG:
                    reg_idx = operand & 3
                    if reg_idx == 0:
                        cell.reg_a += 1
                    elif reg_idx == 1:
                        cell.reg_b += 1
                    else:
                        cell.reg_c += 1

    # Phase 2: resolve moves (first-come wins)
    occupied = set()
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] is not None:
                occupied.add((r, c))

    random.shuffle(moves)
    for old_r, old_c, new_r, new_c in moves:
        if (new_r, new_c) not in occupied and grid[old_r][old_c] is not None:
            cell = grid[old_r][old_c]
            if cell.bonded:
                continue  # bonded cells don't move
            grid[new_r][new_c] = cell
            grid[old_r][old_c] = None
            occupied.discard((old_r, old_c))
            occupied.add((new_r, new_c))

    # Phase 3: replications (limit growth)
    random.shuffle(replications)
    max_cells = (rows * cols) // 3
    cell_count = sum(1 for r in range(rows) for c in range(cols) if grid[r][c] is not None)
    for _src_r, _src_c, nr, nc in replications:
        if cell_count >= max_cells:
            break
        if grid[nr][nc] is None:
            parent = grid[_src_r][_src_c]
            if parent is not None:
                child = _PMCell(list(parent.program))
                child.reg_a = random.randint(0, 3)
                child.reg_b = parent.reg_b
                grid[nr][nc] = child
                cell_count += 1

    # Phase 4: diffuse signal field
    new_sig = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            val = self.pm_signal[r][c] * 0.6
            for dr, dc in DR:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    val += self.pm_signal[nr][nc] * 0.08
            if grid[r][c] is not None and grid[r][c].signal_val > 0:
                val = max(val, float(grid[r][c].signal_val))
            new_sig[r][c] = val
    self.pm_signal = new_sig

    # Phase 5: stats
    bonded = 0
    on_target = 0
    max_sig = 0
    cell_count = 0
    for r in range(rows):
        for c in range(cols):
            cell = grid[r][c]
            if cell is not None:
                cell_count += 1
                if cell.bonded:
                    bonded += 1
                if (r, c) in target:
                    on_target += 1
                max_sig = max(max_sig, cell.signal_val)
    self.pm_bonded_count = bonded
    self.pm_on_target = on_target
    self.pm_cell_count = cell_count
    self.pm_max_signal = max_sig

    if self.pm_damage_flash > 0:
        self.pm_damage_flash -= 1

    self.pm_generation += 1


def _best_dir_to_target(r, c, target, rows, cols):
    """Return direction (0-3) that moves (r,c) closest to nearest target cell."""
    best_dist = float("inf")
    best_d = -1
    # sample up to 50 target cells to keep it fast
    sample = random.sample(list(target), min(50, len(target)))
    min_dist = float("inf")
    closest_r, closest_c = r, c
    for tr, tc in sample:
        d = abs(tr - r) + abs(tc - c)
        if d < min_dist:
            min_dist = d
            closest_r, closest_c = tr, tc

    for d in range(4):
        nr, nc = r + DR[d][0], c + DR[d][1]
        if 0 <= nr < rows and 0 <= nc < cols:
            dist = abs(closest_r - nr) + abs(closest_c - nc)
            if dist < best_dist:
                best_dist = dist
                best_d = d
    return best_d


def _min_dist_to_target(r, c, target, rows, cols):
    """Manhattan distance from (r,c) to nearest target cell."""
    if (r, c) in target:
        return 0
    sample = random.sample(list(target), min(30, len(target)))
    return min(abs(tr - r) + abs(tc - c) for tr, tc in sample)


# ── Enter / Exit ─────────────────────────────────────────────────────────

def _enter_progmatter_mode(self):
    """Enter Programmable Matter — show preset menu."""
    self.pm_menu = True
    self.pm_menu_sel = 0
    self._flash("Programmable Matter — select a configuration")


def _exit_progmatter_mode(self):
    """Exit Programmable Matter mode."""
    self.progmatter_mode = False
    self.pm_menu = False
    self.pm_running = False
    self._flash("Programmable Matter mode OFF")


# ── Menu key handling ────────────────────────────────────────────────────

def _handle_progmatter_menu_key(self, key: int) -> bool:
    """Handle keys in preset selection menu."""
    if key == curses.KEY_UP:
        self.pm_menu_sel = (self.pm_menu_sel - 1) % len(PM_PRESETS)
        return True
    if key == curses.KEY_DOWN:
        self.pm_menu_sel = (self.pm_menu_sel + 1) % len(PM_PRESETS)
        return True
    if key in (curses.KEY_ENTER, 10, 13):
        self.pm_menu = False
        _progmatter_init(self, self.pm_menu_sel)
        self._flash(f"Programmable Matter: {PM_PRESETS[self.pm_menu_sel][0]}")
        return True
    if key in (ord("q"), ord("Q"), 27):
        _exit_progmatter_mode(self)
        return True
    return False


# ── Simulation key handling ──────────────────────────────────────────────

def _handle_progmatter_key(self, key: int) -> bool:
    """Handle keys during simulation."""
    if key == ord(" "):
        self.pm_running = not self.pm_running
        return True
    if key in (ord("q"), ord("Q"), 27):
        _exit_progmatter_mode(self)
        return True
    if key == ord("v"):
        self.pm_viz = (self.pm_viz + 1) % 3
        labels = ["Cells", "Signal Field", "Target Overlay"]
        self._flash(f"View: {labels[self.pm_viz]}")
        return True
    if key == ord("i"):
        self.pm_show_info = not self.pm_show_info
        return True
    if key == ord("d"):
        # damage: remove cells in 3x3 area around cursor
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                nr = self.pm_cursor_r + dr
                nc = self.pm_cursor_c + dc
                if 0 <= nr < self.pm_rows and 0 <= nc < self.pm_cols:
                    if self.pm_grid[nr][nc] is not None:
                        self.pm_grid[nr][nc] = None
        self.pm_damage_flash = 10
        self._flash("Damage dealt! Watch self-repair...")
        return True
    if key == ord("+") or key == ord("="):
        self.pm_speed = min(5, self.pm_speed + 1)
        self._flash(f"Speed: {self.pm_speed}x")
        return True
    if key == ord("-"):
        self.pm_speed = max(1, self.pm_speed - 1)
        self._flash(f"Speed: {self.pm_speed}x")
        return True
    # cursor movement
    if key == curses.KEY_UP:
        self.pm_cursor_r = max(0, self.pm_cursor_r - 1)
        return True
    if key == curses.KEY_DOWN:
        self.pm_cursor_r = min(self.pm_rows - 1, self.pm_cursor_r + 1)
        return True
    if key == curses.KEY_LEFT:
        self.pm_cursor_c = max(0, self.pm_cursor_c - 1)
        return True
    if key == curses.KEY_RIGHT:
        self.pm_cursor_c = min(self.pm_cols - 1, self.pm_cursor_c + 1)
        return True
    if key == ord("r"):
        # reset / restart with same preset
        _progmatter_init(self, self.pm_preset_idx)
        self._flash("Reset!")
        return True
    if key == ord("s"):
        # single step
        for _ in range(self.pm_speed):
            _progmatter_step(self)
        return True
    return False


# ── Drawing ──────────────────────────────────────────────────────────────

def _draw_progmatter_menu(self, max_y: int, max_x: int):
    """Draw the preset selection menu."""
    title = "═══ PROGRAMMABLE MATTER ═══"
    subtitle = "Self-assembling state-machine cells"
    y = max(0, max_y // 2 - len(PM_PRESETS) - 4)
    x = max(0, (max_x - len(title)) // 2)

    try:
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, x, title)
        self.stdscr.attroff(curses.A_BOLD)
        y += 1
        sx = max(0, (max_x - len(subtitle)) // 2)
        self.stdscr.addstr(y, sx, subtitle, curses.A_DIM)
        y += 2

        for i, (name, desc, *_rest) in enumerate(PM_PRESETS):
            if y + 1 >= max_y:
                break
            marker = ">" if i == self.pm_menu_sel else " "
            attr = curses.A_REVERSE if i == self.pm_menu_sel else 0
            line = f" {marker} {name}"
            self.stdscr.addstr(y, x, line[:max_x - x - 1], attr | curses.A_BOLD)
            y += 1
            if y < max_y:
                dline = f"     {desc}"
                self.stdscr.addstr(y, x, dline[:max_x - x - 1], curses.A_DIM)
            y += 1

        y += 1
        if y < max_y:
            help_text = "UP/DOWN select  |  ENTER start  |  Q quit"
            hx = max(0, (max_x - len(help_text)) // 2)
            self.stdscr.addstr(y, hx, help_text, curses.A_DIM)
    except curses.error:
        pass


def _draw_progmatter(self, max_y: int, max_x: int):
    """Draw the programmable matter simulation."""
    rows, cols = self.pm_rows, self.pm_cols
    grid = self.pm_grid
    target = self.pm_target
    viz = self.pm_viz
    sig = self.pm_signal

    # cell glyphs by state
    state_ch = {
        ST_IDLE: ".",
        ST_MOVING: ">",
        ST_BONDED: "#",
        ST_SIGNALING: "*",
    }

    # determine color pairs available
    has_color = curses.has_colors()

    # draw grid
    for r in range(min(rows, max_y - 3)):
        for c in range(min(cols, (max_x - 28) // 2)):
            sx = c * 2
            sy = r + 1
            if sy >= max_y - 2 or sx + 1 >= max_x - 28:
                continue

            cell = grid[r][c]
            on_tgt = (r, c) in target

            try:
                if viz == 0:  # cell view
                    if cell is not None:
                        ch = state_ch.get(cell.state, "?")
                        attr = curses.A_BOLD
                        if cell.bonded:
                            attr |= curses.A_REVERSE
                        if cell.state == ST_SIGNALING:
                            attr |= curses.A_BOLD
                        if has_color:
                            if cell.bonded:
                                attr |= curses.color_pair(3)  # green
                            elif cell.state == ST_MOVING:
                                attr |= curses.color_pair(5)  # cyan
                            elif cell.state == ST_SIGNALING:
                                attr |= curses.color_pair(4)  # yellow
                            else:
                                attr |= curses.color_pair(7)  # white
                        self.stdscr.addstr(sy, sx, ch, attr)
                    elif on_tgt and target:
                        self.stdscr.addstr(sy, sx, ".", curses.A_DIM)
                    else:
                        self.stdscr.addstr(sy, sx, " ")

                elif viz == 1:  # signal field
                    sv = sig[r][c]
                    if sv > 0.5:
                        level = min(4, int(sv))
                        chars = " .oO@"
                        ch = chars[min(level, len(chars) - 1)]
                        attr = curses.A_BOLD if sv > 2.0 else 0
                        if has_color:
                            attr |= curses.color_pair(4)  # yellow
                        self.stdscr.addstr(sy, sx, ch, attr)
                    elif cell is not None:
                        self.stdscr.addstr(sy, sx, ".", curses.A_DIM)
                    else:
                        self.stdscr.addstr(sy, sx, " ")

                elif viz == 2:  # target overlay
                    if cell is not None and on_tgt:
                        # on target - green
                        attr = curses.A_BOLD
                        if has_color:
                            attr |= curses.color_pair(3)
                        self.stdscr.addstr(sy, sx, "#", attr)
                    elif cell is not None and not on_tgt:
                        # off target - red
                        attr = curses.A_DIM
                        if has_color:
                            attr |= curses.color_pair(2)
                        self.stdscr.addstr(sy, sx, "o", attr)
                    elif on_tgt:
                        # empty target cell - dim marker
                        attr = curses.A_DIM
                        if has_color:
                            attr |= curses.color_pair(5)
                        self.stdscr.addstr(sy, sx, "+", attr)
                    else:
                        self.stdscr.addstr(sy, sx, " ")

            except curses.error:
                pass

    # cursor
    cy = self.pm_cursor_r + 1
    cx = self.pm_cursor_c * 2
    if 0 < cy < max_y - 2 and 0 <= cx < max_x - 28:
        try:
            self.stdscr.addstr(cy, cx, "X",
                               curses.A_BLINK | curses.A_BOLD |
                               (curses.color_pair(2) if has_color else 0))
        except curses.error:
            pass

    # damage flash
    if self.pm_damage_flash > 0:
        try:
            self.stdscr.addstr(0, 0, " DAMAGE! ", curses.A_BOLD | curses.A_REVERSE |
                               (curses.color_pair(2) if has_color else 0))
        except curses.error:
            pass

    # info panel (right side)
    if self.pm_show_info:
        _draw_pm_info(self, max_y, max_x, has_color)


def _draw_pm_info(self, max_y, max_x, has_color):
    """Draw the right-side info panel."""
    px = max_x - 27
    if px < 10:
        return
    py = 1
    target = self.pm_target
    target_size = len(target) if target else 0

    lines = [
        ("PROGRAMMABLE MATTER", curses.A_BOLD),
        (f"Preset: {self.pm_preset_name}", curses.A_DIM),
        ("", 0),
        (f"Gen: {self.pm_generation}", 0),
        (f"Cells: {self.pm_cell_count}", 0),
        (f"Bonded: {self.pm_bonded_count}", 0),
    ]

    if target_size > 0:
        pct = self.pm_on_target / target_size * 100 if target_size else 0
        lines.append((f"On target: {self.pm_on_target}/{target_size}", 0))
        # progress bar
        bar_w = 20
        filled = int(pct / 100 * bar_w)
        bar = "[" + "#" * filled + "." * (bar_w - filled) + "]"
        lines.append((f"{pct:5.1f}% {bar}", curses.A_BOLD))

    if self.pm_counter_mode:
        lines.append((f"Max signal: {self.pm_max_signal}", 0))

    lines.append(("", 0))
    lines.append((f"Speed: {self.pm_speed}x", curses.A_DIM))
    viz_names = ["Cells", "Signals", "Target"]
    lines.append((f"View: {viz_names[self.pm_viz]}", curses.A_DIM))

    lines.append(("", 0))
    lines.append(("-- Controls --", curses.A_BOLD))
    lines.append(("SPACE play/pause", curses.A_DIM))
    lines.append(("S     single step", curses.A_DIM))
    lines.append(("V     cycle view", curses.A_DIM))
    lines.append(("D     deal damage", curses.A_DIM))
    lines.append(("+/-   speed", curses.A_DIM))
    lines.append(("R     reset", curses.A_DIM))
    lines.append(("I     toggle info", curses.A_DIM))
    lines.append(("Q     quit", curses.A_DIM))

    # program listing
    lines.append(("", 0))
    lines.append(("-- Program --", curses.A_BOLD))
    for i, (op, operand) in enumerate(self.pm_program):
        name = OP_NAMES.get(op, "???")
        marker = ">" if i == 0 else " "  # just show program
        lines.append((f" {marker}{i:02d} {name} {operand}", curses.A_DIM))

    for i, (text, attr) in enumerate(lines):
        y = py + i
        if y >= max_y - 1:
            break
        try:
            self.stdscr.addstr(y, px, text[:26], attr)
        except curses.error:
            pass


def _is_progmatter_auto_stepping(self):
    """Return True if mode should auto-step."""
    return self.pm_running


# ── Registration ─────────────────────────────────────────────────────────

def register(App):
    """Attach Programmable Matter methods to the App class."""
    App._progmatter_step = _progmatter_step
    App._progmatter_init = _progmatter_init
    App._enter_progmatter_mode = _enter_progmatter_mode
    App._exit_progmatter_mode = _exit_progmatter_mode
    App._handle_progmatter_menu_key = _handle_progmatter_menu_key
    App._handle_progmatter_key = _handle_progmatter_key
    App._draw_progmatter_menu = _draw_progmatter_menu
    App._draw_progmatter = _draw_progmatter
    App._is_progmatter_auto_stepping = _is_progmatter_auto_stepping
