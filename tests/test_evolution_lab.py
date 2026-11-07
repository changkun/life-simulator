"""Tests for evolution_lab mode."""
from tests.conftest import make_mock_app
from life.modes.evolution_lab import (
    register, _random_genome, _crossover, _mutate,
    _genome_label, _create_sim, _step_sim, _compute_fitness,
    _FITNESS_PRESETS,
)


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    app._enter_elab_mode()
    assert app.elab_menu is True
    assert app.elab_mode is False


def test_step_no_crash():
    app = _make_app()
    app.elab_mode = True
    app._elab_init()
    assert app.elab_mode is True
    assert len(app.elab_sims) > 0
    for _ in range(10):
        app._elab_step()


def test_exit_cleanup():
    app = _make_app()
    app.elab_mode = True
    app._elab_init()
    app._exit_elab_mode()
    assert app.elab_mode is False
    assert app.elab_sims == []
    assert app.elab_genomes == []


def test_random_genome_valid():
    """Random genomes always have at least one birth and survival rule."""
    for _ in range(20):
        g = _random_genome()
        assert len(g["birth"]) >= 1
        assert len(g["survival"]) >= 1
        assert g["neighborhood"] in ("moore", "von_neumann")
        assert g["num_states"] >= 2


def test_crossover_produces_valid_child():
    """Crossover of two genomes produces a valid child genome."""
    g1 = _random_genome()
    g2 = _random_genome()
    child = _crossover(g1, g2)
    assert len(child["birth"]) >= 1
    assert child["neighborhood"] in ("moore", "von_neumann")
    assert child["num_states"] >= 2


def test_mutation_preserves_validity():
    """Mutated genome still has at least one birth rule."""
    g = _random_genome()
    for _ in range(20):
        g = _mutate(g, rate=0.5)
        assert len(g["birth"]) >= 1


def test_genome_label_format():
    """genome_label produces a non-empty string."""
    g = {"birth": {3}, "survival": {2, 3}, "neighborhood": "moore", "num_states": 2}
    label = _genome_label(g)
    assert len(label) > 0
    assert "B3" in label or "b3" in label.lower() or "/" in label


def test_fitness_scoring():
    """Fitness computation returns all expected metric keys."""
    g = _random_genome()
    grid = _create_sim(g, 10, 10)
    pop_history = []
    for _ in range(20):
        _step_sim(grid)
        pop_history.append(grid.population)
    weights = _FITNESS_PRESETS["balanced"]
    fitness = _compute_fitness(grid, pop_history, weights)
    assert "total" in fitness
    assert "entropy" in fitness
    assert "symmetry" in fitness
    assert "stability" in fitness
    assert "longevity" in fitness
    assert "diversity" in fitness
    assert fitness["total"] >= 0


def test_scoring_triggers_phase_change():
    """Scoring all organisms transitions phase to 'scored'."""
    app = _make_app()
    app.elab_mode = True
    app.elab_auto_advance = False  # prevent auto-breed
    app.elab_auto_breed = False
    app._elab_init()
    # Fast-forward to eval point
    for _ in range(app.elab_eval_gens + 1):
        app._elab_step()
    assert app.elab_phase == "scored"


def test_s_saves_and_a_adopts(tmp_path, monkeypatch):
    import life.modes.evolution_lab as lab
    monkeypatch.setattr(lab, "_SAVED_FILE", str(tmp_path / "evolution_lab.json"))
    monkeypatch.setattr(lab, "SAVE_DIR", str(tmp_path))
    app = _make_app()
    app._elab_init()
    app.elab_cursor = 1
    app._handle_elab_key(ord("s"))
    assert app.elab_cursor == 1
    assert (tmp_path / "evolution_lab.json").exists()
    birth = set(app.elab_genomes[1]["birth"])
    app._handle_elab_key(ord("a"))
    assert app.elab_mode is False
    assert app.grid.birth == birth


def test_space_breeds_next_generation_when_scored_with_auto_advance_off():
    app = _make_app()
    app.elab_auto_advance = False
    app._elab_init()
    app._elab_score_all()
    assert app.elab_phase == "scored"
    gen = app.elab_generation
    app._handle_elab_key(ord(" "))
    assert app.elab_generation == gen + 1
    assert app.elab_phase == "simulating"
    assert app.elab_running is True
