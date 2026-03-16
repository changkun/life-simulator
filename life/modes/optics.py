"""Mode: optics — Geometric Optics & Light simulation.

Rays of light propagate through a 2D scene containing mirrors, lenses,
prisms, and diffraction gratings, demonstrating reflection, refraction
(Snell's law), total internal reflection, chromatic dispersion into
spectral colors, caustic focusing, and interference patterns.

Users can interactively place and rotate optical elements.

Emergent phenomena:
  - Total internal reflection at critical angles
  - Chromatic dispersion / rainbow splitting
  - Caustic focusing patterns
  - Interference fringes from gratings
  - Multiple reflections in mirror halls
"""
import curses
import math
import random

# ══════════════════════════════════════════════════════════════════════
#  Presets
# ══════════════════════════════════════════════════════════════════════

OPTICS_PRESETS = [
    ("Rainbow Prism",
     "White light enters a glass prism and disperses into spectral colors",
     "prism"),
    ("Telescope",
     "Two convex lenses form a refracting telescope — parallel rays focus to an eyepiece",
     "telescope"),
    ("Microscope",
     "Objective and eyepiece lenses magnify light from a nearby point source",
     "microscope"),
    ("Fiber Optic Cable",
     "Total internal reflection guides light through a curved waveguide",
     "fiber"),
    ("Hall of Mirrors",
     "Multiple flat mirrors create infinite reflections and interference patterns",
     "mirrors"),
    ("Solar Concentrator",
     "Parabolic mirror focuses parallel sunlight to a single focal point — caustic patterns",
     "solar"),
]

# ══════════════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════════════

# Refractive indices
_N_AIR = 1.0
_N_GLASS = 1.52
_N_FIBER = 1.48

# Spectral colors: (name, wavelength_nm, curses_color_pair, n_offset)
# n_offset is added to base refractive index for dispersion
_SPECTRUM = [
    ("red",    700, 1,  -0.008),
    ("orange", 620, 9,  -0.004),
    ("yellow", 580, 3,   0.000),
    ("green",  530, 2,   0.005),
    ("cyan",   490, 6,   0.010),
    ("blue",   450, 4,   0.016),
    ("violet", 400, 5,   0.024),
]

_WHITE_SPECTRUM = list(range(len(_SPECTRUM)))

_MAX_BOUNCES = 200
_RAY_STEP = 0.3

# Element types
_ELEM_MIRROR = "mirror"
_ELEM_LENS = "lens"
_ELEM_PRISM = "prism"
_ELEM_GRATING = "grating"
_ELEM_BLOCK = "block"  # glass block for refraction

# ══════════════════════════════════════════════════════════════════════
#  Optical element
# ══════════════════════════════════════════════════════════════════════

class _OpticalElement:
    """An optical element in the scene."""
    __slots__ = ("kind", "x", "y", "angle", "length", "n", "focal",
                 "slit_spacing", "verts")

    def __init__(self, kind, x, y, angle=0.0, length=8, n=_N_GLASS,
                 focal=10.0, slit_spacing=2.0):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.angle = float(angle)  # radians
        self.length = length
        self.n = n
        self.focal = focal
        self.slit_spacing = slit_spacing
        self.verts = None  # precomputed vertices for prism

    def endpoints(self):
        """Return (x1,y1,x2,y2) for a line element."""
        dx = math.cos(self.angle) * self.length / 2
        dy = math.sin(self.angle) * self.length / 2
        return (self.x - dx, self.y - dy, self.x + dx, self.y + dy)

    def normal(self):
        """Normal vector (perpendicular to element surface)."""
        return (-math.sin(self.angle), math.cos(self.angle))

    def prism_edges(self):
        """Return 3 edges [(x1,y1,x2,y2), ...] for equilateral prism."""
        if self.verts is None:
            s = self.length
            a = self.angle
            # Equilateral triangle centered at (x, y)
            verts = []
            for i in range(3):
                theta = a + i * 2 * math.pi / 3 - math.pi / 2
                verts.append((self.x + s * math.cos(theta),
                              self.y + s * math.sin(theta)))
            self.verts = verts
        v = self.verts
        return [
            (v[0][0], v[0][1], v[1][0], v[1][1]),
            (v[1][0], v[1][1], v[2][0], v[2][1]),
            (v[2][0], v[2][1], v[0][0], v[0][1]),
        ]


