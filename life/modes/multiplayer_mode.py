"""Mode: mp — simulation mode for the life package."""
import curses
import math
import random
import time


from life.colors import color_for_mp
from life.constants import CELL_CHAR, MP_DEFAULT_PORT, MP_PLANNING_TIME, MP_SIM_GENS, SPEEDS, SPEED_LABELS
from life.grid import Grid
from life.multiplayer import MultiplayerNet
from life.utils import sparkline

def _mp_init_owner_grid(self):
    """Create a fresh ownership grid matching the main grid dimensions."""
    self.mp_owner = [[0] * self.grid.cols for _ in range(self.grid.rows)]



def _mp_enter_host(self):
    """Start hosting a multiplayer game."""
    if self.mp_mode:
        self._mp_exit()
        return
    ps = self._prompt_text(f"Host on port (default {MP_DEFAULT_PORT})")
    if ps is None:
        return
    port = MP_DEFAULT_PORT
    if ps.strip():
        try:
            port = int(ps.strip())
        except ValueError:
            self._flash("Invalid port number")
            return
    net = MultiplayerNet()
    if not net.start_host(port):
        self._flash(f"Cannot bind to port {port}")
        return
    self.mp_net = net
    self.mp_mode = True
    self.mp_role = "host"
    self.mp_player = 1
    self.mp_phase = "lobby"
    self.mp_host_port = port
    self.running = False
    self._flash(f"Hosting on port {port} — waiting for opponent...")



def _mp_enter_client(self):
    """Connect to a multiplayer host."""
    if self.mp_mode:
        self._mp_exit()
        return
    addr = self._prompt_text("Connect to (host:port or host)")
    if not addr:
        return
    if ":" in addr:
        parts = addr.rsplit(":", 1)
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            self._flash("Invalid port")
            return
    else:
        host = addr
        port = MP_DEFAULT_PORT
    net = MultiplayerNet()
    self._flash(f"Connecting to {host}:{port}...")
    self.stdscr.refresh()
    if not net.connect(host, port):
        self._flash(f"Cannot connect to {host}:{port}")
        return
    self.mp_net = net
    self.mp_mode = True
    self.mp_role = "client"
    self.mp_player = 2
    self.mp_phase = "lobby"
    self.mp_connect_addr = addr
    self.running = False
    self._flash("Connected! Waiting for game setup...")



def _mp_exit(self):
    """Leave multiplayer mode and clean up."""
    if self.mp_net:
        self.mp_net.send({"type": "quit"})
        self.mp_net.stop()
    self.mp_mode = False
    self.mp_net = None
    self.mp_role = None
    self.mp_phase = "idle"
    self.mp_player = 0
    self.mp_owner = []
    self.mp_scores = [0, 0]
    self.mp_round = 0
    self.mp_ready = [False, False]
    self.running = False
    self._flash("Multiplayer ended")



def _mp_start_planning(self):
    """Begin the planning phase: clear grid, set territory, start timer."""
    self.grid.clear()
    self._mp_init_owner_grid()
    self.mp_phase = "planning"
    self.mp_ready = [False, False]
    self.mp_round += 1
    self.mp_planning_deadline = time.monotonic() + MP_PLANNING_TIME
    # Centre cursor in player's half
    half = self.grid.cols // 2
    if self.mp_player == 1:
        self.cursor_c = half // 2
    else:
        self.cursor_c = half + half // 2
    self.cursor_r = self.grid.rows // 2
    self._flash(f"Round {self.mp_round} — Place cells on your side! ({MP_PLANNING_TIME}s)")



def _mp_start_sim(self):
    """Transition from planning to simulation phase."""
    self.mp_phase = "running"
    self.mp_start_gen = self.grid.generation
    self.mp_scores = [0, 0]
    self.mp_territory_bonus = [0, 0]
    self.running = True
    self.speed_idx = 3  # 4× speed for watching
    self._flash("Simulation running! Watch your cells compete...")



