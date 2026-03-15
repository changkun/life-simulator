"""Mode: race — simulation mode for the life package."""
import curses
import math
import random
import time


from life.colors import color_for_age
from life.constants import CELL_CHAR
from life.rules import RULE_PRESETS, parse_rule_string, rule_string

def _enter_race_mode(self):
    """Open the multi-rule selection menu for race mode."""
    if self.compare_mode:
        self._exit_compare_mode()
    self.race_rule_menu = True
    self.race_rule_sel = 0
    self.race_selected_rules = []



def _exit_race_mode(self):
    """Leave race mode and discard race grids."""
    self.race_mode = False
    self.race_grids.clear()
    self.race_pop_histories.clear()
    self.race_rule_menu = False
    self.race_selected_rules.clear()
    self.race_finished = False
    self.race_winner = None
    self.race_stats.clear()
    self.race_state_hashes.clear()
    self._flash("Race mode OFF")



def _handle_race_rule_menu_key(self, key: int) -> bool:
    """Handle input in the race rule selection menu."""
    if key == -1:
        return True
    if key == 27 or key == ord("q"):  # ESC or q — cancel
        self.race_rule_menu = False
        self.race_selected_rules.clear()
        return True
    if key in (curses.KEY_UP, ord("k")):
        self.race_rule_sel = (self.race_rule_sel - 1) % len(self.rule_preset_list)
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.race_rule_sel = (self.race_rule_sel + 1) % len(self.rule_preset_list)
        return True
    if key == ord(" "):  # Space to toggle selection
        name = self.rule_preset_list[self.race_rule_sel]
        preset = RULE_PRESETS[name]
        # Check if already selected — toggle off
        existing = [i for i, (n, b, s) in enumerate(self.race_selected_rules) if n == name]
        if existing:
            self.race_selected_rules.pop(existing[0])
        elif len(self.race_selected_rules) < 4:
            self.race_selected_rules.append((name, set(preset["birth"]), set(preset["survival"])))
        else:
            self._flash("Max 4 rules — deselect one first")
        return True
    if key == ord("/"):  # Custom rule entry
        if len(self.race_selected_rules) >= 4:
            self._flash("Max 4 rules — deselect one first")
            return True
        rs = self._prompt_text("Custom rule (e.g. B36/S23)")
        if rs:
            parsed = parse_rule_string(rs)
            if parsed:
                self.race_selected_rules.append((rs, parsed[0], parsed[1]))
            else:
                self._flash("Invalid rule string (use format B.../S...)")
        return True
    if key in (10, 13, curses.KEY_ENTER):  # Enter — start race
        if len(self.race_selected_rules) < 2:
            self._flash("Select at least 2 rules (Space=toggle, /=custom)")
            return True
        self._start_race()
        return True
    if key == ord("g"):  # Change max generations
        gs = self._prompt_text(f"Race duration in generations (current: {self.race_max_gens})")
        if gs:
            try:
                val = int(gs)
                if 10 <= val <= 10000:
                    self.race_max_gens = val
                else:
                    self._flash("Must be between 10 and 10000")
            except ValueError:
                self._flash("Invalid number")
        return True
    return True



