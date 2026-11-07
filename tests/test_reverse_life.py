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
