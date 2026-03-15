"""Mode: alife — simulation mode for the life package."""
import curses
import math
import random
import time


from life.utils import sparkline

def _enter_alife_mode(self):
    """Enter Artificial Life Ecosystem — show preset menu."""
    self.alife_menu = True
    self.alife_menu_sel = 0
    self._flash("Artificial Life Ecosystem — select an environment")



def _exit_alife_mode(self):
    """Exit Artificial Life Ecosystem mode."""
    self.alife_mode = False
    self.alife_menu = False
    self.alife_running = False
    self.alife_creatures = []
    self.alife_food = []
    self.alife_pop_history = []
    self.alife_herb_history = []
    self.alife_pred_history = []
    self._flash("Artificial Life Ecosystem OFF")



def _alife_make_creature(self, r: float, c: float, diet: int = 0,
                          speed: float = 1.0, size: float = 1.0,
                          sense: float = 5.0, generation: int = 0,
                          brain: list | None = None) -> dict:
    """Create a creature dict. diet: 0=herb, 1=pred, 2=omni."""
    if brain is None:
        # Simple neural net: 6 inputs -> 4 hidden -> 2 outputs (dx, dy)
        # Inputs: nearest_food_dx, nearest_food_dy, nearest_pred_dx, nearest_pred_dy, energy, bias
        brain = [random.gauss(0, 0.5) for _ in range(6 * 4 + 4 * 2)]
    cid = self.alife_next_id
    self.alife_next_id += 1
    return {
        "id": cid, "r": r, "c": c, "vr": 0.0, "vc": 0.0,
        "diet": diet,  # 0=herbivore, 1=predator, 2=omnivore
        "speed": max(0.3, min(3.0, speed)),
        "size": max(0.5, min(3.0, size)),
        "sense": max(2.0, min(15.0, sense)),
        "energy": 80.0 + size * 20,
        "max_energy": 100.0 + size * 30,
        "age": 0,
        "generation": generation,
        "brain": brain,
        "kills": 0,
        "children": 0,
    }



def _alife_brain_forward(self, brain: list, inputs: list) -> tuple:
    """Run a simple 6->4->2 neural network forward pass."""
    # Layer 1: 6 inputs -> 4 hidden (weights 0..23, biases implicitly in weights)
    hidden = [0.0] * 4
    for h in range(4):
        s = 0.0
        for i in range(6):
            s += inputs[i] * brain[h * 6 + i]
        hidden[h] = math.tanh(s)
    # Layer 2: 4 hidden -> 2 outputs (weights 24..31)
    out = [0.0, 0.0]
    for o in range(2):
        s = 0.0
        for h in range(4):
            s += hidden[h] * brain[24 + o * 4 + h]
        out[o] = math.tanh(s)
    return out[0], out[1]



def _alife_mutate_brain(self, brain: list) -> list:
    """Return a mutated copy of a brain."""
    new_brain = []
    for w in brain:
        if random.random() < self.alife_mutation_rate:
            new_brain.append(w + random.gauss(0, 0.3))
        else:
            new_brain.append(w)
    return new_brain



