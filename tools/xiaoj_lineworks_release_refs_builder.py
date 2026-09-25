#!/usr/bin/env python3
"""Build a LINE WORKS release refs draft from safe refs only.

The builder performs no DB writes, no deploys, no service restarts, no secret
reads, and no external API calls. It rejects secret-shaped values by keeping
them unverified and surfacing draft warnings.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_release_refs.py"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/lineworks"


def load_service():
    package_name = "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services.lineworks_release_refs"
    spec = importlib.util.spec_from_file_location(package_name, SERVICE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SERVICE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: str) -> dict:
    if not path:
        return {}
    json_path = Path(path).expanduser()
    if not json_path.is_absolute():
        json_path = ROOT / json_path
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{json_path} must contain a JSON object")
    return data


def default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_DIR / f"LINEWORKS_RELEASE_REFS_DRAFT_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a LINE WORKS release refs draft")
    parser.add_argument("--input", default="", help="Optional JSON file with lineworks_send and connector_refs")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--allow-verified", action="store_true", help="Preserve verified=true only when refs are safe")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    service = load_service()
    source = read_json(args.input)
    draft = service.build_lineworks_release_refs_draft(
        release_refs=source.get("lineworks_send", source),
        connector_refs=source.get("connector_refs", {}),
        allow_verified=args.allow_verified,
    )
    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(draft, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "W7TP_XIAOJ_LINEWORKS_RELEASE_REFS_BUILDER_REPORT_V1",
        "state": draft["state"],
        "output_path": str(out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path),
        "draft_hash": draft["draft_hash"],
        "draft_warnings": draft["draft_warnings"],
        "side_effects": draft["p1_side_effects"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if draft["state"] == "RELEASE_REFS_DRAFT_READY_FOR_READINESS_CHECK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
