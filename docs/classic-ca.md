# Classic Cellular Automata

The foundations of artificial life — discrete rule systems that generate complexity from simplicity.

---

## Game of Life

**Background.** Conway's Game of Life, devised by mathematician John Horton Conway in 1970, is the most widely studied cellular automaton. Operating on a two-dimensional grid with only two states (alive or dead) and a single deterministic rule, it demonstrates that extraordinarily complex behavior — self-replication, computation, even universal Turing-completeness — can emerge from minimal ingredients. It remains a cornerstone of complexity science, recreational mathematics, and theoretical computer science.

**Formulation.**

```
Grid:       2D square lattice, toroidal boundary conditions
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

**What to look for.** Stable structures (blocks, beehives), oscillators (blinkers, pulsars), and gliders that translate across the grid. Glider guns produce an infinite stream of gliders, proving the system supports unbounded growth. Random initial densities near 37% produce the richest transient dynamics. The B3/S23 rule sits at a critical boundary between rules that die out and rules that fill the plane — this edge-of-chaos position is what makes it so generative.

**References.**
- Gardner, M. "Mathematical Games: The Fantastic Combinations of John Conway's New Solitaire Game 'Life'." *Scientific American*, 223(4), 1970. https://doi.org/10.1038/scientificamerican1070-120
- Berlekamp, E., Conway, J., & Guy, R. *Winning Ways for Your Mathematical Plays*, Vol. 2. Academic Press, 1982. https://en.wikipedia.org/wiki/Winning_Ways_for_your_Mathematical_Plays

---

## Wolfram 1D Automaton

**Background.** Stephen Wolfram's elementary cellular automata, systematically catalogued in the 1980s, operate on a one-dimensional array where each cell's next state depends on itself and its two immediate neighbors. Despite this extreme simplicity — 3 binary inputs yielding 256 possible rules — the system spans the full spectrum from trivial to Turing-complete. Rule 110 was proven computationally universal by Matthew Cook in 2004, making it perhaps the simplest known system capable of arbitrary computation.

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

Seed modes: "center" (single 1 in middle), "random", "gol_row" (from GoL grid)
```

**What to look for.** Rule 30 produces pseudorandom output from a single seed — Wolfram used it in Mathematica's random number generator. Rule 90 generates a perfect Sierpinski triangle (the XOR rule). Rule 110 supports gliders and localized structures that interact to perform computation. Rule 184 models single-lane traffic flow. Cycling through rules with arrow keys reveals the four Wolfram classes: fixed point, periodic, chaotic, and complex.

**References.**
- Wolfram, S. *A New Kind of Science*. Wolfram Media, 2002. https://www.wolframscience.com/nks/
- Cook, M. "Universality in Elementary Cellular Automata." *Complex Systems*, 15(1), 2004. https://doi.org/10.25088/ComplexSystems.15.1.1

---

## Langton's Ant

**Background.** Conceived by Chris Langton in 1986, Langton's Ant is a two-dimensional Turing machine where a single agent moves on a grid, turning and flipping cell colors according to a simple rule string. The classic "RL" ant exhibits a remarkable phase transition: after approximately 10,000 steps of seemingly chaotic behavior, it spontaneously constructs an infinite diagonal highway. This emergent order from chaos remains one of the most striking demonstrations of self-organization in discrete systems.

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

Supports 1-4 simultaneous ants placed symmetrically around center.
Steps per frame: adjustable (1, 5, 10, 50, 100, 500)
```

**What to look for.** With "RL", watch the initial chaotic cloud resolve into a highway around step 10,000. Multi-character rules like "RLR" or "LLRR" produce symmetric, fractal-like patterns with intricate internal structure. Multiple ants interact through the shared grid state, creating interference patterns. The transition from disorder to order is robust — it occurs regardless of initial grid state, a fact that remains unproven mathematically.

**References.**
- Langton, C. "Studying Artificial Life with Cellular Automata." *Physica D*, 22(1-3), 1986. https://doi.org/10.1016/0167-2789(86)90237-X
- Gajardo, A., Moreira, A., & Goles, E. "Complexity of Langton's Ant." *Discrete Applied Mathematics*, 117, 2002. https://doi.org/10.1016/S0166-218X(01)00302-X

---

## Hexagonal Grid

**Background.** Hexagonal cellular automata replace the standard square lattice with a hexagonal tiling, giving each cell exactly six equidistant neighbors instead of the Moore neighborhood's eight (at varying distances). This geometry is widespread in nature — basalt columns, honeycomb, and retinal cells all exhibit hexagonal packing. The uniform neighbor distance eliminates the anisotropy inherent in square grids, producing more isotropic growth patterns and different stability characteristics.

**Formulation.**

```
Grid:       2D hexagonal lattice (offset coordinate representation)
States:     {0 = dead, 1 = alive}
Neighborhood: 6 adjacent hexagonal cells (all equidistant)

