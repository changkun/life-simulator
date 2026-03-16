"""Tests for evolution_lab mode."""
from tests.conftest import make_mock_app
from life.modes.evolution_lab import register


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_elab_mode()
    assert app.elab_menu is True
    assert app.elab_mode is False


def test_step_no_crash():
    app = _make_app()
    app.elab_mode = True
    app._elab_init()
    assert app.elab_mode is True
    assert len(app.elab_sims) > 0
    for _ in range(10):
        app._elab_step()


def test_exit_cleanup():
    app = _make_app()
    app.elab_mode = True
    app._elab_init()
    app._exit_elab_mode()
    assert app.elab_mode is False
    assert app.elab_sims == []
    assert app.elab_genomes == []
