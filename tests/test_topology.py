"""Tests for life.modes.topology — Topology Mode."""
from tests.conftest import make_mock_app
from life.modes.topology import register
from life.grid import Grid


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_enter():
    app = _make_app()
    # Topology is a cross-cutting feature, not a menu mode
    assert hasattr(app, '_topology_cycle')
    assert hasattr(app, '_topology_set')
    assert app.grid.topology == Grid.TOPO_TORUS


def test_step_no_crash():
    app = _make_app()
    # Cycle through all topologies 10 times
    for _ in range(10):
        app._topology_cycle(1)
    # Should have cycled through 5 topologies twice
    assert app.grid.topology in Grid.TOPOLOGIES


def test_exit_cleanup():
    app = _make_app()
    app._topology_set("klein_bottle")
    assert app.grid.topology == Grid.TOPO_KLEIN
    # Reset to default
    app._topology_set("torus")
    assert app.grid.topology == Grid.TOPO_TORUS
