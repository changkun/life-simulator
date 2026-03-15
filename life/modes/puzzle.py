"""Mode: puzzle — simulation mode for the life package."""
import curses
import math
import random
import time


from life.colors import color_for_age
from life.constants import CELL_CHAR
from life.grid import Grid
from life.patterns import PUZZLES
from life.utils import sparkline

def _enter_puzzle_mode(self):
    """Open the puzzle selection menu."""
    self.puzzle_menu = True
    self.puzzle_sel = 0
    self.puzzle_mode = False
    self.puzzle_phase = "idle"



def _exit_puzzle_mode(self):
    """Leave puzzle mode entirely."""
    self.puzzle_mode = False
    self.puzzle_menu = False
    self.puzzle_phase = "idle"
    self.puzzle_current = None
    self.puzzle_placed_cells.clear()
    self.puzzle_state_hashes.clear()
    self.puzzle_win_gen = None
    self._flash("Puzzle mode OFF")



def _puzzle_start_planning(self, puzzle: dict):
    """Begin the planning phase for a specific puzzle."""
    self.puzzle_current = puzzle
    self.puzzle_mode = True
    self.puzzle_menu = False
    self.puzzle_phase = "planning"
    self.puzzle_placed_cells.clear()
    self.puzzle_state_hashes.clear()
    self.puzzle_win_gen = None
    self.puzzle_sim_gen = 0
    self.puzzle_peak_pop = 0
    self.puzzle_score = 0
    self.puzzle_initial_bbox = None
    # Clear grid for a fresh start
    self.grid.clear()
    self.running = False
    self.pop_history.clear()
    self._record_pop()
    self._reset_cycle_detection()
    # Centre cursor
    self.cursor_r = self.grid.rows // 2
    self.cursor_c = self.grid.cols // 2
    self._flash(f"Puzzle: {puzzle['name']} — place cells, then press Enter to run!")



def _puzzle_run(self):
    """Transition from planning to running phase."""
    puzzle = self.puzzle_current
    if not puzzle:
        return
    n = len(self.puzzle_placed_cells)
    if n == 0:
        self._flash("Place at least one cell before running!")
        return
    max_cells = puzzle.get("max_cells", 999)
    if n > max_cells:
        self._flash(f"Too many cells! Max {max_cells}, you placed {n}")
        return
    self.puzzle_phase = "running"
    self.puzzle_start_pop = n
    self.puzzle_sim_gen = 0
    self.puzzle_peak_pop = n
    self.puzzle_state_hashes.clear()
    self.puzzle_state_hashes[self.grid.state_hash()] = 0
    # Compute initial bounding box for escape_box puzzles
    if puzzle["type"] == "escape_box":
        rows = [r for r, c in self.puzzle_placed_cells]
        cols = [c for r, c in self.puzzle_placed_cells]
        mid_r = (min(rows) + max(rows)) // 2
        mid_c = (min(cols) + max(cols)) // 2
        half = puzzle.get("box_size", 10) // 2
        self.puzzle_initial_bbox = (mid_r - half, mid_c - half,
                                    mid_r + half, mid_c + half)
    self.running = True
    self._flash("Simulating...")



