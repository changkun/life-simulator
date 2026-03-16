"""Tests for life.modes.maze_solver — Maze Solver mode."""
from tests.conftest import make_mock_app
from life.modes.maze_solver import register


def _make_app():
    app = make_mock_app()
    app.mazesolver_mode = False
    app.mazesolver_menu = False
    app.mazesolver_menu_sel = 0
    app.mazesolver_running = False
    app.mazesolver_speed = 3
    app.mazesolver_grid = []
    app.mazesolver_solve_queue = []
    app.mazesolver_solve_visited = set()
    app.mazesolver_solve_parent = {}
    app.mazesolver_solve_path = []
    app.mazesolver_frontier_set = set()
    app.mazesolver_wf_trail = []
    app.mazesolver_gen_stack = []
    app.mazesolver_gen_visited = set()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_mazesolver_mode()
    assert app.mazesolver_menu is True


def test_step_no_crash():
    app = _make_app()
    app.mazesolver_mode = True
    app._mazesolver_init(0)
    app.mazesolver_running = True
    for _ in range(10):
        app._mazesolver_step()
    assert app.mazesolver_generation >= 0


def test_exit_cleanup():
    app = _make_app()
    app.mazesolver_mode = True
    app._mazesolver_init(0)
    app._exit_mazesolver_mode()
    assert app.mazesolver_mode is False
    assert app.mazesolver_grid == []
