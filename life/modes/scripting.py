"""Mode: scripting — Simulation Scripting & Choreography System.

A meta-mode that lets users write and play back simple scripts (.show files)
to orchestrate timed sequences of mode transitions, parameter sweeps,
effect toggles, and layer changes.  Think of it as a programmable director
for the entire simulation platform.

Keybinding: Ctrl+U

Example .show script (line-based DSL):

    mode reaction_diffusion
    set feed 0.055 kill 0.062
    effect scanlines on
    wait 5s
    transition crossfade 2s
    mode game_of_life
    topology torus
    wait 3s
    sweep speed 1 10 over 4s
    effect bloom on
    wait 3s
"""

import curses
import math
import os
import re
import time

from life.constants import SPEEDS
from life.modes.mashup import MASHUP_SIMS, _ENGINES
from life.modes.post_processing import EFFECT_LIST
from life.grid import Grid

# ── Density characters for rendering ──
_DENSITY = " ░▒▓█"

# ── Simulation ID aliases ──
# Map friendly names (used in scripts) → engine IDs (used by _ENGINES)
_MODE_ALIASES = {
    "game_of_life": "gol",
    "gol": "gol",
    "wave": "wave",
    "wave_equation": "wave",
    "reaction_diffusion": "rd",
    "rd": "rd",
    "forest_fire": "fire",
    "fire": "fire",
    "boids": "boids",
    "boids_flocking": "boids",
    "ising": "ising",
    "ising_model": "ising",
    "rock_paper_scissors": "rps",
    "rps": "rps",
    "physarum": "physarum",
    "slime": "physarum",
}

# ── Effect name aliases ──
_EFFECT_ALIASES = {e[0]: e[0] for e in EFFECT_LIST}
_EFFECT_ALIASES.update({
    "bloom": "bloom",
    "glow": "bloom",
    "trails": "trails",
    "motion_trails": "trails",
    "edge": "edge_detect",
    "edge_detect": "edge_detect",
    "color_cycle": "color_cycle",
    "color": "color_cycle",
    "crt": "crt",
    "scanlines": "scanlines",
    "scanline": "scanlines",
})

# ── Topology aliases ──
_TOPO_ALIASES = {
    "plane": "plane",
    "torus": "torus",
    "klein": "klein_bottle",
    "klein_bottle": "klein_bottle",
    "mobius": "mobius_strip",
    "mobius_strip": "mobius_strip",
    "projective": "projective_plane",
    "projective_plane": "projective_plane",
}

# ── Speed label → index mapping ──
_SPEED_NAMES = {
    "0.5x": 0, "1x": 1, "2x": 2, "4x": 3,
    "10x": 4, "20x": 5, "50x": 6, "100x": 7,
}

# ════════════════════════════════════════════════════════════════════
#  DSL Parser
# ════════════════════════════════════════════════════════════════════

def _parse_duration(s):
    """Parse a duration string like '5s', '2.5s', '500ms' → seconds (float)."""
    s = s.strip().lower()
    if s.endswith("ms"):
        return float(s[:-2]) / 1000.0
    if s.endswith("s"):
        return float(s[:-1])
    return float(s)


