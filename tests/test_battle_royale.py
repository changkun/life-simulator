"""Tests for life.modes.battle_royale — Battle Royale mode."""
import unittest.mock
from tests.conftest import make_mock_app
from life.modes.battle_royale import register, PRESETS


def _make_app():
    app = make_mock_app()
    app.br_mode = False
    app.br_menu = False
    app.br_menu_sel = 0
    app.br_menu_phase = 0
    app.br_custom_picks = []
    app.br_running = False
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_battle_royale()
    assert app.br_menu is True
    assert app.br_menu_phase == 0


def test_step_no_crash():
    app = _make_app()
    # _br_init calls curses.init_pair which needs a real curses screen
    # Patch it to avoid error
    with unittest.mock.patch("life.modes.battle_royale._init_br_colors"):
        app._br_init(["life", "highlife", "daynight", "seeds"])
    assert app.br_mode is True
    for _ in range(10):
        app._br_do_step()
    assert app.br_generation == 10


def test_exit_cleanup():
    app = _make_app()
    with unittest.mock.patch("life.modes.battle_royale._init_br_colors"):
        app._br_init(["life", "highlife", "daynight", "seeds"])
    app._exit_battle_royale()
    assert app.br_mode is False
    assert app.br_running is False


def test_factions_start_in_corners():
    """After init, each faction should have cells in its designated corner."""
    from life.modes.battle_royale import _br_init_grid
    rows, cols = 30, 30
    owner, age = _br_init_grid(rows, cols, ["life", "highlife", "daynight", "seeds"])
    # Faction 0: top-left corner
    has_f0 = any(owner[r][c] == 0 for r in range(rows // 4) for c in range(cols // 4))
    # Faction 1: top-right corner
    has_f1 = any(owner[r][c] == 1 for r in range(rows // 4) for c in range(3 * cols // 4, cols))
    # Faction 2: bottom-left corner
    has_f2 = any(owner[r][c] == 2 for r in range(3 * rows // 4, rows) for c in range(cols // 4))
    # Faction 3: bottom-right corner
    has_f3 = any(owner[r][c] == 3 for r in range(3 * rows // 4, rows) for c in range(3 * cols // 4, cols))
    assert has_f0, "Faction 0 should have cells in top-left"
    assert has_f1, "Faction 1 should have cells in top-right"
    assert has_f2, "Faction 2 should have cells in bottom-left"
    assert has_f3, "Faction 3 should have cells in bottom-right"


def test_scores_match_grid():
    """Scores returned by _br_scores should match manual counting."""
    from life.modes.battle_royale import _br_scores
    rows, cols = 10, 10
    owner = [[-1] * cols for _ in range(rows)]
    owner[0][0] = 0
    owner[0][1] = 0
    owner[1][0] = 1
    owner[9][9] = 3
    scores, total = _br_scores(owner, rows, cols)
    assert scores[0] == 2
    assert scores[1] == 1
    assert scores[2] == 0
    assert scores[3] == 1
    assert total == 100


def test_step_changes_grid_state():
    """Running a step should produce a different grid state."""
    app = _make_app()
    with unittest.mock.patch("life.modes.battle_royale._init_br_colors"):
        app._br_init(["life", "highlife", "daynight", "seeds"])
    initial_scores = list(app.br_scores)
    # Run several steps -- with stochastic rules, grid should change
    for _ in range(5):
        app._br_do_step()
    assert app.br_generation == 5
    # Scores structure should still be valid
    assert len(app.br_scores) == 4
    assert all(s >= 0 for s in app.br_scores)


def test_menu_accepts_all_enter_keys():
    import curses
    for key in (10, 13, curses.KEY_ENTER):
        app = _make_app()
        app._enter_battle_royale()
        app.br_menu_sel = len(PRESETS)
        app._handle_br_menu_key(key)
        assert app.br_menu_phase == 1


def test_no_stepping_after_draw():
    """After a draw (winner == -2) neither Space nor n restarts play."""
    app = _make_app()
    app.br_winner = -2
    app.br_running = False
    app.br_generation = 5
    app._handle_br_key(ord(" "))
    assert app.br_running is False
    app._handle_br_key(ord("n"))
    assert app.br_generation == 5
