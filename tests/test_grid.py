"""Tests for the Grid class."""
import pytest
from life.grid import Grid


class TestGridBasics:
    def setup_method(self):
        self.grid = Grid(10, 10)

    def test_initial_state(self):
        assert self.grid.rows == 10
        assert self.grid.cols == 10
        assert self.grid.generation == 0
        assert self.grid.population == 0
        assert self.grid.birth == {3}
        assert self.grid.survival == {2, 3}

    def test_set_alive(self):
        self.grid.set_alive(0, 0)
        assert self.grid.cells[0][0] == 1
        assert self.grid.population == 1

    def test_set_dead(self):
        self.grid.set_alive(0, 0)
        self.grid.set_dead(0, 0)
        assert self.grid.cells[0][0] == 0
        assert self.grid.population == 0

    def test_is_alive(self):
        assert not self.grid.is_alive(0, 0)
        self.grid.set_alive(0, 0)
        assert self.grid.is_alive(0, 0)
        assert not self.grid.is_alive(-1, 0)
        assert not self.grid.is_alive(0, 100)

    def test_toggle(self):
        self.grid.toggle(5, 5)
        assert self.grid.cells[5][5] > 0
        self.grid.toggle(5, 5)
        assert self.grid.cells[5][5] == 0

    def test_clear(self):
        self.grid.set_alive(1, 1)
        self.grid.set_alive(2, 2)
        self.grid.clear()
        assert self.grid.population == 0
        assert self.grid.generation == 0

    def test_load_pattern(self):
        self.grid.load_pattern("block")
        assert self.grid.population == 4

    def test_load_pattern_unknown(self):
        self.grid.load_pattern("nonexistent_pattern")
        assert self.grid.population == 0


class TestGridStep:
    def test_blinker_oscillates(self):
        g = Grid(5, 5)
        # Horizontal blinker at center
        g.set_alive(2, 1)
        g.set_alive(2, 2)
        g.set_alive(2, 3)
        g.step()
        # Should become vertical
        assert g.cells[1][2] > 0
        assert g.cells[2][2] > 0
        assert g.cells[3][2] > 0
        assert g.cells[2][1] == 0
        assert g.cells[2][3] == 0
        assert g.generation == 1

    def test_block_stable(self):
        g = Grid(5, 5)
        g.set_alive(1, 1)
        g.set_alive(1, 2)
        g.set_alive(2, 1)
        g.set_alive(2, 2)
        g.step()
        assert g.population == 4
        assert g.cells[1][1] > 0

    def test_cell_aging(self):
        g = Grid(5, 5)
        # Block stays alive, ages
        g.set_alive(1, 1)
        g.set_alive(1, 2)
        g.set_alive(2, 1)
        g.set_alive(2, 2)
        g.step()
        assert g.cells[1][1] == 2  # age increments

    def test_step_updates_generation(self):
        g = Grid(5, 5)
        g.step()
        assert g.generation == 1
        g.step()
        assert g.generation == 2


class TestGridTopology:
    def test_torus_wrap(self):
        g = Grid(5, 5)
        assert g._wrap(-1, -1) == (4, 4)
        assert g._wrap(5, 5) == (0, 0)

    def test_plane_no_wrap(self):
        g = Grid(5, 5)
        g.topology = Grid.TOPO_PLANE
        assert g._wrap(-1, 0) is None
        assert g._wrap(0, 0) == (0, 0)

    def test_klein_bottle(self):
        g = Grid(5, 5)
        g.topology = Grid.TOPO_KLEIN
        coord = g._wrap(-1, 2)
        assert coord is not None
        assert coord[0] == 4  # wrapped row

    def test_mobius_strip(self):
        g = Grid(5, 5)
        g.topology = Grid.TOPO_MOBIUS
        assert g._wrap(-1, 2) is None  # rows don't wrap
        coord = g._wrap(2, -1)
        assert coord is not None


class TestGridHex:
    def test_hex_neighbour_count(self):
        g = Grid(10, 10)
        g.hex_mode = True
        # Set some neighbors for cell (4, 4)
        g.set_alive(3, 4)
        g.set_alive(3, 5)
        n = g._count_neighbours(4, 4)
        assert n == 2


class TestGridSerialization:
    def test_to_dict_load_dict_roundtrip(self):
        g = Grid(10, 10)
        g.set_alive(1, 2)
        g.set_alive(3, 4)
        g.generation = 42
        d = g.to_dict()
        g2 = Grid(10, 10)
        g2.load_dict(d)
        assert g2.generation == 42
        assert g2.population == 2
        assert g2.cells[1][2] > 0
        assert g2.cells[3][4] > 0

    def test_state_hash_deterministic(self):
        g = Grid(5, 5)
        g.set_alive(1, 1)
        h1 = g.state_hash()
        h2 = g.state_hash()
        assert h1 == h2

    def test_state_hash_changes(self):
        g = Grid(5, 5)
        g.set_alive(1, 1)
        h1 = g.state_hash()
        g.set_alive(2, 2)
        h2 = g.state_hash()
        assert h1 != h2
