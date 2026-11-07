# Classic Cellular Automata

The foundations of artificial life — discrete rule systems that generate complexity from simplicity.

---

## Game of Life

**Background.** Conway's Game of Life, devised by mathematician John Horton Conway in 1970, is the most widely studied cellular automaton. It runs on a two-dimensional grid with two states (alive or dead) and one deterministic rule. From these minimal ingredients come complex behavior, including self-replication and universal computation.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary by default (other topologies selectable)
States:     {0 = dead, 1 = alive}
Neighborhood: Moore (8 surrounding cells)

Let N(r,c) = number of alive neighbors of cell (r,c).

Transition rule (B3/S23):
  If cell is dead  and N(r,c) = 3:           cell becomes alive   (birth)
  If cell is alive and N(r,c) in {2, 3}:     cell stays alive     (survival)
  Otherwise:                                  cell becomes dead    (death)

Parameters:
  birth     = {3}      — set of neighbor counts that trigger birth
  survival  = {2, 3}   — set of neighbor counts that permit survival
```

**What to look for.** Stable structures (blocks, beehives), oscillators (blinkers, pulsars), and gliders that translate across the grid. Glider guns emit an endless stream of gliders, so the population can grow without bound. Random initial densities near 37% produce the richest transient dynamics. B3/S23 sits between rules that die out and rules that fill the plane, which makes it so generative.

**References.**
- Gardner, M. "Mathematical Games: The Fantastic Combinations of John Conway's New Solitaire Game 'Life'." *Scientific American*, 223(4), 1970. https://doi.org/10.1038/scientificamerican1070-120
- Berlekamp, E., Conway, J., & Guy, R. *Winning Ways for Your Mathematical Plays*, Vol. 2. Academic Press, 1982. https://en.wikipedia.org/wiki/Winning_Ways_for_your_Mathematical_Plays

---

## Wolfram 1D Automaton

**Background.** Stephen Wolfram's elementary cellular automata, systematically catalogued in the 1980s, operate on a one-dimensional array where each cell's next state depends on itself and its two immediate neighbors. Three binary inputs give 256 possible rules, yet the behavior ranges from trivial to universal. Matthew Cook proved Rule 110 computationally universal in 2004.

**Formulation.**

```
Grid:       1D array of width W, periodic boundary (wrapping)
States:     {0, 1}
Neighborhood: cell itself + left neighbor + right neighbor (3 cells)

The 3-cell neighborhood (left, center, right) forms a 3-bit index:
  idx = (left << 2) | (center << 1) | right    (range 0-7)

For rule number R (0-255), the output bit for pattern idx is:
  output = (R >> idx) & 1

The 8-bit binary representation of R is the complete lookup table:
  Patterns:  111  110  101  100  011  010  001  000
  Outputs:   R_7  R_6  R_5  R_4  R_3  R_2  R_1  R_0

Seed modes: "center" (single 1 in middle), "gol_row" (middle row of the Game of Life grid; center cell if empty), "random"
Each new row is the next generation and is drawn below the previous one.
```

**What to look for.** Rule 30 produces pseudorandom output from a single seed — Wolfram used it in Mathematica's random number generator. Rule 90 generates a perfect Sierpinski triangle (the XOR rule). Rule 110 supports gliders and localized structures that interact to perform computation. Rule 184 models single-lane traffic flow. Stepping through rules with Left/Right (or h/l) reveals the four Wolfram classes: fixed point, periodic, chaotic, and complex.

**References.**
- Wolfram, S. *A New Kind of Science*. Wolfram Media, 2002. https://www.wolframscience.com/nks/
- Cook, M. "Universality in Elementary Cellular Automata." *Complex Systems*, 15(1), 2004. https://doi.org/10.25088/ComplexSystems.15.1.1

---

## Langton's Ant

**Background.** Chris Langton described Langton's Ant in 1986. A single agent moves on a grid, turning and changing cell colors according to a rule string. The classic "RL" ant behaves chaotically for about 10,000 steps, then builds an endless diagonal highway.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary
States:     {0, 1, ..., len(rule)-1}   (one state per rule character)
Agent:      position (r, c) and direction d in {0=up, 1=right, 2=down, 3=left}

Rule string: sequence of R (right turn) and L (left turn) characters
             e.g., "RL" = classic Langton's Ant

At each step:
  1. Read cell color s = grid[r, c]
  2. Look up turn direction: rule[s mod len(rule)]
     If 'R': d = (d + 1) mod 4   (turn clockwise)
     If 'L': d = (d - 1) mod 4   (turn counterclockwise)
  3. Advance cell color: grid[r, c] = (s + 1) mod len(rule)
  4. Move forward one step in direction d

1-4 ants start symmetrically around the center (a single ant starts at the center).
Steps per frame: 1, 5, 10, 50, 100 or 500 (+/- keys, or the menu)
Rule: at least 2 characters, R or L only

Presets:
  RL, RLR, LLRR, LRRRRRLLR, RRLLLRLLLRRR, RRLL, RLLR, LRRL
```

