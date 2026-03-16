"""Tests for life.modes.sorting_visualizer — Sorting Visualizer mode."""
from tests.conftest import make_mock_app
from life.modes.sorting_visualizer import register


def _make_app():
    app = make_mock_app()
    app.sortvis_mode = False
    app.sortvis_menu = False
    app.sortvis_menu_sel = 0
    app.sortvis_running = False
    app.sortvis_speed = 1
    app.sortvis_show_info = False
    app.sortvis_steps = []
    app.sortvis_array = []
    app.sortvis_sorted_indices = set()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_sortvis_mode()
    assert app.sortvis_menu is True


def test_step_no_crash():
    app = _make_app()
    app.sortvis_mode = True
    app.sortvis_preset_name = "bubble"
    app._sortvis_init("bubble")
    for _ in range(10):
        app._sortvis_step()
    assert app.sortvis_generation >= 0


def test_exit_cleanup():
    app = _make_app()
    app.sortvis_mode = True
    app.sortvis_preset_name = "bubble"
    app._sortvis_init("bubble")
    app._exit_sortvis_mode()
    assert app.sortvis_mode is False
    assert app.sortvis_steps == []
