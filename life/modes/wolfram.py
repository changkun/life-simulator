"""Mode: wolfram — simulation mode for the life package."""
import curses
import math
import random
import time


from life.constants import SPEEDS, SPEED_LABELS

def _wolfram_apply_rule(self, rule_num: int, left: int, center: int, right: int) -> int:
    """Apply a Wolfram elementary rule. The 3-cell neighbourhood (left, center, right)
    forms a 3-bit index into the 8-bit rule number."""
    idx = (left << 2) | (center << 1) | right
    return (rule_num >> idx) & 1



def _wolfram_init(self):
    """Initialize the Wolfram automaton with the chosen seed mode."""
    max_y, max_x = self.stdscr.getmaxyx()
    self.wolfram_width = max_x - 2  # leave margin
    if self.wolfram_width < 10:
        self.wolfram_width = 10
    row0 = [0] * self.wolfram_width
    if self.wolfram_seed_mode == "center":
        row0[self.wolfram_width // 2] = 1
    elif self.wolfram_seed_mode == "gol_row":
        # Use the middle row of the current Game of Life grid
        mid_r = self.grid.rows // 2
        for c in range(min(self.wolfram_width, self.grid.cols)):
            if self.grid.is_alive(mid_r, c):
                row0[c] = 1
        # If completely empty, fall back to center cell
        if sum(row0) == 0:
            row0[self.wolfram_width // 2] = 1
    elif self.wolfram_seed_mode == "random":
        for c in range(self.wolfram_width):
            row0[c] = random.randint(0, 1)
    self.wolfram_rows = [row0]



def _wolfram_step(self):
    """Compute the next row of the 1D automaton."""
    if not self.wolfram_rows:
        return
    prev = self.wolfram_rows[-1]
    w = len(prev)
    new_row = [0] * w
    for i in range(w):
        left = prev[(i - 1) % w]
        center = prev[i]
        right = prev[(i + 1) % w]
        new_row[i] = self._wolfram_apply_rule(self.wolfram_rule, left, center, right)
    self.wolfram_rows.append(new_row)



def _enter_wolfram_mode(self):
    """Enter the Wolfram 1D automaton mode — show rule menu first."""
    self.wolfram_menu = True
    self.wolfram_menu_sel = 0
    self._flash("Wolfram 1D Automaton — select a rule")



def _exit_wolfram_mode(self):
    """Exit Wolfram mode back to normal Game of Life."""
    self.wolfram_mode = False
    self.wolfram_menu = False
    self.wolfram_running = False
    self.wolfram_rows = []
    self._flash("Wolfram mode OFF")



def _handle_wolfram_menu_key(self, key: int) -> bool:
    """Handle keys in the Wolfram rule selection menu."""
    if key == -1:
        return True
    n_presets = len(self.WOLFRAM_PRESETS)
    if key == curses.KEY_UP or key == ord("k"):
        self.wolfram_menu_sel = (self.wolfram_menu_sel - 1) % (n_presets + 3)
        return True
    if key == curses.KEY_DOWN or key == ord("j"):
        self.wolfram_menu_sel = (self.wolfram_menu_sel + 1) % (n_presets + 3)
        return True
    if key == ord("q") or key == 27:
        self.wolfram_menu = False
        self._flash("Wolfram mode cancelled")
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if self.wolfram_menu_sel < n_presets:
            self.wolfram_rule = self.WOLFRAM_PRESETS[self.wolfram_menu_sel][0]
        elif self.wolfram_menu_sel == n_presets:
            # Custom rule input
            txt = self._prompt_text("Enter rule number (0-255)")
            if txt is not None:
                try:
                    val = int(txt)
                    if 0 <= val <= 255:
                        self.wolfram_rule = val
                    else:
                        self._flash("Rule must be 0-255")
                        return True
                except ValueError:
                    self._flash("Invalid number")
                    return True
            else:
                return True
        elif self.wolfram_menu_sel == n_presets + 1:
            # Toggle seed mode
            modes = ["center", "gol_row", "random"]
            idx = modes.index(self.wolfram_seed_mode)
            self.wolfram_seed_mode = modes[(idx + 1) % len(modes)]
            return True
        elif self.wolfram_menu_sel == n_presets + 2:
            # Start with currently selected settings
            pass
        self.wolfram_menu = False
        self.wolfram_mode = True
        self.wolfram_running = False
        self._wolfram_init()
        self._flash(f"Wolfram Rule {self.wolfram_rule} — Space=play, n=step, q=exit")
        return True
    return True



def _handle_wolfram_key(self, key: int) -> bool:
    """Handle keys while in Wolfram 1D automaton mode."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._exit_wolfram_mode()
        return True
    if key == ord(" "):
        self.wolfram_running = not self.wolfram_running
        self._flash("Playing" if self.wolfram_running else "Paused")
        return True
    if key == ord("n") or key == ord("."):
        self.wolfram_running = False
        self._wolfram_step()
        return True
    if key == ord("r"):
        # Reset with current rule
        self._wolfram_init()
        self._flash(f"Reset Rule {self.wolfram_rule}")
        return True
    if key == ord("R") or key == ord("m"):
        # Open rule menu again
        self.wolfram_mode = False
        self.wolfram_running = False
        self.wolfram_menu = True
        self.wolfram_menu_sel = 0
        return True
    if key == ord(">"):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == ord("<"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        self._flash(f"Speed: {SPEED_LABELS[self.speed_idx]}")
        return True
    if key == curses.KEY_LEFT or key == ord("h"):
        if self.wolfram_rule > 0:
            self.wolfram_rule -= 1
            self._wolfram_init()
            self._flash(f"Rule {self.wolfram_rule}")
        return True
    if key == curses.KEY_RIGHT or key == ord("l"):
        if self.wolfram_rule < 255:
            self.wolfram_rule += 1
            self._wolfram_init()
            self._flash(f"Rule {self.wolfram_rule}")
        return True
    return True



def _draw_wolfram_menu(self, max_y: int, max_x: int):
    """Draw the Wolfram rule selection menu."""
    title = "── Wolfram 1D Elementary Cellular Automaton ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    subtitle = "Select a rule preset or enter a custom rule (0-255)"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    n_presets = len(self.WOLFRAM_PRESETS)
    for i, (rule_num, desc) in enumerate(self.WOLFRAM_PRESETS):
        y = 5 + i
        if y >= max_y - 6:
            break
        # Show mini rule table: 8 outputs for the 8 input patterns
        rule_bits = f"{rule_num:08b}"
        line = f"  {desc}  [{rule_bits}]"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.wolfram_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    # Extra menu items
    extra_y = 5 + min(n_presets, max_y - 11)
    extra_items = [
        f"  [Custom] Enter rule number manually",
        f"  [Seed: {self.wolfram_seed_mode}] Toggle initial condition (center/GoL row/random)",
        f"  >>> Start with Rule {self.wolfram_rule}, seed={self.wolfram_seed_mode} <<<",
    ]
    for i, line in enumerate(extra_items):
        y = extra_y + i
        idx = n_presets + i
        if y >= max_y - 2:
            break
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if idx == self.wolfram_menu_sel:
            attr = curses.color_pair(7) | curses.A_BOLD
        try:
            self.stdscr.addstr(y, 1, line, attr)
        except curses.error:
            pass

    # Draw the rule table visualization for current rule
    table_y = extra_y + len(extra_items) + 1
    if table_y < max_y - 3:
        rule_bits = f"{self.wolfram_rule:08b}"
        header = f"  Rule {self.wolfram_rule} table:  "
        patterns = ["111", "110", "101", "100", "011", "010", "001", "000"]
        for j, pat in enumerate(patterns):
            header += f" {pat}={rule_bits[j]}"
        header = header[:max_x - 2]
        try:
            self.stdscr.addstr(table_y, 1, header, curses.color_pair(1))
        except curses.error:
            pass

    # Hint
    hint_y = max_y - 1
    if hint_y > 0:
        hint = " [j/k]=navigate [Enter]=select [q/Esc]=cancel"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_wolfram(self, max_y: int, max_x: int):
    """Draw the Wolfram 1D automaton — rows cascade top to bottom."""
    # Title bar
    rule_bits = f"{self.wolfram_rule:08b}"
    title = f" Wolfram Rule {self.wolfram_rule} [{rule_bits}]  Gen: {len(self.wolfram_rows) - 1}  Seed: {self.wolfram_seed_mode}"
    state = " PLAY" if self.wolfram_running else " PAUSE"
    title += f"  {state}"
    title = title[:max_x - 1]
    try:
        self.stdscr.addstr(0, 0, title, curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Rule table visualization on line 1
    table_line = " Table: "
    patterns = ["111", "110", "101", "100", "011", "010", "001", "000"]
    for j, pat in enumerate(patterns):
        table_line += f"{pat}={'#' if rule_bits[j] == '1' else '.'} "
    table_line = table_line[:max_x - 1]
    try:
        self.stdscr.addstr(1, 0, table_line, curses.color_pair(1))
    except curses.error:
        pass

    # Draw the automaton rows
    draw_start = 3
    draw_rows = max_y - 5  # leave room for status/hint
    if draw_rows < 1:
        draw_rows = 1

    # Show the most recent rows that fit on screen
    total_rows = len(self.wolfram_rows)
    start_idx = max(0, total_rows - draw_rows)
    display_width = min(self.wolfram_width, max_x - 1)

    for i, row_idx in enumerate(range(start_idx, total_rows)):
        y = draw_start + i
        if y >= max_y - 2:
            break
        row = self.wolfram_rows[row_idx]
        # Center the row if it's narrower than the screen
        offset = max(0, (max_x - display_width) // 2)
        line_chars = []
        for c in range(display_width):
            if c < len(row) and row[c]:
                line_chars.append("\u2588")  # full block
            else:
                line_chars.append(" ")
        line = "".join(line_chars)
        try:
            color = curses.color_pair(1)
            # Use different colors for generation bands
            if row_idx % 2 == 0:
                color = curses.color_pair(2) if curses.has_colors() else curses.A_NORMAL
            self.stdscr.addstr(y, offset, line, color)
        except curses.error:
            pass

    # Highlight known interesting rules
    interesting = {30: "chaotic", 90: "Sierpinski", 110: "Turing-complete",
                   184: "traffic", 73: "complex", 54: "complex"}
    note = interesting.get(self.wolfram_rule, "")
    if note:
        note = f" ({note})"

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        pop = sum(self.wolfram_rows[-1]) if self.wolfram_rows else 0
        density = pop / self.wolfram_width * 100 if self.wolfram_width > 0 else 0
        status = f" Rule: {self.wolfram_rule}{note}  |  Gen: {len(self.wolfram_rows) - 1}  |  Alive: {pop}/{self.wolfram_width} ({density:.0f}%)  |  Speed: {SPEED_LABELS[self.speed_idx]}"
        status = status[:max_x - 1]
        try:
            self.stdscr.addstr(status_y, 0, status, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [h/l]=prev/next rule [r]=reset [R]=menu [</>]=speed [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register wolfram mode methods on the App class."""
    App._wolfram_apply_rule = _wolfram_apply_rule
    App._wolfram_init = _wolfram_init
    App._wolfram_step = _wolfram_step
    App._enter_wolfram_mode = _enter_wolfram_mode
    App._exit_wolfram_mode = _exit_wolfram_mode
    App._handle_wolfram_menu_key = _handle_wolfram_menu_key
    App._handle_wolfram_key = _handle_wolfram_key
    App._draw_wolfram_menu = _draw_wolfram_menu
    App._draw_wolfram = _draw_wolfram