def _mp_place_cell(self, r: int, c: int, alive: bool):
    """Place or remove a cell during planning, respecting territory."""
    half = self.grid.cols // 2
    # Player 1 owns left half, Player 2 owns right half
    if self.mp_player == 1 and c >= half:
        self._flash("You can only place on the LEFT side")
        return
    if self.mp_player == 2 and c < half:
        self._flash("You can only place on the RIGHT side")
        return
    if alive:
        self.grid.set_alive(r, c)
        self.mp_owner[r][c] = self.mp_player
    else:
        self.grid.set_dead(r, c)
        self.mp_owner[r][c] = 0
    # Send placement to peer
    if self.mp_net:
        self.mp_net.send({"type": "place", "r": r, "c": c, "alive": alive,
                          "player": self.mp_player})



def _mp_step(self):
    """Advance one generation with ownership tracking.

    New cells inherit the majority owner of their alive neighbours.
    Surviving cells keep their current owner.
    """
    rows, cols = self.grid.rows, self.grid.cols
    old_cells = self.grid.cells
    old_owner = self.mp_owner
    new_cells = [[0] * cols for _ in range(rows)]
    new_owner = [[0] * cols for _ in range(rows)]
    pop = 0
    for r in range(rows):
        for c in range(cols):
            n = self.grid._count_neighbours(r, c)
            alive = old_cells[r][c] > 0
            if alive and n in self.grid.survival:
                new_cells[r][c] = old_cells[r][c] + 1
                new_owner[r][c] = old_owner[r][c]
                pop += 1
            elif not alive and n in self.grid.birth:
                new_cells[r][c] = 1
                pop += 1
                # Determine owner from neighbours
                p1 = 0
                p2 = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        nr = (r + dr) % rows
                        nc = (c + dc) % cols
                        if old_cells[nr][nc] > 0:
                            ow = old_owner[nr][nc]
                            if ow == 1:
                                p1 += 1
                            elif ow == 2:
                                p2 += 1
                if p1 > p2:
                    new_owner[r][c] = 1
                elif p2 > p1:
                    new_owner[r][c] = 2
                else:
                    new_owner[r][c] = 0  # contested
    self.grid.cells = new_cells
    self.grid.generation += 1
    self.grid.population = pop
    self.mp_owner = new_owner



def _mp_calc_scores(self):
    """Calculate scores: cells owned + bonus for cells in enemy territory."""
    s1 = s2 = 0
    b1 = b2 = 0
    half = self.grid.cols // 2
    for r in range(self.grid.rows):
        for c in range(self.grid.cols):
            ow = self.mp_owner[r][c]
            if self.grid.cells[r][c] > 0:
                if ow == 1:
                    s1 += 1
                    if c >= half:  # P1 cell in P2's territory
                        b1 += 1
                elif ow == 2:
                    s2 += 1
                    if c < half:  # P2 cell in P1's territory
                        b2 += 1
    self.mp_scores = [s1, s2]
    self.mp_territory_bonus = [b1, b2]



def _mp_finish(self):
    """End the simulation round and show results."""
    self.mp_phase = "finished"
    self.running = False
    self._mp_calc_scores()
    s1, s2 = self.mp_scores
    b1, b2 = self.mp_territory_bonus
    total1 = s1 + b1 * 2  # territory bonus worth double
    total2 = s2 + b2 * 2
    if total1 > total2:
        winner = "Player 1 (Blue)"
    elif total2 > total1:
        winner = "Player 2 (Red)"
    else:
        winner = "TIE"
    self._flash(f"Round over! {winner} wins!  P1:{total1} P2:{total2}")
    if self.mp_net and self.mp_role == "host":
        self.mp_net.send({"type": "finished", "scores": [s1, s2],
                          "bonus": [b1, b2]})



