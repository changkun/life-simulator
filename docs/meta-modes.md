# Meta Modes

Tools for exploring, combining, evolving, and recording simulations — the laboratory around the laboratory.

---

## Compare Rules

**Source:** `life/modes/compare_rules.py`

### Background

Compare Rules displays two cellular automata side by side, each running a different B/S ruleset on the same initial configuration. This makes it easy to see how small rule changes produce dramatically different long-term behavior. Population sparklines beneath each panel give an at-a-glance view of growth trajectories.

### How it works

The screen is split vertically at the midpoint. Both grids share a viewport origin (scroll position), so the same spatial region is visible in each panel. The left panel uses the current rule. The right panel uses a second rule that you pick from the rule presets or type as a custom B/S string with `/`. Both grids start as copies of the current pattern. Each generation, both step independently and each records its own population history, drawn as a Unicode sparkline.

### What to explore

- Compare Conway's Life (B3/S23) against HighLife (B36/S23) to see replicator emergence.
- Try a rule that dies quickly on the left against one that fills the grid on the right.
- Watch population sparklines diverge or converge over hundreds of generations.

---

## Multi-Rule Race

**Source:** `life/modes/race_rules.py`

### Background

Multi-Rule Race pits 2--4 cellular automata rulesets against each other. All grids start as copies of the current pattern and run for a set number of generations. A live scoreboard tracks population, peak population, oscillation period, extinction generation, and a final score.

### How it works

In the rule menu, `Space` toggles a preset, `/` adds a custom rule, `g` sets the duration (10--10,000 generations), and `Enter` starts the race. Grids are tiled 1x2 for two rules and 2x2 for three or four. Each grid runs independently with its own B/S rule, and state hashes detect cycles. The race ends when the duration expires, even if every rule is still alive. The final score is the end population, plus a survival bonus (the full duration, or the generations survived before extinction), plus 50 for an oscillation with period above 1, plus half the peak population. A progress bar shows elapsed generations against the duration.

### What to explore

- Race explosive rules (Seeds B2/S) against stable ones (Life B3/S23) to see who survives.
- Set a long duration (5000+ generations) to discover which rules have staying power.
- Watch the oscillation column: the scoreboard reports a period once a grid repeats a state.

---

## Puzzle / Challenge

**Source:** `life/modes/puzzle.py`

### Background

Puzzle mode presents a series of cellular automata challenges: build a still life, construct an oscillator with a minimum period, reach a target population, escape a bounding box, cause extinction, or survive for a given number of generations. Each puzzle limits how many cells you may place.

### How it works

The mode has three phases: *planning* (place cells on a blank grid with draw/erase tools), *running* (the simulation advances while win/loss conditions are checked each step), and *result* (score displayed). Win detection uses state-hash cycle detection for still-life and oscillator puzzles, population thresholds for growth puzzles, and bounding-box geometry for escape puzzles. Scoring rewards efficiency: `score = 100 * max_cells / cells_used + speed_bonus`, capped at 999. The speed bonus (up to 50) applies to oscillator, population, escape and extinction puzzles. In planning, `e` toggles a cell, `d` and `x` switch to draw and erase, `c` clears, and `Enter` runs.

### What to explore

- The "escape box" puzzle type: your pattern must send live cells outside a dotted boundary.
- Try to beat your best score by using fewer cells. Hints are available with `?`.
- Attempt the extinction puzzles, which require building patterns that self-destruct.

---

## Evolution / GA

**Source:** `life/modes/evolution.py`

### Background

Evolution mode uses a genetic algorithm to breed Life-like rulesets. A population of candidate B/S rules runs in parallel on small grids. After a set number of generations, each rule is scored on longevity, population stability, diversity, and average population. The top performers carry over and reproduce through crossover and mutation.

### How it works

```
for each generation:
    for each individual in population:
        initialize 30x40 grid with 20% random fill
        simulate for grid_gens steps
        record population history
    score all individuals (weighted sum of 4 fitness components)
    sort by fitness; keep top elite_count as parents
    breed next generation: crossover pairs of parents, mutate offspring
```

Crossover is uniform per digit: for each neighbor count 0--8, the child takes the birth and survival bits from a randomly chosen parent. Mutation flips individual digits at the set rate. The first generation uses random rules. Four fitness modes (balanced, longevity, diversity, population) reweight the scoring components: balanced weights them equally, and each other mode triples one component. After scoring, a ranked scoreboard lists the rules. `Space` plays or pauses and `n` steps; once the generation is scored, either one breeds the next. `s` skips to scoring, `f` cycles the fitness mode, `m` sets the mutation rate, and `<`/`>` change the speed.

### What to explore

- Set fitness to "diversity" and watch the GA discover chaotic, visually rich rules.
- Once a generation is scored, pick a rule with the arrow keys and adopt it into the main simulator with `a` to explore it at full resolution.
- Increase mutation rate to 30%+ for more exploration; decrease to 5% for refinement.

### References

- Holland, J. H. (1975). *Adaptation in Natural and Artificial Systems*. University of Michigan Press. https://doi.org/10.7551/mitpress/1090.001.0001

---

## Screensaver / Demo Reel

**Source:** `life/modes/screensaver.py`

### Background

Screensaver mode cycles through the simulation modes, running each for a set interval before moving to the next. It works as an unattended demo reel.

### How it works

A playlist is built from the mode registry: all modes, your favorites, or one category, in order or shuffled. Only simulations that the main loop dispatches by table are played, so Game of Life, the screensaver itself, toggles such as Topology, and interactive meta modes are skipped. To start each mode, the screensaver tries a fixed list of strategies (press Enter on its menu, call its init function, try common preset names). It never presses arbitrary menu items, so it cannot trigger saves or deletes. A mode that none of these start stays in its menu. Transitions use a dissolve effect: random block characters are drawn over the screen at decreasing density. An overlay box with the mode name, category and playlist position shows for 3 seconds, then fades. A status bar always shows the countdown to the next mode. The interval is 5 to 120 seconds, adjusted with `+`/`-`.

### What to explore

- Use "All Modes -- Shuffle" for a randomized tour of every simulation.
- Press `i` to keep the overlay box on screen.
- Pause with `Space` to linger on an interesting simulation, then resume cycling.
- Skip with `n` or `p` (or the arrow keys).

---

## Parameter Space Explorer

**Source:** `life/modes/param_explorer.py`

### Background

Parameter Space Explorer displays a grid of live simulation thumbnails, each running the same model with linearly interpolated parameter values across two axes. By selecting an interesting tile and pressing Enter, you zoom into a neighborhood of that parameter combination, iteratively narrowing in on compelling regions of the parameter landscape.

### How it works

The explorer supports two engines: Gray-Scott Reaction-Diffusion (feed vs. kill rate) and Smooth Life, a simplified continuous CA with a Gaussian growth function (mu vs. sigma). For an NxM tile grid, parameter values are evenly spaced across the visible range on each axis. Each tile runs its own independent mini-simulation. Zooming in with `Enter` shows 40% of the current span on each axis, centered on the selected tile's parameters; `z` or `-` zooms out to 150% of the span around the current center. Preset bookmarks jump to known interesting parameter combinations.

### What to explore

- In Gray-Scott mode, zoom into the boundary between "spots" and "worms" around feed=0.04, kill=0.063.
- Use `p` to cycle through the named presets. Gray-Scott has Coral Growth, Mitosis, Fingerprints, Spots, Worms, Spirals, Maze and Chaos; Smooth Life has Orbium, Geminium, Stable Blobs, Oscillators and Chaos.
- Raise steps per frame with `+` (lower with `_`, range 1--10) to speed up slow-forming patterns.
- Press `r` to return to the full range and `R` or `m` to go back to the engine menu.

---

## Evolution Lab

**Source:** `life/modes/evolution_lab.py`

### Background

Evolution Lab extends the basic Evolution mode with analytics-driven fitness scoring (Shannon entropy, symmetry, stability, longevity, diversity), multi-state genomes (Moore and von Neumann neighborhoods, 2--5 cell states), manual "favorite" protection from culling, and save/load of discovered organisms.

### How it works

Genomes encode birth/survival sets, neighborhood type, and state count. Fitness is a weighted sum of five metrics, with weight presets balanced, beauty, chaos, complexity, and stability. The beauty preset, for example, weights symmetry at 3x. Stability is a proxy based on how much the population varies over the last 30 generations. Favorites are immune to culling and always parent the next generation. The breeding pipeline is: sort by fitness (favorites first), select elite parents, fill remaining slots with crossover and mutation. Organisms can be saved to `~/.life_saves/evolution_lab.json` and reloaded as seeds for future runs.

### What to explore

- Use the "beauty" fitness preset to evolve rules that produce symmetric, visually striking patterns.
- Favorite a promising organism (`Enter` or `f` on its tile) and watch its traits propagate through subsequent generations. `a` adopts the organism under the cursor into the main simulator.
- Save an organism with `s`, then restart with "START (From Saved)" to continue evolving from your best discoveries.

---

## Evolutionary Playground

**Source:** `life/modes/evo_playground.py`

### Background

Evolutionary Playground is a human-in-the-loop genetic algorithm where you are the fitness function. A grid of live simulations runs with different randomly generated CA rules. You watch them, select the most interesting ones as parents, and press `b` to breed the next generation through crossover and mutation.

### How it works

The population fills the terminal as a tiled grid of mini-simulations. Genomes include birth/survival sets, neighborhood type (Moore, von Neumann, or hexagonal), and multi-state cell counts. Selection is manual: navigate with the arrow keys, press `Enter` to toggle a tile as a parent (`A` toggles all). Breeding requires at least 2 parents. Children inherit traits via uniform crossover and per-digit mutation. The mutation rate is set in the start menu. `S` saves the rule under the cursor to `~/.life_saves/evolved_rules.json`; `a` adopts it into the main simulator; `r` starts a new random population.

### What to explore

- Select parents with contrasting behaviors (one chaotic, one stable) to see what crossover produces.
- Increase mutation rate to 25%+ for more novelty per generation.
- After several generations of selective breeding, adopt the best rule into the main Life grid.

---

## Live Rule Editor

**Source:** `life/modes/rule_editor.py`

### Background

Live Rule Editor lets you type Python expressions that define custom cellular automaton birth and survival rules. The expressions run on a grid as you edit them. Variables available include `neighbors` (list of 8 neighbor states), `age`, `x`, `y`, `step`, and `random()`.

### How it works

Birth and survival expressions are compiled with Python's `compile()` into code objects, then evaluated per-cell each generation using a restricted `eval()` sandbox (no `__builtins__`). The sandbox exposes `sum`, `len`, `min`, `max`, `any`, `all`, `abs`, `int`, `float`, `math`, and `random`. Expressions like `sum(neighbors) == 3 and age < 10` let you create age-dependent rules, positional biases, or stochastic behavior. `Enter` edits the selected expression, `Tab` switches fields, and `i` imports a rule from Evolutionary Playground. Ten starter snippets are provided. `+`/`-` change the speed, `r` randomizes the grid, `c` clears it, `S` saves the rule and `m` returns to the menu. Rules are saved to and loaded from `~/.life_saves/custom_rules.json`.

### What to explore

- Try `sum(neighbors) == 3 or (sum(neighbors) == 2 and random() < 0.05)` for stochastic Life.
- Create position-dependent rules: `sum(neighbors) == 3 and (x + y) % 3 == 0`.
- Press `a` to translate your expression into a standard B/S rule and apply it to the main grid. This works only for rules that depend on the neighbor count alone.

---

## Simulation Mashup

