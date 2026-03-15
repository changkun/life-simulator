"""Simulation Genome Sharing System — encode/decode simulation configs as compact seed strings.

A horizontal feature that works across all modes. Press 'g' to export the current
simulation's configuration as a shareable code (e.g., RD-x7Kp2mQ9), or paste a code
to instantly reproduce that exact simulation setup.
"""
import base64
import copy
import hashlib
import json
import zlib

from life.registry import MODE_REGISTRY

# ── Attributes to skip when capturing genome ────────────────────────────────

_SKIP_SUFFIXES = {
    "_mode", "_menu", "_menu_sel", "_menu_phase", "_running", "_generation",
    "_rows", "_cols", "_agents", "_particles", "_cells", "_grid", "_state",
    "_field", "_data", "_trail", "_trails", "_history", "_buf", "_buffer",
    "_thread", "_stop", "_lock", "_prev", "_cache", "_dirty", "_canvas",
    "_frame", "_frames", "_snapshot", "_snapshots", "_overlay",
}

# Attrs that are pure state (not config) and should never be in a genome
_SKIP_EXACT = {
    "running", "generation", "rows", "cols", "menu", "menu_sel", "menu_phase",
}

# Mode prefix → short human-readable abbreviation for the genome code
_MODE_ABBREVS = {
    "gol": "GOL", "wolfram": "WLF", "ant": "ANT", "hex": "HEX",
    "ww": "WW", "cyclic": "CYC", "hodge": "HDG", "lenia": "LEN",
    "turmite": "TRM", "gol3d": "G3D",
    "sand": "SND", "boids": "BOI", "plife": "PLF", "physarum": "PHY",
    "aco": "ACO", "nbody": "NBD", "dla": "DLA",
    "wave": "WAV", "ising": "ISG", "kuramoto": "KUR", "qwalk": "QWK",
    "lightning": "LTN", "chladni": "CHL", "magfield": "MAG",
    "fdtd": "FDT", "dpend": "DPN", "cloth": "CLO",
    "fluid": "FLD", "ns": "NS", "rbc": "RBC", "sph": "SPH", "mhd": "MHD",
    "rd": "RD", "bz": "BZ", "chemo": "CHM", "fire": "FIR",
    "sir": "SIR", "lv": "LV", "snn": "SNN", "cpm": "CPM",
    "spd": "SPD", "schelling": "SCH", "rps": "RPS",
    "sandpile": "SPL", "attractor": "ATR", "fractal": "FRC",
    "snowflake": "SNW", "erosion": "ERO", "ifs": "IFS", "lsystem": "LSY",
    "wfc": "WFC", "maze": "MAZ", "voronoi": "VOR", "terrain": "TER",
    "flythrough": "FLY", "raymarch": "RAY", "shadertoy": "SHD",
    "musvis": "MVS", "snowfall": "SNF", "matrix": "MTX",
    "traffic": "TRF", "galaxy": "GAL", "smokefire": "SMK",
    "fireworks": "FRW", "alife": "ALF", "doomrc": "DRC",
    "tectonic": "TEC", "weather": "WTH", "ocean": "OCN",
    "volcano": "VLC", "blackhole": "BLH", "orrery": "ORR",
    "aurora": "AUR", "pwave": "PWV", "tornado": "TOR",
    "sortvis": "SRT", "dnahelix": "DNA", "fourier": "FFT",
    "fluidrope": "FRP", "lissajous": "LIS", "mazesolver": "MSV",
    "antfarm": "AFM", "kaleido": "KAL", "aquarium": "AQU",
    "collider": "COL",
    # Meta modes
    "compare": "CMP", "race": "RAC", "puzzle": "PZL", "evo": "EVO",
    "mashup": "MSH", "br": "BR", "obs": "OBS", "cinem": "CIN",
    "screensaver": "SSV", "pexplorer": "PEX", "ep": "EP", "re": "RE",
}

# Reverse lookup: abbreviation → prefix
_ABBREV_TO_PREFIX = {v: k for k, v in _MODE_ABBREVS.items()}

# Excluded modes (meta-modes that don't have simple reproducible configs)
_EXCLUDED_ATTRS = {
    "compare_mode", "race_mode", "obs_mode", "cinem_mode",
    "screensaver_mode", "pexplorer_mode",
}


def _get_active_mode_prefix(self):
    """Return (prefix, mode_attr) for the currently active mode, or (None, None)."""
    for entry in MODE_REGISTRY:
        attr = entry.get("attr")
        if not attr:
            continue
        if attr in _EXCLUDED_ATTRS:
            continue
        if getattr(self, attr, False):
            prefix = attr.rsplit("_mode", 1)[0]
            return prefix, attr
    return None, None


