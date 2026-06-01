#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runtime Shadow Inventory

Scans runtime shadow/output directories and reports size, count, newest mtime,
largest files, and archive-age candidates.

Safety:
- no delete
- no move
- no compression
- no service restart
- no SSH
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRS = [
    "runtime/reports",
    "runtime/proofs",
    "runtime/merlin_apply_queue",
    "runtime/merlin_approval_gate",
    "runtime/merlin_intent_driver",
    "runtime/merlin_human_execution_checklist",
    "runtime/merlin_execution_result",
    "runtime/router_guard_dryrun",
    "runtime/patches",
]
DOC_OUT = ROOT / "docs" / "project" / "RUNTIME_SHADOW_INVENTORY.md"
REPORT_DIR = ROOT / "runtime" / "reports"


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for u in units:
        if x < 1024 or u == units[-1]:
            return f"{x:.1f} {u}" if u != "B" else f"{int(x)} B"
        x /= 1024
    return str(n)


def file_info(path: Path) -> Dict[str, Any]:
    st = path.stat()
    age_days = (now_utc().timestamp() - st.st_mtime) / 86400
    return {
        "path": str(path.relative_to(ROOT)),
        "size_bytes": st.st_size,
        "size": human_size(st.st_size),
        "mtime": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(),
        "age_days": round(age_days, 2),
    }


def scan_dir(rel: str) -> Dict[str, Any]:
    base = ROOT / rel
    if not base.exists():
        return {
            "dir": rel,
            "exists": False,
            "file_count": 0,
            "total_bytes": 0,
            "total_size": "0 B",
            "newest_mtime": "",
            "age_7d": 0,
            "age_30d": 0,
            "age_90d": 0,
            "top_files": [],
        }

    files = [p for p in base.rglob("*") if p.is_file()]
    infos = [file_info(p) for p in files]
    total = sum(i["size_bytes"] for i in infos)

    newest = max((i["mtime"] for i in infos), default="")
    top = sorted(infos, key=lambda x: x["size_bytes"], reverse=True)[:30]

    return {
        "dir": rel,
        "exists": True,
        "file_count": len(infos),
        "total_bytes": total,
        "total_size": human_size(total),
        "newest_mtime": newest,
        "age_7d": sum(1 for i in infos if i["age_days"] >= 7),
        "age_30d": sum(1 for i in infos if i["age_days"] >= 30),
        "age_90d": sum(1 for i in infos if i["age_days"] >= 90),
        "top_files": top,
    }


def build_report(limit: int) -> Dict[str, Any]:
    dirs = [scan_dir(d) for d in DEFAULT_DIRS]
    all_top: List[Dict[str, Any]] = []
    for d in dirs:
        all_top.extend(d["top_files"])
    all_top = sorted(all_top, key=lambda x: x["size_bytes"], reverse=True)[:limit]

    return {
        "tool": "runtime_shadow_inventory",
        "generated_at": now_utc().isoformat(),
        "delete": False,
        "move": False,
        "compress": False,
        "dirs": dirs,
        "summary": {
            "dir_count": len(dirs),
            "file_count": sum(d["file_count"] for d in dirs),
            "total_bytes": sum(d["total_bytes"] for d in dirs),
            "total_size": human_size(sum(d["total_bytes"] for d in dirs)),
            "age_7d": sum(d["age_7d"] for d in dirs),
            "age_30d": sum(d["age_30d"] for d in dirs),
            "age_90d": sum(d["age_90d"] for d in dirs),
        },
        "top_files": all_top,
    }


def to_markdown(r: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Runtime Shadow Inventory")
    lines.append("")
    lines.append(f"- Generated: `{r['generated_at']}`")
    lines.append("- Mode: `inventory only / no delete / no move / no compression`")
    lines.append(f"- Total files: `{r['summary']['file_count']}`")
    lines.append(f"- Total size: `{r['summary']['total_size']}`")
    lines.append(f"- >= 7 days: `{r['summary']['age_7d']}`")
    lines.append(f"- >= 30 days: `{r['summary']['age_30d']}`")
    lines.append(f"- >= 90 days: `{r['summary']['age_90d']}`")
    lines.append("")
    lines.append("## Directories")
    lines.append("")
    lines.append("| Dir | Exists | Files | Size | Newest | >=7d | >=30d | >=90d |")
    lines.append("|---|---:|---:|---:|---|---:|---:|---:|")
    for d in r["dirs"]:
        lines.append(
            f"| `{d['dir']}` | {d['exists']} | {d['file_count']} | {d['total_size']} | "
            f"`{d['newest_mtime']}` | {d['age_7d']} | {d['age_30d']} | {d['age_90d']} |"
        )
    lines.append("")
    lines.append("## Top Files")
    lines.append("")
    lines.append("| File | Size | Age days | MTime |")
    lines.append("|---|---:|---:|---|")
    for f in r["top_files"]:
        lines.append(f"| `{f['path']}` | {f['size']} | {f['age_days']} | `{f['mtime']}` |")
    lines.append("")
    lines.append("## Rule")
    lines.append("")
    lines.append("This report is inventory only. Do not delete or archive without explicit human review.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--no-doc", action="store_true")
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_OUT.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(args.limit)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIR / f"runtime_shadow_inventory_{ts}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = None
    if not args.no_doc:
        DOC_OUT.write_text(to_markdown(report), encoding="utf-8")
        md_path = str(DOC_OUT)

    print(json.dumps({
        "decision": "runtime_shadow_inventory_generated",
        "json": str(json_path),
        "markdown": md_path,
        "file_count": report["summary"]["file_count"],
        "total_size": report["summary"]["total_size"],
        "delete": False,
        "move": False,
        "compress": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
