"""Tests for the Emergent Computation Detector overlay."""
import random
from types import SimpleNamespace

from life.modes import computation_detector as cd


def _app():
    app = SimpleNamespace()
    cd._compdet_init(app)
    app.compdet_size = 8
    app._get_minimap_data = lambda: (16, 16, lambda r, c: float(random.random() < 0.5))
    app._flash = lambda msg: None
    return app


def test_compute_keeps_refreshing_without_post_processing():
    """The analysis must advance even when pp_frame_count never changes."""
    random.seed(1)
    app = _app()
    for _ in range(40):
        cd._compdet_compute(app)
    assert len(app.compdet_history) == app.compdet_max_history
    assert app.compdet_bits_processed > 0


def test_compute_is_throttled():
    random.seed(1)
    app = _app()
    for _ in range(3):
        cd._compdet_compute(app)
    assert app.compdet_te_map is not None
    n = len(app.compdet_history)
    for _ in range(app.compdet_compute_interval - 1):
        cd._compdet_compute(app)
    assert len(app.compdet_history) == n
    cd._compdet_compute(app)
    assert len(app.compdet_history) == n + 1