# ══════════════════════════════════════════════════════════════════════
#  Ray tracing helpers
# ══════════════════════════════════════════════════════════════════════

def _seg_intersect(px, py, dx, dy, x1, y1, x2, y2):
    """Find intersection of ray (px,py)+t*(dx,dy) with segment (x1,y1)-(x2,y2).

    Returns (t, u) where t is ray parameter and u is segment parameter [0,1],
    or None if no intersection.
    """
    ex, ey = x2 - x1, y2 - y1
    denom = dx * ey - dy * ex
    if abs(denom) < 1e-12:
        return None
    t = ((x1 - px) * ey - (y1 - py) * ex) / denom
    u = ((x1 - px) * dy - (y1 - py) * dx) / denom
    if t > 0.01 and 0.0 <= u <= 1.0:
        return (t, u)
    return None


def _reflect_vec(dx, dy, nx, ny):
    """Reflect direction (dx,dy) about normal (nx,ny)."""
    dot = dx * nx + dy * ny
    return (dx - 2 * dot * nx, dy - 2 * dot * ny)


def _refract_vec(dx, dy, nx, ny, n1, n2):
    """Refract direction (dx,dy) through surface with normal (nx,ny).

    Returns refracted direction or None for total internal reflection.
    """
    # Ensure normal points against ray direction
    cos_i = -(dx * nx + dy * ny)
    if cos_i < 0:
        nx, ny = -nx, -ny
        cos_i = -cos_i
    ratio = n1 / n2
    sin2_t = ratio * ratio * (1.0 - cos_i * cos_i)
    if sin2_t > 1.0:
        return None  # Total internal reflection
    cos_t = math.sqrt(1.0 - sin2_t)
    rx = ratio * dx + (ratio * cos_i - cos_t) * nx
    ry = ratio * dy + (ratio * cos_i - cos_t) * ny
    mag = math.sqrt(rx * rx + ry * ry)
    if mag > 1e-12:
        rx /= mag
        ry /= mag
    return (rx, ry)


