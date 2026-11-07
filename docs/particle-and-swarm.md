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

8. CROWD SLOWDOWN (when τ > 0 and at least one neighbor lies within quorum_r):
   quorum_r = align_r, or repel_r when align_r = 0
   local_density = n_quorum / (π * quorum_r²)    (denominator at least 1)
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

The crowd slowdown counts neighbors inside `align_r`, or inside `repel_r` when `align_r` is 0. It applies to every preset once the tumble rate is above 0, including **Motility-Induced Clustering** (tumble rate 0.05). In the other presets the tumble rate starts at 0, so raising it with `t` enables the slowdown.

### Presets

- **Bacterial Turbulence**: Dense pushers (extensile dipoles, contract = −0.3) with nematic alignment. Produces chaotic vortex streets and jet-like flows characteristic of dense bacterial suspensions like *B. subtilis*.
- **Active Nematics**: Rod-like extensile particles (contract = −0.5) with strong nematic alignment. Nucleates ±½ topological defect pairs that unbind and annihilate — the hallmark of active nematic turbulence observed in microtubule-kinesin mixtures.
- **Motility-Induced Clustering**: Run-and-tumble particles (τ = 0.05, v₀ = 1.0) with no alignment and strong repulsion. Particles tumble at random, push each other apart and slow down in crowds.
- **Vicsek Flocking**: Polar aligning particles with moderate noise (η = 0.3). Demonstrates the Vicsek transition: below a critical noise the system orders into a coherent flock.
- **Active Spinner Gas**: Self-rotating particles (spin_w = 0.3) that turn by a fixed angle each step, so they travel in circles. Collisions are plain repulsion; there is no odd-elastic force.
- **Contractile Gel**: Puller particles (contract = +0.5) that tend to form asters and contractile networks, as in actomyosin gels where motors pull filaments inward.

### Controls

`v` cycles the view (Arrows, Density, Vorticity). `s`/`S` change v₀, `e`/`E` the noise η, `a`/`A` the alignment weight, `p`/`P` the repulsion weight, and `t`/`T` the tumble rate. `+`/`-` set steps per frame (1 to 10). A mouse click adds 15 particles, up to 3000 in total.

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

`v` cycles the view (Grains, Force Chains, Density). `g`/`G` change gravity strength, `t`/`T` tilt gravity sideways, `f`/`F` friction, `e`/`E` restitution, `s`/`S` shake amplitude, and `k`/`K` contact stiffness. `+`/`-` set steps per frame. A mouse click drops 12 grains, up to 1000 grains in total.

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

The menu description of Pulsing ("Rhythmic contraction patterns") is only a label. Maze Solver is the preset with the highest turn speed; the mode has no food sources or walls.

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

`e`/`E` raise and lower the evaporation rate, `d`/`D` the deposit strength, and `s`/`S` the steps per frame (1 to 10). Unlike the other modes, ACO has no `m` key for the menu; use `R`.

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
| Binary Star | 1.0 | 0.02 | 0.5 | Two stars of mass 200, 12 apart, on a circular mutual orbit, plus 20 light debris bodies |
| Galaxy Collision | 0.5 | 0.03 | 1.0 | Two disks of 40 light bodies around a mass-100 centre, on a collision course |
| Random Cluster | 0.8 | 0.03 | 0.8 | 60 bodies of random mass in a small cloud |
| Figure-Eight | 1.0 | 0.01 | 0.1 | Three masses of 10 started from the Chenciner-Montgomery initial conditions, with velocities scaled for G, mass and size |
| Lagrange Points | 1.0 | 0.02 | 0.5 | Central mass 400, one planet, two light trojans at L4/L5, and 15 debris bodies |

### Controls

`g`/`G` change G, `d`/`D` the timestep, and `s`/`S` the softening. `t` toggles trails and `c` toggles centring the view on the centre of mass. `+`/`-` set steps per frame.

### What to look for

The Solar System preset shows Keplerian orbits, with inner planets moving faster than outer ones. Binary Star starts the two stars on a circular mutual orbit. Figure-Eight starts the three bodies on the figure-8 solution. Galaxy Collision produces tidal tails and merging structures. Bodies that come closer than the merge distance combine, so counts fall over time. In Lagrange Points, the trojans start 60 degrees ahead of and behind the planet.

### References

- Aarseth, S. J. "Gravitational N-Body Simulations." Cambridge University Press, 2003. https://doi.org/10.1017/CBO9780511535246
- Chenciner, A. & Montgomery, R. "A remarkable periodic solution of the three-body problem in the case of equal masses." *Annals of Mathematics*, 152, 881-901, 2000. https://doi.org/10.2307/2661357