def _parse_script(text):
    """Parse a .show script into a list of command dicts.

    Returns list of dicts, each with a 'cmd' key and command-specific data.
    Raises ValueError on parse errors.
    """
    commands = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        # Skip blank lines and comments
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        cmd = tokens[0].lower()

        if cmd == "mode":
            # mode <sim_name>
            if len(tokens) < 2:
                raise ValueError(f"Line {lineno}: 'mode' requires a simulation name")
            sim_name = tokens[1].lower()
            if sim_name not in _MODE_ALIASES:
                raise ValueError(f"Line {lineno}: unknown mode '{tokens[1]}'. "
                                 f"Available: {', '.join(sorted(set(_MODE_ALIASES.values())))}")
            commands.append({"cmd": "mode", "sim": _MODE_ALIASES[sim_name], "line": lineno})

        elif cmd == "wait":
            # wait <duration>
            if len(tokens) < 2:
                raise ValueError(f"Line {lineno}: 'wait' requires a duration (e.g. 5s)")
            try:
                dur = _parse_duration(tokens[1])
            except ValueError:
                raise ValueError(f"Line {lineno}: invalid duration '{tokens[1]}'")
            commands.append({"cmd": "wait", "duration": dur, "line": lineno})

        elif cmd == "effect":
            # effect <name> on|off|toggle
            if len(tokens) < 3:
                raise ValueError(f"Line {lineno}: 'effect' requires <name> <on|off|toggle>")
            ename = tokens[1].lower()
            if ename not in _EFFECT_ALIASES:
                raise ValueError(f"Line {lineno}: unknown effect '{tokens[1]}'")
            action = tokens[2].lower()
            if action not in ("on", "off", "toggle"):
                raise ValueError(f"Line {lineno}: effect action must be on/off/toggle")
            commands.append({"cmd": "effect", "effect": _EFFECT_ALIASES[ename],
                             "action": action, "line": lineno})

        elif cmd == "topology":
            # topology <name>
            if len(tokens) < 2:
                raise ValueError(f"Line {lineno}: 'topology' requires a topology name")
            tname = tokens[1].lower()
            if tname not in _TOPO_ALIASES:
                raise ValueError(f"Line {lineno}: unknown topology '{tokens[1]}'")
            commands.append({"cmd": "topology", "topo": _TOPO_ALIASES[tname], "line": lineno})

        elif cmd == "set":
            # set <param> <value> [<param> <value> ...]
            if len(tokens) < 3 or (len(tokens) - 1) % 2 != 0:
                raise ValueError(f"Line {lineno}: 'set' requires pairs of <param> <value>")
            params = {}
            for i in range(1, len(tokens), 2):
                pname = tokens[i].lower()
                try:
                    pval = float(tokens[i + 1])
                except ValueError:
                    pval = tokens[i + 1]
                params[pname] = pval
            commands.append({"cmd": "set", "params": params, "line": lineno})

        elif cmd == "sweep":
            # sweep <param> <from> <to> over <duration>
            if len(tokens) < 6 or tokens[4].lower() != "over":
                raise ValueError(f"Line {lineno}: 'sweep' format: sweep <param> <from> <to> over <duration>")
            try:
                val_from = float(tokens[2])
                val_to = float(tokens[3])
                dur = _parse_duration(tokens[5])
            except ValueError:
                raise ValueError(f"Line {lineno}: invalid sweep values")
            commands.append({"cmd": "sweep", "param": tokens[1].lower(),
                             "from": val_from, "to": val_to,
                             "duration": dur, "line": lineno})

        elif cmd == "transition":
            # transition crossfade <duration>
            if len(tokens) < 3:
                raise ValueError(f"Line {lineno}: 'transition' format: transition crossfade <duration>")
            style = tokens[1].lower()
            if style not in ("crossfade", "cut", "fade"):
                raise ValueError(f"Line {lineno}: transition style must be crossfade/cut/fade")
            try:
                dur = _parse_duration(tokens[2])
            except ValueError:
                raise ValueError(f"Line {lineno}: invalid transition duration")
            commands.append({"cmd": "transition", "style": style, "duration": dur, "line": lineno})

        elif cmd == "speed":
            # speed <label_or_index>
            if len(tokens) < 2:
                raise ValueError(f"Line {lineno}: 'speed' requires a value")
            val = tokens[1].lower()
            if val in _SPEED_NAMES:
                idx = _SPEED_NAMES[val]
            else:
                try:
                    idx = int(val)
                    if idx < 0 or idx >= len(SPEEDS):
                        raise ValueError
                except ValueError:
                    raise ValueError(f"Line {lineno}: invalid speed '{tokens[1]}'. "
                                     f"Use: {', '.join(_SPEED_NAMES.keys())}")
            commands.append({"cmd": "speed", "index": idx, "line": lineno})

        elif cmd == "color":
            # color <1-7>
            if len(tokens) < 2:
                raise ValueError(f"Line {lineno}: 'color' requires a value 1-7")
            try:
                c = int(tokens[1])
                if c < 1 or c > 7:
                    raise ValueError
            except ValueError:
                raise ValueError(f"Line {lineno}: color must be 1-7")
            commands.append({"cmd": "color", "color": c, "line": lineno})

        elif cmd == "label":
            # label <text...>
            text = " ".join(tokens[1:]) if len(tokens) > 1 else ""
            commands.append({"cmd": "label", "text": text, "line": lineno})

        elif cmd == "loop":
            # loop  (jump back to start)
            commands.append({"cmd": "loop", "line": lineno})

        else:
            raise ValueError(f"Line {lineno}: unknown command '{cmd}'")

    return commands


