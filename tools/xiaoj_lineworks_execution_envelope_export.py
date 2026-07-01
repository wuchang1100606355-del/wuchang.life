#!/usr/bin/env python3
"""Export a redacted LINE WORKS execution envelope.

This is an offline handoff artifact for the future P2 runtime connector. It
performs no DB writes, no deploys, no service restarts, no secret reads, and no
external API calls.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"
CONNECTOR = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_connector.py"
DEFAULT_REFS = ROOT / "packets/product_av_ordering_ai/lineworks_release_refs_template.json"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/lineworks"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_DIR / f"LINEWORKS_EXECUTION_ENVELOPE_{stamp}.json"


def build_export_report(
    refs: dict,
    refs_path: Path,
    message: str,
    target_ref: str,
    channel: str,
    actor_ref: str,
) -> dict[str, Any]:
    engine = load_module("p1_intent_engine_lineworks_export", ENGINE)
    connector = load_module("lineworks_connector_export", CONNECTOR)
    candidate = engine.lineworks_notify_payload(message, target_ref, channel, actor_ref)
    release_status = engine.formal_release_status_payload({"lineworks_send": refs.get("lineworks_send", {})})
    connector_refs = refs.get("connector_refs") if isinstance(refs.get("connector_refs"), dict) else {}
    return connector.build_lineworks_execution_envelope_export(
        candidate,
        release_status,
        connector_refs,
        refs_path=relative_path(refs_path),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a redacted LINE WORKS execution envelope")
    parser.add_argument("--refs", default=str(DEFAULT_REFS), help="Path to lineworks release refs JSON")
    parser.add_argument("--message", default="LINE WORKS 候選通知 envelope 匯出", help="Candidate message preview")
    parser.add_argument("--target-ref", default="TARGET_REF_EXPORT_CHECK", help="Target ref or masked/hash ref")
    parser.add_argument("--actor-ref", default="ACTOR_REF_EXPORT_CHECK", help="Actor ref or masked/hash ref")
    parser.add_argument("--channel", default="member_service", help="Notification channel")
    parser.add_argument("--out", default="", help="Output JSON path. Defaults to runtime/product_av_ordering_ai/lineworks")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    refs_path = Path(args.refs).expanduser()
    if not refs_path.is_absolute():
        refs_path = ROOT / refs_path
    refs = read_json(refs_path)
    report = build_export_report(refs, refs_path, args.message, args.target_ref, args.channel, args.actor_ref)

    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report["output_path"] = relative_path(out_path)
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report["state"] == "PASS_LINEWORKS_EXECUTION_ENVELOPE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
