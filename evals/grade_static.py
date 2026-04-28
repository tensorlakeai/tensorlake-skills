#!/usr/bin/env python3
"""Static check: flag method/attribute names used on tensorlake-typed objects
that do not exist on the resolved SDK class.

For each output.md under evals/workspace/iteration-N/eval-*/with_skill/, pulls
out python code blocks, parses them with ast, tracks which local names are
tensorlake-typed via imports and direct constructor calls (e.g.
`sb = Sandbox(...)`), and records every attribute access on those names whose
attr is not a member of the receiver's resolved class. Names that are
tensorlake-rooted but whose class can't be pinned (e.g. an imported helper
function or the `tensorlake` module itself) fall back to a loose check against
the union of all public names in the package. Result lands at
evals/workspace/iteration-N/static_check.json.

Catches hallucinated method names on known classes (e.g.
`sandbox.expose_port`, `sandbox.run_background`, `sandbox.run_command`)
without the cost of an LLM judge or a live execution sandbox.
"""
import argparse
import ast
import importlib
import inspect
import json
import pkgutil
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKSPACE = REPO / "evals" / "workspace"
CODE_FENCE = re.compile(r"```(?:python|py)\n(.*?)```", re.DOTALL)

_UNKNOWN = object()  # receiver isn't tensorlake-typed; skip the attr check entirely


def collect_sdk_info() -> tuple[dict[str, set[str]], dict[str, dict[str, str]], set[str], set[str]]:
    """Returns (class_members, method_returns, all_names, delegated_attrs).

    class_members maps a public tensorlake class's simple name to the set of
    its public attribute names. method_returns[cls][method] is the simple class
    name a method returns, when its return annotation resolves to a public
    tensorlake class — used to follow classmethod constructors like
    `Sandbox.create(...)` and instance methods like `sandbox.fork(...)`.
    all_names is the union of every public name found anywhere in the package,
    used as a loose fallback when we know a receiver is tensorlake-rooted but
    can't pin its class. delegated_attrs is the union of public attributes from
    classes that implement `__getattr__` (e.g. `Traced` exposes `.value` while
    delegating everything else to its wrapped result) — these names are
    always allowed on any tensorlake-typed receiver.
    """
    try:
        import tensorlake  # pyright: ignore[reportMissingImports]
    except ImportError as exc:
        sys.exit(f"tensorlake SDK not installed in this Python: {exc}")

    class_members: dict[str, set[str]] = {}
    method_returns: dict[str, dict[str, str]] = {}
    all_names: set[str] = set()
    delegated_attrs: set[str] = set()
    visited: set[str] = set()

    def class_attrs(cls: type) -> set[str]:
        attrs = {a for a in dir(cls) if not a.startswith("_")}
        # Pydantic / dataclass / annotation-only fields aren't always in dir().
        attrs.update(a for a in getattr(cls, "__annotations__", {}) if not a.startswith("_"))
        attrs.update(getattr(cls, "model_fields", {}) or {})
        return attrs

    # Match a simple identifier appearing inside a stringified annotation, so we can
    # pick `Sandbox` out of `'Sandbox'`, `Traced[Sandbox]`, `Sandbox | None`, etc.
    _name_re = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\b")

    def returned_class(annotation) -> str | None:
        """Reduce a return annotation to a simple tensorlake class name, if any."""
        if annotation is inspect.Signature.empty or annotation is None:
            return None
        if isinstance(annotation, type) and getattr(annotation, "__module__", "").startswith("tensorlake"):
            return annotation.__name__
        if isinstance(annotation, str):
            # PEP 563 stringified annotations preserve source text verbatim (including quotes,
            # generic brackets, unions). Prefer the last-matched known class so that generic
            # wrappers like `Traced[CommandResult]` resolve to the inner payload type.
            best: str | None = None
            for ident in _name_re.findall(annotation):
                if ident in class_members:
                    best = ident
            return best
        for arg in getattr(annotation, "__args__", ()) or ():
            inner = returned_class(arg)
            if inner:
                return inner
        return None

    def class_method_returns(cls: type) -> dict[str, str]:
        out: dict[str, str] = {}
        for name in dir(cls):
            if name.startswith("_"):
                continue
            try:
                meth = inspect.getattr_static(cls, name)
            except AttributeError:
                continue
            is_classmethod = isinstance(meth, classmethod)
            # Unwrap classmethod / staticmethod wrappers.
            target = meth.__func__ if isinstance(meth, (classmethod, staticmethod)) else meth
            if not callable(target):
                continue
            try:
                sig = inspect.signature(target)
            except (ValueError, TypeError):
                continue
            ret_cls = returned_class(sig.return_annotation)
            if not ret_cls and is_classmethod and sig.return_annotation is inspect.Signature.empty:
                # Convention: classmethods without an explicit return annotation are usually
                # alternate constructors that return their own class (e.g. `Sandbox.create`).
                ret_cls = cls.__name__
            if ret_cls:
                out[name] = ret_cls
        return out

    def visit(obj) -> None:
        mod_name = getattr(obj, "__name__", "")
        if mod_name in visited:
            return
        visited.add(mod_name)
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue
            all_names.add(attr_name)
            try:
                child = getattr(obj, attr_name)
            except Exception:
                continue
            if inspect.isclass(child) and getattr(child, "__module__", "").startswith("tensorlake"):
                attrs = class_attrs(child)
                class_members.setdefault(child.__name__, set()).update(attrs)
                all_names.update(attrs)
                if "__getattr__" in child.__dict__:
                    # Wrappers like `Traced` forward unknown attrs to a wrapped value;
                    # treat their own public attrs as universally accessible.
                    delegated_attrs.update(attrs)

    visit(tensorlake)
    for _, name, _ in pkgutil.walk_packages(tensorlake.__path__, prefix="tensorlake."):
        if name.startswith("tensorlake.vendor"):
            continue
        try:
            visit(importlib.import_module(name))
        except Exception:
            continue

    # Second pass: now that class_members is populated, resolve method return types
    # (forward refs by simple name need the full class set to be available).
    for cls_name in list(class_members):
        for mod_name in list(visited):
            try:
                mod = sys.modules.get(mod_name) or importlib.import_module(mod_name)
            except Exception:
                continue
            cls = getattr(mod, cls_name, None)
            if inspect.isclass(cls) and getattr(cls, "__module__", "").startswith("tensorlake"):
                method_returns.setdefault(cls_name, {}).update(class_method_returns(cls))
                break

    return class_members, method_returns, all_names, delegated_attrs


