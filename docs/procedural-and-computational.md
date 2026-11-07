# Procedural & Computational

Algorithms made visible — from constraint solving to ray marching, neural networks to digital evolution.

---

## Wave Function Collapse

**Background**

Wave Function Collapse (WFC) is a constraint-satisfaction algorithm inspired by quantum mechanics and first described by Maxim Gumin in 2016. Originally developed for procedural texture synthesis, it generates globally coherent patterns from local adjacency rules. The algorithm is widely used in game development for procedurally generating tile maps, dungeon layouts, and texture patterns.

**Formulation**

```
Given:
  T          = set of tile types {0, 1, ..., N-1}
  A(t, d)    = set of tiles allowed adjacent to tile t in direction d
               where d in {N, S, E, W}
  grid[r][c] = set of possible tiles for cell (r, c), initially T

Algorithm (one step):
  1. OBSERVE: find uncollapsed cell with minimum entropy
     entropy(r, c) = |grid[r][c]|
     candidates = {(r, c) : collapsed[r][c] == -1 and entropy is minimal}

  2. COLLAPSE: pick random cell from candidates, pick random tile from its possibilities
     grid[r][c] = {tile}

  3. PROPAGATE (stack-based, starting at the collapsed cell):
     for each uncollapsed neighbor (nr, nc) in direction d:
       allowed = union of A(t, d) for all t in grid[r][c]
       grid[nr][nc] = grid[nr][nc] intersect allowed
       if |grid[nr][nc]| == 0: CONTRADICTION
       if |grid[nr][nc]| reduced:
         if |grid[nr][nc]| == 1: mark the cell collapsed
         continue propagating from (nr, nc)

Adjacency symmetry is enforced:
  if B in A(A_tile, N) then A_tile in A(B, S)
```

**What to look for**

Uncollapsed cells show how many tiles they still allow: `▓▓` for four or more, `▒▒` for three, `░░` for two, `!!` for one. A contradiction occurs when no valid tile remains for a cell. The run then stops, and `r` restarts it. The six presets (Island, Coastline, Village, Maze, Terrain, Dungeon) use different tile sets and adjacency rules, so the same algorithm gives very different layouts. `Space` runs, `n` steps, and `s`/`S` raise or lower the steps per frame.

**References**

- Gumin, M. "WaveFunctionCollapse." GitHub repository, 2016. https://github.com/mxgmn/WaveFunctionCollapse
- Karth, I. and Smith, A.M. "WaveFunctionCollapse is Constraint Solving in the Wild." *Proceedings of FDG*, 2017. https://doi.org/10.1145/3102071.3110566

---

## Maze Generation

**Background**

Maze generation algorithms construct perfect mazes -- connected graphs where exactly one path exists between any two cells. Three generators are implemented: the recursive backtracker (depth-first search), Prim's algorithm (randomized minimum spanning tree), and Kruskal's algorithm (edge merging with disjoint sets). Four solvers then run on the finished maze: A*, Dijkstra, BFS and DFS. The six presets pair them as Classic DFS + A*, Prim + Dijkstra, Kruskal + BFS, Backtracker + DFS, Prim + A*, and Kruskal + Dijkstra.

**Formulation**

```
Grid: odd-dimensioned array where odd-indexed cells are passages, even-indexed are walls.

Recursive Backtracker (DFS):
  1. Start at cell (1,1), mark visited, push onto stack
  2. While stack not empty:
     - current = stack.top()
     - neighbors = unvisited cells 2 steps away (N/S/E/W)
     - if neighbors exist:
         pick random neighbor (nr, nc)
         carve wall between current and neighbor
         mark neighbor visited, push onto stack
     - else: pop stack (backtrack)

Prim's Algorithm:
  1. Start at cell (1,1), add frontier edges
  2. While frontier edges exist:
     - pick random edge (from, to)
     - if 'to' unvisited: carve wall, add new frontier edges from 'to'

Kruskal's Algorithm:
  1. Mark all odd-indexed cells as passages, assign unique set IDs
  2. List all possible edges between adjacent passages, shuffle
  3. For each edge (c1, c2):
     - if set(c1) != set(c2): carve wall, merge sets

Pathfinding (after generation):
  A*:       f(n) = g(n) + h(n), where h = Manhattan distance to end
  Dijkstra: f(n) = g(n), uniform cost
  BFS:      FIFO queue, guarantees shortest path
  DFS:      LIFO stack, explores deeply before backtracking
```

**What to look for**

The recursive backtracker produces long, winding corridors with a bias toward depth. Prim's algorithm creates shorter, more branching passages. Kruskal's algorithm joins random cell pairs, so it grows the maze everywhere at once. During solving, compare how A* (guided by the Manhattan distance heuristic) explores fewer cells than Dijkstra or BFS to find the shortest path. Explored cells and the final solution path are drawn in different styles. `Space` plays, `n` steps, `s`/`S` change the steps per frame, `r` reseeds, and `R` returns to the menu.

**References**

- Buck, J. *Mazes for Programmers.* Pragmatic Bookshelf, 2015. https://pragprog.com/titles/jbmaze/mazes-for-programmers/
- Cormen, T.H. et al. *Introduction to Algorithms,* 3rd ed. MIT Press, 2009. (Ch. 22-24: Graph algorithms) https://mitpress.mit.edu/books/introduction-algorithms-third-edition

---

## Voronoi Diagram

**Background**

Voronoi diagrams partition space into regions closest to a set of seed points, a construction first studied by Dirichlet (1850) and formalized by Voronoi (1908). This implementation models crystal growth: seeds expand outward with anisotropic growth rates determined by preferred crystallographic angles, producing realistic grain boundary patterns found in metals and ceramics.

**Formulation**

```
Parameters:
  seeds[i]  = (r, c)         position of seed i
  angle[i]  = theta           preferred growth direction (radians)
  aniso     = A in [0, 0.9]   anisotropy strength

Growth probability for frontier cell (r, c) belonging to grain i:
  dr = r - seeds[i].r
  dc = c - seeds[i].c
  angle_to_cell = atan2(dr, dc)
  diff = |angle_to_cell - angle[i]|
  if diff > pi: diff = 2*pi - diff

  P(claim) = max(0.1, 1.0 - A * diff / pi)

Each step:
  1. Shuffle frontier randomly (ensures natural growth)
  2. For each frontier cell: claim with probability P
  3. Claimed cells add their unclaimed 8-neighbors to frontier

Grain boundary detection:
  Cell (r, c) is a boundary if any 8-neighbor belongs to a different grain.

Seed placement modes: random, edge, bicrystal, center
```