**What to look for.** With "RL", watch the initial chaotic cloud resolve into a highway around step 10,000. Multi-character rules like "RLR" or "LLRR" produce symmetric, fractal-like patterns with intricate internal structure. Multiple ants interact through the shared grid. The highway appears from every starting pattern tried, but no one has proved that it always does.

**References.**
- Langton, C. "Studying Artificial Life with Cellular Automata." *Physica D*, 22(1-3), 1986. https://doi.org/10.1016/0167-2789(86)90237-X
- Gajardo, A., Moreira, A., & Goles, E. "Complexity of Langton's Ant." *Discrete Applied Mathematics*, 117, 2002. https://doi.org/10.1016/S0166-218X(01)00302-X

---

## Hexagonal Grid

**Background.** Hexagonal cellular automata replace the square lattice with a hexagonal tiling. Each cell has six equidistant neighbors instead of the Moore neighborhood's eight at two distances. The uniform distance removes some of the anisotropy of square grids.

**Formulation.**

```
Grid:       2D hexagonal lattice (offset rows), same boundary as the Game of Life grid
States:     {0 = dead, 1 = alive}
Neighborhood: 6 adjacent hexagonal cells (all equidistant)

Let N(r,c) = number of alive hex-neighbors of cell (r,c).

Default transition rule (B2/S34):
  If cell is dead  and N(r,c) = 2:             cell becomes alive   (birth)
  If cell is alive and N(r,c) in {3, 4}:       cell stays alive     (survival)
  Otherwise:                                    cell becomes dead    (death)

Turning hex mode off restores the square grid and Conway's rule:
  birth = {3}, survival = {2, 3}   (Conway B3/S23)
```

**What to look for.** Patterns look rounder than on the square grid because of the six-fold symmetry. Oscillators and still lifes take different forms. The mode switches to B2/S34, which suits six neighbors. Compare the same initial configuration on square vs. hexagonal grids to see how topology shapes emergent behavior.

**References.**
- Bays, C. "Cellular Automata in the Triangular Tessellation." *Complex Systems*, 8(2), 1994. https://doi.org/10.25088/ComplexSystems.8.2.127
- Wolfram, S. "Statistical Mechanics of Cellular Automata." *Reviews of Modern Physics*, 55(3), 1983. https://doi.org/10.1103/RevModPhys.55.601

---

## Wireworld

**Background.** Brian Silverman invented Wireworld in 1987. This four-state cellular automaton simulates digital logic circuits. Electrons travel along conductor paths, which allows gates, clocks, diodes, and even full adders.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary
States:     4 states:
  WW_EMPTY     = 0  (empty / background)
  WW_CONDUCTOR = 1  (wire / conductor)
  WW_HEAD      = 2  (electron head)
  WW_TAIL      = 3  (electron tail)
Neighborhood: Moore (8 cells)

Transition rules:
  Empty      -> Empty                          (always)
  Head       -> Tail                           (always)
  Tail       -> Conductor                      (always)
  Conductor  -> Head    if exactly 1 or 2 Moore neighbors are Head
  Conductor  -> Conductor  otherwise

Presets: Diode, Clock, OR gate, AND gate, XOR gate, Loop, Empty grid

Editing: move the cursor with the arrow keys (or hjkl) and toggle drawing with e.
  Brushes: conductor (1), electron head (2), electron tail (3), eraser (0)
  Enter cycles the cell under the cursor through empty, conductor, head, tail.
  r clears the grid.
