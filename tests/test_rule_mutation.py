"""Tests for life.modes.rule_mutation — Rule Mutation Engine."""
import random
from types import SimpleNamespace

from tests.conftest import make_mock_app
from life.modes import rule_mutation as rm


def _make_app(rows=30, cols=80):
    app = make_mock_app(rows, cols)
    rm.register(type(app))
    app.analytics = SimpleNamespace(
        phase_detector=SimpleNamespace(enabled=False))
    return app


def _start(app, name):
    idx = [p[0] for p in rm.RMUT_PRESETS].index(name)
    app._enter_rmut_mode()
    app._rmut_init(idx)


def test_from_nothing_finds_a_viable_rule():
    """An empty ruleset kills the grid, so mutants must get a re-seeded grid."""
    random.seed(1)
    app = _make_app()
    _start(app, "From Nothing")
    for _ in range(rm._EVAL_WINDOW * 12):
        app._rmut_step()
    assert app.rmut_accepted_mutations > 0
    assert app.rmut_current_birth


def test_lineage_parent_is_the_rule_that_was_mutated():
    random.seed(3)
    app = _make_app()
    _start(app, "Chaos Seeker")
    for _ in range(rm._EVAL_WINDOW * 30):
        before = rm.rule_string(app.rmut_current_birth,
                                app.rmut_current_survival)
        n = len(app.rmut_lineage)
        app._rmut_step()
        if len(app.rmut_lineage) > n:
            assert app.rmut_lineage[-1].parent_str == before
    assert len(app.rmut_lineage) > 3


def test_full_reset_cancels_a_mutant_under_test():
    random.seed(5)
    app = _make_app()
    _start(app, "Entropy Climber")
    for _ in range(rm._EVAL_WINDOW + 5):
        app._rmut_step()
    assert app.rmut_eval_phase == "evaluating"
    app._handle_rmut_key(ord("R"))
    assert app.rmut_eval_phase == "stable"
    assert app.rmut_candidate_birth is None


def test_complexity_hunter_description_matches_fitness():
    """_compute_fitness has no diversity term, so the text must not claim one."""
    desc = dict((p[0], p[1]) for p in rm.RMUT_PRESETS)["Complexity Hunter"]
    assert "diversity" not in desc.lower()
    assert len(desc) <= 70