**What to look for**

With anisotropy at zero, grains grow as roughly circular Voronoi cells. As anisotropy increases, grains elongate along their preferred angles, producing faceted crystals resembling real metallographic micrographs. Grain boundaries (highlighted as distinct characters) form triple junctions where three grains meet, a universal feature of polycrystalline materials. The Bicrystal preset, with just two seeds, shows a single grain boundary. The other presets are Fine Microstructure, Coarse Grains, Columnar Growth, Dendritic Arms, Isotropic Foam, Sparse Nucleation and Radial Burst. `a`/`A` raise or lower the anisotropy while it runs, and `+`/`-` change the steps per frame.

**References**

- Aurenhammer, F. "Voronoi Diagrams: A Survey of a Fundamental Geometric Data Structure." *ACM Computing Surveys* 23(3), 1991. https://doi.org/10.1145/116873.116880
- Anderson, M.P. et al. "Computer Simulation of Grain Growth -- I. Kinetics." *Acta Metallurgica* 32(5), 1984. https://doi.org/10.1016/0001-6160(84)90151-2

---

## Terrain Generation

**Background**

Procedural terrain generation combines layered noise functions with geological erosion simulation to produce realistic landscapes. The technique originates from Perlin's gradient noise (1985) and has been extended with hydraulic and thermal erosion models used in films and games. This implementation couples tectonic uplift, thermal weathering, hydraulic erosion, and vegetation dynamics into a continuous geological simulation.

**Formulation**

```
Terrain generation (layered value noise):
  height(r, c) = sum over octaves:
    smooth_noise(frequency_i, amplitude_i)
  where each octave uses bilinear interpolation on a sparse random grid.
  Typical octave stack: freq = {3, 6, 12, 24}, amp = {0.5, 0.3, 0.15, 0.05}

Tectonic uplift (per step):
  factor(r, c) = max(0.2, 1.0 - 0.6 * dist_to_center / max_dist)
  h(r, c) += uplift_rate * factor * (0.8 + 0.4 * rand())

Thermal erosion (talus slope failure):
  talus_threshold = 0.06
  for each neighbor (nr, nc):
    diff = h(r,c) - h(nr,nc)
    if diff > talus_threshold:
      veg_factor = max(0.1, 1.0 - vegetation(r,c) * 0.8)
      hard_factor = 1.0 / (0.5 + hardness(r,c))
      transfer = thermal_rate * (diff - threshold) * 0.5 * veg_factor * hard_factor
      h(r,c) -= transfer;  h(nr,nc) += transfer

Hydraulic erosion (rain-driven):
  Find steepest downhill neighbor
  erode_amt = rain_rate * slope * veg_factor * noise
  Deposit 60% downstream, 40% lost to sea (net sediment transport)

Vegetation dynamics:
  Below sea level:      v = 0 (submerged)
  Coastal (< sea+0.05): v grows slowly, max 0.2
  Alpine (> 0.85):      v decays (too cold)
  High (0.7-0.85):      v grows slowly, max 0.4
  Temperate:            v grows proportional to (1 - slope_penalty)
```

**What to look for**

Over geological epochs, observe the competition between uplift (building mountains) and erosion (wearing them down). Vegetation stabilizes slopes, so a higher vegetation growth rate reduces erosion. `v` cycles four views: topographic (elevation bands with vegetation), raw elevation, vegetation density, and erosion (slope steepness in four colour bands). The presets are Continental, Archipelago, Alpine Peaks, Rolling Plains, Great Rift and Coastal Erosion. While running, `u`/`U` change uplift, `t`/`T` thermal erosion, `w`/`W` rain, `g`/`G` vegetation growth and `s`/`S` sea level.

**References**

- Musgrave, F.K., Kolb, C.E., and Mace, R.S. "The Synthesis and Rendering of Eroded Fractal Terrains." *SIGGRAPH* 1989. https://doi.org/10.1145/74334.74337
- Cordonnier, G. et al. "Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion." *Computer Graphics Forum* 35(2), 2016. https://doi.org/10.1111/cgf.12820

---

## 3D Terrain Flythrough

**Background**

First-person terrain flythrough draws procedural landscapes in pseudo-3D, in the spirit of the Voxel Space engine (Comanche, 1992). This mode generates a 256x256 heightmap from cosine-interpolated layered noise. It draws a first-person view with altitude zones, distance fog, and a day/night cycle. It is a simplification: each screen row maps to a ground distance and each column to a ray direction, so nearer ridges do not hide terrain behind them.

**Formulation**

```
Heightmap generation: same layered noise as Terrain Generation, but with
  cosine interpolation: f_smooth = (1 - cos(f * pi)) * 0.5
  on a 256x256 tile-wrapping grid.

Camera model:
  position = (cam_x, cam_y, cam_z)  -- y is altitude
  orientation = (yaw, pitch)
  movement: dx = cos(yaw) * speed,  dz = sin(yaw) * speed
  minimum altitude = terrain_height(cam_x, cam_z) + 2.0

Perspective projection (per screen column):
  ray_yaw = yaw + (col / view_w - 0.5) * FOV
  ray_dir = (cos(ray_yaw), sin(ray_yaw))

  For each row below horizon:
    frac = rows_below_horizon / (view_h - horizon_row)
    dist = min_dist + (max_dist - min_dist) * (1 - frac)^0.5
    world_pos = camera + ray_dir * dist * pitch_factor
    terrain_h = bilinear_interpolate(heightmap, world_pos)

Height-based biome rendering:
  < 0.15: deep water    0.15-0.25: shallow    0.25-0.30: beach
  0.30-0.50: grass      0.50-0.65: forest     0.65-0.80: rock
  0.80-0.90: mountain   > 0.90: snow caps

Distance fog: beyond 50 units, characters fade to dots
Day/night: time cycles 0.0-1.0 (midnight-midnight), affects sky color and dimming
```

**What to look for**

The non-linear depth mapping (square root) gives a natural perspective where nearby terrain has high detail and the horizon fades gradually. Fly over canyon terrain types to see the carved V-shape valleys. The day/night cycle changes the sky colour through dawn, day (with a sun arc), dusk, and night (stars and moon). The presets are Rolling Hills, Mountain Range, Desert Canyon, Volcanic Islands, Glacial Valley and Alien World. They show how one noise framework gives very different landscapes through post-processing transforms. Fly with `WASD`, look with the arrow keys, change altitude with `e`/`c`, and set the speed with `+`/`-`. `t` toggles the automatic clock, and `T` advances it.

**References**

