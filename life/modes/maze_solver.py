"""Mode: mazesolver — simulation mode for the life package."""
import curses
import heapq
import math
import random
import time

MAZESOLVER_PRESETS = [
    ("A* Search (Medium)", "Optimal pathfinding with heuristic — medium maze", "astar", "medium"),
    ("BFS (Medium)", "Breadth-first search — guaranteed shortest path", "bfs", "medium"),
    ("DFS (Medium)", "Depth-first search — fast but not optimal", "dfs", "medium"),
    ("Wall Follower (Medium)", "Right-hand rule wall following — classic algorithm", "wall_follower", "medium"),
    ("A* (Small)", "A* on a small maze — quick solve", "astar", "small"),
    ("A* (Large)", "A* on a large maze — watch it explore", "astar", "large"),
    ("BFS (Large)", "BFS flood-fill on a large maze", "bfs", "large"),
    ("DFS (Large)", "DFS deep exploration on a large maze", "dfs", "large"),
]


def _enter_mazesolver_mode(self):
    """Enter Maze Solver Visualizer mode — show preset menu."""
    self.mazesolver_mode = True
    self.mazesolver_menu = True
    self.mazesolver_menu_sel = 0
    self.mazesolver_running = False
    self._flash("Maze Solver Visualizer — select a configuration")




def _exit_mazesolver_mode(self):
    """Exit Maze Solver Visualizer mode."""
    self.mazesolver_mode = False
    self.mazesolver_menu = False
    self.mazesolver_running = False
    self.mazesolver_grid = []
    self.mazesolver_solve_queue = []
    self.mazesolver_solve_visited = set()
    self.mazesolver_solve_parent = {}
    self.mazesolver_solve_path = []
    self.mazesolver_frontier_set = set()
    self.mazesolver_wf_trail = []
    self.mazesolver_gen_stack = []
    self.mazesolver_gen_visited = set()
    self._flash("Maze Solver mode OFF")




