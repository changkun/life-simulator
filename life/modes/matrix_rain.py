"""Mode: matrix — simulation mode for the life package."""
import curses
import math
import random
import time

MATRIX_PRESETS = [
    ("Classic Green", "The iconic green Matrix rain with mixed characters", "classic"),
    ("Dense Rain", "Heavy downpour of characters — maximum density", "dense"),
    ("Sparse Drizzle", "Light, sparse streams for a subtle effect", "sparse"),
    ("Katakana Only", "Pure half-width Katakana characters", "katakana"),
    ("Binary", "Pure 0s and 1s — digital rain", "binary"),
    ("Rainbow", "Multi-colored character streams", "rainbow"),
]

_MATRIX_KATAKANA = "ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"
_MATRIX_DIGITS = "0123456789"
_MATRIX_LATIN = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_MATRIX_SYMBOLS = "+-*/<>=$#@&!?~^%"


def _enter_matrix_mode(self):
    """Enter Matrix Digital Rain mode — show preset menu."""
    self.matrix_menu = True
    self.matrix_menu_sel = 0




def _exit_matrix_mode(self):
    """Exit Matrix Digital Rain mode."""
    self.matrix_mode = False
    self.matrix_menu = False
    self.matrix_running = False
    self.matrix_columns = []




def _matrix_init(self, preset: str):
    """Initialize Matrix rain simulation from preset."""
    rows, cols = self.grid.rows, self.grid.cols
    self.matrix_rows = rows
    self.matrix_cols = cols
    self.matrix_time = 0.0
    self.matrix_generation = 0
    self.matrix_columns = []

    if preset == "classic":
        self.matrix_density = 0.4
        self.matrix_char_pool = _MATRIX_KATAKANA + _MATRIX_DIGITS + _MATRIX_LATIN + _MATRIX_SYMBOLS
        self.matrix_color_mode = "green"
        self.matrix_speed = 2
    elif preset == "dense":
        self.matrix_density = 0.75
        self.matrix_char_pool = _MATRIX_KATAKANA + _MATRIX_DIGITS + _MATRIX_LATIN + _MATRIX_SYMBOLS
        self.matrix_color_mode = "green"
        self.matrix_speed = 3
    elif preset == "sparse":
        self.matrix_density = 0.15
        self.matrix_char_pool = _MATRIX_KATAKANA + _MATRIX_DIGITS + _MATRIX_LATIN
        self.matrix_color_mode = "green"
        self.matrix_speed = 1
    elif preset == "katakana":
        self.matrix_density = 0.4
        self.matrix_char_pool = _MATRIX_KATAKANA
        self.matrix_color_mode = "green"
        self.matrix_speed = 2
    elif preset == "binary":
        self.matrix_density = 0.5
        self.matrix_char_pool = "01"
        self.matrix_color_mode = "green"
        self.matrix_speed = 2
    elif preset == "rainbow":
        self.matrix_density = 0.4
        self.matrix_char_pool = _MATRIX_KATAKANA + _MATRIX_DIGITS + _MATRIX_LATIN + _MATRIX_SYMBOLS
        self.matrix_color_mode = "rainbow"
        self.matrix_speed = 2

    # Initialize column streams
    # Each column can have multiple streams (list of stream dicts)
    # Stream dict: {y: float, speed: float, length: int, chars: list[str], age: int}
    self.matrix_columns = [[] for _ in range(cols)]
    for c in range(cols):
        if random.random() < self.matrix_density:
            self._matrix_spawn_stream(c, initial=True)




