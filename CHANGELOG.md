# Changelog

All notable changes to this project are documented in this file.

## 2026-03-15

### Added: TUI Dashboard — landing screen with live preview, categories, and favorites

Replaces the old "drop straight into Game of Life" startup with a polished home screen
that lets users discover, browse, and launch all 90+ simulation modes.

**New file:** `life/dashboard.py` (~880 lines)

**Features:**
- ASCII art "LIFE SIM" banner (auto-downsizes for narrow terminals)
- Left panel: all modes grouped by category with icons (⬡ Classic CA, ◎ Particle & Swarm, ≈ Fluid Dynamics, etc.)
- Right panel: mode info (name, category, description, hotkey) + live animated mini-preview of the selected mode
- 20+ unique preview animations (waves, particles, fractals, fire, matrix rain, fish tank, DNA helix, pendulums, colliders, etc.)
- Favorites: press `f` to star/unstar, `Tab` to filter to favorites only, persisted to `~/.life_saves/favorites.json`
- Live search: type to filter modes by name, description, or category
- Category cycling: `Ctrl+A` cycles through category filters
- `Enter` launches selected mode, `Esc` exits to default Game of Life
- `M` opens the legacy mode browser (still accessible as a hidden shortcut)

**Integration:**
- Dashboard auto-opens on startup unless `--pattern`, `--host`, `--connect`, or `--no-dashboard` is specified
- `m` key now opens the dashboard (previously opened the flat mode browser)
- Dashboard renders at highest priority in the draw loop (before mode browser)
- Dashboard key handling is first check in the run loop

**CLI:** `--no-dashboard` flag for users who prefer the old immediate-start behavior

**Why:** With 90+ modes, the old CLI-flag / in-app-mode-browser flow made discovery
hard. The dashboard transforms this from a CLI tool into a showcase application — a
visual "home base" for the entire simulation collection.

### Refactored: Split 51K-line monolith into modular package

The single-file `life.py` (51,228 lines, 987 functions) has been decomposed into a
104-file Python package under `life/`. The original entry point (`life.py`) is now a
10-line shim; all logic lives in the package.

**Package layout:**

| Module | Purpose | Lines |
|--------|---------|-------|
| `life/app.py` | App class core — init, run loop, draw dispatch | ~6,500 |
| `life/grid.py` | Grid class — toroidal cellular automaton grid | ~140 |
| `life/constants.py` | Speed tables, cell chars, zoom levels | ~30 |
| `life/patterns.py` | 13 preset patterns + 10 puzzle challenges | ~200 |
| `life/rules.py` | Rule presets, `rule_string()`, `parse_rule_string()` | ~40 |
| `life/colors.py` | Color palettes, age/mp/heat color helpers | ~330 |
| `life/utils.py` | Pattern recognition, RLE parsing, GIF encoder, sparkline | ~520 |
| `life/sound.py` | SoundEngine — procedural audio synthesis | ~175 |
| `life/multiplayer.py` | MultiplayerNet — TCP networking | ~380 |
| `life/registry.py` | MODE_CATEGORIES + MODE_REGISTRY (89 entries) | ~230 |
| `life/modes/*.py` | **91 mode files**, one per simulation mode | ~44,700 |

**Architecture:**

- Each mode file defines standalone functions (`enter`/`exit`/`step`/`draw`/`handle`)
  and a `register(App)` function that monkey-patches them onto the App class.
- `life/modes/__init__.py` has `register_all_modes()` which loads all 91 mode files.
- `life/__init__.py` uses lazy imports to avoid circular dependencies.
- Backward compatible: `./life.py` still works; `python -m life` also works.
- App class has 929 methods after all modes register.

**Why:** At 51K lines, the monolith was becoming impractical to navigate, test, or
extend. Every new simulation mode made the problem worse. The package structure makes
future mode additions trivial (add one file, register in `__init__.py`) and the
codebase navigable.

### Added: Particle Collider / Hadron Collider (Ctrl+Shift+Z)

A CERN-inspired particle physics simulation — beams orbit an elliptical accelerator ring and collide at detector interaction points, producing showers of decay products.

**What it does:**
- Elliptical accelerator ring drawn with box-drawing characters and pulsing energy animation
- Beam particles (clockwise and counter-clockwise) orbiting with trailing dots
- 4 detector interaction points modeled after real LHC experiments (ATLAS, CMS, ALICE, LHCb) with collision flash effects
- Collision showers: 4–25 decay product particles spray outward with physics-based deceleration and lifetime decay
- 12 detectable particles: Higgs boson, W/Z bosons, top/charm quarks, muons, taus, photons, gluons, pions, kaons, B mesons — with measured mass and energy
- 4 presets: LHC Standard (13.6 TeV p-p), Heavy Ion (dense showers), Electron-Positron (clean jets), Discovery Mode (high luminosity/rare particles)
- CERN-aesthetic UI: beam status readout, scrolling detector event log, flash detection banner
- Controls: `Space` (pause), `c` (force collision), `+`/`-` (speed), `r` (reset), `R` (menu), `i` (info overlay), `q` (quit)

**Why:** The project had physics modes (gravity, fluids, electromagnetism) but nothing at the subatomic scale. This adds high-energy particle physics with a fun, educational CERN aesthetic.

**Category:** Physics & Math (~550 lines added to life.py)

### Added: ASCII Aquarium / Fish Tank (Ctrl+Shift+Y)

A relaxing, screensaver-style "zen mode" — the project's first purely ambient simulation.

**What it does:**
- 8 fish species with unique ASCII sprites (Minnow, Guppy, Tetra, Angelfish, Clownfish, Pufferfish, Swordfish, Whale), each with distinct size, speed, and directional art
- 4 presets: Tropical Reef, Deep Ocean, Koi Pond, Goldfish Bowl
- Procedural environment: swaying seaweed, rising bubble streams, surface light ripples, caustic light patterns, sandy bottom with height variation
- Interactive: feed fish (`f`), tap glass to startle (`t`), add/remove fish (`a`/`d`), add bubble streams (`b`), adjust speed (`+`/`-`), toggle info (`i`), pause (`Space`)

**Why:** The project had 60+ modes covering physics, biology, fractals, and chaos — but nothing purely ambient or meditative. This fills the "zen mode" gap.

**Category:** Audio & Visual (~560 lines added to life.py)

## Previous additions (selected)

| Date | Mode | Key |
|------|------|-----|
| — | ASCII Aquarium / Fish Tank | Ctrl+Shift+Y |
| — | Kaleidoscope / Symmetry Patterns | Ctrl+Shift+V |
| — | Ant Farm Simulation | — |
| — | Matrix Digital Rain | — |
| — | Maze Solving Algorithm Visualizer | — |
| — | Lissajous Curve / Harmonograph | — |
| — | Fluid Rope / Honey Coiling | — |
| — | Snowfall & Blizzard | — |
| — | Fourier Epicycle Drawing | — |
| — | DNA Helix & Genetic Algorithm | — |
| — | Sorting Algorithm Visualizer | — |