**Source:** `life/modes/mashup.py`

### Background

Simulation Mashup layers two different simulation engines on the same grid with emergent coupling. Each engine's density field influences the other: boids steer toward wave gradients, fire ignition probability increases near dense Life populations, Ising spin flips are biased by reaction-diffusion concentrations, and so on.

### How it works

Eight mini-simulation engines are implemented (Game of Life, Wave Equation, Reaction-Diffusion, Forest Fire, Boids Flocking, Ising Model, Rock-Paper-Scissors, Physarum Slime). The menu offers eight preset pairs plus a custom pick. Each exposes `init`, `step(state, other_density, coupling_strength)`, and `density` functions. On each tick, simulation A receives B's density map as a coupling input and vice versa. The coupling strength (0.0--1.0, default 0.5) controls how strongly each simulation influences the other. Rendering overlays both density fields with color-coding: cyan for A, red for B, magenta for overlap.

### What to explore

- "Boids + Wave Equation": watch flocking agents create ripples and steer along wave gradients.
- Adjust coupling with `+`/`-` (steps of 0.05) to find the sweet spot between independence and lock-in.
- Press `0` to set coupling to 0 and run both simulations independently. Press `5` to return to 0.5.

---

## Battle Royale

**Source:** `life/modes/battle_royale.py`

### Background

Battle Royale places four cellular automata factions on a shared grid, each with its own B/S rule. Factions compete for territory through birth, survival, and conquest mechanics. The last faction standing wins.

### How it works

The grid tracks per-cell ownership (faction index or neutral) and age. Each generation: an empty cell is born for the faction whose birth set matches its neighbor count, and the faction with more neighbors wins (ties are random). Alive cells check survival using their faction's survival set. A surviving cell is conquered when enemy neighbors outnumber its own faction's by more than 1 and the strongest enemy faction has 3 or more neighbors. Territory percentages are displayed in a live scoreboard with a stacked bar chart. Eight factions exist (Life, HighLife, Day&Night, Seeds, Morley, Maze, Amoeba, Diamoeba); four fight in each battle.

### What to explore

- "Classic Showdown" pits Life, HighLife, Day&Night, and Seeds in a four-way battle. The other presets are "Aggressive Mix", "Territorial War" and "Survival of the Fittest".
- Watch Seeds (B2/S) explode quickly but burn out, while Life slowly consolidates territory.
- Try "Custom Battle..." to pick any 4 of the 8 factions.

---

## Simulation Portal

**Source:** `life/modes/portal.py`

### Background

Simulation Portal splits the screen into two halves (vertically or horizontally), each running a different simulation engine from the mashup module. Density bleeds across the seam to a set depth, so each simulation feeds the other at the interface.

### How it works

Boundary influence is computed by taking the edge columns (or rows) of one simulation's density field, fading them linearly with distance from the seam, and injecting them into the other simulation's coupling input. A's right edge feeds B's left edge, and B's left edge feeds A's right edge. The "bleed" parameter (1--20 cells, default 3) sets how deep the cross-talk extends. Coupling (0.0--1.0, default 0.5) scales its strength. Near-seam cells are drawn in magenta to show the cross-talk zone.

### What to explore

- Toggle orientation with `o` to see how vertical vs. horizontal seams change the interaction.
- Increase bleed depth with `b` (decrease with `B`) to let the simulations influence each other more deeply.
- Adjust coupling with `+`/`-`.
- Try "Wave ↔ Forest Fire": wave amplitude ignites fire at the boundary.

---

## Split-Screen Dual Simulation

**Source:** `life/modes/split_screen.py`

### Background

Split-Screen Dual Simulation runs any two of the eight mini-simulation engines side by side with optional bidirectional coupling. Each pane has its own state, generation counter, and density grid. Observatory tiles 2--9 viewports with no coupling, and Mashup couples two engines on one grid. Split-Screen sits between them: coupling runs from fully independent (0%) to fully coupled (100%).

### How it works

The terminal is split vertically at the midpoint by a `│` divider. Each pane wraps one of the eight engines from the mashup module (Game of Life, Wave, Reaction-Diffusion, Forest Fire, Boids, Ising, Rock-Paper-Scissors, Physarum).

Coupling (`split_coupling`, 0.0--1.0) starts at 0.0. Above 0, each engine receives the *other* pane's density map as input before stepping. Both densities are taken before either pane steps, so neither has priority. The divider then shows a `⇄` arrow at its center, and the title bar shows the coupling percentage.

The menu offers 8 preset pairings (such as "Game of Life vs Lenia-style RD" and "Boids vs Physarum") plus a two-step custom picker for the left and right engines. `Tab` moves focus between panes, `s` swaps the two simulations, and `r` resets only the focused pane.

### What to explore

- Compare "Game of Life vs Boids" to see grid-based discrete dynamics next to free-roaming agents.
- Pair "Ising vs Rock-Paper-Scissors" for two spatial competition models.
- Reset one pane with `r` while the other runs to compare a fresh state with an evolved one.
- Press `c` to cycle coupling (0% → 20% → 50% → 80% → 100% → 0%) and watch how each pane responds to the other.
- Fine-tune coupling with `+`/`-` (5% steps).
- Try "Reaction-Diffusion vs Physarum" at high coupling.

---

## Simulation Observatory

**Source:** `life/modes/observatory.py`

### Background

Simulation Observatory runs 2--9 independent simulations simultaneously in a tiled layout. Unlike Mashup, there is no coupling between viewports. The focus is on visual comparison: press `1`--`9` to expand a viewport to full screen, then press `0` to return to the grid view.

### How it works

Viewports are arranged in auto-calculated grid layouts (1x2, 2x2, 2x3, or 3x3) based on the number of simulations selected. Each viewport wraps one of the eight mini-simulation engines from the mashup module. All viewports step in lockstep each frame. The presets are "Fluid Trio", "Chaos Theory", "Micro vs Macro", "Nature's Patterns", and "Everything"; a custom option lets you pick the layout and engines.

### What to explore

- The "Everything" preset runs all 8 engines, plus a second Game of Life, in a 3x3 grid.
- Focus on the Physarum viewport (`8`) to see trail networks form in a larger view. The focused viewport draws the same grid bigger, not at a higher resolution.
- Compare Wave, RD, and Physarum side by side in the "Fluid Trio" preset.

---

## Layer Compositing

**Source:** `life/modes/layer_compositing.py`

### Background

Layer Compositing stacks 2--4 independent simulations as transparent layers with configurable blend modes (add, XOR, mask, multiply, screen) and per-layer opacity and tick rate. The result is a single composited viewport.

### How it works

Each layer wraps an independent simulation engine with no coupling. On each frame, layers whose `generation % tick_mult == 0` are stepped, so a higher tick multiplier runs a layer slower. The compositing engine iterates over every cell, applying blend functions sequentially from the base layer upward. The base layer has no blend mode:

```
for each cell (r, c):
    val = layer[0].density * layer[0].opacity
    for layer in layers[1:]:
        val = blend_fn(val, layer.density * layer.opacity)
    dominant_layer = argmax(layer_contributions)
```

The dominant layer determines the cell's display color. `screen` is an inverse multiply that lightens. `mask` keeps the value below it only where the layer's density exceeds 0.15.

### What to explore

- "Breathing Shapes": Reaction-Diffusion masked by Game of Life.
- Use `Tab` to cycle focus between layers, then `+`/`-` to adjust opacity in real time.
- Press `t`/`T` to slow down or speed up the focused layer.
- Press `b` to cycle the blend mode of the focused layer (the base layer always uses Add).
- Press `r` to reset all layers and `R` to return to the menu. A custom stack holds 2--4 layers.

---

## Cinematic Demo Reel

**Source:** `life/modes/cinematic_demo.py`

### Background

Cinematic Demo Reel is an autonomous director that sequences through simulation engines with smooth crossfade transitions, animated camera moves (zoom, pan), and title card overlays. It plays like a screensaver but with deliberate cinematographic intent.

### How it works

Each "act" specifies a simulation engine, duration (10--14 seconds), camera path, and color theme. Camera parameters (zoom, pan_x, pan_y) are interpolated with a smooth ease-in-out function: `t = t^2 * (3 - 2t)`. The view window maps screen coordinates to a subregion of the simulation grid based on the current zoom and pan. Crossfade transitions blend the previous act's density field with the new one over 1.5 seconds. Title cards display the act name for 3 seconds with a 1-second fade-out. Five curated playlists are provided, including a "Random Director" mode that shuffles acts.

### What to explore

- "The Grand Tour" visits all 8 engines in sequence with varied camera paths.
- "Fluid Dreams" focuses on Wave, Reaction-Diffusion, and Physarum for a meditative experience.
- Press `n`/`p` to skip forward or backward through acts manually.

---

## Topology Mode

**Source:** `life/modes/topology.py`

### Background

Topology Mode changes the grid's boundary conditions, transforming the surface on which any simulation runs. Five topologies are supported: plane (hard edges), torus (both axes wrap, the default), Klein bottle (columns wrap; rows wrap with a horizontal flip), Mobius strip (columns wrap with a vertical flip; rows have hard edges), and projective plane (both axes wrap with flips).

### How it works

The Grid class implements neighbor lookups that consult the `topology` attribute. For twist-wrapping topologies, when a coordinate wraps past an edge, the opposite axis is mirrored: on a Klein bottle, a cell going off the top row reappears at the bottom with its column reflected (`c' = cols - 1 - c`). Pick Topology Mode in the mode browser to move to the next topology; each pick cycles once (Ctrl+W saves a snapshot). Outside the torus, the mode draws a label in the top-right corner and edge indicators: thin lines for walls, double lines for seamless wraps, and wavy lines for twist wraps. Corner markers and midpoint arrows mark twisted edges.

### What to explore

- Run a glider on a Mobius strip and watch it return mirror-reversed.
- Compare pattern evolution on a torus and a Klein bottle.
- Try the projective plane with a symmetric initial pattern to see how the flips affect symmetry.

---

## Visual FX Pipeline

**Source:** `life/modes/post_processing.py`

### Background

The Visual FX Pipeline provides six stackable post-processing effects (scanlines, bloom, motion trails, edge detection, color cycling, CRT distortion) that layer on top of any active simulation mode. Effects compose freely and operate entirely in terminal character space.

### How it works

Pick Visual FX Pipeline in the mode browser to open the effects menu, where `1`--`6` toggle effects and `Esc` closes it (Ctrl+V toggles the sparkline HUD). Effects are applied after the simulation's draw call, operating directly on the curses screen buffer via `inch()` and `chgat()`. Scanlines dim every other row. Bloom makes occupied cells bold and paints dim glow characters in the four adjacent empty cells. Trails keep a buffer of past frame occupancy maps; older frames are drawn with progressively lighter block characters. Edge detection builds an occupancy bitmap and erases interior cells (those with all four cardinal neighbors occupied). Color cycling rotates color pair indices modulo 5 based on a frame counter. CRT adds vignette darkening, scanlines, and a rounded bezel border.

### What to explore

- Enable bloom + trails together for a neon glow effect on any simulation.
- Edge detection transforms dense patterns into outline-only contour maps.
- CRT distortion makes any simulation look like it is running on a vintage monitor.

---

## Recording & Export

**Source:** `life/modes/recording.py`

### Background

Recording & Export captures terminal frames during any simulation and exports them as asciinema v2 `.cast` files (playable in any terminal or embeddable on the web) or plain-text flipbooks. Ctrl+X starts and stops the capture.

### How it works

