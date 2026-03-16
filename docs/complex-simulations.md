# Complex Simulations & Audio-Visual

Multi-physics systems and aesthetic visualizations — where science meets art in the terminal.

---


## Traffic Flow (Nagel-Schreckenberg Model)

**Background.** The Nagel-Schreckenberg (NaSch) model, introduced in 1992, is a foundational cellular automaton for traffic simulation. It reproduces the spontaneous formation of phantom traffic jams -- stop-and-go waves that appear with no external cause. Each lane is a one-dimensional lattice with periodic boundaries, and each cell is either empty or occupied by a car carrying an integer velocity.

**Formulation.** Four rules are applied simultaneously to all cars each timestep:

```
1. Acceleration:   v(t+1) = min(v(t) + 1, vmax)
2. Braking:        v(t+1) = min(v(t+1), gap)
                   where gap = (distance to next car ahead) - 1
3. Randomization:  with probability p_slow:
                       v(t+1) = max(v(t+1) - 1, 0)
4. Movement:       position(t+1) = (position(t) + v(t+1)) mod L

Parameters:
  vmax    — maximum speed (cells/step), typically 5
  p_slow  — stochastic braking probability, range [0, 1]
  density — fraction of cells initially occupied (rho)
  L       — lane length (adapts to terminal width)

Diagnostics:
  avg_speed = sum(v_i) / N_cars
  flow      = sum(v_i) / (lanes * L)
```

**What to look for.** At low density (rho < 0.15), all cars cruise at vmax and flow increases linearly with density. Near a critical density (rho ~ 0.35-0.45), phantom jams nucleate from the randomization step and propagate backward as kinematic waves. At high density, persistent stop-and-go waves dominate. Raising p_slow increases jam frequency; lowering it creates smoother flow that collapses more catastrophically. The simulation includes 8 presets spanning light traffic through 8-lane highways.

**References.**
- Nagel, K. & Schreckenberg, M. "A cellular automaton model for freeway traffic." *Journal de Physique I*, 2(12), 2221-2229, 1992. https://doi.org/10.1051/jp1:1992277
- Chowdhury, D., Santen, L. & Schadschneider, A. "Statistical physics of vehicular traffic and some related systems." *Physics Reports*, 329(4-6), 199-329, 2000. https://doi.org/10.1016/S0370-1573(99)00117-9

---

## Galaxy Formation

**Background.** This N-body simulation models the gravitational dynamics of spiral galaxies. Particles representing stars and gas orbit within an analytic dark matter halo whose gravitational potential follows an NFW (Navarro-Frenk-White) profile. The simulation demonstrates how logarithmic spiral arms, velocity dispersion, tidal interactions, and gas pressure give rise to the rich morphological diversity observed in galaxies -- from grand-design spirals to ellipticals and mergers.

**Formulation.** Each particle i carries state [x, y, vx, vy, mass, type] and evolves via leapfrog integration:

```
Halo force (NFW-like profile):
  r     = sqrt((x - cx)^2 + (y - cy)^2)
  F_halo = -G * M_halo * r / (r + r_s)^2

Grid-based particle-particle gravity (binned to 4-cell resolution):
  F_pp  = G * m_bin / (d^2 + epsilon^2)
  where d = distance to bin center-of-mass, epsilon = softening

Gas pressure (for gas particles, type > 0.5):
  If local_density > 3.0:
    F_pressure = 0.5 * (density - 3.0) * (outward direction)
  Gas cooling: v *= 0.998 per step

Circular orbital velocity (initialization):
  v_circ = sqrt(G * M_halo * r / (r + r_s)^2 + 0.1)

Spiral arm placement (logarithmic spiral perturbation):
  angle = base_angle + arm_index * (2*pi / N_arms) + 0.3 * ln(1 + r) * N_arms

Leapfrog integration:
  v(t + dt/2) = v(t) + a(t) * dt
  x(t + dt)   = x(t) + v(t + dt/2) * dt

Parameters:
  G           — gravitational constant (default 1.0, range 0.1-5.0)
  M_halo      — dark matter halo mass (300-1000)
  r_s         — halo scale radius (15-30)
  dt          — timestep (default 0.03)
  epsilon     — softening length (1.0)
```

