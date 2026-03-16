"""Tests for life.modes.cellular_potts — Cellular Potts Model mode."""
from tests.conftest import make_mock_app
from life.modes.cellular_potts import register


def _make_app():
    app = make_mock_app()
    app.cpm_mode = False
    app.cpm_menu = False
    app.cpm_menu_sel = 0
    app.cpm_running = False
    app.cpm_generation = 0
    app.cpm_preset_name = ""
    app.cpm_rows = 0
    app.cpm_cols = 0
    app.cpm_steps_per_frame = 500
    app.cpm_grid = []
    app.cpm_num_cells = 0
    app.cpm_temperature = 10.0
    app.cpm_lambda_area = 1.0
    app.cpm_target_area = []
    app.cpm_cell_type = []
    app.cpm_J = []
    app.cpm_num_types = 2
    app.cpm_viz_mode = 0
    app.cpm_chemotaxis = False
    app.cpm_chem_field = []
    app.cpm_chem_lambda = 0.0
    app.cpm_chem_decay = 0.01
    app.cpm_chem_source_type = 0
    app.cpm_area_cache = []
    # Presets: (name, desc, preset_id)
    type(app).CPM_PRESETS = [
        ("Cell Sorting", "Differential adhesion drives cell type segregation", "sorting"),
        ("Wound Healing", "Cell sheet migration into empty wound region", "wound"),
        ("Tumor Growth", "Tumor cells invade surrounding tissue", "tumor"),
        ("Checkerboard", "Alternating cell types in a grid", "checker"),
        ("Foam", "Single-type foam coarsening", "foam"),
        ("Chemotaxis", "Cells migrate up a chemical gradient", "chemotaxis"),
    ]
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_cpm_mode()
    assert app.cpm_menu is True
    assert app.cpm_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app.cpm_mode = True
    app._cpm_init(0)
    assert app.cpm_mode is True
    assert app.cpm_menu is False
    for _ in range(10):
        app._cpm_step()
    assert app.cpm_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app.cpm_mode = True
    app._cpm_init(0)
    app._exit_cpm_mode()
    assert app.cpm_mode is False
    assert app.cpm_menu is False
    assert app.cpm_running is False