def root_name(node: ast.AST) -> str | None:
    """Walk a (possibly chained) Attribute/Call tree down to its root Name id."""
    while True:
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            break
    return node.id if isinstance(node, ast.Name) else None


def collect_typed_names(
    tree: ast.AST,
    class_members: dict[str, set[str]],
    method_returns: dict[str, dict[str, str]],
) -> dict[str, str | None]:
    """Map local name -> known tensorlake class name (precise) or None (loose).

    Loose means we know the name is tensorlake-rooted (e.g. an imported helper
    function or the `tensorlake` module itself) but can't pin it to a class.
    Types only propagate when the RHS resolves to a known tensorlake class via
    one of: direct constructor call (`Sandbox(...)`), classmethod constructor
    on a known class (`Sandbox.create(...)`), or instance method whose return
    annotation is a tensorlake class. Chained calls whose return type isn't a
    known tensorlake class do NOT propagate — that's what previously widened
    plain dicts/lists into "tensorlake-typed" and caused false positives.
    """
    types: dict[str, str | None] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("tensorlake"):
                    types[alias.asname or alias.name.split(".")[0]] = None
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("tensorlake"):
            for alias in node.names:
                local = alias.asname or alias.name
                # If the imported symbol is itself a class we know about, track it precisely.
                types[local] = alias.name if alias.name in class_members else None

    def constructor_class(value: ast.AST) -> str | None:
        """If `value` is a Call producing a known tensorlake class, return its class name."""
        if not isinstance(value, ast.Call):
            return None
        func = value.func
        if isinstance(func, ast.Name):
            # Direct constructor: `Sandbox(...)` where Sandbox was imported.
            t = types.get(func.id)
            return t if t in class_members else None
        if isinstance(func, ast.Attribute):
            # Resolve receiver's class so we can look up its method return type.
            owner = receiver_class(func.value, types, class_members)
            if isinstance(owner, str) and func.attr in method_returns.get(owner, {}):
                return method_returns[owner][func.attr]
            # Fallback: `mod.SomeClass(...)` with attr a known class name and chain rooted in tensorlake.
            if func.attr in class_members and root_name(func) in types:
                return func.attr
        return None

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                cls = constructor_class(node.value)
                if cls is None:
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id not in types:
                        types[target.id] = cls
                        changed = True
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if not (item.optional_vars and isinstance(item.optional_vars, ast.Name)):
                        continue
                    cls = constructor_class(item.context_expr)
                    if cls and item.optional_vars.id not in types:
                        types[item.optional_vars.id] = cls
                        changed = True
    return types


