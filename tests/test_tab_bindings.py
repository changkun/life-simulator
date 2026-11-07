"""Tab is shared between the global minimap toggle and screens that bind it.

App._tab_claimed() gives Tab to the dashboard, the computation detector and
every mode or menu listed in App._TAB_SCREENS; everywhere else Tab toggles the
minimap. That list is maintained by hand, so check it against the key
handlers: a handler that binds Tab must be listed (or its Tab never fires),
and a listed screen must actually bind Tab (or it loses the minimap toggle).
"""
import inspect
import re

from life.app import App
from life.registry import MODE_DISPATCH

# key == 9, key in (..., 9, ...), ord("\t") / ord('\t'); not ord("9").
_TAB_RE = re.compile(
    r"""key\s*(?:==|in)\s*[^:\n]*?(?:(?<!['"])\b9\b(?!['"])|ord\(\s*['"]\\t['"]\s*\))"""
)


def _binds_tab(method_name):
    fn = getattr(App, method_name, None)
    if fn is None:
        return False
    return bool(_TAB_RE.search(inspect.getsource(fn)))


def _screens_binding_tab():
    screens = set()
    for md in MODE_DISPATCH:
        if _binds_tab(md["keys"]):
            screens.add(md["attr"])
        if _binds_tab(md["menu_keys"]):
            screens.add(md["menu_attr"])
    return screens


def test_regex_matches_tab_spellings_only():
    assert _TAB_RE.search("    if key == 9:  # Tab")
    assert _TAB_RE.search("    elif key == ord('\\t'):")
    assert _TAB_RE.search('    if key == ord("\\t") or key == ord("e"):')
    assert _TAB_RE.search("    if key in (9, curses.KEY_BTAB):")
    assert not _TAB_RE.search('    if key == ord("9"):')
    assert not _TAB_RE.search("    if key == 90:")


def test_every_tab_binding_is_claimed():
    missing = _screens_binding_tab() - set(App._TAB_SCREENS)
    assert not missing, (
        f"{sorted(missing)} bind Tab but are not in App._TAB_SCREENS, "
        "so the minimap toggle swallows their Tab")


def test_every_claimed_screen_binds_tab():
    stale = set(App._TAB_SCREENS) - _screens_binding_tab()
    assert not stale, (
        f"{sorted(stale)} are in App._TAB_SCREENS but no longer bind Tab, "
        "so they lose the minimap toggle for nothing")