def _should_include_attr(prefix, attr_name):
    """Decide whether an attribute should be included in the genome."""
    if not attr_name.startswith(prefix + "_"):
        return False

    suffix = attr_name[len(prefix):]  # includes leading _

    # Skip known state-only suffixes
    if suffix in _SKIP_SUFFIXES:
        return False

    bare = suffix.lstrip("_")
    if bare in _SKIP_EXACT:
        return False

    # Skip private/internal
    if bare.startswith("_"):
        return False

    return True


def _capture_genome(self):
    """Capture the current simulation's configuration as a dict.

    Returns (prefix, config_dict) or (None, None) if no mode is active.
    """
    prefix, mode_attr = _get_active_mode_prefix(self)

    if prefix is None:
        # Check if base GoL mode is active (no special mode)
        config = {
            "_mode": "gol",
            "speed_idx": self.speed_idx,
            "rule_b": sorted(self.grid.birth),
            "rule_s": sorted(self.grid.survival),
        }
        # Capture initial state fingerprint (hash of live cell positions)
        alive = []
        for r in range(self.grid.rows):
            for c in range(self.grid.cols):
                if self.grid.cells[r][c] > 0:
                    alive.append((r, c))
        if alive:
            state_hash = hashlib.md5(
                json.dumps(alive, separators=(",", ":")).encode()
            ).hexdigest()[:8]
            config["state_fp"] = state_hash
            config["grid_size"] = [self.grid.rows, self.grid.cols]
            # Store cell positions if small enough
            if len(alive) <= 500:
                config["cells"] = alive
        return "gol", config

    # Capture mode-specific parameters
    config = {"_mode": prefix, "speed_idx": self.speed_idx}

    # Scan all attributes with this prefix
    attr_prefix = prefix + "_"
    for attr_name in sorted(vars(self)):
        if not _should_include_attr(prefix, attr_name):
            continue

        val = getattr(self, attr_name)

        # Only include serializable config values
        if isinstance(val, (int, float)):
            key = attr_name[len(attr_prefix):]
            config[key] = val
        elif isinstance(val, str) and len(val) < 200:
            key = attr_name[len(attr_prefix):]
            config[key] = val
        elif isinstance(val, bool):
            key = attr_name[len(attr_prefix):]
            config[key] = val
        elif isinstance(val, (list, tuple)):
            # Only include small lists of primitives (like rule sets, seeds)
            if len(val) <= 50 and all(isinstance(x, (int, float, str, bool)) for x in val):
                key = attr_name[len(attr_prefix):]
                config[key] = list(val)

    # For GoL-based modes, also capture the rule string
    if hasattr(self, 'grid') and self.grid:
        config["rule_b"] = sorted(self.grid.birth)
        config["rule_s"] = sorted(self.grid.survival)

    return prefix, config


def _encode_genome(prefix, config):
    """Encode a config dict into a compact shareable string.

    Format: {ABBREV}-{base64url_payload}
    """
    abbrev = _MODE_ABBREVS.get(prefix, prefix.upper()[:3])

    # Serialize, compress, encode
    json_bytes = json.dumps(config, separators=(",", ":"), sort_keys=True).encode("utf-8")
    compressed = zlib.compress(json_bytes, 9)

    # Use base64url (no padding) for URL-safe sharing
    b64 = base64.urlsafe_b64encode(compressed).rstrip(b"=").decode("ascii")

    return f"{abbrev}-{b64}"


def _decode_genome(code):
    """Decode a genome string back into (prefix, config_dict).

    Returns (prefix, config) or (None, None) on error.
    """
    code = code.strip()
    if "-" not in code:
        return None, None

    abbrev, b64 = code.split("-", 1)
    abbrev = abbrev.upper()

    prefix = _ABBREV_TO_PREFIX.get(abbrev)
    if prefix is None:
        # Try treating abbrev as a raw prefix
        prefix = abbrev.lower()

    # Restore base64 padding
    padding = 4 - (len(b64) % 4)
    if padding < 4:
        b64 += "=" * padding

    try:
        compressed = base64.urlsafe_b64decode(b64)
        json_bytes = zlib.decompress(compressed)
        config = json.loads(json_bytes)
    except Exception:
        return None, None

    return prefix, config


