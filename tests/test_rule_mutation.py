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
