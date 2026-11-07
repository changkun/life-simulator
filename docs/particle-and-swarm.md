# Particle & Swarm Systems

Emergent collective behavior from simple individual rules — flocking, foraging, and self-organization.

---

## Active Matter

### Background

Active matter is a class of non-equilibrium systems composed of self-propelled units that extract energy from their environment and convert it into directed motion. Unlike passive particles governed by detailed balance, active particles break time-reversal symmetry at the individual level, producing collective phenomena with no equilibrium analogue. The field spans biological systems (bacterial suspensions, cytoskeletal filaments, bird flocks) and synthetic ones (Janus colloids, vibrated granular rods, light-activated swimmers).

Two landmark theoretical frameworks define the field. The Vicsek model (1995) showed that point particles with constant speed and local alignment interactions undergo a genuine phase transition from disordered gas to long-range-ordered flock — remarkable because the Mermin-Wagner theorem forbids such order in equilibrium 2D systems. Motility-induced phase separation (MIPS), formalized by Cates and Tailleur (2015), demonstrated that particles which simply slow down in crowds will spontaneously phase-separate into dense liquid-like clusters and dilute gas, with no attractive interactions required.

### Formulation

Each particle has position (r, c) on a toroidal domain, heading angle θ, velocity (vr, vc), and a fuel level f that scales propulsion. Fuel regenerates to 1 and never drops, so it has no effect. A spatial hash gives O(N) neighbor lookup.

```
Per-timestep update for particle i:

1. NEIGHBOR SEARCH (spatial grid, cell_size = max(align_r, repel_r)):
   For each neighbor j within grid cell and 8 adjacent cells:
     dr = r_j - r_i  (with toroidal minimum-image convention)
     dc = c_j - c_i
     dist = sqrt(dr² + dc²)

2. ALIGNMENT TORQUE (if dist < align_r and align_w > 0):
   Polar:    accumulate sin(θ_j), cos(θ_j)
   Nematic:  accumulate sin(2θ_j), cos(2θ_j)  (double-angle trick)
   target = atan2(sin_sum, cos_sum)  [÷2 for nematic]
   θ_new += align_w * angular_diff(target, θ) * 0.3

3. SHORT-RANGE REPULSION (if dist < repel_r):
   overlap = 1 - dist/repel_r
   F_repel -= (dr, dc)/dist * overlap * repel_w

4. CONTRACTILE/EXTENSILE DIPOLE (if |contract| > 0 and dist < align_r):
   Project self-propulsion direction onto pair axis:
     dot = e_i · n_ij
   Contractile (>0) pulls along axis, extensile (<0) pushes:
     F_dipole += n_ij * contract * dot / (dist + 0.5)

5. SELF-ROTATION: θ_new += spin_w

6. RUN-AND-TUMBLE: with probability τ, θ_new = random in [0, 2π)

7. ANGULAR NOISE: θ_new += N(0, η)

8. CROWD SLOWDOWN (when τ > 0 and at least one aligning neighbor was counted in step 2):
   local_density = n_align / (π * align_r²)
   prop_speed = v₀ / (1 + 5 * local_density)

9. VELOCITY UPDATE:
   v_new = propulsion + F_repel + F_dipole
   v_new = v_new * (1 - friction) + v_old * friction * 0.5
   |v_new| clamped to 3 * v₀

10. POSITION UPDATE (toroidal):
    r_new = (r + vr) mod rows
    c_new = (c + vc) mod cols
```

The order parameter ψ quantifies collective alignment: ψ = |Σ exp(iθ)| / N for polar (Vicsek), ψ = |Σ exp(2iθ)| / N for nematic. ψ → 1 indicates long-range order; ψ → 0 indicates disorder. The title bar shows ψ.

The crowd slowdown counts only neighbors inside `align_r` while `align_w > 0`. The **Motility-Induced Clustering** preset has `align_r = 0`, so it never slows down in crowds; its clustering comes from repulsion and tumbling alone. In presets with `align_r > 0`, raising the tumble rate with `t` enables the slowdown.

### Presets

- **Bacterial Turbulence**: Dense pushers (extensile dipoles, contract = −0.3) with nematic alignment. Produces chaotic vortex streets and jet-like flows characteristic of dense bacterial suspensions like *B. subtilis*.
- **Active Nematics**: Rod-like extensile particles (contract = −0.5) with strong nematic alignment. Nucleates ±½ topological defect pairs that unbind and annihilate — the hallmark of active nematic turbulence observed in microtubule-kinesin mixtures.
- **Motility-Induced Clustering**: Run-and-tumble particles (τ = 0.05, v₀ = 1.0) with no alignment and strong repulsion. Particles tumble at random and push each other apart.
- **Vicsek Flocking**: Polar aligning particles with moderate noise (η = 0.3). Demonstrates the Vicsek transition: below a critical noise the system orders into a coherent flock.
- **Active Spinner Gas**: Self-rotating particles (spin_w = 0.3) that turn by a fixed angle each step, so they travel in circles. Collisions are plain repulsion; there is no odd-elastic force.
- **Contractile Gel**: Puller particles (contract = +0.5) that tend to form asters and contractile networks, as in actomyosin gels where motors pull filaments inward.

### Controls

`v` cycles the view (Arrows, Density, Vorticity). `s`/`S` change v₀, `e`/`E` the noise η, `a`/`A` the alignment weight, `p`/`P` the repulsion weight, and `t`/`T` the tumble rate. `+`/`-` set steps per frame. A mouse click adds 15 particles.