---

## Diffusion-Limited Aggregation

### Background

Diffusion-Limited Aggregation (DLA) was introduced by Witten and Sander in 1981 to model growth processes controlled by diffusion. Random walkers undergo Brownian motion until they contact a growing crystal, at which point they stick irreversibly. The resulting structures are branching fractals with a fractal dimension of approximately 1.7 in two dimensions. DLA models phenomena including electrodeposition, mineral dendrites, dielectric breakdown, and bacterial colony growth.

### Formulation

A grid stores crystal cells (positive integer = the step at which the cell attached) and empty cells (0). Walkers perform random walks until they stick to the crystal:

```
Walker step:
    1. Random displacement: dr, dc each in {-1, 0, 1} (8-connected, may stay put).
       Six-fold preset: one of the 6 neighbors of a hexagonal lattice instead.
       Optional bias: with P = |bias_r| (or |bias_c|), force dr (dc) to the sign of the bias.
    2. Move: (r, c) += (dr, dc). If the target is off the grid or crystal, stay put.
    3. Adjacency check (8-neighbors, or 6 on the hex lattice):
       if any neighbor is crystal AND rand() < stickiness:
           attach walker to crystal (grid[r][c] = step)
           update max_radius
    4. Otherwise kill the walker if dist(walker, center) > spawn_radius + 20.

Walker spawning (replenished after any attachment or when below the target count):
    Walkers spawn on a ring (an ellipse on a non-square grid) around the grid centre,
    at radius about max_crystal_radius + 10, scaled by a random 0.8-1.2 and capped to the grid.
    A walker never spawns within 2 cells of the crystal.
    If the ring is nearly full, walkers spawn at random free cells instead.
    Electrodeposition spawns walkers in the top third of the grid.
    Target population by preset: 300 (Crystal Growth), 400 (Multi-Seed, Line Seed,
    Ring Seed), 30 (Snowflake), 500 (Electrodeposition); adjustable with w/W.

Cleanup:
    Every 20 steps, walkers sealed inside crystal pockets are removed (flood fill from the edge).
    A walker that has not attached after max(1000, 2 * rows * cols) moves is respawned.
    After 400 steps with no attachment the crystal counts as complete and the run stops.

Symmetry (Snowflake preset, 6-fold):
    On attachment, the cell is also copied to its 11 other images on the hexagonal
    lattice (6 rotations and their mirrors). An image is placed only if it touches
    the existing crystal.

Stickiness: P(attach | adjacent) = stickiness parameter (default 1.0)
    Lower stickiness (e.g., 0.7) lets walkers penetrate deeper,
    producing more branching.
```

### Presets

- **Crystal Growth**: Single centre seed. Stickiness 1.0.
- **Multi-Seed**: Five seeds (four quarter points and the centre) that grow and merge.
- **Snowflake**: Centre seed, 6-fold symmetry, stickiness 0.7, only 30 walkers.
- **Electrodeposition**: The whole bottom row is the cathode. A downward bias of 0.15 (toward increasing row) pulls walkers to it.
- **Line Seed**: Horizontal line seed across the middle half of the grid.
- **Ring Seed**: Circular ring seed of radius min(rows, cols) / 5. Walkers attach on both sides.

### Controls

`s`/`S` change stickiness (0.1 to 1.0) and `w`/`W` change the target walker count. `+`/`-` change steps per frame. Crystal colors show age.

### What to look for

The branching arises because the outer tips of the crystal are more accessible to random walkers than the inner fjords, a screening effect that gives fractal structure. Lowering stickiness below 1.0 lets walkers diffuse past tips into concavities, giving denser, more compact structures. Electrodeposition adds a downward drift and grows vertical dendrites from the cathode. The Snowflake preset repeats each attachment on the hexagonal lattice, so the crystal keeps six-fold and mirror symmetry as it grows.

### References

- Witten, T. A. & Sander, L. M. "Diffusion-limited aggregation, a kinetic critical phenomenon." *Physical Review Letters*, 47(19), 1400-1403, 1981. https://doi.org/10.1103/PhysRevLett.47.1400
- Meakin, P. "Fractals, Scaling and Growth Far from Equilibrium." Cambridge University Press, 1998. https://doi.org/10.1017/CBO9780511806179

---

## Bee Colony & Waggle Dance Communication

### Background

