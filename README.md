# Life Simulator

```
  ╔════════════════════════════════════════════════════════════════════════════╗
  ║                                                                            ║
  ║    ██      ██ ████████ ████████                                            ║
  ║    ██      ██ ██       ██                                                  ║
  ║    ██      ██ ██████   ██████                                              ║
  ║    ██      ██ ██       ██                                                  ║
  ║    ███████ ██ ██       ████████                                            ║
  ║                                                                            ║
  ║    ███████ ██ ██     ██ ██    ██ ██       ████   ██████ ████████ ███████   ║
  ║    ██      ██ ███   ███ ██    ██ ██      ██  ██    ██   ██    ██ ██    ██  ║
  ║    ███████ ██ ██ ███ ██ ██    ██ ██      ██████    ██   ██    ██ ███████   ║
  ║         ██ ██ ██  █  ██ ██    ██ ██      ██  ██    ██   ██    ██ ██   ██   ║
  ║    ███████ ██ ██     ██  ██████  ███████ ██  ██    ██   ████████ ██    ██  ║
  ║                                                                            ║
  ║    cellular automata · fluid dynamics · particle systems                   ║
  ║    quantum circuits · neural networks · ecology · fractals                 ║
  ║    game theory · astrophysics · chemistry · evolution                      ║
  ║                                                                            ║
  ╚════════════════════════════════════════════════════════════════════════════╝
```

A terminal-based life simulator written in pure Python. It covers cellular
automata, fluid dynamics, particle systems, quantum circuits, neural networks,
ecology, game theory, fractals, and more, all rendered with curses.
It needs only the standard library.

For the scientific background, mathematical formulations, and literature references
behind each simulation mode, see the **[Scientific Guide](docs/README.md)**.

