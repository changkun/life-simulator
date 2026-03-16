"""Tests for life.modes.genome — Genome Sharing System."""
from tests.conftest import make_mock_app
from life.modes.genome import register, _encode_genome, _decode_genome


def _make_app():
    app = make_mock_app()
    # genome needs _any_menu_open
    app._any_menu_open = lambda: False
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    # Genome is a cross-cutting feature, not a mode with enter
    assert hasattr(app, '_genome_handle_key')
    assert hasattr(app, '_genome_capture')


def test_step_no_crash():
    app = _make_app()
    # Test encode/decode round-trip
    config = {"_mode": "gol", "speed_idx": 2, "rule_b": [3], "rule_s": [2, 3]}
    code = _encode_genome("gol", config)
    assert code.startswith("GOL-")
    prefix, decoded = _decode_genome(code)
    assert prefix == "gol"
    assert decoded["_mode"] == "gol"
    # Run 10 round-trips
    for i in range(10):
        config["speed_idx"] = i % 8
        code = _encode_genome("gol", config)
        p, d = _decode_genome(code)
        assert d is not None


def test_exit_cleanup():
    app = _make_app()
    # No special exit for genome — just verify decode of bad input
    prefix, config = _decode_genome("INVALID")
    assert prefix is None
    assert config is None