def _trace_single_ray(elements, px, py, dx, dy, n_medium, spectral_idx,
                       max_bounces, rows, cols):
    """Trace a single ray through the scene.

    Returns list of (x, y, color_pair) points along the ray path.
    """
    points = []
    bounces = 0
    cur_n = n_medium
    color = _SPECTRUM[spectral_idx][2]

    while bounces < max_bounces:
        # Find nearest intersection
        best_t = float("inf")
        best_elem = None
        best_edge = None
        best_u = 0.0

        for elem in elements:
            if elem.kind == _ELEM_PRISM:
                for edge in elem.prism_edges():
                    hit = _seg_intersect(px, py, dx, dy, *edge)
                    if hit and hit[0] < best_t:
                        best_t = hit[0]
                        best_elem = elem
                        best_edge = edge
                        best_u = hit[1]
            else:
                ex1, ey1, ex2, ey2 = elem.endpoints()
                hit = _seg_intersect(px, py, dx, dy, ex1, ey1, ex2, ey2)
                if hit and hit[0] < best_t:
                    best_t = hit[0]
                    best_elem = elem
                    best_edge = (ex1, ey1, ex2, ey2)
                    best_u = hit[1]

        # Limit ray length
        max_t = math.sqrt(rows * rows + cols * cols)
        if best_t > max_t:
            best_t = max_t
            best_elem = None

        # Record points along ray segment
        step = _RAY_STEP
        t = 0.0
        while t < best_t:
            rx, ry = px + dx * t, py + dy * t
            if 0 <= rx < cols and 0 <= ry < rows:
                points.append((rx, ry, color))
            elif len(points) > 2:
                break  # Left the scene
            t += step

        if best_elem is None:
            break

        # Move to intersection point
        px = px + dx * best_t
        py = py + dy * best_t
        bounces += 1

        # Compute surface normal at hit point
        ex, ey = best_edge[2] - best_edge[0], best_edge[3] - best_edge[1]
        emag = math.sqrt(ex * ex + ey * ey)
        if emag < 1e-12:
            break
        nx, ny = -ey / emag, ex / emag

        # Handle interaction based on element type
        if best_elem.kind == _ELEM_MIRROR:
            dx, dy = _reflect_vec(dx, dy, nx, ny)

        elif best_elem.kind == _ELEM_LENS:
            # Thin lens: deflect ray toward/away from focal point
            # using lensmaker's equation approximation
            f = best_elem.focal
            # Distance from center of lens along lens axis
            lx, ly = px - best_elem.x, py - best_elem.y
            h = lx * (-math.sin(best_elem.angle)) + ly * math.cos(best_elem.angle)
            # Deflection angle
            theta = -math.atan2(h, f)
            cos_a = math.cos(theta)
            sin_a = math.sin(theta)
            # Apply deflection in normal direction
            ndir = dx * nx + dy * ny
            sign = 1.0 if ndir < 0 else -1.0
            dx = dx + sign * sin_a * nx
            dy = dy + sign * sin_a * ny
            mag = math.sqrt(dx * dx + dy * dy)
            if mag > 1e-12:
                dx /= mag
                dy /= mag

        elif best_elem.kind == _ELEM_PRISM:
            # Refraction with dispersion
            n_glass = best_elem.n + _SPECTRUM[spectral_idx][3]
            # Determine if entering or exiting
            dot_in = dx * nx + dy * ny
            if dot_in < 0:
                # Entering glass
                result = _refract_vec(dx, dy, nx, ny, _N_AIR, n_glass)
                if result is None:
                    dx, dy = _reflect_vec(dx, dy, nx, ny)
                else:
                    dx, dy = result
                    cur_n = n_glass
            else:
                # Exiting glass
                result = _refract_vec(dx, dy, nx, ny, n_glass, _N_AIR)
                if result is None:
                    dx, dy = _reflect_vec(dx, dy, nx, ny)
                else:
                    dx, dy = result
                    cur_n = _N_AIR

        elif best_elem.kind == _ELEM_BLOCK:
            # Glass block: refraction
            n_glass = best_elem.n + _SPECTRUM[spectral_idx][3]
            dot_in = dx * nx + dy * ny
            if dot_in < 0:
                result = _refract_vec(dx, dy, nx, ny, _N_AIR, n_glass)
                if result is None:
                    dx, dy = _reflect_vec(dx, dy, nx, ny)
                else:
                    dx, dy = result
                    cur_n = n_glass
            else:
                result = _refract_vec(dx, dy, nx, ny, n_glass, _N_AIR)
                if result is None:
                    dx, dy = _reflect_vec(dx, dy, nx, ny)
                else:
                    dx, dy = result
                    cur_n = _N_AIR

        elif best_elem.kind == _ELEM_GRATING:
            # Diffraction grating: split into multiple orders
            # For simplicity, deflect based on spectral index
            d = best_elem.slit_spacing
            wavelength = _SPECTRUM[spectral_idx][1] / 1000.0  # arbitrary scale
            # First-order diffraction angle offset
            sin_offset = wavelength / d
            sin_offset = max(-0.8, min(0.8, sin_offset))
            theta = math.asin(sin_offset)
            # Reflect with angle offset
            rdx, rdy = _reflect_vec(dx, dy, nx, ny)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            dx = rdx * cos_t - rdy * sin_t
            dy = rdx * sin_t + rdy * cos_t

        # Nudge past surface
        px += dx * 0.05
        py += dy * 0.05

    return points