**What to look for.** In the Milky Way and Grand Design presets, watch spiral arms wind up over time. The Whirlpool preset features a companion galaxy on an infall trajectory producing tidal tails. The Merger preset shows two disk galaxies colliding, producing a burst of tidal debris. Elliptical galaxies maintain a pressure-supported spheroid with no net rotation. Toggling the dark matter halo overlay (h key) reveals the NFW density profile underlying all dynamics. Gas particles experience drag and pressure, collecting in spiral arm density peaks.

**References.**
- Navarro, J.F., Frenk, C.S. & White, S.D.M. "The Structure of Cold Dark Matter Halos." *The Astrophysical Journal*, 462, 563, 1996. https://doi.org/10.1086/177173
- Toomre, A. & Toomre, J. "Galactic Bridges and Tails." *The Astrophysical Journal*, 178, 623-666, 1972. https://doi.org/10.1086/151823

---

## Smoke & Fire

**Background.** This mode simulates combustion and buoyant fluid dynamics on an Eulerian grid. Temperature, smoke density, fuel, and velocity fields interact through simplified Navier-Stokes-like advection, diffusion, and buoyancy. The approach follows the seminal work of Stam (1999) on stable fluids, adapted for real-time ASCII rendering. Fire sources inject heat, which rises through buoyancy, consumes fuel through combustion, and generates smoke that dissipates over time.

**Formulation.** Five scalar fields are evolved each timestep: temperature T, smoke S, fuel F, and velocity (vx, vy).

```
Buoyancy (heat rises):
  vy -= buoyancy * T

Wind and turbulence:
  vx += wind
  vx += random(-0.5, 0.5) * turbulence * (1 + T * 2)
  vy += random(-0.5, 0.5) * turbulence * 0.5

Velocity damping:
  vx *= 0.85,  vy *= 0.85

Combustion (fuel burns when T > 0.2 and F > 0.01):
  burn = min(F, 0.05 * T)
  F   -= burn
  T   += burn * 3.0     (heat release)

Fire spread (when T > 0.4, to 4-connected neighbors):
  If neighbor has fuel > 0.1 and T < 0.3:
    neighbor.F -= 0.002
    neighbor.T += 0.05 * T

Smoke production:  S += T * smoke_rate * 0.3
Cooling:           T -= cooling * (1 + height_fraction * 0.5)
Smoke dissipation: S *= 0.985;  S -= 0.003

Semi-Lagrangian advection (bilinear interpolation):
  source = (r - vy, c - vx)
  T_new = 0.4 * T_local + 0.6 * T_sampled
  S_new = 0.4 * S_local + 0.6 * S_sampled

Diffusion (4-neighbor averaging):
  T = 0.8 * T + 0.2 * mean(T_neighbors)
  S = 0.85 * S + 0.15 * mean(S_neighbors)

Presets:           buoyancy  turbulence  cooling  smoke_rate  wind
  Campfire         0.15      0.04        0.012    0.3         0.0
  Wildfire         0.12      0.06        0.008    0.4         0.02
  Explosion        0.25      0.12        0.02     0.6         0.0
  Candles          0.10      0.02        0.018    0.15        0.0
  Inferno          0.20      0.08        0.006    0.5         0.01
  Smokestack       0.18      0.05        0.01     0.5         0.03
```

**What to look for.** The Campfire preset shows a steady flickering flame with a rising smoke plume. Wildfire demonstrates fire spread across a fuel-laden landscape with wind-driven propagation. The Explosion preset creates a radial blast wave with outward velocity. Increasing turbulence produces chaotic, billowing flames; increasing buoyancy makes flames taller and thinner. Fire sources flicker stochastically with intensity modulated by 0.7 + random * 0.3. Users can interactively place fire sources and fuel patches.

