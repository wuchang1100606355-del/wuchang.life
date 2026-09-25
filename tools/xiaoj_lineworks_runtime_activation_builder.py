#!/usr/bin/env python3
"""Build a LINE WORKS runtime activation packet for dry-run readiness."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_activation.py"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/lineworks"


def load_service():
    name = "lineworks_activation_builder_service"
    spec = importlib.util.spec_from_file_location(name, SERVICE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SERVICE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def default_out_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUT_DIR / f"LINEWORKS_RUNTIME_ACTIVATION_PACKET_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a LINE WORKS runtime activation packet")
    parser.add_argument("--operator-ref", default="", help="Operator hash or uppercase opaque ref")
    parser.add_argument("--execution-envelope-hash", default="", help="64-hex execution envelope hash")
    parser.add_argument("--candidate-packet-hash", default="", help="Optional 64-hex candidate packet hash")
    parser.add_argument("--release-packet-hash", default="", help="Optional 64-hex release packet hash")
    parser.add_argument("--reason-ref", default="REASON_REF_LINEWORKS_RUNTIME_DRY_RUN", help="Safe reason ref")
    parser.add_argument("--confirm-human-activation", action="store_true", help="Mark human activation true when inputs are safe")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    service = load_service()
    packet = service.build_lineworks_runtime_activation_packet(
        operator_ref=args.operator_ref,
        execution_envelope_hash=args.execution_envelope_hash,
        candidate_packet_hash=args.candidate_packet_hash,
        release_packet_hash=args.release_packet_hash,
        reason_ref=args.reason_ref,
        confirm_human_activation=args.confirm_human_activation,
    )
    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "W7TP_XIAOJ_LINEWORKS_RUNTIME_ACTIVATION_BUILDER_REPORT_V1",
        "state": packet["state"],
        "output_path": str(out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path),
        "activation_packet_hash": packet["activation_packet_hash"],
        "draft_warnings": packet["draft_warnings"],
        "side_effects": packet["side_effects"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if packet["state"] == "RUNTIME_ACTIVATION_PACKET_READY_FOR_DRY_RUN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
