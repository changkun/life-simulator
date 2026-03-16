"""Color schemes and initialization for the terminal UI."""
import curses

# Age-based colour tiers (pair indices 1–5)
AGE_COLORS = [
    (curses.COLOR_GREEN, 1),   # newborn
    (curses.COLOR_CYAN, 2),    # young
    (curses.COLOR_YELLOW, 3),  # mature
    (curses.COLOR_MAGENTA, 4), # old
    (curses.COLOR_RED, 5),     # ancient
]


def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    for fg, idx in AGE_COLORS:
        curses.init_pair(idx, fg, -1)
    # Pair 6: dim border / info text
    curses.init_pair(6, curses.COLOR_WHITE, -1)
    # Pair 7: highlight / title
    curses.init_pair(7, curses.COLOR_CYAN, -1)
    # Heatmap colour tiers (pairs 10–16): cool to hot
    curses.init_pair(10, 17, -1)   # very dim blue (near-zero activity)
    curses.init_pair(11, 19, -1)   # blue
    curses.init_pair(12, 27, -1)   # bright blue
    curses.init_pair(13, 51, -1)   # cyan
    curses.init_pair(14, 226, -1)  # yellow
    curses.init_pair(15, 208, -1)  # orange
    curses.init_pair(16, 196, -1)  # red
    curses.init_pair(17, 231, -1)  # white (maximum heat)
    # Fallback heatmap pairs for terminals with < 256 colors
    curses.init_pair(18, curses.COLOR_BLUE, -1)
    curses.init_pair(19, curses.COLOR_CYAN, -1)
    curses.init_pair(20, curses.COLOR_YELLOW, -1)
    curses.init_pair(21, curses.COLOR_RED, -1)
    curses.init_pair(22, curses.COLOR_WHITE, -1)
    # Pattern search highlight colours (pairs 30–33)
    curses.init_pair(30, curses.COLOR_CYAN, -1)     # Still life
    curses.init_pair(31, curses.COLOR_YELLOW, -1)    # Oscillator
    curses.init_pair(32, curses.COLOR_MAGENTA, -1)   # Spaceship
    curses.init_pair(33, curses.COLOR_WHITE, -1)     # Other / label text
    # Blueprint selection highlight (pair 40)
    curses.init_pair(40, curses.COLOR_GREEN, -1)     # Blueprint selection border/cells
    # Multiplayer player colours (pairs 50–57)
    if curses.COLORS >= 256:
        curses.init_pair(50, 33, -1)    # P1 newborn  (blue)
        curses.init_pair(51, 39, -1)    # P1 young    (light blue)
        curses.init_pair(52, 27, -1)    # P1 mature   (bright blue)
        curses.init_pair(53, 21, -1)    # P1 old      (deep blue)
        curses.init_pair(54, 196, -1)   # P2 newborn  (red)
        curses.init_pair(55, 209, -1)   # P2 young    (orange-red)
        curses.init_pair(56, 160, -1)   # P2 mature   (dark red)
        curses.init_pair(57, 124, -1)   # P2 old      (deep red)
    else:
        curses.init_pair(50, curses.COLOR_BLUE, -1)
        curses.init_pair(51, curses.COLOR_CYAN, -1)
        curses.init_pair(52, curses.COLOR_BLUE, -1)
        curses.init_pair(53, curses.COLOR_BLUE, -1)
        curses.init_pair(54, curses.COLOR_RED, -1)
        curses.init_pair(55, curses.COLOR_MAGENTA, -1)
        curses.init_pair(56, curses.COLOR_RED, -1)
        curses.init_pair(57, curses.COLOR_RED, -1)
    curses.init_pair(58, curses.COLOR_YELLOW, -1)   # contested/neutral born cell
    # Reaction-diffusion colour pairs (60–67): V concentration gradient
    if curses.COLORS >= 256:
        curses.init_pair(60, 17, -1)    # very dark blue (trace V)
        curses.init_pair(61, 19, -1)    # dark blue
        curses.init_pair(62, 27, -1)    # blue
        curses.init_pair(63, 45, -1)    # cyan-blue
        curses.init_pair(64, 51, -1)    # cyan
        curses.init_pair(65, 48, -1)    # aquamarine
        curses.init_pair(66, 226, -1)   # yellow
        curses.init_pair(67, 231, -1)   # white (high V)
    else:
        curses.init_pair(60, curses.COLOR_BLUE, -1)
        curses.init_pair(61, curses.COLOR_BLUE, -1)
        curses.init_pair(62, curses.COLOR_CYAN, -1)
        curses.init_pair(63, curses.COLOR_CYAN, -1)
        curses.init_pair(64, curses.COLOR_GREEN, -1)
        curses.init_pair(65, curses.COLOR_YELLOW, -1)
        curses.init_pair(66, curses.COLOR_MAGENTA, -1)
        curses.init_pair(67, curses.COLOR_WHITE, -1)
    # Lenia colour pairs (70–77): warm organic gradient
    if curses.COLORS >= 256:
        curses.init_pair(70, 22, -1)    # dark green (trace)
        curses.init_pair(71, 28, -1)    # green
        curses.init_pair(72, 34, -1)    # bright green
        curses.init_pair(73, 148, -1)   # yellow-green
        curses.init_pair(74, 214, -1)   # orange
        curses.init_pair(75, 208, -1)   # deep orange
        curses.init_pair(76, 196, -1)   # red
        curses.init_pair(77, 231, -1)   # white (high activity)
    else:
        curses.init_pair(70, curses.COLOR_GREEN, -1)
        curses.init_pair(71, curses.COLOR_GREEN, -1)
        curses.init_pair(72, curses.COLOR_YELLOW, -1)
        curses.init_pair(73, curses.COLOR_YELLOW, -1)
        curses.init_pair(74, curses.COLOR_RED, -1)
        curses.init_pair(75, curses.COLOR_RED, -1)
        curses.init_pair(76, curses.COLOR_MAGENTA, -1)
        curses.init_pair(77, curses.COLOR_WHITE, -1)
    # Physarum colour pairs (80–87): yellow/amber bio-network gradient
    if curses.COLORS >= 256:
        curses.init_pair(80, 22, -1)    # dark green (faint trail)
        curses.init_pair(81, 58, -1)    # olive
        curses.init_pair(82, 100, -1)   # dark yellow
        curses.init_pair(83, 142, -1)   # yellow
        curses.init_pair(84, 178, -1)   # gold
        curses.init_pair(85, 214, -1)   # orange
        curses.init_pair(86, 220, -1)   # bright yellow
        curses.init_pair(87, 231, -1)   # white (dense trail)
    else:
        curses.init_pair(80, curses.COLOR_GREEN, -1)
        curses.init_pair(81, curses.COLOR_GREEN, -1)
        curses.init_pair(82, curses.COLOR_YELLOW, -1)
        curses.init_pair(83, curses.COLOR_YELLOW, -1)
        curses.init_pair(84, curses.COLOR_YELLOW, -1)
        curses.init_pair(85, curses.COLOR_RED, -1)
        curses.init_pair(86, curses.COLOR_MAGENTA, -1)
        curses.init_pair(87, curses.COLOR_WHITE, -1)

    # ── Hydraulic Erosion terrain/water colour pairs (90–99) ──
    if curses.COLORS >= 256:
        curses.init_pair(90, 17, -1)    # deep ocean (very low terrain)
        curses.init_pair(91, 22, -1)    # dark green (low terrain)
        curses.init_pair(92, 28, -1)    # green (lowland)
        curses.init_pair(93, 34, -1)    # bright green (plains)
        curses.init_pair(94, 142, -1)   # yellow-green (hills)
        curses.init_pair(95, 178, -1)   # gold (highlands)
        curses.init_pair(96, 130, -1)   # brown (mountains)
        curses.init_pair(97, 231, -1)   # white (peaks)
        curses.init_pair(98, 33, -1)    # blue (shallow water)
        curses.init_pair(99, 21, -1)    # deep blue (deep water)
    else:
        curses.init_pair(90, curses.COLOR_BLUE, -1)
        curses.init_pair(91, curses.COLOR_GREEN, -1)
        curses.init_pair(92, curses.COLOR_GREEN, -1)
        curses.init_pair(93, curses.COLOR_GREEN, -1)
        curses.init_pair(94, curses.COLOR_YELLOW, -1)
        curses.init_pair(95, curses.COLOR_YELLOW, -1)
        curses.init_pair(96, curses.COLOR_RED, -1)
        curses.init_pair(97, curses.COLOR_WHITE, -1)
        curses.init_pair(98, curses.COLOR_CYAN, -1)
        curses.init_pair(99, curses.COLOR_BLUE, -1)

    # ── Voronoi Crystal Growth colour pairs (100–115) ──
    if curses.COLORS >= 256:
        curses.init_pair(100, 196, -1)   # red
        curses.init_pair(101, 46, -1)    # green
        curses.init_pair(102, 33, -1)    # blue
        curses.init_pair(103, 226, -1)   # yellow
        curses.init_pair(104, 201, -1)   # magenta
        curses.init_pair(105, 51, -1)    # cyan
        curses.init_pair(106, 208, -1)   # orange
        curses.init_pair(107, 141, -1)   # purple
        curses.init_pair(108, 118, -1)   # lime
        curses.init_pair(109, 197, -1)   # pink
        curses.init_pair(110, 87, -1)    # teal
        curses.init_pair(111, 220, -1)   # gold
        curses.init_pair(112, 69, -1)    # cornflower
        curses.init_pair(113, 168, -1)   # rose
        curses.init_pair(114, 35, -1)    # sea green
        curses.init_pair(115, 240, -1)   # grey (grain boundaries)
    else:
        curses.init_pair(100, curses.COLOR_RED, -1)
        curses.init_pair(101, curses.COLOR_GREEN, -1)
        curses.init_pair(102, curses.COLOR_BLUE, -1)
        curses.init_pair(103, curses.COLOR_YELLOW, -1)
        curses.init_pair(104, curses.COLOR_MAGENTA, -1)
        curses.init_pair(105, curses.COLOR_CYAN, -1)
        curses.init_pair(106, curses.COLOR_RED, -1)
        curses.init_pair(107, curses.COLOR_MAGENTA, -1)
        curses.init_pair(108, curses.COLOR_GREEN, -1)
        curses.init_pair(109, curses.COLOR_RED, -1)
        curses.init_pair(110, curses.COLOR_CYAN, -1)
        curses.init_pair(111, curses.COLOR_YELLOW, -1)
        curses.init_pair(112, curses.COLOR_BLUE, -1)
        curses.init_pair(113, curses.COLOR_RED, -1)
        curses.init_pair(114, curses.COLOR_GREEN, -1)
        curses.init_pair(115, curses.COLOR_WHITE, -1)

    # ── Terrain Generation & Erosion Landscape colour pairs (120–131) ──
    if curses.COLORS >= 256:
        curses.init_pair(120, 17, -1)    # deep ocean
        curses.init_pair(121, 27, -1)    # ocean
        curses.init_pair(122, 33, -1)    # shallow water
        curses.init_pair(123, 229, -1)   # beach/sand
        curses.init_pair(124, 34, -1)    # coastal grass
        curses.init_pair(125, 28, -1)    # lowland forest
        curses.init_pair(126, 22, -1)    # dense forest
        curses.init_pair(127, 142, -1)   # highland scrub
        curses.init_pair(128, 130, -1)   # rock/mountain
        curses.init_pair(129, 245, -1)   # alpine/bare rock
        curses.init_pair(130, 231, -1)   # snow
        curses.init_pair(131, 40, -1)    # vegetation overlay (bright green)
    else:
        curses.init_pair(120, curses.COLOR_BLUE, -1)
        curses.init_pair(121, curses.COLOR_BLUE, -1)
        curses.init_pair(122, curses.COLOR_CYAN, -1)
        curses.init_pair(123, curses.COLOR_YELLOW, -1)
        curses.init_pair(124, curses.COLOR_GREEN, -1)
        curses.init_pair(125, curses.COLOR_GREEN, -1)
        curses.init_pair(126, curses.COLOR_GREEN, -1)
        curses.init_pair(127, curses.COLOR_YELLOW, -1)
        curses.init_pair(128, curses.COLOR_RED, -1)
        curses.init_pair(129, curses.COLOR_WHITE, -1)
        curses.init_pair(130, curses.COLOR_WHITE, -1)
        curses.init_pair(131, curses.COLOR_GREEN, -1)




