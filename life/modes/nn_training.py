"""Neural Network Training Visualizer — watch a small neural network learn in real time.

ASCII visualization of forward pass, backprop, weight updates, decision boundary,
and loss landscape navigation.  Tasks: XOR, spiral, circle, two-moons.

Presets:
  1. XOR Gate              — 2-2-1 network learns exclusive-or
  2. Spiral Classification — 2-8-8-3 separates interleaved spirals
  3. Circle Decision       — 2-4-1 inside vs outside circle
  4. Two Moons             — 2-6-4-1 separates crescent-shaped clusters
  5. Sine Curve Regression — 2-8-4-1 learns sin(x) function fitting
  6. Gaussian Clusters     — 2-8-4-3 multi-class Gaussian blobs
"""
import curses
import math
import random

# ── Presets ──────────────────────────────────────────────────────────────
NNTRAIN_PRESETS = [
    ("XOR Gate", "2-2-1 learns exclusive-or",
     {"layers": [2, 2, 1], "task": "xor", "lr": 1.0, "n_samples": 4,
      "activation": "sigmoid", "epochs_per_step": 5}),
    ("Spiral Classification", "2-8-8-3 separates interleaved spirals",
     {"layers": [2, 8, 8, 3], "task": "spiral", "lr": 0.3, "n_samples": 150,
      "activation": "relu", "epochs_per_step": 2}),
    ("Circle Decision", "2-4-1 inside vs outside circle",
     {"layers": [2, 4, 1], "task": "circle", "lr": 0.5, "n_samples": 80,
      "activation": "sigmoid", "epochs_per_step": 3}),
    ("Two Moons", "2-6-4-1 separates crescent-shaped clusters",
     {"layers": [2, 6, 4, 1], "task": "moons", "lr": 0.4, "n_samples": 120,
      "activation": "relu", "epochs_per_step": 2}),
    ("Sine Regression", "2-8-4-1 learns sin(x) curve fitting",
     {"layers": [2, 8, 4, 1], "task": "sine", "lr": 0.1, "n_samples": 60,
      "activation": "relu", "epochs_per_step": 3}),
    ("Gaussian Clusters", "2-8-4-3 multi-class Gaussian blobs",
     {"layers": [2, 8, 4, 3], "task": "gaussian", "lr": 0.25, "n_samples": 120,
      "activation": "relu", "epochs_per_step": 2}),
]

# ── Activation functions ────────────────────────────────────────────────

def _sigmoid(x):
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))

def _sigmoid_deriv(out):
    return out * (1.0 - out)

def _relu(x):
    return max(0.0, x)

def _relu_deriv(out):
    return 1.0 if out > 0.0 else 0.0

def _tanh_act(x):
    return math.tanh(max(-500.0, min(500.0, x)))

def _tanh_deriv(out):
    return 1.0 - out * out

_ACT = {
    "sigmoid": (_sigmoid, _sigmoid_deriv),
    "relu": (_relu, _relu_deriv),
    "tanh": (_tanh_act, _tanh_deriv),
}

# ── Data generators ─────────────────────────────────────────────────────

def _gen_xor(n):
    pts = [(0.0, 0.0, 0.0), (0.0, 1.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 0.0)]
    data = []
    for _ in range(n):
        x1, x2, y = random.choice(pts)
        data.append((x1 + random.gauss(0, 0.05), x2 + random.gauss(0, 0.05), [y]))
    return data

def _gen_spiral(n):
    data = []
    per_class = n // 3
    for c in range(3):
        for i in range(per_class):
            r = i / per_class * 5.0
            t = 1.75 * i / per_class * 2 * math.pi + (2 * math.pi / 3) * c
            x = r * math.sin(t) + random.gauss(0, 0.3)
            y = r * math.cos(t) + random.gauss(0, 0.3)
            label = [0.0, 0.0, 0.0]
            label[c] = 1.0
            data.append((x / 6.0 + 0.5, y / 6.0 + 0.5, label))
    return data

def _gen_circle(n):
    data = []
    for _ in range(n):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        inside = 1.0 if x * x + y * y < 0.5 else 0.0
        data.append((x * 0.5 + 0.5, y * 0.5 + 0.5, [inside]))
    return data

