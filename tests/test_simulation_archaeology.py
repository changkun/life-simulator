"""Tests for Simulation Archaeology."""
from tests.conftest import make_mock_app
from life.modes import simulation_archaeology as sa


def _make_app():
    app = make_mock_app()
    sa.register(type(app))
    app._enter_archaeo_mode()
    app.archaeo_difficulty = "expert"  # no free clues
    app._handle_archaeo_key(10)       # leave the menu (selected: easy)
    return app


def test_timeline_needs_its_clue():
    app = _make_app()
    app.archaeo_difficulty = "expert"
    sa._generate_puzzle(app)
    app.archaeo_revealed_clues = set()
    app._handle_archaeo_key(ord("t"))
    assert app.archaeo_show_timeline is False
    app.archaeo_revealed_clues.add("timeline")
    app._handle_archaeo_key(ord("t"))
    assert app.archaeo_show_timeline is True
    app._handle_archaeo_key(ord("t"))
    assert app.archaeo_show_timeline is False