def _alife_init(self, preset_idx: int):
    """Initialize ecosystem with chosen preset."""
    import random as _r
    name, _desc, ptype = self.ALIFE_PRESETS[preset_idx]
    self.alife_preset_name = name
    max_y, max_x = self.stdscr.getmaxyx()
    self.alife_rows = max_y - 3  # leave room for HUD
    self.alife_cols = max_x - 1
    rows, cols = self.alife_rows, self.alife_cols

    # Initialize food grid
    self.alife_food = [[0.0] * cols for _ in range(rows)]

    # Preset-specific parameters
    n_herb, n_pred, n_omni = 30, 0, 0
    food_density = 0.3
    self.alife_food_regrow = 0.02
    self.alife_mutation_rate = 0.15

    if ptype == "grassland":
        n_herb, n_pred, n_omni = 40, 0, 0
        food_density = 0.4
        self.alife_food_regrow = 0.03
    elif ptype == "predprey":
        n_herb, n_pred, n_omni = 35, 8, 0
        food_density = 0.35
        self.alife_food_regrow = 0.025
    elif ptype == "desert":
        n_herb, n_pred, n_omni = 20, 5, 0
        food_density = 0.1
        self.alife_food_regrow = 0.008
        self.alife_mutation_rate = 0.25
    elif ptype == "reef":
        n_herb, n_pred, n_omni = 50, 10, 10
        food_density = 0.5
        self.alife_food_regrow = 0.04
    elif ptype == "evolab":
        n_herb, n_pred, n_omni = 30, 5, 5
        food_density = 0.3
        self.alife_mutation_rate = 0.35
        self.alife_food_regrow = 0.025
    elif ptype == "soup":
        n_herb, n_pred, n_omni = 8, 0, 2
        food_density = 0.15
        self.alife_food_regrow = 0.015
        self.alife_mutation_rate = 0.2

    # Scatter initial food
    for r in range(rows):
        for c in range(cols):
            if _r.random() < food_density:
                self.alife_food[r][c] = _r.uniform(0.3, 1.0)

    # Spawn creatures
    self.alife_creatures = []
    self.alife_next_id = 0
    for _ in range(n_herb):
        cr = _r.uniform(1, rows - 2)
        cc = _r.uniform(1, cols - 2)
        self.alife_creatures.append(self._alife_make_creature(
            cr, cc, diet=0, speed=_r.uniform(0.6, 1.4),
            size=_r.uniform(0.7, 1.5), sense=_r.uniform(3, 8)))
    for _ in range(n_pred):
        cr = _r.uniform(1, rows - 2)
        cc = _r.uniform(1, cols - 2)
        self.alife_creatures.append(self._alife_make_creature(
            cr, cc, diet=1, speed=_r.uniform(1.0, 2.0),
            size=_r.uniform(1.0, 2.0), sense=_r.uniform(5, 12)))
    for _ in range(n_omni):
        cr = _r.uniform(1, rows - 2)
        cc = _r.uniform(1, cols - 2)
        self.alife_creatures.append(self._alife_make_creature(
            cr, cc, diet=2, speed=_r.uniform(0.8, 1.6),
            size=_r.uniform(0.8, 1.8), sense=_r.uniform(4, 10)))

    self.alife_tick = 0
    self.alife_generation = 0
    self.alife_gen_max = 0
    self.alife_total_births = 0
    self.alife_total_deaths = 0
    self.alife_pop_history = []
    self.alife_herb_history = []
    self.alife_pred_history = []
    self.alife_menu = False
    self.alife_mode = True
    self.alife_running = True
    self.alife_show_stats = True
    self._flash(f"Ecosystem: {name} — space=pause  s=stats  r=reset  +/-=food")



