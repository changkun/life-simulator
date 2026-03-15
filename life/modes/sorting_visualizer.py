"""Mode: sortvis — simulation mode for the life package."""
import curses
import math
import random
import time


def _sortvis_generate_steps_bubble(arr: list[int]) -> list[tuple]:
    """Generate all steps for bubble sort."""
    a = arr[:]
    steps = []
    n = len(a)
    for i in range(n):
        for j in range(0, n - i - 1):
            steps.append(("cmp", j, j + 1, a[:]))
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                steps.append(("swap", j, j + 1, a[:]))
        steps.append(("sorted", n - i - 1, a[:]))
    return steps




def _sortvis_generate_steps_quick(arr: list[int]) -> list[tuple]:
    """Generate all steps for quicksort (Lomuto partition)."""
    a = arr[:]
    steps = []

    def partition(lo, hi):
        pivot = a[hi]
        steps.append(("pivot", hi, a[:]))
        i = lo
        for j in range(lo, hi):
            steps.append(("cmp", j, hi, a[:]))
            if a[j] <= pivot:
                a[i], a[j] = a[j], a[i]
                if i != j:
                    steps.append(("swap", i, j, a[:]))
                i += 1
        a[i], a[hi] = a[hi], a[i]
        if i != hi:
            steps.append(("swap", i, hi, a[:]))
        steps.append(("sorted", i, a[:]))
        return i

    def qsort(lo, hi):
        if lo < hi:
            p = partition(lo, hi)
            qsort(lo, p - 1)
            qsort(p + 1, hi)

    qsort(0, len(a) - 1)
    return steps




def _sortvis_generate_steps_merge(arr: list[int]) -> list[tuple]:
    """Generate all steps for merge sort."""
    a = arr[:]
    steps = []

    def merge_sort(lo, hi):
        if lo >= hi:
            return
        mid = (lo + hi) // 2
        merge_sort(lo, mid)
        merge_sort(mid + 1, hi)
        # Merge
        left = a[lo:mid + 1]
        right = a[mid + 1:hi + 1]
        i = j = 0
        k = lo
        while i < len(left) and j < len(right):
            steps.append(("cmp", lo + i, mid + 1 + j, a[:]))
            if left[i] <= right[j]:
                a[k] = left[i]
                steps.append(("write", k, a[:]))
                i += 1
            else:
                a[k] = right[j]
                steps.append(("write", k, a[:]))
                j += 1
            k += 1
        while i < len(left):
            a[k] = left[i]
            steps.append(("write", k, a[:]))
            i += 1
            k += 1
        while j < len(right):
            a[k] = right[j]
            steps.append(("write", k, a[:]))
            j += 1
            k += 1

    merge_sort(0, len(a) - 1)
    # Mark all sorted at end
    for idx in range(len(a)):
        steps.append(("sorted", idx, a[:]))
    return steps