def _trace_all_rays(self):
    """Trace all light source rays through the scene."""
    elements = self.optics_elements
    sources = self.optics_sources
    rows = self.optics_rows
    cols = self.optics_cols
    all_points = []

    for src in sources:
        sx, sy, angle, spread, n_rays, spectral = src
        for i in range(n_rays):
            if n_rays == 1:
                a = angle
            else:
                a = angle - spread / 2 + spread * i / (n_rays - 1)
            dx = math.cos(a)
            dy = math.sin(a)

            if spectral:
                # White light: trace each color separately
                for si in _WHITE_SPECTRUM:
                    pts = _trace_single_ray(elements, sx, sy, dx, dy,
                                            _N_AIR, si, _MAX_BOUNCES,
                                            rows, cols)
                    all_points.extend(pts)
            else:
                # Monochromatic (yellow/white)
                pts = _trace_single_ray(elements, sx, sy, dx, dy,
                                        _N_AIR, 3, _MAX_BOUNCES,
                                        rows, cols)
                all_points.extend(pts)

    self.optics_ray_points = all_points

    # Build intensity grid for caustic visualization
    grid = self.optics_intensity
    for r in range(rows):
        for c in range(cols):
            grid[r][c] = 0.0
    for x, y, _ in all_points:
        iy, ix = int(round(y)), int(round(x))
        if 0 <= iy < rows and 0 <= ix < cols:
            grid[iy][ix] += 1.0

    # Build color grid (last color wins, but could blend)
    cgrid = self.optics_color_grid
    for r in range(rows):
        for c in range(cols):
            cgrid[r][c] = -1
    for x, y, color in all_points:
        iy, ix = int(round(y)), int(round(x))
        if 0 <= iy < rows and 0 <= ix < cols:
            cgrid[iy][ix] = color


# ══════════════════════════════════════════════════════════════════════
#  Scene builders for presets
# ══════════════════════════════════════════════════════════════════════

def _build_scene_prism(rows, cols):
    """Rainbow Prism: white light through a prism."""
    cx, cy = cols * 0.5, rows * 0.5
    elements = [
        _OpticalElement(_ELEM_PRISM, cx, cy, angle=0.0,
                        length=min(rows, cols) * 0.2, n=_N_GLASS),
    ]
    # Light source from left
    sources = [(cols * 0.1, cy, 0.0, 0.06, 5, True)]
    return elements, sources


def _build_scene_telescope(rows, cols):
    """Telescope: two convex lenses."""
    cy = rows * 0.5
    f1 = cols * 0.2
    f2 = cols * 0.1
    elements = [
        _OpticalElement(_ELEM_LENS, cols * 0.3, cy, angle=math.pi / 2,
                        length=rows * 0.6, focal=f1),
        _OpticalElement(_ELEM_LENS, cols * 0.7, cy, angle=math.pi / 2,
                        length=rows * 0.4, focal=f2),
    ]
    # Parallel rays from left
    sources = [(2, cy, 0.0, 0.3, 8, False)]
    return elements, sources


def _build_scene_microscope(rows, cols):
    """Microscope: objective + eyepiece with point source."""
    cy = rows * 0.5
    f1 = cols * 0.08
    f2 = cols * 0.15
    elements = [
        _OpticalElement(_ELEM_LENS, cols * 0.25, cy, angle=math.pi / 2,
                        length=rows * 0.5, focal=f1),
        _OpticalElement(_ELEM_LENS, cols * 0.65, cy, angle=math.pi / 2,
                        length=rows * 0.5, focal=f2),
    ]
    # Diverging point source close to objective
    sources = [(cols * 0.12, cy, 0.0, 0.5, 12, False)]
    return elements, sources


def _build_scene_fiber(rows, cols):
    """Fiber Optic Cable: curved waveguide with total internal reflection."""
    elements = []
    # Create two parallel angled mirrors forming a waveguide
    n_seg = 10
    amplitude = rows * 0.2
    for i in range(n_seg):
        t = i / n_seg
        x = cols * (0.15 + 0.7 * t)
        y_center = rows * 0.5 + amplitude * math.sin(2 * math.pi * t)
        tang_angle = math.atan2(
            amplitude * 2 * math.pi * math.cos(2 * math.pi * t) * 0.7 / n_seg,
            cols * 0.7 / n_seg
        )
        gap = rows * 0.08
        seg_len = cols * 0.7 / n_seg * 1.3

        # Top wall
        elements.append(
            _OpticalElement(_ELEM_MIRROR, x, y_center - gap,
                            angle=tang_angle, length=seg_len))
        # Bottom wall
        elements.append(
            _OpticalElement(_ELEM_MIRROR, x, y_center + gap,
                            angle=tang_angle, length=seg_len))

    cy = rows * 0.5
    sources = [(cols * 0.08, cy, 0.0, 0.15, 6, True)]
    return elements, sources


