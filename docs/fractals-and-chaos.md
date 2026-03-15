# Fractals & Chaos

Self-similarity, strange attractors, and the beautiful geometry of nonlinear dynamics.

---

## Abelian Sandpile

### Background

The Abelian Sandpile Model (ASM) was introduced by Bak, Tang, and Wiesenfeld in 1987 as the first example of a system exhibiting self-organized criticality -- the tendency of large dissipative systems to drive themselves to a critical state without external tuning. When grains pile up on a grid and topple to neighbors at a threshold, the resulting avalanche-size distribution follows a power law. The model is "Abelian" because the final stable configuration is independent of the order in which unstable cells topple.

### Formulation

```
Grid: 2D integer lattice, each cell holds z(r, c) grains.
Threshold: z >= 4 triggers toppling.

Toppling rule (parallel update):
    z(r, c)     -= 4
    z(r-1, c)   += 1
    z(r+1, c)   += 1
    z(r, c-1)   += 1
    z(r, c+1)   += 1

Boundary: open -- grains at edges fall off and are lost.

Identity element computation:
    E = topple(2 * max_stable)
    identity = topple(2 * max_stable - E)
    where max_stable has z(r,c) = 3 for all cells.
```

Parameters by preset:

| Preset         | Drop Mode    | Drop Amount | Initial Pile | Steps/Frame |
|----------------|-------------|-------------|-------------|-------------|
| Single Tower   | center      | 1           | 0           | 1           |
| Big Pile       | center      | 0           | 10000       | 10          |
| Random Rain    | random      | 1           | 0           | 1           |
| Four Corners   | corners     | 1           | 0           | 1           |
| Diamond Seed   | diamond     | 1           | 0           | 1           |
| Checkerboard   | checkerboard| 0           | 0           | 5           |
| Max Stable     | max_stable  | 0           | 0           | 5           |
| Identity       | identity    | 0           | 0           | 10          |

### What to look for

The "Big Pile" preset produces a striking fractal pattern as 10,000 grains cascade outward from the center. Watch how the diamond-shaped boundary of the avalanche contains self-similar internal structure with four-fold symmetry. In "Random Rain" mode, the system self-organizes to a critical state where most of the grid sits at 3 grains, and single additions trigger cascading avalanches of all sizes. The Identity Element preset reveals the unique sandpile configuration that acts as a mathematical identity under the sandpile addition operation -- a beautiful fractal in its own right.

### References

- Bak, P., Tang, C., & Wiesenfeld, K. "Self-organized criticality: An explanation of the 1/f noise." *Physical Review Letters* 59(4), 1987. https://doi.org/10.1103/PhysRevLett.59.381
- Dhar, D. "Self-organized critical state of sandpile automaton models." *Physical Review Letters* 64(14), 1990. https://doi.org/10.1103/PhysRevLett.64.1613

---

## Strange Attractors

### Background

Strange attractors are geometric structures in phase space toward which chaotic dynamical systems evolve. Edward Lorenz discovered the first in 1963 while modeling atmospheric convection, revealing that deterministic systems can exhibit sensitive dependence on initial conditions -- popularly known as the "butterfly effect." The simulator implements six classical chaotic systems, each with distinct topology and symmetry properties, integrated using a second-order Runge-Kutta (midpoint) method.

### Formulation

```
Integration: RK2 midpoint method, dt = 0.005

Lorenz system (sigma, rho, beta):
    dx/dt = sigma * (y - x)
    dy/dt = x * (rho - z) - y
    dz/dt = x * y - beta * z

Roessler system (a, b, c):
    dx/dt = -y - z
    dy/dt = x + a * y
    dz/dt = b + z * (x - c)

Thomas system (b):
    dx/dt = sin(y) - b * x
    dy/dt = sin(z) - b * y
    dz/dt = sin(x) - b * z

Aizawa system (a, b, c, d, e, f):
    dx/dt = (z - b) * x - d * y
    dy/dt = d * x + (z - b) * y
    dz/dt = c + a*z - z^3/3 - (x^2 + y^2)(1 + e*z) + f*z*x^3

Halvorsen system (a):
    dx/dt = -a*x - 4*y - 4*z - y^2
    dy/dt = -a*y - 4*z - 4*x - z^2
    dz/dt = -a*z - 4*x - 4*y - x^2

Chen system (a, b, c):
    dx/dt = a * (y - x)
    dy/dt = (c - a) * x - x*z + c*y
    dz/dt = x * y - b * z
```

