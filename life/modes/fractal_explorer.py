"""Mode: fractal — simulation mode for the life package."""
import curses
import math
import random
import time


def _fractal_init(self, preset: str):
    """Initialize fractal exploration for a given preset."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.fractal_rows = max(10, max_y - 3)
    self.fractal_cols = max(20, max_x - 1)
    self.fractal_generation = 0
    self.fractal_dirty = True
    self.fractal_smooth = True
    self.fractal_color_scheme = 0

    if preset == "mandelbrot_classic":
        self.fractal_type = "mandelbrot"
        self.fractal_center_re = -0.5
        self.fractal_center_im = 0.0
        self.fractal_zoom = 1.0
        self.fractal_max_iter = 80
    elif preset == "mandelbrot_seahorse":
        self.fractal_type = "mandelbrot"
        self.fractal_center_re = -0.745
        self.fractal_center_im = 0.113
        self.fractal_zoom = 50.0
        self.fractal_max_iter = 200
    elif preset == "mandelbrot_elephant":
        self.fractal_type = "mandelbrot"
        self.fractal_center_re = 0.282
        self.fractal_center_im = 0.01
        self.fractal_zoom = 20.0
        self.fractal_max_iter = 200
    elif preset == "mandelbrot_minibrot":
        self.fractal_type = "mandelbrot"
        self.fractal_center_re = -1.749
        self.fractal_center_im = 0.0
        self.fractal_zoom = 500.0
        self.fractal_max_iter = 500
    elif preset == "mandelbrot_spiral":
        self.fractal_type = "mandelbrot"
        self.fractal_center_re = -0.7463
        self.fractal_center_im = 0.1102
        self.fractal_zoom = 200.0
        self.fractal_max_iter = 300
    elif preset == "julia_dendrite":
        self.fractal_type = "julia"
        self.fractal_julia_re = 0.0
        self.fractal_julia_im = 1.0
        self.fractal_center_re = 0.0
        self.fractal_center_im = 0.0
        self.fractal_zoom = 1.0
        self.fractal_max_iter = 100
    elif preset == "julia_rabbit":
        self.fractal_type = "julia"
        self.fractal_julia_re = -0.123
        self.fractal_julia_im = 0.745
        self.fractal_center_re = 0.0
        self.fractal_center_im = 0.0
        self.fractal_zoom = 1.0
        self.fractal_max_iter = 100
    elif preset == "julia_sanmarco":
        self.fractal_type = "julia"
        self.fractal_julia_re = -0.75
        self.fractal_julia_im = 0.0
        self.fractal_center_re = 0.0
        self.fractal_center_im = 0.0
        self.fractal_zoom = 1.0
        self.fractal_max_iter = 100
    elif preset == "julia_siegel":
        self.fractal_type = "julia"
        self.fractal_julia_re = -0.391
        self.fractal_julia_im = -0.587
        self.fractal_center_re = 0.0
        self.fractal_center_im = 0.0
        self.fractal_zoom = 1.0
        self.fractal_max_iter = 120
    elif preset == "julia_dragon":
        self.fractal_type = "julia"
        self.fractal_julia_re = -0.8
        self.fractal_julia_im = 0.156
        self.fractal_center_re = 0.0
        self.fractal_center_im = 0.0
        self.fractal_zoom = 1.0
        self.fractal_max_iter = 100
    else:
        self.fractal_type = "mandelbrot"
        self.fractal_center_re = -0.5
        self.fractal_center_im = 0.0
        self.fractal_zoom = 1.0
        self.fractal_max_iter = 80

    self.fractal_running = True
    self.fractal_dirty = True



def _fractal_compute(self):
    """Compute the fractal iteration buffer for the current viewport."""
    rows = self.fractal_rows
    cols = self.fractal_cols
    # The visible region in the complex plane
    aspect = cols / (rows * 2.0)  # *2 because terminal chars are ~2x tall as wide
    half_h = 1.5 / self.fractal_zoom
    half_w = half_h * aspect
    re_min = self.fractal_center_re - half_w
    re_max = self.fractal_center_re + half_w
    im_min = self.fractal_center_im - half_h
    im_max = self.fractal_center_im + half_h
    max_iter = self.fractal_max_iter
    buf = []
    is_julia = self.fractal_type == "julia"
    jre = self.fractal_julia_re
    jim = self.fractal_julia_im
    for r in range(rows):
        row_data = []
        ci = im_max - (im_max - im_min) * r / rows
        for c in range(cols):
            cr = re_min + (re_max - re_min) * c / cols
            if is_julia:
                zr, zi = cr, ci
                c_re, c_im = jre, jim
            else:
                zr, zi = 0.0, 0.0
                c_re, c_im = cr, ci
            n = 0
            while n < max_iter:
                zr2 = zr * zr
                zi2 = zi * zi
                if zr2 + zi2 > 4.0:
                    break
                zi = 2.0 * zr * zi + c_im
                zr = zr2 - zi2 + c_re
                n += 1
            row_data.append(n)
        buf.append(row_data)
    self.fractal_buffer = buf
    self.fractal_dirty = False



def _enter_fractal_mode(self):
    self.fractal_menu = True
    self.fractal_menu_sel = 0
    self._flash("Fractal Explorer — select a preset")



def _exit_fractal_mode(self):
    self.fractal_mode = False
    self.fractal_menu = False
    self.fractal_running = False
    self.fractal_buffer = []
    self._flash("Fractal Explorer OFF")



def _handle_fractal_menu_key(self, key: int) -> bool:
    n = len(self.FRACTAL_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.fractal_menu_sel = (self.fractal_menu_sel - 1) % n
    elif key == curses.KEY_DOWN or key == ord("j"):
        self.fractal_menu_sel = (self.fractal_menu_sel + 1) % n
    elif key in (ord("q"), 27):
        self.fractal_menu = False
        self._flash("Fractal Explorer cancelled")
    elif key in (10, 13, curses.KEY_ENTER):
        name, _desc, preset_id = self.FRACTAL_PRESETS[self.fractal_menu_sel]
        self.fractal_menu = False
        self.fractal_mode = True
        self.fractal_preset_name = name
        self._fractal_init(preset_id)
    return True



def _handle_fractal_key(self, key: int) -> bool:
    pan_step = 0.15 / self.fractal_zoom
    if key == ord("q") or key == 27:
        self._exit_fractal_mode()
    elif key == curses.KEY_UP or key == ord("k"):
        self.fractal_center_im += pan_step
        self.fractal_dirty = True
    elif key == curses.KEY_DOWN or key == ord("j"):
        self.fractal_center_im -= pan_step
        self.fractal_dirty = True
    elif key == curses.KEY_LEFT or key == ord("h"):
        self.fractal_center_re -= pan_step
        self.fractal_dirty = True
    elif key == curses.KEY_RIGHT or key == ord("l"):
        self.fractal_center_re += pan_step
        self.fractal_dirty = True
    elif key == ord("+") or key == ord("=") or key == ord("z"):
        self.fractal_zoom *= 1.5
        self.fractal_dirty = True
        self._flash(f"Zoom: {self.fractal_zoom:.1f}x")
    elif key == ord("-") or key == ord("_") or key == ord("x"):
        self.fractal_zoom = max(0.1, self.fractal_zoom / 1.5)
        self.fractal_dirty = True
        self._flash(f"Zoom: {self.fractal_zoom:.1f}x")
    elif key == ord("i"):
        self.fractal_max_iter = min(5000, self.fractal_max_iter + 20)
        self.fractal_dirty = True
        self._flash(f"Max iterations: {self.fractal_max_iter}")
    elif key == ord("I"):
        self.fractal_max_iter = max(20, self.fractal_max_iter - 20)
        self.fractal_dirty = True
        self._flash(f"Max iterations: {self.fractal_max_iter}")
    elif key == ord("t"):
        if self.fractal_type == "mandelbrot":
            self.fractal_type = "julia"
            self._flash(f"Julia set (c = {self.fractal_julia_re:+.3f}{self.fractal_julia_im:+.3f}i)")
        else:
            self.fractal_type = "mandelbrot"
            self._flash("Mandelbrot set")
        self.fractal_dirty = True
    elif key == ord("c"):
        n_schemes = len(self.FRACTAL_COLOR_SCHEMES)
        self.fractal_color_scheme = (self.fractal_color_scheme + 1) % n_schemes
        scheme_name = self.FRACTAL_COLOR_SCHEMES[self.fractal_color_scheme][0]
        self._flash(f"Color: {scheme_name}")
    elif key == ord("r"):
        # Reset to current preset
        for _name, _desc, pid in self.FRACTAL_PRESETS:
            if _name == self.fractal_preset_name:
                self._fractal_init(pid)
                self._flash("Reset view")
                break
    elif key == ord("R"):
        self.fractal_mode = False
        self.fractal_menu = True
        self.fractal_menu_sel = 0
    elif key == ord("1"):
        self.fractal_julia_re = -0.7
        self.fractal_julia_im = 0.27015
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.3f}{self.fractal_julia_im:+.3f}i")
    elif key == ord("2"):
        self.fractal_julia_re = -0.123
        self.fractal_julia_im = 0.745
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.3f}{self.fractal_julia_im:+.3f}i")
    elif key == ord("3"):
        self.fractal_julia_re = -0.8
        self.fractal_julia_im = 0.156
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.3f}{self.fractal_julia_im:+.3f}i")
    elif key == ord("4"):
        self.fractal_julia_re = 0.285
        self.fractal_julia_im = 0.01
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.3f}{self.fractal_julia_im:+.3f}i")
    elif key == ord("5"):
        self.fractal_julia_re = -0.391
        self.fractal_julia_im = -0.587
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.3f}{self.fractal_julia_im:+.3f}i")
    elif key == ord("a"):
        # Adjust Julia c real part up
        self.fractal_julia_re += 0.01
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.4f}{self.fractal_julia_im:+.4f}i")
    elif key == ord("A"):
        self.fractal_julia_re -= 0.01
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.4f}{self.fractal_julia_im:+.4f}i")
    elif key == ord("s"):
        self.fractal_julia_im += 0.01
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.4f}{self.fractal_julia_im:+.4f}i")
    elif key == ord("S"):
        self.fractal_julia_im -= 0.01
        if self.fractal_type == "julia":
            self.fractal_dirty = True
        self._flash(f"Julia c = {self.fractal_julia_re:+.4f}{self.fractal_julia_im:+.4f}i")
    return True



def _draw_fractal_menu(self, max_y: int, max_x: int):
    self.stdscr.erase()
    title = "═══ Fractal Explorer ═══"
    if max_x > len(title):
        try:
            self.stdscr.addstr(1, (max_x - len(title)) // 2, title, curses.color_pair(4) | curses.A_BOLD)
        except curses.error:
            pass
    subtitle = "Explore the Mandelbrot set and Julia set fractals"
    if max_x > len(subtitle):
        try:
            self.stdscr.addstr(2, (max_x - len(subtitle)) // 2, subtitle, curses.color_pair(6))
        except curses.error:
            pass
    start_y = 4
    for idx, (name, desc, _pid) in enumerate(self.FRACTAL_PRESETS):
        if start_y + idx >= max_y - 6:
            break
        marker = "▸ " if idx == self.fractal_menu_sel else "  "
        attr = curses.A_BOLD | curses.color_pair(3) if idx == self.fractal_menu_sel else curses.color_pair(7)
        line = f"{marker}{name}"
        try:
            self.stdscr.addstr(start_y + idx, 4, line[:max_x - 5], attr)
        except curses.error:
            pass
        if idx == self.fractal_menu_sel and max_x > 40:
            try:
                self.stdscr.addstr(start_y + idx, 32, desc[:max_x - 33], curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass
    # Controls box
    box_y = max(start_y + len(self.FRACTAL_PRESETS) + 1, max_y - 5)
    controls = [
        "↑↓/jk = navigate   Enter = select   q/Esc = cancel",
    ]
    for ci, ct in enumerate(controls):
        if box_y + ci < max_y - 1:
            try:
                self.stdscr.addstr(box_y + ci, 4, ct[:max_x - 5], curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass



def _draw_fractal(self, max_y: int, max_x: int):
    # Recompute viewport size if terminal resized
    new_rows = max(10, max_y - 3)
    new_cols = max(20, max_x - 1)
    if new_rows != self.fractal_rows or new_cols != self.fractal_cols:
        self.fractal_rows = new_rows
        self.fractal_cols = new_cols
        self.fractal_dirty = True
    if self.fractal_dirty:
        self._fractal_compute()

    self.stdscr.erase()
    buf = self.fractal_buffer
    max_iter = self.fractal_max_iter
    density = self.FRACTAL_DENSITY
    n_density = len(density)
    scheme = self.FRACTAL_COLOR_SCHEMES[self.fractal_color_scheme][1]
    n_colors = len(scheme)

    for r in range(min(len(buf), max_y - 3)):
        row_data = buf[r]
        line_chars = []
        line_attrs = []
        for c_idx in range(min(len(row_data), max_x - 1)):
            n = row_data[c_idx]
            if n >= max_iter:
                # Inside the set — render as space (black)
                line_chars.append(" ")
                line_attrs.append(0)
            else:
                # Map iteration count to density character
                frac = n / max_iter
                ch_idx = int(frac * (n_density - 1))
                ch = density[min(ch_idx, n_density - 1)]
                # Map iteration count to color
                col_idx = n % n_colors
                attr = curses.color_pair(scheme[col_idx])
                if n > max_iter * 0.7:
                    attr |= curses.A_BOLD
                line_chars.append(ch)
                line_attrs.append(attr)
        # Batch render: build the line as one string, apply dominant attr
        # For better color, render char by char
        for ci, (ch, at) in enumerate(zip(line_chars, line_attrs)):
            try:
                self.stdscr.addch(r + 1, ci, ch, at)
            except curses.error:
                pass

    # Status bar
    ftype = self.fractal_type.capitalize()
    if self.fractal_type == "julia":
        ftype += f" c={self.fractal_julia_re:+.4f}{self.fractal_julia_im:+.4f}i"
    status = (f" {self.fractal_preset_name} │ {ftype}"
              f" │ Zoom: {self.fractal_zoom:.1f}x"
              f" │ Iter: {self.fractal_max_iter}"
              f" │ Center: ({self.fractal_center_re:.6f}, {self.fractal_center_im:.6f})")
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
        hint = " ←→↑↓=pan  z/x=zoom  i/I=iter  t=toggle type  c=color  1-5=Julia presets  a/A s/S=tweak c  r=reset  R=menu  q=exit"
    try:
        self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

# ══════════════════════════════════════════════════════════════════════
#  Navier-Stokes Fluid Dynamics — Mode Ctrl+D
# ══════════════════════════════════════════════════════════════════════

NS_PRESETS = [
    ("Dye Playground", "Empty canvas — inject dye with cursor and watch it flow", "playground"),
    ("Vortex Pair", "Two counter-rotating vortices merging", "vortex_pair"),
    ("Jet Stream", "Continuous fluid jet from the left wall", "jet"),
    ("Karman Vortices", "Flow past a circular obstacle with vortex shedding", "karman"),
    ("Four Corners", "Dye sources in each corner with opposing flows", "four_corners"),
    ("Shear Layer", "Opposing horizontal flows creating Kelvin-Helmholtz instability", "shear"),
]

NS_DYE_CHARS = [" ", "░", "▒", "▓", "█"]
NS_VEL_CHARS = [" ", "·", "∘", "○", "●"]
NS_VORT_POS = [" ", "·", "∘", "○", "◉"]
NS_VORT_NEG = [" ", "·", "∙", "•", "⬤"]




def register(App):
    """Register fractal mode methods on the App class."""
    App._fractal_init = _fractal_init
    App._fractal_compute = _fractal_compute
    App._enter_fractal_mode = _enter_fractal_mode
    App._exit_fractal_mode = _exit_fractal_mode
    App._handle_fractal_menu_key = _handle_fractal_menu_key
    App._handle_fractal_key = _handle_fractal_key
    App._draw_fractal_menu = _draw_fractal_menu
    App._draw_fractal = _draw_fractal