```

**What to look for.** Electrons (head-tail pairs) propagate along conductor wires at one cell per generation. The "1 or 2 heads" condition lets signals merge at junctions, which logic gates rely on. Load a preset to watch signals propagate, or draw your own circuit from the Empty grid.

**References.**
- Silverman, B. Described in Dewdney, A. K. "Computer Recreations: The Cellular Automata Programs That Create Wireworld, Rugworld, and Other Diversions." *Scientific American*, 262(1), 1990. https://doi.org/10.1038/scientificamerican0190-146
- Rennard, J.-P. "Implementation of Logical Functions in the Game of Life." In *Collision-Based Computing*, Springer, 2002. https://doi.org/10.1007/978-1-4471-0129-1_18

---

## Cyclic CA

**Background.** David Griffeath introduced the Cyclic Cellular Automaton in the late 1980s. Cell states form a cycle, and a cell can only be overtaken by its immediate successor. This one-way competition produces rotating spiral waves, similar to those of the Belousov-Zhabotinsky reaction.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary
States:     {0, 1, 2, ..., n_states - 1}  arranged in a cycle
Neighborhood: Moore (8 cells) or Von Neumann (4 cells)

Let successor(s) = (s + 1) mod n_states.
Let count = number of neighbors in state successor(s).

Transition rule:
  If count >= threshold:
    cell advances: s -> successor(s)
  Else:
    cell remains in state s

Presets:            states  threshold  neighborhood
  Classic Spirals     8        1         Moore
  Fine Spirals       14        1         Moore
  Turbulent           5        1         Moore
  Slow Waves         16        1         Moore
  Von Neumann         8        1         Von Neumann
  High Threshold      8        3         Moore
  Minimal             4        1         Moore
  Crystalline         6        2         Von Neumann
```

**What to look for.** With threshold=1 and Moore neighborhood, beautiful rotating spirals emerge from random initial conditions within 50-100 generations. More states produce thinner, more intricate spiral arms. Higher thresholds require more neighbors to advance, producing blocky, crystalline patterns. Von Neumann neighborhoods give diamond-shaped wavefronts. Change the threshold (t/T) and the number of states (s/S) while running to move between spiral, turbulent, and frozen regimes.

**References.**
- Fisch, R., Gravner, J., & Griffeath, D. "Cyclic Cellular Automata in Two Dimensions." In *Spatial Stochastic Processes*, Birkhäuser, 1991. https://doi.org/10.1007/978-1-4612-0451-0_11
- Griffeath, D. "Self-Organization of Random Cellular Automata: Four Snapshots." In *Probability and Phase Transition*, Springer, 1994. https://doi.org/10.1007/978-94-015-8326-8_4

---

## Hodgepodge Machine

**Background.** Martin Gerhardt and Heike Schuster developed the Hodgepodge Machine in 1989 to model the Belousov-Zhabotinsky (BZ) chemical reaction. Each cell moves from healthy (0) through increasing stages of infection to ill, then resets to healthy. The model produces spiral and concentric waves like those seen in BZ reaction dishes.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary
States:     {0, 1, 2, ..., n-1}  where n = n_states
            0 = healthy, 1..n-2 = infected, n-1 = ill
Neighborhood: Moore (8 cells)

