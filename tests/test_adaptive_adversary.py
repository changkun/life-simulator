"""Tests for adaptive_adversary mode."""
import curses

import pytest

from tests.conftest import make_mock_app
from life.modes import adaptive_adversary as adv
from life.modes.adaptive_adversary import register


class _RecordingScreen:
    """Screen stub that records every string drawn."""

    def __init__(self, rows=60, cols=200):
        self.rows, self.cols = rows, cols
        self.drawn = []

    def getmaxyx(self):
        return self.rows, self.cols

    def erase(self):
        pass

    def addstr(self, _y, _x, text, *_attr):
        self.drawn.append(text)


@pytest.fixture(autouse=True)
def _no_curses_colors(monkeypatch):
    """Drawing needs an initialised terminal for colour pairs; stub them."""
    monkeypatch.setattr(curses, "init_pair", lambda *a: None)
    monkeypatch.setattr(curses, "color_pair", lambda n: 0)


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.stdscr = _RecordingScreen()
    return app


def _box_lines(screen):
    return [s for s in screen.drawn if s[:1] in "╔║╠╚"]


def test_enter_and_exit():
    app = _make_app()
    app._enter_adversary_mode()
    assert app.adversary_mode is True
    assert app.adversary_cells is not None
    app._handle_adversary_key(ord("q"))
    assert app.adversary_mode is False
    assert app.adversary_cells is None


def test_reenter_resets_state():
    app = _make_app()
    app._enter_adversary_mode()
    app.adversary_wins = 5
    app.adversary_player_profile["moves_up"] = 9
    app._exit_adversary_mode()
    app._enter_adversary_mode()
    assert app.adversary_wins == 0
    assert app.adversary_player_profile["moves_up"] == 0


def test_moves_advance_turn_and_profile():
    app = _make_app()
    app._enter_adversary_mode()
    app._handle_adversary_key(ord(" "))
    assert app.adversary_turn == 1
    assert app.adversary_player_profile["total_moves"] == 1
    assert app.adversary_player_profile["moves_wait"] == 1


def test_win_then_move_advances_level():
    app = _make_app()
    app._enter_adversary_mode()
    app.adversary_player_r = app.adversary_exit_r
    app.adversary_player_c = app.adversary_exit_c - 1
    app.adversary_cells[app.adversary_exit_r][app.adversary_exit_c - 1] = adv.FLOOR
    app._handle_adversary_key(ord("d"))
    assert app.adversary_won and app.adversary_game_over
    app._handle_adversary_key(ord("d"))
    assert app.adversary_level == 2
    assert not app.adversary_game_over


def test_report_shows_zero_moves_before_play():
    app = _make_app()
    app._enter_adversary_mode()
    app.adversary_show_report = True
    app._draw_adversary()
    assert any("Total moves:     0" in s for s in app.stdscr.drawn)


def test_overlay_boxes_are_aligned():
    app = _make_app()
    app._enter_adversary_mode()
    app.adversary_player_profile["wins"] = 12
    app.adversary_show_help = True
    app._draw_adversary()
    assert len({len(s) for s in _box_lines(app.stdscr)}) == 1
    app.stdscr.drawn.clear()
    app.adversary_show_help = False
    app.adversary_show_report = True
    app._draw_adversary()
    assert len({len(s) for s in _box_lines(app.stdscr)}) == 1
