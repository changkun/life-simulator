"""Mode: gol3d — simulation mode for the life package."""
import curses
import math
import random
import time


from life.grid import Grid

def _enter_gol3d_mode(self):
    """Enter 3D Game of Life mode — show preset menu."""
    self.gol3d_menu = True
    self.gol3d_menu_sel = 0
    self._flash("3D Game of Life — select a ruleset")



def _exit_gol3d_mode(self):
    """Exit 3D Game of Life mode."""
    self.gol3d_mode = False
    self.gol3d_menu = False
    self.gol3d_running = False
    self._flash("3D Game of Life OFF")



def _gol3d_init(self, preset_idx: int):
    """Initialize 3D Game of Life with chosen preset."""
    name, _desc, birth, survive, density = self.GOL3D_PRESETS[preset_idx]
    self.gol3d_preset_name = name
    self.gol3d_birth = birth
    self.gol3d_survive = survive
    self.gol3d_density = density
    self.gol3d_generation = 0
    self.gol3d_running = True
    self.gol3d_cam_theta = 0.5
    self.gol3d_cam_phi = 0.5
    self.gol3d_cam_dist = 2.5
    self.gol3d_auto_rotate = True
    self.gol3d_rotate_speed = 0.02

    # Initialize 3D grid with random seed
    import random as _rng
    sz = self.gol3d_size
    grid = []
    pop = 0
    for x in range(sz):
        plane = []
        for y in range(sz):
            row = []
            for z in range(sz):
                # Seed more densely near center
                dx = x - sz / 2
                dy = y - sz / 2
                dz = z - sz / 2
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                if dist < sz * 0.4 and _rng.random() < density:
                    row.append(1)
                    pop += 1
                else:
                    row.append(0)
            plane.append(row)
        grid.append(plane)
    self.gol3d_grid = grid
    self.gol3d_population = pop

    self.gol3d_menu = False
    self.gol3d_mode = True
    self._flash(f"3D GoL: {name} — arrows to orbit, space to pause")



def _gol3d_step(self):
    """Advance one generation of 3D cellular automaton."""
    sz = self.gol3d_size
    grid = self.gol3d_grid
    birth = self.gol3d_birth
    survive = self.gol3d_survive

    new_grid = []
    pop = 0
    for x in range(sz):
        plane = []
        for y in range(sz):
            row = []
            for z in range(sz):
                # Count 26 neighbors (Moore neighborhood)
                count = 0
                for dx in (-1, 0, 1):
                    nx = x + dx
                    if nx < 0 or nx >= sz:
                        continue
                    for dy in (-1, 0, 1):
                        ny = y + dy
                        if ny < 0 or ny >= sz:
                            continue
                        for dz in (-1, 0, 1):
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                            nz = z + dz
                            if nz < 0 or nz >= sz:
                                continue
                            count += grid[nx][ny][nz]

                alive = grid[x][y][z]
                if alive:
                    val = 1 if count in survive else 0
                else:
                    val = 1 if count in birth else 0
                row.append(val)
                pop += val
            plane.append(row)
        new_grid.append(plane)

    self.gol3d_grid = new_grid
    self.gol3d_population = pop
    self.gol3d_generation += 1

    # Auto-rotate camera
    if self.gol3d_auto_rotate:
        self.gol3d_cam_theta += self.gol3d_rotate_speed



