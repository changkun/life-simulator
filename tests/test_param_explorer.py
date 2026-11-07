"""Tests for life.modes.param_explorer — Parameter Space Explorer mode."""
from tests.conftest import make_mock_app
from life.modes.param_explorer import register


def _make_app():
    app = make_mock_app()
    app.pexplorer_mode = False
    app.pexplorer_menu = False
    app.pexplorer_menu_sel = 0
    app.pexplorer_running = False
    app.pexplorer_sims = []
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_param_explorer_mode()
    assert app.pexplorer_menu is True
    assert app.pexplorer_menu_sel == 0


def test_step_no_crash():
    app = _make_app()
    app._pexplorer_init(0)  # Init with first explorable mode (RD)
    assert app.pexplorer_mode is True
    assert app.pexplorer_menu is False
    app.pexplorer_running = True
    for _ in range(10):
        app._pexplorer_step()
    assert app.pexplorer_generation == 20  # 2 steps per frame * 10


def test_exit_cleanup():
    app = _make_app()
    app._pexplorer_init(0)
    app._exit_param_explorer_mode()
    assert app.pexplorer_mode is False
    assert app.pexplorer_running is False
    assert app.pexplorer_sims == []


def test_parameter_grid_interpolation():
    """Each tile in the grid should have distinct, linearly interpolated parameters."""
    app = _make_app()
    app._pexplorer_init(0)  # RD mode
    gr = app.pexplorer_grid_rows
    gc = app.pexplorer_grid_cols
    # Parameters across columns (param_x = feed) should be monotonically increasing
    for row in range(gr):
        prev_px = None
        for col in range(gc):
            px, py = app.pexplorer_params[row][col]
            if prev_px is not None and gc > 1:
                assert px >= prev_px, "param_x should increase across columns"
            prev_px = px
    # Parameters across rows (param_y = kill) should be monotonically increasing
    for col in range(gc):
        prev_py = None
        for row in range(gr):
            px, py = app.pexplorer_params[row][col]
            if prev_py is not None and gr > 1:
                assert py >= prev_py, "param_y should increase across rows"
            prev_py = py


def test_step_advances_all_sims():
    """Stepping should advance every mini-simulation in the grid."""
    app = _make_app()
    app._pexplorer_init(0)
    # Verify all sims start at generation 0
    for row in app.pexplorer_sims:
        for sim in row:
            assert sim["gen"] == 0
    app._pexplorer_step()
    # After one step, every sim should have advanced
    for row in app.pexplorer_sims:
        for sim in row:
            assert sim["gen"] == app.pexplorer_steps_per_frame


def test_zoom_narrows_parameter_range():
    """Zooming into a tile should narrow the parameter range."""
    app = _make_app()
    app._pexplorer_init(0)
    full_px = app.pexplorer_px_range
    full_py = app.pexplorer_py_range
    full_span_x = full_px[1] - full_px[0]
    full_span_y = full_py[1] - full_py[0]
    # Zoom into center tile
    cr = app.pexplorer_grid_rows // 2
    cc = app.pexplorer_grid_cols // 2
    px, py = app.pexplorer_params[cr][cc]
    app._pexplorer_init(0, center_x=px, center_y=py)
    zoomed_span_x = app.pexplorer_px_range[1] - app.pexplorer_px_range[0]
    zoomed_span_y = app.pexplorer_py_range[1] - app.pexplorer_py_range[0]
    assert zoomed_span_x < full_span_x, "Zoomed x-range should be narrower"
    assert zoomed_span_y < full_span_y, "Zoomed y-range should be narrower"


def test_zoom_in_narrows_each_time_and_out_widens():
    app = _make_app()
    app._pexplorer_init(0)
    full = app.pexplorer_px_full
    full_span = full[1] - full[0]
    span0 = app.pexplorer_px_range[1] - app.pexplorer_px_range[0]
    px, py = app.pexplorer_params[2][2]
    app._pexplorer_zoom(0.4, px, py)
    span1 = app.pexplorer_px_range[1] - app.pexplorer_px_range[0]
    app._pexplorer_zoom(0.4, px, py)
    span2 = app.pexplorer_px_range[1] - app.pexplorer_px_range[0]
    assert span1 < span0 and span2 < span1
    assert span2 >= 0.05 * full_span - 1e-12
    app._pexplorer_zoom(1.5, px, py)
    span3 = app.pexplorer_px_range[1] - app.pexplorer_px_range[0]
    assert span3 > span2
    lo, hi = app.pexplorer_px_range
    assert full[0] <= lo and hi <= full[1]


def test_zoom_out_key_widens_range():
    app = _make_app()
    app._pexplorer_init(0)
    px, py = app.pexplorer_params[1][1]
    app._pexplorer_zoom(0.4, px, py)
    before = app.pexplorer_px_range[1] - app.pexplorer_px_range[0]
    app._handle_pexplorer_key(ord("z"))
    after = app.pexplorer_px_range[1] - app.pexplorer_px_range[0]
    assert after > before


def test_steps_per_frame_survives_zoom():
    app = _make_app()
    app._enter_param_explorer_mode()
    app._pexplorer_init(0)
    app._handle_pexplorer_key(ord("+"))
    steps = app.pexplorer_steps_per_frame
    assert steps == 3
    app._handle_pexplorer_key(10)
    assert app.pexplorer_steps_per_frame == steps
    app._enter_param_explorer_mode()
    assert app.pexplorer_steps_per_frame == 2