def _mp_send_state(self):
    """Host sends full grid state + ownership to client."""
    if not self.mp_net or self.mp_role != "host":
        return
    cells = []
    for r in range(self.grid.rows):
        for c in range(self.grid.cols):
            age = self.grid.cells[r][c]
            if age > 0:
                cells.append((r, c, age, self.mp_owner[r][c]))
    self.mp_net.send({
        "type": "state",
        "gen": self.grid.generation,
        "cells": cells,
        "scores": self.mp_scores,
        "bonus": self.mp_territory_bonus,
    })



def _mp_recv_state(self, msg: dict):
    """Client applies a full state update from host."""
    self.grid.generation = msg["gen"]
    self.grid.cells = [[0] * self.grid.cols for _ in range(self.grid.rows)]
    self.mp_owner = [[0] * self.grid.cols for _ in range(self.grid.rows)]
    pop = 0
    for entry in msg["cells"]:
        r, c, age, ow = entry
        if 0 <= r < self.grid.rows and 0 <= c < self.grid.cols:
            self.grid.cells[r][c] = age
            self.mp_owner[r][c] = ow
            pop += 1
    self.grid.population = pop
    if "scores" in msg:
        self.mp_scores = msg["scores"]
    if "bonus" in msg:
        self.mp_territory_bonus = msg["bonus"]



def _mp_poll(self):
    """Process incoming network messages each frame."""
    if not self.mp_net:
        return
    for msg in self.mp_net.poll():
        mtype = msg.get("type")
        if mtype == "quit":
            self._flash("Opponent disconnected!")
            self._mp_exit()
            return
        elif mtype == "hello":
            # Client receives game config from host
            rows = msg.get("rows", self.grid.rows)
            cols = msg.get("cols", self.grid.cols)
            if rows != self.grid.rows or cols != self.grid.cols:
                self.grid = Grid(rows, cols)
            self.mp_sim_gens = msg.get("max_gens", MP_SIM_GENS)
            # Don't start planning yet — wait for explicit start_planning
        elif mtype == "start_planning":
            self._mp_start_planning()
        elif mtype == "place":
            r, c = msg["r"], msg["c"]
            player = msg.get("player", 0)
            if msg.get("alive", True):
                self.grid.set_alive(r, c)
                if 0 <= r < self.grid.rows and 0 <= c < self.grid.cols:
                    self.mp_owner[r][c] = player
            else:
                self.grid.set_dead(r, c)
                if 0 <= r < self.grid.rows and 0 <= c < self.grid.cols:
                    self.mp_owner[r][c] = 0
        elif mtype == "ready":
            peer = 2 if self.mp_player == 1 else 1
            self.mp_ready[peer - 1] = True
            self._flash("Opponent is ready!")
            if self.mp_ready[0] and self.mp_ready[1]:
                self._mp_start_sim()
                if self.mp_role == "host":
                    self.mp_net.send({"type": "start_sim"})
        elif mtype == "start_sim":
            self._mp_start_sim()
        elif mtype == "state":
            self._mp_recv_state(msg)
        elif mtype == "finished":
            self.mp_phase = "finished"
            self.running = False
            if "scores" in msg:
                self.mp_scores = msg["scores"]
            if "bonus" in msg:
                self.mp_territory_bonus = msg["bonus"]
    # Check for disconnection
    if self.mp_net and not self.mp_net.connected and self.mp_phase != "lobby":
        self._flash("Connection lost!")
        self._mp_exit()



def _mp_lobby_tick(self):
    """Host lobby: check if client connected, then send hello and start planning."""
    if self.mp_role == "host" and self.mp_net and self.mp_net.connected:
        self.mp_net.send({
            "type": "hello",
            "rows": self.grid.rows,
            "cols": self.grid.cols,
            "max_gens": self.mp_sim_gens,
        })
        self._mp_start_planning()
        self.mp_net.send({"type": "start_planning"})
    elif self.mp_role == "client":
        # Client waits for hello message (handled in _mp_poll)
        pass



