"""Tests for Rule Phylogenetics mode."""
from life.modes.rule_phylogenetics import _build_lineage, _cluster_entries


def _entries():
    return [
        {"label": "B3/S23", "classification": "glider", "score": 10, "round": 0},
        {"label": "B36/S23", "classification": "glider", "score": 9, "round": 0},
        {"label": "B2/S", "classification": "chaotic", "score": 40, "round": 1},
        {"label": "B1357/S1357", "classification": "replicator", "score": 5, "round": 1},
    ]


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