### What to look for

In **Bacterial Turbulence**, look for vortex patterns with a characteristic length scale. Switch to the Vorticity view (`v`) to see counter-rotating vortex pairs. **Active Nematics** is set up for ±½ topological defects (comet-shaped +½, trefoil −½) that move and annihilate. In **Motility-Induced Clustering**, use the Density view to see where particles pile up. **Vicsek Flocking** shows an order-disorder transition: use `e`/`E` to tune the noise through the critical point and watch ψ change. In **Active Spinner Gas**, watch the circling trajectories. **Contractile Gel** may produce aster-like structures where particles converge.

### References

- Vicsek, T., Czirók, A., Ben-Jacob, E., Cohen, I. & Shochet, O. "Novel type of phase transition in a system of self-driven particles." *Physical Review Letters*, 75(6), 1226-1229, 1995. https://doi.org/10.1103/PhysRevLett.75.1226
- Cates, M. E. & Tailleur, J. "Motility-induced phase separation." *Annual Review of Condensed Matter Physics*, 6, 219-244, 2015. https://doi.org/10.1146/annurev-conmatphys-031214-014710
- Marchetti, M. C., et al. "Hydrodynamics of soft active matter." *Reviews of Modern Physics*, 85(3), 1143-1189, 2013. https://doi.org/10.1103/RevModPhys.85.1143

---

## Granular Dynamics

### Background

Granular materials — sand, grains, powders, cereals — are sometimes called "the fourth state of matter" because they exhibit solid-like, liquid-like, and gas-like behavior depending on conditions, yet fit none of these categories. A sandpile can support weight like a solid (via force chains), flow like a liquid (avalanches, hopper discharge), or behave like a gas (dilute inelastic particles). The Discrete Element Method (DEM), introduced by Cundall and Strack (1979), models each grain as an individual particle subject to contact forces, gravity, and friction. From these simple ingredients emerge rich phenomena: force chain networks (branching stress paths visible under photoelastic imaging), jamming transitions (where a flowing granular medium suddenly arrests), avalanche cascades exhibiting self-organized criticality, arching and clogging in hoppers, and the Brazil nut effect (large grains rising to the top when shaken via granular convection).

This mode fills the gap between the project's rule-based Falling Sand cellular automaton (which uses material-type swap rules) and its continuum fluid modes (Navier-Stokes, LBM). Here every grain is a physical particle with Hertzian contact, Coulomb friction, and inertia.

### Formulation

Each grain has position (r, c), velocity (vr, vc), radius, mass (proportional to area, m = πr²), accumulated contact force magnitude, and a large-grain flag. Spatial hashing (cell size 2.0) provides O(N) neighbor lookup.

```
Contact force between grains i and j (if overlapping):
    dr = r_j - r_i,  dc = c_j - c_i
    dist = sqrt(dr² + dc²)
    overlap = (rad_i + rad_j) - dist

    Normal direction: n = (dr, dc) / dist

    Hertzian normal force:
        F_n = k * overlap^1.5                    (nonlinear spring)

    Normal damping (dashpot):
        v_rel_n = (v_j - v_i) · n
        F_damp = -0.3 * k * v_rel_n * sqrt(overlap)
        F_n_total = max(0, F_n + F_damp)         (no tensile contact)

    Coulomb friction (regularized):
        v_rel_t = (v_j - v_i) · t                (tangential relative velocity)
        F_t_max = μ * F_n_total                   (Coulomb limit)
        F_t = clamp(-0.5 * k * v_rel_t * sqrt(overlap), -F_t_max, F_t_max)

    Apply equal and opposite forces to i and j.

Wall collisions:
    Axis-aligned walls: Hertzian normal force k * overlap^1.5, plus friction
        mu * F_n opposing the sliding velocity (no dashpot; the ceiling has no friction)
    Line-segment walls (hopper funnel): project particle center onto segment,
        compute overlap from closest point, apply normal + friction forces

Velocity and position update (symplectic Euler):
    a = gravity + F_contact / mass + shake_offset / mass
    v_new = (v + a) * (1 - damping)
    |v_new| clamped to 3.0
    r_new = r + v_new
    Hard boundary clamp with restitution coefficient

Shaking (Brazil Nut Effect preset):
    shake_offset = A * sin(gen * ω * 2π)         (vertical force term)

Drum rotation (Drum Rotation preset):
    gravity direction rotates: θ += 0.01 per step
    g_r = |g| * cos(θ),  g_c = |g| * sin(θ)
```

The Force Chains view shows the largest normal force at each contact midpoint, decayed by 0.7 per step so the pattern persists.

### Presets

- **Hopper Flow**: Funnel of two converging walls with a narrow outlet. Grains can arch and clog at the aperture; tilt gravity sideways (`t`/`T`) to restart flow.
- **Avalanche Slope**: A pile of grains at the bottom centre, settling toward the angle of repose. Add grains with a click to trigger avalanches, as in self-organized criticality models (Bak-Tang-Wiesenfeld).
- **Brazil Nut Effect**: Mixed small and large grains under vertical shaking. Large grains (yellow diamonds) tend to rise to the surface through granular convection.
- **Force Chain Network**: Densely packed grains under strong gravity with high stiffness. Switch to the Force Chains view (`v`) to see the stress network: a few contacts carry most of the load while many grains bear almost none.
- **Granular Gas**: Dilute, highly elastic grains (restitution 0.9) with no gravity and random initial velocities. Dissipation can cause dense clumps to form, separated by voids.
- **Drum Rotation**: Grains in a container whose gravity direction rotates slowly, as in a rotating drum. Expect an avalanching surface flow.

