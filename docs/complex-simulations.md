# Complex Simulations & Audio-Visual

Physics, ecology, and climate simulations, plus audio-visual modes. Each entry lists the mode's background, formulation, presets, controls, and what to look for.

---


## Traffic Flow (Nagel-Schreckenberg Model)

**Background.** The Nagel-Schreckenberg (NaSch) model, introduced in 1992, is a foundational cellular automaton for traffic simulation. It reproduces the spontaneous formation of phantom traffic jams -- stop-and-go waves that appear with no external cause. Each lane is a one-dimensional lattice with periodic boundaries, and each cell is either empty or occupied by a car carrying an integer velocity. This implementation adds multi-lane lane-changing (symmetric two-lane rule), road scenarios (bottleneck, on-ramp, incident), and a live fundamental diagram of flow against density.

**Formulation.** The NaSch update applies four rules simultaneously to all cars each timestep:

```
1. Acceleration:   v(t+1) = min(v(t) + 1, vmax)
2. Braking:        v(t+1) = min(v(t+1), gap)
                   where gap = (distance to next car ahead) - 1
3. Randomization:  with probability p_slow:
                       v(t+1) = max(v(t+1) - 1, 0)
4. Movement:       position(t+1) = (position(t) + v(t+1)) mod L
```

**Lane-changing.** Before the NaSch update, each car that lacks room ahead tries one randomly chosen adjacent lane:

```
Change lane if ALL of:
  - gap_current < v + 1          (not enough room ahead)
  - gap_target > gap_current     (target lane is better)
  - gap_back_target >= vmax      (won't cut off car behind)
  - target cell is empty
```

**Scenario types.** Each preset selects one of four road configurations:

- **open** — periodic ring road (standard NaSch boundary conditions)
- **bottleneck** — speed limit drops to vmax=2 in the centre third of the road, causing flow breakdown and upstream queuing
- **onramp** — a slip road injects cars into lane 0 with probability 0.08 per step, in the zone from one third to one half of the road
- **incident** — a permanent obstacle (stalled vehicle) blocks lane 1 at the road midpoint, producing a rubbernecking cascade

**Parameters:**

```
  vmax    — maximum speed (cells/step), typically 5
  p_slow  — stochastic braking probability, range [0, 1]
  density — fraction of cells initially occupied (ρ)
  lanes   — number of lanes (capped by terminal height)
  L       — lane length (terminal width minus 2, at least 40)

Diagnostics:
  avg_speed = Σv_i / N_cars
  flow (J)  = Σv_i / (lanes × L)
  density (ρ_measured) = N_cars / (lanes × L)
```

**Fundamental diagram.** The flow vs. density plot (drawn in ASCII beside the road view) keeps the last 300 samples. Block glyphs show how often each plot cell was visited, and a filled circle marks the current point. In theory, flow rises linearly in the free-flow regime, peaks at the critical density, then falls as stop-and-go waves dominate.

**Space-time diagram.** Toggled with `v`, this view plots position (x-axis) against time (y-axis, newest at bottom). Glyph and color show the average speed across lanes. Phantom jams appear as dark bands that drift upstream (to the left).

**Presets (10):** Open Highway, Moderate Flow, Rush Hour, Gridlock, Bottleneck, On-Ramp Merge, Incident, Cautious Drivers, Aggressive Drivers, Wide Highway (8 lanes).

**Controls:** `Space`=play/pause, `n`=step, `v`=view toggle (road/space-time), `f`=fundamental diagram on/off, `l`=lane-changing on/off, `p/P`=decrease/increase p_slow (0.05 steps), `+/-`=steps per frame (1-50), `r`=reset, `R`=menu, `q`=exit. `d/D` change the stored density value but do not affect running cars.

**What to look for.** At low density, cars cruise near vmax and flow grows with density. Above the critical density, phantom jams nucleate from the randomization step and move backward as dark bands in the space-time view. At high density, persistent stop-and-go waves dominate. Raising p_slow makes jams more frequent. In the Bottleneck preset, watch for flow breakdown at the speed-limit transition. In On-Ramp Merge, merging cars create disturbances that travel upstream. Toggle lane-changing off to compare with independent lanes.

**References.**
- Nagel, K. & Schreckenberg, M. "A cellular automaton model for freeway traffic." *Journal de Physique I*, 2(12), 2221-2229, 1992. https://doi.org/10.1051/jp1:1992277
- Chowdhury, D., Santen, L. & Schadschneider, A. "Statistical physics of vehicular traffic and some related systems." *Physics Reports*, 329(4-6), 199-329, 2000. https://doi.org/10.1016/S0370-1573(99)00117-9
- Rickert, M., Nagel, K., Schreckenberg, M. & Latour, A. "Two lane traffic simulations using cellular automata." *Physica A*, 231(4), 534-550, 1996. https://doi.org/10.1016/0378-4371(95)00442-4

---

## Galaxy Formation

**Background.** This N-body simulation models the gravitational dynamics of spiral galaxies. Particles representing stars and gas orbit within an analytic dark matter halo whose gravitational potential follows an NFW (Navarro-Frenk-White) profile. The presets show how spiral arms, velocity dispersion, tidal interactions, and gas pressure produce different galaxy shapes, from grand-design spirals to ellipticals and mergers.

**Formulation.** Each particle carries the state [x, y, vx, vy, mass, type]. Each step applies these forces:

```
Halo force (NFW-like profile):
  r     = sqrt((x - cx)^2 + (y - cy)^2)
  F_halo = -G * M_halo * r / (r + r_s)^2

Grid-based particle-particle gravity (binned to 4-cell resolution,
summed over the 5x5 bins around each particle):
  F_pp  = G * m_bin / (d^2 + epsilon^2)
  where d = distance to bin center-of-mass, epsilon = softening

Gas pressure (for gas particles, type > 0.5):
  If the particle's bin mass > 3.0:
    F_pressure = 0.5 * (bin_mass - 3.0) * (away from bin center-of-mass)
  Gas cooling: v *= 0.998 per step

Circular orbital velocity (initialization):
  v_circ = sqrt(G * M_halo * r / (r + r_s)^2 + 0.1)

Spiral arm placement (logarithmic spiral perturbation):
  angle = base_angle + arm_index * (2*pi / N_arms) + 0.3 * ln(1 + r) * N_arms

Integration (kick, then drift; positions wrap at the edges):
  v(t + dt) = v(t) + a(t) * dt
  x(t + dt) = x(t) + v(t + dt) * dt

Parameters:
  G           — gravitational constant (default 1.0, range 0.1-5.0)
  M_halo      — dark matter halo mass (1000; 300 in Dwarf Irregular)
  r_s         — halo scale radius (30; 15 in Dwarf Irregular; scaled down on small grids)
  dt          — timestep (default 0.03, range 0.005-0.2)
  epsilon     — softening length (1.0)
```

**Presets (8):** Milky Way, Grand Design, Whirlpool, Elliptical, Dwarf Irregular, Galaxy Merger, Ring Galaxy, Barred Spiral.

**Controls:** `Space`=play/pause, `n`=step, `v`=view (combined/stars/gas/velocity), `g/G`=raise/lower gravity, `d/D`=raise/lower dt, `w/W`=rotation speed and `f/F`=gas fraction (both change a stored value that the simulation never reads, so they have no effect), `h`=halo overlay, `+/-`=steps per frame (1-10), `r`=reset, `R` or `m`=menu, `q` or `Esc`=exit.

**What to look for.** In the Milky Way and Grand Design presets, watch spiral arms wind up over time. The Whirlpool preset adds a small companion galaxy that starts off to one side and moves toward the main disk. The Galaxy Merger preset starts two disk galaxies on a collision course. Elliptical starts with random velocities and no net rotation. The halo overlay (`h`) shows the NFW density profile behind all the dynamics. Gas particles lose speed slowly and feel pressure in dense bins.

**References.**
- Navarro, J.F., Frenk, C.S. & White, S.D.M. "The Structure of Cold Dark Matter Halos." *The Astrophysical Journal*, 462, 563, 1996. https://doi.org/10.1086/177173
- Toomre, A. & Toomre, J. "Galactic Bridges and Tails." *The Astrophysical Journal*, 178, 623-666, 1972. https://doi.org/10.1086/151823

---

## Smoke & Fire

**Background.** This mode simulates combustion and buoyant fluid dynamics on an Eulerian grid. Temperature, smoke density, fuel, and velocity fields interact through simplified Navier-Stokes-like advection, diffusion, and buoyancy. The advection step follows Stam (1999) on stable fluids, simplified for ASCII rendering and without a pressure solve. Fire sources inject heat. Heat rises through buoyancy, burns fuel, and makes smoke that fades over time.

**Formulation.** Each step evolves temperature T, smoke S, fuel F, and the velocity (vx, vy).

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
                   (height_fraction = 0 at the bottom row, near 1 at the top)
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
  Wildfire Spread  0.12      0.06        0.008    0.4         0.02
  Explosion Burst  0.25      0.12        0.02     0.6         0.0
  Candle Row       0.10      0.02        0.018    0.15        0.0
  Inferno          0.20      0.08        0.006    0.5         0.01
  Smoke Stack      0.18      0.05        0.01     0.5         0.03
```

**Controls:** `Space`=play/pause, `n`=step, arrows or `hjkl`=move cursor, `f` or `Enter`=add or remove a fire source at the cursor, `F`=add fuel around the cursor, `b/B`=buoyancy up/down, `t/T`=turbulence up/down, `w/W`=wind up/down, `c/C`=cooling up/down, `>/<`=steps per frame (1-10), `R`=menu, `q`=exit. There is no reset key. Use `R` and pick the scene again.

**What to look for.** Campfire shows a steady flickering flame with a rising smoke plume. Wildfire Spread ignites fuel on the left, and the fire moves right across the fuel bed, helped by the wind. Explosion Burst starts with a radial velocity burst. More turbulence makes the flames billow. More buoyancy makes them taller and thinner. Fire sources flicker with intensity 0.7 + random * 0.3.

**References.**
- Stam, J. "Stable Fluids." *Proceedings of SIGGRAPH '99*, ACM, 121-128, 1999. https://doi.org/10.1145/311535.311548
- Nguyen, D.Q., Fedkiw, R. & Jensen, H.W. "Physically Based Modeling and Animation of Fire." *ACM Transactions on Graphics*, 21(3), 721-728, 2002. https://doi.org/10.1145/566654.566643

---

## Fireworks

**Background.** This particle system simulates pyrotechnic displays using Newtonian projectile dynamics. Rockets launch upward against gravity, explode into bursts of sparks in several patterns, and fade with short trails. Ballistic motion, drag, and gravity give the sparks their arc and droop.

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
  Crossette:  4-6 sub-sparks (life 10-16 ticks) that each re-explode as a
              spherical burst when they die

Parameters:
  gravity     — downward acceleration (0.04-0.06 in the presets)
  launch_rate — probability of auto-launch per tick (0.04-0.18 in the presets)
  wind        — horizontal drift per tick
  fuse        — ticks before a rocket explodes, random in [rows/4, rows*2/3]

Trail rendering: 6-element position history for sparks, oldest entries dimmer
Life fraction:   life / max_life determines spark brightness
```

**Presets (6):** Grand Finale, Gentle Evening, Crossette Show, Willow Garden, Ring Parade, Random Mix.

**Controls:** `Space`=play/pause, `n`=step, `f` or `Enter`=launch a rocket, `a`=auto-launch on/off, `g/G`=gravity up/down, `w/W`=wind up/down, `l/L`=launch rate up/down, `+/-` or `>/<`=steps per frame (1-10), `r`=reset, `R`=menu, `q`=exit.

**What to look for.** Grand Finale has the highest launch rate (0.18) and mixes all patterns. Willow shells leave long, drooping trails because their gravity multiplier is higher. Crossette shells cascade: each sub-spark flies outward, then bursts into its own secondary burst. Higher gravity pulls sparks down faster. Wind drifts all active particles sideways. The preset's pattern applies to the three opening rockets and to manual launches. Auto-launched rockets pick a random pattern.

