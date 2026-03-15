# Life Simulator

A terminal-based life simulator built entirely with Python's standard library.
Cellular automata, fluid dynamics, quantum circuits, neural networks, ecology,
and more — all rendered with curses. No external dependencies.

## Quick Start

```bash
uv run life
```

Press `m` to open the mode browser, `?` for help, `q` to quit.

## Requirements

- Python 3.10+
- A terminal with color support (256-color recommended)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
git clone https://github.com/changkun/null-claude.git
cd null-claude

# Using uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Usage

```bash
uv run life                          # Launch (opens dashboard)
uv run life --pattern glider         # Start with a specific pattern
uv run life --rows 100 --cols 200    # Custom grid size
uv run life --no-dashboard           # Skip dashboard, start in Game of Life
uv run life --screensaver            # Demo reel mode (auto-cycles all modes)
uv run life --screensaver-interval 5 # 5 seconds per mode
uv run life --list-patterns          # List all built-in patterns
uv run life --host                   # Host a multiplayer game
uv run life --connect HOST:PORT      # Join a multiplayer game
```

Or without uv:

```bash
python life.py
```

## Simulation Modes

Press `m` at any time to open the mode browser. Modes are organized into
categories:

### Classic CA

| Mode | Key | Description |
|------|-----|-------------|
| Game of Life | *(default)* | Conway's classic with pattern library, rule editor, heatmap, cycle detection |
| Wolfram 1D | `1` | All 256 elementary 1D cellular automata |
| Langton's Ant | `2` | Turmite with emergent highway behavior |
| Hexagonal Grid | `3` | 6-neighbor topology with B2/S34 rule |
| Wireworld | `4` | 4-state circuit simulation (electron heads/tails) |
| Cyclic CA | `U` | N-state cyclic automaton with spiral waves |
| Hodgepodge Machine | `~` | BZ-like excitable medium |
| Lenia | `7` | Continuous smooth-kernel cellular automaton |
| Turmites | `Q` | Generalized 2D Turing machines |
| 3D Game of Life | `Ctrl+Shift+L` | 20^3 voxel grid with volumetric ray casting |

### Particle & Swarm

| Mode | Key | Description |
|------|-----|-------------|
| Falling Sand | `5` | Multi-material particle physics sandbox |
| Boids Flocking | `9` | Reynolds separation/alignment/cohesion |
| Particle Life | `0` | N-body attraction/repulsion matrix |
| Physarum Slime Mold | `8` | Agent-based trail-following network |
| Ant Colony | `A` | Pheromone-based foraging |
| N-Body Gravity | `Y` | Velocity Verlet orbital mechanics |

### Physics & Waves

| Mode | Key | Description |
|------|-----|-------------|
| 2D Wave Equation | `!` | Finite-difference membrane with reflection/absorption/wrap |
| Ising Model | `#` | Metropolis spin dynamics with phase transition |
| Kuramoto Oscillators | `(` | Phase synchronization on a lattice |
| Spiking Neural Net | `` ` `` | Izhikevich neuron grid with synaptic coupling |
| Double Pendulum | `Ctrl+P` | RK4 integration with trajectory trails |
| Pendulum Wave | `Ctrl+Shift+P` | SHM with analytically computed realignment |

### Fluid Dynamics

| Mode | Key | Description |
|------|-----|-------------|
| Lattice Boltzmann | `F` | D2Q9 LBM with BGK collision |
| Navier-Stokes | `Ctrl+D` | Stable fluids with semi-Lagrangian advection |
| SPH Fluid | `Ctrl+A` | Particle-based Lagrangian hydrodynamics |
| Rayleigh-Benard | `Ctrl+R` | Buoyancy-driven convection rolls |
| Smoke & Fire | `\` | Combustion with advection and turbulence |
| Cloth Simulation | `'` | Verlet integration with spring constraints |

### Chemical & Biological