- Comanche engine, NovaLogic, 1992. (Voxel Space rendering technique) https://en.wikipedia.org/wiki/Voxel_Space
- Perlin, K. "An Image Synthesizer." *SIGGRAPH* 1985. https://doi.org/10.1145/325165.325247

---

## SDF Ray Marching

**Background**

Signed Distance Field (SDF) ray marching is a rendering technique where the distance to the nearest surface guides ray advancement, enabling efficient rendering of implicit surfaces, fractals, and boolean CSG operations. Popularized by Inigo Quilez through ShaderToy (2013+), it has become the standard technique for real-time fractal rendering. This implementation renders six scenes (Sphere, Torus, Multi-Shape, Mandelbulb, Infinite Spheres, Smooth Blend) with Blinn-Phong shading and soft shadows.

**Formulation**

```
Core ray marching loop (64 iterations max):
  t = 0
  for each step:
    p = camera_pos + ray_dir * t
    d = SDF(p)
    if d < 0.002: HIT
    t += d
    if t > 30.0: MISS

SDF primitives:
  Sphere:   SDF = |p| - R
  Torus:    q = (sqrt(px^2 + pz^2) - R, py)
            SDF = |q| - r
  Box:      d = |p| - half_extents
            SDF = |max(d, 0)| + min(max(dx, dy, dz), 0)

  Mandelbulb fractal (8 iterations):
    z = p; dr = 1
    r = |z|;  if r > 2: break
    theta = acos(zz/r) * power
    phi = atan2(zy, zx) * power
    zr = r^power
    dr = r^(power-1) * power * dr + 1
    z = zr * (sin(theta)*cos(phi), sin(theta)*sin(phi), cos(theta)) + p
    SDF = 0.5 * ln(r) * r / dr

  Infinite Spheres: repeat space with period 3, then SDF = |p_local| - 0.8

  Smooth blend (smooth union):
    h = clamp(0.5 + 0.5*(d2-d1)/k, 0, 1)
    SDF = lerp(d2, d1, h) - k*h*(1-h)     where k = 0.5

Surface normal (central differences, epsilon = 0.001):
  n = normalize(SDF(p+ex) - SDF(p-ex), SDF(p+ey) - SDF(p-ey), SDF(p+ez) - SDF(p-ez))

Lighting (Blinn-Phong):
  diffuse  = max(0, n . L)
  half_vec = normalize(L - ray_dir)
  specular = (max(0, n . half_vec))^32 * 0.5
  ambient  = 0.15
  brightness = ambient + diffuse * shadow * 0.75 + specular * shadow

Soft shadows (32 steps, k = 8):
  t = 0.05; res = 1.0
  d = SDF(origin + L * t)
  res = min(res, k * d / t)
  t += max(d, 0.02)
  shadow = clamp(res, 0, 1)
```

**What to look for**

The Mandelbulb preset shows self-similar detail as you zoom in with `+`/`-`. Press `p` or `P` to lower or raise the power (default 8, range 2 to 16) and the shape changes. The Smooth Blend scene shows how SDFs join two shapes with a smooth transition. Soft shadows (toggle with `s`) fade gradually near the edges of occluders. `l`/`L` move the light, `a` toggles auto-rotation, and the arrow keys orbit the camera. The color mapping uses surface normal direction: green for Y-facing, cyan for Z-facing, magenta for X-facing surfaces.

**References**

- Hart, J.C. "Sphere Tracing: A Geometric Method for the Antialiased Ray Tracing of Implicit Surfaces." *The Visual Computer* 12(10), 1996. https://doi.org/10.1007/s003710050084
- Quilez, I. "Distance Functions." 2008-2024. https://iquilezles.org/articles/distfunctions/

---

## Shader Toy

**Background**

Shader Toy implements real-time per-pixel mathematical animations inspired by the ShaderToy web platform created by Inigo Quilez and Pol Jeremias in 2013. Each preset defines a fragment shader as a pure function of normalized screen coordinates (nx, ny) and time t, producing visual effects through trigonometric composition, distance fields, and iterative transforms. The simulator renders these to ASCII with configurable color palettes.

**Formulation**

```
For each cell at normalized coords (nx, ny) and time t
  (ny in [-1, 1]; nx is scaled by the terminal aspect ratio):
  val = shader(nx, ny, t)    -- returns value in [0, 1]
  char = shade_chars[int(val * N)]
  color = palette_map(val)

Presets: Plasma Waves, Tunnel Zoom, Metaballs, Moiré Rings, Fractal Flame,
Warp Grid, Lava Lamp, Matrix Rain, Kaleidoscope, Spiral Galaxy.
Four are written out here:

  Plasma Waves:
    v = sin(nx*10*A + t) + sin((ny*10*B + t)*0.7)
      + sin((nx*10 + ny*10 + t)*0.5)
      + sin(sqrt(nx^2*100 + ny^2*100)*A + t)
    val = (v/4 + 1) * 0.5

  Tunnel Zoom:
    r = sqrt(dx^2 + dy^2) + epsilon
    angle = atan2(dy, dx)
    val = (sin(1/(r*A) + t*2) * cos(angle*3*B + t) + 1) * 0.5

  Metaballs:
    val = sum over 5 balls:
      cx_i = sin(t * (0.3 + i*0.17) * A) * 0.5
      cy_i = cos(t * (0.4 + i*0.13) * B) * 0.5
      0.03 / ((nx-cx)^2 + (ny-cy)^2 + 0.01)
    val = min(1, val * 0.15)

  Spiral Galaxy:
    r = sqrt(nx^2 + ny^2);  angle = atan2(ny, nx)
    spiral = sin(angle*2*A - r*10*B + t*1.5)
    arm = max(0, spiral) * max(0, 1 - r*1.2)
    core = max(0, 0.3 - r) * 3
    val = arm + core + sin(r*30 - t*3) * 0.1 * max(0, 1 - r*2)

Parameters A, B in [0.1, 3.0] scale frequency terms in each shader.
Color modes: Rainbow, Fire, Ocean, Mono.
```

**What to look for**

Parameters A and B (`a`/`A`, `b`/`B`) mostly scale spatial frequency, so raising them gives finer detail. The Metaballs shader demonstrates implicit surface visualization: watch five moving charge points create smooth organic merges where their fields overlap. The Kaleidoscope preset folds the angle into mirrored segments (A sets the segment count) and applies a radial wave. `c` cycles the four colour palettes, `n`/`N` switch shaders, and `+`/`-` change the speed.

**References**