## Table of Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Simulation Modes](#simulation-modes)
- [Controls](#controls)
  - [Core](#core)
  - [Drawing & Editing](#drawing--editing)
  - [Navigation & View](#navigation--view)
  - [Mode Shortcuts](#mode-shortcuts)
  - [Timeline & Replay](#timeline--replay)
  - [File I/O](#file-io)
- [Features](#features)
  - [Mode Browser](#mode-browser)
  - [Pattern Library](#pattern-library)
  - [Rule Editor](#rule-editor)
  - [Timeline & Branching](#timeline--branching)
  - [Snapshots](#snapshots)
  - [Heatmap & Overlays](#heatmap--overlays)
  - [Truecolor & Colormaps](#truecolor--colormaps)
  - [3D Isometric View](#3d-isometric-view)
  - [Multiplayer](#multiplayer)
  - [Screensaver / Demo Reel](#screensaver--demo-reel)
  - [GIF & Cast Recording](#gif--cast-recording)
  - [Genome Sharing](#genome-sharing)
  - [Scripting & Choreography](#scripting--choreography)
- [Project Structure](#project-structure)
- [License](#license)

---

## Quick Start

```bash
make        # or: uv sync
uv run life
```

Press `m` to open the mode browser, `?` for help, `q` to quit.

## Requirements

- Python 3.10+
- A terminal with color support (256-color recommended; 24-bit truecolor for best visuals)
- At least 80×24 characters. Every mode fits that size: `tests/test_layout_80x24.py` draws each mode's menu, run and alternate views on an 80×24 screen and fails if any text runs off the edge or uses a double-width character.
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
git clone https://github.com/changkun/life-simulator.git
cd life-simulator

# Using uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Usage

```bash
uv run life                          # Launch (opens dashboard)
uv run life --pattern glider         # Start with a specific pattern
uv run life --pattern glider_gun     # Gosper glider gun
uv run life --rows 100 --cols 200    # Custom grid size
uv run life --no-dashboard           # Skip dashboard, start in Game of Life
uv run life --screensaver            # Demo reel (shuffled, all modes)
uv run life --screensaver all_sequential   # Demo reel (ordered)
uv run life --screensaver-interval 5 # 5 seconds per mode
uv run life --list-patterns          # List all built-in patterns
uv run life --terrarium              # Persistent terrarium (saves on exit, resumes on next launch)
uv run life --host                   # Host a multiplayer game
uv run life --host 9000              # Host on a specific port
uv run life --connect HOST:PORT      # Join a multiplayer game
```

Or without uv:

```bash
python life.py
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-p`, `--pattern` | — | Start with a built-in pattern (see `--list-patterns`, e.g. `glider`, `glider_gun`, `pulsar`) |
| `--rows` | 80 | Grid height |
| `--cols` | 120 | Grid width |
| `--no-dashboard` | off | Skip dashboard, start directly in Game of Life |
| `--screensaver` | — | Demo reel mode (`all_sequential`, `all_shuffle`, `fav_sequential`, `fav_shuffle`) |
| `--screensaver-interval` | 15 | Seconds per mode in screensaver mode |
| `--list-patterns` | — | List available patterns and exit |
| `--terrarium` | off | Launch Terrarium mode: persistent simulation that saves on exit and resumes on next launch |
| `--host` | — | Host a multiplayer game (optional port, default 7654) |
| `--connect` | — | Connect to a multiplayer game (`HOST:PORT`) |

## Simulation Modes

Press `m` at any time to open the mode browser. The registry holds 181 modes in 12 categories:

- **Classic CA** (12) — Game of Life, Wolfram 1D Automaton, Langton's Ant, Hexagonal Grid, Wireworld, Cyclic CA, Hodgepodge Machine, Lenia, Turmites, 3D Game of Life, Hyperbolic Cellular Automata, Graph Cellular Automata
- **Particle & Swarm** (10) — Falling Sand, Boids Flocking, Particle Life, Physarum Slime Mold, Ant Colony Optimization, N-Body Gravity, Diffusion-Limited Aggregation, Active Matter, Granular Dynamics, Bee Colony & Waggle Dance Communication
- **Physics & Waves** (31) — Wave Equation, Ising Model, Kuramoto Oscillators, Quantum Walk, Lightning, Chladni Plate Vibrations, Magnetic Field Lines, FDTD Electromagnetic Waves, Double Pendulum, Cloth Simulation, Earthquake & Seismic Waves, Plate Tectonics & Mantle Convection, Volcanic Eruption, Black Hole Accretion Disk, Solar System Orrery, Planetary Accretion & Solar System Formation, Aurora Borealis, Pendulum Wave, Tornado & Supercell Storm, Electric Circuit Simulator, Molecular Dynamics / Phase Transitions, Magnetism & Spin Glass, Spacetime Fabric, Quantum Game of Life, Time Crystal, Topological Solitons, Spin Ice & Emergent Monopoles, Percolation Theory & Critical Phenomena, Geometric Optics & Light, Tokamak Fusion Plasma Confinement, Nuclear Reactor Physics & Meltdown Dynamics
- **Fluid Dynamics** (13) — Lattice Boltzmann Fluid, Navier-Stokes, Rayleigh-Benard Convection, SPH Fluid, MHD Plasma, Superfluid Helium, Atmospheric Weather, Ocean Currents, Fluid Rope / Honey Coiling, Fluid of Life, Ferrofluid Dynamics, Planetary Atmosphere & Weather System, Ocean Thermohaline Circulation & Global Current System
- **Chemical & Biological** (26) — Reaction-Diffusion Textures, BZ Reaction, Chemotaxis, Forest Fire, SIR Epidemic, Lotka-Volterra, Spiking Neural Network, Cellular Potts Model, Artificial Life Ecosystem, Ant Farm Simulation, Morphogenesis, Artificial Chemistry, Immune System Response & Pathogen Defense, Coral Reef Ecosystem, Ecosystem Evolution & Speciation, Mycelium Network / Wood Wide Web, Primordial Soup & Origin of Life, Embryogenesis & Gastrulation, Firefly Synchronization & Bioluminescence, Blood Vessel Network & Angiogenesis, Bacterial Quorum Sensing & Biofilm Formation, Cardiac Electrophysiology & Arrhythmia, Cortical Neural Dynamics & Seizure Propagation, Protein Folding & Misfolding, CRISPR-Cas9 Gene Editing & Repair, Mitosis & Cell Division Cycle
- **Game Theory & Social** (6) — Spatial Prisoner's Dilemma, Schelling Segregation, Rock-Paper-Scissors, Stock Market, Civilization & Cultural Evolution, Crowd Dynamics & Evacuation
- **Fractals & Chaos** (8) — Abelian Sandpile, Strange Attractors, Fractal Explorer, Snowflake Growth, Erosion Patterns, Chaos Game / IFS Fractals, L-System Fractal Garden, Lissajous Curve / Harmonograph
- **Procedural & Computational** (17) — Wave Function Collapse, Maze Generation, Voronoi Diagram, Terrain Generation, 3D Terrain Flythrough, SDF Ray Marching, Shader Toy, Doom Raycaster, Sorting Algorithm Visualizer, DNA Helix & Genetic Algorithm, Fourier Epicycle Drawing, Maze Solver Visualizer, Neural Network Training Visualizer, Quantum Circuit Simulator, Tierra Digital Organisms, Living Labyrinth, Programmable Matter
- **Audio & Visual** (6) — Music Visualizer, Snowfall & Blizzard, Matrix Digital Rain, Cellular Symphony, Kaleidoscope / Symmetry Patterns, ASCII Aquarium / Fish Tank
- **Complex Simulations** (14) — Traffic Flow, Galaxy Formation, Smoke & Fire, Fireworks, Wildfire Spread & Firefighting, City Growth & Urban Simulation, Termite Mound Construction & Stigmergy, Deep Sea Hydrothermal Vent Ecosystem, Stellar Lifecycle & Supernova, Tide Pool & Intertidal Ecosystem, Spider Orb Web Construction & Prey Capture, Deep-Sea Bioluminescent Abyss, Mycorrhizal Network & Wood Wide Web, Glacier Dynamics & Ice Age Cycles
- **Meta Modes** (37) — Compare Rules, Multi-Rule Race, Puzzle / Challenge, Evolution / GA, Screensaver / Demo Reel, Parameter Space Explorer, Evolution Lab, Auto-Discovery, Evolutionary Playground, Live Rule Editor, Simulation Mashup, Battle Royale, Simulation Portal, Split-Screen Dual Simulation, Simulation Observatory, Layer Compositing, Cinematic Demo Reel, Topology Mode, Visual FX Pipeline, Recording & Export, Scripting & Choreography, Neural Cellular Automata, Timeline Branching, Ancestor Search, Self-Modifying Rules CA, Rule Mutation Engine, Sim-in-a-Cell, Symbiosis Multi-Physics, Terrarium, Emergent Computation Detector, Butterfly Effect, Genesis Protocol, Phase Space Navigator, Adaptive Adversary, Simulation Archaeology, Rule Phylogenetics, Reverse Life
- **Physics & Math** (1) — Particle Collider / Hadron Collider

Modes with no key (shown as `—` in the browser) open only from the browser. Visual FX
Pipeline opens an effects menu where `1`-`6` toggle effects and `Esc` closes it. Topology
Mode cycles the grid topology each time you select it.

## Controls

### Core

| Key | Action |
|-----|--------|
| `Space` | Play / pause |
| `n` / `.` | Step one generation |
| `<` / `>` | Decrease / increase speed |
| `q` | Quit |
| `?` / `h` | Help screen |
| `m` | Mode browser |
| `M` | Toggle sound |
| `N` | Multiplayer (prompts to host or connect) |
| `Ctrl+K` | Toggle analytics overlay |

### Drawing & Editing

| Key | Action |
|-----|--------|
| Arrow keys / `k` `j` `l` | Move cursor (`k` up, `j` down, `l` right; `h` opens help) |
| `e` | Toggle cell under cursor |
| `d` | Draw mode (paint while moving) |
| `x` | Erase mode (erase while moving) |
| `Esc` | Exit draw/erase mode |
| `p` | Pattern selector |
| `t` | Stamp pattern at cursor |
| `r` | Randomize grid |
| `c` | Clear grid |
| `R` | Rule editor (B/S presets) |

### Navigation & View

| Key | Action |
|-----|--------|
| `+` / `-` | Zoom in / out (density glyphs); mouse wheel also zooms |
| `0` | Reset zoom to 1:1 |
| `Tab` | Toggle minimap overlay |
| `H` | Toggle heatmap (cumulative cell activity) |
| `v` | Toggle 3D isometric view |
| `K` | Cycle colormap |
| `W` | Save a region as a blueprint |
| `w` | Blueprint library (stamp or delete saved blueprints) |
| `V` | Compare two rules side-by-side |
| `Z` | Race 2-4 rules with scoreboard |
| `f` | Pattern search (find known shapes) |
| `g` | Toggle ghost trail |
| `G` | Toggle morph transitions between modes |
| `:` | Cycle the morph easing curve (while morphing is on) |
| `I` | Toggle computation detector (`Tab` cycles its view) |
| `y` | Toggle spectrum overlay |
| `Ctrl+P` | Toggle phase detector |
| `Ctrl+T` | Phase bookmarks (needs detected transitions) |
| `Ctrl+V` | Toggle sparkline metrics HUD |

### Mode Shortcuts

| Key | Mode |
|-----|------|
| `1` | Wolfram 1D Automaton |
| `2` | Langton's Ant |
| `3` | Hexagonal Grid |
| `4` | Wireworld |
| `5` | Falling Sand |
| `6` | Reaction-Diffusion Textures |
| `7` | Lenia |
| `8` | Physarum Slime Mold |
| `9` | Boids Flocking |
| `A` | Ant Colony Optimization |
| `C` | Puzzle / Challenge |
| `D` | Diffusion-Limited Aggregation |
| `E` | Evolution / GA (Game of Life screen) |
| `F` | Lattice Boltzmann Fluid |
| `J` | Lotka-Volterra |
| `L` | Maze Generation |
| `O` | Forest Fire |
| `P` | Abelian Sandpile |
| `Q` | Turmites |
| `S` | Stock Market |
| `T` | Traffic Flow |
| `U` | Cyclic CA |
| `X` | Wave Function Collapse |
| `Y` | N-Body Gravity |
| `#` | Ising Model |
| `@` | Spatial Prisoner's Dilemma |
| `&` | Rock-Paper-Scissors |
| `!` | Wave Equation |
| `(` | Kuramoto Oscillators |
| `)` | Spiking Neural Network |
| `` ` `` | BZ Reaction |
| `{` | Chemotaxis |
| `}` | MHD Plasma |
| `\|` | Strange Attractors |
| `^` | Lightning (Game of Life screen) |
| `"` | Galaxy Formation |
| `*` | Snowflake Growth |
| `$` | Erosion Patterns |
| `~` | Hodgepodge Machine |
| `%` | Voronoi Diagram |
| `;` | Terrain Generation |
| `'` | Cloth Simulation |
| `/` | L-System Fractal Garden |
| `\` | Smoke & Fire |

Some modes use `Ctrl+` keys:

| Key | Mode |
|-----|------|
| `Ctrl+A` | SPH Fluid |
| `Ctrl+B` | Butterfly Effect |
| `Ctrl+D` | Navier-Stokes |
| `Ctrl+F` | Fireworks (see below) |
| `Ctrl+G` | Chaos Game / IFS Fractals |
| `Ctrl+L` | Chladni Plate Vibrations |
| `Ctrl+N` | Magnetic Field Lines |
| `Ctrl+R` | Rayleigh-Benard Convection |
| `Ctrl+U` | Scripting & Choreography |
| `Ctrl+X` | Recording & Export |
| `Ctrl+Y` | 3D Terrain Flythrough |

`Ctrl+F` forks a branch while the timeline is scrubbed back. It also freezes
the long-exposure composite while a capture is running or a composite exists.
Otherwise it starts Fireworks. In the same way, `[` `]` and `{` `}` adjust the
exposure only in those states. Otherwise `{` opens Chemotaxis and `}` opens
MHD Plasma.

Every other mode has no key and opens only from the mode browser (`m`). That
includes Particle Life, Quantum Walk, FDTD Electromagnetic Waves, Double
Pendulum, SIR Epidemic, Cellular Potts Model, Schelling Segregation and Fractal
Explorer. At the Game of Life screen their old keys do other things: `0` resets
zoom, `E` opens Evolution / GA, `K` cycles colormaps, `^` opens Lightning, `G`
toggles morph transitions, `Ctrl+E` starts or stops a long exposure, `Ctrl+P`
toggles the phase detector, `Ctrl+T` opens phase bookmarks, `Ctrl+K` toggles
analytics, `Ctrl+O` loads a snapshot, `Ctrl+W` saves one and `Ctrl+V` toggles
the sparkline HUD.

Inside a mode, a key the mode binds itself goes to the mode, not to the global
overlays (ghost trail `g`, morph `G`, computation detector `I`, time travel
`u` `[` `]`, parameter tuner `P`, minimap `Tab`). The overlays still work in
Game of Life and in modes that leave the key free. `z` (genome) also works in
modes that do not bind it.

Mouse clicks and drags edit the Game of Life grid only when no mode is active.
The wheel zooms, and a right-button drag pans.

### Timeline & Replay

| Key | Action |
|-----|--------|
| `u` | Undo / rewind one generation |
| `[` / `]` | Scrub timeline back/forward 10 steps |
| `Ctrl+F` | Fork branch (while scrubbed back) |
| `b` | Bookmark current generation |
| `B` | List / jump to bookmarks |

### File I/O

| Key | Action |
|-----|--------|
| `s` | Save grid state |
| `o` | Open / load a saved state |
| `Ctrl+W` | Save full snapshot (grid + mode + config) |
| `Ctrl+O` | Load a full snapshot |
| `i` | Import RLE pattern file |
| `a` | Record / stop GIF export |
| `Ctrl+X` | Record / export `.cast` or `.txt` |
| `Ctrl+E` | Start / stop a long exposure (`Ctrl+]` exports the composite) |
| `z` | Genome: export / import simulation config |

## Features

### Mode Browser

Press `m` to open the mode browser (also the dashboard shown at launch). It
lists all modes by category, with search and favorites. Select a mode to enter it.
Opening Game of Life on an empty grid seeds a random soup, paused; press `r` to
reseed or `c` to clear.

### Pattern Library

Press `p` to browse built-in patterns: gliders, guns, oscillators, still lifes,
methuselahs, and more. Press `t` to stamp the selected pattern at the cursor.

### Rule Editor

Press `R` to open the interactive rule editor. Toggle individual B/S bits to
create custom cellular automaton rules, or select from presets.

### Timeline & Branching

The last 500 generations are kept in a history buffer. Rewind with `u`, scrub with
`[`/`]`, and fork alternate timelines with `Ctrl+F` at any past point. Bookmarks
(`b`/`B`) mark interesting states for later recall.

### Snapshots

Press `Ctrl+W` to save a full simulation snapshot — grid state, active mode,
mode-specific parameters, viewport position, zoom, speed, colormap, and more —
to a named `.snapshot.json` file in `~/.life_saves/snapshots/`. Press `Ctrl+O`
to browse saved snapshots with metadata preview, load one to resume exactly where
you left off, or delete old ones.

### Heatmap & Overlays

Press `H` for a heatmap that colors each cell by how many generations it
has been alive since the grid was last cleared or randomized.

### Truecolor & Colormaps

Terminals that set `COLORTERM` to `truecolor` or `24bit` get continuous RGB
gradients. Press `K` to cycle through 8 colormaps: viridis, magma, inferno,
plasma, ocean, thermal, terrain, and amber. Reaction-Diffusion Textures, Lenia,
Lattice Boltzmann Fluid, Physarum Slime Mold, and Wave Equation use the colormaps
directly; other terminals use the 256-color palette.

### 3D Isometric View

Press `v` to render the grid as an isometric 3D landscape where live cells are
raised blocks. Cell height shows age.

### Multiplayer

Host a game with `--host` or join with `--connect HOST:PORT`. You can also press
`N` in the app. Players share the same grid over TCP.

### Screensaver / Demo Reel

Launch with `--screensaver` to auto-cycle through modes with transitions.
Set the interval with `--screensaver-interval` and the playlist with a preset:
`all_sequential`, `all_shuffle`, `fav_sequential`, or `fav_shuffle`.

### GIF & Cast Recording

Press `a` to record frames and export as animated GIF. Press `Ctrl+X` to record
terminal frames and export as asciinema `.cast` or plain-text flipbook.

### Genome Sharing

Press `z` to encode the current simulation configuration (mode and parameters)
as a shareable seed string. Paste a seed to reproduce
someone else's exact configuration.

### Scripting & Choreography

Press `Ctrl+U` to enter scripting mode. Write `.show` files with timed mode
transitions, parameter sweeps, and effect toggles for automated presentations.

## Project Structure

```
life.py            # Entry point
life/
  app.py           # Core application and key handling
  dashboard.py     # Landing screen and mode browser
  analytics.py     # Analytics overlay and phase detector
  grid.py          # Grid / world management
  colors.py        # Color schemes and colormaps
  constants.py     # Shared constants
  patterns.py      # Built-in patterns and puzzles
  registry.py      # Mode registry and categories
  rules.py         # CA rule presets and parsing
  sound.py         # Audio synthesis
  multiplayer.py   # TCP multiplayer
  utils.py         # RLE parsing, GIF encoding, pattern recognition
  modes/           # Simulation mode modules
docs/              # Scientific guide (formulations & references)
```

Design choices:

- **Zero dependencies** — pure Python standard library, no pip packages
- **Modular modes** — each simulation is a module in `life/modes/`
- **Registry-driven** — `life/registry.py` lists every mode; the mode browser reads it
- **Single entry point** — `uv run life` or `python life.py`

## License

[MIT](LICENSE) — Changkun Ou