def _handle_gol3d_menu_key(self, key: int) -> bool:
    """Handle input in 3D GoL preset menu."""
    n = len(self.GOL3D_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.gol3d_menu_sel = (self.gol3d_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.gol3d_menu_sel = (self.gol3d_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._gol3d_init(self.gol3d_menu_sel)
    elif key in (ord("q"), 27):
        self.gol3d_menu = False
        self._flash("3D Game of Life cancelled")
    return True



def _handle_gol3d_key(self, key: int) -> bool:
    """Handle input in active 3D GoL simulation."""
    orbit_step = 0.1

    if key == ord(" "):
        self.gol3d_running = not self.gol3d_running
    elif key == curses.KEY_LEFT:
        self.gol3d_cam_theta -= orbit_step
    elif key == curses.KEY_RIGHT:
        self.gol3d_cam_theta += orbit_step
    elif key == curses.KEY_UP:
        self.gol3d_cam_phi = min(1.5, self.gol3d_cam_phi + orbit_step)
    elif key == curses.KEY_DOWN:
        self.gol3d_cam_phi = max(-1.5, self.gol3d_cam_phi - orbit_step)
    elif key == ord("a"):
        self.gol3d_auto_rotate = not self.gol3d_auto_rotate
        self._flash(f"Auto-rotate: {'ON' if self.gol3d_auto_rotate else 'OFF'}")
    elif key == ord("+") or key == ord("="):
        self.gol3d_cam_dist = max(1.2, self.gol3d_cam_dist - 0.2)
        self._flash(f"Zoom: {self.gol3d_cam_dist:.1f}")
    elif key == ord("-"):
        self.gol3d_cam_dist = min(5.0, self.gol3d_cam_dist + 0.2)
        self._flash(f"Zoom: {self.gol3d_cam_dist:.1f}")
    elif key == ord("n"):
        # Single step
        self._gol3d_step()
    elif key == ord("r"):
        # Reset with same preset
        idx = next((i for i, p in enumerate(self.GOL3D_PRESETS)
                    if p[0] == self.gol3d_preset_name), 0)
        self._gol3d_init(idx)
    elif key in (ord("R"), ord("m")):
        self.gol3d_mode = False
        self.gol3d_running = False
        self.gol3d_menu = True
        self.gol3d_menu_sel = 0
    elif key in (ord("q"), 27):
        self._exit_gol3d_mode()
    else:
        return True
    return True



def _draw_gol3d_menu(self, max_y: int, max_x: int):
    """Draw the 3D GoL preset selection menu."""
    self.stdscr.erase()
    title = "── 3D Game of Life ── Select Ruleset ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Volumetric 3D cellular automaton with ASCII ray casting"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc, _b, _s, _d) in enumerate(self.GOL3D_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<26s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.gol3d_menu_sel:
            attr = curses.color_pair(3) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_gol3d(self, max_y: int, max_x: int):
    """Render 3D Game of Life via volumetric ASCII ray casting."""
    self.stdscr.erase()

    view_h = max_y - 3
    view_w = max_x - 1
    if view_h < 5 or view_w < 10:
        return

    shade = self.GOL3D_SHADE_CHARS
    n_shades = len(shade) - 1
    sz = self.gol3d_size
    grid = self.gol3d_grid
    half = sz / 2.0

    # Camera position on orbital sphere
    theta = self.gol3d_cam_theta
    phi = self.gol3d_cam_phi
    dist = self.gol3d_cam_dist * sz
    cam_x = dist * math.cos(phi) * math.cos(theta) + half
    cam_y = dist * math.sin(phi) + half
    cam_z = dist * math.cos(phi) * math.sin(theta) + half

    # Camera looks at center of grid
    fx = half - cam_x
    fy = half - cam_y
    fz = half - cam_z
    fwd_len = math.sqrt(fx * fx + fy * fy + fz * fz)
    if fwd_len < 1e-6:
        fwd_len = 1.0
    fw_x, fw_y, fw_z = fx / fwd_len, fy / fwd_len, fz / fwd_len

    # Right = cross(fwd, world_up)
    up_x, up_y, up_z = 0.0, 1.0, 0.0
    rt_x = fw_y * up_z - fw_z * up_y
    rt_y = fw_z * up_x - fw_x * up_z
    rt_z = fw_x * up_y - fw_y * up_x
    rt_len = math.sqrt(rt_x * rt_x + rt_y * rt_y + rt_z * rt_z)
    if rt_len < 1e-6:
        up_x, up_y, up_z = 0.0, 0.0, 1.0
        rt_x = fw_y * up_z - fw_z * up_y
        rt_y = fw_z * up_x - fw_x * up_z
        rt_z = fw_x * up_y - fw_y * up_x
        rt_len = math.sqrt(rt_x * rt_x + rt_y * rt_y + rt_z * rt_z)
    if rt_len > 1e-6:
        rt_x /= rt_len; rt_y /= rt_len; rt_z /= rt_len

    # Up = cross(right, fwd)
    cu_x = rt_y * fw_z - rt_z * fw_y
    cu_y = rt_z * fw_x - rt_x * fw_z
    cu_z = rt_x * fw_y - rt_y * fw_x

    # Light direction (fixed from top-right)
    light_x, light_y, light_z = 0.5, 0.8, 0.3
    ll = math.sqrt(light_x * light_x + light_y * light_y + light_z * light_z)
    light_x /= ll; light_y /= ll; light_z /= ll

    aspect = (view_w / view_h) * 0.5
    fov = 1.0

    # Step size for ray marching through voxel grid
    step_size = 0.7
    max_steps = int(sz * 4)
    max_t = sz * 3.5

    # Build the frame buffer row by row
    for row in range(view_h):
        line_chars = []
        line_attrs = []
        ndy = (0.5 - row / view_h) * 2.0

        for col in range(view_w):
            ndx = (col / view_w - 0.5) * 2.0 * aspect

            # Ray direction
            rd_x = fw_x * fov + rt_x * ndx + cu_x * ndy
            rd_y = fw_y * fov + rt_y * ndx + cu_y * ndy
            rd_z = fw_z * fov + rt_z * ndx + cu_z * ndy
            rd_len = math.sqrt(rd_x * rd_x + rd_y * rd_y + rd_z * rd_z)
            if rd_len > 1e-8:
                rd_x /= rd_len; rd_y /= rd_len; rd_z /= rd_len

            # Find entry point into bounding box [0, sz)^3
            # Using slab method
            t_min = 0.0
            t_max = max_t
            hit_box = True
            for axis in range(3):
                if axis == 0:
                    o, d = cam_x, rd_x
                elif axis == 1:
                    o, d = cam_y, rd_y
                else:
                    o, d = cam_z, rd_z
                if abs(d) < 1e-10:
                    if o < -0.5 or o > sz + 0.5:
                        hit_box = False
                        break
                else:
                    t1 = (-0.5 - o) / d
                    t2 = (sz + 0.5 - o) / d
                    if t1 > t2:
                        t1, t2 = t2, t1
                    t_min = max(t_min, t1)
                    t_max = min(t_max, t2)
                    if t_min > t_max:
                        hit_box = False
                        break

            if not hit_box:
                # Background
                bg = 0.3 + 0.25 * ndy
                if bg > 0.38:
                    line_chars.append("·")
                    line_attrs.append(curses.color_pair(6) | curses.A_DIM)
                else:
                    line_chars.append(" ")
                    line_attrs.append(curses.color_pair(0))
                continue

            # March through the voxel grid
            t = max(t_min, 0.1)
            hit = False
            hit_x = hit_y = hit_z = 0
            hit_t = 0.0
            density_accum = 0.0

            for _ in range(max_steps):
                px = cam_x + rd_x * t
                py = cam_y + rd_y * t
                pz = cam_z + rd_z * t

                gx = int(px)
                gy = int(py)
                gz = int(pz)

                if 0 <= gx < sz and 0 <= gy < sz and 0 <= gz < sz:
                    if grid[gx][gy][gz]:
                        hit = True
                        hit_x, hit_y, hit_z = gx, gy, gz
                        hit_t = t
                        break
                elif t > t_max:
                    break

                t += step_size

            if hit:
                # Compute surface normal from neighboring voxels
                nx_val = 0.0
                ny_val = 0.0
                nz_val = 0.0
                for d in (-1, 1):
                    ax = hit_x + d
                    if 0 <= ax < sz:
                        nx_val -= d * grid[ax][hit_y][hit_z]
                    else:
                        nx_val -= d  # boundary acts as empty
                    ay = hit_y + d
                    if 0 <= ay < sz:
                        ny_val -= d * grid[hit_x][ay][hit_z]
                    else:
                        ny_val -= d
                    az = hit_z + d
                    if 0 <= az < sz:
                        nz_val -= d * grid[hit_x][hit_y][az]
                    else:
                        nz_val -= d

                # Fallback: use entry direction as normal
                n_len = math.sqrt(nx_val * nx_val + ny_val * ny_val + nz_val * nz_val)
                if n_len < 1e-6:
                    # Use ray direction flipped as normal
                    nx_val, ny_val, nz_val = -rd_x, -rd_y, -rd_z
                    n_len = 1.0
                else:
                    nx_val /= n_len; ny_val /= n_len; nz_val /= n_len

                # Diffuse lighting
                diff = max(0.0, nx_val * light_x + ny_val * light_y + nz_val * light_z)

                # Depth fog
                depth_frac = hit_t / max_t
                fog = max(0.0, 1.0 - depth_frac * 1.5)

                # Ambient occlusion approximation — count neighbors
                ao_count = 0
                for dx in (-1, 0, 1):
                    ax = hit_x + dx
                    if ax < 0 or ax >= sz:
                        continue
                    for dy in (-1, 0, 1):
                        ay = hit_y + dy
                        if ay < 0 or ay >= sz:
                            continue
                        for dz in (-1, 0, 1):
                            if dx == 0 and dy == 0 and dz == 0:
                                continue
                            az = hit_z + dz
                            if 0 <= az < sz:
                                ao_count += grid[ax][ay][az]
                ao = 1.0 - ao_count / 26.0 * 0.5

                brightness = (0.15 + diff * 0.65) * fog * ao
                brightness = max(0.0, min(1.0, brightness))

                idx = int(brightness * n_shades)
                ch = shade[idx]

                # Color based on voxel position for variety
                cx = hit_x / sz
                cy = hit_y / sz
                cz = hit_z / sz
                if cy > cx and cy > cz:
                    attr = curses.color_pair(1)  # green for top
                elif cx > cz:
                    attr = curses.color_pair(4)  # magenta for x-axis
                else:
                    attr = curses.color_pair(2)  # cyan for z-axis

                if brightness > 0.6:
                    attr |= curses.A_BOLD
                elif brightness < 0.2:
                    attr |= curses.A_DIM

                line_chars.append(ch)
                line_attrs.append(attr)
            else:
                # Background
                bg = 0.3 + 0.25 * ndy
                if bg > 0.38:
                    line_chars.append("·")
                    line_attrs.append(curses.color_pair(6) | curses.A_DIM)
                else:
                    line_chars.append(" ")
                    line_attrs.append(curses.color_pair(0))

        # Write line to screen
        for col_i, (ch, attr) in enumerate(zip(line_chars, line_attrs)):
            try:
                self.stdscr.addstr(1 + row, col_i, ch, attr)
            except curses.error:
                pass

    # HUD
    state = "▶ RUNNING" if self.gol3d_running else "⏸ PAUSED"
    rot_deg = int(math.degrees(self.gol3d_cam_theta)) % 360
    phi_deg = int(math.degrees(self.gol3d_cam_phi))
    hud = (f" {self.gol3d_preset_name}"
           f"  |  {state}"
           f"  |  θ={rot_deg}° φ={phi_deg}°"
           f"  |  Pop: {self.gol3d_population}"
           f"  |  Gen: {self.gol3d_generation}"
           f"  |  Grid: {self.gol3d_size}³")
    try:
        self.stdscr.addstr(0, 0, hud[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    help_text = (" ←→↑↓=orbit  +/-=zoom  a=auto-rotate"
                 "  n=step  r=reset  m=menu  space=pause  q=quit")
    try:
        self.stdscr.addstr(max_y - 1, 0, help_text[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register gol3d mode methods on the App class."""
    App._enter_gol3d_mode = _enter_gol3d_mode
    App._exit_gol3d_mode = _exit_gol3d_mode
    App._gol3d_init = _gol3d_init
    App._gol3d_step = _gol3d_step
    App._handle_gol3d_menu_key = _handle_gol3d_menu_key
    App._handle_gol3d_key = _handle_gol3d_key
    App._draw_gol3d_menu = _draw_gol3d_menu
    App._draw_gol3d = _draw_gol3d