- Quilez, I. and Jeremias, P. "ShaderToy." https://www.shadertoy.com, 2013.
- Gonzalez-Vivo, P. and Lowe, J. *The Book of Shaders.* 2015. https://thebookofshaders.com

---

## Doom Raycaster

**Background**

The Doom-style raycaster reproduces the rendering technique used by Wolfenstein 3D (id Software, 1992), where a single ray is cast per screen column to determine wall distance and projected height. This was one of the first real-time 3D rendering methods for consumer hardware. This version marches each ray in fixed 0.02 steps instead of using a grid DDA. It adds fisheye correction, distance-based wall shading, and floor shading, and the player walks through one of six fixed 16x16 maps.

**Formulation**

```
Camera model:
  position = (px, py) in map coordinates
  angle = pa (player angle in radians)
  FOV = field of view (60 degrees)

For each screen column x in [0, screen_w):
  ray_angle = (pa - FOV/2) + (x / screen_w) * FOV

  Ray stepping (step_size = 0.02, max_depth = 16):
    ray_x = px + cos(ray_angle) * dist
    ray_y = py + sin(ray_angle) * dist
    if map[int(ray_y)][int(ray_x)] == '#': HIT

  Fisheye correction:
    dist_corrected = dist * cos(ray_angle - pa)

  Wall projection:
    wall_height = screen_h / dist_corrected
    ceiling = (screen_h - wall_height) / 2
    floor = ceiling + wall_height

  Rendering per column:
    y < ceiling:  empty (ceiling)
    ceiling <= y <= floor:  wall char by shade_wall[dist/depth]
    y > floor:    floor char by shade_floor[brightness]

  Wall color by distance:
    < 25% depth: bold magenta    < 50%: yellow
    < 75%: red                   else: dim

Collision detection with wall sliding:
  margin = 0.2 (player radius)
  Try full movement (checks all four corners of the bounding box),
  then X-only, then Y-only (each checks two opposite corners)
```

**What to look for**

The fisheye correction eliminates the barrel distortion that would otherwise occur when projecting rays at angles away from the view center. Notice how wall shading characters transition from solid blocks at close range to sparse dots at distance, creating a convincing depth effect in pure ASCII. Wall sliding allows smooth movement along walls instead of abrupt stops. The presets are Dungeon, Office, Outdoor Ruins, Arena, Maze and Fortress. `W`/`S` or the up/down arrows move, `A`/`D` strafe, `Q`/`E` or the left/right arrows turn, and `Esc` exits.

**References**

- Permadi, F. "Ray-Casting Tutorial." 1996. https://permadi.com/1996/05/ray-casting-tutorial/
- Sanglard, F. *Game Engine Black Book: Wolfenstein 3D.* Self-published, 2017. https://fabiensanglard.net/gebbwolf3d/

---

## Sorting Algorithm Visualizer

**Background**

Sorting algorithm visualization transforms abstract computational complexity into observable behavior. First popularized by Ronald Baecker's film "Sorting Out Sorting" (1981), animated sorting has become a standard pedagogical tool. This implementation pre-computes all comparison and swap operations for six algorithms, then replays them as animated bar charts with per-step highlighting.

**Formulation**

```
Algorithms and their complexities:

  Bubble Sort:     O(n^2) comparisons, O(n^2) swaps
    for i in [0, n):
      for j in [0, n-i-1):
        if a[j] > a[j+1]: swap(a[j], a[j+1])

  Quicksort (Lomuto partition):  O(n log n) average, O(n^2) worst
    partition(lo, hi):
      pivot = a[hi]; i = lo
      for j in [lo, hi): if a[j] <= pivot: swap(a[i], a[j]); i++
      swap(a[i], a[hi]); return i

  Merge Sort:      O(n log n) guaranteed
    Divide array in half, recursively sort, merge by comparing heads

  Heap Sort:       O(n log n) in-place
    Build max-heap, repeatedly extract maximum to sorted position

  Radix Sort (LSD): O(d * (n + k)) where d = digits, k = 10
    For each digit position (units, tens, ...):
      counting sort by current digit

  Shell Sort:      O(n^2) worst case with the gap/2 sequence
    gap = n/2; while gap > 0:
      insertion sort with stride = gap; gap /= 2

Each operation recorded as a step tuple:
  ("cmp", i, j, array_state)   -- comparison
  ("swap", i, j, array_state)  -- element exchange
  ("write", i, array_state)    -- overwrite (merge/radix)
  ("pivot", i, array_state)    -- quicksort pivot selected
  ("read", i, array_state)     -- radix digit read
  ("sorted", idx, array_state) -- mark position final
```

**What to look for**

Bubble sort's quadratic nature is immediately visible as the algorithm makes many passes with diminishing effect. Quicksort shows dramatic pivot-based partitioning with recursive subdivision. Merge sort's merge phase creates satisfying sorted runs that double in length. Radix sort operates digit-by-digit with no comparisons, producing wave-like reorganization patterns. The info panel (toggle with `i`) tracks comparisons and swaps/writes. Compare how many writes merge sort makes against the swaps quicksort makes. `Space` plays, `n` steps, `+`/`-` change the speed, and `r` reshuffles.

**References**

- Baecker, R. "Sorting Out Sorting" (film). University of Toronto, 1981. https://www.youtube.com/watch?v=SJwEwA5gOkM
- Sedgewick, R. and Wayne, K. *Algorithms,* 4th ed. Addison-Wesley, 2011. https://algs4.cs.princeton.edu/home/

---

## DNA Helix & Genetic Algorithm

**Background**

Genetic algorithms (GAs), introduced by John Holland in 1975, optimize by mimicking natural selection: a population of candidate solutions undergoes selection, crossover, and mutation over generations. This mode visualizes a binary GA evolving toward a target genome, rendered as a rotating double helix. The Royal Road fitness function, designed by Mitchell et al. (1992), specifically tests the GA's ability to discover building blocks.

**Formulation**

```
Genome: binary string of length L (32, 48, 64, or 128 bits)
Population: N individuals (10 to 60)

Target: random bits, except OneMax Challenge and Royal Road (all ones)

Fitness functions:
  Standard:   f(genome) = (matching bits with target) / L
  Royal Road:  block_size = 8;  n_blocks = L / 8
               f(genome) = (complete matching 8-bit blocks) / n_blocks

Selection: tournament selection, size 3
  Pick 3 random individuals, select the fittest

Crossover (single-point, rate = crossover_rate):
  cx = random point in [1, L-1]
  child = parent1[:cx] + parent2[cx:]

Mutation (per-bit, rate = mutation_rate):
  for each bit i in child:
    if rand() < mutation_rate: child[i] = 1 - child[i]

Elitism: best individual always survives to next generation

Preset configurations:
  Classic Binary GA: L=32,  N=40,  mutation=0.02,  crossover=0.7
  OneMax Challenge:  L=64,  N=50,  mutation=0.015, crossover=0.8
  Long Strand:       L=128, N=60,  mutation=0.005, crossover=0.7
  Hyper-Mutation:    L=32,  N=40,  mutation=0.10,  crossover=0.6
  Minimal Pop:       L=48,  N=10,  mutation=0.03,  crossover=0.7
  Royal Road:        L=64,  N=50,  mutation=0.02,  crossover=0.75
```

