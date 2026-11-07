"""Tests for Terrarium mode."""
import json

import pytest

from tests.conftest import make_mock_app
from life.modes import terrarium
from life.modes.terrarium import register


@pytest.fixture
def paths(tmp_path, monkeypatch):
    d = tmp_path / "terrarium"
    monkeypatch.setattr(terrarium, "TERRARIUM_DIR", str(d))
    monkeypatch.setattr(terrarium, "TERRARIUM_STATE_FILE", str(d / "state.json"))
    monkeypatch.setattr(terrarium, "TERRARIUM_CHRONICLE_FILE", str(d / "chronicle.json"))
    return d


class _Detector:
    def __init__(self):
        self.enabled = False

    def reset(self):
        pass

    def drain_pending(self):
        return []


class _Analytics:
    def __init__(self):
        self.phase_detector = _Detector()

    def update(self, grid, pop_history):
        pass


def _make_app():
    app = make_mock_app()
    register(type(app))
    app._terrarium_init()
    app.tc_colormap = "viridis"
    app.tc_colormap_idx = 0
    app.heatmap_mode = False
    app._snapshot_detect_mode = lambda: "terrarium_mode"
    app._snapshot_collect_mode_params = lambda mode: {}
    app.analytics = _Analytics()
    app.phase_transition_log = []
    app.history = []
    app.pop_history = []
    app._record_pop = lambda: None
    app._reset_cycle_detection = lambda: None
    return app


def _saved_total():
    with open(terrarium.TERRARIUM_STATE_FILE) as f:
        return json.load(f)["terrarium"]["total_generations"]


def test_total_generations_not_double_counted(paths):
    """A resumed session continues the grid's generation, so it must not be added twice."""
    app = _make_app()
    app.terrarium_first_started = 1.0
    app.grid.generation = 100
    app.terrarium_mode = True
    app._terrarium_save_state()
    assert _saved_total() == 100

    app2 = _make_app()
    app2.terrarium_mode = True
    assert app2._terrarium_load_state() is True
    app2.grid.generation += 40
    app2._terrarium_save_state()
    assert _saved_total() == 140


def test_catchup_summary_stays_bounded(paths, monkeypatch):
    """A rule that dies out every generation must not flood the summary."""
    monkeypatch.setattr(terrarium, "MAX_CATCHUP_GENS", 1000)
    monkeypatch.setattr(terrarium, "MAX_SUMMARY_EVENTS", 20)
    app = _make_app()
    app.terrarium_first_started = 1.0
    app.grid.birth, app.grid.survival = set(), set()
    app.grid.set_alive(3, 3)
    app._terrarium_catchup(100000, {"speed_idx": 2})
    assert len(app.terrarium_catchup_summary) < terrarium.MAX_SUMMARY_EVENTS + 30
    assert any("more" in line for line in app.terrarium_catchup_summary)


def test_enter_resets_chronicle_view(paths):
    """Re-entering must not reopen the chronicle viewer left open last time."""
    app = _make_app()
    app._terrarium_chronicle_view = True
    app._enter_terrarium_mode()
    assert app._terrarium_chronicle_view is False
    app._exit_terrarium_mode()
    assert app.terrarium_mode is False
    assert app.terrarium_show_summary is False


class _Screen:
    def getmaxyx(self):
        return 24, 80

    def __getattr__(self, name):
        return lambda *a, **k: None


def test_summary_scroll_stops_at_last_line(paths, monkeypatch):
    monkeypatch.setattr("curses.color_pair", lambda n: 0)
    app = _make_app()
    app.stdscr = _Screen()
    app.tc_buf = []
    app._tc_refresh = lambda: None
    app.terrarium_mode = True
    app.terrarium_show_summary = True
    app.terrarium_catchup_summary = [f"line {i}" for i in range(30)]
    for _ in range(100):
        app._handle_terrarium_summary_key(258)  # KEY_DOWN
    app._draw_terrarium_summary(24, 80)
    assert app.terrarium_summary_scroll == 30 - (24 - 5)
    app.terrarium_chronicle = [{"iso_time": "t", "generation": i, "detail": "d", "kind": "x"}
                               for i in range(40)]
    app.terrarium_summary_scroll = 500
    app._draw_terrarium_chronicle_view(24, 80)
    assert app.terrarium_summary_scroll == 40 - (24 - 5)