**References.**
- Reeves, W.T. "Particle Systems -- A Technique for Modeling a Class of Fuzzy Objects." *ACM Transactions on Graphics*, 2(2), 91-108, 1983. https://doi.org/10.1145/357318.357320
- Sims, K. "Particle Animation and Rendering Using Data Parallel Computation." *Computer Graphics (SIGGRAPH '90 Proceedings)*, 24(4), 405-413, 1990. https://doi.org/10.1145/97880.97923

---


## Sonification Engine (Generative Soundscape)

**Source:** `life/modes/sonification.py`

**Background.** The sonification engine is a cross-cutting audio layer that attaches to any running simulation mode and maps its spatial dynamics to a real-time generative music composition. Rather than a standalone mode, it operates as a toggleable overlay (Ctrl+S) that adds sound to the visuals. Conway's Game of Life sounds fundamentally different from a fluid simulation or a strange attractor. The engine synthesizes four simultaneous voices (bass, melody, harmony, rhythm) using additive waveform synthesis, with musical parameters driven by frame-by-frame analysis of the simulation's spatial state.

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

**What to look for.** Toggle sonification with Ctrl+S during any running simulation. In a Game of Life glider gun, you'll hear a steady low-register pulse with sparse rhythm; as the field fills, the pitch register climbs and chord complexity increases. In Boids, the melody pans across the stereo field as the flock moves. In Reaction-Diffusion, high entropy produces extended 9th/13th chords while stable Turing patterns stay in simple triads. In chaotic rules like Seeds (B2/S), expect dense syncopated rhythms and wide chord voicings. The status bar shows the current root note, melody note count, cluster count (pan:N), and frame number.

**References.**
- Hermann, T., Hunt, A. & Neuhoff, J.G. *The Sonification Handbook*. Logos Publishing House, 2011. https://sonification.de/handbook/
- Vickers, P. & Hogg, B. "Sonification Abstraite/Sonification Concrète: An 'Aesthetic Perspective Space' for Classifying Auditory Displays." *Journal of the Audio Engineering Society*, 2006.

---

## Music Visualizer

**Background.** This mode synthesizes a stream of musical tones and shows it in six views: spectrum analyzer, oscilloscope waveform, beat-reactive particles, a combined view, a bass-driven tunnel, and frequency rain. It does not read a microphone or play audio. The pipeline adds harmonics, builds a simulated FFT spectrum, and detects beats with an energy threshold.

**Formulation.** Audio synthesis and analysis are performed each frame:

```
Waveform synthesis (additive harmonics):
  sample(t) = 0.6 * sin(2*pi * f * t)
            + 0.25 * sin(2*pi * 2f * t)
            + 0.1  * sin(2*pi * 3f * t)
            + 0.05 * sin(2*pi * 5f * t)
            + noise ~ N(0, 0.05)
  Amplitude modulation: sample *= 0.7 + 0.3 * sin(2*pi * 0.5 * t)

  where f = base frequency from the tone pattern, cycling at 4 notes/sec
  Tone patterns (4 of them, one with silent notes) rotate every 2 seconds

Simulated FFT (spectrum bins):
  For each harmonic h with amplitude a:
    bin = floor(f * h / max_freq * N_bars)
    spectrum[bin +/- 1] += a * falloff   (falloff: 1.0 center, 0.4 adjacent)
  Bass rumble: spectrum[i] += 0.3 * (0.5 + 0.5 * sin(2*pi * 2 * t)) * sens * (1 - i/4)
               for the first four bins (i = 0..3)
  Noise floor: spectrum[i] += U(0, 0.05) * sens, then clamp to [0, 1]

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

Bass Tunnel view:
  For each pixel at (dx, dy) from center:
    angle = atan2(dy, dx)
    depth = 1.0 / distance
    u = angle/pi + t * 0.5
    v = depth + t * (1 + bass * 3)
    pattern = sin(u * 8) * sin(v * 4), modulated by bass energy
    brightness = min(1, 2 / (distance + 0.5))
```

**Presets (6):** Spectrum Bars, Waveform, Particles, Combined, Bass Tunnel, Frequency Rain. Each preset only picks the starting view.

**Controls:** `Space`=play/pause, `v`=next view, `c`=color scheme, `+/-`=sensitivity (0.1-3.0), `b/B`=more/fewer bars (8-64), `n/N`=next/previous preset, `r`=reset, `R` or `m`=menu, `q`=exit.

**What to look for.** The spectrum view shows bars colored by frequency band (bass/mid/high) with peak markers that decay slowly. A detected beat spawns particles and flashes the waveform view. The tunnel scrolls faster with bass energy. Four color schemes (spectrum, fire, ocean, neon) map intensity to different palettes. Sensitivity scales the synthesized amplitudes before clamping.

**References.**
- Smith, J.O. "Spectral Audio Signal Processing." W3K Publishing, 2011. https://ccrma.stanford.edu/~jos/sasp/
- Scheirer, E.D. "Tempo and beat analysis of acoustic musical signals." *Journal of the Acoustical Society of America*, 103(1), 588-601, 1998. https://doi.org/10.1121/1.421129

---

## Snowfall & Blizzard

**Background.** This mode simulates snowfall with wind gusts, ground accumulation, snow drifting, and a simple temperature effect. Each snowflake is an independent particle pushed by gravity, wind, and a lateral wobble. Snow piles up column by column and the wind moves it sideways to form drifts. Weather ranges from gentle flurries to arctic whiteouts.

**Formulation.** Each snowflake carries state [x, y, vx, vy, size, wobble_phase]:

```
Wind gusts (sinusoidal variation):
  gust = 0.4 * sin(phase) + 0.2 * sin(2.3 * phase + 1.0)
  effective_wind = wind_speed * wind_dir + gust
  (phase advances by 0.7 * dt per step)

Lateral wobble:
  wobble_phase += dt * (2.0 + size * 0.5)
  wobble = sin(wobble_phase) * (0.15 + size * 0.05)

Velocity update:
  target_vx = effective_wind * (0.6 + size * 0.1)
  vx += (target_vx - vx) * 0.1      (smooth wind response)
  vx += wobble * 0.1
  vy  = 0.3 + size * 0.2 + random(-0.05, 0.05)
  If temperature > 0: vy *= 0.8      (wet snow falls slower)

Accumulation (per-column height, capped at max_accum):
  When flake hits ground_level:
    accumulation[col] += 0.02 + size * 0.01
    (the flake then respawns at the top)

Snow drifting (when |effective_wind| > 0.5):
  transfer = accumulation[i] * |effective_wind| * 0.002
  accumulation[i] -= transfer
  accumulation[i + wind_dir] += transfer
  Smoothing: a[i] = 0.98*a[i] + 0.01*(a[i-1] + a[i+1])

Ground drift particles (when |effective_wind| > 1.0):
  Spawn from piles higher than 0.5, blown horizontally for 15-40 steps

Presets:                density  wind   temp    visibility  max_accum
  Gentle Snowfall          80    0.3    -3C     1.00        rows/4
  Steady Winter Storm     180    1.2    -8C     0.75        rows/3
  Heavy Blizzard          400    3.5    -15C    0.35        rows/2
  Arctic Whiteout         600    5.0    -25C    0.15        rows/2
  Wet Spring Snow         120    0.5    +1C     0.85        rows/5
  Mountain Squall         350    2.5    -10C    0.45        rows/3
  (Arctic Whiteout blows toward the left; the others toward the right.)

Flake sizes: 0=small, 1=medium, 2=large
  At reset, temperatures above -2C bias flake sizes one step larger
  (only Wet Spring Snow)
```

**Controls:** `Space`=play/pause, `n` or `.`=step, `+/-`=speed (1-10), `w/W`=wind up/down, `d`=flip wind direction, `f/F`=more/fewer flakes (20-800), `t/T`=warmer/colder (-30 to +3C), `i`=info panel, `r`=reset, `R` or `m`=menu, `q`=exit.

**What to look for.** In Gentle Snowfall, flakes trace slow wavy paths. In Heavy Blizzard and Arctic Whiteout, the flake count and wind make near-horizontal streaks with low visibility. Snow piles into uneven drifts shaped by the wind. Flipping the wind (`d`) slowly reshapes them. Above 0C, flakes fall 20% slower. In strong wind, drift particles blow off the tops of piles.

**References.**
- Fearing, P. "Computer Modelling of Fallen Snow." *Proceedings of SIGGRAPH '00*, ACM, 37-46, 2000. https://doi.org/10.1145/344779.344936
- Moeslund, T.B., Madsen, C.B., Aagaard, M. & Lerche, D. "Modeling Falling and Accumulating Snow." *Vision, Video and Graphics*, 2005. https://doi.org/10.2312/egs20051023

---

## Matrix Digital Rain

**Background.** Inspired by the iconic cascading green characters from the 1999 film *The Matrix*, this mode draws columns of falling character streams with a bright head, a fading tail, and random character changes. Streams in a column have different speeds and lengths, which gives a sense of depth.

**Formulation.** Each column maintains a list of independent streams:

```
Stream state: {y, speed, length, chars[], age, mutate_rate}

Stream spawning:
  speed       ~ U(0.3, 1.5)
  length      ~ randint(4, max(5, rows/2))
  mutate_rate ~ U(0.02, 0.1)
  At reset, each column gets one stream with probability = density.
  Afterwards, a new stream spawns with probability density * 0.02 per column per step.

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

  Where streams overlap, the brighter cell wins

Character pools:
  Katakana:  half-width katakana block (U+FF66-FF9D)
  Digits:    0-9
  Latin:     A-Z
  Symbols:   +-*/<>=$#@&!?~^%
  Binary mode: "01" only

Color modes: green (classic), blue (drawn in cyan), rainbow
  Rainbow: color_pair = (col * 7 + generation) % 6 + 1

Presets:         density  speed  chars
  Classic Green  0.40     2      full set
  Dense Rain     0.75     3      full set
  Sparse Drizzle 0.15     1      no symbols
  Katakana Only  0.40     2      katakana only
  Binary         0.50     2      "01" only
  Rainbow        0.40     2      full set, rainbow color
```

**Controls:** `Space`=play/pause, `n` or `.`=step, `s/S` or `+/-`=faster/slower (1-10), `d/D`=density up/down, `c`=cycle color (green, blue, rainbow), `i`=info overlay, `r`=reset, `R` or `m`=menu, `q`=exit.

**What to look for.** The white head of each stream reads as an advancing cursor, and the tail fades into the background. Character mutation makes the streams flicker. Dense Rain fills most columns with falling text. Sparse Drizzle leaves large gaps, so you can follow single streams. In rainbow mode, color depends on the column and the frame counter, so diagonal color bands scroll across the screen.

**References.**
- Pimenta, S. & Poovaiah, R. "On defining visual rhythms for digital media." *Design Thoughts*, 2010. https://doi.org/10.1080/14626268.2010.521913
- Original concept design by Simon Whiteley for *The Matrix* (1999, Warner Bros.)

---

## Kaleidoscope / Symmetry Patterns

**Background.** This mode draws symmetric patterns by plotting animated seed elements and reflecting them across N-fold symmetry axes. Each point is copied N times around the center, plus mirror copies, like the dihedral group D_n and a physical kaleidoscope. It has seven animation styles and a paint mode.

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
Color shift: a color-shift value grows by 0.01 per step; the palette index moves by 10x that (0.1 per step)

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
  Paint Mode  6-fold    manual    Jewel Tones (no auto, no fade)
```

**Controls:** `Space`=play/pause, `+/-`=speed (1-10), `s`=cycle symmetry (4, 6, 8, 12), `c`=cycle palette, `f`=fade on/off, `p`=paint on/off, arrows=move the paint cursor and paint (paint on), `Enter`=paint at the cursor, `b`=brush size (1-3), `i`=info overlay, `r`=clear canvas, `Esc`=back to the menu.

**What to look for.** Higher symmetry orders (8, 12) give dense, mandala-like patterns. 4-fold symmetry gives simpler diamond grids. The petal style draws rose curves whose lobe count depends on the seed's frequency. Spiral seeds wind outward and are copied across all axes. With fade on, old marks leave trails. With fade off, structure builds up. In Paint Mode, each cursor move paints and is mirrored across all axes.

**References.**
- Coxeter, H.S.M. *Regular Polytopes*, 3rd ed. Dover Publications, 1973. https://store.doverpublications.com/products/9780486614809
- Lu, P.J. & Steinhardt, P.J. "Decagonal and Quasi-Crystalline Tilings in Medieval Islamic Architecture." *Science*, 315(5815), 1106-1110, 2007. https://doi.org/10.1126/science.1135491

---

## ASCII Aquarium / Fish Tank

**Background.** This mode draws a fish tank with animated fish, swaying seaweed, rising bubbles, a sandy bottom, and food you can drop. Each of the 8 fish species has its own ASCII sprite for each facing, its own speed range, and a vertical bob. Fish chase food, bolt when you tap the glass, and wrap around the tank edges.

**Formulation.** The aquarium maintains several entity lists updated each tick:

```
Fish dynamics:
  x += vx * startle_multiplier    (startle_mult = 2.5 when startled, else 1.0)
  Wrap: past the right edge, a fish re-enters from the left (and vice versa)
  Direction reversal: 0.5% chance per tick
  Vertical bobbing:
    bob_phase += 0.08
    y = target_y + bob_amp * sin(bob_phase)
  Depth change: 1% chance per tick, new target_y ~ U(water_top + 1, sand_row - 3)
  Startle: tapping the glass sets startled = 3.0; it drops by 0.1 per tick
           (about 30 ticks), and fish move at 2.5x speed meanwhile

Food-seeking behavior:
  If food exists within Manhattan distance 15 of the nearest food:
    Turn toward nearest food
    Move target_y 10% of the way toward the food's y each tick
  Eat food when Manhattan distance < 2

Bubble dynamics:
  y += vy                         (vy ~ U(-0.8, -0.3))
  x += sin(age * 0.3) * 0.15     (lateral wobble)
  Growth: after age 5, 5% chance per tick to use the next bubble glyph
  Stream spawning: every (8 - speed) ticks of age, 30% chance to emit a
                   new bubble at the stream's x
  Removed at the water surface

Food particles:
  y += 0.15 (slow sinking)
  x += sin(age * 0.2) * 0.1 (gentle drift)
  Removed after 300 ticks

Seaweed animation:
  Sway driven by sin(time * speed + phase) per segment

Presets:
  Goldfish Bowl:  4-7 fish, Goldfish and Angelfish
  Tropical Reef:  10-16 fish, Neon Tetra, Goldfish, Angelfish, Koi, Guppy, Clownfish
  Koi Pond:       6-10 fish, Koi and Guppy
  Deep Sea:       5-8 fish, Clownfish, Pufferfish and Anglerfish

Caustic light effect: phase advances at 0.05/tick for surface shimmer
```

**Controls:** `Space`=play/pause, `f`=drop food, `t`=tap the glass, `a`=add a fish, `d`=remove a fish, `b`=add a bubble stream, `+/-`=speed (1-5), `i`=info overlay, `R` or `Esc`=menu, `q`=exit.

**What to look for.** Fish swim back and forth with a natural bobbing motion driven by sinusoidal oscillation. Dropped food (`f`) pulls nearby fish out of their patrol and into the sinking particles. Tapping the glass (`t`) makes every fish reverse and swim faster for a few seconds. Bubble streams rise from the bottom with a small sideways wobble. Seaweed sways with a different phase per plant. The sand has random heights per column.

**References.**
- Reynolds, C.W. "Flocks, Herds, and Schools: A Distributed Behavioral Model." *Computer Graphics (SIGGRAPH '87 Proceedings)*, 21(4), 25-34, 1987. https://doi.org/10.1145/37402.37406
- Tu, X. & Terzopoulos, D. "Artificial Fishes: Physics, Locomotion, Perception, Behavior." *Proceedings of SIGGRAPH '94*, ACM, 43-50, 1994. https://doi.org/10.1145/192161.192170

---

## Cellular Symphony

**Background.** Cellular Symphony treats the grid as a step sequencer: each row is a beat, each live cell is a voice, and the column sets the pitch. CA patterns such as gliders, oscillators, and still lifes then make distinct musical textures with no composing. Pitch, timbre, and loudness each come from a different property of the cell. Rule sets change the sound: Conway's Life gives chaotic jazz-like phrases, Seeds gives staccato bursts, and Maze gives thick clusters.

**Formulation.** The sequencer scans one grid row per beat at a configurable tempo (20-300 BPM, steps of 10). For each live cell in the current row:

```
Pitch mapping (column → frequency):
  intervals = SCALES[scale]           (pentatonic, chromatic, blues, whole_tone)
  num_notes = len(intervals) * octave_range
  idx       = col * num_notes / total_cols
  octave, degree = divmod(idx, len(intervals))
  semitones = octave * 12 + intervals[degree]
  freq      = 130.81 * 2^(semitones / 12)     (base = C3)

Timbre shaping (neighbor count → harmonic richness):
  nbrs = Moore neighborhood count (0–8)
  Fundamental:           always present
  +octave harmonic:      amplitude 0.3  when nbrs >= 3
  +third harmonic:       amplitude 0.15 when nbrs >= 5 (a fifth above the octave)
  +fourth harmonic:      amplitude 0.08 when nbrs >= 7 (two octaves up)
  Waveform options (t): sine, saw, square, triangle
  Octave range options (o): 2, 3, 4, 5

Amplitude shaping (cell age → loudness):
  age = min(cell_value, 10)
  amp_scale = 0.4 + 0.6 * (age / 10)

Synthesis:
  Voices capped at 16 per beat (the 16 leftmost live cells)
  Per-voice amplitude = volume / num_voices
  Attack/release ramp = 8 ms (anti-click)
  Note duration = clamp(beat_interval * 0.8, 0.05 s, 2.0 s)
  Output: S16LE mono PCM at 22050 Hz

CA stepping:
  The grid advances one generation after the scan has played every row once
```

**Rule presets (7).** Tab cycles through them. Each has a musical character:

| Rule | Birth | Survival | Character |
|------|-------|----------|-----------|
| Conway's Life | 3 | 2,3 | chaotic jazz |
| Seeds | 2 | — | staccato bursts |
| Day & Night | 3,6,7,8 | 3,4,6,7,8 | dense chords |
| Diamoeba | 3,5,6,7,8 | 5,6,7,8 | evolving drones |
| HighLife | 3,6 | 2,3 | melodic drift |
| Maze | 3 | 1,2,3,4,5 | thick clusters |
| Anneal | 4,6,7,8 | 3,5,6,7,8 | ambient wash |

**Controls:** `Space`=play/pause, `Enter`=play one row, `p`=paint mode (arrows move the cursor, `x` toggles the cell under it), `s`=cycle scale (pentatonic, chromatic, blues, whole-tone), `t`=cycle timbre, `o`=cycle octave range, `+/-`=tempo, `v/V`=volume up/down, `r`=randomize grid, `c`=clear grid, `Tab`=next rule preset, `m`=mute, `h`=help overlay, `q` or `Esc`=exit.

**What to look for.** The scan row sweeps down the grid (highlighted), and you can hear structure. Gliders repeat a melodic fragment that shifts pitch as they cross columns. Blinkers pulse at a fixed pitch. Random regions are dense and noisy, and thin out as the CA settles. Pentatonic avoids dissonance. Chromatic gives every column its own semitone. The voice meter at the bottom shows the current polyphony. In paint mode, a diagonal line of cells plays as an ascending or descending run on the next scan.

**References.**
- Hermann, T., Hunt, A. & Neuhoff, J.G. *The Sonification Handbook*. Logos Verlag, 2011. https://sonification.de/handbook/
- Xenakis, I. *Formalized Music: Thought and Mathematics in Composition*. Pendragon Press, 1992.
- Burraston, D. & Edmonds, E. "Cellular Automata in Generative Electronic Music and Sonic Art: A Historical and Technical Review." *Digital Creativity*, 16(3), 165-185, 2005. https://doi.org/10.1080/14626260500370882

---

## Wildfire Spread & Firefighting

**Source:** `life/modes/wildfire.py`

**Background.** This mode simulates wildfire spread with a Rothermel-inspired model on uneven terrain. Unlike the Forest Fire mode (a percolation-style CA with binary states), it tracks continuous fire intensity. It models crown fire, wind- and slope-driven spread, ember spotting, smoke plumes, and autonomous firefighters. Six fuel types (grass, shrub, timber, urban, water, rock) differ in spread rate, heat content, moisture extinction, crown fire threshold, and ember production. Elevation comes from random Gaussian hills, and each preset has its own fuel layout.

**Formulation.** Fire intensity evolves on an 8-connected grid. Each cell maintains: intensity (continuous, ≥0), fuel type, fuel moisture, elevation, burned status, crown fire flag, and smoke density.

```
Spread from neighbor n to cell (r,c):
  base     = I_n × spread_rate_fuel(n) × global_spread / dist(n)
  wind     = max(0.1, 1.0 + 0.5 × dot(wind_vec(n), direction_to(r,c)))
  slope    = clamp(1.0 + slope_factor × Δh / max(1, 3 × dist), 0.2, 3.0)
             (Δh = elevation of the target cell minus the neighbor's)
  moisture = (1 - (m / m_ext)^1.5)  if m < m_ext, else 0
             (m, m_ext: moisture and extinction moisture of the target cell)
  crown    = 1.5 if neighbor is crown fire, else 1.0

  contribution = base × wind × slope × moisture × crown
  spread_in = Σ max(0, contribution)  over all 8 neighbors

Intensity update (existing fire):
  I(t+1) = I(t) + 0.3 × spread_in − burnout × (1 + 0.1 × I(t))
  If already burned: additional −0.5 × burnout (fuel exhaustion)

New ignition (I(t) = 0):
  threshold = 0.15 + moisture × 0.5
  If spread_in > threshold:  I(t+1) = 0.5 × spread_in

Crown fire transition:
  Crown when I ≥ fuel-specific crown_thr AND I ≥ global crown_intensity
  (crown_intensity is 2.5; 1.8 in Firestorm)
```

**Fuel properties:**

```
  Fuel Type  spread  heat  moist_ext  crown_thr  ember_prod
  Grass       1.8    0.6     0.25      999 (n/a)    0.02
  Shrub       1.2    1.0     0.30       3.5          0.05
  Timber      0.7    1.8     0.35       2.5          0.10
  Urban       0.4    2.5     0.15       2.0          0.08
  Water       0.0    0.0     1.00      999 (n/a)     0.0
  Rock        0.0    0.0     1.00      999 (n/a)     0.0
```

**Ember spotting.** Cells with intensity > 1.5 launch embers with probability `fuel_ember × ember_prob × intensity`. Embers travel downwind with angular perturbation (±0.5 rad) at random range (3 to `ember_range` cells). Embers ignite dry, unburned, non-firebreak cells where moisture < 0.8 × moisture extinction, starting fires at intensity 0.8–1.3.

**Smoke plume.** Cells with intensity above 0.3 add smoke = intensity × 0.15 (×2 for crown fire), plus 40% of that one cell downwind (0.8× the local wind velocity, truncated to whole cells). All smoke is multiplied by `smoke_decay` (0.92) each step.

**Firefighter agents.** Two agent types move one cell per step toward the nearest cell with intensity above 0.3, within a search radius of max(5, min(rows, cols) / 5). They do not step into cells with intensity of 0.5 or more.
- **Break agents** mark the unburned, unburning cells in the 3×3 area around them as firebreaks. Fire cannot enter those cells.
- **Water agents** subtract 1.5 from intensity and add 0.3 to moisture (capped at 1.0) in the 3×3 area around them.
After acting, break agents wait 2 steps and water agents wait 3. Firestorm has no firefighters. Prescribed Burn and Urban-Wildland Interface have more than the other presets.

**Fuel moisture dynamics.** Cells with intensity above 0.5 dry their 8 neighbors by `0.005 × intensity` per step. This lowers ignition thresholds ahead of the front.

**Presets (6):**

| Preset | Wind | Moisture | Elevation | Terrain | Behavior |
|--------|------|----------|-----------|---------|----------|
| Grassland Brushfire | 1.5 E | 0.10 | 3 m | Flat grass | Fast, low-intensity, wide front |
| Mountain Wildfire | 0.8 NE | 0.20 | 25 m | Steep timber | Slope-driven runs, heavy spotting |
| Urban-Wildland Interface | 1.2 E | 0.12 | 8 m | Urban clusters in shrub and timber | Structure ignitions, firefighter defense |
| Prescribed Burn | 0.5 E | 0.22 | 4 m | Grass/shrub | Low intensity, containment lines |
| Firestorm | 2.0 ENE | 0.05 | 15 m | Mostly timber and shrub | Crown fire, heavy spotting, three ignition points, no firefighters |
| Canyon Wind Event | 2.5 S | 0.08 | 20 m | Canyon channel | Strong southward wind along the canyon |

**Controls:** `Space`=play/pause, `n`=step, `v`=cycle views (fire/elevation/fuel/moisture), `w/W`=rotate wind direction (+/- 0.2 rad), `s/S`=wind speed down/up (0-5), `+/-`=steps per frame (1-20), `r`=reset, `R`=menu, `q`=exit.

**What to look for.** In Grassland Brushfire, the fire front advances rapidly but at low intensity, leaving a wide ash footprint. Mountain Wildfire shows slope-driven acceleration: fire races uphill and launches embers downwind, which start secondary fronts. The Urban-Wildland Interface shows structure-to-vegetation-to-structure fire chains, with firefighter agents attempting to defend buildings. Prescribed Burn demonstrates controlled fire management: break agents cut firebreaks and water agents suppress escaping flames. Firestorm has extreme conditions: crown fire and doubled smoke production. Canyon Wind Event pushes fire south through a shrub and grass canyon, with slower timber on the ridges. Switch views to see how elevation drives spread, how fuel layout creates corridors, and how moisture drops ahead of the front.

**References.**
- Rothermel, R.C. "A Mathematical Model for Predicting Fire Spread in Wildland Fuels." USDA Forest Service Research Paper INT-115, 1972. https://www.fs.usda.gov/treesearch/pubs/32533
- Finney, M.A. "FARSITE: Fire Area Simulator — Model Development and Evaluation." USDA Forest Service Research Paper RMRS-RP-4, 1998. https://doi.org/10.2737/RMRS-RP-4
- Albini, F.A. "Estimating Wildfire Behavior and Effects." USDA Forest Service General Technical Report INT-30, 1976. https://www.fs.usda.gov/treesearch/pubs/29574
- Linn, R.R. & Cunningham, P. "Numerical simulations of grass fires using a coupled atmosphere-fire model." *Journal of Geophysical Research*, 110, D13107, 2005. https://doi.org/10.1029/2004JD005597

---

## City Growth & Urban Simulation

**Source:** `life/modes/city_growth.py`

**Background.** This mode simulates urban growth. Residential, commercial, and industrial zones form around roads, driven by land value, population, and simple zoning attraction and repulsion rules. It models the city at the scale of districts, not single buildings or vehicles. Land value, road access, traffic, and zoning compatibility feed back on each other. The ideas come from urban economics (Alonso's bid-rent theory).

**Formulation.** Each cell has a zone type, a density level (0-5), a land value (0-100), a traffic load, and a population. There are eight zone types:

```
Zone types:
  Empty (0)       — undeveloped land
  Road (1)        — transportation network
  Residential (2) — housing, carries population
  Commercial (3)  — shops, offices, employment
  Industrial (4)  — factories, warehouses
  Park (5)        — green space, amenity bonus
  Water (6)       — natural water bodies
  Ruin (7)        — decayed infrastructure

Density levels (for Residential/Commercial/Industrial):
  0 = vacant, 1 = sparse, 2 = low, 3 = medium, 4 = high, 5 = maximum
  Population cap per cell = (density + 1) * 20
```

Each step has four phases. The growth rate (`+/-`) scales zoning, population growth, density, gentrification, reclaiming, and new roads. It does not scale land value, traffic, or decay.

**1. Land value.** Each non-water cell changes its land value a little each step (neighbors are the 8 surrounding cells):

```
Land value change per step:
  road within 2 cells:        +0.3        (nearest road 5+ cells away or none: -0.1)
  each commercial neighbor:   +0.15
  each industrial neighbor:   -0.4
  each park neighbor:         +0.25
  each ruin neighbor:         -0.3
  traffic on the cell:        -0.2 * traffic
  decay > 0.5:                -0.5
  centrality:                 +0.1 * (1 - distance_to_center / max_distance)

  value = clamp(value + change, 0, 100)
```

**2. Traffic.** Each populated zone cell adds 0.05 * population of traffic to every road cell in the 7x7 square around it, divided by the Manhattan distance (at least 1). Traffic on a road cell is half its old value plus the new load, capped at 20. Traffic is only tracked on road cells, so it lowers road land value but does not reach the population rules.

**3. Zoning and growth.** Each step, an empty cell within 3 cells of a road may become a zone. One random roll picks among the four types below. The odds depend on land value and neighbors. "Near a road" means within 2 cells and "next to a road" means within 1 (Manhattan distance):

```
Empty cell, road within 3 cells (base rate, times growth rate):
  Residential 0.005  x2 near a road, x1.5 with 2+ residential neighbors,
                     x1.3 with a commercial neighbor, x0.3 with 2+ industrial
                     neighbors, x1.5 if value > 60, x0.5 if value < 30
  Commercial  0.003  x3 next to a road, x2 with 2+ residential neighbors,
                     x2 if value > 70, x0.5 with 3+ commercial neighbors
  Industrial  0.002  x2 next to a road, x2 if value < 40, x0.2 if value > 70,
                     x1.5 with an industrial neighbor
  Park        0.0005 x3 with 3+ residential neighbors and value > 50
```

- **Population.** Occupied zones grow by a zone-specific rate (residential 2%, commercial 1.5%, industrial 1% per step, all times the growth rate; residential rises with nearby commercial cells, commercial with nearby residential cells, and industrial rises 1.5x next to a road). Industrial neighbors push residential growth down. Density rises by one level with 1% chance when population and land value are high enough.
- **Gentrification.** A residential cell of density 2 or less with land value above 80 turns commercial with 0.3% chance per step.
- **Decay.** A zone with no population gains decay. At decay above 0.9 it becomes a ruin with 0.5% chance per step. Population lowers decay.
- **Reclaim.** A ruin with 2 or more residential or commercial neighbors becomes residential with 0.3% chance per step.
- **Roads.** Empty cells more than 3 cells from a road, next to a residential cell, become road with a small chance. On 5% of steps, times the growth rate, the model samples 20 random cells and picks the zone cell with the highest population times road distance (it needs a score above 10). It then builds a road toward that cell from the nearest road within 5 cells.

**Presets (6):** Medieval Town, Suburban Sprawl, Dense Metropolis, Coastal City, Post-Apocalyptic Regrowth, Megacity.

| Preset | Initial Layout |
|--------|----------------|
| Medieval Town | Small central market square with roads and a few buildings around it |
| Suburban Sprawl | Road grid with scattered houses and up to three short strip malls |
| Dense Metropolis | Radial and ring roads, dense commercial core, residential ring |
| Coastal City | Water on the right, harbor industry, coast road, inland town center |
| Post-Apocalyptic Regrowth | Ruined grid city with small survivor settlements; roads decay into ruins over time |
| Megacity | Several city centers joined by roads, grid overlay, industry on the edges |

**View modes (4, cycle with `v`):**
1. **Zone map** — zone types shown as colored Unicode characters (▪ residential, ◆ commercial, ▲ industrial, ♣ park, · road, ~ water, ░ ruin)
2. **Land value heatmap** — intensity-mapped gradient showing economic geography
3. **Traffic heatmap** — congestion visualization revealing bottlenecks
4. **Population density** — where people actually live

**Controls:** `Space`=play/pause, `n`=step, `v`=cycle views, `+/-`=growth rate (x1.3 or /1.3, range 0.1-5), `p`=place a park near the center, `r`=reset, `R` or `m`=menu, `q` or `Esc`=exit.

**What to look for.** In Medieval Town, the street network grows outward from the market, with commercial zones along the main roads and housing filling in behind. Suburban Sprawl spreads low-density housing far from the center. Dense Metropolis has a land-value peak in the commercial core, and gentrification converts residential edges to commercial. Coastal City concentrates growth along the shore, with industry kept near the harbor. In Post-Apocalyptic Regrowth, survivor clusters slowly reclaim ruins. Megacity has several competing centers. In the traffic view, watch roads saturate near populated zones. In the land value view, watch industry push values down and parks and commerce push them up.

**References.**
- Alonso, W. *Location and Land Use*. Harvard University Press, 1964.
- Batty, M. "The Size, Scale, and Shape of Cities." *Science*, 319(5864), 769-771, 2008. https://doi.org/10.1126/science.1151419
- Portugali, J. *Self-Organization and the City*. Springer, 2000. https://doi.org/10.1007/978-3-662-04099-7
- Waddell, P. "UrbanSim: Modeling Urban Development for Land Use, Transportation, and Environmental Planning." *Journal of the American Planning Association*, 68(3), 297-314, 2002. https://doi.org/10.1080/01944360208976274

---


## Termite Mound Construction & Stigmergy

**Background.** Termite mounds are among the most impressive examples of emergent architecture in biology. Individual termites are simple agents with no blueprint or central coordinator, yet colonies of *Macrotermes* and *Amitermes* construct elaborate mounds with ventilation shafts, brood chambers, fungus gardens, and royal chambers — structures that can reach several meters in height. The key mechanism is *stigmergy* (Grassé, 1959): indirect coordination where an agent's modification of the environment stimulates further work by other agents. A termite deposits a soil pellet laced with pheromone; the pheromone attracts other termites to deposit nearby, creating a positive feedback loop that bootstraps pillars, arches, and walls from purely local rules.

**Formulation.** The simulation runs on a 2D grid with three pheromone layers (build, dig, trail) and eight material types. Each tick proceeds in two phases:

**Phase 1 — Pheromone diffusion and evaporation:**

```
For each pheromone layer P ∈ {build, dig, trail}:
  P'(r,c) = P(r,c) × (1 − evap_rate)
           + diffuse_rate × (avg_neighbors(P, r, c) − P(r,c))
  P'(r,c) = clamp(P'(r,c), 0, 1)
```

where `avg_neighbors` averages the 4-connected (von Neumann) neighbor values. Default evaporation rate is 0.02 and diffusion rate is 0.15 (presets change them: see the code). Trail pheromone evaporates 1.5× faster to prevent path saturation.

**Phase 2 — Termite agent actions:** Each termite looks at its 8 neighboring cells and moves to the one with the best score. The score depends on its role, plus random noise (up to 0.8) and a small bonus (0.2) for moving closer to its home cell:

```
Builder, or worker carrying soil:
  carrying: 3.0 × ph_build, plus 0.3 per adjacent soil or wall cell
  empty:    2.0 if the cell is soil, plus 0.5 × ph_trail
Digger:
  empty:    3.0 × ph_dig, plus 1.5 if the cell is soil
  carrying: 2.0 × ph_build − 1.0 × ph_dig
Worker (empty):  1.5 × ph_trail
Soldier:         1.0 × ph_trail, plus 1.0 for air cells next to soil or wall
Fungus tender:   3.0 on fungus, 2.0 on chamber, plus 0.5 × ph_dig
```

After moving, each termite leaves 0.1 trail pheromone behind and acts:

- **Builders and workers** pick up soil within 3 rows of the surface. They deposit it as wall on an air cell where build pheromone exceeds the threshold. The deposit adds 0.3 build pheromone, which reinforces the spot (the stigmergy loop).
- **Diggers** turn soil into chamber where dig pheromone exceeds its threshold and pick up the soil. They add 0.2 dig pheromone. A carrying digger drops wall at a build site or at least 2 rows above the surface.
- **Soldiers** turn soil next to air or chamber into wall with 10% chance per step.
- **Fungus tenders** turn chamber cells with at least 3 soil or wall neighbors into fungus garden with 15% chance per step.
- **Queens** stay put, add build pheromone (0.05) on their own cell and dig pheromone (0.03) below it, and mark their cell as royal chamber.

**Structural support rule.** Builders and diggers can only drop material next to existing soil, wall, or surface cells (workers and builders may also drop it at or below the surface row). This prevents floating construction.

**Ventilation shafts (cathedral preset).** The preset seeds a column of build pheromone above the surface and a dig zone below it. Every 20 ticks, wall cells in the central five columns (up to 12 rows above the surface) turn into tunnel with 3% chance if a chamber or air cell lies within 3 rows below. These are open vertical channels, like the chimneys in real *Macrotermes* mounds.

**Magnetic alignment (magnetic preset).** The preset seeds a narrow build band and a wide dig zone. Each tick, build pheromone more than 2 columns from the center is multiplied by 0.95. This suppresses sideways growth and gives a thin wedge, like the compass-aligned mounds of *Amitermes meridionalis*.

**Mega-colony multi-queen structure.** The Mega-Colony preset places 3-5 colony centers across the grid, each with its own queen and termites. The mounds grow independently.

**Presets (6):**

| Preset | Character | Initial Configuration |
|--------|-----------|----------------------|
| Cathedral Mound | Towering spire, ventilation shafts | Builders clustered at center, vertical build-pheromone column |
| Magnetic Termite Mound | Flat N-S aligned wedge | Narrow build band, wide E-W dig zone |
| Underground Network | Subsurface tunnels, foraging galleries | Mostly diggers below surface, radial dig-pheromone gradient |
| Fungus Farming Colony | Humidity-controlled fungus chambers | Mixed roles with 30% fungus tenders, subsurface dig seeds |
| Defensive Fortress | Thick outer walls, soldier patrols | Ring of build pheromone for walls, a dig zone inside, 20% soldiers |
| Mega-Colony | Multi-queen, 3-5 mounds | Multiple colony centers with independent populations |

**View modes (3, cycle with `v`):**
1. **Mound** — material rendering with termites overlaid (♛ magenta = queen, ● red = soldier, ◆ green = fungus tender, ◇ yellow = termite carrying soil, dim · = other termites)
2. **Pheromone** — build pheromone (yellow) vs dig pheromone (blue) concentration heatmap, showing the invisible chemical landscape guiding construction
3. **Structure** — walls with two or more adjacent air, chamber, or tunnel cells drawn bold (exterior), other walls drawn lighter (interior), plus chambers, fungus, and tunnels

**Controls:** `Space`=play/pause, `n`=step, `v`=cycle views, `+/-`=steps per frame (1-20), `r`=reset, `R`=menu, `q`=exit.

**What to look for.** In Cathedral Mound, walls rise above the surface where builders follow the build pheromone, and vertical tunnels open inside them every 20 ticks. Magnetic Termite Mound builds a flat, narrow shape. In the pheromone view, the suppressed build zone explains why. Underground Network is best in the structure view: dug chambers spread out from the center as diggers follow the dig pheromone. In Fungus Farming Colony, fungus tenders turn dug chambers into fungus garden cells (♣). Defensive Fortress thickens a ring of wall as builders and soldiers work the perimeter. Mega-Colony grows several independent mounds side by side. Switch between the three views often. The pheromone view shows the signals that drive all the visible building.

**References.**
- Grassé, P.-P. "La reconstruction du nid et les coordinations interindividuelles chez *Bellicositermes natalensis* et *Cubitermes* sp. La théorie de la stigmergie." *Insectes Sociaux*, 6(1), 41-80, 1959. https://doi.org/10.1007/BF02223791
- Camazine, S. et al. *Self-Organization in Biological Systems*. Princeton University Press, 2001.
- Bonabeau, E., Dorigo, M. & Theraulaz, G. *Swarm Intelligence: From Natural to Artificial Systems*. Oxford University Press, 1999.
- Turner, J. S. *The Extended Organism: The Physiology of Animal-Built Structures*. Harvard University Press, 2000.

---


## Deep Sea Hydrothermal Vent Ecosystem

**Background.** Hydrothermal vents are fissures on the ocean floor where geothermally heated water erupts into near-freezing deep-ocean seawater. Discovered in 1977 along the Galápagos Rift, these systems host some of Earth's most extreme ecosystems — thriving without sunlight through chemosynthesis, where microbes oxidize hydrogen sulfide (H₂S) and other reduced chemicals as their primary energy source. "Black smokers" emit superheated fluid (up to 400°C) laden with metal sulfides that precipitate on contact with 2°C ambient water, gradually building towering chimney structures. The surrounding fauna — giant tube worms (*Riftia pachyptila*), vent shrimp (*Rimicaris exoculata*), mussels (*Bathymodiolus*), crabs, and octopuses — form a food web rooted entirely in chemosynthetic bacterial production. This simulation models the coupled thermal, chemical, geological, and ecological dynamics of a deep-sea vent field.

**Formulation.** The simulation operates on a 2D grid representing a vertical cross-section of the ocean floor and water column. Three continuous scalar fields evolve each timestep:

```
Temperature field T(x,y):
  T(t+1) = T(t) + D_T · ∇²T  +  buoyancy advection  +  vent injection
  where D_T = thermal diffusion coefficient
  Buoyancy: hot fluid rises at rate proportional to (T - T_ambient)
  Vent sources inject T_vent at chimney positions each tick

H₂S concentration field S(x,y):
  S(t+1) = S(t) + D_S · ∇²S  -  λ_S · S  +  vent injection
  where λ_S = decay/oxidation rate, D_S = diffusion coefficient

Mineral concentration field M(x,y):
  M(t+1) = M(t) + D_M · ∇²M  -  λ_M · M  +  vent injection
  Minerals precipitate into solid chimney when M > threshold AND T gradient is steep
```

**Chimney growth.** When dissolved mineral concentration exceeds a precipitation threshold at a cell where hot vent fluid meets cold water (steep temperature gradient), mineral material solidifies — converting the cell to chimney rock. This positive feedback loop (chimney constrains flow → concentrates minerals → more precipitation) produces the characteristic tall, narrow chimney morphology of black smokers.

**Ocean current drift.** A global current vector rotates slowly over time, advecting the temperature, H₂S, and mineral plume fields laterally. This disperses plume material downstream and transports larvae between vent sites.

**Tectonic events.** At a configurable rate, the simulation generates tectonic disturbances: new fissures open (activating new vent sources), existing chimneys collapse (converting chimney cells back to water/rubble), and vent activity waxes or wanes (modulating injection temperature and chemical flux).

**Fauna model.** Six organism types inhabit the vent field, each with type-specific behavior:

| Organism | Role | Behavior |
|----------|------|----------|
| Chemosynthetic microbes | Primary producer | Reproduce in high-H₂S, high-temperature zones; metabolize H₂S for energy; thermophilic (prefer 40–120°C) |
| Tube worms | Sessile symbiont | Anchor near vents; harbor internal chemosynthetic bacteria; grow/shrink based on local H₂S supply |
| Mussels | Filter feeder | Cluster at vent bases; filter microbes from water; sessile once established |
| Shrimp | Mobile grazer | Chemotax toward H₂S gradients; graze on microbe colonies; avoid extreme heat |
| Crabs | Scavenger | Roam the seafloor; consume microbes, mussels, and detritus |
| Octopuses | Apex predator | Rare; hunt crabs and shrimp; roam large territories |

Organisms have energy budgets, reproduce when energy exceeds a threshold (with a carrying-capacity check), and die when energy reaches zero or temperature exceeds their tolerance. Some creatures exhibit bioluminescence — rendered as flickering cyan highlights.

**Presets (6):**

| Preset | Character | Initial Configuration |
|--------|-----------|----------------------|
| Classic Black Smoker | Tall iron-sulfide chimneys, 350°C fluid, dark mineral clouds | 2–3 chimneys, fast precipitation, full fauna suite |
| White Smoker Garden | Lower temperature (150–250°C), barium/calcium deposits, lush fauna | Many small vents, slower chimney growth, dense tube worm colonies |
| Lost City (Alkaline Vents) | Tall carbonate towers, warm (40–90°C), alkaline, hydrogen-rich | Tall initial structures, low H₂S, high mineral content, slow chemistry |
| Mid-Ocean Ridge | Active spreading center, multiple vent fields | High tectonic rate, scattered vent clusters, frequent fissure events |
| Vent Field Colonization | Pioneer species colonize newly opened vents | Bare basalt start, vents activate gradually, fauna arrives via larval drift |
| Dying Vent Succession | Waning vent activity, community collapse | Initially active vents with established fauna; activity declines over time |

**View modes (3, cycle with `v`):**
1. **Ecosystem** — full terrain rendering with chimney structures, fauna icons, thermal plume coloring (red/yellow for hot fluid), and bioluminescent creature highlights against a dark ocean background
2. **Thermal heatmap** — temperature field visualization from deep blue (2°C ambient) through cyan, green, yellow to bright red/white (350°C+ vent fluid)
3. **Chemistry** — H₂S concentration (green) and dissolved mineral concentration (yellow/brown) overlaid, showing the chemical landscape that drives both chimney growth and the food web

**Controls:** `Space`=play/pause, `n`=step, `v`=cycle views, `+/-`=simulation speed, `r`=reset, `R`=menu, `q`=exit.

**What to look for.** In Classic Black Smoker, watch chimney structures grow upward from the seafloor as mineral precipitation builds layer by layer — the chimneys constrain the plume, concentrating minerals and accelerating their own growth. Tube worms cluster in the warm zone just outside the lethal-temperature boundary, while shrimp swarm through the H₂S gradient. Switch to the thermal view to see the buoyant plume billow upward and drift with the current. White Smoker Garden produces a gentler, more biologically productive scene — lower temperatures mean a wider habitable zone and denser fauna. Lost City is visually distinct: tall, pale carbonate towers with warm (not superheated) fluid and a different chemical regime. Mid-Ocean Ridge is the most dynamic — frequent tectonic events open new fissures and collapse existing chimneys, forcing fauna to migrate. Vent Field Colonization shows ecological succession in action: microbes arrive first, followed by tube worms, then grazers and predators. Dying Vent Succession is the inverse — watch the community unravel as chemical energy dwindles, with apex predators disappearing first and chemosynthetic microbes persisting longest.

**References.**
- Van Dover, C. L. *The Ecology of Deep-Sea Hydrothermal Vents*. Princeton University Press, 2000.
- Kelley, D. S. et al. "An off-axis hydrothermal vent field near the Mid-Atlantic Ridge at 30°N." *Nature*, 412, 145–149, 2001. https://doi.org/10.1038/35084000
- Luther, G. W. et al. "Chemical speciation drives hydrothermal vent ecology." *Nature*, 410, 813–816, 2001. https://doi.org/10.1038/35071069
- Corliss, J. B. et al. "Submarine thermal springs on the Galápagos Rift." *Science*, 203(4385), 1073–1083, 1979. https://doi.org/10.1126/science.203.4385.1073


---


## Stellar Lifecycle & Supernova

**Background.** Stars are the fundamental engines of the universe — forging elements in their cores, sculpting galaxies with their radiation and winds, and seeding interstellar space with heavy elements when they die. A star's life is determined almost entirely by its birth mass: low-mass stars burn hydrogen slowly for billions of years and fade as white dwarfs, while massive stars blaze through their fuel in millions of years and detonate as core-collapse supernovae, leaving neutron stars or black holes. The Hertzsprung-Russell diagram — plotting stellar luminosity against surface temperature — reveals the evolutionary tracks stars follow from birth to death. This mode follows stars from gas cloud collapse to remnant. Supernova shockwaves can trigger new star formation, so the cycle can sustain itself.

**Formulation.** Each star is an agent with mass, position, velocity, hydrogen fuel fraction, surface temperature, luminosity, radius, and a 6-element fusion shell composition vector. The key physical relations:

```
Mass-luminosity relation (main sequence):
  L = M^3.5       (in solar units)

Main sequence hydrogen burning (per tick, times the time scale):
  fuel -= 0.001 · M^2.5     (massive stars die young)

Surface temperature scaling:
  T = 5778 · M^{0.505}  K

Radius scaling:
  R = M^{0.8}        (main sequence)
  R = M^{0.8} · 2.5  (subgiant)
  R = M^{0.8} · 10   (red giant)
  R = M^{0.8} · 20   (supergiant)
```

**Stellar evolution stages.** Stars pass through up to 11 stages depending on mass:

| Stage | Trigger | Properties |
|-------|---------|------------|
| Gas Cloud | Initial state | Low temperature (100 K + 50 K per M☉), extended radius, near-zero luminosity |
| Protostar | Random collapse in dense gas or near a shockwave, or age above 20 | Warming (2000 K + 500 K per M☉) |
| Main Sequence | Age > 30 | Hydrogen fusion; L, T, R from mass relations |
| Subgiant | Fuel ≤ 10% | Radius × 2.5, luminosity × 2, T × 0.85 |
| Red Giant | Fuel ≤ 2%, M ≤ 8 M☉ | Radius × 10, luminosity × 5, T × 0.55 (at least 3000 K) |
| Supergiant | Fuel ≤ 2%, M > 8 M☉ | Radius × 20, luminosity × 10, T × 0.45 (at least 3500 K), onion-shell fusion |
| Supernova | Supergiant fuel exhausted | Luminosity 10⁶ × M, expanding shockwave; lasts 15 ticks |
| Planetary Nebula | Red giant fuel exhausted | Expanding shell of ejected gas |
| White Dwarf | Nebula radius > 8 | M = min(1.4, 0.6 × M) M☉, slowly cooling, adds gas nearby |
| Neutron Star | Post-supernova, initial M ≤ 25 M☉ | M = 1.4 M☉, tiny radius, extreme temperature |
| Black Hole | Post-supernova, initial M > 25 M☉ | M = 0.3 × M_initial, zero luminosity |

**Hydrogen burning.** On the main sequence, fuel decreases at a rate proportional to M^{2.5}, so a 20 M☉ star burns fuel about 1800× faster than a 1 M☉ star. The fuel fraction and stage set the shell composition for the core view: helium builds up first, then heavier layers appear in massive stars (H → He → C → O → Si → Fe).

**Supernova feedback.** When a supergiant exhausts its fuel, it detonates as a core-collapse supernova:
1. A shockwave is created at the star's position with strength min(1, initial mass / 20)
2. The shockwave expands at 1.2 cells/tick, decaying in strength by 8% per tick
3. Each tick, with probability 0.02 × strength, a random point on the shockwave ring becomes a new gas-cloud star if the gas density there exceeds 0.3. Gas-cloud stars near the ring also collapse into protostars more easily
4. After 15 ticks the remnant forms and ejects gas into a 6-cell radius

This creates a self-sustaining cycle: supernovae compress gas → new stars form → massive ones evolve fast → more supernovae.

**Binary mass transfer.** Each preset pairs stars up with a set probability (stars in a pair start 2 cells apart). While one partner is a red giant or supergiant and the other is on the main sequence (or is a white dwarf or neutron star), mass moves from the giant to its companion at 0.005 per tick.

**Wolf-Rayet winds.** Wind strength = wind scale × M / 10. A star with wind strength above 2.0 loses mass during the supergiant phase (0.01 × wind strength per tick, down to half its mass) before it explodes. The Wolf-Rayet preset uses a wind scale of 5.

**Gas dynamics.** A 2D density grid represents the interstellar medium. Gas clouds are seeded as 3-8 circular regions with a quadratic falloff. Every 5 ticks, each cell keeps 92% of its gas and takes 2% of each 4-neighbor's gas, so the gas slowly spreads and fades. Supernova ejecta and planetary nebula shedding inject fresh gas, maintaining the reservoir for future star formation.

**Spectral classification.** Stars are assigned OBAFGKM spectral class from surface temperature:

| Class | Temperature | Color (terminal) |
|-------|-------------|-------------------|
| O | > 30,000 K | Cyan/blue, bold |
| B | 10,000–30,000 K | Cyan/blue, bold |
| A | 7,500–10,000 K | White, bold |
| F | 6,000–7,500 K | White, bold |
| G | 5,200–6,000 K | Yellow, bold |
| K | 3,700–5,200 K | Red |
| M | < 3,700 K | Red |

**Presets (6):**

| Preset | Character | Initial Configuration |
|--------|-----------|----------------------|
| Open Cluster Nursery | Young stellar nursery — gas clouds collapsing into protostars | Up to 60 stars (0.3–8 M☉), dense gas (0.6), all start as gas clouds, pairing probability 0.1 |
| Red Giant Graveyard | Aging cluster of evolved stars shedding nebulae | Up to 40 stars (0.8–5 M☉), sparse gas (0.15), start as red giants with 2–15% fuel remaining |
| Supernova Chain Reaction | Massive stars near end of life — cascading detonations | Up to 50 stars (5–40 M☉), moderate gas (0.4), start as supergiants with 1–8% fuel |
| Binary Star Mass Transfer | Close binary pairs exchanging mass | Up to 30 stars (1–15 M☉), sparse gas (0.1), pairing probability 0.8, main sequence start |
| Globular Cluster Evolution | Dense old cluster, stars at various ages | Up to 120 stars (0.2–3 M☉), minimal gas (0.05), main sequence start with varied ages, pairing probability 0.15 |
| Wolf-Rayet Wind Bubble | Ultra-massive stars with strong winds | Up to 25 stars (20–80 M☉), moderate gas (0.3), wind scale 5, main sequence start, pairing probability 0.2 |

**View modes (3, cycle with `v`):**
1. **Star Field** — spatial view of the stellar nursery: gas cloud density rendered as ASCII art (`.:-=+*#%@`), stars as colored glyphs by stage (~ gas cloud, + protostar, * main sequence, O red giant, # supergiant, @ supernova, % planetary nebula, . white dwarf, : neutron star, o black hole), expanding supernova explosion rings, expanding nebula shells, binary link markers, and shockwave fronts
2. **HR Diagram** — live Hertzsprung-Russell plot with log₁₀(luminosity) on the Y axis (10^{-4} to 10^{+7} L☉) and log₁₀(temperature) on the X axis (reversed: hot O stars at left, cool M stars at right), dotted main sequence guide line, spectral class labels along the temperature axis, stars plotted as colored glyphs by evolutionary stage, and a legend panel
3. **Core Cross-Section** — concentric onion-layer visualization of the selected star's internal fusion shells (H → He → C → O → Si → Fe), drawn as filled circles with aspect-ratio correction, color-coded by element, with a composition legend showing relative shell fractions, star properties panel (mass, stage, spectral class, temperature, luminosity, radius, age, fuel), and an energy output bar indicator

Star counts depend on the terminal size. Masses follow a power law that favors low-mass stars. Pairing stops at the first failed roll, so the number of pairs is small.

**Controls:** `Space`=play/pause, `v`=cycle views, `s`=select next star, `+/-`=time scale (0.5-5), `r`=back to the preset menu, `q`=exit. In the menu, `Enter` or `Space` starts a preset.

**What to look for.** In Open Cluster Nursery, watch the gas clouds flicker and collapse one by one into protostars (+ symbols), then ignite as main sequence stars (*) — the most massive ones will be blue (O/B class) at the hot end of the HR diagram, while the numerous low-mass stars cluster as red M dwarfs at the cool end. Switch to the HR diagram to see the population track the classic main sequence band. As time progresses, the most massive stars peel off the main sequence first, swelling into red giants (O) and supergiants (#) — watch them migrate to the upper-right of the HR diagram. When a supergiant detonates (@), the expanding shockwave ring compresses surrounding gas and triggers a new burst of star formation. In Supernova Chain Reaction, the chain detonations are particularly dramatic — each explosion seeds gas that enables the next generation. Switch to Core Cross-Section view and cycle through stars with `s` to see the onion-layer structure of a massive supergiant: hydrogen envelope surrounding helium, carbon, oxygen, silicon, and (just before detonation) an inert iron core. Binary Star Mass Transfer shows pairs linked by dashes. The giant loses mass to its companion. Wolf-Rayet Wind Bubble has the most massive stars. Their mass erodes in the supergiant phase before they explode.

**References.**
- Kippenhahn, R., Weigert, A. & Weiss, A. *Stellar Structure and Evolution*. 2nd ed., Springer, 2012. https://doi.org/10.1007/978-3-642-30304-3
- Salpeter, E. E. "The luminosity function and stellar evolution." *Astrophysical Journal*, 121, 161–167, 1955. https://doi.org/10.1086/145971
- Woosley, S. E. & Weaver, T. A. "The evolution and explosion of massive stars." *Reviews of Modern Physics*, 74(4), 1015–1071, 2002. https://doi.org/10.1103/RevModPhys.74.1015
- Hertzsprung, E. "Über die Sterne der Unterabteilungen c und ac." *Astronomische Nachrichten*, 179(24), 373–380, 1909. https://doi.org/10.1002/asna.19091792402


---


## Tide Pool & Intertidal Ecosystem

**Background.** The rocky intertidal zone — the narrow band of shore between high and low tide marks — is one of ecology's most studied natural laboratories. Twice daily, the tide transforms this strip from a wave-battered submarine habitat into a sun-baked, desiccating terrestrial one. Species survive by partitioning the shore into vertical zones based on their tolerance to exposure: barnacles and limpets cement themselves high where few competitors survive the drying, mussels dominate the mid-zone in dense beds, sea stars patrol below as keystone predators, and kelp forests anchor the permanently wet low zone. Paine's (1966) classic removal experiments showed that a single predator — the ochre sea star *Pisaster ochraceus* — prevents competitive exclusion by mussels, maintaining the species diversity of the entire community. Connell (1972) demonstrated that the upper limits of species distributions are set by physical stress (desiccation, heat), while lower limits are set by biotic interactions (predation, competition). This simulation models these dual gradients — physical stress from above, biological pressure from below — driven by the rhythmic pulse of a sinusoidal tide.

**Formulation.** The simulation operates on a 2D grid representing a vertical rocky shore cross-section, with elevation increasing upward (row 0 = spray zone, row N = subtidal). The tide is modeled as a sinusoidal oscillation:

```
Tide level (0–1):
  L(t) = 0.5 + A · sin(2πt / T)

where:
  A = tidal amplitude (fraction of vertical range, 0.20–0.45)
  T = tidal period (180–300 ticks per full cycle)

Water line row:
  W(t) = (1 - L(t)) · N_rows

Wave surge noise:
  δ(t) = 0.03·sin(0.7t) + 0.02·sin(1.3t)

Final level:
  L_eff(t) = clamp(L(t) + δ(t), 0, 1)
```

The shore is divided into 5 zonation bands computed from terminal height:

| Zone | Rows | Ecological Character |
|------|------|---------------------|
| Spray | 0–10% | Splashed but rarely submerged; lichens, cyanobacteria |
| High Intertidal | 10–30% | Brief submersion at high tide; barnacles, limpets, periwinkles |
| Mid Intertidal | 30–55% | Alternating exposure/submersion; mussels, anemones, sea stars |
| Low Intertidal | 55–80% | Mostly submerged; kelp, urchins, hermit crabs |
| Subtidal | 80–100% | Permanently submerged; full marine community |

**Terrain.** The terrain is rock with two special features: **tide pools** (depressions that retain water at low tide, concentrated in mid/low zones) and **sand patches** (in low/subtidal, avoided by most mobile organisms except hermit crabs). Algae grows on wet, illuminated rock surfaces.

**Physical stress fields.** Two scalar fields — temperature and moisture — are updated per cell each tick:

```
If submerged or in tide pool:
  temp(r,c)  ← max(0, temp - 0.05)         (cooling)
  moist(r,c) ← min(1, moist + 0.1)         (wetting)

If exposed:
  elev = 1 - r/N                            (higher = more exposed)
  temp(r,c)  ← min(1, temp + 0.02·(1+elev)) (heating)
  moist(r,c) ← max(0, moist - 0.03·(1+elev))(drying)

Splash zone (up to 5% of rows above waterline):
  30% chance per cell: moist += 0.05        (spray moisture)
```

**Algae dynamics.** Algae density (0–1 per cell) grows on rock and pool tiles:

```
growth = 0.005 · light(r) · moisture(r,c)
  where light(r) = max(0.1, 1 - r/(2·N))

Decay if moisture < 0.2: algae -= 0.01
Rock becomes algae-covered at density > 0.3, reverts at < 0.1
```

Grazers (urchins eat up to 0.1/tick, limpets up to 0.05/tick) keep algae in check.

**Species ecology.** Eight species in two categories, sessile (attached to rock) and mobile. The "Preferred Zone" is where each species is placed at the start. "Exposed cost" is the energy lost per tick at low tide:

| Species | Type | Preferred Zone | Feeding | Exposed cost | Special Mechanic |
|---------|------|---------------|---------|--------------|-----------------|
| Barnacle | Sessile | High | Filter feeds when submerged (+0.01/tick) | -0.005 energy | Eaten by sea stars |
| Mussel | Sessile | Mid | Filter feeds when submerged (+0.012/tick) | -0.004 energy | Grows in size; eaten by sea stars |
| Anemone | Sessile | Mid-Low | Filter feeds when submerged (+0.008/tick) | -0.006 energy | Can sit in tide pools |
| Kelp | Sessile | Low-Subtidal | Photosynthesis when submerged (+0.015 × light) | -0.01 energy, +0.04 stress | Grows in size; grazed by urchins |
| Limpet | Mobile | High-Mid | Grazes algae (0.05/tick) | -0.001 energy, +0.003 stress | Moves even when exposed |
| Sea Star | Mobile | Mid-Low | Eats mussels and barnacles on its cell when submerged (-0.3 prey energy, +0.15 own) | -0.003 energy, +0.015 stress | Moves only when submerged |
| Urchin | Mobile | Low-Subtidal | Grazes algae (0.1/tick) and kelp (-0.1 kelp energy) | -0.003 energy, +0.015 stress | Moves only when submerged |
| Hermit Crab | Mobile | Mid-Low | Scavenges (+0.003/tick) | -0.003 energy, +0.015 stress | Swaps shells with empty shells; can cross sand |

Sessile organisms gain stress only when exposed, at (1 - moisture) × 0.02 + temperature × 0.015 per tick. All organisms lose stress when submerged.

**Organism lifecycle.** All organisms have energy, age, and stress (0-1). Death occurs when energy ≤ 0, stress ≥ 1.0, or age exceeds the lifespan (2000 ticks for sessile, 3000 for mobile). Reproduction needs energy above 1.5 (sessile, 1% chance/tick) or 1.6 (mobile, 0.8% chance/tick), and places a new individual in an adjacent cell. Sessile offspring need an unoccupied rock or pool cell.

**Hermit crab vacancy chains.** Empty shells are tracked as (row, col, size) tuples. Each tick, a hermit crab looks for empty shells within one cell. If one is larger than its own, the crab swaps and leaves its old shell at its position. Dead crabs release their shells. A new crab takes a random empty shell, or gets a small 0.2 shell if none exist. The Hermit Crab Shell Economy preset starts with 40 crabs and 20 empty shells.

**Sea star wasting disease.** In the Sea Star Wasting Event preset, all sea stars start with stress 0.4-0.7 and gain +0.005 stress per tick. Above stress 0.7, they also lose 0.02 energy per tick. As stars die, predation on mussels and barnacles drops, and the mussels can spread through the mid zone. The preset is modeled on the 2013-2015 sea star wasting epidemic on the Pacific coast.

**Presets (6):**

| Preset | Character | Initial Configuration |
|--------|-----------|----------------------|
| Pacific Rocky Shore | Temperate intertidal with full zonation | Up to 60 barnacles, 40 mussels, 25 anemones, 30 kelp, 20 limpets, 15 sea stars, 20 urchins, 15 hermit crabs; tide A=0.35, T=240 |
| Tropical Coral Flat | Shallow flat with a small tidal range | A=0.20, T=300; more urchins (35) and anemones (40), fewer mussels (15) and kelp (15), 6-12 tide pools instead of 4-8 |
| Mussel Bed Dominance | Dense mussel beds competing for rock space | Up to 80 mussels in the mid zone, 30 barnacles, standard tide |
| Sea Star Wasting Event | Disease-stressed sea stars | 30 sea stars with initial stress 0.4-0.7 and ongoing disease stress, standard otherwise |
| Extreme Tidal Range | Bay of Fundy-scale tides | A=0.45, T=180; the water line sweeps a large part of the shore |
| Hermit Crab Shell Economy | Dense hermit crab population with vacancy chains | 40 hermit crabs, 20 empty shells of varying sizes, standard otherwise |

Starting counts are placement attempts. Some fail because the random cell is not suitable.

**View modes (3, cycle with `v`):**
1. **Shore** — spatial ecosystem rendering: rock (#), sand (:), tide pools (~), algae (./%); organisms as colored glyphs (^ barnacle, M mussel, * anemone, X sea star, o urchin, | kelp, @ hermit crab, n limpet); animated water line with > indicator; splash spray dots above waterline; zone labels (SPRAY/HIGH/MID/LOW/SUBTIDAL) on right edge; info bar showing sessile/mobile counts, shell count, and tide state
2. **Cross-Section** — 5 horizontal zonation bands showing zone name, characteristic species list, current population count, submersion state ([submerged]/[exposed]), and density bar chart; animated water level label moves vertically with tide
3. **Graphs** — tide level sparkline (Unicode block elements ▁▂▃▄▅▆▇█), per-species population time series with mini sparklines for top 4 species by current count, average community stress history; all graphs show last 200 ticks

**Controls:** `Space`=play/pause, `n`/`.`=step, `v`=cycle views, `+/-`=simulation speed, `r`=reset, `R`/`m`=menu, `q`=exit.

**What to look for.** In Pacific Rocky Shore, watch the tide rise and fall. As the water recedes, exposed organisms gain stress. Sea stars (X) feed only while submerged, so predation fronts move with the tide. The Graphs view shows stress rising and falling with the tide. In Mussel Bed Dominance, the mussels spread by budding into free rock cells. In Sea Star Wasting Event, the stars die off (X glyphs vanish) and the Graphs view shows what happens to the mussel count as predation drops. Extreme Tidal Range sweeps the water line across a large part of the screen each cycle. Hermit Crab Shell Economy is best in the Shore view: follow the @ symbols as they swap shells. Tropical Coral Flat has a gentle tide, so exposure stress is smaller.

**References.**
- Connell, J. H. "Community interactions on marine rocky intertidal shores." *Annual Review of Ecology and Systematics*, 3, 169–192, 1972. https://doi.org/10.1146/annurev.es.03.110172.001125
- Paine, R. T. "Food web complexity and species diversity." *The American Naturalist*, 100(910), 65–75, 1966. https://doi.org/10.1086/282400
- Paine, R. T. "Intertidal community structure: experimental studies on the relationship between a dominant competitor and its principal predator." *Oecologia*, 15, 93–120, 1974. https://doi.org/10.1007/BF00345739
- Menge, B. A. "Organization of the New England rocky intertidal community: role of predation, competition, and environmental heterogeneity." *Ecological Monographs*, 46(4), 355–393, 1976. https://doi.org/10.2307/1942563
- Denny, M. W. & Wethey, D. S. "Physical processes that generate patterns in marine communities." In *Marine Community Ecology* (eds. Bertness, M. D. et al.), 3–37, Sinauer, 2001.
- Lewis, J. R. *The Ecology of Rocky Shores*. English Universities Press, 1964.

---

## Spider Orb Web Construction & Prey Capture

**Background.** Orb-weaving spiders (family Araneidae) construct geometrically regular webs that are marvels of biological engineering — radial frame threads provide structural support while sticky spiral threads capture prey. The spider sits at the hub or on a signal thread, reading vibrations transmitted through the silk network to detect, locate, and identify trapped prey. The mode generates a finished web at the start, then simulates prey hitting sticky threads, vibrations spreading through the silk, the spider rushing out to wrap prey, wind deforming the elastic web, and thread breakage and repair.

**Web structure.** The web is a graph of nodes and threads, generated all at once (the spider does not build it step by step):

```
1. Frame:    4 anchor nodes form a rectangular boundary (SILK_FRAME, strength=1.0, elasticity=0.3);
             each radius tip also connects to the nearest anchor
2. Radii:    N radial threads from the central hub to the tips (SILK_RADIAL, strength=0.8, elasticity=0.4)
             Intermediate nodes sit at regular intervals along each radius
3. Aux:      Rings of threads between neighboring radii, in the inner quarter of the web
             (SILK_AUX, strength=0.4, elasticity=0.2); a non-sticky scaffold
4. Sticky:   The same rings in the outer part (SILK_STICKY, strength=0.5, elasticity=0.8)
             Capture zone: prey stick on contact
```

The Cobweb Tangle Weaver preset adds up to 2 × N random sticky cross-threads between nodes less than half the web radius apart.

**Silk types.** Four silk types with distinct mechanical properties:

| Silk Type | Strength | Elasticity | Sticky | Role |
|-----------|----------|------------|--------|------|
| Frame | 1.0 | 0.3 | No | Structural boundary, anchors to environment |
| Radial | 0.8 | 0.4 | No | Structural spokes from hub to frame |
| Auxiliary | 0.4 | 0.2 | No | Inner scaffold spiral, spider walkway |
| Sticky | 0.5 | 0.8 | Yes | Outer capture spiral with glue droplets |

**Vibration propagation.** When prey struggles, it generates vibration at its capture node. Waves propagate through the thread adjacency graph:

```
Node vibration decay:   v(t+1) = v(t) × 0.85
Thread vibration decay: v(t+1) = v(t) × 0.80

Transfer per hop:
  attenuation = max(0.1, 1.0 - distance × 0.02)
  thread_vibration = max(current, source × 0.3 × attenuation)
  neighbor_vibration = max(current, transfer × 0.5)
```

The spider detects the node with maximum vibration (threshold > 0.05) and checks for trapped, unwrapped prey within distance 3 of that node.

**Prey mechanics.** Five insect types with distinct properties:

| Prey | Glyph | Struggle | Mass | Spawn Weight |
|------|-------|----------|------|--------------|
| Moth | m | 0.7 | 0.6 | 3 |
| Fly | f | 0.5 | 0.3 | 4 |
| Mosquito | : | 0.3 | 0.1 | 3 |
| Beetle | B | 0.9 | 0.8 | 1 |
| Butterfly | W | 0.4 | 0.4 | 1 |

Prey spawn at random screen edges, fly with a random walk, a slight pull toward the center, and wind drift, and stick to SILK_STICKY threads via point-to-segment collision (distance < 0.8). Trapped prey snap to the nearest thread node and generate an initial vibration burst of mass × 1.5. Struggle decays at ×0.995/tick; wrapping by the spider further suppresses it at ×0.9/tick.

**Wind physics.** Elastic spring model on the thread network:

```
Base wind:  wx = strength × sin(t × 0.02) × 0.5
            wy = strength × cos(t × 0.015) × 0.3

Gusts:      3% chance/tick, duration 10–40 ticks
            gust_strength = base × (1.5 + rand × 2.0)
            Storm preset: gust_strength × 2.0

Node forces:
  Wind:     v += wind × 0.01
  Restore:  v += (rest_pos - pos) × 0.05
  Spring:   F = k × stretch × direction / distance
            k = 0.02 × (1.0 + elasticity)
  Damping:  v × 0.85 each tick
```

**Thread degradation.** Threads break probabilistically based on accumulated stress:

```
Break probability:
  + 0.05 × (tension - strength) / strength    if tension > strength
  + 0.002                                      if storm preset
  + 0.001                                      if sticky silk and age > 500
  + 0.005                                      if already stressed
```

Threads enter STRESSED state when tension > 0.7 × strength. Broken threads are removed from the adjacency graph, blocking vibration propagation through that path.

**Spider AI.** State machine with energy and silk management:

| State | Behavior | Energy Cost |
|-------|----------|-------------|
| WAITING | At hub, monitors vibrations, regenerates (+0.002 energy, +0.05 silk/tick) | None |
| RUSHING | Moves toward trapped prey at speed min(1.5, dist×0.3) | -0.003/tick |
| WRAPPING | Wraps prey (+0.05 wrapped/tick, -0.3 silk/tick), suppresses struggle | -0.002/tick |
| REPAIRING | Moves to broken threads, repairs (-3.0 silk each, restored at 70% strength) | -0.002/tick |
| RESTING | Returns to hub, fast regeneration (+0.005 energy, +0.1 silk/tick) | None |

Energy < 0.1 forces RESTING state. A completed wrap counts as a capture, grants +0.2 energy, and records the angular zone (8 bins). The zone counts are kept but do not change the web.

**Presets (6):**

| Preset | Character | Configuration |
|--------|-----------|--------------|
| Garden Orb Weaver | Classic orb web, sheltered garden | 24 radii, 1.2 spiral spacing, no wind, prey rate 0.02 |
| Morning Dew Web | Calm dawn, dew on silk | Wind 0.01, prey rate 0.01, slow peaceful web |
| Storm Damage & Repair | Fierce gusts shred the web | Wind 0.5, gusts ×2, prey rate 0.015, frequent breakage |
| Prey Bonanza | Insect swarm overwhelms web | Prey rate 0.08, wind 0.05, rapid silk depletion |
| Cobweb Tangle Weaver | Irregular 3D tangle web | 40 radii, 0.8 spacing, extra random cross-threads, prey rate 0.025 |
| Golden Silk Orbweaver | Nephila-style giant web | Radius 0.48 of the smaller screen side (others 0.40), 32 radii, 150 starting silk, prey rate 0.03 |

**View modes (3, cycle with `v`):**
1. **Web Structure** — thread network drawn with Unicode line characters (`─│╲╱·`), junction dots at nodes, vibration ripples (`○` high / `∙` medium), prey glyphs color-coded (green free, red trapped, dim wrapped `●`), spider `◆` colored by state (green waiting, red rushing, yellow wrapping, cyan repairing), wind direction arrow with magnitude bar, spider state label
2. **Vibration Heatmap** — threads colored by vibration intensity (`·`=none, `░`=low, `▒`=medium, `▓`=high, `█`=peak), trapped prey as `◎`, spider as `◆`, legend bar
3. **Time-Series Graphs** — four sparkline graphs (Unicode block elements `▁▂▃▄▅▆▇█`) showing cumulative captures, web integrity %, silk reserves, and trapped prey count over last 200 ticks; stats summary with total captures, silk level, energy %, and current state

**Controls:** `Space`=play/pause, `n`/`.`=step, `v`=cycle views, `+/-`=simulation speed, `r`=reset, `R`/`m`=menu, `q`=exit.

**What to look for.** In Garden Orb Weaver, the spider waits at the hub while the web stays still. When a prey insect (colored green) drifts into a sticky spiral thread, it snaps to the nearest node and begins struggling — vibration ripples (`○∙`) radiate outward through the thread network. The spider turns red and rushes along the radial threads toward the trapped prey, then turns yellow while wrapping it in silk. Switch to Vibration Heatmap view to see wave propagation clearly — trapped prey appear as bright `◎` spots with `▓█` intensity fading outward through connected threads. Storm Damage & Repair has strong gusts. They deform the web, threads snap, and the spider repairs them with weaker silk. In the Graphs view, web integrity drops during gusts and recovers as the spider repairs. Prey Bonanza brings many insects, and wrapping drains the spider's silk and energy. Morning Dew Web has almost no wind and slow prey. Golden Silk Orbweaver has a larger web and more silk. Cobweb Tangle Weaver adds cross-threads in all directions, so vibrations take different paths.

**References.**
- Vollrath, F. "Spider webs and silks." *Scientific American*, 266(3), 70–76, 1992. https://doi.org/10.1038/scientificamerican0392-70
- Wirth, E. & Barth, F. G. "Forces in the spider orb web." *Journal of Comparative Physiology A*, 171, 359–371, 1992. https://doi.org/10.1007/BF00223966
- Masters, W. M. & Markl, H. "Vibration signal transmission in spider orb webs." *Science*, 213(4505), 363–365, 1981. https://doi.org/10.1126/science.213.4505.363
- Zschokke, S. & Vollrath, F. "Web construction patterns in a range of orb-weaving spiders (Araneae)." *European Journal of Entomology*, 92(3), 523–541, 1995.
- Ko, F. K. & Jovicic, J. "Modeling of mechanical properties and structural design of spider web." *Biomacromolecules*, 5(3), 780–785, 2004. https://doi.org/10.1021/bm0345099

---

## Deep-Sea Bioluminescent Abyss

**Background.** The deep ocean below 1000 meters — the bathypelagic, abyssopelagic, and hadal zones — is a world of perpetual darkness where nearly all ecological interactions are mediated through bioluminescence. Over 90% of organisms in the deep sea produce light for predation, defense, communication, or camouflage. This simulation models the light-based ecology of the abyssal zone, where anglerfish lure prey with bioluminescent escae, dragonfish hunt with red photophores invisible to most prey, giant squid use chromatophore countershading to match the ambient darkness, and disturbance of bioluminescent plankton triggers chain-reaction light cascades that propagate through the water column. Marine snow (organic detritus sinking from above) fuels the deep-sea food web, and hydrostatic pressure increases with depth, slowing creature metabolism.

**Formulation.** The simulation tracks three entity types: creatures (8 species), bioluminescent plankton, and marine snow particles. A 2D flash intensity map records light events for rendering.

```
Depth zones (row fraction → zone):
  0.00–0.20  Mesopelagic   (200–1000m,  ~100 atm)
  0.20–0.55  Bathypelagic   (1000–4000m, ~400 atm)
  0.55–0.80  Abyssopelagic  (4000–6000m, ~600 atm)
  0.80–1.00  Hadal          (6000m+,     ~1100 atm)

Metabolism factor (depth-dependent):
  metabolism_factor = max(0.3, 1.0 − depth_frac × 0.6)
  energy_cost/tick = base_metabolism × metabolism_factor × 0.15

Plankton cascade propagation (up to 3 rounds per tick):
  Creature movement disturbs plankton within radius (2.0 + creature_size)
  Disturbed plankton: brightness += 0.6, trigger_timer = 8 ticks
  Cascade: bright plankton (>0.3) trigger neighbors within distance 3.0
    cascade_strength = source_brightness × (1.0 − d/3.0) × 0.5
    Threshold: cascade_strength > 0.15 to propagate
  Brightness decay: ×0.85 per tick

Marine snow drift:
  dy = 0.15 + size × 0.1  (sinking)
  dx = drift + sin(t × 0.05 + x × 0.1) × 0.1  (sinusoidal wobble)

Flash map decay: ×0.7 per tick
```

**Creature species (8):**

| Species | Glyph | Role | Behavior |
|---------|-------|------|----------|
| Anglerfish | `§` | Lure ambush predator | Bioluminescent esca pulses (0.4 + 0.4×sin), lures lanternfish/hatchetfish within range 12; slow approach (0.03 accel) for ambush capture at distance < 1.5 |
| Giant Squid | `¶` | Active predator | Chromatophore countershading (brightness = 1.0 − depth×1.5), hunts creatures < 60% own size, flees dragonfish with ink cloud defense (radius 1.5, 30-tick duration, 40-tick cooldown) |
| Jellyfish | `~` | Passive drifter | Sinusoidal drift, rhythmic glow pulses (0.5 + 0.5×sin), feeds on plankton within radius 2.0 |
| Lanternfish | `°` | Prey fish (schooling) | Counterillumination in shallow depths, schools with same-type neighbors (cohesion within 8.0), fatally attracted to anglerfish lures (range 3–12), flees predators with panic flash |
| Hatchetfish | `◊` | Prey fish (schooling) | Same schooling/counterillumination behavior as lanternfish; distinct depth preference (0.1–0.4 depth fraction) |
| Dragonfish | `≈` | Red searchlight predator | Red photophores (invisible to prey) flash every 8 ticks, actively hunts lanternfish/hatchetfish/shrimp/jellyfish within radius 12 |
| Shrimp | `,` | Scavenger with defense | Bioluminescent vomit defense: 3×3 flash burst (intensity 0.4 per cell) when predator within 4.0, 20-tick cooldown; passive energy gain while idle |
| Tube Worm | `\|` | Sessile vent community | Immobile (speed 0), chemosynthetic energy from hydrothermal vents (0.5×strength when within vent radius), gentle pulse every 20 ticks |

**Predator-prey dynamics:**
- **Anglerfish lure attraction**: Prey fish (lanternfish, hatchetfish) are drawn toward anglerfish lure when brightness > 0.5 and distance 3–12, with acceleration proportional to lure brightness × 0.03. Once within 5.0, anglerfish switches to hunting state.
- **Giant squid hunting**: Targets creatures smaller than 60% of its own size within radius 10. Chromatophore camouflage reduces visibility at depth. Ink cloud deployed as defensive startle when fleeing threats.
- **Dragonfish red photophores**: Red light (670nm+) invisible to most deep-sea prey — dragonfish can illuminate and track prey without triggering a flight response. Hunts actively with 0.06 acceleration toward target.
- **Shrimp bioluminescent vomit**: Sprays a 3×3 grid of intense light to blind/disorient approaching predators, then flees at 0.15 acceleration.
- **Capture mechanic**: Predators (anglerfish, squid, dragonfish) capture prey at distance < 1.5, gaining 60% of prey's energy. Capture generates a bright flash (1.0 intensity).

**Respawn mechanics:**
- Creatures respawn (15% chance per dead creature, every 30 ticks) when population drops below 40% of initial count.
- Plankton respawn (20% chance per dead plankton, every 10 ticks) when population drops below 60%.

**Presets (6):**

| Preset | Character | Configuration |
|--------|-----------|--------------|
| Midnight Zone Ecosystem | Balanced deep-sea community | 4 anglerfish, 2 squid, 15 jellyfish, 25 lanternfish, 15 hatchetfish, 3 dragonfish, 20 shrimp; 400 plankton, 60 snow particles |
| Anglerfish Hunting Ground | Dense predator field | 12 anglerfish, 40 lanternfish, 20 hatchetfish — watch lure attraction draw prey to their doom |
| Bioluminescent Storm | Massive plankton bloom | 1200 plankton, 25 jellyfish — creature movement triggers spectacular cascading chain-reaction light bursts |
| Giant Squid Territory | Squid-dominated ecosystem | 8 squid with chromatophore displays, ink cloud defenses, active pursuit of smaller creatures |
| Marine Snow Blizzard | Heavy detrital rain | 200 snow particles, 30 shrimp, 5 tubeworms — dense organic particle rain fuels the food web |
| Abyssal Vent Oasis | Hydrothermal vent community | 4 vents, 20 tubeworms, 35 shrimp — chemosynthetic community clustered around vent energy sources |

**View modes (3, cycle with `v`):**
1. **Dark Abyss** — black background with glowing organisms: creature glyphs colored by type/state, bioluminescent flash effects rendered as intensity-scaled characters (`·∙•○◎●◉*✦✧`), marine snow particles (`.,:·`), ink clouds as dark patches, vent plumes with animated shimmer, depth zone labels along left edge
2. **Depth-Pressure Cross-Section** — 4 depth zone bands with pressure/depth labels, creature distribution bar charts per zone showing population counts by species, plankton density bars per zone
3. **Time-Series Graphs** — 10 sparkline graphs (Unicode block elements `▁▂▃▄▅▆▇█`) tracking flash events, cascade events, predation, plankton population, creature population, anglerfish count, giant squid count, jellyfish count, average energy, and marine snow count over last 200 ticks

**Controls:** `Space`=play/pause, `v`=cycle views, `r`=back to the preset menu, `q`=exit. In the menu, `Enter` or `Space` starts a preset.

**What to look for.** In Midnight Zone Ecosystem, the screen is nearly black — watch for scattered dim glows from jellyfish pulses and the rhythmic pulsing of anglerfish lures. When a lanternfish school drifts near an anglerfish, the lure brightens and prey are drawn in; capture triggers a bright flash. Switch to Bioluminescent Storm to see the most dramatic visual: with 1200 plankton, any creature movement sets off cascading chain-reaction light bursts that ripple outward in waves — like underwater lightning illuminating the darkness. Giant Squid Territory shows squid chromatophore behavior: squid darken as they descend and brighten near the surface. When threatened by dragonfish, they release ink clouds (dark patches) and flee with a startling flash. In Anglerfish Hunting Ground, 12 anglerfish lures create a deadly field of pulsing lights; lanternfish and hatchetfish are drawn toward them and captured. Marine Snow Blizzard shows a gentle white rain of organic particles drifting downward with sinusoidal wobble, feeding plankton and supporting a dense shrimp/tubeworm community. Abyssal Vent Oasis concentrates life around hydrothermal vents — tubeworms cluster at the bottom, shrimp swarm near vent plumes for chemosynthetic energy.

**References.**
- Haddock, S. H. D., Moline, M. A. & Case, J. F. "Bioluminescence in the sea." *Annual Review of Marine Science*, 2, 443–493, 2010. https://doi.org/10.1146/annurev-marine-120308-081028
- Widder, E. A. "Bioluminescence in the ocean: origins of biological, chemical, and ecological diversity." *Science*, 328(5979), 704–708, 2010. https://doi.org/10.1126/science.1174269
- Johnsen, S. "The optics of life: a biologist's guide to light in nature." Princeton University Press, 2012.
- Herring, P. J. "The biology of the deep ocean." Oxford University Press, 2002.
- Douglas, R. H. et al. "Dragon fish see using chlorophyll." *Nature*, 393, 423–424, 1998. https://doi.org/10.1038/30871

---

## Mycorrhizal Network & Wood Wide Web

**Background.** Mycorrhizal fungi form symbiotic associations with the roots of over 90% of terrestrial plant species, creating vast underground networks — the "wood wide web" — through which trees exchange carbon, phosphorus, water, and chemical alarm signals. Large hub trees ("mother trees") serve as network centers, detecting stressed seedlings and routing surplus resources through the fungal mesh. Pest-attacked trees broadcast volatile and chemical alarm signals that propagate through the network, triggering preemptive defensive responses in neighbors. The fungi take a carbon "tax" (typically 8–10%) for brokering all transfers. This simulation models the emergent self-organization of these networks: hub-and-spoke topology around mother trees, gradient-driven nutrient flow from surplus to deficit, alarm cascade propagation, and the fragility of the system when hub trees are removed.

**Formulation.** The simulation tracks trees (5 species + seedlings) with individual carbon/phosphorus/water budgets, connected by mycorrhizal hyphae that carry nutrients and signals.

```
Tree physiology (per tick, when not dormant):
  Photosynthesis:   carbon += rate × size × season_mult × soil_moisture
  Root uptake:      phosphorus += 0.005 × root_radius × soil_nutrients
                    water += 0.01 × root_radius × soil_moisture
  Growth:           size += 0.0002 × growth_mult  (if C>0.8, P>0.3, W>0.3)
  Metabolism:       carbon -= 0.005 × size × (0.3 if dormant else 1.0)
  Seedlings graduate to a random species when size > 0.25

Seasons (120 ticks each):
  Spring:  photo_mult = 0.7→1.0, growth ×1.2
  Summer:  photo_mult = 1.0, growth ×1.0
  Autumn:  photo_mult = 1.0→0.5, growth ×0.5
  Winter:  photo_mult = 0.1, growth ×0.1, deciduous trees go dormant
           (Pine and Fir remain active — evergreen species)

Network construction (once, at the start; later growth and decay only change hyphae):
  Trees connect when distance ≤ root_radius_A + root_radius_B
  Connection probability = 1.0 − (d / max_reach) × 0.6
    +0.30 if either tree is a mother tree
    +0.15 if same species (ectomycorrhizal specificity)

Mother tree resource sharing (carbon):
  Transfer = min(0.03, mother_carbon × 0.05) when mother C > 1.0, neighbor C < 0.4
  Fungal tax = transfer × 0.10 (carbon diverted to fungal pool)

Non-mother mutualism (gradient-driven):
  Transfer = (C_a − C_b) × 0.02  when |diff| > 0.3
  Fungal tax = |transfer| × 0.08

Alarm cascade:
  Pest-attacked trees (pest > 0.2) broadcast alarm through connected hyphae
  Receiving trees: defense += signal_strength × 0.5
  Re-broadcast: if signal_strength > 0.3, cascade at 60% attenuation
  Signal timer: 15–20 ticks propagation delay
  Defense reduces pest infection probability: chance × (1.0 − defense_level)

Hypha lifecycle:
  Thickness grows with use (carbon/phosphorus flow + signal activity)
  Unused hyphae decay: health −0.002/tick when use < 0.001
  Active hyphae heal: health +0.001/tick
  Dead hyphae (health ≤ 0) are pruned and indices remapped
```

**Tree species (5 + seedlings):**

| Species | Glyph | Characteristics |
|---------|-------|----------------|
| Oak | `O` | Deciduous, strong root system, common mother tree |
| Birch | `B` | Deciduous, pioneer species |
| Pine | `P` | Evergreen (active in winter), coniferous |
| Fir | `F` | Evergreen (active in winter), coniferous |
| Maple | `M` | Deciduous, vibrant autumn colors |
| Seedling | `.` | Juvenile, 30% photosynthesis rate, graduates at size 0.25 |

**Presets (6):**

| Preset | Character | Configuration |
|--------|-----------|--------------|
| Old-Growth Cooperation | Dense diverse old-growth | 4–6 mother trees (size 0.8–1.0), 35 mature trees, 20 seedlings — watch mother trees fund seedlings through dense fungal mesh |
| Drought Triage | Progressive water stress | Soil moisture starts at 30% of the normal level and keeps drying; drought intensity starts at 0.7 and rises +0.001/tick. Mother trees share water as well as carbon |
| Pest Cascade | Bark beetle outbreak | Trees in the last 10 columns start infected (pest 0.3–0.7); alarm signals spread through the network and defense levels rise |
| Clear-Cut Fragmentation | Logging removes hub trees | Left third: 4 large trees and 20 mature trees. Middle: 6 small trees. Right third: 8 seedlings. The network ends up as separate islands |
| Monoculture vs. Biodiversity | Side-by-side comparison | Left half: 25 pines. Right half: 3 large trees, 20 mixed trees, and 10 seedlings. Compare network density |
| Seasonal Nutrient Cycling | Four-season cycle | Starts in spring (the other presets start in summer). Winter makes deciduous trees dormant while Pine and Fir stay active |

**View modes (3, cycle with `v`):**
1. **Forest** — split display: above-ground canopy with seasonal-colored tree glyphs (green/gold/bare), mother tree markers (`M`), pest indicators; below-ground hyphal network with pulsing connections (thickness-scaled `·∙•─═`), flowing nutrient particles (C=green, P=magenta, W=blue, !=red alarm), root system circles
2. **Network Topology** — graph diagram showing trees as labeled nodes (species glyph + health bar) and hyphae as edges, colored by current activity: red=alarm signal, green=carbon flow, magenta=phosphorus flow, dim=idle
3. **Time-Series Graphs** — 10 sparkline metrics (Unicode block elements `▁▂▃▄▅▆▇█`): total carbon flow, total phosphorus flow, alarm signals, network edges, average tree health, mother tree count, seedling count, fungal tax collected, average defense level, connected components

**Controls:** `Space`=play/pause, `n` or `.`=step, `v`=cycle views, `+/-`=steps per frame (1-20), `r`=reset, `R` or `m`=menu, `q`=exit.

**What to look for.** In Old-Growth Cooperation, the mother trees form bright hub nodes with thick radiating hyphae — green carbon particles flow outward from mothers toward dim seedlings. In Drought Triage, the soil dries over time and mother trees send water (blue particles) to dry neighbors. In Pest Cascade, red alarm particles spread from the east edge through the network. Trees that receive an alarm raise their defense level, which lowers their chance of infection. Clear-Cut Fragmentation leaves the right side with few or no connections, while the left side keeps a dense web. Monoculture vs. Biodiversity compares network density on the two halves. Seasonal Nutrient Cycling shows the annual rhythm: photosynthesis rises in spring, peaks in summer, falls in autumn, and nearly stops in winter, when only Pine and Fir stay active.

**References.**
- Simard, S. W. et al. "Net transfer of carbon between ectomycorrhizal tree species in the field." *Nature*, 388, 579–582, 1997. https://doi.org/10.1038/41557
- Simard, S. W. "Finding the Mother Tree: Discovering the Wisdom of the Forest." Alfred A. Knopf, 2021.
- Beiler, K. J. et al. "Architecture of the wood-wide web: *Rhizopogon* spp. genets link multiple Douglas-fir cohorts." *New Phytologist*, 185(2), 543–553, 2010. https://doi.org/10.1111/j.1469-8137.2009.03069.x
- Babikova, Z. et al. "Underground signals carried through common mycelial networks warn neighbouring plants of aphid attack." *Ecology Letters*, 16(7), 835–843, 2013. https://doi.org/10.1111/ele.12115
- Klein, T. et al. "Belowground carbon trade among tall trees in a temperate forest." *Science*, 352(6283), 342–344, 2016. https://doi.org/10.1126/science.aad6188


---


## Glacier Dynamics & Ice Age Cycles

**Background.** Earth's climate oscillates between glacial and interglacial states on timescales of tens to hundreds of thousands of years, driven by the interplay of orbital mechanics, atmospheric composition, and ice-sheet feedback. Milutin Milankovitch identified three orbital parameters — eccentricity (~100 kyr), obliquity (~41 kyr), and precession (~23 kyr) — whose combined effect modulates high-latitude insolation sufficiently to trigger ice ages. But orbital forcing alone is too weak; amplifying feedbacks (ice-albedo, CO₂ greenhouse, thermohaline circulation changes) transform small insolation anomalies into hemisphere-spanning glaciations. This mode couples these mechanisms in a 60-band latitudinal cross-section from pole to equator. It covers glacial and interglacial states, abrupt events (Heinrich iceberg surges, Dansgaard-Oeschger warmings), and extreme states such as Snowball Earth and the PETM hothouse. One tick stands for an arbitrary span of time.

**Formulation.** The model evolves 60 latitude bands (index 0 = pole, 59 = equator) each tick. Temperature is a normalized value (0 to 1.2), not degrees:

```
Orbital forcing (Milankovitch):
  e(t) = 0.04 × sin(2π t/400 + φ_e)       eccentricity (~100 kyr)
  o(t) = 0.03 × sin(2π t/164 + φ_o)       obliquity (~41 kyr)
  p(t) = 0.02 × sin(2π t/92  + φ_p)       precession (~23 kyr)
  ΔS(t) = e(t) + o(t) + p(t)              combined anomaly

Insolation at latitude i (polar_weight = 1 at the pole, 0 at the equator):
  S_base(i) = 1.0 × (0.2 + 0.8 × i/59)
  S(i)      = S_base(i) + (1.5·o + e + p) × polar_weight + 0.3·p
  α(i)      = 0.75 where ice cover is full (ice ≥ 0.5), blended with land (0.25)
              below that; ice-free bands mix land (0.25) and ocean (0.06),
              with more ocean toward the equator
  S_absorbed(i) = S(i) × (1 − α(i))

CO₂ budget:
  volcanic outgassing:  +0.08 × volcanic multiplier ppm/tick
  silicate weathering:  −0.0003 × T_global × CO₂        (temperature-dependent sink)
  ocean absorption:     −0.0001 × (CO₂ − 280) × (1 + T_global)   (only above 280 ppm)
  anthropogenic:        +injection_rate                    (user-controllable)
  bounds: [150, 4000] ppm

Temperature response (dt = 0.25):
  T_target(i) = 0.7 × S_absorbed(i) + 0.006 × (CO₂ − 280) + D-O warmth × (1 − 0.5 × i/59)
  T(i) += dt × (0.05 × (T_target − T) + 0.03 × (T(i-1) + T(i+1) − 2T(i)))
  (the second term is meridional heat diffusion)

Ice dynamics, per band (freeze threshold = 0.25 + 0.1 × i/59):
  growth:  if T < threshold: ice += 0.012 × (threshold − T) × (1 + 0.5 × (1 − i/59))
  melt:    if T > threshold: ice −= 0.015 × (T − threshold) × (1 + 2 × CO₂ forcing)
  flow:    each band passes 0.002 × ice to its equatorward neighbor
  calving: above ice 2.0, lose 15% of the excess every tick
  Heinrich surge: chance 0.003 × (max ice / 3) per tick while some band exceeds 2.0,
           with a 30-tick cooldown. It discharges 40% of the ice in the polar quarter
           of the bands and cools those bands by 0.03
  bounds: [0, 3.0]

Sea level:
  ΔSL = −40 × mean(ice)    meters relative to baseline

Isostatic adjustment:
  bedrock(i) → bedrock(i) + 0.003 × (−0.3 × ice(i) − bedrock(i))    depression/rebound

Dansgaard-Oeschger events:
  random period 50–120 ticks, warming amplitude +0.08,
  gradual cooling at −0.002/tick between events
```

**Ice-albedo feedback.** This is the critical amplifying mechanism: ice (α = 0.75) reflects far more sunlight than ocean (0.06) or bare land (0.25). As ice advances equatorward, regional albedo rises, reducing absorbed insolation, lowering temperature, and promoting further ice growth — a positive feedback loop. In the Snowball Earth preset, this runaway is visible as ice rapidly engulfs mid-latitudes. Conversely, warming melts ice, darkening the surface, absorbing more heat, accelerating melt — the mechanism driving rapid deglaciation.

**CO₂ coupling.** The carbon cycle acts as Earth's thermostat over geological time. Volcanic outgassing (controllable with `V`/`B`) adds CO₂; silicate weathering (Walker feedback: warmer → faster weathering → more CO₂ drawn down) and ocean absorption remove it. The greenhouse term adds 0.006 to the target temperature per ppm above the 280 ppm preindustrial baseline. In the PETM preset (1800 ppm), the extreme greenhouse forcing produces an ice-free hothouse. The Anthropogenic preset injects +3 ppm/tick to simulate fossil fuel emissions overwhelming natural sinks.

**Abrupt climate events.** Two types of rapid oscillation are modeled atop the slow orbital cycles:

- **Heinrich events** — when ice thickness exceeds 2.0 at a latitude band, there is a small chance per tick of an iceberg discharge (40% of the polar ice), like the collapse of the Laurentide ice sheet's Hudson Strait ice stream. The freshwater pulse cools the polar bands.
- **Dansgaard-Oeschger (D-O) oscillations** — abrupt warming events (+0.08 warmth) at random intervals of 50-120 ticks, followed by gradual cooling (−0.002/tick). They stand in for the quasi-periodic warmings recorded in Greenland ice cores. Trigger one with `d`.

**Presets (6):**

| Preset | CO₂ (ppm) | Configuration |
|--------|-----------|---------------|
| Last Glacial Maximum | 190 | Peak ice extent, low CO₂; thick ice over the polar 35% of the bands, with glacial-phase Milankovitch offsets |
| Holocene Optimum | 280 | Warm interglacial, thin ice over the polar 8% of the bands, high obliquity phase |
| Snowball Earth Onset | 200 | Low CO₂, volcanic outgassing at 0.3×, ice over the polar 45% of the bands, cooled start |
| PETM Hothouse | 1800 | No ice, warm start, volcanic outgassing at 2.5×; models the Paleocene-Eocene Thermal Maximum (~56 Ma) |
| Anthropogenic Rapid CO₂ Injection | 420 + 3/tick | Thin ice over the polar 10% of the bands, with a constant +3 ppm/tick injection |
| Dansgaard-Oeschger Oscillations | 220 | Glacial baseline with ice over the polar 30% of the bands; the first D-O event comes after 20 ticks |

**View modes (3, cycle with `v`):**
1. **Polar-to-equator cross-section** — vertical profile showing ice sheet height (white `█▓▒░`), bedrock depression (brown), sea level line (blue `~`), temperature-colored background (blue=cold → red=warm), insolation indicators, and info panel with current CO₂/sea level/ice volume/climate state
2. **Time-series sparkline dashboard** — 10 metrics tracked over 400-tick window using Unicode block elements (`▁▂▃▄▅▆▇█`): global temperature, CO₂ concentration, total ice volume, sea level, 65°N insolation, global albedo, ice extent (latitude bands with ice), weathering rate, D-O index, Heinrich event count
3. **Orbital parameter & feedback diagram** — Milankovitch component phases (eccentricity, obliquity, precession) with bar charts showing current amplitude, feedback strength table (ice-albedo, CO₂ greenhouse, weathering thermostat, D-O warming), and climate state classification (glacial/interglacial/hothouse/snowball)

**Controls:** `Space`=play/pause, `n`=step, `v`=cycle views, `+/-`=CO₂ injection rate (0-20 ppm/tick, steps of 0.5), `V/B`=raise/lower the volcanic multiplier (0-5, steps of 0.5), `h`=trigger Heinrich event, `d`=trigger D-O warming, `r`=reset, `R` or `m`=menu, `q`=exit.

**What to look for.** In the Last Glacial Maximum preset, ice sheets dominate the polar half of the cross-section; switch to the time-series view to see CO₂ and temperature correlated in lockstep. Start the Snowball Earth preset and watch the ice-albedo runaway: ice advances equatorward, albedo rises, temperature drops, and the positive feedback drives ice to cover nearly all latitude bands — then raise volcanic activity with `V` to push CO₂ up (a snowball Earth is thought to have ended this way ~700 Ma). In the PETM Hothouse, there is no ice and temperatures are high even at the poles. The Anthropogenic preset starts from modern conditions; watch CO₂ climb as the +3 ppm/tick injection overwhelms weathering and ocean sinks, driving rapid ice loss and sea level rise. The D-O Oscillations preset shows the sawtooth pattern of abrupt warming followed by gradual cooling, with occasional Heinrich events (visible as sudden ice volume drops) interrupting the pattern — these events are recorded in real ice cores as layers of ice-rafted debris across the North Atlantic.

**References.**
- Milankovitch, M. "Canon of Insolation and the Ice-Age Problem." Royal Serbian Academy, 1941.
- Imbrie, J. et al. "On the structure and origin of major glaciation cycles." *Paleoceanography*, 8(6), 699–735, 1993. https://doi.org/10.1029/93PA02751
- Dansgaard, W. et al. "Evidence for general instability of past climate from a 250-kyr ice-core record." *Nature*, 364, 218–220, 1993. https://doi.org/10.1038/364218a0
- Heinrich, H. "Origin and consequences of cyclic ice rafting in the Northeast Atlantic Ocean during the past 130,000 years." *Quaternary Research*, 29(2), 142–152, 1988. https://doi.org/10.1016/0033-5894(88)90057-9
- Hoffman, P. F. et al. "A Neoproterozoic snowball earth." *Science*, 281(5381), 1342–1346, 1998. https://doi.org/10.1126/science.281.5381.1342
- Zachos, J. C. et al. "Trends, rhythms, and aberrations in global climate 65 Ma to present." *Science*, 292(5517), 686–693, 2001. https://doi.org/10.1126/science.1059412