Let N(r,c) = number of alive hex-neighbors of cell (r,c).

Default transition rule (B2/S34):
  If cell is dead  and N(r,c) = 2:             cell becomes alive   (birth)
  If cell is alive and N(r,c) in {3, 4}:       cell stays alive     (survival)
  Otherwise:                                    cell becomes dead    (death)

On exit, grid reverts to standard square rules:
  birth = {3}, survival = {2, 3}   (Conway B3/S23)
```

**What to look for.** Patterns are more rounded and organic than their square-grid counterparts due to the six-fold symmetry. Oscillators and still lifes take different forms — the hex "beehive" is a natural stable structure. The B2/S34 rule was chosen to produce interesting dynamics on six neighbors (Conway's B3/S23 is too sparse for hex grids). Compare the same initial configuration on square vs. hexagonal grids to see how topology shapes emergent behavior.

**References.**
- Bays, C. "Cellular Automata in the Triangular Tessellation." *Complex Systems*, 8(2), 1994. https://doi.org/10.25088/ComplexSystems.8.2.127
- Wolfram, S. "Statistical Mechanics of Cellular Automata." *Reviews of Modern Physics*, 55(3), 1983. https://doi.org/10.1103/RevModPhys.55.601

---

## Wireworld

**Background.** Wireworld, invented by Brian Silverman in 1987, is a four-state cellular automaton designed specifically for simulating digital logic circuits. Electrons propagate along conductor paths, enabling the construction of AND, OR, and NOT gates, clocks, diodes, and even full adders. Unlike the Game of Life's biological metaphor, Wireworld provides a direct, intuitive model of electronic computation, making it a powerful pedagogical tool for understanding how physical systems implement Boolean logic.

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

Drawing interface provides cursor-based circuit editing:
  Brushes: conductor (1), electron head (2), electron tail (3), eraser (0)
```

**What to look for.** Electrons (head-tail pairs) propagate along conductor wires at one cell per generation. A single-cell gap creates a diode (one-way propagation). T-junctions route signals. The constraint "1 or 2 heads" is critical — it prevents backward propagation while allowing signal merging for logic gates. Load a preset circuit to watch clock pulses propagate, or draw your own logic gates from scratch.

**References.**
- Silverman, B. Described in Dewdney, A. K. "Computer Recreations: The Cellular Automata Programs That Create Wireworld, Rugworld, and Other Diversions." *Scientific American*, 262(1), 1990. https://doi.org/10.1038/scientificamerican0190-146
- Rennard, J.-P. "Implementation of Logical Functions in the Game of Life." In *Collision-Based Computing*, Springer, 2002. https://doi.org/10.1007/978-1-4471-0129-1_18

---

## Cyclic Cellular Automaton

**Background.** The Cyclic Cellular Automaton, introduced by David Griffeath in the late 1980s, models systems where states advance through a fixed cycle — each state can only be consumed by its immediate successor. This asymmetric predator-prey dynamic spontaneously generates rotating spiral waves reminiscent of the Belousov-Zhabotinsky chemical reaction. The system demonstrates how simple local competition rules can produce large-scale self-organized spatial patterns, connecting cellular automata to excitable media theory.

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

**What to look for.** With threshold=1 and Moore neighborhood, beautiful rotating spirals emerge from random initial conditions within 50-100 generations. More states produce thinner, more intricate spiral arms. Higher thresholds require more neighbors to advance, producing blocky, crystalline patterns. Von Neumann neighborhoods yield diamond-shaped wavefronts instead of circular ones. Adjusting states and threshold in real time reveals phase transitions between spiral, turbulent, and frozen regimes.