def color_for_age(age: int) -> int:
    """Return a curses colour pair attribute based on cell age."""
    if age <= 1:
        return curses.color_pair(1)
    if age <= 3:
        return curses.color_pair(2)
    if age <= 8:
        return curses.color_pair(3)
    if age <= 20:
        return curses.color_pair(4)
    return curses.color_pair(5)


# Multiplayer player colour pairs: P1 → 50-53, P2 → 54-57, neutral → 58
_MP_P1_PAIRS = [50, 51, 52, 53]  # newborn → old
_MP_P2_PAIRS = [54, 55, 56, 57]



def color_for_mp(age: int, owner: int) -> int:
    """Return a curses colour pair for a multiplayer cell based on owner (1 or 2) and age."""
    if owner == 1:
        pairs = _MP_P1_PAIRS
    elif owner == 2:
        pairs = _MP_P2_PAIRS
    else:
        return curses.color_pair(58)
    if age <= 1:
        return curses.color_pair(pairs[0])
    if age <= 5:
        return curses.color_pair(pairs[1])
    if age <= 15:
        return curses.color_pair(pairs[2])
    return curses.color_pair(pairs[3])


# Heatmap 256-color tiers (pair indices 10–17) and 8-color fallback (18–22)
HEAT_PAIRS_256 = [10, 11, 12, 13, 14, 15, 16, 17]
HEAT_PAIRS_8 = [18, 18, 19, 19, 20, 20, 21, 22]



def color_for_heat(fraction: float) -> int:
    """Return a curses colour pair attribute for a heatmap fraction 0.0–1.0.
    0 = coolest (dim blue), 1 = hottest (white)."""
    if curses.COLORS >= 256:
        pairs = HEAT_PAIRS_256
    else:
        pairs = HEAT_PAIRS_8
    idx = min(int(fraction * len(pairs)), len(pairs) - 1)
    return curses.color_pair(pairs[idx])


# ── GIF encoder (pure Python, no external dependencies) ─────────────────────

# Color palette for GIF: index 0 = background, 1–5 = age tiers
_GIF_PALETTE = [
    (18, 18, 24),     # 0: background (dark)
    (0, 200, 0),      # 1: newborn (green)
    (0, 200, 200),    # 2: young (cyan)
    (200, 200, 0),    # 3: mature (yellow)
    (200, 0, 200),    # 4: old (magenta)
    (200, 0, 0),      # 5: ancient (red)
    (100, 100, 100),  # 6: grid lines (subtle)
    (255, 255, 255),  # 7: spare (white)
]


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
