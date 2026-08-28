#!/usr/bin/env python3
"""Dependency-free static type-resolution and JSON contract check."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import sys
import typing
from pathlib import Path


def check_contract(root: Path) -> dict[str, object]:
    failures: list[str] = []
    checked_functions = 0
    resolved_callables = 0
    src_root = root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    for path in sorted((root / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            checked_functions += 1
            if node.returns is None:
                failures.append(f"{path.relative_to(root)}:{node.lineno}:{node.name}:missing-return")
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            for argument in arguments:
                if argument.arg in {"self", "cls"}:
                    continue
                if argument.annotation is None:
                    failures.append(
                        f"{path.relative_to(root)}:{node.lineno}:{node.name}:{argument.arg}:missing-annotation"
                    )
            if node.args.vararg is not None and node.args.vararg.annotation is None:
                failures.append(f"{path.relative_to(root)}:{node.lineno}:{node.name}:vararg:missing-annotation")
            if node.args.kwarg is not None and node.args.kwarg.annotation is None:
                failures.append(f"{path.relative_to(root)}:{node.lineno}:{node.name}:kwarg:missing-annotation")

        relative = path.relative_to(src_root).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts.pop()
        if not parts:
            continue
        module_name = ".".join(parts)
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            failures.append(
                f"{path.relative_to(root)}:import-failed:{type(exc).__name__}"
            )
            continue
        callables: list[tuple[str, object]] = []
        for name, value in vars(module).items():
            if (
                inspect.isfunction(value)
                and value.__module__ == module_name
                and Path(value.__code__.co_filename).resolve() == path.resolve()
            ):
                callables.append((name, value))
            elif inspect.isclass(value) and value.__module__ == module_name:
                for method_name, descriptor in vars(value).items():
                    candidate = descriptor
                    if isinstance(descriptor, (classmethod, staticmethod)):
                        candidate = descriptor.__func__
                    if (
                        inspect.isfunction(candidate)
                        and Path(candidate.__code__.co_filename).resolve() == path.resolve()
                    ):
                        callables.append((f"{name}.{method_name}", candidate))
        for qualified_name, value in callables:
            try:
                hints = typing.get_type_hints(value)
                signature = inspect.signature(value)
            except Exception as exc:
                failures.append(
                    f"{path.relative_to(root)}:{qualified_name}:unresolved-type:"
                    f"{type(exc).__name__}"
                )
                continue
            resolved_callables += 1
            if "return" not in hints:
                failures.append(
                    f"{path.relative_to(root)}:{qualified_name}:unresolved-return"
                )
            for parameter in signature.parameters.values():
                if parameter.name in {"self", "cls"}:
                    continue
                if parameter.name not in hints:
                    failures.append(
                        f"{path.relative_to(root)}:{qualified_name}:"
                        f"{parameter.name}:unresolved-parameter"
                    )
    config = json.loads((root / "config" / "allowlist.json").read_text(encoding="utf-8"))
    if config.get("schema") != "W7TP_STATE_FIELD_MCP_FIXED_ALLOWLIST_CANDIDATE_V1":
        failures.append("config/allowlist.json:schema:mismatch")
    return {
        "check": "STATIC_ANNOTATION_RESOLUTION_AND_JSON_CONTRACT",
        "checked_functions": checked_functions,
        "resolved_runtime_callables": resolved_callables,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "note": (
            "Dependency-free bounded static check: parses every source, requires complete "
            "function annotations, imports every module, and resolves public callable type hints. "
            "It does not claim whole-program inference equivalent to mypy or pyright."
        ),
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = check_contract(root)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