**References.**
- Fisch, R., Gravner, J., & Griffeath, D. "Cyclic Cellular Automata in Two Dimensions." In *Spatial Stochastic Processes*, Birkhäuser, 1991. https://doi.org/10.1007/978-1-4612-0451-0_11
- Griffeath, D. "Self-Organization of Random Cellular Automata: Four Snapshots." In *Probability and Phase Transition*, Springer, 1994. https://doi.org/10.1007/978-94-015-8326-8_4

---

## Hodgepodge Machine

**Background.** The Hodgepodge Machine, developed by Martin Gerhardt and Heike Schuster in 1989, is a cellular automaton that models the Belousov-Zhabotinsky (BZ) chemical reaction — the first experimentally observed chemical oscillator. Cells pass through a continuous infection cycle from healthy (0) through increasingly infected states to terminally ill, then reset to healthy. The model produces self-organizing spiral waves that closely match the concentric and rotating patterns seen in real BZ reaction dishes, bridging discrete computation and physical chemistry.

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
    new_state = min(floor(sum_s / count) + g, n-1)

  Ill (s = n-1):
    new_state = 0   (recovery to healthy)

Parameters:      n_states   k1   k2    g
  Classic Spirals   100      2    3    28
  Tight Spirals     200      1    2    45
  Target Waves      100      3    3    18
  Chaotic Mix        50      2    3    10
  Slow Waves        150      1    1    55
  Fast Reaction      60      3    4     8
  Crystal Growth     80      1    4    35
  Thin Filaments    255      2    3    80
```

**What to look for.** The parameter `g` controls the speed of infection progression — higher values produce faster, tighter spirals. Parameters `k1` and `k2` govern how readily healthy cells become infected by their neighbors. With Classic Spirals (g=28), watch self-organizing spiral arms emerge from random noise within 20-30 generations. "Target Waves" (higher k values) produce expanding concentric rings instead of spirals. The transition from spirals to target waves to chaos as parameters change mirrors real chemical reaction phase diagrams.

**References.**
- Gerhardt, M. & Schuster, H. "A Cellular Automaton Describing the Formation of Spatially Ordered Structures in Chemical Systems." *Physica D*, 36(3), 1989. https://doi.org/10.1016/0167-2789(89)90184-X
- Winfree, A. T. "Spiral Waves of Chemical Activity." *Science*, 175(4022), 1972. https://doi.org/10.1126/science.175.4022.634

---

## Lenia

**Background.** Lenia, developed by Bert Wang-Chak Chan in 2019, generalizes Conway's Game of Life from discrete states to continuous space. Cells hold real values between 0 and 1, a smooth ring-shaped convolution kernel replaces the discrete neighbor count, and a Gaussian growth function governs the dynamics. The result is strikingly organic: Lenia produces self-organizing lifeforms that glide, rotate, pulse, and even self-replicate with a biological realism unprecedented in cellular automata. It has been called "the missing link between cellular automata and artificial life."

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
  Smooth Life       15   0.170   0.020   0.08
  Hydrogeminium      8   0.130   0.013   0.12
  Scutium           12   0.160   0.018   0.10
```

**What to look for.** The parameter `mu` sets the target local density for growth — cells with neighborhood potential near `mu` grow, others decay. Sigma controls the tolerance width. Orbium is the classic glider: a smooth, moving organism. Geminium self-replicates by splitting. Adjusting `mu` upward makes organisms denser; adjusting `sigma` wider makes them more tolerant of density variation. The kernel radius R determines the spatial scale of interaction. Watch how organisms maintain coherent identity while continuously updating — a key property of biological life.

**References.**
- Chan, B. W.-C. "Lenia: Biology of Artificial Life." *Complex Systems*, 28(3), 2019. https://doi.org/10.25088/ComplexSystems.28.3.251
- Chan, B. W.-C. "Lenia and Expanded Universe." *Proceedings of ALIFE 2020*, MIT Press, 2020. https://doi.org/10.1162/isal_a_00297

---

## Turmites

