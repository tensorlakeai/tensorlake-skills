#!/usr/bin/env python3
"""Static check: flag method/attribute names used on tensorlake-typed objects
that do not exist anywhere in the installed `tensorlake` SDK.

For each output.md under evals/workspace/iteration-N/eval-*/with_skill/, pulls
out python code blocks, parses them with ast, tracks which local names are
tensorlake-typed (via imports + assignments from tensorlake-rooted calls), and
records every attribute access on those names whose attr is not a known SDK
name. Result lands at evals/workspace/iteration-N/static_check.json.

Catches the dominant no_docs failure mode (hallucinated APIs like
`sandbox.expose_port`, `sandbox.run_background`, `desktop.key`) without the
cost of an LLM judge or a live execution sandbox.
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


def collect_sdk_names() -> set[str]:
    """Every public attribute name reachable anywhere in the tensorlake package."""
    try:
        import tensorlake  # pyright: ignore[reportMissingImports]
    except ImportError as exc:
        sys.exit(f"tensorlake SDK not installed in this Python: {exc}")

    names: set[str] = set()
    visited: set[str] = set()

    def add_class_members(cls: type) -> None:
        for sub in dir(cls):
            if not sub.startswith("_"):
                names.add(sub)
        # Pydantic / dataclass / annotation-only fields aren't always in dir().
        for ann in getattr(cls, "__annotations__", {}):
            if not ann.startswith("_"):
                names.add(ann)
        for field in getattr(cls, "model_fields", {}) or {}:
            names.add(field)

    def visit(obj) -> None:
        mod_name = getattr(obj, "__name__", "")
        if mod_name in visited:
            return
        visited.add(mod_name)
        for attr_name in dir(obj):
            if attr_name.startswith("_"):
                continue
            names.add(attr_name)
            try:
                child = getattr(obj, attr_name)
            except Exception:
                continue
            if inspect.isclass(child) and getattr(child, "__module__", "").startswith("tensorlake"):
                add_class_members(child)

    visit(tensorlake)
    for _, name, _ in pkgutil.walk_packages(tensorlake.__path__, prefix="tensorlake."):
        if name.startswith("tensorlake.vendor"):
            continue
        try:
            visit(importlib.import_module(name))
        except Exception:
            continue
    return names


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


def collect_typed_names(tree: ast.AST) -> set[str]:
    """Names in this code block that refer to tensorlake-rooted objects."""
    typed: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("tensorlake"):
                    typed.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("tensorlake"):
            for alias in node.names:
                typed.add(alias.asname or alias.name)

    # Iterate to a fixed point: x = foo(); y = x.bar(); both should be marked.
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                rn = root_name(node.value)
                if rn in typed:
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id not in typed:
                            typed.add(target.id)
                            changed = True
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                        if root_name(item.context_expr) in typed and item.optional_vars.id not in typed:
                            typed.add(item.optional_vars.id)
                            changed = True
    return typed


def find_unknown_attrs(code: str, sdk_names: set[str]) -> tuple[list[str], str | None]:
    """Return (unknown attr chains, syntax error message or None)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [], f"syntax error: {exc.msg} at line {exc.lineno}"

    typed = collect_typed_names(tree)
    bad: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if root_name(node.value) not in typed:
            continue
        if node.attr in sdk_names:
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
    sdk_names = collect_sdk_names()
    print(f"{len(sdk_names)} names", flush=True)

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
        unknown_attrs: list[str] = []
        syntax_errors: list[str] = []
        for block in blocks:
            bad, err = find_unknown_attrs(block, sdk_names)
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
        "sdk_name_count": len(sdk_names),
        "total_unknown_attrs": total_unknown,
        "findings": findings,
    }, indent=2))
    print(f"✓ wrote {out}  —  {total_unknown} unknown attr(s) across {len(findings)} evals")
    sys.exit(1 if total_unknown else 0)


if __name__ == "__main__":
    main()
