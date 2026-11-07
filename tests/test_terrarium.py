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
    enabled = False

    def reset(self):
        pass


class _Analytics:
    phase_detector = _Detector()


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
