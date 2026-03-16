"""Mode: neural_ca — Neural Cellular Automata.

Per-cell neural networks learn to self-organize into target patterns.
Instead of lookup-table rules, each cell runs a small neural network:
  perception (neighbor convolution) → hidden layer → state update.

Training uses evolutionary strategies (ES) for gradient-free optimization.
Users can draw a target shape, press train, and watch the NCA learn to
reproduce it — all in the terminal, pure Python (no NumPy dependency).

Inspired by Google's "Growing Neural Cellular Automata" (Mordvintsev et al.).
"""
import curses
import math
import os
import random

from life.constants import SAVE_DIR, SPEEDS, SPEED_LABELS

# ── Constants ────────────────────────────────────────────────────────

_NCA_CHANNELS = 3       # state channels per cell: [alive, hidden1, hidden2]
_PERCEPTION_DIM = 9     # 3 sobel filters × 3 channels = 9 perception inputs
_HIDDEN_DIM = 8         # hidden layer size (kept small for pure-Python speed)
_UPDATE_DIM = _NCA_CHANNELS  # output updates all channels

# Perception kernels (Sobel-like 3×3 for identity + gradients)
# Each kernel is a flat list of 9 values (row-major 3×3)
_IDENTITY_K = [0, 0, 0, 0, 1, 0, 0, 0, 0]
_SOBEL_X = [-0.125, 0, 0.125, -0.25, 0, 0.25, -0.125, 0, 0.125]
_SOBEL_Y = [-0.125, -0.25, -0.125, 0, 0, 0, 0.125, 0.25, 0.125]
_KERNELS = [_IDENTITY_K, _SOBEL_X, _SOBEL_Y]

_DENSITY = ["  ", "░░", "▒▒", "▓▓", "██"]

_PRESET_NAMES = ["circle", "square", "diamond", "cross", "ring", "heart", "custom"]

# 3×3 neighbor offsets (row-major)
_OFFSETS_3x3 = [(-1, -1), (-1, 0), (-1, 1),
                (0, -1),  (0, 0),  (0, 1),
                (1, -1),  (1, 0),  (1, 1)]


# ── Pure-Python Matrix Helpers ───────────────────────────────────────

def _zeros_2d(rows, cols):
    """Create a 2D list of zeros."""
    return [[0.0] * cols for _ in range(rows)]


def _zeros_3d(h, w, c):
    """Create a 3D list of zeros: h × w × c."""
    return [[[0.0] * c for _ in range(w)] for _ in range(h)]


def _copy_3d(state):
    """Deep copy a 3D state grid."""
    return [[[state[r][c][ch] for ch in range(len(state[0][0]))]
             for c in range(len(state[0]))] for r in range(len(state))]


def _copy_2d(grid):
    """Deep copy a 2D grid."""
    return [[grid[r][c] for c in range(len(grid[0]))] for r in range(len(grid))]


# ── Neural Network (flat weight vectors) ─────────────────────────────

def _param_count():
    """Total number of learnable parameters."""
    return _PERCEPTION_DIM * _HIDDEN_DIM + _HIDDEN_DIM + _HIDDEN_DIM * _UPDATE_DIM + _UPDATE_DIM


def _init_weights_flat():
    """Initialize neural network as a flat list of floats."""
    n = _param_count()
    scale1 = math.sqrt(2.0 / _PERCEPTION_DIM)
    scale2 = math.sqrt(2.0 / _HIDDEN_DIM) * 0.1
    flat = []
    # W1: PERCEPTION_DIM × HIDDEN_DIM
    for _ in range(_PERCEPTION_DIM * _HIDDEN_DIM):
        flat.append(random.gauss(0, scale1))
    # b1: HIDDEN_DIM
    for _ in range(_HIDDEN_DIM):
        flat.append(0.0)
    # W2: HIDDEN_DIM × UPDATE_DIM
    for _ in range(_HIDDEN_DIM * _UPDATE_DIM):
        flat.append(random.gauss(0, scale2))
    # b2: UPDATE_DIM
    for _ in range(_UPDATE_DIM):
        flat.append(0.0)
    return flat