def _matrix_spawn_stream(self, col: int, initial: bool = False):
    """Spawn a new falling stream in the given column."""
    rows = self.matrix_rows
    speed = random.uniform(0.3, 1.5)
    length = random.randint(4, max(5, rows // 2))
    chars = [random.choice(self.matrix_char_pool) for _ in range(length)]
    start_y = random.uniform(-rows * 0.8, -1) if initial else random.uniform(-length * 2, -1)
    stream = {
        "y": start_y,
        "speed": speed,
        "length": length,
        "chars": chars,
        "age": 0,
        "mutate_rate": random.uniform(0.02, 0.1),  # char randomization rate
    }
    self.matrix_columns[col].append(stream)




def _matrix_step(self):
    """Advance the Matrix rain by one step."""
    self.matrix_generation += 1
    self.matrix_time += 0.033
    rows = self.matrix_rows
    cols = self.matrix_cols

    for c in range(cols):
        new_streams = []
        for stream in self.matrix_columns[c]:
            stream["y"] += stream["speed"]
            stream["age"] += 1

            # Randomly mutate characters for the flickering effect
            for i in range(len(stream["chars"])):
                if random.random() < stream["mutate_rate"]:
                    stream["chars"][i] = random.choice(self.matrix_char_pool)

            # Keep stream if its tail is still on screen
            tail_y = stream["y"] - stream["length"]
            if tail_y < rows + 5:
                new_streams.append(stream)

        self.matrix_columns[c] = new_streams

        # Possibly spawn new streams
        if random.random() < self.matrix_density * 0.02:
            self._matrix_spawn_stream(c)




def _handle_matrix_menu_key(self, key: int) -> bool:
    """Handle keys in the Matrix preset menu."""
    n = len(MATRIX_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.matrix_menu_sel = (self.matrix_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.matrix_menu_sel = (self.matrix_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.matrix_menu = False
        self.matrix_mode = False
        self._exit_matrix_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = MATRIX_PRESETS[self.matrix_menu_sel]
        self.matrix_preset_name = preset[2]
        self._matrix_init(preset[2])
        self.matrix_menu = False
        self.matrix_mode = True
        self.matrix_running = True
    else:
        return True
    return True




def _handle_matrix_key(self, key: int) -> bool:
    """Handle keys during Matrix simulation."""
    if key in (27, ord('q')):
        self._exit_matrix_mode()
        return True
    elif key == ord(' '):
        self.matrix_running = not self.matrix_running
    elif key in (ord('n'), ord('.')):
        self._matrix_step()
    elif key == ord('r'):
        self._matrix_init(self.matrix_preset_name)
    elif key in (ord('R'), ord('m')):
        self.matrix_menu = True
        self.matrix_running = False
    elif key == ord('+') or key == ord('s'):
        self.matrix_speed = min(10, self.matrix_speed + 1)
    elif key == ord('-') or key == ord('S'):
        self.matrix_speed = max(1, self.matrix_speed - 1)
    elif key == ord('i'):
        self.matrix_show_info = not self.matrix_show_info
    elif key == ord('d'):
        # Increase density
        self.matrix_density = min(1.0, self.matrix_density + 0.05)
    elif key == ord('D'):
        # Decrease density
        self.matrix_density = max(0.05, self.matrix_density - 0.05)
    elif key == ord('c'):
        # Cycle color mode
        modes = ["green", "blue", "rainbow"]
        idx = modes.index(self.matrix_color_mode) if self.matrix_color_mode in modes else 0
        self.matrix_color_mode = modes[(idx + 1) % len(modes)]
    else:
        return True
    return True




def _draw_matrix_menu(self, max_y: int, max_x: int):
    """Draw the Matrix preset selection menu."""
    self.stdscr.erase()
    title = "── Matrix Digital Rain ──"
    if max_x > len(title) + 2:
        self.stdscr.addstr(1, (max_x - len(title)) // 2, title, curses.A_BOLD | curses.color_pair(1))

    subtitle = "Cascading character streams inspired by The Matrix"
    if max_y > 3 and max_x > len(subtitle) + 2:
        self.stdscr.addstr(2, (max_x - len(subtitle)) // 2, subtitle, curses.A_DIM)

    # ASCII art
    art = [
        "  ｦ 0 ｱ   ﾑ 1 ﾓ   ｳ 0 ﾎ  ",
        "  ｧ 1 ｲ   ﾒ 0 ﾔ   ｴ 1 ﾏ  ",
        "  ｨ 0 ｳ   ﾓ 1 ﾕ   ｵ 0 ﾐ  ",
        "  ▓ 1 ▒   ░ 0 ▒   ▓ 1 ░  ",
        "  ░ 0 ░   ▒ 1 ░   ░ 0 ░  ",
        "  · · ·   · · ·   · · ·  ",
    ]
    art_start = 4
    for i, line in enumerate(art):
        y = art_start + i
        if y >= max_y - len(MATRIX_PRESETS) - 6:
            break
        x = (max_x - len(line)) // 2
        if x > 0 and y < max_y:
            try:
                self.stdscr.addstr(y, x, line, curses.color_pair(1) | curses.A_DIM)
            except curses.error:
                pass

    menu_y = max(art_start + len(art) + 1, max_y // 2 - len(MATRIX_PRESETS) // 2)
    header = "Select a rain style:"
    if menu_y - 1 > 0 and max_x > len(header) + 4:
        try:
            self.stdscr.addstr(menu_y - 1, 3, header, curses.A_BOLD | curses.color_pair(1))
        except curses.error:
            pass

    for i, (name, desc, _key) in enumerate(MATRIX_PRESETS):
        y = menu_y + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.matrix_menu_sel else "  "
        attr = curses.A_REVERSE | curses.color_pair(1) if i == self.matrix_menu_sel else curses.color_pair(1)
        line = f"{marker}{name:<24s} {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    footer = " ↑↓=select  Enter=start  q=back "
    try:
        self.stdscr.addstr(max_y - 1, 0, footer[:max_x - 1], curses.A_DIM | curses.A_REVERSE)
    except curses.error:
        pass




def _draw_matrix(self, max_y: int, max_x: int):
    """Draw the Matrix Digital Rain simulation."""
    self.stdscr.erase()
    rows = min(max_y - 1, self.matrix_rows)
    cols = min(max_x, self.matrix_cols)
    if rows < 5 or cols < 10:
        try:
            self.stdscr.addstr(0, 0, "Terminal too small")
        except curses.error:
            pass
        return

    # Build a screen buffer: for each cell, store (char, brightness)
    # brightness: 0=empty, 1=dim tail, 2=mid, 3=bright, 4=head (white)
    screen = {}  # (row, col) -> (char, brightness)

    for c in range(cols):
        for stream in self.matrix_columns[c]:
            head_y = stream["y"]
            length = stream["length"]
            chars = stream["chars"]

            for i in range(length):
                cell_y = int(head_y) - i
                if cell_y < 0 or cell_y >= rows:
                    continue

                # Character from stream (wrapping index)
                ch = chars[i % len(chars)]

                # Brightness: head is brightest, fades toward tail
                fraction = i / max(length - 1, 1)  # 0=head, 1=tail
                if i == 0:
                    brightness = 4  # head — white/bright
                elif fraction < 0.2:
                    brightness = 3  # near head — bright green
                elif fraction < 0.5:
                    brightness = 2  # mid — medium green
                else:
                    brightness = 1  # tail — dim green

                # Later streams overwrite earlier ones (front layering)
                existing = screen.get((cell_y, c))
                if existing is None or brightness > existing[1]:
                    screen[(cell_y, c)] = (ch, brightness)

    # Render
    for (r, c), (ch, brightness) in screen.items():
        if r >= max_y - 1 or c >= max_x - 1:
            continue
        try:
            # Determine color and attribute based on brightness and color mode
            if self.matrix_color_mode == "green":
                if brightness == 4:
                    attr = curses.color_pair(6) | curses.A_BOLD  # white head
                elif brightness == 3:
                    attr = curses.color_pair(1) | curses.A_BOLD  # bright green
                elif brightness == 2:
                    attr = curses.color_pair(1)  # normal green
                else:
                    attr = curses.color_pair(1) | curses.A_DIM  # dim green
            elif self.matrix_color_mode == "blue":
                if brightness == 4:
                    attr = curses.color_pair(6) | curses.A_BOLD  # white head
                elif brightness == 3:
                    attr = curses.color_pair(2) | curses.A_BOLD  # bright cyan
                elif brightness == 2:
                    attr = curses.color_pair(2)  # normal cyan
                else:
                    attr = curses.color_pair(2) | curses.A_DIM  # dim cyan
            else:  # rainbow
                # Use column position to pick color
                color_idx = (c * 7 + self.matrix_generation) % 6 + 1
                if brightness == 4:
                    attr = curses.color_pair(6) | curses.A_BOLD  # white head
                elif brightness >= 3:
                    attr = curses.color_pair(color_idx) | curses.A_BOLD
                elif brightness == 2:
                    attr = curses.color_pair(color_idx)
                else:
                    attr = curses.color_pair(color_idx) | curses.A_DIM

            self.stdscr.addstr(r, c, ch, attr)
        except curses.error:
            pass

    # Info overlay
    if self.matrix_show_info:
        total_streams = sum(len(streams) for streams in self.matrix_columns)
        info_lines = [
            f" Preset: {self.matrix_preset_name}  Color: {self.matrix_color_mode}",
            f" Density: {self.matrix_density:.0%}  Streams: {total_streams}  Gen: {self.matrix_generation}",
            f" Speed: {self.matrix_speed}x",
        ]
        for i, line in enumerate(info_lines):
            if i < max_y - 2:
                try:
                    self.stdscr.addstr(i, 0, line[:max_x - 1], curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 1
    state = "▶ RUNNING" if self.matrix_running else "⏸ PAUSED"
    status = f" {state} | Gen {self.matrix_generation} | Speed {self.matrix_speed}x | Density {self.matrix_density:.0%} | {self.matrix_color_mode}"
    try:
        self.stdscr.addstr(status_y, 0, status[:max_x - 1], curses.color_pair(1) | curses.A_REVERSE)
        # Pad rest of line
        remaining = max_x - 1 - len(status)
        if remaining > 0:
            self.stdscr.addstr(status_y, len(status), " " * remaining, curses.color_pair(1) | curses.A_REVERSE)
    except curses.error:
        pass

    # Hint
    hint_y = max_y - 1
    now = time.monotonic()
    if self.message and now - self.message_time < 3.0:
        pass  # message already shown in status
    else:
        hint = " [Space]=play [n]=step [s/S]=speed [d/D]=density [c]=color [r]=reset [R]=menu [i]=info [q]=exit"
        hint_start = len(status) + 1
        if hint_start + len(hint) < max_x:
            pass  # status bar already covers the line


def register(App):
    """Register matrix mode methods on the App class."""
    App._enter_matrix_mode = _enter_matrix_mode
    App._exit_matrix_mode = _exit_matrix_mode
    App._matrix_init = _matrix_init
    App._matrix_spawn_stream = _matrix_spawn_stream
    App._matrix_step = _matrix_step
    App._handle_matrix_menu_key = _handle_matrix_menu_key
    App._handle_matrix_key = _handle_matrix_key
    App._draw_matrix_menu = _draw_matrix_menu
    App._draw_matrix = _draw_matrix

