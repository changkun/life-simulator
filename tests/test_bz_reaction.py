"""Tests for bz_reaction mode."""
import math
import random
from tests.conftest import make_mock_app
from life.modes.bz_reaction import register, BZ_FLOOR, BZ_PRESETS


class TestBZReaction:
    def setup_method(self):
        random.seed(42)
        self.app = make_mock_app()
        register(type(self.app))

    # ── Presets ──────────────────────────────────────────────────────
    def test_presets_exist(self):
        assert len(BZ_PRESETS) == 8

    def test_presets_structure(self):
        for preset in BZ_PRESETS:
            assert len(preset) == 7
            name, desc, alpha, beta, gamma, diff, init_type = preset
            assert isinstance(name, str) and name
            assert isinstance(desc, str)
            assert isinstance(alpha, (int, float)) and alpha > 0
            assert isinstance(beta, (int, float)) and beta > 0
            assert isinstance(gamma, (int, float)) and gamma > 0
            assert isinstance(diff, (int, float)) and diff > 0
            assert init_type in ("spiral_seed", "center_seed", "random_seeds",
                                 "random_noise", "multi_spiral")

    def test_presets_registered_on_class(self):
        assert hasattr(type(self.app), 'BZ_PRESETS')
        assert type(self.app).BZ_PRESETS is BZ_PRESETS

    # ── Enter / Exit ─────────────────────────────────────────────────
    def test_enter(self):
        self.app._enter_bz_mode()
        assert self.app.bz_menu is True
        assert self.app.bz_menu_sel == 0

    def test_exit_cleanup(self):
        self.app.bz_mode = True
        self.app.bz_menu_sel = 0
        self.app._bz_init(0)
        self.app._bz_step()
        self.app._exit_bz_mode()
        assert self.app.bz_mode is False
        assert self.app.bz_menu is False
        assert self.app.bz_running is False
        assert self.app.bz_a == []
        assert self.app.bz_b == []
        assert self.app.bz_c == []

    # ── Init for all presets ─────────────────────────────────────────
    def test_init_all_presets(self):
        """Every preset index initializes without error."""
        for idx in range(len(BZ_PRESETS)):
            random.seed(42)
            self.app._bz_init(idx)
            assert self.app.bz_mode is True
            assert self.app.bz_running is False
            assert self.app.bz_generation == 0
            assert self.app.bz_preset_name == BZ_PRESETS[idx][0]
            assert self.app.bz_rows > 0
            assert self.app.bz_cols > 0
            assert len(self.app.bz_a) == self.app.bz_rows
            assert len(self.app.bz_a[0]) == self.app.bz_cols

    def test_init_spiral_seed(self):
        """spiral_seed produces asymmetric wavefront with non-zero a and c."""
        self.app._bz_init(0)  # Classic Spirals uses spiral_seed
        rows, cols = self.app.bz_rows, self.app.bz_cols
        # Should have some non-zero activator values in left half
        a_sum = sum(self.app.bz_a[r][c] for r in range(rows) for c in range(cols))
        c_sum = sum(self.app.bz_c[r][c] for r in range(rows) for c in range(cols))
        assert a_sum > 0, "spiral_seed should produce non-zero activator"
        assert c_sum > 0, "spiral_seed should produce non-zero recovery"

    def test_init_center_seed(self):
        """center_seed produces a Gaussian blob centered at grid midpoint."""
        self.app._bz_init(2)  # Slow Waves uses center_seed
        cr = self.app.bz_rows // 2
        cc = self.app.bz_cols // 2
        # Center should have highest activation
        center_val = self.app.bz_a[cr][cc]
        corner_val = self.app.bz_a[0][0]
        assert center_val > corner_val

    def test_init_random_noise(self):
        """random_noise initializes all three grids with values in [0, 0.3]."""
        self.app._bz_init(3)  # Turbulent uses random_noise
        rows, cols = self.app.bz_rows, self.app.bz_cols
        for r in range(rows):
            for c in range(cols):
                assert 0.0 <= self.app.bz_a[r][c] <= 0.3
                assert 0.0 <= self.app.bz_b[r][c] <= 0.3
                assert 0.0 <= self.app.bz_c[r][c] <= 0.3

    # ── Step dynamics ────────────────────────────────────────────────
    def test_step_no_crash(self):
        self.app.bz_mode = True
        self.app.bz_menu_sel = 0
        self.app._bz_init(0)
        for _ in range(10):
            self.app._bz_step()
        assert self.app.bz_generation == 10

    def test_step_increments_generation(self):
        self.app._bz_init(0)
        assert self.app.bz_generation == 0
        self.app._bz_step()
        assert self.app.bz_generation == 1
        self.app._bz_step()
        assert self.app.bz_generation == 2

    def test_step_values_clamped(self):
        """All concentrations stay in [0, 1] after stepping."""
        self.app._bz_init(3)  # Turbulent — random noise start
        for _ in range(20):
            self.app._bz_step()
        rows, cols = self.app.bz_rows, self.app.bz_cols
        for r in range(rows):
            for c in range(cols):
                assert 0.0 <= self.app.bz_a[r][c] <= 1.0
                assert 0.0 <= self.app.bz_b[r][c] <= 1.0
                assert 0.0 <= self.app.bz_c[r][c] <= 1.0

    def test_step_evolves_state(self):
        """After stepping, the grid should differ from initial state."""
        self.app._bz_init(0)
        initial_a = [row[:] for row in self.app.bz_a]
        self.app._bz_step()
        differs = False
        for r in range(self.app.bz_rows):
            for c in range(self.app.bz_cols):
                if abs(self.app.bz_a[r][c] - initial_a[r][c]) > 1e-10:
                    differs = True
                    break
            if differs:
                break
        assert differs, "BZ step should change the activator field"

    def test_step_cyclic_rule(self):
        """Each species grows on the one it feeds on and shrinks under its predator."""
        self.app._bz_init(0)
        rows, cols = self.app.bz_rows, self.app.bz_cols
        alpha = self.app.bz_alpha
        beta = self.app.bz_beta
        gamma = self.app.bz_gamma
        diff = self.app.bz_diffusion
        a, b, c = self.app.bz_a, self.app.bz_b, self.app.bz_c

        def mean(g, r, col):
            return g[r][col] + diff * (
                g[(r - 1) % rows][col] + g[(r + 1) % rows][col]
                + g[r][(col - 1) % cols] + g[r][(col + 1) % cols]
                - 4.0 * g[r][col])

        r, col = rows // 2, cols // 2
        am, bm, cm = mean(a, r, col), mean(b, r, col), mean(c, r, col)
        expected = (
            am + am * (alpha * bm - gamma * cm),
            bm + bm * (beta * cm - alpha * am),
            cm + cm * (gamma * am - beta * bm),
        )
        expected = tuple(min(1.0, v) for v in expected)

        self.app._bz_step()
        actual = (self.app.bz_a[r][col], self.app.bz_b[r][col], self.app.bz_c[r][col])
        for got, want in zip(actual, expected):
            if want < BZ_FLOOR:
                assert 0.0 <= got < BZ_FLOOR
            else:
                assert abs(got - want) < 1e-10

    def test_species_at_zero_grows_back(self):
        """A species wiped out everywhere returns instead of freezing the grid."""
        self.app._bz_init(0)
        rows, cols = self.app.bz_rows, self.app.bz_cols
        self.app.bz_a = [[1.0] * cols for _ in range(rows)]
        self.app.bz_b = [[0.0] * cols for _ in range(rows)]
        self.app.bz_c = [[0.0] * cols for _ in range(rows)]
        peak_b = peak_c = 0.0
        for _ in range(60):
            self.app._bz_step()
            peak_b = max(peak_b, max(v for row in self.app.bz_b for v in row))
            peak_c = max(peak_c, max(v for row in self.app.bz_c for v in row))
        assert peak_b > 0.5 and peak_c > 0.5

    def test_noise_start_keeps_waves_going(self):
        """A noisy start must not settle to a uniform state or saturate."""
        random.seed(42)
        self.app._bz_init(3)  # Turbulent starts from random noise
        for _ in range(300):
            self.app._bz_step()
        cells = [v for row in self.app.bz_a for v in row]
        mean = sum(cells) / len(cells)
        spread = (sum((v - mean) ** 2 for v in cells) / len(cells)) ** 0.5
        assert spread > 0.03, "activator went uniform"
        assert 0.02 < mean < 0.9, "activator died out or saturated"

    def test_every_preset_stays_patterned_for_400_steps(self):
        """No preset may fade to a uniform grid within 400 steps."""
        for idx in range(len(BZ_PRESETS)):
            random.seed(7 + idx)
            self.app._bz_init(idx)
            for _ in range(400):
                self.app._bz_step()
            cells = [v for row in self.app.bz_a for v in row]
            mean = sum(cells) / len(cells)
            spread = (sum((v - mean) ** 2 for v in cells) / len(cells)) ** 0.5
            assert spread > 0.03, BZ_PRESETS[idx][0]

    def test_diffusion_spreads_activation(self):
        """A point excitation should diffuse to neighbors."""
        self.app._bz_init(0)
        # Clear grid and place single point activation
        rows, cols = self.app.bz_rows, self.app.bz_cols
        for r in range(rows):
            for c in range(cols):
                self.app.bz_a[r][c] = 0.0
                self.app.bz_b[r][c] = 0.0
                self.app.bz_c[r][c] = 0.0
        cr, cc = rows // 2, cols // 2
        self.app.bz_a[cr][cc] = 1.0
        self.app._bz_step()
        # Neighbors should have gained some activation from diffusion
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            assert self.app.bz_a[cr + dr][cc + dc] > 0.0, (
                "Diffusion should spread activation to neighbors")

    def test_wrapping_boundary(self):
        """BZ uses periodic (wrapping) boundary conditions."""
        self.app._bz_init(0)
        rows, cols = self.app.bz_rows, self.app.bz_cols
        # Clear and place activation at top-left corner
        for r in range(rows):
            for c in range(cols):
                self.app.bz_a[r][c] = 0.0
                self.app.bz_b[r][c] = 0.0
                self.app.bz_c[r][c] = 0.0
        self.app.bz_a[0][0] = 1.0
        self.app._bz_step()
        # Should wrap: bottom row and rightmost col should get diffusion
        assert self.app.bz_a[rows - 1][0] > 0.0, "Should wrap vertically"
        assert self.app.bz_a[0][cols - 1] > 0.0, "Should wrap horizontally"

    def test_all_presets_run_10_steps(self):
        """Every preset should survive 10 steps without values leaving [0,1]."""
        for idx in range(len(BZ_PRESETS)):
            random.seed(42)
            self.app._bz_init(idx)
            for _ in range(10):
                self.app._bz_step()
            rows, cols = self.app.bz_rows, self.app.bz_cols
            for r in range(rows):
                for c in range(cols):
                    assert 0.0 <= self.app.bz_a[r][c] <= 1.0
                    assert 0.0 <= self.app.bz_b[r][c] <= 1.0
                    assert 0.0 <= self.app.bz_c[r][c] <= 1.0

    # ── Grid dimensions ──────────────────────────────────────────────
    def test_grid_dimensions(self):
        """Grid dimensions match stored rows/cols."""
        self.app._bz_init(0)
        assert len(self.app.bz_a) == self.app.bz_rows
        assert len(self.app.bz_b) == self.app.bz_rows
        assert len(self.app.bz_c) == self.app.bz_rows
        for r in range(self.app.bz_rows):
            assert len(self.app.bz_a[r]) == self.app.bz_cols
            assert len(self.app.bz_b[r]) == self.app.bz_cols
            assert len(self.app.bz_c[r]) == self.app.bz_cols

    # ── Parameters stored correctly ──────────────────────────────────
    def test_parameters_stored(self):
        """Init stores correct alpha, beta, gamma, diffusion from preset."""
        for idx, (name, _, alpha, beta, gamma, diff, _) in enumerate(BZ_PRESETS):
            self.app._bz_init(idx)
            assert self.app.bz_alpha == alpha
            assert self.app.bz_beta == beta
            assert self.app.bz_gamma == gamma
            assert self.app.bz_diffusion == diff
            assert self.app.bz_preset_name == name

    # ── Quiescent state stability ────────────────────────────────────
    def test_zero_grid_stays_dark(self):
        """An all-zero grid gets only traces under the floor, no activation."""
        self.app._bz_init(0)
        rows, cols = self.app.bz_rows, self.app.bz_cols
        for r in range(rows):
            for c in range(cols):
                self.app.bz_a[r][c] = 0.0
                self.app.bz_b[r][c] = 0.0
                self.app.bz_c[r][c] = 0.0
        for _ in range(5):
            self.app._bz_step()
        for r in range(rows):
            for c in range(cols):
                assert self.app.bz_a[r][c] < BZ_FLOOR
                assert self.app.bz_b[r][c] < BZ_FLOOR
                assert self.app.bz_c[r][c] < BZ_FLOOR

    def test_diffusion_key_stops_at_quarter(self):
        """D is capped at 0.25, where the cell's own weight in its mean hits zero."""
        self.app._bz_init(0)
        for _ in range(30):
            self.app._handle_bz_key(ord("D"))
        assert self.app.bz_diffusion == 0.25

    def test_hint_bar_fits_80_columns(self):
        """Every key in the hint bar, q=exit included, fits a 24x80 terminal."""
        self.app._bz_init(0)
        self.app.message = ""
        lines = []
        self.app.stdscr.addstr = lambda y, x, s, *a: lines.append(s)
        self.app._draw_bz(24, 80)
        hint = [s for s in lines if "q=exit" in s][-1]
        assert len(hint) <= 79
        assert hint.rstrip().endswith("q=exit")
