#!/usr/bin/env python3
"""Build a LINE WORKS operator handoff pack.

The CLI is intentionally thin: it reads refs, calls the shared handoff service,
and writes a runtime artifact. It performs no DB writes, no deploys, no service
restarts, no secret reads, and no external API calls.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_handoff.py"
DEFAULT_REFS = ROOT / "packets/product_av_ordering_ai/lineworks_release_refs_template.json"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/lineworks"
SERVICE_PACKAGE = "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services"


def ensure_package_stub(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    elif not hasattr(module, "__path__"):
        module.__path__ = [str(path)]  # type: ignore[attr-defined]


def load_handoff_service():
    ensure_package_stub("Taiji_Odoo", ROOT / "Taiji_Odoo")
    ensure_package_stub("Taiji_Odoo.addons", ROOT / "Taiji_Odoo/addons")
    ensure_package_stub(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway",
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway",
    )
    ensure_package_stub(SERVICE_PACKAGE, ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services")
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.lineworks_handoff", SERVICE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SERVICE}")
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
    return DEFAULT_OUT_DIR / f"LINEWORKS_OPERATOR_HANDOFF_PACK_{stamp}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a LINE WORKS operator handoff pack")
    parser.add_argument("--refs", default=str(DEFAULT_REFS), help="Path to lineworks release refs JSON")
    parser.add_argument("--message", default="LINE WORKS 操作交接包候選通知", help="Candidate message preview")
    parser.add_argument("--target-ref", default="TARGET_REF_HANDOFF_CHECK", help="Target ref or masked/hash ref")
    parser.add_argument("--actor-ref", default="ACTOR_REF_HANDOFF_CHECK", help="Actor ref or masked/hash ref")
    parser.add_argument("--operator-ref", default="OPERATOR_REF_HANDOFF_CHECK", help="Operator ref for activation draft")
    parser.add_argument("--channel", default="member_service", help="Notification channel")
    parser.add_argument("--confirm-human-activation", action="store_true", help="Mark activation true when inputs are safe")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    refs_path = Path(args.refs).expanduser()
    if not refs_path.is_absolute():
        refs_path = ROOT / refs_path
    refs = read_json(refs_path)

    service = load_handoff_service()
    pack = service.build_lineworks_operator_handoff_pack(
        refs=refs,
        refs_path=relative_path(refs_path),
        message=args.message,
        target_ref=args.target_ref,
        actor_ref=args.actor_ref,
        operator_ref=args.operator_ref,
        channel=args.channel,
        confirm_human_activation=args.confirm_human_activation,
    )

    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "W7TP_XIAOJ_LINEWORKS_OPERATOR_HANDOFF_REPORT_V1",
        "state": pack["state"],
        "output_path": relative_path(out_path),
        "operator_next_actions": pack.get("operator_next_actions", []),
        "side_effects": pack.get("side_effects", {}),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if pack["state"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