def _puzzle_step(self):
    """Advance one generation and check win/loss conditions."""
    puzzle = self.puzzle_current
    if not puzzle or self.puzzle_phase != "running":
        return
    self.grid.step()
    self._record_pop()
    self.puzzle_sim_gen += 1
    pop = self.grid.population
    if pop > self.puzzle_peak_pop:
        self.puzzle_peak_pop = pop

    sim_gens = puzzle.get("sim_gens", 100)
    ptype = puzzle["type"]

    # Cycle detection for puzzles
    h = self.grid.state_hash()
    cycle_period = None
    if h in self.puzzle_state_hashes:
        cycle_period = self.puzzle_sim_gen - self.puzzle_state_hashes[h]
    else:
        self.puzzle_state_hashes[h] = self.puzzle_sim_gen

    # Check win conditions by puzzle type
    if ptype == "still_life":
        if cycle_period is not None and cycle_period == 1 and pop > 0:
            self._puzzle_win()
            return
        if pop == 0:
            self._puzzle_fail("All cells died — not a still life!")
            return
        if self.puzzle_sim_gen >= sim_gens:
            self._puzzle_fail("Did not stabilise into a still life in time.")
            return

    elif ptype == "oscillator":
        min_period = puzzle.get("min_period", 2)
        if cycle_period is not None and cycle_period >= min_period and pop > 0:
            self.puzzle_win_gen = self.puzzle_sim_gen
            self._puzzle_win()
            return
        if pop == 0:
            self._puzzle_fail("All cells died — not an oscillator!")
            return
        if self.puzzle_sim_gen >= sim_gens:
            if cycle_period is not None and cycle_period == 1 and pop > 0:
                self._puzzle_fail(f"Stable still life (period 1) — need period >= {min_period}.")
            else:
                self._puzzle_fail("Did not form an oscillator in time.")
            return

    elif ptype == "reach_population":
        target = puzzle.get("target_pop", 50)
        if pop >= target:
            self.puzzle_win_gen = self.puzzle_sim_gen
            self._puzzle_win()
            return
        if pop == 0:
            self._puzzle_fail("All cells died before reaching the target population!")
            return
        if self.puzzle_sim_gen >= sim_gens:
            self._puzzle_fail(f"Peak population {self.puzzle_peak_pop} — needed {target}.")
            return

    elif ptype == "escape_box":
        if self.puzzle_initial_bbox and pop > 0:
            min_r, min_c, max_r, max_c = self.puzzle_initial_bbox
            escaped = False
            for r in range(self.grid.rows):
                for c in range(self.grid.cols):
                    if self.grid.cells[r][c] > 0:
                        if r < min_r or r > max_r or c < min_c or c > max_c:
                            escaped = True
                            break
                if escaped:
                    break
            if escaped:
                self.puzzle_win_gen = self.puzzle_sim_gen
                self._puzzle_win()
                return
        if pop == 0:
            self._puzzle_fail("All cells died before escaping the box!")
            return
        if self.puzzle_sim_gen >= sim_gens:
            self._puzzle_fail("Pattern did not escape the bounding box in time.")
            return

    elif ptype == "extinction":
        if pop == 0:
            self.puzzle_win_gen = self.puzzle_sim_gen
            self._puzzle_win()
            return
        if cycle_period is not None and pop > 0:
            self._puzzle_fail("Pattern stabilised — it won't go extinct!")
            return
        if self.puzzle_sim_gen >= sim_gens:
            self._puzzle_fail(f"Population still {pop} after {sim_gens} generations.")
            return

    elif ptype == "survive_gens":
        target_gens = puzzle.get("target_gens", 500)
        # Fail if extinct or still life before target
        if pop == 0:
            self._puzzle_fail(f"Went extinct at gen {self.puzzle_sim_gen} — needed {target_gens}+ active.")
            return
        if cycle_period is not None and cycle_period == 1:
            self._puzzle_fail(f"Became a still life at gen {self.puzzle_sim_gen} — needed active for {target_gens}+ gens.")
            return
        if self.puzzle_sim_gen >= target_gens:
            self._puzzle_win()
            return
        if self.puzzle_sim_gen >= sim_gens:
            self._puzzle_fail(f"Simulation ended. Pattern didn't stay active long enough.")
            return



def _puzzle_win(self):
    """Handle a puzzle win."""
    self.running = False
    self.puzzle_phase = "success"
    puzzle = self.puzzle_current
    # Score: fewer cells = better, bonus for fewer generations to win
    cells_used = len(self.puzzle_placed_cells)
    max_cells = puzzle.get("max_cells", cells_used)
    # Base score: 100 * (max_cells / cells_used), clamped
    if cells_used > 0:
        cell_bonus = int(100 * max_cells / cells_used)
    else:
        cell_bonus = 100
    # Speed bonus: for types where winning fast matters
    gen_bonus = 0
    if self.puzzle_win_gen is not None:
        sim_gens = puzzle.get("sim_gens", 100)
        remaining = sim_gens - self.puzzle_win_gen
        gen_bonus = int(50 * remaining / max(1, sim_gens))
    self.puzzle_score = min(999, cell_bonus + gen_bonus)
    # Track best score
    pid = puzzle["id"]
    if pid not in self.puzzle_scores or self.puzzle_score > self.puzzle_scores[pid]:
        self.puzzle_scores[pid] = self.puzzle_score
    self._flash(f"PUZZLE SOLVED! Score: {self.puzzle_score} ({cells_used} cells used)")



def _puzzle_fail(self, reason: str):
    """Handle a puzzle failure."""
    self.running = False
    self.puzzle_phase = "fail"
    self.puzzle_score = 0
    self._flash(f"FAILED: {reason}")



def _handle_puzzle_menu_key(self, key: int) -> bool:
    """Handle input in the puzzle selection menu."""
    if key == -1:
        return True
    if key == 27 or key == ord("q"):
        self.puzzle_menu = False
        return True
    if key in (curses.KEY_UP, ord("k")):
        self.puzzle_sel = (self.puzzle_sel - 1) % len(PUZZLES)
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.puzzle_sel = (self.puzzle_sel + 1) % len(PUZZLES)
        return True
    if key in (10, 13, curses.KEY_ENTER):
        self._puzzle_start_planning(PUZZLES[self.puzzle_sel])
        return True
    return True