Default parameters:

| Attractor   | Key Parameters                              |
|-------------|---------------------------------------------|
| Lorenz      | sigma=10.0, rho=28.0, beta=8/3              |
| Roessler    | a=0.2, b=0.2, c=5.7                         |
| Thomas      | b=0.208186                                   |
| Aizawa      | a=0.95, b=0.7, c=0.6, d=3.5, e=0.25, f=0.1 |
| Halvorsen   | a=1.89                                       |
| Chen        | a=35.0, b=3.0, c=28.0                        |

### What to look for

The Lorenz attractor's iconic butterfly shape emerges as particles trace two lobes, switching unpredictably between them. Increase rho to 99.96 ("High Rho" preset) for a more chaotic regime with finer structure. The Thomas attractor has cyclically symmetric equations producing a smooth helical shape. The Halvorsen attractor exhibits three-fold rotational symmetry. Rotate the view with arrow keys to see the full 3D structure projected through two rotation angles (x-axis and z-axis). The density heatmap uses logarithmic scaling, so the most-visited regions glow brightest.

### References

- Lorenz, E. N. "Deterministic Nonperiodic Flow." *Journal of the Atmospheric Sciences* 20(2), 1963. https://doi.org/10.1175/1520-0469(1963)020<0130:DNF>2.0.CO;2
- Sprott, J. C. *Elegant Chaos: Algebraically Simple Chaotic Flows.* World Scientific, 2010. https://doi.org/10.1142/7183

---

## Fractal Explorer

### Background

The Mandelbrot set, defined by Benoit Mandelbrot in 1980, is the set of complex numbers c for which the iteration z -> z^2 + c does not diverge when started from z = 0. Its boundary has infinite fractal detail at every scale. The closely related Julia sets fix c and vary the starting point z. Together they form the most widely recognized objects in fractal geometry, illustrating how simple quadratic iteration over the complex plane generates unbounded complexity.

### Formulation

```
Mandelbrot set:
    z(0) = 0
    z(n+1) = z(n)^2 + c
    where c = (c_re, c_im) is the pixel coordinate
    Escape condition: |z|^2 > 4.0

Julia set:
    z(0) = (pixel_re, pixel_im)
    z(n+1) = z(n)^2 + c
    where c is a fixed complex constant
    Escape condition: |z|^2 > 4.0

Iteration (expanded real arithmetic):
    zr_new = zr^2 - zi^2 + c_re
    zi_new = 2 * zr * zi + c_im

Viewport mapping:
    half_height = 1.5 / zoom
    half_width  = half_height * (cols / (rows * 2.0))
```

Selected presets:

| Preset            | Type       | Center / c               | Zoom  | Max Iter |
|-------------------|-----------|--------------------------|-------|----------|
| Classic           | Mandelbrot | (-0.5, 0.0)             | 1x    | 80       |
| Seahorse Valley   | Mandelbrot | (-0.745, 0.113)         | 50x   | 200      |
| Elephant Valley   | Mandelbrot | (0.282, 0.01)           | 20x   | 200      |
| Minibrot          | Mandelbrot | (-1.749, 0.0)           | 500x  | 500      |
| Dendrite Julia    | Julia      | c = 0.0 + 1.0i          | 1x    | 100      |
| Douady Rabbit     | Julia      | c = -0.123 + 0.745i     | 1x    | 100      |
| Dragon Julia      | Julia      | c = -0.8 + 0.156i       | 1x    | 100      |

### What to look for

Zoom into the boundary of the Mandelbrot set to discover miniature copies of the full set (minibrots) embedded at every scale. The Seahorse Valley preset reveals spiral structures where the main cardioid meets the period-2 bulb. Each Julia set preset shows a different topology determined by where c lies relative to the Mandelbrot set: connected sets (c inside) versus Cantor-dust disconnected sets (c outside). Use the `a/A` and `s/S` keys to continuously vary the Julia parameter c and watch the set deform in real time.

### References