# ── Built-in example scripts ──

EXAMPLE_SCRIPTS = [
    {
        "name": "Emergence",
        "desc": "Game of Life → Reaction-Diffusion with effects",
        "script": """\
# Emergence — from simple rules to complex patterns
mode game_of_life
label Emergence
speed 2x
wait 5s
transition crossfade 2s
mode reaction_diffusion
effect bloom on
wait 6s
effect scanlines on
wait 4s
effect bloom off
effect scanlines off
""",
    },
    {
        "name": "Fluid Dreams",
        "desc": "Wave, RD, and Physarum with transitions",
        "script": """\
# Fluid Dreams — liquid phenomena
mode wave_equation
label Fluid Dreams
speed 4x
wait 5s
transition crossfade 2s
mode reaction_diffusion
effect trails on
wait 6s
transition crossfade 2s
mode physarum
effect bloom on
wait 6s
effect trails off
effect bloom off
""",
    },
    {
        "name": "Life & Death",
        "desc": "GoL, Forest Fire, Ising — creation and destruction",
        "script": """\
# Life & Death
mode game_of_life
label Life & Death
wait 5s
transition crossfade 1.5s
mode forest_fire
effect crt on
wait 5s
effect crt off
transition crossfade 1.5s
mode ising_model
effect color_cycle on
wait 5s
effect color_cycle off
""",
    },
    {
        "name": "Speed Ramp",
        "desc": "Boids with accelerating speed sweep",
        "script": """\
# Speed Ramp — watch the flock accelerate
mode boids
label Speed Ramp
speed 1x
wait 2s
sweep speed 1 7 over 6s
wait 2s
""",
    },
    {
        "name": "Full Tour",
        "desc": "All 8 engines in sequence with effects",
        "script": """\
# The Full Tour
mode game_of_life
label Game of Life
speed 2x
wait 4s
transition crossfade 1.5s
mode wave_equation
label Wave Equation
wait 4s
transition crossfade 1.5s
mode reaction_diffusion
label Reaction-Diffusion
effect bloom on
wait 5s
effect bloom off
transition crossfade 1.5s
mode forest_fire
label Forest Fire
wait 4s
transition crossfade 1.5s
mode boids
label Boids Flocking
wait 4s
transition crossfade 1.5s
mode ising
label Ising Model
effect scanlines on
wait 4s
effect scanlines off
transition crossfade 1.5s
mode rps
label Rock Paper Scissors
effect color_cycle on
wait 4s
effect color_cycle off
transition crossfade 1.5s
mode physarum
label Physarum Slime
effect trails on
wait 5s
effect trails off
loop
""",
    },
]


# ════════════════════════════════════════════════════════════════════
#  Mode entry / exit
# ════════════════════════════════════════════════════════════════════

def _enter_scripting_mode(self):
    """Enter Scripting & Choreography mode — show script selection menu."""
    self.script_menu = True
    self.script_menu_sel = 0
    self.script_menu_phase = 0  # 0=main menu, 1=load file prompt
    self.script_show_source = False
    self._flash("Scripting & Choreography — Ctrl+U")