Honeybee colonies are among the most studied examples of swarm intelligence, combining individual simplicity with remarkable collective problem-solving. Karl von Frisch's work (Nobel Prize 1973) decoded the waggle dance — a figure-eight movement performed by returning foragers on the vertical comb face, encoding the distance and direction to a food source relative to the sun's azimuth. Recruits observing the dance extract this vector information and navigate to the advertised patch, creating a positive feedback loop where richer sources attract more foragers. Thomas Seeley's later work showed that this dance-based recruitment system implements a decentralized "house-hunting" algorithm with near-optimal collective decision-making.

Beyond communication, honeybee colonies exhibit age-based division of labor (temporal polyethism): young bees nurse brood, middle-aged bees build comb and process nectar, and older bees forage and guard. This role allocation is not genetically fixed but emerges from hormonal thresholds modulated by colony needs — a workforce that dynamically reallocates itself. The colony also collectively thermoregulates the brood nest to 35°C ± 1°C through endothermic muscle shivering (heating) and wing-fanning evaporative cooling, maintaining homeostasis across ambient temperatures from −20°C to +45°C.

This mode simulates foraging economics, waggle dance recruitment, hexagonal comb construction, thermoregulation, and age-based polyethism as an integrated colony-level system.

### Formulation

Each bee agent has position (x, y), heading, speed, energy, age, role, and behavioral state. Seven roles exist: Queen, Nurse, Builder, Forager, Guard, Fanner, and Scout. Flower patches have position, radius, nectar/pollen reserves with regeneration, bloom windows, and a species. A patch's species sets its color in the Colony view. The hive sits at the field centre with radius min(rows, cols) / 8; "in the hive" means within 1.5 hive radii of the centre.

```
Age-based polyethism (every 100 ticks each bee ages by 1; rules tried in this order):
    age > 40, any non-Guard   → Guard     (P = 0.10)
    age > 20, Nurse           → Forager   (P = 0.15)
    age > 12, Nurse           → Builder   (P = 0.10)

Emergency role switching (bees in the hive):
    alert_level > 0.5: Forager → Guard  (P = 0.05 per tick)
    hive_temp > 38°C:  any (not Queen or Fanner) → Fanner  (P = 0.03 per tick)
    A Fanner becomes a Forager again when hive_temp < 35.5°C (P = 0.05 per tick)

Forager behavior (state machine):
    IDLE      → in the hive: follow an active dance (P = 0.04 × quality per tick) → FOLLOWING
                else go to the last known patch if its nectar > 1 → FORAGING
                else (P = 0.02 per tick) pick a random target → FORAGING
    FORAGING  → move toward target at speed 0.4–0.7
                on arrival inside a patch with nectar: take up to 2 nectar and 1 pollen
                → RETURNING; else wander to a new nearby target, giving up with
                P = 0.05 per tick → RETURNING
    RETURNING → steer toward hive center at 1.2 × speed
                on arrival: honey_store += 0.8 × nectar, pollen_store += 0.9 × pollen
                if nectar > 0.5 → DANCING, else → IDLE
    DANCING   → stay near the hive for max(10, int(40 × quality)) ticks
                quality = min(1, nectar / 3)
                → IDLE
    FOLLOWING → head for hive + dist × (cos angle, sin angle), the exact patch
                location encoded in the dance (no noise)
                on arrival: same as FORAGING (stays FOLLOWING while it wanders)

Scout behavior:
    Random exploration at 1.3 × speed, returning home with P = 0.005 per tick
    On entering a patch with nectar > 10: take up to 1 nectar, return, and dance
    for max(15, int(50 × quality)) ticks, quality = patch nectar / max nectar

Waggle dance encoding:
    angle:    direction from hive to patch (radians)
    distance: euclidean distance from hive to patch (grid cells)
    quality:  sets dance length and the chance that idle foragers follow it

Temperature regulation (per tick):
    heat_gain = n_bees × 0.015 × 0.01
    cooling   = n_fanning_fanners × 0.4 × 0.1
    drift     = (ambient − hive_temp) × 0.01
    hive_temp += drift + heat_gain − cooling
    hive_temp ∈ [ambient, 45°C]

Comb construction (Builder role, inside the hive radius):
    P = 0.03 per tick, if honey_store > 1: pick a random comb cell; if it is empty
    and touches a non-empty cell, make it WAX
    honey_store −= 0.5, wax_store += 0.1
    Deposited nectar and pollen fill the empty or wax cell nearest the comb centre,
    searching out to 6 cells; if none is free, no comb cell changes (the stores
    still grow).

Queen egg-laying (every 50 ticks):
    If honey_store > 5: pick a random cell within ±2 of the comb centre;
    if empty, make it BROOD and honey_store −= 0.5

Nurse behavior:
    Wander within hive radius
    With P = 0.02 per tick, if pollen_store > 0.1, check a random comb cell;
    on BROOD, pollen_store −= 0.1

Patch regeneration:
    In bloom:  nectar += 0.02 × max_nectar per tick (pollen at half that rate)
    Out of bloom: nectar decays slowly (−0.01/tick)
    Bloom cycling: every 500 ticks, 30% of patches get a new bloom window
    (starts within 200 ticks, lasts 200–600) and their nectar is set to half the maximum
```