def _sortvis_generate_steps_heap(arr: list[int]) -> list[tuple]:
    """Generate all steps for heap sort."""
    a = arr[:]
    steps = []
    n = len(a)

    def heapify(size, root):
        largest = root
        left = 2 * root + 1
        right = 2 * root + 2
        if left < size:
            steps.append(("cmp", largest, left, a[:]))
            if a[left] > a[largest]:
                largest = left
        if right < size:
            steps.append(("cmp", largest, right, a[:]))
            if a[right] > a[largest]:
                largest = right
        if largest != root:
            a[root], a[largest] = a[largest], a[root]
            steps.append(("swap", root, largest, a[:]))
            heapify(size, largest)

    # Build max heap
    for i in range(n // 2 - 1, -1, -1):
        heapify(n, i)
    # Extract elements
    for i in range(n - 1, 0, -1):
        a[0], a[i] = a[i], a[0]
        steps.append(("swap", 0, i, a[:]))
        steps.append(("sorted", i, a[:]))
        heapify(i, 0)
    steps.append(("sorted", 0, a[:]))
    return steps




def _sortvis_generate_steps_radix(arr: list[int]) -> list[tuple]:
    """Generate all steps for LSD radix sort."""
    a = arr[:]
    steps = []
    if not a:
        return steps
    max_val = max(a)
    exp = 1
    while max_val // exp > 0:
        # Counting sort by current digit
        output = [0] * len(a)
        count = [0] * 10
        for i in range(len(a)):
            digit = (a[i] // exp) % 10
            steps.append(("read", i, a[:]))
            count[digit] += 1
        for i in range(1, 10):
            count[i] += count[i - 1]
        for i in range(len(a) - 1, -1, -1):
            digit = (a[i] // exp) % 10
            count[digit] -= 1
            output[count[digit]] = a[i]
        for i in range(len(a)):
            if a[i] != output[i]:
                a[i] = output[i]
                steps.append(("write", i, a[:]))
        exp *= 10
    for idx in range(len(a)):
        steps.append(("sorted", idx, a[:]))
    return steps




def _sortvis_generate_steps_shell(arr: list[int]) -> list[tuple]:
    """Generate all steps for shell sort."""
    a = arr[:]
    steps = []
    n = len(a)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = a[i]
            j = i
            while j >= gap:
                steps.append(("cmp", j, j - gap, a[:]))
                if a[j - gap] > temp:
                    a[j] = a[j - gap]
                    steps.append(("swap", j, j - gap, a[:]))
                    j -= gap
                else:
                    break
            a[j] = temp
            if j != i:
                steps.append(("write", j, a[:]))
        gap //= 2
    for idx in range(n):
        steps.append(("sorted", idx, a[:]))
    return steps




def _enter_sortvis_mode(self):
    """Enter Sorting Algorithm Visualizer — show preset menu."""
    self.sortvis_menu = True
    self.sortvis_menu_sel = 0




def _exit_sortvis_mode(self):
    """Exit Sorting Algorithm Visualizer."""
    self.sortvis_mode = False
    self.sortvis_menu = False
    self.sortvis_running = False
    self.sortvis_steps = []
    self.sortvis_array = []
    self.sortvis_sorted_indices = set()




def _sortvis_init(self, preset: str):
    """Initialize sorting visualization from preset."""
    import random as _rnd
    rows, cols = self.grid.rows, self.grid.cols
    self.sortvis_rows = rows
    self.sortvis_cols = cols
    self.sortvis_generation = 0
    self.sortvis_step_idx = 0
    self.sortvis_comparisons = 0
    self.sortvis_swaps = 0
    self.sortvis_highlight_cmp = ()
    self.sortvis_highlight_swap = ()
    self.sortvis_sorted_indices = set()
    self.sortvis_done = False
    self.sortvis_algorithm = preset

    # Size array to fit terminal width (each bar gets ~1-2 cols)
    self.sortvis_array_size = min(max(20, cols - 4), 200)
    max_val = max(10, rows - 6)
    self.sortvis_array = list(range(1, self.sortvis_array_size + 1))
    # Scale values to fit display height
    for i in range(len(self.sortvis_array)):
        self.sortvis_array[i] = max(1, int(self.sortvis_array[i] * max_val / self.sortvis_array_size))
    _rnd.shuffle(self.sortvis_array)

    # Pre-compute all sorting steps
    generators = {
        "bubble": _sortvis_generate_steps_bubble,
        "quick": _sortvis_generate_steps_quick,
        "merge": _sortvis_generate_steps_merge,
        "heap": _sortvis_generate_steps_heap,
        "radix": _sortvis_generate_steps_radix,
        "shell": _sortvis_generate_steps_shell,
    }
    gen = generators.get(preset, _sortvis_generate_steps_bubble)
    self.sortvis_steps = gen(self.sortvis_array)




def _sortvis_step(self):
    """Advance sorting visualization by one step."""
    if self.sortvis_step_idx >= len(self.sortvis_steps):
        self.sortvis_done = True
        self.sortvis_running = False
        self.sortvis_highlight_cmp = ()
        self.sortvis_highlight_swap = ()
        # Mark all sorted
        self.sortvis_sorted_indices = set(range(len(self.sortvis_array)))
        return

    step = self.sortvis_steps[self.sortvis_step_idx]
    self.sortvis_step_idx += 1
    self.sortvis_generation += 1
    kind = step[0]

    if kind == "cmp":
        _, i, j, arr = step
        self.sortvis_array = arr
        self.sortvis_highlight_cmp = (i, j)
        self.sortvis_highlight_swap = ()
        self.sortvis_comparisons += 1
    elif kind == "swap":
        _, i, j, arr = step
        self.sortvis_array = arr
        self.sortvis_highlight_swap = (i, j)
        self.sortvis_highlight_cmp = ()
        self.sortvis_swaps += 1
    elif kind == "write":
        _, i, arr = step
        self.sortvis_array = arr
        self.sortvis_highlight_swap = (i,)
        self.sortvis_highlight_cmp = ()
        self.sortvis_swaps += 1
    elif kind == "sorted":
        if len(step) == 3:
            _, idx, arr = step
            self.sortvis_array = arr
        else:
            _, idx, arr = step[0], step[1], step[2] if len(step) > 2 else self.sortvis_array
        self.sortvis_sorted_indices.add(idx)
        self.sortvis_highlight_cmp = ()
        self.sortvis_highlight_swap = ()
    elif kind == "pivot":
        _, idx, arr = step
        self.sortvis_array = arr
        self.sortvis_highlight_cmp = (idx,)
        self.sortvis_highlight_swap = ()
    elif kind == "read":
        _, idx, arr = step
        self.sortvis_array = arr
        self.sortvis_highlight_cmp = (idx,)
        self.sortvis_highlight_swap = ()




def _handle_sortvis_menu_key(self, key: int) -> bool:
    """Handle keys in the sorting visualizer preset menu."""
    n = len(SORTVIS_PRESETS)
    if key in (curses.KEY_DOWN, ord('j')):
        self.sortvis_menu_sel = (self.sortvis_menu_sel + 1) % n
    elif key in (curses.KEY_UP, ord('k')):
        self.sortvis_menu_sel = (self.sortvis_menu_sel - 1) % n
    elif key in (27, ord('q')):
        self.sortvis_menu = False
        self.sortvis_mode = False
        self._exit_sortvis_mode()
    elif key in (10, 13, curses.KEY_ENTER):
        preset = SORTVIS_PRESETS[self.sortvis_menu_sel]
        self.sortvis_preset_name = preset[2]
        self._sortvis_init(preset[2])
        self.sortvis_menu = False
        self.sortvis_mode = True
        self.sortvis_running = True
    else:
        return True
    return True




def _handle_sortvis_key(self, key: int) -> bool:
    """Handle keys during sorting visualization."""
    if key in (27, ord('q')):
        self._exit_sortvis_mode()
        return True
    elif key == ord(' '):
        self.sortvis_running = not self.sortvis_running
    elif key in (ord('n'), ord('.')):
        self._sortvis_step()
    elif key == ord('r'):
        self._sortvis_init(self.sortvis_preset_name)
    elif key in (ord('R'), ord('m')):
        self.sortvis_menu = True
        self.sortvis_running = False
    elif key == ord('+'):
        self.sortvis_speed = min(50, self.sortvis_speed + 1)
    elif key == ord('-'):
        self.sortvis_speed = max(1, self.sortvis_speed - 1)
    elif key == ord('i'):
        self.sortvis_show_info = not self.sortvis_show_info
    else:
        return True
    return True




def _draw_sortvis_menu(self, max_y: int, max_x: int):
    """Draw the sorting visualizer preset selection menu."""
    self.stdscr.erase()
    title = "── Sorting Algorithm Visualizer ──"
    if max_x > len(title) + 2:
        self.stdscr.addstr(1, (max_x - len(title)) // 2, title, curses.A_BOLD)

    subtitle = "Watch classic sorting algorithms animate as colorful bar charts"
    if max_y > 3 and max_x > len(subtitle) + 2:
        self.stdscr.addstr(2, (max_x - len(subtitle)) // 2, subtitle, curses.A_DIM)

    # ASCII art bars
    art = [
        "  ██                           ",
        "  ██ ██                        ",
        "  ██ ██ ██                     ",
        "  ██ ██ ██ ██           ██     ",
        "  ██ ██ ██ ██ ██     ██ ██     ",
        "  ██ ██ ██ ██ ██  ██ ██ ██ ██  ",
        "  ██ ██ ██ ██ ██ ██ ██ ██ ██ ██",
        "  ─────────────────────────────",
        "   ↑↓ comparing   ↕ swapping  ",
    ]
    art_start = 4
    for i, line in enumerate(art):
        y = art_start + i
        if y >= max_y - len(SORTVIS_PRESETS) - 6:
            break
        x = (max_x - len(line)) // 2
        if x > 0 and y < max_y:
            try:
                self.stdscr.addstr(y, x, line, curses.A_DIM)
            except curses.error:
                pass

    menu_y = max(art_start + len(art) + 1, max_y // 2 - len(SORTVIS_PRESETS) // 2)
    header = "Select a sorting algorithm:"
    if menu_y - 1 > 0 and max_x > len(header) + 4:
        try:
            self.stdscr.addstr(menu_y - 1, 3, header, curses.A_BOLD)
        except curses.error:
            pass

    for i, (name, desc, _key) in enumerate(SORTVIS_PRESETS):
        y = menu_y + i
        if y >= max_y - 2:
            break
        marker = "▸ " if i == self.sortvis_menu_sel else "  "
        attr = curses.A_REVERSE if i == self.sortvis_menu_sel else 0
        line = f"{marker}{name:<22s} {desc}"
        try:
            self.stdscr.addstr(y, 2, line[:max_x - 4], attr)
        except curses.error:
            pass

    footer = " ↑↓=select  Enter=start  q=back "
    try:
        self.stdscr.addstr(max_y - 1, 0, footer[:max_x - 1], curses.A_DIM | curses.A_REVERSE)
    except curses.error:
        pass




def _draw_sortvis(self, max_y: int, max_x: int):
    """Draw the Sorting Algorithm Visualizer."""
    self.stdscr.erase()
    rows = min(max_y, self.sortvis_rows)
    cols = min(max_x, self.sortvis_cols)
    if rows < 10 or cols < 20:
        try:
            self.stdscr.addstr(0, 0, "Terminal too small")
        except curses.error:
            pass
        return

    n = len(self.sortvis_array)
    if n == 0:
        return

    # Reserve space: 1 line title, 1 line gap, bars area, 1 line baseline, 2 lines status
    bar_area_top = 2
    bar_area_bottom = rows - 3
    bar_height_max = bar_area_bottom - bar_area_top
    if bar_height_max < 3:
        bar_height_max = rows - 4
        bar_area_top = 1
        bar_area_bottom = bar_area_top + bar_height_max

    max_val = max(self.sortvis_array) if self.sortvis_array else 1

    # Compute bar width and spacing
    available_w = cols - 2  # margins
    bar_w = max(1, available_w // n)
    if bar_w > 3:
        bar_w = 3
    total_w = bar_w * n
    x_offset = max(1, (cols - total_w) // 2)

    # Title
    algo_names = {"bubble": "Bubble Sort", "quick": "Quicksort", "merge": "Merge Sort",
                  "heap": "Heap Sort", "radix": "Radix Sort (LSD)", "shell": "Shell Sort"}
    title = algo_names.get(self.sortvis_algorithm, "Sorting")
    if self.sortvis_done:
        title += " — COMPLETE"
    try:
        self.stdscr.addstr(0, (cols - len(title)) // 2, title, curses.A_BOLD)
    except curses.error:
        pass

    # Determine color pairs available
    has_color = curses.has_colors()

    # Draw bars
    for i in range(n):
        val = self.sortvis_array[i]
        bar_h = max(1, int(val * bar_height_max / max_val))
        bx = x_offset + i * bar_w

        if bx + bar_w > cols - 1:
            break

        # Determine bar color/attribute
        attr = 0
        if i in self.sortvis_sorted_indices:
            # Sorted — green/bold
            if has_color:
                attr = curses.color_pair(3)  # green
            else:
                attr = curses.A_DIM
        elif i in self.sortvis_highlight_swap:
            # Swapping — red/reverse
            if has_color:
                attr = curses.color_pair(2)  # red
            else:
                attr = curses.A_REVERSE
        elif i in self.sortvis_highlight_cmp:
            # Comparing — yellow/bold
            if has_color:
                attr = curses.color_pair(4)  # yellow
            else:
                attr = curses.A_BOLD

        # Draw the bar (bottom-up)
        char = "█" if bar_w == 1 else "██" if bar_w == 2 else "███"
        for row_off in range(bar_h):
            y = bar_area_bottom - row_off
            if bar_area_top <= y < rows - 2:
                try:
                    self.stdscr.addstr(y, bx, char[:bar_w], attr)
                except curses.error:
                    pass

    # Info panel
    if self.sortvis_show_info:
        progress = (self.sortvis_step_idx * 100 // max(1, len(self.sortvis_steps)))
        info_lines = [
            f"Algorithm: {algo_names.get(self.sortvis_algorithm, '?')}",
            f"Array size: {n}",
            f"Steps: {self.sortvis_step_idx}/{len(self.sortvis_steps)}",
            f"Comparisons: {self.sortvis_comparisons}",
            f"Swaps/writes: {self.sortvis_swaps}",
            f"Progress: {progress}%",
        ]
        panel_w = max(len(l) for l in info_lines) + 4
        panel_x = max(0, cols - panel_w - 1)
        panel_y = 1
        for idx, line in enumerate(info_lines):
            y = panel_y + idx
            if y < rows - 2:
                try:
                    self.stdscr.addstr(y, panel_x, f" {line:<{panel_w - 2}} ",
                                       curses.A_REVERSE)
                except curses.error:
                    pass

    # Status bar
    status_y = rows - 2
    state = "✓ DONE" if self.sortvis_done else ("▶ RUNNING" if self.sortvis_running else "⏸ PAUSED")
    progress = self.sortvis_step_idx * 100 // max(1, len(self.sortvis_steps))
    status = f" Step {self.sortvis_step_idx}/{len(self.sortvis_steps)}  {state}  cmp={self.sortvis_comparisons} swp={self.sortvis_swaps}  spd={self.sortvis_speed}x  [{progress}%]"
    try:
        self.stdscr.addstr(status_y, 0, status[:cols - 1], curses.A_REVERSE)
        pad = cols - 1 - len(status)
        if pad > 0:
            self.stdscr.addstr(status_y, len(status), " " * pad, curses.A_REVERSE)
    except curses.error:
        pass

    hint = " Space=play n=step +/-=speed i=info r=reset R=menu q=exit"
    if status_y + 1 < max_y:
        try:
            self.stdscr.addstr(status_y + 1, 0, hint[:cols - 1], curses.A_DIM)
        except curses.error:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  DNA Helix & Genetic Algorithm
# ═══════════════════════════════════════════════════════════════════════════════

DNAHELIX_PRESETS = [
    ("Classic Binary GA", "Evolve a 32-bit genome to match a random target — standard genetic algorithm", "classic"),
    ("OneMax Challenge", "Maximize the number of 1-bits in a 64-bit genome — classic GA benchmark", "onemax"),
    ("Long Strand", "128-bit genome with low mutation — watch slow convergence on a tall helix", "long"),
    ("Hyper-Mutation", "High mutation rate (10%) causes chaotic exploration before convergence", "hyper"),
    ("Minimal Pop", "Tiny population of 10 with a 48-bit target — strong genetic drift", "minimal"),
    ("Royal Road", "64-bit genome with 8-bit schema blocks — fitness jumps when full blocks match", "royal"),
]





def register(App):
    """Register sortvis mode methods on the App class."""
    App._sortvis_generate_steps_bubble = _sortvis_generate_steps_bubble
    App._sortvis_generate_steps_quick = _sortvis_generate_steps_quick
    App._sortvis_generate_steps_merge = _sortvis_generate_steps_merge
    App._sortvis_generate_steps_heap = _sortvis_generate_steps_heap
    App._sortvis_generate_steps_radix = _sortvis_generate_steps_radix
    App._sortvis_generate_steps_shell = _sortvis_generate_steps_shell
    App._enter_sortvis_mode = _enter_sortvis_mode
    App._exit_sortvis_mode = _exit_sortvis_mode
    App._sortvis_init = _sortvis_init
    App._sortvis_step = _sortvis_step
    App._handle_sortvis_menu_key = _handle_sortvis_menu_key
    App._handle_sortvis_key = _handle_sortvis_key
    App._draw_sortvis_menu = _draw_sortvis_menu
    App._draw_sortvis = _draw_sortvis

