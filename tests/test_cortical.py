"""Tests for cortical mode."""
import random
from tests.conftest import make_mock_app
from life.modes.cortical import register, CORTICAL_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    app._enter_cortical_mode()
    return app


def test_presets_start_and_step():
    random.seed(1)
    app = _make_app()
    for i in range(len(CORTICAL_PRESETS)):
        app._cortical_init(i)
        for _ in range(5):
            app._cortical_step()
        assert app.cortical_generation == 5


def test_escape_and_q_exit():
    for key in (27, ord("q")):
        app = _make_app()
        app._cortical_init(0)
        assert app._handle_cortical_key(key) is True
        assert app.cortical_mode is False


def test_exit_clears_state():
    app = _make_app()
    app._cortical_init(0)
    app._exit_cortical_mode()
    assert app.cortical_mode is False
    assert "cortical_E" not in vars(app)