def _unpack_weights(flat):
    """Unpack flat weights into (w1, b1, w2, b2) as nested lists.

    w1: PERCEPTION_DIM × HIDDEN_DIM (list of lists)
    b1: HIDDEN_DIM (list)
    w2: HIDDEN_DIM × UPDATE_DIM (list of lists)
    b2: UPDATE_DIM (list)
    """
    idx = 0
    w1 = []
    for i in range(_PERCEPTION_DIM):
        row = flat[idx:idx + _HIDDEN_DIM]
        w1.append(row)
        idx += _HIDDEN_DIM
    b1 = flat[idx:idx + _HIDDEN_DIM]
    idx += _HIDDEN_DIM
    w2 = []
    for i in range(_HIDDEN_DIM):
        row = flat[idx:idx + _UPDATE_DIM]
        w2.append(row)
        idx += _UPDATE_DIM
    b2 = flat[idx:idx + _UPDATE_DIM]
    return w1, b1, w2, b2


# ── Perception & Forward Pass ────────────────────────────────────────

def _forward(state, flat_params, h, w, stochastic_rate=0.5):
    """Run one NCA step: perceive → dense → relu → dense → residual update.

    state: h × w × C (3D list)
    Returns new state (h × w × C as 3D list).
    """
    c = _NCA_CHANNELS
    w1, b1, w2, b2 = _unpack_weights(flat_params)

    new_state = _copy_3d(state)

    for r in range(h):
        for col in range(w):
            # Stochastic update: skip some cells
            if random.random() > stochastic_rate:
                continue

            # ── Perception: apply 3 kernels to C channels ──
            perc = [0.0] * _PERCEPTION_DIM  # 3 kernels × C channels = 9
            pi = 0
            for ki, kernel in enumerate(_KERNELS):
                for ci in range(c):
                    val = 0.0
                    for oi, (dr, dc) in enumerate(_OFFSETS_3x3):
                        kv = kernel[oi]
                        if kv != 0:
                            nr = (r + dr) % h
                            nc = (col + dc) % w
                            val += kv * state[nr][nc][ci]
                    perc[pi] = val
                    pi += 1

            # ── Layer 1: dense + ReLU ──
            hidden = [0.0] * _HIDDEN_DIM
            for j in range(_HIDDEN_DIM):
                s = b1[j]
                for i in range(_PERCEPTION_DIM):
                    s += perc[i] * w1[i][j]
                hidden[j] = max(0.0, s)  # ReLU

            # ── Layer 2: dense (raw update) ──
            update = [0.0] * _UPDATE_DIM
            for j in range(_UPDATE_DIM):
                s = b2[j]
                for i in range(_HIDDEN_DIM):
                    s += hidden[i] * w2[i][j]
                update[j] = s

            # ── Residual update ──
            for ci in range(c):
                new_state[r][col][ci] = state[r][col][ci] + update[ci]

    # ── Alive masking ──
    # Cell stays alive only if it or a neighbor has alpha > 0.1
    for r in range(h):
        for col in range(w):
            any_alive = False
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nr = (r + dr) % h
                    nc = (col + dc) % w
                    if new_state[nr][nc][0] > 0.1:
                        any_alive = True
                        break
                if any_alive:
                    break
            if not any_alive:
                for ci in range(c):
                    new_state[r][col][ci] = 0.0
            else:
                # Clamp to [0, 1]
                for ci in range(c):
                    v = new_state[r][col][ci]
                    if v < 0.0:
                        new_state[r][col][ci] = 0.0
                    elif v > 1.0:
                        new_state[r][col][ci] = 1.0

    return new_state


# ── Target Pattern Generation ────────────────────────────────────────

