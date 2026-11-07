"""Every key the mode registry lists must open its entry from Game of Life.

The registry key is what the mode browser, the help screen and the docs
show. Entries reached only through the mode browser use the key "—".
"""
import pytest

from life.registry import MODE_DISPATCH, MODE_REGISTRY
from tests.real_app import patch_curses, run_app

# Entries whose key opens a menu or overlay not named after the entry's attr.
_OPENS = {
    "Compare Rules": "compare_rule_menu",
    "Multi-Rule Race": "race_rule_menu",
    "Puzzle / Challenge": "puzzle_menu",
    "Scripting & Choreography": "script_menu",
    "Emergent Computation Detector": "compdet_active",
}


def _code(key):
    if key.startswith("Ctrl+") and len(key) == 6:
        return ord(key[-1].upper()) - 64
    if len(key) == 1 and key.isascii():
        return ord(key)
    raise ValueError(f"registry key {key!r} cannot be typed")


def _keyed_entries():
    """Entries with a key that opens them from Game of Life.

    A note in parentheses, as in "Ctrl+F (scrub)", marks a key that works only
    in a particular state, so it is left out.
    """
    return [e for e in MODE_REGISTRY if e["key"] != "—" and "(" not in e["key"]]


@pytest.fixture(autouse=True)
def _fake_curses(monkeypatch):
    patch_curses(monkeypatch)


def test_registry_keys_can_be_typed():
    for entry in _keyed_entries():
        _code(entry["key"])


def test_registry_keys_are_unique():
    keys = [e["key"] for e in _keyed_entries()]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("entry", _keyed_entries(), ids=lambda e: e["name"])
def test_registry_key_opens_its_entry(entry):
    app = run_app([_code(entry["key"]), -1])
    flags = [_OPENS.get(entry["name"]), entry["attr"]]
    md = next((m for m in MODE_DISPATCH if m["attr"] == entry["attr"]), None)
    if md:
        flags.append(md["menu_attr"])
    assert any(getattr(app, f, False) for f in flags if f), (
        f"{entry['key']} does not open {entry['name']}")


@pytest.mark.parametrize("entry", [e for e in MODE_REGISTRY if e["key"] == "—" and e["attr"]],
                         ids=lambda e: e["name"])
def test_browser_only_entries_can_be_entered(entry):
    assert entry["enter"], f"{entry['name']} has no key and no enter function"
