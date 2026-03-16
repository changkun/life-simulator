"""Mode: fluid_life — hybrid Game of Life + Navier-Stokes fluid simulation.

Live cells generate heat (buoyancy), dead cells sink. The fluid advects cells
to new grid positions before the CA rule is applied, so gliders ride currents,
oscillators create vortex streets, and guns pump jets of fluid. Users can place
fans, heaters, and walls to sculpt the flow.
"""
import curses
import math
import random
import time

from life.colors import colormap_addstr

# ══════════════════════════════════════════════════════════════════════
#  Fluid of Life — coupled CA + LBM fluid dynamics
# ══════════════════════════════════════════════════════════════════════

# D2Q9 lattice velocities
FL_EX = [0, 1, 0, -1,  0, 1, -1, -1,  1]
FL_EY = [0, 0, 1,  0, -1, 1,  1, -1, -1]
FL_W  = [4.0/9, 1.0/9, 1.0/9, 1.0/9, 1.0/9,
         1.0/36, 1.0/36, 1.0/36, 1.0/36]
FL_OPP = [0, 3, 4, 1, 2, 7, 8, 5, 6]

# Tool types for interactive placement
FL_TOOLS = [
    ("cursor", "Select / toggle cells"),
    ("wall",   "Place solid walls"),
    ("fan_r",  "Fan blowing right →"),
    ("fan_l",  "Fan blowing left ←"),
    ("fan_u",  "Fan blowing up ↑"),
    ("fan_d",  "Fan blowing down ↓"),
    ("heater", "Heat source (buoyancy up)"),
    ("cooler", "Cold sink (pushes down)"),
    ("eraser", "Remove walls/fans/heaters"),
]

FL_PRESETS = [
    ("Glider Stream",
     "Classic gliders advected by gentle rightward wind",
     1.6, 0.04, 0.0008, 0.15),
    ("Blinker Vortices",
     "Oscillators stir the fluid into vortex streets",
     1.5, 0.02, 0.0012, 0.20),
    ("Gosper Gun Jet",
     "Gosper gun pumps a fluid jet across the domain",
     1.7, 0.03, 0.0010, 0.18),
    ("Thermal Soup",
     "Random soup with strong buoyancy — cells rise and swirl",
     1.4, 0.01, 0.0020, 0.25),
    ("Wind Tunnel",
     "Strong horizontal wind advects all CA structures rightward",
     1.8, 0.08, 0.0005, 0.10),
    ("Convection Cells",
     "Bottom heater drives Rayleigh-Bénard-like rolls through CA",
     1.5, 0.01, 0.0015, 0.22),
]

# Glider (SE direction) pattern offsets
_GLIDER = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]

# Gosper glider gun pattern
_GOSPER_GUN = [
    (0,24),(1,22),(1,24),(2,12),(2,13),(2,20),(2,21),(2,34),(2,35),
    (3,11),(3,15),(3,20),(3,21),(3,34),(3,35),(4,0),(4,1),(4,10),
    (4,16),(4,20),(4,21),(5,0),(5,1),(5,10),(5,14),(5,16),(5,17),
    (5,22),(5,24),(6,10),(6,16),(6,24),(7,11),(7,15),(8,12),(8,13),
]

# Blinker (horizontal) offsets
_BLINKER = [(0, 0), (0, 1), (0, 2)]


def _enter_fluidlife_mode(self):
    """Enter Fluid of Life — show preset menu."""
    self.fluidlife_menu = True
    self.fluidlife_menu_sel = 0
    self._flash("Fluid of Life — select a configuration")


def _exit_fluidlife_mode(self):
    """Exit Fluid of Life mode."""
    self.fluidlife_mode = False
    self.fluidlife_menu = False
    self.fluidlife_running = False
    self._flash("Fluid of Life mode OFF")


