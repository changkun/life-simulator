"""Test mode wiring: verify every MODE_REGISTRY entry is properly connected in app.py.

These tests scan the app.py source text to ensure each mode has:
  1. Init — `self.{attr} = False` in __init__
  2. Key dispatch — `self.{attr}` checked in the key dispatch chain
  3. Draw dispatch — `self.{attr}` checked in the _draw() method
  4. Menu wiring — for modes with menus: menu in _any_menu_open(), menu draw, menu key dispatch
  5. Menu handler sets mode flag — selecting a preset sets `self.{attr} = True`
"""
import inspect
import re

import pytest

from life.registry import MODE_REGISTRY


# ── Load app.py source once ──────────────────────────────────────────────────
def _load_app_source():
    import life.app as app_mod
    return inspect.getsource(app_mod)


APP_SOURCE = _load_app_source()

# Split source into sections for targeted checks
_init_match = re.search(r'def __init__\(self.*?\n(.*?)(?=\n    def )', APP_SOURCE, re.DOTALL)
INIT_SOURCE = _init_match.group(1) if _init_match else ""

_draw_match = re.search(r'def _draw\(self\):\n(.*?)(?=\n    def )', APP_SOURCE, re.DOTALL)
DRAW_SOURCE = _draw_match.group(1) if _draw_match else ""

_any_menu_match = re.search(r'def _any_menu_open\(self\).*?(?=\n    def )', APP_SOURCE, re.DOTALL)
ANY_MENU_SOURCE = _any_menu_match.group(0) if _any_menu_match else ""

# Key dispatch: the run() method's key handling section
_run_match = re.search(r'def run\(self\):\n(.*)', APP_SOURCE, re.DOTALL)
RUN_SOURCE = _run_match.group(1) if _run_match else ""


# ── Build test parameter list ────────────────────────────────────────────────
# Skip modes that don't follow the standard pattern
SKIP_ATTRS = {
    None,             # Game of Life (attr=None), Topology, Visual FX
    'cast_recording', # Special toggle, not a standard mode
}

SKIP_ENTER_NONE = {
    'tbranch_mode',   # enter=None, activated via scrubbing
}


def _standard_modes():
    """Yield (attr, entry) for modes that should follow standard wiring."""
    seen = set()
    for entry in MODE_REGISTRY:
        attr = entry.get('attr')
        if attr in SKIP_ATTRS:
            continue
        if attr in seen:
            continue
        seen.add(attr)
        if attr in SKIP_ENTER_NONE and entry.get('enter') is None:
            continue
        yield attr, entry


STANDARD_MODES = list(_standard_modes())
MODE_IDS = [attr for attr, _ in STANDARD_MODES]


# ── Detect which modes have menus ────────────────────────────────────────────
def _mode_has_menu(attr):
    """Check if a mode has a menu attribute (prefix_menu pattern)."""
    # Derive the prefix from the attr (e.g., 'wolfram_mode' -> 'wolfram')
    prefix = attr.replace('_mode', '')
    menu_attr = f'{prefix}_menu'
    # Check if this menu attr is referenced anywhere in the source
    return f'self.{menu_attr}' in APP_SOURCE


def _get_menu_attr(attr):
    prefix = attr.replace('_mode', '')
    return f'{prefix}_menu'


MODES_WITH_MENUS = [(attr, entry) for attr, entry in STANDARD_MODES if _mode_has_menu(attr)]
MENU_IDS = [attr for attr, _ in MODES_WITH_MENUS]


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestModeAttrInit:
    """Every mode's boolean flag must be initialized to False in __init__."""

    @pytest.mark.parametrize("attr", MODE_IDS, ids=MODE_IDS)
    def test_init_present(self, attr):
        # Look for either `self.attr = False` or `self.attr: bool = False`
        pattern = rf'self\.{re.escape(attr)}\s*[:=]'
        assert re.search(pattern, INIT_SOURCE), (
            f"self.{attr} not initialized in App.__init__"
        )


class TestModeKeyDispatch:
    """Every mode must be checked in the key dispatch chain in run()."""

    @pytest.mark.parametrize("attr", MODE_IDS, ids=MODE_IDS)
    def test_key_dispatch_present(self, attr):
        # Standard modes with special key handling patterns
        special_key_dispatch = {
            'compare_mode', 'race_mode', 'puzzle_mode',
            'heatmap_mode', 'pattern_search_mode', 'blueprint_mode',
            'iso_mode', 'hex_mode', 'mp_mode',
        }
        if attr in special_key_dispatch:
            # These modes integrate into the main GoL key handling
            assert f'self.{attr}' in RUN_SOURCE, (
                f"self.{attr} not found in run() at all"
            )
            return

        # Look for the standard pattern: `elif self.{attr}:` or `if self.{attr}`
        # in key dispatch
        pattern = rf'(?:elif|if)\s+self\.{re.escape(attr)}'
        assert re.search(pattern, RUN_SOURCE), (
            f"self.{attr} missing from key dispatch in run()"
        )