def _handle_puzzle_planning_key(self, key: int) -> bool:
    """Handle input during puzzle planning phase (place cells)."""
    if key == -1:
        return True
    puzzle = self.puzzle_current
    if not puzzle:
        return True
    max_cells = puzzle.get("max_cells", 999)

    if key == 27:  # ESC — exit puzzle
        self._exit_puzzle_mode()
        return True
    if key in (10, 13, curses.KEY_ENTER):  # Enter — run simulation
        self._puzzle_run()
        return True
    if key == ord("e"):  # Toggle cell
        pos = (self.cursor_r, self.cursor_c)
        if pos in self.puzzle_placed_cells:
            self.grid.set_dead(self.cursor_r, self.cursor_c)
            self.puzzle_placed_cells.discard(pos)
        else:
            if len(self.puzzle_placed_cells) >= max_cells:
                self._flash(f"Max {max_cells} cells! Remove some first.")
            else:
                self.grid.set_alive(self.cursor_r, self.cursor_c)
                self.puzzle_placed_cells.add(pos)
        return True
    if key == ord("d"):  # Draw mode
        if self.draw_mode == "draw":
            self.draw_mode = None
            self._flash("Draw mode OFF")
        else:
            self.draw_mode = "draw"
            if len(self.puzzle_placed_cells) < max_cells:
                pos = (self.cursor_r, self.cursor_c)
                self.grid.set_alive(self.cursor_r, self.cursor_c)
                self.puzzle_placed_cells.add(pos)
            self._flash("Draw mode ON (move to paint)")
        return True
    if key == ord("x"):  # Erase mode
        if self.draw_mode == "erase":
            self.draw_mode = None
            self._flash("Erase mode OFF")
        else:
            self.draw_mode = "erase"
            pos = (self.cursor_r, self.cursor_c)
            self.grid.set_dead(self.cursor_r, self.cursor_c)
            self.puzzle_placed_cells.discard(pos)
            self._flash("Erase mode ON (move to erase)")
        return True
    if key == ord("c"):  # Clear all placed cells
        self.grid.clear()
        self.puzzle_placed_cells.clear()
        self._flash("Cleared all cells")
        return True
    if key == ord("?"):  # Show hint
        hint = puzzle.get("hint", "No hint available.")
        self._flash(f"Hint: {hint}")
        return True
    # Arrow / vim keys for cursor movement
    moved = False
    if key in (curses.KEY_UP, ord("k")):
        self.cursor_r = (self.cursor_r - 1) % self.grid.rows
        moved = True
    elif key in (curses.KEY_DOWN, ord("j")):
        self.cursor_r = (self.cursor_r + 1) % self.grid.rows
        moved = True
    elif key in (curses.KEY_LEFT, ord("h")):
        self.cursor_c = (self.cursor_c - 1) % self.grid.cols
        moved = True
    elif key in (curses.KEY_RIGHT, ord("l")):
        self.cursor_c = (self.cursor_c + 1) % self.grid.cols
        moved = True
    if moved and self.draw_mode:
        pos = (self.cursor_r, self.cursor_c)
        if self.draw_mode == "draw":
            if len(self.puzzle_placed_cells) < max_cells:
                self.grid.set_alive(self.cursor_r, self.cursor_c)
                self.puzzle_placed_cells.add(pos)
        elif self.draw_mode == "erase":
            self.grid.set_dead(self.cursor_r, self.cursor_c)
            self.puzzle_placed_cells.discard(pos)
    return True  # consume all keys in puzzle planning



def _handle_puzzle_result_key(self, key: int) -> bool:
    """Handle input on puzzle success/fail screen."""
    if key == -1:
        return True
    if key == ord("r") or key == ord("R"):  # Retry
        self._puzzle_start_planning(self.puzzle_current)
        return True
    if key == ord("q") or key == 27:  # Quit puzzle mode
        self._exit_puzzle_mode()
        return True
    if key == ord("n") or key in (10, 13, curses.KEY_ENTER):  # Next puzzle
        idx = next((i for i, p in enumerate(PUZZLES) if p["id"] == self.puzzle_current["id"]), 0)
        if idx + 1 < len(PUZZLES):
            self._puzzle_start_planning(PUZZLES[idx + 1])
        else:
            self._flash("That was the last puzzle! Press q to exit.")
        return True
    if key == ord("l"):  # Back to puzzle list
        self._enter_puzzle_mode()
        return True
    return True