def _fluidlife_init(self, preset_idx: int):
    """Initialize the coupled CA + LBM simulation."""
    name, _desc, omega, inflow, buoyancy, advection = FL_PRESETS[preset_idx]
    self.fluidlife_preset_name = name
    self.fluidlife_preset_idx = preset_idx
    self.fluidlife_omega = omega
    self.fluidlife_inflow = inflow
    self.fluidlife_buoyancy = buoyancy
    self.fluidlife_advection = advection
    self.fluidlife_generation = 0
    self.fluidlife_running = False
    self.fluidlife_viz = 0  # 0=coupled, 1=fluid speed, 2=CA only, 3=vorticity
    self.fluidlife_tool = 0  # cursor
    self.fluidlife_cursor_r = 0
    self.fluidlife_cursor_c = 0
    self.fluidlife_show_velocity = True
    self.fluidlife_ca_interval = 3  # CA steps every N fluid steps
    self.fluidlife_steps_per_frame = 2

    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(10, max_y - 4)
    cols = max(10, (max_x - 1) // 2)
    self.fluidlife_rows = rows
    self.fluidlife_cols = cols

    # CA grid: 0=dead, 1=alive
    self.fluidlife_cells = [[0] * cols for _ in range(rows)]
    # Cell age (for coloring)
    self.fluidlife_age = [[0] * cols for _ in range(rows)]

    # Interactive objects: walls, fans, heaters
    # Type grid: 0=empty, 1=wall, 2=fan_r, 3=fan_l, 4=fan_u, 5=fan_d, 6=heater, 7=cooler
    self.fluidlife_objects = [[0] * cols for _ in range(rows)]

    # LBM distribution functions
    ex, ey, w = FL_EX, FL_EY, FL_W
    u0 = inflow
    self.fluidlife_f = []
    for r in range(rows):
        row_data = []
        for c in range(cols):
            cell = [0.0] * 9
            rho = 1.0
            ux, uy = u0, 0.0
            usq = ux * ux + uy * uy
            for i in range(9):
                eu = ex[i] * ux + ey[i] * uy
                cell[i] = w[i] * rho * (1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * usq)
            row_data.append(cell)
        self.fluidlife_f.append(row_data)

    # Seed initial CA pattern based on preset
    _fluidlife_seed(self, preset_idx)

    self.fluidlife_menu = False
    self.fluidlife_mode = True
    self._flash(f"Fluid of Life: {name} — Space to start, t=tool")


def _fluidlife_seed(self, preset_idx: int):
    """Seed initial CA patterns based on preset."""
    rows = self.fluidlife_rows
    cols = self.fluidlife_cols
    cells = self.fluidlife_cells

    if preset_idx == 0:  # Glider Stream — several gliders
        for i in range(5):
            sr, sc = rows // 4 + i * 3, 5 + i * 6
            for dr, dc in _GLIDER:
                r2, c2 = (sr + dr) % rows, (sc + dc) % cols
                cells[r2][c2] = 1
    elif preset_idx == 1:  # Blinker Vortices
        for i in range(6):
            for j in range(4):
                sr = rows // 6 + i * (rows // 7)
                sc = cols // 5 + j * (cols // 5)
                for dr, dc in _BLINKER:
                    r2, c2 = (sr + dr) % rows, (sc + dc) % cols
                    cells[r2][c2] = 1
    elif preset_idx == 2:  # Gosper Gun
        sr, sc = rows // 3, 5
        for dr, dc in _GOSPER_GUN:
            r2, c2 = sr + dr, sc + dc
            if 0 <= r2 < rows and 0 <= c2 < cols:
                cells[r2][c2] = 1
    elif preset_idx == 3:  # Thermal Soup
        for r in range(rows):
            for c in range(cols):
                if random.random() < 0.15:
                    cells[r][c] = 1
    elif preset_idx == 4:  # Wind Tunnel — gliders spread out
        for i in range(8):
            sr = rows // 8 + i * (rows // 9)
            sc = random.randint(3, cols // 3)
            for dr, dc in _GLIDER:
                r2, c2 = (sr + dr) % rows, (sc + dc) % cols
                cells[r2][c2] = 1
    elif preset_idx == 5:  # Convection Cells — bottom row heaters + soup
        objs = self.fluidlife_objects
        for c in range(cols):
            if c % 8 < 4:
                objs[rows - 1][c] = 6  # heater
            else:
                objs[0][c] = 7  # cooler
        for r in range(rows // 3, 2 * rows // 3):
            for c in range(cols):
                if random.random() < 0.12:
                    cells[r][c] = 1


def _fluidlife_lbm_step(self):
    """One LBM step: stream, bounce-back, buoyancy forcing, collide."""
    rows = self.fluidlife_rows
    cols = self.fluidlife_cols
    f = self.fluidlife_f
    cells = self.fluidlife_cells
    objs = self.fluidlife_objects
    omega = self.fluidlife_omega
    buoyancy = self.fluidlife_buoyancy
    inflow = self.fluidlife_inflow
    ex, ey, w, opp = FL_EX, FL_EY, FL_W, FL_OPP

    # Streaming
    f_new = [[[0.0] * 9 for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            for i in range(9):
                sr = (r - ey[i]) % rows
                sc = (c - ex[i]) % cols
                f_new[r][c][i] = f[sr][sc][i]

    # Bounce-back for walls
    for r in range(rows):
        for c in range(cols):
            if objs[r][c] == 1:  # wall
                for i in range(9):
                    f_new[r][c][i] = f[r][c][opp[i]]

    # Collision + forcing
    for r in range(rows):
        for c in range(cols):
            if objs[r][c] == 1:
                continue
            fc = f_new[r][c]
            rho = 0.0
            ux = 0.0
            uy = 0.0
            for i in range(9):
                rho += fc[i]
                ux += ex[i] * fc[i]
                uy += ey[i] * fc[i]
            if rho > 0.0:
                ux /= rho
                uy /= rho
            else:
                rho = 1.0

            # Buoyancy: live cells push fluid upward (negative y)
            if cells[r][c]:
                uy -= buoyancy
            # Object forcing
            ot = objs[r][c]
            force_x, force_y = 0.0, 0.0
            if ot == 2:    # fan right
                force_x = 0.05
            elif ot == 3:  # fan left
                force_x = -0.05
            elif ot == 4:  # fan up
                force_y = -0.05
            elif ot == 5:  # fan down
                force_y = 0.05
            elif ot == 6:  # heater
                force_y = -buoyancy * 3
            elif ot == 7:  # cooler
                force_y = buoyancy * 3
            ux += force_x
            uy += force_y

            # BGK collision
            usq = ux * ux + uy * uy
            for i in range(9):
                eu = ex[i] * ux + ey[i] * uy
                feq = w[i] * rho * (1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * usq)
                fc[i] += omega * (feq - fc[i])

    # Boundary conditions: left inflow, right outflow
    for r in range(rows):
        if objs[r][0] != 1:
            rho = 1.0
            ux, uy = inflow, 0.0
            usq = ux * ux
            for i in range(9):
                eu = ex[i] * ux + ey[i] * uy
                f_new[r][0][i] = w[i] * rho * (1.0 + 3.0 * eu + 4.5 * eu * eu - 1.5 * usq)
        if objs[r][cols - 1] != 1 and objs[r][cols - 2] != 1:
            for i in range(9):
                f_new[r][cols - 1][i] = f_new[r][cols - 2][i]

    self.fluidlife_f = f_new


def _fluidlife_get_velocity(self):
    """Extract macroscopic velocity field from LBM distributions."""
    rows = self.fluidlife_rows
    cols = self.fluidlife_cols
    f = self.fluidlife_f
    objs = self.fluidlife_objects
    ex, ey = FL_EX, FL_EY
    ux = [[0.0] * cols for _ in range(rows)]
    uy = [[0.0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if objs[r][c] == 1:
                continue
            fc = f[r][c]
            rho = 0.0
            vx = 0.0
            vy = 0.0
            for i in range(9):
                rho += fc[i]
                vx += ex[i] * fc[i]
                vy += ey[i] * fc[i]
            if rho > 0.0:
                ux[r][c] = vx / rho
                uy[r][c] = vy / rho
    return ux, uy


def _fluidlife_advect(self):
    """Advect CA cells according to fluid velocity field.

    Each live cell accumulates displacement from the velocity field.
    When displacement exceeds 1 cell, the cell moves to the new position.
    Uses a simple semi-Lagrangian approach.
    """
    rows = self.fluidlife_rows
    cols = self.fluidlife_cols
    cells = self.fluidlife_cells
    age = self.fluidlife_age
    objs = self.fluidlife_objects
    adv = self.fluidlife_advection
    ux, uy = _fluidlife_get_velocity(self)

    new_cells = [[0] * cols for _ in range(rows)]
    new_age = [[0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            if not cells[r][c]:
                continue
            # Compute displacement
            dx = ux[r][c] * adv
            dy = uy[r][c] * adv
            # Target position (with some randomness for natural feel)
            nr = r + int(round(dy * 20))
            nc = c + int(round(dx * 20))
            # Wrap toroidally
            nr = nr % rows
            nc = nc % cols
            # Don't move into walls or occupied cells
            if objs[nr][nc] == 1:
                nr, nc = r, c
            if new_cells[nr][nc] == 0:
                new_cells[nr][nc] = 1
                new_age[nr][nc] = age[r][c]
            else:
                # Collision: stay in place if possible
                if new_cells[r][c] == 0:
                    new_cells[r][c] = 1
                    new_age[r][c] = age[r][c]

    self.fluidlife_cells = new_cells
    self.fluidlife_age = new_age


def _fluidlife_ca_step(self):
    """Apply one generation of Conway's Game of Life (B3/S23)."""
    rows = self.fluidlife_rows
    cols = self.fluidlife_cols
    cells = self.fluidlife_cells
    age = self.fluidlife_age
    objs = self.fluidlife_objects
    new_cells = [[0] * cols for _ in range(rows)]
    new_age = [[0] * cols for _ in range(rows)]

    for r in range(rows):
        for c in range(cols):
            if objs[r][c] == 1:
                continue
            # Count neighbors (Moore neighborhood, toroidal)
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr = (r + dr) % rows
                    nc = (c + dc) % cols
                    if cells[nr][nc]:
                        n += 1
            alive = cells[r][c]
            if alive:
                if n == 2 or n == 3:
                    new_cells[r][c] = 1
                    new_age[r][c] = age[r][c] + 1
            else:
                if n == 3:
                    new_cells[r][c] = 1
                    new_age[r][c] = 1

    self.fluidlife_cells = new_cells
    self.fluidlife_age = new_age


def _fluidlife_step(self):
    """One combined step: multiple LBM sub-steps, periodic advection + CA."""
    gen = self.fluidlife_generation

    for _ in range(self.fluidlife_steps_per_frame):
        _fluidlife_lbm_step(self)

    # Advect cells every step
    _fluidlife_advect(self)

    # CA update every ca_interval steps
    if gen % self.fluidlife_ca_interval == 0:
        _fluidlife_ca_step(self)

    self.fluidlife_generation += 1


def _fluidlife_count_population(self):
    """Count live cells."""
    total = 0
    for row in self.fluidlife_cells:
        for c in row:
            if c:
                total += 1
    return total


# ── Key handling ──────────────────────────────────────────────────────

def _handle_fluidlife_menu_key(self, key: int) -> bool:
    """Handle input in preset selection menu."""
    n = len(FL_PRESETS)
    if key in (ord('j'), curses.KEY_DOWN):
        self.fluidlife_menu_sel = (self.fluidlife_menu_sel + 1) % n
    elif key in (ord('k'), curses.KEY_UP):
        self.fluidlife_menu_sel = (self.fluidlife_menu_sel - 1) % n
    elif key in (ord('\n'), ord('\r')):
        _fluidlife_init(self, self.fluidlife_menu_sel)
    elif key in (ord('q'), 27):
        self.fluidlife_menu = False
        self._flash("Fluid of Life cancelled")
    return True


def _handle_fluidlife_key(self, key: int) -> bool:
    """Handle input in active simulation."""
    rows = self.fluidlife_rows
    cols = self.fluidlife_cols

    if key == ord(' '):
        self.fluidlife_running = not self.fluidlife_running
    elif key in (ord('n'), ord('.')):
        _fluidlife_step(self)
    elif key == ord('v'):
        self.fluidlife_viz = (self.fluidlife_viz + 1) % 4
        names = ["Coupled", "Fluid Speed", "CA Only", "Vorticity"]
        self._flash(f"Viz: {names[self.fluidlife_viz]}")
    elif key == ord('t') or key == ord('T'):
        self.fluidlife_tool = (self.fluidlife_tool + 1) % len(FL_TOOLS)
        tool_name, tool_desc = FL_TOOLS[self.fluidlife_tool]
        self._flash(f"Tool: {tool_name} — {tool_desc}")
    elif key == ord('f'):
        self.fluidlife_show_velocity = not self.fluidlife_show_velocity
    elif key == curses.KEY_UP or key == ord('w'):
        self.fluidlife_cursor_r = (self.fluidlife_cursor_r - 1) % rows
    elif key == curses.KEY_DOWN or key == ord('s'):
        self.fluidlife_cursor_r = (self.fluidlife_cursor_r + 1) % rows
    elif key == curses.KEY_LEFT or key == ord('a'):
        self.fluidlife_cursor_c = (self.fluidlife_cursor_c - 1) % cols
    elif key == curses.KEY_RIGHT or key == ord('d'):
        self.fluidlife_cursor_c = (self.fluidlife_cursor_c + 1) % cols
    elif key in (ord('\n'), ord('\r'), ord('e')):
        # Place with current tool
        cr, cc = self.fluidlife_cursor_r, self.fluidlife_cursor_c
        tool_name = FL_TOOLS[self.fluidlife_tool][0]
        if tool_name == "cursor":
            self.fluidlife_cells[cr][cc] = 1 - self.fluidlife_cells[cr][cc]
            if self.fluidlife_cells[cr][cc]:
                self.fluidlife_age[cr][cc] = 1
        elif tool_name == "wall":
            self.fluidlife_objects[cr][cc] = 1
        elif tool_name == "fan_r":
            self.fluidlife_objects[cr][cc] = 2
        elif tool_name == "fan_l":
            self.fluidlife_objects[cr][cc] = 3
        elif tool_name == "fan_u":
            self.fluidlife_objects[cr][cc] = 4
        elif tool_name == "fan_d":
            self.fluidlife_objects[cr][cc] = 5
        elif tool_name == "heater":
            self.fluidlife_objects[cr][cc] = 6
        elif tool_name == "cooler":
            self.fluidlife_objects[cr][cc] = 7
        elif tool_name == "eraser":
            self.fluidlife_objects[cr][cc] = 0
    elif key == ord('b') or key == ord('B'):
        delta = 0.0002 if key == ord('b') else -0.0002
        self.fluidlife_buoyancy = max(0.0, min(0.01, self.fluidlife_buoyancy + delta))
        self._flash(f"Buoyancy: {self.fluidlife_buoyancy:.4f}")
    elif key == ord('u') or key == ord('U'):
        delta = 0.01 if key == ord('u') else -0.01
        self.fluidlife_inflow = max(0.0, min(0.2, self.fluidlife_inflow + delta))
        self._flash(f"Inflow: {self.fluidlife_inflow:.3f}")
    elif key == ord('c') or key == ord('C'):
        delta = 1 if key == ord('c') else -1
        self.fluidlife_ca_interval = max(1, min(20, self.fluidlife_ca_interval + delta))
        self._flash(f"CA interval: every {self.fluidlife_ca_interval} steps")
    elif key == ord('+') or key == ord('='):
        self.fluidlife_steps_per_frame = min(10, self.fluidlife_steps_per_frame + 1)
        self._flash(f"LBM steps/frame: {self.fluidlife_steps_per_frame}")
    elif key == ord('-'):
        self.fluidlife_steps_per_frame = max(1, self.fluidlife_steps_per_frame - 1)
        self._flash(f"LBM steps/frame: {self.fluidlife_steps_per_frame}")
    elif key == ord('r'):
        _fluidlife_init(self, self.fluidlife_preset_idx)
    elif key == ord('R') or key == ord('m'):
        self.fluidlife_mode = False
        self.fluidlife_running = False
        self.fluidlife_menu = True
        self.fluidlife_menu_sel = 0
    elif key in (ord('q'), 27):
        _exit_fluidlife_mode(self)
    return True


# ── Drawing ───────────────────────────────────────────────────────────

def _draw_fluidlife_menu(self, max_y: int, max_x: int):
    """Draw preset selection menu."""
    self.stdscr.erase()
    title = "── Fluid of Life ── CA × Fluid Dynamics ── Select Configuration ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Live cells generate buoyancy · Fluid advects cells · Two-way coupling"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc, omega, inflow, buoy, adv) in enumerate(FL_PRESETS):
        y = 4 + i * 3
        if y >= max_y - 3:
            break
        line = f"  {name}"
        params = f"    ω={omega:.2f}  inflow={inflow:.2f}  buoyancy={buoy:.4f}  advection={adv:.2f}"
        detail = f"    {desc}"
        attr = curses.color_pair(6)
        if i == self.fluidlife_menu_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
            self.stdscr.addstr(y + 1, 2, detail[:max_x - 4], curses.color_pair(6) | curses.A_DIM)
            self.stdscr.addstr(y + 2, 2, params[:max_x - 4], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def _draw_fluidlife(self, max_y: int, max_x: int):
    """Draw the active coupled simulation."""
    self.stdscr.erase()
    rows = self.fluidlife_rows
    cols = self.fluidlife_cols
    cells = self.fluidlife_cells
    cell_age = self.fluidlife_age
    objs = self.fluidlife_objects
    viz = self.fluidlife_viz

    state = "▶ RUNNING" if self.fluidlife_running else "⏸ PAUSED"
    pop = _fluidlife_count_population(self)
    tool_name = FL_TOOLS[self.fluidlife_tool][0]
    viscosity = (1.0 / self.fluidlife_omega - 0.5) / 3.0
    viz_names = ["Coupled", "Fluid Speed", "CA Only", "Vorticity"]

    title = (f" Fluid of Life: {self.fluidlife_preset_name}  |  gen {self.fluidlife_generation}"
             f"  |  pop {pop}  |  ν={viscosity:.4f}"
             f"  |  buoy={self.fluidlife_buoyancy:.4f}"
             f"  |  {viz_names[viz]}  |  [{tool_name}]  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Get velocity field for visualization
    ux_field, uy_field = _fluidlife_get_velocity(self)

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    # Compute speed field
    speed = [[0.0] * cols for _ in range(rows)]
    max_speed = 0.001
    for r in range(view_rows):
        for c in range(view_cols):
            s = math.sqrt(ux_field[r][c] ** 2 + uy_field[r][c] ** 2)
            speed[r][c] = s
            if s > max_speed:
                max_speed = s

    # Compute vorticity if needed
    vort = None
    max_vort = 0.001
    if viz == 3:
        vort = [[0.0] * cols for _ in range(rows)]
        for r in range(1, min(view_rows, rows - 1)):
            for c in range(1, min(view_cols, cols - 1)):
                if objs[r][c] == 1:
                    continue
                duy_dx = (uy_field[r][(c + 1) % cols] - uy_field[r][(c - 1) % cols]) * 0.5
                dux_dy = (ux_field[(r + 1) % rows][c] - ux_field[(r - 1) % rows][c]) * 0.5
                curl = duy_dx - dux_dy
                vort[r][c] = curl
                if abs(curl) > max_vort:
                    max_vort = abs(curl)

    # Velocity arrows for overlay
    vel_chars = {
        (1, 0): '→', (-1, 0): '←', (0, -1): '↑', (0, 1): '↓',
        (1, -1): '↗', (-1, -1): '↖', (1, 1): '↘', (-1, 1): '↙',
        (0, 0): '·',
    }

    tc_buf = getattr(self, 'tc_buf', None)
    use_tc = tc_buf is not None and tc_buf.enabled
    cursor_r = self.fluidlife_cursor_r
    cursor_c = self.fluidlife_cursor_c

    for r in range(view_rows):
        for c in range(view_cols):
            sx = c * 2
            sy = 1 + r
            is_cursor = (r == cursor_r and c == cursor_c)

            obj_type = objs[r][c]

            # Object rendering
            if obj_type == 1:  # wall
                ch = "██"
                attr = curses.color_pair(7) | curses.A_DIM
                try:
                    self.stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass
                if is_cursor:
                    try:
                        self.stdscr.addstr(sy, sx, ch, curses.color_pair(7) | curses.A_REVERSE)
                    except curses.error:
                        pass
                continue
            elif obj_type >= 2:
                obj_chars = {2: '→ ', 3: '← ', 4: '↑ ', 5: '↓ ', 6: '♨ ', 7: '❄ '}
                obj_colors = {2: 4, 3: 4, 4: 4, 5: 4, 6: 1, 7: 5}
                ch = obj_chars.get(obj_type, '? ')
                clr = obj_colors.get(obj_type, 6)
                attr = curses.color_pair(clr) | curses.A_BOLD
                try:
                    self.stdscr.addstr(sy, sx, ch, attr)
                except curses.error:
                    pass
                # Still show if cell is alive on top of an object
                if cells[r][c]:
                    try:
                        self.stdscr.addstr(sy, sx, "●", curses.color_pair(2) | curses.A_BOLD)
                    except curses.error:
                        pass
                if is_cursor:
                    try:
                        self.stdscr.addstr(sy, sx, "[]", curses.color_pair(7) | curses.A_REVERSE)
                    except curses.error:
                        pass
                continue

            alive = cells[r][c]
            spd_norm = min(1.0, speed[r][c] / max_speed)

            if viz == 0:  # Coupled view
                if alive:
                    # Color by age
                    a = cell_age[r][c]
                    if a > 20:
                        attr = curses.color_pair(1) | curses.A_BOLD  # red = old
                    elif a > 10:
                        attr = curses.color_pair(3)  # yellow
                    elif a > 3:
                        attr = curses.color_pair(2) | curses.A_BOLD  # green
                    else:
                        attr = curses.color_pair(5) | curses.A_BOLD  # cyan/new
                    ch = "●"
                    if use_tc:
                        norm = min(1.0, a / 25.0)
                        colormap_addstr(self.stdscr, sy, sx, "● ",
                                        'inferno', norm, bold=True, tc_buf=tc_buf)
                    else:
                        try:
                            self.stdscr.addstr(sy, sx, ch + " ", attr)
                        except curses.error:
                            pass
                elif self.fluidlife_show_velocity and spd_norm > 0.05:
                    # Show fluid velocity as background
                    vx = ux_field[r][c]
                    vy = uy_field[r][c]
                    dx = 1 if vx > 0.005 else (-1 if vx < -0.005 else 0)
                    dy = 1 if vy > 0.005 else (-1 if vy < -0.005 else 0)
                    arrow = vel_chars.get((dx, dy), '·')
                    if use_tc:
                        colormap_addstr(self.stdscr, sy, sx, arrow + " ",
                                        'viridis', spd_norm * 0.6, tc_buf=tc_buf)
                    else:
                        if spd_norm > 0.5:
                            attr = curses.color_pair(4)
                        elif spd_norm > 0.2:
                            attr = curses.color_pair(6) | curses.A_DIM
                        else:
                            attr = curses.color_pair(6) | curses.A_DIM
                        try:
                            self.stdscr.addstr(sy, sx, arrow + " ", attr)
                        except curses.error:
                            pass

            elif viz == 1:  # Fluid speed
                if alive:
                    ch = "●"
                    attr = curses.color_pair(2) | curses.A_BOLD
                    try:
                        self.stdscr.addstr(sy, sx, ch + " ", attr)
                    except curses.error:
                        pass
                elif spd_norm > 0.02:
                    lvl = int(spd_norm * 4)
                    lvl = min(4, max(0, lvl))
                    ch = [" ", "░", "▒", "▓", "█"][lvl]
                    if ch != " ":
                        if use_tc:
                            colormap_addstr(self.stdscr, sy, sx, ch + " ",
                                            'inferno', spd_norm, tc_buf=tc_buf)
                        else:
                            if spd_norm > 0.6:
                                attr = curses.color_pair(1) | curses.A_BOLD
                            elif spd_norm > 0.3:
                                attr = curses.color_pair(3)
                            else:
                                attr = curses.color_pair(4) | curses.A_DIM
                            try:
                                self.stdscr.addstr(sy, sx, ch + " ", attr)
                            except curses.error:
                                pass

            elif viz == 2:  # CA only
                if alive:
                    a = cell_age[r][c]
                    if a > 20:
                        attr = curses.color_pair(1) | curses.A_BOLD
                    elif a > 10:
                        attr = curses.color_pair(3)
                    elif a > 3:
                        attr = curses.color_pair(2) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(5) | curses.A_BOLD
                    try:
                        self.stdscr.addstr(sy, sx, "██", attr)
                    except curses.error:
                        pass

            elif viz == 3:  # Vorticity
                if alive:
                    try:
                        self.stdscr.addstr(sy, sx, "● ", curses.color_pair(2) | curses.A_BOLD)
                    except curses.error:
                        pass
                elif vort is not None:
                    v = vort[r][c]
                    vnorm = min(1.0, abs(v) / max_vort)
                    if vnorm > 0.03:
                        lvl = int(vnorm * 4)
                        lvl = min(4, max(0, lvl))
                        if v >= 0:
                            ch = ["·", "∘", "○", "◎", "◉"][lvl]
                            attr = curses.color_pair(1) | (curses.A_BOLD if vnorm > 0.5 else 0)
                        else:
                            ch = ["·", "∙", "•", "●", "⬤"][lvl]
                            attr = curses.color_pair(4) | (curses.A_BOLD if vnorm > 0.5 else 0)
                        if use_tc:
                            colormap_addstr(self.stdscr, sy, sx, ch + " ",
                                            'plasma', vnorm, tc_buf=tc_buf)
                        else:
                            try:
                                self.stdscr.addstr(sy, sx, ch + " ", attr)
                            except curses.error:
                                pass

            # Cursor overlay
            if is_cursor:
                try:
                    self.stdscr.addstr(sy, sx, "[]", curses.color_pair(7) | curses.A_REVERSE)
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        avg_spd = 0.0
        cnt = 0
        for r in range(rows):
            for c in range(cols):
                if objs[r][c] != 1:
                    avg_spd += speed[r][c]
                    cnt += 1
        avg_spd /= max(1, cnt)
        info = (f" Gen {self.fluidlife_generation}  |  grid={rows}×{cols}"
                f"  |  pop={pop}  |  avg flow={avg_spd:.4f}"
                f"  |  CA every {self.fluidlife_ca_interval} steps"
                f"  |  LBM/f={self.fluidlife_steps_per_frame}"
                f"  |  cursor=({cursor_r},{cursor_c})")
        try:
            self.stdscr.addstr(status_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [v]=viz [t]=tool [↑↓←→]=move [Enter]=place [b/B]=buoyancy [r]=reset [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _is_fluidlife_auto_stepping(self) -> bool:
    """Return True if auto-stepping."""
    return self.fluidlife_running


# ── Registration ──────────────────────────────────────────────────────

def register(App):
    """Register Fluid of Life mode methods on the App class."""
    App._enter_fluidlife_mode = _enter_fluidlife_mode
    App._exit_fluidlife_mode = _exit_fluidlife_mode
    App._fluidlife_init = _fluidlife_init
    App._fluidlife_step = _fluidlife_step
    App._handle_fluidlife_menu_key = _handle_fluidlife_menu_key
    App._handle_fluidlife_key = _handle_fluidlife_key
    App._draw_fluidlife_menu = _draw_fluidlife_menu
    App._draw_fluidlife = _draw_fluidlife
    App._is_fluidlife_auto_stepping = _is_fluidlife_auto_stepping
