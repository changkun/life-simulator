"""Tests for Mitosis & Cell Division Cycle mode."""
import random

from tests.conftest import make_mock_app
from life.modes.mitosis import (
    register, MITOSIS_PRESETS, _PHASE_APOPTOTIC,
)


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.mitosis_mode = False
    app.mitosis_menu = False
    app.mitosis_menu_sel = 0
    app.mitosis_running = False
    return app


def _count_cells(app):
    return sum(1 for row in app.mitosis_cells for c in row if c is not None)


def test_enter_shows_menu():
    app = _make_app()
    app._enter_mitosis_mode()
    assert app.mitosis_menu is True
    assert app.mitosis_menu_sel == 0


def test_menu_enter_starts_preset():
    app = _make_app()
    app._enter_mitosis_mode()
    app._handle_mitosis_menu_key(ord('j'))
    assert app.mitosis_menu_sel == 1
    app._handle_mitosis_menu_key(10)
    assert app.mitosis_menu is False
    assert app.mitosis_preset_name == MITOSIS_PRESETS[1][0]
    assert app.mitosis_running is True


def test_all_presets_start_and_evolve():
    for i in range(len(MITOSIS_PRESETS)):
        random.seed(i)
        app = _make_app()
        app._mitosis_init(i)
        assert _count_cells(app) > 0
        for _ in range(60):
            app._mitosis_step()
        assert app.mitosis_generation == 60
        assert len(app.mitosis_history['total_cells']) == 60
        assert any(c['phase'] != 1 for row in app.mitosis_cells
                   for c in row if c is not None)


def test_history_is_bounded():
    random.seed(1)
    app = _make_app()
    app._mitosis_init(0)
    for _ in range(520):
        app._mitosis_step()
    assert all(len(v) == 500 for v in app.mitosis_history.values())


def test_tumor_preset_gains_aneuploidy():
    random.seed(3)
    app = _make_app()
    app._mitosis_init(2)
    for _ in range(200):
        app._mitosis_step()
    assert app.mitosis_history['aneuploid_frac'][-1] > 0


def test_keys():
    random.seed(2)
    app = _make_app()
    app._mitosis_init(0)
    app._handle_mitosis_key(ord(' '))
    assert app.mitosis_running is True
    app._handle_mitosis_key(ord(' '))
    assert app.mitosis_running is False
    app._handle_mitosis_key(ord('n'))
    assert app.mitosis_generation == 1
    app._handle_mitosis_key(ord('v'))
    assert app.mitosis_view == "detail"
    for _ in range(10):
        app._handle_mitosis_key(ord('+'))
    assert app.mitosis_speed == 8
    for _ in range(10):
        app._handle_mitosis_key(ord('-'))
    assert app.mitosis_speed == 1
    app._handle_mitosis_key(ord('R'))
    assert app.mitosis_menu is True
    assert app._handle_mitosis_key(ord('z')) is False


def test_apoptosis_key_marks_selected_cell():
    random.seed(4)
    app = _make_app()
    app._mitosis_init(0)
    app.mitosis_sel_r, app.mitosis_sel_c = 0, 0
    app.mitosis_cells[0][0] = {
        'phase': 1, 'apoptosis_timer': 0, 'aneuploid': False,
    }
    app._handle_mitosis_key(ord('a'))
    assert app.mitosis_cells[0][0]['phase'] == _PHASE_APOPTOTIC
    assert app.mitosis_apo_signal[0][0] == 1.0


def test_exit_clears_state():
    app = _make_app()
    app._mitosis_init(0)
    app._exit_mitosis_mode()
    assert app.mitosis_mode is False
    assert app.mitosis_menu is False
    assert app.mitosis_running is False


def test_reenter_after_exit():
    app = _make_app()
    app._mitosis_init(0)
    app._exit_mitosis_mode()
    app._enter_mitosis_mode()
    app._handle_mitosis_menu_key(10)
    assert _count_cells(app) > 0
    app._mitosis_step()


def test_escape_leaves_the_run():
    app = _make_app()
    app._mitosis_init(0)
    assert app._handle_mitosis_key(27) is True
    assert app.mitosis_mode is False