**What to look for**

The fitness sparkline plots the best fitness of each generation. Elitism keeps it from falling. It typically rises fast while easy bits are found, then slows as the last mismatches are fixed. The Hyper-Mutation preset flips 10% of bits per child, which keeps breaking good genomes and works against convergence. The Minimal Pop preset has only 10 individuals, so drift is strong. The Royal Road fitness function produces staircase-like jumps as complete 8-bit schema blocks snap into place, illustrating Holland's building block hypothesis. `Space` plays, `n` steps one generation, `+`/`-` change the speed, and `i` toggles the info panel.

**References**

- Holland, J.H. *Adaptation in Natural and Artificial Systems.* University of Michigan Press, 1975. https://doi.org/10.7551/mitpress/1090.001.0001
- Mitchell, M., Forrest, S., and Holland, J.H. "The Royal Road for Genetic Algorithms: Fitness Landscapes and GA Performance." *Proceedings of the First European Conference on Artificial Life*, 1992. https://doi.org/10.7551/mitpress/2090.003.0019

---

## Fourier Epicycle Drawing

**Background**

Fourier epicycles demonstrate that any closed curve can be approximated by a sum of rotating circles, a consequence of the Discrete Fourier Transform (DFT) first formalized by Joseph Fourier in 1807. This visualization computes the DFT of a sampled path and reconstructs it as a chain of orbiting circles, directly illustrating how frequency decomposition works. The concept was popularized by 3Blue1Brown's 2019 video "But what is a Fourier series?"

**Formulation**

```
Input: N sample points P[n] = (x_n, y_n) along a closed curve
  (presets use N = 128; a free-drawn path uses the points you drew)

Discrete Fourier Transform:
  For each frequency k in [0, N):
    Re_k = (1/N) * sum_{n=0}^{N-1} [ x_n * cos(2*pi*k*n/N) + y_n * sin(2*pi*k*n/N) ]
    Im_k = (1/N) * sum_{n=0}^{N-1} [ y_n * cos(2*pi*k*n/N) - x_n * sin(2*pi*k*n/N) ]
    amplitude_k = sqrt(Re_k^2 + Im_k^2)
    phase_k = atan2(Im_k, Re_k)

  Coefficients sorted by amplitude (largest first)

Reconstruction (epicycle chain):
  At time t:
    (x, y) = (0, 0)
    for i in [0, num_circles):
      angle = freq_i * t + phase_i
      x += amplitude_i * cos(angle)
      y += amplitude_i * sin(angle)
    trace.append((x, y))

  Time step: dt = 2*pi / N (one full cycle reproduces the original path)

Presets: Circle, Square Wave, Star, Figure 8, Heart, Spiral Square, Free Draw
Free Draw: move the cursor, press d to lower or raise the pen, x to clear,
  Enter to compute the DFT and start playback
```

**What to look for**

Start with all circles enabled, then use `[` and `]` to change the count. With few circles, only the coarse shape is visible; adding circles progressively refines the approximation. The Square Wave preset is instructive: sharp corners need many high-frequency harmonics, so reducing circles rounds them off. The heart preset demonstrates how a non-trivial parametric curve decomposes into a manageable number of epicycles. Free Draw lets you sketch any shape and see its Fourier decomposition. `c` toggles the circles, `i` the info panel, and `+`/`-` set the speed.

**References**

- Fourier, J. *Theorie analytique de la chaleur.* 1822. https://archive.org/details/thorieanalytiq00four
- Sanderson, G. (3Blue1Brown) "But what is a Fourier series? From heat flow to drawing with circles." YouTube, 2019. https://www.youtube.com/watch?v=r6sGWTCMz2k

---

## Maze Solver Visualizer

**Background**

This mode focuses on comparing pathfinding algorithms by generating a maze instantly and then animating the solving process step-by-step. Four algorithms are implemented: A* (optimal, heuristic-guided), BFS (optimal, exhaustive), DFS (non-optimal, depth-first), and the right-hand wall follower (a simple rule requiring no memory of visited cells). The eight presets are A* Search (Medium), BFS (Medium), DFS (Medium), Wall Follower (Medium), A* (Small), A* (Large), BFS (Large) and DFS (Large). Small mazes are at most 21x21 cells, medium at most 41x51, and large fill the terminal.

**Formulation**

```
Maze generation: recursive backtracker (instant, pre-computed)

Solving algorithms:

  A* Search:
    priority queue ordered by f = g + h
    g = steps from start;  h = |end_r - r| + |end_c - c| (Manhattan distance)
    Optimal and complete; explores fewest cells when heuristic is admissible

  BFS (Breadth-First Search):
    FIFO queue
    Explores in concentric wavefronts from start
    Guarantees shortest path; explores all cells at distance d before d+1

  DFS (Depth-First Search):
    LIFO stack
    Explores as deep as possible before backtracking
    NOT guaranteed to find shortest path; may explore many dead ends

  Wall Follower (right-hand rule):
    Directions: right=0, down=1, left=2, up=3
    Priority: try turn right, then straight, then left, then reverse
    for turn in [+1, 0, -1, +2]:
      new_dir = (current_dir + turn) % 4
      if passable: move and update direction
    Works only on simply-connected mazes (no loops)

Path reconstruction: trace parent pointers from end to start
  (the wall follower's path is its full trail, including revisits)
```

**What to look for**

Compare the explored cell count across algorithms on the same maze. A* typically explores a narrow corridor toward the goal, while BFS floods outward uniformly. DFS may find a long, winding path quickly or get trapped in dead ends far from the goal. The wall follower traces the maze boundary, often visiting cells multiple times -- its trail shows characteristic repeated visits to corridors. The frontier (cells in the queue, shown as highlighted blocks) reveals each algorithm's search strategy: A*'s frontier clusters near the goal, BFS's frontier forms a wavefront, DFS's frontier is a single deep tendril. `Space` plays, `n` steps, `s`/`S` change the steps per frame, and `r` generates a new maze.

