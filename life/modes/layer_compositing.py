"""Mode: layer_compositing — stack 2-4 independent simulations as transparent layers
with configurable blend modes (add, XOR, mask, multiply), each running at its own
tick rate, composited into a single viewport in real-time."""
import curses
import math
import random
import time

from life.constants import SPEEDS

# Re-use the mini-simulation engines from mashup mode
from life.modes.mashup import _ENGINES, MASHUP_SIMS, _SIM_BY_ID

# Density visualization characters (5 levels)
_DENSITY = " ░▒▓█"

# ── Compositable simulation catalogue (same as mashup) ─────────────
COMP_SIMS = MASHUP_SIMS

# ── Blend modes ─────────────────────────────────────────────────────

def _blend_add(a, b):
    return min(1.0, a + b)

def _blend_multiply(a, b):
    return a * b

def _blend_xor(a, b):
    # High where exactly one is active, low where both or neither
    return abs(a - b)

def _blend_mask(a, b):
    # Layer B masks Layer A: A visible only where B > threshold
    return a if b > 0.15 else 0.0

def _blend_screen(a, b):
    return 1.0 - (1.0 - a) * (1.0 - b)

BLEND_MODES = [
    ("add",      "Add",      _blend_add,      "Sum intensities (bright overlaps)"),
    ("xor",      "XOR",      _blend_xor,      "Difference — high where only one active"),
    ("mask",     "Mask",     _blend_mask,      "Lower layers visible only where top > 0"),
    ("multiply", "Multiply", _blend_multiply,  "Darken — both must be active"),
    ("screen",   "Screen",   _blend_screen,    "Lighten — inverse multiply"),
]

_BLEND_BY_ID = {b[0]: b for b in BLEND_MODES}

# ── Presets ─────────────────────────────────────────────────────────

COMP_PRESETS = [
    {
        "name": "Breathing Shapes",
        "desc": "Reaction-Diffusion masked by Game of Life — organic pulsing forms",
        "layers": [
            {"sim": "rd",   "blend": "add",  "opacity": 1.0, "tick_mult": 1},
            {"sim": "gol",  "blend": "mask", "opacity": 0.8, "tick_mult": 2},
        ],
    },
    {
        "name": "Shimmering Flock",
        "desc": "Wave Equation added to Boids — luminous swarm patterns",
        "layers": [
            {"sim": "wave",  "blend": "add",  "opacity": 1.0, "tick_mult": 1},
            {"sim": "boids", "blend": "add",  "opacity": 0.7, "tick_mult": 1},
        ],
    },
    {
        "name": "Crystal Lightning",
        "desc": "Fractal Reaction-Diffusion XOR'd with Forest Fire",
        "layers": [
            {"sim": "rd",   "blend": "add",      "opacity": 1.0, "tick_mult": 1},
            {"sim": "fire", "blend": "xor",      "opacity": 0.9, "tick_mult": 2},
        ],
    },
    {
        "name": "Spin Waves",
        "desc": "Ising magnetic domains multiplied by Wave interference",
        "layers": [
            {"sim": "ising", "blend": "add",      "opacity": 1.0, "tick_mult": 1},
            {"sim": "wave",  "blend": "multiply", "opacity": 0.8, "tick_mult": 1},
        ],
    },
    {
        "name": "Slime Circuit",
        "desc": "Physarum trails screened over Rock-Paper-Scissors",
        "layers": [
            {"sim": "rps",     "blend": "add",    "opacity": 1.0, "tick_mult": 1},
            {"sim": "physarum","blend": "screen",  "opacity": 0.7, "tick_mult": 1},
        ],
    },
    {
        "name": "Triple Cascade",
        "desc": "Game of Life + Wave + Fire — three-layer visual chaos",
        "layers": [
            {"sim": "gol",  "blend": "add",  "opacity": 1.0, "tick_mult": 2},
            {"sim": "wave", "blend": "add",  "opacity": 0.6, "tick_mult": 1},
            {"sim": "fire", "blend": "xor",  "opacity": 0.5, "tick_mult": 3},
        ],
    },
    {
        "name": "Quad Stack",
        "desc": "Four simulations blended — maximum visual complexity",
        "layers": [
            {"sim": "gol",     "blend": "add",      "opacity": 1.0, "tick_mult": 2},
            {"sim": "wave",    "blend": "screen",    "opacity": 0.6, "tick_mult": 1},
            {"sim": "boids",   "blend": "add",       "opacity": 0.5, "tick_mult": 1},
            {"sim": "physarum","blend": "multiply",   "opacity": 0.4, "tick_mult": 1},
        ],
    },
]

