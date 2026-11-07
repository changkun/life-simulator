"""Tests for primordial_soup mode (RNA-world / origin-of-life rewrite)."""
import curses
import random
from tests.conftest import make_mock_app
from life.modes.primordial_soup import (
    register, PSOUP_PRESETS, MOL_WATER, MOL_ROCK, MOL_VENT, MOL_MINERAL,
    VIEWS, _energy_at,
)


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.psoup_mode = False
    app.psoup_menu = False
    app.psoup_menu_sel = 0
    app.psoup_running = False
    return app


def _idx(preset_id):
    return next(i for i, p in enumerate(PSOUP_PRESETS) if p[2] == preset_id)


def test_register_exposes_presets():
    app = _make_app()
    assert type(app).PRIMSOUP_PRESETS is PSOUP_PRESETS
    assert len(PSOUP_PRESETS) >= 6
    ids = [p[2] for p in PSOUP_PRESETS]
    assert len(set(ids)) == len(ids)


def test_enter():
    app = _make_app()
    app._enter_psoup_mode()
    assert app.psoup_mode is True
    assert app.psoup_menu is True
    assert app.psoup_menu_sel == 0


def test_exit_cleanup():
    app = _make_app()
    app._psoup_init(0)
    app._exit_psoup_mode()
    assert app.psoup_mode is False
    assert app.psoup_menu is False
    assert app.psoup_running is False
    # per-run state is removed (mock returns False for missing attrs)
    assert "psoup_grid" not in vars(app)


def test_all_presets_init():
    """Every preset initializes with consistent grids and parameters."""
    for idx in range(len(PSOUP_PRESETS)):
        random.seed(idx)
        app = _make_app()
        app._psoup_init(idx)
        assert app.psoup_preset_idx == idx
        assert app.psoup_menu is False
        assert len(app.psoup_grid) == app.psoup_rows
        assert all(len(row) == app.psoup_cols for row in app.psoup_grid)
        assert len(app.psoup_energy) == app.psoup_rows
        assert len(app.psoup_vents) == app.psoup_params["n_vents"] > 0


def test_init_does_not_autostart():
    app = _make_app()
    app._psoup_init(0)
    assert app.psoup_running is False
    assert app.psoup_generation == 0


def test_vents_and_floor_present_in_grid():
    random.seed(42)
    app = _make_app()
    app._psoup_init(_idx("black_smoker"))
    flat = [c for row in app.psoup_grid for c in row]
    assert flat.count(MOL_VENT) > 0
    assert flat.count(MOL_ROCK) + flat.count(MOL_MINERAL) > 0
    assert flat.count(MOL_WATER) > 0


def test_preseeded_presets():
    random.seed(3)
    app = _make_app()
    app._psoup_init(_idx("protocell_comp"))
    assert len(app.psoup_protocells) == app.psoup_params["preseed_protocells"]
    app = _make_app()
    app._psoup_init(_idx("error_catastrophe"))
    assert len(app.psoup_rna) > 0


def test_energy_decays_with_distance():
    vents = [(10, 10)]
    near = _energy_at(10, 11, vents, 1.0, 50.0)
    far = _energy_at(0, 0, vents, 1.0, 50.0)
    assert near > far
    assert 0 < far <= near <= 1.0


def test_step_no_crash_all_presets():
    for idx in range(len(PSOUP_PRESETS)):
        random.seed(idx)
        app = _make_app()
        app.psoup_mode = True
        app._psoup_init(idx)
        for _ in range(10):
            app._psoup_step()
        assert app.psoup_generation == 10
        assert app.psoup_mode is True


def test_step_appends_history_and_keeps_grid_shape():
    random.seed(42)
    app = _make_app()
    app._psoup_init(0)
    for _ in range(5):
        app._psoup_step()
    h = app.psoup_history
    assert app.psoup_generation == 5
    for key in ("molecules", "amino", "nucleo", "rna_count", "protocells"):
        assert len(h[key]) == 5
    assert len(app.psoup_grid) == app.psoup_rows
    assert all(len(r) == app.psoup_cols for r in app.psoup_grid)