| Mode | Key | Description |
|------|-----|-------------|
| Reaction-Diffusion | `6` | Gray-Scott two-chemical pattern formation |
| BZ Reaction | `` ` `` | 3-variable Oregonator spiral waves |
| Chemotaxis | `{` | Bacterial colony morphogenesis |
| Epidemic SIR | `E` | Distance-weighted disease spread |
| Forest Fire | `O` | Drossel-Schwabl self-organized criticality |
| Predator-Prey | `J` | Lotka-Volterra population dynamics |

### Game Theory & Social

| Mode | Key | Description |
|------|-----|-------------|
| Prisoner's Dilemma | `@` | Spatial imitation dynamics |
| Schelling Segregation | `K` | Preference-driven macro-segregation |
| Rock-Paper-Scissors | `&` | Cyclic dominance with spiral waves |

### Fractals & Chaos

| Mode | Key | Description |
|------|-----|-------------|
| Mandelbrot/Julia | `Ctrl+B` | Interactive fractal explorer with zoom |
| Strange Attractors | `\|` | 6 chaotic 3D ODE systems with density heatmap |
| L-System Plants | `/` | Lindenmayer grammar with turtle graphics |
| IFS Fractals | `Ctrl+G` | Iterated function system chaos game |

### Procedural & Computational

| Mode | Key | Description |
|------|-----|-------------|
| Sorting Visualizer | `Ctrl+Shift+X` | 6 algorithms with animated bar charts |
| Quantum Circuit | `Ctrl+Q` | State vector simulator with Bloch spheres |
| Tierra | `Ctrl+Shift+T` | Self-replicating assembly programs in shared memory |
| Wave Function Collapse | `X` | Entropy-driven procedural generation |
| Maze Generation | `L` | 3 generators + 4 solvers animated step-by-step |
| Fourier Epicycles | `Ctrl+Shift+F` | DFT decomposition into spinning circles |

### Complex Simulations

| Mode | Key | Description |
|------|-----|-------------|
| Ecosystem Evolution | — | Landscape-scale macro-evolution with speciation |
| Civilization | — | Macro-historical simulation with emergent cultures |
| Coral Reef | — | Multi-species marine ecosystem with bleaching |
| Stock Market | — | Agent-based bubbles, crashes, and price discovery |
| Immune System | — | Adaptive immune response with pathogen arms race |
| Primordial Soup | — | Abiogenesis from chemistry to biology |

### Meta Modes

| Mode | Key | Description |
|------|-----|-------------|
| Screensaver | `Ctrl+Shift+D` | Auto-cycling demo reel with crossfade transitions |
| Layer Compositing | — | Stack 2-4 simulations with blend modes |
| Simulation Portal | — | Spatial gateways connecting two simulations |
| Genome Sharing | — | Encode/decode simulation configs as shareable seeds |
| Mashup Mode | — | Layer two simulations on the same grid |
| Recording & Export | `G` | Capture as animated GIF or text flipbook |

## Game of Life Controls

These controls apply in the default Game of Life mode:

| Key | Action |
|-----|--------|
| `Space` | Play / pause |
| `n` / `.` | Step one generation |
| `+` / `-` | Adjust speed |
| Arrow keys / `hjkl` | Move cursor |
| `e` | Toggle cell |
| `d` / `x` | Draw / erase mode |
| `p` | Pattern library |
| `t` | Stamp pattern at cursor |
| `r` | Randomize grid |
| `c` | Clear grid |
| `R` | Rule editor |
| `i` | Import RLE file |
| `s` / `o` | Save / load state |
| `u` | Undo (rewind one generation) |
| `[` / `]` | Scrub timeline +-10 steps |
| `b` / `B` | Bookmark / bookmark list |
| `H` | Heatmap overlay |
| `F` | Pattern recognition |
| `V` | Split-screen comparison |
| `I` | 3D isometric view |
| `G` | GIF recording |
| `m` | Mode browser |
| `?` / `h` | Help screen |
| `q` | Quit |

## Project Structure

```
life.py            # Convenience entry point
life/              # Main package
  __init__.py      # Package init and main() export
  __main__.py      # python -m life support
  app.py           # Core application class
  grid.py          # Grid / world management
  colors.py        # Terminal color definitions
  constants.py     # Shared constants
  patterns.py      # Built-in pattern library
  registry.py      # Mode registry and categories
  rules.py         # CA rule engine
  sound.py         # Audio synthesis
  multiplayer.py   # TCP multiplayer
  utils.py         # Shared utilities
  modes/           # Simulation mode modules
    __init__.py
    boids.py
    quantum_circuit.py
    ...
```

## License

[MIT](LICENSE) — Changkun Ou