**Background.** Turmites, named by A.K. Dewdney in 1989, generalize Langton's Ant by giving the agent internal states. The ant reads the cell color, consults a state-transition table to decide what color to write, which direction to turn, and what internal state to enter next. This makes turmites equivalent to two-dimensional Turing machines. Different transition tables produce a remarkable variety of emergent behavior — from Fibonacci spirals and growing squares to snowflake-like crystals and chaotic scribbling — all from deterministic table lookups.

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

Example presets (name, colors, states, table):
  Langton's Ant    2C 1S  [[(1,1,0), (1,3,0)]]
  Fibonacci Spiral 2C 2S  [[(1,1,1), (1,1,0)], [(1,0,0), (0,0,1)]]
  Square Builder   2C 2S  [[(1,1,0), (0,1,1)], [(1,3,1), (0,3,0)]]
  Snowflake        2C 3S  [[(1,1,1), (1,3,2)], [(1,1,0), (0,0,2)], [(1,3,0), (0,3,1)]]
  3-Color Spiral   3C 2S  [[(1,1,1), (2,3,0), (0,1,0)], [(2,1,0), (0,3,1), (1,3,1)]]
```

**What to look for.** Langton's Ant (1 state) produces the classic highway. Fibonacci Spiral (2 states) constructs logarithmic spiral arms. Square Builder fills a growing square region. The Snowflake preset (3 states) grows a symmetric crystal. Compare the 3-Color Spiral's output to the simpler 2-color presets — additional colors dramatically expand the behavioral repertoire. The step counter shows how many iterations are needed before recognizable structure emerges; some presets require thousands of steps.

**References.**
- Dewdney, A. K. "Computer Recreations: Two-Dimensional Turing Machines and Tur-mites Make Tracks on a Plane." *Scientific American*, 261(3), 1989. https://doi.org/10.1038/scientificamerican0989-180
- Pegg, E. "Turmite." *MathWorld*, Wolfram Research. https://mathworld.wolfram.com/Turmite.html

---

## 3D Game of Life

**Background.** The 3D Game of Life extends Conway's cellular automaton into three-dimensional space, where each cell has 26 Moore neighbors (the surrounding cube minus itself). The vastly larger neighborhood requires different birth/survival thresholds to produce interesting dynamics. This implementation renders the volumetric simulation via ASCII ray casting with diffuse lighting, depth fog, and ambient occlusion — a full 3D graphics pipeline running entirely in the terminal. The camera orbits automatically, revealing the evolving structure from all angles.

**Formulation.**

```
Grid:       3D cubic lattice of size S x S x S (non-wrapping boundaries)
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
  Shade characters: " .:-=+*#%@" (10 brightness levels)

Initial seeding: random within central sphere (radius < 0.4 * grid_size),
                 density set per preset
```

**What to look for.** 3D rules behave very differently from 2D due to the 26-neighbor count. Survival sets typically include higher values (e.g., {4,5} rather than {2,3}) to compensate for the larger neighborhood. Watch for hollow shell structures, 3D oscillators, and crystalline growth. The auto-rotating camera reveals internal structure invisible from any single angle. The ambient occlusion shading makes dense clusters appear darker inside, providing depth cues in pure ASCII. Population counts fluctuate more dramatically than in 2D as structures are inherently less stable.

**References.**
- Bays, C. "Candidates for the Game of Life in Three Dimensions." *Complex Systems*, 1(3), 1987. https://doi.org/10.25088/ComplexSystems.1.3.373
- Bays, C. "A Note on the Game of Life in Hexagonal and Pentagonal Tessellations." *Complex Systems*, 15(3), 2005. https://doi.org/10.25088/ComplexSystems.15.3.245

---

## Hyperbolic Cellular Automata

**Background.** Hyperbolic cellular automata run on tilings of the hyperbolic plane — the negatively curved non-Euclidean geometry where the parallel postulate fails and the number of cells grows exponentially with distance. Rendered as a Poincare disk, these automata produce patterns impossible on flat grids: exponentially branching wavefronts, infinite-degree neighborhoods, and conformal shrinkage toward the disk boundary. The system combines two deep mathematical structures — hyperbolic geometry and cellular automata — revealing how curvature fundamentally alters emergent dynamics.

**Formulation.**

```
Geometry:   Poincare disk model of the hyperbolic plane
Tiling:     Schlafli symbol {p, q}: regular p-gons, q meeting at each vertex
Adjacency:  graph built via BFS with Mobius translation:
              z' = (z + a) / (1 + conj(a) * z)
            Center-to-center distance: r = tanh(acosh(cos(pi/q) / sin(pi/p)))