# ── Layer colors (one per layer index, cycled) ──────────────────────
_LAYER_COLORS = [6, 1, 3, 2, 5, 4]  # cyan, red, yellow, green, magenta, blue


# ════════════════════════════════════════════════════════════════════
#  Mode entry / exit
# ════════════════════════════════════════════════════════════════════

def _enter_comp_mode(self):
    """Enter Layer Compositing mode — show preset menu."""
    self.comp_menu = True
    self.comp_menu_sel = 0
    self.comp_menu_phase = 0  # 0=presets, 1=custom_pick_sim, 2=custom_pick_blend, 3=confirm
    self.comp_custom_layers = []
    self._flash("Layer Compositing — pick a preset or build your own")


def _exit_comp_mode(self):
    """Exit Layer Compositing mode and clean up."""
    self.comp_mode = False
    self.comp_menu = False
    self.comp_running = False
    self.comp_layers = []
    self._flash("Layer Compositing OFF")


# ════════════════════════════════════════════════════════════════════
#  Initialization
# ════════════════════════════════════════════════════════════════════

def _comp_init(self, layer_defs):
    """Initialize the layer stack from a list of layer definitions.

    Each layer_def: {"sim": id, "blend": blend_id, "opacity": float, "tick_mult": int}
    """
    max_y, max_x = self.stdscr.getmaxyx()
    rows = max(20, max_y - 4)
    cols = max(20, (max_x - 1) // 2)
    self.comp_rows = rows
    self.comp_cols = cols
    self.comp_layers = []

    for i, ld in enumerate(layer_defs):
        sim_id = ld["sim"]
        init_fn, _, density_fn = _ENGINES[sim_id]
        state = init_fn(rows, cols)
        density = density_fn(state)
        layer = {
            "sim_id": sim_id,
            "sim_name": _SIM_BY_ID[sim_id]["name"],
            "state": state,
            "density": density,
            "blend": ld.get("blend", "add"),
            "opacity": ld.get("opacity", 1.0),
            "tick_mult": max(1, ld.get("tick_mult", 1)),
            "color": _LAYER_COLORS[i % len(_LAYER_COLORS)],
        }
        self.comp_layers.append(layer)

    self.comp_generation = 0
    self.comp_running = False
    self.comp_focus = 0  # selected layer for editing
    self.comp_menu = False
    self.comp_mode = True

    names = " + ".join(l["sim_name"] for l in self.comp_layers)
    self._flash(f"Compositing: {names} — Space to start")


# ════════════════════════════════════════════════════════════════════
#  Simulation step
# ════════════════════════════════════════════════════════════════════

def _comp_step(self):
    """Advance all layers. Each layer runs independently (no coupling)
    at its own tick rate."""
    gen = self.comp_generation
    for layer in self.comp_layers:
        # Only step this layer if generation aligns with its tick multiplier
        if gen % layer["tick_mult"] == 0:
            _, step_fn, density_fn = _ENGINES[layer["sim_id"]]
            # No coupling — pass None for other_density, 0 for coupling strength
            step_fn(layer["state"], None, 0.0)
            layer["density"] = density_fn(layer["state"])
    self.comp_generation += 1


# ════════════════════════════════════════════════════════════════════
#  Compositing engine — blend all layers into a single density grid
# ════════════════════════════════════════════════════════════════════

def _comp_composite(self):
    """Blend all layers into a single (value, dominant_layer_index) grid."""
    rows = self.comp_rows
    cols = self.comp_cols
    layers = self.comp_layers
    if not layers:
        return [[0.0] * cols for _ in range(rows)], [[0] * cols for _ in range(rows)]

    # Result grids
    result = [[0.0] * cols for _ in range(rows)]
    dominant = [[0] * cols for _ in range(rows)]  # which layer contributes most

    for r in range(rows):
        for c in range(cols):
            val = 0.0
            max_contrib = 0.0
            dom = 0
            for li, layer in enumerate(layers):
                d = layer["density"]
                lv = d[r][c] if r < len(d) and c < len(d[r]) else 0.0
                lv *= layer["opacity"]

                if li == 0:
                    # Base layer — just use its value
                    val = lv
                    max_contrib = lv
                    dom = 0
                else:
                    # Blend with accumulated result
                    blend_id = layer["blend"]
                    blend_info = _BLEND_BY_ID.get(blend_id)
                    if blend_info:
                        blend_fn = blend_info[2]
                        val = blend_fn(val, lv)
                    else:
                        val = min(1.0, val + lv)

                if lv > max_contrib:
                    max_contrib = lv
                    dom = li

            result[r][c] = max(0.0, min(1.0, val))
            dominant[r][c] = dom

    return result, dominant


# ════════════════════════════════════════════════════════════════════
#  Menu drawing
# ════════════════════════════════════════════════════════════════════

def _draw_comp_menu(self, max_y, max_x):
    """Draw the layer compositing configuration menu."""
    self.stdscr.erase()
    phase = self.comp_menu_phase

    title = "── Layer Compositing ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    if phase == 0:
        # ── Preset selection ──
        subtitle = "Choose a preset or build custom layers:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                               curses.color_pair(6))
        except curses.error:
            pass

        for i, preset in enumerate(COMP_PRESETS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.comp_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            line = f"{marker}{preset['name']}"
            nlayers = len(preset["layers"])
            tag = f" ({nlayers} layers)"
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
                self.stdscr.addstr(y, 2 + len(line), tag[:max_x - len(line) - 4],
                                   curses.color_pair(3))
            except curses.error:
                pass
            if sel:
                try:
                    self.stdscr.addstr(y + 1, 4,
                                       preset["desc"][:max_x - 6],
                                       curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass

        # Custom option
        ci = len(COMP_PRESETS)
        y = 5 + ci + 1  # +1 for description line of last selected
        if y < max_y - 3:
            sel = self.comp_menu_sel == ci
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(3)
            try:
                self.stdscr.addstr(y, 2, f"{marker}Custom Layer Stack..."[:max_x - 4], attr)
            except curses.error:
                pass

    elif phase == 1:
        # ── Pick simulation for next custom layer ──
        n_existing = len(self.comp_custom_layers)
        subtitle = f"Layer {n_existing + 1} — Select simulation:"
        if n_existing > 0:
            existing = ", ".join(_SIM_BY_ID[l["sim"]]["name"] for l in self.comp_custom_layers)
            subtitle = f"Layers so far: {existing}  |  Layer {n_existing + 1}:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2),
                               subtitle[:max_x - 2], curses.color_pair(6))
        except curses.error:
            pass
        for i, sim in enumerate(COMP_SIMS):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.comp_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{sim['name']}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 30, sim["desc"][:max_x - 32],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    elif phase == 2:
        # ── Pick blend mode for this layer ──
        sim_name = _SIM_BY_ID[self.comp_pick_sim]["name"]
        subtitle = f"Layer {len(self.comp_custom_layers) + 1}: {sim_name} — Select blend mode:"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2),
                               subtitle[:max_x - 2], curses.color_pair(6))
        except curses.error:
            pass
        for i, (bid, bname, _, bdesc) in enumerate(BLEND_MODES):
            y = 5 + i
            if y >= max_y - 3:
                break
            sel = i == self.comp_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{bname}"[:max_x - 4], attr)
                self.stdscr.addstr(y, 20, bdesc[:max_x - 22],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    elif phase == 3:
        # ── Confirm / add more layers ──
        subtitle = "Layer stack configured. Add more or start?"
        try:
            self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2),
                               subtitle[:max_x - 2], curses.color_pair(6))
        except curses.error:
            pass

        # Show current stack
        for i, ld in enumerate(self.comp_custom_layers):
            y = 5 + i
            if y >= max_y - 5:
                break
            sim_name = _SIM_BY_ID[ld["sim"]]["name"]
            blend_name = _BLEND_BY_ID[ld["blend"]][1]
            line = f"  Layer {i + 1}: {sim_name}  blend={blend_name}  tick=×{ld['tick_mult']}"
            try:
                self.stdscr.addstr(y, 2, line[:max_x - 4],
                                   curses.color_pair(_LAYER_COLORS[i % len(_LAYER_COLORS)]))
            except curses.error:
                pass

        n = len(self.comp_custom_layers)
        opts_y = 5 + n + 1
        options = []
        if n < 4:
            options.append("Add another layer")
        options.append("Start compositing!")

        for i, opt in enumerate(options):
            y = opts_y + i
            if y >= max_y - 3:
                break
            sel = i == self.comp_menu_sel
            marker = "▸ " if sel else "  "
            attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(3)
            try:
                self.stdscr.addstr(y, 2, f"{marker}{opt}"[:max_x - 4], attr)
            except curses.error:
                pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [Up/Down]=navigate  [Enter]=select  [Esc]=back/exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Menu key handling