**References**

- Hart, P.E., Nilsson, N.J., and Raphael, B. "A Formal Basis for the Heuristic Determination of Minimum Cost Paths." *IEEE Transactions on Systems Science and Cybernetics* 4(2), 1968. https://doi.org/10.1109/TSSC.1968.300136
- Even, S. *Graph Algorithms,* 2nd ed. Cambridge University Press, 2011. https://doi.org/10.1017/CBO9781139015165

---

## Neural Network Training Visualizer

**Background**

This mode implements a complete feed-forward neural network with backpropagation in pure Python (no external libraries), visualizing the training process in real time. The network architecture, weight connections, gradient flow, decision boundary, and loss/accuracy curves are all displayed simultaneously. The implementation follows Rumelhart, Hinton, and Williams' 1986 backpropagation algorithm, the foundation of modern deep learning.

**Formulation**

```
Network: fully connected layers, sizes set by the preset (e.g., 2-8-8-3)

Weight initialization (Xavier):
  scale = sqrt(2 / (fan_in + fan_out))
  w[l][j][i] ~ Normal(0, scale)

Forward pass:
  a[0] = input
  for each layer l:
    z[l][j] = sum_i(w[l][j][i] * a[l-1][i]) + b[l][j]
    a[l][j] = activation(z[l][j])
  Output layer: softmax (more than one output); otherwise the preset's activation

Activation functions (hidden layers; presets use sigmoid or relu):
  sigmoid(x) = 1 / (1 + exp(-x));     deriv: s * (1-s)
  relu(x) = max(0, x);                deriv: 1 if x > 0 else 0
  tanh(x) = tanh(x);                  deriv: 1 - t^2  (available, no preset uses it)

Loss functions:
  Single output: L = 0.5 * sum(output - target)^2
  Multi-class:   L = -sum(target * log(output))  (cross-entropy with softmax)

Backpropagation:
  Output deltas:
    Single:  delta[L] = (out - target) * activation'(out)
    Softmax: delta[L] = out - target

  Hidden deltas:
    delta[l][i] = sum_j(w[l+1][j][i] * delta[l+1][j]) * activation'(a[l+1][i])

  Weight update (SGD):
    grad = delta[l][j] * a[l-1][i]
    w[l][j][i] -= learning_rate * grad

Presets (layers, activation, learning rate, samples):
  XOR Gate               2-2-1      sigmoid  1.0   4 noisy points
  Spiral Classification  2-8-8-3    relu     0.3   150 points, 3 classes
  Circle Decision        2-4-1      sigmoid  0.5   80 points
  Two Moons              2-6-4-1    relu     0.4   120 points
  Sine Regression        2-8-4-1    relu     0.1   60 points
  Gaussian Clusters      2-8-4-3    relu     0.25  120 points, 3 classes

Visualization: neuron activation mapped to fill characters (empty to full circle),
  weight magnitude to line thickness, gradient flow animated as pulsing arrows
```

**What to look for**

The decision boundary view reveals how the network partitions input space. For XOR, watch the 2-2-1 network learn a non-linear boundary that no single perceptron can produce. The spiral task uses a deeper network (2-8-8-3) to separate three interleaved classes. The loss curve shows characteristic training dynamics: initial plateau (random weights), rapid descent (gradient catches), and potential oscillation (learning rate too high). Press `[` or `]` to lower or raise the learning rate and see its effect on stability. `v` cycles the panels, `+`/`-` change the training speed, and `n` trains one step.

**References**

- Rumelhart, D.E., Hinton, G.E., and Williams, R.J. "Learning representations by back-propagating errors." *Nature* 323, 1986. https://doi.org/10.1038/323533a0
- Goodfellow, I., Bengio, Y., and Courville, A. *Deep Learning.* MIT Press, 2016. https://www.deeplearningbook.org/

---

## Quantum Circuit Simulator

**Background**

This mode simulates quantum circuits using full state-vector simulation, applying unitary gate operations to a 2^n-dimensional complex amplitude vector. Six preset circuits demonstrate fundamental quantum computing concepts: Bell state entanglement, GHZ states, quantum teleportation, the Deutsch-Jozsa algorithm, Grover's search, and the Quantum Fourier Transform. Qubit states are drawn as mini Bloch sphere projections, and repeated runs build a histogram.

**Formulation**

```
State vector: |psi> = sum_{i=0}^{2^n - 1} alpha_i |i>
  where alpha_i are complex amplitudes, sum |alpha_i|^2 = 1
  Initial state: |00...0> (alpha_0 = 1, all others 0)

Gate operations (applied to state vector):

  Hadamard H on qubit q:
    |0> -> (|0> + |1>) / sqrt(2)
    |1> -> (|0> - |1>) / sqrt(2)

  Pauli-X (NOT):  |0> <-> |1>
  Pauli-Y:        |0> -> i|1>,  |1> -> -i|0>
  Pauli-Z:        |1> -> -|1>
  S gate:         |1> -> i|1>
  T gate:         |1> -> e^(i*pi/4)|1>

  CNOT (controlled-X): flips target if control is |1>
  CZ (controlled-Z):   applies Z to target if control is |1>
  CP (controlled-phase): |11> -> e^(i*theta)|11>
  SWAP:                  |01> <-> |10>

  Measurement on qubit q:
    P(outcome=1) = sum |alpha_i|^2 for all i where bit q is 1
    Collapse: zero out non-matching amplitudes, renormalize

Bloch sphere projection for qubit q:
  alpha_0, alpha_1 = square roots of the probabilities of q being 0 or 1,
    with the relative phase taken from the summed amplitudes of each branch
  theta = 2 * acos(|alpha_0|)
  phi = phase(alpha_1) - phase(alpha_0)
  Display: project (sin(theta)*cos(phi), cos(theta)) onto 2D circle

Entanglement indicator (a heuristic):
  purity = p0^2 + p1^2 where p0, p1 are the qubit's 0/1 probabilities
  if purity < 0.99: qubit is flagged, and flagged qubits are linked in pairs
  A lone qubit in superposition is flagged too, so a link is not proof of entanglement.

Histogram: run the full circuit N times (m = 100 shots, M = 1000 shots),
  sample one basis state from each run's final distribution
```

**What to look for**

The Bell State circuit produces exactly two outcomes (|00> and |11>) with 50% probability each, while individual qubit measurements are completely random -- the hallmark of entanglement. In Grover's Search, the marked state |11> goes from 25% to 100% probability after one oracle + diffusion iteration. The Quantum Fourier Transform produces a uniform superposition of all basis states when applied to |100> (the binary representation of 4). The Bloch sphere projections show qubit states moving from the north pole (|0>) to the equator (superposition) at Hadamard gates. `Space` runs, `n` applies the next gate, `f` applies all remaining gates, `m`/`M` take 100/1000 shots, and `+`/`-` set the speed.