Every bee except the queen loses 0.001 energy per tick. A bee in the hive below 0.3 energy eats 0.1 honey for +0.2 energy.

Unlike the real colony described above, the hive here starts at 35°C and cools toward ambient (20°C by default); without fanners it settles at ambient + 0.015 × n_bees. Fanners go back to foraging once the hive is below 35.5°C. Brood cells never hatch; they only record egg-laying.

### Presets

Every preset also has a queen and max(3, foragers / 10) scouts.

- **Spring Bloom**: Up to 12 random patches; 60 foragers, 20 nurses, 10 builders, 5 guards, 5 fanners.
- **Overwintering Cluster**: Ambient −5°C, hive starts at 20°C, honey store 200. Only 3 small patches (nectar 20), far from the hive; 15 foragers, 30 nurses, 5 builders, 5 guards, 25 fanners.
- **Swarm Departure**: 8 random patches; 50 foragers, 15 nurses, 15 builders, 10 guards, 5 fanners. Only the population and patches differ from other presets; no nest-site search is modelled.
- **Bear Attack Defense**: Up to 10 patches; 40 foragers, 15 nurses, 5 builders, 30 guards, 5 fanners; alert level starts at 0.8. A bear starts 5 hive radii away and walks toward the hive at 0.15 per tick. Inside 2 hive radii it raises the alert by 0.02 per tick (alert decays 0.002 per tick), and inside 1.2 hive radii it drains 0.5 honey per tick. Guards within 3 hive radii move toward the bear. If more than 10 guards are within 3 cells of it, the bear is pushed back by 0.3 per tick; it leaves once it is more than 6 hive radii away.
- **Robber Bee Invasion**: 5 patches; 35 foragers, 15 nurses, 5 builders, 25 guards, 5 fanners; alert level starts at 0.5. 20 robbers start 2 to 4 hive radii away and move toward the hive at 0.3 per tick. Within 1.5 hive radii each steals 0.3 honey with P = 0.1 per tick, and the first guard within 2 cells drains 0.05 of its energy per tick. At zero energy a robber respawns at a random spot within ±5 hive radii of the hive centre (each axis) with energy 0.8.
- **Pollination Network**: 18 patches in 6 clusters of 3, one species per cluster; 70 foragers, 20 nurses, 10 builders, 5 guards, 5 fanners. Foragers return to their last known patch while it has nectar, so each forager tends to keep visiting the same patch.

### Controls

`Space` starts and pauses. `n` advances one tick. `v` cycles the view (colony, dance, comb). `+`/`-` set steps per frame (1 to 20). `r` resets the preset and `R` (or `m`) returns to the menu.

### What to look for

In **Spring Bloom**, scouts and foragers search at random, then dances recruit idle foragers to the patches that returned nectar. As patches deplete, new dances advertise other locations. In **Overwintering Cluster**, watch the temperature in the info bar and the honey store. In **Bear Attack Defense**, foragers in the hive turn into guards soon after the start, and the guards can push the bear back if enough of them gather near it. In the **Comb** view (`v`), cells show `H` (honey), `P` (pollen), `B` (brood) and a bare hexagon for wax; builders extend the comb outward from the centre. The **Dance** view zooms into the hive. Each dance is drawn as a waggle run along the direction to the patch. The run is longer for farther patches, and bold for quality above 0.6.

### References

- von Frisch, K. "The Dance Language and Orientation of Bees." Harvard University Press, 1967. https://doi.org/10.4159/harvard.9780674418776
- Seeley, T. D. "Honeybee Democracy." Princeton University Press, 2010. https://press.princeton.edu/books/paperback/9780691147215/honeybee-democracy
- Seeley, T. D. "The Wisdom of the Hive." Harvard University Press, 1995. https://doi.org/10.4159/9780674043404
- Camazine, S., Deneubourg, J.-L., Franks, N. R., Sneyd, J., Theraulaz, G. & Bonabeau, E. "Self-Organization in Biological Systems." Princeton University Press, 2001. https://press.princeton.edu/books/paperback/9780691116242/self-organization-in-biological-systems
