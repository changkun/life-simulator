"""Tests for life.modes.genesis_protocol — Genesis Protocol mode."""
import curses

from tests.conftest import make_mock_app
from life.modes import genesis_protocol as gp


def _make_app():
    app = make_mock_app()
    app.genesis_mode = False
    app.genesis_menu = False
    app.genesis_menu_sel = 0
    app.genesis_running = False
    app.genesis_batch_size = 8
    app.genesis_eval_steps = 50
    app.genesis_mutation_rate = 0.15
    app.genesis_hall_max = 50
    app.genesis_round = 0
    app.genesis_sim_step = 0
    app.genesis_phase = "idle"
    app.genesis_cursor = 0
    app.genesis_auto_continue = False
    app.genesis_hall = []
    app.genesis_hall_view = False
    app.genesis_history = []
    app.genesis_total_universes = 0
    app.genesis_best_ever_score = 0.0
    app.genesis_best_ever_rule = ""
    app.genesis_hall_threshold = 80.0
    gp.register(type(app))
    return app


def test_skip_collects_period_and_te_samples():
    app = _make_app()
    gp._genesis_start_round(app)
    app._handle_genesis_key(ord("S"))
    assert app.genesis_phase == "scored"
    assert app.genesis_sim_step == app.genesis_eval_steps
    assert all(len(h) > 0 for h in app.genesis_te_histories)


def test_skip_with_auto_continue_stops_after_one_round():
    app = _make_app()
    app.genesis_auto_continue = True
    gp._genesis_start_round(app)
    app._handle_genesis_key(ord("S"))
    assert app.genesis_round == 2
    assert app.genesis_phase == "simulating"


def test_enter_adopts_selected_rule():
    app = _make_app()
    gp._genesis_start_round(app)
    genome = app.genesis_genomes[0]
    app._handle_genesis_key(10)
    assert app.grid.birth == genome["birth"]
    assert app.grid.survival == genome["survival"]
    assert app.genesis_mode is False


def test_a_moves_cursor_left():
    app = _make_app()
    gp._genesis_start_round(app)
    app.genesis_cursor = 2
    app._handle_genesis_key(ord("a"))
    assert app.genesis_cursor == 1
    assert app.genesis_mode is True


def test_exit_clears_state():
    app = _make_app()
    gp._genesis_start_round(app)
    app._exit_genesis_mode()
    assert not app.genesis_mode and not app.genesis_running
    assert app.genesis_sims == []


_HALL_ENTRY = {"genome": {"birth": [3], "survival": [2, 3]},
               "label": "x", "score": 90.0}


def test_esc_and_q_in_hall_view_exit_mode():
    for key in (27, ord("q")):
        app = _make_app()
        app.genesis_mode = True
        app.genesis_hall = [dict(_HALL_ENTRY)]
        app.genesis_hall_view = True
        app.genesis_hall_sel = 0
        app._handle_genesis_key(key)
        assert not app.genesis_mode


def test_h_in_hall_view_returns_to_explorer():
    app = _make_app()
    app.genesis_mode = True
    app.genesis_hall = [dict(_HALL_ENTRY)]
    app.genesis_hall_view = True
    app.genesis_hall_sel = 0
    app._handle_genesis_key(ord("h"))
    assert app.genesis_mode
    assert not app.genesis_hall_view