**References**

- Nielsen, M.A. and Chuang, I.L. *Quantum Computation and Quantum Information.* Cambridge University Press, 2000. https://doi.org/10.1017/CBO9780511976667
- Mermin, N.D. *Quantum Computer Science: An Introduction.* Cambridge University Press, 2007. https://doi.org/10.1017/CBO9780511813870

---

## Tierra Digital Organisms

**Background**

Tierra, created by ecologist Thomas Ray in 1990, is a landmark artificial life system where self-replicating machine-code programs compete for memory and CPU time in a shared "primordial soup." In Ray's runs, mutation led to parasites (programs that exploit others' copy routines), immunity, and hyper-parasites. This mode is a simplified Tierra-style system: a 16-opcode virtual machine, a shared memory, a reaper queue, and a terminal view. Each organism executes only its own code, so Ray's host-parasite interactions are not modelled.

**Formulation**

```
Memory: circular array of size M (3072-6144), each cell holds one opcode (0-15)
Instruction set (16 opcodes):
  NOP0(0), NOP1(1): template markers for addressing
  FIND(2):   search forward for complement of following template
  MOV_H(3):  move head to found address
  COPY(4):   copy instruction from read-head to write-head
  INC(5), DEC(6): increment/decrement register
  JMP(7):    jump to template complement
  JMPZ(8):   jump if register zero
  ALLOC(9):  allocate daughter cell (request contiguous free block)
  SPLIT(10): divide — daughter becomes independent organism
  PUSH(11), POP(12): stack operations
  SWAP(13), CALL(14), RET(15): register/subroutine operations

Ancestor genome (42 instructions): minimal self-copier
  1. Start template (1111), then ALLOC for the daughter space
  2. PUSH, FIND the end template, MOV_H to set the read head, POP
  3. Copy loop: COPY, INC, INC, DEC counter, JMPZ exit, JMP loop
  4. SPLIT to create an independent daughter
  5. JMP back to start
  Parasite World uses a 30-instruction ancestor; Symbiosis Lab seeds both.

Mutation:
  Copy mutation: during COPY, each instruction has probability P_mut of being
    replaced by random opcode (0.002 to 0.015 depending on preset)
  Cosmic rays: per step, int(P_cosmic * mem_size) random memory cells are
    overwritten with random opcodes (Genesis rounds down to none)

Reaper queue (population control, when max_organisms is reached):
  "oldest":       kill organism with highest age
  "large_first":  kill organism with largest genome
  "errors_first": kill organism with most execution errors
  Organisms with more than 200 errors die regardless of the reaper.

Species identification: h = (h * 31 + op_i + i) mod 2^32, folded over the genome

Presets:
  Genesis:        mutation=0.002, cosmic=0.0001, reaper=oldest
  Cambrian Burst: mutation=0.015, cosmic=0.001,  reaper=oldest
  Arms Race:      mutation=0.005, cosmic=0.0005, reaper=large_first
  Parasite World: mutation=0.010, cosmic=0.0005, reaper=oldest (small ancestor)
  Symbiosis Lab:  mutation=0.005, cosmic=0.0003, reaper=errors_first (dual ancestors)
```

**What to look for**

In the memory view, watch colored blocks expand as organisms replicate and fill free space (shown as dim dots). Species diversity (shown in stats view) typically follows a pattern: initial monoculture, then diversification as mutations accumulate, then possible mass extinction events when a successful parasite emerges. The Parasite World preset starts from the small ancestor with a higher mutation rate. The Arms Race preset reaps the largest genomes first, which favors smaller ones. The phylogenetic view shows the genome-length distribution, so you can see whether lengths drift shorter or longer. `v` cycles memory, stats and phylogeny views, `m` mutates 20 random cells, `r` reaps one organism, `Space` pauses, `n` steps while paused, and `+`/`-` set the speed.

**References**

- Ray, T.S. "An Approach to the Synthesis of Life." *Artificial Life II,* Addison-Wesley, 1991. https://doi.org/10.7551/mitpress/1428.003.0010
- Adami, C. *Introduction to Artificial Life.* Springer, 1998. https://doi.org/10.1007/978-1-4612-1650-6

---

## Living Labyrinth

**Background**

The Living Labyrinth is a playable roguelike where the dungeon itself is a cellular automaton. Here the user is a *participant*, not an observer: an agent (`@`) navigates a maze whose walls grow and decay by CA rules. The concept merges two traditions: roguelike dungeon crawlers (Rogue, 1980; Brogue, 2009) where procedural generation creates each run's unique challenge, and cellular automata as generative systems for dynamic environments. The dungeon changes every turn, so the best path changes with it.

**Formulation**

```
Maze generation (recursive backtracker + opening):
  1. Generate perfect maze on odd-dimensioned grid via DFS
  2. For each internal wall cell adjacent to 2+ floor cells:
     open with probability 0.3 (creates loops for CA to exploit)

CA evolution (Moore neighborhood, toroidal boundary):
  For each cell (r, c) not frozen:
    count = number of alive Moore neighbors (8-connected)
    if alive:  survive if count in S, else die
    if dead:   birth if count in B, else stay dead
  Wall age tracks generations survived (used for rendering)
  The player and exit cells are forced open after every tick.

8 rule presets:
  Maze:       B3/S12345
  Coral:      B3/S45678
  Anneal:     B4678/S35678
  Day & Night: B3678/S34678
  Stains:     B3678/S235678
  Diamoeba:   B35678/S5678
  Slow Decay: B3/S238
  Life:       B3/S23   (Conway's rule)
  r cycles the rule at any time.

Items (radius-based effects):
  Freeze:  set frozen_mask[r][c] = 10 for cells within radius 5
           (frozen cells skip CA update for 10 turns)
  Reverse: restore cells within radius 6 to state from 5 turns ago
           (uses circular history buffer of depth 10)
  Mutate:  for cells within radius 7, flip alive<->dead with P=0.4
           (creates openings through walls, or new obstacles)

Scoring:
  Level complete: speed_bonus + level_bonus
  speed_bonus = max(0, 500 - 2 * turns_taken)
  level_bonus = level_number * 100
  After a win, the rule advances at levels 4, 7, 10, ... for variety
```

**What to look for**

