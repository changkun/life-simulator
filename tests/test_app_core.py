"""Tests for core App behaviour: mode switches and the galaxy minimap."""
import pytest

from tests.real_app import patch_curses, _Screen
from life.app import App


@pytest.fixture
def app(monkeypatch):
    patch_curses(monkeypatch)
    return App(_Screen([]), None, 30, 60)


def test_mode_switch_closes_menu_left_open(app):
    app._enter_nca_mode()
    assert app.nca_menu and not app.nca_mode
    app._exit_current_modes()
    assert not app.nca_menu


def test_mode_switch_closes_rule_menu_left_open(app):
    app.compare_rule_menu = True
    app._exit_current_modes()
    assert not app.compare_rule_menu