### Controls

`v` cycles the view (Grains, Force Chains, Density). `g`/`G` change gravity strength, `t`/`T` tilt gravity sideways, `f`/`F` friction, `e`/`E` restitution, `s`/`S` shake amplitude, and `k`/`K` contact stiffness. `+`/`-` set steps per frame. A mouse click drops 12 grains.

### What to look for

In **Hopper Flow**, watch free flow give way to complete arrest when an arch forms across the aperture. Tilting gravity can break the arch. In **Force Chain Network**, the Force Chains view shows that stress is carried unevenly: a few branching chains hold large forces while neighbors are nearly stress-free. The **Brazil Nut** preset shows size segregation: large grains work their way upward as the box shakes. **Granular Gas** starts uniform and can develop dense clusters separated by voids. **Avalanche Slope** produces avalanches of varying size when grains are added.

### References

- Cundall, P. A. & Strack, O. D. L. "A discrete numerical model for granular assemblies." *Géotechnique*, 29(1), 47-65, 1979. https://doi.org/10.1680/geot.1979.29.1.47
- Jaeger, H. M., Nagel, S. R. & Behringer, R. P. "Granular solids, liquids, and gases." *Reviews of Modern Physics*, 68(4), 1259-1273, 1996. https://doi.org/10.1103/RevModPhys.68.1259
- Bak, P., Tang, C. & Wiesenfeld, K. "Self-organized criticality: An explanation of the 1/f noise." *Physical Review Letters*, 59(4), 381-384, 1987. https://doi.org/10.1103/PhysRevLett.59.381

---

## Falling Sand

### Background

Falling sand simulations belong to the family of cellular automaton models that approximate granular material dynamics under gravity. Popularized in the early 2000s through browser-based "falling sand games," the genre traces its conceptual roots to lattice gas automata and granular physics. Each cell contains an element type — sand, water, fire, stone, oil, plant, or steam — and the system's richness arises from pairwise interaction rules between these materials.

### Formulation

The simulation processes cells bottom-to-top with randomized column order to avoid directional bias. Each element obeys type-specific rules:

```
Element behaviors (per tick):

SAND:   Try move to (r+1, c). If blocked by water or oil, swap with it (sand sinks).
        Otherwise try diagonal (r+1, c +/- 1).

WATER:  Try fall (r+1, c), then diagonal, then flow sideways (r, c +/- 1).
        Sinks below oil (density: water > oil).

FIRE:   Rises upward with P(move_up) = 0.7, lateral drift in {-1, 0, 0, 1}.
        Lifetime = 12 + rand(0..8) ticks.
        Ignites adjacent plant (P = 0.4), oil (P = 0.5).
        Evaporates adjacent water to steam (P = 0.08).
        Dying fire produces steam with P = 0.2.

PLANT:  Grows into an empty cell when a 4-neighbor is water (P = 0.05).
        Growth directions: up, diagonal-up, sideways.

OIL:    Liquid behavior (fall, diagonal, sideways). Floats above water.
        Highly flammable (fire ignition P = 0.5).

STEAM:  Rises with lateral drift. After 15 + rand(0..10) ticks it condenses to water
        with P = 0.4, otherwise vanishes.

STONE:  Static. Immovable barrier.
```

### Presets

- **Hourglass**: Sand falling through a narrow gap.
- **Rainfall**: Water drops falling on stone platforms.
- **Bonfire**: Fire burning through a plant forest.
- **Sandbox**: Empty grid for free drawing.
- **Lava Lamp**: Water and sand mixing.
- **Forest Fire**: Dense forest with fire ignition points.
- **Oil Refinery**: Oil floating on water with fire hazards.
- **Waterfall**: Water cascading over stone ledges.

### Controls

Move the cursor with the arrow keys or `h`/`j`/`k`/`l`. Press `Enter` (or `d`) to paint with the current brush. `1`-`7` select sand, water, fire, stone, plant, oil or steam; `0` erases. `+`/`-` change the brush size (1 to 5). `r` clears the grid.

### What to look for

Sand piles into heaps and slides down diagonal slopes. Water flows around obstacles and levels out, while oil floats on top of it. Fire spreads through plants and oil, and the steam-condensation cycle forms a simple water cycle. The Hourglass preset shows granular flow through a narrow aperture.

### References

- Bak, P., Tang, C., & Wiesenfeld, K. "Self-organized criticality." *Physical Review A*, 38(1), 364-374, 1988. https://doi.org/10.1103/PhysRevA.38.364
- Batty, M. "Cities and Complexity." MIT Press, 2005. (Chapter on cellular automata and urban simulation.) https://mitpress.mit.edu/books/cities-and-complexity

---

## Boids Flocking

### Background

Boids is Craig Reynolds' 1986 algorithm for simulating the coordinated motion of animal groups — bird flocks, fish schools, insect swarms. Reynolds showed that three local steering rules, applied independently by each agent, are sufficient to produce globally coherent flocking behavior without any centralized control. The model became foundational in computer graphics (used in films from *Batman Returns* onward) and remains central to swarm intelligence research.

### Formulation

Each boid has position (r, c) and velocity (vr, vc) on a toroidal grid. At each step, three steering forces are computed using pairwise toroidal distances:

