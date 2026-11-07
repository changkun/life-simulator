"""Tests for the dashboard's live preview (life.dashboard._preview_static)."""
import pytest

from life.dashboard import _preview_static
from life.registry import MODE_REGISTRY


@pytest.mark.parametrize("name", [m["name"] for m in MODE_REGISTRY])
def test_preview_draws_in_small_boxes(name):
    """A long description can push the preview box down to a row or two.

    Every preview must still draw there without raising; the dashboard
    clips points that fall outside the box.
    """
    for h in (1, 2, 3, 5):
        for w in (3, 4, 8):
            for tick in (0, 7):
                _preview_static(name, tick, h, w)
