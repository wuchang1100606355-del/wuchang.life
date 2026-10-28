#!/usr/bin/env python3
"""Inventory skill definitions and Total Field manifests without activation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() in {"name", "description"}:
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def find_skill_files(root: Path, include_uninstalled: bool) -> list[Path]:
    root = root.resolve()
    paths = []
    for path in root.rglob("SKILL.md"):
        relative = path.relative_to(root)
        if not include_uninstalled and relative.parts and relative.parts[0] == "uninstalled":
            continue
        paths.append(path)
    return sorted(paths)


def inventory(root: Path, include_uninstalled: bool = False) -> dict[str, Any]:
    root = root.resolve()
    entries = []
    names: dict[str, list[str]] = {}
    for skill_file in find_skill_files(root, include_uninstalled):
        skill_dir = skill_file.parent
        relative_dir = skill_dir.relative_to(root).as_posix()
        metadata = parse_frontmatter(skill_file)
        name = metadata.get("name")
        manifest = skill_dir / "total-field-skill-manifest.json"
        manifest_state = None
        manifest_skill_id = None
        manifest_error = None
        if manifest.is_file():
            try:
                value = json.loads(manifest.read_text(encoding="utf-8"))
                manifest_state = value.get("manifest_state")
                manifest_skill_id = value.get("skill_id")
            except Exception as exc:
                manifest_error = type(exc).__name__
        status = (
            "MANIFEST_PRESENT"
            if manifest.is_file() and manifest_error is None
            else "MANIFEST_INVALID"
            if manifest.is_file()
            else "UNREGISTERED_CANDIDATE"
        )
        entries.append({
            "name": name,
            "description": metadata.get("description"),
            "path": relative_dir,
            "definition_status": status,
            "manifest": manifest.relative_to(root).as_posix() if manifest.is_file() else None,
            "manifest_state": manifest_state,
            "manifest_skill_id": manifest_skill_id,
            "manifest_error": manifest_error,
        })
        if name:
            names.setdefault(name, []).append(relative_dir)

    duplicates = {
        name: paths for name, paths in sorted(names.items()) if len(paths) > 1
    }
    missing = [item["path"] for item in entries if item["definition_status"] == "UNREGISTERED_CANDIDATE"]
    invalid = [item["path"] for item in entries if item["definition_status"] == "MANIFEST_INVALID"]
    return {
        "state": "PASS_SKILL_INVENTORY_CREATED",
        "root": str(root),
        "skill_count": len(entries),
        "manifest_count": sum(item["manifest"] is not None for item in entries),
        "unregistered_candidate_count": len(missing),
        "invalid_manifest_count": len(invalid),
        "duplicate_names": duplicates,
        "unregistered_candidates": missing,
        "invalid_manifests": invalid,
        "skills": entries,
        "activation_performed": False,
        "forbidden_actions_performed": [],
        "next": (
            "DEFINE_MISSING_TOTAL_FIELD_SKILL_MANIFESTS"
            if missing or invalid or duplicates
            else "SUBMIT_CATALOG_CANDIDATE_TO_TOTAL_FIELD"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--include-uninstalled", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.root.is_dir():
        print(json.dumps({
            "state": "HOLD_SKILL_ROOT_NOT_FOUND",
            "root": str(args.root),
            "human_response": {
                "question": "為什麼還不能建立總場技能目錄？",
                "answer": "指定位置不是可讀取的技能目錄，因此沒有推測或啟用任何技能。",
                "solution": "請提供包含 SKILL.md 的技能根目錄；工具只會唯讀盤點。",
                "user_action_required": True
            },
            "forbidden_actions_performed": []
        }, ensure_ascii=False, indent=2))
        return 2
    result = inventory(args.root, args.include_uninstalled)
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        sys.stdout.write(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