```
For each boid i, accumulate steering from all neighbors j:

SEPARATION (radius R_s, weight W_s):
    If dist(i,j) < R_s:  steer_sep += -(dr, dc) / dist^2

ALIGNMENT (radius R_a, weight W_a):
    If dist(i,j) < R_a:  accumulate velocity of j
    steer_ali = (avg_neighbor_vel - vel_i) * W_a

COHESION (radius R_c, weight W_c):
    If dist(i,j) < R_c:  accumulate relative position of j
    steer_coh = avg_neighbor_offset * W_c * 0.1

Velocity update:
    v_new = v_old + (steer_sep * W_s + steer_ali + steer_coh) * 0.1
    |v_new| clamped to max_speed
    If |v_new| < 0.1: restart in a random direction at speed 0.2

Position update (toroidal wrap):
    pos_new = (pos_old + v_new) mod grid_size
```

The boid count is a fraction of the grid area (at least 30). Each boid starts inside a disc around the centre with a random velocity.

### Presets

| Preset | Boids / cell | R_s | R_a | R_c | W_s | W_a | W_c | max_speed |
|---|---|---|---|---|---|---|---|---|
| Murmuration | 0.08 | 2.5 | 7.0 | 12.0 | 2.5 | 1.2 | 1.0 | 1.2 |
| Fish School | 0.06 | 3.0 | 6.0 | 10.0 | 1.5 | 1.5 | 1.8 | 0.6 |
| Swarm | 0.10 | 2.0 | 10.0 | 15.0 | 1.0 | 0.8 | 0.5 | 1.5 |
| Migration | 0.04 | 3.0 | 15.0 | 20.0 | 1.2 | 2.0 | 0.8 | 1.0 |
| Dense Flock | 0.12 | 2.0 | 5.0 | 8.0 | 2.0 | 1.5 | 2.0 | 0.8 |
| Chaos | 0.10 | 4.0 | 6.0 | 8.0 | 3.0 | 0.5 | 0.3 | 1.8 |

The menu describes Murmuration as having "predator avoidance", but the code has no predator.

### Controls

`s`/`S` change the separation radius, `a`/`A` the alignment radius, and `c`/`C` the cohesion radius. The weights and max speed are fixed per preset. `+`/`-` set steps per frame. `r` re-creates the flock from the current preset.

### What to look for

Coherent flocking emerges from purely local rules. A larger separation radius (`s`) pushes boids apart and breaks the flock into smaller groups. A larger alignment radius (`a`) lets each boid match more neighbors, which gives longer parallel streams. A larger cohesion radius (`c`) pulls boids toward a wider neighborhood, so the flock draws together. The shift between ordered flocking and disordered swarming as parameters change resembles phase transitions studied in active matter.

### References

- Reynolds, C. W. "Flocks, herds and schools: A distributed behavioral model." *ACM SIGGRAPH Computer Graphics*, 21(4), 25-34, 1987. https://doi.org/10.1145/37402.37406
- Vicsek, T., et al. "Novel type of phase transition in a system of self-driven particles." *Physical Review Letters*, 75(6), 1226-1229, 1995. https://doi.org/10.1103/PhysRevLett.75.1226

---

## Particle Life

### Background

Particle Life (also called "Primordial Soup") was popularized by Jeffrey Ventrella and later by Tom Molinari's viral simulations. It extends simple particle systems by assigning each particle a type and defining attraction/repulsion strengths between all type pairs via a random matrix. Despite having no explicit chemistry, the system spontaneously produces lifelike behaviors: clustering, orbiting, chasing, and symbiotic co-rotation that evoke biological organisms.

### Formulation

Each particle has position (r, c), velocity (vr, vc), and a discrete type t in {0, ..., N-1}. An N x N interaction matrix A[i][j] in [-1, 1] defines the force between types. Forces are computed pairwise on a toroidal domain:

```
For each particle pair (i, j) with types (t_i, t_j):
    d = toroidal_distance(i, j)
    if d > max_radius or d < 0.01: skip

    rel_dist = d / max_radius          (normalized to [0, 1])

    Force profile:
        if rel_dist < 0.3:
            force = (rel_dist / 0.3) - 1.0      (short-range repulsion)
        else:
            force = A[t_i][t_j] * (1.0 - |2.0 * rel_dist - 1.3| / 0.7)
            force = clamp(force, -1, 1)

    F_i += normalize(dr, dc) * force * force_scale

Velocity update:
    v_new = (v_old + F) * (1 - friction)
    |v_new| clamped to 2.0

Position update:
    pos_new = (pos_old + v_new) mod grid_size
```

The matrix is not symmetric, so type A can chase type B while B flees.

### Presets

- **Primordial Soup**: 6 types, random rules, friction 0.5.
- **Symbiosis**: 4 types, fixed seed 42, friction 0.4.
- **Clusters**: 3 types, fixed seed 123, friction 0.6.
- **Predator-Prey**: 5 types, fixed seed 7, friction 0.3.
- **Galaxy**: 4 types, fixed seed 314, large radius 25, friction 0.35.
- **Chaos**: 8 types, random rules, force scale 0.07, friction 0.25.

Presets with a seed give the same rules every time; the others draw new rules on each reset.

### Controls

`f`/`F` change friction, `d`/`D` the maximum interaction radius, and `g`/`G` the force scale. `x` draws a new random matrix and keeps the particles. `+`/`-` set steps per frame. `r` resets the preset.

### What to look for

The force profile is key: universal short-range repulsion prevents collapse, while the type-dependent mid-range zone creates the diversity. With some matrices, lifelike structures appear: clusters that orbit each other, types that chase other types, or stable pairs. Press `x` to re-randomize the matrix and reshape the ecosystem in real time. Higher friction damps motion and favors stable structures; lower friction gives faster, more chaotic dynamics.