def _mazesolver_init(self, preset_idx: int):
    """Initialize maze solver simulation with the given preset."""
    name, _desc, algo, maze_size = MAZESOLVER_PRESETS[preset_idx]
    self.mazesolver_preset_name = name
    self.mazesolver_algo = algo
    self.mazesolver_maze_size = maze_size
    self.mazesolver_generation = 0
    self.mazesolver_running = False
    self.mazesolver_solve_done = False
    self.mazesolver_solve_steps = 0

    max_y, max_x = self.stdscr.getmaxyx()
    # Compute grid dimensions based on size preset
    if maze_size == "small":
        raw_rows = max(11, min(21, max_y - 3))
        raw_cols = max(11, min(21, (max_x - 1) // 2))
    elif maze_size == "large":
        raw_rows = max(11, max_y - 3)
        raw_cols = max(11, (max_x - 1) // 2)
    else:  # medium
        raw_rows = max(11, min(41, max_y - 3))
        raw_cols = max(11, min(51, (max_x - 1) // 2))
    # Must be odd for wall/passage grid
    self.mazesolver_rows = raw_rows if raw_rows % 2 == 1 else raw_rows - 1
    self.mazesolver_cols = raw_cols if raw_cols % 2 == 1 else raw_cols - 1
    rows, cols = self.mazesolver_rows, self.mazesolver_cols

    # Initialize grid: all walls, then generate maze instantly with backtracker
    self.mazesolver_grid = [[0] * cols for _ in range(rows)]
    self.mazesolver_start = (1, 1)
    self.mazesolver_end = (rows - 2, cols - 2)

    # Generate complete maze using recursive backtracker (instant)
    self.mazesolver_phase = "generating"
    self.mazesolver_gen_visited = set()
    self.mazesolver_gen_stack = []
    sr, sc = 1, 1
    self.mazesolver_grid[sr][sc] = 1
    self.mazesolver_gen_visited.add((sr, sc))
    self.mazesolver_gen_stack = [(sr, sc)]
    # Run generation to completion
    while self.mazesolver_gen_stack:
        cr, cc = self.mazesolver_gen_stack[-1]
        neighbors = []
        for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            nr, nc = cr + dr, cc + dc
            if 0 < nr < rows and 0 < nc < cols and (nr, nc) not in self.mazesolver_gen_visited:
                neighbors.append((nr, nc, cr + dr // 2, cc + dc // 2))
        if neighbors:
            nr, nc, wr, wc = random.choice(neighbors)
            self.mazesolver_grid[wr][wc] = 1
            self.mazesolver_grid[nr][nc] = 1
            self.mazesolver_gen_visited.add((nr, nc))
            self.mazesolver_gen_stack.append((nr, nc))
        else:
            self.mazesolver_gen_stack.pop()

    # Ensure start and end are passages
    er, ec = self.mazesolver_end
    self.mazesolver_grid[sr][sc] = 1
    self.mazesolver_grid[er][ec] = 1

    # Initialize solver
    self.mazesolver_phase = "solving"
    self.mazesolver_solve_visited = set()
    self.mazesolver_solve_parent = {}
    self.mazesolver_solve_path = []
    self.mazesolver_solve_done = False
    self.mazesolver_frontier_set = set()

    if algo == "astar":
        h = abs(er - sr) + abs(ec - sc)
        self.mazesolver_solve_queue = [(h, 0, sr, sc)]
        self.mazesolver_solve_visited.add((sr, sc))
        self.mazesolver_frontier_set.add((sr, sc))
    elif algo == "bfs":
        self.mazesolver_solve_queue = [(sr, sc)]
        self.mazesolver_solve_visited.add((sr, sc))
        self.mazesolver_frontier_set.add((sr, sc))
    elif algo == "dfs":
        self.mazesolver_solve_queue = [(sr, sc)]
        self.mazesolver_solve_visited.add((sr, sc))
        self.mazesolver_frontier_set.add((sr, sc))
    elif algo == "wall_follower":
        self.mazesolver_wf_pos = (sr, sc)
        self.mazesolver_wf_dir = 0  # start facing right
        self.mazesolver_wf_trail = [(sr, sc)]
        self.mazesolver_solve_visited.add((sr, sc))

    self.mazesolver_menu = False
    self._flash(f"Maze Solver: {name} — Space to start")




def _mazesolver_step(self):
    """Advance maze solver by one step."""
    if self.mazesolver_solve_done or self.mazesolver_phase != "solving":
        return
    algo = self.mazesolver_algo
    er, ec = self.mazesolver_end
    rows, cols = self.mazesolver_rows, self.mazesolver_cols

    if algo == "astar":
        if not self.mazesolver_solve_queue:
            self.mazesolver_solve_done = True
            self.mazesolver_phase = "done"
            self._flash("No path found!")
            return
        _f, g, cr, cc = heapq.heappop(self.mazesolver_solve_queue)
        self.mazesolver_frontier_set.discard((cr, cc))
        if (cr, cc) == (er, ec):
            self._mazesolver_reconstruct_path()
            return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and self.mazesolver_grid[nr][nc] == 1 and (nr, nc) not in self.mazesolver_solve_visited:
                self.mazesolver_solve_visited.add((nr, nc))
                self.mazesolver_solve_parent[(nr, nc)] = (cr, cc)
                ng = g + 1
                h = abs(er - nr) + abs(ec - nc)
                heapq.heappush(self.mazesolver_solve_queue, (ng + h, ng, nr, nc))
                self.mazesolver_frontier_set.add((nr, nc))
        self.mazesolver_solve_steps += 1

    elif algo == "bfs":
        if not self.mazesolver_solve_queue:
            self.mazesolver_solve_done = True
            self.mazesolver_phase = "done"
            self._flash("No path found!")
            return
        cr, cc = self.mazesolver_solve_queue.pop(0)
        self.mazesolver_frontier_set.discard((cr, cc))
        if (cr, cc) == (er, ec):
            self._mazesolver_reconstruct_path()
            return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and self.mazesolver_grid[nr][nc] == 1 and (nr, nc) not in self.mazesolver_solve_visited:
                self.mazesolver_solve_visited.add((nr, nc))
                self.mazesolver_solve_parent[(nr, nc)] = (cr, cc)
                self.mazesolver_solve_queue.append((nr, nc))
                self.mazesolver_frontier_set.add((nr, nc))
        self.mazesolver_solve_steps += 1

    elif algo == "dfs":
        if not self.mazesolver_solve_queue:
            self.mazesolver_solve_done = True
            self.mazesolver_phase = "done"
            self._flash("No path found!")
            return
        cr, cc = self.mazesolver_solve_queue.pop()
        self.mazesolver_frontier_set.discard((cr, cc))
        if (cr, cc) == (er, ec):
            self._mazesolver_reconstruct_path()
            return
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < rows and 0 <= nc < cols and self.mazesolver_grid[nr][nc] == 1 and (nr, nc) not in self.mazesolver_solve_visited:
                self.mazesolver_solve_visited.add((nr, nc))
                self.mazesolver_solve_parent[(nr, nc)] = (cr, cc)
                self.mazesolver_solve_queue.append((nr, nc))
                self.mazesolver_frontier_set.add((nr, nc))
        self.mazesolver_solve_steps += 1

    elif algo == "wall_follower":
        # Right-hand rule wall follower
        # Directions: 0=right, 1=down, 2=left, 3=up
        DR = [0, 1, 0, -1]
        DC = [1, 0, -1, 0]
        cr, cc = self.mazesolver_wf_pos
        if (cr, cc) == (er, ec):
            # Build path from trail
            self.mazesolver_solve_path = list(self.mazesolver_wf_trail)
            self.mazesolver_solve_done = True
            self.mazesolver_phase = "done"
            self._flash(f"Path found! Length={len(self.mazesolver_solve_path)}, steps={self.mazesolver_solve_steps}")
            return
        d = self.mazesolver_wf_dir
        # Try: turn right, go straight, turn left, turn back
        for turn in [1, 0, -1, 2]:
            nd = (d + turn) % 4
            nr, nc = cr + DR[nd], cc + DC[nd]
            if 0 <= nr < rows and 0 <= nc < cols and self.mazesolver_grid[nr][nc] == 1:
                self.mazesolver_wf_dir = nd
                self.mazesolver_wf_pos = (nr, nc)
                self.mazesolver_wf_trail.append((nr, nc))
                self.mazesolver_solve_visited.add((nr, nc))
                break
        self.mazesolver_solve_steps += 1

    self.mazesolver_generation += 1




def _mazesolver_reconstruct_path(self):
    """Trace back from end to start to build the solution path."""
    path = []
    cur = self.mazesolver_end
    while cur != self.mazesolver_start and cur in self.mazesolver_solve_parent:
        path.append(cur)
        cur = self.mazesolver_solve_parent[cur]
    path.append(self.mazesolver_start)
    path.reverse()
    self.mazesolver_solve_path = path
    self.mazesolver_solve_done = True
    self.mazesolver_phase = "done"
    self._flash(f"Path found! Length={len(path)}, explored={len(self.mazesolver_solve_visited)} cells, steps={self.mazesolver_solve_steps}")




def _handle_mazesolver_menu_key(self, key: int) -> bool:
    """Handle input in Maze Solver preset menu."""
    n = len(MAZESOLVER_PRESETS)
    if key in (ord("j"), curses.KEY_DOWN):
        self.mazesolver_menu_sel = (self.mazesolver_menu_sel + 1) % n
    elif key in (ord("k"), curses.KEY_UP):
        self.mazesolver_menu_sel = (self.mazesolver_menu_sel - 1) % n
    elif key in (ord("\n"), ord("\r")):
        self._mazesolver_init(self.mazesolver_menu_sel)
    elif key in (ord("q"), 27):
        self.mazesolver_menu = False
        self.mazesolver_mode = False
        self._flash("Maze Solver mode cancelled")
    return True




def _handle_mazesolver_key(self, key: int) -> bool:
    """Handle input in active Maze Solver simulation."""
    if key == ord(" "):
        self.mazesolver_running = not self.mazesolver_running
    elif key in (ord("n"), ord(".")):
        for _ in range(self.mazesolver_speed):
            self._mazesolver_step()
    elif key == ord("r"):
        # Reseed — regenerate with same preset
        idx = next((i for i, p in enumerate(MAZESOLVER_PRESETS)
                    if p[0] == self.mazesolver_preset_name), 0)
        self._mazesolver_init(idx)
        self.mazesolver_running = False
    elif key == ord("R"):
        self.mazesolver_mode = False
        self.mazesolver_running = False
        self.mazesolver_menu = True
        self.mazesolver_menu_sel = 0
    elif key == ord("s"):
        self.mazesolver_speed = min(30, self.mazesolver_speed + 1)
        self._flash(f"Steps/frame: {self.mazesolver_speed}")
    elif key == ord("S"):
        self.mazesolver_speed = max(1, self.mazesolver_speed - 1)
        self._flash(f"Steps/frame: {self.mazesolver_speed}")
    elif key in (ord("q"), 27):
        self._exit_mazesolver_mode()
    return True




def _draw_mazesolver_menu(self, max_y: int, max_x: int):
    """Draw the Maze Solver preset selection menu."""
    self.stdscr.erase()
    title = "── Maze Solver Visualizer — Select Preset ──"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass
    subtitle = "Watch pathfinding algorithms explore and solve mazes in real-time"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2), subtitle,
                           curses.color_pair(6))
    except curses.error:
        pass
    for i, (name, desc, *_) in enumerate(MAZESOLVER_PRESETS):
        y = 4 + i
        if y >= max_y - 2:
            break
        marker = "▶ " if i == self.mazesolver_menu_sel else "  "
        attr = curses.color_pair(7) | curses.A_BOLD if i == self.mazesolver_menu_sel else curses.color_pair(6)
        line = f"{marker}{name:30s} — {desc}"
        try:
            self.stdscr.addstr(y, 4, line[:max_x - 5], attr)
        except curses.error:
            pass
    # Legend
    legend_y = max_y - 3
    if legend_y > 4 + len(MAZESOLVER_PRESETS):
        legend = " Legend:  ██=wall  SS=start  EE=end  ░░=explored  ▓▓=frontier  ██=path"
        try:
            self.stdscr.addstr(legend_y, 2, legend[:max_x - 3], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass
    hint = " [j/k]=navigate  [Enter]=select  [q]=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hint[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass




def _draw_mazesolver(self, max_y: int, max_x: int):
    """Draw the active Maze Solver Visualizer."""
    self.stdscr.erase()
    rows, cols = self.mazesolver_rows, self.mazesolver_cols
    grid = self.mazesolver_grid
    state = "▶ RUNNING" if self.mazesolver_running else "⏸ PAUSED"
    phase_label = self.mazesolver_phase.upper()
    algo_name = {"bfs": "BFS", "dfs": "DFS", "astar": "A*", "wall_follower": "Wall Follower"}.get(self.mazesolver_algo, self.mazesolver_algo)

    title = (f" Maze Solver: {algo_name} ({self.mazesolver_maze_size})"
             f"  |  {phase_label}  |  steps={self.mazesolver_solve_steps}"
             f"  |  explored={len(self.mazesolver_solve_visited)}"
             f"  |  {state}")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(7) | curses.A_BOLD)
    except curses.error:
        pass

    # Build sets for fast lookup
    solve_visited = self.mazesolver_solve_visited
    solve_path_set = set(self.mazesolver_solve_path)
    frontier = self.mazesolver_frontier_set
    sr, sc = self.mazesolver_start
    er, ec = self.mazesolver_end

    # Wall follower current position
    wf_pos = self.mazesolver_wf_pos if self.mazesolver_algo == "wall_follower" else None
    wf_trail_set = set(self.mazesolver_wf_trail[-20:]) if self.mazesolver_algo == "wall_follower" else set()

    # For BFS/DFS/A*: current frontier items in queue
    if self.mazesolver_algo != "wall_follower":
        # Rebuild frontier set from queue for accurate display
        frontier = set()
        for item in self.mazesolver_solve_queue:
            if self.mazesolver_algo == "astar":
                _, _, qr, qc = item
            else:
                qr, qc = item
            frontier.add((qr, qc))

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
            # Solution path (highest priority after start/end)
            if (r, c) in solve_path_set:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "██",
                                       curses.color_pair(2) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            # Wall follower current position
            if wf_pos and (r, c) == wf_pos:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "@@",
                                       curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            # Wall follower recent trail
            if (r, c) in wf_trail_set:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "▓▓",
                                       curses.color_pair(3) | curses.A_BOLD)
                except curses.error:
                    pass
                continue
            # Frontier cells (currently in queue)
            if (r, c) in frontier:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "▓▓",
                                       curses.color_pair(3))
                except curses.error:
                    pass
                continue
            # Explored cells (visited but not in frontier)
            if (r, c) in solve_visited:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "░░",
                                       curses.color_pair(4))
                except curses.error:
                    pass
                continue
            # Wall vs passage
            if grid[r][c] == 0:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "██",
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass
            else:
                try:
                    self.stdscr.addstr(1 + r, c * 2, "  ", curses.color_pair(0))
                except curses.error:
                    pass

    # Status bar
    status_y = max_y - 2
    if status_y > 1:
        explored = len(self.mazesolver_solve_visited)
        path_len = len(self.mazesolver_solve_path)
        q_len = len(self.mazesolver_solve_queue) if self.mazesolver_algo != "wall_follower" else len(self.mazesolver_wf_trail)
        info = (f" Algorithm: {algo_name}  |  maze: {self.mazesolver_rows}x{self.mazesolver_cols} ({self.mazesolver_maze_size})"
                f"  |  steps={self.mazesolver_solve_steps}  explored={explored}"
                f"  queue={q_len}  path={path_len}"
                f"  |  speed={self.mazesolver_speed}")
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
            hint = " [Space]=play [n]=step [s/S]=speed+/- [r]=new maze [R]=menu [q]=exit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass


def register(App):
    """Register mazesolver mode methods on the App class."""
    App._enter_mazesolver_mode = _enter_mazesolver_mode
    App._exit_mazesolver_mode = _exit_mazesolver_mode
    App._mazesolver_init = _mazesolver_init
    App._mazesolver_step = _mazesolver_step
    App._mazesolver_reconstruct_path = _mazesolver_reconstruct_path
    App._handle_mazesolver_menu_key = _handle_mazesolver_menu_key
    App._handle_mazesolver_key = _handle_mazesolver_key
    App._draw_mazesolver_menu = _draw_mazesolver_menu
    App._draw_mazesolver = _draw_mazesolver