When recording is active, each frame the system reads every cell of the curses window via `inch()`, groups runs of identical attributes, and emits ANSI escape sequences for color and style changes. A parallel plain-text capture strips all ANSI codes. Frame capture respects an FPS budget (default 10 fps) and a safety cap of 3000 frames. The `.cast` exporter writes asciinema v2 format: a JSON header line followed by `[elapsed, "o", data]` event lines. A blinking red REC indicator with the frame count and elapsed time is drawn in the top-right corner during recording. Stopping opens an export menu: `1` for `.cast`, `2` for `.txt`, `3` for both, and `d`, `q` or `Esc` to discard. `Up`/`Down` and `Enter` also pick a format. Each cell is read with `inch()`, which keeps only the low 8 bits, so non-ASCII glyphs are not recorded faithfully.

### What to explore

- Record a Battle Royale match and play it back with `asciinema play` on the saved `.cast` file.
- Export both formats to get a web-embeddable `.cast` and a searchable `.txt`.
- Recordings are saved to `~/.life_saves/` as `recording_<timestamp>.cast` or `.txt`.

---

## Scripting & Choreography

**Source:** `life/modes/scripting.py`

### Background

Scripting & Choreography provides a line-based DSL (`.show` files) for orchestrating timed sequences of mode transitions, parameter sweeps, visual effect toggles, speed changes, and labels. Think of it as a programmable director for the entire simulation platform.

### How it works

The DSL parser tokenizes each line into commands: `mode`, `wait`, `effect`, `topology`, `set`, `sweep`, `transition`, `speed`, `color`, `label`, and `loop`. The execution engine maintains a program counter and processes commands sequentially until it hits a blocking command (`wait` or `sweep`). Sweeps interpolate a parameter over time using smoothstep easing; a sweep changes only `speed`, and `set` accepts `speed`, plus `feed` and `kill` for Reaction-Diffusion. Crossfade transitions blend the previous simulation's density field with the new one. The `loop` command resets the program counter to zero. Five built-in example scripts are included. Users can also load `.show` files from disk.

### What to explore

- Run "Full Tour" for a scripted presentation of all 8 engines with effects and transitions.
- Write your own `.show` file to create a custom demo with precise timing and parameter control.
- Press `s` during playback to view the script source with the current instruction highlighted.

---

## Neural Cellular Automata

**Source:** `life/modes/neural_ca.py`

### Background

Neural Cellular Automata replaces lookup-table rules with per-cell neural networks. Each cell perceives its neighborhood through Sobel-like convolution kernels, processes the signal through a two-layer neural network (perception to hidden via ReLU, hidden to state update via residual connection), and updates its multi-channel state. The network weights are trained via Evolution Strategies to reproduce a target pattern from a small seed.

### How it works

```
perception = [identity, sobel_x, sobel_y] * 3 channels = 9 inputs
hidden = ReLU(W1 @ perception + b1)        # 8 neurons
update = W2 @ hidden + b2                   # 3 channels
new_state = old_state + update              # residual
alive_mask: cell dies if no neighbor has alpha > 0.1
```

Training uses antithetic Evolution Strategies: generate N/2 random perturbations (and their negatives), grow each candidate from seed for the set number of grow steps (default 20), compute the loss against the target, and estimate a gradient for the weight update. The system has 107 learnable parameters. Press `p` to cycle the targets (circle, square, diamond, cross, ring, heart, custom); `custom` appears once you have drawn one.

### What to explore

- Train on the "heart" target and watch the seed grow into a heart shape over 50+ training generations.
- Press `g` to regrow from seed with current weights to test robustness.
- Draw a custom target with `d` (arrows move, `Space` paints a cell, `f` paints a 3×3 block, `e` switches between painting and erasing, `c` clears, `Enter` or `q` finishes), then press `t` to train.

### References

- Mordvintsev, A. et al. (2020). "Growing Neural Cellular Automata." *Distill*. https://distill.pub/2020/growing-ca/

---

## Timeline Branching

**Source:** `life/modes/timeline_branch.py`

### Background

Timeline Branching lets you fork an alternate timeline from any point in a simulation's history. Scrub back through the history (`u` steps back, `[` and `]` jump by 10), then press Ctrl+F to fork the grid state into a branch (optionally with a different rule), and watch both timelines evolve side by side in a split view with a live divergence metric.

### How it works

Forking copies the primary grid (cells, rules, topology) into a secondary grid. Both grids advance in lockstep from the fork point. The split view renders them side by side with dual sparklines and a divergence bar. Divergence is the share of cells that are alive in one grid and dead in the other: `divergence = count(alive_a != alive_b) / total_cells * 100%`. The fork menu offers two options: "Fork with same rules" (to study sensitivity to initial conditions) or "Fork with different rule" (to compare rule behavior from identical starting states). The fork-point generation and rule labels are displayed in a status bar. Ctrl+F opens the fork menu only while you are scrubbed back; without a scrubbed frame the key goes to the active mode. Ctrl+F or `q` exits the split view and returns to the primary timeline.

### What to explore

- Fork from a complex state and apply a different rule to the branch to see how quickly they diverge.
- Fork with the same rule to demonstrate sensitivity to initial conditions (chaos in CA dynamics).
- Use the divergence percentage to quantify how "far apart" two timelines have drifted.

---

## Ancestor Search

**Source:** `life/modes/ancestor_search.py`

### Background

Ancestor Search reverse-engineers cellular automata: given a target pattern, it searches backwards in time to find predecessor states that evolve into the target after one CA step. It can also detect Garden of Eden patterns -- configurations with no possible predecessor under the current rule.

### How it works

The search engine uses simulated annealing with stochastic restarts. Candidates are flat binary grids. Fitness is the count of cells matching the target after one forward CA step (perfect = all cells match). Each generation applies adaptive-rate mutations and occasional crossover with the global best. Simulated annealing also accepts a worse candidate with probability `exp(delta / temperature)`, where `delta` is negative and temperature cools by 0.3% per generation. Every 50 generations without a perfect solution counts as a restart: the worst half of the candidates is replaced and the temperature partly resets. After 200 restarts with no solution, a local search (500 multi-flip attempts) runs. If it also fails, the target is reported as a probable Garden of Eden; this is a heuristic, not a proof. The display shows up to three panels, depending on terminal width: the target, the best ancestor, and either a found solution or the best ancestor after one step.

### What to explore

- Search for ancestors of the "glider" pattern: multiple valid predecessors exist.
- Try the "r-pentomino" (a methuselah): finding its ancestors reveals the complexity of backward search.
- Draw a custom pattern and check whether it is a Garden of Eden -- a state that can never arise naturally.

---

## Self-Modifying Rules CA

**Source:** `life/modes/self_modifying_rules.py`

### Background

Self-Modifying Rules creates a cellular automaton where each living cell carries its own rule DNA, a pair of 9-bit bitstrings (birth and survival). When a cell is born, it inherits a possibly mutated rule from the majority of its live neighbors. This produces emergent speciation, ecological niches, and evolutionary arms races without any external fitness function.

### How it works

Each cell's genome is a `(birth_bits, survival_bits)` pair. Alive cells check survival using their own genome's survival set. Dead cells use the birth set of the majority genome among their live neighbors (ties are random). A newborn cell inherits that genome. With the mutation probability, the child's bits are flipped at random (15% per bit). Species are identified by unique genomes and color-coded by hashing the genome into 8 terminal colors. The info panel tracks species count, births, deaths, total mutations, and displays sparklines for diversity and population over time. Eight presets are provided, ranging from "Life vs HighLife" (two-species competition) to "Cambrian Explosion" (8 random seed species) to "Blank Canvas" (every cell gets a random genome).

### What to explore

- "Mutation Storm" starts with a single Life rule but high mutation creates rapid speciation -- watch dozens of species emerge.
- Adjust mutation rate with `+`/`-` in real time: low rates favor stable ecosystems, high rates cause constant turnover.
- The species panel shows which B/S rules are currently winning the ecological competition.

---

## Long-Exposure Photography

**Source:** `life/modes/long_exposure.py`

### Background

Long-Exposure Photography composites hundreds of simulation frames into a single artistic still image, like astrophotography for cellular automata. Where Ghost Trail shows fading echoes of the last few frames, Long Exposure accumulates an entire time window (10–1000 generations) into a permanent composite that reveals the full trajectory, flow patterns, and density structure of any simulation.

### How it works

When capture is active, every rendered frame is accumulated into a per-pixel buffer that tracks seven values: total R/G/B (for additive and average blending), hit count (how many frames occupied this pixel), and peak R/G/B (for max blending). The system captures from both the truecolor buffer (`tc_buf`) and the curses screen, so it works with every mode regardless of its rendering path.

When the exposure window is reached (or the user manually freezes), the accumulation buffer is composited into a final image using one of three blend modes:

- **Additive**: base color is the per-pixel average, scaled by a density factor (0.3 + 0.7 × density) with a luminance boost (up to +80 RGB) for high-traffic areas. This creates glowing trails where activity was concentrated.
- **Max**: each pixel shows the brightest color it ever displayed during the exposure. Good for capturing peak moments and transient flashes.
- **Average**: simple arithmetic mean of all frames. Reveals the steady-state palette and suppresses transient noise.

The frozen composite renders as a full-screen truecolor image using density-mapped glyphs (`· ░ ▒ ▓ █`), creating a topographic density map where glyph weight corresponds to how frequently each pixel was active. Very low-density pixels (< 1% of max) are rendered as faint dots with dimmed colors.

Export produces two files: a JSON file containing per-pixel coordinates, RGB values, and density fractions (machine-readable, suitable for further processing), and an ANSI art `.ans` file with embedded 24-bit color escapes (viewable with `cat` in any truecolor terminal).

Ctrl+E starts and stops a capture; stopping freezes the composite. Ctrl+] exports it. Ctrl+F (freeze or unfreeze), `[` and `]` (window length, in steps of 50) and `{` and `}` (blend mode) act only while a capture is running or a composite exists. Otherwise those keys go to the active mode or the launchers (Ctrl+F Fireworks, `{` Chemotaxis, `}` MHD Plasma). While the spectrum overlay is on, it takes `{` and `}` first.

### What to explore

- Capture a 500-frame exposure of Boids or N-Body to see orbital trajectories materialize as luminous trails.
- Use **max** blend on Reaction-Diffusion to capture the full wavefront propagation in a single image.
- Try **average** blend on a chaotic rule (Seeds, B2/S) to reveal the statistical density structure.
- Combine with Ghost Trail active for both real-time echoes and long-term accumulation simultaneously.
- Export the `.ans` file and view it in a truecolor terminal for a shareable artwork snapshot.

---

## Ghost Trail / Temporal Echo

**Source:** `life/modes/ghost_trail.py`

### Background

Ghost Trail adds a temporal echo rendering layer that overlays fading afterimages from previous frames onto any simulation mode. It makes motion visible: particles leave streaks, wavefronts show their propagation paths, cellular automata reveal their recent evolution, and flocking agents draw luminous trails. The feature enhances every mode at once without modifying any mode logic.

### How it works

Each draw cycle, the system captures a snapshot of every occupied cell on screen — both curses-rendered cells (via `inch()`) and truecolor cells (from `tc_buf`). Snapshots are stored in a ring buffer sized to `trail_depth + 1` frames.