Each rule plays differently. In a test run on a fresh 41x81 maze, the Maze rule thickened the walls to a steady density, Stains filled almost the whole grid, and Anneal, Day & Night, Slow Decay and Life thinned the walls. Coral and Diamoeba first thinned and then regrew them. Wall age shows in the glyph: `░░` for new walls, then `▒▒`, `▓▓`, and `██` for walls that have lasted more than 8 generations. Items act locally: Freeze locks nearby walls for 10 turns (`f`), Reverse rewinds them up to 5 steps (`v`), and Mutate flips about 40% of the cells nearby (`m`). `+`/`-` set how many CA ticks run per player move (1 to 5), which sets the pace against your movement.

**References**

- Toy, M. et al. *Rogue.* UC Berkeley, 1980. (Original roguelike establishing the genre) https://en.wikipedia.org/wiki/Rogue_(video_game)
- Walker, B. *Brogue.* 2009-2020. (Modern roguelike with procedural dungeon generation and emergent systems) https://sites.google.com/site/broguegame/
- Wolfram, S. *A New Kind of Science.* Wolfram Media, 2002. (Comprehensive survey of CA behavior classes) https://www.wolframscience.com/nks/

---

## Programmable Matter

**Background**

Programmable matter refers to materials whose physical properties can be programmed to achieve specific shapes or behaviors. The concept originates from Toffoli and Margolus's work on programmable lattice gases (1987) and was formalized by Seth Goldstein and Todd Mowry at Carnegie Mellon (2004) as "claytronics" — ensembles of tiny robots called catoms that can self-assemble into arbitrary 3D shapes. This mode implements a 2D discrete variant: each cell on the grid is an independent state machine executing a local program, communicating with immediate neighbors through signals and bonds. The result is a bridge between passive cellular automata (where rules are fixed and global) and agent-based models (where agents have complex internal state) — cells here are *actively programmable*, yet operate under strict locality constraints.

**Formulation**

```
Cell state machine:
  state  in {empty, idle, moving, bonded, signaling}
  reg_a  = direction register (0-3: N/E/S/W)
  reg_b  = signal register
  reg_c  = general-purpose / counter register
  pc     = program counter
  program = list of (opcode, operand) pairs

Instruction set (15 opcodes, 2 executed per cell per step):
  NOP        — no operation
  MOVE       — move in direction reg_a; if target shape exists, bias toward
               nearest target cell via Manhattan distance gradient
  BOND       — bond to the first adjacent cell found (both become bonded and
               stop moving)
  UNBOND     — release all bonds, return to idle
  SIGNAL     — emit signal value (reg_b or reg_c) into signal field
  READ       — count 4-neighbors, average their signals into reg_c/reg_b
  IF_NBRS n  — skip next instruction if neighbor_count >= n
  IF_REG  n  — skip next instruction if reg_a != n
  SET_REG n  — set reg[n & 3] = (n >> 2), or random 0-3 if zero
  REPLICATE  — spawn copy into first empty neighbor (with population cap)
  TURN    n  — reg_a = (reg_a + n) mod 4
  IF_BONDED  — skip next instruction if not bonded
  GOTO    n  — set pc = n mod program_length
  IF_DIST n  — skip next instruction if Manhattan distance to the nearest
               of 30 sampled target cells > n
  INC_REG n  — increment reg[n & 3]

Simulation phases per step:
  1. EXECUTE: each cell runs 2 instructions from its program
  2. RESOLVE MOVEMENT: shuffle proposed moves, first-come-wins, bonded cells skip
  3. REPLICATE: shuffle proposed replications, spawn until population cap
     (max_cells = rows * cols / 3)
  4. DIFFUSE SIGNALS: new_signal[r][c] = 0.6 * signal[r][c]
       + 0.08 * sum(signal[neighbors])
       A cell with a nonzero signal keeps the field at no less than its value
  5. UPDATE STATS: count cells, bonded cells, on-target cells, max signal

Presets (cells, program):
  Circle Formation, Square Formation, Letter 'H', Diamond Formation
                                (80-100 cells, shape assembly)
  Self-Replicating Cluster      (15 cells, replicate when sparse)
  Distributed Counter           (40 cells)
  Random Explorers              (50 cells)
  Line Formation                (60 cells)

Target shape generators:
  Circle:   (r - cr)^2 + (c - cc)^2 <= radius^2, radius = min(rows, cols) / 4
  Square:   |r - cr| <= side/2 and |c - cc| <= side/2, side = min(rows, cols) / 3
  Diamond:  |r - cr| + |c - cc| <= radius  (L1 norm ball)
  Letter:   5x5 pixel font scaled by min(rows, cols) / 12 (the preset uses H)
  Line:     single row at center, cols/4 to 3*cols/4

Gradient-following movement:
  Sample up to 50 target cells, find closest by Manhattan distance
  For each of 4 directions, pick the one minimizing distance to closest target
  Bonded cells do not move (structural stability)
```

**What to look for**

Shape assembly presets demonstrate emergent self-organization: cells scattered randomly across the grid gradually converge on the target shape, with bonding creating structural stability once cells reach their positions. The progress bar in the info panel tracks what fraction of target cells are occupied. Move the cursor with the arrow keys and press `d` to remove a 5×5 patch of cells. Removed cells are not replaced, but free cells that are still moving can fill the gap, with no global coordinator. The Self-Replicating Cluster preset shows exponential growth governed by local density: cells replicate only when they have fewer than 3 neighbors, creating an expanding frontier. In the Distributed Counter preset, each cell reads its neighbors (register C = neighbor count, register B = mean neighbor signal), adds one to register C, and signals register B if it is nonzero, else register C. The Signal Field view (`v`) shows these values diffusing, and the info panel shows the maximum signal. `v` cycles three views. Cells shows each state machine (`.` idle, `>` moving, `#` bonded, `*` signaling). Signal Field shows the communication layer. Target Overlay shows assembly progress: `#` is a cell on the target, `o` a cell off it, and `+` an empty target cell. `Space` plays, `s` steps, `+`/`-` set the speed, `i` toggles the info panel, and `r` resets.

**References**

- Goldstein, S.C., Campbell, J.D., and Mowry, T.C. "Programmable Matter." *IEEE Computer* 38(6), 2005. https://doi.org/10.1109/MC.2005.198
- Toffoli, T. and Margolus, N. *Cellular Automata Machines: A New Environment for Modeling.* MIT Press, 1987. https://doi.org/10.7551/mitpress/1763.001.0001
- Derakhshandeh, Z. et al. "Amoebot — A New Model for Programmable Matter." *SPAA*, 2014. https://doi.org/10.1145/2612669.2612712