- Mandelbrot, B. B. *The Fractal Geometry of Nature.* W. H. Freeman, 1982. https://en.wikipedia.org/wiki/The_Fractal_Geometry_of_Nature
- Douady, A. & Hubbard, J. H. "Iteration des polynomes quadratiques complexes." *Comptes Rendus* 294, 1982. https://doi.org/10.1016/B978-0-12-164902-0.50014-X

---

## Snowflake Growth (Reiter Crystal)

### Background

Clifford Reiter's snowflake model (2005) simulates ice crystal growth on a hexagonal lattice through diffusion-limited aggregation of water vapor. By tuning deposition rate, background vapor concentration, and diffusion speed, the model reproduces the full range of natural snow crystal morphologies -- from simple hexagonal prisms to elaborate stellar dendrites. The hexagonal lattice is essential: it naturally produces the six-fold symmetry observed in real snowflakes.

### Formulation

```
Lattice: hexagonal grid using even-row offset coordinates.
Each cell has: frozen (boolean), vapor (float).

Parameters:
    alpha (deposition rate)  -- vapor added to receptive cells per step
    beta  (initial vapor)    -- background supersaturation level
    gamma (noise amplitude)  -- random perturbation on deposition
    mu    (diffusion rate)   -- fraction of vapor exchanged with neighbors

Algorithm per step (Reiter 2005):
    1. Identify receptive cells: non-frozen cells adjacent to frozen cells.
    2. Deposition: vapor(r,c) += alpha + uniform(-gamma, gamma)
       for each receptive cell.
    3. Diffusion among non-frozen, non-receptive cells:
       vapor_new(r,c) = (1 - mu) * vapor(r,c) + mu * avg(neighbors)
    4. Freezing: if vapor(r,c) >= 1.0 for a receptive cell, freeze it.
    5. Symmetry enforcement: newly frozen cells are mirrored
       across all 12 symmetry operations (6 rotations x 2 reflections)
       when 6-fold symmetric mode is enabled.
```

Selected presets:

| Preset           | alpha | beta | mu   | Symmetric |
|------------------|-------|------|------|-----------|
| Classic Dendrite | 0.40  | 0.40 | 0.80 | Yes       |
| Thin Needles     | 0.30  | 0.30 | 0.90 | Yes       |
| Broad Plates     | 0.50  | 0.55 | 0.50 | Yes       |
| Fernlike         | 0.65  | 0.35 | 0.70 | Yes       |
| Simple Hexagon   | 0.15  | 0.70 | 0.40 | Yes       |
| Noisy Crystal    | 0.40  | 0.40 | 0.80 | No        |

### What to look for

The interplay between alpha and beta determines crystal morphology. High beta (supersaturation) with low alpha produces broad plates; low beta with high alpha yields thin dendritic arms. The mu parameter controls diffusion: high mu smooths the vapor field and produces simpler shapes, while low mu creates steeper gradients and more branching. Disable symmetry (`s` key) to see naturalistic asymmetric crystals. The "Fernlike" preset (alpha=0.65) generates highly branched structures resembling biological ferns -- demonstrating that similar growth rules underlie both ice crystals and plant morphology.

### References

- Reiter, C. A. "A local cellular model for snow crystal growth." *Chaos, Solitons & Fractals* 23(4), 2005. https://doi.org/10.1016/j.chaos.2004.06.071
- Libbrecht, K. G. "The physics of snow crystals." *Reports on Progress in Physics* 68(4), 2005. https://doi.org/10.1088/0034-4885/68/4/R03

---

## Erosion Patterns

### Background

Hydraulic erosion simulates how flowing water sculpts terrain over time, carving river valleys, canyons, and dendritic drainage networks. This implementation uses a simplified shallow-water model where rainfall accumulates, flows downhill proportional to height differences, erodes sediment proportional to flow velocity, and deposits sediment when flow slows. The terrain itself is generated using layered smooth noise (inspired by diamond-square algorithms) with multiple octaves for natural-looking heightmaps.

### Formulation

