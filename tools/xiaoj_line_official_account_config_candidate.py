#!/usr/bin/env python3
"""Build a LINE Official Account configuration candidate from operator intent."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_config.py"
DEFAULT_OUT_DIR = ROOT / "runtime/product_av_ordering_ai/line_official_account"
SERVICE_PACKAGE = "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services"


def ensure_package_stub(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    elif not hasattr(module, "__path__"):
        module.__path__ = [str(path)]  # type: ignore[attr-defined]


def load_service():
    ensure_package_stub("Taiji_Odoo", ROOT / "Taiji_Odoo")
    ensure_package_stub("Taiji_Odoo.addons", ROOT / "Taiji_Odoo/addons")
    ensure_package_stub(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway",
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway",
    )
    ensure_package_stub(SERVICE_PACKAGE, ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services")
    spec = importlib.util.spec_from_file_location(f"{SERVICE_PACKAGE}.line_official_account_config", SERVICE)
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
    return DEFAULT_OUT_DIR / f"LINE_OFFICIAL_ACCOUNT_CONFIG_CANDIDATE_{stamp}.json"


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a LINE Official Account configuration candidate")
    parser.add_argument("--intent", required=True, help="Natural-language operator intent")
    parser.add_argument("--refs", default="", help="Optional JSON with LINE Official Account refs")
    parser.add_argument("--style-ref", default="STYLE_REF_XIAOJ_WARM_PRECISE")
    parser.add_argument("--operator-ref", default="OPERATOR_REF_LINE_OFFICIAL_ACCOUNT_REVIEW")
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    service = load_service()
    refs = read_json(args.refs)
    candidate = service.build_line_official_account_config_candidate(
        args.intent,
        refs=refs,
        style_ref=args.style_ref,
        operator_ref=args.operator_ref,
    )
    out_path = Path(args.out).expanduser() if args.out else default_out_path()
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_CONFIG_CANDIDATE_REPORT_V1",
        "state": candidate["state"],
        "output_path": relative_path(out_path),
        "packet_hash": candidate.get("authority_packet", {}).get("packet_hash", ""),
        "failure_reasons": candidate.get("local_verifier", {}).get("failure_reasons", []),
        "side_effects": candidate.get("side_effects", {}),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if candidate["state"] == "READY_FOR_HUMAN_APPROVAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