def _gen_moons(n):
    data = []
    half = n // 2
    for i in range(half):
        angle = math.pi * i / half
        x = math.cos(angle) + random.gauss(0, 0.1)
        y = math.sin(angle) + random.gauss(0, 0.1)
        data.append((x * 0.25 + 0.5, y * 0.25 + 0.4, [0.0]))
    for i in range(half):
        angle = math.pi * i / half
        x = 1.0 - math.cos(angle) + random.gauss(0, 0.1)
        y = 1.0 - math.sin(angle) - 0.5 + random.gauss(0, 0.1)
        data.append((x * 0.25 + 0.25, y * 0.25 + 0.5, [1.0]))
    return data

def _gen_sine(n):
    data = []
    for _ in range(n):
        x = random.uniform(0, 1)
        y = math.sin(x * 2 * math.pi) * 0.4 + 0.5 + random.gauss(0, 0.05)
        data.append((x, 0.5, [y]))
    return data

def _gen_gaussian(n):
    centers = [(0.3, 0.3), (0.7, 0.3), (0.5, 0.75)]
    data = []
    per_class = n // 3
    for c, (cx, cy) in enumerate(centers):
        for _ in range(per_class):
            x = cx + random.gauss(0, 0.08)
            y = cy + random.gauss(0, 0.08)
            label = [0.0, 0.0, 0.0]
            label[c] = 1.0
            data.append((x, y, label))
    return data

_GEN = {
    "xor": _gen_xor, "spiral": _gen_spiral, "circle": _gen_circle,
    "moons": _gen_moons, "sine": _gen_sine, "gaussian": _gen_gaussian,
}

# ── Softmax ─────────────────────────────────────────────────────────────

def _softmax(vals):
    mx = max(vals)
    exps = [math.exp(v - mx) for v in vals]
    s = sum(exps)
    return [e / s for e in exps]

# ── Tiny neural network (pure Python, no deps) ─────────────────────────

