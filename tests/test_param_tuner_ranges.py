"""Static sanity checks for the parameter tuner table.

Checks every TUNABLE_PARAMS entry names an attribute the mode really reads
(outside its init helper), and that its descriptor is well formed.  Whether
the range covers every preset value is verified by an ad-hoc headless scan,
not here, because that needs full App construction.
"""
import ast
import pathlib

import pytest

from life.modes.param_tuner import TUNABLE_PARAMS
from life.registry import MODE_DISPATCH

MODES_DIR = pathlib.Path(__file__).resolve().parent.parent / "life" / "modes"
PREFIXES = {md["prefix"] for md in MODE_DISPATCH}


def _loaded_outside_init() -> dict[str, set[str]]:
    """Map attribute name -> files that read it in a non-init function."""
    out: dict[str, set[str]] = {}
    for path in MODES_DIR.glob("*.py"):
        if path.name == "param_tuner.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if "init" in fn.name:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                    out.setdefault(node.attr, set()).add(path.name)
    return out


_READS = _loaded_outside_init()

ENTRIES = [(prefix, p) for prefix, params in TUNABLE_PARAMS.items() for p in params]


def test_prefixes_are_known():
    assert set(TUNABLE_PARAMS) <= PREFIXES, set(TUNABLE_PARAMS) - PREFIXES


@pytest.mark.parametrize("prefix,p", ENTRIES, ids=[p["attr"] for _, p in ENTRIES])
def test_attr_is_read_by_mode(prefix, p):
    attr = p["attr"]
    assert attr.startswith(prefix + "_"), f"{attr} does not belong to mode {prefix}"
    assert attr in _READS, f"{attr} is never read outside an init helper (unknown or init-only)"


@pytest.mark.parametrize("prefix,p", ENTRIES, ids=[p["attr"] for _, p in ENTRIES])
def test_descriptor_well_formed(prefix, p):
    assert p["min"] < p["max"]
    assert 0 < p["step"] < (p["max"] - p["min"])
    if p["fmt"] == "d":
        assert all(isinstance(p[k], int) for k in ("min", "max", "step"))
    else:
        format(1.0, p["fmt"])  # raises on a bad format spec
