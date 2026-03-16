"""Mode: raymarch — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_raymarch_mode(self):
    """Enter SDF Ray Marching mode — show preset menu."""
    self.raymarch_menu = True
    self.raymarch_menu_sel = 0
    self._flash("SDF Ray Marching — select a scene")



def _exit_raymarch_mode(self):
    """Exit SDF Ray Marching mode."""
    self.raymarch_mode = False
    self.raymarch_menu = False
    self.raymarch_running = False
    self._flash("Ray Marching mode OFF")



def _raymarch_init(self, preset_idx: int):
    """Initialize ray marching with chosen scene preset."""
    name, _desc, scene = self.RAYMARCH_PRESETS[preset_idx]
    self.raymarch_scene_name = name
    self.raymarch_scene = scene
    self.raymarch_generation = 0
    self.raymarch_running = True
    self.raymarch_cam_theta = 0.0
    self.raymarch_cam_phi = 0.4
    self.raymarch_cam_dist = 4.0
    self.raymarch_auto_rotate = True
    self.raymarch_rotate_speed = 0.03
    self.raymarch_light_theta = 0.8
    self.raymarch_light_phi = 0.6
    self.raymarch_shadows = True
    self.raymarch_mandelbulb_power = 8.0
    self.raymarch_menu = False
    self.raymarch_mode = True
    self._flash(f"Ray Marching: {name} — arrows to orbit, space to pause")



def _raymarch_sdf(self, px: float, py: float, pz: float) -> float:
    """Evaluate the signed distance field at point (px, py, pz)."""
    scene = self.raymarch_scene

    if scene == "sphere":
        return math.sqrt(px * px + py * py + pz * pz) - 1.0

    elif scene == "torus":
        # Torus with R=1.0, r=0.4
        qx = math.sqrt(px * px + pz * pz) - 1.0
        return math.sqrt(qx * qx + py * py) - 0.4

    elif scene == "multi":
        # Union of sphere, torus, and box
        d_sphere = math.sqrt((px - 1.5) ** 2 + py * py + pz * pz) - 0.7
        qx = math.sqrt((px + 1.5) ** 2 + pz * pz) - 0.8
        d_torus = math.sqrt(qx * qx + py * py) - 0.3
        # Box centered at (0, 0, 1.5)
        bx, by, bz = abs(px) - 0.6, abs(py) - 0.6, abs(pz - 1.5) - 0.6
        d_box = (max(bx, 0) ** 2 + max(by, 0) ** 2 + max(bz, 0) ** 2) ** 0.5 + min(max(bx, max(by, bz)), 0)
        return min(d_sphere, d_torus, d_box)

    elif scene == "mandelbulb":
        # Mandelbulb fractal SDF
        power = self.raymarch_mandelbulb_power
        zx, zy, zz = px, py, pz
        dr = 1.0
        r = 0.0
        for _ in range(8):
            r = math.sqrt(zx * zx + zy * zy + zz * zz)
            if r > 2.0:
                break
            if r < 1e-21:
                r = 1e-21
            theta = math.acos(max(-1.0, min(1.0, zz / r))) * power
            phi = math.atan2(zy, zx) * power
            zr = r ** power
            dr = r ** (power - 1.0) * power * dr + 1.0
            st = math.sin(theta)
            zx = zr * st * math.cos(phi) + px
            zy = zr * st * math.sin(phi) + py
            zz = zr * math.cos(theta) + pz
        return 0.5 * math.log(max(r, 1e-10)) * r / max(dr, 1e-10)

    elif scene == "infinite":
        # Infinite repeating spheres with period 3
        period = 3.0
        mx = ((px + period * 0.5) % period) - period * 0.5
        my = ((py + period * 0.5) % period) - period * 0.5
        mz = ((pz + period * 0.5) % period) - period * 0.5
        return math.sqrt(mx * mx + my * my + mz * mz) - 0.8

    elif scene == "blend":
        # Smooth union of two spheres
        d1 = math.sqrt((px - 0.8) ** 2 + py * py + pz * pz) - 0.8
        d2 = math.sqrt((px + 0.8) ** 2 + py * py + pz * pz) - 0.8
        k = 0.5
        h = max(0.0, min(1.0, 0.5 + 0.5 * (d2 - d1) / k))
        return d2 * (1 - h) + d1 * h - k * h * (1 - h)

    return 1e10



def _raymarch_normal(self, px: float, py: float, pz: float) -> tuple:
    """Compute surface normal at point via central differences."""
    e = 0.001
    sdf = self._raymarch_sdf
    nx = sdf(px + e, py, pz) - sdf(px - e, py, pz)
    ny = sdf(px, py + e, pz) - sdf(px, py - e, pz)
    nz = sdf(px, py, pz + e) - sdf(px, py, pz - e)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-10:
        return (0.0, 1.0, 0.0)
    return (nx / length, ny / length, nz / length)



def _raymarch_shadow(self, ox: float, oy: float, oz: float,
                     lx: float, ly: float, lz: float) -> float:
    """Soft shadow ray march from surface point toward light."""
    t = 0.05
    res = 1.0
    k = 8.0
    for _ in range(32):
        px = ox + lx * t
        py = oy + ly * t
        pz = oz + lz * t
        d = self._raymarch_sdf(px, py, pz)
        if d < 0.001:
            return 0.0
        res = min(res, k * d / t)
        t += max(d, 0.02)
        if t > 20.0:
            break
    return max(0.0, min(1.0, res))



def _raymarch_step(self):
    """Advance one frame — rotate camera if auto-rotate is on."""
    if self.raymarch_auto_rotate:
        self.raymarch_cam_theta += self.raymarch_rotate_speed
    self.raymarch_generation += 1



def _handle_raymarch_menu_key(self, key: int) -> bool:
    """Handle input in ray marching preset menu."""
    n = len(self.RAYMARCH_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.raymarch_menu_sel = (self.raymarch_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.raymarch_menu_sel = (self.raymarch_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._raymarch_init(self.raymarch_menu_sel)
    elif key in (ord("q"), 27):
        self.raymarch_menu = False
        self._flash("Ray Marching cancelled")
    return True



def _handle_raymarch_key(self, key: int) -> bool:
    """Handle input in active ray marching simulation."""
    orbit_step = 0.1

    if key == ord(" "):
        self.raymarch_running = not self.raymarch_running
    elif key == curses.KEY_LEFT:
        self.raymarch_cam_theta -= orbit_step
    elif key == curses.KEY_RIGHT:
        self.raymarch_cam_theta += orbit_step
    elif key == curses.KEY_UP:
        self.raymarch_cam_phi = min(1.5, self.raymarch_cam_phi + orbit_step)
    elif key == curses.KEY_DOWN:
        self.raymarch_cam_phi = max(-1.5, self.raymarch_cam_phi - orbit_step)
    elif key == ord("a"):
        self.raymarch_auto_rotate = not self.raymarch_auto_rotate
        self._flash(f"Auto-rotate: {'ON' if self.raymarch_auto_rotate else 'OFF'}")
    elif key == ord("+") or key == ord("="):
        self.raymarch_cam_dist = max(1.5, self.raymarch_cam_dist - 0.3)
        self._flash(f"Distance: {self.raymarch_cam_dist:.1f}")
    elif key == ord("-"):
        self.raymarch_cam_dist = min(12.0, self.raymarch_cam_dist + 0.3)
        self._flash(f"Distance: {self.raymarch_cam_dist:.1f}")
    elif key == ord("s"):
        self.raymarch_shadows = not self.raymarch_shadows
        self._flash(f"Shadows: {'ON' if self.raymarch_shadows else 'OFF'}")
    elif key == ord("l"):
        self.raymarch_light_theta += 0.2
        self._flash("Light rotated")
    elif key == ord("L"):
        self.raymarch_light_phi = min(1.5, self.raymarch_light_phi + 0.15)
    elif key == ord("p"):
        if self.raymarch_scene == "mandelbulb":
            self.raymarch_mandelbulb_power = max(2.0, self.raymarch_mandelbulb_power - 0.5)
            self._flash(f"Mandelbulb power: {self.raymarch_mandelbulb_power:.1f}")
    elif key == ord("P"):
        if self.raymarch_scene == "mandelbulb":
            self.raymarch_mandelbulb_power = min(16.0, self.raymarch_mandelbulb_power + 0.5)
            self._flash(f"Mandelbulb power: {self.raymarch_mandelbulb_power:.1f}")
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.RAYMARCH_PRESETS)
                    if p[0] == self.raymarch_scene_name), 0)
        self._raymarch_init(idx)
    elif key in (ord("R"), ord("m")):
        self.raymarch_mode = False
        self.raymarch_running = False
        self.raymarch_menu = True
        self.raymarch_menu_sel = 0
    elif key in (ord("q"), 27):
        self._exit_raymarch_mode()
    else:
        return True
    return True



def _draw_raymarch_menu(self, max_y: int, max_x: int):
    """Draw the ray marching preset selection menu."""
    self.stdscr.erase()
    title = "── SDF Ray Marching ── Select Scene ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Real-time signed distance field 3D rendering with ASCII shading"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc, _scene) in enumerate(self.RAYMARCH_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<20s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.raymarch_menu_sel:
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



def _draw_raymarch(self, max_y: int, max_x: int):
    """Render 3D SDF scene via ray marching with ASCII shading."""
    self.stdscr.erase()

    view_h = max_y - 3
    view_w = max_x - 1
    if view_h < 5 or view_w < 10:
        return

    shade = self.RAYMARCH_SHADE_CHARS
    n_shades = len(shade) - 1

    # Camera position on orbital sphere
    theta = self.raymarch_cam_theta
    phi = self.raymarch_cam_phi
    dist = self.raymarch_cam_dist
    cam_x = dist * math.cos(phi) * math.cos(theta)
    cam_y = dist * math.sin(phi)
    cam_z = dist * math.cos(phi) * math.sin(theta)

    # Camera looks at origin — build view basis vectors
    # Forward = normalize(-cam)
    fwd_len = math.sqrt(cam_x ** 2 + cam_y ** 2 + cam_z ** 2)
    if fwd_len < 1e-6:
        fwd_len = 1.0
    fw_x, fw_y, fw_z = -cam_x / fwd_len, -cam_y / fwd_len, -cam_z / fwd_len

    # Right = normalize(cross(fwd, world_up))
    up_x, up_y, up_z = 0.0, 1.0, 0.0
    rt_x = fw_y * up_z - fw_z * up_y
    rt_y = fw_z * up_x - fw_x * up_z
    rt_z = fw_x * up_y - fw_y * up_x
    rt_len = math.sqrt(rt_x ** 2 + rt_y ** 2 + rt_z ** 2)
    if rt_len < 1e-6:
        up_x, up_y, up_z = 0.0, 0.0, 1.0
        rt_x = fw_y * up_z - fw_z * up_y
        rt_y = fw_z * up_x - fw_x * up_z
        rt_z = fw_x * up_y - fw_y * up_x
        rt_len = math.sqrt(rt_x ** 2 + rt_y ** 2 + rt_z ** 2)
    if rt_len > 1e-6:
        rt_x /= rt_len
        rt_y /= rt_len
        rt_z /= rt_len

    # Up = cross(right, fwd)
    cu_x = rt_y * fw_z - rt_z * fw_y
    cu_y = rt_z * fw_x - rt_x * fw_z
    cu_z = rt_x * fw_y - rt_y * fw_x

    # Light direction
    lt = self.raymarch_light_theta
    lp = self.raymarch_light_phi
    light_x = math.cos(lp) * math.cos(lt)
    light_y = math.sin(lp)
    light_z = math.cos(lp) * math.sin(lt)

    # Aspect ratio correction (terminal chars are ~2:1 height:width)
    aspect = (view_w / view_h) * 0.5
    fov = 1.5

    sdf = self._raymarch_sdf
    do_shadows = self.raymarch_shadows

    # Build the frame buffer
    for row in range(view_h):
        line_chars = []
        line_attrs = []
        # Normalized screen coords
        ndy = (0.5 - row / view_h) * 2.0

        for col in range(view_w):
            ndx = (col / view_w - 0.5) * 2.0 * aspect

            # Ray direction in world space
            rd_x = fw_x * fov + rt_x * ndx + cu_x * ndy
            rd_y = fw_y * fov + rt_y * ndx + cu_y * ndy
            rd_z = fw_z * fov + rt_z * ndx + cu_z * ndy
            rd_len = math.sqrt(rd_x ** 2 + rd_y ** 2 + rd_z ** 2)
            if rd_len > 1e-8:
                rd_x /= rd_len
                rd_y /= rd_len
                rd_z /= rd_len

            # Ray march
            t = 0.0
            hit = False
            for _ in range(64):
                px = cam_x + rd_x * t
                py = cam_y + rd_y * t
                pz = cam_z + rd_z * t
                d = sdf(px, py, pz)
                if d < 0.002:
                    hit = True
                    break
                t += d
                if t > 30.0:
                    break

            if hit:
                # Surface point
                hx = cam_x + rd_x * t
                hy = cam_y + rd_y * t
                hz = cam_z + rd_z * t

                # Normal
                nx, ny, nz = self._raymarch_normal(hx, hy, hz)

                # Diffuse lighting
                diff = max(0.0, nx * light_x + ny * light_y + nz * light_z)

                # Ambient
                ambient = 0.15

                # Shadow
                shadow = 1.0
                if do_shadows and diff > 0.01:
                    shadow = self._raymarch_shadow(
                        hx + nx * 0.02, hy + ny * 0.02, hz + nz * 0.02,
                        light_x, light_y, light_z)

                # Specular (Blinn-Phong)
                hf_x = light_x - rd_x
                hf_y = light_y - rd_y
                hf_z = light_z - rd_z
                hf_len = math.sqrt(hf_x ** 2 + hf_y ** 2 + hf_z ** 2)
                if hf_len > 1e-8:
                    hf_x /= hf_len
                    hf_y /= hf_len
                    hf_z /= hf_len
                spec_dot = max(0.0, nx * hf_x + ny * hf_y + nz * hf_z)
                specular = spec_dot ** 32 * 0.5

                brightness = ambient + (diff * shadow * 0.75) + (specular * shadow)
                brightness = max(0.0, min(1.0, brightness))

                idx = int(brightness * n_shades)
                ch = shade[idx]

                # Color based on normal direction for visual variety
                nr = abs(nx)
                ng = abs(ny)
                nb = abs(nz)
                if ng > nr and ng > nb:
                    attr = curses.color_pair(1)  # green for Y-facing
                elif nr > nb:
                    attr = curses.color_pair(4)  # red/magenta for X-facing
                else:
                    attr = curses.color_pair(2)  # cyan for Z-facing

                if brightness > 0.7:
                    attr |= curses.A_BOLD
                elif brightness < 0.2:
                    attr |= curses.A_DIM

                line_chars.append(ch)
                line_attrs.append(attr)
            else:
                # Background — gradient
                bg_val = 0.3 + 0.3 * ndy
                if bg_val > 0.4:
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
    state = "▶ RENDERING" if self.raymarch_running else "⏸ PAUSED"
    rot_deg = int(math.degrees(self.raymarch_cam_theta)) % 360
    phi_deg = int(math.degrees(self.raymarch_cam_phi))
    hud = (f" {self.raymarch_scene_name}"
           f"  |  {state}"
           f"  |  θ={rot_deg}° φ={phi_deg}°"
           f"  |  Dist: {self.raymarch_cam_dist:.1f}"
           f"  |  Shadows: {'ON' if self.raymarch_shadows else 'OFF'}"
           f"  |  Gen: {self.raymarch_generation}")
    if self.raymarch_scene == "mandelbulb":
        hud += f"  |  Power: {self.raymarch_mandelbulb_power:.1f}"
    try:
        self.stdscr.addstr(0, 0, hud[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    help_text = (" ←→↑↓=orbit  +/-=zoom  a=auto-rotate  s=shadows"
                 "  l/L=light  p/P=power  r=reset  m=menu  q=quit")
    try:
        self.stdscr.addstr(max_y - 1, 0, help_text[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def register(App):
    """Register raymarch mode methods on the App class."""
    App._enter_raymarch_mode = _enter_raymarch_mode
    App._exit_raymarch_mode = _exit_raymarch_mode
    App._raymarch_init = _raymarch_init
    App._raymarch_sdf = _raymarch_sdf
    App._raymarch_normal = _raymarch_normal
    App._raymarch_shadow = _raymarch_shadow
    App._raymarch_step = _raymarch_step
    App._handle_raymarch_menu_key = _handle_raymarch_menu_key
    App._handle_raymarch_key = _handle_raymarch_key
    App._draw_raymarch_menu = _draw_raymarch_menu
    App._draw_raymarch = _draw_raymarch

