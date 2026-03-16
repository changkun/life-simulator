"""Tests for life.modes.evo_playground — Evolutionary Playground mode."""
from tests.conftest import make_mock_app
from life.modes.evo_playground import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_evo_playground()
    assert app.ep_menu is True
    assert app.ep_mode is False


def test_step_no_crash():
    app = _make_app()
    app._ep_init()
    assert app.ep_mode is True
    assert len(app.ep_sims) > 0
    for _ in range(10):
        app._ep_step()
    assert app.ep_sim_generation == 10


def test_exit_cleanup():
    app = _make_app()
    app._ep_init()
    app._exit_evo_playground()
    assert app.ep_mode is False
    assert app.ep_sims == []
    assert app.ep_genomes == []
    assert app.ep_selected == set()
