"""Tests for life.modes.active_matter — Active Matter."""
import math

from tests.conftest import make_mock_app
from life.modes.active_matter import register, ACTIVE_MATTER_PRESETS


def _make_app():
    app = make_mock_app()
    register(type(app))
    return app


def test_mips_slows_particles_in_crowds():
    """The MIPS preset has no alignment, yet crowded particles must slow down."""
    app = _make_app()
    idx = next(i for i, p in enumerate(ACTIVE_MATTER_PRESETS) if p[2] == "mips")
    app._active_matter_init(idx)
    app.active_matter_noise = 0.0
    app.active_matter_tumble = 1e-9  # keep the slowdown on, tumbling off
    app.active_matter_repel_w = 0.0
    # Two particles close together, heading the same way.
    app.active_matter_particles = [
        [5.0, 5.0, 0.0, 0.0, 0.0, 1.0],
        [5.0, 5.8, 0.0, 0.0, 0.0, 1.0],
    ]
    app._active_matter_step()
    speed = math.hypot(app.active_matter_particles[0][3],
                       app.active_matter_particles[0][4])
    assert speed < app.active_matter_v0 * 0.9