def _alife_step(self):
    """Advance ecosystem by one tick."""
    import random as _r
    import math
    rows, cols = self.alife_rows, self.alife_cols
    if rows <= 0 or cols <= 0:
        return
    self.alife_tick += 1

    # Regrow food
    for r in range(rows):
        row = self.alife_food[r]
        for c in range(cols):
            if row[c] < 1.0:
                row[c] = min(1.0, row[c] + self.alife_food_regrow * _r.uniform(0.5, 1.5))
                # Chance to sprout new food near existing food
                if row[c] > 0.5 and _r.random() < 0.002:
                    nr, nc = r + _r.randint(-1, 1), c + _r.randint(-1, 1)
                    if 0 <= nr < rows and 0 <= nc < cols and self.alife_food[nr][nc] < 0.1:
                        self.alife_food[nr][nc] = 0.3

    creatures = self.alife_creatures
    new_creatures = []
    dead_ids = set()

    # Build spatial lookup for creature interactions
    grid_lookup: dict[tuple, list[int]] = {}
    for idx, cr in enumerate(creatures):
        gr, gc = int(cr["r"]) // 4, int(cr["c"]) // 4
        key = (gr, gc)
        if key not in grid_lookup:
            grid_lookup[key] = []
        grid_lookup[key].append(idx)

    for idx, cr in enumerate(creatures):
        if cr["id"] in dead_ids:
            continue

        r, c = cr["r"], cr["c"]
        sense = cr["sense"]
        diet = cr["diet"]

        # Find nearest food (for herbivores/omnivores)
        nearest_food_dr, nearest_food_dc = 0.0, 0.0
        if diet != 1:  # not pure predator
            best_fd = sense + 1
            ir, ic = int(r), int(c)
            sr = max(0, ir - int(sense))
            er = min(rows, ir + int(sense) + 1)
            sc = max(0, ic - int(sense))
            ec = min(cols, ic + int(sense) + 1)
            for fr in range(sr, er):
                for fc in range(sc, ec):
                    if self.alife_food[fr][fc] > 0.2:
                        d = abs(fr - r) + abs(fc - c)
                        if d < best_fd and d > 0.1:
                            best_fd = d
                            nearest_food_dr = (fr - r) / best_fd
                            nearest_food_dc = (fc - c) / best_fd

        # Find nearest threat (predators for herbivores) or prey (for predators)
        nearest_threat_dr, nearest_threat_dc = 0.0, 0.0
        gr, gc = int(r) // 4, int(c) // 4
        best_td = sense + 1
        for dgr in range(-2, 3):
            for dgc in range(-2, 3):
                nkey = (gr + dgr, gc + dgc)
                if nkey not in grid_lookup:
                    continue
                for oidx in grid_lookup[nkey]:
                    if oidx == idx:
                        continue
                    other = creatures[oidx]
                    if other["id"] in dead_ids:
                        continue
                    d = abs(other["r"] - r) + abs(other["c"] - c)
                    if d >= best_td or d < 0.1:
                        continue
                    if diet == 0 and other["diet"] >= 1:
                        # Herbivore sees predator/omnivore as threat
                        best_td = d
                        nearest_threat_dr = (other["r"] - r) / d
                        nearest_threat_dc = (other["c"] - c) / d
                    elif diet >= 1 and other["diet"] == 0 and other["size"] < cr["size"] * 1.3:
                        # Predator/omnivore sees smaller herbivore as prey
                        best_td = d
                        nearest_threat_dr = (other["r"] - r) / d
                        nearest_threat_dc = (other["c"] - c) / d

        # Neural network inputs
        energy_norm = cr["energy"] / cr["max_energy"]
        nn_inputs = [nearest_food_dr, nearest_food_dc,
                     nearest_threat_dr, nearest_threat_dc,
                     energy_norm, 1.0]  # bias

        # Brain decides movement direction
        dr, dc = self._alife_brain_forward(cr["brain"], nn_inputs)

        # Apply movement
        spd = cr["speed"] * self.alife_speed_scale
        cr["vr"] = cr["vr"] * 0.3 + dr * spd * 0.7
        cr["vc"] = cr["vc"] * 0.3 + dc * spd * 0.7
        cr["r"] = max(0, min(rows - 1, cr["r"] + cr["vr"]))
        cr["c"] = max(0, min(cols - 1, cr["c"] + cr["vc"]))

        # Energy cost: movement + metabolism
        move_cost = (abs(cr["vr"]) + abs(cr["vc"])) * 0.3 * cr["size"]
        base_cost = 0.1 * cr["size"]
        cr["energy"] -= move_cost + base_cost
        cr["age"] += 1

        # Eat food (herbivores and omnivores)
        if diet != 1:
            ir, ic = int(cr["r"]), int(cr["c"])
            if 0 <= ir < rows and 0 <= ic < cols:
                food_here = self.alife_food[ir][ic]
                if food_here > 0.05:
                    eat = min(food_here, 0.4 * cr["size"])
                    self.alife_food[ir][ic] -= eat
                    cr["energy"] = min(cr["max_energy"], cr["energy"] + eat * 50)

        # Predator/omnivore hunting
        if diet >= 1:
            ir, ic = int(cr["r"]), int(cr["c"])
            gr2, gc2 = ir // 4, ic // 4
            for dgr in range(-1, 2):
                for dgc in range(-1, 2):
                    nkey = (gr2 + dgr, gc2 + dgc)
                    if nkey not in grid_lookup:
                        continue
                    for oidx in grid_lookup[nkey]:
                        other = creatures[oidx]
                        if other["id"] in dead_ids or other["id"] == cr["id"]:
                            continue
                        if other["diet"] == 1 and diet == 1:
                            continue  # predators don't eat each other
                        d = math.sqrt((other["r"] - cr["r"])**2 + (other["c"] - cr["c"])**2)
                        if d < 1.5 and other["size"] < cr["size"] * 1.3:
                            # Kill and eat
                            energy_gain = other["energy"] * 0.6 + other["size"] * 20
                            cr["energy"] = min(cr["max_energy"], cr["energy"] + energy_gain)
                            cr["kills"] += 1
                            dead_ids.add(other["id"])
                            self.alife_total_deaths += 1

        # Death check
        if cr["energy"] <= 0 or cr["age"] > 800 + cr["size"] * 200:
            dead_ids.add(cr["id"])
            self.alife_total_deaths += 1
            # Drop food where creature died
            ir, ic = int(cr["r"]), int(cr["c"])
            if 0 <= ir < rows and 0 <= ic < cols:
                self.alife_food[ir][ic] = min(1.0, self.alife_food[ir][ic] + cr["size"] * 0.3)
            continue

        # Reproduction check
        if (cr["energy"] > cr["max_energy"] * 0.75 and cr["age"] > 60
                and _r.random() < 0.02 * (1.0 / cr["size"])):
            cr["energy"] *= 0.45
            cr["children"] += 1
            self.alife_total_births += 1
            child_gen = cr["generation"] + 1
            self.alife_gen_max = max(self.alife_gen_max, child_gen)
            # Mutate traits
            child_speed = cr["speed"] + _r.gauss(0, 0.1) * self.alife_mutation_rate * 3
            child_size = cr["size"] + _r.gauss(0, 0.1) * self.alife_mutation_rate * 3
            child_sense = cr["sense"] + _r.gauss(0, 0.3) * self.alife_mutation_rate * 3
            child_diet = cr["diet"]
            # Rare diet mutation
            if _r.random() < self.alife_mutation_rate * 0.1:
                child_diet = _r.randint(0, 2)
            child_brain = self._alife_mutate_brain(cr["brain"])
            child = self._alife_make_creature(
                cr["r"] + _r.uniform(-2, 2),
                cr["c"] + _r.uniform(-2, 2),
                diet=child_diet, speed=child_speed, size=child_size,
                sense=child_sense, generation=child_gen, brain=child_brain)
            child["energy"] = cr["max_energy"] * 0.4
            new_creatures.append(child)

    # Remove dead, add newborn
    self.alife_creatures = [cr for cr in creatures if cr["id"] not in dead_ids]
    self.alife_creatures.extend(new_creatures)

    # Cap population to avoid slowdown
    max_pop = (rows * cols) // 15
    if len(self.alife_creatures) > max_pop:
        # Remove lowest energy creatures
        self.alife_creatures.sort(key=lambda c: c["energy"], reverse=True)
        excess = self.alife_creatures[max_pop:]
        self.alife_total_deaths += len(excess)
        self.alife_creatures = self.alife_creatures[:max_pop]

    # Track population
    n_total = len(self.alife_creatures)
    n_herb = sum(1 for cr in self.alife_creatures if cr["diet"] == 0)
    n_pred = sum(1 for cr in self.alife_creatures if cr["diet"] == 1)
    self.alife_pop_history.append(n_total)
    self.alife_herb_history.append(n_herb)
    self.alife_pred_history.append(n_pred)
    if len(self.alife_pop_history) > 200:
        self.alife_pop_history = self.alife_pop_history[-200:]
        self.alife_herb_history = self.alife_herb_history[-200:]
        self.alife_pred_history = self.alife_pred_history[-200:]

    self.alife_generation += 1

    # If population dies out, respawn a few creatures
    if len(self.alife_creatures) == 0:
        for _ in range(5):
            cr = _r.uniform(1, rows - 2)
            cc = _r.uniform(1, cols - 2)
            self.alife_creatures.append(self._alife_make_creature(
                cr, cc, diet=0, speed=_r.uniform(0.6, 1.4),
                size=_r.uniform(0.7, 1.5), sense=_r.uniform(3, 8),
                generation=self.alife_gen_max + 1))