def _mp_planning_tick(self):
    """Check planning timer and auto-ready if expired."""
    remaining = self.mp_planning_deadline - time.monotonic()
    if remaining <= 0 and not self.mp_ready[self.mp_player - 1]:
        self._mp_set_ready()



def _mp_set_ready(self):
    """Mark this player as ready."""
    self.mp_ready[self.mp_player - 1] = True
    if self.mp_net:
        self.mp_net.send({"type": "ready"})
    self._flash("Ready! Waiting for opponent...")
    if self.mp_ready[0] and self.mp_ready[1]:
        self._mp_start_sim()
        if self.mp_role == "host" and self.mp_net:
            self.mp_net.send({"type": "start_sim"})



def _mp_sim_tick(self):
    """Host runs simulation step and broadcasts state."""
    if self.mp_role != "host":
        return
    self._mp_step()
    self._mp_calc_scores()
    # Broadcast every 3 generations to reduce bandwidth
    if self.grid.generation % 3 == 0:
        self._mp_send_state()
    gens_elapsed = self.grid.generation - self.mp_start_gen
    if gens_elapsed >= self.mp_sim_gens:
        self._mp_finish()



def _handle_mp_planning_key(self, key: int) -> bool:
    """Handle input during multiplayer planning phase."""
    if key == -1:
        return True
    if key == ord("q"):
        self._mp_exit()
        return True
    # Movement
    if key in (curses.KEY_UP, ord("k")):
        self.cursor_r = (self.cursor_r - 1) % self.grid.rows
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.cursor_r = (self.cursor_r + 1) % self.grid.rows
        return True
    if key in (curses.KEY_LEFT, ord("h")):
        self.cursor_c = (self.cursor_c - 1) % self.grid.cols
        return True
    if key in (curses.KEY_RIGHT, ord("l")):
        self.cursor_c = (self.cursor_c + 1) % self.grid.cols
        return True
    # Place/remove cell
    if key == ord("e") or key == ord(" "):
        alive = self.grid.cells[self.cursor_r][self.cursor_c] == 0
        self._mp_place_cell(self.cursor_r, self.cursor_c, alive)
        return True
    if key == ord("d"):
        # Toggle draw mode for painting
        if self.draw_mode == "draw":
            self.draw_mode = None
            self._flash("Draw mode OFF")
        else:
            self.draw_mode = "draw"
            self._mp_place_cell(self.cursor_r, self.cursor_c, True)
            self._flash("Draw mode ON (move to paint)")
        return True
    if key == ord("x"):
        if self.draw_mode == "erase":
            self.draw_mode = None
            self._flash("Erase mode OFF")
        else:
            self.draw_mode = "erase"
            self._mp_place_cell(self.cursor_r, self.cursor_c, False)
            self._flash("Erase mode ON")
        return True
    if key == 27:  # ESC
        self.draw_mode = None
        return True
    # Ready up
    if key in (10, 13, curses.KEY_ENTER):
        if not self.mp_ready[self.mp_player - 1]:
            self._mp_set_ready()
        return True
    # Random fill on player's side
    if key == ord("r"):
        import random
        half = self.grid.cols // 2
        c_start = 0 if self.mp_player == 1 else half
        c_end = half if self.mp_player == 1 else self.grid.cols
        for r in range(self.grid.rows):
            for c in range(c_start, c_end):
                if random.random() < 0.15:
                    self.grid.set_alive(r, c)
                    self.mp_owner[r][c] = self.mp_player
        if self.mp_net:
            # Send all placements
            for r in range(self.grid.rows):
                for c in range(c_start, c_end):
                    if self.grid.cells[r][c] > 0:
                        self.mp_net.send({"type": "place", "r": r, "c": c,
                                          "alive": True, "player": self.mp_player})
        self._flash("Random fill on your territory!")
        return True
    # Clear player's side
    if key == ord("c"):
        half = self.grid.cols // 2
        c_start = 0 if self.mp_player == 1 else half
        c_end = half if self.mp_player == 1 else self.grid.cols
        for r in range(self.grid.rows):
            for c in range(c_start, c_end):
                if self.grid.cells[r][c] > 0:
                    self.grid.set_dead(r, c)
                    self.mp_owner[r][c] = 0
                    if self.mp_net:
                        self.mp_net.send({"type": "place", "r": r, "c": c,
                                          "alive": False, "player": self.mp_player})
        self._flash("Cleared your territory")
        return True
    return True