### References

- Ventrella, J. "Clusters." 2017. https://ventrella.com/Clusters/
- Chan, B. W.-C. "Lenia: Biology of Artificial Life." *Complex Systems* 28(3), 2019. https://doi.org/10.25088/ComplexSystems.28.3.251

---

## Physarum Slime Mold

### Background

This model simulates the transport network behavior of *Physarum polycephalum*, a slime mold that constructs near-optimal networks between food sources. Jeff Jones (2010) developed the agent-based model used here, where mobile agents deposit a chemical trail, sense the trail gradient, and steer toward higher concentrations. The resulting patterns include branching networks, rings, and Voronoi-like tessellations. Real *Physarum* has been shown to build networks comparable to the Tokyo rail system (Tero et al., 2010).

### Formulation

Each agent has position (r, c) and a heading angle theta. A 2D trail map T[r][c] stores chemical concentration in [0, 1].

```
Agent update (sense-rotate-move-deposit):
    1. SENSE at three positions ahead:
       F_left  = T[pos + sensor_dist * dir(theta + sensor_angle)]
       F_center = T[pos + sensor_dist * dir(theta)]
       F_right = T[pos + sensor_dist * dir(theta - sensor_angle)]

    2. ROTATE toward strongest signal:
       if F_center > F_left and F_center > F_right:  keep heading
       elif F_center < F_left and F_center < F_right: random turn +/- turn_speed
       elif F_left > F_right:  theta += turn_speed
       elif F_right > F_left:  theta -= turn_speed

    3. MOVE: pos_new = pos + move_speed * dir(theta)   (toroidal wrap)

    4. DEPOSIT: T[pos_new] = min(1.0, T[pos_new] + deposit_amount)

Trail diffusion and decay (per tick):
    T_new[r][c] = max(0, (3x3 box blur of T at (r,c)) / 9 - decay_rate)
```

Parameters: sensor angle (SA, radians), sensor distance (SD), turn speed (TS, radians), move speed (MS), deposit amount (dep), decay rate (dec). Agents start in a disc at the centre, heading inward. The agent count is a fraction of the grid area.

### Presets

| Preset | SA | SD | TS | MS | dep | dec | Agents / cell |
|---|---|---|---|---|---|---|---|
| Explorer | 0.40 | 9.0 | 0.30 | 1.0 | 0.5 | 0.020 | 0.15 |
| Dense Web | 0.30 | 5.0 | 0.40 | 1.0 | 0.8 | 0.010 | 0.30 |
| Tendrils | 0.60 | 12.0 | 0.20 | 1.5 | 0.3 | 0.030 | 0.10 |
| Pulsing | 0.35 | 7.0 | 0.50 | 0.8 | 1.0 | 0.040 | 0.20 |
| Maze Solver | 0.25 | 8.0 | 0.60 | 1.0 | 0.6 | 0.015 | 0.25 |
| Galaxy | 0.80 | 10.0 | 0.15 | 1.2 | 0.4 | 0.025 | 0.12 |

The menu descriptions of Pulsing ("rhythmic contraction") and Maze Solver ("finds shortest paths between food") are only labels. The mode has no food sources or walls.

### Controls

`a`/`A` change SA, `s`/`S` change SD, `t`/`T` change TS, and `d`/`D` change the decay rate. `+`/`-` set steps per frame. `r` re-seeds the agents with the preset values.

### What to look for

Chaotic agents self-organize into branching networks. The sensor angle shapes the network: narrow angles (SA < 0.3) give tight strands, and wider angles give broader, more diffuse patterns. Higher decay keeps only the strongest trails and gives sparser networks. Trails attract agents, which deposit more trail; decay counterbalances this feedback.

### References

- Jones, J. "Characteristics of pattern formation and evolution in approximations of Physarum transport networks." *Artificial Life*, 16(2), 127-153, 2010. https://doi.org/10.1162/artl.2010.16.2.16202
- Tero, A., et al. "Rules for biologically inspired adaptive network design." *Science*, 327(5964), 439-442, 2010. https://doi.org/10.1126/science.1187936

---

## Ant Colony Optimization

### Background

Ant Colony Optimization (ACO) was introduced by Marco Dorigo in 1992, inspired by the foraging behavior of real ant colonies. Ants deposit pheromone trails when returning from food sources, and other ants probabilistically follow stronger trails. This positive feedback loop, balanced by pheromone evaporation, allows the colony to collectively discover and reinforce efficient paths. ACO has been applied to combinatorial optimization problems including the traveling salesman problem and network routing.

### Formulation

Ants have position (r, c), heading angle, and a food-carrying flag. A pheromone grid P[r][c] stores concentration values. The nest sits at the grid centre. Food sources have a position and a finite quantity (4 × food_radius²).

```
Ant behavior (per tick):

IF carrying food (returning to nest):
    1. DEPOSIT pheromone: P[r][c] += deposit_strength  (capped at 1.0)
    2. STEER toward nest:
       target_angle = atan2(nest_r - r, nest_c - c)
       heading += (target_angle - heading) * 0.3 + rand(-0.2, 0.2)
    3. If within 2.0 of nest in both r and c: drop food, increment counter, random new heading

ELSE (searching for food):
    1. SENSE pheromone in three directions (dist=3.0, angle=0.5 rad):
       F_left  = P[ahead_left]
       F_center = P[ahead]
       F_right = P[ahead_right]
    2. STEER: if F_center >= both sides, jitter heading by rand(-0.1, 0.1);
       otherwise turn 0.3 rad (+/- 0.1) toward the stronger side
       + random wander: heading += rand(-0.15, 0.15)
    3. If within 2.5 of a food source (in both r and c) with quantity > 0.5:
       pick up food, food.quantity -= 1, head toward nest (+/- 0.3 rad)

MOVE: pos += dir(heading) * 1.0  (toroidal wrap)

Pheromone update:
    blended = P[r][c] * (1 - diffusion) + (3x3 avg) * diffusion
    P_new[r][c] = max(0, blended - evaporation)
```

