"""Tests for life.modes.reverse_life — Reverse Life mode."""
from tests.conftest import make_mock_app
from life.modes import reverse_life as rl


def _make_app():
    app = make_mock_app()
    rl.register(type(app))
    return app


def test_enter_survives_terminal_with_few_color_pairs():
    """init_pair raises ValueError (not curses.error) above COLOR_PAIRS."""
    app = _make_app()
    app._enter_reverse_life_mode()
    assert app.reverse_life_mode is True
    assert app.reverse_life_solver is not None
