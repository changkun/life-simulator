"""Tests for CRISPR-Cas9 Gene Editing & Repair mode."""
import random

from tests.conftest import make_mock_app
from life.modes import crispr
from life.modes.crispr import register, CRISPR_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    app.crispr_mode = False
    app.crispr_menu = False
    app.crispr_menu_sel = 0
    app.crispr_running = False
    return app


def test_complement_handles_deleted_bases():
    assert crispr._complement_seq(list("AC-G")) == ["T", "G", "N", "C"]


def test_long_run_all_presets():
    """Deletions followed by base, prime and HDR edits must not crash."""
    for idx in range(len(CRISPR_PRESETS)):
        random.seed(idx)
        app = _make_app()
        app._crispr_init(idx)
        for _ in range(800):
            app._crispr_step()
        assert app.crispr_generation == 800


def test_init_baseline_matches_dna():
    """Edits are measured against the finished setup, not the raw sequence."""
    for seed in range(10):
        random.seed(seed)
        app = _make_app()
        app._crispr_init(2)
        assert app.crispr_dna == app.crispr_dna_original


def test_on_target_site_matches_guide():
    """Seeded off-target sites must not overwrite the on-target match."""
    for seed in range(20):
        random.seed(seed)
        app = _make_app()
        app._crispr_init(2)  # Off-Target Mutagenesis: most seeded sites
        app.crispr_guide = crispr._generate_guide_for_target(
            app.crispr_dna, app.crispr_target_pam)
        score = crispr._match_score(
            app.crispr_guide, app.crispr_dna, app.crispr_target_pam)
        assert score == crispr._GUIDE_LEN
        assert len(app.crispr_off_targets) <= 6


def test_exit_cleanup_and_reentry():
    app = _make_app()
    app._crispr_init(3)
    app.crispr_mode = True
    app._exit_crispr_mode()
    assert app.crispr_mode is False
    assert "crispr_pop" not in vars(app)
    app._crispr_init(0)
    assert app.crispr_generation == 0