def test_history_is_trimmed():
    random.seed(1)
    app = _make_app()
    app._psoup_init(0)
    app.psoup_max_history = 4
    for _ in range(8):
        app._psoup_step()
    assert all(len(v) <= 4 for v in app.psoup_history.values())


# ── Menu key handling ───────────────────────────────────────────────────────

def test_menu_navigation_wraps():
    app = _make_app()
    app._enter_psoup_mode()
    app._handle_psoup_menu_key(ord("j"))
    assert app.psoup_menu_sel == 1
    app._handle_psoup_menu_key(ord("k"))
    app._handle_psoup_menu_key(curses.KEY_UP)
    assert app.psoup_menu_sel == len(PSOUP_PRESETS) - 1


def test_menu_enter_starts_selected_preset():
    app = _make_app()
    app._enter_psoup_mode()
    app._handle_psoup_menu_key(ord("j"))
    app._handle_psoup_menu_key(10)
    assert app.psoup_menu is False
    assert app.psoup_preset_idx == 1


def test_menu_escape_and_q_exit():
    for key in (27, ord("q")):
        app = _make_app()
        app._enter_psoup_mode()
        app._handle_psoup_menu_key(key)
        assert app.psoup_menu is False
        assert app.psoup_mode is False


# ── Game key handling ───────────────────────────────────────────────────────

def test_key_pause_and_single_step():
    app = _make_app()
    app._psoup_init(0)
    app._handle_psoup_key(ord(" "))
    assert app.psoup_running is True
    app._handle_psoup_key(ord(" "))
    assert app.psoup_running is False
    app._handle_psoup_key(ord("n"))
    assert app.psoup_generation == 1


def test_key_view_cycles():
    app = _make_app()
    app._psoup_init(0)
    seen = [app.psoup_view]
    for _ in range(len(VIEWS)):
        app._handle_psoup_key(ord("v"))
        seen.append(app.psoup_view)
    assert seen[0] == seen[-1]
    assert set(seen) == set(VIEWS)


def test_key_environment_controls():
    app = _make_app()
    app._psoup_init(0)
    t = app.psoup_params["temperature"]
    app._handle_psoup_key(ord("h"))
    assert app.psoup_params["temperature"] == t + 15
    app._handle_psoup_key(ord("c"))
    assert app.psoup_params["temperature"] == t
    app.psoup_params["uv_level"] = 0.0
    app._handle_psoup_key(ord("u"))
    assert app.psoup_params["uv_level"] > 0
    app._handle_psoup_key(ord("u"))
    assert app.psoup_params["uv_level"] == 0


def test_key_restart_keeps_preset():
    random.seed(5)
    app = _make_app()
    app._psoup_init(2)
    for _ in range(3):
        app._psoup_step()
    app._handle_psoup_key(ord("r"))
    assert app.psoup_generation == 0
    assert app.psoup_preset_idx == 2


def test_key_menu_return():
    app = _make_app()
    app._psoup_init(0)
    app.psoup_running = True
    app._handle_psoup_key(ord("m"))
    assert app.psoup_menu is True
    assert app.psoup_running is False


def test_key_quit_exits():
    for key in (ord("q"), 27):
        app = _make_app()
        app._psoup_init(0)
        app._handle_psoup_key(key)
        assert app.psoup_mode is False
        assert app.psoup_running is False


def test_vents_emit_gases_beside_the_vent_block():
    """Gases appear in the water ring beside the 3x3 vent block."""
    from life.modes.primordial_soup import MOL_H2, MOL_CO2, MOL_NH3
    random.seed(1)
    app = _make_app()
    app._psoup_init(0)
    gases = {MOL_H2, MOL_CO2, MOL_NH3}
    seen = 0
    for _ in range(60):
        app._psoup_step()
        for vr, vc in app.psoup_vents:
            for dc in (-2, 2):
                if 0 <= vc + dc < app.psoup_cols:
                    seen += app.psoup_grid[vr][vc + dc] in gases
    assert seen > 0