def _build_scene_mirrors(rows, cols):
    """Hall of Mirrors: multiple flat mirrors."""
    elements = []
    cy = rows * 0.5
    cx = cols * 0.5

    # Angled mirrors around the scene
    positions = [
        (cols * 0.15, rows * 0.3, math.pi / 4),
        (cols * 0.85, rows * 0.3, -math.pi / 4),
        (cols * 0.15, rows * 0.7, -math.pi / 4),
        (cols * 0.85, rows * 0.7, math.pi / 4),
        (cx, rows * 0.1, 0.0),
        (cx, rows * 0.9, 0.0),
    ]
    for x, y, a in positions:
        elements.append(
            _OpticalElement(_ELEM_MIRROR, x, y, angle=a,
                            length=min(rows, cols) * 0.2))

    sources = [(cx, cy, 0.0, math.pi * 2, 16, True)]
    return elements, sources


def _build_scene_solar(rows, cols):
    """Solar Concentrator: parabolic mirror focuses parallel rays."""
    elements = []
    cx = cols * 0.6
    cy = rows * 0.5
    focal = cols * 0.25

    # Approximate parabola with mirror segments
    n_seg = 14
    for i in range(n_seg):
        frac = (i - n_seg / 2 + 0.5) / (n_seg / 2)
        y = cy + frac * rows * 0.4
        # Parabola: x = y^2 / (4f) offset
        dy = y - cy
        x = cx + (dy * dy) / (4 * focal)
        # Tangent angle of parabola
        slope = dy / (2 * focal)
        tang_angle = math.atan(slope)
        elements.append(
            _OpticalElement(_ELEM_MIRROR, x, y, angle=tang_angle,
                            length=rows * 0.08))

    # Parallel rays from right
    sources = [(cols * 0.95, cy, math.pi, 0.5, 14, False)]
    return elements, sources


_SCENE_BUILDERS = {
    "prism": _build_scene_prism,
    "telescope": _build_scene_telescope,
    "microscope": _build_scene_microscope,
    "fiber": _build_scene_fiber,
    "mirrors": _build_scene_mirrors,
    "solar": _build_scene_solar,
}


# ══════════════════════════════════════════════════════════════════════
#  Initialization
# ══════════════════════════════════════════════════════════════════════

def _enter_optics_mode(self):
    """Enter Geometric Optics mode — show preset menu."""
    self.optics_menu = True
    self.optics_menu_sel = 0
    self._flash("Geometric Optics & Light — select a scenario")


def _exit_optics_mode(self):
    """Exit Geometric Optics mode."""
    self.optics_mode = False
    self.optics_menu = False
    self.optics_running = False
    self._flash("Optics mode OFF")


def _optics_init(self, preset_idx: int):
    """Initialize optics simulation with the given preset."""
    name, _desc, preset_id = self.OPTICS_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()

    rows = max(8, max_y - 5)
    cols = max(12, max_x - 2)
    self.optics_rows = rows
    self.optics_cols = cols

    self.optics_preset_name = name
    self.optics_preset_id = preset_id
    self.optics_generation = 0
    self.optics_running = False
    self.optics_menu = False
    self.optics_mode = True

    # Scene elements and light sources
    builder = _SCENE_BUILDERS[preset_id]
    elements, sources = builder(rows, cols)
    self.optics_elements = elements
    # sources: list of (x, y, angle, spread, n_rays, is_white)
    self.optics_sources = sources

    # Ray trace results
    self.optics_ray_points = []
    self.optics_intensity = [[0.0] * cols for _ in range(rows)]
    self.optics_color_grid = [[-1] * cols for _ in range(rows)]

    # Interactive state
    self.optics_sel_elem = -1  # selected element index (-1 = none)
    self.optics_cursor_x = cols // 2
    self.optics_cursor_y = rows // 2
    self.optics_show_intensity = False  # toggle caustic heatmap
    self.optics_anim_angle = 0.0  # for animated source rotation

    # Initial trace
    _trace_all_rays(self)