Hyperbolic distance:
  d(z1, z2) = acosh(1 + 2|z1-z2|^2 / ((1 - |z1-z2/(1-conj(z1)*z2)|^2)))

Available tilings:
  {5,4}  Pentagonal     4 pentagons per vertex
  {7,3}  Heptagonal     3 heptagons per vertex
  {4,5}  Square         5 squares per vertex
  {3,7}  Triangular     7 triangles per vertex
  {6,4}  Hexagonal      4 hexagons per vertex
  {8,3}  Octagonal      3 octagons per vertex

CA rule: standard totalistic (birth/survival sets on neighbor count)
  B3/S23 (Life), B2/S34 (Pulse), B3/S234 (Coral), B35/S2345 (Bloom),
  B2/S23 (Spread), B3/S345 (Hardy), B23/S34 (Wave), B2/S{} (Seeds)

Tiling generation: 6 BFS layers, cells clipped at |z| > 0.96
```

**What to look for.** The same B3/S23 rule behaves very differently on hyperbolic tilings than on flat grids because the exponential growth of neighborhoods means signals spread much faster. "Bloom" (B35/S2345) fills the disk rapidly due to the high neighbor counts. Cells near the disk boundary appear smaller (conformal mapping) — this faithfully represents the hyperbolic geometry where equal-area cells appear increasingly compressed. Compare {5,4} (dense, many neighbors) to {7,3} (sparse, fewer neighbors per vertex) to see how local connectivity reshapes global dynamics.

**References.**
- Margenstern, M. "A Weakly Universal Cellular Automaton in the Heptagrid of the Hyperbolic Plane." *Complex Systems* 27(4), 2018. https://doi.org/10.25088/ComplexSystems.27.4.377
- Margenstern, M. *Cellular Automata in Hyperbolic Spaces*. Old City Publishing, 2007. https://www.worldcat.org/oclc/144331358

---

## Graph Cellular Automata

**Background.** Graph Cellular Automata generalize the concept of a cellular automaton from regular lattices to arbitrary network topologies. Instead of a grid, cells live on the nodes of a graph — small-world networks, scale-free networks, random graphs, trees, or star topologies — with edges defining neighborhoods. This framework connects CA dynamics to network science, revealing how topology shapes information flow, synchronization, and pattern formation. It directly models processes on real-world networks: disease spread on social networks, signal propagation in neural circuits, and opinion dynamics in communities.

**Formulation.**

```
Graph:      N nodes with adjacency defined by topology generator
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
  Grid 2D          standard square lattice (for comparison)
  Caveman Graph    cliques of size 5 connected in a ring

Layout: force-directed (Fruchterman-Reingold style)
  Repulsion: F_rep = k^2 / d    (k = sqrt(1/N))
  Attraction: F_att = d^2 / k   (along edges only)
  Cooling: temperature *= 0.95 per iteration

Live metrics: clustering coefficient, average path length,
              degree distribution, population history sparkline
```

**What to look for.** The same CA rule produces dramatically different dynamics on different topologies. On scale-free networks, high-degree hub nodes act as super-spreaders — a single activated hub can trigger cascading birth across the entire network. Small-world networks show rapid global synchronization due to their short average path lengths. Star graphs exhibit centralized control: the hub's state dominates. Compare the clustering coefficient (how clique-like the neighborhood is) with the CA's ability to sustain stable structures — high clustering tends to support persistent patterns. Toggle edges on/off to see how the network structure itself shapes what emerges.

**References.**
- Watts, D. & Strogatz, S. "Collective Dynamics of 'Small-World' Networks." *Nature*, 393, 1998. https://doi.org/10.1038/30918
- Marr, C. & Hutt, M.-T. "Topology Regulates Pattern Formation Capacity of Binary Cellular Automata on Graphs." *Physica A*, 354, 2005. https://doi.org/10.1016/j.physa.2005.02.032