def _make_target(name, h, w):
    """Generate a binary target pattern as h × w list of floats."""
    target = _zeros_2d(h, w)
    cy, cx = h // 2, w // 2
    radius = min(h, w) // 4

    if name == "circle":
        r2 = radius * radius
        for r in range(h):
            for c in range(w):
                if (r - cy) ** 2 + (c - cx) ** 2 <= r2:
                    target[r][c] = 1.0

    elif name == "square":
        for r in range(max(0, cy - radius), min(h, cy + radius)):
            for c in range(max(0, cx - radius), min(w, cx + radius)):
                target[r][c] = 1.0

    elif name == "diamond":
        for r in range(h):
            for c in range(w):
                if abs(r - cy) + abs(c - cx) <= radius:
                    target[r][c] = 1.0

    elif name == "cross":
        arm = max(2, radius // 3)
        for r in range(max(0, cy - radius), min(h, cy + radius + 1)):
            for c in range(max(0, cx - arm), min(w, cx + arm + 1)):
                target[r][c] = 1.0
        for r in range(max(0, cy - arm), min(h, cy + arm + 1)):
            for c in range(max(0, cx - radius), min(w, cx + radius + 1)):
                target[r][c] = 1.0

    elif name == "ring":
        inner = radius * 2 // 3
        inner2 = inner * inner
        r2 = radius * radius
        for r in range(h):
            for c in range(w):
                d2 = (r - cy) ** 2 + (c - cx) ** 2
                if inner2 <= d2 <= r2:
                    target[r][c] = 1.0

    elif name == "heart":
        for r in range(h):
            for c in range(w):
                x = (c - cx) / max(radius, 1)
                y = -(r - cy) / max(radius, 1)
                if (x ** 2 + (y - abs(x) ** 0.7) ** 2) < 0.8:
                    target[r][c] = 1.0

    return target


def _seed_state(h, w, seed_radius=2):
    """Create initial state: small seed in center."""
    state = _zeros_3d(h, w, _NCA_CHANNELS)
    cy, cx = h // 2, w // 2
    for dr in range(-seed_radius, seed_radius + 1):
        for dc in range(-seed_radius, seed_radius + 1):
            r, c = cy + dr, cx + dc
            if 0 <= r < h and 0 <= c < w:
                state[r][c][0] = 1.0
                for ch in range(1, _NCA_CHANNELS):
                    state[r][c][ch] = 0.5
    return state


# ── Loss computation ─────────────────────────────────────────────────

def _compute_loss(state, target, h, w):
    """MSE loss between alive channel and target pattern."""
    total = 0.0
    for r in range(h):
        for c in range(w):
            d = state[r][c][0] - target[r][c]
            total += d * d
    return total / (h * w)


# ── Evolutionary Strategies (ES) Training ────────────────────────────

def _es_step(params, target, grid_h, grid_w, pop_size=16, sigma=0.02,
             lr=0.03, grow_steps=30):
    """One step of evolution strategies for NCA training.

    Uses antithetic sampling for variance reduction.
    Returns (new_params, best_loss, mean_loss).
    """
    n_params = len(params)
    half = pop_size // 2

    # Generate perturbations (antithetic)
    epsilons = []
    for i in range(half):
        eps = [random.gauss(0, 1) for _ in range(n_params)]
        epsilons.append(eps)
        epsilons.append([-e for e in eps])  # antithetic pair

    losses = []
    for i in range(pop_size):
        # Create candidate
        candidate = [params[j] + sigma * epsilons[i][j] for j in range(n_params)]

        # Grow from seed
        state = _seed_state(grid_h, grid_w)
        for _ in range(grow_steps):
            state = _forward(state, candidate, grid_h, grid_w, stochastic_rate=0.5)

        loss = _compute_loss(state, target, grid_h, grid_w)
        losses.append(loss)

    # Normalize losses
    mean_loss = sum(losses) / pop_size
    best_loss = min(losses)
    centered = [l - mean_loss for l in losses]
    std = math.sqrt(sum(c * c for c in centered) / pop_size)
    if std > 1e-8:
        centered = [c / std for c in centered]

    # Estimated gradient
    grad = [0.0] * n_params
    for j in range(n_params):
        g = 0.0
        for i in range(pop_size):
            g += epsilons[i][j] * centered[i]
        grad[j] = g / (pop_size * sigma)

    # Update params (gradient descent)
    new_params = [params[j] - lr * grad[j] for j in range(n_params)]

    return new_params, best_loss, mean_loss


# ── Mode Functions ───────────────────────────────────────────────────

def _enter_nca_mode(self):
    """Enter Neural CA mode — show settings menu."""
    self.nca_mode = False
    self.nca_menu = True
    self.nca_menu_sel = 0
    self._flash("Neural Cellular Automata — cells learn to self-organize")


def _exit_nca_mode(self):
    """Exit Neural CA mode."""
    self.nca_mode = False
    self.nca_menu = False
    self.nca_running = False
    self.nca_training = False
    self.nca_state = None
    self.nca_params = None
    self.nca_target = None
    self.nca_loss_history = []
    self.nca_custom_target = None
    self._flash("Neural CA OFF")


def _nca_init(self):
    """Initialize NCA simulation with current settings."""
    max_y, max_x = self.stdscr.getmaxyx()
    gh = min(self.nca_grid_h, max_y - 8)
    gw = min(self.nca_grid_w, (max_x - 2) // 2)
    self.nca_grid_h_actual = gh
    self.nca_grid_w_actual = gw

    # Initialize target
    preset = _PRESET_NAMES[self.nca_target_idx]
    if preset == "custom" and self.nca_custom_target is not None:
        self.nca_target = _copy_2d(self.nca_custom_target)
    else:
        self.nca_target = _make_target(preset, gh, gw)

    # Initialize neural network weights
    self.nca_params = _init_weights_flat()

    # Initialize state from seed
    self.nca_state = _seed_state(gh, gw)

    # Training state
    self.nca_loss_history = []
    self.nca_train_gen = 0
    self.nca_best_loss = float("inf")
    self.nca_best_params = None

    # Simulation state
    self.nca_sim_step = 0

    # Enter running mode
    self.nca_menu = False
    self.nca_mode = True
    self.nca_phase = "idle"
    self.nca_running = False
    self.nca_training = False
    self.nca_drawing = False
    self.nca_draw_val = 1


def _nca_step(self):
    """Advance NCA simulation by one step."""
    if self.nca_state is None or self.nca_params is None:
        return

    gh = self.nca_grid_h_actual
    gw = self.nca_grid_w_actual

    if self.nca_training:
        # Training step via ES
        self.nca_params, best, mean = _es_step(
            self.nca_params,
            self.nca_target,
            gh, gw,
            pop_size=self.nca_es_pop,
            sigma=self.nca_es_sigma,
            lr=self.nca_es_lr,
            grow_steps=self.nca_grow_steps,
        )
        self.nca_train_gen += 1
        self.nca_loss_history.append(best)
        if best < self.nca_best_loss:
            self.nca_best_loss = best
            self.nca_best_params = list(self.nca_params)

        # After each training step, regrow from seed to show current state
        self.nca_state = _seed_state(gh, gw)
        for _ in range(self.nca_grow_steps):
            self.nca_state = _forward(self.nca_state, self.nca_params,
                                      gh, gw, stochastic_rate=0.5)
        self.nca_sim_step = self.nca_grow_steps

    elif self.nca_running:
        # Just run forward (inference mode)
        self.nca_state = _forward(self.nca_state, self.nca_params,
                                  gh, gw, stochastic_rate=0.5)
        self.nca_sim_step += 1


def _nca_reset_state(self):
    """Reset state to seed, keeping trained weights."""
    if self.nca_params is not None:
        self.nca_state = _seed_state(self.nca_grid_h_actual, self.nca_grid_w_actual)
        self.nca_sim_step = 0


# ── Drawing mode (custom target) ────────────────────────────────────

def _nca_enter_drawing(self):
    """Enter target drawing mode."""
    gh, gw = self.nca_grid_h_actual, self.nca_grid_w_actual
    if self.nca_custom_target is None:
        self.nca_custom_target = _zeros_2d(gh, gw)
    self.nca_drawing = True
    self.nca_draw_cursor_r = gh // 2
    self.nca_draw_cursor_c = gw // 2
    self.nca_target_idx = _PRESET_NAMES.index("custom")


def _nca_draw_toggle(self, r, c):
    """Toggle a cell in the custom target."""
    if self.nca_custom_target is not None:
        gh = len(self.nca_custom_target)
        gw = len(self.nca_custom_target[0]) if gh > 0 else 0
        if 0 <= r < gh and 0 <= c < gw:
            self.nca_custom_target[r][c] = float(self.nca_draw_val)


# ── Key Handling ─────────────────────────────────────────────────────

def _handle_nca_menu_key(self, key):
    """Handle input in the NCA settings menu."""
    if key == 27:  # ESC
        self.nca_menu = False
        return True
    if key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
        if self.nca_menu_sel == 7:  # Start
            _nca_init(self)
            return True
    if key == curses.KEY_UP:
        self.nca_menu_sel = max(0, self.nca_menu_sel - 1)
        return True
    if key == curses.KEY_DOWN:
        self.nca_menu_sel = min(7, self.nca_menu_sel + 1)
        return True
    if key in (curses.KEY_LEFT, curses.KEY_RIGHT):
        d = 1 if key == curses.KEY_RIGHT else -1
        sel = self.nca_menu_sel
        if sel == 0:  # Target pattern
            self.nca_target_idx = (self.nca_target_idx + d) % len(_PRESET_NAMES)
        elif sel == 1:  # Grid height
            self.nca_grid_h = max(8, min(50, self.nca_grid_h + d * 2))
        elif sel == 2:  # Grid width
            self.nca_grid_w = max(8, min(60, self.nca_grid_w + d * 2))
        elif sel == 3:  # Grow steps
            self.nca_grow_steps = max(5, min(100, self.nca_grow_steps + d * 5))
        elif sel == 4:  # ES population
            self.nca_es_pop = max(4, min(32, self.nca_es_pop + d * 2))
        elif sel == 5:  # Learning rate
            lr_vals = [0.001, 0.003, 0.01, 0.03, 0.05, 0.1, 0.2]
            try:
                idx = min(range(len(lr_vals)), key=lambda i: abs(lr_vals[i] - self.nca_es_lr))
            except ValueError:
                idx = 3
            idx = max(0, min(len(lr_vals) - 1, idx + d))
            self.nca_es_lr = lr_vals[idx]
        elif sel == 6:  # Sigma
            sig_vals = [0.005, 0.01, 0.02, 0.05, 0.1]
            try:
                idx = min(range(len(sig_vals)), key=lambda i: abs(sig_vals[i] - self.nca_es_sigma))
            except ValueError:
                idx = 2
            idx = max(0, min(len(sig_vals) - 1, idx + d))
            self.nca_es_sigma = sig_vals[idx]
        return True
    return True


def _handle_nca_key(self, key):
    """Handle input in the NCA running mode."""
    if key == 27:  # ESC
        self.nca_training = False
        self.nca_running = False
        self.nca_drawing = False
        self.nca_mode = False
        return True

    # Drawing mode keys
    if self.nca_drawing:
        if key in (ord('q'), ord('\n'), ord('\r'), curses.KEY_ENTER):
            self.nca_target = _copy_2d(self.nca_custom_target)
            self.nca_drawing = False
            self._flash("Custom target set — press 't' to train")
            return True
        if key == curses.KEY_UP:
            self.nca_draw_cursor_r = max(0, self.nca_draw_cursor_r - 1)
        elif key == curses.KEY_DOWN:
            self.nca_draw_cursor_r = min(self.nca_grid_h_actual - 1, self.nca_draw_cursor_r + 1)
        elif key == curses.KEY_LEFT:
            self.nca_draw_cursor_c = max(0, self.nca_draw_cursor_c - 1)
        elif key == curses.KEY_RIGHT:
            self.nca_draw_cursor_c = min(self.nca_grid_w_actual - 1, self.nca_draw_cursor_c + 1)
        elif key == ord(' '):
            _nca_draw_toggle(self, self.nca_draw_cursor_r, self.nca_draw_cursor_c)
        elif key == ord('e'):
            self.nca_draw_val = 0 if self.nca_draw_val == 1 else 1
        elif key == ord('c'):
            self.nca_custom_target = _zeros_2d(self.nca_grid_h_actual, self.nca_grid_w_actual)
        elif key == ord('f'):
            cr, cc = self.nca_draw_cursor_r, self.nca_draw_cursor_c
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    _nca_draw_toggle(self, cr + dr, cc + dc)
        return True

    # Normal mode keys
    if key == ord('t'):
        self.nca_training = not self.nca_training
        self.nca_running = False
        if self.nca_training:
            self._flash("Training started — ES optimizing neural weights")
        else:
            self._flash("Training paused")
        return True

    if key == ord(' '):
        if self.nca_training:
            self.nca_training = False
        self.nca_running = not self.nca_running
        return True

    if key == ord('r'):
        _nca_reset_state(self)
        self._flash("State reset to seed")
        return True

    if key == ord('R'):
        _nca_init(self)
        self._flash("Full reset — new random weights")
        return True

    if key == ord('d'):
        _nca_enter_drawing(self)
        self._flash("Draw target: arrows=move, space=toggle, f=brush, e=toggle erase, Enter=done")
        return True

    if key == ord('s'):
        self.nca_training = False
        self.nca_running = False
        if self.nca_state is not None and self.nca_params is not None:
            self.nca_state = _forward(self.nca_state, self.nca_params,
                                      self.nca_grid_h_actual, self.nca_grid_w_actual,
                                      stochastic_rate=0.5)
            self.nca_sim_step += 1
        return True

    if key == ord('b'):
        if self.nca_best_params is not None:
            self.nca_params = list(self.nca_best_params)
            _nca_reset_state(self)
            self._flash(f"Loaded best params (loss={self.nca_best_loss:.4f})")
        return True

    if key == ord('g'):
        _nca_reset_state(self)
        if self.nca_params is not None:
            gh = self.nca_grid_h_actual
            gw = self.nca_grid_w_actual
            for _ in range(self.nca_grow_steps):
                self.nca_state = _forward(self.nca_state, self.nca_params,
                                          gh, gw, stochastic_rate=0.5)
            self.nca_sim_step = self.nca_grow_steps
        self._flash(f"Grew {self.nca_grow_steps} steps from seed")
        return True

    if key == ord('p'):
        self.nca_target_idx = (self.nca_target_idx + 1) % len(_PRESET_NAMES)
        preset = _PRESET_NAMES[self.nca_target_idx]
        if preset != "custom":
            self.nca_target = _make_target(preset, self.nca_grid_h_actual,
                                           self.nca_grid_w_actual)
        elif self.nca_custom_target is not None:
            self.nca_target = _copy_2d(self.nca_custom_target)
        self._flash(f"Target: {preset}")
        return True

    if key == ord('v'):
        self.nca_view = (self.nca_view + 1) % 3
        views = ["NCA state", "Target", "Side-by-side"]
        self._flash(f"View: {views[self.nca_view]}")
        return True

    if key in (ord('+'), ord('=')):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        return True
    if key in (ord('-'), ord('_')):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        return True

    return True


# ── Drawing / Rendering ─────────────────────────────────────────────

def _render_grid_2d(stdscr, data, h, w, y_off, x_off, max_y, max_x, color_pair_fn=None):
    """Render a 2D float list [0,1] as density blocks."""
    for r in range(h):
        sy = y_off + r
        if sy < 0 or sy >= max_y - 1:
            continue
        for c in range(w):
            sx = x_off + c * 2
            if sx < 0 or sx + 1 >= max_x:
                continue
            v = data[r][c]
            di = int(v * (len(_DENSITY) - 1))
            di = max(0, min(len(_DENSITY) - 1, di))
            ch = _DENSITY[di]
            try:
                if color_pair_fn and di > 0:
                    stdscr.addstr(sy, sx, ch, color_pair_fn(v))
                else:
                    stdscr.addstr(sy, sx, ch)
            except curses.error:
                pass


def _draw_nca_menu(self, max_y, max_x):
    """Draw NCA settings menu."""
    self.stdscr.erase()
    title = "═══ Neural Cellular Automata ═══"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.A_BOLD)
    except curses.error:
        pass

    desc_lines = [
        "Per-cell neural networks learn to self-organize into target patterns.",
        "Cells perceive neighbors via convolution, then update via a small NN.",
        "Training uses Evolution Strategies (gradient-free optimization).",
    ]
    for i, line in enumerate(desc_lines):
        try:
            self.stdscr.addstr(3 + i, max(0, (max_x - len(line)) // 2), line)
        except curses.error:
            pass

    items = [
        ("Target Pattern", _PRESET_NAMES[self.nca_target_idx]),
        ("Grid Height", str(self.nca_grid_h)),
        ("Grid Width", str(self.nca_grid_w)),
        ("Grow Steps", str(self.nca_grow_steps)),
        ("ES Population", str(self.nca_es_pop)),
        ("Learning Rate", f"{self.nca_es_lr:.3f}"),
        ("Sigma (noise)", f"{self.nca_es_sigma:.3f}"),
        (">>> START <<<", ""),
    ]

    y0 = 7
    for i, (label, val) in enumerate(items):
        y = y0 + i
        if y >= max_y - 2:
            break
        attr = curses.A_REVERSE if i == self.nca_menu_sel else 0
        line = f"  {label}: {val}  " if val else f"  {label}  "
        try:
            self.stdscr.addstr(y, max(0, (max_x - len(line)) // 2), line, attr)
        except curses.error:
            pass

    help_lines = [
        "↑↓ select  ←→ adjust  Enter start  Esc back",
        f"Network: {_param_count()} parameters  ({_NCA_CHANNELS}ch, {_HIDDEN_DIM}h)",
    ]
    for i, line in enumerate(help_lines):
        y = y0 + len(items) + 1 + i
        if y < max_y - 1:
            try:
                self.stdscr.addstr(y, max(0, (max_x - len(line)) // 2), line,
                                   curses.A_DIM)
            except curses.error:
                pass


def _draw_nca(self, max_y, max_x):
    """Draw NCA running view."""
    self.stdscr.erase()

    state = self.nca_state
    target = self.nca_target
    if state is None or target is None:
        return

    gh = len(state)
    gw = len(state[0]) if gh > 0 else 0

    # Extract alive channel as 2D grid
    alive = [[state[r][c][0] for c in range(gw)] for r in range(gh)]

    # Color helper
    def color_fn(v):
        if not getattr(self, 'colors_enabled', True):
            return curses.A_NORMAL
        if v > 0.7:
            return curses.color_pair(3) | curses.A_BOLD
        elif v > 0.3:
            return curses.color_pair(2)
        else:
            return curses.color_pair(4)

    def target_color_fn(v):
        if not getattr(self, 'colors_enabled', True):
            return curses.A_NORMAL
        return curses.color_pair(1)

    # Drawing mode
    if self.nca_drawing:
        title = "── Draw Target ──"
        try:
            self.stdscr.addstr(0, max(0, (max_x - len(title)) // 2), title,
                               curses.A_BOLD)
        except curses.error:
            pass

        y_off = 1
        if self.nca_custom_target is not None:
            ct_h = len(self.nca_custom_target)
            ct_w = len(self.nca_custom_target[0]) if ct_h > 0 else 0
            _render_grid_2d(self.stdscr, self.nca_custom_target, ct_h, ct_w,
                            y_off, 0, max_y, max_x, target_color_fn)
            # Draw cursor
            cr, cc = self.nca_draw_cursor_r, self.nca_draw_cursor_c
            sy, sx = y_off + cr, cc * 2
            cursor_ch = "▓▓" if self.nca_draw_val == 1 else "░░"
            try:
                self.stdscr.addstr(sy, sx, cursor_ch,
                                   curses.A_BLINK | curses.A_REVERSE)
            except curses.error:
                pass

        mode_str = "DRAW" if self.nca_draw_val == 1 else "ERASE"
        help_str = f"Mode: {mode_str}  ←→↑↓=move  Space=toggle  f=brush  e=swap  c=clear  Enter=done"
        try:
            self.stdscr.addstr(max_y - 1, 0, help_str[:max_x - 1], curses.A_DIM)
        except curses.error:
            pass
        return

    # Header
    preset = _PRESET_NAMES[self.nca_target_idx]
    if self.nca_training:
        phase = "training"
    elif self.nca_running:
        phase = "running"
    else:
        phase = "paused"

    header = f" NCA | {preset} | step {self.nca_sim_step} | gen {self.nca_train_gen} | {phase} "
    try:
        self.stdscr.addstr(0, 0, header[:max_x - 1], curses.A_BOLD)
    except curses.error:
        pass

    # Determine layout
    view = self.nca_view
    y_off = 1
    loss = _compute_loss(state, target, gh, gw)

    if view == 0:
        _render_grid_2d(self.stdscr, alive, gh, gw, y_off, 0, max_y, max_x, color_fn)
    elif view == 1:
        th = len(target)
        tw = len(target[0]) if th > 0 else 0
        _render_grid_2d(self.stdscr, target, th, tw, y_off, 0, max_y, max_x, target_color_fn)
    else:
        # Side by side
        half_w = max_x // 2
        label_nca = "NCA State"
        label_tgt = "Target"
        try:
            self.stdscr.addstr(y_off, max(0, (half_w - len(label_nca)) // 2),
                               label_nca, curses.A_BOLD)
            self.stdscr.addstr(y_off, half_w + max(0, (half_w - len(label_tgt)) // 2),
                               label_tgt, curses.A_BOLD)
        except curses.error:
            pass
        _render_grid_2d(self.stdscr, alive, gh, gw, y_off + 1, 0, max_y, max_x, color_fn)
        th = len(target)
        tw = len(target[0]) if th > 0 else 0
        _render_grid_2d(self.stdscr, target, th, tw, y_off + 1, half_w,
                        max_y, max_x, target_color_fn)

    # Loss & training info bar
    info_y = min(y_off + gh + 1, max_y - 3)
    loss_str = f"Loss: {loss:.4f}"
    if self.nca_best_loss < float("inf"):
        loss_str += f"  Best: {self.nca_best_loss:.4f}"
    loss_str += f"  Params: {_param_count()}"
    try:
        self.stdscr.addstr(info_y, 0, loss_str[:max_x - 1])
    except curses.error:
        pass

    # Loss sparkline
    if self.nca_loss_history:
        from life.analytics import _sparkline
        spark_w = min(40, max_x - 12)
        spark = _sparkline(self.nca_loss_history, spark_w)
        spark_str = f"Loss: {spark}"
        try:
            self.stdscr.addstr(info_y + 1, 0, spark_str[:max_x - 1], curses.A_DIM)
        except curses.error:
            pass

    # Help bar
    help_str = "t=train  Space=run  s=step  r=reset  R=reinit  d=draw  g=grow  b=best  p=preset  v=view  Esc=exit"
    try:
        self.stdscr.addstr(max_y - 1, 0, help_str[:max_x - 1], curses.A_DIM)
    except curses.error:
        pass


# ── Registration ─────────────────────────────────────────────────────

def register(App):
    """Register Neural CA methods on the App class."""
    App._enter_nca_mode = _enter_nca_mode
    App._exit_nca_mode = _exit_nca_mode
    App._nca_init = _nca_init
    App._nca_step = _nca_step
    App._nca_reset_state = _nca_reset_state
    App._nca_enter_drawing = _nca_enter_drawing
    App._nca_draw_toggle = _nca_draw_toggle
    App._handle_nca_menu_key = _handle_nca_menu_key
    App._handle_nca_key = _handle_nca_key
    App._draw_nca_menu = _draw_nca_menu
    App._draw_nca = _draw_nca