def _apply_genome(self, prefix, config):
    """Apply a decoded genome config to set up the simulation.

    Returns True on success, error string on failure.
    """
    mode_prefix = config.get("_mode", prefix)

    # Find the matching mode entry
    target_attr = f"{mode_prefix}_mode"
    target_entry = None
    for entry in MODE_REGISTRY:
        if entry.get("attr") == target_attr:
            target_entry = entry
            break

    # Special case: base GoL
    if mode_prefix == "gol" and target_entry is None:
        # Apply GoL config
        self._exit_current_modes()
        if "rule_b" in config:
            self.grid.birth = set(config["rule_b"])
        if "rule_s" in config:
            self.grid.survival = set(config["rule_s"])
        if "speed_idx" in config:
            self.speed_idx = max(0, min(len(_get_speeds()) - 1, config["speed_idx"]))
        if "cells" in config and "grid_size" in config:
            gr, gc = config["grid_size"]
            if gr == self.grid.rows and gc == self.grid.cols:
                self.grid.clear()
                for r, c in config["cells"]:
                    if 0 <= r < self.grid.rows and 0 <= c < self.grid.cols:
                        self.grid.set_alive(r, c)
            else:
                # Different grid size — place cells centered
                self.grid.clear()
                off_r = (self.grid.rows - gr) // 2
                off_c = (self.grid.cols - gc) // 2
                for r, c in config["cells"]:
                    nr, nc = r + off_r, c + off_c
                    if 0 <= nr < self.grid.rows and 0 <= nc < self.grid.cols:
                        self.grid.set_alive(nr, nc)
        self._flash(f"Genome loaded: Game of Life")
        return True

    if target_entry is None:
        return f"Unknown mode: {mode_prefix}"

    # Exit current mode and enter target mode
    self._exit_current_modes()

    # Enter the target mode
    enter_fn = getattr(self, target_entry["enter"], None)
    if enter_fn:
        enter_fn()

    # Apply speed
    if "speed_idx" in config:
        self.speed_idx = max(0, min(len(_get_speeds()) - 1, config["speed_idx"]))

    # Apply all config parameters
    attr_prefix = mode_prefix + "_"
    for key, val in config.items():
        if key.startswith("_") or key in ("speed_idx", "rule_b", "rule_s"):
            continue
        attr_name = attr_prefix + key
        if hasattr(self, attr_name):
            try:
                setattr(self, attr_name, val)
            except (TypeError, ValueError):
                pass

    # Apply rule if present
    if hasattr(self, 'grid') and self.grid:
        if "rule_b" in config:
            self.grid.birth = set(config["rule_b"])
        if "rule_s" in config:
            self.grid.survival = set(config["rule_s"])

    # Close any menu that the enter function opened
    menu_attr = f"{mode_prefix}_menu"
    if hasattr(self, menu_attr):
        setattr(self, menu_attr, False)

    mode_name = target_entry.get("name", mode_prefix)
    self._flash(f"Genome loaded: {mode_name}")
    return True


def _get_speeds():
    """Import and return SPEEDS constant."""
    from life.constants import SPEEDS
    return SPEEDS


# ── Key handler ──────────────────────────────────────────────────────────────

def _genome_handle_key(self, key):
    """Handle genome sharing key (g). Returns True if handled."""
    import curses

    if key != ord("g"):
        return False

    # Don't interfere with mode-specific key handlers
    # Only activate when no menu is open
    if self._any_menu_open():
        return False

    # Show export/import prompt
    choice = self._prompt_text("Genome: [E]xport code / [I]mport code")
    if not choice:
        return True

    ch = choice.strip().upper()

    if ch.startswith("E") or ch == "":
        # Export current simulation genome
        prefix, config = _capture_genome(self)
        if config is None:
            self._flash("No active simulation to export")
            return True

        code = _encode_genome(prefix, config)

        # Show the code and let user copy it
        self._prompt_text(f"Genome code (copy it): {code}")
        self._flash(f"Genome: {code}")
        return True

    elif ch.startswith("I"):
        # Import genome code
        code = self._prompt_text("Paste genome code")
        if not code:
            return True

        prefix, config = _decode_genome(code)
        if config is None:
            self._flash("Invalid genome code")
            return True

        result = _apply_genome(self, prefix, config)
        if result is not True:
            self._flash(f"Genome error: {result}")
        return True

    return True


# ── Registration ─────────────────────────────────────────────────────────────

def register(App):
    """Register genome sharing methods on the App class."""
    App._genome_handle_key = _genome_handle_key
    App._genome_capture = _capture_genome
    App._genome_encode = _encode_genome
    App._genome_decode = _decode_genome
    App._genome_apply = _apply_genome