Parameters: evaporation rate, deposit strength, diffusion rate. Depleted food sources are removed. All ants start at the nest. Food is placed at random at least a quarter of the shorter grid side from the nest.

Returning ants steer straight at the nest rather than following pheromone, so trails form along the lines from food to nest. The mode does not model competition between alternative routes.

### Presets

| Preset | Evaporation | Deposit | Diffusion | Ants / cell | Food sources | Food radius |
|---|---|---|---|---|---|---|
| Forager | 0.02 | 0.3 | 0.01 | 0.08 | 4 | 3 |
| Highway | 0.005 | 0.6 | 0.005 | 0.12 | 3 | 4 |
| Explorer | 0.05 | 0.2 | 0.02 | 0.10 | 6 | 2 |
| Swarm | 0.015 | 0.4 | 0.01 | 0.25 | 5 | 3 |
| Minimal | 0.01 | 0.5 | 0.008 | 0.04 | 2 | 5 |
| Feast | 0.03 | 0.35 | 0.015 | 0.15 | 8 | 4 |

### Controls

`e`/`E` raise and lower the evaporation rate, `d`/`D` the deposit strength, and `s`/`S` the steps per frame. Unlike the other modes, ACO has no `m` key for the menu; use `R`.

### What to look for

The initial random wandering gives way to trails between the nest and the food sources. Once an ant finds food and returns, its pheromone biases nearby searching ants toward the same source, a positive feedback loop. Higher evaporation keeps trails short-lived and the colony more exploratory; lower evaporation makes trails persist, and ants keep following them after a source is depleted. The food-collected counter shows how well the colony forages.

### References

- Dorigo, M. "Optimization, Learning and Natural Algorithms." PhD Thesis, Politecnico di Milano, 1992. https://en.wikipedia.org/wiki/Ant_colony_optimization_algorithms
- Dorigo, M. & Stutzle, T. "Ant Colony Optimization." MIT Press, 2004. https://mitpress.mit.edu/books/ant-colony-optimization

---

## N-Body Gravity

### Background

The N-body gravitational problem — computing the motion of N masses under mutual gravitational attraction — is one of the oldest problems in computational physics, dating to Newton's work on planetary orbits. No general closed-form solution exists for N > 2 (proved by Poincare), making numerical integration essential. This simulation uses the velocity Verlet integrator, a symplectic method that conserves energy better than naive Euler integration, combined with gravitational softening to handle close encounters.

### Formulation

Each body has position (r, c), velocity (vr, vc), and mass m. The simulation uses velocity Verlet (leapfrog) integration:

```
Gravitational acceleration on body i from body j:
    dr = r_j - r_i,  dc = c_j - c_i
    dist^2 = dr^2 + dc^2 + epsilon^2      (softening prevents singularity)
    a_i += G * m_j * (dr, dc) / (dist^2 * sqrt(dist^2))

Velocity Verlet integration (per timestep dt):
    1. Compute accelerations a(t) from current positions
    2. v_half = v(t) + 0.5 * dt * a(t)
    3. r(t+dt) = r(t) + dt * v_half
    4. Compute accelerations a(t+dt) from new positions
    5. v(t+dt) = v_half + 0.5 * dt * a(t+dt)

Collision merging:
    if dist(i,j) < 0.3 + 0.1 * ln(1 + m_i + m_j):
        Merge by conservation of momentum:
        m_new = m_i + m_j
        v_new = (m_i * v_i + m_j * v_j) / m_new
        r_new = (m_i * r_i + m_j * r_j) / m_new

Orbital velocity (circular orbit):
    v = sqrt(G * M_central / r)
```

Parameters: G (gravitational constant), dt (timestep), epsilon (softening). Each preset sets its own values.

### Presets

| Preset | G | dt | epsilon | Setup |
|---|---|---|---|---|
| Solar System | 1.0 | 0.02 | 0.5 | Star of mass 500 and six planets on circular orbits at random angles |
| Binary Star | 1.0 | 0.02 | 0.5 | Two stars of mass 200 in mutual orbit, plus 20 light debris bodies |
| Galaxy Collision | 0.5 | 0.03 | 1.0 | Two disks of 40 light bodies around a mass-100 centre, on a collision course |
| Random Cluster | 0.8 | 0.03 | 0.8 | 60 bodies of random mass in a small cloud |
| Figure-Eight | 1.0 | 0.01 | 0.1 | Three equal masses started from the Chenciner-Montgomery initial conditions |
| Lagrange Points | 1.0 | 0.02 | 0.5 | Central mass 400, one planet, two light trojans at L4/L5, and 15 debris bodies |

### Controls

`g`/`G` change G, `d`/`D` the timestep, and `s`/`S` the softening. `t` toggles trails and `c` toggles centring the view on the centre of mass. `+`/`-` set steps per frame.

### What to look for

