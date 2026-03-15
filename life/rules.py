"""Rule presets and parsing for life-like cellular automata."""

RULE_PRESETS = {
    "Conway's Life": {"birth": {3}, "survival": {2, 3}},
    "HighLife":      {"birth": {3, 6}, "survival": {2, 3}},
    "Day & Night":   {"birth": {3, 6, 7, 8}, "survival": {3, 4, 6, 7, 8}},
    "Seeds":         {"birth": {2}, "survival": set()},
    "Life w/o Death":{"birth": {3}, "survival": {0, 1, 2, 3, 4, 5, 6, 7, 8}},
    "Diamoeba":      {"birth": {3, 5, 6, 7, 8}, "survival": {5, 6, 7, 8}},
    "2x2":           {"birth": {3, 6}, "survival": {1, 2, 5}},
    "Morley":        {"birth": {3, 6, 8}, "survival": {2, 4, 5}},
    "Anneal":        {"birth": {4, 6, 7, 8}, "survival": {3, 5, 6, 7, 8}},
}


def rule_string(birth: set, survival: set) -> str:
    """Format birth/survival sets as a rule string like 'B3/S23'."""
    b = "".join(str(n) for n in sorted(birth))
    s = "".join(str(n) for n in sorted(survival))
    return f"B{b}/S{s}"


def parse_rule_string(rs: str) -> tuple[set, set] | None:
    """Parse a rule string like 'B3/S23' into (birth, survival) sets.
    Returns None on invalid input."""
    rs = rs.strip().upper()
    if "/" not in rs:
        return None
    parts = rs.split("/", 1)
    if len(parts) != 2:
        return None
    b_part, s_part = parts
    if not b_part.startswith("B") or not s_part.startswith("S"):
        return None
    try:
        birth = {int(ch) for ch in b_part[1:]} if len(b_part) > 1 else set()
        survival = {int(ch) for ch in s_part[1:]} if len(s_part) > 1 else set()
    except ValueError:
        return None
    if not all(0 <= n <= 8 for n in birth | survival):
        return None
    return birth, survival