Three rules based on current state s:

  Healthy (s = 0):
    a = count of infected neighbors (0 < state < n-1)
    b = count of ill neighbors (state = n-1)
    new_state = min(floor(a/k1 + b/k2), n-1)

  Infected (0 < s < n-1):
    sum_s = s + sum of all non-zero neighbor states
    count = 1 + number of non-zero neighbors
    new_state = min(sum_s // count + g, n-1)   (integer division)

  Ill (s = n-1):
    new_state = 0   (recovery to healthy)

Presets:         n_states   k1   k2    g
  Classic Spirals   100      2    3    28
  Tight Spirals     200      1    2    45
  Target Waves      100      3    3    18
  Chaotic Mix        50      2    3    10
  Slow Waves        150      1    1    55
  Fast Reaction      60      3    4     8
  Crystal Growth     80      1    4    35
  Thin Filaments    255      2    3    80
```

**What to look for.** The parameter `g` sets how fast infection advances. Change it with g/G, and the state count with s/S. Parameters `k1` and `k2` govern how readily healthy cells become infected by their neighbors. With Classic Spirals (g=28), spiral arms emerge from random noise. Target Waves (k1=k2=3, g=18) produce expanding rings instead of spirals.

**References.**
- Gerhardt, M. & Schuster, H. "A Cellular Automaton Describing the Formation of Spatially Ordered Structures in Chemical Systems." *Physica D*, 36(3), 1989. https://doi.org/10.1016/0167-2789(89)90184-X
- Winfree, A. T. "Spiral Waves of Chemical Activity." *Science*, 175(4022), 1972. https://doi.org/10.1126/science.175.4022.634

---

## Lenia

**Background.** Bert Wang-Chak Chan developed Lenia in 2019. It generalizes the Game of Life to continuous values: cells hold real numbers between 0 and 1, a smooth ring-shaped kernel replaces the neighbor count, and a Gaussian growth function drives the update. The result can be lifelike patterns that glide, rotate, pulse, and replicate.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary
States:     continuous values A(r,c) in [0.0, 1.0]
Kernel:     ring-shaped, radius R, size (2R+1) x (2R+1)

Kernel function (normalized to sum = 1):
  K(dx, dy) = exp(-((d/R - 0.5) / 0.15)^2 / 2)    if d/R <= 1
              0                                       otherwise
  where d = sqrt(dx^2 + dy^2)

Convolution potential:
  U(r,c) = sum over kernel: K(dy, dx) * A(r + dy - R, c + dx - R)

Growth function (Gaussian bump):
  G(u) = 2 * exp(-((u - mu) / sigma)^2 / 2) - 1

Update rule:
  A(t + dt) = clamp(A(t) + dt * G(U), 0, 1)

Presets (name, R, mu, sigma, dt):
  Orbium            13   0.150   0.015   0.10
  Geminium          10   0.140   0.014   0.10
  Scutium           12   0.160   0.016   0.10
  Hydrogeminium     15   0.150   0.017   0.05
  Pentadecathlon     8   0.120   0.012   0.10
  Wanderer          10   0.130   0.020   0.08

Start: a few random smooth blobs near the center. Presets set only the
parameters, so a given species may not appear from every seed.
```

**What to look for.** The parameter `mu` sets the target local density for growth — cells with neighborhood potential near `mu` grow, others decay. Sigma controls the tolerance width. Orbium is the classic glider, a smooth moving organism. Geminium is known for splitting in two. Raising `mu` (u/U) favors denser patterns; widening `sigma` (s/S) tolerates more variation. The kernel radius R (d/D) sets the spatial scale of interaction, and dt (t/T) the step size.

**References.**
- Chan, B. W.-C. "Lenia: Biology of Artificial Life." *Complex Systems*, 28(3), 2019. https://doi.org/10.25088/ComplexSystems.28.3.251
- Chan, B. W.-C. "Lenia and Expanded Universe." *Proceedings of ALIFE 2020*, MIT Press, 2020. https://doi.org/10.1162/isal_a_00297

---

## Turmites

**Background.** A.K. Dewdney named turmites in 1989. They generalize Langton's Ant by giving the agent internal states. The agent reads the cell color, then a state-transition table gives the color to write, the turn, and the next internal state. Different tables produce spirals, growing squares, crystals, and chaotic scribbles.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary
Cell states: {0, 1, ..., num_colors - 1}
Agent:      position (r, c), direction d in {0,1,2,3}, internal state s

Transition table: table[s][color] = (write_color, turn, new_state)
  turn: 0 = no turn, 1 = right (clockwise), 2 = u-turn, 3 = left (counterclockwise)

At each step:
  1. Read color = grid[r, c]
  2. Look up (write_color, turn, new_state) = table[state][color]
  3. Write: grid[r, c] = write_color
  4. Turn:  d = (d + turn) mod 4
  5. Update state: s = new_state
  6. Move forward one step in direction d

Presets (name, colors, states, table), first five shown:
  Langton's Ant    2C 1S  [[(1,1,0), (0,3,0)]]
  Fibonacci Spiral 2C 2S  [[(1,1,1), (1,1,0)], [(1,0,0), (0,0,1)]]
  Square Builder   2C 2S  [[(1,1,0), (0,1,1)], [(1,3,1), (0,3,0)]]
  Snowflake        2C 3S  [[(1,1,1), (1,3,2)], [(1,1,0), (0,0,2)], [(1,3,0), (0,3,1)]]
  3-Color Spiral   3C 2S  [[(1,1,1), (2,3,0), (0,1,0)], [(2,1,0), (0,3,1), (1,3,1)]]

Five more presets: Chaos, Highway Builder, Spiral Growth, Diamond, Worm Trail.
One agent starts at the center. Steps per frame: 1, 5, 10, 50, 100 or 500 (+/-).
```

**What to look for.** Langton's Ant (1 state) produces the classic highway. Fibonacci Spiral (2 states) constructs logarithmic spiral arms. Square Builder fills a growing square region. The Snowflake preset (3 states) grows a symmetric crystal. Compare the 3-Color Spiral with the 2-color presets. Some presets need thousands of steps before structure appears; the step counter shows progress.

**References.**
- Dewdney, A. K. "Computer Recreations: Two-Dimensional Turing Machines and Tur-mites Make Tracks on a Plane." *Scientific American*, 261(3), 1989. https://doi.org/10.1038/scientificamerican0989-180
- Pegg, E. "Turmite." *MathWorld*, Wolfram Research. https://mathworld.wolfram.com/Turmite.html

---

## 3D Game of Life

**Background.** The 3D Game of Life runs the Game of Life in three dimensions. Each cell has 26 Moore neighbors, so the rules need different birth and survival counts. The mode renders the volume as ASCII by ray marching, with diffuse lighting, depth fog, and ambient occlusion. The camera orbits automatically.

**Formulation.**

```
Grid:       3D cubic lattice of size S x S x S (S = 20, non-wrapping boundaries)
States:     {0 = dead, 1 = alive}
Neighborhood: 3D Moore (26 neighbors: 3^3 - 1)

Let N(x,y,z) = number of alive neighbors among the 26 surrounding cells.

Transition rule:
  If cell is dead  and N(x,y,z) in birth_set:     cell becomes alive
  If cell is alive and N(x,y,z) in survive_set:    cell stays alive
  Otherwise:                                        cell becomes dead

Rendering:
  Camera: orbital (theta, phi, distance), auto-rotating
  Method: volumetric ray marching through voxel grid
  Shading: diffuse lighting + depth fog + ambient occlusion
  Shade characters: " .:-=+*#%@█" (11 brightness levels)

Initial seeding: random within central sphere (radius < 0.4 * grid_size),
                 density set per preset

Presets (birth / survival):
  Classic 3D     B5 / S45        Clouds    B5-7 / S4-6
  Crystal        B6 / S567       Amoeba    B5 / S3-5
  Diamoeba 3D    B5-7 / S5-8     Sparse    B6-8 / S5-7
  Pulse          B4 / S34        Builder   B6 / S456

Keys: arrows orbit, a toggles auto-rotate, +/- zoom, n steps
```

**What to look for.** 3D rules behave very differently from 2D due to the 26-neighbor count. Survival sets use higher counts (for example {4,5} rather than {2,3}) to suit the larger neighborhood. Watch for hollow shells, oscillators, and crystalline growth. Orbiting the camera reveals structure hidden from a single angle. Ambient occlusion darkens the inside of dense clusters, which gives depth cues in ASCII.

**References.**
- Bays, C. "Candidates for the Game of Life in Three Dimensions." *Complex Systems*, 1(3), 1987. https://doi.org/10.25088/ComplexSystems.1.3.373
- Bays, C. "A Note on the Game of Life in Hexagonal and Pentagonal Tessellations." *Complex Systems*, 15(3), 2005. https://doi.org/10.25088/ComplexSystems.15.3.245

---

## Hyperbolic Cellular Automata

**Background.** Hyperbolic cellular automata run on tilings of the hyperbolic plane, where the number of cells grows exponentially with distance. The mode draws the tiling as a Poincare disk, so cells shrink toward the boundary. Wavefronts branch exponentially, unlike on flat grids.

**Formulation.**

```
Geometry:   Poincare disk model of the hyperbolic plane
Tiling:     Schlafli symbol {p, q}: regular p-gons, q meeting at each vertex
Adjacency:  graph built via BFS with Mobius translation:
              z' = (z + a) / (1 + conj(a) * z)
            Center-to-center distance: r = tanh(acosh(cos(pi/q) / sin(pi/p)))

Hyperbolic distance (with w = |(z1 - z2) / (1 - conj(z1)*z2)|):
  d(z1, z2) = acosh(1 + 2 w^2 / (1 - w^2))

Available tilings:
  {5,4}  Pentagonal     4 pentagons per vertex
  {7,3}  Heptagonal     3 heptagons per vertex
  {4,5}  Square         5 squares per vertex
  {3,7}  Triangular     7 triangles per vertex
  {6,4}  Hexagonal      4 hexagons per vertex
  {8,3}  Octagonal      3 octagons per vertex

Neighbors: the cells sharing an edge (up to p per cell)
CA rule: totalistic (birth/survival sets on neighbor count)
  B3/S23 (Life), B2/S34 (Pulse), B3/S234 (Coral), B35/S2345 (Bloom),
  B2/S23 (Spread), B3/S345 (Hardy), B23/S34 (Wave), B2/S (Seeds)

Start: about 30% of the cells within |z| < 0.5 are alive.
Keys: n next rule, t next tiling, r randomize, c clear, s step, +/- speed

Tiling generation: 6 BFS layers, cells clipped at |z| > 0.96
```

**What to look for.** The same B3/S23 rule behaves differently here than on a flat grid, because the cell count grows exponentially with distance. Bloom (B35/S2345) fills the disk quickly. Cells near the boundary look smaller, but all cells are the same size in hyperbolic geometry. Each cell has p neighbors, so compare {3,7} (3 neighbors) with {8,3} (8 neighbors) to see how connectivity changes the dynamics.

**References.**
- Margenstern, M. "A Weakly Universal Cellular Automaton in the Heptagrid of the Hyperbolic Plane." *Complex Systems* 27(4), 2018. https://doi.org/10.25088/ComplexSystems.27.4.377
- Margenstern, M. *Cellular Automata in Hyperbolic Spaces*. Old City Publishing, 2007. https://www.worldcat.org/oclc/144331358

---

## Graph Cellular Automata

**Background.** Graph Cellular Automata move cellular automata from regular lattices to network topologies. Cells sit on the nodes of a graph, and edges define neighborhoods. This shows how network structure shapes the dynamics.

**Formulation.**

```
Graph:      N nodes (30-120 by default, scaled to the terminal; +/- changes it by 10) with adjacency from the topology generator
States:     {alive, dead} with age tracking
Neighborhood: all nodes connected by an edge

Transition rule: standard totalistic (birth/survival on neighbor count)
  For node i with live_neighbors = |{j in adj(i) : state(j) = alive}|:
    Dead  -> Alive  if live_neighbors in birth_set
    Alive -> Alive  if live_neighbors in survive_set
    Otherwise -> Dead

Available topologies:
  Ring Lattice     each node connected to K=4 nearest on a ring
  Small-World (WS) Watts-Strogatz: ring + random rewiring (p=0.3)
  Scale-Free (BA)  Barabasi-Albert preferential attachment (m=2)
  Random (ER)      Erdos-Renyi, edge probability p=0.08
  Star Graph       central hub connected to all others
  Binary Tree      complete binary tree
  Grid 2D          square lattice without wrapping (for comparison)
  Caveman Graph    cliques of size 5 connected in a ring

Rules (birth/survival): B3/S23 (Life), B2/S34 (Pulse), B3/S234 (Coral),
  B23/S3 (Sparse), B1/S12 (Dense), B2/S23 (Spread), B34/S345 (Hardy),
  B2/S (Seeds)

Start: each node is alive with probability 0.3.
Keys: n next rule, t next topology, r randomize, c clear, s step,
  e toggle edges, m toggle metrics, l re-layout, +/- node count

Layout: force-directed (Fruchterman-Reingold style)
  Repulsion: F_rep = k^2 / d    (k = sqrt(1/N))
  Attraction: F_att = d^2 / k   (along edges only)
  Cooling: temperature *= 0.95 per iteration (starts at 0.1)

Live metrics: clustering coefficient, average path length,
              degree distribution, population history sparkline
```

**What to look for.** The same rule behaves very differently on different topologies. Hubs in scale-free networks and the center of a star graph see many neighbors, so their state follows the birth and survival sets differently from low-degree nodes. Short average path lengths in small-world networks let activity cross the graph quickly. Compare the clustering coefficient with how long patterns persist. Toggle edges with e to see the layout without clutter.

**References.**
- Watts, D. & Strogatz, S. "Collective Dynamics of 'Small-World' Networks." *Nature*, 393, 1998. https://doi.org/10.1038/30918
- Marr, C. & Hutt, M.-T. "Topology Regulates Pattern Formation Capacity of Binary Cellular Automata on Graphs." *Physica A*, 354, 2005. https://doi.org/10.1016/j.physa.2005.02.032