def _exit_scripting_mode(self):
    """Exit Scripting mode and clean up."""
    self.script_mode = False
    self.script_menu = False
    self.script_running = False
    self.script_paused = False
    self.script_sim_state = None
    self.script_prev_density = None
    self.script_commands = []
    self.script_active_sweeps = []
    # Clear any effects we turned on
    self.pp_active.clear()
    self._flash("Scripting mode OFF")


# ════════════════════════════════════════════════════════════════════
#  Script execution engine
# ════════════════════════════════════════════════════════════════════

def _script_init(self, script_text, script_name="Script"):
    """Parse and initialize a script for playback."""
    try:
        commands = _parse_script(script_text)
    except ValueError as e:
        self._flash(f"Parse error: {e}")
        return False

    if not commands:
        self._flash("Script is empty")
        return False

    self.script_menu = False
    self.script_mode = True
    self.script_running = True
    self.script_paused = False
    self.script_name = script_name
    self.script_commands = commands
    self.script_pc = 0  # program counter
    self.script_wait_until = 0.0
    self.script_generation = 0
    self.script_active_sweeps = []  # list of active sweep animations
    self.script_label = ""
    self.script_label_alpha = 0.0
    self.script_label_time = 0.0
    self.script_color = 6
    self.script_source = script_text

    # Transition state
    self.script_crossfade = 0.0
    self.script_crossfade_duration = 0.0
    self.script_prev_density = None

    # Simulation grid
    max_y, max_x = self.stdscr.getmaxyx()
    self.script_sim_rows = max(30, max_y)
    self.script_sim_cols = max(40, max_x // 2)
    self.script_sim_state = None
    self.script_sim_id = ""
    self.script_density = None

    # Execute commands up to the first wait/sweep (immediate setup)
    _script_execute_immediate(self)
    return True


def _script_launch_sim(self, sim_id):
    """Launch a new simulation engine."""
    if sim_id not in _ENGINES:
        self._flash(f"Unknown engine: {sim_id}")
        return

    # Save previous density for crossfade
    if self.script_density is not None:
        self.script_prev_density = [row[:] for row in self.script_density]
    else:
        self.script_prev_density = None

    init_fn, _, dens_fn = _ENGINES[sim_id]
    self.script_sim_state = init_fn(self.script_sim_rows, self.script_sim_cols)
    self.script_sim_id = sim_id
    self.script_density = dens_fn(self.script_sim_state)


def _script_execute_immediate(self):
    """Execute commands starting at script_pc until we hit a blocking command
    (wait, sweep) or reach the end."""
    while self.script_pc < len(self.script_commands):
        cmd = self.script_commands[self.script_pc]

        if cmd["cmd"] == "mode":
            _script_launch_sim(self, cmd["sim"])
            self.script_pc += 1

        elif cmd["cmd"] == "wait":
            self.script_wait_until = time.monotonic() + cmd["duration"]
            self.script_pc += 1
            return  # block until wait expires

        elif cmd["cmd"] == "effect":
            eid = cmd["effect"]
            if cmd["action"] == "on":
                self.pp_active.add(eid)
            elif cmd["action"] == "off":
                self.pp_active.discard(eid)
            else:  # toggle
                if eid in self.pp_active:
                    self.pp_active.discard(eid)
                else:
                    self.pp_active.add(eid)
            self.script_pc += 1

        elif cmd["cmd"] == "topology":
            self.grid.topology = cmd["topo"]
            self.script_pc += 1

        elif cmd["cmd"] == "set":
            for pname, pval in cmd["params"].items():
                if pname == "speed" and isinstance(pval, (int, float)):
                    idx = max(0, min(len(SPEEDS) - 1, int(pval)))
                    self.speed_idx = idx
                elif pname == "feed" and self.script_sim_id == "rd" and self.script_sim_state:
                    self.script_sim_state["feed"] = float(pval)
                elif pname == "kill" and self.script_sim_id == "rd" and self.script_sim_state:
                    self.script_sim_state["kill"] = float(pval)
            self.script_pc += 1

        elif cmd["cmd"] == "sweep":
            sweep = {
                "param": cmd["param"],
                "from": cmd["from"],
                "to": cmd["to"],
                "duration": cmd["duration"],
                "start_time": time.monotonic(),
            }
            self.script_active_sweeps.append(sweep)
            # Also set wait for the sweep duration
            self.script_wait_until = time.monotonic() + cmd["duration"]
            self.script_pc += 1
            return  # block until sweep completes

        elif cmd["cmd"] == "transition":
            if cmd["style"] in ("crossfade", "fade"):
                self.script_crossfade = 1.0
                self.script_crossfade_duration = cmd["duration"]
            # "cut" = no transition, just proceed
            self.script_pc += 1

        elif cmd["cmd"] == "speed":
            self.speed_idx = cmd["index"]
            self.script_pc += 1

        elif cmd["cmd"] == "color":
            self.script_color = cmd["color"]
            self.script_pc += 1

        elif cmd["cmd"] == "label":
            self.script_label = cmd["text"]
            self.script_label_alpha = 1.0
            self.script_label_time = time.monotonic()
            self.script_pc += 1

        elif cmd["cmd"] == "loop":
            self.script_pc = 0
            # Continue executing from the top

        else:
            self.script_pc += 1

    # Reached end of script
    if self.script_pc >= len(self.script_commands):
        self.script_running = False


def _script_step(self):
    """Advance the script — step simulation, update sweeps and transitions."""
    if not self.script_running or self.script_paused:
        return

    now = time.monotonic()

    # Step the simulation engine if one is active
    if self.script_sim_state and self.script_sim_id:
        _, step_fn, dens_fn = _ENGINES[self.script_sim_id]
        step_fn(self.script_sim_state, None, 0.0)
        self.script_density = dens_fn(self.script_sim_state)
        self.script_generation += 1

    # Update crossfade decay
    if self.script_crossfade > 0 and self.script_crossfade_duration > 0:
        decay_rate = 1.0 / (self.script_crossfade_duration * 20)
        self.script_crossfade = max(0.0, self.script_crossfade - decay_rate)

    # Update active sweeps
    finished_sweeps = []
    for i, sweep in enumerate(self.script_active_sweeps):
        elapsed = now - sweep["start_time"]
        t = min(1.0, elapsed / max(0.01, sweep["duration"]))
        # Smooth ease
        t_smooth = t * t * (3.0 - 2.0 * t)
        val = sweep["from"] + (sweep["to"] - sweep["from"]) * t_smooth

        # Apply the swept parameter
        pname = sweep["param"]
        if pname == "speed":
            self.speed_idx = max(0, min(len(SPEEDS) - 1, int(val)))

        if elapsed >= sweep["duration"]:
            finished_sweeps.append(i)

    for i in reversed(finished_sweeps):
        self.script_active_sweeps.pop(i)

    # Update label fade: visible 3s, then fade over 1s
    if self.script_label_alpha > 0:
        label_elapsed = now - self.script_label_time
        if label_elapsed < 3.0:
            self.script_label_alpha = 1.0
        elif label_elapsed < 4.0:
            self.script_label_alpha = max(0.0, 1.0 - (label_elapsed - 3.0))
        else:
            self.script_label_alpha = 0.0

    # Check if we're waiting
    if now >= self.script_wait_until:
        # Done waiting — advance to next commands
        _script_execute_immediate(self)


# ════════════════════════════════════════════════════════════════════
#  Drawing
# ════════════════════════════════════════════════════════════════════

def _draw_script_menu(self, max_y, max_x):
    """Draw the script selection / load menu."""
    self.stdscr.erase()

    # Title
    title = "━━━ SIMULATION SCRIPTING & CHOREOGRAPHY ━━━"
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(2) | curses.A_BOLD)
    except curses.error:
        pass

    subtitle = "Programmable shows: timed mode transitions, effects, parameter sweeps"
    try:
        self.stdscr.addstr(2, max(0, (max_x - len(subtitle)) // 2),
                           subtitle[:max_x - 2],
                           curses.color_pair(7) | curses.A_DIM)
    except curses.error:
        pass

    if self.script_menu_phase == 0:
        # Main menu: example scripts + load from file
        menu_y = 5
        total = len(EXAMPLE_SCRIPTS) + 1  # +1 for "Load .show file"

        for i, ex in enumerate(EXAMPLE_SCRIPTS):
            y = menu_y + i * 3
            if y >= max_y - 3:
                break
            selected = i == self.script_menu_sel
            marker = "▸ " if selected else "  "
            attr = (curses.color_pair(2) | curses.A_REVERSE | curses.A_BOLD
                    if selected else curses.color_pair(6))
            line = f"{marker}{ex['name']}"
            try:
                self.stdscr.addstr(y, 4, line[:max_x - 6], attr)
            except curses.error:
                pass
            if y + 1 < max_y - 3:
                try:
                    self.stdscr.addstr(y + 1, 8, ex["desc"][:max_x - 10],
                                       curses.color_pair(7) | curses.A_DIM)
                except curses.error:
                    pass

        # "Load .show file" option
        load_y = menu_y + len(EXAMPLE_SCRIPTS) * 3
        if load_y < max_y - 3:
            selected = self.script_menu_sel == len(EXAMPLE_SCRIPTS)
            marker = "▸ " if selected else "  "
            attr = (curses.color_pair(2) | curses.A_REVERSE | curses.A_BOLD
                    if selected else curses.color_pair(3))
            try:
                self.stdscr.addstr(load_y, 4,
                                   f"{marker}Load .show file from disk"[:max_x - 6], attr)
            except curses.error:
                pass

    # Footer
    footer = " ↑↓ Select │ Enter Launch │ Esc Back "
    try:
        self.stdscr.addstr(max_y - 1, 0, footer[:max_x - 1].ljust(max_x - 1),
                           curses.color_pair(6) | curses.A_REVERSE)
    except curses.error:
        pass


def _draw_scripting(self, max_y, max_x):
    """Draw the scripting playback — simulation with status and labels."""
    self.stdscr.erase()
    color = self.script_color

    if self.script_density is None:
        # No simulation yet — show waiting message
        try:
            self.stdscr.addstr(max_y // 2, max(0, (max_x - 20) // 2),
                               "Waiting for script...",
                               curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass
        _draw_script_status(self, max_y, max_x)
        return

    density = self.script_density
    prev = self.script_prev_density
    cf = self.script_crossfade

    # Screen rendering area
    screen_rows = max_y - 2
    screen_cols = (max_x - 1) // 2

    sim_rows = self.script_sim_rows
    sim_cols = self.script_sim_cols

    for sy in range(min(screen_rows, sim_rows)):
        if 1 + sy >= max_y - 1:
            break
        sim_r = int(sy * sim_rows / max(1, screen_rows))
        if sim_r >= sim_rows:
            continue
        d_row = density[sim_r] if sim_r < len(density) else []
        p_row = prev[sim_r] if prev and sim_r < len(prev) else None

        for sx in range(min(screen_cols, sim_cols)):
            px = sx * 2
            if px + 1 >= max_x:
                break
            sim_c = int(sx * sim_cols / max(1, screen_cols))
            if sim_c >= sim_cols:
                continue

            val = d_row[sim_c] if sim_c < len(d_row) else 0.0

            # Crossfade blending
            if cf > 0 and p_row is not None and sim_c < len(p_row):
                old_val = p_row[sim_c]
                val = old_val * cf + val * (1.0 - cf)

            if val < 0.01:
                continue

            di = max(1, min(4, int(val * 4.0)))
            ch = _DENSITY[di]

            if val > 0.7:
                attr = curses.color_pair(color) | curses.A_BOLD
            elif val > 0.3:
                attr = curses.color_pair(color)
            else:
                attr = curses.color_pair(color) | curses.A_DIM

            try:
                self.stdscr.addstr(1 + sy, px, ch + " ", attr)
            except curses.error:
                pass

    # Label overlay
    if self.script_label and self.script_label_alpha > 0:
        _draw_script_label(self, max_y, max_x)

    # Status bar
    _draw_script_status(self, max_y, max_x)


def _draw_script_label(self, max_y, max_x):
    """Draw the label overlay."""
    alpha = self.script_label_alpha
    label = self.script_label

    attr = (curses.color_pair(2) | curses.A_BOLD if alpha > 0.5
            else curses.color_pair(7) | curses.A_DIM)

    box_w = len(label) + 6
    box_h = 3
    bx = max(0, (max_x - box_w) // 2)
    by = max(0, (max_y - box_h) // 2 - 3)

    if by + box_h < max_y and bx + box_w < max_x:
        try:
            top = "╔" + "═" * (box_w - 2) + "╗"
            self.stdscr.addstr(by, bx, top[:max_x - bx - 1], attr)
            mid = f"║ {label}".ljust(box_w - 1) + "║"
            self.stdscr.addstr(by + 1, bx, mid[:max_x - bx - 1], attr)
            bot = "╚" + "═" * (box_w - 2) + "╝"
            self.stdscr.addstr(by + 2, bx, bot[:max_x - bx - 1], attr)
        except curses.error:
            pass


def _draw_script_status(self, max_y, max_x):
    """Draw the status bar at the bottom."""
    paused_str = " PAUSED" if self.script_paused else ""
    finished_str = " FINISHED" if not self.script_running and self.script_mode else ""

    # Current command info
    pc = self.script_pc
    total = len(self.script_commands)
    cmd_info = ""
    if pc > 0 and pc <= total:
        prev_cmd = self.script_commands[pc - 1]
        cmd_info = f"cmd {pc}/{total}"

    # Remaining wait time
    now = time.monotonic()
    wait_remaining = max(0, self.script_wait_until - now) if self.script_wait_until > 0 else 0

    sim_name = self.script_sim_id.upper() if self.script_sim_id else "—"

    status = (f" {self.script_name}"
              f" │ {sim_name}"
              f" │ {cmd_info}"
              f" │ gen {self.script_generation}")
    if wait_remaining > 0:
        status += f" │ wait {wait_remaining:.1f}s"
    status += f"{paused_str}{finished_str}"
    status += " │ Space Pause │ n Skip │ r Restart │ Esc Exit "

    if max_y > 0:
        try:
            self.stdscr.addstr(max_y - 1, 0,
                               status[:max_x - 1].ljust(max_x - 1),
                               curses.color_pair(6) | curses.A_REVERSE)
        except curses.error:
            pass


# ════════════════════════════════════════════════════════════════════
#  Script source viewer / editor overlay
# ════════════════════════════════════════════════════════════════════

def _draw_script_source(self, max_y, max_x):
    """Draw a source code overlay of the current script."""
    lines = self.script_source.splitlines()
    box_w = min(max_x - 4, 60)
    box_h = min(max_y - 4, len(lines) + 4)
    bx = max(0, (max_x - box_w) // 2)
    by = max(0, (max_y - box_h) // 2)

    try:
        self.stdscr.addstr(by, bx, "╔" + "═" * (box_w - 2) + "╗",
                           curses.color_pair(7))
        title = f" {self.script_name} "
        self.stdscr.addstr(by, bx + 2, title[:box_w - 4],
                           curses.color_pair(2) | curses.A_BOLD)
    except curses.error:
        pass

    # Current PC line
    current_line = 0
    if self.script_pc < len(self.script_commands):
        current_line = self.script_commands[self.script_pc].get("line", 0)

    for i, line in enumerate(lines):
        y = by + 1 + i
        if y >= by + box_h - 1:
            break
        is_current = (i + 1) == current_line
        prefix = "▸ " if is_current else "  "
        attr = (curses.color_pair(2) | curses.A_BOLD if is_current
                else curses.color_pair(7))
        content = f"║{prefix}{line}"
        content = content[:box_w - 1].ljust(box_w - 1) + "║"
        try:
            self.stdscr.addstr(y, bx, content, attr)
        except curses.error:
            pass

    try:
        self.stdscr.addstr(by + box_h - 1, bx,
                           "╚" + "═" * (box_w - 2) + "╝",
                           curses.color_pair(7))
        hint = " s=close source │ Esc=exit "
        self.stdscr.addstr(by + box_h - 1, bx + 2, hint[:box_w - 4],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ════════════════════════════════════════════════════════════════════
#  Key handling
# ════════════════════════════════════════════════════════════════════

def _handle_script_menu_key(self, key):
    """Handle keys in the script selection menu."""
    if key == -1:
        return True

    n = len(EXAMPLE_SCRIPTS) + 1  # +1 for load option

    if key in (curses.KEY_DOWN, ord("j")):
        self.script_menu_sel = (self.script_menu_sel + 1) % n
        return True
    if key in (curses.KEY_UP, ord("k")):
        self.script_menu_sel = (self.script_menu_sel - 1) % n
        return True
    if key in (27, ord("q")):
        self.script_menu = False
        self.script_mode = False
        return True
    if key in (10, 13, curses.KEY_ENTER):
        if self.script_menu_sel < len(EXAMPLE_SCRIPTS):
            ex = EXAMPLE_SCRIPTS[self.script_menu_sel]
            _script_init(self, ex["script"], ex["name"])
        else:
            # Load from file
            path = self._prompt_text("Path to .show file:")
            if path:
                path = os.path.expanduser(path.strip())
                if os.path.isfile(path):
                    try:
                        with open(path, "r") as f:
                            text = f.read()
                        name = os.path.basename(path)
                        _script_init(self, text, name)
                    except Exception as e:
                        self._flash(f"Error: {e}")
                else:
                    self._flash(f"File not found: {path}")
        return True
    return True


def _handle_script_key(self, key):
    """Handle keys during script playback."""
    if key == -1:
        return True

    # Escape / q = exit
    if key == 27 or key == ord("q"):
        _exit_scripting_mode(self)
        return True

    # Space = pause/resume
    if key == ord(" "):
        self.script_paused = not self.script_paused
        if not self.script_paused:
            # Adjust wait time for pause duration
            pass  # wait_until is monotonic, but we'd need to track pause time
        return True

    # n = skip current wait / advance
    if key == ord("n"):
        self.script_wait_until = 0.0
        self.script_active_sweeps.clear()
        _script_execute_immediate(self)
        return True

    # r = restart script
    if key == ord("r"):
        if self.script_source:
            _script_init(self, self.script_source, self.script_name)
        return True

    # s = toggle source view
    if key == ord("s"):
        self.script_show_source = not self.script_show_source
        return True

    return True


# ════════════════════════════════════════════════════════════════════
#  Registration
# ════════════════════════════════════════════════════════════════════

def register(App):
    """Register scripting mode methods on the App class."""
    App._enter_scripting_mode = _enter_scripting_mode
    App._exit_scripting_mode = _exit_scripting_mode
    App._script_init = _script_init
    App._script_launch_sim = _script_launch_sim
    App._script_step = _script_step
    App._handle_script_menu_key = _handle_script_menu_key
    App._handle_script_key = _handle_script_key
    App._draw_script_menu = _draw_script_menu
    App._draw_scripting = _draw_scripting
    App._draw_script_label = _draw_script_label
    App._draw_script_status = _draw_script_status
    App._draw_script_source = _draw_script_source
