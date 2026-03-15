"""Utility functions: pattern recognition, RLE parsing, GIF encoding, etc."""
import hashlib
import json
import math
import os
import struct

from life.constants import SAVE_DIR, BLUEPRINT_FILE, SPARKLINE_CHARS
from life.patterns import PATTERNS

def _load_blueprints() -> dict:
    """Load user-saved blueprint patterns from disk."""
    if not os.path.isfile(BLUEPRINT_FILE):
        return {}
    try:
        with open(BLUEPRINT_FILE, "r") as f:
            data = json.load(f)
        blueprints = {}
        for name, entry in data.items():
            blueprints[name] = {
                "description": entry.get("description", "Custom blueprint"),
                "cells": [tuple(c) for c in entry["cells"]],
            }
        return blueprints
    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        return {}


def _save_blueprints(blueprints: dict):
    """Save user blueprint patterns to disk."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    data = {}
    for name, entry in blueprints.items():
        data[name] = {
            "description": entry["description"],
            "cells": list(entry["cells"]),
        }
    with open(BLUEPRINT_FILE, "w") as f:
        json.dump(data, f)



# Pattern recognition is initialized lazily after PATTERNS is available
# ── Pattern recognition library ─────────────────────────────────────────────

# Canonical patterns stored as frozensets of (row, col) tuples, normalised to
# top-left origin.  For each pattern we pre-compute all distinct orientations
# (rotations × reflections, up to 8) so recognition is orientation-agnostic.


def _normalise(cells):
    """Shift a set of (r,c) tuples so the minimum row and column are 0."""
    if not cells:
        return frozenset()
    min_r = min(r for r, c in cells)
    min_c = min(c for r, c in cells)
    return frozenset((r - min_r, c - min_c) for r, c in cells)


def _orientations(cells):
    """Return all distinct orientations (rotations + reflections) of a pattern."""
    fs = _normalise(cells)
    seen = set()
    results = []
    cur = set(fs)
    for _ in range(4):
        for reflect in (False, True):
            if reflect:
                oriented = frozenset((-r, c) for r, c in cur)
            else:
                oriented = frozenset(cur)
            normed = _normalise(oriented)
            if normed not in seen:
                seen.add(normed)
                results.append(normed)
        # Rotate 90° clockwise: (r, c) -> (c, -r)
        cur = {(c, -r) for r, c in cur}
    return results


def _build_recognition_db():
    """Build the pattern recognition database from PATTERNS.

    Returns a list of (name, category, width, height, orientations) tuples.
    Only includes small/medium patterns suitable for real-time scanning
    (skips patterns larger than 15 cells).
    """
    # Categories for display
    categories = {
        "block": "Still life",
        "beehive": "Still life",
        "blinker": "Oscillator",
        "toad": "Oscillator",
        "beacon": "Oscillator",
        "glider": "Spaceship",
        "lwss": "Spaceship",
    }
    # Additional well-known small patterns not in the PATTERNS dict
    extra_patterns = {
        "loaf": {
            "cells": [(0, 1), (0, 2), (1, 0), (1, 3), (2, 1), (2, 3), (3, 2)],
            "category": "Still life",
        },
        "boat": {
            "cells": [(0, 0), (0, 1), (1, 0), (1, 2), (2, 1)],
            "category": "Still life",
        },
        "tub": {
            "cells": [(0, 1), (1, 0), (1, 2), (2, 1)],
            "category": "Still life",
        },
        "ship": {
            "cells": [(0, 0), (0, 1), (1, 0), (1, 2), (2, 1), (2, 2)],
            "category": "Still life",
        },
        "pond": {
            "cells": [(0, 1), (0, 2), (1, 0), (1, 3), (2, 0), (2, 3), (3, 1), (3, 2)],
            "category": "Still life",
        },
    }

    db = []
    for name, pdata in PATTERNS.items():
        cells = pdata["cells"]
        if len(cells) > 15:
            continue
        cat = categories.get(name, "Pattern")
        orients = _orientations(cells)
        h = max(r for r, c in cells) + 1
        w = max(c for r, c in cells) + 1
        db.append((name, cat, w, h, orients))
    for name, info in extra_patterns.items():
        cells = info["cells"]
        cat = info["category"]
        orients = _orientations(cells)
        h = max(r for r, c in cells) + 1
        w = max(c for r, c in cells) + 1
        db.append((name, cat, w, h, orients))
    return db


# Deferred init: built once on first use (after PATTERNS is defined)
_RECOGNITION_DB = None


def _get_recognition_db():
    global _RECOGNITION_DB
    if _RECOGNITION_DB is None:
        _RECOGNITION_DB = _build_recognition_db()
    return _RECOGNITION_DB


def scan_patterns(grid):
    """Scan the grid and return a list of detected patterns.

    Each result is a dict: {name, category, r, c, w, h, cells}
    where (r, c) is the top-left corner and cells is the set of (gr, gc)
    absolute grid positions belonging to the match.
    """
    db = _get_recognition_db()
    rows, cols = grid.rows, grid.cols

    # Build a set of all alive positions for fast lookup
    alive = set()
    for r in range(rows):
        for c in range(cols):
            if grid.cells[r][c] > 0:
                alive.add((r, c))

    if not alive:
        return []

    # For each alive cell, try to match each pattern orientation starting at that cell
    # as the top-left corner of the pattern's bounding box.
    found = []
    claimed = set()  # cells already claimed by a detected pattern

    # Sort DB so larger patterns match first (avoids sub-pattern conflicts)
    sorted_db = sorted(db, key=lambda x: max(len(o) for o in x[4]), reverse=True)

    for name, cat, pw, ph, orients in sorted_db:
        for orient in orients:
            oh = max(r for r, c in orient) + 1
            ow = max(c for r, c in orient) + 1
            for ar, ac in alive:
                if (ar, ac) in claimed:
                    continue
                # Check if (ar, ac) could be part of this orientation
                # Try it as the min-row, min-col anchor
                match_cells = set()
                ok = True
                for pr, pc in orient:
                    gr = (ar + pr) % rows
                    gc = (ac + pc) % cols
                    if (gr, gc) not in alive:
                        ok = False
                        break
                    match_cells.add((gr, gc))
                if not ok:
                    continue
                # Verify no extra alive cells in the bounding box
                # (otherwise we'd match subsets of larger structures)
                extra = False
                for dr in range(oh):
                    for dc in range(ow):
                        gr = (ar + dr) % rows
                        gc = (ac + dc) % cols
                        if (gr, gc) in alive and (gr, gc) not in match_cells:
                            extra = True
                            break
                    if extra:
                        break
                if extra:
                    continue
                # Check that none of these cells are already claimed
                if match_cells & claimed:
                    continue
                claimed |= match_cells
                found.append({
                    "name": name,
                    "category": cat,
                    "r": ar,
                    "c": ac,
                    "w": ow,
                    "h": oh,
                    "cells": match_cells,
                })

    return found


# ── RLE parser ──────────────────────────────────────────────────────────────


def parse_rle(text: str) -> dict:
    """Parse an RLE (Run Length Encoded) pattern string.

    Returns a dict with keys: 'name', 'comments', 'cells' (list of (r,c) tuples),
    'rule' (str or None), 'width', 'height'.
    """
    name = ""
    comments = []
    rule = None
    header_found = False
    pattern_data = ""

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            # Metadata comments
            if line.startswith("#N"):
                name = line[2:].strip()
            elif line.startswith("#C") or line.startswith("#c"):
                comments.append(line[2:].strip())
            elif line.startswith("#O"):
                comments.append(f"Author: {line[2:].strip()}")
            # #r, #P, etc. are ignored
            continue
        if not header_found:
            # Parse header line: x = M, y = N [, rule = ...]
            if line.startswith("x"):
                header_found = True
                # Extract x, y, and optional rule
                parts = {}
                for segment in line.split(","):
                    segment = segment.strip()
                    if "=" in segment:
                        k, v = segment.split("=", 1)
                        parts[k.strip().lower()] = v.strip()
                # Rule can appear in various forms
                if "rule" in parts:
                    rule_val = parts["rule"].strip()
                    # Convert common rule formats: e.g. "B3/S23", "23/3" (S/B), "b3/s23"
                    rule_val_upper = rule_val.upper()
                    if rule_val_upper.startswith("B"):
                        rule = rule_val_upper
                    elif "/" in rule_val:
                        # Legacy format: S/B (survival/birth)
                        s_part, b_part = rule_val.split("/", 1)
                        if s_part.isdigit() or s_part == "":
                            rule = f"B{b_part}/S{s_part}"
                continue
        # Pattern data lines (accumulate until '!')
        pattern_data += line
        if "!" in line:
            break

    # Strip everything after '!'
    if "!" in pattern_data:
        pattern_data = pattern_data[: pattern_data.index("!")]

    # Decode RLE pattern data
    cells = []
    row = 0
    col = 0
    i = 0
    while i < len(pattern_data):
        ch = pattern_data[i]
        if ch.isdigit():
            # Read full run count
            j = i
            while j < len(pattern_data) and pattern_data[j].isdigit():
                j += 1
            count = int(pattern_data[i:j])
            i = j
            if i >= len(pattern_data):
                break
            ch = pattern_data[i]
            i += 1
        else:
            count = 1
            i += 1

        if ch == "b" or ch == ".":
            col += count
        elif ch == "o" or ch == "A":
            for _ in range(count):
                cells.append((row, col))
                col += 1
        elif ch == "$":
            row += count
            col = 0

    # Compute bounding box
    if cells:
        max_r = max(r for r, c in cells)
        max_c = max(c for r, c in cells)
    else:
        max_r = max_c = 0

    return {
        "name": name,
        "comments": comments,
        "cells": cells,
        "rule": rule,
        "width": max_c + 1,
        "height": max_r + 1,
    }


def _gif_age_index(age: int) -> int:
    """Map cell age to palette index (mirrors color_for_age tiers)."""
    if age <= 0:
        return 0
    if age <= 1:
        return 1
    if age <= 3:
        return 2
    if age <= 8:
        return 3
    if age <= 20:
        return 4
    return 5


def _lzw_compress(pixels: list[int], min_code_size: int) -> bytes:
    """LZW compression for GIF image data."""
    clear_code = 1 << min_code_size
    eoi_code = clear_code + 1

    code_table: dict[tuple, int] = {}
    for i in range(clear_code):
        code_table[(i,)] = i

    next_code = eoi_code + 1
    code_size = min_code_size + 1
    max_code = (1 << code_size)

    # Bit packing
    bit_buffer = 0
    bits_in_buffer = 0
    output = bytearray()

    def emit(code: int):
        nonlocal bit_buffer, bits_in_buffer
        bit_buffer |= code << bits_in_buffer
        bits_in_buffer += code_size
        while bits_in_buffer >= 8:
            output.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bits_in_buffer -= 8

    emit(clear_code)
    buffer = (pixels[0],)

    for px in pixels[1:]:
        buffer_plus = buffer + (px,)
        if buffer_plus in code_table:
            buffer = buffer_plus
        else:
            emit(code_table[buffer])
            if next_code < 4096:
                code_table[buffer_plus] = next_code
                next_code += 1
                if next_code > max_code and code_size < 12:
                    code_size += 1
                    max_code = 1 << code_size
            else:
                # Table full, reset
                emit(clear_code)
                code_table = {}
                for i in range(clear_code):
                    code_table[(i,)] = i
                next_code = eoi_code + 1
                code_size = min_code_size + 1
                max_code = 1 << code_size
            buffer = (px,)

    emit(code_table[buffer])
    emit(eoi_code)

    # Flush remaining bits
    if bits_in_buffer > 0:
        output.append(bit_buffer & 0xFF)

    return bytes(output)


def _gif_sub_blocks(data: bytes) -> bytes:
    """Split data into GIF sub-blocks (max 255 bytes each)."""
    result = bytearray()
    i = 0
    while i < len(data):
        chunk = data[i:i + 255]
        result.append(len(chunk))
        result.extend(chunk)
        i += 255
    result.append(0)  # block terminator
    return bytes(result)


def write_gif(filepath: str, frames: list[list[list[int]]],
              cell_size: int = 4, delay_cs: int = 10):
    """Write an animated GIF from a list of grid frames.

    Each frame is a 2D list of cell ages (0 = dead, >0 = alive with age).
    cell_size: pixels per cell side.
    delay_cs: delay between frames in centiseconds (1/100 s).
    """
    if not frames:
        return
    rows = len(frames[0])
    cols = len(frames[0][0]) if rows else 0
    width = cols * cell_size
    height = rows * cell_size

    # Use 3-bit palette (8 colours)
    min_code_size = 3
    palette_size = 8

    # Build flat palette bytes
    palette_bytes = bytearray()
    for r, g, b in _GIF_PALETTE[:palette_size]:
        palette_bytes.extend([r, g, b])

    out = bytearray()
    # Header
    out.extend(b"GIF89a")
    # Logical screen descriptor
    out.extend(struct.pack("<HH", width, height))
    # GCT flag=1, color res=2 (3 bits), sort=0, GCT size=2 (8 colors)
    out.append(0b10000010)
    out.append(0)  # bg color index
    out.append(0)  # pixel aspect ratio

    # Global color table
    out.extend(palette_bytes)

    # Netscape looping extension (loop forever)
    out.extend(b"\x21\xFF\x0BNETSCAPE2.0\x03\x01\x00\x00\x00")

    for frame in frames:
        # Graphic control extension (delay + disposal)
        out.extend(b"\x21\xF9\x04")
        out.append(0x00)  # disposal=0, no transparency
        out.extend(struct.pack("<H", delay_cs))
        out.append(0)  # transparent color index (unused)
        out.append(0)  # block terminator

        # Image descriptor
        out.extend(b"\x2C")
        out.extend(struct.pack("<HHHH", 0, 0, width, height))
        out.append(0)  # no local color table

        # Build pixel data
        pixels = []
        for r in range(rows):
            row = frame[r]
            for _ in range(cell_size):
                for c in range(cols):
                    idx = _gif_age_index(row[c])
                    pixels.extend([idx] * cell_size)

        # LZW compress
        out.append(min_code_size)
        compressed = _lzw_compress(pixels, min_code_size)
        out.extend(_gif_sub_blocks(compressed))

    # Trailer
    out.append(0x3B)

    with open(filepath, "wb") as f:
        f.write(out)



def sparkline(values: list[int], width: int) -> str:
    """Return a Unicode sparkline string for the given values, scaled to fit width."""
    if not values:
        return ""
    # Use the last `width` values
    vals = values[-width:]
    lo = min(vals)
    hi = max(vals)
    rng = hi - lo if hi > lo else 1
    result = []
    for v in vals:
        idx = int((v - lo) / rng * (len(SPARKLINE_CHARS) - 1))
        result.append(SPARKLINE_CHARS[idx])
    return "".join(result)


