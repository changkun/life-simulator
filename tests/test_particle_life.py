"""Tests for particle_life mode."""
import random
import math
import pytest
from tests.conftest import make_mock_app
from life.modes.particle_life import register


# (name, desc, num_types, density, max_radius, friction, force_scale, seed)
PLIFE_PRESETS = [
    ("Primordial Soup", "Random rules", 6, 0.06, 15.0, 0.5, 0.05, None),
    ("Symbiosis", "Orbiting species", 4, 0.05, 18.0, 0.4, 0.04, 42),
    ("Clusters", "Self-organizing clumps", 3, 0.08, 12.0, 0.6, 0.06, 123),
]

PLIFE_CHARS = ["\u25cf", "\u25c6", "\u25a0", "\u25b2", "\u2605", "\u25c9", "\u2666", "\u2726"]
PLIFE_COLORS = [1, 2, 3, 4, 5, 6, 7, 1]


class TestParticleLife:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        cls = type(self.app)
        cls.PLIFE_PRESETS = PLIFE_PRESETS
        cls.PLIFE_CHARS = PLIFE_CHARS
        cls.PLIFE_COLORS = PLIFE_COLORS
        # Instance defaults
        self.app.plife_steps_per_frame = 1
        self.app.plife_preset_name = ""
        self.app.plife_num_particles = 0
        self.app.plife_num_types = 6
        self.app.plife_rules = []
        self.app.plife_particles = []
        self.app.plife_max_radius = 15.0
        self.app.plife_friction = 0.5
        self.app.plife_force_scale = 0.05
        register(cls)

    def test_enter(self):
        self.app._enter_plife_mode()
        assert self.app.plife_menu is True
        assert self.app.plife_menu_sel == 0

    def test_init(self):
        self.app._plife_init(0)
        assert self.app.plife_mode is True
        assert self.app.plife_menu is False
        assert self.app.plife_generation == 0
        assert len(self.app.plife_particles) > 0
        assert len(self.app.plife_rules) > 0
        assert self.app.plife_preset_name == "Primordial Soup"

    def test_init_with_seed(self):
        # Preset with seed=42 should produce deterministic results
        self.app._plife_init(1)
        particles_1 = [p[:] for p in self.app.plife_particles]
        self.app._plife_init(1)
        particles_2 = [p[:] for p in self.app.plife_particles]
        assert len(particles_1) == len(particles_2)
        for p1, p2 in zip(particles_1, particles_2):
            assert p1 == p2

    def test_step_no_crash(self):
        self.app._plife_init(1)  # Use seeded preset for determinism
        for _ in range(10):
            self.app._plife_step()
        assert self.app.plife_generation == 10

    def test_particles_stay_in_bounds(self):
        self.app._plife_init(1)
        for _ in range(10):
            self.app._plife_step()
        rows, cols = self.app.plife_rows, self.app.plife_cols
        for p in self.app.plife_particles:
            assert 0 <= p[0] < rows
            assert 0 <= p[1] < cols

    def test_velocity_clamped(self):
        self.app._plife_init(1)
        for _ in range(10):
            self.app._plife_step()
        for p in self.app.plife_particles:
            spd = math.sqrt(p[2] ** 2 + p[3] ** 2)
            assert spd <= 2.0 + 0.01  # max_spd is 2.0 in _plife_step

    def test_rules_matrix(self):
        self.app._plife_init(0)
        rules = self.app.plife_rules
        nt = self.app.plife_num_types
        assert len(rules) == nt
        for row in rules:
            assert len(row) == nt
            for val in row:
                assert -1.0 <= val <= 1.0

    def test_exit_cleanup(self):
        self.app._plife_init(0)
        self.app._plife_step()
        self.app._exit_plife_mode()
        assert self.app.plife_mode is False
        assert self.app.plife_menu is False
        assert self.app.plife_running is False
        assert self.app.plife_particles == []
        assert self.app.plife_rules == []