**References.**
- Stam, J. "Stable Fluids." *Proceedings of SIGGRAPH '99*, ACM, 121-128, 1999. https://doi.org/10.1145/311535.311548
- Nguyen, D.Q., Fedkiw, R. & Jensen, H.W. "Physically Based Modeling and Animation of Fire." *ACM Transactions on Graphics*, 21(3), 721-728, 2002. https://doi.org/10.1145/566654.566643

---

## Fireworks

**Background.** This particle system simulates pyrotechnic displays using Newtonian projectile dynamics. Rockets launch upward against gravity, explode at apogee into bursts of sparks following various geometric patterns, and fade with trailing afterimages. The simulation captures the physics of ballistic trajectories, air drag, and gravitational settling that give real fireworks their characteristic arc and droop.

**Formulation.** Two entity types are simulated: rockets and spark particles.

```
Rocket dynamics:
  vr += gravity           (deceleration during ascent)
  vc += wind
  r  += vr,  c += vc
  Explode when: fuse <= 0 OR vr >= 0 (apex reached)

Spark dynamics after burst:
  vr += gravity * k       (k = 1.5 for willow, 0.8 for others)
  vc += wind
  vr += random(-0.02, 0.02)   (jitter)
  vc += random(-0.02, 0.02)
  vr *= drag              (drag = 0.97 for willow, 0.985 for others)
  vc *= drag
  r  += vr,  c += vc

Burst patterns:
  Spherical:  N=30-60 sparks, angle ~ U(0, 2*pi), speed ~ U(0.3, 1.2)
  Ring:       N=24-40 sparks, angle = 2*pi*i/N, uniform speed
              Optional inner ring at 50% radius
  Willow:     N=40-70 sparks, long life (30-55 ticks), high gravity
  Crossette:  4-6 sub-rockets that each re-explode as spherical bursts

Parameters:
  gravity     — downward acceleration (default 0.05)
  launch_rate — probability of auto-launch per tick (0.04-0.18)
  wind        — horizontal drift per tick
  fuse        — random height in [rows/4, rows*2/3]

Trail rendering: 6-element position history, oldest entries dimmer
Life fraction:   life / max_life determines spark brightness
```

**What to look for.** The Finale preset uses a high launch rate with all burst patterns randomized, creating dense overlapping displays. Willow shells produce long, drooping trails that trace parabolic arcs under high gravity multiplier. Crossette shells create a cascade effect: each sub-rocket travels outward before detonating into its own secondary burst. Increasing gravity shortens burst radius and makes sparks fall faster; wind causes coherent lateral drift across all active particles. Trail rendering creates persistence-of-vision streaks.

