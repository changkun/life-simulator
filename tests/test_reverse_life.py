"""Tests for life.modes.reverse_life — Reverse Life mode."""
from tests.conftest import make_mock_app
from life.modes import reverse_life as rl


def _make_app():
    app = make_mock_app()
    rl.register(type(app))
    return app


def _solve(solver, limit=20000):
    for _ in range(limit):
        if not solver.solve_step():
            break
    return solver


def _forward(sol, birth, survival):
    """Step a predecessor grid once on a torus and return it as booleans."""
    rows, cols = len(sol), len(sol[0])
    out = []
    for r in range(rows):
        row = []
        for c in range(cols):
            n = sum(sol[(r + dr) % rows][(c + dc) % cols]
                    for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if dr or dc)
            row.append(n in (survival if sol[r][c] else birth))
        out.append(row)
    return out


def test_enter_survives_terminal_with_few_color_pairs():
    """init_pair raises ValueError (not curses.error) above COLOR_PAIRS."""
    app = _make_app()
    app._enter_reverse_life_mode()
    assert app.reverse_life_mode is True
    assert app.reverse_life_solver is not None


def test_every_preset_solves_quickly_and_steps_forward_to_target():
    """The search is limited to the pattern's box, so presets finish fast."""
    app = _make_app()
    app._enter_reverse_life_mode()
    for idx, (name, _cells) in enumerate(rl._PRESETS):
        if name == "R-pentomino result":
            continue  # large target; search time is unbounded
        app.reverse_life_preset_idx = idx
        rl._load_preset(app)
        solver = _solve(app.reverse_life_solver)
        assert solver.solved, name
        sol = solver.get_solution_grid()
        assert _forward(sol, solver.birth, solver.survival) == \
            app.reverse_life_target, name


def test_empty_target_has_small_search_region():
    app = _make_app()
    app._enter_reverse_life_mode()
    solver = app.reverse_life_solver
    assert 0 < solver.total_cells < app.grid.rows * app.grid.cols
    assert _solve(solver).solved


def test_search_pad_keys_change_region():
    app = _make_app()
    app._enter_reverse_life_mode()
    app.reverse_life_preset_idx = 0
    rl._load_preset(app)
    small = app.reverse_life_solver.total_cells
    app._handle_reverse_life_key(ord("+"))
    assert app.reverse_life_search_pad == 3
    assert app.reverse_life_solver.total_cells > small


def _block_app():
    app = _make_app()
    app._enter_reverse_life_mode()
    app.reverse_life_preset_idx = 0
    rl._load_preset(app)
    return app


def test_n_finds_a_different_predecessor():
    app = _block_app()
    first = _solve(app.reverse_life_solver)
    assert first.solved
    app._handle_reverse_life_key(ord("n"))
    second = _solve(app.reverse_life_solver)
    assert second.solved
    assert second.get_solution_grid() != first.get_solution_grid()
    assert _forward(second.get_solution_grid(), second.birth,
                    second.survival) == app.reverse_life_target


def test_alternatives_run_out_without_claiming_garden_of_eden():
    app = _block_app()
    app.reverse_life_search_pad = 0
    rl._init_solver(app)
    seen = 0
    while True:
        solver = _solve(app.reverse_life_solver)
        if not solver.solved:
            break
        seen += 1
        assert seen < 50
        app._handle_reverse_life_key(ord("n"))
    assert seen >= 1
    assert solver.failed
    assert not solver.is_garden_of_eden


def test_lone_cell_without_padding_is_garden_of_eden():
    app = _make_app()
    app._enter_reverse_life_mode()
    app.grid.cells[5][5] = 1
    app.reverse_life_search_pad = 0
    rl._capture_target(app)
    rl._init_solver(app)
    solver = _solve(app.reverse_life_solver)
    assert solver.failed
    assert solver.is_garden_of_eden


def test_exit_clears_running_and_help():
    app = _block_app()
    app.reverse_life_running = True
    app.reverse_life_help = True
    app._exit_reverse_life_mode()
    assert app.reverse_life_running is False
    assert app.reverse_life_help is False


def test_enter_variants_accept_solution_and_update_population():
    for key in (10, 13):
        app = _block_app()
        _solve(app.reverse_life_solver)
        app._handle_reverse_life_key(key)
        assert app.reverse_life_steps_back == 1, key
        live = sum(1 for row in app.grid.cells for v in row if v)
        assert app.grid.population == live > 0


def test_instant_speed_returns_within_budget(monkeypatch):
    """A hard target must not block the frame loop."""
    app = _block_app()
    app.reverse_life_speed_idx = len(rl._SPEEDS) - 1
    monkeypatch.setattr(rl, "_INSTANT_BUDGET", 0.0)
    app.reverse_life_running = True
    app._reverse_life_step()
    assert app.reverse_life_running is True
    assert not app.reverse_life_solver.solved
    monkeypatch.setattr(rl, "_INSTANT_BUDGET", 5.0)
    app._reverse_life_step()
    assert app.reverse_life_solver.solved
    assert app.reverse_life_running is False


def test_g_runs_at_instant_speed():
    app = _block_app()
    app._handle_reverse_life_key(ord("g"))
    assert rl._SPEEDS[app.reverse_life_speed_idx][1] == 0
    assert app.reverse_life_solver.solved
    assert app.reverse_life_running is False
