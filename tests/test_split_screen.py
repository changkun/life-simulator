"""Tests for Split-Screen Dual Simulation."""
from tests.conftest import make_mock_app
from life.modes.split_screen import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.split_mode = False
    app.split_menu = False
    app.split_running = False
    return app


def test_reset_keeps_pane_dimensions():
    """Resetting a pane must not change its grid size, or coupling would mix sizes."""
    app = _make_app()
    app._split_init("gol", "rd")
    rows, cols = app.split_left["sim_rows"], app.split_left["sim_cols"]
    app.split_focus = 0
    app._handle_split_key(ord("r"))
    pane = app.split_left
    assert (pane["sim_rows"], pane["sim_cols"]) == (rows, cols)
    assert len(pane["density"]) == rows
    assert len(pane["density"][0]) == cols
    assert len(app.split_right["density"][0]) == cols
    assert pane["generation"] == 0


def test_step_and_exit():
    app = _make_app()
    app._split_init("wave", "ising")
    app.split_coupling = 0.5
    for _ in range(5):
        app._split_step()
    assert app.split_generation == 5
    app._exit_split_mode()
    assert app.split_mode is False
    assert app.split_left is None