**References.**
- Reeves, W.T. "Particle Systems -- A Technique for Modeling a Class of Fuzzy Objects." *ACM Transactions on Graphics*, 2(2), 91-108, 1983. https://doi.org/10.1145/357318.357320
- Sims, K. "Particle Animation and Rendering Using Data Parallel Computation." *Computer Graphics (SIGGRAPH '90 Proceedings)*, 24(4), 405-413, 1990. https://doi.org/10.1145/97880.97923

---


## Sonification Engine (Generative Soundscape)

**Source:** `life/modes/sonification.py`

**Background.** The sonification engine is a cross-cutting audio layer that attaches to any running simulation mode and maps its spatial dynamics to a real-time generative music composition. Rather than a standalone mode, it operates as a toggleable overlay (Ctrl+A) that transforms the simulator from a purely visual experience into a synesthetic one — Conway's Game of Life sounds fundamentally different from a fluid simulation or a strange attractor. The engine synthesizes four simultaneous voices (bass, melody, harmony, rhythm) using additive waveform synthesis, with musical parameters driven by frame-by-frame analysis of the simulation's spatial state.

**Formulation.** Five core mappings translate simulation metrics to musical parameters:

```
1. Population density → Pitch register:
   density_shift = (density - 0.3) * 18 semitones
   pitch_mult = 2^(density_shift / 12)
   Applied to bass, melody, and harmony root frequencies.
   Bass clamped to [30, 500] Hz.
   Effect: sparse simulations rumble in sub-bass; dense ones climb into mid-range.

2. Entropy → Chord complexity:
   entropy < 0.15:  open fifth [0, 7]
   entropy < 0.3:   triad [0, 4, 7]
   entropy < 0.5:   seventh [0, 4, 7, 11]
   entropy < 0.7:   ninth [0, 4, 7, 11, 14]
   entropy >= 0.7:  extended [0, 2, 4, 7, 9, 11, 14]
   Entropy is Shannon entropy of the row density distribution, normalized
   to [0, 1]. Ordered patterns stay consonant; chaos produces rich harmony.

3. Spatial clusters → Stereo panning:
   Column profile is scanned for contiguous density peaks (threshold > 0.03).
   Each cluster's centroid maps to a pan position: pan = centroid / n_cols.
   Falls back to quadrant-based panning when no clusters are detected.
   Per-voice stereo placement:
     Bass:    always centered (pan 0.5)
     Melody:  panned to primary (loudest) cluster
     Harmony: chord voices spread across detected clusters (round-robin)
     Rhythm:  panned opposite to melody (1.0 - primary_pan)
   More clusters = wider stereo image.

4. Rate of change (delta) → Rhythm density:
   delta = |density(t) - density(t-1)|
   scaled = min(1.0, delta * 5.0)
   Pattern index = floor(scaled * N_patterns)
   Patterns range from sparse 4-on-floor to dense 16th-note syncopation.
   Rhythm voice mix level also scales with delta.

5. Center of mass → Melody contour:
   register_shift = (0.5 - cy) * 8 semitones
   Higher center of mass = higher melodic register.
   Column density peaks select scale degrees for arpeggiated melody.

Voice synthesis:
  Bass:    0.8 * sin(phase) + 0.2 * sawtooth(phase), portamento between frames
  Melody:  weighted mix of sine, sawtooth, pulse (per category profile)
           Per-step envelope with 3ms attack/decay ramps
  Harmony: sine pad, per-voice stereo from cluster positions
  Rhythm:  0.6 * noise + 0.4 * sin(perc_phase), gated by pattern, fast decay

Master volume = 0.08 + 0.4 * density + 0.2 * min(1.0, delta * 10)
Voice levels normalized: bass ~35%, melody ~30%, harmony ~20%, rhythm ~15%
  (adjusted by drone level, activity, entropy, and delta)

Audio output: 22050 Hz, S16LE stereo, via paplay/aplay/afplay
Frame duration: delay * 0.8 * tempo_mult, clamped to [0.04, 1.5] seconds

Audio profiles per category (12 defined):
  Category              base_freq  scale              tempo  drone
  Classic CA            220 Hz     pentatonic          1.0    0.0
  Particle & Swarm      330 Hz     minor pent + b7     1.5    0.0
  Physics & Waves       196 Hz     major               0.8    0.3
  Fluid Dynamics        110 Hz     in-sen              0.6    0.5
  Chemical & Biological 261 Hz     harmonic minor      0.9    0.2
  Fractals & Chaos      174 Hz     whole-tone-ish      0.7    0.4
  (and 6 more)
```

**What to look for.** Toggle sonification with Ctrl+A during any running simulation. In a Game of Life glider gun, you'll hear a steady low-register pulse with sparse rhythm; as the field fills, the pitch register climbs and chord complexity increases. In Boids, the melody pans across the stereo field as the flock moves. In Reaction-Diffusion, high entropy produces extended 9th/13th chords while stable Turing patterns stay in simple triads. In chaotic rules like Seeds (B2/S), expect dense syncopated rhythms and wide chord voicings. The status bar shows the current root note, melody note count, cluster count (pan:N), and frame number.

**References.**
- Hermann, T., Hunt, A. & Neuhoff, J.G. *The Sonification Handbook*. Logos Publishing House, 2011. https://sonification.de/handbook/
- Vickers, P. & Hogg, B. "Sonification Abstraite/Sonification Concrète: An 'Aesthetic Perspective Space' for Classifying Auditory Displays." *Journal of the Audio Engineering Society*, 2006.

---

## Music Visualizer

**Background.** This mode generates synthetic audio waveforms from musical tone sequences and visualizes them through six rendering modes: spectrum analyzer, oscilloscope waveform, beat-reactive particles, a combined view, a bass-driven tunnel effect, and frequency rain. The audio pipeline synthesizes additive harmonics, simulates an FFT spectrum, and implements a simple beat detection algorithm based on energy thresholds.

**Formulation.** Audio synthesis and analysis are performed each frame:

```
Waveform synthesis (additive harmonics):
  sample(t) = 0.6 * sin(2*pi * f * t)
            + 0.25 * sin(2*pi * 2f * t)
            + 0.1  * sin(2*pi * 3f * t)
            + 0.05 * sin(2*pi * 5f * t)
            + noise ~ N(0, 0.05)
  Amplitude modulation: sample *= 0.7 + 0.3 * sin(2*pi * 0.5 * t)

  where f = base frequency from tone pattern, cycling at 4 notes/sec
  Tone patterns rotate every 2 seconds

Simulated FFT (spectrum bins):
  For each harmonic h with amplitude a:
    bin = floor(f * h / max_freq * N_bars)
    spectrum[bin +/- 1] += a * falloff   (falloff: 1.0 center, 0.4 adjacent)
  Bass rumble: spectrum[0..3] += 0.3 * (0.5 + 0.5 * sin(2*pi * 2 * t)) * sens

Peak decay:
  peak[i] = max(spectrum[i], peak[i] * 0.95)

Beat detection:
  beat_avg = beat_avg * 0.9 + energy * 0.1
  Beat triggers when: energy > beat_avg * 1.5 AND energy > 0.15
  On beat: spawn 5-15 particles radially from center

Band energies:
  bass = mean(spectrum[0 : N/3])
  mid  = mean(spectrum[N/3 : 2N/3])
  high = mean(spectrum[2N/3 : N])

Tunnel effect (view mode 4):
  For each pixel at (dx, dy) from center:
    angle = atan2(dy, dx)
    depth = 1.0 / distance
    u = angle/pi + t * 0.5
    v = depth + t * (1 + bass * 3)
    pattern = sin(u * 8) * sin(v * 4), modulated by bass energy
    brightness = min(1, 2 / (distance + 0.5))
```

**What to look for.** The spectrum view shows FFT bars colored by frequency band (bass/mid/high) with floating peak indicators that decay slowly. Beat detection triggers particle bursts and border flashes on the waveform view. The tunnel view warps with bass energy, creating a zoom-in effect on heavy beats. Four color schemes (Spectrum, Fire, Ocean, Neon) map intensity to different palettes. Sensitivity control scales all amplitudes linearly.

**References.**
- Smith, J.O. "Spectral Audio Signal Processing." W3K Publishing, 2011. https://ccrma.stanford.edu/~jos/sasp/
- Scheirer, E.D. "Tempo and beat analysis of acoustic musical signals." *Journal of the Acoustical Society of America*, 103(1), 588-601, 1998. https://doi.org/10.1121/1.421129

---

## Snowfall & Blizzard

**Background.** This mode simulates snowfall with realistic particle dynamics including wind gusts, ground accumulation, snow drifting, and temperature-dependent flake behavior. Each snowflake is an independent particle affected by gravity, wind, and lateral wobble. Snow accumulates column by column on the ground and can be redistributed by wind, forming drifts. The simulation captures the visual character of weather ranging from gentle flurries to arctic whiteouts.

**Formulation.** Each snowflake carries state [x, y, vx, vy, size, wobble_phase]:

```
Wind gusts (sinusoidal variation):
  gust = 0.4 * sin(phase) + 0.2 * sin(2.3 * phase + 1.0)
  effective_wind = wind_speed * wind_dir + gust

Lateral wobble:
  wobble_phase += dt * (2.0 + size * 0.5)
  wobble = sin(wobble_phase) * (0.15 + size * 0.05)

Velocity update:
  target_vx = effective_wind * (0.6 + size * 0.1)
  vx += (target_vx - vx) * 0.1      (smooth wind response)
  vx += wobble * 0.1
  vy  = 0.3 + size * 0.2 + random(-0.05, 0.05)
  If temperature > 0: vy *= 0.8      (wet snow falls slower)

Accumulation (per-column height):
  When flake hits ground_level:
    accumulation[col] += 0.02 + size * 0.01

Snow drifting (when |wind| > 0.5):
  transfer = accumulation[i] * |wind| * 0.002
  accumulation[i] -= transfer
  accumulation[i + wind_dir] += transfer
  Smoothing: a[i] = 0.98*a[i] + 0.01*(a[i-1] + a[i+1])

Ground drift particles (when |wind| > 1.0):
  Spawn from snow pile tops, blown horizontally

Presets:         density  wind   temp    visibility  max_accum
  Gentle            80    0.3    -3C     1.00        rows/4
  Steady           180    1.2    -8C     0.75        rows/3
  Blizzard         400    3.5    -15C    0.35        rows/2
  Whiteout         600    5.0    -25C    0.15        rows/2
  Wet Snow         120    0.5    +1C     0.85        rows/5
  Squall           350    2.5    -10C    0.45        rows/3

Flake sizes: 0=small, 1=medium, 2=large
  Warmer temperatures bias toward larger (wetter) flakes
```

**What to look for.** In gentle mode, individual flakes trace sinusoidal paths as they drift down. At blizzard intensity, the sheer particle count and horizontal wind create near-horizontal streaks with greatly reduced visibility. Snow accumulates into uneven drifts shaped by wind direction -- reversing wind direction (d key) gradually reshapes the terrain. Warm temperatures produce slower, heavier flakes. Ground-level drift particles are blown off snow pile peaks in high wind, adding texture near the surface.

**References.**
- Fearing, P. "Computer Modelling of Fallen Snow." *Proceedings of SIGGRAPH '00*, ACM, 37-46, 2000. https://doi.org/10.1145/344779.344936
- Moeslund, T.B., Madsen, C.B., Aagaard, M. & Lerche, D. "Modeling Falling and Accumulating Snow." *Vision, Video and Graphics*, 2005. https://doi.org/10.2312/egs20051023

---

## Matrix Digital Rain

**Background.** Inspired by the iconic cascading green characters from the 1999 film *The Matrix*, this mode renders columns of falling character streams with head-glow, brightness decay, and stochastic character mutation. The algorithm creates an illusion of depth through layered streams with varying speeds and lengths within each column.

**Formulation.** Each column maintains a list of independent streams:

```
Stream state: {y, speed, length, chars[], age, mutate_rate}

Stream spawning:
  speed       ~ U(0.3, 1.5)
  length      ~ randint(4, max(5, rows/2))
  mutate_rate ~ U(0.02, 0.1)
  New streams spawn with probability: density * 0.02 per column per step

Stream update:
  y += speed
  For each char in stream:
    If random() < mutate_rate: replace with random char from pool
  Remove stream when: (y - length) > rows + 5

Brightness model (per character cell):
  fraction = index / (length - 1)     (0 = head, 1 = tail)
  brightness:
    index == 0:     4 (head — rendered white)
    fraction < 0.2: 3 (near head — bright green)
    fraction < 0.5: 2 (mid — normal green)
    else:           1 (tail — dim green)

  Later streams overwrite earlier (front layering)

Character pools:
  Katakana:  half-width katakana block (U+FF66-FF9D)
  Digits:    0-9
  Latin:     A-Z
  Symbols:   =+*#@!?%&<>{}[]
  Binary mode: "01" only

Color modes: green (classic), blue, rainbow
  Rainbow: color_pair = (col * 7 + generation) % 6 + 1

Presets:    density  speed  chars
  Classic   0.40     2      full set
  Dense     0.75     3      full set
  Sparse    0.15     1      no symbols
  Katakana  0.40     2      katakana only
  Binary    0.50     2      "01" only
  Rainbow   0.40     2      full set, rainbow color
```

**What to look for.** The white "head" of each stream creates the illusion of an advancing cursor, while the dimming tail fades into the background. Character mutation (flickering) makes streams appear to continuously decode new data. Dense mode fills most columns, creating a near-solid wall of falling text. Sparse mode leaves large gaps, emphasizing individual stream trajectories. In rainbow mode, column position modulates color, creating diagonal color bands that scroll with the animation frame counter.

**References.**
- Pimenta, S. & Poovaiah, R. "On defining visual rhythms for digital media." *Design Thoughts*, 2010. https://doi.org/10.1080/14626268.2010.521913
- Original concept design by Simon Whiteley for *The Matrix* (1999, Warner Bros.)

---

## Kaleidoscope / Symmetry Patterns

**Background.** This mode generates mesmerizing symmetry patterns by plotting procedural seed elements and reflecting them across N-fold rotational symmetry axes. Drawing from mathematical concepts in group theory (dihedral groups D_n), each point is replicated N times around the center with additional mirror reflections, producing the characteristic symmetry of physical kaleidoscopes. Seven procedural animation styles and an interactive paint mode are available.

**Formulation.** The core symmetry operation maps a single plotted point to 2N reflected copies:

```
Symmetry reflection (dihedral group D_n):
  Given point at polar coordinates (r, theta) from center:
  For k = 0 to N-1:
    angle_1 = theta + k * (2*pi / N)
    angle_2 = -theta + 2*k * (2*pi / N) / N    (mirror reflection)
    Plot at both (r, angle_1) and (r, angle_2)
  Aspect ratio correction: x_screen = x * 2.0 (terminal chars ~2x tall)

Procedural seed styles:
  Crystal:   radial line segments, length oscillating with sin(t * freq)
  Wave:      sinusoidal radial waves: amp * sin(r * 0.2 * freq - t * 2 + phase)
  Line:      rotating line with intensity pulsing: 0.6 + 0.4 * sin(step * 0.3 + t)
  Burst:     expanding/contracting pulses: radius ~ (1 + sin(t * freq)) / 2
  Petal:     rose curves: r = R * |sin(freq * angle + t/2 + phase)|
  Spiral:    Archimedean spiral: r = step * radius * 3, angle = step * freq + t * 1.5
  Ring:      concentric pulsing rings with sinusoidal gating

Fade: intensity -= 0.04 per step (toggleable)
Color shift: palette index drifts continuously at 0.01/step

Symmetry orders: 4, 6, 8, 12
Palettes: Jewel Tones, Ice, Fire, Forest, Neon, Monochrome

Presets:      symmetry  style     palette
  Snowflake   6-fold    crystal   Ice
  Mandala     8-fold    wave      Jewel Tones
  Diamond     4-fold    line      Jewel Tones
  Starburst   12-fold   burst     Neon
  Flower      6-fold    petal     Forest
  Vortex      8-fold    spiral    Fire
  Hypnotic    4-fold    ring      Monochrome
  Paint       6-fold    manual    Jewel Tones (no auto, no fade)
```

**What to look for.** Higher symmetry orders (8, 12) produce dense, mandala-like patterns, while 4-fold symmetry creates simpler diamond grids. The Petal style traces rose curves whose lobe count depends on the frequency parameter, producing flower-like forms. Spiral seeds wind outward in Archimedean paths replicated across all axes. Enabling fade creates a trailing afterimage effect; disabling it builds up persistent structures. In Paint mode, cursor movement is mirrored in real time across all symmetry axes, allowing interactive pattern creation.

**References.**
- Coxeter, H.S.M. *Regular Polytopes*, 3rd ed. Dover Publications, 1973. https://store.doverpublications.com/products/9780486614809
- Lu, P.J. & Steinhardt, P.J. "Decagonal and Quasi-Crystalline Tilings in Medieval Islamic Architecture." *Science*, 315(5815), 1106-1110, 2007. https://doi.org/10.1126/science.1135491

---

## ASCII Aquarium / Fish Tank

**Background.** This mode renders a self-contained aquarium ecosystem with procedurally animated fish, swaying seaweed, rising bubbles, interactive feeding, and a sandy bottom terrain. Each fish species has distinct ASCII art sprites for left and right facing orientations, characteristic swimming speeds, and vertical bobbing behavior. The simulation models basic ecological behaviors including food-seeking, startle responses, and wrap-around swimming.

**Formulation.** The aquarium maintains several entity lists updated each tick:

```
Fish dynamics:
  x += vx * startle_multiplier    (startle_mult = 2.5 when startled, else 1.0)
  Wrap: if x > cols + body_len, x = -body_len (and vice versa)
  Direction reversal: 0.5% chance per tick
  Vertical bobbing:
    bob_phase += 0.08
    y = target_y + bob_amp * sin(bob_phase)
  Depth change: 1% chance per tick, new target_y ~ U(water_top, sand_row)
  Startle decay: startled -= 0.1 per tick

Food-seeking behavior:
  If food exists within distance 15:
    Turn toward nearest food
    Adjust target_y toward food's y (10% per tick)
  Eat food when distance < 2

Bubble dynamics:
  y += vy                         (vy ~ U(-0.8, -0.3))
  x += sin(age * 0.3) * 0.15     (lateral wobble)
  Growth: 5% chance per tick to increase char size
  Stream spawning: 30% chance per update cycle from stream origin

Food particles:
  y += 0.15 (slow sinking)
  x += sin(age * 0.2) * 0.1 (gentle drift)
  Removed after 300 ticks

Seaweed animation:
  Sway driven by sin(time * speed + phase) per segment

Presets:
  Tropical Reef:  10-16 fish, species 0-5 (diverse small fish)
  Deep Ocean:     5-8 fish, species 5-7 (large, slow species)
  Koi Pond:       6-10 fish, species 3-4 (medium ornamental)
  Goldfish Bowl:  4-7 fish, species 1-2 (classic goldfish)

Caustic light effect: phase advances at 0.05/tick for surface shimmer
```

**What to look for.** Fish swim back and forth with a natural bobbing motion driven by sinusoidal oscillation. Dropping food (f key) causes nearby fish to break from their patrol pattern and converge on the sinking particles. Tapping the glass (t key) startles all fish, causing them to reverse direction at 2.5x speed before gradually calming. Bubble streams rise from the bottom with gentle lateral oscillation and occasionally spawn new bubbles. Seaweed sways continuously with per-plant phase offsets creating asynchronous motion. Sand terrain is procedurally generated with varying heights per column.

**References.**
- Reynolds, C.W. "Flocks, Herds, and Schools: A Distributed Behavioral Model." *Computer Graphics (SIGGRAPH '87 Proceedings)*, 21(4), 25-34, 1987. https://doi.org/10.1145/37402.37406
- Tu, X. & Terzopoulos, D. "Artificial Fishes: Physics, Locomotion, Perception, Behavior." *Proceedings of SIGGRAPH '94*, ACM, 43-50, 1994. https://doi.org/10.1145/192161.192170