def receiver_class(node: ast.AST, types: dict[str, str | None], class_members: dict[str, set[str]]):
    """Resolve the immediate class of an attribute's receiver.

    Returns the class name (str), None for loose tensorlake-typed, or the
    sentinel _UNKNOWN if the receiver isn't tensorlake-typed at all.
    """
    if isinstance(node, ast.Name):
        return types.get(node.id, _UNKNOWN)
    if isinstance(node, ast.Attribute):
        outer = receiver_class(node.value, types, class_members)
        if outer is _UNKNOWN:
            return _UNKNOWN
        # We can only narrow further when the attr name is itself a known class.
        if node.attr in class_members:
            return node.attr
        return None
    if isinstance(node, ast.Call):
        return receiver_class(node.func, types, class_members)
    return _UNKNOWN


def find_unknown_attrs(
    code: str,
    class_members: dict[str, set[str]],
    method_returns: dict[str, dict[str, str]],
    all_names: set[str],
    delegated_attrs: set[str],
) -> tuple[list[str], str | None]:
    """Return (unknown attr chains, syntax error message or None)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [], f"syntax error: {exc.msg} at line {exc.lineno}"

    types = collect_typed_names(tree, class_members, method_returns)
    bad: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        owner = receiver_class(node.value, types, class_members)
        if isinstance(owner, str):
            if node.attr in class_members.get(owner, set()) or node.attr in delegated_attrs:
                continue
        elif owner is None:
            if node.attr in all_names:
                continue
        else:  # _UNKNOWN — receiver isn't tensorlake-typed
            continue
        bad.add(ast.unparse(node))

    return sorted(bad), None


def latest_iteration() -> int:
    nums = []
    for p in WORKSPACE.glob("iteration-*"):
        suffix = p.name.split("-", 1)[1]
        if suffix.isdigit():
            nums.append(int(suffix))
    if not nums:
        sys.exit("no iterations found in evals/workspace/")
    return max(nums)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iteration", type=int, help="iteration to check; default latest")
    args = ap.parse_args()

    iteration = args.iteration or latest_iteration()
    iter_dir = WORKSPACE / f"iteration-{iteration}"
    print(f"→ static check on iteration {iteration}", flush=True)

    print("  collecting SDK names...", end=" ", flush=True)
    class_members, method_returns, all_names, delegated_attrs = collect_sdk_info()
    typed_method_count = sum(len(v) for v in method_returns.values())
    print(
        f"{len(class_members)} classes, {typed_method_count} typed methods, "
        f"{len(all_names)} names, {len(delegated_attrs)} delegated",
        flush=True,
    )

    eval_dirs = [
        d for d in iter_dir.iterdir()
        if d.is_dir() and d.name.startswith("eval-") and d.name.split("-")[1].isdigit()
    ]
    findings = []
    total_unknown = 0
    for slug_dir in sorted(eval_dirs, key=lambda p: int(p.name.split("-")[1])):
        out_path = slug_dir / "with_skill" / "output.md"
        if not out_path.exists():
            continue
        eval_id = int(slug_dir.name.split("-")[1])

        blocks = CODE_FENCE.findall(out_path.read_text())
        try:
            files_data = json.loads((slug_dir / "with_skill" / "files.json").read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            files_data = {}
        for path, content in files_data.items():
            if path.endswith(".py") and isinstance(content, str):
                blocks.append(content)
        unknown_attrs: list[str] = []
        syntax_errors: list[str] = []
        for block in blocks:
            bad, err = find_unknown_attrs(block, class_members, method_returns, all_names, delegated_attrs)
            unknown_attrs.extend(bad)
            if err:
                syntax_errors.append(err)
        unknown_attrs = sorted(set(unknown_attrs))
        total_unknown += len(unknown_attrs)

        if unknown_attrs or syntax_errors:
            mark = f"✗ {len(unknown_attrs)} unknown"
            if syntax_errors:
                mark += f", {len(syntax_errors)} syntax"
        else:
            mark = "✓ clean"
        print(f"  • eval {eval_id}: {len(blocks)} blocks  {mark}", flush=True)
        for attr in unknown_attrs:
            print(f"      ✗ {attr}")
        for err in syntax_errors:
            print(f"      ! {err}")

        findings.append({
            "eval_id": eval_id,
            "code_blocks": len(blocks),
            "unknown_attrs": unknown_attrs,
            "syntax_errors": syntax_errors,
        })

    out = iter_dir / "static_check.json"
    out.write_text(json.dumps({
        "iteration": iteration,
        "sdk_class_count": len(class_members),
        "sdk_name_count": len(all_names),
        "total_unknown_attrs": total_unknown,
        "findings": findings,
    }, indent=2))
    print(f"✓ wrote {out}  —  {total_unknown} unknown attr(s) across {len(findings)} evals")
    sys.exit(1 if total_unknown else 0)


if __name__ == "__main__":
    main()