```
Terrain generation: multi-octave smooth noise with bilinear interpolation.
    terrain(r,c) = sum over octaves of: amplitude * interpolated_noise(frequency)

Erosion step:
    1. Rainfall:
       water(r,c) += rain_rate * (0.8 + 0.4 * random())

    2. Flow routing (4-connected neighbors):
       effective_height h = terrain(r,c) + water(r,c)
       flow goes to neighbors with lower h, proportional to height difference
       flow_out = min(water, total_height_diff * 0.5)

    3. Erosion:
       velocity = height_diff * flow_amount
       erode_amount = solubility * velocity
       erode_amount = min(erode_amount, terrain(r,c) * 0.1)
       terrain(r,c) -= erode_amount

    4. Deposition:
       When water pools (no downhill neighbor):
           deposit = min(sediment, deposition_rate * water)
           terrain(r,c) += deposit

    5. Evaporation:
       water(r,c) -= min(water, evap_rate)
       Remaining sediment deposited when water fully evaporates.

    Boundary: edges drain at 50% rate each step.
```

Presets:

| Preset         | Rain   | Evap   | Solubility | Deposition | Terrain  |
|----------------|--------|--------|-----------|-----------|----------|
| River Valley   | 0.012  | 0.004  | 0.008     | 0.015     | gentle   |
| Mountain Gorge | 0.015  | 0.003  | 0.015     | 0.010     | steep    |
| Badlands       | 0.020  | 0.003  | 0.020     | 0.008     | rough    |
| Alpine Peaks   | 0.008  | 0.002  | 0.012     | 0.012     | alpine   |
| Volcanic Island| 0.014  | 0.004  | 0.014     | 0.012     | volcano  |

### What to look for

Watch dendritic drainage networks emerge as water finds optimal paths downhill. The "Badlands" preset has high solubility and rainfall, producing dense branching channel systems reminiscent of aerial photographs of eroded landscapes. The "Volcanic Island" preset starts with a central peak and develops radial drainage patterns. Compare "River Valley" (gentle terrain, wide meandering rivers) with "Mountain Gorge" (steep terrain, narrow deep canyons) to see how slope controls erosion morphology. Blue cells indicate water depth; terrain is color-coded by elevation from dark lowlands to bright peaks.

### References

