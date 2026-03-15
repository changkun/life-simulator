"""Mode: musvis — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_musvis_mode(self):
    """Enter Music Visualizer mode — show preset menu."""
    self.musvis_menu = True
    self.musvis_menu_sel = 0
    self._flash("Music Visualizer — select a visualization")



def _exit_musvis_mode(self):
    """Exit Music Visualizer mode."""
    self.musvis_mode = False
    self.musvis_menu = False
    self.musvis_running = False
    self.musvis_particles = []
    self.musvis_spectrum = []
    self.musvis_waveform = []
    self.musvis_peak_history = []
    self._flash("Music Visualizer OFF")



def _musvis_init(self, preset_idx: int):
    """Initialize music visualizer with chosen preset."""
    name, _desc = self.MUSVIS_PRESETS[preset_idx]
    self.musvis_preset_name = name
    self.musvis_preset_idx = preset_idx
    self.musvis_generation = 0
    self.musvis_time = 0.0
    self.musvis_running = True
    self.musvis_menu = False
    self.musvis_mode = True
    self.musvis_spectrum = [0.0] * self.musvis_num_bars
    self.musvis_waveform = [0.0] * 80
    self.musvis_beat_energy = 0.0
    self.musvis_beat_avg = 0.0
    self.musvis_beat_flash = 0.0
    self.musvis_particles = []
    self.musvis_peak_history = [0.0] * self.musvis_num_bars
    self.musvis_bass_energy = 0.0
    self.musvis_mid_energy = 0.0
    self.musvis_high_energy = 0.0
    self.musvis_tone_phase = 0.0
    # Map preset_idx to view_mode
    view_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
    self.musvis_view_mode = view_map.get(preset_idx, 0)
    self._flash(f"Visualizer: {name} — space=pause, c=color, v=view, +/-=sensitivity")



def _musvis_generate_audio_data(self):
    """Generate synthetic audio data from oscillating tones (simulates microphone input)."""
    t = self.musvis_time
    sens = self.musvis_sensitivity

    # Select tone pattern based on time
    pattern_idx = int(t / 2.0) % len(self.MUSVIS_TONE_PATTERNS)
    pattern = self.MUSVIS_TONE_PATTERNS[pattern_idx]
    note_idx = int(t * 4.0) % len(pattern)
    base_freq = pattern[note_idx]

    # Generate waveform samples
    n_samples = 80
    waveform = []
    for i in range(n_samples):
        sample_t = t + i * 0.001
        val = 0.0
        if base_freq > 0:
            # Fundamental
            val += 0.6 * math.sin(2.0 * math.pi * base_freq * sample_t)
            # Harmonics
            val += 0.25 * math.sin(2.0 * math.pi * base_freq * 2.0 * sample_t)
            val += 0.1 * math.sin(2.0 * math.pi * base_freq * 3.0 * sample_t)
            val += 0.05 * math.sin(2.0 * math.pi * base_freq * 5.0 * sample_t)
        # Add some noise for realism
        val += random.gauss(0, 0.05)
        # Add a slow LFO modulation
        val *= 0.7 + 0.3 * math.sin(2.0 * math.pi * 0.5 * sample_t)
        waveform.append(max(-1.0, min(1.0, val * sens)))

    self.musvis_waveform = waveform

    # Simulate FFT — create spectrum from tone frequencies
    n_bars = self.musvis_num_bars
    spectrum = [0.0] * n_bars
    max_freq = 2000.0

    if base_freq > 0:
        # Place energy at fundamental and harmonics
        for harmonic, amp in [(1, 0.8), (2, 0.4), (3, 0.2), (5, 0.1)]:
            freq = base_freq * harmonic
            bin_idx = int(freq / max_freq * n_bars)
            if 0 <= bin_idx < n_bars:
                # Spread energy across neighboring bins
                for offset in range(-1, 2):
                    bi = bin_idx + offset
                    if 0 <= bi < n_bars:
                        falloff = 1.0 if offset == 0 else 0.4
                        spectrum[bi] += amp * falloff * sens

    # Add some low-frequency rumble
    beat_pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * 2.0 * t)  # 2 Hz beat
    for i in range(min(4, n_bars)):
        spectrum[i] += 0.3 * beat_pulse * sens * (1.0 - i / 4.0)

    # Add subtle noise floor
    for i in range(n_bars):
        spectrum[i] += random.uniform(0, 0.05) * sens
        spectrum[i] = max(0.0, min(1.0, spectrum[i]))

    # Apply peak decay
    for i in range(n_bars):
        self.musvis_peak_history[i] = max(
            spectrum[i],
            self.musvis_peak_history[i] * 0.95  # Slow decay
        )

    self.musvis_spectrum = spectrum

    # Calculate band energies
    third = n_bars // 3
    self.musvis_bass_energy = sum(spectrum[:third]) / max(1, third)
    self.musvis_mid_energy = sum(spectrum[third:2*third]) / max(1, third)
    self.musvis_high_energy = sum(spectrum[2*third:]) / max(1, n_bars - 2*third)

    # Beat detection
    total_energy = sum(spectrum) / n_bars
    self.musvis_beat_avg = self.musvis_beat_avg * 0.9 + total_energy * 0.1
    if total_energy > self.musvis_beat_avg * 1.5 and total_energy > 0.15:
        self.musvis_beat_flash = 1.0
        self.musvis_beat_energy = total_energy
        # Spawn particles on beat
        self._musvis_spawn_particles()
    else:
        self.musvis_beat_flash *= 0.85



def _musvis_spawn_particles(self):
    """Spawn beat-reactive particles."""
    n_new = random.randint(5, 15)
    for _ in range(n_new):
        angle = random.uniform(0, 2.0 * math.pi)
        speed = random.uniform(0.5, 2.5) * (0.5 + self.musvis_beat_energy)
        self.musvis_particles.append({
            "r": 0.0,  # row offset from center
            "c": 0.0,  # col offset from center
            "vr": -math.cos(angle) * speed,
            "vc": math.sin(angle) * speed * 2.0,  # wider for aspect ratio
            "life": 1.0,
            "char": random.choice("*+.oO@#"),
            "color": random.randint(1, 5),
        })



def _musvis_update_particles(self):
    """Update particle positions and lifetimes."""
    alive = []
    for p in self.musvis_particles:
        p["r"] += p["vr"]
        p["c"] += p["vc"]
        p["vr"] *= 0.97  # Friction
        p["vc"] *= 0.97
        p["life"] -= 0.02
        if p["life"] > 0:
            alive.append(p)
    self.musvis_particles = alive[:200]  # Cap particle count



def _musvis_step(self):
    """Advance one frame of the visualizer."""
    self.musvis_time += 0.04
    self.musvis_generation += 1
    self._musvis_generate_audio_data()
    self._musvis_update_particles()



def _handle_musvis_menu_key(self, key: int) -> bool:
    """Handle input in music visualizer preset menu."""
    n = len(self.MUSVIS_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.musvis_menu_sel = (self.musvis_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.musvis_menu_sel = (self.musvis_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._musvis_init(self.musvis_menu_sel)
    elif key in (ord("q"), 27):
        self.musvis_menu = False
        self._flash("Music Visualizer cancelled")
    return True



def _handle_musvis_key(self, key: int) -> bool:
    """Handle input in active music visualizer."""
    if key == ord(" "):
        self.musvis_running = not self.musvis_running
    elif key == ord("n"):
        n = len(self.MUSVIS_PRESETS)
        self._musvis_init((self.musvis_preset_idx + 1) % n)
    elif key == ord("N"):
        n = len(self.MUSVIS_PRESETS)
        self._musvis_init((self.musvis_preset_idx - 1) % n)
    elif key == ord("v"):
        self.musvis_view_mode = (self.musvis_view_mode + 1) % 6
        names = ["Spectrum", "Waveform", "Particles", "Combined", "Bass Tunnel", "Freq Rain"]
        self._flash(f"View: {names[self.musvis_view_mode]}")
    elif key == ord("c"):
        self.musvis_color_mode = (self.musvis_color_mode + 1) % len(self.MUSVIS_COLOR_NAMES)
        self._flash(f"Color: {self.MUSVIS_COLOR_NAMES[self.musvis_color_mode]}")
    elif key in (ord("+"), ord("=")):
        self.musvis_sensitivity = min(3.0, self.musvis_sensitivity + 0.1)
        self._flash(f"Sensitivity: {self.musvis_sensitivity:.1f}")
    elif key == ord("-"):
        self.musvis_sensitivity = max(0.1, self.musvis_sensitivity - 0.1)
        self._flash(f"Sensitivity: {self.musvis_sensitivity:.1f}")
    elif key == ord("b"):
        self.musvis_num_bars = min(64, self.musvis_num_bars + 4)
        self.musvis_spectrum = [0.0] * self.musvis_num_bars
        self.musvis_peak_history = [0.0] * self.musvis_num_bars
        self._flash(f"Bars: {self.musvis_num_bars}")
    elif key == ord("B"):
        self.musvis_num_bars = max(8, self.musvis_num_bars - 4)
        self.musvis_spectrum = [0.0] * self.musvis_num_bars
        self.musvis_peak_history = [0.0] * self.musvis_num_bars
        self._flash(f"Bars: {self.musvis_num_bars}")
    elif key == ord("r"):
        self._musvis_init(self.musvis_preset_idx)
    elif key in (ord("R"), ord("m")):
        self.musvis_mode = False
        self.musvis_running = False
        self.musvis_menu = True
        self.musvis_menu_sel = 0
    elif key in (ord("q"), 27):
        self._exit_musvis_mode()
    else:
        return True
    return True



def _musvis_color(self, val: float, band: int = 0) -> int:
    """Return curses color attribute for a visualizer value."""
    mode = self.musvis_color_mode
    if mode == 0:  # spectrum - color by frequency band
        if band == 0:  # bass
            return curses.color_pair(1) | curses.A_BOLD  # green
        elif band == 1:  # mid
            return curses.color_pair(3) | curses.A_BOLD  # yellow
        else:  # high
            return curses.color_pair(5) | curses.A_BOLD  # red
    elif mode == 1:  # fire
        if val < 0.3:
            return curses.color_pair(5)  # red dim
        elif val < 0.6:
            return curses.color_pair(3) | curses.A_BOLD  # yellow
        else:
            return curses.color_pair(7) | curses.A_BOLD  # white bright
    elif mode == 2:  # ocean
        if val < 0.3:
            return curses.color_pair(1)  # green dim
        elif val < 0.6:
            return curses.color_pair(2)  # cyan
        else:
            return curses.color_pair(2) | curses.A_BOLD  # cyan bright
    else:  # neon
        if val < 0.25:
            return curses.color_pair(4)  # magenta
        elif val < 0.5:
            return curses.color_pair(2) | curses.A_BOLD  # cyan bold
        elif val < 0.75:
            return curses.color_pair(3) | curses.A_BOLD  # yellow bold
        else:
            return curses.color_pair(7) | curses.A_BOLD  # white bold



def _draw_musvis_menu(self, max_y: int, max_x: int):
    """Draw the music visualizer preset selection menu."""
    self.stdscr.erase()
    title = "── Music Visualizer ── Select Visualization ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Audio-reactive ASCII animations with spectrum analysis & beat detection"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass

    for i, (name, desc) in enumerate(self.MUSVIS_PRESETS):
        y = 4 + i * 2
        if y >= max_y - 2:
            break
        line = f"  {name:<20s}  {desc}"
        attr = curses.color_pair(6)
        if i == self.musvis_menu_sel:
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



def _draw_musvis(self, max_y: int, max_x: int):
    """Render the music visualizer to the terminal."""
    self.stdscr.erase()
    view_h = max_y - 3
    view_w = max_x - 1
    if view_h < 5 or view_w < 10:
        return

    vm = self.musvis_view_mode
    if vm == 0:
        self._draw_musvis_spectrum(view_h, view_w)
    elif vm == 1:
        self._draw_musvis_waveform(view_h, view_w)
    elif vm == 2:
        self._draw_musvis_particles_view(view_h, view_w)
    elif vm == 3:
        self._draw_musvis_combined(view_h, view_w)
    elif vm == 4:
        self._draw_musvis_tunnel(view_h, view_w)
    elif vm == 5:
        self._draw_musvis_rain(view_h, view_w)

    # HUD
    state = "▶ PLAYING" if self.musvis_running else "⏸ PAUSED"
    color_name = self.MUSVIS_COLOR_NAMES[self.musvis_color_mode]
    beat_ind = "●" if self.musvis_beat_flash > 0.3 else "○"
    hud = (f" {self.musvis_preset_name}"
           f"  |  {state}"
           f"  |  {beat_ind} Beat"
           f"  |  Bass:{self.musvis_bass_energy:.2f}"
           f"  Mid:{self.musvis_mid_energy:.2f}"
           f"  High:{self.musvis_high_energy:.2f}"
           f"  |  Color: {color_name}"
           f"  |  Sens: {self.musvis_sensitivity:.1f}"
           f"  |  Frame: {self.musvis_generation}")
    try:
        hud_attr = curses.color_pair(7) | curses.A_BOLD
        if self.musvis_beat_flash > 0.5:
            hud_attr = curses.color_pair(5) | curses.A_BOLD
        self.stdscr.addstr(0, 0, hud[:max_x - 1], hud_attr)
    except curses.error:
        pass

    help_text = (" space=pause  v=view  c=color  +/-=sensitivity"
                 "  b/B=bars  n/N=next/prev  r=reset  m=menu  q=quit")
    try:
        self.stdscr.addstr(max_y - 1, 0, help_text[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_musvis_spectrum(self, view_h: int, view_w: int):
    """Draw FFT spectrum bar display."""
    spectrum = self.musvis_spectrum
    peaks = self.musvis_peak_history
    n_bars = len(spectrum)
    if n_bars == 0:
        return

    bar_w = max(1, view_w // n_bars)
    third = n_bars // 3
    bar_chars = self.MUSVIS_BAR_CHARS

    for i in range(n_bars):
        val = spectrum[i]
        peak_val = peaks[i]
        bar_h = int(val * (view_h - 2))
        peak_h = int(peak_val * (view_h - 2))

        # Determine band for coloring
        if i < third:
            band = 0
        elif i < 2 * third:
            band = 1
        else:
            band = 2

        x_start = i * bar_w
        if x_start >= view_w:
            break

        # Draw the bar from bottom up
        for row in range(view_h - 2):
            y = view_h - row
            if y < 1 or y >= view_h:
                continue

            fill_level = bar_h - row
            if fill_level > 0:
                # Full or partial fill
                ch_idx = min(len(bar_chars) - 1, int(fill_level * (len(bar_chars) - 1) / max(1, bar_h)) + 1)
                if ch_idx < 1:
                    ch_idx = 1
                ch = bar_chars[min(ch_idx, len(bar_chars) - 1)]
                attr = self._musvis_color(val, band)
                for dx in range(min(bar_w, view_w - x_start)):
                    try:
                        self.stdscr.addstr(y, x_start + dx, ch, attr)
                    except curses.error:
                        pass
            elif row == peak_h and peak_h > 0:
                # Peak indicator
                attr = curses.color_pair(7) | curses.A_BOLD
                for dx in range(min(bar_w, view_w - x_start)):
                    try:
                        self.stdscr.addstr(y, x_start + dx, "─", attr)
                    except curses.error:
                        pass



def _draw_musvis_waveform(self, view_h: int, view_w: int):
    """Draw oscilloscope-style waveform."""
    waveform = self.musvis_waveform
    n_samples = len(waveform)
    if n_samples == 0:
        return

    mid_y = view_h // 2 + 1
    amp = (view_h - 4) / 2.0

    # Draw center line
    for x in range(view_w):
        try:
            self.stdscr.addstr(mid_y, x, "─", curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    # Draw waveform
    prev_y = None
    for x in range(min(view_w, n_samples)):
        sample_idx = int(x * n_samples / view_w)
        if sample_idx >= n_samples:
            sample_idx = n_samples - 1
        val = waveform[sample_idx]
        y = int(mid_y - val * amp)
        y = max(1, min(view_h, y))

        # Determine color from waveform intensity
        intensity = abs(val)
        attr = self._musvis_color(intensity, 1)

        # Draw connecting vertical line if big jump
        if prev_y is not None and abs(y - prev_y) > 1:
            step = 1 if y > prev_y else -1
            for iy in range(prev_y, y, step):
                if 1 <= iy <= view_h:
                    try:
                        self.stdscr.addstr(iy, x, "│", attr)
                    except curses.error:
                        pass

        ch = "█" if intensity > 0.5 else "▓" if intensity > 0.3 else "░"
        try:
            self.stdscr.addstr(y, x, ch, attr)
        except curses.error:
            pass
        prev_y = y

    # Beat flash border
    if self.musvis_beat_flash > 0.3:
        flash_attr = curses.color_pair(5) | curses.A_BOLD
        for x in range(view_w):
            try:
                self.stdscr.addstr(1, x, "▀", flash_attr)
                self.stdscr.addstr(view_h, x, "▄", flash_attr)
            except curses.error:
                pass



def _draw_musvis_particles_view(self, view_h: int, view_w: int):
    """Draw beat-reactive particle explosions."""
    cx = view_w // 2
    cy = view_h // 2 + 1

    # Draw a central energy indicator
    energy = self.musvis_bass_energy + self.musvis_mid_energy
    radius = int(energy * 5) + 1
    ring_chars = "·∘○◎●"
    for dr in range(-radius, radius + 1):
        for dc in range(-radius * 2, radius * 2 + 1):
            dist = math.sqrt(dr * dr + (dc / 2.0) ** 2)
            if abs(dist - radius) < 1.0:
                y, x = cy + dr, cx + dc
                if 1 <= y <= view_h and 0 <= x < view_w:
                    ch = ring_chars[min(int(energy * 4), len(ring_chars) - 1)]
                    attr = self._musvis_color(energy, 0)
                    try:
                        self.stdscr.addstr(y, x, ch, attr)
                    except curses.error:
                        pass

    # Draw particles
    for p in self.musvis_particles:
        y = int(cy + p["r"])
        x = int(cx + p["c"])
        if 1 <= y <= view_h and 0 <= x < view_w:
            alpha = p["life"]
            attr = curses.color_pair(p["color"])
            if alpha > 0.5:
                attr |= curses.A_BOLD
            try:
                self.stdscr.addstr(y, x, p["char"], attr)
            except curses.error:
                pass



def _draw_musvis_combined(self, view_h: int, view_w: int):
    """Draw combined spectrum + waveform + particles view."""
    # Top third: mini spectrum
    spec_h = view_h // 3
    spectrum = self.musvis_spectrum
    n_bars = len(spectrum)
    if n_bars > 0:
        bar_w = max(1, view_w // n_bars)
        third = n_bars // 3
        for i in range(n_bars):
            val = spectrum[i]
            bar_h = int(val * (spec_h - 1))
            band = 0 if i < third else (1 if i < 2 * third else 2)
            x_start = i * bar_w
            if x_start >= view_w:
                break
            attr = self._musvis_color(val, band)
            for row in range(bar_h):
                y = spec_h - row + 1
                if 1 <= y <= spec_h + 1:
                    for dx in range(min(bar_w, view_w - x_start)):
                        try:
                            self.stdscr.addstr(y, x_start + dx, "█", attr)
                        except curses.error:
                            pass

    # Middle third: waveform
    wave_top = spec_h + 2
    wave_h = view_h // 3
    mid_y = wave_top + wave_h // 2
    waveform = self.musvis_waveform
    n_samples = len(waveform)
    if n_samples > 0:
        amp = (wave_h - 2) / 2.0
        for x in range(min(view_w, n_samples)):
            si = int(x * n_samples / view_w)
            if si >= n_samples:
                si = n_samples - 1
            val = waveform[si]
            y = int(mid_y - val * amp)
            y = max(wave_top, min(wave_top + wave_h, y))
            attr = self._musvis_color(abs(val), 1)
            try:
                self.stdscr.addstr(y, x, "●", attr)
            except curses.error:
                pass

    # Bottom third: particles
    part_top = wave_top + wave_h + 1
    part_h = view_h - part_top
    pcx = view_w // 2
    pcy = part_top + part_h // 2
    for p in self.musvis_particles:
        y = int(pcy + p["r"] * 0.5)
        x = int(pcx + p["c"] * 0.5)
        if part_top <= y < view_h and 0 <= x < view_w:
            attr = curses.color_pair(p["color"])
            if p["life"] > 0.5:
                attr |= curses.A_BOLD
            try:
                self.stdscr.addstr(y, x, p["char"], attr)
            except curses.error:
                pass



def _draw_musvis_tunnel(self, view_h: int, view_w: int):
    """Draw bass-reactive tunnel zoom effect."""
    cx = view_w // 2
    cy = view_h // 2 + 1
    bass = self.musvis_bass_energy
    t = self.musvis_time
    tunnel_chars = " .:-=+*#%@█"
    n_ch = len(tunnel_chars) - 1

    for row in range(1, view_h + 1):
        for col in range(view_w):
            dx = (col - cx) / max(1, cx)
            dy = (row - cy) / max(1, cy) * 2.0  # Aspect correction

            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 0.01:
                dist = 0.01

            # Tunnel coordinates
            angle = math.atan2(dy, dx)
            depth = 1.0 / dist

            # Animated scrolling texture
            u = angle / math.pi + t * 0.5
            v = depth + t * (1.0 + bass * 3.0)

            # Checkerboard-ish pattern modulated by audio
            pattern = math.sin(u * 8.0) * math.sin(v * 4.0)
            pattern = (pattern + 1.0) * 0.5

            # Modulate by bass
            pattern *= (0.3 + bass * 2.0)

            # Distance fade
            brightness = min(1.0, 2.0 / (dist + 0.5))
            val = pattern * brightness
            val = max(0.0, min(1.0, val))

            ch = tunnel_chars[int(val * n_ch)]

            # Color by distance and energy
            if dist < 0.5:
                band = 2
            elif dist < 1.0:
                band = 1
            else:
                band = 0
            attr = self._musvis_color(val, band)

            try:
                self.stdscr.addstr(row, col, ch, attr)
            except curses.error:
                pass



def _draw_musvis_rain(self, view_h: int, view_w: int):
    """Draw frequency rain — spectrum bins as falling rain columns."""
    spectrum = self.musvis_spectrum
    n_bars = len(spectrum)
    if n_bars == 0:
        return

    t = self.musvis_time
    third = n_bars // 3
    rain_chars = ".,:;!|I#@█"
    n_ch = len(rain_chars) - 1

    for col in range(view_w):
        # Map column to spectrum bin
        bin_idx = int(col * n_bars / view_w)
        if bin_idx >= n_bars:
            bin_idx = n_bars - 1
        energy = spectrum[bin_idx]
        band = 0 if bin_idx < third else (1 if bin_idx < 2 * third else 2)

        # Rain speed proportional to energy
        speed = 2.0 + energy * 10.0
        # Rain density proportional to energy
        drop_density = energy * 3.0

        for row in range(1, view_h + 1):
            # Animated rain drop pattern
            phase = (row * 0.3 + col * 0.1 + t * speed) % 7.0
            if phase < drop_density:
                val = energy * (1.0 - phase / max(0.01, drop_density))
                val = max(0.0, min(1.0, val))
                ch = rain_chars[int(val * n_ch)]
                attr = self._musvis_color(val, band)
                if val > 0.7:
                    attr |= curses.A_BOLD
                try:
                    self.stdscr.addstr(row, col, ch, attr)
                except curses.error:
                    pass


def register(App):
    """Register musvis mode methods on the App class."""
    App._enter_musvis_mode = _enter_musvis_mode
    App._exit_musvis_mode = _exit_musvis_mode
    App._musvis_init = _musvis_init
    App._musvis_generate_audio_data = _musvis_generate_audio_data
    App._musvis_spawn_particles = _musvis_spawn_particles
    App._musvis_update_particles = _musvis_update_particles
    App._musvis_step = _musvis_step
    App._handle_musvis_menu_key = _handle_musvis_menu_key
    App._handle_musvis_key = _handle_musvis_key
    App._musvis_color = _musvis_color
    App._draw_musvis_menu = _draw_musvis_menu
    App._draw_musvis = _draw_musvis
    App._draw_musvis_spectrum = _draw_musvis_spectrum
    App._draw_musvis_waveform = _draw_musvis_waveform
    App._draw_musvis_particles_view = _draw_musvis_particles_view
    App._draw_musvis_combined = _draw_musvis_combined
    App._draw_musvis_tunnel = _draw_musvis_tunnel
    App._draw_musvis_rain = _draw_musvis_rain