The Solar System preset shows Keplerian orbits, with inner planets moving faster than outer ones. Binary Star shows mutual orbital motion. Galaxy Collision produces tidal tails and merging structures. Bodies that come closer than the merge distance combine, so counts fall over time. In Lagrange Points, the trojans start 60 degrees ahead of and behind the planet.

In the current code, the Figure-Eight velocities are scaled differently from its masses and lengths, so the three bodies do not follow the figure-8 and merge into one early in the run.

### References

- Aarseth, S. J. "Gravitational N-Body Simulations." Cambridge University Press, 2003. https://doi.org/10.1017/CBO9780511535246
- Chenciner, A. & Montgomery, R. "A remarkable periodic solution of the three-body problem in the case of equal masses." *Annals of Mathematics*, 152, 881-901, 2000. https://doi.org/10.2307/2661357

---

## Diffusion-Limited Aggregation

### Background

Diffusion-Limited Aggregation (DLA) was introduced by Witten and Sander in 1981 to model growth processes controlled by diffusion. Random walkers undergo Brownian motion until they contact a growing crystal, at which point they stick irreversibly. The resulting structures are branching fractals with a fractal dimension of approximately 1.7 in two dimensions. DLA models phenomena including electrodeposition, mineral dendrites, dielectric breakdown, and bacterial colony growth.

### Formulation

A grid stores crystal cells (positive integer = generation attached) and empty cells (0). Walkers perform random walks until they adhere to the crystal aggregate:

```
Walker step:
    1. Random displacement: dr, dc in {-1, 0, 1} (8-connected)
       Optional bias: if |bias_r| > 0, force dr toward bias with P = |bias_r|
    2. Move: (r, c) += (dr, dc), reject if target is crystal
    3. Adjacency check (8-connected neighborhood):
       if any neighbor is crystal AND rand() < stickiness:
           attach walker to crystal (grid[r][c] = generation)
           update max_radius
    4. Kill walker if dist(walker, center) > spawn_radius + 20

Walker spawning:
    Walkers spawn on a ring at radius = max_crystal_radius + 10
    Maintained at constant population (default 300-500)

Symmetry (snowflake mode, k-fold):
    On attachment at offset (dr, dc) from center:
    for angle = 0, 2*pi/k, ..., 2*pi*(k-1)/k:
        (rr, rc) = center + rotate(dr, dc, angle)
        attach crystal at (rr, rc)
    For k=6: additional mirror reflections for full hexagonal symmetry

Stickiness: P(attach | adjacent) = stickiness parameter (default 1.0)
    Lower stickiness (e.g., 0.7) allows walkers to penetrate deeper,
    producing more branching.
```

Presets: Crystal Growth (single seed), Multi-Seed (5 seeds), Snowflake (6-fold symmetry, stickiness 0.7), Electrodeposition (bottom-edge cathode with upward bias -0.15), Line Seed, Ring Seed.

### What to look for

The fundamental DLA branching pattern arises because outer tips of the crystal are more accessible to random walkers than inner fjords, creating a screening effect that produces fractal branching. Reducing stickiness below 1.0 allows walkers to diffuse past tips into concavities, producing denser, more compact structures. The electrodeposition preset adds a downward drift, creating vertically aligned dendritic structures reminiscent of metal deposition on electrodes. The snowflake preset applies 6-fold rotational symmetry with mirror reflections, generating structures remarkably similar to real ice crystals.

### References

- Witten, T. A. & Sander, L. M. "Diffusion-limited aggregation, a kinetic critical phenomenon." *Physical Review Letters*, 47(19), 1400-1403, 1981. https://doi.org/10.1103/PhysRevLett.47.1400
- Meakin, P. "Fractals, Scaling and Growth Far from Equilibrium." Cambridge University Press, 1998. https://doi.org/10.1017/CBO9780511806179

---

## Bee Colony & Waggle Dance Communication

### Background

Honeybee colonies are among the most studied examples of swarm intelligence, combining individual simplicity with remarkable collective problem-solving. Karl von Frisch's Nobel Prize–winning work (1967) decoded the waggle dance — a figure-eight movement performed by returning foragers on the vertical comb face, encoding the distance and direction to a food source relative to the sun's azimuth. Recruits observing the dance extract this vector information and navigate to the advertised patch, creating a positive feedback loop where richer sources attract more foragers. Thomas Seeley's later work showed that this dance-based recruitment system implements a decentralized "house-hunting" algorithm with near-optimal collective decision-making.

Beyond communication, honeybee colonies exhibit age-based division of labor (temporal polyethism): young bees nurse brood, middle-aged bees build comb and process nectar, and older bees forage and guard. This role allocation is not genetically fixed but emerges from hormonal thresholds modulated by colony needs — a workforce that dynamically reallocates itself. The colony also collectively thermoregulates the brood nest to 35°C ± 1°C through endothermic muscle shivering (heating) and wing-fanning evaporative cooling, maintaining homeostasis across ambient temperatures from −20°C to +45°C.

This mode simulates foraging economics, waggle dance recruitment, hexagonal comb construction, thermoregulation, and age-based polyethism as an integrated colony-level system.

### Formulation

Each bee agent has position (x, y), heading, speed, energy, age, role, and behavioral state. Seven roles exist: Queen, Nurse, Builder, Forager, Guard, Fanner, and Scout. Flower patches have position, nectar/pollen reserves with regeneration, bloom windows, and species identity.