class _MiniNet:
    """Minimal feed-forward network with backprop."""

    def __init__(self, layer_sizes, act_name="sigmoid", lr=0.5):
        self.sizes = layer_sizes
        self.n_layers = len(layer_sizes)
        act_fn, act_d = _ACT.get(act_name, _ACT["sigmoid"])
        self.act = act_fn
        self.act_d = act_d
        self.lr = lr
        self.multi_class = layer_sizes[-1] > 1
        # Xavier init
        self.weights = []  # weights[l][j][i]
        self.biases = []   # biases[l][j]
        for l in range(1, self.n_layers):
            fan_in = layer_sizes[l - 1]
            fan_out = layer_sizes[l]
            scale = math.sqrt(2.0 / (fan_in + fan_out))
            w = [[random.gauss(0, scale) for _ in range(fan_in)] for _ in range(fan_out)]
            b = [0.0] * fan_out
            self.weights.append(w)
            self.biases.append(b)
        # For visualization: store recent gradient magnitudes
        self.grad_mag = []  # same shape as weights, stores |dw|
        for l in range(len(self.weights)):
            self.grad_mag.append([[0.0] * len(self.weights[l][0])
                                  for _ in range(len(self.weights[l]))])
        self.activations = []  # last forward pass activations per layer
        self.loss_history = []
        self.acc_history = []

    def forward(self, x):
        """Forward pass, returns output and stores activations."""
        self.activations = [list(x)]
        a = list(x)
        for l in range(len(self.weights)):
            is_last = (l == len(self.weights) - 1)
            new_a = []
            for j in range(len(self.weights[l])):
                z = self.biases[l][j]
                for i in range(len(a)):
                    z += self.weights[l][j][i] * a[i]
                if is_last and self.multi_class:
                    new_a.append(z)  # raw logits for softmax
                else:
                    new_a.append(self.act(z))
            if is_last and self.multi_class:
                new_a = _softmax(new_a)
            a = new_a
            self.activations.append(list(a))
        return a

    def backward(self, target):
        """Backprop from last forward pass. Returns loss."""
        n_l = len(self.weights)
        deltas = [None] * n_l
        out = self.activations[-1]
        # Output deltas
        if self.multi_class:
            # Cross-entropy derivative with softmax: delta = out - target
            deltas[-1] = [out[j] - target[j] for j in range(len(out))]
            loss = 0.0
            for j in range(len(out)):
                loss -= target[j] * math.log(max(out[j], 1e-15))
        else:
            deltas[-1] = [(out[j] - target[j]) * self.act_d(out[j])
                          for j in range(len(out))]
            loss = sum((out[j] - target[j]) ** 2 for j in range(len(out))) * 0.5
        # Hidden deltas
        for l in range(n_l - 2, -1, -1):
            d = []
            for i in range(len(self.weights[l])):
                err = 0.0
                for j in range(len(self.weights[l + 1])):
                    err += self.weights[l + 1][j][i] * deltas[l + 1][j]
                d.append(err * self.act_d(self.activations[l + 1][i]))
            deltas[l] = d
        # Update weights & record gradient magnitudes
        for l in range(n_l):
            a_prev = self.activations[l]
            for j in range(len(self.weights[l])):
                for i in range(len(self.weights[l][j])):
                    grad = deltas[l][j] * a_prev[i]
                    self.grad_mag[l][j][i] = abs(grad)
                    self.weights[l][j][i] -= self.lr * grad
                self.biases[l][j] -= self.lr * deltas[l][j]
        return loss

    def train_batch(self, data):
        """Train on entire dataset, returns (avg_loss, accuracy)."""
        total_loss = 0.0
        correct = 0
        for x1, x2, target in data:
            out = self.forward([x1, x2])
            total_loss += self.backward(target)
            if self.multi_class:
                pred = out.index(max(out))
                true = target.index(max(target))
                if pred == true:
                    correct += 1
            else:
                pred_v = 1.0 if out[0] > 0.5 else 0.0
                if abs(pred_v - target[0]) < 0.5:
                    correct += 1
        avg_loss = total_loss / len(data)
        acc = correct / len(data)
        self.loss_history.append(avg_loss)
        self.acc_history.append(acc)
        return avg_loss, acc


# ── Mode functions ──────────────────────────────────────────────────────

def _enter_nntrain_mode(self):
    """Enter Neural Network Training Visualizer — show preset menu."""
    self.nntrain_menu = True
    self.nntrain_menu_sel = 0
    self._flash("Neural Network Training Visualizer — select a scenario")


def _exit_nntrain_mode(self):
    """Exit Neural Network Training Visualizer."""
    self.nntrain_mode = False
    self.nntrain_menu = False
    self.nntrain_running = False
    self.nntrain_net = None
    self.nntrain_data = None
    self._flash("Neural Network Training OFF")


def _nntrain_init(self, preset_idx: int):
    name, _desc, cfg = NNTRAIN_PRESETS[preset_idx]
    max_y, max_x = self.stdscr.getmaxyx()
    self.nntrain_menu = False
    self.nntrain_running = True
    self.nntrain_preset_name = name
    self.nntrain_generation = 0
    self.nntrain_epoch = 0
    self.nntrain_max_y = max_y
    self.nntrain_max_x = max_x
    self.nntrain_cfg = dict(cfg)
    self.nntrain_epochs_per_step = cfg["epochs_per_step"]
    self.nntrain_view = 0  # 0=all, 1=network, 2=boundary, 3=loss
    self.nntrain_speed = 1
    self.nntrain_paused = False

    # Build network
    self.nntrain_net = _MiniNet(cfg["layers"], cfg["activation"], cfg["lr"])
    # Generate data
    gen = _GEN[cfg["task"]]
    self.nntrain_data = gen(cfg["n_samples"])
    # Pulse timer for gradient flow animation
    self.nntrain_pulse_phase = 0.0


def _nntrain_step(self):
    """Advance training by configured epochs per step."""
    if self.nntrain_paused:
        return
    net = self.nntrain_net
    data = self.nntrain_data
    for _ in range(self.nntrain_epochs_per_step * self.nntrain_speed):
        net.train_batch(data)
        self.nntrain_epoch += 1
    self.nntrain_generation += 1
    self.nntrain_pulse_phase += 0.3