def _handle_alife_menu_key(self, key: int) -> bool:
    """Handle Artificial Life menu input."""
    n = len(self.ALIFE_PRESETS)
    if key == ord("j") or key == curses.KEY_DOWN:
        self.alife_menu_sel = (self.alife_menu_sel + 1) % n
    elif key == ord("k") or key == curses.KEY_UP:
        self.alife_menu_sel = (self.alife_menu_sel - 1) % n
    elif key in (curses.KEY_ENTER, 10, 13):
        self._alife_init(self.alife_menu_sel)
    elif key == ord("q") or key == 27:
        self.alife_menu = False
        self._flash("Artificial Life cancelled")
    else:
        return True
    return True



def _handle_alife_key(self, key: int) -> bool:
    """Handle active Artificial Life input."""
    if key == ord(" "):
        self.alife_running = not self.alife_running
        self._flash("PAUSED" if not self.alife_running else "RUNNING")
    elif key == ord("n") or key == ord("."):
        self._alife_step()
    elif key == ord("r"):
        self._alife_init(self.ALIFE_PRESETS.index(
            next(p for p in self.ALIFE_PRESETS if p[0] == self.alife_preset_name)))
    elif key == ord("R") or key == ord("m"):
        self.alife_running = False
        self.alife_mode = False
        self.alife_menu = True
        self.alife_menu_sel = 0
    elif key == ord("s"):
        self.alife_show_stats = not self.alife_show_stats
    elif key == ord("+") or key == ord("="):
        self.alife_food_regrow = min(0.1, self.alife_food_regrow * 1.3)
        self._flash(f"Food regrowth: {self.alife_food_regrow:.3f}")
    elif key == ord("-") or key == ord("_"):
        self.alife_food_regrow = max(0.001, self.alife_food_regrow * 0.7)
        self._flash(f"Food regrowth: {self.alife_food_regrow:.3f}")
    elif key == ord("f"):
        # Scatter extra food
        import random as _r
        for _ in range(self.alife_rows * self.alife_cols // 5):
            fr = _r.randint(0, self.alife_rows - 1)
            fc = _r.randint(0, self.alife_cols - 1)
            self.alife_food[fr][fc] = min(1.0, self.alife_food[fr][fc] + 0.5)
        self._flash("Scattered extra food!")
    elif key == ord("<"):
        self.alife_speed_scale = max(0.2, self.alife_speed_scale * 0.8)
        self._flash(f"Speed scale: {self.alife_speed_scale:.1f}x")
    elif key == ord(">"):
        self.alife_speed_scale = min(3.0, self.alife_speed_scale * 1.25)
        self._flash(f"Speed scale: {self.alife_speed_scale:.1f}x")
    elif key == ord("q") or key == 27:
        self._exit_alife_mode()
    else:
        return True
    return True



def _draw_alife_menu(self, max_y: int, max_x: int):
    """Draw Artificial Life preset selection menu."""
    self.stdscr.erase()
    title = "=== Artificial Life Ecosystem ==="
    try:
        self.stdscr.addstr(1, max(0, (max_x - len(title)) // 2), title,
                           curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(3, 2, "Select an environment:", curses.color_pair(6))
    except curses.error:
        pass

    for i, (name, desc, _ptype) in enumerate(self.ALIFE_PRESETS):
        y = 5 + i * 2
        if y >= max_y - 2:
            break
        marker = ">" if i == self.alife_menu_sel else " "
        attr = curses.color_pair(3) | curses.A_BOLD if i == self.alife_menu_sel else curses.color_pair(0)
        try:
            self.stdscr.addstr(y, 3, f"{marker} {name}", attr)
            self.stdscr.addstr(y + 1, 7, desc[:max_x - 10], curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass

    hints = "j/k=navigate  Enter=select  q=cancel"
    try:
        self.stdscr.addstr(max_y - 1, 0, hints[:max_x - 1], curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass



def _draw_alife(self, max_y: int, max_x: int):
    """Draw the Artificial Life Ecosystem."""
    self.stdscr.erase()
    rows = min(self.alife_rows, max_y - 3)
    cols = min(self.alife_cols, max_x - 1)

    if rows <= 0 or cols <= 0:
        return

    # Food density characters and colors
    food_chars = [" ", ".", ":", ";", "+", "*", "#"]

    # Render food layer
    for r in range(rows):
        for c in range(cols):
            fv = self.alife_food[r][c] if r < len(self.alife_food) and c < len(self.alife_food[0]) else 0
            if fv > 0.05:
                fi = min(len(food_chars) - 1, int(fv * (len(food_chars) - 1)))
                ch = food_chars[fi]
                if ch != " ":
                    try:
                        self.stdscr.addstr(r + 1, c, ch, curses.color_pair(1) | curses.A_DIM)
                    except curses.error:
                        pass

    # Render creatures
    for cr in self.alife_creatures:
        ir, ic = int(cr["r"]), int(cr["c"])
        if ir < 0 or ir >= rows or ic < 0 or ic >= cols:
            continue
        diet = cr["diet"]
        size_idx = min(4, max(0, int(cr["size"] * 2) - 1))
        if diet == 0:
            ch = self.ALIFE_HERB_CHARS[size_idx]
            color = curses.color_pair(1)  # green for herbivores
        elif diet == 1:
            ch = self.ALIFE_PRED_CHARS[size_idx]
            color = curses.color_pair(5)  # red for predators
        else:
            ch = self.ALIFE_OMNI_CHARS[size_idx]
            color = curses.color_pair(2)  # cyan for omnivores

        # Bright if high energy, dim if low
        if cr["energy"] > cr["max_energy"] * 0.6:
            color |= curses.A_BOLD
        elif cr["energy"] < cr["max_energy"] * 0.25:
            color |= curses.A_DIM

        try:
            self.stdscr.addstr(ir + 1, ic, ch, color)
        except curses.error:
            pass

    # Title bar
    n_total = len(self.alife_creatures)
    n_herb = sum(1 for cr in self.alife_creatures if cr["diet"] == 0)
    n_pred = sum(1 for cr in self.alife_creatures if cr["diet"] == 1)
    n_omni = sum(1 for cr in self.alife_creatures if cr["diet"] == 2)
    title = (f" Artificial Life: {self.alife_preset_name} | "
             f"Pop: {n_total} (H:{n_herb} P:{n_pred} O:{n_omni}) | "
             f"Gen: {self.alife_gen_max} | Tick: {self.alife_tick} ")
    try:
        self.stdscr.addstr(0, 0, title[:max_x - 1], curses.color_pair(0) | curses.A_REVERSE)
        # Pad title bar
        if len(title) < max_x:
            self.stdscr.addstr(0, len(title), " " * (max_x - len(title) - 1),
                               curses.color_pair(0) | curses.A_REVERSE)
    except curses.error:
        pass

    # Stats panel (right side)
    if self.alife_show_stats and n_total > 0 and max_x > 40:
        panel_w = min(30, max_x // 3)
        px = max_x - panel_w - 1
        py = 2

        # Compute dominant traits
        avg_speed = sum(cr["speed"] for cr in self.alife_creatures) / n_total
        avg_size = sum(cr["size"] for cr in self.alife_creatures) / n_total
        avg_sense = sum(cr["sense"] for cr in self.alife_creatures) / n_total
        avg_energy = sum(cr["energy"] for cr in self.alife_creatures) / n_total

        stats_lines = [
            f"=== Population Stats ===",
            f"Births: {self.alife_total_births}  Deaths: {self.alife_total_deaths}",
            f"Avg speed:  {avg_speed:.2f}",
            f"Avg size:   {avg_size:.2f}",
            f"Avg sense:  {avg_sense:.2f}",
            f"Avg energy: {avg_energy:.1f}",
            f"Food rate:  {self.alife_food_regrow:.3f}",
            f"Mutation:   {self.alife_mutation_rate:.2f}",
        ]

        # Population sparkline
        if len(self.alife_pop_history) > 2:
            spark_w = min(panel_w - 6, 20)
            stats_lines.append(f"Pop: {sparkline(self.alife_pop_history, spark_w)}")
            if any(h > 0 for h in self.alife_herb_history):
                stats_lines.append(f"  H: {sparkline(self.alife_herb_history, spark_w)}")
            if any(h > 0 for h in self.alife_pred_history):
                stats_lines.append(f"  P: {sparkline(self.alife_pred_history, spark_w)}")

        for i, line in enumerate(stats_lines):
            if py + i >= max_y - 2:
                break
            try:
                self.stdscr.addstr(py + i, px, line[:panel_w],
                                   curses.color_pair(6) | curses.A_DIM)
            except curses.error:
                pass

    # Help bar
    state = "PAUSED" if not self.alife_running else "RUNNING"
    help_text = (f" [{state}] space=pause  n=step  r=reset  m=menu  s=stats  "
                 f"f=food  +/-=regrow  </>=speed  q=quit")
    try:
        self.stdscr.addstr(max_y - 1, 0, help_text[:max_x - 1],
                           curses.color_pair(6) | curses.A_DIM)
    except curses.error:
        pass


# ══════════════════════════════════════════════════════════════════════════


def register(App):
    """Register alife mode methods on the App class."""
    App._enter_alife_mode = _enter_alife_mode
    App._exit_alife_mode = _exit_alife_mode
    App._alife_make_creature = _alife_make_creature
    App._alife_brain_forward = _alife_brain_forward
    App._alife_mutate_brain = _alife_mutate_brain
    App._alife_init = _alife_init
    App._alife_step = _alife_step
    App._handle_alife_menu_key = _handle_alife_menu_key
    App._handle_alife_key = _handle_alife_key
    App._draw_alife_menu = _draw_alife_menu
    App._draw_alife = _draw_alife