def _mp_apply_draw_mode(self):
    """Apply draw/erase under cursor during multiplayer planning, respecting territory."""
    if not self.draw_mode or self.mp_phase != "planning":
        return
    if self.mp_ready[self.mp_player - 1]:
        return  # already locked in
    half = self.grid.cols // 2
    c = self.cursor_c
    if (self.mp_player == 1 and c >= half) or (self.mp_player == 2 and c < half):
        return  # out of territory
    if self.draw_mode == "draw":
        self._mp_place_cell(self.cursor_r, self.cursor_c, True)
    elif self.draw_mode == "erase":
        self._mp_place_cell(self.cursor_r, self.cursor_c, False)



def _handle_mp_running_key(self, key: int) -> bool:
    """Handle input during multiplayer simulation phase."""
    if key == -1:
        return True
    if key == ord("q"):
        self._mp_exit()
        return True
    if key == ord(" "):
        self.running = not self.running
        return True
    if key == ord("+") or key == ord("="):
        if self.speed_idx < len(SPEEDS) - 1:
            self.speed_idx += 1
        return True
    if key == ord("-") or key == ord("_"):
        if self.speed_idx > 0:
            self.speed_idx -= 1
        return True
    # Arrow keys for scrolling viewport
    if key in (curses.KEY_UP, ord("k")):
        self.cursor_r = (self.cursor_r - 1) % self.grid.rows
        return True
    if key in (curses.KEY_DOWN, ord("j")):
        self.cursor_r = (self.cursor_r + 1) % self.grid.rows
        return True
    if key in (curses.KEY_LEFT, ord("h")):
        self.cursor_c = (self.cursor_c - 1) % self.grid.cols
        return True
    if key in (curses.KEY_RIGHT, ord("l")):
        self.cursor_c = (self.cursor_c + 1) % self.grid.cols
        return True
    return True



def _handle_mp_finished_key(self, key: int) -> bool:
    """Handle input on the multiplayer results screen."""
    if key == -1:
        return True
    if key == ord("q") or key == 27:
        self._mp_exit()
        return True
    # Enter = play again
    if key in (10, 13, curses.KEY_ENTER):
        if self.mp_role == "host" and self.mp_net:
            self._mp_start_planning()
            self.mp_net.send({"type": "start_planning"})
        else:
            self._flash("Waiting for host to start next round...")
        return True
    return True

# ── Save / Load ──



