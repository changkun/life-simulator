"""Shared test fixtures for the Life Simulator test suite."""
import time
import threading
import pytest

from life.grid import Grid
from life.constants import SPEEDS, SPEED_LABELS
from life.rules import RULE_PRESETS, rule_string, parse_rule_string
from life.patterns import PATTERNS, PUZZLES
from life.registry import MODE_CATEGORIES, MODE_REGISTRY


class MockStdscr:
    """Minimal curses screen stub for testing."""

    def __init__(self, rows=40, cols=120):
        self._rows = rows
        self._cols = cols

    def getmaxyx(self):
        return self._rows, self._cols

    def addstr(self, *args, **kwargs):
        pass

    def clear(self):
        pass

    def erase(self):
        pass

    def refresh(self):
        pass

    def nodelay(self, flag):
        pass

    def keypad(self, flag):
        pass

    def getch(self):
        return -1

    def timeout(self, ms):
        pass

    def move(self, y, x):
        pass

    def clrtoeol(self):
        pass

    def attron(self, attr):
        pass

    def attroff(self, attr):
        pass

    def inch(self, *args):
        return 0

    def getstr(self, *args, **kwargs):
        return b""

    def derwin(self, *args):
        return MockStdscr(self._rows, self._cols)

    def subwin(self, *args):
        return MockStdscr(self._rows, self._cols)