When rendering echoes, the system iterates from the most recent past frame to the oldest. For each cell that was occupied in a past frame but is *not* occupied in the current frame (and hasn't been claimed by a newer echo), a dimmed truecolor glyph is emitted into `tc_buf`. Echo glyphs progress from dense to sparse with age: `▓ → ▒ → ░ → ·`.

Color dimming is RGB-aware: truecolor cells decay their original RGB values by the decay factor; curses-only cells derive a base color from the active colormap. Two decay curves are available:
- **Exponential** (default): `factor = 0.65^age` — rapid falloff, sharp trails
- **Linear**: `factor = 1 - age/(depth+1)` — even fade, longer visible tails

The entire pipeline hooks into `_tc_refresh()`, running once per draw cycle before the truecolor buffer is rendered to the terminal.

Press `g` to toggle the trail (a mode that binds `g` keeps it). While it is on, `<`/`,` and `>`/`.` change the depth (1--20 frames) and Ctrl+G switches the decay curve.

### What to explore

- Toggle ghost trail on Boids or N-Body to see orbital paths and flocking trajectories materialize.
- Use exponential decay on Physarum to highlight active growth fronts while old trails vanish quickly.
- Switch to linear decay on slow simulations (Ising, Lenia) for a smoother, longer-lasting echo effect.
- Increase trail depth to 15–20 frames on fast-moving simulations for dramatic light-painting effects.
- Combine with the Visual FX Pipeline (bloom + ghost trail) for neon afterglow aesthetics.

---

## Parameter Tuner

**Source:** `life/modes/param_tuner.py`

### Background

Parameter Tuner adds a real-time HUD overlay for interactively adjusting any simulation mode's constants while it runs. Instead of restarting a mode with different parameters, you press `P` inside a mode to open a translucent panel listing the active mode's tunable values — diffusion rates, gravity constants, coupling strengths, temperatures, thresholds — and tweak them live with immediate visual feedback. A mode that binds `P` keeps the key.

### How it works

The system has two layers. First, an explicit parameter registry (`TUNABLE_PARAMS`) defines curated min/max/step/format metadata for 30 modes covering 82 individual parameters: Boids (7 params for separation/alignment/cohesion radii and weights), Physarum (sensor angle, distance, turn/move speed, deposit, decay), Reaction-Diffusion (feed/kill rates, diffusion coefficients), Ising (temperature, external field), N-Body (gravity, timestep, softening), and many more.

Second, an auto-detection fallback scans any mode's `self.{prefix}_*` attributes for numeric values, filters out structural/internal attributes via a suffix blocklist, and generates reasonable ranges and step sizes based on magnitude. This means modes without explicit definitions can still use the tuner.

The HUD draws on the right side of the screen with:
- Parameter names with current formatted values
- Visual progress bars showing position within the valid range
- Scroll support for modes with many parameters
- Footer with control hints

Key handling intercepts arrow keys and vim-style navigation only when the tuner is active; all other keys pass through to the simulation, which keeps running underneath.

### What to explore

- Open Boids and crank Separation Weight to 5x while watching the flock explode apart, then drop it to 0.1 and watch them collide.
- In Reaction-Diffusion, sweep the feed rate from 0.02 to 0.06 to watch the pattern transition from spots to worms to spirals to chaos.
- Use `[`/`]` for 10x step adjustments to quickly sweep across a parameter's full range.
- Try the auto-detected parameters on modes without explicit definitions — the tuner discovers numeric attributes automatically.

---

## Auto-Discovery

**Source:** `life/modes/auto_discovery.py`

### Background

Auto-Discovery is an autonomous pattern exploration engine that searches the vast cellular automaton rule space for visually striking emergent behavior without human intervention. Evolution Lab needs you to pick a fitness preset, and Evolutionary Playground relies on human selection. Auto-Discovery is autonomous: it generates, simulates, scores, curates, and breeds candidate configurations in a loop, building a gallery of the most interesting patterns it finds.

### How it works

The engine operates in a generate-evaluate-breed cycle:

1. **Generate**: A batch of candidate configurations is created, each with a randomized B/S ruleset, neighborhood type (Moore or von Neumann), and one of six initial condition styles (random, symmetric, clustered, sparse, striped, central). The batch is displayed as a tiled grid of live mini-simulations.

2. **Evaluate**: Each candidate runs for a configurable number of steps (50--500, default 150) and is scored on five metrics:
   - **Entropy** — Shannon entropy of the grid, measuring structural complexity
   - **Symmetry** — horizontal, vertical, and rotational symmetry detection, measuring emergent order
   - **Stability** — coefficient of variation of the population time series, rewarding the sweet spot between static and chaotic
   - **Periodicity** — state hash cycle detection, rewarding oscillating patterns
   - **Longevity** — the share of the run with a live population; extinction and grid saturation are penalized

3. **Curate**: The top three candidates of each round join the gallery if they reach the score threshold (starts at 150 and rises as the gallery fills). Entries with the same rule and a similar score are skipped. The gallery is sorted by score and capped at a maximum size (10--100, default 50).

4. **Breed**: The next batch is produced through crossover and mutation from the top six gallery entries and the three best candidates of the round.

The gallery browser lists entries by score. `Enter` adopts the selected rule into the main grid, `x` removes an entry, and `W` saves the gallery to `~/.life_saves/auto_discovery_gallery.json`. In the explorer, `a` adopts the rule under the cursor. The start menu can load the saved gallery to continue from it.

### What to explore

- Let it run unattended for several rounds — the gallery accumulates increasingly refined patterns as breeding favors high-scoring configurations.
- Press `g` to browse the gallery, then Enter to adopt a discovered rule into the main Life grid at full resolution.
- Set the mutation rate in the start menu: high for novelty, low for refining known good rules.
- Save the gallery with `W`, then choose "START FROM GALLERY" later to continue from your best discoveries.
- Compare with Evolution Lab: Auto-Discovery varies seed styles and curates on its own, while Evolution Lab gives you control over fitness weights.

---

## Mode Morph Transitions

**Source:** `life/modes/morph_transition.py`

### Background

Mode Morph Transitions replaces the hard cut between simulation modes with a smooth crossfade. When you switch modes (manually or via screensaver auto-cycling), the outgoing mode's final frame is captured and faded out over a configurable number of frames while the new mode fades in underneath. This turns mode-switching into a visually seamless experience, especially effective during demo-reel playback.

### How it works

The transition engine hooks into two points in the main loop pipeline:

1. **Capture** (`_morph_on_mode_exit`): Just before `_exit_current_modes` clears the old mode, the system snapshots every occupied cell on screen — both truecolor RGB cells from `tc_buf` and curses character cells via `inch()`. The snapshot is stored as a dictionary mapping `(y, x)` positions to `(char, r, g, b)` tuples.

2. **Blend** (`_morph_on_refresh`): After `_tc_refresh` renders the new mode's frame, the transition engine overlays the captured old frame with decreasing opacity. For truecolor cells, RGB values are scaled by `alpha_old = 1 - easing(progress/duration)`. For curses-only cells, a grey value is derived from the alpha. Cells where the new mode already has content are skipped, so new content always takes visual priority. Output is emitted as raw ANSI 24-bit color escapes directly to stdout.

Three easing curves control the fade profile:
- **Linear**: constant fade rate
- **Smooth**: cubic smooth-step `t²(3 - 2t)` for a natural feel (default)
- **Ease-in-out**: quintic `16t⁵` / `1 - 16(1-t)⁵` for dramatic slow-start-slow-end

Duration is configurable from 10 to 120 frames (default 45, roughly 1.5 seconds at 30 fps). The feature requires zero changes to any individual mode file — it operates entirely through the app-level dispatch and refresh hooks.

### What to explore

- Toggle morph transitions on with `G` (Shift+G) at the Game of Life screen, then switch between modes to see the crossfade in action. Inside a mode that binds `G` itself, the key goes to the mode.
- Use `[` / `]` at the Game of Life screen to shorten or lengthen the transition duration — short (10 frames) feels snappy, long (90+ frames) feels dreamlike. Inside a mode they scrub time or go to the mode.
- Cycle easing curves with `:` to compare linear (mechanical), smooth (natural), and ease-in-out (cinematic) fade profiles.
- Enable morph transitions alongside the screensaver/demo-reel mode for an unattended visual showcase with seamless mode changes.

---

## Rule Mutation Engine

**Source:** `life/modes/rule_mutation.py`

### Background

Rule Mutation Engine turns the simulator from a tool you explore manually into one that explores *itself*. It runs a live genetic algorithm on cellular automaton birth/survival rulesets, mutating the rule every 80 generations and keeping mutations that raise a fitness score built mainly on Shannon entropy. A lineage sidebar shows the ancestry of the current rule.

Auto-Discovery evaluates batches of candidates in a tiled grid. Rule Mutation Engine works on a single live simulation, so you see the rule shift, the population change, and the fitness score move in real time.

### How it works

The engine operates in a two-phase cycle:

1. **Stable phase** (40 generations): The current rule runs undisturbed. Entropy is sampled every 2 steps, and population and periodicity are tracked. At the end of the window, a composite fitness score is computed and the grid is saved as a revert checkpoint.

2. **Evaluation phase** (40 generations): A candidate rule is produced by randomly flipping digits in the birth/survival sets at the configured mutation rate. The candidate rule is applied to the live grid and evaluated for another 40 steps. At the end:
   - **Hard reject** if the grid goes extinct (population = 0) or saturates (>85% alive). On extinction, the grid is restored from the checkpoint and re-seeded if it is still empty.
   - **Reject** if the grid is frozen (period 1) and fitness did not improve.
   - **Accept** if the candidate's fitness is at least the current fitness minus 0.02.
   - Otherwise accept with a 5% chance, for exploration.

**Fitness function** — a weighted composite of these signals:
- **Shannon entropy** (×40): the dominant factor, the mean of the last 20 samples.
- **Population dynamics** (up to +35): +15 when 5–60% of cells are alive (+5 for 1–85%), plus up to +20 for a changing population (coefficient of variation 0.02–0.5, full bonus from 0.3).
- **Periodicity scoring** (−20 to +10): penalises static grids (period 1: −20) and short cycles (below 5: −10), rewards longer oscillations (5--19: +5, 20 or more: +10).
- **Partial symmetry bonus** (+10): rewards average horizontal, vertical, and rotational symmetry of 20--80%, which looks more interesting than none or full symmetry.
- **Extinction penalty** (−50): applies when the grid is empty.

**Lineage tracking**: Every mutation attempt is recorded as a `LineageNode` with rule string, fitness score, generation, parent rule, and accept/reject status. The sidebar shows the ancestry as a scrolling list with ✓/✗ markers.

### Presets

| Preset | Initial rule | Mutation rate | Strategy |
|--------|-------------|---------------|----------|
| Entropy Climber | B3/S23 | 0.12 | Start from Conway's Life, hill-climb entropy |
| Chaos Seeker | Random | 0.25 | Aggressive mutations from a random starting point |
| Gentle Drift | B36/S23 | 0.06 | Slow, careful evolution from HighLife |
| Complexity Hunter | B3/S23 | 0.15 | Moderate mutation from Conway's Life; the same fitness function as the other presets |
| From Nothing | B/S (empty) | 0.30 | Discover viable rules from an empty ruleset |
| Day & Night Explorer | B3678/S34678 | 0.10 | Explore the neighborhood of Day & Night |

### What to explore

- Run Entropy Climber and watch the rule gradually depart from standard Life, discovering increasingly complex behavior.
- Try From Nothing to see viable birth/survival rules emerge from a blank ruleset — the lineage sidebar shows the evolutionary path.
- Use `e` to pause evolution while the simulation keeps running, freezing on a particularly interesting rule to observe its long-term dynamics.
- Adjust mutation rate with `+`/`-` (0.01--0.50): high for novelty, low for incremental refinement. `[` and `]` change the steps per frame; `r` re-seeds the grid and `R` restarts from a random rule.
- Press `a` to adopt the currently evolved rule into the main Game of Life grid for full-resolution exploration.
- Compare with Auto-Discovery: Rule Mutation mutates one live simulation in place, while Auto-Discovery evaluates batches with crossover breeding.

---

## 2D Spatial Frequency Spectrum

**Source:** `life/modes/spectrum.py`

### Background

The 2D Spatial Frequency Spectrum overlay performs a Discrete Fourier Transform on any running simulation's grid and displays the frequency-domain magnitude as a colorful panel. It reveals hidden periodic structures — standing waves, lattice patterns, rotational symmetry, oscillation frequencies — that are invisible in the spatial domain. Like ghost trail and long-exposure, it works as a universal overlay on any mode without modifying any mode logic.

### How it works

Press `y` to toggle the overlay (a mode that binds `y` keeps it). `{` and `}` halve and double the DFT size between 8 and 64 while the overlay is on. It samples the current simulation state into an N×N grid (default 32×32) via `_get_minimap_data()`, the same universal sampling interface used by the minimap. The 2D DFT is computed using a separable approach:

```
For each row:    X_row[k] = Σ_n x[n] · e^(-j2πkn/N)
For each column: X[k_r, k_c] = Σ_n X_row[n, k_c] · e^(-j2πk_r·n/N)
```

Pre-computed twiddle factor tables (`cos_table`, `sin_table`) avoid redundant trigonometric calls, bringing the complexity to O(N³) for the full 2D transform. The second pass handles complex-valued input from the row transform using the identity `(a + bi)(cos θ - i sin θ) = (a cos θ + b sin θ) + i(b cos θ - a sin θ)`.

The resulting magnitude spectrum is DC-centered by swapping quadrants (shifting by N/2 in both axes), so the zero-frequency component appears at the center of the panel. Log-magnitude scaling (`log1p`) compresses the wide dynamic range for perceptual clarity, and values are normalised to [0, 1] for colormap lookup.

Rendering uses the inferno colormap via `colormap_rgb()` into the truecolor buffer (`tc_buf`), producing a smooth gradient from black (no energy) through purple and orange to yellow (peak energy). A bordered panel is drawn in the bottom-left corner, sized to at most 1/3 of the terminal in each dimension. A status badge in the top-right corner shows the current DFT resolution.

Caching recomputes the spectrum every 3 draw frames to stay responsive without introducing lag on larger resolutions.

### What to explore

- Toggle the spectrum on Game of Life glider guns to see the directional frequency signature of repeating structures.
- Run it on Wave Equation simulations to watch standing wave modes appear as bright spots in the frequency domain.
- Compare Reaction-Diffusion spots vs. worms: spots produce ring-like spectra (isotropic), worms produce directional bands.
- Double the resolution with `}` (up to 64×64) for finer frequency discrimination on large grids.
- Halve it with `{` (down to 8×8) for a fast, coarse overview that updates with minimal lag.
- Combine with ghost trail for simultaneous temporal and spectral analysis of any simulation.

---

## Phase Transition Detector

**Source:** `life/analytics.py` (engine), `life/app.py` (UI)

### Background

Phase transitions — moments when a system's qualitative behavior shifts abruptly — are the most scientifically interesting events in any simulation. Entropy collapses, symmetry breaking, the onset of oscillation, population crashes, and chaos-to-order transitions are all signatures of critical phenomena. The Phase Transition Detector monitors running analytics streams and automatically identifies these moments, bookmarking them for later review.

### How it works

The detector is a global overlay (not a mode) that works across all simulation modes with no per-mode configuration. When enabled via **Ctrl+P**, it watches five analytics channels every generation:

| Channel | Detection method | Threshold |
|---------|-----------------|-----------|
| Entropy | Z-score against rolling 200-generation baseline | \|z\| > 2.5 |
| Population | Z-score against rolling 200-generation baseline | \|z\| > 3.0 |
| Symmetry | Absolute change in averaged symmetry score | Δ > 0.25 |
| Periodicity | Edge detection (period appears/disappears) | Binary |
| Stability | Classification transition (ordered ↔ chaotic) | Phase boundary crossing |

A cooldown of 20 generations between same-type detections prevents noisy rapid-fire alerts. When a transition is detected:

1. A **timestamped bookmark** is automatically added to the bookmark timeline (e.g., `⚡ chaos→order @gen 847`).
2. A **2-second flash banner** appears centered at the top of the screen with a blink effect.
3. An **audio ping** (880 Hz, 80 ms) plays if sound is enabled.

The Rule Mutation Engine has dedicated integration: when the detector is active during rule mutation, accepted mutations are fed to the detector so it can flag when a mutation crosses a phase boundary.

### Controls

| Key | Action |
|-----|--------|
| **Ctrl+P** | Toggle detector on/off |
| **Ctrl+T** | Open phase transition bookmark browser |
| **↑/↓** or **k/j** | Navigate bookmark list |
| **Enter** | Jump to selected bookmark |
| **Esc** | Close bookmark browser |

### What to explore

- Run Conway's Life from a random fill and watch the detector flag the initial chaos→order transition as gliders and still lifes emerge from the primordial noise.
- Enable the detector alongside the Rule Mutation Engine to see which mutations trigger phase boundary crossings.
- Use Reaction-Diffusion and sweep parameters — the detector will bookmark the exact generation where spots transition to worms to spirals.
- After a long session, press **Ctrl+T** to browse all detected transitions and jump between the most interesting moments, turning hours of observation into a curated highlight reel.
- Combine with the analytics overlay (**Ctrl+K**) to see transition counts and recent events in real time.

---

## Sim-in-a-Cell

**Source:** `life/modes/recursive_sim.py`

### Background

Sim-in-a-Cell introduces multi-scale emergence: every cell in a macro-level grid contains a complete, independently running micro-simulation. The micro-simulation's aggregate density feeds upward to determine the macro cell's state, while the macro cell's state feeds back down into its micro-simulation as an external coupling signal. The result is two levels of reality influencing each other simultaneously — patterns at the micro scale drive macro-scale dynamics, and macro-scale context reshapes micro-scale behavior.

Any two of the eight mashup engines (Game of Life, Wave, Reaction-Diffusion, Forest Fire, Boids, Ising, Rock-Paper-Scissors, Physarum) can be combined as macro and micro engines, creating 64 cross-scale combinations. Eight curated presets highlight especially interesting pairings.

### How it works

```
each generation:
    for each macro cell (r,c):
        compute macro cell density as external signal
        scale by coupling strength → uniform field for micro grid
        step the micro-simulation with external influence
        aggregate micro-grid density → rsim_micro_densities[r][c]
    build density field from all micro densities
    step the macro engine with micro density field as external input
    refresh macro density cache
```

The macro grid dimensions are fitted to the terminal (up to 30×40). Each macro cell hosts a micro-grid of configurable size (6×6, 8×8, 10×10, or 12×12). Bidirectional coupling strength is adjustable from 0 (fully independent) to 1 (maximum influence) with a default of 0.5.

In overview mode, each macro cell is rendered as a 2-character-wide block. The glyph (`░▒▓█`) encodes micro density; color encodes macro state (magenta = both active, cyan = macro alive, green = micro active). A movable cursor lets you select any cell to zoom into.

In zoom mode, the selected cell's micro-simulation is rendered full-screen with scaled-up blocks. A minimap in the corner shows your position in the macro grid. Arrow keys navigate between neighboring cells without returning to the overview.

### Controls

| Key | Action |
|-----|--------|
| **Space** | Play / pause |
| **n** or **.** | Single step |
| **+** / **-** | Increase / decrease coupling strength |
| **0** | Set coupling to zero (independent) |
| **>** / **<** | Increase / decrease simulation speed |
| **Enter** or **z** | Zoom into selected cell |
| **Esc** or **Backspace** | Back to overview (when zoomed) |
| **Arrow keys** / **hjkl** | Move cursor (overview) or navigate neighbor cells (zoom) |
| **r** | Reset simulation |
| **R** or **Esc** | Return to preset menu (overview) |
| **q** | Exit mode |

### What to explore

- Start with "GoL ← RD Cells" to see a Game of Life grid where each cell's alive/dead state is driven by the churning patterns of a Reaction-Diffusion micro-world.
- Try "GoL ← GoL Cells" for true recursive Life — Game of Life all the way down.
- Set coupling to 0 and watch macro and micro evolve independently, then slowly increase coupling to see cross-scale synchronization emerge.
- Zoom into individual cells and watch how neighboring macro-cell states visibly influence a cell's internal dynamics.
- Compare "Ising ← RPS Cells" (magnetic spins driven by rock-paper-scissors competition) with "RPS ← Wave Cells" (competitive dynamics driven by wave interference) to see how the choice of micro engine fundamentally changes macro-scale behavior.
- Use small cell sizes (6×6) for faster iteration and larger macro grids, or large cell sizes (12×12) for richer micro-simulation detail.

---

## Symbiosis Multi-Physics

**Source:** `life/modes/symbiosis.py`

### Background

Symbiosis Multi-Physics is a co-simulation mode where 3–8 distinct simulation engines run simultaneously on overlapping layers of the same grid, interacting through shared environmental fields. Unlike Mashup (two engines coupled by density) or Split-Screen (two panes), Symbiosis keeps each engine's own dynamics and couples them through four shared fields: temperature, chemical concentration, and flow velocity (u and v components). Engines can follow chemical trails shaped by currents or react to heat from other engines.

### How it works

Each engine runs its own simulation step independently, producing a density grid per layer. After each generation, every engine's density is used to update the shared environmental fields according to engine-specific contribution rules:

- **Wave** → raises temperature (kinetic energy), creates flow gradients
- **Reaction-Diffusion** → deposits chemical concentration
- **Fire** → raises temperature (combustion heat)
- **Boids** → create flow fields (flock velocity) and deposit chemical pheromones
- **Physarum** → deposits chemical trail pheromone
- **Ising** → raises temperature from spin frustration energy
- **RPS** → deposits chemical from competition intensity
- **Game of Life** → raises temperature from population density

The fields then feed back into each engine through coupling densities — each engine type responds to different fields (e.g., fire responds to chemical fuel and wind, boids follow chemical gradients and are carried by flow currents, physarum is attracted to chemicals but avoids heat). Fields decay and diffuse each step.

Visualization uses RGB-layered color channels: each engine is assigned a color (red, green, cyan, yellow, magenta, or white), with the dominant layer at each cell determining the displayed color. When two layers overlap with similar intensity, magenta is used to indicate mixing. Density is shown using five-level Unicode block characters (░▒▓█).

### Presets

| Preset | Engines | Description |
|--------|---------|-------------|
| **Fluid-Chemical-Biological** | Wave + RD + Physarum | Waves drive chemical reactions; chemicals guide slime mold; slime creates wave disturbances |
| **Fire-Ising-Boids** | Fire + Ising + Boids | Fire heats spins; magnetic domains steer flocks; flock density fuels combustion |
| **Wave-RPS-GoL** | Wave + RPS + GoL | Waves modulate dominance; RPS competition seeds life; life emits wave pulses |
| **Full Ecosystem** | RD + Boids + Fire + Physarum | Chemistry, organisms, fire, and fungal networks interacting through shared fields |
| **Quantum-Classical Bridge** | Wave + Ising + RD | Wave interference shapes spin domains; spin alignment catalyzes reactions; reactions emit waves |
| **Predator Ecosystem** | Boids + Physarum + RPS + GoL | Flocks, slime trails, cyclic competition, and cellular life in one shared world |
| **Custom** | Pick 3–8 engines | Checkbox selection from the full engine catalogue |

### Controls

| Key | Action |
|-----|--------|
| **Space** | Play / pause |
| **n** or **.** | Single step |
| **1**–**8** | Solo layer N (press again to unsolo) |
| **!**–**\*** (Shift+1–8) | Mute / unmute layer N |
| **a** | Show all layers |
| **f** | Toggle environmental field overlay |
| **F** | Cycle through field views (temperature → chemical → flow_u → flow_v) |
| **+** / **-** | Increase / decrease coupling strength |
| **0** | Set coupling to zero (independent engines) |
| **>** / **<** | Increase / decrease simulation speed |
| **r** | Reset simulation |
| **R** | Return to preset menu |
| **q** or **Esc** | Exit mode |

### What to explore

- Start with "Fluid-Chemical-Biological" to see the canonical three-way interaction: waves create flow that shapes chemical gradients, which in turn guide physarum growth, whose structures then disturb the wave field.
- Use the field overlay (**f**/**F**) to watch the invisible environmental fields that mediate cross-engine coupling — see temperature hotspots from fire, chemical trails from physarum, flow vectors from wave gradients.
- Solo individual layers (**1**–**8**) to see how each engine behaves in isolation while still being influenced by the shared fields, then show all (**a**) to see the combined picture.
- Try "Full Ecosystem" (4 engines) for a richer interaction network where chemistry, organisms, fire, and fungal networks create complex feedback loops.
- Adjust coupling from 0 (independent) to 1.0 (maximum) to see how cross-domain influence changes emergent behavior. At zero coupling, engines evolve independently; at high coupling, they become strongly correlated.
- Build a custom combination to test unusual pairings — what happens when Ising spins interact with boid flocks through temperature fields?

---

## Terrarium

**Source:** `life/modes/terrarium.py`

### Background

Terrarium turns the simulator from a tool you run into a world you tend. It adds session persistence and the passage of real time — your simulation saves automatically when you leave and resumes exactly where it left off when you return. While you're away, the terrarium fast-forwards through elapsed generations and keeps a chronicle of notable events (extinctions, population records, phase transitions) with real-world timestamps. Returning to your terrarium shows a summary of what happened while you were gone, like checking in on a digital aquarium.

### How it works

State is saved to `~/.life_saves/terrarium/` as two files: `state.json` (grid, viewport, speed, colormap, terrarium metadata) and `chronicle.json` (timestamped event log). Writes are atomic — a temp file is written first, then renamed into place — so a crash mid-save can't corrupt the save file.

On resume, the elapsed real-world time is converted to generations at the saved speed setting and fast-forwarded (capped at 50,000). During catch-up, the simulation runs at full speed while monitoring for extinctions (auto-reseeds random cells to keep the world alive), population records, and phase transitions. Analytics and the phase transition detector run at sample intervals during catch-up to detect qualitative shifts.

The chronicle is a bounded log (max 5,000 entries) that records events with both real-world timestamps and simulation generation numbers. Events include: terrarium creation, session starts/ends, population records (>10% increase over previous peak), extinctions, re-seeds, and phase transitions.

Auto-save runs every 60 seconds during simulation, and state is always saved on quit (`q`), `Ctrl+C`, or `SystemExit`.

### Controls

| Key | Action |
|-----|--------|
| `--terrarium` | CLI flag to launch in terrarium mode |
| **Enter** or **Esc** | Dismiss the welcome-back summary and start the simulation (from the chronicle: back to the summary) |
| **↑** / **↓** | Scroll summary or chronicle |
| **c** | Toggle chronicle viewer from summary screen |
| **q** | Return from chronicle to summary; while running, save and exit |

### What to explore

- Launch with `python life.py --terrarium` and let it run for a while, then quit and come back later — hours, days — to see what happened.
- Watch the chronicle accumulate over multiple sessions. Population records, extinctions, and phase transitions tell the story of your terrarium's life.
- Leave the terrarium running overnight and check the welcome-back summary in the morning for a history of what happened while you slept.
- If your terrarium reaches extinction, it will auto-reseed — watch how different random configurations evolve differently after each extinction event.
- Use the chronicle viewer (`c`) to scroll through the full event history and spot patterns across sessions.

---

## Emergent Computation Detector

**Source:** `life/modes/computation_detector.py`

### Background

Existing analytics measure statistical properties (entropy, periodicity, phase transitions) but not **causal structure and information flow**. The Emergent Computation Detector is an information-theoretic overlay that instruments any running simulation to find computational structures — glider guns, logic gates, signal channels, memory cells — using transfer entropy, integrated information, and causal density.

This mode works as a universal overlay, not a standalone simulation. It samples the active simulation via `_get_minimap_data()`, meaning it works across every existing mode without modification. Toggle it with `I` at the Game of Life screen or in any mode that leaves `I` free; a mode that binds `I` keeps it.

### How it works

**Transfer entropy** measures directed information flow between cells. For each cell, the detector estimates how much knowing a neighbor's past state reduces uncertainty about the cell's future state, using a binned conditional entropy estimator: TE(X→Y) = H(Y_t | Y_{t-1}) − H(Y_t | Y_{t-1}, X_{t-1}). The total outgoing TE per cell is summed across cardinal neighbors and normalized to [0, 1] for the heatmap.

**Causal density** measures how tightly coupled a cell is with its neighborhood. For each of 8 neighbors, if the pairwise transfer entropy exceeds a threshold (0.02 bits), it counts as a causal link. Causal density is the fraction of neighbors with significant causal connections — high values indicate cells that are part of a coherent computational unit rather than isolated noise.

**Information flow direction** computes pairwise TE from each cell to all 8 neighbors, then selects the direction with the highest TE as the dominant flow direction. This is rendered as Unicode arrows (↑↓←→↗↘↖↙), revealing signal propagation paths.

**Structure classification** uses flood-fill to identify connected regions of high TE/CD, then classifies each region by its properties:

| Structure | Icon | Detection criteria |
|-----------|------|-------------------|
| Oscillator | ∿ | Periodic activity, size ≤ 6 |
| Gun | ⊛ | Periodic activity, high TE, size > 6 |
| Gate | ⊕ | High causal density, size ≤ 4 |
| Memory | ⊞ | High causal density, size > 4 |
| Wire | ━ | Moderate TE, low CD, elongated |
| Source | ◉ | High TE, low CD |
| Sink | ◎ | Low TE, high CD |
| Still life | ■ | Low TE, moderate CD, non-periodic |

**Integration score (Φ)** approximates integrated information by weighting each cell's transfer entropy by its causal density and summing across the grid. Higher Φ means the system's information processing exceeds what independent parts would achieve.

The detector samples the simulation into a configurable N×N grid (default 24×24), maintains a ring buffer of 12 frames, and recomputes all measures every 4 draw frames to balance responsiveness with CPU cost.

### Controls

| Key | Action |
|-----|--------|
| **I** | Toggle computation detector on/off |
| **Tab** | Cycle view: Transfer Entropy → Causal Density → Info Flow Arrows |
| **+** / **-** | Increase / decrease sampling resolution (8–48, step 4) |
| **l** | Toggle structure labels on/off |

### What to explore

- Run Conway's Life and toggle `I` — watch gliders appear as directional TE channels and oscillators light up as periodic high-CD clusters.
- Compare the Φ integration score across different rule sets. Rules that produce complex behavior (like B3/S23) should score higher than rules that quickly die or fill the grid uniformly.
- Use the causal density view to find "computational cores" — regions where cells are tightly coupled and processing information collectively.
- Watch the info flow arrows during a glider collision to see information scatter and recombine.
- Try it on non-CA modes (wave equations, reaction-diffusion, boids) — the information-theoretic measures work on any dynamics, revealing computational structure in continuous systems too.
- Adjust resolution with `+`/`-`: lower resolution (8×8) gives faster updates for real-time exploration; higher resolution (48×48) reveals finer structure for detailed analysis.

---

## Butterfly Effect

**Source:** `life/modes/butterfly_effect.py`

### Background

Butterfly Effect mode answers the question "did this cell actually matter?" by forking the simulation at any point, applying a single-cell perturbation, and running both the original and altered timelines in parallel. A real-time divergence heatmap shows exactly how and where the perturbation cascades through the system, turning the simulator into a causal analysis tool.

### How it works

Press **Ctrl+B** to enter Butterfly Effect mode. The current grid state is deep-copied into a second "perturbed" timeline. A crosshair cursor appears for cell selection — navigate with arrow keys or hjkl, then press Enter to flip that cell (alive→dead or dead→alive). Both timelines then evolve independently using identical rules.

Each generation, the engine computes a cell-by-cell diff between the two grids. In cumulative mode, the heatmap accumulates total historical divergence per cell; in instantaneous mode, it shows only the current frame's differences. The divergence percentage (fraction of cells that differ) and peak divergence are tracked continuously.

Three visualization modes are available:

- **Heatmap Overlay** — The original grid rendered with a color-coded divergence overlay. Cells where the timelines have diverged are colored along a blue→cyan→green→yellow→orange→red→pink ramp. Undivergent live cells are shown dimmed. The perturbation point blinks with an `X` marker.

- **Side-by-Side** — Split screen with the original timeline on the left and the perturbed timeline on the right. Cells that differ between timelines are highlighted in red on the perturbed side. Population sparklines appear below each panel.

- **Dual Overlay** — A blended single-grid view where green cells are alive only in the original, red cells are alive only in the perturbed timeline, and yellow cells are alive in both. Dead-in-both cells are blank.

The heatmap supports both linear and logarithmic color scaling. Log scale is useful for revealing subtle early divergence before the perturbation has cascaded widely.

### Controls

| Key | Action |
|-----|--------|
| **Ctrl+B** | Enter/exit Butterfly Effect mode |
| **Arrows** / **hjkl** | Move the cursor while picking. While running, only the arrow keys scroll the viewport; `h` toggles the heatmap mode |
| **Enter** | Confirm cell perturbation |
| **Space** | Play/pause both timelines |
| **n** / **.** | Single-step both timelines |
| **d** | Cycle view: Heatmap → Side-by-Side → Dual Overlay |
| **h** | Toggle cumulative vs instantaneous heatmap |
| **c** | Toggle linear vs logarithmic color scale |
| **r** | Reset: re-snapshot grid and pick a new cell |
| **<** / **>** | Adjust simulation speed (`,` also slows it) |
| **Esc** / **q** | While picking: cancel and leave the mode. While running: `q` leaves the mode |

### What to explore

- Perturb a cell near a glider's path and watch the divergence spread as the glider's trajectory shifts, creating a widening cone of causal influence.
- Compare perturbation sensitivity across different rulesets — chaotic rules (like B3678/S34678) will show rapid, explosive divergence while stable rules show minimal spread.
- Use log scale to catch the exact moment divergence begins propagating — useful for identifying causal chains.
- Try perturbing cells in different regions: a cell in a dense cluster vs. an isolated cell vs. one near a glider gun. The divergence patterns reveal the causal structure of the simulation.
- Watch the population delta between timelines — sometimes killing a single cell causes a population explosion in the perturbed timeline (or vice versa).
- Use the instantaneous diff mode to see the "active front" of divergence — the boundary where the perturbation is currently spreading.

---

## Genesis Protocol

**Source:** `life/modes/genesis_protocol.py`

### Background

Genesis Protocol is an autonomous open-ended evolution engine for cellular automata rule-space exploration. Rather than requiring the user to manually choose rules and initial conditions, the system independently generates random rule combinations, simulates them, measures their emergent complexity using information-theoretic metrics, and curates a persistent ranked gallery of the most interesting discovered universes. It turns the simulator from a tool you operate into one that explores on its own.

The mode builds on the project's existing infrastructure — rule mutation from the auto-discovery engine, information-theoretic measures from the computation detector, and parallel simulation from split-screen and symbiosis modes — tying them together into a single autonomous loop: **generate → simulate → measure → rank → breed → repeat**.

### How it works

Each round, the system generates a batch of candidate universes (4--20, default 8) with random or evolved genomes. A genome encodes: birth set, survival set, neighborhood type (Moore or von Neumann), initial density, and seed style (random, symmetric, clustered, sparse, striped, or central). Candidates are displayed in a tiled grid and simulated forward for 120 generations (50--500 in the start menu).

During simulation, the system collects per-universe metrics:

- **Shannon entropy** — structural complexity of the spatial pattern
- **Transfer entropy** — information flow between cells (sampled on a 16×16 subgrid)
- **Spatial complexity** — edge density between differing cell states
- **Symmetry** — partial symmetry scores highest (pure symmetry or pure randomness score low)
- **Population dynamics** — coefficient of variation of the population trajectory
- **Periodicity** — oscillation detection via autocorrelation of population history

After the run, each universe receives a composite fitness score (0–100). Structural classification identifies gliders, oscillators, replicators, still lifes, chaotic patterns, expanding, and collapsing configurations. Top scorers are promoted to the Hall of Fame (persisted to `~/.life_saves/genesis_hall_of_fame.json`) if they exceed an adaptive quality threshold (starts at 80, rises as better universes are found).

The next round breeds from the best: crossover between hall-of-fame members and top performers, point mutation on birth/survival sets, and fresh random genomes for diversity injection. The system auto-continues indefinitely, building up an increasingly curated collection of complex emergent universes.

### Controls

| Key | Action |
|-----|--------|
| **Space** | Pause/resume simulation (once the round is scored: breed the next round) |
| **S** | Skip to scoring (finish the current evaluation at once) |
| **b** | Score the round, or breed the next one once scored |
| **Arrows** / **wasd** | Move the cursor between tiles |
| **Enter** | Adopt the selected universe's rules into the main grid and leave the mode |
| **h** | Toggle Hall of Fame browser (only once it has entries) |
| **↑ / ↓** or **k / j** (in HoF view) | Scroll through Hall of Fame entries |
| **h** (in HoF view) | Return to the explorer |
| **Enter** (in HoF view) | Adopt the selected entry's rules |
| **x** (in HoF view) | Remove the selected entry |
| **A** | Toggle auto-continue between rounds |
| **W** | Save the Hall of Fame |
| **r** | Start over with a new random batch |
| **R** | Return to the settings menu |
| **> / <** | Change speed |
| **Esc** / **q** | Exit Genesis Protocol (also from the Hall of Fame view) |

### What to explore

- Launch it and walk away — come back to find a curated collection of universes the system discovered autonomously, each with complexity scores and structural classifications.
- Watch the Hall of Fame threshold rise over time as the system discovers increasingly complex rule combinations.
- Look for universes classified as "glider" or "replicator" — these represent rules that produce mobile or self-copying structures, which are relatively rare in random rule-space.
- Compare the information-theoretic profiles of different structural classes: oscillators tend to have high periodicity but moderate entropy, while chaotic patterns have high entropy but low periodicity.
- Adopt an interesting discovered rule into your main simulation to explore it in detail with other modes (computation detector, butterfly effect, etc.).
- Browse the Hall of Fame across sessions — the persistent gallery accumulates discoveries over multiple runs, building a long-term catalog of interesting CA rule-space regions.

---

## Adaptive Adversary

**Source:** `life/modes/adaptive_adversary.py`

### Background

Adaptive Adversary is a co-evolutionary roguelike that fuses two prior modes: the Living Labyrinth (playable CA dungeon) and the Genesis Protocol (evolutionary rule-space search). The result is a dungeon that *learns from how you play* — tracking your movement patterns, item preferences, hesitancy, and path predictability, then evolving its CA ruleset between levels to exploit your specific behavioral weaknesses. A population of adversary genomes competes to be "most challenging but still solvable," creating an emergent arms race between human intuition and algorithmic evolution.

The concept draws on competitive co-evolution (Hillis 1990, Sims 1994): rather than optimizing against a fixed objective, the adversary and player mutually adapt, producing escalating complexity. This is the project's core theme — emergence through interaction — made directly participatory.

### How it works

The player navigates the same roguelike structure as the Living Labyrinth: maze generation via recursive backtracker with 30% extra passage opening, turn-based movement, collectible items (Freeze/Reverse/Mutate), and a CA that evolves the dungeon walls each turn.

The key addition is the adversary layer, which operates on three timescales:

**Within a level** — a player behavior profile accumulates statistics:
- Movement direction counts (up/down/left/right/wait)
- Item usage by type (freeze, reverse, mutate)
- Turns to exit, deaths, direction changes
- Position trail for predictability analysis

**Between levels** — the weakness analyzer examines the profile and produces targeted adaptations:
- **Directional bias** (>35% in one direction) → evolve asymmetric corridor collapse from the favored direction
- **Item dependency** (>50% usage of one type) → evolve counters (e.g., freeze-dependent → faster wall regrowth; reverse-dependent → more volatile dynamics)
- **Hesitancy** (>20% wait moves) → evolve aggressive wall encroachment
- **Path predictability** (low direction-change rate) → evolve corridor traps

**Across generations** — a population of 8 adversary genomes evolves via:
- **Genome representation**: birth set, survival set, asymmetry bias (0–1), wall aggression (0.1–1.5)
- **Fitness function**: base score + weakness-targeting bonuses × solvability multiplier. The solvability sweet spot rewards 30–80 turn completions (×1.3), and penalizes trivial (<15 turns, ×0.5) or tedious (>150 turns, ×0.7) levels
- **Selection**: elite preservation (top 3) + crossover from top half + point mutation (18% per gene) + one random genome for exploration
- **Targeted mutation**: after standard evolution, the best genome receives additional mutations tuned to the player's detected weaknesses

A BFS solvability check runs after each level generation; if no path exists from player to exit, a guaranteed corridor is carved. The CA keeps the player's cell and the exit open on every tick, so walls close in around the player but never crush them.

### Controls

| Key | Action |
|-----|--------|
| **Arrows / WASD / hjkl** | Move player (`@`) |
| **Space** | Wait one turn |
| **f** | Use Freeze item (locks walls in radius for 10 turns) |
| **v** | Use Reverse item (rewinds CA state locally) |
| **m** | Use Mutate item (randomly flips cells nearby) |
| **+/-** | Adjust CA ticks per player move |
| **TAB** | Toggle Adversary Report overlay |
| **?** | Toggle help overlay |
| **n** | Restart from level 1 (after a win: next level) |
| **Esc / q** | Exit Adaptive Adversary |

### What to explore

- Play several levels naturally, then press TAB to read the Adversary Report — it shows your movement bar chart, item usage, detected behavioral patterns, and exactly how the dungeon adapted. Try deliberately changing your strategy and watch the adversary re-adapt.
- If you always go right, the dungeon will evolve asymmetric rules that collapse corridors from the right. Counter by varying your approach direction.
- Heavy Freeze usage triggers faster wall regrowth — the dungeon learns to make your favorite tool less effective. Try rationing items or switching to Mutate.
- Watch the evolution generation counter climb as the adversary adapts between levels.
- The solvability sweet spot means the dungeon *wants* to challenge you, not trap you. A level you clear in 30--80 turns earns the highest fitness multiplier (×1.3), a trivial one the lowest.
- Compare the CA behavior across levels — you're watching natural selection in real time, with yourself as the selection pressure.

---

## Phase Space Navigator

**Source:** `life/modes/phase_space.py`

### Background

Phase Space Navigator maps the entire behavioral landscape of cellular automaton rule-space as an interactive 2D heatmap. Where Genesis Protocol explores rule-space one universe at a time, and Butterfly Effect examines causal sensitivity within a single simulation, the Phase Space Navigator gives a **global view** — showing where complexity, chaos, oscillation, and death occur across all possible rule parameterizations simultaneously. It is the natural culmination of the project's analytical trajectory: a "map of all possible universes."

The mode runs one micro-simulation per heatmap cell behind the scenes, classifying each point in a 2D parameter space by its emergent behavior. The user can sweep across rule parameters (birth vs. survival thresholds, density vs. birth, Langton-style lambda/mu fractions) and instantly see the narrow edge-of-chaos regions where interesting dynamics live. Pressing Enter on any point teleports into a full-screen simulation of that rule.

### How it works

The navigator spans a configurable 2D parameter space. Four axis modes are available:

- **Birth vs Survival** — single birth/survival neighbor thresholds (B{x}/S{y}), with both axes spanning 0--8.
- **Birth Range vs Survival Range** — centered ranges with configurable width, exploring rules with multiple birth/survival values at once.
- **Density vs Birth Threshold** — how initial cell density affects outcomes across different birth rules (with fixed Conway survival).
- **Lambda vs Mu** — Langton's lambda-like fractional parameters controlling the probability of each neighbor count appearing in birth/survival sets.

The heatmap is sized to the terminal (8--60 columns, 6--40 rows). For each grid point, a micro-simulation (16×16 cells, 80 steps) is seeded at 35% density (except on the density axis) and run to completion. Simulations are evaluated using a center-outward spiral scan for visual effect during the loading phase.

Each point is classified into one of six behavioral categories from its population history: **dead** (extinct), **explosive** (over 85% of cells alive), or, by the coefficient of variation of the last 20 populations, **static** (a constant population or a variation below 1%), **oscillating** (below 5%), **complex** (edge of chaos, below 15%) or **chaotic** (above that). These classifications drive three visualization views:

- **Classification view** — each behavior type has its own block shade and color, with a legend beside the map.
- **Complexity heatmap** — 0–1 intensity score combining entropy, population variability, and behavioral classification weights.
- **Entropy heatmap** — Shannon entropy of the final pattern's live/dead split (0--1 bit).

The teleport feature launches a full-size simulation with the selected point's rule, allowing detailed observation before returning to the map. The adopt feature applies the selected rule to the main simulation.

### Controls

| Key | Action |
|-----|--------|
| **Arrows / hjkl** | Move cursor on the heatmap |
| **Shift+H/J/K/L** | Fast cursor movement (5 cells) |
| **Enter** | Teleport into selected point's simulation (full-screen preview) |
| **a** | Adopt the cursor's rule into the main simulation |
| **v** | Cycle view: Classification → Complexity → Entropy |
| **t** | Toggle axis labels |
| **r** | Rescan with new random seeds |
| **m** | Cycle axis mode (Birth/Survival, Range, Density, Lambda/Mu) |
| **Space** | Play/pause scanning |
| **R** | Return to settings menu |
| **Backspace / b** | Return from teleport preview to heatmap |
| **Esc / q** | Exit Phase Space Navigator |

### What to explore

- Start with Birth vs Survival mode to see the full 9×9 landscape of simple threshold rules. The yellow "complex" points reveal the narrow edge-of-chaos corridor — rules like B3/S23 (Conway's Life) that balance growth and death.
- Switch to Lambda vs Mu mode to see Langton's classic result: a phase transition from death (low lambda) through a narrow band of complexity to chaos (high lambda). The heatmap makes this transition visible as a diagonal ridge.
- Use Density vs Birth Threshold to understand why some rules are sensitive to initial conditions while others converge to the same behavior regardless of starting density.
- Teleport into points near the boundary between two behavioral regions — these transition zones often produce the most surprising dynamics.
- Rescan with `r` to see how stochastic effects change the map — regions that remain stable across rescans are genuinely robust, while flickering regions indicate sensitivity to initial conditions.
- Combine with other modes: find an interesting rule in Phase Space, adopt it with `a`, then analyze it with Butterfly Effect or the Computation Detector to understand its internal structure.

---

## Simulation Archaeology

**Source:** `life/modes/simulation_archaeology.py`

### Background

Every other mode in the simulator asks "what does this rule produce?" Simulation Archaeology inverts that question: given a mysterious frozen end-state, what rules and initial conditions produced it? This turns rule-space exploration into a detective game — you're presented with an artifact (the final state of an unknown CA run) and must deduce the birth/survival rule that created it using analytical clues, hypothesis testing, and visual comparison.

The mode leverages the analytical infrastructure built by Genesis Protocol, Phase Space Navigator, and Butterfly Effect (entropy, symmetry, periodicity, stability classification) to give those measurements a gameplay purpose: they're the clues you use to narrow down your hypothesis.

### How it works

**Puzzle generation:** The mode selects a CA rule (difficulty-dependent), seeds a grid using one of five seed styles (random, symmetric, clustered, sparse, central), runs it forward for N generations (40–200 depending on difficulty), and captures the end-state as a frozen "artifact." Timeline snapshots and analytical measurements (entropy, symmetry, stability, population, periodicity) are computed and stored as potential clues.

**Deduction loop:** You edit birth/survival digit sets directly (number keys toggle individual digits 0–8, Tab switches between editing birth vs survival), adjust initial density (+/−), and cycle seed style guesses. Press Space to simulate your candidate rule forward the same number of generations, then visually compare the result against the artifact.

**Clue system:** 11 clue types are available — entropy, symmetry scores (H/V/rotation), stability classification, population percentage, birth/survival digit counts, individual digit hints, timeline animation fragments, initial density, and periodicity. Higher difficulties start with fewer free clues; requesting additional clues with `c` costs 15 points each.

**Scoring:** Each puzzle starts at 100 points maximum. Each clue costs 15 points. Wrong guesses don't cost points but provide partial-credit feedback via Jaccard similarity of the guessed vs actual digit sets, rated as "very close" (>80%), "getting warm" (>50%), "some overlap" (>20%), or "not quite."

**Four difficulty levels:**
- **Easy** — well-known rules (Conway's Life, HighLife, Day & Night, Seeds, Diamoeba, Morley, Anneal, 2×2) with 4 free clues and 40-generation runs
- **Medium** — known rules with random single-digit mutations, or semi-random rules, 2 free clues, 80 generations
- **Hard** — fully random birth/survival sets, 1 free clue, 120 generations
- **Expert** — fully random rules, no free clues, 200 generations

### Key controls

| Key | Action |
|-----|--------|
| **0–8** | Toggle digit in current edit set (birth or survival) |
| **Tab** | Switch between editing birth and survival sets |
| **Space** | Simulate candidate rule forward and view result |
| **Enter** | Submit guess and check answer |
| **+/−** | Adjust initial density guess |
| **s** | Cycle seed style guess |
| **c** | Request a clue (costs 15 points) |
| **v** | Cycle view mode: artifact → candidate → difference → side-by-side |
| **t** | Toggle timeline fragment animation (only after the timeline clue is revealed with `c`) |
| **d** | Cycle difficulty level |
| **n** | Skip to next puzzle |
| **r** | Reset candidate guess to defaults |
| **a** | Give up and reveal answer |
| **h** | Show or hide the bottom key-hint bar |
| **q / Esc** | Exit mode |

### What to explore

- Start on Easy to learn the visual signatures of well-known rules. Conway's Life artifacts have characteristic still-life clusters; Seeds produces distinctive flash-and-die patterns; Day & Night creates dense symmetric blobs.
- Use the entropy clue first — it's often the most discriminating. Very low entropy suggests a rule that converges to simple still lifes; high entropy suggests chaotic or space-filling behavior.
- The difference view (red = mismatch) is your most powerful comparison tool. Even when the overall patterns look similar, the diff highlights subtle structural disagreements.
- On harder difficulties, use the birth/survival count clues to constrain the search space before requesting individual digit hints.
- Timeline fragments reveal the dynamics — a rule that oscillates vs one that slowly decays vs one that explodes all look different in motion, even if their final states are superficially similar.

---

## Rule Phylogenetics

**Source:** `life/modes/rule_phylogenetics.py`

### Background

Rule Phylogenetics applies comparative genomics to cellular automaton rules. It treats B/S rulesets as 18-bit genetic sequences, computes distances between them, builds family trees, and identifies conserved behavioral motifs, which are minimal rule fragments that produce specific behaviors across many rule variants. It reads the Genesis Protocol Hall of Fame (`~/.life_saves/genesis_hall_of_fame.json`) as its dataset.

Genesis Protocol *breeds* rules, Phase Space Navigator *maps* rule space, and Rule Phylogenetics *classifies* the relationships between rules.

### How it works

**Genome encoding:** Each B/S rule is encoded as an 18-bit binary vector — 9 bits for birth conditions (B0–B8) and 9 bits for survival conditions (S0–S8). This uniform representation enables direct bitwise comparison, distance computation, and motif detection across any pair of rules.

**Distance metrics:** Three complementary distance measures are combined with weights (default 0.4 Hamming, 0.3 Jaccard, 0.3 behavioral; the start menu cycles four weight presets):

- **Hamming distance** — raw bit-level difference between two rule genomes, normalized to [0, 1]. Measures syntactic distance.
- **Jaccard distance** — set-theoretic (1 − intersection/union) over the combined set of B and S digits. Measures structural similarity of the rule logic.
- **Behavioral distance** — adds 0.5 when the classification labels (glider, oscillator, chaotic, etc.) differ, plus up to 0.5 for the relative difference in Hall of Fame score. Measures phenotypic similarity regardless of genotype.

**Phylogenetic tree construction:** UPGMA (Unweighted Pair Group Method with Arithmetic Mean) hierarchical clustering builds a dendrogram from the pairwise distance matrix. The tree is rendered as color-coded ASCII art: green for glider/replicator rules, yellow for oscillators, red for chaotic rules, cyan for stable/still-life rules.

**Conserved motif detection:** A library of known behavioral motifs (e.g., "Life core" = B{3} S{2,3}, "Replicator seed" = B{1}, "HighLife extension" = B{3,6} S{2,3}) is checked against all rules in the dataset. For each motif, the mode reports frequency of occurrence, example rules carrying that motif, and a visual frequency bar. This reveals which minimal rule fragments drive specific behaviors.

**Lineage tracing:** Reconstructs parent→child breeding relationships from the Genesis Protocol's round-based Hall of Fame history. Shows which specific birth/survival mutations occurred between generations and whether those mutations caused behavioral shifts (e.g., stable→chaotic).

**Rule diff:** Side-by-side genome visualization of any two rules, with bit-level diffs marked by `^` characters, all three distance metrics, and behavioral shift detection.

### Five interactive views

1. **Tree (key: 1)** — Full phylogenetic tree, color-coded by behavioral classification. Arrow keys move the cursor, Enter previews the selected rule live.

2. **Motifs (key: 2)** — Conserved motif catalog showing each motif's name, birth/survival fragment, associated behavior, frequency across the dataset, and example rules. Scroll through with arrow keys.

3. **Diff (key: 3)** — Mark two rules with `a` and `b`, press `d`, and see a genome comparison: full 18-bit vectors, birth/survival set differences, Hamming/Jaccard/behavioral distances, and behavioral shift analysis.

4. **Lineage (key: 4)** — Breeding history from Genesis Protocol. Shows generation chains with parent→child arrows, mutation annotations, and behavioral classification at each node. Traces how rule families evolved through the breeding process.

5. **Families (key: 5)** — Summary of rule families grouped by classification. Each lists its member count and share, and its top four members by score with up to two motif names each.

### Key controls

| Key | Action |
|-----|--------|
| **1–5** | Switch between Tree / Motifs / Diff / Lineage / Families views |
| **↑/↓** | Move the cursor within the current view |
| **PgUp/PgDn** | Move the cursor by 10 |
| **Enter** | Preview the rule under the cursor (tree leaf, motif example, diff-list rule or lineage child) as a live mini-simulation |
| **Space** | Pause/resume the preview |
| **a** / **b** / **d** | In the Diff view: mark rule A, mark rule B, compute the diff |
| **s** | Cycle sort order (score, classification, Hamming distance from Life) |
| **r** | Rebuild the analysis from the already loaded entries |
| **q / Esc** | Close the preview or diff; otherwise exit the mode |

### What to explore

- Look for the "Life core" motif (B{3} S{2,3}) — it appears in a surprising number of behaviorally interesting rules. Rules that share this motif tend to support gliders even when they differ in other positions.
- Compare the phylogenetic tree against your intuitions from Phase Space Navigator. Rules that are close in the tree should also be close in phase space, but behavioral distance can sometimes group syntactically distant rules together.
- Use the Lineage view after a long Genesis Protocol session to see which breeding mutations were productive vs neutral. Most single-bit mutations are behavioral no-ops, but flipping certain positions (especially B3, S2, S3) can cause dramatic phase transitions.
- The Diff view is particularly revealing for "near-miss" rule pairs — rules that differ by a single bit but behave completely differently. These are the phase boundaries of rule-space.

---

## Reverse Life

**Source:** `life/modes/reverse_life.py`

### Background

Reverse Life runs the Game of Life backwards. Given the pattern on the main grid, it searches for a predecessor: a configuration that produces the pattern after one step. It also detects Garden of Eden patterns, which have no predecessor.

### How it works

A constraint solver assigns each predecessor cell to alive or dead. Constraint propagation prunes impossible values, and backtracking resolves the rest. The solver uses the main grid's current birth/survival rule. The search covers the bounding box of the live cells grown by a pad of 2 cells (`+`/`-` change it, 0--10, and restart the search); cells outside the box stay dead. A pattern with no predecessor in that region is reported as a Garden of Eden. Rules that include B0 search the whole grid.

The solver runs as a generator, so the search is visible: candidate cells flicker, dead ends flash red, and a solution shows in green. `Space` starts and pauses the search; `s` cycles its speed (slow, medium, fast, instant). `Enter` accepts the solution as the new target, so you can step further back in time. `n` searches for a different predecessor once one is found.

### Controls

| Key | Action |
|-----|--------|
| **Space** | Start/pause the solver |
| **Enter** | Accept the solution as the new target and reverse again |
| **n** | Search for a different predecessor (after a solution is found) |
| **r** | Reset the solver, keeping the pattern |
| **+** / **-** | Grow / shrink the search pad (0--10) and restart |
| **g** | Run the solver to completion at instant speed (Garden of Eden check) |
| **s** | Cycle solver speed |
| **v** | Cycle view: solver, solution, overlay, diff |
| **c** | Toggle constraint-propagation display |
| **d** | Cycle display: cells, search tree, stats |
| **p** | Load the next preset pattern |
| **h** | Toggle help |
| **q** | Exit mode |

### What to explore

- Press `p` to cycle the presets (Block, two Blinker phases, Glider, Beehive, Loaf, Toad, Beacon, R-pentomino result) and solve each one.
- Accept a solution with `Enter` several times to walk a pattern back through time.
- Press `g` on a random pattern to check whether it is a Garden of Eden.