def _draw_mp_lobby(self, max_y: int, max_x: int):
    """Draw the waiting-for-connection lobby screen."""
    lines = [
        "╔════════════════════════════════════════════╗",
        "║        MULTIPLAYER — Waiting for Player    ║",
        "╠════════════════════════════════════════════╣",
        "║                                            ║",
    ]
    if self.mp_role == "host":
        lines.append(f"║  Hosting on port {self.mp_host_port:<25d} ║")
        lines.append("║  Waiting for opponent to connect...       ║")
    else:
        lines.append("║  Connecting...                            ║")
        lines.append("║  Waiting for host to start game...        ║")
    lines += [
        "║                                            ║",
        "║  You are: " + ("Player 1 (BLUE)" if self.mp_player == 1 else "Player 2 (RED) ") + "              ║",
        "║                                            ║",
        "║  Press q to cancel                         ║",
        "║                                            ║",
        "╚════════════════════════════════════════════╝",
    ]
    start_y = max(0, (max_y - len(lines)) // 2)
    for i, line in enumerate(lines):
        y = start_y + i
        if y >= max_y:
            break
        x = max(0, (max_x - len(line)) // 2)
        attr = curses.color_pair(7)
        try:
            self.stdscr.addstr(y, x, line, attr)
        except curses.error:
            pass



def _draw_mp_grid(self, max_y: int, max_x: int, status_rows: int = 5):
    """Render the grid with multiplayer ownership colours.

    Returns (vis_rows, vis_cols) used for layout.
    """
    vis_rows = max_y - status_rows
    vis_cols = (max_x - 1) // 2
    half = self.grid.cols // 2

    # Centre viewport on cursor
    self.view_r = self.cursor_r - vis_rows // 2
    self.view_c = self.cursor_c - vis_cols // 2

    for sy in range(min(vis_rows, self.grid.rows)):
        gr = (self.view_r + sy) % self.grid.rows
        for sx in range(min(vis_cols, self.grid.cols)):
            gc = (self.view_c + sx) % self.grid.cols
            age = self.grid.cells[gr][gc]
            is_cursor = (gr == self.cursor_r and gc == self.cursor_c)
            px = sx * 2
            py = sy
            if py >= max_y - 2 or px + 1 >= max_x:
                continue
            # Draw territory divider
            if gc == half:
                try:
                    self.stdscr.addstr(py, px, "│ ", curses.color_pair(6) | curses.A_DIM)
                except curses.error:
                    pass
                continue
            if age > 0:
                ow = 0
                if self.mp_owner and gr < len(self.mp_owner) and gc < len(self.mp_owner[0]):
                    ow = self.mp_owner[gr][gc]
                attr = color_for_mp(age, ow)
                if age > 3:
                    attr |= curses.A_BOLD
                if is_cursor:
                    attr |= curses.A_REVERSE
                try:
                    self.stdscr.addstr(py, px, CELL_CHAR, attr)
                except curses.error:
                    pass
            else:
                if is_cursor:
                    try:
                        self.stdscr.addstr(py, px, "▒▒", curses.color_pair(6) | curses.A_DIM)
                    except curses.error:
                        pass
    return vis_rows, vis_cols



def _draw_mp_planning(self, max_y: int, max_x: int):
    """Draw the multiplayer planning phase with grid and timer."""
    self._draw_mp_grid(max_y, max_x, status_rows=4)

    remaining = max(0, self.mp_planning_deadline - time.monotonic())
    my_ready = self.mp_ready[self.mp_player - 1]
    opp_ready = self.mp_ready[2 - self.mp_player]

    # Player info bar
    info_y = max_y - 4
    if info_y > 0:
        p_label = "P1 (BLUE)" if self.mp_player == 1 else "P2 (RED)"
        p_color = curses.color_pair(50) if self.mp_player == 1 else curses.color_pair(54)
        status = "READY" if my_ready else "PLACING"
        opp_status = "READY" if opp_ready else "placing..."
        info = f" You: {p_label} [{status}]  │  Opponent: [{opp_status}]  │  Round {self.mp_round}"
        try:
            self.stdscr.addstr(info_y, 0, info[:max_x - 1], p_color | curses.A_BOLD)
        except curses.error:
            pass

    # Timer bar
    timer_y = max_y - 3
    if timer_y > 0:
        secs = int(remaining)
        bar_width = max_x - 30
        if bar_width > 0:
            frac = remaining / MP_PLANNING_TIME
            filled = int(frac * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            timer_color = curses.color_pair(1) if remaining > 10 else curses.color_pair(5)
            timer_str = f" Time: {secs:2d}s [{bar}]"
            try:
                self.stdscr.addstr(timer_y, 0, timer_str[:max_x - 1], timer_color)
            except curses.error:
                pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        half_label = "LEFT" if self.mp_player == 1 else "RIGHT"
        status = (
            f" PLANNING — Place cells on {half_label} side  │  "
            f"Pop: {self.grid.population}  │  "
            f"Cursor: ({self.cursor_r},{self.cursor_c})"
        )
        try:
            self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                               curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [e/Space]=toggle cell [d]=draw [x]=erase [r]=random fill [c]=clear [Enter]=ready [q]=quit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_mp_game(self, max_y: int, max_x: int):
    """Draw the multiplayer simulation with scoreboard."""
    self._draw_mp_grid(max_y, max_x, status_rows=5)

    gens_elapsed = self.grid.generation - self.mp_start_gen
    gens_remain = max(0, self.mp_sim_gens - gens_elapsed)

    # Score bar
    score_y = max_y - 5
    if score_y > 0:
        s1, s2 = self.mp_scores
        b1, b2 = self.mp_territory_bonus
        total1 = s1 + b1 * 2
        total2 = s2 + b2 * 2
        # Score bar with proportional fill
        bar_width = max(10, max_x - 50)
        total = max(total1 + total2, 1)
        p1_fill = int(total1 / total * bar_width)
        p2_fill = bar_width - p1_fill
        p1_bar = "█" * p1_fill
        p2_bar = "█" * p2_fill
        try:
            self.stdscr.addstr(score_y, 0, " P1:", curses.color_pair(50) | curses.A_BOLD)
            self.stdscr.addstr(score_y, 4, f"{total1:4d} ", curses.color_pair(51))
            self.stdscr.addstr(score_y, 10, p1_bar, curses.color_pair(50))
            self.stdscr.addstr(score_y, 10 + p1_fill, p2_bar, curses.color_pair(54))
            p2_label = f" {total2:4d} :P2"
            self.stdscr.addstr(score_y, 10 + bar_width + 1, p2_label,
                               curses.color_pair(54) | curses.A_BOLD)
        except curses.error:
            pass

    # Progress bar
    prog_y = max_y - 4
    if prog_y > 0:
        frac = gens_elapsed / max(self.mp_sim_gens, 1)
        prog_w = max_x - 30
        if prog_w > 0:
            filled = int(frac * prog_w)
            bar = "█" * filled + "░" * (prog_w - filled)
            prog_str = f" Gen {gens_elapsed}/{self.mp_sim_gens} [{bar}]"
            try:
                self.stdscr.addstr(prog_y, 0, prog_str[:max_x - 1],
                                   curses.color_pair(6))
            except curses.error:
                pass

    # Population sparkline
    spark_y = max_y - 3
    if spark_y > 0:
        # Quick sparkline from current pop
        s1, s2 = self.mp_scores
        info = f" P1 cells: {s1}  │  P2 cells: {s2}  │  Total: {self.grid.population}"
        try:
            self.stdscr.addstr(spark_y, 0, info[:max_x - 1], curses.color_pair(6))
        except curses.error:
            pass

    # Status bar
    status_y = max_y - 2
    if status_y > 0:
        state = "▶ RUNNING" if self.running else "⏸ PAUSED"
        speed = SPEED_LABELS[self.speed_idx]
        role = "HOST" if self.mp_role == "host" else "CLIENT"
        status = (
            f" MULTIPLAYER {role}  │  {state}  │  Speed: {speed}  │  "
            f"Round {self.mp_round}  │  {gens_remain} gens left"
        )
        try:
            self.stdscr.addstr(status_y, 0, status[:max_x - 1],
                               curses.color_pair(7) | curses.A_BOLD)
        except curses.error:
            pass

    # Hint bar
    hint_y = max_y - 1
    if hint_y > 0:
        now = time.monotonic()
        if self.message and now - self.message_time < 3.0:
            hint = f" {self.message}"
        else:
            hint = " [Space]=pause [+/-]=speed [Arrows]=scroll [q]=quit"
        try:
            self.stdscr.addstr(hint_y, 0, hint[:max_x - 1],
                               curses.color_pair(6) | curses.A_DIM)
        except curses.error:
            pass



def _draw_mp_finished(self, max_y: int, max_x: int):
    """Draw the multiplayer results screen."""
    s1, s2 = self.mp_scores
    b1, b2 = self.mp_territory_bonus
    total1 = s1 + b1 * 2
    total2 = s2 + b2 * 2

    if total1 > total2:
        winner_text = "Player 1 (BLUE) WINS!"
        winner_color = curses.color_pair(50)
    elif total2 > total1:
        winner_text = "Player 2 (RED) WINS!"
        winner_color = curses.color_pair(54)
    else:
        winner_text = "IT'S A TIE!"
        winner_color = curses.color_pair(58)

    lines = [
        ("╔════════════════════════════════════════════════╗", curses.color_pair(7)),
        ("║           MULTIPLAYER — ROUND OVER            ║", curses.color_pair(7)),
        ("╠════════════════════════════════════════════════╣", curses.color_pair(7)),
        ("║                                                ║", curses.color_pair(7)),
        (f"║  {winner_text:^44s}  ║", winner_color | curses.A_BOLD),
        ("║                                                ║", curses.color_pair(7)),
        (f"║  Player 1 (BLUE):                              ║", curses.color_pair(50)),
        (f"║    Cells alive: {s1:<6d}                         ║", curses.color_pair(51)),
        (f"║    Territory bonus: {b1:<4d} (x2 = {b1*2:<5d})         ║", curses.color_pair(51)),
        (f"║    TOTAL: {total1:<8d}                           ║", curses.color_pair(50) | curses.A_BOLD),
        ("║                                                ║", curses.color_pair(7)),
        (f"║  Player 2 (RED):                               ║", curses.color_pair(54)),
        (f"║    Cells alive: {s2:<6d}                         ║", curses.color_pair(55)),
        (f"║    Territory bonus: {b2:<4d} (x2 = {b2*2:<5d})         ║", curses.color_pair(55)),
        (f"║    TOTAL: {total2:<8d}                           ║", curses.color_pair(54) | curses.A_BOLD),
        ("║                                                ║", curses.color_pair(7)),
        ("║  Enter = play again  │  q/Esc = exit           ║", curses.color_pair(6)),
        ("║                                                ║", curses.color_pair(7)),
        ("╚════════════════════════════════════════════════╝", curses.color_pair(7)),
    ]
    start_y = max(0, (max_y - len(lines)) // 2)
    for i, (line, attr) in enumerate(lines):
        y = start_y + i
        if y >= max_y:
            break
        x = max(0, (max_x - len(line)) // 2)
        try:
            self.stdscr.addstr(y, x, line, attr)
        except curses.error:
            pass




def register(App):
    """Register mp mode methods on the App class."""
    App._mp_init_owner_grid = _mp_init_owner_grid
    App._mp_enter_host = _mp_enter_host
    App._mp_enter_client = _mp_enter_client
    App._mp_exit = _mp_exit
    App._mp_start_planning = _mp_start_planning
    App._mp_start_sim = _mp_start_sim
    App._mp_place_cell = _mp_place_cell
    App._mp_step = _mp_step
    App._mp_calc_scores = _mp_calc_scores
    App._mp_finish = _mp_finish
    App._mp_send_state = _mp_send_state
    App._mp_recv_state = _mp_recv_state
    App._mp_poll = _mp_poll
    App._mp_lobby_tick = _mp_lobby_tick
    App._mp_planning_tick = _mp_planning_tick
    App._mp_set_ready = _mp_set_ready
    App._mp_sim_tick = _mp_sim_tick
    App._handle_mp_planning_key = _handle_mp_planning_key
    App._mp_apply_draw_mode = _mp_apply_draw_mode
    App._handle_mp_running_key = _handle_mp_running_key
    App._handle_mp_finished_key = _handle_mp_finished_key
    App._draw_mp_lobby = _draw_mp_lobby
    App._draw_mp_grid = _draw_mp_grid
    App._draw_mp_planning = _draw_mp_planning
    App._draw_mp_game = _draw_mp_game
    App._draw_mp_finished = _draw_mp_finished

