"""Tests for life.modes.artificial_life — Artificial Life mode."""
from tests.conftest import make_mock_app
from life.modes.artificial_life import register


def _make_app():
    app = make_mock_app()
    app.alife_mode = False
    app.alife_menu = False
    app.alife_menu_sel = 0
    app.alife_running = False
    app.alife_generation = 0
    app.alife_tick = 0
    app.alife_preset_name = ""
    app.alife_rows = 0
    app.alife_cols = 0
    app.alife_creatures = []
    app.alife_food = []
    app.alife_next_id = 0
    app.alife_food_regrow = 0.02
    app.alife_mutation_rate = 0.15
    app.alife_speed_scale = 1.0
    app.alife_gen_max = 0
    app.alife_total_births = 0
    app.alife_total_deaths = 0
    app.alife_pop_history = []
    app.alife_herb_history = []
    app.alife_pred_history = []
    app.alife_show_stats = True
    type(app).ALIFE_PRESETS = [
        ("Grassland", "Abundant food, herbivores only", "grassland"),
        ("Predator-Prey", "Classic Lotka-Volterra dynamics", "predprey"),
        ("Desert", "Scarce resources, high mutation", "desert"),
        ("Coral Reef", "Dense ecosystem with all diet types", "reef"),
        ("Evolution Lab", "High mutation for rapid evolution", "evolab"),
        ("Primordial Soup", "Sparse start, life finds a way", "soup"),
    ]
    type(app).ALIFE_HERB_CHARS = "oOo@Q"
    type(app).ALIFE_PRED_CHARS = "xX*#W"
    type(app).ALIFE_OMNI_CHARS = "~=+&$"
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_alife_mode()
    assert app.alife_menu is True
    assert app.alife_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.alife_mode = True
    # Use "soup" preset for fewest creatures
    app._alife_init(5)
    assert app.alife_mode is True
    assert app.alife_menu is False
    for _ in range(10):
        app._alife_step()
    assert app.alife_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.alife_mode = True
    app._alife_init(5)
    app._exit_alife_mode()
    assert app.alife_mode is False
    assert app.alife_menu is False
    assert app.alife_running is False
