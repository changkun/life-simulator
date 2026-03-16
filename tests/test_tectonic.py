"""Tests for life.modes.tectonic — Tectonic Plates mode."""
from tests.conftest import make_mock_app
from life.modes.tectonic import register


# MockStdscr doesn't have addch; add it
def _addch(self, *args, **kwargs):
    pass


def _make_app():
    app = make_mock_app()
    # Patch addch onto the mock stdscr
    type(app.stdscr).addch = _addch
    app.tectonic_mode = False
    app.tectonic_menu = False
    app.tectonic_menu_sel = 0
    app.tectonic_running = False
    app.tectonic_generation = 0
    app.tectonic_preset_name = ""
    app.tectonic_rows = 0
    app.tectonic_cols = 0
    app.tectonic_elevation = []
    app.tectonic_plate_id = []
    app.tectonic_plates = []
    app.tectonic_num_plates = 6
    app.tectonic_show_plates = False
    app.tectonic_show_help = True
    app.tectonic_speed_scale = 1.0
    app.tectonic_volcanic = []
    app.tectonic_age = 0
    type(app).TECTONIC_PRESETS = [
        ("Pangaea Breakup", "Supercontinent rifts apart", "pangaea"),
        ("Continent Collision", "Two landmasses collide", "collision"),
        ("Island Arcs", "Oceanic-oceanic subduction zones", "arcs"),
        ("Mid-Ocean Ridges", "Divergent plate boundaries", "ridges"),
        ("Ring of Fire", "Subduction ring around central plate", "ring"),
        ("Random Tectonics", "Random plate configuration", "random"),
    ]
    type(app).TECTONIC_ELEV_CHARS = list("≈≈~-=:*#▲▲")
    type(app).TECTONIC_ELEV_THRESHOLDS = [
        -5000, -3000, -500, 0, 300, 1200, 3000, 6000, 8000, 9000,
    ]
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_tectonic_mode()
    assert app.tectonic_menu is True
    assert app.tectonic_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.tectonic_mode = True
    app._tectonic_init(5)  # "random" preset
    assert app.tectonic_mode is True
    assert app.tectonic_menu is False
    for _ in range(10):
        app._tectonic_step()
    assert app.tectonic_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.tectonic_mode = True
    app._tectonic_init(5)
    app._exit_tectonic_mode()
    assert app.tectonic_mode is False
    assert app.tectonic_menu is False
    assert app.tectonic_running is False