```
Age-based polyethism (every 100 ticks):
    age > 12, Nurse → Builder   (P = 0.10)
    age > 20, Nurse → Forager   (P = 0.15)
    age > 40, any   → Guard     (P = 0.10)

Emergency role switching:
    alert_level > 0.5: Forager → Guard  (P = 0.05 per tick, if in hive)
    hive_temp > 38°C:  any → Fanner     (P = 0.03 per tick, if in hive)

Forager behavior (state machine):
    IDLE     → pick known patch or random direction → FORAGING
    FORAGING → move toward target patch at speed 0.4–0.7
               on arrival: harvest nectar/pollen (deplete patch proportionally)
               → RETURNING
    RETURNING → steer toward hive center
               on arrival: deposit nectar → honey_store, pollen → pollen_store
               → DANCING
    DANCING  → perform waggle dance for 15–25 ticks
               dance encodes: angle = atan2(patch.y − hive.y, patch.x − hive.x)
                              distance = euclidean(patch, hive)
               quality ∝ nectar collected
               → IDLE (cycle repeats)

    FOLLOWING → recruit observes dance, extracts (angle, distance)
               navigates to encoded location with angular noise ±0.2 rad
               → FORAGING on arrival near target

Scout behavior:
    Random exploration at wider radius than foragers
    On discovering a rich patch (nectar > 30): return and dance

Waggle dance encoding:
    angle:    direction from hive to food source (radians)
    distance: euclidean distance / field_diagonal (normalized)
    quality:  proportional to nectar harvested (affects recruit probability)
    type:     ROUND (close source, dist < 5) or WAGGLE (far source)

Temperature regulation:
    heat_gain = n_bees × 0.015 × 0.01
    cooling   = n_fanners × 0.4 × 0.1
    drift     = (ambient − hive_temp) × 0.01
    hive_temp += drift + heat_gain − cooling
    hive_temp ∈ [ambient, 45°C]

Comb construction (Builder role):
    If wax_store > 2: place WAX cell adjacent to existing comb (P = 0.15)
    wax_store += honey_store × 0.01  (bees convert honey to wax)

Queen egg-laying (every 50 ticks):
    If honey_store > 5: place BROOD in empty comb cell, honey_store −= 0.5

Nurse behavior:
    Tend BROOD cells: pollen_store −= 0.05 per nursing action
    Wander within hive radius

Patch regeneration:
    In bloom:  nectar += regen_rate × max_nectar per tick
    Out of bloom: nectar decays slowly (−0.01/tick)
    Bloom cycling: every 500 ticks, 30% of patches shift bloom windows
```

### Presets

- **Spring Bloom**: Abundant wildflower meadow with 12 diverse patches and a large forager workforce. The colony operates at peak efficiency — watch waggle dance trails converge on the richest patches as scouts discover them.
- **Overwintering Cluster**: Ambient temperature −5°C with minimal forage. Bees cluster tightly for warmth, fanners work overtime, and the colony slowly depletes honey reserves. A survival scenario where thermoregulation dominates behavior.
- **Swarm Departure**: Colony in reproductive mode — scouts search for new nest sites while foragers maintain existing operations. Demonstrates the exploration-exploitation trade-off at colony scale.
- **Bear Attack Defense**: A bear agent advances toward the hive, triggering high alert. Foragers abandon patches and switch to guard duty; guards converge to sting the intruder. If enough guards mobilize (>10 near bear), they push it back. Honey stores drain if the bear breaches the hive perimeter.
- **Robber Bee Invasion**: Foreign bees (20 robbers) approach the hive to steal honey. Guards intercept and drain robber energy; depleted robbers respawn at distance. A resource-defense scenario with attacker-defender dynamics.
- **Pollination Network**: Six flower species arranged in clusters, with 18 patches total. Foragers develop patch fidelity — watch specialization emerge as bees repeatedly visit the same species clusters, mimicking real-world floral constancy.

### What to look for

In **Spring Bloom**, watch the initial exploration phase where scouts fan out randomly, then observe how the first successful forager's waggle dance triggers a cascade of recruitment to her patch — the colony rapidly focuses its workforce on the best sources. As patches deplete, dancers switch to advertising new locations, demonstrating the exploration-exploitation balance. In **Overwintering Cluster**, the hive temperature gauge is the key metric: watch fanners activate when temperature rises above 38°C from bee body heat, then deactivate as it drops, creating an oscillating thermostat. The **Bear Attack** preset shows emergency role switching in action — the forager-to-guard transition happens within ticks of the bear entering alert range, and the collective defense pushes the bear away if guard mobilization is fast enough. In the **Comb view** (press v), observe hexagonal cells filling with honey (gold), pollen (orange), and brood (pink) as builders expand the comb structure outward from the center. The **Dance view** zooms into the dance floor, rendering the figure-eight waggle dance trajectories — each dance's orientation encodes direction and its duration encodes distance, exactly as von Frisch described.

### References

- von Frisch, K. "The Dance Language and Orientation of Bees." Harvard University Press, 1967. https://doi.org/10.4159/harvard.9780674418776
- Seeley, T. D. "Honeybee Democracy." Princeton University Press, 2010. https://press.princeton.edu/books/paperback/9780691147215/honeybee-democracy
- Seeley, T. D. "The Wisdom of the Hive." Harvard University Press, 1995. https://doi.org/10.4159/9780674043404
- Camazine, S., Deneubourg, J.-L., Franks, N. R., Sneyd, J., Theraulaz, G. & Bonabeau, E. "Self-Organization in Biological Systems." Princeton University Press, 2001. https://press.princeton.edu/books/paperback/9780691116242/self-organization-in-biological-systems
