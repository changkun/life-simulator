"""Tests for maze mode."""
import random
import pytest
from tests.conftest import make_mock_app
from life.modes.maze import register


# MAZE_PRESETS is referenced on self but never registered as class attr
MAZE_PRESETS = [
    ("DFS Backtracker + BFS", "Recursive backtracker generation, BFS solve",
     "backtracker", "bfs", 1),
    ("Prim + A*", "Prim's algorithm generation, A* solve",
     "prim", "astar", 1),
    ("Kruskal + DFS", "Kruskal's algorithm generation, DFS solve",
     "kruskal", "dfs", 1),
]


class TestMaze:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        register(cls)
        cls.MAZE_PRESETS = MAZE_PRESETS
        # Instance attrs
        self.app.maze_mode = False
        self.app.maze_menu = False
        self.app.maze_menu_sel = 0
        self.app.maze_running = False
        self.app.maze_grid = []
        self.app.maze_gen_stack = []
        self.app.maze_gen_edges = []
        self.app.maze_gen_visited = set()
        self.app.maze_gen_sets = {}
        self.app.maze_solve_queue = []
        self.app.maze_solve_visited = set()
        self.app.maze_solve_parent = {}
        self.app.maze_solve_path = []
        self.app.maze_steps_per_frame = 3

    def test_enter(self):
        self.app._enter_maze_mode()
        assert self.app.maze_menu is True

    def test_init_backtracker(self):
        self.app.maze_mode = True
        self.app._maze_init(0)
        assert self.app.maze_mode is True
        assert self.app.maze_phase == "generating"

    def test_init_prim(self):
        self.app.maze_mode = True
        self.app._maze_init(1)
        assert self.app.maze_mode is True

    def test_init_kruskal(self):
        self.app.maze_mode = True
        self.app._maze_init(2)
        assert self.app.maze_mode is True

    def test_step_no_crash(self):
        self.app.maze_mode = True
        self.app._maze_init(0)
        for _ in range(10):
            self.app._maze_step()
        assert self.app.maze_generation == 10

    def test_full_generation_and_solve(self):
        """Run generation to completion and then solve."""
        self.app.maze_mode = True
        self.app._maze_init(0)
        # Run enough steps to complete generation and solving
        for _ in range(5000):
            self.app._maze_step()
            if self.app.maze_phase == "done":
                break
        # Should have moved past generating phase
        assert self.app.maze_phase in ("solving", "done")

    def test_exit_cleanup(self):
        self.app.maze_mode = True
        self.app._maze_init(0)
        self.app._exit_maze_mode()
        assert self.app.maze_mode is False
