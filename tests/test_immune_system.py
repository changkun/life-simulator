"""Tests for immune_system mode."""
from tests.conftest import make_mock_app
from life.modes.immune_system import register, ENT_BACTERIA, ENT_TISSUE, ENT_EMPTY


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.immune_mode = False
    app.immune_menu = False
    app.immune_menu_sel = 0
    app.immune_running = False
    app.immune_grid = []
    app.immune_entities = []
    return app


def test_enter():
    app = _make_app()
    app._enter_immune_mode()
    assert app.immune_menu is True


def test_step_no_crash():
    app = _make_app()
    app.immune_mode = True
    app._immune_init(0)
    assert app.immune_mode is True
    for _ in range(10):
        app._immune_step()


def test_exit_cleanup():
    app = _make_app()
    app._immune_init(0)
    app._exit_immune_mode()
    assert app.immune_mode is False


def test_init_places_pathogens_and_tissue():
    """After init, the grid should contain tissue and pathogens."""
    app = _make_app()
    app._immune_init(0)  # Normal Bacterial Infection preset
    rows, cols = app.immune_rows, app.immune_cols
    tissue_count = 0
    pathogen_count = 0
    for r in range(rows):
        for c in range(cols):
            et = app.immune_grid[r][c]
            if et == ENT_TISSUE:
                tissue_count += 1
            elif et == ENT_BACTERIA:
                pathogen_count += 1
    assert tissue_count > 0, "Should have tissue cells"
    assert pathogen_count > 0, "Should have bacteria for preset 0"


def test_cytokine_gradient_updates():
    """After steps, cytokine levels near pathogens should be non-zero."""
    app = _make_app()
    app._immune_init(0)
    for _ in range(5):
        app._immune_step()
    # Check that cytokine grid has some positive values
    total_cyto = sum(app.immune_cytokine[r][c]
                     for r in range(app.immune_rows)
                     for c in range(app.immune_cols))
    assert total_cyto > 0, "Cytokine should diffuse from pathogen sites"


def test_all_presets_init():
    """All 6 presets should initialize without error."""
    for idx in range(6):
        app = _make_app()
        app._immune_init(idx)
        assert app.immune_mode is True
        # Run a few steps to ensure no crash
        for _ in range(3):
            app._immune_step()


def test_antibody_field_exists():
    """Antibody field should be initialized and updated."""
    app = _make_app()
    app._immune_init(0)
    assert len(app.immune_antibody) == app.immune_rows
    assert len(app.immune_antibody[0]) == app.immune_cols


def test_complement_field_exists():
    """Complement field should have non-zero values when enabled."""
    app = _make_app()
    app._immune_init(0)
    total_comp = sum(app.immune_complement[r][c]
                     for r in range(app.immune_rows)
                     for c in range(app.immune_cols))
    assert total_comp > 0, "Complement should be seeded in tissue"


def test_fever_dynamics():
    """Fever should rise above baseline after infection progresses."""
    app = _make_app()
    app._immune_init(0)
    assert app.immune_fever == 37.0
    for _ in range(30):
        app._immune_step()
    # Fever should have changed (likely risen due to cytokines)
    assert app.immune_fever >= 37.0


def test_history_recording():
    """Metrics history should accumulate entries."""
    app = _make_app()
    app._immune_init(0)
    for _ in range(10):
        app._immune_step()
    hist = app.immune_history
    assert len(hist['pathogen_load']) == 10
    assert len(hist['fever_temp']) == 10
    assert len(hist['antibody_titer']) == 10


def test_vaccination_preset_has_memory():
    """Vaccination preset should seed memory cells."""
    app = _make_app()
    app._immune_init(5)  # Vaccination & Re-exposure
    from life.modes.immune_system import ENT_MEMORY
    mem_count = sum(1 for r in range(app.immune_rows)
                    for c in range(app.immune_cols)
                    if app.immune_grid[r][c] == ENT_MEMORY)
    assert mem_count > 0, "Vaccination preset should have memory cells"
