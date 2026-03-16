"""Mode: cpm — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_cpm_mode(self):
    """Enter Cellular Potts Model mode — show preset menu."""
    self.cpm_menu = True
    self.cpm_menu_sel = 0
    self._flash("Cellular Potts Model — select a simulation")



def _exit_cpm_mode(self):
    """Exit Cellular Potts Model mode."""
    self.cpm_mode = False
    self.cpm_menu = False
    self.cpm_running = False
    self.cpm_grid = []
    self.cpm_chem_field = []
    self._flash("CPM mode OFF")



def _cpm_init(self, preset_idx: int):
    """Initialize CPM simulation with the given preset."""
    import random as _rnd
    name, _desc, preset_id = self.CPM_PRESETS[preset_idx]
    self.cpm_preset_name = name
    self.cpm_generation = 0
    self.cpm_running = False
    self.cpm_viz_mode = 0
    self.cpm_chemotaxis = False
    self.cpm_chem_lambda = 0.0

    max_y, max_x = self.stdscr.getmaxyx()
    self.cpm_rows = max(20, max_y - 3)
    self.cpm_cols = max(20, max_x - 1)
    rows, cols = self.cpm_rows, self.cpm_cols

    self.cpm_grid = [[0] * cols for _ in range(rows)]
    self.cpm_chem_field = [[0.0] * cols for _ in range(rows)]

    if preset_id == "sorting":
        # Two cell types, randomly intermixed — should sort by differential adhesion
        self.cpm_num_types = 2
        # J[i][j] = adhesion energy between type i and type j
        # Lower J = stronger adhesion. Types prefer same-type contact.
        # Medium=0, type1=1, type2=2
        self.cpm_J = [
            [0.0, 16.0, 16.0],   # medium-medium, medium-type1, medium-type2
            [16.0, 2.0, 11.0],    # type1-medium, type1-type1, type1-type2
            [16.0, 11.0, 2.0],    # type2-medium, type2-type1, type2-type2
        ]
        self.cpm_temperature = 10.0
        self.cpm_lambda_area = 2.0
        target_a = 25
        cell_id = 1
        cell_types = []
        target_areas = [0]  # index 0 = medium
        # Place cells in center region
        margin_r = rows // 6
        margin_c = cols // 6
        r0, r1 = margin_r, rows - margin_r
        c0, c1 = margin_c, cols - margin_c
        spacing = int(target_a ** 0.5) + 1
        for rr in range(r0, r1, spacing):
            for cc in range(c0, c1, spacing):
                ctype = 1 if _rnd.random() < 0.5 else 2
                # Fill a small square for this cell
                half = spacing // 2
                for dr in range(-half, half + 1):
                    for dc in range(-half, half + 1):
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            self.cpm_grid[nr][nc] = cell_id
                cell_types.append(ctype)
                target_areas.append(target_a)
                cell_id += 1
        self.cpm_num_cells = cell_id - 1
        self.cpm_cell_type = [0] + cell_types  # index 0 = medium
        self.cpm_target_area = target_areas
        self.cpm_steps_per_frame = 800

    elif preset_id == "wound":
        # Dense cell sheet with a wound (empty region) on one side
        self.cpm_num_types = 1
        self.cpm_J = [
            [0.0, 16.0],
            [16.0, 2.0],
        ]
        self.cpm_temperature = 10.0
        self.cpm_lambda_area = 2.0
        target_a = 30
        cell_id = 1
        cell_types = []
        target_areas = [0]
        spacing = int(target_a ** 0.5) + 1
        wound_col = cols * 2 // 3  # wound starts at 2/3 across
        margin = 2
        for rr in range(margin, rows - margin, spacing):
            for cc in range(margin, wound_col, spacing):
                half = spacing // 2
                for dr in range(-half, half + 1):
                    for dc in range(-half, half + 1):
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            self.cpm_grid[nr][nc] = cell_id
                cell_types.append(1)
                target_areas.append(target_a)
                cell_id += 1
        self.cpm_num_cells = cell_id - 1
        self.cpm_cell_type = [0] + cell_types
        self.cpm_target_area = target_areas
        self.cpm_steps_per_frame = 800

    elif preset_id == "tumor":
        # Small cluster of tumor cells (type 2) surrounded by normal tissue (type 1)
        self.cpm_num_types = 2
        self.cpm_J = [
            [0.0, 16.0, 8.0],
            [16.0, 2.0, 14.0],
            [8.0, 14.0, 6.0],
        ]
        self.cpm_temperature = 12.0
        self.cpm_lambda_area = 1.5
        target_a = 25
        cell_id = 1
        cell_types = []
        target_areas = [0]
        spacing = int(target_a ** 0.5) + 1
        cr, cc_center = rows // 2, cols // 2
        tumor_radius = min(rows, cols) // 8
        margin = 2
        for rr in range(margin, rows - margin, spacing):
            for cc in range(margin, cols - margin, spacing):
                dist = ((rr - cr) ** 2 + (cc - cc_center) ** 2) ** 0.5
                if dist < tumor_radius:
                    ctype = 2  # tumor
                else:
                    ctype = 1  # normal
                half = spacing // 2
                for dr in range(-half, half + 1):
                    for dc in range(-half, half + 1):
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            self.cpm_grid[nr][nc] = cell_id
                cell_types.append(ctype)
                target_areas.append(target_a if ctype == 1 else target_a + 15)
                cell_id += 1
        self.cpm_num_cells = cell_id - 1
        self.cpm_cell_type = [0] + cell_types
        self.cpm_target_area = target_areas
        self.cpm_steps_per_frame = 800

    elif preset_id == "checker":
        # Checkerboard arrangement of two cell types
        self.cpm_num_types = 2
        self.cpm_J = [
            [0.0, 14.0, 14.0],
            [14.0, 4.0, 10.0],
            [14.0, 10.0, 4.0],
        ]
        self.cpm_temperature = 8.0
        self.cpm_lambda_area = 2.0
        target_a = 20
        cell_id = 1
        cell_types = []
        target_areas = [0]
        spacing = int(target_a ** 0.5) + 1
        margin = 2
        row_idx = 0
        for rr in range(margin, rows - margin, spacing):
            col_idx = 0
            for cc in range(margin, cols - margin, spacing):
                ctype = 1 if (row_idx + col_idx) % 2 == 0 else 2
                half = spacing // 2
                for dr in range(-half, half + 1):
                    for dc in range(-half, half + 1):
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            self.cpm_grid[nr][nc] = cell_id
                cell_types.append(ctype)
                target_areas.append(target_a)
                cell_id += 1
                col_idx += 1
            row_idx += 1
        self.cpm_num_cells = cell_id - 1
        self.cpm_cell_type = [0] + cell_types
        self.cpm_target_area = target_areas
        self.cpm_steps_per_frame = 600

    elif preset_id == "foam":
        # Single type, large cells — foam-like coarsening
        self.cpm_num_types = 1
        self.cpm_J = [
            [0.0, 8.0],
            [8.0, 2.0],
        ]
        self.cpm_temperature = 5.0
        self.cpm_lambda_area = 3.0
        target_a = 60
        cell_id = 1
        cell_types = []
        target_areas = [0]
        spacing = int(target_a ** 0.5) + 1
        margin = 1
        for rr in range(margin, rows - margin, spacing):
            for cc in range(margin, cols - margin, spacing):
                half = spacing // 2
                for dr in range(-half, half + 1):
                    for dc in range(-half, half + 1):
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            self.cpm_grid[nr][nc] = cell_id
                cell_types.append(1)
                target_areas.append(target_a)
                cell_id += 1
        self.cpm_num_cells = cell_id - 1
        self.cpm_cell_type = [0] + cell_types
        self.cpm_target_area = target_areas
        self.cpm_steps_per_frame = 1000

    elif preset_id == "chemotaxis":
        # Cells migrate toward chemical source on right side
        self.cpm_num_types = 1
        self.cpm_J = [
            [0.0, 14.0],
            [14.0, 2.0],
        ]
        self.cpm_temperature = 10.0
        self.cpm_lambda_area = 2.0
        self.cpm_chemotaxis = True
        self.cpm_chem_lambda = 200.0
        self.cpm_chem_decay = 0.005
        self.cpm_chem_source_type = 0  # medium-produced (i.e. external source)
        target_a = 30
        cell_id = 1
        cell_types = []
        target_areas = [0]
        spacing = int(target_a ** 0.5) + 1
        margin = 2
        # Place cells on left third
        for rr in range(margin, rows - margin, spacing):
            for cc in range(margin, cols // 3, spacing):
                half = spacing // 2
                for dr in range(-half, half + 1):
                    for dc in range(-half, half + 1):
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            self.cpm_grid[nr][nc] = cell_id
                cell_types.append(1)
                target_areas.append(target_a)
                cell_id += 1
        self.cpm_num_cells = cell_id - 1
        self.cpm_cell_type = [0] + cell_types
        self.cpm_target_area = target_areas
        # Initialize chemical gradient — high on right
        for r in range(rows):
            for c in range(cols):
                self.cpm_chem_field[r][c] = c / max(1, cols - 1)
        self.cpm_steps_per_frame = 500

    # Build area cache
    self.cpm_area_cache = [0] * (self.cpm_num_cells + 1)
    for r in range(rows):
        for c in range(cols):
            cid = self.cpm_grid[r][c]
            if cid > 0:
                self.cpm_area_cache[cid] += 1

    self.cpm_menu = False
    self.cpm_mode = True
    self._flash(f"CPM: {name} — Space to start")



def _cpm_step(self):
    """One Metropolis step of the Cellular Potts Model."""
    import random as _rnd
    import math
    rows, cols = self.cpm_rows, self.cpm_cols
    grid = self.cpm_grid
    J = self.cpm_J
    T = self.cpm_temperature

    # Pick a random pixel
    r = _rnd.randint(0, rows - 1)
    c = _rnd.randint(0, cols - 1)
    current = grid[r][c]

    # Find a random neighbor (4-connected)
    dr, dc = _rnd.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
    nr, nc = r + dr, c + dc
    if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
        self.cpm_generation += 1
        return  # boundary — skip
    neighbor = grid[nr][nc]

    if current == neighbor:
        self.cpm_generation += 1
        return  # same cell — no change possible

    # Propose copying neighbor's ID into (r, c)
    # This means cell 'neighbor' tries to extend into pixel (r, c)
    # and cell 'current' would lose pixel (r, c)

    source = neighbor  # the cell that will gain the pixel
    target = current   # the cell that will lose the pixel

    # Compute contact energy change (delta H_adhesion)
    # Check all 4 neighbors of (r, c) — except the source neighbor itself
    delta_H = 0.0
    type_source = self.cpm_cell_type[source] if source > 0 else 0
    type_target = self.cpm_cell_type[target] if target > 0 else 0

    for dr2, dc2 in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr2, nc2 = r + dr2, c + dc2
        if nr2 < 0 or nr2 >= rows or nc2 < 0 or nc2 >= cols:
            # Boundary acts as medium
            nbr_id = 0
        else:
            nbr_id = grid[nr2][nc2]

        if nbr_id == source and nbr_id == target:
            continue

        type_nbr = self.cpm_cell_type[nbr_id] if nbr_id > 0 else 0

        # Energy after change (pixel becomes source)
        if source != nbr_id:
            delta_H += J[type_source][type_nbr]
        # Energy before change (pixel was target)
        if target != nbr_id:
            delta_H -= J[type_target][type_nbr]

    # Area constraint: H_area = lambda * (area - target_area)^2
    area_cache = self.cpm_area_cache
    if source > 0 and source < len(area_cache):
        area_s = area_cache[source]
        ta_s = self.cpm_target_area[source]
        delta_H += self.cpm_lambda_area * (
            (area_s + 1 - ta_s) ** 2 - (area_s - ta_s) ** 2
        )
    if target > 0 and target < len(area_cache):
        area_t = area_cache[target]
        ta_t = self.cpm_target_area[target]
        delta_H += self.cpm_lambda_area * (
            (area_t - 1 - ta_t) ** 2 - (area_t - ta_t) ** 2
        )

    # Chemotaxis contribution
    if self.cpm_chemotaxis and source > 0:
        delta_H -= self.cpm_chem_lambda * self.cpm_chem_field[r][c]

    # Metropolis acceptance
    accepted = False
    if delta_H <= 0:
        accepted = True
    else:
        prob = math.exp(-delta_H / max(T, 0.01))
        if _rnd.random() < prob:
            accepted = True

    if accepted:
        grid[r][c] = source
        # Update area cache
        if source > 0 and source < len(area_cache):
            area_cache[source] += 1
        if target > 0 and target < len(area_cache):
            area_cache[target] -= 1

    self.cpm_generation += 1



def _cpm_diffuse_chem(self):
    """Diffuse and decay the chemical field (called less frequently)."""
    rows, cols = self.cpm_rows, self.cpm_cols
    old = self.cpm_chem_field
    new = [[0.0] * cols for _ in range(rows)]
    D = 0.1  # diffusion coefficient
    decay = self.cpm_chem_decay
    for r in range(rows):
        for c in range(cols):
            val = old[r][c]
            lap = 0.0
            cnt = 0
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    lap += old[nr][nc]
                    cnt += 1
            lap -= cnt * val
            new[r][c] = val + D * lap - decay * val
            if new[r][c] < 0:
                new[r][c] = 0.0
    # Re-apply source on right edge
    for r in range(rows):
        new[r][cols - 1] = 1.0
    self.cpm_chem_field = new



def _handle_cpm_menu_key(self, key: int) -> bool:
    """Handle keys in the CPM preset menu."""
    if key == -1:
        return True
    n = len(self.CPM_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.cpm_menu_sel = (self.cpm_menu_sel - 1) % n
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.cpm_menu_sel = (self.cpm_menu_sel + 1) % n
        return True
    if key == ord("q") or key == 27:
        self.cpm_menu = False
        self._flash("CPM cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._cpm_init(self.cpm_menu_sel)
        return True
    return True



def _handle_cpm_key(self, key: int) -> bool:
    """Handle keys while in Cellular Potts Model mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_cpm_mode()
        return True
    if key == ord(" "):
        self.cpm_running = not self.cpm_running
        self._flash("Playing" if self.cpm_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        for _ in range(self.cpm_steps_per_frame):
            self._cpm_step()
        if self.cpm_chemotaxis:
            self._cpm_diffuse_chem()
        return True
    if key == ord("v"):
        self.cpm_viz_mode = (self.cpm_viz_mode + 1) % 3
        labels = ["Cell type", "Cell ID", "Boundaries"]
        self._flash(f"Viz: {labels[self.cpm_viz_mode]}")
        return True
    if key == ord("t") or key == ord("+"):
        self.cpm_temperature = min(100.0, self.cpm_temperature + 1.0)
        self._flash(f"Temperature: {self.cpm_temperature:.1f}")
        return True
    if key == ord("T") or key == ord("-"):
        self.cpm_temperature = max(0.5, self.cpm_temperature - 1.0)
        self._flash(f"Temperature: {self.cpm_temperature:.1f}")
        return True
    if key == ord("a"):
        self.cpm_lambda_area = min(20.0, self.cpm_lambda_area + 0.5)
        self._flash(f"λ_area: {self.cpm_lambda_area:.1f}")
        return True
    if key == ord("A"):
        self.cpm_lambda_area = max(0.0, self.cpm_lambda_area - 0.5)
        self._flash(f"λ_area: {self.cpm_lambda_area:.1f}")
        return True
    if key == ord(">"):
        self.cpm_steps_per_frame = min(10000, self.cpm_steps_per_frame * 2)
        self._flash(f"Steps/frame: {self.cpm_steps_per_frame}")
        return True
    if key == ord("<"):
        self.cpm_steps_per_frame = max(50, self.cpm_steps_per_frame // 2)
        self._flash(f"Steps/frame: {self.cpm_steps_per_frame}")
        return True
    if key == ord("r"):
        self._cpm_init(self.cpm_menu_sel)
        self._flash("Reset")
        return True
    if key == ord("R"):
        self.cpm_mode = False
        self.cpm_running = False
        self.cpm_menu = True
        self.cpm_menu_sel = 0
        return True
    return True



def _draw_cpm_menu(self, max_y: int, max_x: int):
    """Draw the CPM preset selection menu."""
    self.stdscr.erase()
    title = "── Cellular Potts Model ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Multicellular tissue dynamics via energy minimization"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n = len(self.CPM_PRESETS)
    for i, (pname, desc, _pid) in enumerate(self.CPM_PRESETS):
        y = 5 + i
        if y >= max_y - 14:
            break
        line = f"  {pname:<22s} {desc}"
        attr = curses.color_pair(6)
        if i == self.cpm_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line[:max_x - 2], attr)
        except curses.error:
            pass

    info_y = 5 + n + 1
    info_lines = [
        "The Cellular Potts Model simulates biological tissue",
        "as multi-pixel cells on a lattice. Cells grow, shrink,",
        "and move via the Metropolis algorithm — each pixel copy",
        "attempt is accepted or rejected based on energy change.",
        "",
        "Energy terms include contact adhesion (J matrix),",
        "area constraints, and optional chemotaxis. Cells",
        "self-organize through differential adhesion — the",
        "same mechanism that drives embryonic cell sorting.",
    ]
    for i, line in enumerate(info_lines):
        y = info_y + i
        if y >= max_y - 3:
            break
        try:
            self.stdscr.addstr(y, max(1, (max_x - len(line)) // 2),
                               line[:max_x - 2], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    footer = "↑/↓ select · Enter confirm · q cancel"
    try:
        self.stdscr.addstr(max_y - 2, max(0, (max_x - len(footer)) // 2), footer,
                           curses.color_pair(7))
    except curses.error:
        pass



def _draw_cpm(self, max_y: int, max_x: int):
    """Draw the Cellular Potts Model simulation."""
    self.stdscr.erase()
    rows = self.cpm_rows
    cols = self.cpm_cols
    grid = self.cpm_grid

    # Color palette for cell types
    type_colors = [
        curses.color_pair(0),                   # medium (dark)
        curses.color_pair(3),                    # type 1 — green
        curses.color_pair(4),                    # type 2 — blue
        curses.color_pair(5),                    # type 3 — magenta
        curses.color_pair(2),                    # type 4 — red
        curses.color_pair(6),                    # type 5 — cyan
        curses.color_pair(1),                    # type 6 — yellow
    ]

    # ID-based color cycling
    id_colors = [
        curses.color_pair(3), curses.color_pair(4), curses.color_pair(5),
        curses.color_pair(2), curses.color_pair(6), curses.color_pair(1),
        curses.color_pair(7),
    ]

    draw_rows = min(rows, max_y - 2)
    draw_cols = min(cols, max_x - 1)

    if self.cpm_viz_mode == 0:
        # Cell type visualization
        for r in range(draw_rows):
            for c in range(draw_cols):
                cid = grid[r][c]
                if cid == 0:
                    # Check if chemotaxis field should be shown
                    if self.cpm_chemotaxis:
                        val = self.cpm_chem_field[r][c]
                        if val > 0.01:
                            idx = min(3, int(val * 4))
                            ramp = " ·:░"
                            try:
                                self.stdscr.addstr(r + 1, c, ramp[idx],
                                                   curses.color_pair(6) | curses.A_DIM)
                            except curses.error:
                                pass
                    continue
                ctype = self.cpm_cell_type[cid] if cid < len(self.cpm_cell_type) else 0
                # Check if boundary pixel
                is_boundary = False
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if grid[nr][nc] != cid:
                            is_boundary = True
                            break
                    else:
                        is_boundary = True
                        break

                color_idx = ctype % len(type_colors)
                color = type_colors[color_idx]
                if is_boundary:
                    ch = "█"
                    color = color | curses.A_BOLD
                else:
                    ch = "▓"
                try:
                    self.stdscr.addstr(r + 1, c, ch, color)
                except curses.error:
                    pass

    elif self.cpm_viz_mode == 1:
        # Cell ID visualization — each cell gets a unique color
        for r in range(draw_rows):
            for c in range(draw_cols):
                cid = grid[r][c]
                if cid == 0:
                    continue
                color = id_colors[cid % len(id_colors)]
                try:
                    self.stdscr.addstr(r + 1, c, "█", color)
                except curses.error:
                    pass

    elif self.cpm_viz_mode == 2:
        # Boundary-only visualization
        for r in range(draw_rows):
            for c in range(draw_cols):
                cid = grid[r][c]
                if cid == 0:
                    continue
                is_boundary = False
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if grid[nr][nc] != cid:
                            is_boundary = True
                            break
                    else:
                        is_boundary = True
                        break
                if is_boundary:
                    ctype = self.cpm_cell_type[cid] if cid < len(self.cpm_cell_type) else 0
                    color = type_colors[ctype % len(type_colors)] | curses.A_BOLD
                    try:
                        self.stdscr.addstr(r + 1, c, "·", color)
                    except curses.error:
                        pass

    # Diffuse chemical field periodically when running
    if self.cpm_running and self.cpm_chemotaxis and self.cpm_generation % 2000 == 0:
        self._cpm_diffuse_chem()

    # Count cells and types for status
    type_counts = {}
    for cid in range(1, self.cpm_num_cells + 1):
        if cid < len(self.cpm_cell_type):
            ct = self.cpm_cell_type[cid]
            type_counts[ct] = type_counts.get(ct, 0) + 1

    viz_labels = ["Type", "ID", "Boundary"]
    status = (f" CPM: {self.cpm_preset_name}"
              f" │ Step: {self.cpm_generation:,}"
              f" │ {'▶' if self.cpm_running else '⏸'}"
              f" │ T={self.cpm_temperature:.1f}"
              f" │ λA={self.cpm_lambda_area:.1f}"
              f" │ Cells: {self.cpm_num_cells}"
              f" │ Viz: {viz_labels[self.cpm_viz_mode]}")
    try:
        self.stdscr.addstr(0, 0, status[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Hint bar
    hint_y = max_y - 1
    now = time.monotonic()
    if self.message and now - self.message_time < 3.0:
        hint = f" {self.message}"
    else:
        hint = " Space=play  n=step  v=viz  t/T=temp  a/A=λ_area  </>=speed  r=reset  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register cpm mode methods on the App class."""
    App._enter_cpm_mode = _enter_cpm_mode
    App._exit_cpm_mode = _exit_cpm_mode
    App._cpm_init = _cpm_init
    App._cpm_step = _cpm_step
    App._cpm_diffuse_chem = _cpm_diffuse_chem
    App._handle_cpm_menu_key = _handle_cpm_menu_key
    App._handle_cpm_key = _handle_cpm_key
    App._draw_cpm_menu = _draw_cpm_menu
    App._draw_cpm = _draw_cpm

