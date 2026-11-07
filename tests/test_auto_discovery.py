"""Tests for life.modes.auto_discovery — Auto-Discovery mode."""
import curses

from tests.conftest import make_mock_app
from life.modes.auto_discovery import register


def _make_app():
    app = make_mock_app()
    app.adisco_mode = False
    app.adisco_menu = False
    app.adisco_menu_sel = 0
    app.adisco_batch_size = 12
    app.adisco_eval_steps = 150
    app.adisco_mutation_rate = 0.15
    app.adisco_auto_continue = False
    app.adisco_gallery_max = 50
    app.adisco_gallery_threshold = 150
    app.adisco_round = 0
    app.adisco_sims = []
    app.adisco_genomes = []
    app.adisco_fitness = []
    app.adisco_pop_histories = []
    app.adisco_period_detectors = []
    app.adisco_cursor = 0
    app.adisco_sim_step = 0
    app.adisco_phase = "idle"
    app.adisco_running = False
    app.adisco_gallery = []
    app.adisco_gallery_view = False
    app.adisco_gallery_sel = 0
    app.adisco_gallery_scroll = 0
    app.adisco_history = []
    register(type(app))
    return app


def test_a_adopts_cursor_rule_instead_of_moving_left():
    app = _make_app()
    app._enter_adisco_mode()
    app._adisco_init()
    app.adisco_cursor = 2
    genome = app.adisco_genomes[2]
    app._handle_adisco_key(ord("a"))
    assert app.adisco_mode is False
    assert app.grid.birth == genome["birth"]
    assert app.grid.survival == genome["survival"]


def test_left_arrow_moves_cursor():
    app = _make_app()
    app._enter_adisco_mode()
    app._adisco_init()
    app.adisco_cursor = 2
    app._handle_adisco_key(curses.KEY_LEFT)
    assert app.adisco_cursor == 1


def test_skip_feeds_period_detectors_and_scores():
    app = _make_app()
    app._enter_adisco_mode()
    app._adisco_init()
    app._handle_adisco_key(ord("S"))
    assert app.adisco_phase == "scored"
    assert app.adisco_sim_step == app.adisco_eval_steps
    assert all(d.hashes for d in app.adisco_period_detectors)
    assert all("total" in f for f in app.adisco_fitness)


def test_crossover_density_stays_in_range():
    from life.modes.auto_discovery import _crossover
    low = {"birth": {3}, "survival": {2}, "neighborhood": "moore",
           "density": 0.02, "seed_style": "random"}
    high = dict(low, density=0.6)
    for _ in range(500):
        for pair in ((low, low), (high, high)):
            assert 0.02 <= _crossover(*pair)["density"] <= 0.6


def test_removing_last_gallery_entry_keeps_selection_valid():
    app = _make_app()
    app.adisco_gallery = [{"label": "B3/S23"}]
    app.adisco_gallery_view = True
    app._handle_adisco_gallery_key(ord("x"))
    assert app.adisco_gallery == []
    assert app.adisco_gallery_sel == 0