- Musgrave, F. K., Kolb, C. E., & Mace, R. S. "The Synthesis and Rendering of Eroded Fractal Terrains." *Computer Graphics (SIGGRAPH '89)* 23(3), 1989. https://doi.org/10.1145/74334.74337
- Cordonnier, G. et al. "Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion." *Computer Graphics Forum* 35(2), 2016. https://doi.org/10.1111/cgf.12820

---

## Chaos Game / IFS Fractals

### Background

Iterated Function Systems (IFS), formalized by Michael Barnsley in 1988, generate fractals by randomly and repeatedly applying a set of contractive affine transformations to a point. The "Chaos Game" is the stochastic algorithm: pick a transform at random (weighted by probability), apply it to the current point, plot the result, and repeat. From this simple random process, deterministic fractal structure emerges -- the attractor of the IFS. Barnsley's famous fern demonstrated that just four affine maps can encode a botanically realistic image.

### Formulation

```
Affine transform (a, b, c, d, e, f, prob):
    x' = a*x + b*y + e
    y' = c*x + d*y + f

Algorithm (Chaos Game):
    1. Start at arbitrary point (x, y).
    2. Choose transform i with probability prob_i.
    3. Apply: (x, y) <- transform_i(x, y)
    4. Plot (x, y) on the density grid.
    5. Repeat from step 2.

    50 initial iterations are discarded (transient warm-up).
```

IFS transform tables:

**Barnsley Fern** (4 transforms):

| Transform | a     | b     | c     | d     | e   | f   | prob |
|-----------|-------|-------|-------|-------|-----|-----|------|
| Stem      | 0.00  | 0.00  | 0.00  | 0.16  | 0.0 | 0.0 | 0.01 |
| Main      | 0.85  | 0.04  | -0.04 | 0.85  | 0.0 | 1.6 | 0.85 |
| Left      | 0.20  | -0.26 | 0.23  | 0.22  | 0.0 | 1.6 | 0.07 |
| Right     | -0.15 | 0.28  | 0.26  | 0.24  | 0.0 | 0.44| 0.07 |

**Sierpinski Triangle** (3 transforms, equal probability 1/3):

| Transform | a   | b   | c   | d   | e    | f   |
|-----------|-----|-----|-----|-----|------|-----|
| Bottom-L  | 0.5 | 0.0 | 0.0 | 0.5 | 0.0  | 0.0 |
| Bottom-R  | 0.5 | 0.0 | 0.0 | 0.5 | 0.5  | 0.0 |
| Top       | 0.5 | 0.0 | 0.0 | 0.5 | 0.25 | 0.5 |

Other presets include: Sierpinski Carpet (8 transforms), Vicsek Snowflake (5 transforms), Heighway Dragon (2 transforms), Maple Leaf (4 transforms), Koch Snowflake (4 transforms with rotation), and Crystal (6 rotated arms + center).

### What to look for

Enable color mode (`c` key) to see which transform produced each point -- this reveals the recursive decomposition of the fractal. In the Barnsley Fern, the green "main" transform (probability 0.85) draws the overall frond shape, while the left and right transforms create the sub-fronds. The Heighway Dragon uses only two transforms, both involving 45-degree rotations, producing a space-filling curve. Increase the point rate (`>` key) to watch structure emerge faster. The density field uses logarithmic scaling: regions visited by many transforms overlap and glow brighter, highlighting the invariant measure of the IFS.

### References

- Barnsley, M. F. *Fractals Everywhere.* Academic Press, 1988. https://doi.org/10.1016/C2009-0-21078-4
- Peitgen, H.-O., Juergens, H., & Saupe, D. *Chaos and Fractals: New Frontiers of Science.* Springer, 1992. https://doi.org/10.1007/978-1-4757-4740-9

---

## L-System Fractal Garden

### Background

Lindenmayer systems (L-systems), invented by biologist Aristid Lindenmayer in 1968, model plant growth through parallel string rewriting. A grammar of production rules expands an axiom string over successive generations; the resulting string is then interpreted as turtle graphics commands to draw branching structures. This implementation extends classical L-systems with seasonal cycles (spring/summer/autumn/winter), wind effects, light competition between plants, genetic mutation, and seed dispersal -- creating an ecological simulation built on fractal geometry.

### Formulation

```
L-system grammar:
    Axiom:   initial string (e.g., "F")
    Rules:   character -> replacement string
    Symbols: F = draw forward, + = turn right, - = turn left,
             [ = push state (branch), ] = pop state (leaf point),
             X = placeholder (no drawing, only expanded by rules)

Expansion: apply all rules in parallel to every character in the string.

Turtle interpretation:
    heading starts at -pi/2 (upward) + light_bias
    F: draw line segment of length base_len * length_scale^depth
    +: heading += angle (degrees)
    -: heading -= angle (degrees)
    [: push (x, y, heading, length, depth) onto stack; depth += 1
    ]: pop state; mark leaf/flower at current position

Wind model:
    wind_bend = wind * height_fraction * 0.4 * sin(wind_phase + y * 0.1)
    Applied to heading when drawing F segments.

Growth rate per season:
    Spring: 1.0, Summer: 0.7, Autumn: 0.2, Winter: 0.0
    Effective rate = growth_rate * season_factor * plant_health

Light competition:
    For each x-column, the plant with the topmost segment gets full light.
    Shaded plants receive 30% light, reducing their health.
```

Selected species grammars:

| Species      | Axiom | Rule for F/X                           | Angle | Depth |
|-------------|-------|----------------------------------------|-------|-------|
| Binary Tree | F     | F -> FF+[+F-F-F]-[-F+F+F]             | 30    | 8     |
| Fern        | X     | X -> F+[[X]-X]-F[-FX]+X, F -> FF      | 22    | 7     |
| Bush        | F     | F -> F[+F]F[-F][F]                     | 25.7  | 6     |
| Pine        | F     | F -> F[+F]F[-F]F                       | 35    | 8     |
| Sakura      | F     | F -> FF+[+F-F]-[-F+F]                  | 28    | 7     |
| Coral       | F     | F -> F[+F][--F]F[++F][-F]              | 24    | 5     |

### What to look for

In the "Garden" preset, multiple species compete for light: taller trees shade smaller plants, reducing their health and growth rate. Enable mutation (`m` key) to introduce random changes to branching rules and angles -- over many generations, plants evolve adapted forms. Watch the seasonal cycle: flowers bloom in spring and summer, leaves turn yellow and fall in autumn, deciduous trees stand bare in winter while evergreens persist. Wind (`w/W` keys) bends branches proportionally to their height, creating naturalistic swaying. The "Competition" preset with seven species shows ecological dynamics: some species thrive while others are outcompeted.

### References

- Lindenmayer, A. "Mathematical models for cellular interaction in development." *Journal of Theoretical Biology* 18(3), 1968. https://doi.org/10.1016/0022-5193(68)90079-9
- Prusinkiewicz, P. & Lindenmayer, A. *The Algorithmic Beauty of Plants.* Springer-Verlag, 1990. https://doi.org/10.1016/0022-5193(68)90079-9

---

## Lissajous Curve / Harmonograph

### Background

Lissajous figures, studied by Jules Antoine Lissajous in 1857, are the parametric curves traced when two perpendicular simple harmonic oscillations are combined. When the frequency ratio is rational, the curve closes; irrational ratios produce space-filling patterns. The harmonograph extends this by adding secondary oscillators and exponential damping, simulating the physical instrument invented in the 19th century where pendulums drive a pen across paper. The resulting figures -- spiraling, decaying, and interfering -- demonstrate the rich geometry of superposed oscillations.

### Formulation

```
Basic Lissajous curve:
    x(t) = A_x * sin(freq_a * t + phase)
    y(t) = A_y * sin(freq_b * t)

Harmonograph extension (with secondary oscillators and damping):
    decay(t) = exp(-damping * t)
    x(t) = A_x * decay * sin(freq_a * t + phase)
          + A_x * 0.5 * decay * sin(freq_c * t + phase2)
    y(t) = A_y * decay * sin(freq_b * t)
          + A_y * 0.5 * decay * sin(freq_d * t)

Parameters:
    freq_a, freq_b   -- primary oscillator frequencies
    freq_c, freq_d   -- secondary oscillator frequencies (0 = disabled)
    phase, phase2     -- phase offsets (radians)
    damping           -- exponential decay rate (0 = no decay)
    A_x, A_y          -- amplitudes (default 0.9)
    dt                 -- time step (0.02)
```

Presets:

| Preset        | freq_a | freq_b | freq_c | freq_d | phase    | damping | Trail  |
|--------------|--------|--------|--------|--------|----------|---------|--------|
| Classic 3:2  | 3.0    | 2.0    | --     | --     | pi/4     | 0       | 4000   |
| Figure Eight | 2.0    | 1.0    | --     | --     | pi/2     | 0       | 4000   |
| Star         | 5.0    | 4.0    | --     | --     | pi/4     | 0       | 4000   |
| Harmonograph | 2.01   | 3.0    | --     | --     | pi/6     | 0.003   | 8000   |
| Lateral      | 2.0    | 3.0    | 2.005  | 3.003  | pi/4     | 0.002   | 10000  |
| Rose         | 7.0    | 4.0    | --     | --     | 0        | 0       | 4000   |
| Decay Spiral | 10.0   | 9.0    | --     | --     | pi/3     | 0.008   | 6000   |
| Knot         | 5.0    | 3.0    | --     | --     | pi/7     | 0.001   | 8000   |

### What to look for

The frequency ratio determines the curve's topology: the "Classic 3:2" preset traces a closed figure with 3 lobes horizontally and 2 vertically. The "Harmonograph" preset uses a slightly irrational ratio (2.01:3.0) with damping, so the curve slowly shifts phase as it decays, filling a region before fading to stillness -- this mimics a real physical harmonograph. The "Lateral" preset adds secondary oscillators at frequencies very close to the primaries (2.005 and 3.003), creating intricate beating patterns and slowly evolving interference figures. Adjust `a/A` and `b/B` to change frequency ratios interactively and watch the figure restructure. The intensity accumulation on the canvas reveals which regions the curve visits most frequently.

### References

- Lissajous, J. A. "Memoire sur l'etude optique des mouvements vibratoires." *Annales de Chimie et de Physique* 51, 1857. https://doi.org/10.1002/andp.18571780611
- Ashton, A. *Harmonograph: A Visual Guide to the Mathematics of Music.* Wooden Books, 2003. https://www.woodenbooks.com/harmonograph