def _handle_nntrain_menu_key(self, key):
    n = len(NNTRAIN_PRESETS)
    if key == curses.KEY_DOWN:
        self.nntrain_menu_sel = (self.nntrain_menu_sel + 1) % n
        return True
    if key == curses.KEY_UP:
        self.nntrain_menu_sel = (self.nntrain_menu_sel - 1) % n
        return True
    if key in (curses.KEY_ENTER, 10, 13):
        self.nntrain_menu = False
        self.nntrain_mode = True
        _nntrain_init(self, self.nntrain_menu_sel)
        return True
    if key in (27, ord('q')):
        _exit_nntrain_mode(self)
        return True
    return True


def _handle_nntrain_key(self, key):
    if key == ord(' '):
        self.nntrain_paused = not self.nntrain_paused
        self._flash("PAUSED" if self.nntrain_paused else "RUNNING")
        return True
    if key == ord('n'):
        # Single step
        was = self.nntrain_paused
        self.nntrain_paused = False
        _nntrain_step(self)
        self.nntrain_paused = was
        return True
    if key == ord('v'):
        self.nntrain_view = (self.nntrain_view + 1) % 4
        labels = ["All Panels", "Network Only", "Decision Boundary", "Loss Curve"]
        self._flash(f"View: {labels[self.nntrain_view]}")
        return True
    if key == ord('+') or key == ord('='):
        self.nntrain_speed = min(20, self.nntrain_speed + 1)
        self._flash(f"Speed x{self.nntrain_speed}")
        return True
    if key == ord('-'):
        self.nntrain_speed = max(1, self.nntrain_speed - 1)
        self._flash(f"Speed x{self.nntrain_speed}")
        return True
    if key == ord('['):
        net = self.nntrain_net
        net.lr = max(0.001, net.lr * 0.8)
        self._flash(f"LR: {net.lr:.4f}")
        return True
    if key == ord(']'):
        net = self.nntrain_net
        net.lr = min(5.0, net.lr * 1.25)
        self._flash(f"LR: {net.lr:.4f}")
        return True
    if key == ord('r'):
        _nntrain_init(self, self.nntrain_menu_sel)
        self._flash("Reset")
        return True
    if key == ord('R'):
        self.nntrain_menu = True
        self.nntrain_running = False
        return True
    if key in (27, ord('q')):
        _exit_nntrain_mode(self)
        return True
    return True


# ── Drawing helpers ─────────────────────────────────────────────────────

def _act_color(val, bold=False):
    """Map activation 0..1 to color pair."""
    if val < 0.15:
        cp = 10  # deep blue (cold)
    elif val < 0.3:
        cp = 13  # cyan
    elif val < 0.5:
        cp = 1   # green
    elif val < 0.7:
        cp = 3   # yellow
    elif val < 0.85:
        cp = 5   # red
    else:
        cp = 17  # white-hot
    attr = curses.color_pair(cp)
    if bold:
        attr |= curses.A_BOLD
    return attr


def _weight_char(mag):
    """Weight magnitude to connection character."""
    if mag < 0.1:
        return '·'
    if mag < 0.3:
        return '─'
    if mag < 0.6:
        return '━'
    if mag < 1.0:
        return '═'
    return '█'


def _gradient_char(grad_mag, phase):
    """Gradient flow animation character."""
    pulse = (math.sin(phase + grad_mag * 10) + 1) / 2
    if grad_mag < 0.001:
        return ' '
    if pulse > 0.7 and grad_mag > 0.01:
        return '»'
    if grad_mag < 0.01:
        return '·'
    if grad_mag < 0.05:
        return '~'
    return '≈'


