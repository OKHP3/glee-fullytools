"""Structural guard for active Python tooling's public path-to-URL contract.

This is a deliberately focused lint, not a proof of arbitrary Python semantics.
It catches index-filename normalization and URL construction from filesystem
path expressions (including renamed intermediates). URL-to-file lookups and
ordinary relative-path reporting remain allowed. Only public_inventory.py owns
forward conversion; an unused import never exempts local conversion code.
"""
import ast
from pathlib import Path


def duplicate_url_rules(source: str) -> list[int]:
    tree = ast.parse(source)
    violations = set()
    helpers = set()
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "public_inventory":
            helpers.update(alias.asname or alias.name for alias in node.names
                           if alias.name == "derive_url")
        if isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names
                           if alias.name == "public_inventory")
    scopes = [tree, *(node for node in ast.walk(tree)
                      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))]
    for scope in scopes:
        # Don't mix unrelated functions' path variables at module scope.
        nodes = []

        def walk(node):
            if node is not scope and isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                return
            nodes.append(node)
            for child in ast.iter_child_nodes(node):
                walk(child)

        walk(scope)
        path_names = set()

        def path_derived(node):
            if isinstance(node, ast.Call):
                func = node.func
                if ((isinstance(func, ast.Name) and func.id in helpers)
                    or (isinstance(func, ast.Attribute) and func.attr == "derive_url"
                        and isinstance(func.value, ast.Name) and func.value.id in modules)):
                    return False
            return (
                (isinstance(node, ast.Name) and node.id in path_names)
                or (isinstance(node, ast.Attribute) and node.attr in {
                    "relative_to", "as_posix", "parts", "parent"
                })
                or any(path_derived(child) for child in ast.iter_child_nodes(node))
            )

        # Assignment order may differ across branches; reach a fixed point.
        changed = True
        while changed:
            before = set(path_names)
            for node in nodes:
                if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value:
                    if path_derived(node.value):
                        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                        path_names.update(
                            child.id for target in targets for child in ast.walk(target)
                            if isinstance(child, ast.Name)
                        )
            changed = before != path_names

        for node in nodes:
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"replace", "removesuffix", "rstrip"} and any(
                    isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                    and "index.html" in arg.value for arg in node.args
                ):
                    violations.add(node.lineno)
            # Slash-prefixed strings concatenated/interpolated with path data
            # are forward conversions; Path / "index.html" is inverse lookup.
            if isinstance(node, (ast.JoinedStr, ast.BinOp)):
                if isinstance(node, ast.BinOp) and not isinstance(node.op, ast.Add):
                    continue
                # Only inspect the string's prefix, not a slash separator
                # inside a diagnostic or a trailing slash on a report path.
                values = node.values[:1] if isinstance(node, ast.JoinedStr) else [node.left, node.right]
                if (isinstance(node, ast.JoinedStr) and node.values
                    and isinstance(node.values[0], ast.FormattedValue)
                    and isinstance(node.values[0].value, ast.Name)
                    and node.values[0].value.id in {"SITE", "ORIGIN"}):
                    values = node.values[1:2]
                has_slash = any(
                    isinstance(child, ast.Constant) and isinstance(child.value, str)
                    and child.value.startswith("/") for child in values
                )
                if has_slash and path_derived(node):
                    violations.add(node.lineno)
    return sorted(violations)


def scan_scripts(scripts: Path) -> list[str]:
    """Include newly added/nested tools; omit fixtures and retired scripts."""
    issues = []
    for path in sorted(scripts.rglob("*.py")):
        rel = path.relative_to(scripts)
        if {"tests", "archive", "__pycache__"} & set(rel.parts):
            continue
        if rel == Path("public_inventory.py"):
            continue
        for line in duplicate_url_rules(path.read_text(encoding="utf-8")):
            issues.append(f"{rel.as_posix()}:{line}: use public_inventory.derive_url")
    return issues