def _draw_race_rule_menu(self, max_y: int, max_x: int):
    """Draw the multi-select rule menu for race mode."""
    title = "── Race Mode: Select 2-4 Rules (Space=toggle, Enter=start, /=custom, g=gens, q=cancel) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    sel_names = {n for n, b, s in self.race_selected_rules}
    info = f"Selected: {len(self.race_selected_rules)}/4  │  Duration: {self.race_max_gens} gens"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(info)) // 2), info,
                           curses.color_pair(6))
    except curses.error:
        pass

    for i, name in enumerate(self.rule_preset_list):
        y = 5 + i
        if y >= max_y - 2:
            break
        preset = RULE_PRESETS[name]
        rs = rule_string(preset["birth"], preset["survival"])
        check = "[X]" if name in sel_names else "[ ]"
        line = f"  {check} {name:<20s} {rs}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.race_rule_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        try:
            self.stdscr.addstr(y, 2, line, attr)
        except curses.error:
            pass

    # Show custom rules if any
    custom_y = 5 + len(self.rule_preset_list) + 1
    for i, (name, birth, survival) in enumerate(self.race_selected_rules):
        if name not in RULE_PRESETS:
            if custom_y < max_y - 2:
                rs = rule_string(birth, survival)
                line = f"  [X] {rs:<20s} (custom)"
                try:
                    self.stdscr.addstr(custom_y, 2, line[:max_x - 2],
                                       curses.color_pair(3))
                except curses.error:
                    pass
                custom_y += 1

    tip_y = max_y - 1
    if tip_y > 0:
        tip = " Space=toggle selection │ /=custom rule │ g=set duration │ Enter=start race │ q/Esc=cancel"
        try:
            self.stdscr.addstr(tip_y, 0, tip[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_race(self, max_y: int, max_x: int):
    """Draw the race mode view with tiled sub-grids and scoreboard."""
    n = len(self.race_grids)
    if n == 0:
        return

    # Layout: 2 columns, 1-2 rows depending on count
    # n=2: 1 row, 2 cols  |  n=3: 2 rows (2+1)  |  n=4: 2 rows, 2 cols
    if n <= 2:
        tile_rows, tile_cols = 1, n
    else:
        tile_rows, tile_cols = 2, 2

    scoreboard_h = n + 3  # header + n entries + separator + winner line
    grid_area_h = max_y - scoreboard_h - 1
    grid_area_w = max_x

    if grid_area_h < 4 or grid_area_w < 10:
        try:
            self.stdscr.addstr(0, 0, "Terminal too small for race mode", curses.color_pair(5))
        except curses.error:
            pass
        return

    # Each tile dimensions (in screen coords)
    tile_h = grid_area_h // tile_rows
    tile_w = grid_area_w // tile_cols

    # Draw each grid tile
    for idx in range(n):
        tr = idx // tile_cols  # tile row
        tc = idx % tile_cols   # tile column
        origin_y = tr * tile_h
        origin_x = tc * tile_w
        cell_vis_rows = tile_h - 2  # leave room for label
        cell_vis_cols = (tile_w - 1) // 2  # each cell = 2 screen cols

        g = self.race_grids[idx]
        name, birth, survival = self.race_selected_rules[idx]
        rs = rule_string(birth, survival)

        # Draw label bar at top of tile
        stats = self.race_stats[idx]
        label = f" {name} ({rs}) Pop:{g.population}"
        if stats.get("extinction_gen") is not None:
            label += " EXTINCT"
        elif stats.get("osc_period") is not None:
            label += f" Osc:{stats['osc_period']}"
        label = label[:tile_w - 1]
        # Color the label: winner gets special highlight
        label_attr = curses.color_pair(7) | curses.A_BOLD
        if self.race_finished and self.race_winner and name in self.race_winner:
            label_attr = curses.color_pair(3) | curses.A_BOLD
        try:
            self.stdscr.addstr(origin_y, origin_x, label, label_attr)
        except curses.error:
            pass

        # Draw cells
        view_r = self.cursor_r - cell_vis_rows // 2
        view_c = self.cursor_c - cell_vis_cols // 2
        for sy in range(min(cell_vis_rows, g.rows)):
            gr = (view_r + sy) % g.rows
            for sx in range(min(cell_vis_cols, g.cols)):
                gc = (view_c + sx) % g.cols
                age = g.cells[gr][gc]
                px = origin_x + sx * 2
                py = origin_y + 1 + sy
                if py >= origin_y + tile_h - 1 or px + 1 >= origin_x + tile_w:
                    continue
                if py >= grid_area_h or px + 1 >= max_x:
                    continue
                if age > 0:
                    try:
                        self.stdscr.addstr(py, px, CELL_CHAR, color_for_age(age))
                    except curses.error:
                        pass

        # Draw tile border (right edge) if not last column
        if tc < tile_cols - 1:
            border_x = origin_x + tile_w - 1
            if border_x < max_x:
                for sy in range(tile_h):
                    py = origin_y + sy
                    if py < grid_area_h:
                        try:
                            self.stdscr.addstr(py, border_x, "│",
                                               curses.color_pair(6) | curses.A_DIM)
                        except curses.error:
                            pass

        # Draw tile border (bottom edge) if not last row
        if tr < tile_rows - 1:
            border_y = origin_y + tile_h - 1
            if border_y < grid_area_h:
                for sx in range(tile_w):
                    px = origin_x + sx
                    if px < max_x:
                        try:
                            self.stdscr.addstr(border_y, px, "─",
                                               curses.color_pair(6) | curses.A_DIM)
                        except curses.error:
                            pass

    # Draw scoreboard at bottom
    sb_y = grid_area_h
    gens_elapsed = 0
    if self.race_grids:
        gens_elapsed = self.race_grids[0].generation - self.race_start_gen

    # Progress bar
    progress = min(1.0, gens_elapsed / max(1, self.race_max_gens))
    bar_w = max_x - 30
    if bar_w > 5:
        filled = int(bar_w * progress)
        bar = "█" * filled + "░" * (bar_w - filled)
        progress_line = f" Gen {gens_elapsed}/{self.race_max_gens} [{bar}] {int(progress * 100)}%"
        progress_line = progress_line[:max_x - 1]
        try:
            self.stdscr.addstr(sb_y, 0, progress_line,
                               curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Scoreboard header
    sb_y += 1
    header = f" {'#':<3s} {'Rule':<25s} {'Pop':>7s} {'Peak':>7s} {'Osc':>6s} {'Extinct':>8s} {'Score':>7s}"
    header = header[:max_x - 1]
    if sb_y < max_y:
        try:
            self.stdscr.addstr(sb_y, 0, header,
                               curses.color_pair(6) | curses.A_BOLD)
        except curses.error:
            pass

    # Scoreboard entries (sorted by score if finished, else by population)
    entries = []
    for i, (name, birth, survival) in enumerate(self.race_selected_rules):
        stats = self.race_stats[i]
        g = self.race_grids[i]
        rs = rule_string(birth, survival)
        score = stats.get("final_score", 0)
        entries.append((i, name, rs, g.population, stats))

    if self.race_finished:
        entries.sort(key=lambda e: e[4].get("final_score", 0), reverse=True)
    else:
        entries.sort(key=lambda e: e[3], reverse=True)

    for rank, (i, name, rs, pop, stats) in enumerate(entries):
        sb_y += 1
        if sb_y >= max_y - 1:
            break
        osc = str(stats["osc_period"]) if stats["osc_period"] is not None else "—"
        ext = str(stats["extinction_gen"] - self.race_start_gen) if stats["extinction_gen"] is not None else "alive"
        score_str = str(stats.get("final_score", "—")) if self.race_finished else "—"
        display_name = f"{name[:15]} {rs}"
        medal = ""
        if self.race_finished and rank == 0:
            medal = "👑 "
        line = f" {medal}{rank+1:<3d} {display_name:<25s} {pop:>7d} {stats['peak_pop']:>7d} {osc:>6s} {ext:>8s} {score_str:>7s}"
        line = line[:max_x - 1]
        attr = curses.color_pair(6)
        if self.race_finished and rank == 0:
            attr = curses.color_pair(3) | curses.A_BOLD
        elif stats["extinction_gen"] is not None:
            attr = curses.color_pair(5) | curses.A_DIM
        try:
            self.stdscr.addstr(sb_y, 0, line, attr)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        elif self.race_finished:
            hint = " Race complete! [Space]=restart [Z]=exit race [q]=quit"
        else:
            hint = " [Space]=play/pause [n]=step [+/-]=speed [Z]=exit race [Arrows]=scroll [q]=quit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register race mode methods on the App class."""
    App._enter_race_mode = _enter_race_mode
    App._exit_race_mode = _exit_race_mode
    App._handle_race_rule_menu_key = _handle_race_rule_menu_key
    App._draw_race_rule_menu = _draw_race_rule_menu
    App._draw_race = _draw_race