def _draw_network(scr, net, y0, x0, h, w, phase):
    """Draw the network architecture with neurons and connections."""
    if h < 6 or w < 20:
        return
    n_layers = len(net.sizes)
    layer_spacing = max(1, (w - 4) // max(1, n_layers - 1))

    # Compute neuron positions
    positions = []  # positions[layer] = list of (row, col)
    for l in range(n_layers):
        n_neurons = net.sizes[l]
        lx = x0 + 2 + l * layer_spacing
        available_h = h - 2
        neuron_spacing = max(1, available_h // max(1, n_neurons + 1))
        pos = []
        for n in range(n_neurons):
            ny = y0 + 1 + (n + 1) * neuron_spacing
            ny = min(ny, y0 + h - 2)
            pos.append((ny, lx))
        positions.append(pos)

    # Draw connections with weight magnitude and gradient pulse
    for l in range(len(net.weights)):
        for j in range(len(net.weights[l])):
            for i in range(len(net.weights[l][j])):
                if j >= len(positions[l + 1]) or i >= len(positions[l]):
                    continue
                r1, c1 = positions[l][i]
                r2, c2 = positions[l + 1][j]
                w_val = net.weights[l][j][i]
                g_val = net.grad_mag[l][j][i]
                w_abs = min(abs(w_val), 2.0) / 2.0

                # Color by weight sign: green=positive, red=negative
                if w_val >= 0:
                    cp = curses.color_pair(1)  # green
                else:
                    cp = curses.color_pair(5)  # red

                # Brightness by magnitude
                if w_abs > 0.5:
                    cp |= curses.A_BOLD

                # Draw a simple line between neurons
                steps = max(abs(c2 - c1), abs(r2 - r1), 1)
                for s in range(1, steps):
                    t = s / steps
                    cr = int(r1 + (r2 - r1) * t)
                    cc = int(c1 + (c2 - c1) * t)
                    if y0 <= cr < y0 + h and x0 <= cc < x0 + w:
                        # Gradient pulse
                        pulse = (math.sin(phase * 3 + t * 6.28 + g_val * 20) + 1) / 2
                        ch = _weight_char(w_abs)
                        if g_val > 0.01 and pulse > 0.6:
                            ch = '»' if w_val > 0 else '«'
                            cp |= curses.A_BOLD
                        try:
                            scr.addstr(cr, cc, ch, cp)
                        except curses.error:
                            pass

    # Draw neurons
    acts = net.activations if net.activations else None
    for l in range(n_layers):
        for n, (ny, nx) in enumerate(positions[l]):
            if ny >= y0 + h or nx >= x0 + w - 1:
                continue
            if acts and l < len(acts) and n < len(acts[l]):
                val = max(0.0, min(1.0, acts[l][n]))
                attr = _act_color(val, bold=True)
                # Neuron representation based on activation
                if val < 0.2:
                    ch = '○'
                elif val < 0.5:
                    ch = '◐'
                elif val < 0.8:
                    ch = '◑'
                else:
                    ch = '●'
            else:
                ch = '○'
                attr = curses.color_pair(6)
            try:
                scr.addstr(ny, nx, ch, attr)
            except curses.error:
                pass

    # Layer labels
    labels = ["In"] + [f"H{l}" for l in range(1, n_layers - 1)] + ["Out"]
    for l in range(n_layers):
        if positions[l]:
            _, lx = positions[l][0]
            ly = y0
            if lx < x0 + w - 3 and ly >= 0:
                try:
                    scr.addstr(ly, lx, labels[l][:3],
                               curses.color_pair(7) | curses.A_BOLD)
                except curses.error:
                    pass


def _draw_decision_boundary(scr, net, data, y0, x0, h, w):
    """Draw the decision boundary as a 2D heatmap."""
    if h < 4 or w < 8:
        return
    res_y = h - 2
    res_x = (w - 2) // 2  # 2 chars per cell for aspect ratio

    boundary_chars = ' ░▒▓█'

    for gy in range(res_y):
        for gx in range(res_x):
            px = gx / max(1, res_x - 1)
            py = gy / max(1, res_y - 1)
            out = net.forward([px, py])
            if len(out) == 1:
                val = max(0.0, min(1.0, out[0]))
                ci = int(val * (len(boundary_chars) - 1))
                ch = boundary_chars[ci]
                attr = _act_color(val)
            else:
                # Multi-class: color by argmax, intensity by confidence
                mx = max(out)
                cls = out.index(mx)
                colors = [1, 5, 3, 13, 4]  # green, red, yellow, cyan, magenta
                cp = colors[cls % len(colors)]
                ci = int(mx * (len(boundary_chars) - 1))
                ch = boundary_chars[ci]
                attr = curses.color_pair(cp)
                if mx > 0.7:
                    attr |= curses.A_BOLD

            sy = y0 + 1 + gy
            sx = x0 + 1 + gx * 2
            if sy < y0 + h and sx < x0 + w - 1:
                try:
                    scr.addstr(sy, sx, ch * 2, attr)
                except curses.error:
                    pass

    # Overlay data points
    for x1, x2, target in data:
        dx = int(x1 * (res_x - 1))
        dy = int(x2 * (res_y - 1))
        sy = y0 + 1 + dy
        sx = x0 + 1 + dx * 2
        if y0 + 1 <= sy < y0 + h - 1 and x0 + 1 <= sx < x0 + w - 2:
            if len(target) == 1:
                ch = '+' if target[0] > 0.5 else 'x'
                attr = curses.color_pair(17) | curses.A_BOLD
            else:
                cls = target.index(max(target))
                markers = '+x*oA'
                ch = markers[cls % len(markers)]
                attr = curses.color_pair(17) | curses.A_BOLD
            try:
                scr.addstr(sy, sx, ch, attr)
            except curses.error:
                pass

    # Border
    try:
        scr.addstr(y0, x0 + 2, " Decision Boundary ",
                   curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass


def _draw_loss_curve(scr, net, y0, x0, h, w):
    """Draw loss and accuracy history as ASCII sparkline charts."""
    if h < 4 or w < 10:
        return
    try:
        scr.addstr(y0, x0 + 2, " Loss & Accuracy ",
                   curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    chart_h = (h - 3) // 2
    chart_w = w - 4

    # Loss curve
    loss_hist = net.loss_history[-chart_w:] if net.loss_history else []
    if loss_hist:
        mn = min(loss_hist)
        mx = max(loss_hist)
        rng = mx - mn if mx > mn else 1.0
        try:
            scr.addstr(y0 + 1, x0 + 1, "Loss",
                       curses.color_pair(5) | curses.A_BOLD)
        except curses.error:
            pass
        bar_chars = '▁▂▃▄▅▆▇█'
        for i, val in enumerate(loss_hist):
            norm = (val - mn) / rng
            ci = int(norm * (len(bar_chars) - 1))
            ch = bar_chars[ci]
            sx = x0 + 2 + i
            sy = y0 + 2 + chart_h - 1
            # Draw column
            col_h = max(1, int(norm * chart_h))
            for dy in range(col_h):
                if sy - dy >= y0 + 2 and sx < x0 + w - 1:
                    # Color: high loss = red, low = green
                    if norm > 0.7:
                        cp = curses.color_pair(5)
                    elif norm > 0.3:
                        cp = curses.color_pair(3)
                    else:
                        cp = curses.color_pair(1)
                    try:
                        scr.addstr(sy - dy, sx, ch, cp)
                    except curses.error:
                        pass

    # Accuracy curve
    acc_hist = net.acc_history[-chart_w:] if net.acc_history else []
    if acc_hist:
        acc_y0 = y0 + 3 + chart_h
        try:
            scr.addstr(acc_y0, x0 + 1, "Acc",
                       curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        bar_chars = '▁▂▃▄▅▆▇█'
        for i, val in enumerate(acc_hist):
            ci = int(val * (len(bar_chars) - 1))
            ch = bar_chars[ci]
            sx = x0 + 2 + i
            sy = acc_y0 + chart_h
            col_h = max(1, int(val * chart_h))
            for dy in range(col_h):
                if sy - dy >= acc_y0 + 1 and sx < x0 + w - 1:
                    if val > 0.9:
                        cp = curses.color_pair(1) | curses.A_BOLD
                    elif val > 0.6:
                        cp = curses.color_pair(13)
                    else:
                        cp = curses.color_pair(3)
                    try:
                        scr.addstr(sy - dy, sx, ch, cp)
                    except curses.error:
                        pass


def _draw_nntrain_menu(self, max_y, max_x):
    """Render the preset selection menu."""
    scr = self.stdscr
    title = "═══ Neural Network Training Visualizer ═══"
    try:
        scr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                   curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Watch a neural network learn in real time"
    try:
        scr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                   curses.color_pair(6))
    except curses.error:
        pass

    y = 4
    for i, (name, desc, _cfg) in enumerate(NNTRAIN_PRESETS):
        sel = (i == self.nntrain_menu_sel)
        marker = "▶ " if sel else "  "
        attr = curses.color_pair(7) | curses.A_BOLD if sel else curses.color_pair(6)
        line = f"{marker}{name}"
        if y < max_y - 2:
            try:
                scr.addstr(y, 4, line, attr)
                scr.addstr(y, 30, desc, curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass
        y += 1

    hint = "↑↓ select  Enter confirm  q quit"
    try:
        scr.addstr(max_y - 1, 2, hint, curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


def _draw_nntrain(self, max_y, max_x):
    """Render the neural network training visualization."""
    scr = self.stdscr
    net = self.nntrain_net
    if not net:
        return

    # Run a forward pass on a sample point for display
    if self.nntrain_data:
        sample = self.nntrain_data[self.nntrain_generation % len(self.nntrain_data)]
        net.forward([sample[0], sample[1]])

    phase = self.nntrain_pulse_phase

    # Layout
    view = self.nntrain_view
    usable_h = max_y - 3  # reserve bottom for stats
    usable_w = max_x - 1

    if view == 0:
        # All panels: network top-left, boundary top-right, loss bottom
        net_w = usable_w // 2
        net_h = (usable_h * 2) // 3
        bd_w = usable_w - net_w
        bd_h = net_h
        loss_h = usable_h - net_h
        loss_w = usable_w

        _draw_network(scr, net, 0, 0, net_h, net_w, phase)
        _draw_decision_boundary(scr, net, self.nntrain_data, 0, net_w, bd_h, bd_w)
        _draw_loss_curve(scr, net, net_h, 0, loss_h, loss_w)
    elif view == 1:
        _draw_network(scr, net, 0, 0, usable_h, usable_w, phase)
    elif view == 2:
        _draw_decision_boundary(scr, net, self.nntrain_data,
                                0, 0, usable_h, usable_w)
    elif view == 3:
        _draw_loss_curve(scr, net, 0, 0, usable_h, usable_w)

    # Stats bar
    loss_val = net.loss_history[-1] if net.loss_history else 0.0
    acc_val = net.acc_history[-1] if net.acc_history else 0.0
    arch = "-".join(str(s) for s in net.sizes)

    stats = (f" {self.nntrain_preset_name} │ Arch: {arch} │ "
             f"Epoch: {self.nntrain_epoch} │ Loss: {loss_val:.4f} │ "
             f"Acc: {acc_val:.1%} │ LR: {net.lr:.4f} │ "
             f"Speed: x{self.nntrain_speed} ")

    try:
        scr.addstr(max_y - 2, 0, stats[:max_x - 1],
                   curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    hint = " Space:pause  n:step  v:view  +/-:speed  [/]:LR  r:reset  R:menu  q:exit "
    try:
        scr.addstr(max_y - 1, 0, hint[:max_x - 1],
                   curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ── Registration ────────────────────────────────────────────────────────

def register(App):
    """Register Neural Network Training Visualizer on the App class."""
    App._enter_nntrain_mode = _enter_nntrain_mode
    App._exit_nntrain_mode = _exit_nntrain_mode
    App._nntrain_init = _nntrain_init
    App._nntrain_step = _nntrain_step
    App._handle_nntrain_menu_key = _handle_nntrain_menu_key
    App._handle_nntrain_key = _handle_nntrain_key
    App._draw_nntrain_menu = _draw_nntrain_menu
    App._draw_nntrain = _draw_nntrain
    App.NNTRAIN_PRESETS = NNTRAIN_PRESETS