# ══════════════════════════════════════════════════════════════════════
#  Simulation step
# ══════════════════════════════════════════════════════════════════════

def _optics_step(self):
    """Advance one animation step — rotate source or animate elements."""
    self.optics_anim_angle += 0.03
    # Gently rotate first source direction for visual effect
    if self.optics_sources:
        src = self.optics_sources[0]
        base_angle = src[2]
        wobble = 0.15 * math.sin(self.optics_anim_angle)
        self.optics_sources[0] = (src[0], src[1], base_angle + wobble,
                                   src[3], src[4], src[5])
    _trace_all_rays(self)
    self.optics_generation += 1


# ══════════════════════════════════════════════════════════════════════
#  Key handling
# ══════════════════════════════════════════════════════════════════════

def _handle_optics_menu_key(self, key: int) -> bool:
    """Handle input in Optics preset menu."""
    presets = self.OPTICS_PRESETS
    if key == curses.KEY_DOWN or key == ord("j"):
        self.optics_menu_sel = (self.optics_menu_sel + 1) % len(presets)
    elif key == curses.KEY_UP or key == ord("k"):
        self.optics_menu_sel = (self.optics_menu_sel - 1) % len(presets)
    elif key in (10, 13, curses.KEY_ENTER):
        self._optics_init(self.optics_menu_sel)
    elif key == ord("q") or key == 27:
        self.optics_menu = False
        self._flash("Optics mode cancelled")
    return True


def _handle_optics_key(self, key: int) -> bool:
    """Handle input in active Optics simulation."""
    if key == ord("q") or key == 27:
        self._exit_optics_mode()
        return True
    if key == ord(" "):
        self.optics_running = not self.optics_running
        return True
    if key == ord("n") or key == ord("."):
        self._optics_step()
        return True
    if key == ord("r"):
        idx = next(
            (i for i, p in enumerate(self.OPTICS_PRESETS)
             if p[0] == self.optics_preset_name), 0)
        self._optics_init(idx)
        return True
    if key == ord("R") or key == ord("m"):
        self.optics_mode = False
        self.optics_running = False
        self.optics_menu = True
        self.optics_menu_sel = 0
        return True

    # Toggle caustic heatmap
    if key == ord("h"):
        self.optics_show_intensity = not self.optics_show_intensity
        _trace_all_rays(self)
        self._flash("Intensity heatmap " +
                     ("ON" if self.optics_show_intensity else "OFF"))
        return True

    # Element selection and manipulation
    if key == ord("\t") or key == ord("e"):
        # Cycle through elements
        n = len(self.optics_elements)
        if n > 0:
            self.optics_sel_elem = (self.optics_sel_elem + 1) % n
            e = self.optics_elements[self.optics_sel_elem]
            self._flash(f"Selected: {e.kind} #{self.optics_sel_elem}")
        return True

    # Rotate selected element
    if key == ord("[") and self.optics_sel_elem >= 0:
        e = self.optics_elements[self.optics_sel_elem]
        e.angle -= 0.1
        e.verts = None
        _trace_all_rays(self)
        return True
    if key == ord("]") and self.optics_sel_elem >= 0:
        e = self.optics_elements[self.optics_sel_elem]
        e.angle += 0.1
        e.verts = None
        _trace_all_rays(self)
        return True

    # Move selected element
    elems = self.optics_elements
    if self.optics_sel_elem >= 0 and self.optics_sel_elem < len(elems):
        e = elems[self.optics_sel_elem]
        moved = False
        if key == curses.KEY_LEFT or key == ord("a"):
            e.x -= 1.0
            moved = True
        elif key == curses.KEY_RIGHT or key == ord("d"):
            e.x += 1.0
            moved = True
        elif key == curses.KEY_UP or key == ord("w"):
            e.y -= 1.0
            moved = True
        elif key == curses.KEY_DOWN or key == ord("s"):
            e.y += 1.0
            moved = True
        if moved:
            e.verts = None
            _trace_all_rays(self)
            return True

    # Adjust focal length of selected lens
    if key == ord("f") and self.optics_sel_elem >= 0:
        e = self.optics_elements[self.optics_sel_elem]
        if e.kind == _ELEM_LENS:
            e.focal = max(2.0, e.focal - 2.0)
            _trace_all_rays(self)
            self._flash(f"Focal length: {e.focal:.1f}")
        return True
    if key == ord("F") and self.optics_sel_elem >= 0:
        e = self.optics_elements[self.optics_sel_elem]
        if e.kind == _ELEM_LENS:
            e.focal += 2.0
            _trace_all_rays(self)
            self._flash(f"Focal length: {e.focal:.1f}")
        return True

    return True


