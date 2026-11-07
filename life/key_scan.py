"""Read which keys a key handler checks for, from its source code.

App.run() hands some keys to global hotkeys and overlays before the active
mode sees them. It asks handler_keys() whether the mode binds a key itself,
so that the mode keeps it.

The scan collects every constant a handler compares its key argument
against: ``key == ord("g")``, ``key in (10, 13, curses.KEY_ENTER)``,
``ord("1") <= key <= ord("6")``, ``chr(key) in "abc"`` and module-level
constants. It follows calls that pass the key on to another function or to
a method of the owner class, so handlers that delegate are covered. Keys
built at run time (dict lookups, computed tables) are not found.
"""
import ast
import curses
import functools
import inspect
import textwrap


def _resolve(node, globs):
    """Value of a Name or module.attr expression in the handler's globals."""
    if isinstance(node, ast.Name):
        return globs.get(node.id)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id == "curses":
            return getattr(curses, node.attr, None)
        base = globs.get(node.value.id)
        return getattr(base, node.attr, None) if base is not None else None
    return None


def _codes(node, globs):
    """Key codes an expression on the other side of a comparison stands for."""
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool):
            return set()
        if isinstance(value, int):
            return {value}
        if isinstance(value, str):
            return {ord(c) for c in value}
        return set()
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "ord" and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and len(node.args[0].value) == 1):
        return {ord(node.args[0].value)}
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        out = set()
        for elt in node.elts:
            out |= _codes(elt, globs)
        return out
    value = _resolve(node, globs)
    if isinstance(value, int) and not isinstance(value, bool):
        return {value}
    if isinstance(value, str):
        return {ord(c) for c in value}
    if isinstance(value, (tuple, list, set, frozenset)):
        return {v for v in value if isinstance(v, int) and not isinstance(v, bool)}
    return set()


@functools.lru_cache(maxsize=None)
def handler_keys(fn, owner=None) -> frozenset:
    """Return the key codes that fn, a key handler taking (self, key), checks.

    owner is the class whose methods fn may call with the key.
    """
    return frozenset(_scan(fn, owner, set(), 0))


def _scan(fn, owner, seen, depth):
    fn = getattr(fn, "__func__", fn)
    if fn in seen or depth > 4:
        return set()
    seen.add(fn)
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    except (OSError, TypeError, SyntaxError):
        return set()
    fdef = tree.body[0] if tree.body else None
    if not isinstance(fdef, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return set()
    params = [a.arg for a in fdef.args.args]
    if params and params[0] == "self":
        params = params[1:]
    if not params:
        return set()
    names = {params[0]}
    globs = getattr(fn, "__globals__", {})

    # Plain aliases such as `ch = key`.
    for node in ast.walk(fdef):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Name)
                and node.value.id in names):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))

    def is_key(node):
        return isinstance(node, ast.Name) and node.id in names

    def is_chr_key(node):
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "chr" and len(node.args) == 1
                and is_key(node.args[0]))

    keys = set()
    for node in ast.walk(fdef):
        if isinstance(node, ast.Compare):
            operands = [node.left] + node.comparators
            if (len(operands) == 3 and is_key(operands[1])
                    and all(isinstance(op, (ast.Lt, ast.LtE)) for op in node.ops)):
                low, high = _codes(operands[0], globs), _codes(operands[2], globs)
                if len(low) == 1 and len(high) == 1:
                    lo, hi = low.pop(), high.pop()
                    lo += isinstance(node.ops[0], ast.Lt)
                    hi -= isinstance(node.ops[1], ast.Lt)
                    keys.update(range(lo, hi + 1))
            elif any(is_key(o) for o in operands):
                for o in operands:
                    if not is_key(o):
                        keys |= _codes(o, globs)
            elif any(is_chr_key(o) for o in operands):
                for o in operands:
                    if isinstance(o, ast.Constant) and isinstance(o.value, str):
                        keys.update(ord(c) for c in o.value)
        elif isinstance(node, ast.Call) and any(is_key(a) for a in node.args):
            func = node.func
            callee = None
            if isinstance(func, ast.Name):
                callee = globs.get(func.id)
            elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                  and func.value.id == "self" and owner is not None):
                callee = getattr(owner, func.attr, None)
            if inspect.isfunction(callee) or inspect.ismethod(callee):
                keys |= _scan(callee, owner, seen, depth + 1)
    return keys
