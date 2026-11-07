"""Tests for life.modes.percolation — Percolation Theory & Critical Phenomena."""
from tests.conftest import make_mock_app
from life.modes.percolation import register, PERC_PRESETS


def _make_app():
    app = make_mock_app()
    app.perc_mode = False
    app.perc_menu = False
    app.perc_menu_sel = 0
    app.perc_running = False
    register(type(app))
    return app


def _index(preset_id):
    return next(i for i, p in enumerate(PERC_PRESETS) if p[2] == preset_id)


def test_every_preset_inits_and_steps():
    app = _make_app()
    for i in range(len(PERC_PRESETS)):
        app._perc_init(i)
        assert app.perc_mode is True
        for _ in range(5):
            app._perc_step()
        assert app.perc_generation == 5


def test_invasion_ignores_p_keys():
    app = _make_app()
    app._perc_init(_index("invasion"))
    for _ in range(3):
        app._perc_step()
    p = app.perc_p
    for key in (ord("p"), ord("P"), ord("c")):
        assert app._handle_perc_key(key) is True
    assert app.perc_p == p


def test_critical_key_sets_site_threshold():
    app = _make_app()
    app._perc_init(_index("site"))
    app._handle_perc_key(ord("c"))
    assert abs(app.perc_p - 0.5927) < 1e-9