# ════════════════════════════════════════════════════════════════════

def _handle_comp_menu_key(self, key):
    """Handle input in the compositing configuration menu."""
    if key == -1:
        return True
    phase = self.comp_menu_phase

    # Determine item count for current phase
    if phase == 0:
        n = len(COMP_PRESETS) + 1  # +1 for Custom
    elif phase == 1:
        n = len(COMP_SIMS)
    elif phase == 2:
        n = len(BLEND_MODES)
    elif phase == 3:
        n_layers = len(self.comp_custom_layers)
        n = (1 if n_layers >= 4 else 2)  # "add more" + "start", or just "start"
    else:
        n = 1

    if key == curses.KEY_UP or key == ord("k"):
        self.comp_menu_sel = (self.comp_menu_sel - 1) % max(1, n)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.comp_menu_sel = (self.comp_menu_sel + 1) % max(1, n)
        return True
    if key == 27:  # Esc
        if phase == 3:
            # Go back to adding layers
            self.comp_menu_phase = 1
            self.comp_menu_sel = 0
        elif phase > 0:
            self.comp_menu_phase = phase - 1
            self.comp_menu_sel = 0
        else:
            self.comp_menu = False
            self._flash("Compositing cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if phase == 0:
            sel = self.comp_menu_sel
            if sel < len(COMP_PRESETS):
                preset = COMP_PRESETS[sel]
                self._comp_init(preset["layers"])
            else:
                # Custom mode
                self.comp_custom_layers = []
                self.comp_menu_phase = 1
                self.comp_menu_sel = 0
        elif phase == 1:
            self.comp_pick_sim = COMP_SIMS[self.comp_menu_sel]["id"]
            if len(self.comp_custom_layers) == 0:
                # First layer always uses "add" (base)
                self.comp_custom_layers.append({
                    "sim": self.comp_pick_sim,
                    "blend": "add",
                    "opacity": 1.0,
                    "tick_mult": 1,
                })
                # If we have 2+ layers now or can add more, go to confirm
                self.comp_menu_phase = 3
                self.comp_menu_sel = 0
            else:
                # Non-first layer: pick blend mode
                self.comp_menu_phase = 2
                self.comp_menu_sel = 0
        elif phase == 2:
            blend_id = BLEND_MODES[self.comp_menu_sel][0]
            self.comp_custom_layers.append({
                "sim": self.comp_pick_sim,
                "blend": blend_id,
                "opacity": max(0.3, 1.0 - 0.2 * len(self.comp_custom_layers)),
                "tick_mult": 1,
            })
            self.comp_menu_phase = 3
            self.comp_menu_sel = 0
        elif phase == 3:
            n_layers = len(self.comp_custom_layers)
            if n_layers < 4 and self.comp_menu_sel == 0:
                # Add another layer
                self.comp_menu_phase = 1
                self.comp_menu_sel = 0
            else:
                # Start!
                if n_layers >= 2:
                    self._comp_init(self.comp_custom_layers)
                else:
                    self._flash("Need at least 2 layers — add more")
                    self.comp_menu_phase = 1
                    self.comp_menu_sel = 0
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Main simulation drawing
# ════════════════════════════════════════════════════════════════════

def _draw_comp(self, max_y, max_x):
    """Draw the composited layer simulation."""
    self.stdscr.erase()

    # ── Header ──
    state = "▶ RUNNING" if self.comp_running else "⏸ PAUSED"
    layers = self.comp_layers
    names = " + ".join(l["sim_name"] for l in layers)
    blend_info = "/".join(l["blend"] for l in layers[1:]) if len(layers) > 1 else ""
    title = (f" COMPOSITE: {names}"
             f"  |  gen {self.comp_generation}"
             f"  |  blend={blend_info}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1],
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # ── Composite and render ──
    result, dominant = self._comp_composite()
    rows = self.comp_rows
    cols = self.comp_cols
    view_rows = min(rows, max_y - 4)
    view_cols = min(cols, (max_x - 1) // 2)

    for r in range(view_rows):
        sy = 1 + r
        if sy >= max_y - 3:
            break
        res_row = result[r] if r < len(result) else []
        dom_row = dominant[r] if r < len(dominant) else []
        for c in range(view_cols):
            sx = c * 2
            if sx + 1 >= max_x:
                break
            val = res_row[c] if c < len(res_row) else 0.0
            if val < 0.01:
                continue

            # Density glyph
            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]

            # Color from dominant layer
            dom_idx = dom_row[c] if c < len(dom_row) else 0
            if dom_idx < len(layers):
                pair = layers[dom_idx]["color"]
            else:
                pair = 6

            # Brightness from intensity
            if val > 0.7:
                attr = curses.color_pair(pair) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(pair)
            else:
                attr = curses.color_pair(pair) | curses.A_DIM

            try:
                self.stdscr.addstr(sy, sx, ch + " ", attr)
            except curses.error:
                pass

    # ── Layer legend bar ──
    legend_y = max_y - 3
    if legend_y > 1:
        parts = []
        for i, layer in enumerate(layers):
            blend_tag = layer["blend"] if i > 0 else "base"
            tick_tag = f"×{layer['tick_mult']}" if layer["tick_mult"] > 1 else ""
            focus = "►" if i == self.comp_focus else " "
            parts.append(f"{focus}L{i+1}:{layer['sim_name']}({blend_tag}{tick_tag})")
        legend = "  ".join(parts)
        try:
            self.stdscr.addstr(legend_y, 0, legend[:max_x - 1],
                               curses.color_pair(7))
        except curses.error:
            pass

    # ── Status bar ──
    status_y = max_y - 2
    if status_y > 1:
        # Per-layer average density
        parts = []
        for i, layer in enumerate(layers):
            d = layer["density"]
            total = 0.0
            cnt = max(1, rows * cols)
            for row in d[:rows]:
                for v in row[:cols]:
                    total += v
            avg = total / cnt
            parts.append(f"L{i+1}={avg:.3f}")
        focus_layer = layers[self.comp_focus] if self.comp_focus < len(layers) else None
        focus_info = ""
        if focus_layer:
            focus_info = (f"  |  focus=L{self.comp_focus + 1}"
                         f" opacity={focus_layer['opacity']:.2f}"
                         f" tick=×{focus_layer['tick_mult']}")
        status = f" gen {self.comp_generation}  |  {' '.join(parts)}{focus_info}"
        try:
            self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                               curses.color_pair(6))
        except curses.error:
            pass

    # ── Hint bar ──
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = (" [Space]=play [n]=step [Tab]=focus layer [+/-]=opacity"
                    " [t/T]=tick rate [b]=blend [r]=reset [R]=menu [q]=exit")
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Simulation key handling
# ════════════════════════════════════════════════════════════════════

def _handle_comp_key(self, key):
    """Handle input during active compositing simulation."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_comp_mode()
        return True
    if key == ord(" "):
        self.comp_running = not self.comp_running
        self._flash("Playing" if self.comp_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.comp_running = False
        self._comp_step()
        return True
    # Tab: cycle focused layer
    if key == 9:
        n = len(self.comp_layers)
        if n > 0:
            self.comp_focus = (self.comp_focus + 1) % n
            layer = self.comp_layers[self.comp_focus]
            self._flash(f"Focus: L{self.comp_focus + 1} {layer['sim_name']}"
                       f" (blend={layer['blend']} opacity={layer['opacity']:.2f}"
                       f" tick=×{layer['tick_mult']})")
        return True
    # +/- : adjust focused layer opacity
    if key == ord("+") or key == ord("="):
        if self.comp_layers:
            layer = self.comp_layers[self.comp_focus]
            layer["opacity"] = min(1.0, layer["opacity"] + 0.05)
            self._flash(f"L{self.comp_focus + 1} opacity: {layer['opacity']:.2f}")
        return True
    if key == ord("-") or key == ord("_"):
        if self.comp_layers:
            layer = self.comp_layers[self.comp_focus]
            layer["opacity"] = max(0.0, layer["opacity"] - 0.05)
            self._flash(f"L{self.comp_focus + 1} opacity: {layer['opacity']:.2f}")
        return True
    # t/T: adjust focused layer tick rate
    if key == ord("t"):
        if self.comp_layers:
            layer = self.comp_layers[self.comp_focus]
            layer["tick_mult"] = min(8, layer["tick_mult"] + 1)
            self._flash(f"L{self.comp_focus + 1} tick rate: ×{layer['tick_mult']}")
        return True
    if key == ord("T"):
        if self.comp_layers:
            layer = self.comp_layers[self.comp_focus]
            layer["tick_mult"] = max(1, layer["tick_mult"] - 1)
            self._flash(f"L{self.comp_focus + 1} tick rate: ×{layer['tick_mult']}")
        return True
    # b: cycle blend mode for focused layer
    if key == ord("b"):
        if self.comp_layers and self.comp_focus > 0:
            layer = self.comp_layers[self.comp_focus]
            cur = layer["blend"]
            ids = [b[0] for b in BLEND_MODES]
            idx = ids.index(cur) if cur in ids else 0
            idx = (idx + 1) % len(ids)
            layer["blend"] = ids[idx]
            self._flash(f"L{self.comp_focus + 1} blend: {_BLEND_BY_ID[ids[idx]][1]}")
        elif self.comp_focus == 0:
            self._flash("Base layer always uses Add")
        return True
    # r: reset all layers
    if key == ord("r"):
        defs = []
        for layer in self.comp_layers:
            defs.append({
                "sim": layer["sim_id"],
                "blend": layer["blend"],
                "opacity": layer["opacity"],
                "tick_mult": layer["tick_mult"],
            })
        self._comp_init(defs)
        self._flash("Reset!")
        return True
    # R: back to menu
    if key == ord("R"):
        self.comp_mode = False
        self.comp_running = False
        self.comp_menu = True
        self.comp_menu_phase = 0
        self.comp_menu_sel = 0
        return True
    # Speed controls
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        return True
    return True


# ════════════════════════════════════════════════════════════════════
#  Registration
# ════════════════════════════════════════════════════════════════════

def register(App):
    """Register layer compositing mode methods on the App class."""
    App._enter_comp_mode = _enter_comp_mode
    App._exit_comp_mode = _exit_comp_mode
    App._comp_init = _comp_init
    App._comp_step = _comp_step
    App._comp_composite = _comp_composite
    App._handle_comp_menu_key = _handle_comp_menu_key
    App._handle_comp_key = _handle_comp_key
    App._draw_comp_menu = _draw_comp_menu
    App._draw_comp = _draw_comp
    App.COMP_PRESETS = COMP_PRESETS
    App.COMP_SIMS = COMP_SIMS
    App.BLEND_MODES = BLEND_MODES
