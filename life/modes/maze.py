"""Mode: maze — simulation mode for the life package."""
import curses
import math
import random
import time


def _enter_maze_mode(self):
    """Enter Maze mode — show preset menu."""
    self.maze_menu = True
    self.maze_menu_sel = 0
    self._flash("Maze Generation & Pathfinding — select a configuration")



def _exit_maze_mode(self):
    """Exit Maze mode."""
    self.maze_mode = False
    self.maze_menu = False
    self.maze_running = False
    self.maze_grid = []
    self.maze_gen_stack = []
    self.maze_gen_edges = []
    self.maze_gen_visited = set()
    self.maze_gen_sets = {}
    self.maze_solve_queue = []
    self.maze_solve_visited = set()
    self.maze_solve_parent = {}
    self.maze_solve_path = []
    self._flash("Maze mode OFF")



def _maze_init(self, preset_idx: int):
    """Initialize maze simulation with the given preset."""
    name, _desc, gen_algo, solve_algo, _scale = self.MAZE_PRESETS[preset_idx]
    self.maze_preset_name = name
    self.maze_gen_algo = gen_algo
    self.maze_solve_algo = solve_algo
    self.maze_generation = 0
    self.maze_running = False
    self.maze_phase = "generating"
    self.maze_gen_steps = 0
    self.maze_solve_steps = 0
    self.maze_solve_done = False

    max_y, max_x = self.stdscr.getmaxyx()
    # Maze dimensions must be odd for wall/passage grid
    raw_rows = max(11, max_y - 3)
    raw_cols = max(11, (max_x - 1) // 2)
    self.maze_rows = raw_rows if raw_rows % 2 == 1 else raw_rows - 1
    self.maze_cols = raw_cols if raw_cols % 2 == 1 else raw_cols - 1
    rows, cols = self.maze_rows, self.maze_cols

    # Initialize grid: all walls
    self.maze_grid = [[0] * cols for _ in range(rows)]

    # Start and end positions (top-left and bottom-right passage cells)
    self.maze_start = (1, 1)
    self.maze_end = (rows - 2, cols - 2)

    # Initialize generation algorithm state
    self.maze_gen_visited = set()
    self.maze_gen_stack = []
    self.maze_gen_edges = []
    self.maze_gen_sets = {}

    if gen_algo == "backtracker":
        # Recursive backtracker (DFS-based)
        sr, sc = 1, 1
        self.maze_grid[sr][sc] = 1
        self.maze_gen_visited.add((sr, sc))
        self.maze_gen_stack = [(sr, sc)]
    elif gen_algo == "prim":
        # Prim's algorithm
        sr, sc = 1, 1
        self.maze_grid[sr][sc] = 1
        self.maze_gen_visited.add((sr, sc))
        self._maze_add_prim_edges(sr, sc)
    elif gen_algo == "kruskal":
        # Kruskal's algorithm — list all possible edges, shuffle
        set_id = 0
        for r in range(1, rows, 2):
            for c in range(1, cols, 2):
                self.maze_grid[r][c] = 1
                self.maze_gen_sets[(r, c)] = set_id
                set_id += 1
        edges = []
        for r in range(1, rows, 2):
            for c in range(1, cols, 2):
                if r + 2 < rows:
                    edges.append((r, c, r + 2, c))
                if c + 2 < cols:
                    edges.append((r, c, r, c + 2))
        random.shuffle(edges)
        self.maze_gen_edges = edges

    # Reset solver state
    self.maze_solve_queue = []
    self.maze_solve_visited = set()
    self.maze_solve_parent = {}
    self.maze_solve_path = []

    self.maze_menu = False
    self.maze_mode = True
    self._flash(f"Maze: {name} — Space to start")



def _maze_add_prim_edges(self, r: int, c: int):
    """Add frontier edges from cell (r, c) for Prim's algorithm."""
    rows, cols = self.maze_rows, self.maze_cols
    for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        nr, nc = r + dr, c + dc
        if 0 < nr < rows and 0 < nc < cols and (nr, nc) not in self.maze_gen_visited:
            self.maze_gen_edges.append((r, c, nr, nc))



def _maze_step(self):
    """Advance maze simulation by one step."""
    if self.maze_phase == "generating":
        self._maze_gen_step()
    elif self.maze_phase == "solving":
        self._maze_solve_step()
    self.maze_generation += 1



def _maze_gen_step(self):
    """One step of maze generation."""
    if self.maze_gen_algo == "backtracker":
        self._maze_gen_backtracker_step()
    elif self.maze_gen_algo == "prim":
        self._maze_gen_prim_step()
    elif self.maze_gen_algo == "kruskal":
        self._maze_gen_kruskal_step()



def _maze_gen_backtracker_step(self):
    """Recursive backtracker — one step."""
    if not self.maze_gen_stack:
        self.maze_phase = "solving"
        self._maze_init_solver()
        return
    rows, cols = self.maze_rows, self.maze_cols
    cr, cc = self.maze_gen_stack[-1]
    # Find unvisited neighbors (2 cells away)
    neighbors = []
    for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        nr, nc = cr + dr, cc + dc
        if 0 < nr < rows and 0 < nc < cols and (nr, nc) not in self.maze_gen_visited:
            neighbors.append((nr, nc, cr + dr // 2, cc + dc // 2))
    if neighbors:
        nr, nc, wr, wc = random.choice(neighbors)
        self.maze_grid[wr][wc] = 1  # carve wall between
        self.maze_grid[nr][nc] = 1  # carve destination
        self.maze_gen_visited.add((nr, nc))
        self.maze_gen_stack.append((nr, nc))
        self.maze_gen_steps += 1
    else:
        self.maze_gen_stack.pop()  # backtrack



def _maze_gen_prim_step(self):
    """Prim's algorithm — one step."""
    if not self.maze_gen_edges:
        self.maze_phase = "solving"
        self._maze_init_solver()
        return
    # Pick a random edge from the frontier
    idx = random.randint(0, len(self.maze_gen_edges) - 1)
    fr, fc, nr, nc = self.maze_gen_edges.pop(idx)
    if (nr, nc) not in self.maze_gen_visited:
        # Carve the wall between fr,fc and nr,nc
        wr = (fr + nr) // 2
        wc = (fc + nc) // 2
        self.maze_grid[wr][wc] = 1
        self.maze_grid[nr][nc] = 1
        self.maze_gen_visited.add((nr, nc))
        self._maze_add_prim_edges(nr, nc)
        self.maze_gen_steps += 1



def _maze_gen_kruskal_step(self):
    """Kruskal's algorithm — one step."""
    if not self.maze_gen_edges:
        self.maze_phase = "solving"
        self._maze_init_solver()
        return
    r1, c1, r2, c2 = self.maze_gen_edges.pop()
    s1 = self.maze_gen_sets.get((r1, c1), -1)
    s2 = self.maze_gen_sets.get((r2, c2), -1)
    if s1 != s2 and s1 >= 0 and s2 >= 0:
        # Merge sets — carve wall
        wr = (r1 + r2) // 2
        wc = (c1 + c2) // 2
        self.maze_grid[wr][wc] = 1
        # Merge: replace all s2 with s1
        old_set = s2
        for cell, sid in self.maze_gen_sets.items():
            if sid == old_set:
                self.maze_gen_sets[cell] = s1
        self.maze_gen_steps += 1



def _maze_init_solver(self):
    """Initialize the pathfinding solver after maze generation is complete."""
    self._flash("Maze generated! Now solving...")
    sr, sc = self.maze_start
    er, ec = self.maze_end
    # Ensure start and end are passages
    self.maze_grid[sr][sc] = 1
    self.maze_grid[er][ec] = 1
    self.maze_solve_visited = set()
    self.maze_solve_parent = {}
    self.maze_solve_path = []
    self.maze_solve_done = False
    self.maze_solve_steps = 0

    if self.maze_solve_algo == "astar":
        # Priority queue: (f_score, g_score, r, c)

        g = 0
        h = abs(er - sr) + abs(ec - sc)
        self.maze_solve_queue = [(g + h, g, sr, sc)]
        self.maze_solve_visited.add((sr, sc))
    elif self.maze_solve_algo == "dijkstra":

        self.maze_solve_queue = [(0, sr, sc)]
        self.maze_solve_visited.add((sr, sc))
    elif self.maze_solve_algo == "bfs":
        self.maze_solve_queue = [(sr, sc)]
        self.maze_solve_visited.add((sr, sc))
    elif self.maze_solve_algo == "dfs":
        self.maze_solve_queue = [(sr, sc)]
        self.maze_solve_visited.add((sr, sc))



def _maze_solve_step(self):
    """One step of pathfinding."""
    if self.maze_solve_done or not self.maze_solve_queue:
        if not self.maze_solve_done:
            self.maze_solve_done = True
            self.maze_phase = "done"
            self._flash("No path found!")
        return
    algo = self.maze_solve_algo
    er, ec = self.maze_end
    rows, cols = self.maze_rows, self.maze_cols

    if algo == "astar":

        _f, g, cr, cc = heapq.heappop(self.maze_solve_queue)
        if (cr, cc) == (er, ec):
            self._maze_reconstruct_path()
            return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and self.maze_grid[nr][nc] == 1 and (nr, nc) not in self.maze_solve_visited:
                self.maze_solve_visited.add((nr, nc))
                self.maze_solve_parent[(nr, nc)] = (cr, cc)
                ng = g + 1
                h = abs(er - nr) + abs(ec - nc)
                heapq.heappush(self.maze_solve_queue, (ng + h, ng, nr, nc))
        self.maze_solve_steps += 1

    elif algo == "dijkstra":

        dist, cr, cc = heapq.heappop(self.maze_solve_queue)
        if (cr, cc) == (er, ec):
            self._maze_reconstruct_path()
            return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and self.maze_grid[nr][nc] == 1 and (nr, nc) not in self.maze_solve_visited:
                self.maze_solve_visited.add((nr, nc))
                self.maze_solve_parent[(nr, nc)] = (cr, cc)
                heapq.heappush(self.maze_solve_queue, (dist + 1, nr, nc))
        self.maze_solve_steps += 1

    elif algo == "bfs":
        cr, cc = self.maze_solve_queue.pop(0)
        if (cr, cc) == (er, ec):
            self._maze_reconstruct_path()
            return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and self.maze_grid[nr][nc] == 1 and (nr, nc) not in self.maze_solve_visited:
                self.maze_solve_visited.add((nr, nc))
                self.maze_solve_parent[(nr, nc)] = (cr, cc)
                self.maze_solve_queue.append((nr, nc))
        self.maze_solve_steps += 1

    elif algo == "dfs":
        cr, cc = self.maze_solve_queue.pop()  # stack — LIFO
        if (cr, cc) == (er, ec):
            self._maze_reconstruct_path()
            return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and self.maze_grid[nr][nc] == 1 and (nr, nc) not in self.maze_solve_visited:
                self.maze_solve_visited.add((nr, nc))
                self.maze_solve_parent[(nr, nc)] = (cr, cc)
                self.maze_solve_queue.append((nr, nc))
        self.maze_solve_steps += 1



def _maze_reconstruct_path(self):
    """Trace back from end to start to build the solution path."""
    path = []
    cur = self.maze_end
    while cur != self.maze_start and cur in self.maze_solve_parent:
        path.append(cur)
        cur = self.maze_solve_parent[cur]
    path.append(self.maze_start)
    path.reverse()
    self.maze_solve_path = path
    self.maze_solve_done = True
    self.maze_phase = "done"
    self._flash(f"Path found! Length={len(path)}, explored={len(self.maze_solve_visited)} cells")



def _handle_maze_menu_key(self, key: int) -> bool:
    """Handle input in Maze preset menu."""
    n = len(self.MAZE_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.maze_menu_sel = (self.maze_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.maze_menu_sel = (self.maze_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._maze_init(self.maze_menu_sel)
    elif key in (ord("q"), 27):
        self.maze_menu = False
        self._flash("Maze mode cancelled")
    return True



def _handle_maze_key(self, key: int) -> bool:
    """Handle input in active Maze simulation."""
    if key == ord(" "):
        self.maze_running = not self.maze_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.maze_steps_per_frame):
            self._maze_step()
    elif key == ord("r"):
        idx = next((i for i, p in enumerate(self.MAZE_PRESETS)
                    if p[0] == self.maze_preset_name), 0)
        self._maze_init(idx)
        self.maze_running = False
    elif key == ord("R"):
        self.maze_mode = False
        self.maze_running = False
        self.maze_menu = True
        self.maze_menu_sel = 0
    elif key == ord("s"):
        self.maze_steps_per_frame = min(20, self.maze_steps_per_frame + 1)
        self._flash(f"Steps/frame: {self.maze_steps_per_frame}")
    elif key == ord("S"):
        self.maze_steps_per_frame = max(1, self.maze_steps_per_frame - 1)
        self._flash(f"Steps/frame: {self.maze_steps_per_frame}")
    elif key in (ord("q"), 27):
        self._exit_maze_mode()
    return True



def _draw_maze_menu(self, max_y: int, max_x: int):
    """Draw the Maze preset selection menu."""
    self.stdscr.erase()
    title = "── Maze Generation & Pathfinding — Select Preset ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    for i, (name, desc, *_) in enumerate(self.MAZE_PRESETS):
        y = 3 + i
        if y >= max_y - 1:
            break
        marker = "▶ " if i == self.maze_menu_sel else "  "
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.maze_menu_sel else curses.color_pair(6)
        line = f"{marker}{name:22s} — {desc}"
        try:
            self.stdscr.addstr(y, 4, line[:max_x - 5], attr)
        except curses.error:
            pass
    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_maze(self, max_y: int, max_x: int):
    """Draw the active Maze simulation."""
    self.stdscr.erase()
    rows, cols = self.maze_rows, self.maze_cols
    grid = self.maze_grid
    state = "▶ RUNNING" if self.maze_running else "⏸ PAUSED"
    phase_label = self.maze_phase.upper()

    title = (f" Maze: {self.maze_preset_name}  |  phase={phase_label}"
             f"  |  gen steps={self.maze_gen_steps}  solve steps={self.maze_solve_steps}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Build sets for fast lookup
    solve_visited = self.maze_solve_visited
    solve_path_set = set(self.maze_solve_path)
    gen_stack_set = set(self.maze_gen_stack[-10:]) if self.maze_gen_stack else set()
    sr, sc = self.maze_start
    er, ec = self.maze_end

    # Determine the current generation head for highlighting
    gen_head = self.maze_gen_stack[-1] if self.maze_gen_stack else None

    view_rows = min(rows, max_y - 3)
    view_cols = min(cols, (max_x - 1) // 2)

    for r in range(view_rows):
        for c in range(view_cols):
            # Start position
            if (r, c) == (sr, sc):
                try:
                    self.stdscr.addstr(1 + r, c * 2, "SS",
                                       curses.color_pair(2) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            # End position
            if (r, c) == (er, ec):
                try:
                    self.stdscr.addstr(1 + r, c * 2, "EE",
                                       curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            # Solution path
            if (r, c) in solve_path_set:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "██",
                                       curses.color_pair(2) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            # Solver visited (explored)
            if (r, c) in solve_visited:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "░░",
                                       curses.color_pair(4))
                except curses.error:
                    pass
                continue
            # Generation head (current carving position)
            if gen_head and (r, c) == gen_head:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "██",
                                       curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            # Generation stack trail (recent backtracker positions)
            if (r, c) in gen_stack_set:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "▓▓",
                                       curses.color_pair(3))
                except curses.error:
                    pass
                continue
            # Wall vs passage
            if grid[r][c] == 0:
                # Wall
                try:
                    self.stdscr.addstr(1 + r, c * 2, "██",
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass
            else:
                # Passage
                try:
                    self.stdscr.addstr(1 + r, c * 2, "  ", curses.color_pair(0))
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        explored = len(self.maze_solve_visited)
        path_len = len(self.maze_solve_path)
        info = (f" Phase: {phase_label}  |  gen={self.maze_gen_algo}  solve={self.maze_solve_algo}"
                f"  |  gen_steps={self.maze_gen_steps}  solve_steps={self.maze_solve_steps}"
                f"  |  explored={explored}  path={path_len}"
                f"  |  steps/f={self.maze_steps_per_frame}")
        try:
            self.stdscr.addstr(status_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=play [n]=step [s/S]=speed+/- [r]=reseed [R]=menu [q]=exit"
        hint = hint[:max_x - 1]
        try:
            self.stdscr.addstr(hint_y, 0, hint, curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass




def register(App):
    """Register maze mode methods on the App class."""
    App._enter_maze_mode = _enter_maze_mode
    App._exit_maze_mode = _exit_maze_mode
    App._maze_init = _maze_init
    App._maze_add_prim_edges = _maze_add_prim_edges
    App._maze_step = _maze_step
    App._maze_gen_step = _maze_gen_step
    App._maze_gen_backtracker_step = _maze_gen_backtracker_step
    App._maze_gen_prim_step = _maze_gen_prim_step
    App._maze_gen_kruskal_step = _maze_gen_kruskal_step
    App._maze_init_solver = _maze_init_solver
    App._maze_solve_step = _maze_solve_step
    App._maze_reconstruct_path = _maze_reconstruct_path
    App._handle_maze_menu_key = _handle_maze_menu_key
    App._handle_maze_key = _handle_maze_key
    App._draw_maze_menu = _draw_maze_menu
    App._draw_maze = _draw_maze