class TestModeDrawDispatch:
    """Every mode must be checked in the _draw() method."""

    @pytest.mark.parametrize("attr", MODE_IDS, ids=MODE_IDS)
    def test_draw_dispatch_present(self, attr):
        # Screensaver draws as an overlay, not in _draw()
        special_draw = {
            'compare_mode', 'race_mode', 'heatmap_mode',
            'pattern_search_mode', 'iso_mode', 'hex_mode',
            'mp_mode', 'screensaver_mode', 'puzzle_mode',
        }
        if attr in special_draw:
            # These modes draw via the main GoL drawing + overlays
            # or have special handling outside _draw()
            assert f'self.{attr}' in APP_SOURCE, (
                f"self.{attr} not found in source at all"
            )
            return

        pattern = rf'if self\.{re.escape(attr)}:'
        assert re.search(pattern, DRAW_SOURCE), (
            f"self.{attr} missing from _draw() dispatch"
        )


class TestMenuInAnyMenuOpen:
    """Modes with menus must list their menu attr in _any_menu_open()."""

    @pytest.mark.parametrize("attr", MENU_IDS, ids=MENU_IDS)
    def test_menu_in_any_menu_open(self, attr):
        menu_attr = _get_menu_attr(attr)
        assert f"'{menu_attr}'" in ANY_MENU_SOURCE, (
            f"'{menu_attr}' missing from _any_menu_open() list"
        )


class TestModeMethodsRegistered:
    """Enter and exit functions must exist on the App class."""

    @pytest.mark.parametrize("attr,entry", STANDARD_MODES, ids=MODE_IDS)
    def test_enter_exit_exist(self, attr, entry):
        enter_fn = entry.get('enter')
        exit_fn = entry.get('exit')

        if enter_fn:
            assert f'def {enter_fn}(' in APP_SOURCE or f'App.{enter_fn}' in APP_SOURCE or \
                   hasattr(__import__('life.app', fromlist=['App']).App, enter_fn), (
                f"Enter function {enter_fn} not found for {attr}"
            )

        if exit_fn:
            assert f'def {exit_fn}(' in APP_SOURCE or f'App.{exit_fn}' in APP_SOURCE or \
                   hasattr(__import__('life.app', fromlist=['App']).App, exit_fn), (
                f"Exit function {exit_fn} not found for {attr}"
            )


class TestMenuHandlerSetsMode:
    """Selecting a preset from the menu must eventually set self.{attr} = True.

    This checks that the mode's init function or menu handler contains
    `self.{attr} = True`.
    """

    # Modes whose menu handler + init work differently
    SKIP = {
        'compare_mode',   # compare enters via different flow
        'race_mode',      # race has special rule selection
        'puzzle_mode',    # puzzle has special phase handling
        'evo_mode',       # evolution has special phase handling
        'mp_mode',        # multiplayer has lobby phase
        'screensaver_mode',  # screensaver delegates to sub-modes
        'heatmap_mode',   # toggle, no menu
        'pattern_search_mode',  # toggle
        'iso_mode',       # toggle
        'hex_mode',       # toggle
        'blueprint_mode', # toggle
    }

    @pytest.mark.parametrize("attr,entry", MODES_WITH_MENUS, ids=MENU_IDS)
    def test_menu_sets_mode_flag(self, attr, entry):
        if attr in self.SKIP:
            pytest.skip(f"{attr} has non-standard menu flow")

        # The mode flag must be set to True somewhere in the mode's module
        # Search all mode source files for `self.{attr} = True`
        enter_fn = entry.get('enter', '')
        if not enter_fn:
            pytest.skip("No enter function")

        # Find the module that defines this enter function
        import life.app
        app_cls = life.app.App
        if hasattr(app_cls, enter_fn):
            fn = getattr(app_cls, enter_fn)
            # Get the source module
            mod = inspect.getmodule(fn)
            if mod:
                mod_source = inspect.getsource(mod)
                assert f'self.{attr} = True' in mod_source, (
                    f"self.{attr} = True not found in module defining {enter_fn}"
                )
