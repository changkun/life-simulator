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


class _Screen:
    def __init__(self):
        self.writes = []

    def getmaxyx(self):
        return 24, 80

    def erase(self):
        self.writes.clear()

    def addstr(self, y, x, text, *attrs):
        self.writes.append((y, x, text))


def test_h_hides_and_shows_key_hints():
    app = _make_app()
    app.stdscr = _Screen()
    sa._generate_puzzle(app)

    def bottom_row():
        app.stdscr.erase()
        app._draw_archaeo()
        return [t for y, x, t in app.stdscr.writes if y == 23]

    assert any("Space=run" in t for t in bottom_row())
    app._handle_archaeo_key(ord("h"))
    assert bottom_row() == []
    app._handle_archaeo_key(ord("h"))
    assert any("Space=run" in t for t in bottom_row())


def test_enter_variants_submit_and_start():
    for enter in (10, 13, 343):  # LF, CR, KEY_ENTER
        app = make_mock_app()
        sa.register(type(app))
        app._enter_archaeo_mode()
        assert app.archaeo_menu is True
        app._handle_archaeo_key(enter)
        assert app.archaeo_menu is False
        app.archaeo_guess_birth = set(app.archaeo_answer_birth)
        app.archaeo_guess_survival = set(app.archaeo_answer_survival)
        app._handle_archaeo_key(enter)
        assert app.archaeo_solved is True
        app._handle_archaeo_key(enter)
        assert app.archaeo_solved is False  # next puzzle