def make_mock_app(rows=40, cols=120, grid_rows=30, grid_cols=50):
    """Create a mock App instance suitable for testing modes.

    This avoids importing life.app (which triggers curses initialization)
    by building a lightweight object with the same attributes that modes need.
    """
    app = _MockApp()
    app.stdscr = MockStdscr(rows, cols)
    app.grid = Grid(grid_rows, grid_cols)
    app.running = False
    app.speed_idx = 2
    app.view_r = 0
    app.view_c = 0
    app.zoom_level = 1
    app.cursor_r = grid_rows // 2
    app.cursor_c = grid_cols // 2
    app.show_help = False
    app.message = ""
    app.message_time = 0.0
    app.pattern_menu = False
    app.stamp_menu = False
    app.dashboard = False
    app.dashboard_sel = 0
    app.dashboard_scroll = 0
    app.dashboard_search = ""
    app.dashboard_category_filter = None
    app.dashboard_favorites = set()
    app.dashboard_show_favorites_only = False
    app.dashboard_preview_tick = 0
    app.dashboard_last_preview_time = 0.0
    app.dashboard_tab = 0
    app.mode_browser = False
    app.mode_browser_sel = 0
    app.mode_browser_scroll = 0
    app.mode_browser_search = ""
    app.mode_browser_filtered = list(MODE_REGISTRY)
    app.pattern_list = []
    app.pattern_sel = 0
    app.pop_history = []
    app.state_history = {}
    app.cycle_detected = False
    app.draw_mode = None
    app.history = []
    app.history_max = 500
    app.timeline_pos = None
    app.bookmarks = []
    app.tt_history = []
    app.tt_max = 500
    app.tt_pos = None
    app._tt_last_gen = -1
    app.bookmark_menu = False
    app.bookmark_sel = 0
    app.rule_menu = False
    app.rule_preset_list = sorted(RULE_PRESETS.keys())
    app.rule_sel = 0
    app.compare_mode = False
    app.grid2 = None
    app.pop_history2 = []
    app.compare_rule_menu = False
    app.compare_rule_sel = 0
    # Timeline branching
    app.tbranch_mode = False
    app.tbranch_grid = None
    app.tbranch_pop_history = []
    app.tbranch_origin_gen = 0
    app.tbranch_fork_gen = 0
    app.tbranch_fork_menu = False
    app.tbranch_fork_menu_sel = 0
    # Race mode
    app.race_mode = False
    app.race_grids = []
    app.race_pop_histories = []
    app.race_rule_menu = False
    app.race_rule_sel = 0
    app.race_selected_rules = []
    app.race_start_gen = 0
    app.race_max_gens = 500
    app.race_finished = False
    app.race_winner = None
    app.race_stats = []
    app.race_state_hashes = []
    # Heatmap
    app.heatmap_mode = False
    app.heatmap = [[0] * grid_cols for _ in range(grid_rows)]
    app.heatmap_max = 0
    # Pattern search
    app.pattern_search_mode = False
    app.detected_patterns = []
    app._pattern_scan_gen = -1
    # Blueprint
    app.blueprint_mode = False
    app.blueprint_anchor = None
    app.blueprints = {}
    app.blueprint_menu = False
    app.blueprint_sel = 0
    # GIF recording
    app.recording = False
    app.recorded_frames = []
    app.recording_start_gen = 0
    # Cast recording
    app.cast_recording = False
    app.cast_frames = []
    app.cast_frames_plain = []
    app.cast_timestamps = []
    app.cast_start_time = 0.0
    app.cast_fps = 10
    app.cast_max_frames = 3000
    app.cast_last_capture = 0.0
    app.cast_export_menu = False
    app.cast_export_sel = 0
    app.cast_width = 80
    app.cast_height = 24
    # 3D iso
    app.iso_mode = False
    # Sound
    app.sound_engine = None
    app.sonify_enabled = False
    app._sonify_thread = None
    app._sonify_stop = threading.Event()
    app._sonify_state = {}
    app._sonify_prev_density = 0.0
    # Multiplayer
    app.mp_mode = False
    app.mp_net = None
    app.mp_role = None
    app.mp_phase = "idle"
    app.mp_player = 0
    app.mp_owner = []
    app.mp_scores = [0, 0]
    app.mp_round = 0
    app.mp_planning_deadline = 0.0
    app.mp_ready = [False, False]
    app.mp_sim_gens = 200
    app.mp_start_gen = 0
    app.mp_territory_bonus = [0, 0]
    app.mp_state_dirty = False
    app.mp_host_port = 7654
    app.mp_connect_addr = ""
    # Puzzle
    app.puzzle_mode = False
    app.puzzle_menu = False
    app.puzzle_sel = 0
    app.puzzle_phase = "idle"
    app.puzzle_current = None
    app.puzzle_placed_cells = set()
    app.puzzle_start_pop = 0
    app.puzzle_sim_gen = 0
    app.puzzle_peak_pop = 0
    app.puzzle_initial_bbox = None
    app.puzzle_state_hashes = {}
    app.puzzle_win_gen = None
    app.puzzle_score = 0
    app.puzzle_scores = {}
    # GA evolution
    app.evo_mode = False
    app.evo_menu = False
    app.evo_pop_size = 12
    app.evo_grid_gens = 200
    app.evo_mutation_rate = 0.15
    app.evo_elite_count = 4
    app.evo_generation = 0
    app.evo_grids = []
    app.evo_rules = []
    app.evo_fitness = []
    app.evo_pop_histories = []
    app.evo_sim_step = 0
    app.evo_phase = "idle"
    app.evo_sel = 0
    app.evo_menu_sel = 0
    app.evo_fitness_mode = "balanced"
    app.evo_best_ever = None
    app.evo_history = []
    # Evo playground
    app.ep_mode = False
    app.ep_menu = False
    app.ep_menu_sel = 0
    app.ep_mutation_rate = 0.15
    app.ep_generation = 0
    app.ep_sims = []
    app.ep_genomes = []
    app.ep_pop_histories = []
    app.ep_selected = set()
    app.ep_cursor = 0
    app.ep_sim_generation = 0
    app.ep_running = False
    app.ep_grid_rows = 3
    app.ep_grid_cols = 4
    app.ep_tile_h = 6
    app.ep_tile_w = 8
    # Evolution Lab
    app.elab_mode = False
    app.elab_menu = False
    app.elab_menu_sel = 0
    app.elab_pop_size = 12
    app.elab_eval_gens = 150
    app.elab_mutation_rate = 0.15
    app.elab_elite_count = 4
    app.elab_fitness_preset = "balanced"
    app.elab_auto_advance = True
    app.elab_generation = 0
    app.elab_sims = []
    app.elab_genomes = []
    app.elab_fitness = []
    app.elab_pop_histories = []
    app.elab_favorites = set()
    app.elab_cursor = 0
    app.elab_sim_step = 0
    app.elab_phase = "idle"
    app.elab_running = False
    app.elab_auto_breed = True
    app.elab_grid_rows = 3
    app.elab_grid_cols = 4
    app.elab_tile_h = 6
    app.elab_tile_w = 8
    app.elab_best_ever = None
    app.elab_history = []
    # Class-level constants (from the monolith)
    type(app).WOLFRAM_PRESETS = [
        (30, "Rule 30 -- chaotic / pseudorandom"),
        (90, "Rule 90 -- Sierpinski triangle (XOR)"),
        (110, "Rule 110 -- Turing-complete"),
        (184, "Rule 184 -- traffic flow model"),
        (73, "Rule 73 -- complex structures"),
        (54, "Rule 54 -- complex with triangles"),
        (150, "Rule 150 -- Sierpinski variant"),
        (22, "Rule 22 -- nested triangles"),
        (126, "Rule 126 -- complement of 90"),
        (250, "Rule 250 -- simple stripes"),
        (0, "Rule 0 -- all cells die"),
        (255, "Rule 255 -- all cells alive"),
    ]
    type(app).ANT_PRESETS = [
        ("RL", "Classic Langton's Ant -- produces highway after ~10k steps"),
        ("RLR", "3-color -- symmetric triangular patterns"),
        ("LLRR", "4-color -- grows a filled square"),
        ("LRRRRRLLR", "9-color -- intricate fractal growth"),
        ("RRLLLRLLLRRR", "12-color -- chaotic spiral expansion"),
        ("RRLL", "4-color -- diamond-shaped growth"),
        ("RLLR", "4-color -- square with internal structure"),
        ("LRRL", "4-color -- complex highway variant"),
    ]
    type(app).ANT_COLORS = [1, 2, 3, 4, 5, 6, 7, 8]
    # Wolfram mode defaults
    app.wolfram_mode = False
    app.wolfram_menu = False
    app.wolfram_running = False
    app.wolfram_rows = []
    app.wolfram_rule = 30
    app.wolfram_seed_mode = "center"
    app.wolfram_menu_sel = 0
    app.wolfram_width = 80
    # Ant mode defaults
    app.ant_mode = False
    app.ant_menu = False
    app.ant_running = False
    app.ant_grid = {}
    app.ant_ants = []
    app.ant_rule = "RL"
    app.ant_step_count = 0
    app.ant_num_ants = 1
    app.ant_steps_per_frame = 1
    app.ant_rows = 30
    app.ant_cols = 50
    return app


class _MockApp:
    """Lightweight stand-in for life.app.App that modes can bind to."""

    def _flash(self, msg):
        self.message = msg
        self.message_time = time.monotonic()

    def _prompt_text(self, prompt):
        return None


@pytest.fixture
def mock_app():
    """Pytest fixture returning a fresh MockApp."""
    return make_mock_app()
