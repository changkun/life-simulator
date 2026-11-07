"""Tests for life.modes.angiogenesis — Blood Vessel Network & Angiogenesis."""
from tests.conftest import make_mock_app
from life.modes.angiogenesis import register, ANGIO_PRESETS


def _make_app():
    app = make_mock_app()
    app.angio_mode = False
    app.angio_menu = False
    register(type(app))
    return app


def _started(idx=0):
    app = _make_app()
    app._enter_angio_mode()
    app._angio_init(idx)
    app.angio_mode = True
    return app


def test_enter_opens_menu():
    app = _make_app()
    app._enter_angio_mode()
    assert app.angio_mode is True
    assert app.angio_menu is True


def test_all_presets_start_and_step():
    for idx in range(len(ANGIO_PRESETS)):
        app = _started(idx)
        for _ in range(20):
            app._angio_step()
        assert app.angio_generation == 20


def test_q_and_escape_exit():
    for key in (ord("q"), 27):
        app = _started()
        assert app._handle_angio_key(key) is True
        assert app.angio_mode is False
        assert app.angio_menu is False
        assert not getattr(app, "angio_running", False)


def test_step_advances_one_tick_regardless_of_speed():
    # The app already calls the step function angio_speed times per frame.
    app = _started()
    app.angio_speed = 5
    app._angio_step()
    assert app.angio_generation == 1
