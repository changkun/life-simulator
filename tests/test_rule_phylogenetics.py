"""Tests for Rule Phylogenetics mode."""
import curses

from life.modes import rule_phylogenetics as rp
from life.modes.rule_phylogenetics import _build_lineage, _cluster_entries
from tests.conftest import make_mock_app


def _entries():
    return [
        {"label": "B3/S23", "classification": "glider", "score": 10, "round": 0},
        {"label": "B36/S23", "classification": "glider", "score": 9, "round": 0},
        {"label": "B2/S", "classification": "chaotic", "score": 40, "round": 1},
        {"label": "B1357/S1357", "classification": "replicator", "score": 5, "round": 1},
    ]


def _analyzed_app():
    app = make_mock_app()
    rp.register(type(app))
    rp._phylo_init_state(app)
    app.phylo_entries = _entries()
    rp._phylo_analyze(app)
    return app


def test_weights_change_the_tree():
    """Different distance weights produce different merge heights."""
    a = _cluster_entries(_entries(), (1.0, 0.0, 0.0))
    b = _cluster_entries(_entries(), (0.0, 0.0, 1.0))
    assert a["dist"] != b["dist"]


def test_weights_change_the_lineage():
    """Lineage distances follow the weights."""
    a = _build_lineage(_entries(), (1.0, 0.0, 0.0))
    b = _build_lineage(_entries(), (0.0, 0.0, 1.0))
    assert [x["distance"] for x in a] != [x["distance"] for x in b]


def test_preview_runs_without_prior_space():
    """Enter starts a preview that the main loop steps."""
    app = _analyzed_app()
    app._handle_phylo_key(ord("3"))
    app._handle_phylo_key(10)
    assert app.phylo_preview is not None
    assert app.phylo_running and app.phylo_preview_running
    app._phylo_step()
    assert app.phylo_preview_step == 1
    app._handle_phylo_key(ord("q"))
    assert app.phylo_preview is None and not app.phylo_running


def test_cursor_stays_inside_lists():
    """Down never moves the cursor past the end of the current view."""
    app = _analyzed_app()
    for view_key in "12345":
        app._handle_phylo_key(ord(view_key))
        for _ in range(100):
            app._handle_phylo_key(curses.KEY_DOWN)
        assert app.phylo_cursor < max(1, len(app.phylo_entries))
        assert app.phylo_tree_cursor < max(1, len(app.phylo_tree_lines))


def test_tree_cursor_previews_a_leaf():
    """Enter on a tree leaf previews that rule; internal nodes do nothing."""
    app = _analyzed_app()
    labels = {e["label"] for e in app.phylo_entries}
    for _ in range(len(app.phylo_tree_lines) - 1):
        app._handle_phylo_key(curses.KEY_DOWN)
    app._handle_phylo_key(10)
    assert app.phylo_preview_label in labels