# ══════════════════════════════════════════════════════════════════════
#  Drawing
# ══════════════════════════════════════════════════════════════════════

def _draw_optics_menu(self, max_y: int, max_x: int):
    """Draw the Optics preset selection menu."""
    self.stdscr.erase()
    title = "── Geometric Optics & Light ── Select Scenario ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    for i, (name, desc, _pid) in enumerate(self.OPTICS_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 6:
            break
        marker = "▸ " if i == self.optics_menu_sel else "  "
        attr = (curses.color_pair(3) | curses.A_BOLD
                if i == self.optics_menu_sel else curses.color_pair(7))
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(y, 3, line[:max_x - 4], attr)
        except curses.error:
            pass
        try:
            self.stdscr.addstr(y + 1, 6, desc[:max_x - 8],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Legend
    legend_y = max_y - 5
    if legend_y > 0:
        lines = [
            "Geometric Optics: rays of light interact with mirrors, lenses, and prisms.",
            "Observe reflection, refraction (Snell's law), dispersion, and caustic focusing.",
            "Place and rotate optical elements to explore total internal reflection and more.",
        ]
        for i, line in enumerate(lines):
            try:
                self.stdscr.addstr(legend_y + i, 3, line[:max_x - 4],
                                   curses.color_pair(6))
            except curses.error:
                pass

    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate  [Enter]=select  [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_optics(self, max_y: int, max_x: int):
    """Draw the active Optics simulation."""
    self.stdscr.erase()
    state = "▶ RUNNING" if self.optics_running else "⏸ PAUSED"

    n_rays = len(self.optics_ray_points)
    n_elem = len(self.optics_elements)
    sel = self.optics_sel_elem

    title = (f" Optics: {self.optics_preset_name}  |  "
             f"rays={n_rays}  elements={n_elem}  "
             f"step={self.optics_generation}  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Draw the scene
    _draw_optics_field(self, max_y, max_x)

    # Info bar
    info_y = max_y - 2
    if info_y > 1:
        info = f" elements={n_elem}"
        if sel >= 0 and sel < n_elem:
            e = self.optics_elements[sel]
            info += (f"  selected: {e.kind} #{sel}"
                     f"  pos=({e.x:.0f},{e.y:.0f})"
                     f"  angle={math.degrees(e.angle):.0f}°")
            if e.kind == _ELEM_LENS:
                info += f"  f={e.focal:.1f}"
        if self.optics_show_intensity:
            info += "  [heatmap ON]"
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    import time as _time
    hint_y = max_y - 1
    if hint_y > 0:
        now = _time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = (" [Space]=play [n]=step [e]=select [wasd/←→]=move"
                    " [\\[\\]]=rotate [f/F]=focal [h]=heatmap [r]=reset"
                    " [R]=menu [q]=exit")
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def _draw_optics_field(self, max_y: int, max_x: int):
    """Draw the optics scene: elements, rays, and intensity."""
    rows = self.optics_rows
    cols = self.optics_cols
    intensity = self.optics_intensity
    color_grid = self.optics_color_grid
    elements = self.optics_elements
    show_heat = self.optics_show_intensity
    sel = self.optics_sel_elem

    disp_rows = max_y - 4
    disp_cols = max_x - 1
    row_scale = max(1, (rows + disp_rows - 1) // disp_rows)
    col_scale = max(1, (cols + disp_cols - 1) // disp_cols)

    # Pre-rasterize element positions for drawing
    elem_cells = {}  # (r, c) -> (char, color_pair)
    for ei, elem in enumerate(elements):
        is_sel = (ei == sel)
        if elem.kind == _ELEM_PRISM:
            edges = elem.prism_edges()
            for edge in edges:
                _rasterize_seg(edge[0], edge[1], edge[2], edge[3],
                               elem_cells, "△" if is_sel else "▲", 5 if is_sel else 7,
                               rows, cols)
        else:
            ex1, ey1, ex2, ey2 = elem.endpoints()
            if elem.kind == _ELEM_MIRROR:
                ch = "║" if is_sel else "│"
                cp = 7
            elif elem.kind == _ELEM_LENS:
                ch = "◯" if is_sel else "○"
                cp = 6
            elif elem.kind == _ELEM_GRATING:
                ch = "┊"
                cp = 5
            else:
                ch = "█"
                cp = 7
            if is_sel:
                cp = 3
            _rasterize_seg(ex1, ey1, ex2, ey2, elem_cells, ch, cp,
                           rows, cols)

    # Draw grid
    for sy in range(min(disp_rows, rows)):
        r = sy * row_scale
        if r >= rows:
            break
        screen_y = 1 + sy
        if screen_y >= max_y - 2:
            break
        for sx in range(min(disp_cols, cols)):
            c = sx * col_scale
            if c >= cols:
                break

            # Priority: element > ray > empty
            if (r, c) in elem_cells:
                ch, cp = elem_cells[(r, c)]
                try:
                    self.stdscr.addstr(screen_y, sx, ch,
                                       curses.color_pair(cp) | curses.A_BOLD)
                except curses.error:
                    pass
                continue

            inten = intensity[r][c]
            cg = color_grid[r][c]

            if inten > 0:
                if show_heat:
                    # Caustic heatmap
                    if inten > 8:
                        ch = "█"
                        cp = 1
                    elif inten > 4:
                        ch = "▓"
                        cp = 3
                    elif inten > 2:
                        ch = "▒"
                        cp = 3
                    elif inten > 1:
                        ch = "░"
                        cp = 7
                    else:
                        ch = "·"
                        cp = 7
                else:
                    # Colored ray display
                    if inten > 4:
                        ch = "█"
                    elif inten > 2:
                        ch = "▓"
                    elif inten > 1:
                        ch = "▒"
                    else:
                        ch = "·"
                    cp = cg if cg >= 0 else 7

                attr = curses.color_pair(cp)
                if inten > 6:
                    attr |= curses.A_BOLD
                try:
                    self.stdscr.addstr(screen_y, sx, ch, attr)
                except curses.error:
                    pass
            else:
                try:
                    self.stdscr.addstr(screen_y, sx, " ")
                except curses.error:
                    pass


def _rasterize_seg(x1, y1, x2, y2, cells, ch, cp, rows, cols):
    """Bresenham-ish rasterization of a line segment into grid cells."""
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 0.5:
        r, c = int(round(y1)), int(round(x1))
        if 0 <= r < rows and 0 <= c < cols:
            cells[(r, c)] = (ch, cp)
        return
    steps = int(dist * 2) + 1
    for i in range(steps + 1):
        t = i / steps
        x = x1 + dx * t
        y = y1 + dy * t
        r, c = int(round(y)), int(round(x))
        if 0 <= r < rows and 0 <= c < cols:
            cells[(r, c)] = (ch, cp)


# ══════════════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════════════

def register(App):
    """Register geometric optics mode methods on the App class."""
    App.OPTICS_PRESETS = OPTICS_PRESETS
    App._enter_optics_mode = _enter_optics_mode
    App._exit_optics_mode = _exit_optics_mode
    App._optics_init = _optics_init
    App._optics_step = _optics_step
    App._handle_optics_menu_key = _handle_optics_menu_key
    App._handle_optics_key = _handle_optics_key
    App._draw_optics_menu = _draw_optics_menu
    App._draw_optics = _draw_optics
    App._draw_optics_field = _draw_optics_field