# ── Mode Browser ──────────────────────────────────────────────────────────



def _draw_puzzle_menu(self, max_y: int, max_x: int):
    """Draw the puzzle selection menu."""
    title = "── Puzzle / Challenge Mode (Enter=start, q/Esc=cancel) ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Solve cellular automata challenges with the fewest cells possible!"
    try:
        self.stdscr.addstr(3, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass

    for i, puzzle in enumerate(PUZZLES):
        y = 5 + i
        if y >= max_y - 2:
            break
        pid = puzzle["id"]
        best = self.puzzle_scores.get(pid)
        solved_mark = f" [Best: {best}]" if best is not None else ""
        check = "+" if best is not None else " "
        line = f"  [{check}] {pid:>2d}. {puzzle['name']:<22s} {puzzle['description'][:max_x - 40]}{solved_mark}"
        line = line[:max_x - 2]
        attr = curses.color_pair(6)
        if i == self.puzzle_sel:
            attr = curses.color_pair(7) | curses.A_REVERSE
        elif best is not None:
            attr = curses.color_pair(3)
        try:
            self.stdscr.addstr(y, 2, line, attr)
        except curses.error:
            pass

    tip_y = max_y - 1
    if tip_y > 0:
        tip = " Up/Down=select │ Enter=start puzzle │ q/Esc=cancel"
        try:
            self.stdscr.addstr(tip_y, 0, tip[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_puzzle(self, max_y: int, max_x: int):
    """Draw the puzzle mode UI (planning, running, or result)."""
    puzzle = self.puzzle_current
    if not puzzle:
        return

    # Header
    phase_label = {"planning": "PLANNING", "running": "SIMULATING",
                   "success": "SOLVED!", "fail": "FAILED"}.get(self.puzzle_phase, "")
    cells_used = len(self.puzzle_placed_cells)
    max_cells = puzzle.get("max_cells", 999)
    header = f" Puzzle #{puzzle['id']}: {puzzle['name']}  │  {phase_label}  │  Cells: {cells_used}/{max_cells}"
    header = header[:max_x - 1]
    try:
        if self.puzzle_phase == "success":
            attr = curses.color_pair(3) | curses.A_BOLD
        elif self.puzzle_phase == "fail":
            attr = curses.color_pair(5) | curses.A_BOLD
        else:
            attr = curses.color_pair(7) | curses.A_BOLD
        self.stdscr.addstr(0, 0, header, attr)
    except curses.error:
        pass

    # Goal text
    goal = f" Goal: {puzzle['goal_text']}"
    goal = goal[:max_x - 1]
    try:
        self.stdscr.addstr(1, 0, goal, curses.color_pair(6))
    except curses.error:
        pass

    # Grid rendering
    grid_start_y = 2
    vis_rows = max_y - 7  # leave room for header, goal, status, hint
    vis_cols = (max_x - 1) // 2

    # Centre viewport on cursor
    self.view_r = self.cursor_r - vis_rows // 2
    self.view_c = self.cursor_c - vis_cols // 2

    # Bounding box for escape_box puzzle visualisation
    bbox = self.puzzle_initial_bbox
    if bbox is None and puzzle["type"] == "escape_box" and self.puzzle_placed_cells:
        # Preview bbox centered on placed cells during planning
        rows_p = [r for r, c in self.puzzle_placed_cells]
        cols_p = [c for r, c in self.puzzle_placed_cells]
        mid_r = (min(rows_p) + max(rows_p)) // 2
        mid_c = (min(cols_p) + max(cols_p)) // 2
        half = puzzle.get("box_size", 10) // 2
        bbox = (mid_r - half, mid_c - half, mid_r + half, mid_c + half)

    for sy in range(min(vis_rows, self.grid.rows)):
        gr = (self.view_r + sy) % self.grid.rows
        for sx in range(min(vis_cols, self.grid.cols)):
            gc = (self.view_c + sx) % self.grid.cols
            age = self.grid.cells[gr][gc]
            is_cursor = (gr == self.cursor_r and gc == self.cursor_c)
            px = sx * 2
            py = grid_start_y + sy
            if py >= max_y - 4 or px + 1 >= max_x:
                continue
            # Draw bounding box border for escape_box
            in_bbox_border = False
            if bbox and self.puzzle_phase in ("planning", "running"):
                br0, bc0, br1, bc1 = bbox
                if ((gr == br0 or gr == br1) and bc0 <= gc <= bc1) or \
                   ((gc == bc0 or gc == bc1) and br0 <= gr <= br1):
                    in_bbox_border = True
            if age > 0:
                attr = color_for_age(age)
                if is_cursor:
                    attr |= curses.A_REVERSE
                try:
                    self.stdscr.addstr(py, px, CELL_CHAR, attr)
                except curses.error:
                    pass
            elif in_bbox_border:
                try:
                    self.stdscr.addstr(py, px, "··", curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass
            elif is_cursor:
                try:
                    self.stdscr.addstr(py, px, "▒▒", curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass

    # Progress / status bar
    status_y = max_y - 4
    if status_y > 0:
        if self.puzzle_phase == "running":
            sim_gens = puzzle.get("sim_gens", 100)
            progress = min(1.0, self.puzzle_sim_gen / max(1, sim_gens))
            bar_w = max_x - 40
            if bar_w > 5:
                filled = int(bar_w * progress)
                bar = "█" * filled + "░" * (bar_w - filled)
                status = f" Gen {self.puzzle_sim_gen}/{sim_gens} [{bar}] Pop: {self.grid.population} Peak: {self.puzzle_peak_pop}"
            else:
                status = f" Gen {self.puzzle_sim_gen}/{sim_gens} Pop: {self.grid.population}"
            status = status[:max_x - 1]
            try:
                self.stdscr.addstr(status_y, 0, status, curses.color_pair(7))
            except curses.error:
                pass
        elif self.puzzle_phase == "success":
            score_line = f" SCORE: {self.puzzle_score}  │  Cells used: {cells_used}  │  "
            if self.puzzle_win_gen is not None:
                score_line += f"Won at gen {self.puzzle_win_gen}"
            else:
                score_line += f"Completed in {self.puzzle_sim_gen} gens"
            best = self.puzzle_scores.get(puzzle["id"], 0)
            score_line += f"  │  Best: {best}"
            score_line = score_line[:max_x - 1]
            try:
                self.stdscr.addstr(status_y, 0, score_line, curses.color_pair(3) | curses.A_BOLD)
            except curses.error:
                pass
        elif self.puzzle_phase == "fail":
            fail_line = f" {self.message}" if self.message else " Failed!"
            fail_line = fail_line[:max_x - 1]
            try:
                self.stdscr.addstr(status_y, 0, fail_line, curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

    # Sparkline
    spark_y = max_y - 3
    if spark_y > 0 and len(self.pop_history) > 1:
        spark_width = max_x - 16
        if spark_width > 0:
            spark_str = sparkline(self.pop_history, spark_width)
            label = " Pop history: "
            try:
                self.stdscr.addstr(spark_y, 0, label, curses.color_pair(6) | curses.A_DIM)
                self.stdscr.addstr(spark_y, len(label), spark_str, curses.color_pair(1))
            except curses.error:
                pass

    # Status / mode bar
    mode_y = max_y - 2
    if mode_y > 0:
        mode_info = f" Gen: {self.grid.generation}  │  Pop: {self.grid.population}"
        if self.draw_mode == "draw":
            mode_info += "  │  DRAW MODE"
        elif self.draw_mode == "erase":
            mode_info += "  │  ERASE MODE"
        mode_info = mode_info[:max_x - 1]
        try:
            self.stdscr.addstr(mode_y, 0, mode_info, curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 4.0:
            hint = f" {self.message}"
        elif self.puzzle_phase == "planning":
            hint = " [e]=toggle cell [d]=draw [x]=erase [c]=clear [?]=hint [Enter]=run [Esc]=quit"
        elif self.puzzle_phase == "running":
            hint = " Simulating... [Esc]=abort"
        elif self.puzzle_phase == "success":
            hint = " [r]=retry [n/Enter]=next puzzle [l]=puzzle list [q]=quit"
        elif self.puzzle_phase == "fail":
            hint = " [r]=retry [l]=puzzle list [q]=quit"
        else:
            hint = ""
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register puzzle mode methods on the App class."""
    App._enter_puzzle_mode = _enter_puzzle_mode
    App._exit_puzzle_mode = _exit_puzzle_mode
    App._puzzle_start_planning = _puzzle_start_planning
    App._puzzle_run = _puzzle_run
    App._puzzle_step = _puzzle_step
    App._puzzle_win = _puzzle_win
    App._puzzle_fail = _puzzle_fail
    App._handle_puzzle_menu_key = _handle_puzzle_menu_key
    App._handle_puzzle_planning_key = _handle_puzzle_planning_key
    App._handle_puzzle_result_key = _handle_puzzle_result_key
    App._draw_puzzle_menu = _draw_puzzle_menu
    App._draw_puzzle = _draw_puzzle

